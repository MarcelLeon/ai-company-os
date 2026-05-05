import pytest

from aico.core.project_assignment import ProjectProfile
from aico.core.role_proposal import role_from_llm_output, role_proposal_prompt


def test_role_proposal_prompt_requests_json_for_project_need() -> None:
    project = ProjectProfile(id="aico", name="AI Company OS", repo="/repo")

    prompt = role_proposal_prompt(project, "需要一个增长分析岗位")

    assert "Project: aico [AI Company OS]" in prompt
    assert "Need: 需要一个增长分析岗位" in prompt
    assert "Return only one JSON object" in prompt


def test_role_from_llm_output_parses_json_role_draft() -> None:
    role = role_from_llm_output(
        """
        {
          "id": "Growth Analyst",
          "title": "Growth Analyst",
          "summary": "Analyze activation and retention opportunities.",
          "default_permissions": ["read_docs", "read_audit"],
          "approval_required": ["write_docs"],
          "inline_prompt": "Focus on measurable product opportunities."
        }
        """,
        "增长分析",
    )

    assert role.id == "growth-analyst"
    assert role.title == "Growth Analyst"
    assert role.default_permissions == ("read_docs", "read_audit")
    assert role.approval_required == ("write_docs",)
    assert role.inline_prompt == "Focus on measurable product opportunities."


def test_role_from_llm_output_rejects_missing_json() -> None:
    with pytest.raises(ValueError, match="JSON object"):
        role_from_llm_output("not json", "增长分析")
