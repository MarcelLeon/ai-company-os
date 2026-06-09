# BLOCKERS.md — 卡点难题

> 当前未解决的卡点。**Agent 接手时,如果能解决其中任何一个,这是最高优先级**。
>
> 卡点和 PITFALLS 的区别:
> - PITFALLS = 已经踩了的坑(向后看,记录历史)
> - BLOCKERS = 还没解决但已挡住进度的问题(向前看,等待解决)

---

## 状态图例

- 🔴 **BLOCKING** — 当前直接挡住下一步进度
- 🟡 **DEFERRED** — 不立即挡路但需要在某个 Phase 之前解决
- 🟢 **RESOLVED** — 已解决(归档保留以供回溯)

---

## 当前活跃与近期归档卡点

### [B-006] 人工 dogfood 待测队列缺少机器验收分层

**状态**:🟢 RESOLVED
**提出于**:Round 143
**最后更新**:2026-06-09(Round 145)
**影响**:`/overnight`、父子 agent 委派、delegate 输出可读性和 `/view` 等长链路修复后,如果每次都要求人类完整重跑历史 prompt,会把验证周期变成新的进度阻塞。

**问题描述**
Round 138-142 连续修复了协作风险误判、`/overnight` handoff 完整性、delegate 输出粘连、移动端长墙和老板查看动线。每一项都有 targeted tests 或 full clean env 验证,但下一轮队列仍容易被理解成"必须先人工完整复验同一长链路",导致机器已覆盖的确定性 contract 仍反复占用人工时间。

**已尝试的方向**
- 方向 A:继续把真实 IM 复验放在最高优先级并要求重跑同一类 `/overnight`。问题是父子委派和 provider 长输出耗时不可控,每次修复后完整人工回归成本过高。
- 方向 B:取消人工 dogfooding,只看测试通过。问题是 AICO 的核心价值是老板手机上的可接手体感,真实 provider / Channel 漂移和移动端可读性不能只靠 mock 判断。
- 方向 C:引入验收分层。机器 Gate 先覆盖确定性 contract,人工 Sample 只验证真实 IM 体感和平台漂移。Round 145 后修正为:Agent 能访问本机 Telegram / provider 时先跑真实样本,人工只看体感和接手便利性。

**解决结果**
- `NORTH_STAR.md` 第三句下新增 "Dogfooding 的验收分层":Dogfooding 仍是最终验收,但不替代机器回归。
- `docs/agent/06-testing-guide.md` 新增 "Dogfooding 与机器验收的边界",把机器 Gate / 人工 Sample / 人工 Blocking 固化为默认顺序。
- `STATUS.md` 下一轮建议已按该规则重排:当前 `/overnight` delegate 输出和老板动线从"人工完整复验阻塞"降级为"机器 Gate 后 1 条代表性 IM 样本"。
- Round 144 在 `docs/playbooks/phase-8-absence-loop.md` 固化当前 Phase 8 AI 前置 contract gate;实测 40 passed in 0.30s。
- Round 145 将 playbook 修正为机器 Gate -> Agent 本机真实样本 -> human 体感 Sample,并实测真实 Telegram 中 `implementer/claude-code -> reviewer/codex` 协作链路完成;当前 gate 更新为 41 passed in 0.36s。

**当前 workaround**
- 无。后续若某条真实 IM 待测无法由当前 Agent 环境覆盖,必须把缺口显式写入 `STATUS.md` 或新 BLOCKER。

**相关链接**
- NORTH_STAR.md 第三句 Dogfooding 分层
- docs/agent/06-testing-guide.md Dogfooding 与机器验收的边界
- docs/playbooks/phase-8-absence-loop.md AI 前置 Contract Gate
- ROUNDS Round 143
- ROUNDS Round 144
- ROUNDS Round 145

### [B-005] Orchestrator class size regression

**状态**:🟡 DEFERRED
**提出于**:Round 132
**最后更新**:2026-05-31
**影响**:Boss-first roadmap 后续 sprint(V1/V2/A3/V3)再往 Orchestrator 加 handler 必须遵守"主体不变"边界,否则会再次撞 500 行硬限。不阻塞 A2 落地,但建议在 V3 完成后做一轮独立拆分。

**问题描述**
B-004 在 Round 107 把 `Orchestrator` 拆到 480 行。M2/A2 各加了 1-2 个 command handler 实例化,加上模块级 `_build_orchestrator_event_index` helper 和 `_setup_*` 子方法,类总规模重新涨到约 585 行。每个方法已经被拆到 <100 行(`__init__` 37 / `_setup_command_handlers` 8 / `_setup_coordinators` 26 / `_setup_boss_and_lead_handlers` 36 / `_setup_workflow_handlers` 28),但类整体仍超 500 行硬限。

