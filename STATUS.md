# STATUS.md — 当前状态

> 这个文件高频更新。每一轮 AI 工作或人类工作结束都要更新这里。
> 阅读顺序:从上往下,前面的信息时效性最高。

**最后更新**:2026-05-06
**当前轮次**:Round 60(Task Collaboration Trace)
**当前阶段**:🟡 Phase 5 进行中 — AI 间协作

---

## 项目宏大叙事(一句话)

把开发者 Mac 上散落的 AI 工具收编成一个可远程指挥的"虚拟公司",通过 IM 异步协作,让"AI 团队"成为开发者真正的生产力杠杆。

---

## 阶段地图

| 阶段 | 名称 | 状态 | 验收标准 |
|---|---|---|---|
| Phase 0 | 项目立项与文档体系 | 🟢 完成 | 文档体系建立,北极星确立 |
| Phase 1 | 核心协议与单 Adapter MVP | 🟢 完成 | 1 个 AI(Claude Code)能从 1 个 IM(Telegram)接收任务并返回结果 |
| Phase 2 | 多 Adapter + 状态机 | 🟢 完成 | 至少 2 个 AI 接入,状态可在 IM 中查询 |
| Phase 3 | 人格化层 + 群聊编排 | 🟢 完成 | AI 有差异化人设,群聊能 broadcast 任务 |
| Phase 4 | 审批与审计 | 🟢 完成 | 危险操作可推送审批,所有行为有 trace |
| Phase 5 | AI 间协作 | 🟡 进行中 | AI 之间可以互相 @ 协作,任务编排成型 |
| Phase 6 | 可观测看板 | ⚪ 未开始 | 工时/KPI/token 消耗可视化 |
| Phase 7 | 共享记忆层 | ⚪ 未开始 | 所有 AI 共享上下文记忆 |
| Phase 8 | 离线托管模式 | ⚪ 未开始 | 睡前下任务,早上看结果 |

图例:🟢 完成 / 🟡 进行中 / ⚪ 未开始 / 🔴 阻塞

---

## 当前进度详细

### Phase 0 进度

- [x] 北极星三句话确立
- [x] 文档体系骨架搭建
- [x] AGENTS.md / README.md / NORTH_STAR.md 三入口建立
- [x] journal 体系(ROUNDS / PITFALLS / BLOCKERS)初始化
- [x] 文档目录按 `docs/agent` / `docs/journal` / `docs/architecture` / `docs/human` 归位
- [x] 技术栈选型决策(ADR-0001:Python 3.11+ / FastAPI / asyncio / Pydantic v2)
- [x] 核心协议草案(Adapter 接口、IM 通道接口、任务消息格式)
- [x] 第一个 ADR(架构决策记录)输出
- [x] Python 工程基础设施(`pyproject.toml` / `uv.lock` / ruff / mypy / pytest)
- [x] CI 骨架(GitHub Actions 跑 pytest / ruff / mypy)

### Phase 1 进度

- [x] ADR-0002 Adapter / Channel 协议定稿
- [x] 最小 Router / TaskBus / Orchestrator 假链路
- [x] FakeChannel + FakeAdapter 端到端单测
- [x] Phase 1 MVP 范围 ADR / playbook 明确
- [x] Telegram Channel 文本 MVP
- [x] Claude Code Adapter MVP
- [x] Phase 1 本地启动入口
- [x] Telegram → 编排核心 → Claude Code → Telegram 真实链路验收

### Phase 2 进度

- [x] AdapterRegistry 多 Adapter 注册与按 persona 路由
- [x] `/status` 文本命令返回 Adapter 状态快照
- [x] Codex Adapter 文本 MVP(默认 read-only sandbox)
- [x] Telegram 中启用双 Adapter 后的真实状态查询验收
- [x] `/codex` / `@codex` / `codex:` 文本唤醒路由
- [x] 第二个真实 AI 任务链路验收
- [x] 更明确的任务状态机(running / done / failed / interrupted / rejected)

### Phase 3 进度

- [x] Phase 3 范围 ADR / Playbook
- [x] Persona 最小模型与注册表
- [x] `/broadcast <task>` 最小链路
- [x] Telegram 真实 persona / broadcast 验收
- [x] Persona 外部配置文件入口

### Phase 4 进度

- [x] Phase 4 范围 ADR / Playbook
- [x] 危险操作识别模型(`read_only` / `write_files` / `shell_exec` / `destructive`)
- [x] `waiting_approval` 任务状态
- [x] Telegram `/approve <task_id>` / `/reject <task_id>` 最小审批命令
- [x] 内存审计事件模型
- [x] `/audit` 最近审计事件只读查询
- [x] `/approve` / `/reject` 无 task id 快捷审批
- [x] 审批权限策略(默认 requester,可配置额外 reviewer)
- [x] Adapter 风险能力门禁(read-only Adapter 拒绝危险任务)
- [x] Claude Code 远程审批后免本机二次授权
- [x] `/audit` 多行可读输出
- [x] Telegram 真实审批 smoke test
- [x] 审计事件 JSONL 持久化

### Phase 5 进度

