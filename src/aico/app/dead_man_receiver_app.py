"""Standalone FastAPI process for durable external dead-man monitoring."""

from __future__ import annotations

import argparse
import asyncio
import hmac
import logging
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic
from typing import Annotated, Literal, Protocol, Self

import httpx
import uvicorn
from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from aico.app.dead_man_evidence_signing import (
    DeadManEvidenceSigner,
    DeadManEvidenceSigningError,
    load_evidence_signer,
    serialize_evidence_payload,
    serialize_signed_evidence_envelope,
)
from aico.app.dead_man_receiver import (
    DeadManMonitorConflictError,
    DeadManMonitorNotArmedError,
    DeadManNotificationCoordinator,
    DeadManNotificationPolicyConflictError,
    DeadManNotificationProbeContract,
    DeadManNotificationSink,
    QuorumDeadManNotificationSink,
    SQLiteDeadManReceiverStore,
    WebhookDeadManNotificationSink,
)
from aico.app.runtime_liveness import RuntimeLivenessPulse
from aico.app.runtime_owner import (
    RuntimeOwnerLock,
    RuntimeOwnershipError,
    runtime_owner_lock_path,
)

log = logging.getLogger(__name__)


class DeadManReceiverSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AICO_DEAD_MAN_",
        extra="ignore",
    )

    state_db_path: Path = Path("/data/dead-man.db")
    evidence_signing_private_key_path: Path | None = None
    pulse_bearer_token: SecretStr
    admin_bearer_token: SecretStr
    notification_webhook_url: SecretStr
    notification_bearer_token: SecretStr | None = None
    notification_fallback_webhook_url: SecretStr | None = None
    notification_fallback_bearer_token: SecretStr | None = None
    notification_minimum_acknowledgements: int = Field(default=1, ge=1)
    notification_timeout_seconds: float = Field(default=5, gt=0)
    notification_probe_contract: DeadManNotificationProbeContract = (
        DeadManNotificationProbeContract.DISABLED
    )
    notification_probe_interval_seconds: int = Field(default=900, ge=60)
    notification_probe_failure_threshold: int = Field(default=2, ge=2, le=10)
    notification_probe_max_age_seconds: int = Field(default=1800, ge=120)
    sweep_interval_seconds: float = Field(default=15, gt=0)
    host: str = "0.0.0.0"
    port: int = Field(default=8080, ge=1, le=65535)

    @model_validator(mode="after")
    def validate_security_boundary(self) -> Self:
        url = self.notification_webhook_url.get_secret_value().strip()
        primary_origin = _notification_origin(url)
        fallback = self.notification_fallback_webhook_url
        fallback_token = self.notification_fallback_bearer_token
        if fallback is None and fallback_token is not None:
            raise ValueError("dead-man notification fallback token requires fallback URL")
        route_count = 1
        if fallback is not None:
            fallback_origin = _notification_origin(fallback.get_secret_value().strip())
            if fallback_origin == primary_origin:
                raise ValueError("dead-man fallback must use a different HTTPS origin")
            route_count = 2
        primary_token = self.notification_bearer_token
        if (
            primary_token is not None
            and fallback_token is not None
            and hmac.compare_digest(
                primary_token.get_secret_value(), fallback_token.get_secret_value()
            )
        ):
            raise ValueError("dead-man notification bearer tokens must differ")
        if self.notification_minimum_acknowledgements > route_count:
            raise ValueError(
                "notification minimum acknowledgements cannot exceed configured routes"
            )
        if self.notification_probe_max_age_seconds < self.notification_probe_interval_seconds * 2:
            raise ValueError("notification probe max age must cover two intervals")
        if (
            self.notification_probe_contract
            is DeadManNotificationProbeContract.SILENT_ROUTE_PROBE_V1
            and route_count != 2
        ):
            raise ValueError("silent notification probe requires two notification routes")
        pulse_token = self.pulse_bearer_token.get_secret_value()
        admin_token = self.admin_bearer_token.get_secret_value()
        if len(pulse_token) < 32 or len(admin_token) < 32:
            raise ValueError("dead-man bearer tokens must contain at least 32 characters")
        if _is_placeholder_secret(pulse_token) or _is_placeholder_secret(admin_token):
            raise ValueError("dead-man bearer tokens cannot use placeholder values")
        if hmac.compare_digest(pulse_token, admin_token):
            raise ValueError("dead-man pulse and admin bearer tokens must differ")
        for notification_token in (primary_token, fallback_token):
            if notification_token is None:
                continue
            candidate = notification_token.get_secret_value()
            if hmac.compare_digest(candidate, pulse_token) or hmac.compare_digest(
                candidate, admin_token
            ):
                raise ValueError("dead-man notification tokens must differ from receiver authority")
        return self

    @property
    def notification_route_count(self) -> int:
        return 2 if self.notification_fallback_webhook_url is not None else 1


class DeadManArmRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    expires_after_seconds: int = Field(gt=0)


class RuntimeLivenessPulseRequest(RuntimeLivenessPulse):
    schema_version: Literal[2] = 2

    def to_pulse(self) -> RuntimeLivenessPulse:
        return RuntimeLivenessPulse.model_validate(self.model_dump(exclude={"schema_version"}))


class _ReceiverCheck(Protocol):
    async def check(self, *, now: datetime) -> object: ...


@dataclass(slots=True)
class ReceiverWorkerHealth:
    """Process-local progress evidence for the receiver-owned worker."""

    stale_after_seconds: float
    failure_threshold: int = 3
    last_success_at: float | None = None
    consecutive_failures: int = 0

    def __post_init__(self) -> None:
        if self.stale_after_seconds <= 0:
            raise ValueError("worker stale threshold must be positive")
        if self.failure_threshold <= 0:
            raise ValueError("worker failure threshold must be positive")

    def record_success(self, now: float) -> None:
        self.last_success_at = now
        self.consecutive_failures = 0

    def record_failure(self) -> None:
        self.consecutive_failures += 1

    def is_ready(self, now: float) -> bool:
        if self.last_success_at is None:
            return False
        if self.consecutive_failures >= self.failure_threshold:
            return False
        return now - self.last_success_at <= self.stale_after_seconds


def _is_placeholder_secret(value: str) -> bool:
    normalized = value.strip().lower()
    return normalized.startswith("replace-with-") or normalized in {
        "changeme",
        "change-me",
    }


def _notification_origin(value: str) -> tuple[str, int | None]:
    parsed = httpx.URL(value)
    if parsed.scheme != "https" or parsed.host is None:
        raise ValueError("AICO_DEAD_MAN_NOTIFICATION_WEBHOOK_URL must use HTTPS")
    return parsed.host, parsed.port


