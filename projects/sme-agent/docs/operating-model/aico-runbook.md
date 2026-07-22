# AICO Project Runbook

Run from the AI Company OS repository root.

## Start the durable project office

```bash
export AICO_TELEGRAM_BOT_TOKEN="<token>"
export AICO_ENABLE_CODEX_ADAPTER=true
export AICO_CLAUDE_WORKING_DIRECTORY="/Users/wangzq/VsCodeProjects/ai-company-os"
export AICO_PROJECT_CONFIG_PATH="projects/sme-agent/aico-project.json"
export AICO_MEMORY_PATH=".aico/sme-agent-memory.jsonl"
export AICO_AUDIT_LOG_PATH=".aico/sme-agent-audit.jsonl"
export AICO_STATE_DB_PATH=".aico/sme-agent-state.db"
uv run aico-phase1
```

The AICO process stays open. Stop it with `Ctrl-C`; use `/interrupt <task_id>` for an individual task.

## First project-office check

```text
/use project sme-agent
/team
/brief
/ask challenger review docs/goals/phase-1-metadata.md; identify scope and evidence gaps only.
/ask lead incorporate valid objections and return the final Phase 1 decision memo.
```

## Ongoing rhythm

```text
/inbox
/proposals
/ask lead <bounded outcome>
/approve                     # only when a risky task is expected
/overnight <goal + acceptance evidence + stop condition>
/morning
/task <short_id>
/view
```

The SME project config includes one `commercial-evidence-loop` standing charter. When the project is idle and the required team is appointed, `/inbox`, `/morning`, or scheduled morning push may surface one candidate. Viewing it does not run work. Use `/proposal accept <short_id>` to route it through the normal lead/task/risk/approval chain, or `/proposal reject <short_id> [reason]` to record the decision and cooldown. The charter explicitly stops before external messages/publication, real merchant data/payment, or accepting the 199 RMB offer for the owner.

At the end of every slice, the lead must ensure these files agree:

- `STATUS.md`
- `docs/goals/phase-1-metadata.md` or the active successor Goal Brief
- `docs/handoffs/current.md`
- `docs/journal/ROUNDS.md`
- tests or other L0 evidence referenced by the handoff

## Recovery the next day

1. Run `/morning` and `/inbox`.
2. Read `STATUS.md` and `docs/handoffs/current.md`.
3. Use `/task` or `/view` for evidence; do not reconstruct decisions from memory.
4. If artifacts disagree, stop implementation and ask the lead to reconcile them first.
