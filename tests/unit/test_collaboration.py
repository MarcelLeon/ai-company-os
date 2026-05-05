from aico.core.collaboration import collaboration_payload, parse_collaboration_directive


def test_parse_collaboration_directive_accepts_persona_mention() -> None:
    directive = parse_collaboration_directive("@reviewer: inspect the proposed patch")

    assert directive is not None
    assert directive.target_persona == "reviewer"
    assert directive.payload == "inspect the proposed patch"


def test_parse_collaboration_directive_accepts_space_after_persona() -> None:
    directive = parse_collaboration_directive("@reviewer review一下phase 5有什么风险")

    assert directive is not None
    assert directive.target_persona == "reviewer"
    assert directive.payload == "review一下phase 5有什么风险"


def test_parse_collaboration_directive_ignores_plain_mentions() -> None:
    assert parse_collaboration_directive("Please ask @reviewer later") is None
    assert parse_collaboration_directive("@reviewer") is None


def test_collaboration_payload_preserves_source_persona() -> None:
    assert collaboration_payload("implementer", "review this") == (
        "Collaboration request from implementer:\n\nreview this"
    )
