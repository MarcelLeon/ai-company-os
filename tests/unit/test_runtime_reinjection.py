from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

from aico.app.runtime_reinjection import (
    RuntimeReinjectionError,
    capture_runtime_reinjection_contract,
    verify_runtime_reinjection,
)
from aico.core.standing_autonomy import StandingAutonomyGrant, StandingAutonomyGrantSet


def test_runtime_reinjection_records_slots_not_values_and_allows_rotation(
    tmp_path: Path,
) -> None:
    checkout = _basic_checkout(tmp_path)
    env_path = checkout / ".env"

    contract, captured = capture_runtime_reinjection_contract(checkout)

    assert contract.channel == "telegram"
    assert contract.secret_slots == ("AICO_TELEGRAM_BOT_TOKEN",)
    assert contract.secret_values_recorded is False
    assert contract.secret_hashes_recorded is False
    assert contract.ai_provider_live_probe_required is True
    assert contract.provider_names == ("claude-code",)
    assert contract.provider_count == 1
    assert contract.standing_grant_required is False
    assert captured.operation == "capture"
    assert captured.standing_grant_count == 0
    assert captured.provider_names == ("claude-code",)
    assert captured.external_authentication_live_verified is False
    assert "first-private-runtime-token" not in contract.model_dump_json()
    assert not (checkout / ".aico").exists()

    env_path.write_text(
        env_path.read_text().replace(
            "first-private-runtime-token",
            "rotated-private-runtime-token",
        )
    )
    verified = verify_runtime_reinjection(contract, checkout)

    assert verified.operation == "verify-reinjection"
    assert verified.secret_slot_count == 1
    assert "rotated-private-runtime-token" not in verified.model_dump_json()


def test_runtime_reinjection_rejects_missing_placeholder_or_unsafe_environment(
    tmp_path: Path,
) -> None:
    checkout = _basic_checkout(tmp_path)
    env_path = checkout / ".env"
    contract, _ = capture_runtime_reinjection_contract(checkout)

    env_path.write_text(env_path.read_text().replace("first-private-runtime-token", ""))
    with pytest.raises(RuntimeReinjectionError, match="invalid"):
        verify_runtime_reinjection(contract, checkout)

    env_path.write_text(
        env_path.read_text().replace(
            "AICO_TELEGRAM_BOT_TOKEN=",
            "AICO_TELEGRAM_BOT_TOKEN=replace-with-private-token",
        )
    )
    with pytest.raises(RuntimeReinjectionError, match="invalid"):
        verify_runtime_reinjection(contract, checkout)

    env_path.write_text(
        env_path.read_text().replace(
            "replace-with-private-token",
            "restored-private-token",
        )
    )
    env_path.chmod(0o644)
    with pytest.raises(RuntimeReinjectionError, match="owner-only"):
        verify_runtime_reinjection(contract, checkout)


def test_runtime_reinjection_rejects_duplicate_keys_and_channel_slot_drift(
    tmp_path: Path,
) -> None:
    checkout = _basic_checkout(tmp_path)
    env_path = checkout / ".env"
    contract, _ = capture_runtime_reinjection_contract(checkout)

    env_path.write_text(env_path.read_text() + "AICO_TELEGRAM_BOT_TOKEN=second-token\n")
    with pytest.raises(RuntimeReinjectionError, match="duplicate"):
        verify_runtime_reinjection(contract, checkout)

    _write_env(
        checkout,
        channel="feishu",
        secret_lines=(
            "AICO_FEISHU_APP_ID=cli_test_app",
            "AICO_FEISHU_APP_SECRET=private-feishu-secret",
            "AICO_FEISHU_VERIFICATION_TOKEN=private-feishu-verification",
        ),
    )
    with pytest.raises(RuntimeReinjectionError, match="does not match"):
        verify_runtime_reinjection(contract, checkout)


def test_runtime_reinjection_rejects_tracked_environment(tmp_path: Path) -> None:
    checkout = _basic_checkout(tmp_path)
    _git(checkout, "add", "-f", ".env")
    _git(
        checkout,
        "-c",
        "user.name=AICO Test",
        "-c",
        "user.email=aico@example.invalid",
        "commit",
        "-q",
        "-m",
        "unsafe tracked environment",
    )

    with pytest.raises(RuntimeReinjectionError, match="must not be tracked"):
        capture_runtime_reinjection_contract(checkout)


