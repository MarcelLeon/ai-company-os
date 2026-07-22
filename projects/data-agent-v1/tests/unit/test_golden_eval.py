from __future__ import annotations

from data_agent_v1.eval_runner import run_golden_eval


def test_golden_eval_passes_all_cases() -> None:
    result = run_golden_eval()

    assert result.total == 20
    assert result.passed == 20
    assert result.failures == ()
