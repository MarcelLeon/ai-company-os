from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from data_agent_v1.engine import DataAgentEngine

DEFAULT_EVAL_PATH = Path(__file__).resolve().parents[2] / "evals" / "golden_questions.json"


@dataclass(frozen=True)
class EvalResult:
    total: int
    passed: int
    failures: tuple[str, ...]

    @property
    def pass_rate(self) -> float:
        return self.passed / self.total if self.total else 0.0


def run_golden_eval(path: Path = DEFAULT_EVAL_PATH) -> EvalResult:
    cases = json.loads(path.read_text(encoding="utf-8"))
    engine = DataAgentEngine()
    failures: list[str] = []
    for case in cases:
        response = engine.answer(str(case["question"]))
        if response.intent != case["expected_intent"]:
            failures.append(
                f"{case['id']}: expected intent {case['expected_intent']}, got {response.intent}"
            )
            continue
        expected_facts = case.get("expected_facts", {})
        for key, expected_value in expected_facts.items():
            actual = response.facts.get(str(key))
            if actual != str(expected_value):
                failures.append(f"{case['id']}: expected {key}={expected_value}, got {actual}")
    return EvalResult(total=len(cases), passed=len(cases) - len(failures), failures=tuple(failures))


def main() -> None:
    result = run_golden_eval()
    print(f"golden_eval: {result.passed}/{result.total} passed")
    for failure in result.failures:
        print(f"- {failure}")
    raise SystemExit(0 if not result.failures else 1)


if __name__ == "__main__":
    main()