def test_runtime_reinjection_validates_reissued_standing_grant_binding(
    tmp_path: Path,
) -> None:
    checkout = _basic_checkout(tmp_path)
    managed = checkout / "managed"
    managed.mkdir()
    project_path = checkout / "config/projects.json"
    project_path.parent.mkdir(exist_ok=True)
    project_path.write_text(json.dumps(_standing_project(managed)))
    grant_path = tmp_path / "owner-standing-grant.json"
    grant_path.write_text(
        StandingAutonomyGrantSet(
            grants=(
                StandingAutonomyGrant(
                    grant_id="grant-restored-1",
                    owner_id="owner-test",
                    channel_name="telegram",
                    target_id="chat-test",
                    project_id="aico",
                    charter_id="absence-loop",
                    expires_at=datetime(2027, 1, 1, tzinfo=UTC),
                    max_runs=1,
                    max_duration_seconds=300,
                    token_stop_threshold=100_000,
                ),
            )
        ).model_dump_json()
    )
    grant_path.chmod(0o600)
    _write_env(
        checkout,
        channel="telegram",
        secret_lines=("AICO_TELEGRAM_BOT_TOKEN=first-private-runtime-token",),
        extra_lines=(
            f"AICO_STANDING_AUTONOMY_GRANT_PATH={grant_path}",
            "AICO_MORNING_PUSH_ENABLED=true",
            "AICO_MORNING_PUSH_TARGET_ID=chat-test",
            "AICO_MORNING_PUSH_PROJECT=aico",
            "AICO_ENABLE_CODEX_ADAPTER=true",
            "AICO_CODEX_COMMAND=codex exec --sandbox read-only",
        ),
    )

    contract, evidence = capture_runtime_reinjection_contract(checkout)

    assert contract.standing_grant_required is True
    assert contract.provider_names == ("claude-code", "codex")
    assert evidence.standing_grant_count == 1
    rendered = evidence.model_dump_json()
    assert "owner-test" not in rendered
    assert "chat-test" not in rendered
    assert "grant-restored-1" not in rendered

    grant_path.write_text(StandingAutonomyGrantSet().model_dump_json())
    with pytest.raises(RuntimeReinjectionError, match="invalid"):
        verify_runtime_reinjection(contract, checkout)


def test_runtime_reinjection_rejects_provider_scope_drift_and_invalid_flags(
    tmp_path: Path,
) -> None:
    checkout = _basic_checkout(tmp_path)
    env_path = checkout / ".env"
    contract, _ = capture_runtime_reinjection_contract(checkout)

    env_path.write_text(env_path.read_text() + "AICO_ENABLE_CODEX_ADAPTER=true\n")
    with pytest.raises(RuntimeReinjectionError, match="does not match"):
        verify_runtime_reinjection(contract, checkout)

    env_path.write_text(
        env_path.read_text().replace(
            "AICO_ENABLE_CODEX_ADAPTER=true", "AICO_ENABLE_CODEX_ADAPTER=maybe"
        )
    )
    with pytest.raises(RuntimeReinjectionError, match="flag"):
        verify_runtime_reinjection(contract, checkout)


def _basic_checkout(tmp_path: Path) -> Path:
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    (checkout / ".gitignore").write_text(".env\n.aico/\n")
    _git(checkout, "init", "-q")
    _git(checkout, "add", ".gitignore")
    _git(
        checkout,
        "-c",
        "user.name=AICO Test",
        "-c",
        "user.email=aico@example.invalid",
        "commit",
        "-q",
        "-m",
        "runtime recovery test",
    )
    _write_env(
        checkout,
        channel="telegram",
        secret_lines=("AICO_TELEGRAM_BOT_TOKEN=first-private-runtime-token",),
    )
    return checkout


def _write_env(
    checkout: Path,
    *,
    channel: str,
    secret_lines: tuple[str, ...],
    extra_lines: tuple[str, ...] = (),
) -> None:
    default_project = checkout / "config/projects.json"
    lines = (
        f"AICO_CHANNEL={channel}",
        *secret_lines,
        f"AICO_CLAUDE_WORKING_DIRECTORY={checkout}",
        f"AICO_PROJECT_CONFIG_PATH={default_project}",
        "AICO_STATE_DB_PATH=.aico/state.db",
        "AICO_AUDIT_LOG_PATH=.aico/audit.jsonl",
        "AICO_MEMORY_PATH=.aico/memory.jsonl",
        "AICO_OWNER_SENDER_IDS=owner-test",
        "AICO_TRUSTED_TARGET_IDS=chat-test",
        *extra_lines,
    )
    env_path = checkout / ".env"
    env_path.write_text("\n".join(lines) + "\n")
    env_path.chmod(0o600)


def _standing_project(managed: Path) -> dict[str, object]:
    return {
        "agents": {
            "codex": {
                "id": "codex",
                "provider": "codex",
                "title": "Independent Reviewer",
            }
        },
        "roles": {"reviewer": {"id": "reviewer", "title": "Independent Reviewer"}},
        "projects": {
            "aico": {
                "id": "aico",
                "name": "AI Company OS",
                "repo": str(managed),
                "default_assignment": "aico-reviewer",
                "standing_charter": [
                    {
                        "id": "absence-loop",
                        "objective": "Inspect current recovery evidence.",
                        "role": "reviewer",
                        "acceptance_evidence": ["one bounded report"],
                        "stop_conditions": ["stop before external communication"],
                    }
                ],
            }
        },
        "assignments": [
            {
                "project": "aico",
                "agent": "codex",
                "role": "reviewer",
                "seat": "aico-reviewer",
            }
        ],
    }


def _git(checkout: Path, *args: str) -> None:
    subprocess.run(("git", *args), cwd=checkout, check=True, capture_output=True)
