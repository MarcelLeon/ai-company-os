# Baseline V1 Evidence

## Machine Evidence

```bash
PYTHONPATH=projects/data-agent-v1/src uv run pytest projects/data-agent-v1/tests tests/unit/test_data_agent_project.py -q
uv run ruff check projects/data-agent-v1/src projects/data-agent-v1/tests tests/unit/test_data_agent_project.py
uv run mypy --config-file projects/data-agent-v1/pyproject.toml projects/data-agent-v1/src projects/data-agent-v1/tests
```

Result on 2026-06-28:

```text
7 passed in 0.14s
All checks passed!
Success: no issues found in 10 source files
```

Full root pytest after adding the benchmark test path:

```text
478 passed, 1 skipped in 0.95s
```

## AICO Evidence

Record `/project`, `/team`, `/goal`, `/ask challenger`, `/overnight`,
`/morning`, `/inbox`, `/task`, and `/view` evidence after the real baseline run.

## Human Evidence

Record the final scorecard path and the top three AICO UX problems found.