def build_dead_man_receiver_app(
    settings: DeadManReceiverSettings,
    *,
    notification_sink: DeadManNotificationSink | None = None,
    clock: Callable[[], datetime] | None = None,
    monotonic_clock: Callable[[], float] | None = None,
) -> FastAPI:
    """Build an independently deployable receiver with dedicated persistent state."""

    current_time = clock or (lambda: datetime.now(UTC))
    current_monotonic = monotonic_clock or monotonic
    evidence_signer = _evidence_signer(settings)
    store = SQLiteDeadManReceiverStore(settings.state_db_path)
    sink = notification_sink or _notification_sink(settings)
    coordinator = DeadManNotificationCoordinator(store=store, sink=sink)
    worker_health = ReceiverWorkerHealth(
        stale_after_seconds=settings.sweep_interval_seconds * 3,
    )
    state_path = settings.state_db_path.expanduser().resolve()
    owner_lock = RuntimeOwnerLock(
        runtime_owner_lock_path(state_path, base_dir=state_path.parent),
        resource_path=state_path,
    )
    wake = asyncio.Event()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.receiver_store = store
        try:
            owner_lock.acquire()
        except RuntimeOwnershipError:
            raise RuntimeError("dead-man receiver state owner is already active") from None
        try:
            try:
                configured_at = current_time()
                if (
                    settings.notification_probe_contract
                    is DeadManNotificationProbeContract.DISABLED
                ):
                    store.configure_notification_probe(
                        contract=settings.notification_probe_contract,
                        interval_seconds=settings.notification_probe_interval_seconds,
                        failure_threshold=settings.notification_probe_failure_threshold,
                        max_age_seconds=settings.notification_probe_max_age_seconds,
                        configured_at=configured_at,
                    )
                store.configure_notification_policy(
                    configured_routes=settings.notification_route_count,
                    minimum_acknowledgements=(settings.notification_minimum_acknowledgements),
                    configured_at=configured_at,
                )
                if (
                    settings.notification_probe_contract
                    is DeadManNotificationProbeContract.SILENT_ROUTE_PROBE_V1
                ):
                    store.configure_notification_probe(
                        contract=settings.notification_probe_contract,
                        interval_seconds=settings.notification_probe_interval_seconds,
                        failure_threshold=settings.notification_probe_failure_threshold,
                        max_age_seconds=settings.notification_probe_max_age_seconds,
                        configured_at=configured_at,
                    )
            except DeadManNotificationPolicyConflictError:
                raise RuntimeError(
                    "dead-man notification policy conflicts with pending delivery"
                ) from None
            try:
                await coordinator.check(now=current_time())
            except Exception as exc:
                worker_health.record_failure()
                log.error("Dead-man receiver startup check failed: type=%s", type(exc).__name__)
                raise RuntimeError("dead-man receiver startup check failed") from None
            worker_health.record_success(current_monotonic())
            worker = asyncio.create_task(
                _run_receiver_worker(
                    coordinator,
                    wake=wake,
                    interval_seconds=settings.sweep_interval_seconds,
                    clock=current_time,
                    health=worker_health,
                    monotonic_clock=current_monotonic,
                ),
                name="aico-dead-man-receiver-worker",
            )
            try:
                yield
            finally:
                worker.cancel()
                with suppress(asyncio.CancelledError):
                    await worker
        finally:
            owner_lock.release()

    app = FastAPI(title="AICO Dead-Man Receiver", lifespan=lifespan)
    app.state.receiver_store = store
    app.state.receiver_worker_health = worker_health
    _register_common_routes(app, store, worker_health, current_monotonic)
    _register_receiver_routes(app, settings, store, wake, current_time, evidence_signer)
    return app


def _register_receiver_routes(
    app: FastAPI,
    settings: DeadManReceiverSettings,
    store: SQLiteDeadManReceiverStore,
    wake: asyncio.Event,
    clock: Callable[[], datetime],
    evidence_signer: DeadManEvidenceSigner | None,
) -> None:
    _register_monitor_routes(app, settings, store, wake, clock)
    _register_evidence_routes(app, settings, store, wake, clock, evidence_signer)
    _register_pulse_route(app, settings, store, wake, clock)


def _register_common_routes(
    app: FastAPI,
    store: SQLiteDeadManReceiverStore,
    worker_health: ReceiverWorkerHealth,
    monotonic_clock: Callable[[], float],
) -> None:

    @app.exception_handler(RequestValidationError)
    async def invalid_request(
        _request: Request,
        _error: RequestValidationError,
    ) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": "invalid request"})

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    async def readyz() -> dict[str, str]:
        try:
            store.ping()
        except Exception:
            raise HTTPException(status_code=503, detail="not ready") from None
        if not worker_health.is_ready(monotonic_clock()):
            raise HTTPException(status_code=503, detail="not ready")
        return {"status": "ready"}


