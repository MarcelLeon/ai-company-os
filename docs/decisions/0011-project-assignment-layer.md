# ADR-0011: Project Assignment Layer

**状态**:Accepted
**日期**:2026-05-04
**决策者**:Wang / Codex(协作)
**相关 Round**:Round 29

---

## 背景与问题

Phase 5 已经有 Agent Session、provider resume 和能力展示命令,但真实使用痛点仍然明显:用户日常迭代的是一个或多个完整项目,不是孤立 session。Telegram 里如果只暴露 session,用户无法感知“哪个项目在推进、谁在负责、当前进展、风险和日报/周报”。

需要把技术 session 提升为公司语义:Agent 是员工,Project 是项目,而员工在项目中的岗位、session、权限和 prompt 应由一个显式中间层表达。

## 候选方案

### 方案 A — Agent 直接多对多绑定 Project
- 优点:模型简单。
- 缺点:无法表达同一个 Agent 在不同项目里的 role、session、权限和工作目录差异。
- 复杂度:低,但后续容易混乱。

### 方案 B — 引入 Assignment 作为项目任命
- 优点:明确表达 Agent 在某个 Project 里的岗位;session、状态、权限和 prompt 都可挂在 Assignment/seat 上。
- 缺点:多一个核心概念,需要配置和命令都围绕它设计。
- 复杂度:中。

### 方案 C — 用 slash command 动态创建/修改任命
- 优点:聊天里操作直观。
- 缺点:组织结构会被随手修改,需要权限、回滚、审计和配置持久化;MVP 过重。
- 复杂度:高。

## 决策

选择 **方案 B:引入 Project Assignment Layer**。

Project 和 Agent 不直接绑定。它们通过 Assignment 关联:

```text
Agent 1 --- n Assignment n --- 1 Project
```

Assignment 是“员工在某个项目里的岗位/工位”。provider session、当前状态、权限边界、工作目录、role prompt 和最近产出都绑定到 Assignment,不裸挂在 Agent 上。

Assignment 主要通过配置文件维护;MVP slash command 只做查看和切换,不做组织架构增删改。

## 决策理由

- Project 是用户真正关心的上下文边界,session 只是实现细节。
- 同一个 Agent 可以参与多个 Project,但必须有独立 Assignment/seat,避免上下文串线。
- Assignment 能自然表达公司味:员工、项目、岗位、工位、状态和职责。
- 组织结构配置需要可追溯和可 review,不应在 Telegram 里随手改。
- Prompt 需要分层维护:Agent base prompt、Role prompt、Project brief、Runtime context 分开拼装,避免每个 Assignment 复制大段 prompt。

## 后果

### 正面后果

- 后续可以实现 `/projects`、`/project aico`、`/use project aico`、`/assignments aico` 等公司语义命令。
- 项目日报、周报、风险简报可以从 Project + Assignment + audit/task timeline 聚合。
- Dynamic Island / Mac menu bar 等 UI 可以消费 Project/Assignment 状态,而不是直接展示裸 session。

### 负面后果

- 需要新增配置模型和 prompt 渲染边界。
- 现有 `/sessions`、`/new`、`/use` 需要逐步迁移为 project-scoped 语义。
- 需要谨慎处理旧 persona/agent 命令兼容,避免一次性重写 Phase 5。

### 我们接受这些代价是因为

这是从“AI CLI 会话管理器”走向“AI 公司操作系统”的关键抽象。没有 Project Assignment Layer,后续日报、周报、风险、看板和灵动岛都会缺少稳定语义。

## 不再做的事

- MVP 不做 `/assign claude to aico as implementer` 这类聊天内组织架构修改命令。
- MVP 不做 handoff。项目做到一半临时换 Agent 需要上下文迁移和未完成假设传递,复杂度高,暂不进入主路径。
- 不把 provider session 直接绑定到 Agent 全局状态。
- 不把每个 Assignment 的完整 prompt 复制成一大段文本;必须分层拼装。

## 相关链接

- ROUNDS Round 29
- ADR-0010:Agent Session 与 Harness 边界
- 相关文档:`docs/architecture/project-assignment-layer.md`
