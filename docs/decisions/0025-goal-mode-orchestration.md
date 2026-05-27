# ADR-0025: Goal Mode Orchestration

**状态**:Accepted
**日期**:2026-05-21
**决策者**:Codex
**相关 Round**:Round 100 / Round 101 / Round 105

---

## 背景与问题

Codex CLI 的实验 `/goal` 命令把一个持久目标挂到当前线程,适合有明确停止条件和验证循环的长任务。Claude Code 也可以通过 slash command / project command / hook 机制封装 goal-like 工作流。AICO 现有 `/ask` 是单次派活,`/lead` 是默认牵头角色,`/overnight` 是离线托管工单。它们还缺一个更通用的“目标契约”层:当 boss 给 agent、或 lead 给其他 agent 分配复杂任务时,如果目标和验收结果清晰,系统应让 agent 持续按目标推进、阶段性验证、可暂停/恢复/清除,并把状态暴露给 IM 和 audit。

不同 agent 的现状不一致:

- Codex / Claude Code 等 agent 可以支持原生或适配器级 goal 语法糖。
- CodeFlicker / Trae / Gemini 等 agent 可能只支持普通 prompt / CLI task。
- AICO 不能把所有 agent 都强行塞进同一种 loop;应该先表达统一 `GoalContract`,再按 agent capability 选择 native goal 或 AICO-managed Ralph loop。

本地 Codex CLI 版本为 `0.125.0`,尚不包含 `/goal`;本 ADR 参考的是 OpenAI Developers 当前文档中对 `/goal` 的公开说明,不是本机源码逆向结论。实际运行时必须由 Adapter capability 探测决定,不能硬编码“某 agent 永远支持 goal”。

## 候选方案

### 方案 A — 只复用 `/overnight`

- 优点:已存在 project lead、approval、audit、daily handoff。
- 缺点:`/overnight` 是“睡前下任务,早上看结果”的离线语义,不适合白天普通复杂任务、lead 派生子目标、暂停/恢复/清除。
- 复杂度:低。

### 方案 B — 在 `/ask` 内部隐式循环直到完成

- 优点:老板不用学习新命令。
- 缺点:长任务状态不显式,无法区分一次性咨询和目标托管,也缺少可查看、暂停、恢复、清除的控制面。
- 复杂度:中。

### 方案 C — 新增 capability-aware goal 目标契约层

- 优点:保留 `/ask` 的自然入口,同时为复杂且可验证任务建立持久目标、状态机、验收证据和父子目标关系;支持 native goal agent,也支持普通 agent 的 AICO-managed Ralph loop。
- 缺点:需要新增 GoalRecord、状态恢复、render、audit、A2A 子目标跟踪、Adapter goal capability 探测和 loop hook。
- 复杂度:中高。

### 方案 D — 先做轻量 Goal Brief v0

- 优点:先把 `/goal` 和可验证 `/ask` 变成明确的目标/验收 prompt,并把目标元数据挂到 Task / `/task` 上;不引入持久 GoalRecord、pause/resume/clear 或 managed continuation loop。
- 缺点:不具备真正长期托管、重启恢复、父子目标聚合和 hook 驱动续跑。
- 复杂度:低。

## 决策

选择 **方案 D 作为当前实现切片**,保留 **方案 C 作为后续扩展方向**。

原因:对个人开发用户和开源市场来说,最需要先验证的是“老板能否少写 prompt,agent 能否按验收条件收口”。完整 GoalCapability / GoalExecutor / managed Ralph loop 工程量更高,且效果需要真实 dogfooding 证明。当前先实现轻量 Goal Brief v0,把价值验证前置,避免过早承担长期 loop 的状态机和恢复成本。

## 设计原则

