from aico.core.collaboration import (
    collaboration_payload,
    parse_collaboration_directive,
    split_collaboration_directive,
)


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


def test_parse_collaboration_directive_accepts_later_directive_line() -> None:
    directive = parse_collaboration_directive(
        "Plan:\n- implement inbox list\n@reviewer: review whether this violates approval boundaries"
    )

    assert directive is not None
    assert directive.target_persona == "reviewer"
    assert directive.payload == "review whether this violates approval boundaries"


def test_split_collaboration_directive_keeps_non_directive_text() -> None:
    directive, remaining = split_collaboration_directive(
        "Plan:\n"
        "- implement inbox list\n"
        "@reviewer: review whether this violates approval boundaries\n"
        "Done."
    )

    assert directive is not None
    assert directive.target_persona == "reviewer"
    assert directive.payload == "review whether this violates approval boundaries"
    assert remaining == "Plan:\n- implement inbox list\nDone."


def test_parse_collaboration_directive_ignores_plain_mentions() -> None:
    assert parse_collaboration_directive("Please ask @reviewer later") is None
    assert parse_collaboration_directive("@reviewer") is None


def test_collaboration_payload_preserves_source_persona() -> None:
    assert collaboration_payload("implementer", "review this") == (
        "Collaboration request from implementer:\n\nreview this"
    )


def test_collaboration_payload_can_include_source_context() -> None:
    assert collaboration_payload(
        "reviewer",
        "reflect (a)-(d) in the plan",
        source_context="Findings:\n(a) keep /inbox read-only\n(b) do not batch approvals",
    ) == (
        "Collaboration request from reviewer:\n\n"
        "Context from reviewer output so far:\n"
        "Findings:\n(a) keep /inbox read-only\n(b) do not batch approvals\n\n"
        "Current task:\n"
        "reflect (a)-(d) in the plan"
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
