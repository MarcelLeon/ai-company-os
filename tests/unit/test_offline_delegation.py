from aico.core import offline_delegation_completion_issue


def test_offline_delegation_completion_issue_rejects_too_short_handoff() -> None:
    issue = offline_delegation_completion_issue(
        "Community 文件：写一个简短 Code of Conduct（基于 Contributor Covenant 2.1）："
    )

    assert issue == "handoff output is too short for an overnight delegation"


def test_offline_delegation_completion_issue_accepts_complete_handoff() -> None:
    issue = offline_delegation_completion_issue(
        "done:\n"
        "• reviewed GitHub launch readiness and drafted the community file checklist.\n"
        "blocked:\n"
        "• no blocker in the current local state; public push still needs boss confirmation.\n"
        "risks:\n"
        "• unclear positioning could weaken the first-star conversion story.\n"
        "next actions:\n"
        "• finalize README\n"
        "• add community files\n"
        "• run tests\n"
    )

    assert issue is None