- `/goal` 不是“更强的 `/ask`”,而是一个有验收标准的目标契约。
- AICO 的统一层是 `GoalContract`,不是统一的执行 loop。执行由 `GoalExecutor` 根据 agent capability 决定。
- 目标必须有一个 owner: boss 分配时 owner 是目标 role;lead 分配时 owner 是子目标 role,lead 仍对父目标负责。
- 高风险动作继续走 Phase 4 `/approve`;goal-mode 不提供无人授权。
- 所有状态变化写 audit:created、checkpoint、paused、resumed、achieved、unmet、cleared、budget_limited。
- 目标状态应能从 `/goal`、`/tasks`、`/task <id>` 和 `/daily` 看见。

## 当前实现切片:Goal Brief v0

Goal Brief v0 是“目标契约提示 + 任务元数据”,不是完整长期 goal runtime。

已接受范围:

- `/goal [role] <objective>`:为当前 active project 的指定 role 创建可验证目标任务;未指定 role 时使用当前 project lead/default role。
- `/goal`:从最近 task snapshots 中列出带 goal brief 元数据的任务。
- `/ask <role> <task>`:仅当文本里出现明确验收/停止/证据 marker 时,保守附加 goal brief;普通咨询仍走普通 `/ask`。
- Adapter payload 注入 `AICO Goal Brief`,包含 `goal_id`、objective、acceptance criteria、verification hints、stop conditions 和“未有证据不得 claim done”的规则。
- Task metadata 写入 `aico.intent=goal_brief`、`aico.goal_id`、`aico.goal_objective`、`aico.goal_acceptance`;`/task <id>` 展示 Goal brief。

明确暂缓:

- `GoalCapability` / `GoalExecutor` runtime 分发。
- native `/goal` 语法糖实际调用。
- AICO-managed Ralph loop、GoalHook、continuation task。
- GoalRecord 持久化、pause/resume/clear、父子 goal 聚合。
- 重启后独立 goal 状态恢复。

## Agent Capability Model

每个 Adapter 暴露 `GoalCapability`,由配置和启动时探测共同决定。

| capability | 适用 agent | AICO 行为 |
|---|---|---|
| `native_goal` | Codex 新版 `/goal`;Claude Code 如果本地支持内置 goal | AICO 生成目标契约,再渲染为 agent 原生命令;AICO 只做外层状态、审计、暂停/恢复映射和结果归档 |
| `adapter_goal_sugar` | Claude Code custom slash command / project command;Codex feature flag 包装 | AICO 通过 Adapter 提供的命令模板封装 goal 语法糖,仍由 agent 内部持续推进 |
| `managed_ralph_loop` | CodeFlicker / Trae / Gemini / 只支持普通 prompt 的 CLI | AICO 自己维护 loop:发起 goal turn、解析 hook 结果、必要时继续投递 continuation task |
| `no_goal` | read-only 或不可靠 agent | 不接受 `/goal`,降级为普通 `/ask` 或提示换 agent |

能力判断顺序:

1. Adapter 显式配置优先,例如 `goal_mode=native_goal`。
2. 启动时轻量探测,例如 `codex` feature flag / help 文案、Claude Code project command 是否存在。
3. 未确认时默认 `managed_ralph_loop`,但只对已允许长任务的 agent 启用。
4. 如果 agent 只有 read-only 能力且目标需要 write/run,仍走 `/approve` 或拒绝。

## GoalExecutor 分层

### Native / Adapter Goal

对支持 goal 的 agent,AICO 不重复造 Ralph loop。它只做语法糖封装:

```text
{agent_goal_command}

Objective:
{objective}

Done when:
{acceptance_criteria}

Stop when:
{stop_conditions}

Report:
- status: achieved | unmet | blocked_waiting_approval | budget_limited
- verification evidence
- changed files or artifacts
- remaining risks
```

示例:

```text
Codex executor:
/goal Fix Release Room v0.2 tag/search/export JSON.
Done when contract tests pass, README/CHANGELOG are synced, and unknown id done exits non-zero.
Stop if product semantics or credentials are missing.
```

