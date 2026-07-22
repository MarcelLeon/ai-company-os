from __future__ import annotations

import logging

import pytest

from aico.core.ingress_authorization import (
    AllowAllIngressAuthorizer,
    IngressGuard,
    OwnerBoundIngressAuthorizer,
)
from aico.core.models import ChannelTarget, IncomingMessage, MessageContent


def test_owner_bound_ingress_requires_exact_channel_sender_and_target() -> None:
    authorizer = OwnerBoundIngressAuthorizer(
        channel_name="telegram",
        owner_sender_ids=("owner-1", "owner-2"),
        trusted_target_ids=("chat-1", "chat-2"),
    )

    assert authorizer.allows(_message(sender_id="owner-1", target_id="chat-2"))
    assert not authorizer.allows(_message(sender_id="stranger", target_id="chat-2"))
    assert not authorizer.allows(_message(sender_id="owner-1", target_id="public-chat"))
    assert not authorizer.allows(
        _message(
            channel_name="feishu",
            sender_id="owner-1",
            target_id="chat-2",
        )
    )


def test_owner_bound_ingress_fails_closed_when_identity_sets_are_empty() -> None:
    authorizer = OwnerBoundIngressAuthorizer(
        channel_name="telegram",
        owner_sender_ids=(),
        trusted_target_ids=(),
    )

    assert not authorizer.allows(_message())
    assert AllowAllIngressAuthorizer().allows(_message())


def test_ingress_guard_rate_limits_identity_safe_denial_logs(
    caplog: pytest.LogCaptureFixture,
) -> None:
    guard = IngressGuard(
        OwnerBoundIngressAuthorizer(
            channel_name="telegram",
            owner_sender_ids=("owner-1",),
            trusted_target_ids=("chat-1",),
        )
    )
    caplog.set_level(logging.WARNING, logger="aico.core.ingress_authorization")

    for _ in range(5):
        assert not guard.accepts(_message(sender_id="private-stranger"))

    messages = [record.getMessage() for record in caplog.records]
    assert messages == [
        "Unauthorized IM ingress dropped: total=1",
        "Unauthorized IM ingress dropped: total=2",
        "Unauthorized IM ingress dropped: total=4",
    ]
    assert "private-stranger" not in str(caplog.records)
    assert "please inspect" not in str(caplog.records)


def test_ingress_guard_reveals_identity_only_in_explicit_discovery_mode(
    caplog: pytest.LogCaptureFixture,
) -> None:
    guard = IngressGuard(
        OwnerBoundIngressAuthorizer(
            channel_name="telegram",
            owner_sender_ids=(),
            trusted_target_ids=(),
        ),
        reveal_denied_identity=True,
    )
    caplog.set_level(logging.WARNING, logger="aico.core.ingress_authorization")

    assert not guard.accepts(_message(sender_id="owner-bootstrap", target_id="chat-bootstrap"))

    message = caplog.records[0].getMessage()
    assert "sender='owner-bootstrap'" in message
    assert "target='chat-bootstrap'" in message
    assert "please inspect" not in message


def _message(
    *,
    channel_name: str = "telegram",
    sender_id: str = "owner-1",
    target_id: str = "chat-1",
) -> IncomingMessage:
    return IncomingMessage(
        channel_name=channel_name,
        source=ChannelTarget(channel_name=channel_name, target_id=target_id),
        sender_id=sender_id,
        content=MessageContent(text="please inspect"),
        raw_ref="message-1",
    )
