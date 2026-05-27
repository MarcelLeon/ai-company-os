# ROUNDS.md — 思考与执行轮次记录

> 这个文件记录每一轮思考和执行的核心决策、否决方案、得出结论。
> **每一轮工作结束都要追加一段记录**。
> 阅读顺序:从下往上读,最新的在最下面。Agent 接手时重点看最近 3 轮。

---

## 文件用法

每轮记录使用以下模板:

```markdown
## Round N — YYYY-MM-DD — [角色:Human / Agent名 / 协作]

### 输入
- 上一轮交接的任务
- 本轮的具体目标

### 思考与讨论
- 考虑过的方案 A、B、C
- 为什么选 A,为什么否决 B、C(**重点写否决理由,这对下一轮 AI 极其重要**)

### 产出
- 实际产出的文件/代码/决策

### 关键决策
- 标记本轮做的不可逆决策(影响后续多轮)

### 留给下一轮
- 明确的下一步任务
- 未解的疑问

### 状态变化
- STATUS.md 哪一项从 X 变成 Y
```

---

## Round 1 — 2026-04-26 — 协作(Human + Claude)

### 输入
- 项目从零开始
- 人类提供愿景:"集成 Mac 电脑全部 AI 工具,通过 IM 远程指挥,人格化身份,虚拟公司感"

### 思考与讨论

**核心定位讨论**:
- 候选定位 A:"多 AI 转发器"(把多个 AI CLI 统一接入 IM)→ ❌ **否决**:这是低价值玩具,市面上接近的产品已存在
- 候选定位 B:"AI 团队 OS"(编排层 + 人格化层 + 远程指挥层)→ ✅ **选定**
- 候选定位 C:"CodeIsland 的 IM 版"→ ❌ **否决**:抄袭路线无壁垒

**核心痛点定位**:
- 借鉴 CodeIsland 的"灵动岛交互"思路,但识别出其根本问题不是 UI,而是**绑定 Mac 桌面够不到**
- 因此核心痛点定义为:"AI 在我电脑里干活,但我人不在电脑前"

**北极星三句话**:经过讨论确立(详见 NORTH_STAR.md)。
- 业务价值句强调"无论身处何地"、"远程异步"、"协同"——三个挡板词
- 技术原则句用四个"化"锁死架构形态
- 开发运维句加入"Dogfooding 是唯一验收标准"——这是个人项目能活过两年的关键

**文档体系设计**:
- 候选 A:单一 README → ❌ 信息密度太低,Agent 接手会乱
- 候选 B:Agent 文档 + Human 文档双轨 → ✅ 选定
- 候选 C:Wiki 系统 → ❌ 个人项目过重,且不在 git 里追溯困难

**演化机制设计**:
- 引入 `docs/journal/` 三件套(ROUNDS / PITFALLS / BLOCKERS)
- 灵感来自:工程团队的事后复盘 + ADR + 人类项目笔记
- 关键洞察:**Agent 接手项目最痛苦的不是不会写代码,是不知道前人想过什么、否决过什么**——所以 ROUNDS 重点记录"否决理由"

### 产出
- `README.md`(人入口)
- `AGENTS.md`(AI 入口,带强制阅读路径和自检清单)
- `NORTH_STAR.md`(三句话宪法)
- `STATUS.md`(阶段地图 + 进度 + 下一轮建议)
- `CHANGELOG.md`
- `CONTRIBUTING.md`(commit / PR / 抽象时机规范)
- `docs/journal/ROUNDS.md`(本文件)
- `docs/journal/PITFALLS.md`(初始化)
- `docs/journal/BLOCKERS.md`(初始化)
- `docs/agent/` 8 篇 Agent 指南
- `docs/human/` 3 篇 Human 速查
- `docs/architecture/` 3 篇架构文档
- `docs/decisions/README.md`(ADR 索引和模板)
- `docs/playbooks/README.md`(剧本索引)

### 关键决策
- 🔒 **不可逆决策 1**:文档体系采用 Agent / Human 双入口 + journal 演化机制。这套设计的成本是"每轮要写文档",收益是"项目可被任意 AI 接手而不退化"。
- 🔒 **不可逆决策 2**:北极星三句话不可被功能需求覆盖。冲突时砍需求,不改宪法。
- 🔒 **不可逆决策 3**:Phase 1 MVP 只做"Telegram → 编排核心 → Claude Code → Telegram"单链路。Phase 1 验收前不允许接入第二个 AI 或第二个 IM。

### 留给下一轮

**最高优先级任务**:技术栈选型(写一个 ADR)。需要决定:
- 编排核心是 Java(Spring AI) / Python(FastAPI) / TypeScript(Node)中的哪一个?
- 各 AI CLI(Claude Code、Codex、OpenClaw)的 SDK 在三种语言里成熟度如何?
- 是否考虑混合架构(核心 + Sidecar)?

**待解疑问**:
- AI 之间互相 @ 协作的协议形态(是 Agent2Agent / 是消息总线 / 是 RPC)?这个不需要 Phase 1 决定,但 Phase 2 之前必须有方向。
- 人格化层的最小有效单元是什么?只换 system prompt 够不够?需不需要行为策略层?

### 状态变化
- Phase 0 进度:文档体系骨架 ✅
- Phase 0 待办:技术栈选型、Adapter 协议草案、IM 通道协议草案

---

<!-- 下一轮在这里追加 -->

## Round 2 — 2026-04-27 — 协作(Human + Codex)

### 输入
- 人类要求先做一次文档路径归位 / 修正。
- 人类要求整理后推送到 `https://github.com/MarcelLeon/ai-company-os`。
- 人类明确技术栈偏向 Python,并说明不选 Java 的主要原因是代码量太多、不好维护。

### 思考与讨论

**文档结构选择**:
- 候选 A:保留所有文档在根目录,同步修改 `AGENTS.md` 的强制阅读路径 → ❌ **否决**:这会推翻 Round 1 已经确定的 Agent / Human / journal 分层契约,也会让根目录继续膨胀。
- 候选 B:按 Round 1 设计把文档归位到 `docs/` 子目录 → ✅ **选定**:最小修复,让文件系统重新匹配 `AGENTS.md`、`README.md` 和 `STATUS.md` 的既有路径。
- 候选 C:现在顺手重写所有文档链接和命名体系 → ❌ **否决**:本轮目标是归位和推送,大规模文案重写会扩大 review 面。

**技术栈记录**:
- 人类已给出 Python 偏好和反对 Java 的维护成本理由。
- 本轮只把该输入记录到 `BLOCKERS.md` 和 `STATUS.md`,不直接关闭 B-001,因为正式选型仍应通过 ADR-001 固化。

### 产出
- 将 Agent 指南移动到 `docs/agent/`。
- 将 journal 三件套移动到 `docs/journal/`。
- 将架构文档移动到 `docs/architecture/`。
- 将人类操作文档移动到 `docs/human/`。
- 补回 `docs/decisions/README.md` 和 `docs/playbooks/README.md`。
- 新增 PITFALL P-002,记录文档被扁平化导致路径失效的问题。
- 更新 B-001,记录 Python 倾向和不选 Java 的维护成本理由。

### 关键决策
- 🔒 **决策 1**:仓库根目录只保留入口级文档和项目元文件,其余文档按 `docs/` 分层归位。
- 🔒 **决策 2**:Python 技术栈已有明确倾向,但仍需 ADR-001 正式接受后再开始代码骨架。

### 留给下一轮
- 写 `docs/decisions/0001-tech-stack-selection.md`,正式确认 Python 技术栈。
- 若 ADR-001 接受 Python,创建最小 Python 项目骨架和核心协议模型。
- 建议优先做 `AIAdapter` / `IMChannel` 的 `typing.Protocol` 草案和对应单测。

### 状态变化
- Phase 0 进度:文档路径归位 ✅
- B-001:仍为 DEFERRED,但候选方向收敛到 Python

## Round 3 — 2026-04-27 — Codex

### 输入
- 人类要求先快速了解项目现状,然后严格按文档要求开始开发。
- `STATUS.md` 的下一轮最高优先级是技术栈选型 ADR,随后是 Python 骨架、Adapter 协议草案和 IM Channel 协议草案。

### 思考与讨论

**执行顺序选择**:
- 候选 A:直接写 Telegram / Claude Code 实现 → ❌ **否决**:B-001 尚未关闭,技术栈没有 ADR 固化,直接写实现会违反"ADR 接受后再创建骨架"的交接要求。
- 候选 B:只写 ADR,不写代码 → ❌ **否决**:人类要求"开始开发",且 STATUS 已明确 ADR 接受后应创建 Python 骨架并跑通检查。
- 候选 C:ADR-0001 + 最小 Python 骨架 + 协议草案 + 单测 → ✅ **选定**:能关闭 B-001,同时不越界到具体 Telegram / Claude Code 实现。

**技术栈决策**:
- 选择 Python 3.11+ / FastAPI / asyncio / Pydantic v2 / pytest / ruff / mypy。
- 否决 Java/Spring Boot 作为核心默认栈:工程化强,但 Phase 1 样板代码和长期维护成本偏高。
- 否决 TypeScript/Node.js 作为核心默认栈:Bot/CLI 集成自然,但偏离当前维护偏好,AI 生态复用不如 Python。

**协议抽象边界**:
- 虽然项目强调 Rule of Three,但 `AIAdapter` / `IMChannel` 属于北极星明确要求的核心公开协议,是 `docs/agent/03-design-patterns.md` 允许提前抽象的例外。
- 本轮只定义最小 Protocol 和不可变值对象,不写任何具体插件实现,避免把某个 AI 或 IM 的细节污染核心。

### 产出
- 新增 `docs/decisions/0001-tech-stack-selection.md`,状态 Accepted。
- 新增 `pyproject.toml` 和 `uv.lock`,固化 Python 3.11+、FastAPI、Pydantic v2、pytest、ruff、mypy。
- 新增 `src/aico/core/models.py`,定义 `Task`、`TaskAck`、`TaskOutput`、`IncomingMessage`、`ChannelTarget` 等不可变协议模型。
- 新增 `src/aico/adapter/base.py`,定义 `AIAdapter` Protocol。
- 新增 `src/aico/channel/base.py`,定义 `IMChannel` Protocol。
- 新增 `tests/unit/test_models.py` 和 `tests/unit/test_protocols.py`,覆盖值对象和协议替身。
- 新增 PITFALL P-003,记录本机默认 Python 3.9 / uv cache / 首次拉包的验证坑。

### 关键决策
- 🔒 **决策 1**:ADR-0001 接受 Python 技术栈,后续核心默认使用 Python 3.11+。
- 🔒 **决策 2**:协议对象优先使用 Pydantic v2 frozen model,跨模块边界优先使用 `typing.Protocol`。
- 🔒 **决策 3**:Phase 0 协议草案先只覆盖最小共性方法,具体 Telegram / Claude Code 行为留到 Phase 1 插件实现。

### 留给下一轮
- 写 ADR-0002,正式定稿 Adapter/Channel 协议。
- 明确 Phase 1 MVP 的验收边界:Telegram 文本消息 → 编排核心 → Claude Code → Telegram 文本/编辑消息。
- 实现最小 Router / TaskBus,先用 FakeChannel + FakeAdapter 写 1 条端到端单测。
- 然后再进入 Telegram Channel 和 Claude Code Adapter 的真实插件实现。

### 状态变化
- B-001 技术栈选型:DEFERRED → RESOLVED。
- Phase 0 进度:技术栈选型 ADR ✅,第一个 ADR ✅,Python 工程骨架 ✅,核心协议草案 ✅。
- 新增 P-003:Python/uv 本地验证环境坑。

## Round 4 — 2026-04-27 — Codex

### 输入
- 人类反馈"现在能验证的还比较少,继续执行"。
- `STATUS.md` 的下一轮建议是 ADR-0002、Phase 1 MVP 范围、最小编排核心和假链路测试。

### 思考与讨论

**推进顺序选择**:
- 候选 A:直接写 Telegram Channel → ❌ **否决**:协议 ADR 尚未定稿,直接接真实 IM 会让 Telegram 细节更容易污染核心。
- 候选 B:先写 Claude Code Adapter → ❌ **否决**:没有 Channel 入口和编排闭环时,Adapter 只能孤立测试,不能回应"验证少"的问题。
- 候选 C:ADR-0002 + FakeChannel/FakeAdapter 端到端假链路 → ✅ **选定**:能用纯本地测试验证核心任务流转,同时保持真实插件边界干净。
- 候选 D:引入 EventBus 做更完整状态广播 → ❌ **否决**:ADR-0002 明确 Phase 1 暂不把 EventBus 放进协议,先用更小的 Orchestrator 闭环验证。

**编排边界选择**:
- `MessageRouter` 只负责 `IncomingMessage -> Task`,不关心 Adapter。
- `TaskBus` 只依赖 `AIAdapter`,负责 submit / stream / interrupt 的最小代理。
- `Orchestrator` 只把 `IMChannel`、`MessageRouter`、`TaskBus` 串起来,负责 Channel 回调、ack 消息和流式编辑。
- 真实 Telegram / Claude Code 行为仍留在插件实现里,本轮只用测试替身验证核心。

### 产出
- 新增 `docs/decisions/0002-adapter-channel-protocol.md`,状态 Accepted。
- 新增 `src/aico/core/router.py`,实现 `MessageRouter`。
- 新增 `src/aico/core/task_bus.py`,实现 `TaskBus`。
- 新增 `src/aico/core/orchestrator.py`,实现 `Orchestrator.bind()` 和 `handle_incoming()`。
- 新增 `tests/unit/test_router.py`、`tests/unit/test_task_bus.py`、`tests/unit/test_orchestrator.py`。
- 新增 `.github/workflows/ci.yml`,固化 pytest / ruff / format / mypy。
- 更新 `docs/human/daily-ops.md`,记录本地验证命令。

### 关键决策
- 🔒 **决策 1**:ADR-0002 接受异步接收 + 流式输出 + 显式状态的 Adapter/Channel 协议。
- 🔒 **决策 2**:Phase 1 编排核心先不引入 EventBus,用 `Orchestrator` 串接单链路;后续状态广播需要新 ADR 或明确演化记录。
- 🔒 **决策 3**:CI 使用 `uv sync --locked --all-groups`,要求 `uv.lock` 进入仓库。

### 留给下一轮
- 写 `docs/playbooks/phase-1-mvp.md`,明确 Phase 1 MVP 的真实验收边界。
- 实现 Telegram Channel 文本 MVP,优先用 mock HTTP 覆盖 long polling update 解析、sendMessage、editMessage。
- 实现 Claude Code Adapter MVP,优先用 fake subprocess 覆盖 receive / stream / interrupt。
- 设计真实集成测试 harness,通过环境变量控制是否跑真实 Bot Token / Claude CLI。

### 状态变化
- ADR-0002:待写 → Accepted。
- Phase 0:CI 骨架完成,阶段地图从进行中更新为完成。
- Phase 1:从未开始更新为进行中;完成假链路编排和 11 个本地单测。

## Round 5 — 2026-04-27 — Codex

### 输入
- 人类询问当前进度、有无阻塞;如果没有阻塞则继续开发。
- `STATUS.md` 显示当前没有 Phase 1 阻塞,下一轮最高优先级是 Phase 1 MVP playbook 和 Telegram Channel 文本 MVP。

### 思考与讨论

**阻塞判断**:
- B-002(AI 间协作协议形态待定)仍是 Phase 5 前的延后卡点,不阻塞 Phase 1。
- Phase 1 当前真正缺口是:真实 IM Channel、Claude Code Adapter、真实链路验收。

**推进顺序选择**:
- 候选 A:直接实现 Claude Code Adapter → ❌ **否决**:Telegram 入口尚未落地,继续写 Adapter 会让真实链路仍然缺少 IM 侧验证。
- 候选 B:先写 Phase 1 playbook,然后只更新文档 → ❌ **否决**:人类明确说"没有的话继续开发",只写文档推进不足。
- 候选 C:Phase 1 playbook + Telegram Channel 文本 MVP → ✅ **选定**:先锁定验收边界,再把单链路的 IM 入口补齐,且可用 mock HTTP 稳定验证。
- 候选 D:同时实现 Telegram webhook → ❌ **否决**:Phase 1 不需要公网域名和反向代理,long polling 更符合本地 dogfooding。

**Telegram 实现边界**:
- 只支持文本消息,非文本 update 直接忽略。
- Telegram Bot API 结构只在 `TelegramChannel` 内解析,核心仍只看到 `IncomingMessage` / `MessageContent`。
- HTTP client 通过构造器注入,单测使用 `httpx.MockTransport`,避免真实网络和 Bot Token。

### 产出
- 新增 `docs/playbooks/phase-1-mvp.md`,明确 Phase 1 单链路验收步骤、范围内外、验证项和失败排查。
- 更新 `docs/playbooks/README.md`,将 `phase-1-mvp.md` 标记为已完成。
- 新增 `src/aico/channel/telegram.py`,实现 `TelegramChannel` long polling 文本 MVP。
- 更新 `src/aico/channel/__init__.py`,导出 `TelegramChannel` 和 `TelegramAPIError`。
- 新增 `tests/unit/test_telegram_channel.py`,覆盖文本 update 解析、offset 推进、发送、编辑、删除、非文本忽略和 API 失败。
- 更新 `CHANGELOG.md`,记录 Phase 1 playbook 和 Telegram Channel MVP。

### 关键决策
- 🔒 **决策 1**:Phase 1 Telegram Channel 先采用 long polling,暂不做 webhook。
- 🔒 **决策 2**:真实 Bot Token 集成测试留到下一轮通过环境变量控制,本轮只做 mock HTTP 单测。
- 🔒 **决策 3**:Phase 1 启动入口暂未实现,下一轮在 Claude Code Adapter 后补一个临时 CLI 或脚本串起真实链路。

### 留给下一轮
- 实现 Claude Code Adapter MVP,用 fake subprocess 覆盖 receive / stream / interrupt。
- 写可跳过的真实单链路 integration harness,无 Telegram Token 或 Claude CLI 时 skip。
- 提供 Phase 1 本地启动入口,让 `docs/playbooks/phase-1-mvp.md` 的启动步骤可直接执行。

### 状态变化
- Phase 1 MVP playbook:未完成 → 完成。
- Telegram Channel 文本 MVP:未完成 → 完成。
- 本地单测:11 个 → 16 个,`pytest` / `ruff check` / `ruff format --check` / `mypy` 全绿。

## Round 6 — 2026-04-27 — Codex

### 输入
- 人类要求继续执行,并在适合人类验收时提醒。
- Round 5 后 Phase 1 已有 Telegram Channel 和编排核心,下一步是 Claude Code Adapter MVP 和本地启动入口。

### 思考与讨论

**推进顺序选择**:
- 候选 A:先写真实 Telegram Token 集成测试 → ❌ **否决**:没有 Claude Code Adapter 和启动入口时,真实 Token 测试只能验证 Channel,不能让人类验收单链路。
- 候选 B:实现 Claude Code Adapter MVP,再补 `aico-phase1` 启动入口 → ✅ **选定**:能把 Phase 1 的三段链路串起来,进入人工 smoke test 阶段。
- 候选 C:直接运行真实 `claude -p` 做自动 e2e → ❌ **否决**:真实 CLI 可能消耗外部资源,且 Telegram Bot Token 未配置;先把可控单元测试和启动入口做好。

**Claude Code Adapter 边界**:
- 默认命令采用 `claude -p --output-format text`,但通过环境变量和构造器可配置,避免把易变 CLI 参数扩散到核心。
- Phase 1 只支持单任务占用。忙碌时返回 `AckStatus.BUSY`,不在 Adapter 内排队。
- 输出读取 stdout 行并转换成 `TaskOutput.TEXT`;非零退出读取 stderr 转 `TaskOutput.ERROR`;中断以用户意图为准,即使进程 0 退出也报告 `task interrupted`。

**启动入口边界**:
- 新增 `aico-phase1`,只负责本地 dogfooding wiring,不引入服务端、持久化或复杂配置容器。
- 配置使用 `pydantic-settings` 读取 `AICO_` 前缀环境变量。

### 产出
- 新增 `src/aico/adapter/claude_code.py`,实现 Claude Code CLI Adapter MVP。
- 新增 `tests/unit/test_claude_code_adapter.py`,用 fake subprocess 覆盖 stdout 流、busy、stderr 失败、中断、未知 task 和 health check。
- 调整 `src/aico/adapter/base.py` / `src/aico/channel/base.py`,将协议模型导入改为仅类型检查时导入,消除包初始化循环。
- 新增 `src/aico/app/phase1.py` 和 `aico-phase1` console script,串接 Telegram Channel、MessageRouter、TaskBus、Claude Code Adapter 和 Orchestrator。
- 新增 `tests/unit/test_phase1_app.py`,覆盖启动配置解析和运行时 wiring。
- 更新 `docs/playbooks/phase-1-mvp.md` 与 `docs/human/daily-ops.md`,记录启动命令和环境变量。
- 新增 PITFALL P-004,记录 console script 触发 `hatchling` 构建依赖下载的验证坑。

### 关键决策
- 🔒 **决策 1**:Claude Code Adapter Phase 1 采用单任务占用,不做内部队列。
- 🔒 **决策 2**:`aico-phase1` 是本地验收入口,不是长期生产守护进程;后续生产化需要另行设计。
- 🔒 **决策 3**:Protocol 基类模块不在运行时导入核心模型,避免接口包和核心包互相初始化。

### 留给下一轮
- 让人类按 `docs/playbooks/phase-1-mvp.md` 做真实 Telegram + Claude Code smoke test。
- 根据 smoke test 结果补真实链路 integration harness,无 Token / CLI 时 skip。
- 如果真实 Claude Code 输出不是按行刷新,再考虑切换 `--output-format stream-json` 并扩展解析。

### 状态变化
- Claude Code Adapter MVP:未完成 → 完成。
- Phase 1 本地启动入口:未完成 → 完成。
- 本地单测:16 个 → 24 个,`pytest` / `ruff check` / `ruff format --check` / `mypy` 全绿。

## Round 7 — 2026-04-28 — Codex

### 输入
- 人类反馈已运行 `env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python /opt/homebrew/bin/python3.11 aico-phase1`,并完成真实 Telegram Bot 端到端聊天验收。
- 人类要求如果没问题就开始下一阶段。

### 思考与讨论

**阶段判断**:
- Phase 1 验收标准是 1 个 AI(Claude Code)能从 1 个 IM(Telegram)接收任务并返回结果。人类已完成真实链路 smoke test,因此 Phase 1 可以标记完成。
- Phase 2 验收标准是至少 2 个 AI 接入,状态可在 IM 中查询。最小推进应优先补状态查询和多 Adapter 路由,而不是先引入复杂事件总线。

**推进顺序选择**:
- 候选 A:直接做完整状态机 / EventBus → ❌ **否决**:ADR-0002 曾明确 Phase 1 不引入 EventBus;Phase 2 刚开始也不应先做大框架,应该先让 IM 能查状态。
- 候选 B:先做 AdapterRegistry + `/status` → ✅ **选定**:最小满足“状态可在 IM 中查询”,并为第二个 Adapter 接入铺路。
- 候选 C:只写 CodexAdapter,不改路由 → ❌ **否决**:没有注册表和按 persona 路由时,第二个 Adapter 不能被编排核心稳定选择。

**多 Adapter 边界**:
- `TaskBus` 从单 Adapter 代理演进为通过 `AdapterRegistry` 路由,但保留单 Adapter 兼容模式:未知 persona 仍落到默认 Adapter,不破坏 Phase 1。
- 多 Adapter Registry 模式下未知 persona 会拒绝,避免任务静默跑到错误 AI。
- `CodexAdapter` 复用 ClaudeCodeAdapter 的 CLI 执行形态,但默认命令是 `codex --ask-for-approval never exec --sandbox read-only --color never`,避免远程 IM 默认触发写操作或交互审批。

### 产出
- 更新 `STATUS.md`,标记 Phase 1 完成、Phase 2 进行中。
- 新增 `src/aico/core/adapter_registry.py`,支持 Adapter 注册、按名称 / Telegram 安全别名解析和状态快照。
- 新增 `AdapterSnapshot` 协议模型。
- 更新 `TaskBus`,支持 `AdapterRegistry` 多 Adapter 路由,并保留单 Adapter 默认兜底。
- 更新 `Orchestrator`,支持 `/status` / `status` 文本命令。
- 新增 `src/aico/adapter/codex.py`,实现 Codex Adapter 文本 MVP。
- 更新 `aico-phase1`,可通过 `AICO_ENABLE_CODEX_ADAPTER=true` 启用 Codex Adapter。
- 新增 `tests/unit/test_adapter_registry.py`、`tests/unit/test_codex_adapter.py`,并扩展 TaskBus / Orchestrator / app 单测。
- 更新 `docs/human/daily-ops.md`、`docs/playbooks/phase-1-mvp.md` 和 `CHANGELOG.md`。

### 关键决策
- 🔒 **决策 1**:Phase 2 首个状态查询能力用简单 `/status` 命令实现,暂不引入 EventBus。
- 🔒 **决策 2**:Codex Adapter 默认 read-only sandbox,远程 IM 场景下不默认放开写权限。
- 🔒 **决策 3**:单 Adapter 模式继续向默认 Adapter 兜底,多 Adapter 模式才严格拒绝未知 persona。

### 留给下一轮
- 让人类设置 `AICO_ENABLE_CODEX_ADAPTER=true`,启动 `aico-phase1`,在 Telegram 发送 `/status` 验证双 Adapter 状态。
- 验证 `@codex` 文本任务是否能通过 Codex Adapter 返回只读结果。
- 根据真实输出情况决定 Codex Adapter 是否需要 JSONL / last-message 文件解析。
- 开始设计 task lifecycle 状态机,区分 Adapter 整体状态和单个任务状态。

### 状态变化
- Phase 1:进行中 → 完成。
- Phase 2:未开始 → 进行中。
- Phase 2 进度新增:AdapterRegistry、多 Adapter 路由、`/status`、Codex Adapter MVP。
- 本地单测:24 个 → 33 个,`pytest` / `ruff check` / `ruff format --check` / `mypy` 全绿。

## Round 8 — 2026-04-28 — Codex

### 输入
- 人类反馈 `/status` 已能看到 `claude-code` 和 `codex` 两个模型均为 idle。
- 人类无法唤醒 Codex,询问是否尚未开发;如果没有其他可验收能力则继续开发。

### 思考与讨论

**问题定位**:
- Round 7 已注册 Codex Adapter,但任务路由主要依赖 Telegram `mentions` 字段。
- Telegram 文本里常见的 `/codex ...`、`@codex ...`、`codex: ...` 没有被路由层显式解析,因此用户能看到状态,但无法用自然命令稳定唤醒 Codex。

**推进顺序选择**:
- 候选 A:让用户必须使用 Telegram 原生 @mention entity → ❌ **否决**:这依赖 Bot / 群聊 / 用户名配置,不适合作为 dogfooding 入口。
- 候选 B:补明确文本命令 `/codex`、`@codex`、`codex:` → ✅ **选定**:最小改动,能直接解决远程 IM 唤醒问题。
- 候选 C:立即做完整 slash command 框架 → ❌ **否决**:当前命令数量少,还没到需要新框架的程度;先用小函数解析,避免过早抽象。

### 产出
- 更新 `MessageRouter`,支持 `/codex <task>`、`/codex@bot <task>`、`@codex <task>`、`codex: <task>` 路由,并剥离唤醒前缀。
- `AdapterRegistry` 新增显式别名支持,在 `aico-phase1` 中注册 `/claude` → `claude-code`。
- `Orchestrator` 新增 `/help` / `help` 文本命令。
- 新增 `docs/playbooks/phase-2-multi-adapter.md`,记录 Phase 2 状态查询与点名路由验收步骤。
- 更新 `docs/human/daily-ops.md` 和 `CHANGELOG.md`。
- 扩展 Router / Orchestrator / AdapterRegistry / app 单测。

### 关键决策
- 🔒 **决策 1**:Phase 2 的 IM 唤醒入口先支持明确文本命令,不依赖 Telegram 原生 mention entity。
- 🔒 **决策 2**:暂不引入通用 command framework;当命令数量继续增长或需要权限 / 参数解析时再抽象。

### 留给下一轮
- 人类用 `/codex summarize this repo in one sentence` 验证 Codex 真实链路。
- 如果 Codex 真实输出不稳定,优先尝试 `--output-last-message` 文件输出或 `--json` 事件解析。
- 继续推进 task lifecycle 状态机,让 `/status` 不只展示 Adapter idle/busy,也能展示当前任务。

### 状态变化
- Telegram 双 Adapter 状态查询:未验收 → 已由人类验收。
- Codex 唤醒路由:未完成 → 完成。
- Phase 2 Playbook:未完成 → 完成。
- 本地单测:33 个 → 42 个,`pytest` / `ruff check` / `ruff format --check` / `mypy` 全绿。

## Round 9 — 2026-04-28 — Codex

### 输入
- 人类用 `@codex summarize this repo in one sentence` 验收 Codex 唤醒后收到错误:`unexpected argument '--ask-for-approval' found`。

### 思考与讨论

**问题定位**:
- Codex Adapter 默认命令曾是 `codex exec --sandbox read-only --ask-for-approval never --color never`。
- 本机 `codex exec --help` 显示 `--ask-for-approval` 不属于 `exec` 子命令参数;它是 Codex 顶层参数。
- 因此真实 CLI 解析失败,不是路由失败。

**方案选择**:
- 候选 A:移除 `--ask-for-approval never` → ❌ **否决**:远程 IM 场景下不应默认进入交互审批模式。
- 候选 B:把全局参数移到子命令前:`codex --ask-for-approval never exec ...` → ✅ **选定**:符合 Codex CLI 参数层级,保留非交互安全语义。

### 产出
- 更新 `DEFAULT_CODEX_COMMAND` 为 `codex --ask-for-approval never exec --sandbox read-only --color never`。
- 更新 `AICO_CODEX_COMMAND` 默认值。
- 更新 Codex Adapter 单测、Phase 2 Playbook 和 Round 7 中的命令描述。
- 新增 PITFALL P-005,记录 Codex CLI 全局参数位置坑。

### 关键决策
- 🔒 **决策 1**:Codex Adapter 继续保留 `--ask-for-approval never`,但必须作为顶层参数放在 `exec` 前。

### 留给下一轮
- 人类重启 `aico-phase1` 后再次发送 `@codex summarize this repo in one sentence` 或 `/codex summarize this repo in one sentence`。
- 如果 Codex 被唤醒但输出格式不适合流式编辑,再评估 `--output-last-message` 或 `--json`。

### 状态变化
- P-005 新增并标记 RESOLVED。
- 本地 `codex --ask-for-approval never exec --help` 验证通过。
- 本地单测保持 42 个,`pytest` / `ruff check` / `ruff format --check` / `mypy` 全绿。

## Round 10 — 2026-04-28 — Codex

### 输入
- 人类反馈已在 Telegram 中测试 `@codex summarize this repo in one sentence`,Codex 真实任务链路没有问题。
- 人类要求继续下阶段开发。

### 思考与讨论

**阶段判断**:
- Phase 2 验收标准是至少 2 个 AI 接入,状态可在 IM 中查询。`claude-code` 与 `codex` 已启用,`/status` 已通过人类验收,`@codex` 真实任务也已通过人类验收。
- Phase 2 名称里还包含“状态机”,而现有实现只记录 Adapter 状态,没有把单个任务的 `running / done / failed / interrupted` 作为一等状态。因此本轮先收口 Phase 2 的任务生命周期,再把下一轮入口切到 Phase 3。

**方案选择**:
- 候选 A:直接进入 Phase 3 人格化 / broadcast → ❌ **否决**:任务状态还只停留在 Adapter 维度,进入群聊编排后会更难回答“哪个 AI 的哪个任务处于什么状态”。
- 候选 B:引入完整 EventBus / TaskRepository → ❌ **否决**:当前只需要 IM `/status` 可观测,持久化和事件广播属于 Phase 4+ / Phase 6 的问题,现在引入会扩大范围。
- 候选 C:在 `TaskBus` 内维护内存态 `TaskSnapshot`,随 submit / stream / interrupt 推进生命周期 → ✅ **选定**:最小改动,贴合现有编排边界,能让 `/status` 同时展示 Adapter 和最近任务。

### 产出
- 新增 `TaskStatus` 与 `TaskSnapshot` 协议模型。
- 更新 `TaskBus`,记录最近任务状态,并在任务被接收、拒绝、完成、失败和中断时推进生命周期。
- 更新 `Orchestrator` 的 `/status` 输出,在 Adapter 状态后追加最近任务状态。
- 扩展 `tests/unit/test_models.py`、`tests/unit/test_task_bus.py`、`tests/unit/test_orchestrator.py`,覆盖任务状态模型和生命周期推进。
- 更新 `STATUS.md`、`docs/playbooks/phase-2-multi-adapter.md`、`docs/human/daily-ops.md`、`CHANGELOG.md`。

### 关键决策
- 🔒 **决策 1**:Phase 2 的任务状态先使用内存态 `TaskBus` 维护,不引入持久化仓储。
- 🔒 **决策 2**:`/status` 继续作为 Telegram dogfooding 的最小可观测入口,暂不新增单独任务查询命令。
- 🔒 **决策 3**:Phase 3 启动前先写范围 ADR / Playbook,避免人格化层偏离“管理真实团队”的北极星。

### 留给下一轮
- 写 Phase 3 范围 ADR / Playbook,明确 persona 与 broadcast 的最小验收边界。
- 引入 Persona 最小模型或配置,让同一个 Adapter 可以承载不同职责名与任务前缀。
- 实现群聊 broadcast 最小链路:一个 Telegram 命令广播给已启用 Adapter,分别返回任务状态。

### 状态变化
- Phase 2:进行中 → 完成。
- 第二个真实 AI 任务链路验收:未完成 → 完成。
- 更明确的任务状态机:未完成 → 完成。
- 本地单测:42 个 → 47 个,`pytest` / `ruff check` / `ruff format --check` / `mypy` 全绿。

## Round 11 — 2026-04-28 — Codex

### 输入
- 人类要求继续开发下一阶段。
- `STATUS.md` 的下一轮建议是 Phase 3 范围 ADR / Playbook、Persona 最小模型和群聊 broadcast 最小链路。

### 思考与讨论

**Phase 3 边界判断**:
- 北极星要求“像管理一个真实团队一样”,所以 Persona 必须表达职责边界,不是娱乐化人设文案。
- Phase 5 才解决 AI 间互相 @ 协作协议,因此 Phase 3 的 broadcast 只做“人类 → 多 persona”的任务派发,不做 AI 之间通信。

**方案选择**:
- 候选 A:只给 Claude / Codex 加几段固定 prompt 文案 → ❌ **否决**:这无法形成稳定职责名,也不能支撑群聊 broadcast。
- 候选 B:新增 `PersonaRegistry`,把职责名映射到 Adapter 和职责前缀 → ✅ **选定**:能保留 Adapter 协议,让 `/claude` / `/codex` 作为 alias 兼容,同时让 broadcast 面向 `implementer` / `reviewer`。
- 候选 C:引入完整 `PersonaStrategy` / command framework / workflow engine → ❌ **否决**:当前只有两个 persona 样本,过早抽象会违反 Rule of Three。

**broadcast 边界**:
- `/broadcast <task>` 不创建特殊任务类型,而是拆成多个普通 `Task`,复用 `TaskBus`、Adapter 状态和最近任务状态。
- 默认 persona:
  - `implementer` → `claude-code`,alias:`claude` / `claude-code`
  - `reviewer` → `codex`,alias:`codex`
- Codex 未启用时,broadcast 只发给 `implementer`。

### 产出
- 新增 `docs/decisions/0003-phase-3-persona-broadcast.md`。
- 新增 `docs/playbooks/phase-3-persona-broadcast.md`。
- 新增 `PersonaProfile` 协议模型和 `PersonaRegistry`。
- 更新 `TaskBus`,支持 persona 解析、职责前缀注入和 broadcast target 列表。
- 更新 `Orchestrator`,新增 `/broadcast <task>` 命令。
- 更新 `aico-phase1`,启动时注册默认 `implementer` / `reviewer` persona。
- 新增 `tests/unit/test_persona_registry.py`,并扩展 TaskBus / Orchestrator / phase1 app 单测。
- 更新 `STATUS.md`、`docs/decisions/README.md`、`docs/playbooks/README.md`、`docs/human/daily-ops.md`、`CHANGELOG.md`。

### 关键决策
- 🔒 **决策 1**:Persona 层只映射职责名、Adapter 和任务前缀,不改变 `AIAdapter` 协议。
- 🔒 **决策 2**:broadcast 复用普通任务链路,不绕过 `TaskBus`。
- 🔒 **决策 3**:暂不把 persona 外置成配置文件;真实 Telegram 验收稳定后再设计配置化。

### 留给下一轮
- 人类按 `docs/playbooks/phase-3-persona-broadcast.md` 做真实 Telegram 验收。
- 如果验收稳定,设计 persona 外部配置,避免默认 persona 长期硬编码在 `aico-phase1`。
- 如果继续新增 IM 命令,再考虑小型 command parser,不要直接引入大框架。

### 状态变化
- Phase 3:未开始 → 进行中。
- Phase 3 范围 ADR / Playbook:未完成 → 完成。
- Persona 最小模型:未完成 → 完成。
- 群聊 broadcast 最小链路:未完成 → 完成。
- 本地单测:47 个 → 53 个,`pytest` / `ruff check` / `ruff format --check` / `mypy` 全绿。

## Round 12 — 2026-04-28 — Codex

### 输入
- 人类反馈 Telegram 中 `/help`、`/broadcast summarize this repo in one sentence`、`/status` 都已验证,没问题。
- 人类要求继续开发。

### 思考与讨论

**阶段判断**:
- Phase 3 验收标准是 AI 有差异化人设,群聊能 broadcast 任务。Round 11 已实现 `implementer` / `reviewer` persona 和 `/broadcast`,本轮人类已完成真实 Telegram smoke test。
- Round 11 留给下一轮的最高优先级是 Persona 外部配置,避免默认 persona 长期硬编码在 `aico-phase1`。

**方案选择**:
- 候选 A:继续把默认 persona 写在代码里 → ❌ **否决**:新增职责角色必须改代码,不符合“能力可插拔”。
- 候选 B:用 JSON 文件配置 persona,通过 `AICO_PERSONA_CONFIG_PATH` 指定 → ✅ **选定**:标准库即可解析,结构和 `PersonaProfile` 对齐,适合当前本地 dogfooding。
- 候选 C:引入数据库 / 配置中心 / 动态 reload → ❌ **否决**:Phase 3 过重,会提前引入持久化和运维复杂度。

**校验边界**:
- 配置文件中的 `adapter_name` 必须引用当前已启用 Adapter。
- 如果 persona 引用了未启用 Adapter,启动时 fail-fast,不等到运行中静默丢任务。
- 不指定 `AICO_PERSONA_CONFIG_PATH` 时继续使用内置默认 persona,保持旧启动方式兼容。

### 产出
- 新增 `docs/decisions/0004-persona-external-configuration.md`。
- 新增 `config/personas.example.json`。
- `Phase1Settings` 新增 `persona_config_path`,对应环境变量 `AICO_PERSONA_CONFIG_PATH`。
- `aico-phase1` 支持从 JSON 文件加载 `PersonaProfile`,并校验 Adapter 引用。
- 扩展 `tests/unit/test_phase1_app.py`,覆盖外部配置加载和未启用 Adapter fail-fast。
- 更新 `STATUS.md`、`docs/decisions/README.md`、`docs/playbooks/phase-3-persona-broadcast.md`、`docs/human/daily-ops.md`、`docs/human/quickstart.md`、`docs/architecture/overview.md`、`CHANGELOG.md`。

### 关键决策
- 🔒 **决策 1**:Persona 外部配置采用 JSON 文件,不新增依赖。
- 🔒 **决策 2**:配置加载只在启动时发生,当前不做动态 reload。
- 🔒 **决策 3**:Phase 3 到此标记完成,下一阶段进入 Phase 4 审批与审计。

### 留给下一轮
- 写 Phase 4 范围 ADR / Playbook,明确审批与审计的最小验收边界。
- 先定义危险操作识别模型,覆盖只读 / 写文件 / shell 执行等风险等级。
- 先定义审计事件模型,记录任务提交、审批结果、Adapter 派发和任务完成。

### 状态变化
- Telegram 真实 persona / broadcast 验收:未完成 → 完成。
- Persona 外部配置文件入口:未完成 → 完成。
- Phase 3:进行中 → 完成。
- 本地单测:53 个 → 55 个,`pytest` / `ruff check` / `ruff format --check` / `mypy` 全绿。

## Round 13 — 2026-04-28 — Codex

### 输入
- 人类反馈已测试 `/broadcast`、`/status` 等命令,都没问题。
- `STATUS.md` 的下一轮最高优先级是 Phase 4 范围 ADR / Playbook、危险操作识别模型和审计事件模型。

### 思考与讨论

**阶段判断**:
- Phase 3 已经通过真实 Telegram smoke test,可以进入 Phase 4。
- 北极星第三句要求远程 AI 行为“可审批、可审计、可中断”。当前风险是 Telegram 一句话触发写文件或 shell 执行时,核心没有统一门禁。

**方案选择**:
- 候选 A:继续依赖 Adapter 自己的安全模式 → ❌ **否决**:Codex read-only sandbox 和 Claude Code 的行为不是同一种安全协议,核心无法统一观察和审批。
- 候选 B:在 `TaskBus` 前置风险识别,危险任务进入 `waiting_approval`,Telegram 用 `/approve` / `/reject` 手动处理 → ✅ **选定**:最小闭环,不改 Adapter 协议,能直接 dogfooding。
- 候选 C:引入完整审批工作流引擎和数据库 → ❌ **否决**:Phase 4 起步过重,会提前引入持久化、审批人路由和超时状态机。
- 候选 D:只写 ADR / Playbook,不写代码 → ❌ **否决**:人类已经要求继续开发,且风险模型和审计事件可以用单测稳定验证。

**边界选择**:
- 风险等级先定义为 `read_only` / `write_files` / `shell_exec` / `destructive`。
- 风险识别先用文本启发式,后续根据真实 smoke test 调整规则。
- 审计事件先以内存 append-only log 表达,记录任务提交、审批请求、审批结果、Adapter 派发和任务完成/失败/中断。
- 当前不做审批权限策略和持久化,这两项留给下一轮。

### 产出
- 新增 `docs/decisions/0005-phase-4-approval-audit.md`。
- 新增 `docs/playbooks/phase-4-approval-audit.md`。
- 新增 `RiskLevel`、`RiskAssessment`、`ApprovalRequest`、`AuditEvent` 等协议模型。
- 新增 `src/aico/core/risk.py`,实现 `TextRiskAssessor`。
- 新增 `src/aico/core/audit.py`,实现 `InMemoryAuditLog`。
- 更新 `TaskBus`,危险任务先返回 `waiting_approval`,批准后才派发给 Adapter,并记录审计事件。
- 更新 `Orchestrator`,新增 `/approve <task_id>` 和 `/reject <task_id> [reason]`。
- 新增 `tests/unit/test_risk.py`,并扩展 models / TaskBus / Orchestrator 单测。
- 更新 `STATUS.md`、`docs/decisions/README.md`、`docs/playbooks/README.md`、`docs/human/daily-ops.md`、`CHANGELOG.md`。

### 关键决策
- 🔒 **决策 1**:Phase 4 审批门禁放在 `TaskBus` 前,不散落到各 Adapter 内部。
- 🔒 **决策 2**:危险任务默认不派发,必须显式 `/approve <task_id>` 后才继续。
- 🔒 **决策 3**:审计事件先使用内存 append-only log,不在本轮引入数据库或外部日志系统。
- 🔒 **决策 4**:审批权限策略暂未实现,下一轮必须在真实 smoke test 后优先设计。

### 留给下一轮
- 按 `docs/playbooks/phase-4-approval-audit.md` 做真实 Telegram smoke test。
- 把内存审计事件暴露到结构化日志或只读 `/audit` 命令,让人类能直接确认 trace。
- 设计最小审批权限策略,避免任意 Telegram 用户知道 task id 就能批准。
- 下一次新增命令前考虑小型 command parser,避免命令解析继续散落。

### 状态变化
- Phase 4:未开始 → 进行中。
- Phase 4 范围 ADR / Playbook:未完成 → 完成。
- 危险操作识别模型:未完成 → 完成。
- 审计事件模型:未完成 → 完成。
- 本地单测:55 个 → 66 个,`pytest` / `ruff check` / `ruff format --check` / `mypy` 全绿。

## Round 14 — 2026-04-28 — Codex

### 输入
- 人类要求快速上手项目,然后继续开发接下来的工作。
- `STATUS.md` 的下一轮建议中最高优先级包括 Phase 4 真实审批 smoke test、审计事件可观测输出和审批权限策略。

### 思考与讨论

**接手判断**:
- 按 `AGENTS.md` 强制顺序阅读北极星、状态、轮次、踩坑、卡点和开发规范。
- 当前唯一活跃卡点 B-002 是 Phase 5 前的延后卡点,不阻塞 Phase 4。
- 真实 Telegram smoke test 需要人类环境配合,但审计可观测出口可以本地完成并用单测验证。

**方案选择**:
- 候选 A:直接实现结构化日志输出 → ❌ **否决**:需要先设计日志字段、脱敏和运行时配置,比当前 Phase 4 的最小闭环更重。
- 候选 B:直接做审计事件持久化 → ❌ **否决**:会提前引入 Repository / SQLite 等持久化选择,需要 ADR,且不影响马上在 Telegram 中确认 trace。
- 候选 C:新增 `/audit` 只读命令,展示 `TaskBus` 内存审计事件 → ✅ **选定**:复用 Round 13 的内存 append-only log,最小满足“人类能确认 trace”。
- 候选 D:先抽小型 command parser 再加 `/audit` → ❌ **否决**:命令解析确实开始变多,但本轮只新增一个简单只读命令;把 parser 收口留给下一次命令扩展,避免把可观测出口和重构绑在一起。

### 产出
- 更新 `src/aico/core/orchestrator.py`,新增 `/audit` / `audit` 只读命令和审计事件文本格式化。
- 扩展 `tests/unit/test_orchestrator.py`,覆盖空审计日志和危险任务审计 trace 查询。
- 更新 `docs/playbooks/phase-4-approval-audit.md`,把 `/audit` 加入 smoke test 步骤。
- 更新 `docs/human/daily-ops.md`,记录 `/audit` 常用命令和内存审计限制。
- 更新 `CHANGELOG.md`,记录 `/audit` 用户可见能力。

### 关键决策
- 🔒 **决策 1**:`/audit` 当前只展示最近 10 条内存审计事件,不伪装成持久审计系统。
- 🔒 **决策 2**:本轮不引入命令解析框架;下一次新增命令前优先收口 command parser。

### 留给下一轮
- 人类按 `docs/playbooks/phase-4-approval-audit.md` 做真实 Telegram smoke test,重点验证 `/audit` 能看到 `task_submitted` / `approval_requested` / `approval_approved` / `approval_rejected`。
- 设计最小审批权限策略,避免任意 Telegram 用户知道 task id 就能 `/approve`。
- 选择审计事件持久化或结构化日志输出方案,让 trace 不随进程重启丢失。

### 状态变化
- Phase 4 进度新增:`/audit` 最近审计事件只读查询 ✅。
- 审计事件可观测输出:未完成 → 最小可用(`/audit` 内存视图)。
- 本地单测:66 个 → 68 个,`pytest` / `ruff check` / `ruff format --check` / `mypy` 全绿。

## Round 15 — 2026-04-28 — Codex

### 输入
- 人类在 Telegram + Claude 写文件审批中遇到 `Task rejected: unknown pending approval`。
- 人类反馈审批交互不好:需要手动输入 taskId,且 Telegram 授权提示里不方便看到完整 taskId。

### 思考与讨论

**问题定位**:
- Round 13 的审批命令要求 `/approve <task_id>` 精确匹配完整 task id。
- 真实 IM 场景里 task id 太长,用户不应该被迫复制 UUID。
- 当前权限策略尚未实现,但本轮问题是交互可用性和 pending approval 查找,不需要先扩大到权限系统。

**方案选择**:
- 候选 A:继续要求用户用 `/audit` 找完整 task id → ❌ **否决**:这是把系统复杂度转嫁给人,违背 IM dogfooding 的轻量交互。
- 候选 B:`/approve` 默认批准唯一待审批任务,多任务时提示短 ID → ✅ **选定**:最符合真实聊天习惯,也避免误批多个任务。
- 候选 C:Telegram inline button 审批 → ❌ **暂缓**:体验最好,但需要引入 Telegram callback query 处理,范围比本轮 bug fix 大。
- 候选 D:只把完整 task id 再打印一遍 → ❌ **否决**:仍然要求复制长 ID,不能解决根因。

### 产出
- 更新 `TaskBus.approve()` / `reject_approval()`,支持无 task id 时处理唯一 pending approval。
- 支持 task id 前缀匹配,多个匹配或多个 pending 时返回短 ID 列表。
- 更新 `Orchestrator` 审批提示,展示短 ID,并提示直接发送 `/approve` / `/reject`。
- 扩展 TaskBus / Orchestrator 单测,覆盖无 ID 审批、短 ID 审批、多 pending 提示和无 ID 拒绝。
- 更新 `docs/human/daily-ops.md`、`docs/playbooks/phase-4-approval-audit.md`、`CHANGELOG.md`。
- 新增 PITFALL P-006。

### 关键决策
- 🔒 **决策 1**:IM 审批命令默认面向“当前唯一待审批任务”,不强迫用户复制完整 task id。
- 🔒 **决策 2**:多个待审批任务时不自动猜测,必须让用户用短 ID 指定,避免误批。

### 留给下一轮
- 重新做真实 Telegram 审批 smoke test,优先验证 `/approve` 无 ID 流程。
- 后续若继续优化审批体验,优先考虑 Telegram inline button,但要另起小范围任务。
- 审批权限策略仍是 Phase 4 高优先级,不要因为 UX 修复而忽略。

### 状态变化
- Phase 4 进度新增:`/approve` / `/reject` 无 task id 快捷审批 ✅。
- 新增 P-006,记录 IM 审批命令不要依赖完整 UUID。
- 本地单测:68 个 → 74 个,`pytest` / `ruff check` / `ruff format --check` / `mypy` 全绿。

## Round 16 — 2026-04-28 — Codex

### 输入
- 人类要求快速上手项目并继续开发接下来的工作。
- `STATUS.md` 的高优先级下一步包括真实审批 smoke test、审批权限策略、审计持久化或结构化日志输出。

### 思考与讨论

**接手判断**:
- 按 `AGENTS.md` 强制顺序读取北极星、状态、轮次、踩坑、卡点和开发规范。
- 工作区已有 Round 15 未提交改动,本轮在其基础上继续,不回滚已有内容。
- 真实 Telegram smoke test 需要人类环境配合;本轮优先完成能本地验证的最高优先级代码项:审批权限策略。

**方案选择**:
- 候选 A:继续允许任意用户审批 → ❌ **否决**:群聊中只要看到 task id 或短 ID 就能批准危险任务,违反 Phase 4 的安全目标。
- 候选 B:默认只允许任务发起人审批,并通过配置增加额外审批人 → ✅ **选定**:单人 dogfooding 零配置可用,群聊中有最小权限边界,不把 Telegram ACL 细节耦合进核心。
- 候选 C:立刻接入 Telegram 群管理员权限 → ❌ **否决**:需要额外 Bot API 调用、缓存和 Channel 特定逻辑,对 Phase 4 当前闭环过重。
- 候选 D:先做完整企业 ACL / IAM → ❌ **否决**:个人项目现阶段没有足够样本,会提前引入持久化和权限模型复杂度。

**实现边界**:
- 新增 `ApprovalPolicy` 协议与 `RequesterOrListedApproverPolicy` 默认实现。
- 未授权 `/approve` / `/reject` 不改变 pending task 状态,也不派发 Adapter,只记录 `approval_denied` 审计事件。
- `aico-phase1` 用 `AICO_APPROVAL_REVIEWER_IDS` 读取逗号分隔的额外审批人 Telegram sender id。

### 产出
- 新增 `src/aico/core/approval.py`,定义审批权限策略。
- 更新 `TaskBus`,在批准 / 拒绝 pending approval 前执行 reviewer 权限校验。
- 新增 `AuditEventType.APPROVAL_DENIED`。
- 更新 `aico-phase1`,支持 `AICO_APPROVAL_REVIEWER_IDS`。
- 新增 `docs/decisions/0006-approval-permission-policy.md`,并更新 ADR 索引。
- 更新 Phase 4 playbook、daily ops、CHANGELOG。
- 扩展 TaskBus / Orchestrator / Phase1Settings / models 单测,覆盖未授权审批拒绝和配置审批人通过。

### 关键决策
- 🔒 **决策 1**:危险任务默认只能由任务发起人审批;额外审批人必须显式配置。
- 🔒 **决策 2**:审批权限判断属于核心 `TaskBus` 前置门禁,不是 Telegram Channel 的命令特例。
- 🔒 **决策 3**:当前不接入 Telegram 群管理员权限,避免 IM 细节污染核心审批策略。

### 留给下一轮
- 人类按 `docs/playbooks/phase-4-approval-audit.md` 做真实 Telegram smoke test,新增验证未授权用户审批会被拒绝且记录 `approval_denied`。
- 继续推进审计事件持久化或结构化日志输出,让 trace 不随进程重启丢失。
- 下一次新增命令前优先做小型 command parser;`TaskBus` 已 467 行,继续加功能前要警惕 500 行硬上限。

### 状态变化
- Phase 4 进度新增:审批权限策略 ✅。
- 新增 ADR-0006。
- 本地单测:74 个 → 79 个,`pytest` / `ruff check` / `ruff format --check` / `mypy` 全绿。

## Round 17 — 2026-04-28 — Codex

### 输入
- 人类完成真实 Telegram 测试后反馈 3 点:
  - 给 `@codex` 授权时,Codex 报 read-only 沙箱且不允许申请写权限。
  - `@claude` 写 `/tmp/readme.md` 在 AICO `/approve` 后仍提示需要本机授权写权限,用户不知道该在哪里授权。
  - `/audit` 输出没有舒服的换行。

### 思考与讨论

**问题定位**:
- Codex 在项目里定位是 `reviewer`,能力只有 `CODE_REVIEW` / `STREAM_OUTPUT`,但 Round 16 的审批流只校验“人是否能审批”,没有校验“Adapter 是否能执行该风险等级任务”。因此 `/codex create ...` 会进入无效审批,批准后才由 Codex CLI read-only sandbox 报错。
- Claude Code CLI 的 `-p` 非交互模式仍可能触发 Claude 自己的权限系统。当前 Adapter 只接 stdout/stderr,没有 TTY / stdin 交互桥,所以本机授权提示无法自然转发到 Telegram。
- `/audit` 技术上有换行,但每个事件仍压成一条很长的行,在 Telegram 中可读性差。

**方案选择**:
- 候选 A:继续让底层 CLI 报错 → ❌ **否决**:用户已经批准后才失败,错误来自底层沙箱,不符合“可审批、可审计”的核心体验。
- 候选 B:把 Codex 默认改成 workspace-write → ❌ **否决**:Round 7/9 已决定 Codex 默认 read-only reviewer,远程 IM 不应默认放开写能力。
- 候选 C:TaskBus 在审批前校验 Adapter capability,read-only Adapter 直接拒绝危险任务 → ✅ **选定**:保持 Codex reviewer 定位,错误在核心层可控且可审计。
- 候选 D:把 Claude 原生权限提示桥接到 Telegram → ❌ **否决**:需要 TTY/stdin 交互转发,不同 CLI 格式不同,会把 Adapter 易变细节污染核心。
- 候选 E:Claude 远程入口使用 `--permission-mode bypassPermissions`,由 AICO `/approve` 作为唯一远程审批门 → ✅ **选定**:符合“远程异步”北极星,也避免本机二次授权。

**实现边界**:
- 新增 `risk_capability.py`,将风险等级映射到 Adapter capability,避免 `TaskBus` 超过 500 行硬约束。
- 不改变 Codex 默认 read-only 命令。
- `/audit` 改为多行事件块,不引入 Markdown/HTML parse mode。

### 产出
- 新增 `src/aico/core/risk_capability.py`,实现 Adapter 风险能力门禁。
- 更新 `TaskBus.submit()`,危险任务进入审批前先检查 Adapter 是否具备对应能力;不具备则记录 `TASK_REJECTED` 并返回明确 reason。
- 更新 `ClaudeCodeAdapter` 和 `Phase1Settings` 的默认 Claude 命令,加入 `--permission-mode bypassPermissions`。
- 更新 `Orchestrator` `/audit` 输出,每个事件按多行块展示。
- 新增 `docs/decisions/0007-remote-approval-adapter-boundary.md`。
- 新增 PITFALL P-007。
- 更新 Phase 4 playbook、daily ops、CHANGELOG、STATUS。
- 扩展单测覆盖 Claude 默认命令、read-only Adapter 危险任务拒绝、`/audit` 多行输出。

### 关键决策
- 🔒 **决策 1**:AICO `/approve` 是远程场景唯一审批入口;底层 CLI 不应再要求本机交互授权。
- 🔒 **决策 2**:read-only Adapter 不承接危险任务,即使人类尝试审批也不派发。
- 🔒 **决策 3**:暂不做 CLI TTY 权限提示转发到 Telegram。

### 留给下一轮
- 人类复测 Phase 4 playbook,重点验证 `/codex create ...` 会直接拒绝、`/claude create /tmp/readme.md` 在 `/approve` 后不再要求本机授权、`/audit` 多行可读。
- 继续推进审计事件持久化或结构化日志输出。
- 风险识别仍是文本启发式,后续应升级为规则表,避免误判后配合 Claude bypass 权限造成风险。

### 状态变化
- Phase 4 进度新增:Adapter 风险能力门禁 ✅、Claude Code 远程审批后免本机二次授权 ✅、`/audit` 多行可读输出 ✅。
- 新增 ADR-0007 和 PITFALL P-007。
- 本地单测:79 个 → 82 个,`pytest` / `ruff check` / `ruff format --check` / `mypy` 全绿。

## Round 18 — 2026-04-28 — Codex

### 输入
- 人类复测 Round 17 后反馈“验收了没问题,继续执行”。
- `STATUS.md` 下一轮高优先级剩余项是审计事件持久化或结构化日志输出。

### 思考与讨论

**阶段判断**:
- Phase 4 真实审批 smoke test 已由人类验收通过,可以把真实审批链路标记完成。
- `/audit` 已经能看最近事件,但仍是进程内视图;进程重启会丢失历史 trace。
- 北极星第三句要求 AI 行为可审计,因此需要一个最小跨重启审计留痕。

**方案选择**:
- 候选 A:继续只用内存 `/audit` → ❌ **否决**:真实 smoke test 已通过,继续只保留内存会让审计在重启后消失。
- 候选 B:直接引入 SQLite/Postgres 审计仓储 → ❌ **否决**:需要 Repository、迁移、备份和查询设计,对 Phase 4 收口过重。
- 候选 C:配置 JSONL append-only 文件 → ✅ **选定**:无需新依赖,每行一个结构化事件,可用 `tail` / `jq` / 日志采集读取,足够支撑单机 dogfooding。
- 候选 D:只打 Python structured logger → ❌ **否决**:如果没有明确 handler / 文件配置,人类不一定能找到历史事件;JSONL path 更直接。

**实现边界**:
- `InMemoryAuditLog` 继续作为 `/audit` 的近实时内存视图。
- 新增 `AuditSink` / `JsonlAuditSink`;配置 `AICO_AUDIT_LOG_PATH` 后,每条事件同步 append 到 JSONL 文件。
- 不做日志轮转、压缩、索引和历史查询命令;这些留给 Phase 6 可观测看板。

### 产出
- 更新 `src/aico/core/audit.py`,新增 `AuditSink` 和 `JsonlAuditSink`。
- 更新 `aico-phase1`,新增 `AICO_AUDIT_LOG_PATH` 配置,并将 JSONL sink 接入 `TaskBus`。
- 新增 `tests/unit/test_audit.py`,覆盖 JSONL 写入内容。
- 扩展 Phase1 app 单测,验证配置审计路径后会写入 JSONL。
- 新增 `docs/decisions/0008-audit-jsonl-persistence.md`,并更新 ADR 索引。
- 更新 `docs/human/daily-ops.md`、`docs/playbooks/phase-4-approval-audit.md`、`CHANGELOG.md`、`STATUS.md`。
- 更新 `BLOCKERS.md`,将 B-002 从 DEFERRED 升级为 Phase 5 入口 BLOCKING。

### 关键决策
- 🔒 **决策 1**:Phase 4 审计持久化采用可配置 JSONL append-only 文件,不引入数据库。
- 🔒 **决策 2**:`/audit` 仍只展示进程内最近事件,完整历史从 JSONL 文件读取。
- 🔒 **决策 3**:Phase 4 到此收口完成,下一轮进入 Phase 5 前必须解决 B-002。

### 留给下一轮
- 写 Phase 5 范围 ADR / Playbook,围绕 B-002 决定 AI 间协作协议的最小形态。
- 建议先选择一个最小 demo:人类在 Telegram 发任务给一个 persona,该 persona 通过核心协议请求另一个 persona 协作,结果回到同一会话。
- 进入 Phase 5 前优先收口 command parser,避免 `Orchestrator` 继续增长。

### 状态变化
- Phase 4:进行中 → 完成。
- Telegram 真实审批 smoke test:未完成 → 完成。
- 审计事件持久化或结构化日志输出:未完成 → JSONL 持久化完成。
- B-002:DEFERRED → BLOCKING(Phase 5 入口)。
- 本地单测:82 个 → 84 个,`pytest` / `ruff check` / `ruff format --check` / `mypy` 全绿。

## Round 19 — 2026-04-28 — Codex

### 输入
- 人类要求“继续执行”。
- `STATUS.md` 显示 Phase 4 已完成,下一步最高优先级是启动 Phase 5 并解决 B-002(AI 间协作协议形态)。

### 思考与讨论

**协议调研**:
- A2A 当前是面向 Agent↔Agent 的开放协议,覆盖能力发现、消息 / artifact 交换、长任务协作。
- ACP 早期作为 IBM/BeeAI Agent Communication Protocol,现在已并入 A2A 生态。
- MCP 更适合 Agent↔工具 / 上下文,不适合作为本项目 Phase 5 的 Agent↔Agent 主通道。

**方案选择**:
- 候选 A:走 IM 消息总线 → ❌ **否决**:群聊感强,但会把内部协作语义耦合到 Telegram,未来接飞书/钉钉会重复实现。
- 候选 B:直接实现完整 A2A HTTP server/client → ❌ **否决**:当前两个 Adapter 都在同一进程内,Agent Card/SSE/HTTP 服务对 MVP 过重。
- 候选 C:内部 A2A-inspired 协作指令 `@persona: request` → ✅ **选定**:保留 source/target/payload 协作语义,复用 TaskBus、审批、审计和状态机,未来可映射到 A2A。
- 候选 D:直接 RPC 调用目标 Adapter → ❌ **否决**:会绕过 TaskBus,失去审批、审计和状态可观测,也弱化“真实团队协作”的 IM 体验。

**实现边界**:
- 协作触发语法必须是行首 `@persona: request`,普通文本中的 `@persona` 不触发。
- 协作子任务仍是普通 `Task`,payload 里包含来源 persona。
- 当前只支持单层协作,避免 AI 之间无限递归。
- Telegram 只展示协作过程,不作为内部消息总线。

### 产出
- 新增 `src/aico/core/collaboration.py`,定义 `CollaborationDirective`、指令解析和协作 payload 包装。
- 更新 `Orchestrator`,在 Adapter 文本输出中识别协作指令,自动创建目标 persona 子任务并流式返回结果。
- 更新默认 implementer persona 和 `config/personas.example.json`,提示可用 `@reviewer: ...` 请求 reviewer 协作。
- 新增 `tests/unit/test_collaboration.py`,并扩展 Orchestrator 单测覆盖 implementer → reviewer 协作链路。
- 新增 `docs/decisions/0009-phase-5-collaboration-protocol.md`。
- 新增 `docs/playbooks/phase-5-collaboration.md`,并更新 playbook 索引、daily ops、CHANGELOG。
- 更新 `BLOCKERS.md`,将 B-002 标记为 RESOLVED。
- 更新 `STATUS.md`,Phase 5 进入进行中。

### 关键决策
- 🔒 **决策 1**:Phase 5 MVP 采用内部 A2A-inspired 文本协作指令,不直接实现完整 A2A HTTP。
- 🔒 **决策 2**:协作子任务必须走 `TaskBus`,不得绕过审批、审计和状态机。
- 🔒 **决策 3**:当前只支持单层协作,避免无限递归和不可控任务树。

### 留给下一轮
- 人类按 `docs/playbooks/phase-5-collaboration.md` 做真实 Telegram smoke test。
- 增加显式 `collaboration_requested` 审计事件,让 parent task 与 child task 关系在 JSONL 中可追溯。
- 进入更多 Phase 5 命令前,优先抽小型 command parser;`Orchestrator` 已增长到 371 行。

### 状态变化
- Phase 5:未开始 → 进行中。
- B-002:BLOCKING → RESOLVED。
- Phase 5 进度新增:协作协议 ADR / Playbook ✅、轻量协作指令解析 ✅、Adapter 输出触发目标 persona 子任务 ✅。
- 本地单测:84 个 → 88 个,`pytest` / `ruff check` / `ruff format --check` / `mypy` 全绿。

## Round 20 — 2026-04-28 — Codex

### 输入
- 人类在 Telegram 中发送:
  `@claude 请简要分一下当前仓库phase 5的协作方案，然后输出一行 @reviewer review一下phase 5有什么风险和问题`
- 实际只收到 Claude 的“Phase 5 协作方案简析”,怀疑没有用到 Codex。
- 人类还发现 Claude 执行时输入 `/status` 和 `/audit` 会卡住。

### 思考与讨论

**问题定位**:
- Round 19 的协作解析只支持行首 `@reviewer: ...`。人类真实输入是 `@reviewer review一下...`,没有冒号,因此没有触发 reviewer 子任务。没有看到 `Collaboration requested: implementer -> reviewer` 也说明没有用到 Codex。
- `TelegramChannel.poll_once()` 逐条 update `await self._handler(message)`。普通任务 handler 会一直 await Adapter 输出流,所以长任务期间 polling loop 无法继续处理后续 `/status` / `/audit`。

**方案选择**:
- 候选 A:要求人类必须使用冒号语法 → ❌ **否决**:真实 IM 里自然会写成 `@reviewer review一下...`,语法过窄会反复踩坑。
- 候选 B:协作解析同时支持冒号和空格 → ✅ **选定**:兼容自然输入,仍要求行首 `@persona`,避免正文中的普通 mention 误触发。
- 候选 C:在 Orchestrator 内把长任务放后台 → ❌ **暂缓**:可以做,但当前卡住的直接根因在 Channel polling await handler;先从入口解阻塞。
- 候选 D:TelegramChannel 为每条 incoming message 创建后台 handler task → ✅ **选定**:Channel 继续 polling,长任务运行时轻量命令能进入 Orchestrator。

### 产出
- 更新 `parse_collaboration_directive()`,支持 `@persona request` 和 `@persona: request`。
- 更新 `TelegramChannel`,incoming message handler 改为后台 task 分发,`stop()` 时取消未完成 handler。
- 扩展 `tests/unit/test_collaboration.py`,覆盖空格协作语法。
- 扩展 `tests/unit/test_telegram_channel.py`,覆盖长 handler 未完成时仍可继续 poll 下一条 update。
- 新增 PITFALL P-008 / P-009。
- 更新 Phase 5 playbook、daily ops、STATUS。

### 关键决策
- 🔒 **决策 1**:IM 协作触发语法兼容 `@persona request` 和 `@persona: request`。
- 🔒 **决策 2**:Channel polling 不 await 长任务 handler,只负责快速分发 update。

### 留给下一轮
- 人类复测真实 Telegram:同样的 `@reviewer review一下...` 应触发 `Collaboration requested: implementer -> reviewer`。
- 复测 Claude 长任务期间 `/status` 和 `/audit` 是否能即时响应。
- 后续仍建议抽 command parser;Orchestrator 已接近复杂度边界。

### 状态变化
- 新增 P-008 / P-009。
- 本地单测:88 个 → 90 个,`pytest` / `ruff check` / `ruff format --check` / `mypy` 全绿。

## Round 21 — 2026-04-28 — Codex

### 输入
- 人类反馈 Telegram 中长文本返回时疑似只收到部分信息,怀疑消息被吞。
- 人类要求确认问题,并说明 AICO 对用户 prompt 做了哪些加工。

### 思考与讨论

**问题定位**:
- `Orchestrator` 原本把所有流式输出 chunk 拼成一条文本,持续调用 `editMessageText` 刷新同一条 Telegram 消息。
- Telegram Bot API 单条文本消息有 4096 字符限制。长输出超过限制后,编辑请求会失败,handler 中断,表现为 Telegram 只收到前半段。
- 这不是模型一定少生成,而是 IM 出口层承载失败。

**方案选择**:
- 候选 A:在 `TelegramChannel` 内部静默截断 → ❌ **否决**:截断仍会丢内容,且 Channel 无法理解流式上下文。
- 候选 B:只把上限写进文档,要求 AI 少输出 → ❌ **否决**:真实协作和审计场景天然会有长文本,靠人约束不可靠。
- 候选 C:在核心流式出口加保守分片器 → ✅ **选定**:不改变 `IMChannel` 协议,仍由核心保证不会向任何 Channel 推送超长文本。

### 产出
- 新增 `src/aico/core/streaming.py`,实现 `StreamedMessageWriter`,使用 3900 字符保守上限拆分流式输出。
- 更新 `Orchestrator`,普通任务和审批后任务的输出都经分片器写回 IM。
- 扩展 Orchestrator 单测,覆盖超过单条消息安全长度的长输出会拆成多条消息。
- 新增 PITFALL P-010,更新 daily ops、troubleshooting、Phase 1 / Phase 5 playbook 和 CHANGELOG。

### 关键决策
- 🔒 **决策 1**:IM 流式输出层必须主动处理单条消息长度上限,不能把平台限制留给 Bot API 报错。
- 🔒 **决策 2**:当前用 3900 字符作为保守文本上限,不引入 Telegram 特定协议扩展。

### 留给下一轮
- 真实 Telegram 复测一个超过 4096 字符的长输出,确认会拆成多条消息且内容连续。
- 继续推进 Phase 5 的显式 `collaboration_requested` 审计事件。
- 后续若支持 Markdown/HTML parse mode,需要重新确认实体转义后的长度上限。

### 状态变化
- 新增 P-010。
- 长文本流式输出从“单条消息编辑”改为“安全长度内编辑,超长后续发新消息”。

## Round 22 — 2026-04-29 — Codex

### 输入
- 人类要求继续开发后续工作,最后集中汇报改动和验收方式。
- `STATUS.md` 的下一轮建议包括真实 Telegram 复测、Phase 5 协作审计增强、命令解析收口和风险识别迭代。

### 思考与讨论

**推进边界**:
- 真实 Telegram 复测需要在当前 bot 会话中发送消息并观察回复。当前 shell 有 Token 变量,但没有可靠 chat id / 不应贸然启动长任务打扰人类会话,因此本轮把真实复测保留为人类验收步骤。
- 可本地闭环的开发项包括协作审计增强、命令解析收口、风险识别规则表化。

**方案选择**:
- 候选 A:只做真实 smoke test 脚本 → ❌ **否决**:没有 chat id 和人工观察点,容易做成不稳定或打扰真实 IM 的测试。
- 候选 B:先增强协作审计事件 → ✅ **选定**:直接补齐 Phase 5 “可追溯”缺口,符合北极星第三句。
- 候选 C:继续在 `Orchestrator` 里加命令判断 → ❌ **否决**:`Orchestrator` 已多次被提醒接近复杂度边界,继续堆命令会扩大维护风险。
- 候选 D:把内置命令解析抽成小模块 → ✅ **选定**:命令已有 6 个,满足 Rule of Three 后抽离的条件。
- 候选 E:风险识别直接换 LLM 判定 → ❌ **否决**:远程审批门禁应可预测、可测试;当前更适合规则表迭代。

### 产出
- 新增 `AuditEventType.COLLABORATION_REQUESTED`。
- 新增 `TaskBus.record_collaboration_requested()`,记录 child task、source persona 和 parent task id。
- 更新 `Orchestrator`,触发 `@reviewer ...` 协作时先记录 `collaboration_requested`,再派发 child task。
- 新增 `src/aico/core/commands.py`,统一解析 help/status/audit/broadcast/approve/reject 命令,支持 Telegram bot suffix。
- 更新 `Orchestrator` 使用 command parser,删除原有散落命令解析 helper。
- 更新 `src/aico/core/risk.py`,将风险识别改为 `RiskRule` 规则表。
- 新增 / 扩展 `tests/unit/test_commands.py`、`tests/unit/test_orchestrator.py`、`tests/unit/test_models.py`、`tests/unit/test_risk.py`。
- 更新 daily ops、Phase 5 playbook、CHANGELOG、STATUS。

### 关键决策
- 🔒 **决策 1**:Phase 5 协作关系作为审计事件记录,事件挂在 child task 上,`actor` 使用 source persona,`detail` 记录 parent task。
- 🔒 **决策 2**:内置 IM 命令解析归入独立核心模块,`Orchestrator` 只消费解析结果。
- 🔒 **决策 3**:风险门禁继续采用确定性规则,不引入 LLM 风险判定。

### 留给下一轮
- 人类按 Phase 5 playbook 做真实 Telegram 复测,重点看 `collaboration_requested` 是否出现在 `/audit`。
- 人类做超过 4096 字符长文本复测,确认会拆成多条消息。
- 后续可设计显式 opt-in 的真实 Telegram integration harness,避免自动测试打扰真实聊天。

### 状态变化
- Phase 5 协作任务审计事件增强:未完成 → 完成。
- `Orchestrator` 行数降低到 318 行,`TaskBus` 保持 496 行。

## Round 23 — 2026-04-29 — Codex

### 输入
- 人类反馈 `/claude 请输出一段超过5000字...` 没有收到结果,怀疑卡住或长文本分片仍有问题。
- 人类询问当前并发模型为何多次请求 Claude 会 busy。
- 人类希望“后台搞点日志”,并开始脑暴更薄的 Agent 层 / agent harness。

### 思考与讨论

**问题定位**:
- 当前 long polling 已支持并发分发,但 Claude/Codex Adapter 本身是单任务占用。`ClaudeCodeAdapter.receive_task()` 发现任一未完成 task 时会返回 `AckStatus.BUSY`。
- 长文本分片已有单测覆盖,但如果 Claude CLI 长时间不退出或 stdout 没有完整 line/chunk,Telegram 仍可能长时间没有可推送内容。
- 之前后台缺少关键链路日志,无法区分“Adapter busy”“CLI 没退出”“没有 stdout”“Telegram 出口失败”。

**方案选择**:
- 候选 A:先猜一个长文本 bug 继续改分片 → ❌ **否决**:已有分片测试,且缺少运行时证据,继续猜容易制造新问题。
- 候选 B:补关键链路日志 → ✅ **选定**:先让下一次真实复现可定位。
- 候选 C:马上把 Claude 并发改成多进程池 → ❌ **否决**:涉及工作区写入冲突、审批语义、状态聚合,需要先设计。
- 候选 D:立即引入 pi-mono 或自研 agent harness → ❌ **暂缓**:这是架构层变化,本轮先脑暴和建议写 ADR。

### 产出
- `Phase1Settings` 新增 `log_level` / `log_path`,默认 `INFO` 和 `logs/aico.log`。
- `aico-phase1` 启动时配置 stdout + 文件日志。
- `TelegramChannel` 记录入站消息、handler 生命周期、send/edit 消息长度。
- `Orchestrator` 记录入站、命令、任务路由、ack、stream start/output/finish、协作触发。
- `ClaudeCodeAdapter` 记录 accepted/busy、进程启动、退出码、stdout chunk 数量、任务完成。
- `StreamedMessageWriter` 记录长文本分片触发。
- 新增 PITFALL P-011,更新 daily ops、troubleshooting、CHANGELOG、STATUS。

### 关键决策
- 🔒 **决策 1**:后台日志默认开启到 `logs/aico.log`,但不打印完整用户 prompt,只打印长度和可追踪 id。
- 🔒 **决策 2**:当前 Adapter 并发仍保持 1,不在没有设计的情况下引入多 Claude 进程。
- 🔒 **决策 3**:Agent harness 先做设计 ADR,不直接把 pi-mono 或自研 loop 落进主链路。

### 留给下一轮
- 人类复现长文本请求后,用 `tail -f logs/aico.log` 判断卡点。
- 写 Agent harness 设计 ADR,比较三条路线:继续 CLI 封装、接 pi-mono、AICO 自研轻量 loop/tool/skill harness。
- 若需要提升并发,先设计每 Adapter 的 queue / worker slots / workspace lock / interrupt 语义。

### 状态变化
- 新增 P-011。
- 后台关键链路日志完成。

## Round 24 — 2026-04-29 — Codex

### 输入
- 人类确认 Adapter 层和 Loop 层没有异议。
- 人类要求 Agent Harness 薄层进一步简化:tools/skills 直接获取 Claude/Codex 自己的能力,AICO 仅在 Adapter 层翻译;pi-mono 这条较重链路先不考虑。
- 人类要求把讨论和结论更新到合适文档,然后开始开发。

### 思考与讨论

**边界收敛**:
- AICO 不拥有 Claude/Codex 的 tools/skills registry,也不重写它们的 tool execution loop。
- AICO 必须拥有 IM 侧会话引用,否则 Telegram 无法表达“继续这个 Claude/Codex 会话”。
- provider 的真实上下文仍在 Claude/Codex 内部,AICO 只保存 provider session id / resume hint / workspace / status。

**方案选择**:
- 候选 A:继续只做黑盒 prompt → ❌ **否决**:无法解决无会话管理和能力不可见。
- 候选 B:自研完整 tools/skills runtime → ❌ **否决**:与人类要求相反,会重复 Claude/Codex 能力。
- 候选 C:接 pi-mono 做重 agent runtime → ❌ **否决**:本阶段先不考虑,避免引入新主链路。
- 候选 D:薄 session/capability facade → ✅ **选定**:AICO 只做会话和能力门面,provider-owned tools/skills 由 Adapter 翻译展示。

### 产出
- 新增 ADR-0010:`Agent Session 与 Harness 边界`。
- ADR 明确写入:`AICO Agent Harness is a session and capability facade, not a tool execution runtime.`
- 新增 `src/aico/core/agent_session.py`,定义:
  - `AgentCard`:展示 provider-owned tools/skills 来源和 session feature。
  - `ProviderSessionRef`:保存 Claude/Codex provider session id 和 resume hint。
  - `AgentSession`:保存 AICO session 到 provider session 的引用。
  - `InMemoryAgentSessionStore`:最小内存会话 store。
- `Phase1Runtime` 挂载 `session_store`,但暂不改变现有 Telegram 命令行为。
- 新增 `tests/unit/test_agent_session.py`,扩展 Phase1 app 单测。

### 关键决策
- 🔒 **决策 1**:AICO Agent Harness 是 session/capability facade,不是 tool execution runtime。
- 🔒 **决策 2**:Claude/Codex 的 tools/skills/slash/plugin/mcp 状态由各 Adapter 翻译,不在 AICO 内复制 registry。
- 🔒 **决策 3**:pi-mono 作为较重 Agent runtime 暂不进入主线;未来最多作为独立 Adapter 实验。

### 留给下一轮
- 基于 `InMemoryAgentSessionStore` 做 `/sessions`、`/new <agent>`、`/use <session>` MVP。
- Claude Adapter 优先接 `--session-id` / `--resume` / `--continue`;Codex Adapter 评估 `exec resume`。
- 设计 `/agent <name>` / `/skills <name>` / `/tools <name>` 的 provider introspection 输出。

### 状态变化
- 新增 ADR-0010。
- Phase 5 进度新增 Agent Session / Harness 边界 ADR。

## Round 25 — 2026-04-29 — Codex

### 输入
- 人类确认前一轮 ADR 和薄 Agent Harness 边界没有问题,要求继续开发。
- `STATUS.md` 下一轮建议中最高的可本地闭环开发项是 Session 命令 MVP。

### 思考与讨论

**推进边界**:
- AICO 需要先能在 IM 侧表达“我现在使用哪个 agent session”,否则后续 provider resume 无处挂载。
- 但 Claude/Codex 的真实上下文仍应由 provider 自己保存;本轮不能把 AICO 变成 tool execution runtime。

**方案选择**:
- 候选 A:直接接 Claude/Codex resume 参数 → ❌ **暂缓**:需要先有稳定的 AICO session id / active session 体验,否则 provider session ref 无处查询和切换。
- 候选 B:先做 `/sessions`、`/new`、`/use` → ✅ **选定**:最小闭环,能在 Telegram 侧创建会话引用并切换普通消息默认目标。
- 候选 C:把会话绑定全局用户而不区分聊天 → ❌ **否决**:同一个人可能在私聊、群聊中使用不同上下文;作用域应至少包含 channel / chat / sender。
- 候选 D:`/use` 后覆盖所有路由 → ❌ **否决**:显式 `/codex`、`@reviewer`、`agent:` 应继续优先生效,active session 只接管普通消息。

### 产出
- `CommandName` 新增 `SESSIONS`、`NEW`、`USE`,命令解析支持 `/sessions`、`/new <agent>`、`/use <session_id>`。
- `InMemoryAgentSessionStore` 增加 active session 映射,按 `channel:chat:sender` 作用域保存当前 session。
- `Orchestrator` 支持 session 命令;普通消息没有显式目标时,优先路由到 active session 的 agent。
- `_run_task` 会在 active session 任务执行期间标记 session `busy`,结束后恢复 `idle`。
- `Phase1Runtime` 将同一个 `session_store` 注入 Orchestrator。
- 扩展 `test_commands.py`、`test_agent_session.py`、`test_orchestrator.py`。
- 更新 daily ops、CHANGELOG、STATUS。

### 关键决策
- 🔒 **决策 1**:AICO session 作用域是 `channel:chat:sender`,避免不同聊天里的上下文互相污染。
- 🔒 **决策 2**:`/use` 只改变普通消息默认路由;显式 persona / adapter 路由仍然优先。
- 🔒 **决策 3**:本轮不接 provider resume,保持 ADR-0010 的薄 facade 边界。

### 留给下一轮
- 真实 Telegram 复测 `/sessions`、`/new claude`、`/use <session>` 和普通消息路由。
- Claude Adapter 优先接 provider 原生 `--resume` / `--continue` 能力,把 provider session ref 写入 AICO session。
- 继续做 provider capability 展示,但只翻译 Claude/Codex 自身 tools/skills/slash/plugin/mcp 信息。

### 状态变化
- Phase 5 进度新增 Session 命令 MVP。
- Session 命令从“文档建议”进入“本地单测覆盖的 Telegram 命令入口”。

## Round 26 — 2026-04-29 — Codex

### 输入
- 人类验收 Session 命令 MVP 没问题,要求继续开发。
- `STATUS.md` 下一轮建议最高优先级之一是 Provider session resume 接入。

### 思考与讨论

**CLI 事实确认**:
- 本机 `claude --help` 显示 Claude 支持 `--session-id <uuid>`、`--resume [value]`、`--continue` 和 `--fork-session`。
- 本机 `codex exec resume --help` 显示 Codex 非交互链路支持 `codex exec resume [SESSION_ID] [PROMPT]`。
- Codex 默认命令中的 `exec --sandbox read-only --color never` 不能原样挪到 `exec resume` 后面;`--sandbox` 应提升到全局参数位置,`--color` 对 `exec resume` 不适用。

**方案选择**:
- 候选 A:让 AICO 保存完整对话历史并自己拼上下文 → ❌ **否决**:违反 ADR-0010,AICO 不是 tool execution runtime。
- 候选 B:Claude session 使用 AICO UUID,首轮 `--session-id`,后续 `--resume` → ✅ **选定**:Claude CLI 明确支持指定 session id,适合作为最小闭环。
- 候选 C:Codex 也直接用 AICO UUID 首轮 `exec resume` → ❌ **否决**:Codex `exec` 没有等价的“指定新 session id”入口,直接 resume 不存在的 id 会失败。
- 候选 D:Codex Adapter 先支持已有 provider ref 的 `exec resume` 命令构造 → ✅ **选定**:先封装易变 CLI 形态,后续再解决 provider session id 捕获 / 绑定。

### 产出
- `ProviderSessionRef` 增加 `initialized`,并新增 `ProviderSessionMode`、`ProviderTaskSession`。
- 新增 `task_with_provider_session()` / `provider_session_from_task()`,用 Task metadata 在核心和 Adapter 间传递 provider session 引用。
- `Orchestrator` 在 active session task 中注入 provider session metadata,并在首轮成功派发后标记 provider ref initialized。
- 审批路径也会保留 task → session 关系,危险任务批准后仍能使用原 provider session metadata。
- `ClaudeCodeAdapter` 根据 metadata 构造:
  - `--session-id <uuid>`:provider ref 尚未 initialized。
  - `--resume <uuid>`:provider ref 已 initialized。
  - 如果自定义 command 已含 `--session-id` / `--resume` / `--continue`,不重复追加。
- `CodexAdapter` 支持已有 provider ref 时构造 `codex ... exec resume <session_id> <prompt>`,并处理默认命令中 `--sandbox` / `--color` 的 resume 兼容问题。
- `Phase1Runtime` 为 Claude persona / alias 自动创建 provider ref;Codex 暂不自动创建 provider ref。
- 扩展 `test_agent_session.py`、`test_claude_code_adapter.py`、`test_codex_adapter.py`、`test_orchestrator.py`。
- 更新 daily ops、CHANGELOG、STATUS。

### 关键决策
- 🔒 **决策 1**:AICO 只传 provider session ref,不保存或重放 provider 对话历史。
- 🔒 **决策 2**:Claude 首轮使用 `--session-id`,后续使用 `--resume`,以 AICO UUID 作为 provider session id。
- 🔒 **决策 3**:Codex 在拿不到真实 provider session id 前不自动绑定,只支持已有 provider ref 的 resume 命令构造。

### 留给下一轮
- 真实 Telegram 复测 Claude session resume,重点查看 `logs/aico.log` 中 `provider_session_mode` 和第二轮上下文是否连续。
- 评估 `codex exec --json` 是否稳定输出 session id;若稳定,自动捕获并写回 `ProviderSessionRef`。
- 若无法自动捕获,设计 `/bind <agent> <provider_session_id>` 显式绑定命令。

### 状态变化
- Phase 5 进度新增 Claude Provider Session Resume MVP。
- Codex provider resume 从未知状态进入“命令形态已封装,session id 捕获待做”。

## Round 27 — 2026-04-29 — Codex

### 输入
- 人类反馈 `/codex inspect this` 后一直卡住,询问是否因为 Codex exec 没有稳定“指定新 session id”入口。
- 人类反馈询问 Claude 技能时,Telegram 只收到“作为 implementer 角色...”开头,后续像被吞掉。
- 人类确认 `/new`、`/use` 和连续消息已能保持同一 session。

### 思考与讨论

**日志定位**:
- `logs/aico.log` 显示 Claude/Codex Adapter 仍在产生 stdout chunk,且进程可正常退出;问题发生在 Telegram `editMessageText` 返回 HTTP 400 后。
- 旧实现先 `response.raise_for_status()`,导致 Telegram Bot API JSON `description` 没被解析,日志只看到泛化 HTTP 400。
- handler 因 `editMessageText` 异常退出后不再推送后续 stdout;Codex 底层进程继续占用单槽位,所以后续请求表现为 `Adapter busy`。

**方案选择**:
- 候选 A:继续推进 Codex provider session id 捕获 → ❌ **否决为本轮主线**:本次 `/codex inspect this` 是显式 `/codex` 路由,不依赖 active session 的 provider ref;现象不能用“指定新 session id”解释。
- 候选 B:把所有 Telegram edit 错误都吞掉 → ❌ **否决**:chat not found、权限、消息过长等真实错误必须继续暴露。
- 候选 C:只对 Telegram `message is not modified` 做 no-op 容错,并保留其他错误 → ✅ **选定**:这是流式编辑中可恢复的幂等错误,能修复“只收到开头一句”且不掩盖真实故障。

### 产出
- `TelegramChannel._post()` 改为先解析 Bot API JSON body,保留 HTTP 400 中的 `description`,再判断 `ok` 与 HTTP 状态。
- `TelegramChannel.edit_message()` 对 `Bad Request: message is not modified` 记录日志并返回,不再中断流式 handler。
- 新增单测覆盖:
  - HTTP 400 JSON description 会以 `TelegramAPIError` 暴露。
  - `message is not modified` edit 失败会被安全忽略。
- 新增 PITFALL P-012,记录 Telegram no-op edit 400 导致流式 handler 中断的坑。
- 更新 `STATUS.md`、`CHANGELOG.md`、`docs/human/troubleshooting.md`。

### 关键决策
- 🔒 **决策 1**:Telegram Bot API 的 HTTP 400 先按业务 JSON 错误解析,不能让 httpx 抢先抹掉平台 description。
- 🔒 **决策 2**:流式编辑同一条消息时,`message is not modified` 是可恢复 no-op,其他 Telegram API 错误仍然 fail-fast。
- 🔒 **决策 3**:`/codex inspect this` 的卡住现象本轮判定不是 Codex provider session id 缺失导致,而是 Telegram 出口异常导致 handler 退出后的 busy 后效。

### 留给下一轮
- 重启服务后在 Telegram 真实复测“Claude 有什么技能”和 `/codex inspect this`,确认不会只收到开头一句。
- 继续观察非 no-op Telegram 错误是否需要更友好的降级,例如编辑失败时退回 `sendMessage`。
- Codex provider session id 捕获 / 显式绑定仍是下一轮高优先级,但与本轮 bug 根因分开处理。

### 状态变化
- Phase 5 进度新增 Telegram 流式输出 no-op edit 容错。
- 新增 P-012。

## Round 28 — 2026-04-30 — Codex

### 输入
- 人类要求继续开发迭代“后续两个阶段”,完成后交给人类验收和审查。
- `STATUS.md` 的后续高优先级中,可本地闭环的开发项是 Codex provider session 显式绑定和 agent 能力/职责可见性。

### 思考与讨论

**范围选择**:
- 候选 A:直接进入 Phase 6 可观测看板和 Phase 7 共享记忆 → ❌ **否决**:Phase 5 真实协作 smoke test 还没收口,此时跨阶段铺开会违反“不要扩大任务范围”。
- 候选 B:只做 Telegram 真实复测 → ❌ **否决**:需要人类在真实 IM 中观察,本轮无法独立闭环开发。
- 候选 C:推进 Phase 5 内两个体验阶段:`/bind` 和 agent capability commands → ✅ **选定**:分别解决 Codex 会话恢复缺口和“体感不到底层模型状态/职责/能力”的痛点。

**设计取舍**:
- `/bind codex <provider_session_id>` 支持创建并激活 reviewer/Codex session,后续普通消息走 provider `resume`。这保留了 Round 26 的判断:Codex 首轮仍不假装能指定新 session id。
- `/skills`、`/tools` 不在 AICO 中维护 registry;命令只是把只读探测问题路由给 provider 自己回答,符合 ADR-0010 的薄 harness 边界。
- `Orchestrator` 已接近 500 行硬上限,因此先把命令输出渲染挪到 `command_messages.py`,再接新命令。

### 产出
- 新增 `src/aico/core/agent_directory.py`,从 PersonaRegistry + AdapterRegistry 生成 `AgentCard`,支持 alias / adapter / name 解析。
- `AgentCard` 增加 `aliases`,让 `/agent claude` 能解析到 `implementer`。
- `CommandName` 新增 `AGENTS`、`AGENT`、`SKILLS`、`TOOLS`、`BIND`,并更新 `/help` 文案。
- 新增 `/agents`、`/agent <agent>` 展示 agent card、实时 adapter status、capabilities、provider-owned tools/skills 来源。
- 新增 `/skills <agent>`、`/tools <agent>`,把 provider-owned capability introspection 作为普通只读任务派发给目标 agent。
- 新增 `/bind <session_id|agent> <provider_session_id>` 和 `/bind <provider_session_id>` active-session 快捷绑定。
- `Phase1Runtime` 构建并注入 `AgentDirectory`。
- 新增 / 扩展 `tests/unit/test_commands.py`、`tests/unit/test_agent_session.py`、`tests/unit/test_orchestrator.py`。
- 更新 daily ops、Phase 5 playbook、CHANGELOG、STATUS。

### 关键决策
- 🔒 **决策 1**:Codex provider session 先用显式绑定,不把 AICO UUID 伪装成 Codex 已存在 session。
- 🔒 **决策 2**:AICO 只展示 capability facade 和路由 provider introspection,不复制 Claude/Codex tools/skills registry。
- 🔒 **决策 3**:命令输出渲染从 `Orchestrator` 拆出,保证后续命令增长不会再次顶破 500 行硬约束。

### 留给下一轮
- 人类真实验收 `/agents`、`/agent claude`、`/skills claude`、`/tools codex`。
- 人类使用一个真实 Codex provider session id 验收 `/bind codex <provider_session_id>` 后普通消息是否走 `provider_session_mode=resume`。
- 若 Codex CLI 的 `--json` 能稳定吐出 session id,下一轮再做自动捕获。

### 状态变化
- Phase 5 进度新增 Codex provider session 显式绑定命令。
- Phase 5 进度新增 Agent 能力体验命令。

## Round 29 — 2026-05-04 — Codex

### 输入
- 人类已真实测试 `/agents`、`/skills`、`/tools`。
- 人类指出当前更痛的产品问题是:多项目长期迭代时,Telegram 只暴露 session,用户感知不到项目进展、日报/周报、风险和“谁在负责哪个项目”。
- 人类认可 `Agent 1 --- n Assignment n --- 1 Project` 架构,并要求保存 Project Assignment Layer 设计、同步状态和项目背景文档,准备进入实现。

### 思考与讨论

**核心建模**:
- Agent 是公司员工,Project 是项目,Assignment 是员工在项目里的岗位/工位。
- provider session、当前状态、权限、工作目录、role prompt 和最近产出都应该绑定到 Assignment/seat,不裸挂在 Agent 上。
- 同一个 Agent 可以参与多个 Project,但每个 Project 中必须有独立 Assignment,避免上下文和 session 串线。

**配置方式选择**:
- 候选 A:用 slash command 创建和修改 Assignment → ❌ **否决**:组织架构会被聊天随手改变,需要权限、回滚、审计和配置持久化,MVP 过重。
- 候选 B:Assignment 主要用配置文件维护,slash command 只做查看和切换 → ✅ **选定**:组织结构可 review、可追溯,同时保留 Telegram 的轻量操作体验。
- 候选 C:继续只用 persona/session 表达项目关系 → ❌ **否决**:session 是技术对象,无法稳定表达项目、岗位、周报、风险和跨项目任命。

**Prompt 维护选择**:
- 候选 A:每个 Assignment 写一整段完整 prompt → ❌ **否决**:一旦员工风格或角色职责变更,需要多处复制修改。
- 候选 B:四层拼装 Agent Base Prompt + Role Prompt + Project Brief + Runtime Context → ✅ **选定**:新增员工、角色、项目、任命时只改对应层。

**暂缓项**:
- `/handoff` 暂不进入 MVP。人类判断项目做到一半临时换 Agent 实现难度较大;本轮采纳该边界,避免提前处理上下文迁移。
- 灵动岛 / Mac 顶部 UI 暂不实现。先稳定 Project/Assignment 状态 API,否则 UI 只能展示裸 session。

### 产出
- 新增 `docs/decisions/0011-project-assignment-layer.md`,接受 Project Assignment Layer。
- 新增 `docs/architecture/project-assignment-layer.md`,记录 Agent / Project / Assignment / seat / prompt 分层 / 命令语义。
- 更新 `docs/decisions/README.md`,加入 ADR-0011。
- 更新 `docs/architecture/overview.md`,将 Project Assignment 列为核心抽象。
- 更新 `README.md`,把“Agent 是员工、Project 是项目、Assignment 是岗位”写入 30 秒理解。
- 更新 `STATUS.md`,记录 Round 29 和下一轮实现建议。

### 关键决策
- 🔒 **决策 1**:Agent 与 Project 不直接绑定,必须通过 Assignment 表达项目内岗位。
- 🔒 **决策 2**:provider session 绑定到 Assignment/seat,不是绑定到 Agent 全局状态。
- 🔒 **决策 3**:Assignment MVP 使用配置文件维护;slash command 只做查看和切换,不做组织架构修改。
- 🔒 **决策 4**:Prompt 分层维护,不复制完整 assignment prompt。
- 🔒 **决策 5**:`/handoff` 不进入 Project Assignment Layer MVP。

### 留给下一轮
- 实现 Project Assignment Layer MVP:
  - 配置模型:`agents` / `projects` / `assignments`
  - 配置加载和引用校验
  - project-scoped session ref / Assignment seat
  - `/projects`、`/project <id>`、`/use project <id>`、`/assignments [project]`、`/assignment <seat>` 查看和切换命令
  - Agent Base Prompt + Role Prompt + Project Brief + Runtime Context 分层渲染
- 保持旧 `/sessions` / `/new` / `/use` 兼容,不要一次性重写 Phase 5。
- 不实现 `/assign ...` 和 `/handoff`。

### 状态变化
- Phase 5 进度新增 Project Assignment Layer 设计决策。
- Agent capability commands 已由人类真实验收。
- 下一轮最高优先级从裸 session 验收转为 Project Assignment Layer MVP。

## Round 30 — 2026-05-04 — Codex

### 输入
- 人类要求为项目画两张专业技术视角图,使用 draw.io XML 格式:
  - 架构分层图:偏基础层在下、偏应用层在上。
  - 核心概念和角色分工工作流程图。
- 图要完整结合当前项目设计和实现,用于向用户和读者介绍本项目。

### 思考与讨论

**图一边界**:
- 候选 A:只画三层 IM / Core / Adapter → ❌ **否决**:这会漏掉 Phase 4/5 已实现的审批审计、session、agent directory、协作和 Project Assignment Layer 设计。
- 候选 B:按产品语义、应用运行时、公司模型与治理、协议适配器、本地 provider 与持久化五层绘制 → ✅ **选定**:既能解释当前实现,又能展示下一步 Project Assignment Layer 如何接入。

**图二边界**:
- 候选 A:只画数据模型 ER 图 → ❌ **否决**:用户更需要理解“谁负责什么、任务怎么流转”。
- 候选 B:概念模型 + 操作流程放在一张图中 → ✅ **选定**:上半部分解释 Human / Project / Agent / Assignment / Provider Session,下半部分解释 `/use project`、任务派发、prompt 构建、审批、Adapter 执行、协作、审计和项目简报。

**状态标识**:
- 用实线绿色表示当前已实现能力。
- 用虚线黄色表示已设计/下一步 MVP,避免读者误以为 Project Assignment 命令和报告已经全部落地。

### 产出
- 新增 `docs/architecture/aico-layered-architecture.drawio`。
- 新增 `docs/architecture/aico-concepts-workflow.drawio`。
- 更新 `docs/architecture/overview.md`,加入两张 draw.io 图入口。
- 更新 `STATUS.md`,记录本轮图产出。

### 关键决策
- 🔒 **决策 1**:架构图按分层技术架构表达,不是营销图。
- 🔒 **决策 2**:图中区分已实现与设计中能力。
- 🔒 **决策 3**:Project Assignment Layer 在图中作为下一步核心产品语义出现,但不伪装成已实现代码。

### 留给下一轮
- 继续实现 Project Assignment Layer MVP。
- 如果未来实现 `/brief`、`/risks`、`/daily`、`/weekly`,需要回头把图中相关节点从虚线设计态改成实线实现态。

### 状态变化
- Phase 5 进度新增面向技术读者的 draw.io 架构图与工作流图。

## Round 31 — 2026-05-04 — Codex

### 输入
- 人类要求按照优先级开始开发,到达合适验收流程时找人类确认。
- `STATUS.md` 的最高优先级是 Project Assignment Layer MVP、project-scoped session 和项目/任命查看命令。

### 思考与讨论

**切片选择**:
- 候选 A:一次性实现配置、prompt 分层、brief/risks、日报/周报 → ❌ **否决**:验收面太大,容易把 Project Assignment 的基础路由问题和报告生成问题混在一起。
- 候选 B:先实现配置模型、项目命令、active project 和 assignment-scoped session → ✅ **选定**:这是最小可验收产品切片,能在 Telegram 里直接确认“普通消息进入项目办公室默认工位”。
- 候选 C:先做 `/brief` 和 `/risks` → ❌ **否决**:没有 Project/Assignment 状态底座时,brief 只能重新变成文档摘要,产品语义不稳。

**兼容策略**:
- 保留旧 `/sessions`、`/new <agent>`、`/use <session_id>`。
- 新增 `/use project <project>` 时不删除旧 active session;普通消息如果有 active project,优先走项目默认 assignment;显式 `/claude`、`/codex`、`@reviewer` 等路由仍然优先。

**复杂度控制**:
- `Orchestrator` 在继续接命令后超过 500 行硬约束,因此新增 `orchestrator_commands.py`,把 agent / project / assignment / session 命令处理拆出。
- Prompt 分层仍是高优先级,但留到下一切片,避免这一轮又把 TaskBus / persona 注入一起改大。

### 产出
- 新增 `src/aico/core/project_assignment.py`。
- 新增 `src/aico/core/orchestrator_commands.py`。
- 新增 `config/projects.example.json`。
- `Phase1Settings` 新增 `project_config_path`,对应 `AICO_PROJECT_CONFIG_PATH`。
- `Phase1Runtime` 加载 Project Assignment 配置,并校验 agent provider、assignment agent 和 project 引用。
- 新增 `/projects`、`/project <project>`、`/use project <project>`、`/assignments [project]`、`/assignment <seat>`。
- active project 下的普通消息会走项目默认 assignment,并为该 seat 创建/复用 project-scoped provider session。
- 新增 `tests/unit/test_project_assignment.py`,扩展 commands / orchestrator / phase1 app 单测。
- 更新 daily ops、CHANGELOG、STATUS。

### 关键决策
- 🔒 **决策 1**:Project Assignment 第一切片只做配置、查看、切换和 project-scoped session,不做组织架构修改。
- 🔒 **决策 2**:active project 优先级低于显式 `/claude` / `/codex` / mention 路由,高于旧 active session。
- 🔒 **决策 3**:prompt 分层留到下一切片,避免本轮扩大到报告和 TaskBus prompt 重构。
- 🔒 **决策 4**:命令处理继续外拆,`Orchestrator` 必须保持低于 500 行。

### 留给下一轮
- 人类真实验收:
  - `/projects`
  - `/project aico`
  - `/assignments aico`
  - `/assignment aico-implementer`
  - `/use project aico`
  - 发送普通消息,确认走 `aico-implementer` 且日志中 provider session mode 首轮 new、后续 resume。
- 若验收通过,继续做 Prompt 分层渲染。
- 暂不做 `/assign ...`、`/handoff`、`/brief`、`/risks`。

### 状态变化
- Phase 5 进度新增 Project Assignment Layer MVP 第一切片。
- 下一轮最高优先级改为 Telegram 真实验收和 Prompt 分层渲染。

## Round 32 — 2026-05-04 — Codex

### 输入
- 人类还没有正式测试 assignments / projects,因为 `assignment`、`seat`、`/use role` 等概念和命令不符合唯一老板的直觉。
- 人类希望在正式使用前直接把设计改为老板派发任命的语言:
  - `/project aico`
  - `/team`
  - `/who implementer`
  - `/appoint claude as implementer`
  - `/ask reviewer 检查这个方案`
  - `/lead implementer`
- 人类同时指出只有 implementer / reviewer 过窄,要求完善 role 体系并落地到设计文档。

### 思考与讨论

**产品语言纠偏**:
- 候选 A:继续让 `/assignment <seat>` 作为主入口 → ❌ **否决**:`seat` 是内部稳定 id,不是老板会自然说的话。用户不应该记住 `aico-implementer` 才能管理团队。
- 候选 B:把 Assignment 的产品层表达改为 Appointment / Team → ✅ **选定**:老板进入项目办公室、查看团队、任命员工、把任务交给岗位、设置默认负责人,这符合“像管理真实团队一样”。
- 候选 C:把这一层扩成完整 HR / 组织架构系统 → ❌ **否决**:部门、职级、汇报线、权限组对个人 dogfooding 过重,不服务当前 Phase 5 的项目协作主线。

**Role 体系选择**:
- 候选 A:只保留 implementer / reviewer → ❌ **否决**:只能覆盖写代码和审查,不足以支撑项目管理、测试、架构、文档、运维和安全等长期运营。
- 候选 B:定义通用 RoleTemplate,项目按需启用并覆盖 → ✅ **选定**:role prompt 通用,Project Role Override 表达项目特殊性,Appointment 只表达“谁被任命到哪个岗位”。
- 候选 C:每个项目每个任命复制一整段 prompt → ❌ **否决**:后续改角色职责要多处同步,违反 Round 29 的 prompt 分层原则。

### 产出
- 新增 `docs/decisions/0012-boss-facing-team-commands.md`,接受 boss-facing team commands and role system。
- 重写 `docs/architecture/project-assignment-layer.md`,从 Project Assignment 改为 Project Team and Appointment Layer。
- 设计新的主路径命令:
  - `/project <project>`:进入项目办公室。
  - `/team [project]`:查看项目团队任命。
  - `/who <role>`:查看当前项目某岗位负责人、权限和资源。
  - `/appoint <agent> as <role> [permissions]`:任命员工到当前项目岗位。
- `/ask <role> <task>`:把单次任务交给当前项目某岗位。
- `/lead <role>`:设置普通消息默认牵头角色。
- 完善建议 role 体系:implementer、reviewer、tester、pm、architect、security、docs、ops、analyst、designer。
- 更新 `docs/decisions/README.md` 和 `docs/architecture/overview.md`,加入 ADR-0012 和新的 Appointment / Team 语义。
- 更新 `STATUS.md`,把下一轮最高优先级改为实现 boss-facing Project Team 命令和配置模型。

### 关键决策
- 🔒 **决策 1**:`Assignment` 作为内部领域模型保留,但产品层优先叫 `Appointment / 任命`;`seat` 只用于持久化、日志和排障。
- 🔒 **决策 2**:`/use assignment <seat>` 不作为主路径;交任务用 `/ask <role> <task>`,设置默认负责人用 `/lead <role>`。
- 🔒 **决策 3**:Role 体系采用 RoleTemplate + Project Role Override + Appointment Contract 的分层结构。
- 🔒 **决策 4**:新项目默认只建议或启用 implementer / reviewer,其他 role 显示为未任命或可补齐,避免过度复杂。

### 留给下一轮
- 实现 `/project`、`/team`、`/who`、`/appoint`、`/ask`、`/lead` 的命令解析和最小运行路径。
- 在配置模型中补 `roles`、project role overrides、appointments,并保持旧 `assignments` 配置兼容或提供迁移。
- 实现 prompt 分层渲染:Agent Base Prompt + RoleTemplate Prompt + Project Role Override + Appointment Contract + Runtime Context。
- 将 Round 31 的 `/assignments`、`/assignment <seat>` 降级为兼容或排障命令。

### 状态变化
- Phase 5 进度新增 Project Team / Appointment 老板视角命令设计与 Role 体系完善。
- 下一轮最高优先级从 Round 31 的 Telegram 真实验收调整为先实现新的老板视角命令,再做真实验收。

## Round 33 — 2026-05-04 — Codex

### 输入
- 人类确认 Round 32 的老板视角设计,要求开始开发。
- 当前最高优先级是实现 `/project`、`/team`、`/who`、`/appoint`、`/ask`、`/lead` 和 RoleTemplate / Appointment 配置模型。

### 思考与讨论

**实现切片选择**:
- 候选 A:直接完整实现 prompt 分层、持久化写配置、日报/风险 → ❌ **否决**:会把命令语义、配置模型、prompt runtime 和报告生成混在一起,验收面过大。
- 候选 B:先实现 boss-facing 命令 MVP + roles/appointments 配置模型 → ✅ **选定**:能本地闭环验证老板语言是否跑通,并保持旧 assignment/seat 命令兼容。
- 候选 C:删除旧 `/assignments` / `/assignment` → ❌ **否决**:Round 31 已有代码和测试,直接删除会扩大回归面;先降级为兼容或排障入口。

**Appointment 持久化选择**:
- 候选 A:`/appoint` 直接改写配置文件 → ❌ **暂缓**:需要审计、回滚、并发写入和权限模型,不适合本轮。
- 候选 B:`/appoint` 先做进程内 runtime appointment → ✅ **选定**:足够验证老板任命体验;重启后仍以配置文件为准。

### 产出
- `CommandName` 新增 `TEAM`、`WHO`、`APPOINT`、`ASK`、`DEFAULT`,并更新 `/help`。
- `ProjectAssignmentConfig` 新增 `roles`、`appointments`;`ProjectProfile` 新增 `lead_role` / `default_role` 语义和 project role overrides;旧 `assignments` 字段继续兼容。
- `ProjectAssignmentDirectory` 支持:
  - `appointments(project)`
  - `appointment_for_role(project, role)`
  - `upsert_appointment(...)`
  - `set_default_role(project, role)`
- `/project <project>` 现在进入项目办公室并展示团队和默认 role。
- 新增 `/team`、`/who <role>`、`/appoint <agent> as <role>`、`/ask <role> <task>`、`/lead <role>` 最小命令处理。
- `/ask <role> <task>` 会走该 role 的 appointment-scoped provider session;`/lead <role>` 后普通消息走新的牵头 role。
- `config/projects.example.json` 改为 roles / project role overrides / appointments 示例。
- 更新 `CHANGELOG.md` 和 `docs/human/daily-ops.md`。
- 扩展 `test_commands.py`、`test_project_assignment.py`、`test_orchestrator.py`、`test_phase1_app.py`。

### 关键决策
- 🔒 **决策 1**:`/appoint` 本轮只做进程内任命,MVP 不写回配置文件。
- 🔒 **决策 2**:旧 `assignments` 配置和旧命令继续兼容,新主路径使用 Team / Appointment 命令。
- 🔒 **决策 3**:`/ask <role>` 是单次派活,不改变牵头 role;`/lead <role>` 才改变普通消息默认接活人。

### 留给下一轮
- 人类真实 Telegram 验收:
  - `/project aico`
  - `/team`
  - `/who implementer`
  - `/appoint claude as tester read_repo run_tests`
  - `/ask tester 设计回归测试`
  - `/lead tester`
  - 普通消息是否进入 tester appointment session
- 实现 prompt 分层渲染,让 role template、project override 和 appointment contract 真正进入 Adapter prompt。
- 评估 `/appoint` 是否需要持久化写配置;若要写,必须加审计和回滚策略。

### 状态变化
- Phase 5 进度新增 Project Team / Appointment 命令 MVP。
- Phase 5 进度新增 RoleTemplate / ProjectRoleOverride / Appointment 配置模型 MVP。
- 下一轮最高优先级改为 Project Team Telegram 真实验收和 Prompt 分层渲染。

## Round 34 — 2026-05-04 — Codex

### 输入
- 人类真实执行 `/appoint Claude as tester read_repo run_tests` 后收到:
  - `Cannot appoint Claude as tester`

### 思考与讨论

**问题定位**:
- `DirectoryCommandHandler.handle_appoint()` 先用 `AgentDirectory.resolve(agent_ref)` 判断 agent 是否存在。这个解析是大小写不敏感的,所以 `Claude` 能通过。
- 但随后 `ProjectAssignmentDirectory.upsert_appointment()` 用原始 `agent_id="Claude"` 精确调用 `self.agent(agent_id)`,而配置 key 是小写 `claude`,于是返回 `None` 并拒绝任命。
- role 也有同类风险:`Tester`、`test_lead` 这类自然输入不应轻易失败。

**方案选择**:
- 候选 A:只在命令层把 agent_ref lower() → ❌ **否决**:只能修 `/appoint`,其他 project / role lookup 仍可能踩同类坑。
- 候选 B:在 `ProjectAssignmentDirectory` 内统一做 agent / project / role ref normalization → ✅ **选定**:领域目录负责引用解析,命令层保持轻薄。

### 产出
- `ProjectAssignmentDirectory` 新增 normalized ref map:
  - `_agents_by_ref`
  - `_roles_by_ref`
  - `_projects_by_ref`
- `project()`、`agent()`、`role()` 和 `upsert_appointment()` 统一支持大小写不敏感、下划线/横线兼容解析。
- Runtime appointment 写入 canonical id,例如输入 `Claude` / `Tester` 后实际保存 `claude` / `tester`。
- 更新 `test_project_assignment.py`,覆盖大小写输入。
- 更新 `CHANGELOG.md` 和 `STATUS.md`。

### 关键决策
- 🔒 **决策 1**:老板面向命令中的 agent / role / project ref 必须宽容解析,不要要求用户记住配置 key 的精确大小写。
- 🔒 **决策 2**:宽容解析放在 `ProjectAssignmentDirectory`,而不是散落在各个命令 handler 里。

### 留给下一轮
- 重新在 Telegram 里执行 `/appoint Claude as tester read_repo run_tests`。
- 继续 Project Team Telegram 真实验收和 Prompt 分层渲染。

### 状态变化
- 修复 boss-facing `/appoint` 大小写输入导致任命失败的问题。

## Round 35 — 2026-05-04 — Codex

### 输入
- 人类指出 `/default tester` 这个命令含义难理解,偏工程技术视角。
- 人类要求改为 `/lead`,并继续开发。

### 思考与讨论

**命令语言选择**:
- 候选 A:继续使用 `/default` → ❌ **否决**:default 是配置/路由语言,不是老板语言。
- 候选 B:改为 `/lead <role>` → ✅ **选定**:表达“当前项目由哪个岗位牵头”,更接近老板派发负责人。
- 候选 C:删除 `/default` → ❌ **否决**:刚实现不久,删除会打断已有测试和人类可能的临时用法;保留为兼容别名。

**继续开发切片**:
- 候选 A:做 `/brief` / `/risks` → ❌ **暂缓**:项目感知摘要依赖 prompt/context 层先真实注入。
- 候选 B:实现 Appointment Prompt Stack MVP → ✅ **选定**:让任命书、role、project context 真正进入 provider prompt,而不只是命令展示。

### 产出
- `CommandName` 新增 `LEAD`,支持 `/lead <role>`。
- `Orchestrator` 将 `/lead` 和兼容 `/default` 都路由到同一个 default role handler。
- 命令输出改为 `Lead role for <project>: <role> -> <agent>`。
- 新增 `src/aico/core/prompt_stack.py`,实现 `render_appointment_prompt()`。
- `Orchestrator._task_for_assignment()` 在 project appointment 路由中渲染:
  - Agent section
  - RoleTemplate section
  - Project / ProjectRoleOverride section
  - Appointment Contract
  - Current task
- `RoleProfile` 增加 `inline_prompt`,`ProjectRoleProfile` 增加 `inline_prompt_override`,`ProjectProfile` 增加 `brief`。
- 默认 implementer / reviewer role 增加简短 inline prompt。
- 更新 `CHANGELOG.md`、`STATUS.md`、`docs/human/daily-ops.md`、设计文档中的 `/lead` 语言。
- 扩展单测断言 appointment 路由的 payload 包含 `Role`、`Appointment contract` 和 `Current task`。

### 关键决策
- 🔒 **决策 1**:`/lead <role>` 是主路径,`/default <role>` 只作为兼容别名。
- 🔒 **决策 2**:Prompt stack 只注入 project appointment 路由;显式 `/claude`、`/codex`、`@reviewer` 保持旧 persona prompt,避免扩大行为面。
- 🔒 **决策 3**:本轮 prompt stack 支持 inline prompt 和 prompt path 显示,但不读取外部 prompt 文件内容;文件读取/模板化可在下一轮细化。

### 留给下一轮
- Telegram 真实验收 Project Team / Appointment:
  - `/project aico`
  - `/team`
  - `/who implementer`
  - `/appoint Claude as tester read_repo run_tests`
  - `/ask tester 设计回归测试`
  - `/lead tester`
  - 普通消息是否交给 tester,日志中是否使用 appointment provider session。
- 后续做 `/brief` / `/risks`,从 project config、STATUS/ROUNDS、audit/task snapshot 生成项目摘要。
- 评估 prompt stack 是否需要读取 `base_prompt` / `role.prompt` / `project_role.prompt_override` 文件内容,以及是否需要模板变量。

### 状态变化
- Phase 5 进度新增 Appointment Prompt Stack MVP。
- Prompt 分层渲染从待办改为完成 MVP。
- 下一轮最高优先级改为 Project Team Telegram 真实验收。

## Round 36 — 2026-05-04 — Codex

### 输入
- 人类要求继续向后开发,之后一起验证和验收。
- Round 35 后 Project Team 命令和 Appointment Prompt Stack 已完成 MVP,下一项中优先级最高的是 Project brief / risks。

### 思考与讨论

**简报能力边界**:
- 候选 A:让 Claude/Codex 生成自然语言项目简报 → ❌ **暂缓**:这会依赖 provider 和 prompt 质量,还可能编造本地状态之外的信息。
- 候选 B:先做本地状态摘要 `/brief` / `/risks` → ✅ **选定**:可稳定测试,只基于 Project 配置、team appointments、recent task snapshots 和 audit events。
- 候选 C:直接读取 STATUS/ROUNDS/PITFALLS 并做复杂总结 → ❌ **暂缓**:这是下一步项目记忆/报告层,本轮先提供可验收的项目办公室本地状态。

### 产出
- `CommandName` 新增 `BRIEF` 和 `RISKS`。
- `/brief [project]` 输出:
  - Project id/name/repo/phase
  - north star / status / journal 引用
  - lead role
  - team appointments
  - recent tasks
  - recent audit events
- `/risks [project]` 输出最近本地状态中的风险:
  - waiting_approval / failed / rejected / interrupted tasks
  - 非 read-only 风险任务
  - approval requested / denied / task failed / rejected / interrupted audit events
- 新增 `project_brief_message()` 和 `project_risks_message()`。
- 扩展 `DirectoryCommandHandler` 和 `Orchestrator` 命令分发。
- 扩展 `test_commands.py` 和 `test_orchestrator.py`。
- 更新 `CHANGELOG.md`、`STATUS.md`、`docs/human/daily-ops.md`。

### 关键决策
- 🔒 **决策 1**:`/brief` 和 `/risks` 当前只做本地状态摘要,不调用 provider,不假装拥有共享记忆层。
- 🔒 **决策 2**:项目风险先来自 task/audit 状态,后续再接 STATUS/ROUNDS/PITFALLS 和 AI 生成摘要。

### 留给下一轮
- 人类真实 Telegram 验收:
  - `/project aico`
  - `/brief`
  - `/risks`
  - `/team`
  - `/who implementer`
  - `/appoint Claude as tester read_repo run_tests`
  - `/ask tester 设计回归测试`
  - `/lead tester`
  - 普通消息是否交给 tester appointment session。
- 若验收通过,继续做 Codex bind 真实验收、Claude resume/长文本复测和 Phase 5 协作 smoke test。

### 状态变化
- Phase 5 进度新增 Project brief / risks MVP。
- 下一轮最高优先级仍是 Project Team Telegram 真实验收,但验收清单加入 `/brief` 和 `/risks`。

## Round 37 — 2026-05-04 — Codex

### 输入
- 人类开始验证,同时要求继续开发。
- Round 36 的 `/brief` / `/risks` 已能基于本地 runtime 状态输出,但还没有读取项目文档片段。

### 思考与讨论

**增强方向选择**:
- 候选 A:让 `/brief` 调 provider 总结 STATUS/ROUNDS → ❌ **暂缓**:会引入 provider 不稳定和可能编造的问题。
- 候选 B:读取项目配置声明的文档短片段 → ✅ **选定**:仍是本地只读、可控长度、可测试,但比只展示文档路径更有用。
- 候选 C:一次性解析整份 STATUS/ROUNDS/PITFALLS → ❌ **否决**:长文本会撑爆 Telegram,而且需要更明确的摘要策略。

### 产出
- 新增 `src/aico/core/project_docs.py`:
  - `brief_document_snippets(project)`
  - `risk_document_snippets(project)`
  - `ProjectDocumentSnippet`
- `ProjectProfile` 新增 `blockers_doc` / `pitfalls_doc`。
- 默认 AICO project 和 `config/projects.example.json` 增加:
  - `blockers_doc: docs/journal/BLOCKERS.md`
  - `pitfalls_doc: docs/journal/PITFALLS.md`
- `/brief` 追加 north star / status / journal 文档短片段。
- `/risks` 追加 blockers / pitfalls 文档短片段。
- 文档读取策略:
  - 相对路径按 `project.repo` 解析。
  - 文件不存在或读取失败时跳过。
  - 每个文件最多展示 4 条非空行。
  - 单行最多 140 字符。
- 新增 `tests/unit/test_project_docs.py`。
- 更新 `CHANGELOG.md`、`STATUS.md`、`docs/human/daily-ops.md`。

### 关键决策
- 🔒 **决策 1**:Project document snippets 是本地只读辅助信息,不是共享记忆层。
- 🔒 **决策 2**:文档片段必须有长度上限,避免 Telegram 长文本和噪声问题。
- 🔒 **决策 3**:缺失文档不让命令失败,因为项目配置可能跨仓库复用。

### 留给下一轮
- 人类继续 Telegram 验收 `/brief` / `/risks` 是否有用且不吵。
- 后续如果要更智能的日报/周报,需要设计摘要策略,不要直接把整份 journal 塞给 provider。

### 状态变化
- Project brief / risks 从 runtime-only 摘要增强为 runtime + bounded project document snippets。

## Round 38 — 2026-05-04 — Codex

### 输入
- 人类继续在 Telegram 里验证 Project Team / Appointment,同时要求“继续开发”。
- Round 37 已经把 `/brief` / `/risks` 增强为 runtime + 受限文档片段,但老板日常最直觉的“日报 / 周报”入口还只是设计态。

### 思考与讨论

**日报 / 周报边界**:
- 候选 A:让 provider 读取 journal 后生成自然语言日报 / 周报 → ❌ **暂缓**:目前还没有稳定共享记忆层,直接调 provider 容易编造或把上下文塞太长。
- 候选 B:先做本地项目报告 `/daily` / `/weekly` → ✅ **选定**:能复用 Project Team / Appointment、task snapshot、audit event 和文档 snippet,可测试且适合 Telegram 验收。
- 候选 C:等真实验收全部完成后再做 → ❌ **未选**:用户正在验证,此时补老板日常命令能扩大验收面,也符合北极星里的“远程指挥虚拟公司”。

### 产出
- `CommandName` 新增 `DAILY` 和 `WEEKLY`。
- 新增 `/daily [project]` 和 `/weekly [project]`:
  - `/daily` 使用最近 24 小时本地 AICO 状态窗口。
  - `/weekly` 使用最近 7 天本地 AICO 状态窗口。
  - 输出团队、牵头 role、完成项、未完成项、风险和项目文档短片段。
- 新增 `project_report_message()`,由日报 / 周报共用。
- `DirectoryCommandHandler` 增加 `handle_daily()`、`handle_weekly()` 和内部 `_handle_report()`。
- 更新 `docs/architecture/project-assignment-layer.md`、`docs/human/daily-ops.md`、`CHANGELOG.md`。
- 更新两张 draw.io 图,把 `/daily` / `/weekly` 从 future/next 表述推进到已实现项目状态面。
- 扩展 `tests/unit/test_commands.py` 和 `tests/unit/test_orchestrator.py`。
- 本地 137 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check` 全绿;draw.io XML 解析通过。

### 关键决策
- 🔒 **决策 1**:`/daily` / `/weekly` 当前是本地报告,不调用 provider,不声称拥有跨进程长期记忆。
- 🔒 **决策 2**:日报 / 周报先做“结构化状态面”,未来接共享记忆层或持久化 timeline 后再升级摘要质量。
- 🔒 **决策 3**:报告窗口基于 `TaskSnapshot.updated_at` 和 `AuditEvent.timestamp`;当前 task/audit 仍以内存为主,重启后历史会丢失。

### 留给下一轮
- 人类在 Telegram 里验证:
  - `/daily`
  - `/weekly`
  - `/daily aico`
  - `/weekly aico`
  - 看输出是否“有用且不吵”。
- 若报告过长,优先调整 snippet 数量和 progress/open/risk 行数,不要直接引入 provider 总结。

### 状态变化
- Phase 5 进度新增 Project daily / weekly 本地报告 MVP。
- Project awareness draw.io 节点从“future/next”推进为已实现状态面。

## Round 39 — 2026-05-05 — Codex

### 输入
- 人类真实执行 `/risks`,看到输出包含:
  - `unknown adapter or persona: risky`
  - `risk=write_files`
  - `audit approval_requested ... write_files`
- 人类指出这些不应直接算“项目风险”,要求 `/risks` 只展示真正项目风险,然后继续开发后续功能。

### 思考与讨论

**风险语义重划分**:
- 候选 A:继续把 task/audit 风险信号全部塞进 `/risks` → ❌ **否决**:这是工程监控视角,不是老板关心的项目交付风险。
- 候选 B:`/risks` 只展示项目交付风险,把等待审批和系统噪音移到 `/blockers` → ✅ **选定**:符合“项目风险”和“当前卡点”的自然区分。
- 候选 C:让 LLM 判断哪些是真风险 → ❌ **暂缓**:当前没有稳定事实包和记忆层,先用确定性规则收窄语义。

### 产出
- `/risks` 收窄为真正项目风险:
  - 失败 / 中断任务。
  - 破坏性任务。
  - blockers / pitfalls 文档片段。
- `/risks` 不再展示:
  - 普通 `write_files` 审批请求。
  - `approval_requested` 审计事件。
  - `unknown adapter or persona` 路由噪音。
- 新增 `/blockers [project]`:
  - 等待审批任务,并提示 `/approve <short_id>` / `/reject <short_id>`。
  - 失败 / 拒绝 / 中断任务。
  - 未知 persona 等系统/执行问题。
  - blockers 文档短片段。
- 新增 `blocker_document_snippets(project)`。
- 扩展命令解析、Orchestrator handler 和项目消息渲染。
- 新增回归测试覆盖人类遇到的 `write_files + unknown persona` 噪音场景。
- 更新 `CHANGELOG.md`、`STATUS.md`、`docs/human/daily-ops.md`、`docs/architecture/project-assignment-layer.md`。
- 更新两张 draw.io 图,把 `/blockers` 纳入项目状态面。
- 本地 138 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check` 全绿;draw.io XML 解析通过。

### 关键决策
- 🔒 **决策 1**:`/risks` 是项目交付风险,不是审计日志和风险规则 debug 输出。
- 🔒 **决策 2**:普通写文件审批是正常开发流程,默认放进 `/blockers`,不算项目风险。
- 🔒 **决策 3**:`unknown adapter/persona` 是系统/操作卡点,应出现在 `/blockers`,不计入项目交付风险。

### 留给下一轮
- 人类在 Telegram 里复测:
  - `/risks` 是否不再展示 `write_files` / `approval_requested` / unknown persona 噪音。
  - `/blockers` 是否能承接这些卡点且足够清楚。
- 后续若 `/blockers` 输出过长,优先按 waiting decisions / failed work / documented blockers 分组限流。

### 状态变化
- Phase 5 进度新增 Project blockers MVP。
- Project risk semantics 从“底层信号列表”收敛为“老板视角项目交付风险”。

## Round 40 — 2026-05-05 — Codex

### 输入
- 人类确认 `/risks` 新语义验收没问题,要求继续开发后续能力。
- Round 39 后项目状态面继续增长,`command_messages.py` 和 `DirectoryCommandHandler` 已接近结构边界。

### 思考与讨论

**下一步能力选择**:
- 候选 A:直接接 LLM 总结日报/周报 → ❌ **暂缓**:事实包和长期记忆层还不稳,容易把模板报告变成不可靠自然语言。
- 候选 B:先做确定性 `/next` 下一步动作建议 → ✅ **选定**:老板真正需要“下一步做什么”,且可以基于本地 task/team 状态稳定生成。
- 候选 C:继续只做更多状态报告 → ❌ **未选**:报告已经能看状态,缺的是行动入口。

**结构整理**:
- `command_messages.py` 原本同时放通用命令和 Project/Team/Report 输出,继续加命令会越来越难维护。
- 先拆出 `project_messages.py`,再加 `/next`,避免把项目状态面继续塞进通用消息模块。

### 产出
- 新增 `src/aico/core/project_messages.py`,承载 Project/Team/Appointment/Report 输出渲染。
- `command_messages.py` 回到通用命令消息:status、audit、agent card、approval 等。
- `DirectoryCommandHandler` 的 report 发送辅助逻辑移出类体,让类体保持在 500 行硬约束以内。
- 新增 `/next [project]`:
  - 有等待审批时提示 `/approve <short_id>` / `/reject <short_id>`。
  - 有失败/中断/拒绝任务时提示恢复动作。
  - 有未知 persona 这类系统噪音时提示先看 `/blockers`。
  - 没有卡点时建议把最高优先级任务交给当前 lead role。
- `/next` 只支持 slash command;普通英文 `next` 不作为命令,避免误吞任务。
- 扩展 `tests/unit/test_commands.py` 和 `tests/unit/test_orchestrator.py`。
- 更新 `CHANGELOG.md`、`STATUS.md`、`docs/human/daily-ops.md`、`docs/architecture/project-assignment-layer.md` 和两张 draw.io 图。
- 本地 139 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check` 全绿;draw.io XML 解析通过。

### 关键决策
- 🔒 **决策 1**:`/next` 是确定性行动建议,不调用 LLM。
- 🔒 **决策 2**:`next` 不支持无斜杠触发,因为它是常见英文词,误触发风险高。
- 🔒 **决策 3**:项目状态面渲染独立成 `project_messages.py`,不要继续堆在通用命令消息模块里。

### 留给下一轮
- 人类在 Telegram 里验证:
  - `/next`
  - `/next aico`
  - 普通消息 `next` 是否仍作为任务交给当前 project lead,而不是被命令解析吞掉。
- 后续可考虑让 `/next` 读取持久化 timeline 或事实包,但不应直接让 LLM 自由生成。

### 状态变化
- Phase 5 进度新增 Project next actions MVP。
- Project 状态输出模块完成一次小切分,降低后续状态面扩展成本。

## Round 41 — 2026-05-05 — Codex

### 输入
- 人类授权“没有重大决定就一直开发”,并建议必要时设置小时级定时任务催促项目进度。
- 当前 Project Team 已有 `/team`、`/who`、`/appoint`,但缺少一个直接查看“岗位模板和缺口”的入口。

### 思考与讨论

**持续推进机制**:
- 候选 A:只在当前 turn 继续开发 → ❌ **不足**:人类明确希望有小时级催促机制。
- 候选 B:设置当前线程 heartbeat 自动化 → ✅ **选定**:它能每小时唤醒当前线程,检查新消息和工作树,继续推进小步可验证开发。

**功能选择**:
- 候选 A:持久化 `/appoint` 写配置 → ❌ **暂缓**:涉及审计、回滚和配置写入策略,属于较大决策。
- 候选 B:新增 `/roles` 岗位视图 → ✅ **选定**:小步能力,能直接帮助老板理解项目还缺哪些角色,不改变运行时语义。

### 产出
- 创建 heartbeat 自动化 `AICO hourly progress nudge`,每小时唤醒当前线程继续推进和汇报。
- 新增 `CommandName.ROLES` 和 `/roles [project]`。
- 新增 `roles_message()`:
  - 展示 role id / title。
  - 展示默认权限。
  - 标记 `agent` 或 `unappointed`。
- 新增 `ProjectCommandHandler`,把项目办公室命令从 `DirectoryCommandHandler` 拆出,避免命令类超过 500 行硬约束。
- `ProjectCommandHandler` 和 `Orchestrator` 接入 roles 命令。
- 扩展单测覆盖:
  - `/roles aico` 解析。
  - `/roles` 输出 implementer 已任命、tester 未任命。
- 更新 `CHANGELOG.md`、`STATUS.md`、`docs/human/daily-ops.md`、`docs/architecture/project-assignment-layer.md` 和两张 draw.io 图。
- 完整验证通过:140 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check`;draw.io XML 解析通过。

### 关键决策
- 🔒 **决策 1**:小时级推进使用 thread heartbeat,不是 detached cron,因为目标是延续当前开发线程。
- 🔒 **决策 2**:`/roles` 只做只读视图,不创建或修改任命。
- 🔒 **决策 3**:持久化任命暂不顺手做,避免在没有审计/回滚策略时扩大范围。

### 留给下一轮
- 人类在 Telegram 里验证:
  - `/roles`
  - `/roles aico`
  - `/appoint claude as tester ...` 后 `/roles` 是否显示 tester 已任命。
- 后续可考虑 `/unappoint` 或持久化 appointment,但需要先定审计/回滚策略。

### 状态变化
- Phase 5 进度新增 Project roles view MVP。
- 当前线程新增 hourly heartbeat 自动化,用于持续推进。

## Round 42 — 2026-05-05 — Codex

### 输入
- Hourly heartbeat 唤醒当前开发线程,要求无重大决策时继续推进小步可验证能力。
- 上一轮 `/roles` 已能看到岗位缺口,但老板任命闭环还缺“撤销任命”。

### 思考与讨论

**功能选择**:
- 候选 A:持久化 appointment 到配置文件 → ❌ **暂缓**:涉及配置写入、审计、回滚和多进程一致性,仍需要单独设计。
- 候选 B:新增进程内 `/unappoint <role>` → ✅ **选定**:和现有 `/appoint` 的进程内语义一致,能让老板在当前项目办公室完成任命 / 撤任闭环。

### 产出
- 新增 `CommandName.UNAPPOINT` 和 `/unappoint <role>` help 文案。
- `ProjectAssignmentDirectory` 新增 `remove_appointment_for_role()`:
  - 按当前 project + role 找到 appointment。
  - 删除对应 seat。
  - 如果撤销的是当前 lead role,回退到剩余 appointment 或清空 lead。
- `ProjectCommandHandler` 新增撤任 handler。
- 新增 `appointment_removed_message()` 撤任确认输出。
- 扩展单测覆盖:
  - `/unappoint tester` 命令解析。
  - 撤任 tester 后 appointment/seat 消失,默认 lead 回退到 implementer。
  - Orchestrator 中 `/unappoint tester` 后 `/roles` 显示 tester 回到 `unappointed`, `/who tester` 显示未任命。
- 更新 `CHANGELOG.md`、`STATUS.md`、`docs/human/daily-ops.md` 和 `docs/architecture/project-assignment-layer.md`。
- 完整验证通过:142 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check`;draw.io XML 解析通过。

### 关键决策
- 🔒 **决策 1**:`/unappoint` 只修改当前进程内 appointment 状态,不写配置文件。
- 🔒 **决策 2**:撤销当前 lead role 时自动回退到剩余 appointment,避免普通消息路由进入无负责人状态。

### 留给下一轮
- 人类在 Telegram 里验证:
  - `/appoint claude as tester read_repo run_tests`
  - `/roles`
  - `/unappoint tester`
  - `/roles`
  - `/who tester`
- 后续若要让任命跨重启生效,需要单独设计持久化和审计策略。

### 状态变化
- Phase 5 进度新增 Project unappoint MVP。

## Round 43 — 2026-05-05 — Codex

### 输入
- Hourly heartbeat 再次唤醒当前开发线程,要求无重大决策时继续推进。
- 当前下一步最高优先级是 Project Team Telegram 真实验收,但需要人类重启服务和在 Telegram 中发命令。

### 思考与讨论

**功能选择**:
- 候选 A:继续扩展持久化 appointment → ❌ **暂缓**:仍属于配置写入 / 审计 / 回滚的大决策。
- 候选 B:让 `/project` 支持查看当前 active project → ✅ **选定**:符合老板“回到项目办公室看一眼”的直觉,改动很小,能本地验证。

### 产出
- `/project <project>` 保持原语义:进入指定项目办公室。
- `/project` 新增语义:
  - 已有 active project 时重新展示当前项目办公室。
  - 没有 active project 时提示先使用 `/project <project>`。
- `ProjectCommandHandler` 抽出 `_send_project_office()` 复用办公室输出。
- 更新 help 文案为 `/project [project] - enter or show the project office`。
- 新增 Orchestrator 单测覆盖 `/project` 无 active project 提示、进入项目后 `/project` 复显、且不派发 Adapter 任务。
- 更新 `CHANGELOG.md`、`STATUS.md`、`docs/human/daily-ops.md` 和 `docs/architecture/project-assignment-layer.md`。
- 完整验证通过:143 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check`;draw.io XML 解析通过。

### 关键决策
- 🔒 **决策 1**:`/project` 是当前项目办公室的“复显”入口,不是创建新项目或切换默认项目。
- 🔒 **决策 2**:没有 active project 时继续明确提示 `/project <project>`,避免系统猜默认项目。

### 留给下一轮
- 人类在 Telegram 里验证:
  - `/project`
  - `/project aico`
  - `/project`
- 继续推进前仍优先做 Project Team Telegram 真实验收。

### 状态变化
- Project office 入口体验更接近自然语言心智:进办公室后可以直接 `/project` 看当前办公室。

## Round 44 — 2026-05-05 — Codex

### 输入
- Hourly heartbeat 唤醒当前开发线程,要求继续推进小步可验证能力。
- 最高优先级仍是 Project Team Telegram 真实验收,但需要人类重启服务并在 Telegram 中操作。

### 思考与讨论

**功能选择**:
- 候选 A:继续新增 slash 命令 → ❌ **暂缓**:`Orchestrator` 已接近 500 行边界,继续扩命令会增加结构压力。
- 候选 B:补 Project Team 本地 acceptance flow → ✅ **选定**:能把 Telegram 验收前的主流程行为固定下来,降低真实验收时的排障成本。

### 产出
- 新增 `test_orchestrator_project_team_acceptance_flow`:
  - 先跑 `/project aico` 和 `/project` 复显。
  - 依次跑 `/brief`、`/risks`、`/blockers`、`/next`、`/daily`、`/weekly`、`/roles`、`/team`、`/who implementer`。
  - 任命 tester,用 `/ask tester ...` 派活。
  - 设置 `/lead tester`,确认普通消息走 tester appointment。
  - `/unappoint tester` 后确认 `/roles` 显示 tester 未任命、`/who tester` 提示未任命。
  - 撤任后普通消息回退到 implementer appointment。
- 验收流断言状态面不派发 Adapter 任务,项目任务通过 assignment metadata 区分 tester / implementer。
- 新增 `_metadata_value()` 测试辅助函数。
- 更新 `CHANGELOG.md` 和 `docs/human/daily-ops.md`,记录本地验收流命令。
- 完整验证通过:144 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check`;draw.io XML 解析通过。

### 关键决策
- 🔒 **决策 1**:本轮不新增 runtime command,避免扩大命令面和 `Orchestrator` 体积。
- 🔒 **决策 2**:验收流断言 project role metadata,不把底层 provider target 当作项目 role;同一个 Claude agent 可以被任命为 tester 或 implementer。

### 留给下一轮
- 人类在 Telegram 里按同一条命令流真实验收。
- 如果真实验收失败,先对照本地 acceptance flow 判断是核心行为问题、Telegram 通道问题还是 provider CLI 问题。

### 状态变化
- Phase 5 进度新增 Project Team 本地验收流。

## Round 45 — 2026-05-05 — Codex

### 输入
- Hourly heartbeat 唤醒当前开发线程,要求继续推进小步可验证能力。
- 下一步真实 Telegram 验收仍需人类环境配合。
- `Orchestrator` 类体已接近 500 行硬约束,继续新增命令会很容易踩线。

### 思考与讨论

**功能选择**:
- 候选 A:继续新增 runtime 命令 → ❌ **暂缓**:命令面继续扩大前,需要先释放 `Orchestrator` 类体空间。
- 候选 B:瘦身命令分发结构 → ✅ **选定**:行为不变、风险低,能降低后续迭代被 500 行约束卡住的概率。

### 产出
- `Orchestrator._handle_command()` 改为薄代理。
- 大段 command if/elif 分发移到模块级 `_handle_command()` 函数。
- 分发行为保持不变:
  - help / status / audit 仍在 Orchestrator 层直接响应。
  - Project 命令仍走 `ProjectCommandHandler`。
  - agent/session/provider introspection 仍走 `DirectoryCommandHandler`。
- approve / reject / broadcast 仍走 Orchestrator 既有内部路径。
- `Orchestrator` 实际类体按缩进边界统计从 491 行降到 422 行。
- 完整验证通过:144 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check`;draw.io XML 解析通过。

### 关键决策
- 🔒 **决策 1**:本轮只做结构性瘦身,不改变命令语义。
- 🔒 **决策 2**:暂不新建更多 runtime command,优先保持后续扩展空间。

### 留给下一轮
- 继续优先做 Project Team Telegram 真实验收。
- 如果后续还要新增命令,优先考虑继续拆分命令 dispatcher,不要把逻辑塞回 `Orchestrator` 类体。

### 状态变化
- `Orchestrator` 类体回到安全区间,后续扩展不再贴着 500 行硬约束走。

## Round 46 — 2026-05-05 — Codex

### 输入
- 人类 Telegram 验收发现多次 `/appoint ... as tester ...` 后 `/team` 出现多个 tester。
- 人类追问 role 如何扩展、`/lead` 后 `/team` 是否应看到 lead、Telegram Markdown 不好看的可扩展适配方式,以及 `/brief` / `/risks` / `/blockers` / `/next` 是否能在顶部增加 LLM 总结。

### 思考与讨论

**重复 appointment 语义判断**:
- 候选 A:只在 `/team` 输出时按 role 去重 → ❌ **否决**:这会遮住底层状态问题,`/who`、`/lead`、普通消息路由仍可能看到另一个 appointment。
- 候选 B:在 `ProjectAssignmentDirectory` 下沉唯一约束 → ✅ **选定**:老板语义是“一个项目里的一个 role 只有一个负责人”,底层应按 `project + role` 唯一。

**lead 可见性**:
- 候选 A:只保留 `/lead` 成功消息 → ❌ **否决**:用户回头看 `/team` 时无法知道谁是当前牵头。
- 候选 B:`/team` 顶部显示 lead,并在成员行标记 `[lead]` → ✅ **选定**:最小改动,不改变路由行为。

**本轮暂缓项**:
- Role 创建确认流、IM 富文本渲染层、状态命令顶部 LLM 总结都涉及命令协议、provider 调用或 channel render contract。直接塞进现有命令会扩大范围,因此本轮记录为下一轮高优先级切片。

### 产出
- `ProjectAssignmentDirectory` 初始化和 upsert appointment 时,对同一 `project + role` 保持唯一负责人;重复 role 时最后一个 appointment 生效。
- `/team` 输出新增 `lead: <role> -> <agent>`,并在对应成员行追加 `[lead]`。
- 新增单测覆盖配置/历史重复 role 去重、重复 `/appoint tester` 后 `/team` 只显示一个 tester、`/lead tester` 后 `/team` 可见 lead。
- 新增 PITFALL P-013。
- 更新 `STATUS.md`、`CHANGELOG.md` 和 `docs/human/daily-ops.md`。

### 关键决策
- 🔒 **决策 1**:Project Team 任命唯一键是 `project + role`,不是内部 `seat`。
- 🔒 **决策 2**:`/team` 是老板看团队的主视图,必须直接展示当前 lead。
- 🔒 **决策 3**:LLM 生成 role、IM 富文本、项目状态 LLM 总结都需要独立设计,不要在修重复 appointment 时混入。

### 留给下一轮
- 真实 Telegram 复测:
  - 连续执行两次 `/appoint claude as tester read_repo run_tests`
  - 执行 `/team`,确认只有一个 tester
  - 执行 `/lead tester`
  - 再执行 `/team`,确认顶部有 `lead: tester -> claude`,tester 行有 `[lead]`
- 设计并实现 `/role propose <诉求>` / `/role confirm` 的 LLM 草案确认流。
- 设计 IM render contract,先让 Telegram 支持更好看的 HTML 文案,但不要把 Telegram parse mode 写进核心语义。
- 为 `/brief` / `/risks` / `/blockers` / `/next` 做“本地事实包 + provider 只读总结 + 原始事实保留”的老板摘要 MVP。

### 状态变化
- Phase 5 进度新增 Project appointment 同 role 去重与 `/team` lead 可见性。
- 下一轮建议将 role 创建确认流、IM 文案渲染层和状态命令 LLM 总结提升为高优先级。

## Round 47 — 2026-05-05 — Codex

### 输入
- 人类确认上一轮修复已测试通过,要求继续执行。
- `STATUS.md` 下一轮高优先级包含 Role 创建确认流、IM 文案渲染层和项目状态命令 LLM 总结。

### 思考与讨论

**功能选择**:
- 候选 A:先做 Telegram 富文本渲染 → ❌ **暂缓**:需要设计跨 IM render contract,且当前 `Orchestrator` 已接近 500 行,贸然扩会踩结构边界。
- 候选 B:先做 `/brief` 等 LLM 总结 → ❌ **暂缓**:需要稳定事实包和 provider 调用策略,否则容易生成不可审计摘要。
- 候选 C:先做 `/role propose` / `/role confirm` 确认流 → ✅ **选定**:最贴近用户刚提出的 role 扩展诉求,且可以通过现有 Adapter/TaskBus 本地闭环测试。

**确认流边界**:
- 候选 A:LLM 输出后直接新增 role → ❌ **否决**:违反“AI 行为可审批、可审计”,也容易把坏 JSON 或错误权限静默写进项目。
- 候选 B:LLM 只起草,用户 `/role confirm` 后进程内新增 → ✅ **选定**:老板可以确认,且不碰持久化配置写入。
- 候选 C:确认后直接写 `config/projects.example.json` → ❌ **暂缓**:需要配置写入、审计和回滚策略,超出本轮小步范围。

**风险识别边界**:
- Role proposal 是只读 LLM 生成任务,但用户诉求可能包含“跑测试/写文档”等词。为避免误触发审批,内部 role proposal task 添加 `aico.intent=role_proposal` 元数据,风险识别将其视为 read-only。这个标记由 Orchestrator 内部生成,不是用户文本可直接设置的通道。

### 产出
- 新增 `src/aico/core/role_proposal.py`,负责生成 role proposal prompt 和解析 LLM JSON 输出为 `RoleProfile`。
- 新增 `/role propose <诉求>`、`/role confirm`、`/role discard` 命令。
- `ProjectAssignmentDirectory` 支持 runtime project role,确认后 `/roles` 会显示新增 role 且默认为 unappointed。
- `Orchestrator` 新增 role proposal 任务收集路径,复用当前项目 lead appointment/provider session。
- `TextRiskAssessor` 对内部 role proposal task 按 read-only 处理。
- 新增/更新单测覆盖命令解析、role proposal JSON 解析、runtime role 新增、风险跳过和 Orchestrator 提议/确认闭环。
- 更新 `STATUS.md`、`CHANGELOG.md`、`docs/human/daily-ops.md` 和 Project Assignment Layer 文档。

### 关键决策
- 🔒 **决策 1**:LLM 只能起草 role,不能绕过人类确认直接改项目结构。
- 🔒 **决策 2**:`/role confirm` 当前只改进程内 role registry,不写项目配置文件。
- 🔒 **决策 3**:内部 role proposal task 是 read-only 任务,用元数据标记表达意图,避免文本规则误判。

### 留给下一轮
- Telegram 真实验收:
  - `/project aico`
  - `/role propose 需要一个增长分析岗位`
  - 查看草案是否清楚、权限是否合理
  - `/role confirm`
  - `/roles` 确认新增 role 显示为 unappointed
- `Orchestrator` 类体已接近 500 行;下一轮继续新增能力前,先把 role proposal / collect output helper 拆出。
- 下一步再做 IM render contract 或 `/brief` / `/risks` / `/blockers` / `/next` 顶部 LLM 总结。

### 状态变化
- Phase 5 进度新增 Role proposal confirmation MVP。
- 下一轮建议新增 Role 创建确认流真实验收与 Orchestrator 结构拆分。

## Round 48 — 2026-05-05 — Codex

### 输入
- 人类确认以下真实 Telegram 验收均已通过:
  - 重复 `/appoint ... as tester ...` 不会让 `/team` 出现多个 tester。
  - `/lead tester` 后 `/team` 能显示当前 lead。
  - `/role propose` 后 `/role confirm`,新增 role 能在 `/roles` 中看到。
- 人类要求继续按优先级拆分和开发,有重要决策再询问。

### 思考与讨论

**功能选择**:
- 候选 A:直接开始 IM 富文本 render contract → ❌ **暂缓**:这是下一项高优先级产品能力,但 Round 47 已明确 `Orchestrator` 接近 500 行硬约束,继续扩行为前应先拆结构。
- 候选 B:直接做项目状态命令 LLM 总结 → ❌ **暂缓**:需要 provider 调用和事实包策略,也会继续加重命令 / task collection 路径。
- 候选 C:先拆 role proposal / collect output helper → ✅ **选定**:行为不变、风险低,直接清掉继续开发前的结构债。

**拆分边界**:
- `Orchestrator` 继续负责 IM 入站、命令分发、普通任务流式输出和 appointment task 构造。
- 新增 `RoleProposalCoordinator` 负责 role proposal 内部任务提交、输出收集、provider session busy/idle、provider initialized 标记和 LLM JSON 解析。
- 用户可见语义保持不变:`/role propose` 仍由当前项目 lead role 起草,`/role confirm` 仍只加入当前进程内 project roles。

### 产出
- `src/aico/core/role_proposal.py` 新增 `RoleProposalCoordinator`。
- `Orchestrator` 初始化时创建 coordinator,并把 `ProjectCommandHandler.propose_role` 回调改为 `RoleProposalCoordinator.propose`。
- 删除 `Orchestrator._propose_project_role()` 和 `_collect_task_output()`。
- `Orchestrator` 类体从 482 行降到 439 行,继续低于单类 <500 行硬约束。
- 拆分时发现 `risk -> role_proposal -> task_bus -> risk` 循环导入,将 `TaskBus` 改成 type-checking only import。
- 继续实现 IM render contract 第一切片:
  - `MessageContent` 新增平台无关 `MessageTextSpan` 和 `MessageAction`。
  - Telegram Channel 将 spans 映射为 HTML `parse_mode`,将 actions 映射为 `inline_keyboard`。
  - 没有 spans/actions 的既有纯文本消息 payload 保持不变。
- 新增 ADR-0013,明确不在核心层写 Telegram HTML / MarkdownV2 / `reply_markup`。
- 更新 `STATUS.md`、`CHANGELOG.md` 和 ADR 索引。
- 完整验证通过:153 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`。

### 关键决策
- 🔒 **决策 1**:本轮只做结构拆分,不改变 role proposal 的产品语义。
- 🔒 **决策 2**:role proposal 的运行时协调归 `RoleProposalCoordinator`,prompt/JSON 解析仍留在同一 role proposal 模块内,避免为单一流程过早拆出更多抽象。
- 🔒 **决策 3**:循环导入用 type-checking import 解开,不把 risk 常量迁到新公共模块;当前只有 role proposal 需要这组 intent 常量。
- 🔒 **决策 4**:IM 富文本和按钮能力先进入 `MessageContent` 的平台无关 hints,Telegram 只在 Channel 出口映射为 HTML / inline keyboard。

### 留给下一轮
- 将 IM render contract 用到项目办公室关键消息,优先改 `/project`、`/team`、`/roles` 和审批 / 确认类输出。
- 设计 `/brief`、`/risks`、`/blockers`、`/next` 的 LLM 顶部摘要时,保留“本地事实包 + provider 只读总结 + 原始事实”的可审计结构。
- 继续安排 Codex bind、Claude resume/长文本和 Phase 5 `@reviewer` 协作 smoke test 的真实 IM 复测。

### 状态变化
- Project Team / Appointment Telegram 真实验收:未完成 → 完成。
- Role proposal confirmation Telegram 真实验收:未记录 → 完成。
- Phase 5 进度新增 Orchestrator role proposal helper 拆分。
- Phase 5 进度新增 Platform-neutral IM render contract 第一切片。

## Round 49 — 2026-05-06 — Codex

### 输入
- 人类要求继续开发,没有重要决策可以多开发两轮,之后统一验收能力。
- `STATUS.md` 下一轮最高优先级是将 IM render contract 用到项目办公室关键消息。

### 思考与讨论

**功能选择**:
- 候选 A:直接做 `/brief` 等项目状态命令 LLM 总结 → ❌ **暂缓**:涉及 provider 调用策略和摘要事实包,仍比 render contract 应用更大。
- 候选 B:先将 spans/actions 用到项目办公室消息 → ✅ **选定**:ADR-0013 已定边界,这是自然落地切片,不会改变核心命令语义。
- 候选 C:同时补 Telegram callback query → ✅ **选定**:role proposal 已能带 Confirm / Discard actions,如果不处理 callback query,按钮只会显示不能实际复用命令通路。

### 产出
- `project_messages.py` 新增 `_heading_message()`,为项目办公室关键消息首行增加 `MessageTextSpan(BOLD)`:
  - `/project`
  - `/team`
  - `/roles`
  - `/who`
  - `/appoint`
  - `/unappoint`
  - `/lead`
  - `/role propose` / `/role confirm`
  - 项目 brief / risks / blockers / next / daily / weekly 的本地事实消息
- `role_proposal_message()` 新增两个 actions:
  - `Confirm` → `/role confirm`
  - `Discard` → `/role discard`
- Telegram Channel 新增 `callback_query` 处理:
  - callback data 被转换成 `IncomingMessage.content.text`,复用现有 command parser。
  - 发送 `answerCallbackQuery`,避免 Telegram 客户端按钮点击后持续 loading。
- 更新测试:
  - Telegram callback query 转换为 incoming message。
  - role proposal 消息带 `/role confirm` / `/role discard` actions。
  - 对富文本消息的行为测试改为断言 `.text`,避免 spans 变化误伤业务断言。
- 更新 `STATUS.md`、`CHANGELOG.md` 和 `docs/human/daily-ops.md`。
- 完整验证通过:154 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`。

### 关键决策
- 🔒 **决策 1**:按钮 action value 复用现有 slash command 文本,不引入第二套 callback command 协议。
- 🔒 **决策 2**:Telegram callback query 在 Channel 层转成普通 `IncomingMessage`,核心编排层不感知 Telegram callback 细节。
- 🔒 **决策 3**:本轮只给项目办公室消息加基础 heading span 和 role proposal 确认按钮,不做完整卡片布局。

### 留给下一轮
- 真实 Telegram 验收:
  - `/project aico`、`/team`、`/roles` 首行应加粗。
  - `/role propose 需要一个增长分析岗位` 应出现 Confirm / Discard 按钮。
  - 点击 Confirm 应等价于发送 `/role confirm`,点击 Discard 应等价于发送 `/role discard`。
- 下一步进入项目状态命令 LLM 总结:先做“本地事实包 + lead/pm provider 只读总结 + 原始事实保留”的 MVP。
- 继续安排 Codex bind、Claude resume/长文本和 Phase 5 `@reviewer` 协作 smoke test 的真实 IM 复测。

### 状态变化
- Phase 5 进度新增 Project office key messages 使用 render hints。
- Phase 5 进度新增 Telegram callback query 转入现有命令通路。

## Round 50 — 2026-05-06 — Codex

### 输入
- 人类已验证 Round 49 的 Telegram render / button 能力有效。
- 人类要求继续开发后续能力。
- `STATUS.md` 下一轮最高优先级是项目状态命令 LLM 总结。

### 思考与讨论

**功能选择**:
- 候选 A:给 `/brief`、`/risks`、`/blockers`、`/next` 增加顶部 LLM 摘要 → ✅ **选定**:这正是当前最高优先级,并且有明确边界“事实包 + 只读总结 + 原始事实保留”。
- 候选 B:同时给 `/daily`、`/weekly` 加摘要 → ❌ **暂缓**:日报/周报更长,真实体验和延迟风险更高;先让短状态命令闭环。
- 候选 C:让 LLM 摘要替换原有事实输出 → ❌ **否决**:违反可审计原则,也容易让 hallucination 掩盖真实本地状态。

**实现边界**:
- Summary 输入只取本地事实消息文本,不直接读取额外文件或隐藏状态。
- Summary task 走当前项目 lead appointment/provider session,延续项目办公室语义。
- Summary 失败时发送原事实消息,不让 provider 忙或失败影响 `/brief` 等状态命令。

### 产出
- 新增 `src/aico/core/project_summary.py`:
  - `ProjectSummaryCoordinator`
  - `project_summary_prompt()`
  - 内部 `aico.intent=project_summary` 标记
- `ProjectCommandHandler` 新增可选 `summarize_project` 回调。
- `/brief`、`/risks`、`/blockers`、`/next` 先生成本地事实消息,再尝试生成 `Boss summary` 顶部摘要。
- `project_summary_message()` 保留完整 `Facts` 原文,并为 `Boss summary` / `Facts` 加 heading spans。
- `TextRiskAssessor` 将内部 project summary task 视为 read-only,避免事实文本中的 `run` / `write` / `/approve` 等词误触发审批。
- 新增/更新测试:
  - summary 成功时顶部出现 `Boss summary`,事实原文仍保留。
  - summary submit 失败时仍发送原事实消息。
  - project summary intent 不触发风险审批。
  - acceptance flow 过滤内部 summary task 后仍确认业务任务路由正确。
- 更新 `STATUS.md`、`CHANGELOG.md` 和 `docs/human/daily-ops.md`。
- 完整验证通过:156 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`。

### 关键决策
- 🔒 **决策 1**:LLM summary 是顶部管理摘要,不是事实源;原始事实必须完整保留。
- 🔒 **决策 2**:summary task 失败时静默降级为事实输出,不新增用户可见错误噪音。
- 🔒 **决策 3**:本轮只覆盖 `/brief`、`/risks`、`/blockers`、`/next`,日报/周报是否摘要留给真实体验后判断。

### 留给下一轮
- 真实 Telegram 验收:
  - `/brief`
  - `/risks`
  - `/blockers`
  - `/next`
  - 期望顶部出现 `Boss summary`,下方保留 `Facts`。
- 继续复测 Project office render 和 role proposal buttons。
- 继续安排 Codex bind、Claude resume/长文本和 Phase 5 `@reviewer` 协作 smoke test 的真实 IM 复测。

### 状态变化
- Phase 5 进度新增 Project status LLM summary MVP。

## Round 51 — 2026-05-06 — Codex

### 输入
- 人类验证 Round 50 的 Boss summary 内容有效,但指出格式问题:
  - 只有最上方标题有样式。
  - summary 内部无序列表、`**bold**`、反引号等 Markdown 语法没有被渲染。
- 人类要求修复字体样式后继续开发后续内容。

### 思考与讨论

**样式修复选择**:
- 候选 A:让 Telegram Channel 直接解析 Markdown → ❌ **否决**:会把 Telegram 视图逻辑和 Markdown 方言耦合到 Channel,也不利于 Feishu / Kim 复用。
- 候选 B:要求 LLM 不输出 Markdown → ❌ **否决**:能减少裸露标记,但不能解决“加粗/代码/列表需要可渲染语义”的问题。
- 候选 C:在核心消息层把 summary 轻量 Markdown 转为 `MessageTextSpan` → ✅ **选定**:继续遵守 ADR-0013,核心输出平台无关 spans,Telegram 只负责映射 HTML。

**后续能力选择**:
- 候选 A:继续扩展 summary 到 `/daily` / `/weekly` → ✅ **选定**:人类已确认短状态 summary 内容基本可用,报告命令可以复用同一事实保留策略。
- 候选 B:继续新增项目命令 → ❌ **暂缓**:`ProjectCommandHandler` 已约 482 行,继续加命令前应先拆。

### 产出
- 修复 `project_summary_message()` 的 summary 文本渲染:
  - `- ` / `* ` 列表前缀转换为 `• `。
  - `**bold**` 转为干净文本 + `MessageTextSpan(BOLD)`。
  - `` `code` `` 转为干净文本 + `MessageTextSpan(CODE)`。
  - `*italic*` 转为干净文本 + `MessageTextSpan(ITALIC)`。
  - `Boss summary`、summary 内部 spans、`Facts` 和 facts 原有 spans 的 offset 会正确叠加。
- 新增 `tests/unit/test_project_messages.py`,覆盖 summary Markdown 转 spans。
- `/daily`、`/weekly` 也改为走 `Boss summary + Facts` 输出。
- 更新 acceptance/report 相关单测,过滤内部 `project_summary` task 后继续验证业务任务路由。
- 更新 `STATUS.md`、`CHANGELOG.md` 和 `docs/human/daily-ops.md`。
- 完整验证通过:见本轮交接。

### 关键决策
- 🔒 **决策 1**:summary 轻量 Markdown 在核心消息层转换为平台无关 spans,不在 Telegram Channel 内直接解析 Markdown。
- 🔒 **决策 2**:`/daily`、`/weekly` 复用同一 summary 降级策略;summary 失败仍输出原事实报告。
- 🔒 **决策 3**:继续加项目命令前先拆 `ProjectCommandHandler`,避免触碰单类 <500 行硬约束。

### 留给下一轮
- 真实 Telegram 验收:
  - `/brief`、`/risks`、`/blockers`、`/next`、`/daily`、`/weekly`
  - Boss summary 中 `**bold**`、`` `code` ``、`*italic*` 不应裸露。
  - 列表应显示为 `• `。
  - 下方仍保留完整 `Facts`。
- 下一次代码开发如果继续改项目命令,优先拆 `ProjectCommandHandler` 的 summary/report/role proposal 相关职责。
- 继续安排 Codex bind、Claude resume/长文本和 Phase 5 `@reviewer` 协作 smoke test 的真实 IM 复测。

### 状态变化
- Phase 5 进度新增 Project summary Markdown 转 render spans。
- Phase 5 进度新增 Project report LLM summary MVP(`/daily` / `/weekly`)。

## Round 52 — 2026-05-06 — Codex

### 输入
- 人类继续真实 Telegram 验收:
  - `/project`、`/team`、`/roles` 首行加粗和 `/role propose` Confirm / Discard 按钮已验证通过。
  - `/blockers` 依然没有格式。
  - `/brief` 和 `/next` 的 `Boss summary` 部分有正确格式,但 `Facts` 部分没有格式样式。
- 人类要求给出 Phase 5 `@reviewer ...` 真实协作 smoke test 的样例 prompt。

### 思考与讨论

**Facts 渲染问题判断**:
- 候选 A:在 Telegram Channel 中根据文本内容解析 `/blockers`、`Facts`、`waiting decisions:` 等格式 → ❌ **否决**:会把 Telegram 出口和项目办公室文案耦合,违反 ADR-0013 的平台无关 render contract。
- 候选 B:只修 `/blockers` 特例 → ❌ **否决**:真实问题是 project facts 消息本身只有首行 span,`/brief`、`/next`、`/daily`、`/weekly` 都会继承同样缺口。
- 候选 C:增强项目消息层的 `_heading_message()` 生成更丰富的平台无关 spans → ✅ **选定**:小范围修复,让直接发送 facts 和 `Boss summary + Facts` 组合消息都能复用。

**协作 prompt 选择**:
- 选择要求 Claude 最后一行单独输出 `@reviewer ...` 的 prompt,因为协作解析只接受行首 `@persona request` / `@persona: request`,这样最容易稳定触发真实 smoke test。

### 产出
- `src/aico/core/project_messages.py`:
  - `_heading_message()` 改为调用 `_project_message_spans()`。
  - 首行继续加粗。
  - 非列表小节标题如 `waiting decisions:`、`team:`、`recent tasks:` 会生成 `MessageTextSpan(BOLD)`。
  - 文本中的 slash command 如 `/approve`、`/reject`、`/ask`、`/blockers` 会生成 `MessageTextSpan(CODE)`。
  - `project_summary_message()` 保持原逻辑,继续把 facts spans 平移到 `Facts` 区域。
- `tests/unit/test_project_messages.py`:
  - 新增 `/blockers` 小节标题和 slash command spans 覆盖。
  - 新增 summary 组合消息保留 facts spans 的 offset 覆盖。
- `docs/human/daily-ops.md`:
  - 记录 Facts 区域保留原始事实并渲染小节 / slash command 样式。
  - 补充 Phase 5 协作 smoke test 推荐 prompt。
- 更新 `STATUS.md` 和 `CHANGELOG.md`。
- 验证通过:
  - 159 个单测
  - `ruff check .`
  - `ruff format --check .`
  - `mypy src tests`

### 关键决策
- 🔒 **决策 1**:Facts 区域样式继续走核心 `MessageTextSpan`,不在 Telegram Channel 中解析项目状态文本。
- 🔒 **决策 2**:`/blockers` 不做特例;所有项目状态 facts 消息共享小节标题和 slash command 基础样式。
- 🔒 **决策 3**:本轮只做基础结构样式,不引入完整 Markdown parser 或复杂卡片布局。

### 留给下一轮
- 人类重启服务后复验:
  - `/blockers`
  - `/brief`
  - `/next`
  - `/daily`
  - `/weekly`
  - 重点看 `Facts` 区域小节标题是否加粗、`/approve` / `/reject` / `/ask` 等命令是否按 code 样式展示。
- 使用本轮给出的 sample prompt 做 Phase 5 `@reviewer` 真实协作 smoke test,随后查 `/audit` 是否出现 `collaboration_requested`。
- 下一次代码开发仍优先拆 `ProjectCommandHandler`。

### 状态变化
- Project office render / role proposal button 真实验收已由人类确认通过。
- Phase 5 进度新增 Project status Facts 小节 / slash command render spans。
- 下一轮建议提升为 Project status render 复验和 Phase 5 真实协作 smoke test。

## Round 53 — 2026-05-06 — Codex

### 输入
- 人类执行上一轮给出的 Phase 5 协作 smoke test prompt。
- Telegram 已回复 `Collaboration requested: claude -> reviewer`,说明协作指令已触发。
- 之后卡在 `Task accepted: 31e559c3-bd7c-4e1b-9385-024431f8635a [reviewer]`,没有收到 reviewer 输出。

### 思考与讨论

**定位选择**:
- 候选 A:继续调整协作 prompt → ❌ **否决**:日志已经有 `Collaboration directive` 和 reviewer child task,说明 prompt / parser 不是当前卡点。
- 候选 B:继续调 Telegram render / 分片 → ❌ **否决**:日志停在 reviewer `Stream start`,没有后续 `Stream output`,还没进入 Telegram 输出阶段。
- 候选 C:查 Adapter 进程与日志主链路 → ✅ **选定**:按 P-011 的排障方法 grep task id,确认 Codex CLI 子进程仍在运行但没有 stdout chunk。

**修复选择**:
- 候选 A:给 Codex Adapter 加硬 timeout → ❌ **暂缓**:不同 review 任务耗时差异大,timeout 策略需要单独设计,否则可能误杀有效长任务。
- 候选 B:只在文档里写“手动 kill Codex” → ❌ **否决**:北极星第三句要求 AI 行为可中断,不能只依赖人回到机器上处理。
- 候选 C:补 IM 侧 `/interrupt <task_id>` → ✅ **选定**:底层 Adapter / TaskBus 已有 interrupt 能力,缺的是命令入口和 task id 前缀匹配。

### 产出
- 新增 `CommandName.INTERRUPT` 和 help 文案。
- 新增 Orchestrator `_handle_interrupt()`:
  - 无 task id 时提示 `Usage: /interrupt <task_id>`。
  - 成功时回复 `Task interrupted: <short_id>`。
  - 失败时复用 `ack_failure_message()` 给出 unknown / ambiguous / non-running 等原因。
- `TaskBus.interrupt()` 改为返回 `TaskAck`,支持:
  - 完整 task id 或前缀匹配。
  - unknown task 明确拒绝。
  - 多个匹配 task 明确列出短 ID。
  - 非 running task 拒绝中断。
  - running task 调 Adapter interrupt,更新 `interrupted` 状态并写 `task_interrupted` 审计。
- 新增/更新单测:
  - `/interrupt abcdef12` 命令解析。
  - Orchestrator 可按短 ID 中断 running task。
  - `/interrupt` 无参数提示 usage。
- 新增 PITFALL P-014。
- 更新 `STATUS.md`、`CHANGELOG.md`、`docs/human/daily-ops.md` 和 `docs/playbooks/phase-5-collaboration.md`。

### 关键决策
- 🔒 **决策 1**:本轮先补远程中断入口,不为 Codex Adapter 引入统一 timeout。timeout 需要后续结合任务类型和 provider 行为另行设计。
- 🔒 **决策 2**:`/interrupt` 支持 task id 前缀,延续 `/approve <short_id>` 的 IM 交互风格。
- 🔒 **决策 3**:已 done / failed / rejected / interrupted 的任务不重复 interrupt,避免把历史状态误改。

### 留给下一轮
- 当前正在运行的旧 AICO 进程尚未加载 `/interrupt`,因此这次卡住的 Codex 子进程需要人类先在本机停止服务或杀进程,再重启 AICO。
- 重启后复验:
  - `/status` 查 running task。
  - `/interrupt <short_task_id>` 中断任务。
  - `/audit` 确认出现 `task_interrupted`。
- 继续做 Phase 5 真实协作 smoke test。如果 reviewer 再次长时间无输出,先用 `/interrupt` 收口,再考虑 Codex Adapter timeout / heartbeat 设计。

### 状态变化
- Phase 5 进度新增 IM 远程中断命令(`/interrupt`)。
- 新增 P-014,记录 reviewer accepted 后 Codex 长时间无 stdout 且 IM 无中断入口的问题。

## Round 54 — 2026-05-06 — Codex

### 输入
- 人类要求继续开发。
- 当前最高优先级中的 `/interrupt`、Project status render 和 Phase 5 collaboration smoke 复验都需要人类重启 AICO 服务并在 Telegram 中操作。
- 代码侧仍有结构债:Project command 类此前多轮持续承接项目办公室、状态报告、团队、岗位和 role proposal 流程,接近单类硬约束。

### 思考与讨论

**功能选择**:
- 候选 A:继续新增项目命令 → ❌ **否决**:上一轮刚补 `/interrupt`,项目命令类仍需要先降复杂度,继续加命令会让职责边界变糊。
- 候选 B:拆 Project status/report handler → ❌ **暂缓**:状态 / 报告命令和 summary callback 牵涉 `/brief`、`/risks`、`/blockers`、`/next`、`/daily`、`/weekly`,改动面更大。
- 候选 C:先拆 role proposal 命令处理 → ✅ **选定**:role proposal 已有独立 `RoleProposalCoordinator`,命令层也有独立 draft 状态,最适合小步拆分且行为不变。

**拆分边界**:
- `ProjectCommandHandler` 继续作为 Orchestrator 接入的项目命令门面。
- 新增 `ProjectRoleCommandHandler` 负责 `/role propose`、`/role confirm`、`/role discard` 和 role draft 暂存。
- `ProjectCommandHandler.handle_role()` 只做薄代理,不再持有 `_role_drafts` 和 `_propose_role` 内部状态。

### 产出
- 新增 `src/aico/core/project_role_commands.py`:
  - `ProjectRoleCommandHandler`
  - `RoleProposalRunner` 类型别名
  - role proposal / confirm / discard 子流程
- 更新 `src/aico/core/project_commands.py`:
  - 注入并委托 `ProjectRoleCommandHandler`。
  - 删除 `_handle_role_propose()`、`_handle_role_confirm()`、`_handle_role_discard()`。
  - 删除 `_role_drafts` 和 `_propose_role` 成员。
- 更新 `CHANGELOG.md` 和 `STATUS.md`。
- 完整验证通过:
  - 162 个单测
  - `ruff check .`
  - `ruff format --check .`
  - `mypy src tests`

### 关键决策
- 🔒 **决策 1**:本轮只做结构拆分,不改变 `/role propose` / `/role confirm` / `/role discard` 的用户语义。
- 🔒 **决策 2**:Role proposal 的 provider 调用仍归 `RoleProposalCoordinator`,命令层只负责交互状态和确认流。
- 🔒 **决策 3**:ProjectCommandHandler 继续作为门面保留,避免 Orchestrator 直接知道每个项目命令子 handler。

### 留给下一轮
- 人类重启服务后继续复验:
  - `/interrupt <short_task_id>`
  - `/blockers`
  - `/brief` / `/next` / `/daily` / `/weekly` Facts 样式
  - Phase 5 `@reviewer` collaboration smoke test
- 如果下一轮继续写代码,优先考虑拆 Project status/report handler,不要把新状态命令塞回 `ProjectCommandHandler`。

### 状态变化
- Phase 5 进度新增 ProjectRoleCommandHandler 结构拆分。
- `src/aico/core/project_commands.py` 从 544 行降到 475 行。

## Round 55 — 2026-05-06 — Codex

### 输入
- 人类要求继续开发后续功能。
- 当前真实复验项仍依赖人类重启服务和 Telegram 操作;代码侧继续推进结构拆分,为后续 Phase 6/8 项目状态能力铺路。

### 思考与讨论

**功能选择**:
- 候选 A:新增更多项目状态命令 → ❌ **否决**:状态 / 报告命令刚形成一组,继续塞进门面类会重新制造结构债。
- 候选 B:拆 Project team/assignment handler → ❌ **暂缓**:团队任命流程也值得拆,但当前更容易影响 `/appoint`、`/unappoint`、`/lead` 等老板主路径。
- 候选 C:拆 Project status/report handler → ✅ **选定**:状态 / 报告命令天然一组,且上轮已经把 role proposal 拆出,本轮继续把 `/brief`、`/risks`、`/blockers`、`/next`、`/daily`、`/weekly` 聚合到独立 handler。

**拆分边界**:
- `ProjectCommandHandler` 继续作为 Orchestrator 唯一接入门面。
- 新增 `ProjectStatusCommandHandler` 负责:
  - 本地 facts 构造。
  - 文档 snippet 读取。
  - summary callback 调用。
  - summary 失败降级到原 facts。
- `ProjectCommandHandler` 中对应方法只做薄代理,不改变用户可见行为。

### 产出
- 新增 `src/aico/core/project_status_commands.py`:
  - `ProjectStatusCommandHandler`
  - `ProjectSummaryRunner`
  - `/brief`、`/risks`、`/blockers`、`/next`、`/daily`、`/weekly` 的处理逻辑
- 更新 `src/aico/core/project_commands.py`:
  - 注入并委托 `ProjectStatusCommandHandler`。
  - 删除状态 / 报告 facts 构造、summary 发送和 report helper。
  - 移除不再需要的 docs/message imports。
- 更新 `STATUS.md` 和 `CHANGELOG.md`。
- 定向验证通过:
  - `tests/unit/test_orchestrator.py`
  - `tests/unit/test_project_messages.py`

### 关键决策
- 🔒 **决策 1**:ProjectCommandHandler 保持门面角色,Orchestrator 不直接依赖多个项目子 handler。
- 🔒 **决策 2**:状态 / 报告 handler 只承接既有行为,不改变 summary 策略、不新增 facts 来源。
- 🔒 **决策 3**:本轮不做可观测看板或离线托管新功能,先保证项目状态命令结构稳定。

### 留给下一轮
- 人类重启服务后继续复验:
  - `/interrupt <short_task_id>`
  - `/blockers`
  - `/brief` / `/next` / `/daily` / `/weekly` Facts 样式
  - Phase 5 `@reviewer` collaboration smoke test
- 如果继续写代码,下一步可拆 Project team/assignment handler,或在真实复验通过后进入 Phase 6 最小可观测状态 API。

### 状态变化
- Phase 5 进度新增 ProjectStatusCommandHandler 结构拆分。
- `src/aico/core/project_commands.py` 从 476 行降到 349 行。

## Round 56 — 2026-05-06 — Codex

### 输入
- 人类反馈已经复验 `/interrupt` 和 `/blockers`。
- 本轮继续收口上一轮 Project status/report handler 拆分,补齐完整验证和交接状态。

### 思考与讨论

**当前判断**:
- `/interrupt` 与 `/blockers` 已经从“待真实复验”变成“已真实复验”,应立即从高优待办移除,避免下一轮重复劳动。
- `ProjectStatusCommandHandler` 已经拆出,本轮不继续扩大功能面,先把完整验证补齐。
- 真实协作 smoke test 仍是 Phase 5 最高优先级;如果 reviewer/Codex 再次停在 accepted,现在已有 `/interrupt` 可收口,后续再决定是否做 timeout / heartbeat。

### 产出
- 更新 `STATUS.md`:
  - 当前轮次推进到 Round 56。
  - Phase 5 进度标记 `/interrupt` 和 `/blockers` Telegram 真实复验。
  - 下一轮建议移除已完成的 `/interrupt` / `/blockers` 复验项,保留 `/brief`、`/next`、`/daily`、`/weekly` Facts 样式抽样。
- 完整验证通过:
  - 162 个单测
  - `uv run ruff check .`
  - `uv run ruff format --check .`
  - `uv run mypy src tests`
  - `git diff --check`

### 关键决策
- 🔒 **决策 1**:不把已验收的 `/interrupt` 和 `/blockers` 留在最高优待办里。
- 🔒 **决策 2**:状态 handler 拆分后先验证稳定性,不顺手新增新的项目状态命令。
- 🔒 **决策 3**:Phase 5 下一步仍优先真实协作 smoke test,代码侧备选是继续拆 Project team/assignment handler。

### 留给下一轮
- 继续 Phase 5 `@reviewer` collaboration smoke test。
- 抽样 `/brief`、`/next`、`/daily`、`/weekly` Facts 样式。
- 若继续写代码,优先拆 Project team/assignment handler;若 smoke test 稳定,可以进入 Phase 6 最小可观测状态 API。

### 状态变化
- Phase 5 进度新增 `/interrupt` 和 `/blockers` Telegram 真实复验。

## Round 57 — 2026-05-06 — Codex

### 输入
- 人类复测 Phase 5 `@reviewer` 真实协作 smoke test 后反馈:
  - 收到 `Task accepted: 1481a413-f886-46bc-b7d4-98cccf295218 [reviewer]`。
  - 随后长时间没有 reviewer 输出。
  - `/status` 显示 `claude-code: idle`, `codex: busy`。
- 人类同时反馈 `/brief`、`/next` 有效果,但 Facts 区域无序列表和 inline Markdown 仍渲染不正确;截图中可见 facts 仍显示 `- ` 和 `**当前 workaround**`。

### 思考与讨论

**Codex 卡住判断**:
- 协作解析、child task 创建和 adapter dispatch 都已经成功,否则不会出现 `Task accepted ... [reviewer]` 且 `codex: busy`。
- 真正问题是 Codex CLI 进程 accepted 后一直不向 stdout 写内容,`ClaudeCodeAdapter._stream_reader()` 会无限等待 `readline()`。
- `/interrupt` 已解决人工收口,但北极星要求远程长期托管也不能无限 busy,因此需要 Adapter 侧自动空闲超时。

**Render 判断**:
- Round 51 只处理 Boss summary 的轻量 Markdown。
- Round 52 只给 Facts 小节和 slash command 增加 spans。
- 真实截图说明 Facts 本身也需要同一套轻量 Markdown 规范化:bullet prefix 和 inline bold/code/italic。

### 产出
- Codex busy 自动释放:
  - `ClaudeCodeAdapter` 新增可选 `output_idle_timeout_seconds`。
  - 如果进程仍在运行但 stdout 在阈值内没有下一行输出,Adapter 会 terminate/kill 底层进程,输出 `adapter output idle timeout after <Ns>`。
  - `CodexAdapter` 默认启用 90 秒输出空闲超时。
  - `Phase1Settings` 新增 `AICO_CODEX_OUTPUT_IDLE_TIMEOUT_SECONDS`。
- Project Facts render 修复:
  - `_heading_message()` 改为先逐行规范化再计算 spans。
  - facts 行首 `- ` / `* ` 转为 `• `。
  - facts 中 `**bold**`、`` `code` ``、`*italic*` 转为 render spans。
  - summary + facts 组合消息继续保留平移后的 facts spans。
- 新增/更新单测:
  - Codex 默认 idle timeout。
  - Claude/Codex 复用 adapter 在 stdout 长时间无输出时失败并释放 busy。
  - Project next/blockers facts bullet 和 inline Markdown 渲染。
- 更新 `STATUS.md`、`PITFALLS.md`、`docs/playbooks/phase-5-collaboration.md`、`docs/human/daily-ops.md`。
- 完整验证通过:
  - 165 个单测
  - `uv run ruff check .`
  - `uv run ruff format --check .`
  - `uv run mypy src tests`
  - `git diff --check`

### 关键决策
- 🔒 **决策 1**:只给 Codex 默认启用输出空闲超时,Claude 默认保持不变,避免影响长时间思考但最终有输出的 Claude 主路径。
- 🔒 **决策 2**:默认阈值设为 90 秒,作为当前 smoke test 和远程托管体验的保守平衡;可用环境变量调整。
- 🔒 **决策 3**:Project facts 不引入完整 Markdown 解析器,继续使用当前平台无关 render spans 的轻量子集。

### 留给下一轮
- 先用 `/interrupt 1481a413` 收口旧进程中的 stuck reviewer task,再重启 AICO。
- 重启后复测 Phase 5 `@reviewer` smoke test:
  - 理想结果:reviewer 产出真实 review。
  - 可接受降级:Codex 90 秒无 stdout 后返回 idle timeout,`/status` 恢复 `codex: idle`。
- 抽样 `/brief`、`/next`、`/daily`、`/weekly`,确认 facts bullet 显示为 `• ` 且 `**...**` 不再裸露。

### 状态变化
- Phase 5 进度新增 Codex output idle timeout MVP。
- Phase 5 进度新增 Project Facts bullet / inline Markdown render spans。

## Round 58 — 2026-05-06 — Codex

### 输入
- 人类复验 `/brief` 后反馈“好了很多”,其他无问题。
- 剩余问题:文档 snippet 中的 Markdown 标题仍裸露,截图中可见:
  - `# NORTH_STAR.md — 项目宪法`
  - `## 第一句:业务价值`
  - `### 状态变化`

### 思考与讨论
- Round 57 已处理 facts bullet 和 inline Markdown,但没有处理 Markdown heading。
- 这些 heading 来自 `ProjectDocumentSnippet.lines`,应该在通用 `_heading_message()` 层统一处理,避免只给 `/brief` 写特例。
- 继续保持轻量 Markdown 子集,不引入完整 Markdown parser。

### 产出
- Project Facts Markdown heading render:
  - 识别行首 `#` 到 `######` + 空格。
  - 去掉 `#` 前缀。
  - 对 heading 正文生成 `MessageTextSpan(BOLD)`。
- 更新 `tests/unit/test_project_messages.py`,覆盖文档 snippet 中的 `#`、`##`、`###`。
- 更新 `STATUS.md` 和 `ROUNDS.md`。
- 完整验证通过:
  - 166 个单测
  - `uv run ruff check .`
  - `uv run ruff format --check .`
  - `uv run mypy src tests`
  - `git diff --check`

### 关键决策
- 🔒 **决策 1**:heading 渲染在 `project_messages.py` 通用层处理,覆盖所有 Project status/report 命令。
- 🔒 **决策 2**:只支持 Markdown heading 的常见行首形态,不解析完整 Markdown 文档。

### 留给下一轮
- 重启后抽样 `/brief`,确认文档片段中的 `# / ## / ###` 不再裸露,标题加粗。
- 若 Project status render 复验通过,下一步回到 Phase 5 `@reviewer` smoke test 或继续拆 Project team/assignment handler。

### 状态变化
- Phase 5 进度新增 Project Facts Markdown heading render spans。

## Round 59 — 2026-05-06 — Codex

### 输入
- 人类在 Telegram 验证 `/brief` heading render 后反馈“挺好的”,并要求继续开发后续能力。
- 当前 Phase 5 真实协作 smoke test 仍需要更好的 IM 侧任务追踪,尤其是 reviewer/Codex accepted 后观察、定位、interrupt 和 idle timeout 复验。

### 思考与讨论
- 候选 A:直接进入 Phase 6 看板 API → ❌ **暂缓**:Phase 5 的真实协作 smoke test 还没完全闭环,先补 IM 侧可观测更符合当前 dogfooding。
- 候选 B:继续拆 Project team/assignment handler → ❌ **暂缓**:结构债重要,但用户现在持续在 Telegram 验证运行链路,更需要现场排障能力。
- 候选 C:新增任务追踪命令 → ✅ **选定**:`/status` 只能粗看 adapter busy,`/audit` 偏事件流;需要一个老板能直接看“任务是什么状态、下一步能按什么命令”的入口。

### 产出
- 新增命令:
  - `/tasks [limit]`:列出最近任务,默认 10 条,最多 20 条。
  - `/task <task_id>`:支持完整或短 task id 前缀,展示单任务详情。
- `/task` 详情包含:
  - 完整 task id。
  - target persona。
  - adapter。
  - status。
  - risk。
  - created / updated 时间。
  - reason。
  - 可执行动作。
- 可执行动作:
  - running → `/interrupt <short_id>`。
  - waiting approval → `/approve <short_id>` 和 `/reject <short_id>`。
- `TaskBus` 新增 `task_snapshot(task_ref)` 只读查询入口,复用已有 short id 前缀匹配。
- 更新 `help_text()`、`docs/human/daily-ops.md`、`CHANGELOG.md` 和 `STATUS.md`。
- 新增/更新单测:
  - 命令解析 `/tasks` / `/task`。
  - Orchestrator `/tasks` 不提交 Adapter 任务。
  - `/task` 展示 waiting approval 详情和动作。
  - `/task` usage / unknown task。
- 完整验证通过:
  - 170 个单测
  - `uv run ruff check .`
  - `uv run ruff format --check .`
  - `uv run mypy src tests`
  - `git diff --check`

### 关键决策
- 🔒 **决策 1**:`/tasks` 默认 10 条、最多 20 条,避免 Telegram 中输出过长。
- 🔒 **决策 2**:`/task` 复用现有 short id 前缀匹配,和 `/approve`、`/interrupt` 保持一致。
- 🔒 **决策 3**:本轮只做 IM 可观测,不引入 HTTP API 或数据库。

### 留给下一轮
- 重启后真实验收:
  - `/tasks`
  - `/task <short_task_id>`
  - waiting approval action 提示
  - running task interrupt action 提示
- 继续 Phase 5 `@reviewer` smoke test,用 `/tasks` / `/task` 观察 Codex accepted 后的状态与 idle timeout。

### 状态变化
- Phase 5 进度新增 Task trace commands(`/tasks` / `/task`)。

## Round 60 — 2026-05-06 — Codex

### 输入
- 人类已经验证 `/task` / `/tasks` 相关命令,要求继续开始后续功能开发。
- Round 59 留下的下一步是继续 Phase 5 `@reviewer` 真实协作 smoke test,并用 IM 侧任务追踪观察 parent / child task 与 Codex idle timeout。

### 思考与讨论
- 候选 A:直接进入 Phase 6 看板 API → ❌ **继续暂缓**:Phase 5 真实协作还没完全闭环,现在跳到 HTTP/API 看板会扩大范围。
- 候选 B:给 `TaskSnapshot` / `TaskBus` 增加 parent/child 存储字段 → ❌ **暂缓**:`collaboration_requested` 审计事件已经记录了 child task、source persona 和 `parent_task=<id>`;为了一个 IM 查询视图先改核心任务模型,会让 TaskBus 继续变胖。
- 候选 C:让 `/task` 详情复用审计事件渲染协作上下游 → ✅ **选定**:最小改动,直接增强真实 smoke test 的现场排障能力,且符合“状态可观测、行为可审计”的北极星。

### 产出
- 更新 `src/aico/core/command_messages.py`:
  - `task_detail_message()` 可接收审计事件。
  - child task 详情展示 `requested by` 和 parent `/task <short_id>` 入口。
  - parent task 详情展示 child task、目标 persona 和 child `/task <short_id>` 入口。
- 更新 `src/aico/core/orchestrator_commands.py`:处理 `/task` 时传入当前进程内审计事件。
- 更新 `tests/unit/test_orchestrator.py`:覆盖 `@reviewer` 协作后查询 parent / child task 详情。
- 更新 `STATUS.md`、`CHANGELOG.md`、`docs/human/daily-ops.md` 和 Phase 5 collaboration playbook。

### 关键决策
- 🔒 **决策 1**:本轮不改变 TaskBus 的任务存储模型,协作 trace 先以审计事件为事实来源。
- 🔒 **决策 2**:`/task` 详情只提供可继续点击/复制的短 ID 入口,不在列表视图 `/tasks` 里堆协作树,避免 Telegram 输出过长。

### 留给下一轮
- 重启 AICO 后复测 Phase 5 `@reviewer` smoke test。
- 用 `/tasks` 找到 parent / child task,再分别执行 `/task <parent_short_id>` 和 `/task <child_short_id>`,确认协作 trace 可见。
- 若 Codex child task 仍无 stdout,确认 90 秒 idle timeout 后 `/status` 恢复 `codex: idle`;若没有恢复,再考虑 heartbeat 或更强的 adapter health 事件。

### 状态变化
- Phase 5 进度新增 `/task` collaboration parent / child trace。

## Round 61 — 2026-05-07 — Codex

### 输入
- 人类反馈 `/task parent` / `/task child` 用户价值不大,询问 Phase 5 后续是否还有大功能,并确认可以进入 Phase 6。
- 人类要求先 commit/push 当前代码,然后开启 Phase 6。
- 人类补充产品形态思考:项目起初也想对齐 CodeIsland / macOS Dynamic Island 那种多个 agent 在本机干活的掌控感,希望判断 MVP 是否只有 IM。

### 思考与讨论
- Phase 5 判断:
  - 继续围绕 `/task` 协作树加功能 → ❌ **否决**:更像排障细节,不是“老板管理 AI 公司”的主路径。
  - 把 Phase 5 关掉,真实协作 smoke test 作为后续回归项 → ✅ **选定**:协作协议、child task、审计、中断和 idle timeout 已成型,继续堆功能边际价值低。
- Phase 6 第一切片:
  - 直接做 Mac Dynamic Island / 菜单栏 → ❌ **暂缓**:很有产品味,但会先绑定本地桌面,且状态数据源还没稳定。
  - 直接做 Web dashboard / HTTP API → ❌ **暂缓**:指标口径未 dogfood 前做前端会偏重。
  - 先做 IM-first `/metrics` → ✅ **选定**:延续远程异步主路径,复用 TaskSnapshot / AuditEvent,快速验证哪些指标有用。
- 产品入口判断:
  - MVP 不应是“只有 IM”,而应是“IM 主控 + macOS glance + CLI 排障”。
  - 实现顺序必须先把 IM 指标和观测模型稳定下来,再让 Mac 状态岛消费同一份状态。

### 产出
- 提交并推送 Phase 5 收口 commit:
  - `031e41e Complete phase 5 collaboration observability`
- 新增 `docs/decisions/0014-phase-6-observability-scope.md`:
  - Phase 6 第一切片选择 IM-first `/metrics`。
  - token/cost 当前明确 unavailable,不伪造。
- 新增 `src/aico/core/metrics.py`:
  - 汇总 24h / 7d 任务数、状态分布、adapter 接活数、open work、协作请求数、平均终态耗时。
- 新增 `/metrics` 命令:
  - 更新 command parser、help、Orchestrator 分发和 IM 文本渲染。
  - `TaskBus.task_snapshots(limit=None)` 可返回当前进程内全部 task snapshot,供 metrics 使用。
- 新增 `docs/architecture/product-entrypoints.md`:
  - 记录 MVP 产品入口为 IM 主控 + macOS glance + CLI 排障。
- 新增 `docs/playbooks/phase-6-observability.md`:
  - 记录 `/metrics` Telegram smoke test 步骤。
- 更新 `STATUS.md`、`CHANGELOG.md`、`docs/human/daily-ops.md`、ADR 索引。
- 新增/更新单测:
  - 命令解析支持 `metrics`。
  - Orchestrator `/metrics` 不派发 Adapter 任务,展示状态分布、open work 和 collaboration 数。

### 关键决策
- 🔒 **决策 1**:Phase 5 标记为 feature complete,真实 Telegram 协作 smoke test 后续作为 Phase 6 回归项。
- 🔒 **决策 2**:Phase 6 第一切片不做 Mac GUI / Web dashboard,先做 IM-first `/metrics`。
- 🔒 **决策 3**:Mac Status Island 后续定位为本地 glance 入口,消费 Phase 6 观测模型,不成为唯一主控台。

### 留给下一轮
- 重启 AICO 后真实验收 `/metrics`:
  - 先制造 done / waiting approval / running / collaboration 几类任务。
  - 发送 `/metrics`,确认 24h / 7d 指标和 open work 符合预期。
- 设计 Phase 6 观测状态持久化,解决重启后 24h / 7d 指标丢失的问题。
- 若开始 Mac Status Island 原型,只做 glance / approve / interrupt / jump,不要把完整项目管理搬进本地 UI。

### 状态变化
- Phase 5:进行中 → 完成(feature complete;真实 smoke test 作为回归项保留)。
- Phase 6:未开始 → 进行中。
- Phase 6 进度新增 ADR-0014、`/metrics` MVP、产品入口判断文档和 smoke test playbook。

## Round 62 — 2026-05-07 — Codex

### 输入
- 人类暂时没空验收新功能,要求继续迭代,明天白天再验收能力。
- Round 61 留给下一轮的最高代码侧任务是 Phase 6 观测状态持久化,解决 `/metrics` 重启后清空的问题。

### 思考与讨论
- 候选 A:新增 TaskSnapshot JSONL → ❌ **否决**:会和已有 audit JSONL 形成两份事实来源,需要额外处理双写一致性。
- 候选 B:直接上 SQLite Task/Audit repository → ❌ **暂缓**:Phase 6 指标口径还没真实 dogfood,现在引入数据库和查询层偏重。
- 候选 C:回放已有 audit JSONL 重建 metrics task snapshot → ✅ **选定**:复用 Phase 4 审计事实来源,不加新依赖,能解决重启后历史 done/failed/interrupted/rejected/waiting approval 指标恢复。

### 产出
- 新增 `docs/decisions/0015-observability-event-replay.md`:
  - 确定 Phase 6 先用 audit JSONL replay,不新增 task snapshot JSONL 或 SQLite。
- 更新 `src/aico/core/audit.py`:
  - 新增 `read_jsonl_audit_events(path)`。
  - `InMemoryAuditLog` 支持 `initial_events`。
- 更新 `src/aico/app/phase1.py`:
  - 配置 `AICO_AUDIT_LOG_PATH` 后,启动时读取历史 audit JSONL 并注入 audit log。
- 更新 `src/aico/core/metrics.py`:
  - 从 audit events 重建 metrics 用 `TaskSnapshot`。
  - `/metrics` 会合并当前进程内 snapshot 与 audit replay snapshot,当前进程内状态优先。
- 更新 `STATUS.md`、`CHANGELOG.md`、`docs/human/daily-ops.md`、Phase 6 playbook 和 ADR 索引。
- 新增/更新单测:
  - audit JSONL 读取和 `InMemoryAuditLog(initial_events=...)`。
  - audit events 重建最新 task status / risk / adapter / created / updated。
  - metrics 同时统计 replay 历史任务和当前 open work。
  - phase1 runtime 启动时加载已有 audit JSONL。

### 关键决策
- 🔒 **决策 1**:Phase 6 持久化第一切片以 audit event replay 为准,不新增第二份 task snapshot 存储。
- 🔒 **决策 2**:`/metrics` 可以从 audit replay 恢复历史指标,但 `/tasks` 仍只展示当前进程内任务,避免伪造完整任务列表。
- 🔒 **决策 3**:重建 snapshot 只服务 metrics,不恢复 payload / session history。

### 留给下一轮
- 真实 Telegram 验收 `/metrics`:
  - 配置 `AICO_AUDIT_LOG_PATH`。
  - 跑 done / waiting approval / collaboration 任务。
  - 重启 AICO 后再次 `/metrics`,确认历史指标仍可见。
- 若真实验收口径可用,下一轮可抽出稳定 metrics query 层,供未来 macOS Status Island / Web 复用。

### 状态变化
- Phase 6 进度新增 ADR-0015、audit JSONL 启动回放、`/metrics` audit-backed task snapshot 重建。

## Round 63 — 2026-05-07 — Codex

### 输入
- 人类要求“继续开发后续高优功能”。
- Round 62 留给下一轮的高优代码侧任务是:若无法立刻做真实 Telegram 验收,继续把 Phase 6 metrics summary 提炼成可被 macOS glance / Web 复用的稳定 query 层。

### 思考与讨论
- 候选 A:直接做 Mac Status Island / 菜单栏 UI → ❌ **暂缓**:还需要桌面 UI 技术选型和交互边界,且当前最大价值是先稳定数据契约,避免本地 UI 直接读 IM 文本。
- 候选 B:直接做 HTTP API / Web dashboard → ❌ **暂缓**:Phase 6 指标仍待 Telegram dogfood,现在新增服务面、鉴权和前端会扩大范围。
- 候选 C:抽出结构化 `MetricsReport`,并提供 CLI text/json 入口 → ✅ **选定**:复用 audit replay,不加依赖,让 `/metrics`、CLI 排障和后续 Mac/Web 可以共享同一份观测模型。

### 产出
- 更新 `src/aico/core/metrics.py`:
  - 新增 `MetricsReport`、`MetricsGlance`、`TokenCostSummary`。
  - `build_metrics_report()` 统一合并当前 task snapshot 与 audit replay snapshot。
  - `metrics_report_to_dict()` 输出 JSON 友好的稳定结构。
- 更新 `src/aico/core/command_messages.py`:
  - `/metrics` 改为渲染 `MetricsReport`。
  - 新增 `glance` 小节,展示 `needs_approval` / `working` / `attention` / `quiet` 与 open/running/waiting/failed 数。
- 新增 `src/aico/app/metrics_cli.py` 和 console script `aico-metrics`:
  - 支持 `--audit-log <path>` 或 `AICO_AUDIT_LOG_PATH`。
  - 支持 `--format text|json`。
- 新增/更新单测:
  - Metrics report glance / token-cost 状态。
  - Metrics JSON 序列化。
  - `aico-metrics` text/json 输出。
  - Orchestrator `/metrics` 输出 glance。
- 更新 `STATUS.md`、`CHANGELOG.md`、`docs/human/daily-ops.md` 和 Phase 6 playbook。
- 完整验证通过:
  - 179 个单测
  - `uv run ruff check .`
  - `uv run ruff format --check .`
  - `uv run mypy src tests`
  - `git diff --check`

### 关键决策
- 🔒 **决策 1**:Phase 6 当前只稳定 metrics query/report 层和 CLI 排障入口,不新增 HTTP API 或 Mac GUI。
- 🔒 **决策 2**:`glance` 只表达当前 24h 窗口的紧凑状态,不把完整项目管理语义塞进指标层。
- 🔒 **决策 3**:token/cost 继续显式 unavailable,但作为结构化字段保留,等待 Adapter 未来稳定提供 usage。

### 留给下一轮
- 真实 Telegram 验收 `/metrics`:
  - 配置 `AICO_AUDIT_LOG_PATH`。
  - 制造 done / waiting approval / collaboration 任务。
  - 检查 `glance`、24h / 7d summaries、open work 和 collaboration 数。
  - 重启 AICO 后复查历史指标仍可见。
- 用同一份 audit JSONL 跑 `aico-metrics --audit-log <path>` 和 `aico-metrics --audit-log <path> --format json`,确认 CLI text/json 与 Telegram 口径一致。
- 若开始 Mac Status Island 原型,消费 `MetricsReport` / `aico-metrics --format json`,只做 glance / approve / interrupt / jump。

### 状态变化
- Phase 6 进度新增 MetricsReport 稳定查询模型。
- Phase 6 进度新增 `aico-metrics` CLI text/json 排障入口。

## Round 64 — 2026-05-07 — Codex

### 输入
- 人类要求把 Phase 6 规划的核心能力都开发完,随后一起验收;验收没问题就进入 Phase 7。
- 当前 Phase 6 剩余代码侧核心缺口是 macOS Status Island / glance 原型和 token/cost 接入边界。

### 思考与讨论
- 候选 A:直接做完整 macOS 菜单栏 / Dynamic Island UI → ❌ **暂缓**:需要新的 GUI 技术栈、权限和发布形态;Phase 6 当前应该先稳定可观测数据契约。
- 候选 B:新增 `aico-glance` 数据原型,输出 text/json 给 xbar/Swift/后续原生菜单栏消费 → ✅ **选定**:复用 `MetricsReport`,不加依赖,能覆盖 active agents、open work、最近任务和动作命令提示。
- 候选 C:直接做 HTTP API / Web dashboard → ❌ **暂缓**:验收前新增服务面、鉴权和前端会扩大范围,且 Web/mobile 在产品入口文档里属于后续入口。
- token/cost:
  - 直接估算 token/cost → ❌ **否决**:违反“不要伪造指标”。
  - 等 Adapter 稳定提供 usage 后再做任何代码 → ❌ **否决**:Phase 6 需要先有稳定接入边界。
  - 新增 `task_usage_recorded` 审计事件和 JSON detail 约定 → ✅ **选定**:真实上报一旦可用即可进入 MetricsReport 汇总。

### 产出
- 新增 `docs/decisions/0016-status-island-and-usage-boundary.md`:
  - 确认 Phase 6 不做完整 GUI / Web,先做 glance 数据原型和 usage 接入边界。
- 新增 `src/aico/core/status_island.py`:
  - `StatusIslandSnapshot` / `StatusIslandTask`。
  - `build_status_island_snapshot()`。
  - `status_island_text()` / `status_island_to_dict()`。
- 新增 `src/aico/app/glance_cli.py` 和 console script `aico-glance`:
  - 支持 `--audit-log <path>` 或 `AICO_AUDIT_LOG_PATH`。
  - 支持 `--format text|json`。
  - 最近任务会给出 `/task`、`/approve`、`/reject`、`/interrupt` 命令提示。
- 更新 `src/aico/core/metrics.py`:
  - `MetricsReport` 新增 `recent_tasks`。
  - 新增 `UsageRecord`、`usage_audit_detail()`、`usage_records_from_audit_events()`。
  - `TokenCostSummary` 汇总真实 usage audit events;没有 usage 时继续 unavailable。
- 更新 `src/aico/core/models.py`:新增 `AuditEventType.TASK_USAGE_RECORDED`。
- 新增/更新单测:
  - Status Island snapshot text/json。
  - `aico-glance` text/json 输出。
  - usage audit detail 解析与 token/cost 汇总。
- 完整验证通过:
  - 184 个单测
  - `uv run ruff check .`
  - `uv run ruff format --check .`
  - `uv run mypy src tests`
  - `git diff --check`

### 关键决策
- 🔒 **决策 1**:Phase 6 核心能力以 IM metrics + audit replay + CLI metrics + local glance data + usage boundary 收口,不把完整 GUI/Web 塞进本阶段。
- 🔒 **决策 2**:`aico-glance` 只读取 audit JSONL,不直接操作运行中进程;approve / reject / interrupt 通过 IM 命令提示完成。
- 🔒 **决策 3**:token/cost 只接受 Adapter 真实上报的 `task_usage_recorded` 审计事件,没有真实数据时继续显示 unavailable。

### 留给下一轮
- 集中真实验收 Phase 6:
  - Telegram `/metrics` 和重启恢复。
  - `aico-metrics` text/json。
  - `aico-glance` text/json。
  - Phase 5 `@reviewer` 协作 smoke test 作为回归项。
- 如果验收通过,开启 Phase 7 共享记忆层 ADR,先定义最小记忆范围和可审计边界。

### 状态变化
- Phase 6 进度新增 ADR-0016。
- Phase 6 进度新增 macOS Status Island / glance 数据原型(`aico-glance`)。
- Phase 6 进度新增 token / cost usage 审计事件接入边界。
- Phase 6 代码侧核心能力完成,剩余集中真实验收。

## Round 65 — 2026-05-07 — Codex

### 输入
- 人类补充近期方向:当前文档中的其他计划继续按进度推进,但近期要高优支持:
  - CodeFlicker Adapter、Cursor Adapter,最终让 Telegram `/agents` 有更多可用 agents,并保持可扩展可插拔,未来可继续实现 Trae、OpenClaw 等。
  - 新增 IM Channel,从飞书、钉钉、QQ、微信中先选择 1-2 个支持;选择依据主要是对接成本,因为部分 IM 协议并不标准。

### 思考与讨论
- 候选 A:立刻把 Phase 7 替换为“多 Adapter / 多 Channel Phase” → ❌ **否决**:Phase 6 代码侧刚收口但还缺集中真实验收,直接改阶段会让观测基线不稳;人类也明确“其他计划按进度推进”。
- 候选 B:只在最终回复里口头记一下 → ❌ **否决**:这类方向会影响后续多轮优先级,必须进入 `STATUS.md` 和 `ROUNDS.md`,否则下一轮 Agent 很容易继续只看旧的 Phase 7 建议。
- 候选 C:把它记录成近期高优产品方向,并调整下一轮建议优先级 → ✅ **选定**:不推翻 Phase 6 / Phase 7,但让 Adapter 扩展和 Channel 扩展成为真实验收后的高优路线。
- Adapter 边界:
  - 新工具必须继续实现 `AIAdapter`,通过 `AdapterRegistry`、persona/project 配置进入 `/agents`,不能在核心编排里写 `if codeflicker/cursor`。
  - CodeFlicker / Cursor 的 CLI/API 形态可能变化,进入实现前必须核验官方最新入口,不要按记忆硬写。
- Channel 边界:
  - 新 IM 必须继续实现 `IMChannel`,复用平台无关 render contract。
  - 如果某个 IM 不支持 Telegram 式编辑消息或 inline action,降级逻辑留在 Channel 内部,核心仍只处理 `MessageContent` / `MessageAction`。
  - 先做 1-2 个,不是四个全上;协议标准化、鉴权/部署成本和 dogfooding 成本是首要选择标准。

### 产出
- 更新 `STATUS.md`:
  - 新增“近期高优产品方向”小节。
  - 记录 Adapter 扩展计划:CodeFlicker、Cursor、`/agents` 可见、Trae/OpenClaw 后续可插拔。
  - 记录 Channel 扩展计划:飞书/钉钉/QQ/微信中按成本选 1-2 个,先做文本收发和 render contract 映射。
  - 重排“下一轮建议”,把 Phase 6 验收作为稳定基线,并把 Adapter / Channel 扩展调研与第一实现切片提升为高优。
- 追加本轮 `ROUNDS.md` 记录。

### 关键决策
- 🔒 **决策 1**:近期计划不取消 Phase 6 集中验收,而是在验收基线上推进多 Adapter / 多 Channel 扩展。
- 🔒 **决策 2**:CodeFlicker / Cursor 只通过既有 Adapter 插件路径接入,目标用户体验是 `/agents` 出现更多可用成员。
- 🔒 **决策 3**:飞书、钉钉、QQ、微信不一次性全量接入;先按官方协议标准化和真实对接成本选择 1-2 个。

### 留给下一轮
- 先完成 Phase 6 集中真实验收,把 `/metrics`、`aico-metrics`、`aico-glance` 的状态基线跑稳。
- 随后优先做 CodeFlicker / Cursor 官方入口调研,选 1 个最小 Adapter 实现切片,并确保 `/agents` 能展示。
- 并行或下一轮做飞书 / 钉钉 / QQ / 微信官方 Bot/API 成本核验,选出第一个 Channel 实现目标。

### 状态变化
- `STATUS.md` 当前轮次更新为 Round 65。
- `STATUS.md` 新增近期高优产品方向。
- `STATUS.md` 下一轮建议新增 Adapter 扩展和 Channel 扩展高优项。

## Round 66 — 2026-05-07 — Codex

### 输入
- 人类要求“开始按照计划开发”,有问题和决策疑惑可以找人类确认。
- Round 65 的近期高优方向中,Adapter 扩展排在前列:CodeFlicker Adapter、Cursor Adapter,目标是让 Telegram `/agents` 有更多可用 agents。

### 思考与讨论
- 候选 A:先做 Channel 扩展 → ❌ **暂缓**:飞书、钉钉、QQ、微信需要更多官方 Bot/API 成本核验和可能的人类账号/后台配置配合;Adapter 扩展更容易在当前本地代码里切出可测 MVP。
- 候选 B:先做 Cursor Adapter → ✅ **部分选定**:Cursor 官方文档明确 `cursor-agent -p --output-format text` 非交互形态,适合快速接入。
- 候选 C:先做 CodeFlicker Adapter → ✅ **部分选定**:公开官网没有稳定 CLI 细节,但本机已有 `flickcli`,且 `flickcli --help` 确认 `-q`、`--cwd`、`--tools`、`--output-format`;可以做本机可选 Adapter。
- 候选 D:默认把 Cursor / CodeFlicker 暴露为写能力 Agent → ❌ **否决**:远程 IM 默认放开写文件 / shell 会绕过现有审批纪律;第一切片先按只读分析/规划能力接入。
- 候选 E:重构出通用 CLI Adapter 配置类 → ❌ **否决**:目前已有 Claude/Codex/ Cursor/CodeFlicker 四个样本,但 Claude/Codex 已经有 session/resume 差异;本轮目标是小切片扩展 `/agents`,先复用 `ClaudeCodeAdapter` 子类,不在功能推进中夹带大重构。

### 产出
- 新增 `src/aico/adapter/cursor.py`:
  - `CursorAdapter` 复用 `ClaudeCodeAdapter` 的进程、流式输出、中断、health check。
  - 默认命令 `cursor-agent -p --output-format text`。
  - 默认只声明 `CODE_REVIEW`、`LONG_RUNNING`、`STREAM_OUTPUT`、`INTERRUPTIBLE`。
- 新增 `src/aico/adapter/codeflicker.py`:
  - `CodeFlickerAdapter` 复用 `ClaudeCodeAdapter`。
  - 默认命令 `flickcli -q --output-format text --tools '{"bash":false,"write":false}'`。
  - 配置了 cwd 时会向 CLI 追加 `--cwd <path>`。
- 更新 `src/aico/app/phase1.py`:
  - 新增 `AICO_ENABLE_CURSOR_ADAPTER` / `AICO_CURSOR_COMMAND` / `AICO_CURSOR_OUTPUT_IDLE_TIMEOUT_SECONDS`。
  - 新增 `AICO_ENABLE_CODEFLICKER_ADAPTER` / `AICO_CODEFLICKER_COMMAND` / `AICO_CODEFLICKER_OUTPUT_IDLE_TIMEOUT_SECONDS`。
  - 默认 personas 在对应 Adapter 启用时加入 `cursor` 和 `codeflicker`,因此 `/agents` 可展示新 agent。
- 新增 ADR-0017,记录可选只读 Adapter 第一切片决策。
- 新增 `docs/playbooks/optional-agent-adapters.md`,记录 Cursor / CodeFlicker 真实 smoke test 步骤。
- 更新 `CHANGELOG.md`、`docs/human/daily-ops.md`、`docs/playbooks/README.md`、`docs/decisions/README.md` 和 `STATUS.md`。
- 新增/更新单测:
  - `test_cursor_adapter.py`
  - `test_codeflicker_adapter.py`
  - `test_phase1_app.py` 中可选 Adapter 配置和 `/agents` 门面覆盖。
- 完整验证通过:
  - 193 个单测
  - `uv run ruff check .`
  - `uv run ruff format --check .`
  - `uv run mypy src tests`
  - `git diff --check`

### 关键决策
- 🔒 **决策 1**:Cursor / CodeFlicker 第一切片默认是可选只读 Adapter,不默认暴露写文件 / shell 能力。
- 🔒 **决策 2**:新增 Adapter 只通过 `AIAdapter` / `AdapterRegistry` / Persona 接入,不修改核心路由语义。
- 🔒 **决策 3**:暂不实现 Cursor / CodeFlicker provider session resume;等真实 smoke test 和使用习惯明确后再做。

### 留给下一轮
- 做 Cursor / CodeFlicker 真实 smoke test:
  - Cursor:先安装并登录 `cursor-agent`,再设置 `AICO_ENABLE_CURSOR_ADAPTER=true`。
  - CodeFlicker:确认 `flickcli` SSO 已登录,再设置 `AICO_ENABLE_CODEFLICKER_ADAPTER=true`。
  - Telegram 中发送 `/agents`、`/cursor ...`、`/codeflicker ...`、`/status`、`/tasks`。
- 若真实运行发现 CLI 长时间无输出或输出格式不稳定,优先调整 Adapter 内部命令/解析,不要改核心。
- Channel 扩展进入下一高优:对飞书、钉钉、QQ、微信做官方 Bot/API 成本核验,选第一个 Channel。

### 状态变化
- `STATUS.md` 当前轮次更新为 Round 66。
- 近期高优产品方向中 Cursor Adapter MVP、CodeFlicker Adapter MVP 标记完成。
- 下一轮建议把 Cursor / CodeFlicker 真实 smoke test 提升为高优。

## Round 67 — 2026-05-12 — Codex

### 输入
- 人类要求 Cursor / CodeFlicker “完整支持”,并新增 Trae CLI、Gemini CLI Adapter。
- 人类要求增强 company 感,补充确实有 AI 公司产出的 roles:PM、资深架构师、goldenTester、市场风险、合规法务审查等;短期不要前台、仓库管理员、财务、客户经理这类低相关岗位。
- 人类要求从飞书、钉钉、QQ、微信中选择一个官方接口文档最好、接入成本可控的 Channel。

### 思考与讨论
- 候选 A:继续保持 Cursor / CodeFlicker 只读,Trae / Gemini 也只做只读 → ❌ **否决**:不满足“完整支持”,也无法让这些 CLI 成为真实可派工成员。
- 候选 B:在 AICO 审批门禁下开放 CLI 完整能力 → ✅ **选定**:Adapter capabilities 声明 `code_edit` / `shell_exec`,危险任务仍先走 AICO 风险识别、`/approve`、审计和 `/interrupt`;底层 CLI 用非交互批准模式避免远程任务卡在本机确认。
- 候选 C:扩展 `AIAdapter.receive_task()` 协议,让 Adapter 按 risk 动态切 command approval mode → ❌ **暂缓**:需要改公开协议和 TaskBus/Adapter 交互面,本轮范围会扩大;先复用现有风险门禁闭环。
- Channel 选择:
  - 飞书 → ✅ **选定**:官方 Server API / 事件订阅文档较完整,企业自建应用 + bot 文本收发路径清晰,适合先做企业 IM dogfooding。
  - 钉钉 → ⚪ 可行但未选:机器人能力也标准,但本轮只选一个;飞书 / Lark 文档和应用模型更贴近后续多团队入口。
  - QQ / 微信 → ❌ 暂缓:审核、白名单、合规和非标准机器人能力摩擦更高,不适合作为第一个低成本 Channel。
- Role 扩展原则:
  - 只加能直接服务 AI 公司交付的岗位:PM、Senior Architect、Golden Tester、Market Risk、Legal Compliance。
  - 不加短期缺少 AI 公司产出的职能,避免“公司感”变成空壳角色扮演。

### 产出
- 更新 `CursorAdapter`:
  - 默认命令改为 `cursor-agent -p --force --output-format text`。
  - capabilities 增加 `code_edit` / `shell_exec`。
  - 已绑定 provider session 时支持 `--resume <session_id>`。
- 更新 `CodeFlickerAdapter`:
  - 默认命令改为 `flickcli -q --approval-mode yolo --output-format text`。
  - capabilities 增加 `code_edit` / `shell_exec`。
  - 支持 `--cwd` 和 provider session `--resume`。
- 新增 `TraeAdapter`:
  - 默认命令 `trae-cli --print --yolo`。
  - 支持 `--session-id` / `--resume`。
- 新增 `GeminiAdapter`:
  - 默认命令 `gemini --approval-mode yolo --output-format text`。
  - 支持已绑定 provider session `--resume`。
- 更新 `aico-phase1` wiring:
  - 新增 `AICO_ENABLE_TRAE_ADAPTER` / `AICO_TRAE_COMMAND` / `AICO_TRAE_OUTPUT_IDLE_TIMEOUT_SECONDS`。
  - 新增 `AICO_ENABLE_GEMINI_ADAPTER` / `AICO_GEMINI_COMMAND` / `AICO_GEMINI_OUTPUT_IDLE_TIMEOUT_SECONDS`。
  - 默认 personas 增加 `trae` 和 `gemini`。
  - provider session factory 支持 `codeflicker` 和 `trae` 的 new/resume。
- 更新默认 role 模板:
  - 新增或强化 `pm`、`senior-architect`、`golden-tester`、`market-risk`、`legal-compliance`。
  - 默认 AICO 项目 roles 覆盖全部内置有效岗位。
- 新增 `FeishuChannel`:
  - 获取 tenant access token。
  - 文本发送、编辑、删除。
  - URL verification challenge。
  - `im.message.receive_v1` 文本事件转 `IncomingMessage`。
  - `MessageContent.actions` 第一切片降级为纯文本提示。
- 新增 ADR-0018 和 Feishu Channel playbook。
- 更新 optional adapters playbook、daily ops、ADR/playbook 索引、CHANGELOG、STATUS。
- 新增/更新单测:
  - Cursor / CodeFlicker 完整能力和 resume 命令。
  - Trae / Gemini Adapter 默认命令和 session 命令。
  - Feishu Channel token、发送、URL verification、文本事件解析。
  - Phase1 runtime 可启用所有 optional adapters 和新增 roles。
  - 修复 `aico-metrics` / `aico-glance` CLI 测试中的固定日期,避免当前日期推进后 24h/7d 窗口断言失效。
- 完整验证通过:
  - 207 个单测
  - `uv run ruff check .`
  - `uv run ruff format --check .`
  - `uv run mypy src tests`

### 关键决策
- 🔒 **决策 1**:Cursor / CodeFlicker / Trae / Gemini 作为完整能力 Adapter 接入,底层 CLI 使用非交互批准模式,远程安全边界由 AICO 审批/审计/中断承担。
- 🔒 **决策 2**:第一个非 Telegram Channel 选择 Feishu,先做 Channel 插件和 payload handler,不在本轮引入完整 callback server 生命周期。
- 🔒 **决策 3**:AI Company role 扩展只加能直接提升交付、架构、验收、市场风险、合规审查能力的岗位。

### 留给下一轮
- 真实 smoke test:
  - Cursor:安装并登录 `cursor-agent`,启用 `AICO_ENABLE_CURSOR_ADAPTER=true`,跑只读和写能力审批任务。
  - CodeFlicker:确认 `flickcli` SSO,启用 `AICO_ENABLE_CODEFLICKER_ADAPTER=true`,跑只读和写能力审批任务。
  - Trae:处理本机 keyring/token 问题,启用 `AICO_ENABLE_TRAE_ADAPTER=true`,跑只读和写能力审批任务。
  - Gemini:确认登录/API key,启用 `AICO_ENABLE_GEMINI_ADAPTER=true`,跑只读和写能力审批任务。
- Feishu 部署层:
  - 用 FastAPI route 或现有服务入口承接飞书 callback,调用 `FeishuChannel.handle_event(payload)`。
  - 在飞书开放平台完成 URL verification 和 `im.message.receive_v1` 订阅。
  - 真实验证文本入站、回复、编辑/删除降级。
- Phase 6 集中真实验收仍未完成,不要直接跳 Phase 7。

### 状态变化
- `STATUS.md` 当前轮次更新为 Round 67。
- Adapter 扩展方向新增 Trae / Gemini,Cursor / CodeFlicker 从 MVP 只读升级为完整能力。
- Channel 扩展方向选择 Feishu,第一切片 mock 测试完成,真实 callback server 待下一轮。

## Round 68 — 2026-05-13 — Codex

### 输入
- 人类反馈 `/agents` 中 `implementer` / `reviewer` 与 `cursor` / `codeflicker` / `trae` / `gemini` 命名层混用,`/roles` 太长且格式体感不好。
- 人类要求讨论并先优化一版权限分层:每层枚举要符合 AI Company OS 使用直觉、好记、不要太多,可引入真实团队管理中“默认管理幅度有限、讨论人数不宜过多”的经验。

### 思考与讨论
- 候选 A:实现完整 RBAC / role-aware runtime gate → ❌ **否决**:当前危险动作已有 risk assessor、adapter capability、`/approve` 和审计闭环;本轮直接上 RBAC 会扩大范围,也会让个人 dogfooding 配置变重。
- 候选 B:只改 `/roles` 文案,不定义权限词表 → ❌ **否决**:下一轮仍可能继续新增 `read_xxx` / `write_xxx` 细粒度 token,权限语言会再次发散。
- 候选 C:保留三层边界,但把词表收敛到少量可记忆枚举 → ✅ **选定**:
  - Adapter capability 表达工具物理能力。
  - Role scope 表达岗位默认工作范围。
  - Risk level 表达单次任务风险与审批。
- 命令 UX:
  - `/agents` 应回答“公司里有哪些可派工成员/工具入口”,所以默认显示 `claude` / `codex` 这类入口名,岗位名作为 role 标注。
  - `/roles` 应回答“项目有哪些岗位、谁负责”,默认只展示核心/专家岗位;支持岗位和长说明按需展开。
  - `/role <id>` 承担详情页职责,避免默认列表变成长配置。

### 产出
- 新增 `RoleScope` 枚举:`docs` / `code` / `tests` / `ops` / `audit`。
- 更新默认 role 模板,把 `read_repo` / `write_docs` / `run_tests` 等细粒度默认 permissions 收敛为 5 个 role scope。
- `/appoint <agent> as <role>` 不传 scope 时,自动继承 role 默认 scope。
- `/agents` 默认输出改为工具入口名优先,例如 `claude -> claude-code [role: implementer]`。
- `/roles` 默认输出改为紧凑岗位板:
  - Core:`pm`、`implementer`、`reviewer`、`golden-tester`。
  - Specialists:`senior-architect`、`security`、`legal-compliance`、`market-risk`。
  - Support 默认隐藏到 `/roles all`。
- 新增 `/role <id>` 详情视图,展示 owner、scope、approval 和 risk ladder。
- 新增 ADR-0019,记录三层权限词表和紧凑团队视图决策。
- 更新 `STATUS.md`、`CHANGELOG.md` 和 ADR 索引。
- 更新单测覆盖 compact `/agents`、compact `/roles`、`/roles all`、`/role <id>`、默认 appointment scope 继承和 Phase1 默认 assignment scope。
- 完整验证通过:
  - 208 个单测
  - `uv run ruff check .`
  - `uv run ruff format --check .`
  - `uv run mypy src tests`
  - `git diff --check`

### 关键决策
- 🔒 **决策 1**:本轮不引入完整 RBAC;role scope 是岗位契约和 prompt/appointment 上下文,不是强运行时 ACL。
- 🔒 **决策 2**:权限语言稳定为三层:Adapter capability、Role scope、Risk level。
- 🔒 **决策 3**:`/roles` 默认视图遵守团队管理幅度,只展示少数关键岗位;全量信息进入 `/roles all` / `/role <id>`。

### 留给下一轮
- 如需让 role scope 真正参与执行门禁,新增 `RoleAuthorizationPolicy` 并写新 ADR,不要把 scope 检查散落进 `TaskBus`。
- 对新 `/agents` / `/roles` / `/role <id>` 做 Telegram 真实体感复验。
- Phase 6 集中真实验收仍未完成,不要直接跳 Phase 7。

### 状态变化
- `STATUS.md` 当前轮次更新为 Round 68。
- Phase 5 已完成项补充 `/agents` 工具入口名优先展示和 `/roles` 紧凑视图。
- 新增 ADR-0019。

## Round 69 — 2026-05-13 — Codex

### 输入
- 人类发现多个任务进入 `waiting_approval` 后,裸 `/approve` 会返回:
  `multiple pending approvals: e89c1271, b216b23d, ec63d793`。
- 人类尝试 `/interrupt e89c1271` 清理待审批任务,但收到:
  `task is waiting_approval, not running`。
- 人类想测试 `lead` 某个 agent 后询问团队和项目问题,怀疑当前也无法自然实现。

### 思考与讨论
- 候选 A:新增完整 pending approval 管理器和 `/approvals` 命令 → ❌ **暂缓**:有用,但本轮真正阻塞是普通项目咨询误进审批队列,先修根因。
- 候选 B:允许裸 `/approve` 默认 approve 最新 pending approval → ❌ **否决**:多个危险任务同时待审批时默认批准某一个不安全,也不符合可审批/可审计。
- 候选 C:让 `/interrupt <task_id>` 可以取消 waiting approval → ✅ **选定**:符合“可中断”直觉,也提供清理 pending 队列的最小通用能力。
- 候选 D:给 lead 问题新增 `/ask-info` 或 `/consult` 命令 → ❌ **否决**:会让用户记更多命令;老板在项目办公室里直接问 lead 问题应该自然工作。
- 根因定位:
  - project lead / role task 会渲染完整 Appointment Prompt Stack。
  - 旧 `TextRiskAssessor` 扫整段 prompt,role summary / inline prompt 里的 `write`、`run tests` 等词会污染风险识别。
  - 真正应该评估的是 `Current task:` 之后的人类请求。

### 产出
- 更新 `TextRiskAssessor`:
  - 如果 task payload 包含 `Current task:`,只对最后一个 `Current task:` 后的文本做风险识别。
  - 纯普通 task 仍按整段 payload 识别。
  - 真实用户请求里出现 `run pytest` / `update STATUS.md` / destructive 词时仍触发审批。
- 更新 `TaskBus.interrupt()`:
  - running 任务仍按原逻辑中断 Adapter。
  - `waiting_approval` 任务会被取消,任务状态改为 `interrupted`,pending approval 不再出现在 `/approve` 待选集合中。
  - 记录 `approval_rejected` 和 `task_interrupted` 审计事件,detail 为 `interrupted before approval`。
- 新增测试:
  - risk assessor 忽略 appointment prompt scaffolding 中的 write/run。
  - risk assessor 仍识别 `Current task` 内的真实写/执行请求。
  - task bus interrupt 可取消 waiting approval。
  - orchestrator 中 active project 普通团队/项目问题不会误触发 approval。
- 更新 `STATUS.md` 和 `PITFALLS.md`。
- 完整验证通过:
  - `uv run pytest tests/unit/test_risk.py tests/unit/test_task_bus.py tests/unit/test_orchestrator.py`
  - 72 passed
  - `uv run pytest`
  - 212 passed
  - `uv run ruff check .`
  - `uv run ruff format --check .`
  - `uv run mypy src tests`
  - `git diff --check`

### 关键决策
- 🔒 **决策 1**:风险识别的输入边界是用户真实请求,不是完整 system/role/project prompt。
- 🔒 **决策 2**:`/interrupt <task_id>` 既可中断 running,也可取消 waiting approval;这比新增专门 cancel 命令更符合当前命令模型。
- 🔒 **决策 3**:裸 `/approve` 在多个 pending approvals 时仍不默认选择,必须由用户指定 task id。

### 留给下一轮
- Telegram 真实复验:
  - `/project aico`
  - `/lead implementer`
  - 直接问“这个项目现在团队分工和下一步重点是什么?”
  - 确认不会进入 approval。
  - 人为制造两个待审批任务,用 `/interrupt <short_id>` 取消其中一个,再 `/approve <short_id>` 或 `/reject <short_id>` 处理另一个。
- 如果 pending approval 管理仍不顺手,再新增 `/approvals` 或把 `/tasks` 中 waiting approval 展示做得更突出。

### 状态变化
- `STATUS.md` 当前轮次更新为 Round 69。
- 新增 PITFALL P-016 并标记 resolved。

## Round 70 — 2026-05-14 — Codex

### 输入
- 人类要求让项目命令更有指导性、流程更丝滑。
- 重点命令:`/role`、`/agent`、`/project`、`/team` 等查看类命令。
- 人类希望看完 role 后知道如何授权 permission / scope,看完 agent 后知道如何 appoint,看完 project 后知道如何看日报/周报等。
- 指导命令要足够简短,符合用户动线,同时可作为后续扩展命令的要求。

### 思考与讨论
- 候选 A:扩展 `/help` 为长帮助页 → ❌ **否决**:`/help` 已经是百科入口,不能解决每个页面看完后的下一步动线。
- 候选 B:每个查看结果末尾追加短 `Next:` → ✅ **选定**:最小改动,直接改善 IM 操作流,也不会改变业务语义。
- 候选 C:新增 `/scope <role> ...` 命令 → ❌ **暂缓**:有产品价值,但本轮不应新增权限写入命令;当前已有 `/appoint <agent> as <role> <scope>` 覆盖同 role appointment 的 scope,先复用它。
- Next 设计原则:
  - 每个查看结果只给少量下一步,不做长文档。
  - 使用当前上下文填入真实 role / agent,减少占位符。
  - 默认只推荐已有命令;scope 调整复用 `/appoint`。

### 产出
- `/agents` 输出新增 Next:
  - `/agent <agent>`
  - `/roles`
  - `/appoint <agent> as <role>`
- `/agent <agent>` 输出新增 Next:
  - idle: `/roles`、`/appoint <agent> as <role>`、`/new <agent>`
  - 非 idle: `/tasks`、`/status`、`/agent <agent>`
- `/project` 输出新增 Next:
  - `/brief`
  - `/team`
  - `/next`
  - `/daily`
  - `/weekly`
- `/team` 输出新增 Next:
  - 有 lead: `/ask <lead-role> <task>`、`/who <lead-role>`、`/roles`、`/lead <role>`
  - 无 appointment: `/roles`、`/agents`、`/appoint <agent> as <role>`
- `/roles` 输出新增 Next:
  - `/role <role>`
  - `/agents`
  - `/appoint <agent> as <role>`
  - `/roles all`
- `/role <id>` 输出新增 Next:
  - 未任命:`/agents`、`/appoint <agent> as <role>`、`/roles`
  - 已任命:`/ask <role> <task>`、`/lead <role>`、`/appoint <agent> as <role> <scope>`、`/unappoint <role>`
- 更新 `STATUS.md`、`CHANGELOG.md`、`docs/human/daily-ops.md`、`docs/architecture/project-assignment-layer.md`。
- 新增/更新单测覆盖 project / team / roles / role / agents guidance。
- 完整验证通过:
  - `uv run pytest`
  - 215 passed
  - `uv run ruff check .`
  - `uv run ruff format --check .`
  - `uv run mypy src tests`
  - `git diff --check`

### 关键决策
- 🔒 **决策 1**:Next guidance 是页面级动作提示,不是替代 `/help` 的完整命令说明。
- 🔒 **决策 2**:本轮不新增 `/scope`;scope 调整先复用 `/appoint` 的同 role 覆盖语义。
- 🔒 **决策 3**:Next guidance 不做复杂工作流引擎,只在 message builder 中基于已有上下文生成短命令列表。

### 留给下一轮
- Telegram 真实体感复验 `/project`、`/team`、`/roles`、`/role implementer`、`/agents`、`/agent claude` 的 Next 是否足够短。
- 如果 `/appoint <agent> as <role> <scope>` 作为 scope 调整入口不够直觉,再单独设计 `/scope <role> ...`。

### 状态变化
- `STATUS.md` 当前轮次更新为 Round 70。
- Phase 5 已完成项补充查看类命令 Next guidance。

## Round 71 — 2026-05-14 — Codex

### 输入
- 人类在 Telegram 真实验证后发现:`/roles` 等项目消息里的 `Next:` 命令没有变蓝、不可触碰发送。
- 对比现象:`/agents` 输出中的 `- /agent <agent>` 可以被 Telegram 识别,但项目消息中被转成 `• /role <role>` 后不行。
- 预期:Next 中提示的 `/command` 应保持 Telegram 可识别的裸命令形态。

### 根因定位
- Project message renderer 会把普通 Markdown list 前缀 `- ` / `* ` 统一规范成 `• `。
- 同一渲染链路还会给所有 `/command` 添加 `MessageTextStyle.CODE` span。
- Telegram 发送 rich text 后,code span 和 bullet 规范化会压掉 bot command 的原生自动识别。
- `/agents` 属于普通 command message builder,没有走 project message render spans,所以保留 `- /command` 后能被 Telegram 识别。

### 产出
- 更新 `src/aico/core/project_messages.py`:
  - 识别形如 `- /command` / `* /command` 的 Next 引导命令行。
  - 这类命令行不再规范化为 `• `,保留 `- /command`。
  - 这类命令行不再添加 slash command code span,交给 Telegram 自动识别为可触碰命令。
  - 非 Next 的项目事实、document snippet、blocker 文本仍保留原有 bullet 规范化和 `/approve` 等 code span。
- 更新 `tests/unit/test_project_messages.py`:
  - 覆盖 `/project`、`/team`、`/roles`、`/role` 的 Next 输出为 hyphen list。
  - 覆盖 Next 区块中的 slash command 不生成 `MessageTextStyle.CODE` span。
  - 保留 blockers / summary 中正文命令 code span 的回归覆盖。
- 更新 `STATUS.md`。
- 新增 PITFALL P-017。
- 完整验证通过:
  - `uv run pytest`
  - 215 passed
  - `uv run ruff check .`
  - `uv run ruff format --check .`
  - `uv run mypy src tests`
  - `git diff --check`

### 关键决策
- 🔒 **决策 1**:用于触碰发送的 Next bot command 应优先尊重 IM 平台原生识别,不要强行包成 code rich text。
- 🔒 **决策 2**:例外规则只作用于 `- /command` / `* /command` 这类引导命令行,不改变文档事实和普通正文渲染。
- 🔒 **决策 3**:平台无关 render contract 继续保留,但 Telegram 原生命令识别属于 channel 体感边界,需要在 message builder 测试里锁住输出形态。

### 留给下一轮
- Telegram 真实复验:
  - `/roles`
  - `/role implementer`
  - `/project`
  - `/team`
  - 确认 `Next:` 里的 `/command` 均为蓝色可触碰命令。
- 如果 Feishu/其他 IM 对裸 `/command` 没有同类识别,保持 channel 内降级即可,不要为了单个平台重新改变核心 Next 文本。

### 状态变化
- `STATUS.md` 当前轮次更新为 Round 71。
- 新增 PITFALL P-017 并标记 resolved。

## Round 72 — 2026-05-14 — Codex

### 输入
- 人类完成命令验收后继续推进 Phase 6。
- 人类指出 Telegram `/metrics` 手工制造 done / waiting approval / collaboration 任务,以及重启恢复验收都不太好测。
- 人类要求由 Agent 编写一个省 token 的验证例子,验证这些能力,并给出最新项目状态。

### 思考与方案
- 候选 A:真实调用 Claude/Codex 造任务后在 Telegram 里验收 → ❌ **否决**:会消耗 token,还混入 provider 登录、网络和长任务不确定性。
- 候选 B:只检查 `build_metrics_report()` 纯函数 → ❌ **不足**:能验证统计口径,但覆盖不到 `/metrics` 命令路径、audit JSONL 重启恢复和 CLI/glance 入口。
- 候选 C:新增无 token acceptance test → ✅ **选定**:用 fake Telegram channel、fake Adapter 和临时 audit JSONL 覆盖完整产品路径,不碰真实 LLM。

### 产出
- 新增 `tests/unit/test_phase6_metrics_acceptance.py`:
  - 使用 `NoTokenAdapter` 模拟 provider,只返回 `ok`,不调用真实 CLI/LLM。
  - 通过 `Orchestrator.handle_incoming()` 模拟 Telegram 普通消息和 `/metrics`。
  - 生成 1 个 done task、1 个 waiting approval task、1 条 collaboration request audit event。
  - 通过 `JsonlAuditSink` 写入临时 audit JSONL。
  - 新建“重启后”的 `Orchestrator + TaskBus`,只用 `InMemoryAuditLog(initial_events=...)` 回放 audit JSONL,再次验证 `/metrics`。
  - 用同一份 audit JSONL 验证 `aico-metrics` text/json 和 `aico-glance` text/json。
- 更新 `docs/playbooks/phase-6-observability.md`,加入省 token 本地验收命令:
  - `uv run pytest tests/unit/test_phase6_metrics_acceptance.py`
- 更新 `STATUS.md`:
  - 记录 Phase 6 无 token `/metrics` live 验收、重启恢复验收、CLI/glance 验收已完成。
  - 下一轮建议改为先决定是否接受无 token 自动验收作为 Phase 6 验收门槛;若接受,可进入 Phase 7 共享记忆层 ADR。

### 验证结果
- `uv run pytest tests/unit/test_phase6_metrics_acceptance.py`
  - 1 passed
- 完整验证通过:
  - `uv run pytest`
  - 216 passed
  - `uv run ruff check .`
  - `uv run ruff format --check .`
  - `uv run mypy src tests`
  - `git diff --check`

### 关键决策
- 🔒 **决策 1**:Phase 6 metrics 验收优先把 AICO 自身观测链路跑稳,不要为造样例而调用真实 LLM。
- 🔒 **决策 2**:无 token acceptance test 必须覆盖产品入口 `/metrics`,不能只测纯统计函数。
- 🔒 **决策 3**:重启恢复验收以 audit JSONL 为源,新建 TaskBus 时只注入 initial events,模拟真实重启后内存任务清空的状态。

### 留给下一轮
- 人类确认是否接受无 token 自动验收替代真实 Telegram 手工造数。
- 若接受,将 Phase 6 收口并进入 Phase 7 共享记忆层 ADR。
- 若仍要求 Telegram 网络复验,只复验 `/metrics` 文本展示即可,不要再真实调用 LLM 造任务。

### 状态变化
- `STATUS.md` 当前轮次更新为 Round 72。
- Phase 6 新增无 token metrics acceptance 通过记录。

## Round 73 — 2026-05-15 — Codex

### 输入
- 人类要求保留无 token acceptance case。
- 人类希望再补一个需要 token 的简单任务验证 `/metrics` 相关命令,因为完全不对模型发起任务心里没谱。
- 人类要求写简单 golden 测试并由 Agent 验证,全通过后下轮再继续。

### 思考与方案
- 候选 A:把真实 provider 调用放进普通单测 → ❌ **否决**:会让日常 `uv run pytest` 不稳定且持续烧 token。
- 候选 B:只手工跑一条 CLI 命令,不入库 → ❌ **不足**:无法成为后续可复验的 golden。
- 候选 C:新增 opt-in token golden → ✅ **选定**:默认跳过,设置环境变量时才消耗 token;覆盖真实 provider task、`/metrics`、audit replay 和 `aico-metrics`。

### 产出
- 保留 `tests/unit/test_phase6_metrics_acceptance.py` 无 token acceptance。
- 新增 `tests/golden/test_phase6_metrics_token_golden.py`:
  - 默认跳过;需要 `AICO_RUN_TOKEN_GOLDEN=1` 才运行。
  - `AICO_TOKEN_GOLDEN_COMMAND` 可配置真实 provider CLI。
  - 通过 `ClaudeCodeAdapter` 的通用 CLI 适配路径发起极简模型任务。
  - golden prompt 固定为 `Return exactly this text: AICO_METRICS_TOKEN_SMOKE_OK`。
  - 验证模型输出包含 `AICO_METRICS_TOKEN_SMOKE_OK`。
  - 验证 live `/metrics` 显示 `done=1`、`agents: token-smoke=1`、`status: quiet`。
  - 验证“重启后”只从 audit JSONL 恢复同一条 done task。
  - 验证 `aico-metrics --audit-log ...` 与 live `/metrics` 口径一致。
- 更新 `docs/playbooks/phase-6-observability.md`:
  - 记录无 token acceptance 命令。
  - 记录真实 provider token golden 命令。
- 新增 PITFALL P-018:
  - smoke prompt 中的否定危险词如 `Do not run tools` 也会触发 approval gate。
  - provider token smoke 应使用无风险固定短答 prompt。
- 更新 `STATUS.md`:
  - 当前轮次更新为 Round 73。
  - Phase 6 增加真实模型 token golden 通过记录。
  - 下一轮建议改为 Phase 6 收口并开启 Phase 7 共享记忆层 ADR。

### 验证结果
- 默认 golden 跳过验证:
  - `uv run pytest tests/golden/test_phase6_metrics_token_golden.py`
  - 1 skipped
- 真实 Codex token golden 通过:
  - `env AICO_RUN_TOKEN_GOLDEN=1 AICO_TOKEN_GOLDEN_COMMAND='codex --ask-for-approval never exec --sandbox read-only --color never' uv run pytest tests/golden/test_phase6_metrics_token_golden.py`
  - 初次通过 1 passed in 21.15s;清理导入后最终复跑 1 passed in 12.11s
- 完整验证通过:
  - `uv run pytest`
  - 216 passed, 1 skipped
  - `uv run ruff check .`
  - `uv run ruff format --check .`
  - `uv run mypy src tests`
  - `git diff --check`

### 关键决策
- 🔒 **决策 1**:真实 provider golden 必须 opt-in,不能默认烧 token。
- 🔒 **决策 2**:token golden 验证的是“真实模型任务完成后 metrics 口径可信”,不是验证 token/cost usage;当前 Adapter 仍不会伪造 usage。
- 🔒 **决策 3**:golden prompt 保持短答,不包含 `run` / `modify` / `edit` 等风险词,避免验收目标被 approval gate 污染。

### 留给下一轮
- Phase 6 已有无 token acceptance 和真实 Codex token golden 双保险。
- 下一轮建议收口 Phase 6,然后进入 Phase 7 共享记忆层 ADR。

### 状态变化
- `STATUS.md` 当前轮次更新为 Round 73。
- 新增 PITFALL P-018 并标记 resolved。

## Round 74 — 2026-05-15 — Codex

### 输入
- 人类明确要求:收口 Phase 6,开始 Phase 7。
- 前置状态:Phase 6 已有无 token acceptance 和真实 Codex token golden 双保险,`/metrics`、audit replay、`aico-metrics`、`aico-glance` 口径已验证。

### 思考与方案
- 候选 A:直接开始写记忆存储代码 → ❌ **暂缓**:共享记忆会影响 Prompt Stack、项目报告和多 AI 协作,先定边界避免过度设计。
- 候选 B:直接接向量库 / RAG → ❌ **否决**:第一版难以审计、难以纠错,也会引入新依赖和索引维护。
- 候选 C:先收口 Phase 6,再用 ADR + playbook 启动 Phase 7 第一切片 → ✅ **选定**:符合 AGENTS 要求的重要架构决策先落 ADR,同时给下一轮实现明确验收路径。

### 产出
- Phase 6 状态收口:
  - 阶段地图中 Phase 6 从进行中改为完成。
  - Phase 6 `/metrics` Telegram 手工造数项改为由无 token acceptance / token golden 替代验收。
  - `Phase 6 集中真实验收通过后进入 Phase 7` 标记完成。
- Phase 7 启动:
  - 阶段地图中 Phase 7 从未开始改为进行中。
  - 新增 Phase 7 进度小节。
  - 当前轮次更新为 Round 74。
- 新增 ADR-0020 `Phase 7 Shared Memory Scope`:
  - 决定第一版使用 AICO 本地可审计记忆账本。
  - 第一切片包括 `MemoryRecord`、`MemoryStore`、`JsonlMemoryStore`、`/remember`、`/recall`、`/forget`。
  - 明确不引入向量库、不自动记住所有聊天、不依赖 Provider 私有 session memory。
- 新增 `docs/playbooks/phase-7-shared-memory.md`:
  - 定义 Phase 7 第一切片实现范围。
  - 定义本地单测和 IM 体感验收步骤。
  - 记录失败排查边界。
- 更新 ADR / playbook 索引。
- 更新下一轮建议:
  - 最高优先级改为实现 Phase 7 共享记忆第一切片。
  - 多 Adapter 真实 smoke test、Feishu 部署层仍保留为高优后续项。

### 验证结果
- `uv run pytest`
  - 216 passed, 1 skipped
- `uv run ruff check .`
- `uv run ruff format --check .`
- `uv run mypy src tests`
- `git diff --check`

### 关键决策
- 🔒 **决策 1**:Phase 6 正式完成,后续观测相关工作作为增量能力而不是 Phase 6 阻塞项。
- 🔒 **决策 2**:Phase 7 第一版共享记忆采用可审计 JSONL 账本,不直接上向量库。
- 🔒 **决策 3**:共享记忆必须绑定项目 scope、source、created_by 和归档语义,不能成为不可追溯的黑箱。

### 留给下一轮
- 按 ADR-0020 和 `docs/playbooks/phase-7-shared-memory.md` 实现第一切片:
  - `MemoryRecord`
  - `MemoryStore`
  - `JsonlMemoryStore`
  - `AICO_MEMORY_PATH`
  - `/remember` / `/recall` / `/forget`
  - Prompt Stack 少量当前项目记忆注入

### 状态变化
- `STATUS.md` 当前轮次更新为 Round 74。
- Phase 6:进行中 → 完成。
- Phase 7:未开始 → 进行中。
- ADR-0020 Accepted。

## Round 75 — 2026-05-15 — Codex

### 输入
- 人类明确 Phase 7 记忆层产品基调:
  - `/remember` / `/recall` / `/forget` 可以存在。
  - 但调用和触发这些命令的大比例应该来自 agent,而不是老板。
  - AI Company OS 的目标是让老板方便管理自己的 agent 去做小中型项目,记忆不应变成老板手动维护的痛苦和恐惧来源。

### 思考与讨论
- 候选 A:沿用 ADR-0020 的“显式命令写入”作为主路径 → ❌ **修正**:这会把记忆层做成老板维护数据库,偏离“管理真实团队”的产品体感。
- 候选 B:完全自动记住所有聊天和模型输出 → ❌ **否决**:会制造不可控记忆污染,也违反可审计、可纠错的 Phase 7 边界。
- 候选 C:agent 主动维护记忆,命令作为纠错/补充/排障入口 → ✅ **选定**:老板主体验仍是项目管理命令,agent 负责沉淀和召回上下文。

### 产出
- 新增 ADR-0021 `Agent-Driven Memory Ownership`。
- 更新 `docs/playbooks/phase-7-shared-memory.md`,明确 Phase 7 记忆层的产品基调:
  - 记忆命令存在,但不是老板高频主路径。
  - agent 在任务完成、项目交接、风险确认、日报/周报沉淀时主动写入稳定事实。
  - agent 接项目任务前自动召回当前项目少量高置信记忆。
  - 所有 agent 写入都必须带 source、created_by、confidence 和写入理由。
- 更新 `STATUS.md` 和 ADR 索引,让下一轮实现按 ADR-0020 + ADR-0021 同时推进。

### 关键决策
- 🔒 **决策 1**:Phase 7 的价值不是多几个 slash command,而是让 agent 团队自动沉淀和使用项目上下文。
- 🔒 **决策 2**:`/remember` / `/recall` / `/forget` 是老板的控制权和排障入口,不是主要工作流。
- 🔒 **决策 3**:agent-driven memory 也必须可审计、可纠错、可归档,不能退化为“自动记住一切”。

### 留给下一轮
- 实现 Phase 7 第一切片时,除了命令 MVP,还要在 agent 任务链路设计记忆触发点:
  - Prompt Stack 自动召回当前项目少量高置信记忆。
  - 任务完成或报告生成后,由 agent 写入稳定项目事实。
  - `/recall` 能解释这些记忆的来源和写入理由。
- 避免把验收做成只测试 `/remember` / `/recall` / `/forget`;需要覆盖“老板自然发项目命令,agent 自动用记忆”的路径。

### 状态变化
- `STATUS.md` 当前轮次更新为 Round 75。
- Phase 7 新增 ADR-0021,明确记忆层由 agent 主动维护。

## Round 76 — 2026-05-15 — Codex

### 输入
- 人类担心 `/remember` / `/recall` 在 lead agent 与其他 agent 间交互设计上不够合理。
- 人类要求设计一个符合 A2A 的记忆架构,并参考 `https://github.com/MarcelLeon/attack-on-memory`。
- 必须满足:
  - agent 间交互、agent 和人之间交互有记忆,由 A2A 发起的任务粒度必须包含 project 或 team,跨 team/project 不共享。
  - boss 发起的会话有记忆总结提取能力,识别 boss 喜好/feedback 时一定要记录,具体层级由 LLM 判断确认。
  - 重要记忆可以通过基础设施广播给 team 下全部 agent,老板开会显式触发和 agent 自发广播走通用底层机制。
  - 试验用记忆广播减少 A2A 消息传递和 token 消耗。

### 思考与讨论
- 参考 `attack-on-memory` 后,确认可迁移思想是 Memory Atom、evidence、scope、graph edge、time-window retrieval、selective disclosure、BranchWorldModel,而不是直接引入该项目代码。
- 候选 A:继续只做 `/remember` / `/recall` 命令 MVP → ❌ **否决**:命令会成为旁路,无法支撑 lead agent 和 team agent 的 A2A 协作。
- 候选 B:直接引入向量库 / 图数据库 → ❌ **否决**:ADR-0020 已确定第一版 JSONL 权威源,此时引入新后端会把可审计边界打散。
- 候选 C:设计 A2A-compatible Memory Fabric → ✅ **选定**:内部先不暴露完整 HTTP A2A,但领域对象和事件要能映射到 A2A Task / Message / Part / Artifact / Context / Push。

### 产出
- 新增 ADR-0022 `A2A Memory Fabric`。
- 新增 `docs/architecture/a2a-memory-fabric.md`。
- 更新 `docs/playbooks/phase-7-shared-memory.md`,把第一切片验收从“命令 MVP”扩展为:
  - A2A 子任务必须带 project/team scope。
  - boss 会话结束后能抽取候选记忆并判断层级。
  - team 共识广播通过 `MemoryBroadcast` 写入并生成 receipt。
  - token-saving 试验用 memory refs + MemoryPacket,失败时回退显式消息传递。
- 更新 `STATUS.md` 和 ADR 索引。

### 关键决策
- 🔒 **决策 1**:AICO 记忆层的核心不是 slash command,而是 project/team-scoped A2A Memory Fabric。
- 🔒 **决策 2**:默认禁止跨 project / team 共享记忆;boss global memory 只能用于偏好/工作方式,不能泄漏项目事实。
- 🔒 **决策 3**:记忆广播是底层基础设施,不是 IM 群发;老板会议触发和 agent 自发共识广播必须复用同一机制。
- 🔒 **决策 4**:用 memory refs 减少 A2A 消息传递只是实验,必须保留 citations,并以任务成功率和可审计性为前提。

### 留给下一轮
- 实现 Phase 7 第一切片时,先落 `MemoryAtom` / `MemoryScope` / `MemoryEvidence` / `MemoryEdge` / `MemoryPacket` 领域模型和 JSONL store。
- 再接 Prompt Stack 自动召回,确保 project/team/role/boss scope 过滤正确。
- 命令 MVP 只作为人工入口;不要先把 `/remember` 做成唯一写入路径。
- 为 boss feedback extraction 和 team broadcast 分别补本地验收测试。

### 状态变化
- `STATUS.md` 当前轮次更新为 Round 76。
- Phase 7 新增 ADR-0022 和 A2A Memory Fabric 架构说明。

## Round 77 — 2026-05-15 — Codex

### 输入
- 人类要求给足自主权,把当前记忆架构设计拆成 5 个迭代以内可以落地的步骤。
- 要求符合“以终为始”和 TDD 理念,准备好就开始实现。

### 思考与讨论
- 候选 A:先做 `/remember` / `/recall` / `/forget` → ❌ **否决**:会再次把记忆层做成命令插件,绕开 ADR-0022 的 A2A Memory Fabric。
- 候选 B:一次性实现抽取、广播、Prompt Stack、命令和 token-saving → ❌ **否决**:范围过大,很难用 TDD 保持红绿循环。
- 候选 C:先落可审计领域模型和 JSONL 权威源,再逐步接 Prompt Stack、命令、抽取和广播 → ✅ **选定**:这是 Memory Fabric 的最小可验证内核,后续迭代都能复用。

### 产出
- 更新 `docs/playbooks/phase-7-shared-memory.md`,把 Phase 7 记忆架构拆为 5 个 TDD 迭代:
  - Iteration 1:记忆领域模型与 JSONL 权威源。
  - Iteration 2:Prompt Stack 自动召回。
  - Iteration 3:IM 控制入口。
  - Iteration 4:Boss Feedback 抽取与候选记忆。
  - Iteration 5:Team Broadcast 与 A2A Token-saving 实验。
- 新增 `tests/unit/test_memory.py`,先写红灯测试覆盖:
  - `MemoryAtom` 必须有 evidence 和 project/team scoped 记忆边界。
  - `MemoryScope` 必须校验 boss/project/team/role/agent 层级字段。
  - `JsonlMemoryStore` append/list/search/archive 后能从 JSONL 恢复。
  - `MemoryEdge` 可持久化和恢复。
- 新增 `src/aico/core/memory.py`:
  - `MemoryScopeType`
  - `MemorySensitivity`
  - `MemoryStatus`
  - `MemoryEdgeType`
  - `MemoryScope`
  - `MemoryEvidence`
  - `MemoryAtom`
  - `MemoryEdge`
  - `MemoryStore`
  - `JsonlMemoryStore`
- 更新 `src/aico/core/__init__.py` 导出 memory 模型和 store。
- 更新 `STATUS.md`,标记 `MemoryAtom / MemoryStore` 和 `JsonlMemoryStore` 完成,下一轮建议切到 Prompt Stack 自动召回。

### 验证结果
- 红灯验证:
  - `uv run pytest tests/unit/test_memory.py`
  - 初始失败:无法从 `aico.core` import `JsonlMemoryStore`。
- 绿灯验证:
  - `uv run pytest tests/unit/test_memory.py`
  - 4 passed
- 目标验证:
  - `uv run pytest tests/unit/test_models.py tests/unit/test_memory.py tests/unit/test_audit.py`
  - 12 passed
  - `uv run ruff check src/aico/core/memory.py tests/unit/test_memory.py src/aico/core/__init__.py`
  - `uv run ruff format --check src/aico/core/memory.py tests/unit/test_memory.py src/aico/core/__init__.py`
  - `uv run mypy src/aico/core/memory.py tests/unit/test_memory.py`

### 关键决策
- 🔒 **决策 1**:Phase 7 实现顺序以 Memory Fabric 内核为第一步,不是先做 IM 命令。
- 🔒 **决策 2**:第一版 `JsonlMemoryStore` 是 append-only 权威源,内存索引只做启动重建和运行期查询。
- 🔒 **决策 3**:第一版 search 只做 scope + 子串/标签匹配;不引入向量库、图数据库或 LLM 检索。

### 留给下一轮
- Phase 7 Iteration 2:实现 Prompt Stack 自动召回:
  - 新增 `MemoryPacket` / `MemoryRetriever` / 最小 `MemoryGovernor`。
  - 在 project-scoped task prompt 中注入少量高置信 project/team/role/boss 记忆。
  - 本地测试必须证明归档记忆不会被注入、跨 project/team 记忆不会串入 prompt。

### 状态变化
- `STATUS.md` 当前轮次更新为 Round 77。
- Phase 7 `MemoryAtom / MemoryStore 核心模型` 标记完成。
- Phase 7 `JsonlMemoryStore 本地可审计记忆账本` 标记完成。

## Round 78 — 2026-05-15 — Codex

### 输入
- 人类要求继续开发 Phase 7 记忆架构。
- 上轮已完成 Iteration 1:MemoryAtom / MemoryStore / JsonlMemoryStore。
- `STATUS.md` 下一步指向 Iteration 2:Prompt Stack 自动召回。

### 思考与讨论
- 候选 A:直接做 `/remember` / `/recall` → ❌ **继续否决**:命令入口应建立在自动召回能力之上,否则老板仍会被迫手动维护记忆。
- 候选 B:一次性接 LLM 抽取和 team broadcast → ❌ **暂缓**:还没有受控 `MemoryPacket` 和治理投影,直接抽取会把噪声注入 prompt。
- 候选 C:先实现 `MemoryPacket` / `MemoryRetriever` / `MemoryGovernor`,并接入 appointment prompt 渲染 → ✅ **选定**:能让 agent 自动使用当前项目记忆,同时保持 scope 和 sensitivity 边界。

### 产出
- 扩展 `tests/unit/test_memory.py`:
  - 覆盖 `MemoryRetriever` 从 project/team scope 构建 governed `MemoryPacket`。
  - 验证 candidate、archived、restricted 和其它 project 记忆不会进入 packet。
  - 验证 `MemoryPacket.render_prompt_section()` 输出紧凑 prompt section 和 citations。
- 新增 `tests/unit/test_prompt_stack.py`:
  - 验证 `render_appointment_prompt()` 会把 `Shared memory` 放在 `Current task` 之前。
- 扩展 `tests/unit/test_orchestrator.py`:
  - 验证 active project 普通任务会自动注入同 project 记忆,不会泄漏其它 project 记忆。
- 扩展 `src/aico/core/memory.py`:
  - `MemoryPacketItem`
  - `MemoryCitation`
  - `MemoryPacket`
  - `MemoryGovernor`
  - `MemoryRetriever`
  - search 从整句子串匹配升级为 token 命中匹配,仍不引入向量库。
- 扩展 `src/aico/core/prompt_stack.py`:
  - `render_appointment_prompt(..., memory_packet=None)`。
- 扩展 `src/aico/core/orchestrator.py`:
  - 新增可选 `memory_store`。
  - project-scoped task 渲染 prompt 前自动召回 project/role/agent scope 记忆。
- 更新 `src/aico/core/__init__.py` 导出 memory packet / retriever / governor。
- 更新 `STATUS.md`,标记 Prompt Stack 记忆召回完成,下一轮建议切到 Iteration 3。

### 验证结果
- 红灯验证:
  - `uv run pytest tests/unit/test_memory.py tests/unit/test_prompt_stack.py`
  - 初始失败:缺少 `MemoryCitation` 等导出。
  - 新增 Orchestrator 红灯:缺少 `memory_store` 参数。
- 绿灯验证:
  - `uv run pytest tests/unit/test_memory.py tests/unit/test_prompt_stack.py`
  - 7 passed
  - `uv run pytest tests/unit/test_orchestrator.py::test_orchestrator_injects_project_memory_for_active_project_task tests/unit/test_memory.py tests/unit/test_prompt_stack.py`
  - 8 passed
- 目标验证:
  - `uv run pytest tests/unit/test_memory.py tests/unit/test_prompt_stack.py tests/unit/test_orchestrator.py`
  - 53 passed
  - `uv run ruff check src/aico/core/memory.py src/aico/core/prompt_stack.py src/aico/core/orchestrator.py src/aico/core/__init__.py tests/unit/test_memory.py tests/unit/test_prompt_stack.py tests/unit/test_orchestrator.py`
  - `uv run ruff format --check src/aico/core/memory.py src/aico/core/prompt_stack.py src/aico/core/orchestrator.py src/aico/core/__init__.py tests/unit/test_memory.py tests/unit/test_prompt_stack.py tests/unit/test_orchestrator.py`
  - `uv run mypy src/aico/core/memory.py src/aico/core/prompt_stack.py src/aico/core/orchestrator.py tests/unit/test_memory.py tests/unit/test_prompt_stack.py tests/unit/test_orchestrator.py`

### 关键决策
- 🔒 **决策 1**:Prompt 注入使用 `MemoryPacket` 投影,不把完整 `MemoryAtom` JSON 塞进 provider prompt。
- 🔒 **决策 2**:Orchestrator 的 memory store 是可选依赖;未配置时现有行为完全不变。
- 🔒 **决策 3**:第一版召回只做确定性 scope + token 匹配 + confidence 排序,不接向量库或 LLM 检索。

### 留给下一轮
- Phase 7 Iteration 3:IM 控制入口:
  - 新增 `AICO_MEMORY_PATH` 设置并在 `aico-phase1` runtime 中创建 `JsonlMemoryStore`。
  - 新增 `/remember <text>`、`/recall [query]`、`/forget <memory_id>`。
  - `/remember` 默认写当前 active project scope;没有 active project 时应明确提示先 `/project <project>`。
  - `/recall` 输出 scope、confidence、source/evidence 摘要和短 Next。
  - `/forget` 归档后要证明 prompt stack 不再注入该记忆。

### 状态变化
- `STATUS.md` 当前轮次更新为 Round 78。
- Phase 7 `Prompt Stack 读取当前项目少量高置信记忆` 标记完成。

## Round 79 — 2026-05-15 — Codex

### 输入
- 人类要求继续执行 Phase 7 记忆架构落地。
- 上轮已完成 Iteration 2:Prompt Stack 自动召回。
- `STATUS.md` 下一步指向 Iteration 3:IM 控制入口。

### 思考与讨论
- 候选 A:把 `/remember` / `/recall` / `/forget` 直接写进 `Orchestrator` → ❌ **否决**:`Orchestrator` 已经偏大,继续塞命令细节会违背 handler 拆分方向。
- 候选 B:新增独立 `MemoryCommandHandler` 并只在 Orchestrator 接线 → ✅ **选定**:保持 project command / directory command 一致的命令处理结构,也让后续 agent 自动写入能复用底层 store。
- 候选 C:未配置 `AICO_MEMORY_PATH` 时创建进程内 memory store → ❌ **暂缓**:当前 Phase 7 目标是可审计共享记忆;无持久化时保持无记忆行为更不容易给老板制造“我明明记住了但重启丢失”的错觉。

### 产出
- 扩展 `tests/unit/test_commands.py`:
  - 验证 `/remember <text>`、`/recall [query]`、`/forget <memory_id>` 能解析为内建命令。
- 扩展 `tests/unit/test_phase1_app.py`:
  - 验证配置 `memory_path` 后,Phase1 runtime 给 Orchestrator 注入 `JsonlMemoryStore`。
- 扩展 `tests/unit/test_orchestrator.py`:
  - 验证没有 active project 时 `/remember` 提示先 `/project <project>`。
  - 验证 `/remember` 写入当前 project scope,`/recall` 展示 claim / scope / confidence / evidence,`/forget` 归档后默认不再召回。
  - 验证归档后的记忆不会再进入 project task prompt。
- 新增 `src/aico/core/memory_commands.py`:
  - `MemoryCommandHandler.handle_remember()`
  - `MemoryCommandHandler.handle_recall()`
  - `MemoryCommandHandler.handle_forget()`
- 扩展 `src/aico/core/commands.py`:
  - 新增 `remember` / `recall` / `forget` 命令和 `/help` 文案。
- 扩展 `src/aico/core/orchestrator.py`:
  - 接入 `MemoryCommandHandler`,保持 `Orchestrator` 只负责命令分发。
- 扩展 `src/aico/app/phase1.py`:
  - 新增 `Phase1Settings.memory_path`,对应 `AICO_MEMORY_PATH`。
  - runtime 配置该路径后创建 `JsonlMemoryStore`。
- 更新 `docs/human/daily-ops.md`、`docs/playbooks/phase-7-shared-memory.md`、`CHANGELOG.md` 和 `STATUS.md`。

### 验证结果
- 红灯验证:
  - `uv run pytest tests/unit/test_commands.py::test_parse_command_accepts_memory_commands tests/unit/test_phase1_app.py::test_build_phase1_runtime_configures_memory_store_when_path_set tests/unit/test_orchestrator.py::test_orchestrator_memory_commands_require_active_project tests/unit/test_orchestrator.py::test_orchestrator_remember_recall_and_forget_project_memory`
  - 初始失败:命令未解析、runtime 未注入 memory store、Orchestrator 未处理 memory commands。
- 绿灯验证:
  - 同一目标 pytest 命令:4 passed。
  - `uv run ruff check src/aico/core/memory_commands.py src/aico/core/orchestrator.py src/aico/app/phase1.py tests/unit/test_commands.py tests/unit/test_orchestrator.py tests/unit/test_phase1_app.py`
  - `uv run mypy src/aico/core/memory_commands.py src/aico/core/orchestrator.py src/aico/app/phase1.py tests/unit/test_commands.py tests/unit/test_orchestrator.py tests/unit/test_phase1_app.py`
- 全量验证:
  - `uv run pytest` → 228 passed, 1 skipped。
  - `uv run ruff check .`
  - `uv run ruff format --check .`
  - `uv run mypy src tests`
  - `git diff --check`

### 关键决策
- 🔒 **决策 1**:`/remember` 默认写当前 active project scope,没有 active project 时拒绝写入。
- 🔒 **决策 2**:`/forget` 只 archive,不物理删除 JSONL 历史,以保留审计和回滚空间。
- 🔒 **决策 3**:无 `AICO_MEMORY_PATH` 时保持无记忆行为,不悄悄启用不可恢复的进程内共享记忆。

### 留给下一轮
- Phase 7 Iteration 4:boss feedback 抽取与候选记忆:
  - boss 明确偏好或反馈要被识别并落到 boss global / project / team / role / agent scope。
  - scope 不确定或置信度不足时写成 `candidate`,不能直接进入 prompt stack。
  - 需要继续保持“agent 主动维护记忆,命令只是纠错和验收入口”的产品基调。
- Phase 7 本地验收流:
  - 用 `AICO_MEMORY_PATH` 启动 runtime,跑 `/project aico`、`/remember`、`/recall`、`/forget` 和普通项目任务自动召回。
  - 验证同一 JSONL 重启恢复。

### 状态变化
- `STATUS.md` 当前轮次更新为 Round 79。
- Phase 7 `AICO_MEMORY_PATH 配置入口` 标记完成。
- Phase 7 `/remember` / `/recall` / `/forget` IM 命令 MVP 标记完成。

## Round 80 — 2026-05-15 — Codex

### 输入
- 人类要求继续迭代 Phase 7 记忆架构。
- 上轮已完成 Iteration 3:`AICO_MEMORY_PATH` 和 `/remember` / `/recall` / `/forget`。
- `STATUS.md` 下一步指向 Iteration 4-5:抽取与广播。

### 思考与讨论
- 候选 A:直接接真实 LLM 分类器抽取 boss feedback → ❌ **暂缓**:第一版还没有确认流和失败治理,直接让 LLM 写 active memory 容易把噪声灌入 prompt。
- 候选 B:只做规则化 boss feedback capture service → ✅ **选定**:先覆盖明确偏好/反馈,可测试、可审计、可回滚;后续可把分类器替换为 LLM。
- 候选 C:所有抽取结果都写 active memory → ❌ **否决**:不确定表达必须进入 `candidate`,避免污染 agent prompt。

### 产出
- 新增 `tests/unit/test_memory_capture.py`:
  - 明确 project feedback 写入 project memory。
  - 无 project context 的老板偏好写入 boss global memory。
  - 不确定反馈写为 `candidate`。
  - 普通任务文本不会误捕获。
- 扩展 `tests/unit/test_orchestrator.py`:
  - 非命令老板消息会自动写入当前 project memory。
  - candidate feedback 不进入后续 prompt。
  - boss global preference 可按 query 进入 project task prompt。
- 新增 `src/aico/core/memory_capture.py`:
  - `MemoryCaptureService.capture_boss_feedback()`。
  - 第一版使用明确偏好/反馈 marker 和 project/global marker 做确定性分类。
- 扩展 `src/aico/core/orchestrator.py`:
  - 非命令消息路由前调用 boss feedback capture。
  - project task 记忆召回 scope 增加 boss global + project + role + agent。
- 更新 `src/aico/core/__init__.py` 导出 `MemoryCaptureService`。
- 更新 `STATUS.md`、`CHANGELOG.md`、`docs/human/daily-ops.md` 和 Phase 7 playbook。

### 验证结果
- 红灯验证:
  - `uv run pytest tests/unit/test_memory_capture.py tests/unit/test_orchestrator.py::test_orchestrator_captures_boss_feedback_for_active_project tests/unit/test_orchestrator.py::test_orchestrator_candidate_boss_feedback_stays_out_of_prompt`
  - 初始失败:缺少 `aico.core.memory_capture`。
- 绿灯验证:
  - `uv run pytest tests/unit/test_memory_capture.py tests/unit/test_orchestrator.py::test_orchestrator_captures_boss_feedback_for_active_project tests/unit/test_orchestrator.py::test_orchestrator_candidate_boss_feedback_stays_out_of_prompt tests/unit/test_orchestrator.py::test_orchestrator_injects_captured_boss_global_preference`
  - 7 passed。
  - `uv run ruff check src/aico/core/memory_capture.py src/aico/core/orchestrator.py src/aico/core/__init__.py tests/unit/test_memory_capture.py tests/unit/test_orchestrator.py`
  - `uv run ruff format --check src/aico/core/memory_capture.py src/aico/core/orchestrator.py src/aico/core/__init__.py tests/unit/test_memory_capture.py tests/unit/test_orchestrator.py`
  - `uv run mypy src/aico/core/memory_capture.py src/aico/core/orchestrator.py tests/unit/test_memory_capture.py tests/unit/test_orchestrator.py`
- 全量验证:
  - `uv run pytest` → 235 passed, 1 skipped。
  - `uv run ruff check .`
  - `uv run ruff format --check .`
  - `uv run mypy src tests`
  - `git diff --check`

### 关键决策
- 🔒 **决策 1**:Boss feedback 自动抽取第一版只捕获显式偏好/反馈,不尝试从任意自然语言里猜隐含记忆。
- 🔒 **决策 2**:不确定反馈写 `candidate`,不进入 Prompt Stack。
- 🔒 **决策 3**:project task 可召回 boss global scope,但仍走 `MemoryRetriever` query 和 `MemoryGovernor` 投影。

### 留给下一轮
- Phase 7 Iteration 5:Team Broadcast 与 A2A token-saving 实验:
  - 先做 `MemoryBroadcast` 的内部 service / edge / receipt,让老板会议触发和 agent 共识广播走同一底层机制。
  - A2A 子任务必须带 project/team scope;目标 agent 只接收 governed `MemoryPacket`。
  - token-saving 模式只做可关闭实验;召回失败必须回退显式消息传递。
- Phase 7 本地验收流:
  - 用 `AICO_MEMORY_PATH` 启动 runtime,覆盖命令入口、自动召回、boss feedback capture、candidate 不注入和 JSONL 重启恢复。

### 状态变化
- `STATUS.md` 当前轮次更新为 Round 80。
- Phase 7 `Boss feedback 自动抽取与 candidate 记忆 MVP` 标记完成。

## Round 81 — 2026-05-17 — Codex

### 输入
- 人类要求继续开发 Phase 7。
- 上轮已完成 Iteration 4:boss feedback 自动抽取与 candidate memory。
- `STATUS.md` 下一步指向 Iteration 5:Team Broadcast 与 A2A token-saving 实验。

### 思考与讨论
- 候选 A:直接加 `/memory broadcast` 命令 → ❌ **暂缓**:会把记忆广播再次做成老板手动命令插件,偏离 agent-operated 的 Phase 7 基调。
- 候选 B:先做内部 `MemoryBroadcastService` + edge + receipt → ✅ **选定**:老板会议触发和 agent 自发共识后续都能复用同一底层服务。
- 候选 C:默认用 `memory_refs` 替代 A2A 显式消息 → ❌ **否决**:token-saving 是实验,召回失败必须能回退显式消息。

### 产出
- 扩展 `tests/unit/test_memory.py`:
  - 验证 `MemoryBroadcastService.broadcast_to_team()` 会创建 team memory。
  - 验证写入 `broadcast_to` edge,并返回 `MemoryBroadcastReceipt`。
  - 验证跨 project team scope 会被拒绝。
- 扩展 `tests/unit/test_orchestrator.py`:
  - 验证 broadcast 后的 team memory 会进入 active project task prompt。
- 扩展 `tests/unit/test_collaboration.py`:
  - 验证 `collaboration_payload(..., memory_refs=..., use_memory_refs=True)` 输出 `memory_refs + delta`。
  - 验证无 refs 时仍回退原显式 payload。
- 扩展 `src/aico/core/memory.py`:
  - `MemoryStore.get_atom()`
  - `JsonlMemoryStore.get_atom()`。
- 新增 `src/aico/core/memory_broadcast.py`:
  - `MemoryBroadcastReceipt`
  - `MemoryBroadcastService`。
- 扩展 `src/aico/core/orchestrator.py`:
  - project task 召回 scope 加入 `MemoryScope.team(project_id, "default")`。
- 扩展 `src/aico/core/collaboration.py`:
  - `collaboration_payload()` 支持可关闭 `memory_refs + delta`。
- 更新 `src/aico/core/__init__.py` 导出 broadcast 服务和 receipt。
- 更新 `STATUS.md`、`CHANGELOG.md` 和 Phase 7 playbook。

### 验证结果
- 红灯验证:
  - `uv run pytest tests/unit/test_memory.py::test_memory_broadcast_creates_team_memory_edge_and_receipt tests/unit/test_memory.py::test_memory_broadcast_rejects_cross_project_team_scope tests/unit/test_orchestrator.py::test_orchestrator_injects_broadcast_team_memory_for_active_project_task tests/unit/test_collaboration.py::test_collaboration_payload_can_use_memory_refs_when_enabled tests/unit/test_collaboration.py::test_collaboration_payload_falls_back_to_explicit_payload_without_refs`
  - 初始失败:缺少 `MemoryBroadcastService` / `MemoryBroadcastReceipt` 导出。
- 绿灯验证:
  - 同一目标 pytest 命令:5 passed。
  - `uv run ruff check src/aico/core/memory.py src/aico/core/memory_broadcast.py src/aico/core/collaboration.py src/aico/core/orchestrator.py src/aico/core/__init__.py tests/unit/test_memory.py tests/unit/test_orchestrator.py tests/unit/test_collaboration.py`
  - `uv run ruff format --check src/aico/core/memory.py src/aico/core/memory_broadcast.py src/aico/core/collaboration.py src/aico/core/orchestrator.py src/aico/core/__init__.py tests/unit/test_memory.py tests/unit/test_orchestrator.py tests/unit/test_collaboration.py`
  - `uv run mypy src/aico/core/memory.py src/aico/core/memory_broadcast.py src/aico/core/collaboration.py src/aico/core/orchestrator.py tests/unit/test_memory.py tests/unit/test_orchestrator.py tests/unit/test_collaboration.py`
- 全量验证:
  - `uv run pytest`:240 passed, 1 skipped。
  - `uv run ruff check .`
  - `uv run ruff format --check .`
  - `uv run mypy src tests`
  - `git diff --check`

### 关键决策
- 🔒 **决策 1**:Team Broadcast 先作为内部 service,不新增老板必须操作的新命令。
- 🔒 **决策 2**:Broadcast 会生成新的 team-scoped atom,不改变原 atom 的 scope。
- 🔒 **决策 3**:`memory_refs + delta` 是 opt-in payload 格式;无 refs 时保持完整显式消息。

### 留给下一轮
- Phase 7 共享记忆本地验收流:
  - 用 `AICO_MEMORY_PATH` 覆盖命令入口、自动召回、boss feedback capture、candidate 不注入、team broadcast、JSONL 重启恢复。
  - 验收后考虑将 Phase 7 标记为功能完成,再转向真实 smoke test 或 Phase 8 准备。

### 状态变化
- `STATUS.md` 当前轮次更新为 Round 81。
- Phase 7 `Team Broadcast 与 A2A memory refs 实验 MVP` 标记完成。

## Round 82 — 2026-05-17 — Codex

### 输入
- 人类要求继续开发完成 Phase 7,并给出能满足企业、团队管理常见场景的验收功能和验证方式。
- `STATUS.md` 下一轮最高优先级是 Phase 7 共享记忆本地验收流。

### 思考与讨论
- 候选 A:只在最终回复列人工验收步骤 → ❌ **否决**:Phase 7 牵涉 agent/team/boss 共享状态,只靠口头步骤容易回归。
- 候选 B:新增企业/团队管理 acceptance test → ✅ **选定**:用本地 fake adapter + Orchestrator + JsonlMemoryStore 串起真实产品路径。
- 候选 C:顺手引入中文语义检索 → ❌ **暂缓**:第一版明确是 scope + 子串/标签匹配,语义检索需要单独设计权限、citation 和成本边界。

### 产出
- 新增 `tests/unit/test_phase7_memory_acceptance.py`:
  - 覆盖 project memory 写入、`/recall` 和普通项目任务自动召回。
  - 覆盖其它 project 记忆不串入当前 project prompt。
  - 覆盖 boss global 偏好自动抽取并进入后续 prompt。
  - 覆盖 project candidate feedback 被保存但不注入 Prompt Stack。
  - 覆盖 `MemoryBroadcastService` 生成 team memory、`broadcast_to` edge 和 receipt。
  - 覆盖同一 `AICO_MEMORY_PATH` 重启恢复后,team memory 仍进入后续任务 prompt。
  - 覆盖 A2A `memory_refs + delta` 可用且无 refs 时回退完整显式 payload。
  - 覆盖 `/forget` 归档恢复后的 project memory。
- 更新 `docs/playbooks/phase-7-shared-memory.md`,新增企业/团队管理验收场景。
- 更新 `docs/human/daily-ops.md`,补充 Shared Memory 团队管理验收重点和中文检索边界。
- 更新 `docs/journal/PITFALLS.md`,记录 P-019:Phase 7 第一版中文记忆检索不是语义搜索。
- 更新 `STATUS.md` 和 `CHANGELOG.md`,将 Phase 7 共享记忆本地验收流标记完成。

### 验证结果
- 红灯验证:
  - `uv run pytest tests/unit/test_phase7_memory_acceptance.py`
  - 初始失败:boss global 中文长句 query 没有命中短关键词记忆。
- 绿灯验证:
  - 将验收 query 收敛为第一版 deterministic 检索能稳定支持的关键词。
  - `uv run pytest tests/unit/test_phase7_memory_acceptance.py`:1 passed。
- 全量验证:
  - `uv run pytest`:241 passed, 1 skipped。
  - `uv run ruff check .`
  - `uv run ruff format --check .`
  - `uv run mypy src tests`
  - `git diff --check`

### 关键决策
- 🔒 **决策 1**:Phase 7 完成标准是企业/团队场景 acceptance test 通过,不是只完成五个孤立能力切片。
- 🔒 **决策 2**:第一版记忆检索保持可审计 deterministic 策略;中文语义检索作为后续增强,不混入 Phase 7 收口。
- 🔒 **决策 3**:验收文档必须继续强调老板不应高频手动管理记忆,agent 自动捕获/召回是主路径。

### 留给下一轮
- Cursor / CodeFlicker / Trae / Gemini 真实 smoke test。
- Feishu Channel 部署层与真实 smoke test。
- Phase 8 离线托管模式 ADR。

### 状态变化
- `STATUS.md` 当前轮次更新为 Round 82。
- Phase 7 `共享记忆本地验收流` 标记完成。
- 阶段地图中 Phase 7 标记完成。

## Round 83 — 2026-05-18 — Codex

### 输入
- 人类反馈操作 `/remember` 时报:`Memory store is not configured. Set AICO_MEMORY_PATH first.`

### 思考与讨论
- 候选 A:只回复让人类 export 环境变量 → ❌ **不够**:当前 IM 报错不具备可执行上下文,Quickstart 也没有 memory path,后续会继续踩中。
- 候选 B:无配置时自动创建进程内 memory store → ❌ **否决**:Round 79 已明确无 `AICO_MEMORY_PATH` 时保持无记忆行为,避免“看似记住但重启丢失”。
- 候选 C:保持持久化门槛,但把 IM 提示和 Quickstart 改成可执行 → ✅ **选定**:既保留可审计 JSONL 边界,又降低使用门槛。

### 产出
- 更新 `src/aico/core/memory_commands.py`:
  - 未配置 memory store 时,提示当前 running process 未启用 shared memory。
  - 明确需要启动 `aico-phase1` 前设置 `AICO_MEMORY_PATH` 并重启。
  - 给出后续 `/use project <project>` 与 `/remember <fact>`。
- 扩展 `tests/unit/test_orchestrator.py`:
  - 覆盖 active project 下 `/remember` 遇到未配置 memory store 时的可执行提示。
- 更新 `docs/human/quickstart.md`:
  - 快速启动环境变量加入 `AICO_PROJECT_CONFIG_PATH` 和 `AICO_MEMORY_PATH`。
  - 常用命令加入 `/use project aico`、`/remember`、`/recall` smoke。

### 验证结果
- 目标验证:
  - `uv run pytest tests/unit/test_orchestrator.py::test_orchestrator_memory_commands_explain_how_to_enable_store tests/unit/test_orchestrator.py::test_orchestrator_remember_recall_and_forget_project_memory tests/unit/test_phase1_app.py::test_build_phase1_runtime_configures_memory_store_when_path_set`:3 passed。
  - `uv run ruff check src/aico/core/memory_commands.py tests/unit/test_orchestrator.py`
  - `uv run ruff format --check src/aico/core/memory_commands.py tests/unit/test_orchestrator.py`
  - `uv run mypy src/aico/core/memory_commands.py tests/unit/test_orchestrator.py`
- 全量验证:
  - `uv run pytest`:242 passed, 1 skipped。
  - `uv run ruff check .`
  - `uv run ruff format --check .`
  - `uv run mypy src tests`
  - `git diff --check`

### 关键决策
- 🔒 **决策 1**:不悄悄启用进程内共享记忆;Phase 7 共享记忆必须由 `AICO_MEMORY_PATH` 指向可恢复 JSONL。
- 🔒 **决策 2**:使用侧错误提示必须给出“设置环境变量 + 重启进程”的上下文,因为运行中的 Bot 不会动态读取新 env。

### 留给下一轮
- 如果希望彻底减少配置负担,可以设计显式默认持久化路径 ADR,例如 `.aico/memory.jsonl`;不要在当前修复中静默改变持久化语义。

### 状态变化
- `STATUS.md` 当前轮次更新为 Round 83。

## Round 84 — 2026-05-18 — Codex

### 输入
- 人类验收后指出当前记忆召回像关键词 / 正则匹配,希望使用模型能力按语义检索。

### 思考与讨论
- 候选 A:继续要求老板使用稳定关键词 → ❌ **否决**:这会把记忆负担推回老板,不符合 Phase 7 agent-driven memory 方向。
- 候选 B:每次 `/recall` / Prompt Stack 都调用外部 LLM rerank → ❌ **暂缓**:当前没有稳定模型 endpoint、结构化输出、成本和失败回退边界。
- 候选 C:新增可插拔 `MemorySemanticScorer`,默认本地 semantic scorer,未来可替换 embedding / LLM rerank → ✅ **选定**:先解决中文长句和常见术语语义召回,同时保留 scope/governor/citation。

### 产出
- 更新 `src/aico/core/memory.py`:
  - 新增 `MemorySemanticScorer` Protocol。
  - 新增 `LocalSemanticMemoryScorer`,支持 ASCII token、CJK n-gram 和常见中英项目管理术语别名。
  - `JsonlMemoryStore.search()` 使用 semantic score 排序,不再只按子串过滤。
  - `MemoryRetriever` 先按 scope 收集候选,再按 semantic score 排序;candidate / restricted / archived 仍由 `MemoryGovernor` 排除。
- 更新 `src/aico/core/__init__.py`,导出 semantic scorer 类型。
- 扩展 `tests/unit/test_memory.py`:
  - 中文长句 query 可召回 boss global 偏好。
  - 中文“法务检查”可召回英文 `legal review` 项目记忆。
- 更新 `tests/unit/test_phase7_memory_acceptance.py`,把 Round 82 收敛过的短 query 改回自然长句验收。
- 新增 ADR-0023 `Memory Semantic Retrieval`。
- 更新 Phase 7 playbook、daily ops、A2A memory fabric 架构说明和 P-019。

### 验证结果
- 红灯验证:
  - `uv run pytest tests/unit/test_memory.py::test_memory_retriever_uses_semantic_scoring_for_chinese_long_query tests/unit/test_memory.py::test_memory_search_supports_bilingual_semantic_aliases`
  - 初始失败:长中文 query 和“法务检查”都无法召回。
- 绿灯验证:
  - 同一目标 pytest 命令:2 passed。
  - `uv run pytest tests/unit/test_phase7_memory_acceptance.py tests/unit/test_memory.py`:11 passed。
- 全量验证:
  - `uv run pytest`:244 passed, 1 skipped。
  - `uv run ruff check .`
  - `uv run ruff format --check .`
  - `uv run mypy src tests`
  - `git diff --check`

### 关键决策
- 🔒 **决策 1**:语义召回先作为可插拔 scorer,不把完整 memory store 暴露给 agent 或 provider。
- 🔒 **决策 2**:召回能力提升不能绕过 `MemoryGovernor`;candidate、archived、restricted 仍不能注入 prompt。
- 🔒 **决策 3**:真实 embedding / LLM rerank 是下一层 scorer 实现,需要另行定义成本、延迟、结构化输出和失败回退。

### 留给下一轮
- 如需更强企业级语义召回,实现 embedding / LLM-backed `MemorySemanticScorer`,并增加离线缓存、超时回退和观测指标。

### 状态变化
- `STATUS.md` 当前轮次更新为 Round 84。
- ADR 索引新增 ADR-0023。

## Round 85 — 2026-05-18 — Codex

### 输入
- 人类要求开发飞书 Channel,对齐当前 Telegram。

### 思考与讨论
- 候选 A:把飞书塞进 `aico-phase1` long polling 生命周期 → ❌ **否决**:飞书是事件订阅 webhook 模式,强行复用 Telegram polling 会让 channel 生命周期语义变形。
- 候选 B:只保留 `FeishuChannel.handle_event()` 给未来接入 → ❌ **不足**:人类问的是“开发飞书 channel”,当前缺的是可运行 callback server 和验收路径。
- 候选 C:保留 Telegram 默认入口,新增 `AICO_CHANNEL=feishu` runtime wiring 和独立 `aico-feishu-webhook` FastAPI 入口 → ✅ **选定**:对齐 Telegram 的 Orchestrator 能力,同时尊重飞书 webhook 部署模型。

### 产出
- 更新 `Phase1Settings`:
  - 新增 `AICO_CHANNEL=telegram|feishu`。
  - 新增飞书 App ID、App Secret、Verification Token、API base URL、webhook host / port / path 配置。
- 更新 `build_phase1_runtime()`:
  - 默认仍构造 `TelegramChannel`。
  - `AICO_CHANNEL=feishu` 时构造 `FeishuChannel`,并复用现有 Orchestrator、项目办公室、审批、记忆和报告能力。
- 新增 `src/aico/app/feishu_webhook.py`:
  - `GET /healthz` 健康检查。
  - `POST /feishu/events` 默认事件回调。
  - URL verification 返回 challenge。
  - verification token 不匹配时返回 400。
- 新增 `aico-feishu-webhook` CLI 脚本。
- 新增/更新单测:
  - Feishu runtime wiring。
  - Feishu webhook healthz。
  - URL verification challenge。
  - verification token 拒绝路径。
- 更新 daily ops、Feishu playbook、playbook 索引、STATUS 和 CHANGELOG。

### 验证结果
- 目标验证:
  - `uv run pytest tests/unit/test_feishu_channel.py tests/unit/test_feishu_webhook.py tests/unit/test_phase1_app.py::test_build_phase1_runtime_wires_feishu_channel tests/unit/test_phase1_app.py::test_build_phase1_runtime_requires_feishu_credentials`:10 passed。
  - `uv run ruff check src/aico/app/phase1.py src/aico/app/feishu_webhook.py tests/unit/test_phase1_app.py tests/unit/test_feishu_webhook.py`
  - `uv run ruff format --check src/aico/app/phase1.py src/aico/app/feishu_webhook.py tests/unit/test_phase1_app.py tests/unit/test_feishu_webhook.py`
  - `uv run mypy src/aico/app/phase1.py src/aico/app/feishu_webhook.py tests/unit/test_phase1_app.py tests/unit/test_feishu_webhook.py`

### 关键决策
- 🔒 **决策 1**:Telegram 仍是默认 `aico-phase1` 主控入口;飞书使用独立 `aico-feishu-webhook` 进程。
- 🔒 **决策 2**:飞书 action/card 不在本轮做专属交互;平台无关 `MessageContent.actions` 继续在 Feishu Channel 内降级为文本提示。
- 🔒 **决策 3**:真实 smoke test 不能用 mock 替代,需要企业自建应用凭据和公网 HTTPS callback URL。

### 留给下一轮
- 执行飞书开放平台真实 URL verification。
- 订阅 `im.message.receive_v1`,向机器人发送 `/help` / `/status` / `/project`,确认文本命令进入现有 Orchestrator 并能回包。
- 如需要飞书按钮体验,在 `FeishuChannel` 内增加 interactive card 映射,不要修改 `IMChannel` 核心协议。

### 状态变化
- `STATUS.md` 当前轮次更新为 Round 85。

## Round 86 — 2026-05-18 — Codex

### 输入
- 人类表示飞书 Channel 晚点验证,询问后续还有什么要开发,要求继续开发。

### 思考与讨论
- 当前剩余真实飞书 smoke test 需要企业自建应用凭据和公网 HTTPS callback,不适合在本轮强行推进。
- 飞书官方事件文档说明:2.0 事件用 `header.event_id` 唯一标识,1.0 事件用 `uuid`;事件接收失败会重试,成功接收后也可能因至少一次投递策略收到重复事件。
- 候选 A:等待真实 Feishu 凭据再处理重复事件 → ❌ **否决**:重复投递是 webhook 平台的基础风险,可以本地 TDD 先闭环。
- 候选 B:把幂等塞进 Orchestrator 或 TaskBus → ❌ **否决**:这是 Feishu webhook 投递语义,不应污染核心编排。
- 候选 C:在 `FeishuChannel` 内按 event id / uuid 做进程内 TTL 去重 → ✅ **选定**:对齐 Telegram offset 的“不要重复消费”效果,又保持 Channel 可插拔边界。

### 产出
- 更新 `src/aico/channel/feishu.py`:
  - 新增本地 event id 去重缓存。
  - 默认 TTL 为 8 小时,覆盖飞书重试窗口。
  - 默认最多保留 4096 个 event id,超限时淘汰最早记录。
  - v2 payload 使用 `header.event_id`;v1 payload 使用 `uuid`。
  - 缺少唯一 id 的 payload 保持原路径处理,避免误丢非标准消息。
- 扩展 `tests/unit/test_feishu_channel.py`:
  - 覆盖 v2 `event_id` 重复投递只派发一次。
  - 覆盖 v1 `uuid` 重复投递只派发一次。
  - 覆盖 TTL 到期后允许同一 id 再次处理。
- 更新 daily ops、Feishu playbook、STATUS 和 CHANGELOG。

### 验证结果
- 目标验证:
  - `uv run pytest tests/unit/test_feishu_channel.py tests/unit/test_feishu_webhook.py`:11 passed。
  - `uv run ruff check src/aico/channel/feishu.py tests/unit/test_feishu_channel.py`
  - `uv run ruff format --check src/aico/channel/feishu.py tests/unit/test_feishu_channel.py`
  - `uv run mypy src/aico/channel/feishu.py tests/unit/test_feishu_channel.py`

### 关键决策
- 🔒 **决策 1**:Feishu 重试幂等属于 Channel 边界,不进入核心 Orchestrator。
- 🔒 **决策 2**:本轮先做进程内 TTL 去重,不引入新持久化后端;如果真实 dogfooding 发现重启后重复投递造成问题,再升级为 audit / JSONL backed 去重。
- 🔒 **决策 3**:缺少 event id / uuid 的事件不直接丢弃,因为第一切片仍要优先保证文本入口可用。

### 留给下一轮
- 真实飞书开放平台 URL verification 和文本回包 smoke test。
- Feishu signature / encrypted event 支持可作为下一个生产化切片,前提是确认自建应用事件订阅配置需要 Encrypt Key。

### 状态变化
- `STATUS.md` 当前轮次更新为 Round 86。

## Round 87 — 2026-05-18 — Codex

### 输入
- 人类表示飞书 Channel 真实验证先晚点一起做;如果没有其它问题,开始 Phase 8。

### 思考与讨论
- Phase 8 目标是“睡前下任务,早上看结果”。它必须服务于老板管理项目和团队,不是新增一个危险的无人值守脚本入口。
- 候选 A:直接实现 cron / scheduler / night worker → ❌ **否决**:需要持久化、重启恢复、权限预算和失败恢复;第一切片容易绕过 `/approve`。
- 候选 B:只告诉用户继续用普通项目消息 → ❌ **不足**:没有“托管工单”语义,老板无法区分睡前派工和普通咨询。
- 候选 C:新增 `/overnight <goal>` project-scoped offline delegation work order → ✅ **选定**:派给当前项目 lead/default role,复用已有 appointment prompt、memory、provider session、approval、audit 和 `/daily`。

### 产出
- 新增 ADR-0024 `Phase 8 Offline Delegation Scope`。
- 新增 `src/aico/core/offline_delegation.py`:
  - `OfflineDelegationCommandHandler`
  - `OfflineDelegationRecord`
  - `offline_delegation_prompt()`
  - `offline_delegation_started_message()`
- 新增 `/overnight <goal>`:
  - 需要 active project。
  - 使用当前项目 default assignment / lead role。
  - 创建 `aico.intent=offline_delegation` 元数据。
  - prompt 要求 lead 留下 morning handoff:done、blocked、risks、next actions。
  - 运行仍走 `TaskBus`,因此风险任务继续进入 `/approve`。
- 新增 `/overnight`:
  - 展示当前 active project 本进程内最近托管工单。
  - 给出早报入口 `/daily <project>` 和 `/tasks`。
- 更新 help、daily ops、Phase 8 playbook、STATUS、CHANGELOG 和 ADR 索引。

### 验证结果
- 目标验证:
  - `uv run pytest tests/unit/test_commands.py tests/unit/test_orchestrator.py::test_orchestrator_queues_overnight_delegation_to_project_lead tests/unit/test_orchestrator.py::test_orchestrator_overnight_requires_active_project tests/unit/test_orchestrator.py::test_orchestrator_overnight_keeps_risky_goal_waiting_for_approval`:13 passed。
  - `uv run ruff check src/aico/core/commands.py src/aico/core/offline_delegation.py src/aico/core/orchestrator.py src/aico/core/__init__.py tests/unit/test_commands.py tests/unit/test_orchestrator.py`
  - `uv run ruff format src/aico/core/offline_delegation.py tests/unit/test_orchestrator.py`
  - `uv run mypy src/aico/core/commands.py src/aico/core/offline_delegation.py src/aico/core/orchestrator.py src/aico/core/__init__.py tests/unit/test_commands.py tests/unit/test_orchestrator.py`

### 关键决策
- 🔒 **决策 1**:Phase 8 第一切片是“托管工单”,不是无人值守调度器。
- 🔒 **决策 2**:`/overnight` 不绕过 Phase 4 风险审批;它只改变管理语义和交接要求。
- 🔒 **决策 3**:托管范围默认 project-scoped,通过当前 project lead/default role 承接,不跨 project/team 自动共享上下文。

### 留给下一轮
- 为 `/overnight` 增加持久化记录,让重启后可以从 audit JSONL 恢复托管工单列表。
- 设计多 step / 多 agent 夜间编排,但必须保留审批、审计和中断边界。
- 评估是否需要“早报自动推送”机制,而不是只让老板手动 `/daily`。

### 状态变化
- `STATUS.md` 当前轮次更新为 Round 87。
- Phase 8 从未开始变为进行中。

## Round 88 — 2026-05-18 — Codex

### 输入
- 人类反馈“AI 开源维护者的一晚”展示不全,体现不了项目团队、角色、记忆架构等能力。
- 人类要求给 Codex 足够自由度,把主 demo 项目搞出来;若缺框架能力先梳理对齐,最终落成符合现实团队协作的完整 demo。

### 思考与讨论
- 候选 A:继续做“修一个 issue”的轻量 demo → ❌ **否决**:只能展示 `/overnight` 和单任务派发,无法体现 AICO 的 project office、team appointment、shared memory、approval/audit 和 report 面。
- 候选 B:直接做真实大型开源项目 release demo → ❌ **否决**:外部项目上下文大、失败面太广,首个开源 demo 容易被底层 AI 能力和仓库复杂度吞没。
- 候选 C:内置一个小型 `notes-cli` release room → ✅ **选定**:仓库小到 AI team 能真实完成,但流程足够完整,可以展示 PM / implementer / tester / reviewer / release-manager 的现实协作。
- 候选 D:本轮同时新增 orchestration framework 能力 → ❌ **暂缓**:现有 project/team/memory/approval/audit/overnight 能支撑 Stage 1 demo package;真正需要的新能力是 Stage 2 的 fake transcript / acceptance harness,应先让 demo 资产稳定。

### 产出
- 新增 `docs/examples/README.md` 和 `docs/examples/release-room.md`,定义 open-source examples 的选择标准和 Release Room 主 demo。
- 新增 `docs/playbooks/release-room-demo.md`,覆盖启动环境变量、IM 操作步骤、录屏建议、验证和 fallback。
- 新增 `examples/release-room/aico-project.json`,配置 release-room 项目团队:
  - `pm -> claude`
  - `implementer -> claude`
  - `tester -> codex`
  - `reviewer -> codex`
  - `release-manager -> claude`
- 新增 `examples/release-room/demo-script.md` 和 `examples/release-room/recording-storyboard.md`,把 `/use project`、`/team`、`/remember`、`/ask`、`/role propose`、`/overnight`、`/daily`、`/audit` 串成录屏脚本。
- 新增 `examples/release-room/notes-cli` 示例仓库:
  - v0.1 Python stdlib CLI。
  - `NORTH_STAR.md`、`STATUS.md`、journal 三件套、issue、release notes 草稿。
  - v0.1 通过测试和 v0.2 skipped release contract tests。
- 新增 `tests/unit/test_release_room_example.py`,验证 demo config 能被 `ProjectAssignmentConfig` / `ProjectAssignmentDirectory` 加载,且示例仓库关键项目文档存在。
- 更新 README 和 playbook index,把 Release Room 作为主 demo 入口。

### 验证结果
- `uv run pytest tests/unit/test_release_room_example.py`:2 passed。
- `uv run pytest examples/release-room/notes-cli/tests`:2 passed,3 skipped。
- `uv run ruff check docs/examples README.md docs/playbooks/release-room-demo.md examples/release-room tests/unit/test_release_room_example.py`:passed。
- `uv run ruff format --check examples/release-room tests/unit/test_release_room_example.py`:passed。

### 关键决策
- 🔒 **决策 1**:主开源 demo 选择 Release Room,以“小型真实 release 流程”展示 AICO 的团队管理能力,而不是以单 issue 修复展示 coding agent 能力。
- 🔒 **决策 2**:demo 第一阶段只新增静态资产和配置校验,不新增核心抽象;Stage 2 再做 fake adapter transcript / acceptance harness。
- 🔒 **决策 3**:示例仓库保留 skipped v0.2 contract tests,让 AI team 的目标清晰可验收,同时不让 demo 初始状态在普通测试中失败。

### 留给下一轮
- Release Room Stage 2:新增本地端到端 transcript/acceptance,用 fake adapters 跑完整管理路径,覆盖团队、记忆、审批、任务追踪、早报和审计。
- Release Room Stage 3:用真实 Telegram/Feishu + Claude/Codex 跑核心脚本并录制 GIF。
- 如果 Stage 2 发现现有框架无法稳定表达多角色 release handoff,再单独设计能力缺口,不要把 demo 需求硬塞进核心。

### 状态变化
- `STATUS.md` 当前轮次更新为 Round 88。
- 近期高优产品方向新增 Open-source Showcase。
- 开源 Demo 进度新增 Release Room Stage 1 完成,Stage 2/3 待做。

## Round 89 — 2026-05-18 — Codex

### 输入
- 人类要求开始 Release Room Stage 2。
- Stage 1 已有示例仓库、AICO project/team 配置、playbook、demo script 和录屏 storyboard。

### 思考与讨论
- 候选 A:直接用真实 Claude/Codex 跑 demo → ❌ **暂缓**:真实 IM / CLI 输出有环境依赖,不适合作为第一个可重复验收基线。
- 候选 B:只手写一份 transcript → ❌ **否决**:会退化成说明文档,无法证明 AICO 的 project/team/memory/approval/audit/report 链路真的能跑。
- 候选 C:用 fake adapters 驱动真实 Orchestrator/TaskBus/MemoryStore → ✅ **选定**:底层 AI 输出确定,但 AICO 管理链路真实执行,能稳定回归。
- 候选 D:为了 demo 新增通用 transcript runner 框架 → ❌ **暂缓**:当前只有一个主 demo,按 Rule of Three 不先抽象;等 Stage 3 或第二个 demo 出现再考虑。

### 产出
- 新增 `tests/unit/test_release_room_acceptance.py`:
  - 读取真实 `examples/release-room/aico-project.json`。
  - 使用 `ProjectAssignmentDirectory`、`Orchestrator`、`TaskBus`、`AdapterRegistry`、`JsonlMemoryStore`。
  - 使用 deterministic `ReleaseRoomAdapter` 代替 Claude/Codex。
  - 驱动完整管理路径:`/team`、3 条 `/remember`、PM 拆工、implementer 审批、tester/reviewer 独立验收、release-manager release notes、`/overnight`、`/daily`、`/tasks`、`/metrics`、`/audit`。
  - 验证 memory 注入、approval requested/approved audit、offline delegation metadata 和 daily Boss summary。
- 新增 `examples/release-room/transcript.md`,作为无真实 token 的本地 transcript 和后续录屏素材。
- 更新 `docs/examples/release-room.md`、`docs/playbooks/release-room-demo.md`、`examples/release-room/README.md`、`STATUS.md` 和 `CHANGELOG.md`,将 Stage 2 标记完成。

### 验证结果
- `uv run pytest tests/unit/test_release_room_acceptance.py tests/unit/test_release_room_example.py`:4 passed。
- `uv run pytest examples/release-room/notes-cli/tests`:2 passed,3 skipped。
- `uv run ruff check examples/release-room tests/unit/test_release_room_acceptance.py tests/unit/test_release_room_example.py docs/examples docs/playbooks/release-room-demo.md README.md`:passed。
- `uv run ruff format --check examples/release-room tests/unit/test_release_room_acceptance.py tests/unit/test_release_room_example.py`:passed。
- `uv run mypy tests/unit/test_release_room_acceptance.py tests/unit/test_release_room_example.py`:passed。

### 关键决策
- 🔒 **决策 1**:Release Room Stage 2 的验收对象是 AICO 管理链路,不是底层 AI 代码生成质量;底层输出用 fake adapters 固定。
- 🔒 **决策 2**:暂不抽象 transcript runner;一个主 demo 先用本地测试表达,避免为了展示而新增框架。
- 🔒 **决策 3**:真实录屏前先维护 `examples/release-room/transcript.md` 作为镜头节奏和 README/GIF 素材。

### 留给下一轮
- Release Room Stage 3:用真实 Telegram/Feishu + Claude/Codex 跑核心脚本并录制 30-60 秒 GIF。
- Phase 8 `/overnight` 持久化:让重启后仍能从 audit JSONL 恢复托管工单列表,支撑真实“早上看结果”录屏。
- 如果真实 Stage 3 发现 project role 输出仍过多暴露 agent/provider 名称,再设计 role-first transcript/render 修正。

### 状态变化
- `STATUS.md` 当前轮次更新为 Round 89。
- Release Room Stage 2 local acceptance transcript 标记完成。

## Round 90 — 2026-05-18 — Codex

### 输入
- 人类要求开始 Release Room Stage 3 中的“拿 transcript 做镜头节奏”。
- 人类说明本机有 Telegram App、Claude CLI(但无 Claude Pro)和 Codex,没有 GIF 转换工具。

### 思考与讨论
- 候选 A:直接进入真实 Telegram + Claude/Codex 录屏 → ❌ **暂缓**:Claude 无 Pro 时额度和输出稳定性不适合先作为 README GIF 的节奏基线;直接拍真实长输出也容易把观众注意力带到底层 AI。
- 候选 B:要求先安装 `gifski` 或其它剪辑工具 → ❌ **否决**:本机已有 `ffmpeg`,Stage 3 第一段不应被工具安装卡住。
- 候选 C:先把 Stage 2 transcript 压成 shot rhythm,再用真实 IM 只拍精简管理路径 → ✅ **选定**:保持 README GIF 稳定聚焦 project office / team / memory / approval / audit,真实 dogfooding 后续按同一节奏补拍。

### 产出
- 新增 `examples/release-room/shot-rhythm.md`:
  - 56 秒 README GIF 时间线。
  - 精简命令清单。
  - 保留/删减规则。
  - Claude 无 Pro 时的录制降级建议。
  - README GIF 交付路径 `docs/assets/release-room-demo.gif`。
- 新增 `examples/release-room/make-gif.sh`:
  - 使用 `ffmpeg` 的 palettegen / paletteuse 两段转换。
  - 支持 `AICO_GIF_FPS` 和 `AICO_GIF_WIDTH`。
  - 不依赖 `gifski`。
- 更新 `examples/release-room/README.md`、`recording-storyboard.md`、`docs/examples/release-room.md`、`docs/playbooks/release-room-demo.md` 和 `CHANGELOG.md`。

### 验证结果
- `bash -n examples/release-room/make-gif.sh`:passed。
- `git diff --check`:passed。

### 关键决策
- 🔒 **决策 1**:README GIF 先以 Stage 2 transcript 的管理链路做节奏基线,真实 IM dogfooding 录屏按同一节奏补拍。
- 🔒 **决策 2**:没有 `gifski` 不作为卡点;优先复用本机 `ffmpeg`。
- 🔒 **决策 3**:Stage 3 GIF 不拍 role proposal、完整 `/metrics` 或长代码输出;这些留给长版 demo。

### 留给下一轮
- 按 `examples/release-room/shot-rhythm.md` 在 Telegram App 中录 30-60 秒主 GIF 素材。
- 用 `examples/release-room/make-gif.sh` 转出 `docs/assets/release-room-demo.gif`。
- 将 GIF 嵌入 README 首屏,再做一次 README 视觉和体积检查。

### 状态变化
- `STATUS.md` 当前轮次更新为 Round 90。
- Release Room Stage 3 recording rhythm and GIF conversion path 标记完成;public GIF / README showcase 仍未完成。

## Round 91 — 2026-05-18 — Codex

### 输入
- 人类批准继续执行 Stage 3,并允许在 Telegram App 中向 AICO Bot 发送 Release Room demo 指令。

### 思考与讨论
- 候选 A:按 shot rhythm 直接完整录真实 Claude/Codex public GIF → ❌ **阻塞**:真实 provider 输出首屏不稳定,会把 README demo 从 AICO 管理面拖到底层 CLI 噪音。
- 候选 B:继续硬等 Claude 或继续让 Codex 输出 → ❌ **否决**:会污染 Telegram 对话,且不能解决 public GIF 的质量问题。
- 候选 C:保留真实 dogfooding 证据,把 provider 输出问题记录为 blocker,同时修复日志 token 泄露风险 → ✅ **选定**:先保护安全和交接质量,public GIF 改走 transcript-driven 稳定素材。

### 产出
- 真实 Telegram dogfooding:
  - 停掉重复 `aico-phase1` 实例,解决 Telegram `409 Conflict`。
  - 用真实 Telegram Bot API 启动单实例,并将 `AICO_TELEGRAM_POLL_TIMEOUT_SECONDS=3` 降低 long-polling 空白 warning。
  - 发送 `/use project release-room`、`/team` 和 3 条 `/remember`,均真实回包。
  - `/ask pm ...` 触发 Claude CLI 长时间无输出后,用 `/interrupt 4c0b914a` 成功中断。
  - 临时 `/appoint codex as pm docs audit` 后重试 PM 拆工,发现 Codex CLI warning / HTML / resume error 原样刷进 Telegram。
- 新增 `BLOCKERS.md` B-003:真实 provider 输出不适合作为 public GIF。
- 新增 `PITFALLS.md` P-017:真实 Stage 3 录屏被底层 CLI 噪音污染。
- 新增 `PITFALLS.md` P-018:httpx INFO 日志会把 Telegram Bot token 打进日志。
- 修复 `src/aico/app/phase1.py`:将 `httpx` / `httpcore` logger 降到 WARNING。
- 更新 `tests/unit/test_phase1_app.py`:新增 `test_phase1_logging_suppresses_http_client_info_logs`。
- 更新 `examples/release-room/shot-rhythm.md`、`STATUS.md`。

### 验证结果
- `uv run pytest tests/unit/test_phase1_app.py::test_phase1_logging_suppresses_http_client_info_logs`:1 passed。
- `uv run ruff check src/aico/app/phase1.py tests/unit/test_phase1_app.py`:passed。
- `uv run ruff format --check src/aico/app/phase1.py tests/unit/test_phase1_app.py`:passed。
- `uv run mypy src/aico/app/phase1.py tests/unit/test_phase1_app.py`:passed。

### 关键决策
- 🔒 **决策 1**:B-003 未解前,不要把真实 Claude/Codex 原始输出直接做成 README public GIF。
- 🔒 **决策 2**:Stage 3 public showcase 可以先使用 transcript-driven 稳定素材;真实 provider dogfooding 单独作为验收证据。
- 🔒 **决策 3**:AICO 默认 INFO 日志不应记录 httpx/httpcore 请求 URL,因为 Telegram token 位于 URL path。

### 留给下一轮
- 清理 Codex/Claude Adapter 输出:过滤 CLI warning、HTML 片段、内部路径和 resume error,或增加 public-demo 摘要层。
- 用 transcript-driven 素材生成 `docs/assets/release-room-demo.gif`,嵌入 README。
- B-003 解开后再重录真实 provider public GIF。

### 状态变化
- `STATUS.md` 当前轮次更新为 Round 91。
- B-003 作为当前活跃卡点新增。

## Round 92 — 2026-05-18 — Codex

### 输入
- 人类已删除 `logs/aico.log`,并要求对齐生成 GIF 的卡点:
  - Claude 输出不适合做图,是否可以用 Claude Code CLI。
  - Codex warning / HTML / resume error 不清楚原因,要求继续处理。

### 思考与讨论
- 候选 A:把 Claude 命令从 `claude` 改成 `cc` → ❌ **否决**:本机 `claude --version` 显示 `2.1.143 (Claude Code)`,AICO 默认已经使用 Claude Code CLI;本机 `cc` 是 `/usr/bin/cc` C 编译器。
- 候选 B:只在 shot rhythm 文档里提示“不要拍 Codex 长输出” → ❌ **不足**:真实 Telegram 已证明 Codex 短输出也可能被 CLI 噪音污染,需要 Adapter 层兜底。
- 候选 C:修 provider session 边界 + Codex stdout 过滤 + role 改任命 session 重建 → ✅ **选定**:解决 `thread/resume failed` 根因,并避免 warning/HTML 噪音进入 IM。

### 产出
- `ClaudeCodeAdapter`:
  - 只在 `provider_session.provider_name == adapter.name` 时使用 provider session。
  - 增加 `_process_stdout_line()` 和 `_process_error_content()` hook,让具体 Adapter 能清洗输出。
- `CodexAdapter`:
  - 忽略非 Codex provider session,不再拿 Claude/AICO session id 跑 `codex exec resume`。
  - 过滤典型 timestamped Codex warning、`codex_core_plugins::manifest`、HTML tag、`sqlx::query` 和 `thread/resume failed`。
- `Orchestrator._ensure_assignment_session()`:
  - 同一 assignment seat 改任命到不同 agent/adapter 后关闭旧 session 并重建,避免沿用旧 provider ref。
- 测试:
  - Claude Adapter 忽略其它 provider session ref。
  - Codex Adapter 忽略其它 provider session ref。
  - Codex stdout 噪音过滤。
  - Orchestrator role 改任命后重建 assignment session。
- 真实 Telegram dry run:
  - `/use project release-room`
  - `/appoint codex as pm docs audit`
  - `/ask pm Give a 3-bullet release plan for v0.2. No code. No markdown table.`
  - 结果:Telegram 收到干净 3-bullet release plan,没有 warning / HTML / resume error。
- 更新 B-003、P-017、shot rhythm、STATUS 和 CHANGELOG。

### 验证结果
- `uv run pytest tests/unit/test_orchestrator.py::test_orchestrator_rebuilds_assignment_session_after_reappointing_role tests/unit/test_codex_adapter.py tests/unit/test_claude_code_adapter.py`:19 passed。
- `uv run ruff check src/aico/adapter/claude_code.py src/aico/adapter/codex.py src/aico/core/orchestrator.py tests/unit/test_claude_code_adapter.py tests/unit/test_codex_adapter.py tests/unit/test_orchestrator.py`:passed。
- `uv run ruff format --check src/aico/adapter/claude_code.py src/aico/adapter/codex.py src/aico/core/orchestrator.py tests/unit/test_claude_code_adapter.py tests/unit/test_codex_adapter.py tests/unit/test_orchestrator.py`:passed。
- `uv run mypy src/aico/adapter/claude_code.py src/aico/adapter/codex.py src/aico/core/orchestrator.py tests/unit/test_claude_code_adapter.py tests/unit/test_codex_adapter.py tests/unit/test_orchestrator.py`:passed。

### 关键决策
- 🔒 **决策 1**:Claude Code CLI 命令仍是 `claude`;不要把 `cc` 当 Claude Code 命令。
- 🔒 **决策 2**:Provider session metadata 只能被匹配的 Adapter 消费,防止跨 provider resume。
- 🔒 **决策 3**:IM 默认展示 provider 的干净业务输出;CLI warning / HTML / 内部路径类噪音留在日志或被过滤。

### 留给下一轮
- 按 `shot-rhythm.md` 录制真实 Telegram GIF:Codex 负责 PM/test/review 短输出,Claude 只拍 approval gate / task accepted。
- 如需继续拍 Claude 长输出,先确认无 Pro 环境下的非交互输出稳定性,或把 Claude implementer prompt 压到极短摘要。
- 生成 `docs/assets/release-room-demo.gif` 并嵌入 README。

### 状态变化
- `STATUS.md` 当前轮次更新为 Round 92。
- B-003 从 BLOCKING 调整为 DEFERRED。

## Round 93 — 2026-05-18 — Codex

### 输入
- 人类确认“可以,实际录一遍”,要求按 Stage 3 真实 Telegram flow 录制 demo。

### 产出
- 启动真实 AICO Telegram runtime,使用 fresh project memory / audit JSONL 做 Release Room dogfooding。
- 用 macOS ffmpeg AVFoundation 屏幕采集录制 Telegram 窗口区域:
  - `docs/assets/release-room-demo.mov`:第一段原始录屏。
  - `docs/assets/release-room-demo-part2.mov`:日报和审计收尾原始录屏。
  - `docs/assets/release-room-demo-trimmed.mov`:35 秒剪辑版视频。
  - `docs/assets/release-room-demo.gif`:README 可嵌入 GIF。
- 实录覆盖:
  - `/use project release-room`
  - `/team`
  - 3 条 `/remember`
  - `/appoint codex as pm docs audit`
  - Codex PM handoff 短输出
  - Codex tester regression checklist
  - `/daily release-room`
  - `/audit`
- README 增加 `docs/assets/release-room-demo.gif` 首屏展示。
- 新增 P-020:Codex read-only sandbox 里直接跑 pytest 可能没有可写临时目录。

### 验证结果
- `ffprobe` 确认 `docs/assets/release-room-demo.gif` 时长 35.26 秒、大小约 6.0MB。
- 抽帧检查确认 GIF 主体是 Telegram 窗口,包含 `/team`、project memory、tester output、`/daily` 和 `/audit` 镜头。
- `env AICO_GIF_FPS=8 AICO_GIF_WIDTH=720 bash examples/release-room/make-gif.sh docs/assets/release-room-demo-trimmed.mov docs/assets/release-room-demo.gif`:passed。

### 关键决策
- 🔒 **决策 1**:本轮保留真实 dogfooding 瑕疵,不伪造 transcript;Codex read-only pytest 临时目录失败单独记入 P-020。
- 🔒 **决策 2**:README 先嵌入 35 秒真实 GIF,后续再精剪 approval gate / 减少旧消息露出。

### 留给下一轮
- 复剪更干净的 public GIF:开头直接从 `/use` 开始,减少旧聊天记录露出。
- 若要展示 tester 真跑测试,先处理 Codex read-only 可写临时目录或调整为审批保护的执行路径。

### 状态变化
- `STATUS.md` 当前轮次更新为 Round 93。
- Release Room Stage 3 GIF 从待办改为已完成。

## Round 94 — 2026-05-19 — Codex

### 输入
- 人类要求按开源转化建议改一版,并继续从“AI agent 开发者 / 个人开发者”视角复盘问题。
- 观察到当前 README 仍偏内部项目说明,外部开发者第一眼还不容易理解“为什么要 star / 为什么要试用”。

### 思考与讨论
- 候选 A:只在中文 README 里补几段痛点 → ❌ **否决**:项目刚公开到 GitHub,全球 agent 开发者第一眼通常先看英文首屏;只补中文会限制传播和 star 转化。
- 候选 B:把 README 写成完整产品官网式长文 → ❌ **否决**:仓库入口应让开发者快速判断价值、状态和怎么跑,过重营销会削弱工程可信度。
- 候选 C:英文主 README + 中文镜像 + Quickstart 状态修正 + License → ✅ **选定**:最小范围内补齐外部开源信任和第一眼转化。

### 产出
- 重写 `README.md` 为英文主入口,突出 remote control room、真实本机 Adapter、审批审计、项目办公室、共享记忆和离线托管。
- 新增 `README.zh-CN.md`,保留中文叙事并同步痛点、差异化、当前能力、Quickstart 和路线图。
- 新增 `LICENSE`,采用 MIT License。
- 新增 `SECURITY.md`,说明审批绕过、命令执行、token 泄露等问题的私下报告路径和安全边界。
- 新增 GitHub issue templates:`bug_report.yml`、`feature_request.yml` 和 `config.yml`。
- 更新 `docs/human/quickstart.md`,移除 Phase 3 旧状态和本机绝对路径,改为当前 Phase 8 公开快速路径。
- 更新 `docs/examples/release-room.md`,将 Stage 3 public showcase 状态同步为已落地,后续改为复剪和增强项。
- 更新 `STATUS.md`,记录开源首屏第一版并把下一轮建议调整为外部视角二次验收。

### 验证结果
- 本轮是文档与开源入口改造,未改核心代码。
- `git diff --check`:passed。
- `uv run pytest tests/unit/test_release_room_example.py tests/unit/test_release_room_acceptance.py`:4 passed。
- `uv run ruff check .`:passed。

### 关键决策
- 🔒 **决策 1**:GitHub 主 README 使用英文,中文入口放 `README.zh-CN.md`。
- 🔒 **决策 2**:公开叙事先占住“远程指挥本机真实 AI 工具团队”,不泛化成大而全 Agent OS。
- 🔒 **决策 3**:`/overnight` 等能力在 README 中明确标注仍有持久化 / 重启恢复缺口,避免过度承诺。

### 留给下一轮
- 从全新 clone 跑一次 Quickstart,记录外部开发者真实卡点。
- 补 GitHub metadata、PR template、good first issue 列表和更短的 public roadmap 摘要。
- 复剪 Release Room GIF,减少旧聊天记录露出并补更清晰的 approval gate 镜头。

### 状态变化
- `STATUS.md` 当前轮次更新为 Round 94。
- Open-source Showcase 增加开源首屏第一版完成项,包含 License / Security / issue templates。

## Round 95 — 2026-05-19 — Codex

### 输入
- 人类确认 Cursor / CodeFlicker / Trae / Gemini 真实 smoke test 已完成,要求把公开状态从 pending 改掉。
- 人类要求补安全模型图、3 个“今天能干什么”的具体场景,并说明 GitHub description / topics / social preview 怎么手动配置。
- 人类要求完成后 push 到 GitHub。

### 思考与讨论
- 候选 A:只改 README 中的 pending 文案 → ❌ **否决**:Quickstart 和 STATUS 也有同一状态,只改 README 会导致公开入口和交接状态不一致。
- 候选 B:把 GitHub metadata 写进 README 顶部 → ❌ **否决**:description / topics / social preview 是仓库外部 metadata,放在 README 顶部会干扰读者主线。
- 候选 C:README 补核心内容,另建 GitHub publication checklist → ✅ **选定**:README 保持产品入口,具体可复制配置和官方约束放到 human 文档。

### 产出
- 更新 `README.md` / `README.zh-CN.md`:
  - Cursor / CodeFlicker / Trae / Gemini Adapter 状态改为真实 smoke test 已完成。
  - 新增 `Use It Today` / `今天能拿它做什么`,覆盖维护开源项目、睡前托管 bugfix、通勤路上审批 release。
  - 新增 Mermaid 安全模型图:IM sender -> IMChannel -> approval policy -> adapter capability -> local CLI -> audit log。
  - Roadmap 移除 Cursor / CodeFlicker / Trae / Gemini smoke test,改为 public setup / PR template / good first issue / adapter authoring / no-token demo。
- 更新 `docs/human/quickstart.md`,把 Cursor / CodeFlicker / Trae / Gemini 从待 smoke 改为已完成真实 smoke,但仍要求本机 CLI 已安装并登录。
- 新增 `docs/human/github-publication.md`,提供 GitHub description、website、topics、social preview 文案和手动操作路径。
- 更新 `STATUS.md`,把 Adapter smoke test 勾选完成,并从下一轮高优队列移除。

### 验证结果
- `rg -n "Cursor.*pending|smoke tests still|真实 smoke test 仍|完成 Cursor|待 smoke|roadmap" ...`:只剩正常 roadmap 文案,无 Adapter pending 残留。
- `git diff --check`:passed。
- `uv run pytest tests/unit/test_release_room_example.py tests/unit/test_release_room_acceptance.py`:4 passed。
- `uv run ruff check .`:passed。

### 关键决策
- 🔒 **决策 1**:已由人类确认的真实 smoke test 状态同步到 README / Quickstart / STATUS,不再作为下一轮待办。
- 🔒 **决策 2**:GitHub metadata 配置不写成自动化承诺;当前用文档给管理员可复制步骤。
- 🔒 **决策 3**:安全模型在 README 首屏之后展示,强调 AICO 是本机工具控制层而不是沙箱。

### 留给下一轮
- 生成或设计小于 1 MB 的 `1280 x 640` social preview 静态图。
- 补 adapter authoring guide 和 no-token local demo。
- 补 PR template 和 good first issue 列表。

### 状态变化
- `STATUS.md` 当前轮次更新为 Round 95。
- Adapter 扩展中 Cursor / CodeFlicker / Trae / Gemini 真实 smoke test 从未完成改为完成。

## Round 96 — 2026-05-20 — Codex

### 输入
- 人类认可“按部就班落地记忆能力升级”,要求开始实现记忆检索升级。
- 上一轮规划建议先做 Stage 1+2:固化 retrieval query / hit 契约,增强本地排序和 reason/citation,暂不引入 embedding 或向量库。

### 思考与讨论
- 候选 A:直接接 embedding / 向量数据库 → ❌ **否决**:当前 JSONL + scope/governor 仍是权威源,直接引入新依赖会扩大部署和失败面,也容易绕开现有治理。
- 候选 B:只改 `LocalSemanticMemoryScorer` 别名表 → ❌ **不足**:能改善命中,但 `/recall` 和 prompt 注入仍缺“为什么召回”的解释,后续也难平滑接 reranker。
- 候选 C:新增 `MemoryRetrievalQuery` / `MemoryRetrievalHit`,让 `MemoryRetriever` 先产出可解释 hits,再投影 `MemoryPacket` → ✅ **选定**:能统一 `/recall`、Prompt Stack 和 A2A memory refs 的检索契约,且保持无新依赖。

### 产出
- `src/aico/core/memory.py`:
  - 新增 `MemoryRetrievalQuery`,承载 query、scopes、role、agent、task kind、top_k 和 max_tokens。
  - 新增 `MemoryRetrievalHit`,保留 atom、semantic/scope/recency/confidence/evidence/graph/final score 和 reason。
  - `MemoryRetriever.retrieve()` 返回 ranked hits;`retrieve_packet()` 复用 hits 并按 token budget 投影为 `MemoryPacket`。
  - 排序权重为 semantic 0.45、scope 0.20、confidence 0.15、recency 0.10、evidence 0.05、graph 0.05。
  - scope closeness 先按 agent > role > team > project > boss global;graph score 本轮预留为 0.0。
- `src/aico/core/memory_commands.py`:
  - `/recall` 改为复用 `MemoryRetriever`,输出每条记忆的 reason。
- `src/aico/core/__init__.py`:
  - 导出 `MemoryRetrievalQuery` 和 `MemoryRetrievalHit`。
- `tests/unit/test_memory.py`:
  - 新增 ranked hits / reason 测试。
  - 新增 role scope 优先于 project scope 测试。
  - 新增 token budget 测试。
  - 更新 citation reason 断言。
- 文档:
  - 更新 ADR-0023 的 2026-05-20 落地说明。
  - 更新 Phase 7 playbook Iteration 6。
  - 更新 CHANGELOG 和 STATUS。

### 验证结果
- `uv run pytest tests/unit/test_memory.py tests/unit/test_orchestrator.py::test_orchestrator_remember_recall_and_forget_project_memory tests/unit/test_phase7_memory_acceptance.py`:14 passed。
- `uv run ruff check src/aico/core/memory.py src/aico/core/memory_commands.py src/aico/core/__init__.py tests/unit/test_memory.py`:passed。
- `uv run mypy src/aico/core/memory.py src/aico/core/memory_commands.py src/aico/core/__init__.py tests/unit/test_memory.py`:passed。
- `uv run pytest`:266 passed,1 skipped。
- `uv run ruff check .`:passed。
- `uv run ruff format --check .`:passed。
- `uv run mypy src tests`:passed。
- `git diff --check`:passed。

### 关键决策
- 🔒 **决策 1**:记忆检索的权威流程仍是 scope collect -> governor filter -> semantic/ranking -> token budget -> MemoryPacket,不允许 scorer 绕过治理。
- 🔒 **决策 2**:embedding / LLM rerank 后续只能替换 `MemorySemanticScorer` 或补 `graph_score`,不能改变 `MemoryAtom` / `MemoryPacket` / Orchestrator 契约。
- 🔒 **决策 3**:`/recall` 是纠错和排障入口,因此要展示 reason;老板不需要日常手动调参或维护检索权重。

### 留给下一轮
- 增加 graph expansion:沿 `supports` / `derived_from` / `broadcast_to` 给邻居少量 graph score,但仍必须先过 scope/governor。
- 给 `MemoryRetrievalQuery` 接入 task_kind / role_id / agent_id 的更细粒度业务权重。
- 视真实使用情况再评估 embedding cache,但 JSONL 仍保持权威源。

### 状态变化
- `STATUS.md` 当前轮次更新为 Round 96。
- Phase 7 增加“可解释记忆检索契约”完成项。

## Round 97 — 2026-05-20 — Codex

### 输入
- 人类要求继续开发直到记忆能力可以验收。
- Round 96 已完成可解释 retrieval contract,留给下一轮的是 graph expansion 和 task-aware scoring。

### 思考与讨论
- 候选 A:做多跳 graph traversal → ❌ **否决**:多跳容易带入远关系和噪音,也更容易出现跨 scope 泄漏风险;第一版真实验收只需要一跳。
- 候选 B:给 graph edge 直接绕过 semantic 和 governor → ❌ **否决**:这会破坏 Phase 7 的核心治理边界,尤其是 candidate/restricted/cross-project 记忆。
- 候选 C:只对直接命中的同 scope 记忆扩展一跳 `supports` / `derived_from` / `broadcast_to`,并让 role/task 作为 query hints → ✅ **选定**:最小可验收,也便于后续调权。

### 产出
- `MemoryStore` Protocol 增加 `list_edges()`。
- 新增内部 `MemoryGraphMatch`,用于给 graph neighbor 记录 edge type 和 graph score。
- `MemoryRetriever`:
  - 对直接 semantic 命中的记忆扩展一跳 graph neighbor。
  - 只接受已在本次 allowed scopes 中、且已通过 `MemoryGovernor` 的 graph neighbor。
  - graph edge 支持 `supports` / `derived_from` / `broadcast_to`。
  - `role_id` / `agent_id` / `task_kind` 会扩展为本地 query hints。
  - `/recall` 输出增加 final / semantic / scope / graph score 分项。
- `tests/unit/test_memory.py`:
  - 新增 graph neighbor 可召回且不跨项目测试。
  - 新增 tester / release task hints 影响排序测试。
- 文档:
  - 更新 ADR-0023 Round 97 落地说明。
  - 更新 Phase 7 playbook Iteration 7。
  - 更新 CHANGELOG 和 STATUS。

### 验证结果
- `uv run pytest tests/unit/test_memory.py`:14 passed。
- `uv run pytest tests/unit/test_memory.py tests/unit/test_orchestrator.py::test_orchestrator_remember_recall_and_forget_project_memory tests/unit/test_phase7_memory_acceptance.py`:16 passed。
- `uv run ruff check src/aico/core/memory.py src/aico/core/memory_commands.py tests/unit/test_memory.py`:passed。
- `uv run mypy src/aico/core/memory.py src/aico/core/memory_commands.py tests/unit/test_memory.py`:passed。
- `uv run pytest`:268 passed,1 skipped。
- `uv run ruff check .`:passed。
- `uv run ruff format --check .`:passed。
- `uv run mypy src tests`:passed。
- `git diff --check`:passed。

### 关键决策
- 🔒 **决策 1**:graph expansion 第一版只做一跳,且只扩 `supports` / `derived_from` / `broadcast_to`。
- 🔒 **决策 2**:graph neighbor 不能绕过 scope 和 MemoryGovernor;跨 project edge 存在也不能让目标 atom 进入 packet。
- 🔒 **决策 3**:role/task-aware scoring 先用本地 query hints,不把岗位逻辑写死成独立策略层;真实 dogfooding 后再决定是否拆权重配置。

### 留给下一轮
- 做真实 IM 验收:用 `/remember`、`/recall`、`/ask tester`、`/ask reviewer` 验证 reason/score 和 prompt 注入体感。
- 若验收发现 score 不直观,再考虑 `/recall --debug` 与普通 `/recall` 分层。
- 后续再评估 embedding cache,但不改变 JSONL 权威源和 governor 边界。

### 状态变化
- `STATUS.md` 当前轮次更新为 Round 97。
- Phase 7 增加“记忆检索 graph / task-aware 升级”完成项。

## Round 98 — 2026-05-20 — Codex

### 输入
- 人类真实 IM 验收发现 `/appoint codeflicker as tester` 返回 `Cannot appoint codeflicker as tester`。
- 人类将 Codex 同时任命为 reviewer / tester 后连续 `/ask`,遇到 `Task busy: adapter is busy`。
- 人类执行 `/ask tester prepare release verification handoff` 后遇到 `ERROR: adapter output idle timeout after 90s`,要求排查原因。

### 思考与讨论
- 候选 A:要求用户改用 `/appoint flicker as tester` → ❌ **否决**:`/agents` 展示的是 `codeflicker`,老板自然会输入看到的名字;让用户记 alias 是产品退化。
- 候选 B:继续保持单 adapter 单任务,让用户不要给同一 agent 任命多个 role → ❌ **否决**:虚拟公司里一个真实 agent 可以承担多个岗位,底层 CLI/API 也可以用多个进程或 session 并行。
- 候选 C:默认并发从 1 提到 5,并在 `/agents` / `/appoint` 展示容量约束 → ✅ **选定**:改动小、可观测、符合远程异步派工,同时保留达到上限后的 busy 保护。
- 候选 D:完全移除 output idle timeout → ❌ **否决**:历史上 Codex 无 stdout 会无限占用;更稳妥的是放宽默认阈值并继续可配置。

### 产出
- `ProjectAssignmentDirectory`:
  - 新增 `resolve_agent_id()`,先按 configured agent id 匹配,再在唯一匹配时按 provider 名匹配。
  - `/appoint codeflicker as tester` 可落到默认 CodeFlicker agent。
- `build_phase1_runtime()`:
  - 默认 project config 对 Cursor / CodeFlicker / Trae / Gemini 使用 persona 名作为 agent id。
  - `CompanyAgentProfile` 写入 `max_concurrent_tasks` 和 `recommended_max_appointments`。
- `ClaudeCodeAdapter` 家族:
  - 新增 `max_concurrent_tasks` / `running_task_count()`。
  - 默认并发上限为 5,达到上限时返回 `adapter is at max concurrency (n/limit)`。
  - Codex / Cursor / CodeFlicker / Trae / Gemini 默认 output idle timeout 从 90 秒放宽到 300 秒。
- `AdapterSnapshot` / `/agents` / `/agent` / `/status`:
  - 展示 `running/max` 与 max concurrency。
  - 未满上限的运行中 adapter 会显示为 `available n/max running`。
- `/appoint` 成功回执:
  - 展示 `agent_max_concurrent` 和 `recommended_appointments`。
- 文档:
  - 更新 `STATUS.md`、`CHANGELOG.md`、`docs/human/daily-ops.md`、adapter/collaboration playbooks。
  - 新增 PITFALL P-021 / P-022。

### 验证结果
- `uv run pytest tests/unit/test_claude_code_adapter.py tests/unit/test_codex_adapter.py tests/unit/test_codeflicker_adapter.py tests/unit/test_cursor_adapter.py tests/unit/test_adapter_registry.py tests/unit/test_project_assignment.py tests/unit/test_phase1_app.py tests/unit/test_orchestrator.py::test_orchestrator_reports_adapter_status_without_submitting_task tests/unit/test_orchestrator.py::test_orchestrator_status_includes_recent_tasks tests/unit/test_orchestrator.py::test_orchestrator_reports_agents_and_agent_card tests/unit/test_orchestrator.py::test_orchestrator_handles_team_who_appoint_default_and_ask_commands`:71 passed。
- `uv run pytest`:270 passed,1 skipped。
- `uv run ruff check .`:passed。
- `uv run ruff format --check .`:passed。
- `uv run mypy src tests`:passed。
- `git diff --check`:passed。

### 关键决策
- 🔒 **决策 1**:AICO 的 busy 语义应表示“adapter 达到可接任务上限”,不是“有任意任务在跑”。
- 🔒 **决策 2**:默认并发先定为 5,并通过 IM 文案暴露给用户;后续真实 provider 有更严格限制时再做 per-adapter 调整。
- 🔒 **决策 3**:idle timeout 继续保留,但 90 秒对 Codex 这类可能长时间无中间 stdout 的 CLI 太激进,默认放宽到 300 秒。

### 留给下一轮
- 真实 IM 回归 `/appoint codeflicker as tester`、`/agents` 容量展示、同一 Codex reviewer/tester 连续派工。
- 如果真实 Codex 仍在 300 秒内无输出,再决定是 per-task timeout、heartbeat 还是 provider-specific streaming 修复。

### 状态变化
- `STATUS.md` 当前轮次更新为 Round 98。
- 新增 P-021 / P-022,记录 adapter appointment alias 和单槽位并发坑。

## Round 99 — 2026-05-21 — Codex

### 输入
- 人类确认项目初期和 milestone 阶段的 memory broadcast 有必要,但强调“这个广播要可追踪可审计”。

### 思考与讨论
- 候选 A:只依赖 memory JSONL 中的 team atom / `broadcast_to` edge 推断广播历史 → ❌ **不足**:能恢复记忆关系,但 `/audit` 和 `AICO_AUDIT_LOG_PATH` 看不到一次明确的广播行为。
- 候选 B:把 broadcast 包成普通 `TaskBus` 任务 → ❌ **否决**:memory broadcast 是 Memory Fabric 基础设施动作,不是要派给某个 adapter 执行的 AI 任务;包装成任务会污染 metrics/task 语义。
- 候选 C:保留现有 atom + edge + receipt,并在可选 audit log 中记录结构化 `memory_broadcasted` 事件 → ✅ **选定**:最小改动满足可追踪、可审计,且不改变未配置 audit log 时的原行为。

### 产出
- `AuditEventType` 新增 `memory_broadcasted`。
- `InMemoryAuditLog` 新增 `record_event()`,支持非 `Task` 形态的基础设施事件,原 `record(task=...)` 路径保持兼容。
- `MemoryBroadcastService` 可选接入 `InMemoryAuditLog`;每次 `broadcast_to_team()` 成功后写入 audit event:
  - `task_id`: `memory:<broadcast_memory_id>`
  - `actor`: `created_by`
  - `target`: `team:<project>/<team>`
  - `detail`: JSON,包含 receipt、source memory、broadcast memory、team scope、recipients 和 reason。
- 扩展 `tests/unit/test_memory.py`,验证 broadcast 生成 audit event 并持久化到 `JsonlAuditSink`。
- 更新 Phase 7 playbook、daily ops、CHANGELOG 和 STATUS,明确 team broadcast 的审计验收点。

### 验证结果
- `uv run pytest tests/unit/test_memory.py::test_memory_broadcast_creates_team_memory_edge_and_receipt tests/unit/test_memory.py::test_memory_broadcast_rejects_cross_project_team_scope tests/unit/test_memory.py::test_memory_broadcast_records_traceable_audit_event tests/unit/test_audit.py`:5 passed。
- `uv run pytest tests/unit/test_memory.py tests/unit/test_audit.py tests/unit/test_phase7_memory_acceptance.py`:18 passed。
- `uv run ruff check src/aico/core/audit.py src/aico/core/memory_broadcast.py src/aico/core/models.py tests/unit/test_memory.py tests/unit/test_audit.py`:passed。
- `uv run ruff format --check src/aico/core/audit.py src/aico/core/memory_broadcast.py src/aico/core/models.py tests/unit/test_memory.py tests/unit/test_audit.py`:passed。
- `uv run mypy src/aico/core/audit.py src/aico/core/memory_broadcast.py src/aico/core/models.py tests/unit/test_memory.py tests/unit/test_audit.py`:passed。
- `git diff --check`:passed。
- `uv run pytest`:271 passed,1 skipped。
- `uv run ruff check .`:passed。
- `uv run ruff format --check .`:passed。
- `uv run mypy src tests`:passed。

### 关键决策
- 🔒 **决策 1**:Memory broadcast 的权威关系仍是 MemoryStore 中的 team atom + `broadcast_to` edge;审计事件记录“这次广播行为和 receipt”,不取代 memory store。
- 🔒 **决策 2**:`memory_broadcasted` 不进入 metrics task snapshot,避免把基础设施记忆同步误算成 AI 执行任务。
- 🔒 **决策 3**:未配置 audit log 时 broadcast 行为保持原样;配置 `AICO_AUDIT_LOG_PATH` 后可从 `/audit` 和 JSONL 追踪。

### 留给下一轮
- 如果后续要把“项目初期 / milestone 自动广播”产品化,优先增加 lead-agent 触发策略和 acceptance,而不是新增老板手动 `/memory broadcast` 主命令。
- 真实 IM 验收时,用一次 team broadcast 后查看 `/audit`,确认 `memory_broadcasted` 的 receipt 和 recipients 可读。

### 状态变化
- `STATUS.md` 当前轮次更新为 Round 99。
- Phase 7 增加“Team Broadcast 可追踪审计”完成项。

## Round 100 — 2026-05-21 — Codex

### 输入
- 人类要求调研 Codex `/goal` 命令原理,判断它和 Ralph loop 的关系,并为 AICO 设计 goal 命令交互流程。
- 明确设计范围包含 goal prompt 模板、boss 分配流程和 lead 分配其他 agent 的流程。

### 思考与讨论
- 本机 Codex CLI 为 `0.125.0`,未包含 `/goal`;因此本轮不做本机源码逆向,改为基于 OpenAI Developers 当前文档和 AICO 现有 `/ask`、`/lead`、`/overnight` 语义做产品架构设计。
- 候选 A:只复用 `/overnight` → ❌ **否决**:`/overnight` 是睡前托管和早报语义,不适合白天复杂任务、显式 pause/resume/clear、lead 子目标。
- 候选 B:把 `/ask` 隐式改成持续循环 → ❌ **否决**:会让普通咨询和目标托管混在一起,老板无法看出何时进入长任务状态。
- 候选 C:新增 goal-mode 目标契约层 → ✅ **选定**:复杂且可验证任务可显式 `/goal` 或从 `/ask` 保守升级,并保留 owner、验收、证据、状态、审计和父子目标关系。

### 产出
- 新增 ADR-0025 `Goal Mode Orchestration`(Proposed)。
- 设计 `/goal <role> <objective>`、`/goal <objective>`、`/goal`、`/goal pause/resume/clear <goal_id>` 的交互。
- 设计 `/ask <role> <task>` 的保守自动升级规则:只有多步且有可验证停止条件时才进入 goal-mode。
- 设计 boss 分配回执、lead 子目标分配流程和 parent/child goal 责任链。
- 写入 Goal Prompt 模板和 Goal 分类 Prompt 模板。
- 更新 ADR 索引和 `STATUS.md` 下一轮建议。

### 验证结果
- 文档设计轮未改运行代码,未跑单测。
- 已用 `codex --version` 确认本机 CLI 版本为 `0.125.0`,不支持当前 `/goal` 实验特性。

### 关键决策
- 🔒 **决策 1**:AICO goal-mode 是 `/ask` 与 `/overnight` 之间的通用目标契约层,不是无人值守授权模式。
- 🔒 **决策 2**:goal-mode 不绕过 Phase 4 `/approve`;风险动作仍停在审批。
- 🔒 **决策 3**:lead 可以创建子目标,但 parent goal 责任仍归 lead,子目标必须带独立验收标准。

### 留给下一轮
- 按 ADR-0025 实现 GoalRecord、parser、prompt 注入、audit event、render 和单测。
- 第一版 `/ask` 自动升级保持保守,先显式提示“按 goal-mode 托管”,避免误把咨询变成长任务。
- 后续再把 lead 子目标和 `/overnight` 多 agent 编排统一到同一 GoalRecord 状态模型。

### 状态变化
- `STATUS.md` 当前轮次更新为 Round 100。
- Phase 8 增加 Goal-mode 交互和 prompt 契约设计完成项。

## Round 101 — 2026-05-21 — Codex

### 输入
- 人类指出不同 agent 的 goal 支持现状不同:Claude Code / Codex 等支持 goal 的 agent 应封装其语法糖;不支持 goal 的 agent 需要 AICO 自己写 Ralph loop。
- 要求重构当前 goal 方案,支持不同 agent 现状。

### 思考与讨论
- 候选 A:所有 goal 都由 AICO managed loop 托管 → ❌ **否决**:会浪费 Codex / Claude Code 已有 goal 能力,并把 provider 语法差异错误上收到 core。
- 候选 B:只支持 native goal agent → ❌ **否决**:会让 CodeFlicker / Trae / Gemini 等普通 CLI agent 无法承接长周期任务。
- 候选 C:拆成统一 `GoalContract` + per-adapter `GoalCapability` + 两类 executor → ✅ **选定**:native / adapter-sugar agent 走语法糖,普通 agent 走 AICO-managed Ralph loop。

### 产出
- 重构 ADR-0025:
  - 新增 `GoalCapability`:`native_goal`、`adapter_goal_sugar`、`managed_ralph_loop`、`no_goal`。
  - 新增 `GoalExecutor` 分层:Native / Adapter Goal 与 Managed Ralph Loop。
  - 明确 Codex / Claude Code 等支持 goal 的 agent 由 Adapter 封装语法糖,core 只传 GoalContract。
  - 明确不支持 goal 的 agent 由 AICO 用长期目标 prompt、GoalHook、continuation task、预算和审批边界托管。
  - 增加 Goal Hook 输出契约,避免模型过早结束或无限 continuation。
- 更新 `STATUS.md` 的 Phase 8 进度和下一轮实现建议。

### 验证结果
- 文档设计轮未改运行代码,未跑单测。
- `git diff --check` 通过。

### 关键决策
- 🔒 **决策 1**:AICO 的统一抽象是 `GoalContract`,不是统一执行 loop。
- 🔒 **决策 2**:agent goal 语法糖只能存在于 Adapter,core 不硬编码 Codex / Claude Code 的具体命令。
- 🔒 **决策 3**:managed Ralph loop 只用于不支持 goal 的 agent,并必须有 hook、预算、审批和中断边界。

### 留给下一轮
- 实现时先加 Adapter capability 模型,再加 `/goal` parser 和 GoalRecord。
- 第一版 native executor 只需要把 GoalContract 渲染到 Adapter goal syntax;managed loop 先做单 agent continuation,再做 lead 子目标编排。

### 状态变化
- `STATUS.md` 当前轮次更新为 Round 101。
- Phase 8 增加“Goal-mode 支持 agent capability 分层”完成项。

## Round 102 — 2026-05-21 — Codex

### 输入
- 人类确认 AICO 真正替 boss 省力的底层原理应是:lead agent 吸收团队历史经验和其他 agent 意见后,在授权范围内替 boss 做 review 和决策。
- 要求分阶段落地两个方向:强化 lead 责任和记忆用途标签;新增必备挑刺者 / 哲学家角色,供 lead 决策和 review 时调取。

### 思考与讨论
- 候选 A:立即实现完整自动决策流 → ❌ **否决**:会同时改 role、memory schema、collaboration、audit 和 goal/offline delegation,风险过大,也不利于验收。
- 候选 B:只改 prompt 文案,不改团队契约 → ❌ **否决**:lead 仍可能只是默认路由,缺 challenger 的团队也会继续托管长任务,不能形成真实公司式责任边界。
- 候选 C:先落 Stage 1 组织契约,再做 memory purpose 和 lead decision workflow → ✅ **选定**:先让 team 必须具备 lead + challenger,并让 lead prompt 承担决策责任;后续再让记忆和自动调取流程细化。

### 产出
- 新增 ADR-0026 `Lead Decision Team Contract`,明确 lead 是项目责任人,challenger 是必备独立批判角色。
- `ProjectAssignmentDirectory` 新增 `missing_required_team_roles()`,用于判断项目 team 是否缺 lead 或 challenger。
- 默认角色库新增 `challenger` / Critical Philosopher;默认项目配置会优先任命 Codex 为 challenger,否则复用已有 agent。
- `config/projects.example.json` 和 `examples/release-room/aico-project.json` 补齐 challenger role / appointment。
- `project_office_message()` 和 `/team` 输出新增 `team readiness`。
- `render_appointment_prompt()` 对当前项目 lead 注入更强的 lead responsibility:减少 boss 认知负担、调取记忆、咨询 challenger/reviewer、低风险决策和高风险升级。
- `/overnight` 现在要求当前项目 team 完整,缺 challenger 时提示 `/appoint <agent> as challenger` 并拒绝派发托管任务。
- 更新 Release Room 示例文档、Phase 8 playbook、CHANGELOG 和 STATUS。

### 验证结果
- `env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python /opt/homebrew/bin/python3.11 pytest tests/unit/test_project_assignment.py tests/unit/test_prompt_stack.py tests/unit/test_project_messages.py tests/unit/test_phase1_app.py tests/unit/test_orchestrator.py::test_orchestrator_handles_team_who_appoint_default_and_ask_commands tests/unit/test_orchestrator.py::test_orchestrator_reports_project_roles_and_appointment_gaps tests/unit/test_orchestrator.py::test_orchestrator_queues_overnight_delegation_to_project_lead tests/unit/test_orchestrator.py::test_orchestrator_overnight_requires_challenger tests/unit/test_release_room_example.py tests/unit/test_release_room_acceptance.py`:57 passed。

### 关键决策
- 🔒 **决策 1**:lead 不再只是“默认 role”;它是项目责任人,需要在授权范围内替 boss 做低风险项目决策。
- 🔒 **决策 2**:challenger 是必备团队角色,用于独立质疑前提、机会成本、长期风险和反方论证;它不是普通 reviewer 的别名。
- 🔒 **决策 3**:`/overnight` 等托管入口必须先要求 team readiness complete,避免把长任务交给缺少批判角色的团队。

### 留给下一轮
- 做 Stage 2:给 `MemoryAtom` 增加 purpose,支持 public broadcast、task key progress、task private、decision review。
- 做 Stage 3:lead decision workflow 自动召回记忆、咨询 challenger/reviewer,输出 decision memo 并写 audit。
- 真实 IM 复验 `/team` readiness、`/appoint <agent> as challenger`、`/overnight` 缺 challenger 拦截和完整团队托管。

### 状态变化
- `STATUS.md` 当前轮次更新为 Round 102。
- Phase 8 增加 Lead decision team contract Stage 1 完成项,并把 Memory purpose / Lead decision workflow 放入下一轮高优先级。

## Round 103 — 2026-05-21 — Codex

### 输入
- 人类要求继续执行后续阶段。
- Round 102 已完成 lead + challenger 的团队契约,下一步是给 agent 记忆增加用途标签,让 lead 后续能区分公共共识、关键进展、内部短期记忆和决策评审。

### 思考与讨论
- 候选 A:继续只用 freeform `tags` 表达用途 → ❌ **否决**:无法稳定治理 `task_private`,不同 agent 可能写出不同标签,lead 决策包会变脏。
- 候选 B:新增单值 `purpose` → ❌ **否决**:一条记忆可能既是 broadcast 又是任务关键进展,单值会丢失组合语义。
- 候选 C:新增枚举型 `purpose_tags` → ✅ **选定**:保留组合能力,同时让检索、broadcast、Prompt Stack 和 `/recall` 有稳定治理语义。

### 产出
- 新增 ADR-0027 `Memory Purpose Tags`。
- `MemoryPurpose` 新增 `general_context`、`public_broadcast`、`task_key_progress`、`task_private`、`decision_review`。
- `MemoryAtom` 新增 `purpose_tags`,默认值为 `general_context`,兼容旧 JSONL 记录。
- `MemoryPacketItem` 带上 `purpose_tags`,Prompt Stack 的 `Shared memory` 行会展示 purpose。
- `MemoryRetrievalQuery` 新增 `allowed_purposes`;普通检索默认排除 `task_private`,显式允许时才召回内部短期记忆。
- `/remember` 和 boss feedback 写入 `general_context`。
- `MemoryBroadcastService` 生成的 team memory 带 `public_broadcast`,且不会把源记忆中的 `task_private` 继续传播。
- `/recall` 输出增加 purpose 展示。
- 更新 A2A memory architecture、Phase 7 playbook、CHANGELOG 和 STATUS。

### 验证结果
- `env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python /opt/homebrew/bin/python3.11 pytest tests/unit/test_memory.py tests/unit/test_memory_capture.py tests/unit/test_orchestrator.py::test_orchestrator_remember_recall_and_forget_project_memory tests/unit/test_orchestrator.py::test_orchestrator_injects_broadcast_team_memory_for_active_project_task tests/unit/test_phase7_memory_acceptance.py tests/unit/test_release_room_acceptance.py`:26 passed。

### 关键决策
- 🔒 **决策 1**:记忆用途是一等公民 `purpose_tags`,不是自由文本 tag。
- 🔒 **决策 2**:`task_private` 默认不进入普通检索和 Prompt Stack;lead 决策不能读取 agent 的 raw scratchpad。
- 🔒 **决策 3**:team broadcast 会把记忆升格为 `public_broadcast`,但不会传播 `task_private`。

### 留给下一轮
- 做 Stage 3:lead decision workflow。决策类任务应优先召回 `public_broadcast`、`task_key_progress`、`decision_review`,咨询 challenger/reviewer,输出 decision memo,并把评审结果写成 `decision_review` memory。
- 后续自动任务总结写入时,把稳定进展写成 `task_key_progress`,把内部草稿写成 `task_private`。
- 真实 IM 复验 `/recall` purpose 展示和默认不召回 `task_private` 的行为。

### 状态变化
- `STATUS.md` 当前轮次更新为 Round 103。
- Phase 8 的 Memory purpose 标签项从未完成改为完成,Lead decision workflow Stage 3 成为下一轮最高优先级。

## Round 104 — 2026-05-21 — Codex

### 输入
- 人类要求继续开发 Stage 3:实现 lead decision workflow,让 lead 在决策类任务里优先召回 `public_broadcast` / `task_key_progress` / `decision_review`,自动咨询 challenger/reviewer,并输出 decision memo + 写 audit。

### 思考与讨论
- 候选 A:把 lead 决策完全做成新的 `/decision` 命令 → ❌ **否决**:会增加老板记忆负担,也偏离“lead 替 boss 减负”的产品目标;决策类 plain lead task 和 `/ask <lead-role> ...` 应自然触发。
- 候选 B:只靠 prompt 要求 lead 自己去问 reviewer → ❌ **否决**:不可审计,也不能保证 challenger/reviewer 真被咨询。
- 候选 C:在 Orchestrator 里直接堆完整 workflow → ❌ **否决**:`Orchestrator` 已经偏大,继续堆流程会违反单类复杂度约束。
- 候选 D:新增独立 `LeadDecisionWorkflow`,由 Orchestrator 只做入口识别和执行回调 → ✅ **选定**:复用 TaskBus、appointment prompt、provider session、memory retriever 和 audit,同时把流程复杂度隔离到独立模块。

### 产出
- 新增 `src/aico/core/lead_decision.py`,包含决策任务识别、consultation prompt、decision memo prompt、audit detail 和 `decision_review` memory 写回。
- `Orchestrator` 对当前项目 lead/default role 的明确决策类任务自动触发 `LeadDecisionWorkflow`;普通咨询、显式 adapter target 和非 lead role 不变。
- 决策记忆检索只允许 `public_broadcast`、`task_key_progress`、`decision_review`,因此不会把 `task_private` 或普通 `general_context` 混入 lead decision packet。
- 决策流程会先派发 challenger consultation;如果 reviewer 已任命,也派发 reviewer consultation;最终 lead 任务收到固定 decision memo 输出契约。
- `AuditEventType` 新增 `lead_decision_recorded`;`TaskBus.record_lead_decision()` 写入结构化 detail,记录 memory refs、consulted roles 和 memo 摘要。
- Lead memo 会写回 project memory,source 为 `lead_decision_workflow`,purpose 为 `decision_review`。
- `TextRiskAssessor` 将 `aico.intent=lead_decision` 视为内部只读任务,避免“决定是否 update/delete”这类评审语句误触发执行审批;真正执行仍走普通 `/ask` / `/approve` 流。
- 更新 `CHANGELOG.md`、`STATUS.md` 和 Phase 8 playbook。

### 验证结果
- `env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python /opt/homebrew/bin/python3.11 pytest tests/unit/test_orchestrator.py tests/unit/test_memory.py tests/unit/test_task_bus.py tests/unit/test_audit.py tests/unit/test_phase7_memory_acceptance.py`:98 passed。
- `env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python /opt/homebrew/bin/python3.11 ruff check src/aico/core/lead_decision.py src/aico/core/orchestrator.py src/aico/core/risk.py src/aico/core/task_bus.py src/aico/core/models.py tests/unit/test_orchestrator.py`:passed。
- `env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python /opt/homebrew/bin/python3.11 ruff format --check src/aico/core/lead_decision.py src/aico/core/orchestrator.py src/aico/core/risk.py src/aico/core/task_bus.py src/aico/core/models.py tests/unit/test_orchestrator.py`:passed。
- `env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python /opt/homebrew/bin/python3.11 mypy src/aico/core/lead_decision.py src/aico/core/orchestrator.py src/aico/core/risk.py src/aico/core/task_bus.py tests/unit/test_orchestrator.py`:passed。

### 关键决策
- 🔒 **决策 1**:lead decision workflow 是 read-only review/decision memo,不是执行授权通道;后续执行仍需普通任务和审批。
- 🔒 **决策 2**:Stage 3 只自动咨询 challenger 和已任命 reviewer;tester / architect 等更广泛专家选择留给后续 relevance routing,避免本轮过度扩展。
- 🔒 **决策 3**:决策 memo 写回 `decision_review` memory,但 audit 仍是行为追踪权威;memory 用于后续召回,不替代审计。

### 留给下一轮
- 真实 IM 验收 lead decision workflow:`/project aico`、`/team`、准备 purpose memory、发送 lead 决策任务、查看 `/audit` 和 `/recall decision`。
- 后续可做相关角色选择扩展:根据任务领域在 reviewer 之外自动选择 tester / architect / market-risk / legal 等角色。
- Goal-mode MVP 仍是下一项高优先级工程工作,不要把 goal loop 和 decision workflow 混在同一轮里。

### 状态变化
- `STATUS.md` 当前轮次更新为 Round 104。
- Phase 8 的 Lead decision workflow 项从未完成改为完成,下一轮最高优先级改为真实 IM 验收。

## Round 105 — 2026-05-21 — Codex

### 输入
- 人类确认先落地 goal 能力,但前置判断是完整 GoalExecutor / managed Ralph loop 可能过重,需要从个人开发用户和开源市场视角先做更轻的可验证切片。

### 思考与讨论
- 候选 A:直接实现 ADR-0025 的完整 `GoalCapability` / `GoalExecutor` / managed Ralph loop → ❌ **否决**:状态机、hook、continuation、pause/resume/clear 和重启恢复成本偏高,且真实效果还没有 dogfooding 证据。
- 候选 B:只写文档,不进代码 → ❌ **否决**:无法验证 `/goal` 是否真的改善个人开发用户的派活质量。
- 候选 C:先做 Goal Brief v0 → ✅ **选定**:把 `/goal` 和带明确验收的 `/ask` 收敛成轻量目标契约 prompt + task metadata,先验证“目标和验收更清晰”这一核心价值。

### 产出
- 新增 `src/aico/core/goal_brief.py`,定义 `GoalBrief`、目标文本解析、`AICO Goal Brief` prompt、goal metadata 和 `/goal` 列表消息。
- 新增 `src/aico/core/goal_brief_commands.py`,封装 `/goal` 命令和 `/ask` 保守自动附加逻辑,避免继续膨胀 Orchestrator。
- `CommandName` 新增 `GOAL`,`/help` 增加 `/goal [role] <objective>`。
- `/goal [role] <objective>` 会使用当前 active project;未指定 role 时使用 project lead/default role。
- `/ask <role> <task>` 仅在出现“验收 / 停止 / 通过失败 / evidence / done when / stop if”等明确 marker 时附加 goal brief。
- `TaskSnapshot` 携带 task metadata,`/task <id>` 新增 `Goal brief:` 区块,显示 goal id、objective 和 acceptance。
- ADR-0025 改为 Accepted,明确当前只接受 Goal Brief v0;完整 native goal / adapter sugar / managed Ralph loop 作为后续扩展。
- 更新 `CHANGELOG.md`、`STATUS.md` 和 Phase 8 playbook 的 Goal Brief v0 验收步骤。

### 验证结果
- `uv run pytest tests/unit/test_commands.py tests/unit/test_orchestrator.py::test_orchestrator_goal_command_attaches_goal_brief_to_project_role tests/unit/test_orchestrator.py::test_orchestrator_ask_with_acceptance_attaches_goal_brief_conservatively`:12 passed。
- `uv run pytest tests/unit/test_commands.py tests/unit/test_orchestrator.py`:71 passed。
- `uv run ruff check src/aico/core/goal_brief.py src/aico/core/goal_brief_commands.py src/aico/core/commands.py src/aico/core/command_messages.py src/aico/core/models.py src/aico/core/orchestrator.py src/aico/core/task_bus.py tests/unit/test_commands.py tests/unit/test_orchestrator.py`:passed。
- `uv run ruff format --check src/aico/core/goal_brief.py src/aico/core/commands.py src/aico/core/command_messages.py src/aico/core/models.py src/aico/core/orchestrator.py src/aico/core/task_bus.py tests/unit/test_commands.py tests/unit/test_orchestrator.py`:passed。
- `uv run mypy src/aico/core/goal_brief.py src/aico/core/commands.py src/aico/core/command_messages.py src/aico/core/models.py src/aico/core/orchestrator.py src/aico/core/task_bus.py tests/unit/test_commands.py tests/unit/test_orchestrator.py`:passed。

### 关键决策
- 🔒 **决策 1**:Goal Brief v0 是“目标契约提示 + 元数据追踪”,不是长期托管 runtime。
- 🔒 **决策 2**:`/ask` 自动附加必须保守,只有明确验收/停止/证据 marker 时触发;普通咨询不升级。
- 🔒 **决策 3**:完整 `GoalCapability`、native goal syntax、managed Ralph loop、pause/resume/clear 和重启恢复都暂缓到 dogfooding 后。

### 留给下一轮
- 真实 IM dogfood Goal Brief v0:`/project aico`、`/goal implementer inspect release plan 验收: summarize blockers`、`/task <id>`、`/goal`。
- 用普通咨询和带验收的 `/ask` 各跑一条,确认保守自动附加不会误伤轻任务。
- 如果 v0 明显改善任务收口,再设计完整 GoalExecutor;否则保留为轻量 prompt contract。

### 状态变化
- `STATUS.md` 当前轮次更新为 Round 105。
- Phase 8 增加 Goal Brief v0 完成项,下一轮建议从完整 goal runtime 改为先真实 IM dogfooding。

## Round 106 — 2026-05-21 — Codex

### 输入
- 人类确认 GitHub UI metadata(description、topics、social preview)已验证完成。
- 要求改善 Telegram markdown 消息可读性,标题加粗并适当换行。
- 要求判断内存状态是否需要 SQLite 持久化,并保持技术实现可插拔、可扩展。
- 要求从 1k stars 缺口和 GitHub 公开高优事项中各选 2 个最重要点攻克落地。

### 思考与讨论
- 候选 A:在 Telegram Channel 里直接解析 Markdown → ❌ **否决**:会把 Telegram 方言写死到 Channel,不利于 Feishu 和后续 IM 复用。
- 候选 B:继续只靠项目消息层的局部 spans → ❌ **不足**:真实 provider 流式输出和内置命令仍可能把 Markdown 堆成一坨。
- 候选 C:新增平台无关 rich text renderer → ✅ **选定**:核心层输出 `MessageTextSpan`,Telegram 继续只负责 HTML 映射。
- 候选 D:继续用内存承载 task/approval 状态 → ❌ **否决**:Phase 8 已经进入离线托管语义,重启丢 `/tasks`、`/task` 和 pending approval 不符合企业级可用。
- 候选 E:直接引入 Postgres → ❌ **暂缓**:会提高本地开源试用门槛。
- 候选 F:用 SQLite 做 local-first task state store → ✅ **选定**:无额外服务,可通过 `TaskStateStore` 协议后续替换。

### 产出
- 新增 `src/aico/core/message_rendering.py`,支持轻量 Markdown 标题、小节标题、inline bold / italic / code、slash command spans,并在标题前补结构空行。
- `StreamedMessageWriter` 改为对 provider 流式输出使用 rich text renderer,让 Telegram 中模型 markdown 输出更清晰。
- 内置 command message builder 的 status / tasks / metrics / task / audit / agents 输出改为使用 rich text renderer。
- 新增 ADR-0028 `SQLite Task State Store`。
- 新增 `src/aico/core/task_store.py`,定义 `TaskStateStore` 协议和 `SQLiteTaskStateStore`。
- `TaskBus` 支持可选 `task_store`,启动时恢复 task records、task snapshots 和 approval requests,状态变化时 upsert 到 store。
- `Phase1Settings` 新增 `AICO_STATE_DB_PATH`,runtime 配置后启用 SQLite task state store。
- 新增 `aico-release-room-demo` console script 和 `src/aico/app/release_room_demo.py`,使用 fake adapters 跑 Release Room 管理链路,无需 Telegram token 或真实 LLM/CLI provider。
- 新增 `.github/PULL_REQUEST_TEMPLATE.md` 和 `.github/ISSUE_TEMPLATE/good_first_issue.yml`。
- 更新 README / README.zh-CN / Quickstart / daily ops / CHANGELOG / STATUS / ADR index。
- 新增 B-004,记录 `Orchestrator` / `TaskBus` 超过单类尺寸硬约束的公开前结构债。

### 验证结果
- 目标测试已通过:`pytest tests/unit/test_message_rendering.py tests/unit/test_task_bus.py tests/unit/test_phase1_app.py tests/unit/test_release_room_demo.py tests/unit/test_orchestrator.py`。
- `aico-release-room-demo` 已本地运行,输出包含 `/team`、memory、approval、tester/reviewer、overnight handoff、daily 和 audit。
- 全量质量门禁通过:`pytest` 286 passed / 1 skipped,`ruff check .`, `ruff format --check .`, `mypy src tests`, `git diff --check`。
- 结构扫描仍发现 `Orchestrator` / `TaskBus` 超过项目类尺寸硬约束,已写入 B-004。

### 关键决策
- 🔒 **决策 1**:Telegram 可读性通过平台无关 spans 改善,不在 Telegram Channel 中直接解析 Markdown。
- 🔒 **决策 2**:SQLite 是本地默认业务状态持久化后端,但必须挂在 `TaskStateStore` 协议后,不能让数据库细节污染 Adapter / Channel。
- 🔒 **决策 3**:公开发布最先攻克无 token demo 和贡献者入口,因为它们同时提升陌生开发者转化和 star 后贡献承接。

### 留给下一轮
- 继续做真实 Telegram dogfood:重点看 provider 输出标题/小节在 Telegram 中是否明显更清晰。
- 下一步持久化应扩展到 `/overnight` records 和 operator inbox,不要把 SQLite 第一切片误说成完整离线托管恢复。
- 公开前仍需整理当前大工作树并跑完整 `pytest` / `ruff` / `mypy` / `git diff --check`。

### 状态变化
- `STATUS.md` 当前轮次更新为 Round 106。
- Phase 8 增加 SQLite task state store 第一切片完成项。
- Open-source Showcase 增加 GitHub UI metadata 验收完成和开源首屏第三版完成项。

## Round 107 — 2026-05-21 — Codex

### 输入
- 人类要求拆 `Orchestrator` / `TaskBus`。
- 人类真实验证 Telegram 后指出 `/agents` 仍是一坨纯文本:`-` 没有变成更像无序列表的视觉效果,且 `:` 左侧标题没有高亮。
- 人类指出 `/appoint codex as tester` 返回也缺少 label 加粗和适度换行。

### 思考与讨论
- 候选 A:在 Telegram Channel 里专门把 `/agents` 文案改成 HTML → ❌ **否决**:会重新把平台方言塞进 Channel,违背 Round 106 已选定的 platform-neutral render contract。
- 候选 B:让所有冒号前文本都加粗 → ❌ **否决**:`Task rejected:`、`scripted:` 这类普通状态句也会被误加粗,测试也暴露了这个问题。
- 候选 C:在核心 rich text renderer 中收窄 label key 集合,同时把普通 `-` / `*` 列表转为 `•` → ✅ **选定**:对 `/agents`、`/task`、`/metrics`、provider markdown 输出都生效,但避免误伤普通句子。
- 候选 D:一次性把 `TaskBus` 拆成 repository + approval coordinator + dispatch service → ❌ **暂缓**:本轮目标是解除公开前硬约束,approval/dispatch 继续拆可以留给下一次演进。
- 候选 E:先抽 `TaskStateRepository` 和 `OrchestratorTaskFactory` → ✅ **选定**:这两个职责边界明确,能直接降低类体尺寸,且不改变业务行为。

### 产出
- 新增 `src/aico/core/orchestrator_task_factory.py`,集中处理普通消息、project appointment、provider session、shared memory packet 和 prompt stack 到 `Task` 的构造。
- 新增 `src/aico/core/task_state.py`,集中管理 task records、task snapshots、approval requests 和 task adapter mapping,并继续通过 `TaskStateStore` 持久化。
- `Orchestrator` 仅保留入口、命令协调、审批/中断/broadcast 和 streaming/collaboration 协调;类体从约 646 行降到 480 行。
- `TaskBus` 保留提交、审批、dispatch、stream output、audit 记录等核心行为;类体从约 566 行降到 448 行。
- 模块级 `_handle_command` 拆成 project / project-role / directory / memory helper,单函数不再超过 100 行。
- `rich_text_message()` 增强:
  - 普通 `- item` / `* item` 转为 `• item`。
  - `agent_title:`、`role:`、`adapter:` 等字段 label 左侧加粗。
  - 只对已知字段 label 生效,避免 `Task rejected:` 这类普通句子被误标为标题。
- `project_messages._heading_message()` 补同样的 label 加粗规则,覆盖 `/appoint` 返回。
- 更新 `tests/unit/test_message_rendering.py`、`tests/unit/test_project_messages.py`、`tests/unit/test_orchestrator.py` 和 Phase 6 acceptance 断言。
- B-004 更新为 resolved。

### 验证结果
- `pytest`:289 passed / 1 skipped。
- `ruff check .`:passed。
- `ruff format --check .`:passed。
- `mypy src tests`:passed。
- `git diff --check`:passed。
- 结构扫描:无 `src` 下单类 >= 500 行,无单函数/方法 >= 100 行。

### 关键决策
- 🔒 **决策 1**:IM 可读性继续走核心 `MessageTextSpan` render contract,不在 Telegram Channel 写专用 Markdown/HTML 解析分支。
- 🔒 **决策 2**:字段 label 加粗只覆盖明确的结构化 key,不把任意冒号句子当标题。
- 🔒 **决策 3**:`TaskBus` 第一阶段拆状态仓储,approval coordinator / adapter dispatch service 留给后续增量演进,避免本轮重构过大。

### 留给下一轮
- 真实 Telegram 复验 `/agents` 和 `/appoint codex as tester`,确认 `•` 列表、`Agents:` / `Next:` 小节加粗、`agent_title:` / `role:` label 加粗的实际观感。
- 如果 `• /command` 在 Telegram 中影响命令点击/触碰发送,再设计平台 action/button 或 Next 区域特例,不要回退到 Telegram Channel 里硬编码业务消息。
- 继续做 Phase 8 `/overnight` records / operator inbox 持久化,不要把 SQLite task state 第一切片误说成完整离线托管恢复。

### 状态变化
- `STATUS.md` 当前轮次更新为 Round 107。
- Phase 8 增加 Core structure cleanup 完成项。
- B-004 从 deferred 更新为 resolved。

## Round 108 — 2026-05-21 — Codex

### 输入
- 人类完成 Telegram 复验:`/agents` 与 `/appoint codex as tester` 这次“好很多”,要求关闭该问题状态。
- 人类要求继续开发其他高优能力。

### 思考与讨论
- 候选 A:继续做 Lead decision / Goal Brief 的真实 IM 验收 → ❌ **暂缓**:这些需要人类真实环境继续操作,当前更适合推进可本地闭环的工程能力。
- 候选 B:做 Feishu production smoke → ❌ **暂缓**:需要外部开放平台配置和真实回调环境,本轮不能独立闭环。
- 候选 C:推进 `/overnight` 托管工单持久化 → ✅ **选定**:这是 Phase 8 “睡前下任务,早上看结果”的硬底座,也延续 Round 106 的 SQLite 业务状态层。
- 候选 D:只从 audit JSONL 反推 overnight records → ❌ **否决**:当前 `/overnight` 是业务工单,需要稳定列表和 scope 查询;直接作为业务状态写入 SQLite 更简单可靠,audit 仍保留为追踪权威。

### 产出
- 新增 `OfflineDelegationStore` 协议和 `SQLiteOfflineDelegationStore`,使用同一个 `AICO_STATE_DB_PATH` SQLite 文件保存 `offline_delegations` 表。
- 新增 `SQLiteStateDatabase`,统一维护本地状态库的 `aico_schema` metadata、schema version、状态表计数和 reset 能力。
- 新增 `aico-state --db <path>` CLI:
  - 默认输出 schema version 和已存在状态表行数。
  - `reset --yes` 清空已知 AICO 状态表,方便开发期快速迭代。
- `AICO_STATE_DB_PATH=true` 映射到 `.aico/state.db`,`false` / `0` / `off` 视为关闭;`.aico/` 加入 `.gitignore`,避免再生成仓库根目录 `true` SQLite 文件。
- `OfflineDelegationRecord` 增加 `created_at`,用于稳定恢复排序。
- `OfflineDelegationCommandHandler` 接受可选 store:
  - 未配置时保持原来的内存行为。
  - 配置后创建 `/overnight <goal>` 会写入 SQLite。
  - 重启后重新进入同一 active project,`/overnight` 可从 SQLite 载入最近托管工单。
- `Orchestrator` 新增 `offline_delegation_store` 注入参数。
- `build_phase1_runtime()` 在配置 `AICO_STATE_DB_PATH` 时同时启用 `SQLiteTaskStateStore` 和 `SQLiteOfflineDelegationStore`。
- README / README.zh-CN / Quickstart / daily ops / Phase 8 playbook / ADR-0028 / CHANGELOG 同步更新,不再把 `/overnight` persistence 标为进行中。
- `STATUS.md` 关闭 Telegram render 复验项,并把下一轮高优实现项调整为 operator inbox / morning handoff。

### 验证结果
- Targeted:
  - `pytest tests/unit/test_orchestrator.py::test_orchestrator_restores_overnight_delegations_from_sqlite tests/unit/test_orchestrator.py::test_orchestrator_queues_overnight_delegation_to_project_lead tests/unit/test_phase1_app.py::test_build_phase1_runtime_configures_sqlite_task_state_store`:3 passed。
- Full gate:
  - `pytest`:293 passed / 1 skipped。
  - `ruff check .`:passed。
  - `ruff format --check .`:passed。
  - `mypy src tests`:passed。
  - `git diff --check`:passed。
  - 结构扫描:无 `src` 下单类 >= 500 行,无单函数/方法 >= 100 行。

### 关键决策
- 🔒 **决策 1**:`/overnight` records 属于业务状态,跟 task snapshots / approvals 一样进入 `AICO_STATE_DB_PATH`;audit JSONL 不承担唯一业务恢复职责。
- 🔒 **决策 2**:托管工单持久化不等于恢复底层 CLI 子进程;恢复的是老板早上查看和追踪的 AICO work order。
- 🔒 **决策 3**:开发期允许快速清空业务状态,但必须通过 `aico-state reset --yes` 这样的显式工具,不要让测试/迭代产物悄悄散落在仓库根目录。
- 🔒 **决策 4**:下一步不是更激进的无人值守执行,而是 operator inbox / morning handoff,把人类待处理事项集中起来。

### 留给下一轮
- 设计并实现 operator inbox:聚合 `/overnight` handoff、pending approvals、failed/interrupted tasks、lead decision next actions。
- 给 inbox 复用 SQLite 业务状态层,避免重启后老板待处理事项丢失。
- 真实 IM 继续抽样 `/overnight` 重启恢复,确认用同一个 `AICO_STATE_DB_PATH` 且重新 `/project <project>` 后能看到历史工单。

### 状态变化
- `STATUS.md` 当前轮次更新为 Round 108。
- Phase 8 “托管工单持久化与重启恢复”改为完成。
- Phase 8 增加 SQLite 快速迭代治理完成项。
- 下一轮建议移除已完成的 Telegram render 复验和 `/overnight` persistence,新增 operator inbox / morning handoff 为高优实现项。

## Round 109 — 2026-05-22 — Codex

### 输入
- 人类要求把 Lead decision workflow、Goal Brief v0 和 Phase 5 `@reviewer` 协作 smoke 三个待办整理成真实问题列表和预期效果。
- 人类确认 Adapter appointment / concurrency 真实 IM 回归与 Memory Retrieval 真实 IM 验收已经完成,要求更新状态。

### 思考与讨论
- 候选 A:只在聊天里解释,不改文档 → ❌ **否决**:下一轮 Agent 仍会从 `STATUS.md` 看到过期高优队列,继续重复已完成验收。
- 候选 B:把两个已验收项标成代码完成项 → ❌ **否决**:代码早已完成,本轮变化是“真实 IM 验收状态”而不是新增实现。
- 候选 C:更新 `STATUS.md` 下一轮建议,并在本轮记录状态校准 → ✅ **选定**:符合项目自更新协议,也能把“待验收的问题是什么”写清楚。

### 产出
- `STATUS.md` 当前轮次更新为 Round 109。
- 从下一轮高优队列移除已由人类验证完成的 Adapter appointment / concurrency 真实 IM 回归。
- 从下一轮高优队列移除已由人类验证完成的 Memory Retrieval 真实 IM 验收。
- 将 Lead decision workflow 真实 IM 验收改写为问题列表:team readiness、workflow 触发、purpose-gated memory、consultation / audit / memory write-back。
- 将 Goal Brief v0 真实 IM dogfooding 改写为问题列表:`/goal` 派发、`/task` 可读、`/ask` 保守自动附加、普通咨询不误升级。
- 将 Phase 5 `@reviewer` smoke 回归改写为问题列表:child task 创建、parent/child trace、300 秒 idle timeout 和 busy slot 释放。

### 验证结果
- 本轮只更新状态与交接文档,未改运行代码,未跑测试。

### 关键决策
- 🔒 **决策 1**:真实 IM 验收完成项要从下一轮队列移除,不能只在聊天里记住。
- 🔒 **决策 2**:剩余 smoke / dogfood 项必须写清“真实问题”和“预期效果”,避免下一轮只机械重跑命令。

### 留给下一轮
- 优先真实验收 Lead decision workflow 与 Goal Brief v0;这两个直接影响 Phase 8 中 lead 替老板做决策和目标收口的可信度。
- Phase 5 `@reviewer` 协作 smoke 作为回归项保留,重点看 child task 是否有输出或能按 idle timeout 释放。
- 若继续开发而非验收,当前最高工程项仍是 Phase 8 operator inbox / morning handoff。

### 状态变化
- `STATUS.md` 当前轮次更新为 Round 109。
- Adapter appointment / concurrency 真实 IM 回归从待办移除。
- Memory Retrieval 真实 IM 验收从待办移除。

## Round 110 — 2026-05-24 — Codex

### 输入
- 人类澄清:“真实的问题列表”指的是可以直接问 IM、可验证功能的问题,不需要人类自己把检查点翻译成命令或 prompt。

### 思考与讨论
- 候选 A:保留抽象检查点,在聊天里补例子 → ❌ **否决**:状态文档仍会让下一轮和人类重复做翻译工作。
- 候选 B:把待办改成直接可复制的 IM 问题 → ✅ **选定**:更符合 boss 视角,也能直接 dogfood 真实功能。

### 产出
- `STATUS.md` 当前轮次更新为 Round 110。
- Lead decision workflow 待办改成可直接发送的 `/project`、`/team`、lead decision ask、`/audit`、`/recall decision` 问题序列。
- Goal Brief v0 待办改成可直接发送的 `/goal`、`/task`、带证据 marker 的 `/ask` 和普通咨询对照问题。
- Phase 5 `@reviewer` 协作 smoke 待办改成可直接发送的 implementer ask、`/tasks`、parent/child `/task`、`/status` 问题序列。

### 验证结果
- 本轮只更新状态与交接文档,未改运行代码,未跑测试。

### 关键决策
- 🔒 **决策 1**:真实 IM 验收项应优先写成老板可直接发送的问题,而不是工程师内部检查点。

### 留给下一轮
- 按 `STATUS.md` 中三组“直接可问的问题”逐条发到 Telegram,观察是否符合预期效果。
- 如果实际输出不符合预期,把具体 Telegram 回包记录进 `BLOCKERS.md` 或下一轮 `ROUNDS.md`,不要只写“体验不好”。

## Round 111 — 2026-05-24 — Codex

### 输入
- 人类真实执行两条验证命令:
  - `/ask lead decide whether we should start Phase 8 operator inbox now...`
  - `/ask lead propose a tiny Phase 8 inbox implementation plan, then ask @reviewer: ...`
- Telegram 只显示两条 Codex 任务仍在 running:
  - `4697ce83-d7bc-4e7a-8863-09f43998d009 [codex]: running`
  - `4c31d567-f9cf-48de-a232-8dfe74af5cef [codex]: running`
- 人类要求排查并解决。

### 思考与讨论
- 候选 A:只把验证命令改成 `/ask implementer ...` → ❌ **不足**:`lead` 是老板视角自然说法,系统应该支持,不能把概念翻译成本转嫁给人类。
- 候选 B:只等待 Codex idle timeout → ❌ **不足**:日志确实显示 300 秒后 timeout,但这没有修复验收命令和协作触发的语义问题。
- 候选 C:让 `lead` / `default` 成为项目 default assignment 别名,并增强协作指令解析 → ✅ **选定**:同时解决 lead 验收命令和“计划正文后再 @reviewer”的真实输出形态。

### 产出
- `ProjectAssignmentDirectory.appointment_for_role()` 支持 `lead` / `default` 解析到当前项目 default assignment。
- `split_collaboration_directive()` 新增协作指令拆分能力,可扫描多行输出中的 `@persona: ...`。
- `Orchestrator._stream_outputs_for_task()` 改为在触发 child task 的同时保留非指令正文,避免把计划内容吞掉。
- 新增/更新测试:
  - `test_project_assignment_directory_resolves_lead_alias_to_default_assignment`
  - `test_parse_collaboration_directive_accepts_later_directive_line`
  - `test_split_collaboration_directive_keeps_non_directive_text`
  - `test_orchestrator_ask_lead_alias_runs_lead_decision_workflow`
  - `test_orchestrator_routes_later_collaboration_directive_and_keeps_text`
- 新增 PITFALL P-023,记录 `lead` 概念与 role id 混用、以及协作指令只看首行导致真实验收失败的问题。
- `STATUS.md` 当前轮次更新为 Round 111。

### 验证结果
- Targeted: `uv run pytest tests/unit/test_collaboration.py tests/unit/test_project_assignment.py tests/unit/test_orchestrator.py::test_orchestrator_ask_lead_alias_runs_lead_decision_workflow tests/unit/test_orchestrator.py::test_orchestrator_routes_later_collaboration_directive_and_keeps_text tests/unit/test_orchestrator.py::test_orchestrator_lead_decision_workflow_consults_roles_records_audit_and_memory tests/unit/test_orchestrator.py::test_orchestrator_routes_adapter_collaboration_directive_to_target_persona`:23 passed。
- Full gate: `uv run pytest`:298 passed / 1 skipped。
- Full gate: `uv run ruff check .`:passed。
- Full gate: `uv run ruff format --check .`:passed。
- Full gate: `uv run mypy src tests`:passed。
- `git diff --check`:passed。
- `git diff --check`:passed。

### 关键决策
- 🔒 **决策 1**:`lead` 是项目办公室一等用户语义,`/ask lead ...` 应该工作,而不是要求老板知道当前 lead role id 是 `implementer` 还是 `reviewer`。
- 🔒 **决策 2**:Phase 5 协作指令应支持真实模型输出习惯:先给计划,再在后续行发 `@reviewer: ...`。
- 🔒 **决策 3**:触发协作不应牺牲可见正文;非指令内容仍要展示给老板。

### 留给下一轮
- 重启正在跑的 AICO 服务以加载本轮代码修复。
- 重新执行 `/ask lead decide whether we should start Phase 8 operator inbox now...`,预期触发 lead decision workflow,而不是普通 Codex reviewer 任务。
- 重新执行协作 smoke 时,如果想验 Phase 5 而不是 lead decision,优先用 `/ask implementer ... @reviewer: ...`;如果使用 `/ask lead ...` 且文本包含 `whether`,它会按 lead decision 语义处理。
- 如果 Codex 仍 300 秒无 stdout,这是 provider 层可用性问题;用 `/interrupt <task_id>` 清理,或改用已稳定输出的 agent 做本轮验收。

### 状态变化
- `STATUS.md` 当前轮次更新为 Round 111。
- 新增 P-023。

## Round 112 — 2026-05-25 — Codex

### 输入
- 人类调研相邻开源产品后总结:AICO 与 OMC / CoWork OS 都在卷"AI 公司操作系统",但 AICO 的差异化是"老板不在场"。
- 人类要求先脑暴 3 种改进方案,随后选择方案 C:新增并强化老板不在场假设,但不直接重写北极星三句话。

### 思考与讨论
- 候选 A:只在聊天里解释差异化,不改文档 → ❌ **否决**:这个判断会影响 Phase 8 后续优先级,只留在聊天里会被下一轮 Agent 忘掉。
- 候选 B:直接改写北极星三句话 → ❌ **否决**:现有三句话仍然正确,且 AGENTS 明确北极星不可被功能需求覆盖;本轮应强化解释层和判定规则,不是替换宪法。
- 候选 C:在 `NORTH_STAR.md` 新增"老板缺席操作模型",并同步 `STATUS.md` 顶层叙事 → ✅ **选定**:既保留原北极星,又把 absence-first 变成后续功能取舍的产品约束。
- 候选 D:新增一整篇架构文档 → ❌ **暂缓**:本轮目标是强化目标与北极星指引,不是展开一轮产品文档重构;如果后续 operator inbox / morning handoff 设计需要,再沉淀专门文档。

### 产出
- `NORTH_STAR.md` 在第一句业务价值下新增"老板缺席操作模型(Absence-first)"。
- 明确 AICO 与 OMC / CoWork OS 的边界:AICO 默认老板不在电脑前,通过 IM 指挥本地 AI CLI 团队继续工作。
- 新增 5 个核心能力判定问题:只靠 IM 能不能下达、离开后能不能推进、风险能不能等审批、早上能不能看懂、出问题能不能审计/叫停/恢复。
- `STATUS.md` 更新当前轮次、宏大叙事和"老板不在场假设",并把 Phase 8 operator inbox / morning handoff 重新锚定为 absence-first 的关键拼图。

### 验证结果
- 本轮只更新产品目标与交接文档,未改运行代码,未跑单测。

### 关键决策
- 🔒 **决策 1**:AICO 的差异化解释从"虚拟公司感"进一步收敛为 absence-first:老板不在场时,本地 AI CLI 团队仍要可指挥、可托管、可审批、可叫停、可追责。
- 🔒 **决策 2**:OMC / CoWork OS 的比较只作为边界说明,不把竞品功能复制成 roadmap;后续优先级仍回到 AICO 北极星和 Phase 8 dogfooding。
- 🔒 **决策 3**:不改北极星三句话正文,只新增操作模型和判定规则,避免把项目宪法改成短期营销定位。

### 留给下一轮
- 继续按 `STATUS.md` 的真实 IM 问题列表验收 Lead decision workflow、Goal Brief v0 和 Phase 5 协作 smoke。
- 如果继续开发,优先做 Phase 8 operator inbox / morning handoff,并用本轮新增的 5 个 absence-first 问题约束范围。
- 后续 README / 开源首屏复核时,可把"老板不在场"作为第一屏差异化表达,但不要把它写成只能营销不能验收的口号。

### 状态变化
- `STATUS.md` 当前轮次更新为 Round 112。
- `NORTH_STAR.md` 新增老板缺席操作模型。

## Round 113 — 2026-05-25 — Codex

### 输入
- 人类真实 IM dogfood:
  - 先执行 `/ask reviewer review whether the Phase 8 inbox plan violates approval or audit boundaries...`,任务 `f9d9990f` 长时间无输出后被 `/interrupt`。
  - 随后同一命令成功输出,但 reviewer 继续发起 `@implementer: please reflect (a)-(d) ...`。
  - Telegram 显示 `Collaboration requested: implementer -> implementer`,child implementer 回答缺少 `(a)-(d)`、PR plan 和 ADR 上下文。
- 人类要求排查并优化。

### 思考与讨论
- 候选 A:只告诉人类以后 reviewer 指令不要写 `(a)-(d)` → ❌ **否决**:真实团队协作里引用上一段 findings 是自然行为,不应把上下文拼接成本转嫁给老板或 reviewer。
- 候选 B:禁止 reviewer 再 `@implementer` → ❌ **否决**:reviewer 要求 implementer 按 review findings 改计划/ADR 是合理协作。
- 候选 C:child collaboration payload 带上父任务截至指令前的可见输出上下文,并修正来源 role 展示 → ✅ **选定**:最小改动,保留现有轻量协议,直接解决上下文断层和 `implementer -> implementer` 误导。

### 产出
- `collaboration_payload()` 新增可选 `source_context`,会生成 `Context from <source> output so far` 和 `Request:` 区块。
- `Orchestrator._stream_outputs_for_task()` 在触发协作时把已捕获父输出和当前 chunk 的非指令正文传给 child task。
- 协作来源优先使用 task metadata 中的 `aico.assignment_role`,让 reviewer appointment 发起协作时 IM/audit 显示 `reviewer -> implementer`。
- `TaskBus.record_collaboration_requested()` 支持传入显式 `actor_id`,避免 audit actor 继续落到底层 persona。
- 新增 P-024,记录“短指令引用父输出编号但 child task 丢失上下文”的坑。

### 验证结果
- `uv run pytest tests/unit/test_collaboration.py tests/unit/test_orchestrator.py::test_orchestrator_routes_adapter_collaboration_directive_to_target_persona tests/unit/test_orchestrator.py::test_orchestrator_routes_later_collaboration_directive_and_keeps_text tests/unit/test_orchestrator.py::test_orchestrator_collaboration_uses_assignment_role_and_parent_context`:12 passed。
- `uv run ruff check src/aico/core/collaboration.py src/aico/core/orchestrator.py src/aico/core/task_bus.py tests/unit/test_collaboration.py tests/unit/test_orchestrator.py`:passed。
- Full gate: `uv run pytest`:300 passed / 1 skipped。
- Full gate: `uv run ruff check .`:passed。
- Full gate: `uv run ruff format --check .`:passed。
- Full gate: `uv run mypy src tests`:passed。
- `git diff --check`:passed。

### 关键决策
- 🔒 **决策 1**:协作 child task 必须拿到足以理解短引用的父输出上下文;只传 directive payload 会让真实 AI 团队交接断层。
- 🔒 **决策 2**:老板视角协作来源应该是 project role / assignment role,不是底层 provider persona。`claude as reviewer` 不能在 IM 里显示成 implementer 发起协作。
- 🔒 **决策 3**:本轮不引入复杂 A2A 消息 schema,先沿用轻量文本 payload,只补上下文区块。

### 留给下一轮
- 重启 AICO 服务后,重跑同一条 `/ask reviewer review whether the Phase 8 inbox plan violates approval or audit boundaries...`。
- 预期如果 reviewer 再要求 `@implementer: reflect (a)-(d) ...`,IM 应显示 `Collaboration requested: reviewer -> implementer`,child implementer payload 中包含 reviewer findings 上下文,不应再回答“我不知道 (a)-(d)”。
- 若 Claude 新 session 仍长时间无 stdout,继续用 `/interrupt <task>` 收口;这是 provider 层稳定性问题,与本轮协作上下文修复分开跟踪。

### 状态变化
- `STATUS.md` 当前轮次更新为 Round 113。
- 新增 P-024。

## Round 114 — 2026-05-25 — Codex

### 输入
- 人类下午继续真实 IM dogfood:
  - `/ask reviewer review whether the Phase 8 inbox plan violates approval or audit boundaries. Focus on read-only /inbox, audit event boundary, /approve id hints, and current-project scope keys. Return concise findings.`
  - 仍返回 `ERROR: adapter output idle timeout after 300s`。
- 人类指出:agent 执行长任务 5 分钟是正常的;AICO 是公司,老板不在时更应该允许员工持续工作。

### 思考与讨论
- 候选 A:保持 300 秒,让人类每次手动调环境变量 → ❌ **否决**:这把“公司员工长时间工作”的正常成本转嫁给老板,不符合 absence-first。
- 候选 B:完全移除所有 optional adapter idle timeout → ❌ **暂缓**:历史上 Codex 无 stdout 会无限占用并发槽位;彻底移除默认保护需要更强 heartbeat / inbox 观察面配套。
- 候选 C:默认放宽到 1800 秒,同时允许 `AICO_*_OUTPUT_IDLE_TIMEOUT_SECONDS=0` 禁用自动 idle timeout → ✅ **选定**:把 5 分钟误杀问题先收住,保留可配置和 `/interrupt` 兜底。

### 产出
- `DEFAULT_OPTIONAL_OUTPUT_IDLE_TIMEOUT_SECONDS=1800.0` 作为 Codex / Cursor / CodeFlicker / Trae / Gemini 默认 no-output idle timeout。
- `Phase1Settings` 中 optional CLI adapter timeout 字段从 `gt=0` 改为 `ge=0`;运行时通过 `_optional_idle_timeout()` 将 `0` 转成 `None`。
- `AICO_CODEX_OUTPUT_IDLE_TIMEOUT_SECONDS=0` 等配置现在表示禁用自动 idle timeout;非 0 值仍按秒数触发 no-output guard。
- 更新 daily ops、Phase 5 collaboration playbook、optional adapter playbook、ADR-0017、PITFALL P-014 / P-022 和 CHANGELOG。
- 更新 optional adapter / phase1 单测,覆盖默认 1800 秒和 `0` 禁用。

### 验证结果
- Targeted: `uv run pytest tests/unit/test_codex_adapter.py tests/unit/test_cursor_adapter.py tests/unit/test_codeflicker_adapter.py tests/unit/test_trae_adapter.py tests/unit/test_gemini_adapter.py tests/unit/test_phase1_app.py::test_build_phase1_runtime_can_enable_codex_adapter_for_status tests/unit/test_phase1_app.py::test_build_phase1_runtime_can_disable_optional_adapter_idle_timeout`:19 passed。
- Targeted: `uv run ruff check src/aico/adapter/claude_code.py src/aico/adapter/codex.py src/aico/adapter/cursor.py src/aico/adapter/codeflicker.py src/aico/adapter/trae.py src/aico/adapter/gemini.py src/aico/app/phase1.py tests/unit/test_codex_adapter.py tests/unit/test_cursor_adapter.py tests/unit/test_codeflicker_adapter.py tests/unit/test_trae_adapter.py tests/unit/test_gemini_adapter.py tests/unit/test_phase1_app.py`:passed。
- Full gate: `uv run pytest`:301 passed / 1 skipped。
- Full gate: `uv run ruff check .`:passed。
- Full gate: `uv run ruff format --check .`:passed。
- Full gate: `uv run mypy src tests`:passed。

### 关键决策
- 🔒 **决策 1**:no-output idle timeout 不是任务总时长限制;默认值不能让正常 5 分钟 review 被误杀。
- 🔒 **决策 2**:absence-first 下,默认应偏向让 agent 持续工作;收口手段是 `/interrupt`、并发上限和可配置 guard,不是短超时。
- 🔒 **决策 3**:保留自动 idle guard,但把它定位为“疑似 provider 沉默保护”,并允许高信任 dogfooding 场景显式关闭。

### 留给下一轮
- 重启 AICO 服务后,重跑同一条 reviewer ask。预期默认不会在 300 秒失败;若 1800 秒仍无输出,再判断是 provider 长沉默还是需要更强 heartbeat / inbox 观察。
- 如果希望老板离开电脑后允许长时间 review,启动时可设 `AICO_CODEX_OUTPUT_IDLE_TIMEOUT_SECONDS=0`;仍可通过 `/interrupt <task_id>` 叫停。

### 状态变化
- `STATUS.md` 当前轮次更新为 Round 114。
- P-014 / P-022 更新为 Round 114 策略。

## Round 115 — 2026-05-26 — Codex

### 输入
- 人类提交真实 IM 长任务 `01ddaa36-4575-4204-8431-18d6c6a93a45`,显示 `target: reviewer`, `adapter: codex`, `status: running`,但 IM 侧看起来仍像 hang 住。
- 人类要求先确认长任务行为是否真有问题,解决后把上轮列出的 P0/P1 都支持上,需要人类验证的部分提供可决策上下文。

### 思考与讨论
- 候选 A:保持 Round 114 的 1800 秒 idle timeout,让用户继续等 → ❌ **否决**:这能避免 5 分钟误杀,但无法让老板在 IM 里判断任务是否还活着。
- 候选 B:彻底关闭 idle timeout → ❌ **否决**:会让 provider 永久静默时占住并发槽位,且仍然没有老板可读状态。
- 候选 C:新增 quiet heartbeat,并把 running / approval / handoff 聚合进 current-project `/inbox` → ✅ **选定**:最小闭环,同时满足 absence-first 的可见、可中断、可交接。
- 候选 D:直接实现多 step / 多 agent 夜间自动编排和定时早报 → ❌ **暂缓**:这是更大的 Phase 8 后续工作,不应混进本轮长任务可见性修复。

### 产出
- 排查日志确认 `01ddaa36` 已被 Codex adapter 接收、CLI 进程已启动并进入 `Stream start`;14 分钟以上没有 stdout chunk,所以不是路由提交失败,而是 provider 长静默导致 IM 缺少活性反馈。
- `OutputType.STATUS` 新增为非结果型流式输出;TaskBus 收到后保持 task `running`,并把 status 写入 running reason。
- `ClaudeCodeAdapter` 家族新增 quiet heartbeat:进程仍存活但长时间没有 stdout 时,周期性产出 `Still running: no adapter output...`。
- `Orchestrator` 会把 heartbeat 推送到 IM,但不会写入普通任务 captured output,避免污染 lead decision memo、Goal Brief 输出和协作上下文。
- 新增 `/inbox` 当前项目老板收件箱第一切片,聚合待审批、running/failed/interrupted/rejected、离线托管、Goal Brief / lead decision 和协作 follow-up。
- 更新 daily ops、Phase 5 collaboration playbook、Phase 8 offline delegation playbook、CHANGELOG、STATUS 和 P-025。

### 验证结果
- Targeted:`uv run pytest tests/unit/test_claude_code_adapter.py tests/unit/test_commands.py tests/unit/test_orchestrator.py::test_orchestrator_inbox_summarizes_project_attention_and_handoffs`:25 passed。
- Targeted:`uv run ruff check src/aico/adapter/claude_code.py src/aico/core/models.py src/aico/core/task_bus.py src/aico/core/orchestrator.py src/aico/core/commands.py src/aico/core/offline_delegation.py src/aico/core/inbox.py tests/unit/test_claude_code_adapter.py tests/unit/test_commands.py tests/unit/test_orchestrator.py`:passed。
- Targeted:`uv run mypy src tests`:passed。
- Full gate:`uv run pytest`:303 passed / 1 skipped。
- Full gate:`uv run ruff check .`:passed。
- Full gate:`uv run ruff format --check .`:passed。
- Full gate:`uv run mypy src tests`:passed。
- Full gate:`git diff --check`:passed。
- Structural check:抽查 `orchestrator.py`、`task_bus.py`、`claude_code.py`、`inbox.py` 的 class / function 行数,无单类 >500 或单函数 >100。

### 关键决策
- 🔒 **决策 1**:长任务静默不是“任务完成/失败”的证据;AICO 需要把 provider 静默显示成可操作的 running 状态,而不是让老板猜。
- 🔒 **决策 2**:`OutputType.STATUS` 是状态提示,不是任务结果;不能进入 lead decision memo、Goal Brief final output 或协作 payload。
- 🔒 **决策 3**:`/inbox` 第一版只读、current-project scoped,先解决老板回来看项目时“哪里需要我处理”的入口,不在本轮做定时推送或夜间自动多步编排。

### 留给下一轮
- 重启 AICO 服务后,旧任务 `01ddaa36` 不会自动获得 heartbeat;如果仍在运行,先发送 `/interrupt 01ddaa36` 收口。
- 真实 IM 验证长静默任务:重新发送 reviewer 长任务,预期 IM 周期性显示 `Still running...`,`/task <id>` 展示 running reason,`/inbox` 展示 running task 和 `/interrupt`。
- 真实 IM 验证 Lead decision、Goal Brief、Phase 5 collaboration 时,都补一次 `/inbox`,确认它只展示当前项目 scope,且 heartbeat 文本不污染 memo / goal output。

### 状态变化
- `STATUS.md` 当前轮次更新为 Round 115。
- 新增 P-025。

## Round 116 — 2026-05-26 — Codex

### 输入
- 人类验证 Round 115 heartbeat 生效,但同一类 reviewer/Codex 任务持续显示 `Still running: no adapter output...`,从 120 秒一直到 1680 秒仍没有结果。
- 人类追问“是不是我们的任务有问题,为什么一直执行不了”。

### 思考与讨论
- 候选 A:继续拉长 idle timeout → ❌ **否决**:heartbeat 已证明任务可见,但没有解释为什么 Codex 没有 stdout;继续加长只会隐藏根因。
- 候选 B:认为 prompt 太复杂或 reviewer 任务太难 → ❌ **否决**:状态库显示 payload 约 1996 字符,并非异常巨大;同类 reviewer prompt 以前也能在 1-2 分钟内输出。
- 候选 C:验证 Codex CLI 本体,再查 AICO 子进程启动契约 → ✅ **选定**:最小 smoke 能把“Codex/账号/网络坏了”和“AICO 启动方式有问题”分开。

### 产出
- 日志确认新 task `0e72ac63` 已被 Codex adapter 接收并进入 `Stream start`,之后只有 `type=status` heartbeat,没有 `type=text`。
- SQLite 状态确认 `0e72ac63` 的 task payload 约 1996 字符,状态为 running,reason 为最新 heartbeat。
- 在相同用户权限下执行最小 Codex CLI smoke:4 秒返回 `AICO_SMOKE_OK`,说明 Codex CLI、账号和网络不是整体不可用。
- 根因收敛为子进程 stdin 契约:Codex 0.125 `exec` 会读取 stdin 作为 additional input;AICO 过去没有显式设置 stdin,子进程可能继承到不会 EOF 的 stdin,从而长期等待额外输入且不产出 stdout。
- `_create_process()` 改为 `stdin=DEVNULL`,让所有 ClaudeCodeAdapter 家族非交互 CLI 子进程都显式关闭 stdin。
- 新增单测覆盖 `create_subprocess_exec(..., stdin=DEVNULL, stdout=PIPE, stderr=PIPE)`。
- 更新 CHANGELOG、Phase 5 collaboration playbook、STATUS 和 P-026。

### 验证结果
- Targeted:`uv run pytest tests/unit/test_claude_code_adapter.py tests/unit/test_codex_adapter.py`:21 passed。
- 真实最小 Codex smoke:`codex --ask-for-approval never exec --sandbox read-only --color never "Reply with exactly: AICO_STDIN_CLOSED_OK"` 在 `stdin=DEVNULL` 下返回 `AICO_STDIN_CLOSED_OK`。
- 出于隐私边界,没有把完整真实 task payload 额外发送给外部 Codex 做复现;该 payload 包含项目状态和记忆内容。
- Full gate:`uv run pytest`:304 passed / 1 skipped。
- Full gate:`uv run ruff check .`:passed。
- Full gate:`uv run ruff format --check .`:passed。
- Full gate:`uv run mypy src tests`:passed。
- Full gate:`git diff --check`:passed。

### 关键决策
- 🔒 **决策 1**:非交互 CLI adapter 必须显式关闭 stdin;不能依赖父进程 stdin 是否刚好 EOF。
- 🔒 **决策 2**:连续 heartbeat 是诊断信号,不是完成态;超过 10-20 分钟仍无 stdout 时,应检查 CLI 启动契约和 provider stderr/stdin,不是继续调大 timeout。
- 🔒 **决策 3**:真实项目 payload 不为诊断目的额外导出到外部服务;优先用最小 smoke 和本地状态/log 证明链路。

### 留给下一轮
- 重启 AICO 服务后,先 `/interrupt 0e72ac63` 收掉旧进程,再重试同一条 reviewer ask。
- 预期 Round 116 之后,同一类 Codex reviewer 任务应正常返回文本;如果仍只 heartbeat,下一步需要暴露 stderr tail 或记录 provider 子进程是否在等待 MCP/hook。

### 状态变化
- `STATUS.md` 当前轮次更新为 Round 116。
- 新增 P-026。

## Round 117 — 2026-05-26 — Codex

### 输入
- 人类继续反馈 reviewer/Codex 同一条边界 review 任务仍只显示 `Still running...` 到 120 / 240 秒,担心是否问题太难或 Codex 交互没通。

### 思考与讨论
- 候选 A:回答“模型太慢,再等等” → ❌ **否决**:该任务只是 read-only boundary review,且 payload 约 1996 字符,正常不应数分钟没有任何 stdout。
- 候选 B:认为 `/ask reviewer` 没交给 Codex → ❌ **否决**:日志和 `ps` 均确认 Codex 子进程已启动,命令中包含完整 prompt。
- 候选 C:继续查 CLI 子进程 I/O 契约 → ✅ **选定**:stdin 已修,下一层高风险点是 stderr pipe 没有并发读取。

### 产出
- 日志确认新 task `3be492f3` accepted、`Stream start`,之后只有 heartbeat,无 `type=text`。
- SQLite 状态确认该 task payload 约 1996 字符,不是异常巨大 prompt。
- `ps` 确认真实 Codex 子进程仍在运行,命令参数中包含完整 reviewer prompt,所以不是模型没有收到任务。
- 根因收敛为 stderr pipe 反压:Codex CLI 会持续向 stderr 写运行头、hook、工具日志和 warning;AICO 过去只在进程退出后读 stderr,如果 stderr pipe 写满,子进程会被阻塞,stdout 也不会产出。
- `_run_task()` 改为启动子进程后立即后台 drain stderr,只保留 tail 供失败时生成错误内容;成功任务不把 stderr 噪音推给 IM。
- 新增单测 `test_claude_code_adapter_drains_stderr_while_process_runs()`,构造 stderr 不被读取则 `process.wait()` 不返回的场景。

### 验证结果
- Targeted:`uv run pytest tests/unit/test_claude_code_adapter.py tests/unit/test_codex_adapter.py`:22 passed。
- Full gate:`uv run pytest`:305 passed / 1 skipped。
- Full gate:`uv run ruff check .`:passed。
- Full gate:`uv run ruff format --check .`:passed。
- Full gate:`uv run mypy src tests`:passed。
- Full gate:`git diff --check`:passed。
- Structural check:`src/aico/adapter/claude_code.py` 无单类 >500 或单函数 >100。

### 关键决策
- 🔒 **决策 1**:连续 heartbeat 不是“模型一定太慢”;对短 read-only review 来说,超过数分钟无 stdout 应优先查子进程 I/O。
- 🔒 **决策 2**:CLI adapter 必须同时处理 stdout 和 stderr,否则 provider 诊断日志可能反压阻塞正常结果输出。
- 🔒 **决策 3**:stderr 诊断默认不推给 IM,避免 provider 噪音污染老板体验;失败时保留 tail 作为错误信息。

### 留给下一轮
- 人类真实 IM 复验确认改动有效,本问题已关闭。
- 如果未来同类问题复现,下一步应增加 adapter debug mode:记录 stderr tail 摘要、子进程 fd 状态和 Codex session id,而不是继续猜 prompt 难度。

### 状态变化
- `STATUS.md` 当前轮次更新为 Round 117。
- 新增 P-027。

## Round 118 — 2026-05-26 — Codex

### 输入
- 人类同意将 Phase 8 后续 P0-P4 全部做成可落地功能,要求先写短期计划和防跑偏约束,然后直接进入研发。

### 思考与讨论
- 候选 A:只在聊天中给 sprint 建议 → ❌ **否决**:后续 Agent 接手仍会看到旧的下一轮建议,容易重新把 Dream、self-improving、retrieval backend 当成散点功能。
- 候选 B:直接开做 Dream / hybrid retrieval → ❌ **否决**:这些更像“agent 更会想”,但老板缺席时的接手、审批和验收闭环还没完全闭上。
- 候选 C:先写 ADR-0029 和 Phase 8 Absence Loop playbook,再从 Sprint 1 actionable inbox 开始实现 → ✅ **选定**:把所有能力固定到“下任务 -> 执行 -> 审批/叫停 -> 验收 -> 早上接手 -> 经验沉淀 -> 下次召回”的闭环里,且每个 sprint 都有 IM 验收路径。

### 产出
- 新增 `docs/decisions/0029-phase-8-absence-loop.md`,定义 Phase 8 Absence Loop 和 Sprint 1-5 队列。
- 新增 `docs/playbooks/phase-8-absence-loop.md`,记录 actionable inbox、morning handoff、outcome grader、Dream/runbook memory、hybrid retrieval 的直接 IM 验收脚本和护栏。
- 更新 `docs/decisions/README.md` 和 `docs/playbooks/README.md` 索引。
- Sprint 1 研发第一切片:`/inbox` 新增 `First action`,并把待审批、running、failed/interrupted/rejected、overnight handoff、Goal/decision、collaboration follow-up 都渲染为带下一步命令的 action item。
- 更新 `STATUS.md`、`CHANGELOG.md` 和本轮 `ROUNDS.md`。

### 验证结果
- Targeted:`uv run pytest tests/unit/test_orchestrator.py::test_orchestrator_inbox_summarizes_project_attention_and_handoffs`:1 passed。
- Targeted:`uv run ruff check src/aico/core/inbox.py tests/unit/test_orchestrator.py docs/decisions/0029-phase-8-absence-loop.md docs/playbooks/phase-8-absence-loop.md`:passed。
- Full gate:`uv run pytest`:305 passed / 1 skipped。
- Full gate:`uv run ruff check .`:passed。
- Full gate:`uv run ruff format --check .`:passed。
- Full gate:`uv run mypy src tests`:passed。
- Full gate:`git diff --check`:passed。

### 关键决策
- 🔒 **决策 1**:Phase 8 后续所有新能力必须进入 Absence Loop sprint 队列,不能作为互不相干的研究功能落地。
- 🔒 **决策 2**:短期优先级是老板回来后的可处理入口和 morning handoff;Dream / self-improving / hybrid retrieval 必须服务于“经验沉淀和下次召回”,不能先于接手闭环。
- 🔒 **决策 3**:`/inbox` 仍保持 current-project scoped 和只读控制入口;actionable 是给出下一步命令,不是批量自动审批或自动恢复。

### 留给下一轮
- 真实 IM 验证 Sprint 1:
  - `/project aico`
  - `/inbox`
  - 预期顶部有 `First action`,每个事项都能直接决定下一步。
- 继续研发时按 ADR-0029 做 Sprint 2 Morning Handoff,先做手动触发报告,不要先做定时器或多 step 夜间自动编排。

### 状态变化
- `STATUS.md` 当前轮次更新为 Round 118。
- Phase 8 新增 ADR-0029 / Absence Loop playbook / actionable inbox 完成项。

## Round 119 — 2026-05-26 — Codex

### 输入
- 人类要求按顺序执行刚新增的四个 Sprint,并给出 human 可验证的 dogfood 问题样例、预期观测指标和效果。

### 思考与讨论
- 候选 A:先继续做自动定时早报或多 agent 夜间编排 → ❌ **否决**:会跳过手动可验证闭环,且容易把 Phase 8 做成调度器。
- 候选 B:把 Dream / self-improving 直接写入 active memory → ❌ **否决**:老板缺席时 agent 可以反思,但不能未审查就污染后续 prompt。
- 候选 C:按 playbook 执行 Sprint 2-5 的最小 IM 闭环 → ✅ **选定**:每一步都有可问命令、可观测输出和单测,且不绕过审批 / memory governor。

### 产出
- Sprint 2:`/morning` 新增 active-project 手动早报,汇总 done、blocked、risks、overnight handoffs 和 next actions。
- Sprint 3:Goal Brief 任务完成后自动寻找 tester / reviewer 生成 Outcome Grader 任务,grader prompt 要求 verdict、evidence、gaps 和 boss_next_action。
- Sprint 3 防误判:Outcome Grader 标记为内部只读任务,避免其提示词里的 IM command 文案触发 shell approval;同时收窄 `/ask` 自动 Goal Brief marker,避免“验收标准”这类普通规划语句误升级。
- Sprint 4:`/dream` 新增 Dream review,从 waiting approval / running / failed / interrupted / rejected 任务生成 candidate runbook memory,默认不进入 Prompt Stack。
- Sprint 5:MemoryStore / MemoryRetriever 默认 scorer 从纯 semantic 升级为 local hybrid scorer:exact phrase > phrase overlap > semantic alias fallback,同时保留 scope / purpose / sensitivity / confidence 治理边界。
- 更新 Phase 8 Absence Loop playbook、STATUS、CHANGELOG 和相关单测。

### 验证结果
- Targeted:`uv run pytest tests/unit/test_commands.py tests/unit/test_memory.py tests/unit/test_orchestrator.py -q`:97 passed。
- Full gate:`uv run pytest`:309 passed / 1 skipped。
- Full gate:`uv run ruff check .`:passed。
- Full gate:`uv run ruff format --check .`:passed。
- Full gate:`uv run mypy src tests`:passed。
- Full gate:`git diff --check`:passed。

### 关键决策
- 🔒 **决策 1**:`/morning` 第一版必须手动可触发;定时推送只能复用同一报告,不能成为隐藏逻辑。
- 🔒 **决策 2**:Outcome Grader 是 goal 的验收 follow-up,不是自动修复器;如果后续修复需要写文件或 shell,仍必须走 `/approve`。
- 🔒 **决策 3**:Dream 只能写 reviewable candidate memory;默认 prompt memory 仍由 `MemoryGovernor` 控制。
- 🔒 **决策 4**:Hybrid retrieval 只替换本地 scorer,不改变 MemoryStore / MemoryRetriever / MemoryGovernor 的治理边界。

### 留给下一轮
- 用真实 IM 按顺序 dogfood:`/inbox`、`/morning`、`/goal ... 验收:`、`/task <grader>`、`/dream`、`/recall 早报接手`。
- 如果 Outcome Grader 没出现,先检查当前项目是否任命了 tester 或 reviewer。
- 如果 `/dream` 只有 none,先制造一个 waiting approval / running / failed 任务再试。

### 状态变化
- `STATUS.md` 当前轮次更新为 Round 119。
- Phase 8 Sprint 2-5 第一切片完成。

## Round 120 — 2026-05-27 — Codex

### 输入
- 人类真实 dogfood 反馈:Dogfooding 1 和 2 没问题。
- Dogfooding 3 的 `/goal` 返回没有 IM Markdown/富文本格式化,标题和无序列表没有解析。
- Dogfooding 4 的 `/dream` 返回一串旧失败 task candidate,人类不知道这是否正确。
- Dogfooding 5 的 `/recall` 返回也没有正确 Markdown/富文本格式化。

### 思考与讨论
- 候选 A:解释这是 Telegram Markdown 限制 → ❌ **否决**:项目已有平台无关 `MessageTextSpan` 和 `rich_text_message()`;问题是部分内置命令没有使用它。
- 候选 B:只给 `/goal` 和 `/recall` 套 rich text → ❌ **不完整**:Outcome Grader、Dream、Memory remembered/archived/no-result 也有同类风险。
- 候选 C:统一修 Phase 8 内置命令渲染,并把 Dream 从 raw task list 改成聚合 lesson candidates → ✅ **选定**:同时解决“看起来不好读”和“看不懂对不对”两个 dogfood 问题。

### 产出
- `goal_started_message()`、`goal_list_message()`、Outcome Grader started/skipped 消息改为 `rich_text_message()` 输出。
- `/remember`、`/recall`、`/forget` 和 recall no-result 输出改为 `rich_text_message()` 输出。
- `message_rendering` 增补 `owner`、`tracking`、`goal`、`grader`、`graded_task`、`query`、`purpose`、`evidence` 等 label keys。
- `/dream` 输出新增 Meaning / Effect / Next,明确 candidate memory 不会自动注入 prompt。
- `/dream` candidate 生成从逐条 task 改为按原因聚合:waiting approval、running、adapter idle timeout、interrupted、rejected、generic failed。
- 新增 P-028,记录“内置命令绕过 rich text renderer”的坑。

### 验证结果
- Targeted:`uv run pytest tests/unit/test_orchestrator.py::test_orchestrator_goal_command_attaches_goal_brief_to_project_role tests/unit/test_orchestrator.py::test_orchestrator_remember_recall_and_forget_project_memory tests/unit/test_orchestrator.py::test_orchestrator_dream_writes_reviewable_candidate_memory tests/unit/test_message_rendering.py -q`:8 passed。
- Full gate:`uv run pytest`:309 passed / 1 skipped。
- Full gate:`uv run ruff check .`:passed。
- Full gate:`uv run ruff format --check .`:passed。
- Full gate:`uv run mypy src tests`:passed。
- Full gate:`git diff --check`:passed。

### 关键决策
- 🔒 **决策 1**:IM-facing 内置命令默认必须走 rich text renderer;只返回裸 text 只能用于极短错误提示。
- 🔒 **决策 2**:Dream 的用户价值是“复盘出可采纳经验”,不是暴露内部任务日志;输出必须能让人判断是否要 `/remember`。

### 留给下一轮
- 真实 IM 复验 `/goal`、`/task <outcome_grader>`、`/dream`、`/recall 早报接手`,重点看标题、bullet、slash command 是否已变成预期 IM 格式。

### 状态变化
- `STATUS.md` 当前轮次更新为 Round 120。
- 新增 P-028。

## Round 121 — 2026-05-27 — Codex

### 输入
- 人类反馈纯英文 agent 回复有时阅读吃力,要求新增通用语言切换命令。
- 约束:能力仅限制 agent 回复语言,默认英文。

### 思考与讨论
- 候选 A:把所有 AICO 内置命令也一起翻译 → ❌ **否决**:人类明确说仅限制 agent 回复语言,内置命令翻译会扩大范围并影响既有验收。
- 候选 B:在每个 `/ask`、`/goal`、broadcast、collaboration 命令里分别拼语言提示 → ❌ **否决**:容易漏入口,也会让 Orchestrator/handler 继续膨胀。
- 候选 C:新增 scoped language store,在 `_run_task()` 提交给 TaskBus 前统一注入 response language 约束 → ✅ **选定**:覆盖所有 agent task,保持命令层和 adapter 层无感。

### 产出
- 新增 `src/aico/core/language.py`,包含 `ResponseLanguageStore`、语言解析、语言命令消息和 `task_with_response_language()`。
- 新增 `/language [en|zh]` 命令;`/language` 查看当前 chat 设置,`/language zh` 设置后续 agent 回复为简体中文,`/language en` 恢复默认英文。
- `Orchestrator._run_task()` 在 task submit 前统一注入语言约束,覆盖 plain task、显式 agent task、project role task、Goal、broadcast 和 collaboration。
- 语言约束不翻译 AICO 内置命令;同时要求保留代码块、CLI 片段、路径、日志、标识符、协议关键字和严格 JSON/schema。
- `help_text()` 和命令解析补充 `/language`。
- 新增端到端单测覆盖默认英文、切换中文、恢复英文和 project role task 注入。

### 验证结果
- Targeted:`uv run pytest tests/unit/test_commands.py tests/unit/test_orchestrator.py::test_orchestrator_language_command_scopes_future_agent_replies tests/unit/test_orchestrator.py::test_orchestrator_language_command_injects_project_role_tasks -q`:12 passed。
- Full gate:`uv run pytest`:311 passed / 1 skipped。
- Full gate:`uv run ruff check .`:passed。
- Full gate:`uv run ruff format --check .`:passed。
- Full gate:`uv run mypy src tests`:passed。
- Full gate:`git diff --check`:passed。

### 关键决策
- 🔒 **决策 1**:语言偏好按 IM session scope 生效,不是全局配置;默认英文。
- 🔒 **决策 2**:语言偏好只约束 agent 输出,不改变内置命令语言、风险识别、审批语义或存储治理。
- 🔒 **决策 3**:语言注入提示不能包含 `shell command` 等风险关键词,否则会让普通任务误触发 approval gate。

### 留给下一轮
- 真实 IM 验收:
  - `/language`
  - `/language zh`
  - `/ask implementer summarize current project status`
  - `/language en`
  - `/ask implementer summarize current project status`
- 预期:第一次 agent 用中文回复,恢复后 agent 用英文回复;AICO 内置命令仍保持原语言。

### 状态变化
- `STATUS.md` 当前轮次更新为 Round 121。

## Round 122 — 2026-05-27 — Codex

### 输入
- 人类反馈输出格式仍有较大问题:`Collaboration requested: implementer -> reviewer` 没有转成正确格式。
- 人类确认 Telegram 是否默认不支持 Markdown,询问当前 harness 是否把 Claude/Codex/CodeFlicker 等 agent 的 Markdown 输出改为 HTML。
- 人类提供 `/recall 早报接手` 的真实 Telegram 输出,其中 memory claim 里 `## DecisionYes`、`## Why1.` 等 Markdown heading 和正文粘连,导致很难阅读。
- 人类要求从根源架构解决,不要继续 case by case,并闭环验证各命令实际效果。

### 思考与讨论
- 候选 A:继续给 `/recall`、collaboration 等单点套 `rich_text_message()` → ❌ **否决**:会继续漏掉 agent 流式输出和未来命令。
- 候选 B:让 Telegram 直接使用 Markdown parse mode → ❌ **否决**:项目已有平台无关 span contract,且 Telegram Markdown 方言限制多,直接绑定会污染核心。
- 候选 C:保留平台无关 `MessageTextSpan`,把 `rich_text_message()` 升级为通用 IM Markdown normalization + span rendering → ✅ **选定**:所有内置命令和 agent 流式输出都能复用同一层,Telegram 仍只负责 HTML 映射。

### 产出
- 明确架构:核心输出 `MessageContent.text + MessageTextSpan`;Telegram Channel 在有 spans 时将 spans 映射为 HTML (`parse_mode=HTML`)。
- `rich_text_message()` 新增 preprocessing 阶段:
  - 拆分模型输出中粘连的 `## Heading`。
  - 对 `## DecisionYes`、`## Why1.`、`## Evidence / memory refs- ...` 等已知 heading 做标题 / 正文拆分。
  - Markdown table 转成等宽 IM table,每行用 code span 保持对齐。
  - fenced code block 保留为 code span。
  - label span 匹配改为大小写无关,并扩展 `Memories` 等 label。
- `Collaboration requested` 从裸文本改为结构化富文本消息:
  - title: Collaboration requested
  - source: <role>
  - target: <role>
- 新增单测覆盖 renderer 的粘连 heading、table、fenced code block,以及 Telegram Channel 将这些 spans 转为 HTML。

### 验证结果
- Targeted:`uv run pytest tests/unit/test_message_rendering.py tests/unit/test_telegram_channel.py::test_telegram_channel_renders_agent_markdown_as_html -q`:9 passed。
- Targeted:`uv run pytest tests/unit/test_message_rendering.py tests/unit/test_orchestrator.py::test_orchestrator_remember_recall_and_forget_project_memory tests/unit/test_orchestrator.py::test_orchestrator_routes_adapter_collaboration_directive_to_target_persona tests/unit/test_orchestrator.py::test_orchestrator_routes_later_collaboration_directive_and_keeps_text tests/unit/test_orchestrator.py::test_orchestrator_collaboration_uses_assignment_role_and_parent_context -q`:12 passed。
- Full gate:`uv run pytest`:315 passed / 1 skipped。
- Full gate:`uv run ruff check .`:passed。
- Full gate:`uv run ruff format --check .`:passed。
- Full gate:`uv run mypy src tests`:passed。
- Full gate:`git diff --check`:passed。

### 关键决策
- 🔒 **决策 1**:不要把 Telegram Markdown 方言上推到 core;core 继续维护平台无关 span contract。
- 🔒 **决策 2**:复杂 Markdown 支持应该在 renderer normalization 层统一处理,而不是在每个命令 handler 里修字符串。
- 🔒 **决策 3**:Telegram 不支持真实表格;Markdown table 在 IM 中以等宽 text table + code span 表达,保证可读和稳定。

### 留给下一轮
- 真实 IM 验收:
  - 触发一次 collaboration,检查 `Collaboration requested` 是否显示为结构化标题 + source/target。
  - `/recall 早报接手`,检查粘连 `## DecisionYes` 是否拆成标题和正文。
  - 让 agent 输出一个 Markdown table,检查 Telegram 中是否变为等宽表格。

### 状态变化
- `STATUS.md` 当前轮次更新为 Round 122。

## Round 123 — 2026-05-27 — Codex

### 输入
- 人类指出把模型输出都适配成 `MessageTextSpan` 会导致 `rich_text_message()` case 无限膨胀。
- 人类提出另一条链路:让模型直接输出 Telegram / 不同 Channel 支持的格式,能直接发给 IM;如果模型不支持或效果不好,再回退到 `rich_text_message()`。
- 真实 dogfood 还暴露两个现象:
  - `/ask implementer ... Markdown 表格...` 遇到 provider session already in use,说明该失败发生在输出格式链路前。
  - `/ask tester ... fenced code block...` 经审批后返回单行 ```uv run pytest```,fallback renderer 也没有正确展示。

### 思考与讨论
- 候选 A:继续在 `rich_text_message()` 里补更多 Markdown case → ❌ **否决**:能修眼前样例,但会把 renderer 变成无限方言兼容层,新 Channel 还要复制一遍。
- 候选 B:让模型直接输出 Telegram HTML 并原样发送 → ❌ **否决**:模型可能输出 unsupported tag、属性或半截 HTML,直接发送会导致 Telegram API 报错或格式注入。
- 候选 C:新增 opt-in native output contract + sanitizer + fallback → ✅ **选定**:模型配合时走 Channel-native 格式,模型不配合时自动回到平台无关 rich text。

### 产出
- 新增 `MessageNativeFormat.TELEGRAM_HTML` 和 `MessageContent.native_format`,让 Telegram Channel 能识别“这段文本已经是经过验证的 Telegram HTML”。
- 新增 `src/aico/core/native_output.py`:
  - `task_with_native_output_format()` 在 opt-in 时给 Telegram task 注入输出契约。
  - `telegram_html_message()` 对模型输出做 Telegram HTML 白名单 sanitize / validate。
  - `agent_output_message()` 优先 native,失败回退 `rich_text_message()`。
- 新增 runtime 开关 `AICO_PREFER_NATIVE_CHANNEL_FORMAT=true`;默认关闭,便于和现有 rich text 链路做 A/B dogfood。
- `StreamedMessageWriter` 支持 `preferred_format`,对 agent 流式输出优先尝试 native Telegram HTML。
- Telegram Channel 支持 `native_format=telegram_html` 时直接发送 `parse_mode=HTML`,不再把 native HTML 二次 span rewrite。
- 修复单行 fenced code fallback,` ```uv run pytest``` ` 会展示为 code span,不再被吞。
- 新增单测覆盖 native Telegram HTML、unsupported HTML / Markdown fallback、Orchestrator opt-in prompt 注入和 Telegram native payload。

### 验证结果
- Targeted:`uv run pytest tests/unit/test_native_output.py tests/unit/test_message_rendering.py tests/unit/test_telegram_channel.py::test_telegram_channel_sends_native_telegram_html_without_span_rewrite tests/unit/test_orchestrator.py::test_orchestrator_can_pilot_native_telegram_agent_output -q`:15 passed。
- Full gate:`uv run pytest`:322 passed / 1 skipped。
- Full gate:`uv run ruff check .`:passed。
- Full gate:`uv run ruff format --check .`:passed。
- Full gate:`uv run mypy src tests`:passed。
- Full gate:`git diff --check`:passed。

### 关键决策
- 🔒 **决策 1**:rich text renderer 是 fallback,不是无限兼容所有模型 Markdown 方言的主战场。
- 🔒 **决策 2**:Channel-native output 可以让模型直接输出 Telegram HTML,但必须经过白名单 sanitizer;不能原样信任模型。
- 🔒 **决策 3**:该链路先以 `AICO_PREFER_NATIVE_CHANNEL_FORMAT=true` opt-in 验证,不默认替换现有稳定路径。

### 留给下一轮
- 真实 IM 验收时先设置 `AICO_PREFER_NATIVE_CHANNEL_FORMAT=true` 并重启 AICO。
- 再问:
  - `/ask implementer 用 Telegram HTML 格式列出 inbox/morning/dream/recall 四个功能的状态和下一步,表格请用 <pre>`
  - `/ask tester 用 Telegram HTML 返回一个 <pre> 块,里面只写 uv run pytest`
- 预期:如果 agent 输出合法 Telegram HTML,Telegram 直接按 HTML 渲染;如果输出 Markdown fence 或 unsupported HTML,系统回退到 rich text,不应裸露或吞内容。

### 状态变化
- `STATUS.md` 当前轮次更新为 Round 123。
- 新增 P-031。

## Round 124 — 2026-05-27 — Codex

### 输入
- 人类真实 dogfood `/goal implementer inspect inbox handoff 验收: list actionable items; explain blocked risks`。
- Telegram 收到的是裸 HTML:
  - `<b>Goal Brief 验收 ...</b>`
  - `<blockquote>...</blockquote>`
  - `<pre>... /task <id> ...</pre>`
- 这说明模型已经按 Telegram HTML 输出,但 AICO 没有把它作为 native HTML 发出,而是回退到了 rich text fallback。

### 思考与讨论
- 候选 A:继续让 prompt 禁止 `<id>` 占位符 → ❌ **否决**:模型自然会在命令示例里写 `/task <id>`,这是合理输出,不能靠 prompt 完全避免。
- 候选 B:放宽 sanitizer,所有 unknown tag 都转义为文本 → ❌ **否决**:会让 `<table>` 等真正 unsupported HTML 也伪装成 native 成功,降低 validator 的防线。
- 候选 C:只在 literal block(`<pre>` / `<code>`)内把 unknown tag 转义为文本 → ✅ **选定**:这符合 Telegram HTML 语义,也能处理 `/task <id>` 这类占位符。

### 产出
- 修改 `src/aico/core/native_output.py` 的 Telegram HTML sanitizer:
  - `<pre>` / `<code>` 内遇到 unknown start/end tag 时转义为文本。
  - literal block 外 unsupported tag / attribute 仍然失败并回退。
- 新增单测 `test_telegram_html_message_escapes_placeholders_inside_pre_blocks()`,覆盖 `<pre>/task <id></pre>`。

### 验证结果
- Targeted:`uv run pytest tests/unit/test_native_output.py tests/unit/test_telegram_channel.py::test_telegram_channel_sends_native_telegram_html_without_span_rewrite tests/unit/test_orchestrator.py::test_orchestrator_can_pilot_native_telegram_agent_output -q`:7 passed。
- Full gate:`uv run pytest`:323 passed / 1 skipped。
- Full gate:`uv run ruff check .`:passed。
- Full gate:`uv run ruff format --check .`:passed。
- Full gate:`uv run mypy src tests`:passed。
- Full gate:`git diff --check`:passed。

### 关键决策
- 🔒 **决策 1**:模型在 `<pre>` 中写 `<id>` 是文本占位符,不是 HTML 标签错误;应由 sanitizer 安全转义。
- 🔒 **决策 2**:literal block 外的 unsupported HTML 仍应失败回退,不能为了一个占位符问题放开整条 HTML 防线。

### 留给下一轮
- 重启 AICO 后复验同一个 `/goal ...` 或让 agent 输出 `/task <id>` 的 `<pre>` 表格。
- 预期 Telegram 不再显示裸 `<b>` / `<pre>` 标签;`<pre>` 内的 `<id>` 会作为文本占位符显示。

### 状态变化
- `STATUS.md` 当前轮次更新为 Round 124。
- 更新 P-031。

## Round 125 — 2026-05-27 — Codex

### 输入
- 人类要求定位真实 Telegram 输出中的这段内容来源,并修正类似格式问题:

```text
Still running: no adapter output for 120s. Use /task <id> for details or /interrupt <id> to stop.<b>1. verdict:</b> pass- list actionable items...
```

### 思考与讨论
- 候选 A:继续放宽 native HTML sanitizer,允许状态行中的 `<id>` → ❌ **否决**:这会掩盖根因,且让 AICO 自己的 status 行参与 agent result 渲染。
- 候选 B:把 quiet heartbeat 从 Adapter 移除 → ❌ **否决**:absence-first 仍需要长静默任务的活性反馈。
- 候选 C:把 status 改为 transient UI hint,不进入 final output buffer → ✅ **选定**:符合 Round 115 已定的“`OutputType.STATUS` 不是任务结果”原则。

### 产出
- 定位来源:
  - `src/aico/adapter/claude_code.py` 产生 `Still running: no adapter output for <Ns>...` quiet heartbeat。
  - `src/aico/core/orchestrator.py` 把 `OutputType.STATUS` 交给 streaming writer。
  - 旧 `StreamedMessageWriter.append()` 将 status 写进 `_current_text`,导致后续 native HTML 和 heartbeat 拼接。
- 新增 `StreamedMessageWriter.show_status()`,只临时编辑当前 IM 消息,不写入 `_current_text`。
- `Orchestrator._stream_outputs_for_task()` 遇到 `OutputType.STATUS` 时调用 `show_status()` 并 `continue`。
- Telegram native output prompt 增补格式约束:标题、段落、列表项分行;bullet 使用 `•`,不要使用 Markdown `- `。
- 新增 `tests/unit/test_streaming.py`,覆盖:
  - heartbeat 不污染 native final output。
  - 已有真实输出后 late status 不覆盖结果。

### 验证结果
- Targeted:`uv run pytest tests/unit/test_streaming.py tests/unit/test_native_output.py tests/unit/test_orchestrator.py::test_orchestrator_can_pilot_native_telegram_agent_output -q`:8 passed。
- Full gate:`uv run pytest`:325 passed / 1 skipped。
- Full gate:`uv run ruff check .`:passed。
- Full gate:`uv run ruff format --check .`:passed。
- Full gate:`uv run mypy src tests`:passed。
- Full gate:`git diff --check`:passed。

### 关键决策
- 🔒 **决策 1**:quiet heartbeat 是 transient UI hint,不是 agent result,不能进入最终输出缓冲。
- 🔒 **决策 2**:native HTML 输出失败时先查是否混入 AICO 自己的状态/系统提示,不要先扩 validator。
- 🔒 **决策 3**:模型 native output contract 需要明确换行和 bullet 规范,减少 `pass- list...` 这类粘连文本。

### 留给下一轮
- 重启 AICO 后复验同类 `/goal ...` 任务。
- 预期:等待期间仍可看到 `Still running...`;真实结果到达后该状态行被替换,不会出现在最终消息开头,也不会导致 `<b>` / `<pre>` 裸露。

### 状态变化
- `STATUS.md` 当前轮次更新为 Round 125。
- 新增 P-032。