**已尝试的方向**
- Round 132 已经把 `__init__` 从 117 行拆成 4 个 <40 行的私有方法,satisfies 单方法限制,不满足类整体限制。
- 不在 A2 本 sprint 做大规模重构,以避免扩范围。

**需要什么才能解开**
- 独立重构 sprint:把 command handlers 的实例化 + 命令分发表拆到一个新的 `OrchestratorCommandRegistry` 类(或类似形态),Orchestrator 主体只剩 task 提交 / 流式输出 / 状态查询。
- 不要再依赖"挤一挤就能再加一个 handler"——下一个 handler 会再次撞限。

**当前 workaround**
- 新 sprint(V1/V2/V3/A3)如果需要加新 command handler,**必须放在自己的模块文件**,Orchestrator 内只加 1 行命令分发 + 1 行 handler 实例化。
- 超出"挤一挤"额度时,优先把已有 `_setup_*` 之一进一步拆分,但**主体仍然超限**——记入本卡点。

**相关链接**
- ROUNDS Round 107(B-004 RESOLVED 时的状态)
- ROUNDS Round 132(本卡点提出)
- ADR-0032(A2 完成时识别问题)
- CLAUDE.md "Hard rules" 单类 <500 行限制

### [B-004] Core orchestration classes exceed project size hard limit

**状态**:🟢 RESOLVED
**提出于**:Round 106
**最后更新**:2026-05-21(Round 107)
**影响**:已不再阻塞公开前工程质量收口;保留归档给后续结构演进参考。

**问题描述**
项目规范要求单类 < 500 行、单方法 < 100 行。Round 106 扫描结果曾是:
- `src/aico/core/orchestrator.py`: `Orchestrator` 约 646 行,`_handle_command` 约 103 行。
- `src/aico/core/task_bus.py`: `TaskBus` 约 566 行。

Round 106 为了落地 SQLite task state store 第一切片,在 `TaskBus` 中接入了可选
`TaskStateStore`,让该类尺寸进一步超过硬限制。功能已由测试覆盖,但结构上需要后续拆分。

**已尝试的方向**
- 过去已将 project commands、role commands、status commands、goal brief、lead decision、
  offline delegation 等流程逐步拆出 `Orchestrator`。
- Round 106 先选择最小持久化切片,未同时进行大规模 `TaskBus` 拆分,避免把状态恢复和结构重构混在一轮。

**解决结果**
- Round 107 新增 `OrchestratorTaskFactory`,把 project/session/memory task 构造从 `Orchestrator` 移出。
- Round 107 新增 `TaskStateRepository`,把 task records、snapshots、approvals 和 adapter mapping 从 `TaskBus` 移出。
- 模块级命令分发拆成 project / role / directory / memory helper,单函数不再超过 100 行。
- 结构扫描结果:`Orchestrator` 480 行,`TaskBus` 448 行,无单类 >=500 行或单函数 >=100 行。
- 验证通过:`pytest` 289 passed / 1 skipped,`ruff check .`,`ruff format --check .`,`mypy src tests`,`git diff --check`。

**当前 workaround**
- 无。后续若继续扩展 TaskBus,优先拆 approval coordinator / adapter dispatch service,不要再把状态恢复逻辑塞回 TaskBus。

**相关链接**
- ROUNDS Round 106
- ROUNDS Round 107
- ADR-0028

### [B-003] Release Room Stage 3 真实 provider 输出不适合作为 public GIF

**状态**:🟡 DEFERRED
**提出于**:Round 91
**最后更新**:2026-05-18(Round 92)
**影响**:不再阻塞 Codex 短输出镜头;仍不建议把 Claude/Codex 长输出直接录成 README GIF。

**问题描述**
真实 Telegram dogfooding 已跑通 project office、team、project memory、interrupt 等管理链路。第一轮发现底层 provider 输出不适合入镜:
- Claude CLI 在当前无 Pro / 输出不稳定环境下长时间不回包。
- Codex CLI 输出包含大量 plugin warning、HTML 片段和 thread resume 错误,会污染 Telegram 画面。

Round 92 已修复 Codex 侧主要问题:
- Codex Adapter 不再 resume 非 Codex provider session。
- 同一 role 重新任命给不同 agent 时,assignment session 会重建,避免沿用旧 provider session。
- Codex stdout 会过滤典型 CLI warning、HTML 片段、`sqlx::query` 噪音和 thread resume error。
- 真实 Telegram dry run 已验证 Codex PM 3-bullet 输出干净可入镜。