Claude Code executor 可以选择内置 goal、项目 `.claude/commands/goal.md`,或 adapter 注入的 goal-like prompt。具体语法不能写死在 core,只能由 `ClaudeCodeAdapter.goal_syntax()` 返回。

### Managed Ralph Loop

对不支持 goal 的 agent,AICO 自己承担长期目标控制:

1. 创建 `GoalRecord` 和 parent task。
2. 发送第一轮 `Managed Ralph Loop Prompt`。
3. Adapter 输出进入 `GoalHook`。
4. `GoalHook` 解析结构化结果:
   - `achieved` / `unmet` / `blocked_waiting_approval` / `paused` / `budget_limited` -> 结束或暂停。
   - `continue` -> AICO 生成 continuation task,带上 evidence、剩余验收项、下一 checkpoint。
5. 每轮 continuation 都复用同一 `goal_id`,写 audit,并遵守 `/interrupt` 和 `/approve`。

Ralph loop 的关键不是“让模型无限干活”,而是用外部状态和 hook 防止模型过早把未验收任务说成完成。

硬边界:

- 必须有 `max_turns`、`max_wall_clock`、`max_tokens` 或人工 pause,避免失控。
- 每一轮必须产出 evidence 或 blocker;连续两轮没有新 evidence,进入 `needs_lead_triage`。
- 不能跨越 approval gate 自动继续。
- boss `/interrupt <task_id>` 或 `/goal pause <goal_id>` 必须能停止后续 continuation。

## 触发规则

显式触发:

```text
/goal <role> <objective>
/goal <objective>              # 使用当前 project lead/default role
/goal                           # 查看当前项目目标
```

`pause` / `resume` / `clear` 留给完整 GoalExecutor 阶段,不进入 v0。

隐式升级:

```text
/ask <role> <task>
```

当 `<task>` 同时满足以下条件时,系统可把它升级为 goal-mode:

- 需要多步执行或多轮验证,不是单次问答。
- 有可判断的完成状态,例如测试通过、文档同步、部署验证、报告产出。
- 有明确边界,例如涉及文件、模块、项目、非目标或停止条件。
- 缺少的信息不会影响第一步安全探索。

不升级:

- 纯咨询、头脑风暴、解释代码。
- 目标开放且验收模糊,例如“优化一下项目”。
- 需要人类先裁决产品方向。
- 包含高风险动作但没有审批上下文;此时仍可建 goal,但执行会停在 `/approve`。

## Boss 分配交互流程

### 显式 `/goal`

```text
Boss:
/goal implementer 修复 Release Room v0.2 的 tag/search/export JSON,验收:contract tests pass,README/CHANGELOG 同步,未知 id done 返回非 0。停止:需要产品口径或凭证时暂停。

AICO:
Goal queued. goal-24a1
project: release-room
owner: implementer -> codex
objective: 修复 Release Room v0.2 的 tag/search/export JSON
acceptance:
- contract tests pass
- README/CHANGELOG 同步
- 未知 id done 返回非 0
tracking: /task 24a1
```

v0 流程:

1. Router 解析 `/goal` 并解析 role;未指定 role 时使用当前 project lead/default role。
2. AICO 用轻量 parser 抽取 objective、acceptance、verification、stop conditions;缺少验收时使用保守默认验收:“必须给出具体证据才可 claim done”。
3. AICO 生成 `AICO Goal Brief` prompt,复用普通 project appointment prompt、shared memory、provider session 和 TaskBus。
4. AICO 在 Task metadata 上挂 goal brief 元数据,`/task <id>` 可追踪。
5. 危险动作仍按普通 TaskBus 风险门禁进入 `/approve`。

完整 GoalExecutor 阶段才会执行 capability 探测、native goal dispatch、managed Ralph loop 和持久 GoalRecord。

### `/ask` 自动升级

