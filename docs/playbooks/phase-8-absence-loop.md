# Playbook: Phase 8 Absence Loop

## 适用场景

当 Phase 8 的 inbox、morning handoff、outcome grading、Dream cycle、runbook memory 或 hybrid retrieval 变化时,用本 Playbook 防止实现跑偏。

核心验收不是“功能存在”,而是老板不在电脑前时能否形成闭环:

```text
下任务 -> 执行 -> 审批/叫停 -> 验收 -> 早上接手 -> 经验沉淀 -> 下次召回
```

## Sprint 队列

### Sprint 1: Actionable Inbox

目标:`/inbox` 是老板回来后的第一处理入口,不是纯状态列表。

直接可问:

```text
/project aico
/inbox
```

验收:

- 待审批项必须显示 `/approve <id>` 和 `/reject <id>`。
- running 项必须显示 `/task <id>` 和 `/interrupt <id>`。
- failed / interrupted / rejected 项必须显示 `/task <id>` 和恢复建议。
- `/overnight` 工单必须显示对应 `/task <id>`、`/daily <project>`。
- Goal Brief / lead decision 必须显示 follow-up 命令。
- 协作 follow-up 必须能跳到 child task。
- 输出只包含 current active project,不能串其它 project。

### Sprint 2: Morning Handoff

目标:老板早上不用主动翻 `/tasks`,系统能汇总 done、blocked、risks、next actions 和 approvals。

直接可问:

```text
/project aico
/morning
/inbox
```

验收:

- `/morning` 必须按 current active project 汇总 done、blocked、risks、overnight handoffs 和 next actions。
- blocked / risks 必须带回可执行命令,例如 `/approve <id>`、`/reject <id>`、`/task <id>`、`/interrupt <id>`。
- 输出末尾必须能回到 `/inbox` 和 `/dream`。
- 后续如果引入定时推送,必须仍可手动触发同一报告。

### Sprint 3: Outcome Grader

目标:Goal Brief 的 done 必须有 reviewer/tester/rubric 验收,不能只靠执行 agent 自报。

直接可问:

```text
/project aico
/goal implementer inspect inbox handoff 验收: list actionable items; explain blocked risks
/task <task_id>
/inbox
```

验收:

- goal task 有 acceptance。
- 执行完成后自动找 tester / reviewer 生成 `AICO Outcome Grader` 任务。
- reviewer/tester 验收结果必须给出 verdict / evidence / gaps / boss_next_action。
- outcome grader 任务进入 `/task` 和 `/inbox` 的 goal follow-up。
- 任何需要写文件或 shell 的修复仍走 `/approve`。

### Sprint 4: Dream and Runbook Memory

目标:老板不在时,agent 能整理经验、候选记忆、矛盾和过期项,但不自动污染 active memory。

直接可问:

```text
/project aico
/dream
/inbox
```

验收:

- Dream 输出是 reviewable candidates。
- raw audit/task/memory episodes 保留为 evidence。
- 第一切片至少能从 waiting approval / running / failed / interrupted / rejected 任务生成 runbook candidate。
- 批准前不进入 active prompt memory;当前实现写入 `candidate` 状态,不会被默认 `MemoryGovernor` 注入。
- 如果认可候选经验,由老板用 `/remember <accepted lesson>` 明确晋升为 active memory。

### Sprint 5: Hybrid Retrieval

目标:提升召回质量,但不改变治理边界。

验收:

- MemoryStore / MemoryRetriever / MemoryGovernor 边界不被绕过。
- scope、purpose、sensitivity、confidence 仍生效。
- `/recall` 仍能解释 reason / score,并受 MemoryGovernor 过滤。
- 没有 embedding provider 时使用本地 hybrid scorer:exact phrase > phrase overlap > semantic alias fallback。

直接可问:

```text
/project aico
/remember Morning handoff must show done, blocked, risks, and next actions.
/recall 早报接手
```

验收:

- 记忆能被中英文复述召回。
- reason / score 仍可见。

## 执行护栏

- 每轮只做一个 sprint。
- 每轮必须更新 `STATUS.md` 和 `docs/journal/ROUNDS.md`。
- 没有真实 IM 验收脚本,不得标完成。
- Dream 只能写 candidate / reviewable diff。
- Grader 不能绕过审批。
- 自动继续执行必须可 `/interrupt` 且进 `/inbox`。
- P4 retrieval 只允许替换 scorer / index,不能改治理策略。

## 回归命令

```bash
uv run pytest tests/unit/test_orchestrator.py tests/unit/test_commands.py tests/unit/test_memory.py
uv run ruff check .
uv run ruff format --check .
uv run mypy src tests
git diff --check
```

## 相关

- ADR-0029
- `NORTH_STAR.md`
- `docs/playbooks/phase-8-offline-delegation.md`
- `src/aico/core/inbox.py`
