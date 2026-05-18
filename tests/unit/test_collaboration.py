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


def test_collaboration_payload_can_use_memory_refs_when_enabled() -> None:
    assert collaboration_payload(
        "implementer",
        "focus on broadcast policy",
        memory_refs=("mem-aico", "mem-team"),
        use_memory_refs=True,
    ) == (
        "Collaboration request from implementer:\n\n"
        "Memory refs: mem-aico, mem-team\n"
        "Delta:\n"
        "focus on broadcast policy"
    )


def test_collaboration_payload_falls_back_to_explicit_payload_without_refs() -> None:
    assert (
        collaboration_payload(
            "implementer",
            "full context remains explicit",
            use_memory_refs=True,
        )
        == "Collaboration request from implementer:\n\nfull context remains explicit"
    )