```text
Boss:
/ask tester 根据 v0.2 contract tests 设计并执行回归,必须给出通过/失败证据,如果测试入口不可用就停下说明。

AICO:
Verifiable task detected. Goal brief attached. goal-81f0
owner: tester -> claude-code
acceptance: regression evidence with pass/fail; stop if test entrypoint is unavailable
```

`/ask` 自动升级不额外打断老板,但必须在回执中明确“已按 goal-mode 托管”。如果分类置信度低,保持普通 `/ask`,不要为了自动化制造误解。

## Lead 分配交互流程

lead 不能把父目标甩给别人后失去责任。lead 分配的是“子目标”,系统需要保存 `parent_goal_id`,并针对每个子目标 owner agent 选择对应 executor。

```text
Boss:
/goal pm 推进 v0.2 release,验收:实现、测试、review、release notes 都完成,早报给 done/blocked/risks/next。

PM lead output:
@implementer /goal 实现 tags/search/export JSON 和 unknown id done 退出码修复。验收:contract tests pass;不得改 CLI 公共命令名。
@tester /goal 跑 v0.2 contract tests 并补充失败复现。验收:给出命令、结果、失败日志或通过证据。
@reviewer /goal review v0.2 改动。验收:列出 blockers、risks、missing tests;没有问题也要说明残余风险。

AICO:
Sub-goals created under g-parent:
- g-impl -> implementer
- g-test -> tester
- g-review -> reviewer
PM remains accountable for parent goal g-parent.
```

lead 子目标规则:

- 子目标必须有独立验收标准,否则只用普通 `@role: request`。
- 子目标不能扩大父目标范围;AICO 将 parent goal 的 non-goals 和 approval policy 注入子目标。
- 子目标完成后不直接对 boss 宣称父目标完成,而是回到 lead 汇总。
- 任一子目标 `unmet` 或 `blocked_waiting_approval` 时,parent goal 进入 `needs_lead_triage`。
- native goal 子目标和 managed loop 子目标可以混用;parent goal 只依赖统一 `GoalRecord` 状态,不依赖具体 agent 语法。

## Goal Contract 模板

```text
Goal contract:
- goal_id: {goal_id}
- parent_goal_id: {parent_goal_id_or_none}
- project: {project_id} [{project_name}]
- assigned_role: {role}
- assigned_agent: {agent}
- assigned_by: {boss_or_lead}
- objective: {objective}
- acceptance_criteria:
{acceptance_criteria}
- verification:
{verification_commands_or_artifacts}
- non_goals:
{non_goals}
- stop_conditions:
{stop_conditions}
- risk_policy: Follow AICO approval policy. Do not bypass /approve.
- context_refs:
{files_docs_tasks_memory_refs}
```

## Native Goal Dispatch 模板

```text
{native_or_adapter_goal_command}

Use this AICO goal contract exactly.
{goal_contract}

Do not stop until every acceptance criterion is verified or a stop condition is hit.
When finished, report using the AICO final report format.
```

## Managed Ralph Loop Prompt 模板

```text
You are operating under AICO managed goal loop.

{goal_contract}

Operating loop:
1. Read the required context first. If the goal contract is missing a critical acceptance criterion, pause and report the missing information.
2. State the first checkpoint in one short progress update.
3. Work one checkpoint at a time. After each checkpoint, record evidence: changed files, command output summary, artifact path, or reason it cannot be verified.
4. If a risky action is required, stop at approval and report exactly what approval is needed.
5. If you cannot finish in this turn, return status: continue, with next_checkpoint and remaining_acceptance.
6. Do not claim achieved until every acceptance criterion has evidence.
7. Do not broaden scope. Do not work on unrelated cleanup.

Final report format:
status: achieved | unmet | blocked_waiting_approval | budget_limited | continue
done:
- ...
verification:
- ...
changed_files:
- ...
blocked:
- ...
risks:
- ...
next:
- ...
next_checkpoint:
- ...
remaining_acceptance:
- ...
```

