# Human/AI Alignment Loop

The hard problem is not producing the first implementation. It is keeping humans, the AICO lead, specialist agents, code, and product evidence aligned over many rounds.

## The five durable artifacts

| Artifact | Purpose | Owner | Update trigger |
|---|---|---|---|
| `NORTH_STAR.md` | Stable product boundary | Human | Rare constitutional decision |
| `STATUS.md` | Current truth and next priority | Lead | End of every round |
| Active Goal Brief | Scope and acceptance contract | Lead + human | Before a work slice starts |
| Decision records | Why a durable choice was made | Architect/reviewer | Cross-module or costly decision |
| `docs/handoffs/current.md` | Fast resumable context | Implementer/lead | Every handoff |

Chat history is not a source of truth. Agents rebuild context from these artifacts and evidence.

## One sustainable iteration

1. **Frame** — Human states the outcome. Lead writes or tightens the Goal Brief.
2. **Challenge** — Challenger attacks assumptions, scope, evidence, and opportunity cost.
3. **Decide** — Lead records the chosen slice and rejected alternatives.
4. **Delegate** — Specialists receive role resources, acceptance checks, and permissions.
5. **Implement** — Small change, tests first where practical, no hidden scope expansion.
6. **Verify** — Tester runs deterministic gates; reviewer checks maintainability and evidence.
7. **Handoff** — Lead updates status, decisions, blockers, evidence, and the next first action.
8. **Human checkpoint** — Human only decides product trade-offs, risky actions, or ambiguous acceptance.

## Information compression layers

To stay fast without losing truth, information is compressed in layers:

- **L0 evidence**: code, test output, traces, source documents. Never rewritten.
- **L1 task handoff**: what changed, evidence, risk, remaining work.
- **L2 round summary**: decisions and state changes in `ROUNDS.md`.
- **L3 current state**: only present truth and next priority in `STATUS.md`.
- **L4 reusable memory**: stable facts or promoted experience, always linked to evidence.

Compression must preserve identifiers and evidence links. A summary that cannot point back to L0 is commentary, not project memory.

## Human attention budget

The lead should ask the human only when:

- two product outcomes are both reasonable but materially different;
- an irreversible or externally visible action is required;
- credentials, payment, production data, or destructive operations are involved;
- acceptance depends on subjective business usefulness.

Routine code structure, tests, documentation synchronization, and reversible implementation choices belong to the team.

## Writer and semantic-approval policy

- One bounded slice has exactly one active writer. Parallel agents may research, test, or review, but must not edit overlapping files.
- The Lead coordinates delivery; it does not approve enterprise meaning on behalf of the business.
- Metric formulas, dimension definitions, entity identity, and authoritative sources require a named human business/data steward.
- Tester and Reviewer must be independent from the active writer for completion evidence.
- If parallel write work becomes necessary, assign disjoint modules or separate worktrees before execution.

## Daily AICO rhythm

```text
/use project sme-agent
/inbox
/ask lead <outcome or decision>
/approve or /reject only when required
/overnight <bounded goal with acceptance evidence>
/morning
/task <id> or /view for evidence
```

The next day starts from `/morning`, `STATUS.md`, and `docs/handoffs/current.md`, not from reconstructing yesterday's chat.

## Completion contract

A slice is done only when all are true:

- acceptance checks pass;
- the reviewer found no unresolved correctness or maintainability issue;
- evidence is recorded in the current handoff;
- status and next action are current;
- new uncertainty is either resolved or registered as a blocker.
