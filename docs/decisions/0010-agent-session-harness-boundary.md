# ADR-0010: Agent Session 与 Harness 边界

**状态**:Accepted
**日期**:2026-04-29
**决策者**:Wang / Codex
**相关 Round**:Round 24

---

## 背景与问题

Phase 5 后,AICO 已能通过 IM 派发任务给 Claude/Codex,但真实体验仍像“一次性命令转发器”:
- 没有 AICO 层会话管理,无法表达“继续和这个 Claude/Codex 会话聊”。
- `/status` 只展示粗粒度 idle/busy,用户体感不到底层 Agent 的 tools、skills、slash command、MCP、职责范围和会话状态。
- Claude Code / Codex CLI 自己已有 session、resume、tools、skills、plugins 等能力;AICO 不应重复实现一套 tool loop。

## 候选方案

### 方案 A — 继续只封装 CLI prompt
- 优点:最简单,不改变当前链路。
- 缺点:无会话引用,也无法展示底层能力;AICO 仍像转发器。
- 复杂度:低。

### 方案 B — AICO 自研完整 Agent loop / tools / skills runtime
- 优点:统一能力强,可完全控制工具执行。
- 缺点:会重复造 Claude/Codex 已经有的 agent runtime,维护成本高,也容易偏离当前 Phase 5。
- 复杂度:高。

### 方案 C — 引入 pi-mono 作为较重 Agent runtime
- 优点:可能复用成熟的 agent/tool/skill loop。
- 缺点:会引入新的运行时和技术栈边界;当前核心痛点是会话和能力可见性,不是替换 Claude/Codex loop。
- 复杂度:中到高。

### 方案 D — AICO 只做薄 Agent Harness 门面
- 优点:保留 Claude/Codex 自身 tools/skills/session 能力,AICO 只做 IM 入口、会话引用、能力展示、审批审计和协作编排。
- 缺点:底层能力差异仍由 Adapter 翻译,无法完全统一所有 provider 行为。
- 复杂度:中。

## 决策

选择 **方案 D — AICO 只做薄 Agent Harness 门面**。

核心约束:

> AICO Agent Harness is a session and capability facade, not a tool execution runtime.

也就是说,AICO 的薄 harness 是“会话和能力门面”,不是“工具执行运行时”。

## 决策理由

- 会话管理是 IM 侧必须拥有的用户体验能力;AICO 需要知道“当前聊天正在使用哪个 provider session”。
- 模型上下文、tools、skills、slash command 的真实来源仍属于 Claude/Codex/provider;AICO 只保存引用并做统一展示。
- 短期不接 pi-mono,避免为了解决会话可见性而引入较重 agent runtime。
- 该边界仍允许未来增加 `PiMonoAdapter`,但它只是另一个 Adapter/provider,不是主线前提。

## 后果

### 正面后果
- AICO 可以支持 `/sessions`、`/use <session>`、`/agent claude`、`/skills claude` 这类体验命令。
- 会话上下文不中断依赖 provider session id / resume 能力,不需要 AICO 复制完整聊天历史。
- Claude/Codex 的 tools 和 skills 保持 provider-owned,AICO 不需要维护重复 registry。

### 负面后果
- 不同 provider 暴露 session/tools/skills 的方式不同,Adapter 需要做翻译。
- AICO 无法保证所有 provider 都支持相同的 resume/fork/session 语义。
- 真正的多任务并发仍需额外设计 workspace lock、session lock 和 worker slot。

### 我们接受这些代价是因为
- 当前北极星要求远程管理 AI 团队,不是重写所有 AI 工具。
- 先把“谁在工作、在哪个会话、能做什么”讲清楚,比过早自研 loop 更重要。

## 不再做的事

- 不在 Phase 5 主线实现 AICO 自己的 tool execution runtime。
- 不在短期把 pi-mono 作为主链路依赖。
- 不把 Claude/Codex 的 tools/skills 复制到 AICO 内维护;只通过 Adapter 翻译和展示 provider 自身能力。

## 相关链接

- ROUNDS Round 24
- 相关代码:`src/aico/core/agent_session.py`
