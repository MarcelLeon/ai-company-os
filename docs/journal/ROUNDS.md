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