- [x] Phase 5 协作协议 ADR / Playbook
- [x] B-002 AI 间协作协议形态决策
- [x] 轻量 `@persona: request` 协作指令解析
- [x] Adapter 输出触发目标 persona 子任务
- [x] 协作任务审计事件增强
- [x] Agent Session / Harness 边界 ADR
- [x] Session 命令 MVP(`/sessions` / `/new` / `/use`)
- [x] Claude Provider Session Resume MVP
- [x] Codex `exec resume` 命令形态评估与 Adapter 构造支持
- [x] Telegram 流式输出 no-op edit 容错
- [x] Codex provider session 显式绑定命令(`/bind`)
- [x] Agent 能力体验命令(`/agents` / `/agent` / `/skills` / `/tools`)
- [x] Agent 能力体验命令 Telegram 真实验收(`/agents` / `/skills` / `/tools`)
- [x] Project Assignment Layer 设计决策(Agent / Project / Assignment)
- [x] 面向技术读者的架构图与核心概念工作流图(draw.io)
- [x] Project Assignment Layer MVP 第一切片(配置模型、项目命令、project-scoped session)
- [x] Project Team / Appointment 老板视角命令设计与 Role 体系完善
- [x] Project Team / Appointment 命令 MVP(`/project` / `/team` / `/who` / `/appoint` / `/ask` / `/lead`)
- [x] Project roles view MVP(`/roles`)
- [x] Role proposal confirmation MVP(`/role propose` / `/role confirm` / `/role discard`)
- [x] Project unappoint MVP(`/unappoint`)
- [x] RoleTemplate / ProjectRoleOverride / Appointment 配置模型 MVP
- [x] Appointment Prompt Stack MVP
- [x] Project brief / risks MVP(`/brief` / `/risks`)
- [x] Project daily / weekly 本地报告 MVP(`/daily` / `/weekly`)
- [x] Project blockers MVP(`/blockers`)
- [x] Project next actions MVP(`/next`)
- [x] Project Team 本地验收流
- [x] Project appointment 同 role 去重与 `/team` lead 可见性
- [x] Project Team / Appointment Telegram 真实验收
- [x] Role proposal confirmation Telegram 真实验收
- [x] Orchestrator role proposal helper 拆分
- [x] Platform-neutral IM render contract 第一切片(`spans` / `actions`)
- [x] Project office key messages 使用 render hints
- [x] Telegram callback query 转入现有命令通路
- [x] Project status LLM summary MVP(`/brief` / `/risks` / `/blockers` / `/next`)
- [x] Project summary Markdown 转 render spans
- [x] Project report LLM summary MVP(`/daily` / `/weekly`)
- [x] Project status Facts 小节 / slash command render spans
- [x] IM 远程中断命令(`/interrupt`)
- [x] ProjectRoleCommandHandler 结构拆分
- [x] ProjectStatusCommandHandler 结构拆分
- [x] `/interrupt` Telegram 真实复验
- [x] `/blockers` Telegram 真实复验
- [x] Codex output idle timeout MVP
- [x] Project Facts bullet / inline Markdown render spans
- [x] Project Facts Markdown heading render spans
- [x] Task trace commands(`/tasks` / `/task`)
- [x] `/task` collaboration parent / child trace
- [ ] Telegram 真实协作 smoke test
- [x] Prompt 分层渲染

---

## 上一轮做了什么

**Round 60**(2026-05-06,Codex):
- 人类已验证 `/task` / `/tasks` 相关命令,要求继续后续功能开发。
- 增强 `/task <task_id>` 协作追踪详情:
  - child task 详情会展示 `requested by` 和 parent task 的 `/task <short_id>` 入口。
  - parent task 详情会展示已触发的 child task 列表、目标 persona 和对应 `/task <short_id>` 入口。
  - 该能力复用既有 `collaboration_requested` 审计事件,没有改 TaskBus 存储模型或引入新仓储。
- 新增 Orchestrator 单测覆盖 `@reviewer` 协作后查询 parent / child task 详情。
- 定向验证通过:43 个 `test_orchestrator.py` 单测、改动文件 `ruff check`。

**Round 59**(2026-05-06,Codex):
- 人类在 Telegram 验证 Project Facts heading render 效果良好,要求继续开发后续能力。
- 新增 IM 任务追踪命令:
  - `/tasks [limit]`:展示最近任务,默认 10 条,最多 20 条。
  - `/task <task_id>`:支持完整或短 task id 前缀,展示单个任务详情。
  - waiting approval 任务会给出 `/approve <short_id>` / `/reject <short_id>` 动作提示。
  - running 任务会给出 `/interrupt <short_id>` 动作提示。
- `TaskBus` 新增只读 `task_snapshot(task_ref)` 查询入口,复用既有 task id 前缀匹配语义。
- 更新 help、daily ops 和 changelog;新增命令解析与 Orchestrator 单测。
- 完整验证通过:170 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check`。

**Round 58**(2026-05-06,Codex):
- 人类复验 `/brief` 后反馈整体好了很多,但文档 snippet 中的 Markdown 标题仍裸露,截图中可见 `# NORTH_STAR.md`、`## 第一句`、`### 状态变化`。
- 修复 Project Facts Markdown heading 渲染:
  - `_heading_message()` 现在会识别行首 `#` / `##` / `###` 等 Markdown 标题。
  - 标题会去掉 `#` 前缀,保留原标题文本并生成 `MessageTextSpan(BOLD)`。
  - 该能力作用于 `/brief`、`/risks`、`/blockers`、`/next`、`/daily`、`/weekly` 的 facts 文档片段。
- 新增单测覆盖文档 snippet 中的 Markdown heading 渲染。
- 完整验证通过:166 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check`。

**Round 57**(2026-05-06,Codex):
- 人类复测 Phase 5 `@reviewer` 真实协作 smoke test:
  - Telegram 收到 `Task accepted: 1481a413-f886-46bc-b7d4-98cccf295218 [reviewer]`。
  - `/status` 显示 `claude-code: idle`, `codex: busy`。
  - 结论:协作解析和 child task 创建成功,卡点仍是 Codex CLI accepted 后长期无 stdout。
- 修复 Codex busy 自动释放:
  - `ClaudeCodeAdapter` 增加可选 `output_idle_timeout_seconds`。
  - `CodexAdapter` 默认 90 秒无 stdout 自动终止底层 CLI,输出 `adapter output idle timeout after 90s`,并释放 busy。
  - `Phase1Settings` 新增 `AICO_CODEX_OUTPUT_IDLE_TIMEOUT_SECONDS`。
- 修复 Project Facts 无序列表 / inline Markdown 渲染:
  - `_heading_message()` 现在会规范化 facts 中的 `- ` / `* ` 为 `• `。
  - facts 中 `**bold**`、`` `code` ``、`*italic*` 也会转成 render spans,不再裸露 Markdown 标记。
- 更新 PITFALL P-014、Phase 5 collaboration playbook 和 daily ops。
- 完整验证通过:165 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check`。

**Round 56**(2026-05-06,Codex):
- 人类已完成真实复验:
  - `/interrupt` 可用。
  - `/blockers` 格式可用。