def _register_monitor_routes(
    app: FastAPI,
    settings: DeadManReceiverSettings,
    store: SQLiteDeadManReceiverStore,
    wake: asyncio.Event,
    clock: Callable[[], datetime],
) -> None:
    @app.get("/v1/notification-routes")
    async def notification_routes(
        authorization: Annotated[str | None, Header()] = None,
    ) -> dict[str, object]:
        _require_bearer(authorization, settings.admin_bearer_token)
        probe = store.get_notification_probe()
        return {
            "policy": store.get_notification_policy().model_dump(mode="json"),
            "routes": [route.model_dump(mode="json") for route in store.list_notification_routes()],
            "probe": {
                **probe.model_dump(mode="json"),
                "fresh": probe.is_fresh(at=clock()),
            },
            "pending_route_health_alerts": store.pending_route_health_alert_count(),
        }

    @app.post("/v1/monitors/{runtime_id}/arm")
    async def arm_monitor(
        runtime_id: str,
        body: DeadManArmRequest,
        authorization: Annotated[str | None, Header()] = None,
    ) -> dict[str, object]:
        _require_bearer(authorization, settings.admin_bearer_token)
        try:
            snapshot = store.arm(
                runtime_id,
                expires_after_seconds=body.expires_after_seconds,
                armed_at=clock(),
            )
        except (ValueError, DeadManMonitorConflictError) as exc:
            raise HTTPException(status_code=409, detail="monitor arm conflict") from exc
        wake.set()
        return snapshot.model_dump(mode="json")

    @app.post("/v1/monitors/{runtime_id}/disarm")
    async def disarm_monitor(
        runtime_id: str,
        authorization: Annotated[str | None, Header()] = None,
    ) -> dict[str, bool]:
        _require_bearer(authorization, settings.admin_bearer_token)
        disarmed = store.disarm(runtime_id)
        wake.set()
        return {"disarmed": disarmed}

    @app.get("/v1/monitors/{runtime_id}")
    async def monitor_status(
        runtime_id: str,
        authorization: Annotated[str | None, Header()] = None,
    ) -> dict[str, object]:
        _require_bearer(authorization, settings.admin_bearer_token)
        store.evaluate(now=clock())
        try:
            snapshot = store.get_monitor(runtime_id)
        except DeadManMonitorNotArmedError as exc:
            raise HTTPException(status_code=404, detail="monitor not found") from exc
        wake.set()
        return snapshot.model_dump(mode="json")


def _register_evidence_routes(
    app: FastAPI,
    settings: DeadManReceiverSettings,
    store: SQLiteDeadManReceiverStore,
    wake: asyncio.Event,
    clock: Callable[[], datetime],
    evidence_signer: DeadManEvidenceSigner | None,
) -> None:
    @app.get("/v1/monitors/{runtime_id}/evidence")
    async def monitor_evidence(
        runtime_id: str,
        authorization: Annotated[str | None, Header()] = None,
        max_outages: Annotated[int, Query(ge=1, le=100)] = 20,
    ) -> dict[str, object]:
        _require_bearer(authorization, settings.admin_bearer_token)
        generated_at = clock()
        store.evaluate(now=generated_at)
        try:
            bundle = store.export_evidence(
                runtime_id,
                generated_at=generated_at,
                max_outages=max_outages,
            )
        except DeadManMonitorNotArmedError as exc:
            raise HTTPException(status_code=404, detail="evidence not found") from exc
        wake.set()
        return bundle.model_dump(mode="json")

    @app.get("/v1/monitors/{runtime_id}/signed-evidence")
    async def signed_monitor_evidence(
        runtime_id: str,
        authorization: Annotated[str | None, Header()] = None,
        max_outages: Annotated[int, Query(ge=1, le=100)] = 20,
    ) -> Response:
        _require_bearer(authorization, settings.admin_bearer_token)
        if evidence_signer is None:
            raise HTTPException(status_code=503, detail="evidence signing is unavailable")
        generated_at = clock()
        store.evaluate(now=generated_at)
        try:
            bundle = store.export_evidence(
                runtime_id,
                generated_at=generated_at,
                max_outages=max_outages,
            )
        except DeadManMonitorNotArmedError as exc:
            raise HTTPException(status_code=404, detail="evidence not found") from exc
        envelope = evidence_signer.sign(serialize_evidence_payload(bundle))
        wake.set()
        return Response(
            content=serialize_signed_evidence_envelope(envelope),
            media_type="application/json",
        )


