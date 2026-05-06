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