- 收口 Round 55 的结构拆分验证:
  - `ProjectStatusCommandHandler` 拆分后仍保持 `/brief`、`/risks`、`/blockers`、`/next`、`/daily`、`/weekly` 用户语义不变。
  - 完整验证通过:162 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check`。
- 代码侧下一步不建议继续堆项目命令;若继续开发,优先二选一:
  - 完成 Phase 5 `@reviewer` collaboration smoke test,若 Codex 子任务仍无 stdout,再设计 timeout / heartbeat。
  - 拆 Project team/assignment handler,继续降低 `ProjectCommandHandler` 门面复杂度。

**Round 55**(2026-05-06,Codex):
- 人类要求继续开发后续功能;真实复验仍需人类重启 AICO 服务并在 Telegram 操作。
- 继续处理 Project 命令结构债:
  - 新增 `ProjectStatusCommandHandler`,承接 `/brief`、`/risks`、`/blockers`、`/next`、`/daily`、`/weekly`。
  - 状态 / 报告 handler 集中负责本地 facts 构造、文档 snippet 聚合、summary callback 和 summary 失败降级。
  - `ProjectCommandHandler` 保持 Orchestrator 的项目命令门面,对应 handle 方法改为薄代理。
- 结构结果:
  - `src/aico/core/project_commands.py` 从 476 行降到 349 行。
  - `src/aico/core/project_status_commands.py` 为 195 行。
  - `src/aico/core/project_role_commands.py` 保持 108 行。
- 完整验证已在 Round 56 补齐。

**Round 54**(2026-05-06,Codex):
- 人类要求继续开发;真实 `/interrupt`、Project status render 和 Phase 5 collaboration smoke 复验都需要人类重启服务和 Telegram 操作。
- 按下一轮代码侧高优先级处理结构债:
  - 新增 `ProjectRoleCommandHandler`,承接 `/role propose`、`/role confirm`、`/role discard` 以及 role draft 暂存。
  - `ProjectCommandHandler.handle_role()` 改为薄代理,用户可见语义不变。
  - `ProjectCommandHandler` 不再持有 `_role_drafts` 和 `_propose_role` 运行细节。
- 结构结果:
  - `src/aico/core/project_commands.py` 从 544 行降到 475 行。
  - `src/aico/core/project_role_commands.py` 为 108 行。
- 完整验证通过:162 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`。

**Round 53**(2026-05-06,Codex):
- 人类执行 Phase 5 协作 smoke test 后反馈:
  - Telegram 收到 `Collaboration requested: claude -> reviewer`。
  - 随后停在 `Task accepted: 31e559c3-bd7c-4e1b-9385-024431f8635a [reviewer]`。
- 日志定位:
  - 协作解析和 child task 创建成功。
  - reviewer 子任务已派发到 `codex`,并进入 `Stream start`。
  - 没有后续 `Stream output` / `Adapter process exited`,进程表显示 Codex CLI 子进程仍在运行。
  - 根因不是 Telegram render 或协作协议,而是底层 Codex CLI 长时间无 stdout。
- 修复远程可中断缺口:
  - 新增 `/interrupt <task_id>` 命令。
  - `TaskBus.interrupt()` 支持 task id 前缀匹配,会拒绝 unknown / ambiguous / non-running task。
  - Orchestrator 返回 `Task interrupted: <short_id>` 或明确失败原因。
  - 中断 running 任务会继续更新 `interrupted` 状态并记录 `task_interrupted` 审计事件。
- 新增 PITFALL P-014,记录 reviewer accepted 后 Codex 长时间无 stdout 且 IM 无中断入口的问题。
- 更新 Phase 5 collaboration playbook 和 daily ops。
- 验证通过:定向 66 个单测;完整验证见本轮交接。

**Round 52**(2026-05-06,Codex):
- 人类补充真实 Telegram 验收结果:
  - `/project`、`/team`、`/roles` 首行加粗和 `/role propose` Confirm / Discard 按钮均已验证通过。
  - `/blockers` 仍缺少格式。
  - `/brief`、`/next` 的 `Boss summary` 部分格式正确,但 `Facts` 部分缺少结构化样式。
- 修复项目状态 Facts 渲染:
  - `_heading_message()` 不再只给首行加粗,会为项目消息中的小节标题生成 `MessageTextSpan(BOLD)`。
  - 对事实文本里的 slash command 片段生成 `MessageTextSpan(CODE)`,例如 `/approve`、`/reject`、`/ask`、`/blockers`。
  - `project_summary_message()` 继续把 facts spans 平移到 `Facts` 区域,因此 summary + facts 组合消息也能保留 facts 样式。
- 新增 `tests/unit/test_project_messages.py` 覆盖 `/blockers` 小节 / 命令 spans,以及 summary 组合消息保留 facts spans。
- 在 `docs/human/daily-ops.md` 补充 Phase 5 `@reviewer` 真实协作 smoke test 推荐 prompt。
- 验证通过:159 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`。

**Round 51**(2026-05-06,Codex):
- 人类验证 `/brief` 等 Boss summary 能力有效,指出主要问题是 summary 内部 `**bold**`、反引号、无序列表等 Markdown 文法没有渲染。
- 修复 `project_summary_message()`:
  - summary 里的 `- ` / `* ` 列表前缀转换为 `• `。
  - `**bold**` 转为干净文本 + `MessageTextSpan(BOLD)`。
  - `` `code` `` 转为干净文本 + `MessageTextSpan(CODE)`。
  - `*italic*` 转为干净文本 + `MessageTextSpan(ITALIC)`。
  - 继续保留 `Boss summary` / `Facts` heading spans 和完整 Facts 原文。
- 在已验证短状态 summary 基本可用后,将同样 summary 机制扩展到 `/daily` / `/weekly`;仍保留完整 Facts。
- 新增 `tests/unit/test_project_messages.py`,覆盖 summary Markdown 到 spans 的转换。
- 本地定向测试已通过;完整验证见本轮交接。

**Round 50**(2026-05-06,Codex):
- 人类确认 Round 49 的 Telegram render / button 能力有效,要求继续开发后续能力。
- 新增 `ProjectSummaryCoordinator`,为 `/brief`、`/risks`、`/blockers`、`/next` 生成顶部 `Boss summary`:
  - 输入只使用现有本地事实消息。
  - 通过当前项目 lead appointment/provider session 发起只读 summary task。
  - 输出保留完整 `Facts` 原文,摘要只是顶部管理视角说明。
- 新增 `aico.intent=project_summary` 内部元数据,风险识别将 project summary task 视为 read-only,避免事实文本中出现 `/approve`、`run tests`、`write docs` 等词时误触发审批。
- summary task 如果没有 lead、provider busy、adapter 拒绝或输出失败,命令会直接发送原本的事实消息,不让摘要失败影响状态查询。
- `project_summary_message()` 会把 `Boss summary` 和 `Facts` 作为独立 heading span,Telegram 可加粗展示。
- 本轮未给 `/daily` / `/weekly` 加 LLM summary,避免扩大范围;它们仍是本地事实报告。
- 本地 156 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests` 全绿。