## Goal Hook 输出契约

`GoalHook` 从 agent 输出中解析最终块;解析失败时按 `continue` 处理一次,第二次失败进入 `needs_lead_triage`。

```json
{
  "goal_id": "g-24a1",
  "status": "achieved | unmet | blocked_waiting_approval | budget_limited | continue",
  "evidence": ["..."],
  "completed_acceptance": ["..."],
  "remaining_acceptance": ["..."],
  "next_checkpoint": "...",
  "blocked_reason": "...",
  "approval_request": "..."
}
```

## Goal 分类 Prompt 模板

```text
Classify whether this project request should run as AICO goal-mode.

Input:
- command: {command_name}
- role: {role_or_none}
- project: {project_id_or_none}
- text: {user_text}

Return JSON only:
{
  "mode": "goal" | "ask",
  "confidence": 0.0,
  "objective": "...",
  "acceptance_criteria": ["..."],
  "verification": ["..."],
  "non_goals": ["..."],
  "stop_conditions": ["..."],
  "missing_fields": ["..."],
  "reason": "..."
}

Use goal only when the request is multi-step and has a verifiable stopping condition.
Use ask for explanation, brainstorming, loose tasks, or ambiguous work.
If mode is goal but missing_fields contains critical acceptance information, ask one clarification before starting.
```

## 后果

### 正面后果

- `/goal` 先成为白天复杂任务的轻量验收契约层,低成本验证用户价值。
- boss 可以继续用 `/ask`,带明确验收的任务自动获得更强 prompt 约束和 `/task` 可见性。
- lead 可以拆子目标,但父目标责任链仍可追踪。
- 状态、验收和停止条件比普通 ReAct loop 更清楚。
- 后续仍可支持不同 agent 现状:有原生 goal 的 agent 走语法糖,没有的由 AICO 托管 Ralph loop。

### 负面后果

- v0 只有 Task metadata 和 recent snapshots,重启后没有独立 GoalRecord。
- 隐式升级如果做得激进,会让老板以为一次咨询被系统过度托管。
- 子目标编排会增加 task/metrics 展示复杂度。
- managed Ralph loop 需要严格预算和 hook 解析,否则会变成无限 continuation 或错误完成。
- native goal 语法会随 agent 版本变化,Adapter 需要 runtime capability 探测。

### 我们接受这些代价是因为

- AICO 的核心价值是远程异步管理 AI 团队,不是单次 prompt 转发。
- 目标契约能把“复杂任务”从聊天文本升级为可观测、可审批、可恢复的工作单元。
- AICO 作为编排层应该利用 agent 原生能力,但不能被任何单一 agent 的语法污染核心。

## 不再做的事

- 不把 `/goal` 设计成绕过审批的自动执行模式。
- 不让 lead 静默创建无验收标准的子目标。
- 不把所有 `/ask` 都升级为 goal;普通咨询仍保持轻量。
- 不在 core 中硬编码 `codex` 或 `claude` 的 goal 语法;所有语法糖都在 Adapter 内。
- 不为支持原生 goal 的 agent 再套一层 AICO-managed Ralph loop。
- 不在 v0 里实现 managed Ralph loop、pause/resume/clear 或重启恢复。

## 相关链接

- OpenAI Developers: `Follow a goal` https://developers.openai.com/codex/use-cases/follow-goals
- OpenAI Developers: `Slash commands in Codex CLI` https://developers.openai.com/codex/cli/slash-commands
- Anthropic Claude Code slash commands https://docs.anthropic.com/en/docs/claude-code/slash-commands
- Anthropic Claude Code hooks https://docs.anthropic.com/en/docs/claude-code/hooks
- ADR-0024:Phase 8 Offline Delegation Scope
- 相关代码候选:`src/aico/core/offline_delegation.py`,`src/aico/core/project_commands.py`,`src/aico/core/orchestrator.py`
