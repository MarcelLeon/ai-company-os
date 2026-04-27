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