**Round 49**(2026-05-06,Codex):
- 按下一轮最高优先级,将 ADR-0013 的 IM render contract 用到项目办公室关键消息。
- `project_messages.py` 为项目办公室、团队、岗位、任命、撤任、lead、role proposal 等消息首行增加 `MessageTextSpan(BOLD)`,Telegram 会映射为 HTML 加粗;纯文本 `text` 保持不变。
- `role_proposal_message()` 增加 `MessageAction`:
  - `Confirm` → `/role confirm`
  - `Discard` → `/role discard`
- Telegram Channel 支持 `callback_query`:按钮点击会被转换为 `IncomingMessage(content.text=<callback data>)`,复用现有命令解析;同时调用 `answerCallbackQuery` 避免 Telegram 客户端一直转圈。
- 新增回归测试覆盖 role proposal actions 和 callback query 转入命令消息。
- 本地 154 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests` 全绿。

**Round 48**(2026-05-05,Codex):
- 人类确认 Project Team / Appointment 与 Role proposal confirmation 的真实 Telegram 验收均已通过:
  - 重复 `/appoint ... as tester ...` 不再让 `/team` 出现多个 tester。
  - `/lead tester` 后 `/team` 能看到 lead。
  - `/role propose` 后 `/role confirm`,新增 role 能在 `/roles` 中看到。
- 按下一轮高优先级先做结构拆分,新增 `RoleProposalCoordinator`,把 role proposal 的内部任务提交、输出收集、provider session busy/idle 和 JSON 解析流程从 `Orchestrator` 移到 `src/aico/core/role_proposal.py`。
- `Orchestrator` 只保留接线逻辑,类体从 482 行降到 439 行,继续满足单类 <500 行硬约束。
- 修复拆分时暴露的 `risk -> role_proposal -> task_bus -> risk` 循环导入,`TaskBus` 在 role proposal 模块中改为 type-checking only import。
- 本轮没有改变 `/role propose`、`/role confirm`、`/role discard` 的用户可见语义。
- 继续完成 IM 文案渲染层第一切片: `MessageContent` 增加平台无关 `MessageTextSpan` / `MessageAction`,Telegram Channel 将 spans 映射为 HTML、actions 映射为 inline keyboard;纯文本消息不变。
- 新增 ADR-0013,记录不把 Telegram HTML / reply_markup 写进核心消息层的决策。
- 本地 153 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests` 全绿。

**Round 19**(2026-04-28,Codex):
- 调研 A2A / ACP / MCP 当前状态,决定 Phase 5 MVP 采用内部 A2A-inspired 轻量协作指令,不直接实现 HTTP A2A。
- 新增 `src/aico/core/collaboration.py`,支持解析 Adapter 输出中的 `@persona: request`。
- `Orchestrator` 识别协作指令后创建目标 persona 子任务,复用现有 TaskBus、审批、审计和状态机。
- 默认 implementer persona 提示增加 reviewer 协作指令说明。
- 新增 ADR-0009 和 Phase 5 playbook,并解决 B-002。
- 本地 88 个单测、`ruff check`、`ruff format --check`、`mypy` 全绿。

详见 [`docs/journal/ROUNDS.md`](docs/journal/ROUNDS.md)

**Round 20**(2026-04-28,Codex):
- 人类真实测试发现 `@reviewer review一下...` 没触发 Codex/reviewer,因为协作解析只支持 `@reviewer: ...` 冒号语法。
- 协作指令解析扩展为同时支持 `@persona request` 和 `@persona: request`,仍要求行首触发以避免误判。
- 修复 Telegram polling 串行 await 长任务 handler 的问题;现在每条 incoming message 会后台分发,长任务运行时 `/status` / `/audit` 不再被 polling 阻塞。
- 新增 PITFALL P-008 / P-009,更新 Phase 5 playbook 和 daily ops。
- 本地 90 个单测、`ruff check`、`ruff format --check`、`mypy` 全绿。

**Round 21**(2026-04-28,Codex):
- 人类真实使用中发现 Telegram 长文本只收到部分信息。
- 定位为流式输出持续编辑同一条消息,超过 Telegram 4096 字符限制后 Bot API 失败,handler 中断。
- 新增 `StreamedMessageWriter`,按 3900 字符保守上限拆分长输出;当前消息装满后继续发送下一条消息,避免内容被截断。
- 梳理并向人类说明 AICO 对 prompt 的实际加工:路由前缀剥离、persona role instruction 前置、协作子任务 payload 包装、协作指令行消费、Claude/Codex CLI 权限参数差异。
- 新增 PITFALL P-010,更新 troubleshooting / daily ops / playbook / changelog。

**Round 22**(2026-04-29,Codex):
- 新增 `collaboration_requested` 审计事件,在 AI 间协作触发 reviewer 子任务前记录 parent task 与 child task 的关系。
- 新增 `src/aico/core/commands.py`,把内置 IM 命令解析从 `Orchestrator` 拆出,并支持 `/approve@bot abcdef12` 这类 Telegram bot suffix。
- `Orchestrator` 从 364 行降到 318 行,降低后续命令扩展风险;`TaskBus` 保持 496 行,未突破硬上限。
- 风险识别从散落 marker tuple 改为 `RiskRule` 规则表,新增单测覆盖多规则命中时保留原因。
- 本地 targeted tests 已通过;完整验证见本轮交接。