**已尝试的方向**
- 方向 A:直接用 Claude 做 PM 拆工。结果任务 accepted 后长时间无输出,需要 `/interrupt`。
- 方向 B:临时把 PM 任给 Codex。结果 Telegram 收到大量 CLI warning / HTML / resume error,无法作为 public GIF。
- 方向 C:修 Codex provider session 和 stdout 过滤后重测。结果 Codex PM 短输出可用。

**需要什么才能解开**
- 如要拍 Claude 实现长输出,仍需确认 Claude 当前登录/额度稳定,或只拍 approval gate 不拍长输出。
- 真实录屏前继续跑 `/ask pm ...` dry run,确保首屏是 role handoff 摘要。

**当前 workaround**
- README public GIF 可以使用真实 Telegram + Codex 短输出镜头。
- Claude 只用于 approval gate / implementer 任务 accepted 画面,不要把长输出作为主镜头。

**相关链接**
- ROUNDS Round 91
- PITFALL P-017

---

## 已归档卡点

### [B-002] AI 间协作协议形态待定

**状态**:🟢 RESOLVED(ADR-0009 Accepted)
**提出于**:Round 1
**最后更新**:2026-04-28
**影响**:曾阻塞 Phase 5 启动;Round 19 已确定最小协议形态

**问题描述**
当 AI A 想 @ AI B 协作时,通信机制是什么?
- 选项 1:走 IM 消息总线(AI A 在群里发消息,AI B 监听)→ 简单但耦合 IM
- 选项 2:走内部 Agent2Agent 协议(类似 A2A 标准)→ 解耦但复杂
- 选项 3:走 RPC 调用 → 失去"群聊感"

**已尝试的方向**
- Phase 1-4 暂时绕开了 AI 间协作,只做“人类 → 单/多 Adapter”任务派发。
- Round 18 后 Phase 4 收口,该问题从延后卡点升级为 Phase 5 入口卡点。
- Round 19 选择内部 A2A-inspired 轻量协作指令:`@persona: request`,暂不直接实现 HTTP A2A,也不把 IM 当内部总线。

**需要什么才能解开**
- 已解决:见 ADR-0009 和 `docs/playbooks/phase-5-collaboration.md`。

**当前 workaround**
- 无。

**相关链接**
- ADR-0009
- ROUNDS Round 19

### [B-001] 技术栈选型

**状态**:🟢 RESOLVED(ADR-0001 Accepted)
**提出于**:Round 1
**最后更新**:2026-04-27
**影响**:曾阻塞所有后续编码工作

**问题描述**
编排核心使用 Java / Python / TypeScript 中的哪一个尚未决定。每种都有取舍:
- Java + Spring AI:Wang 已有 `claw-code-java` 经验,但 AI CLI 生态对 Java 支持薄弱
- Python + FastAPI:AI 生态最成熟,但 Wang 的 Java 经验复用有限
- TypeScript + Node:接 Telegram Bot / 各 AI CLI 最丝滑,但偏离 Wang 主战场

**已尝试的方向**
- Round 2 人类明确偏向 Python 技术栈,主要原因是不选 Java:代码量偏多、维护负担偏高。
- Round 2 Agent 初步建议:核心用 Python 3.11+、FastAPI、asyncio、Pydantic v2、typing.Protocol、pytest/ruff/mypy。
- Round 3 已写 ADR-0001 并接受 Python 技术栈,同时创建 `pyproject.toml` 和最小 Python 骨架。

**需要什么才能解开**
- 已解决:见 `docs/decisions/0001-tech-stack-selection.md`。

**当前 workaround**
- 无。后续编码默认使用 ADR-0001 的 Python 技术栈。

**相关链接**
- STATUS.md 下一轮建议 #1
- ADR-0001

---

## 模板(新增卡点用)

```markdown
### [B-XXX] 卡点简短标题

**状态**:🔴 BLOCKING / 🟡 DEFERRED / 🟢 RESOLVED
**提出于**:Round N
**最后更新**:YYYY-MM-DD
**影响**:具体挡住了什么

**问题描述**
详细说明这是什么卡点。

**已尝试的方向**
- 方向 A:为什么没成
- 方向 B:为什么没成

**需要什么才能解开**
- 具体可执行的步骤

**当前 workaround**
- 现在用什么临时方案绕开

**相关链接**
- ROUNDS / PITFALLS / ADR
```
