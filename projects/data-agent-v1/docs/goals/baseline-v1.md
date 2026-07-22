# Goal Brief: Data-Agent V1 Baseline

## Objective

Build a local enterprise data-agent benchmark product that AICO can use as its
first baseline proof of multi-agent product delivery.

## In Scope

- Runnable local CLI.
- Enterprise sample CSV data.
- Explicit semantic layer.
- Deterministic question answering for common business questions.
- 20 golden eval questions.
- Tests and README.
- AICO project-office configuration.
- Benchmark evidence templates.

## Out Of Scope

- Real customer data.
- Cloud deployment.
- Self-serve Web UI.
- LLM provider calls.
- External upload, payment, publication, or account actions.

## Acceptance Checks

- A new user can run the CLI from `README.md`.
- Three manual business questions return evidence and SQL-like calculations.
- 20 golden eval cases pass.
- Root AICO can load the project config.
- Human scorecard is ready for a real AICO baseline run.

## Stop Conditions

- A task needs real external credentials, customer data, payment, upload, or
  publication.
- The product cannot answer with deterministic evidence.
- The benchmark criteria need to change before v1 is scored.