**Round 23**(2026-04-29,Codex):
- 人类反馈 `/claude` 超长文本请求没有收到结果,怀疑卡住或长文本仍有问题。
- 新增后台日志配置:`AICO_LOG_LEVEL`、`AICO_LOG_PATH`,默认写 `logs/aico.log` 并同步输出控制台。
- 在 Telegram Channel、Orchestrator、Claude/Codex Adapter、StreamedMessageWriter 记录关键链路日志,包括入站消息、任务路由、ack、CLI 进程启动/退出、stdout chunk 长度、Telegram send/edit 长度和长文本分片。
- 记录 P-011,明确长任务没结果时先用日志区分 busy、CLI 未退出、无 stdout、Telegram 出口失败。

**Round 24**(2026-04-29,Codex):
- 人类确认 Adapter 层和 Loop 层方向,要求 Agent Harness 薄层继续简化:tools/skills 由 Claude/Codex provider 自己拥有,AICO 仅通过 Adapter 翻译和展示。
- 新增 ADR-0010,明确原话边界:`AICO Agent Harness is a session and capability facade, not a tool execution runtime.`
- 新增 `src/aico/core/agent_session.py`,定义 `AgentCard`、`ProviderSessionRef`、`AgentSession` 和 `InMemoryAgentSessionStore`。
- `Phase1Runtime` 挂载空的 `session_store`,为后续 `/sessions`、`/use`、provider session resume 做准备,不改变当前 Telegram 行为。

**Round 25**(2026-04-29,Codex):
- 基于 `InMemoryAgentSessionStore` 增加 `/sessions`、`/new <agent>`、`/use <session_id>` 命令。
- `AgentSessionStore` 增加按 channel / chat / sender 作用域保存 active session 的能力。
- `Orchestrator` 在普通消息没有显式 `/agent`、`@agent`、`agent:` 或 Telegram mention 时,会优先路由到当前 active session 的 agent。
- `Phase1Runtime` 将同一个 session store 注入 Orchestrator,让 Telegram 命令和运行时共享会话状态。
- 本轮没有接 provider resume;Claude/Codex CLI 原生会话恢复仍是下一步。

**Round 26**(2026-04-29,Codex):
- 用本机 CLI help 确认 Claude 支持 `--session-id`、`--resume`、`--continue`,Codex 支持 `codex exec resume [SESSION_ID] [PROMPT]`。
- `ProviderSessionRef` 增加 `initialized`,并新增 task metadata helper,让 active session task 能携带 provider session id 与 `new/resume` 模式。
- `Orchestrator` 将 active session 的 provider ref 注入 Task metadata;首轮成功派发后标记 provider ref initialized,后续同 session 任务自动进入 resume 模式。
- `ClaudeCodeAdapter` 首轮使用 `--session-id <uuid>`,后续使用 `--resume <uuid>`;自定义命令若已有 session 参数则不重复追加。
- `CodexAdapter` 已支持已有 provider ref 时构造 `codex exec resume <session_id> <prompt>`,并把默认 `exec --sandbox read-only` 安全提升到 resume 可接受的全局参数位置。
- `Phase1Runtime` 为 Claude persona / alias 创建 provider session ref;Codex 暂不自动创建 provider ref,等待后续 session id 捕获或显式绑定。
- 本地 114 个单测、`ruff check`、`ruff format --check`、`mypy`、`git diff --check` 全绿。

**Round 27**(2026-04-29,Codex):
- 人类反馈 `/codex inspect this` 卡住,以及 Claude 回答技能列表时只收到开头一句。
- 查 `logs/aico.log` 定位为 Telegram `editMessageText` 返回 HTTP 400 后 handler 异常退出;这不是 Codex “指定新 session id”能力缺失导致的。
- 修复 Telegram `_post()` 的错误解析顺序,先读取 Bot API JSON `description`,再处理 HTTP / business error。
- `edit_message()` 对 `Bad Request: message is not modified` 做 no-op 容错,避免尾部空白/换行 chunk 把流式输出打断。
- 新增 P-012,记录 no-op edit 400 导致长文本像被吞掉、Adapter 看起来 busy 的坑。
- 本地 Telegram Channel 单测已覆盖 HTTP 400 description 和 no-op edit 容错。

**Round 28**(2026-04-30,Codex):
- 人类要求继续迭代后续两个阶段,然后交给人类验收和审查。
- 选择 Phase 5 中两个可本地闭环的后续阶段:Codex provider session 显式绑定、agent 能力/职责可见性。
- 新增 `/bind <session_id|agent> <provider_session_id>`;支持 `/bind codex <provider_session_id>` 创建并激活 reviewer/Codex session,后续普通消息以 `resume` 模式进入 provider session。
- 新增 `AgentDirectory` 和 agent card 构建,从 persona + adapter 生成只读能力门面,不复制 provider tools/skills registry。
- 新增 `/agents`、`/agent <agent>` 展示角色、adapter、provider、status、capabilities 和 skills/tools 来源。
- 新增 `/skills <agent>`、`/tools <agent>`,把能力探测问题路由给底层 provider 自己回答。
- 把命令输出渲染移动到 `command_messages.py`,让 `Orchestrator` 保持在 500 行以下。
- 本地定向单测已覆盖命令解析、agent directory、provider bind 和 skills introspection。

**Round 29**(2026-05-04,Codex):
- 人类已真实验收 `/agents`、`/skills`、`/tools`,并指出下一阶段痛点不是裸 session,而是多项目长期迭代时缺少项目进展、风险、日报/周报等公司语义。
- 确定 Project Assignment Layer:Agent 是员工,Project 是项目,Assignment 是员工在项目里的岗位/工位;provider session、权限、role prompt、工作目录和状态都绑定到 Assignment/seat。
- 决定 Assignment 主要通过配置文件维护;MVP slash command 只做查看和切换,不做 `/assign ...` 这类聊天内组织架构修改。
- Prompt 模板分为 Agent Base Prompt、Role Prompt、Project Brief、Runtime Context 四层,避免每个 Assignment 复制大段 prompt。
- `/handoff` 暂不进入 MVP,因为项目中途换 Agent 涉及上下文迁移和未完成假设传递,复杂度高。
- 新增 ADR-0011 和 `docs/architecture/project-assignment-layer.md`,并同步 README / 架构总览 / ADR 索引。

