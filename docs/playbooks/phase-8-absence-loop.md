# Playbook: Phase 8 Absence Loop

## 适用场景

当 Phase 8 的 inbox、morning handoff、outcome grading、Dream cycle、runbook memory 或 hybrid retrieval 变化时,用本 Playbook 防止实现跑偏。

核心验收不是“功能存在”,而是老板不在电脑前时能否形成闭环:

```text
下任务 -> 执行 -> 审批/叫停 -> 验收 -> 早上接手 -> 经验沉淀 -> 下次召回
```

## AI 前置 Contract Gate

在要求人类做真实 IM / 手机 dogfood 前,Agent 必须先跑确定性 contract gate。它覆盖机器能稳定判断的部分。
如果当前 Mac 能打开 Telegram App、访问真实 provider 或读取 AICO 日志,Agent 还必须先跑本机真实样本。
human sample 只保留体感判断:老板是否看得顺、是否方便接手、是否信任这个交接。

### 当前 Phase 8 gate

```bash
env -u AICO_VIEW_TOKEN -u AICO_VIEW_ENABLED uv run pytest \
  tests/unit/test_collaboration.py \
  tests/unit/test_risk.py \
  tests/unit/test_task_bus.py::test_task_bus_keeps_collaboration_context_from_escalating_read_only_request \
  tests/unit/test_orchestrator.py::test_orchestrator_does_not_reject_read_only_reviewer_for_risky_parent_context \
  tests/unit/test_orchestrator.py::test_orchestrator_queues_overnight_delegation_to_project_lead \
  tests/unit/test_orchestrator.py::test_orchestrator_marks_short_overnight_handoff_failed \
  tests/unit/test_orchestrator.py::test_orchestrator_splits_long_stream_output_across_messages \
  tests/unit/test_offline_delegation.py \
  tests/unit/test_native_output.py \
  tests/unit/test_streaming.py \
  tests/unit/test_commands.py::test_parse_command_accepts_aico_view_alias \
  tests/unit/test_view_snapshot_commands.py \
  tests/unit/test_telegram_channel.py::test_telegram_channel_sends_document_as_multipart_upload \
  tests/unit/test_telegram_channel.py::test_telegram_channel_default_client_allows_long_poll_timeout \
  -q
```

### 覆盖范围

| Contract | 机器 gate 覆盖 | Agent 本机真实样本 | 仍需 human sample |
|---|---|---|---|
| 父子 agent 委派 | `@reviewer` 解析、父输出上下文、`Current task:` 边界、只读 reviewer 不被 risky parent context 误判为 `shell_exec` | 用真实 Telegram 发短 `/ask implementer ... @reviewer:` 样本;确认日志出现 `source=implementer target=reviewer`,parent/child task 均 done | 协作交接是否像老板能理解的工作交接,而不只是技术上触发 |
| `/overnight` handoff | active project / lead 派发、短输出失败、done/blocked/risks/next actions 合同、等待审批不误判失败 | 用 1 条短目标或历史 task 验证真实 provider 回包包含 done/blocked/risks/next actions,并能在 Telegram 读到 | 真实长任务结束后老板能否直接从手机接手 |
| delegate 输出可读性 | heading / severity bullet 归一化、1400 字移动端分片、分片边界不硬切 | 截取本机 Telegram App 窗口;确认长输出被拆成多条消息且没有明显粘连 | 手机上是否仍像长墙,是否需要 summary + trace 双层输出 |
| 老板查看动线 | `/inbox`、`/morning`、`/task`、`/view` / `/aico-view` 命令和回执合同 | Agent 发送 `/project aico`、`/inbox` 或 `/view`,用日志和 Telegram 回包确认命令实际生效 | 老板是否不用猜就知道现在看哪里、早上看哪里、深挖看哪里 |
| `/view` HTML snapshot | handler 注入、自包含 HTML、Telegram `sendDocument` multipart 上传、不发 localhost 链接 | Agent 发送 `/view`,确认 Telegram `sendDocument`、附件文件名、无 localhost 链接,并尽量打开附件检查首屏 | 手机端是否能打开附件,HTML 第一屏是否符合接手习惯,内容是否只发到可信聊天 |

### Agent 本机真实样本

- 不要把本机可验证事项交给人类。Mac 上有 Telegram App 时,Agent 先打开 bot 聊天、发送样本、看日志和截图。
- 父子协作最小样本:
  `/ask implementer Please output a short handoff, then on its own line @reviewer: Review this handoff in 3 bullets max.`
- 通过标准:
  - Telegram 日志出现 incoming text 和 parent task accepted。
  - parent task 是 `target=implementer` 且真实 adapter 接收。
  - 日志出现 `Collaboration directive: ... source=implementer target=reviewer`。
  - child task 是 `target=reviewer`,真实 adapter 接收并最终 done。
  - Telegram App 可见 `Collaboration requested`、reviewer accepted 和 reviewer 输出。
- 如果样本走到 lead decision / challenger 等非预期路由,不算 implementer -> reviewer 验收通过;换一个不含 decision 触发词的样本重跑。

### Human sample 只看什么

- 只跑 1 条代表性真实 IM 样本,除非 gate 或 Agent 本机真实样本失败。
- Agent 请求人类前必须给出:已验证结果、推荐重点验证点、验证问题、预期效果、后续步骤。
- 记录 `/task <id>`、截图/原始输出、预期效果和实际偏差。
- 如果新偏差能机器化,下一轮先把它补进 gate,再让人类复验。

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
- `/overnight` 工单必须显示对应 `/task <id>` 和 `/morning` 接手入口。
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