def _register_pulse_route(
    app: FastAPI,
    settings: DeadManReceiverSettings,
    store: SQLiteDeadManReceiverStore,
    wake: asyncio.Event,
    clock: Callable[[], datetime],
) -> None:
    @app.post("/v1/runtime-liveness/pulses")
    async def receive_pulse(
        body: RuntimeLivenessPulseRequest,
        authorization: Annotated[str | None, Header()] = None,
        idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    ) -> dict[str, object]:
        _require_bearer(authorization, settings.pulse_bearer_token)
        pulse = body.to_pulse()
        if idempotency_key is None or not hmac.compare_digest(
            idempotency_key,
            pulse.idempotency_key,
        ):
            raise HTTPException(status_code=409, detail="invalid idempotency key")
        try:
            receipt = store.accept(pulse, received_at=clock())
        except DeadManMonitorNotArmedError as exc:
            raise HTTPException(status_code=409, detail="monitor is not armed") from exc
        except DeadManMonitorConflictError as exc:
            raise HTTPException(status_code=409, detail="monitor TTL conflict") from exc
        wake.set()
        return receipt.model_dump(mode="json")


async def _run_receiver_worker(
    coordinator: _ReceiverCheck,
    *,
    wake: asyncio.Event,
    interval_seconds: float,
    clock: Callable[[], datetime],
    health: ReceiverWorkerHealth,
    monotonic_clock: Callable[[], float],
) -> None:
    while True:
        try:
            await coordinator.check(now=clock())
            health.record_success(monotonic_clock())
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            health.record_failure()
            log.error("Dead-man receiver worker failed: type=%s", type(exc).__name__)
        try:
            await asyncio.wait_for(wake.wait(), timeout=interval_seconds)
        except TimeoutError:
            pass
        wake.clear()


def _notification_sink(settings: DeadManReceiverSettings) -> DeadManNotificationSink:
    token = settings.notification_bearer_token
    primary = WebhookDeadManNotificationSink(
        url=settings.notification_webhook_url.get_secret_value(),
        bearer_token=token.get_secret_value() if token is not None else None,
        timeout_seconds=settings.notification_timeout_seconds,
    )
    fallback_url = settings.notification_fallback_webhook_url
    if fallback_url is None:
        return primary
    fallback_token = settings.notification_fallback_bearer_token
    fallback = WebhookDeadManNotificationSink(
        url=fallback_url.get_secret_value(),
        bearer_token=(fallback_token.get_secret_value() if fallback_token is not None else None),
        timeout_seconds=settings.notification_timeout_seconds,
    )
    return QuorumDeadManNotificationSink(
        sinks=(primary, fallback),
        minimum_acknowledgements=settings.notification_minimum_acknowledgements,
    )


def _evidence_signer(settings: DeadManReceiverSettings) -> DeadManEvidenceSigner | None:
    path = settings.evidence_signing_private_key_path
    if path is None:
        return None
    checkout = _source_checkout_root()
    try:
        return load_evidence_signer(
            path,
            forbidden_roots=(() if checkout is None else (checkout,)),
        )
    except DeadManEvidenceSigningError:
        raise RuntimeError("dead-man evidence signing key is invalid") from None


def _source_checkout_root() -> Path | None:
    for parent in Path(__file__).resolve().parents:
        if (parent / ".git").exists() and (parent / "pyproject.toml").is_file():
            return parent
    return None


def _require_bearer(value: str | None, expected: SecretStr) -> None:
    prefix = "Bearer "
    candidate = value.removeprefix(prefix) if value is not None else ""
    if (
        value is None
        or not value.startswith(prefix)
        or not hmac.compare_digest(
            candidate,
            expected.get_secret_value(),
        )
    ):
        raise HTTPException(
            status_code=401,
            detail="unauthorized",
            headers={"WWW-Authenticate": "Bearer"},
        )


def main() -> None:
    argparse.ArgumentParser(description="Run the independent AICO dead-man receiver.").parse_args()
    settings = DeadManReceiverSettings()  # type: ignore[call-arg]
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    uvicorn.run(
        build_dead_man_receiver_app(settings),
        host=settings.host,
        port=settings.port,
        access_log=False,
    )