**Round 30**(2026-05-04,Codex):
- 人类要求产出两张可向用户和技术读者介绍项目的 draw.io 图:一张分层技术架构图,一张核心概念和角色分工工作流程图。
- 新增 `docs/architecture/aico-layered-architecture.drawio`,按用户体验/应用运行时/公司模型与治理/协议适配器/本地 provider 与持久化自上而下分层。
- 新增 `docs/architecture/aico-concepts-workflow.drawio`,解释 Human Manager、Project、Agent Catalog、Assignment/seat、provider session、prompt stack、审批审计和 AI 间协作流程。
- 更新 `docs/architecture/overview.md`,加入两张可编辑图的入口链接。
- 使用 XML 解析验证两个 `.drawio` 文件格式有效。

**Round 31**(2026-05-04,Codex):
- 开始实现 Project Assignment Layer MVP 的第一切片。
- 新增 `src/aico/core/project_assignment.py`,定义 `CompanyAgentProfile`、`ProjectProfile`、`AssignmentProfile`、`ProjectAssignmentConfig` 和 `ProjectAssignmentDirectory`,支持配置校验、active project、默认 assignment 和 task metadata 注入。
- 新增 `config/projects.example.json` 和 `AICO_PROJECT_CONFIG_PATH` 配置入口;未配置时会基于当前 persona/agent 自动生成默认 `aico` 项目 assignment。
- 新增 `/projects`、`/project <project>`、`/use project <project>`、`/assignments [project]`、`/assignment <seat>` 命令。
- `/use project aico` 后,当前聊天 + 发送者的普通消息会路由到项目默认 assignment,provider session ref 绑定到 assignment seat;显式 `/claude` / `/codex` / `@reviewer` 仍优先。
- 将 agent/project/session 类命令处理拆到 `src/aico/core/orchestrator_commands.py`,让 `Orchestrator` 回到 467 行,低于单类 500 行硬约束。
- Targeted tests 53 个通过;ruff 和 mypy targeted checks 通过。

**Round 32**(2026-05-04,Codex):
- 人类指出 `assignment/seat/use role` 不符合唯一老板派发任命的直觉,要求在正式使用前直接改成老板视角设计。
- 决定把 Assignment 的产品层表达改为 Appointment / Team:`seat` 保留为内部稳定 id,主路径命令改为 `/project`、`/team`、`/who`、`/appoint`、`/ask`、`/lead`。
- 新增 ADR-0012,明确 boss-facing team commands 和 role system,并否决 `/use assignment <seat>` 作为主路径。
- 重写 `docs/architecture/project-assignment-layer.md`,补齐 RoleTemplate / Project Role Override / Appointment Contract / Prompt Stack / 新项目默认任命设计。
- 完善 role 体系:除 implementer / reviewer 外,加入 tester、pm、architect、security、docs、ops、analyst、designer 等可选岗位。

**Round 33**(2026-05-04,Codex):
- 实现 boss-facing Project Team 命令 MVP:`/project <project>` 进入项目办公室,`/team` 查看团队,`/who <role>` 查看岗位负责人,`/appoint <agent> as <role>` 任命员工,`/ask <role> <task>` 单次派活,`/lead <role>` 设置默认牵头角色。
- `ProjectAssignmentConfig` 新增 `roles`、`ProjectProfile.roles`、`appointments`,旧 `assignments` 字段继续兼容。
- `ProjectAssignmentDirectory` 支持 runtime appointment upsert、按 role 查 appointment、设置默认 role,并继续为旧 assignment/seat 命令提供兼容。
- `config/projects.example.json` 改成 roles / project role override / appointments 示例,包含 implementer、reviewer、tester、pm 等岗位。
- 新增/更新单测覆盖命令解析、appointment runtime 更新、`/ask` 路由到 role appointment、`/lead` 后普通消息走新默认 role。
- 本地 133 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests` 全绿。

**Round 34**(2026-05-04,Codex):
- 人类真实执行 `/appoint Claude as tester read_repo run_tests` 返回 `Cannot appoint Claude as tester`。
- 定位为命令层能用大小写不敏感的 `AgentDirectory.resolve()` 识别 `Claude`,但 `ProjectAssignmentDirectory.upsert_appointment()` 再用原始 `Claude` 精确查配置 key `claude`,导致任命被拒。
- 修复 `ProjectAssignmentDirectory` 的 agent / role / project lookup,统一使用大小写不敏感、下划线/横线兼容的 ref 解析;runtime appointment 会写入 canonical `claude` / `tester`。
- 新增单测覆盖 `/appoint` 中 `Claude` / `Tester` 这类人类自然输入。
- 本地 133 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests` 全绿。

**Round 35**(2026-05-04,Codex):
- 人类指出 `/default tester` 仍偏工程视角,要求改成更像老板语言的 `/lead tester`,并继续开发。
- 新增 `CommandName.LEAD`,主路径使用 `/lead <role>` 设置当前项目默认牵头 role;`/default <role>` 保留为兼容别名。
- 命令输出从 `Default role` 改为 `Lead role`,强调“由哪个岗位牵头”。
- 新增 `src/aico/core/prompt_stack.py`,实现 Appointment prompt stack MVP。
- 走 project appointment 的任务会渲染 Agent、RoleTemplate、Project、ProjectRoleOverride、Appointment Contract 和 Current task;显式 `/claude`、`/codex`、`@reviewer` 等非 appointment 路由仍走原 persona prompt。
- `RoleProfile` 增加 `inline_prompt`,`ProjectRoleProfile` 增加 `inline_prompt_override`,`ProjectProfile` 增加 `brief`,为后续配置内 prompt 文案和项目简报做准备。
- 本地 133 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests` 全绿。

**Round 36**(2026-05-04,Codex):
- 继续向后开发 Project Team / Appointment 验收面,新增项目办公室只读摘要能力。
- 新增 `/brief [project]`,基于本地 Project 配置、team appointments、lead role、最近 task snapshots 和 audit events 生成项目简报。
- 新增 `/risks [project]`,从最近失败/拒绝/中断/等待审批任务、高风险任务和风险审计事件生成风险列表。
- `/brief` 和 `/risks` 不调用 provider、不假装已有共享记忆层;当前是本地状态摘要 MVP。
- 新增单测覆盖 `/brief`、`/risks` 命令解析和 orchestrator 输出。
- 本地 134 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests` 全绿。

**Round 37**(2026-05-04,Codex):
- 人类开始验证,同时要求继续开发。
- 新增 `src/aico/core/project_docs.py`,提供受限 project document snippet 读取能力。
- `ProjectProfile` 新增 `blockers_doc` 和 `pitfalls_doc`;默认 AICO 项目和 `config/projects.example.json` 配置 `BLOCKERS.md` / `PITFALLS.md`。
- `/brief` 会读取 north star / status / journal 文档短片段;`/risks` 会读取 blockers / pitfalls 文档短片段。
- 文档读取限制为每个文件最多 4 行、单行最多 140 字符;文件不存在或读取失败时安静跳过,不会让 Telegram 命令失败。
- 新增 `tests/unit/test_project_docs.py`,覆盖文档片段读取和缺失文件跳过。
- 本地 136 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests` 全绿。

**Round 38**(2026-05-04,Codex):
- 人类继续 Telegram 验证,同时要求继续向后开发。
- 新增 `/daily [project]` 和 `/weekly [project]` 本地项目报告命令,分别按最近 24 小时 / 7 天窗口聚合团队、牵头 role、完成项、未完成项、风险和项目文档短片段。
- 报告命令复用 Project Team / Appointment 语义,仍只基于当前 AICO 进程内 task/audit 状态和受限文档片段,不调用 provider,不伪造长期共享记忆。
- 更新架构文档、daily ops、CHANGELOG 和 draw.io 图,把 `/daily` / `/weekly` 从设计态推进到已实现的项目状态面。
- 新增单测覆盖命令解析和 Orchestrator 日报/周报输出。
- 本地 137 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check` 全绿;draw.io XML 解析通过。

**Round 39**(2026-05-05,Codex):
- 人类真实使用 `/risks` 后指出输出混入 `write_files` 审批、`unknown adapter/persona` 等底层信号,不符合“项目风险”的直觉。
- 将 `/risks` 收窄为真正项目交付风险:失败/中断任务、破坏性任务和 blockers / pitfalls 文档片段;普通写文件审批、`approval_requested` 审计事件和未知 persona 路由噪音不再展示。
- 新增 `/blockers [project]`,专门展示当前卡住的工作和待决策项,包括等待审批、失败/拒绝/中断任务、未知 persona 等执行/系统问题和 blockers 文档片段。
- 新增回归测试覆盖人类遇到的 `write_files + unknown persona` 噪音场景,确认 `/risks` 不展示这些项,而 `/blockers` 能展示它们。
- 更新 `CHANGELOG.md`、`docs/human/daily-ops.md` 和 Project Team 设计文档。
- 本地 138 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check` 全绿;draw.io XML 解析通过。

**Round 40**(2026-05-05,Codex):
- 人类确认 `/risks` 新语义验收没问题,要求继续开发后续能力。
- 先把 Project/Team/Report 命令消息渲染拆到 `src/aico/core/project_messages.py`,让通用 `command_messages.py` 不再承载项目状态面输出。
- 将 `DirectoryCommandHandler` 的 report 发送辅助逻辑移出类体,使 `Orchestrator` 和 `DirectoryCommandHandler` 类体继续低于 500 行硬约束。
- 新增 `/next [project]`,基于本地 project/team/task 状态给出下一步建议动作:优先处理待审批、失败/中断/拒绝任务和路由/配置问题;没有卡点时建议把任务交给当前 lead role。
- `/next` 只支持 slash command,不把普通英文 `next` 当命令,避免误吞用户任务。
- 新增单测覆盖 `/next` 命令解析、待审批动作建议和普通 `next` 任务不被误吞。
- 更新 `CHANGELOG.md`、`docs/human/daily-ops.md`、Project Team 设计文档和两张 draw.io 图。
- 本地 139 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check` 全绿;draw.io XML 解析通过。

**Round 41**(2026-05-05,Codex):
- 人类授权若无重大决策则持续开发,并设置小时级 heartbeat 自动化催促当前线程继续推进。
- 新增 `/roles [project]`,展示当前项目 role 模板、默认权限和已任命 / 未任命状态,补齐 `/team` 和 `/who` 之外的岗位缺口视图。
- `/roles` 支持当前 active project,也支持 `/roles aico` 显式查看指定项目。
- 新增单测覆盖命令解析和 Orchestrator roles 输出,确认 implementer 已任命、tester 未任命。
- 拆分 `ProjectCommandHandler`,把项目办公室命令从通用 `DirectoryCommandHandler` 移出,保持单类 <500 行约束。
- 更新 `CHANGELOG.md`、`docs/human/daily-ops.md`、Project Team 设计文档和两张 draw.io 图。
- 本地 140 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check` 全绿;draw.io XML 解析通过。

**Round 42**(2026-05-05,Codex):
- Heartbeat 唤醒后继续推进,选择补齐老板任命闭环里的撤任能力,不触碰持久化配置写入。
- 新增 `/unappoint <role>`,可撤销当前 active project 某个 role 的进程内 appointment。
- `ProjectAssignmentDirectory` 新增 `remove_appointment_for_role()`,撤销当前 lead role 时会回退到剩余 appointment。
- 新增撤任确认消息,撤任后 `/roles` 会显示该 role 回到 `unappointed`, `/who <role>` 会提示未任命。
- 新增单测覆盖命令解析、目录撤任与默认 lead 回退、Orchestrator 撤任输出。
- 更新 `CHANGELOG.md`、`docs/human/daily-ops.md` 和 Project Team 设计文档。
- 本地 142 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check` 全绿;draw.io XML 解析通过。

**Round 43**(2026-05-05,Codex):
- Heartbeat 唤醒后继续推进,最高优先级真实 Telegram 验收仍需人类环境配合,因此选择一个不需拍板的项目办公室体验小修。
- `/project <project>` 继续用于进入指定项目;已有 active project 时,发送 `/project` 会重新展示当前项目办公室。
- 未进入任何项目时,`/project` 会提示 `No active project. Use /project <project> first.`。
- 新增单测覆盖未进入项目时的提示、进入项目后的 `/project` 复显,并确认不会派发 Adapter 任务。
- 更新 help 文案、`CHANGELOG.md`、`docs/human/daily-ops.md` 和 Project Team 设计文档。
- 本地 143 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check` 全绿;draw.io XML 解析通过。

**Round 44**(2026-05-05,Codex):
- Heartbeat 唤醒后继续推进;真实 Telegram 验收仍需人类重启服务和发命令,因此补齐本地 Project Team acceptance flow。
- 新增 `test_orchestrator_project_team_acceptance_flow`,串起 `/project aico`、`/project`、`/brief`、`/risks`、`/blockers`、`/next`、`/daily`、`/weekly`、`/roles`、`/team`、`/who implementer`、`/appoint claude as tester read_repo run_tests`、`/ask tester ...`、`/lead tester`、普通消息、`/unappoint tester`、`/roles`、`/who tester` 和撤任后的普通消息回退。
- 验收流确认状态面不派发 Adapter 任务,`/ask tester` 和 tester lead 普通消息带 tester assignment metadata,撤任后普通消息回退到 implementer。
- 更新 `CHANGELOG.md` 和 `docs/human/daily-ops.md`,加入本地验收流命令。
- 本地 144 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check` 全绿;draw.io XML 解析通过。

**Round 45**(2026-05-05,Codex):
- Heartbeat 唤醒后继续推进;真实 Telegram 验收仍需人类环境配合,本轮优先处理 `Orchestrator` 类体接近 500 行硬约束的问题。
- 将大段命令 if/elif 分发从 `Orchestrator._handle_command()` 移到模块级 `_handle_command()` 函数,类内只保留薄代理。
- 行为不变,仍复用现有 ProjectCommandHandler、DirectoryCommandHandler、审批、拒绝和 broadcast 路径。
- `Orchestrator` 实际类体从 491 行降到 422 行,为后续能力扩展留出空间。
- 本地 144 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check` 全绿;draw.io XML 解析通过。

**Round 46**(2026-05-05,Codex):
- 人类 Telegram 验收发现多次 `/appoint ... as tester ...` 后 `/team` 可能出现多个 tester,并追问 role 扩展、lead 可见性、Telegram 文案适配和 LLM 总结。
- 将 Project appointment 的唯一语义下沉到 `ProjectAssignmentDirectory`:同一 project + role 只保留一个 appointment;重复任命会覆盖,历史/配置中重复 role 初始化时按最后一个生效。
- `/team` 现在显示当前 lead,并在对应团队成员行标记 `[lead]`。
- 新增 P-013 记录同 role 多 appointment 的坑。
- 本轮没有把“LLM 生成 role 并确认新增”“IM 独立富文本渲染”“/brief 等顶部 LLM 总结”硬塞进现有命令;这三项需要下一轮按 provider 调用、确认流和 channel render contract 设计后实现。
- 本地 145 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check` 全绿。

**Round 47**(2026-05-05,Codex):
- 继续执行高优先级的 Role 创建确认流。
- 新增 `/role propose <诉求>`:当前项目 lead role 会收到只读 role proposal prompt,要求输出 JSON role 草案。
- 新增 `/role confirm` / `/role discard`:草案按当前 Telegram chat + sender 作用域暂存,确认后只加入当前进程内 project roles,不写配置文件。
- `ProjectAssignmentDirectory` 支持 runtime project role,`/roles` 能展示确认后的新 role 且默认未任命。
- 内部 role proposal task 增加 `aico.intent=role_proposal` 元数据,风险识别将其视为 read-only,避免“起草一个能跑测试的岗位”误触发 shell/write 审批。
- 本轮后 `Orchestrator` 类体已接近 500 行硬约束;继续做 IM render 或 LLM summary 前应先拆出 role proposal / task collection helper。
- 本地 targeted tests、`ruff check .`、`mypy src tests` 已通过;完整验证见本轮交接。

---

## 下一轮建议做什么(优先级从高到低)

> Agent 接手时,如果没有明确任务,从这里挑最高优先级。

1. **【高】重启后复测 Phase 5 真实协作 smoke test**:先用 `/tasks` / `/task <short_id>` 查看当前 stuck reviewer task,必要时 `/interrupt 1481a413` 收口旧进程,再重启 AICO。重启到 Round 60 后重新跑 `@reviewer ...`;用 `/task <parent_short_id>` / `/task <child_short_id>` 确认协作 parent-child trace 可见。若 Codex 仍无 stdout,预期 90 秒后返回 `adapter output idle timeout after 90s` 并恢复 `codex: idle`。
2. **【高】Project status render 最后一轮抽样**:`/brief` 已复验良好;可继续抽样 `/next`、`/daily`、`/weekly` 的 `Facts` 区域,确认 bullet、inline Markdown 和 heading 均不再裸露。
3. **【中】Codex bind 真实验收**:用已有 Codex provider session id 执行 `/bind codex <provider_session_id>`,随后发普通消息,确认日志中 `provider_session_mode=resume`。
4. **【中】Telegram Claude resume 与长文本复测**:继续确认 project-scoped appointment session 不破坏已有 resume 和长文本分片行为。
5. **【中】继续结构拆分**:如果下一轮要扩团队任命 / assignment 命令,优先拆 Project team/assignment handler,不要把新职责塞回 `ProjectCommandHandler`。
6. **【低】灵动岛 / Mac 顶部 UI 原型**:先不做,等 Project/Appointment 状态 API 稳定后再评估移动端或桌面入口。

---

## 当前卡点

参见 [`docs/journal/BLOCKERS.md`](docs/journal/BLOCKERS.md)。B-001、B-002 均已解决;当前没有阻塞 Phase 5 的活跃卡点。

---

## 当前已知风险

| 风险 | 影响 | 当前应对 |
|---|---|---|
| 各 AI CLI 接口不稳定(Claude Code/Codex 都在快速演进) | Adapter 频繁返工 | 协议层做厚,把"易变"封装在 Adapter 内部 |
| 个人项目长期维护动力衰减 | 项目烂尾 | Dogfooding 强制——自己用,自己优化 |
| 范围蔓延(看到什么酷功能都想加) | 进度失控 | 北极星 + Phase 严格门禁 |

---

## 元信息

- **项目仓库**:https://github.com/MarcelLeon/ai-company-os
- **主要维护者**:Wang
- **协作 AI**:Claude(本轮)、未来不限
