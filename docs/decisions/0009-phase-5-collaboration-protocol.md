# ADR-0009: Phase 5 AI 间协作协议

**状态**:Accepted
**日期**:2026-04-28
**决策者**:Codex
**相关 Round**:Round 19

---

## 背景与问题

Phase 5 的验收标准是“AI 之间可以互相 @ 协作,任务编排成型”。B-002 一直延后到 Phase 5 前解决:AI A 想 @ AI B 协作时,到底走 IM 消息总线、内部 Agent2Agent 协议,还是 RPC?

当前系统已经有 Persona、AdapterRegistry、TaskBus、审计和审批门禁。两个真实 Adapter 都在同一编排进程里,还没有跨进程 Agent Server。

## 外部协议现状

- A2A 是面向 Agent↔Agent 的开放协议,强调能力发现、消息 / artifact 交换和长任务协作。
- ACP 早期是 IBM/BeeAI 的 Agent Communication Protocol,现在已并入 A2A 生态。
- MCP 更适合作为 Agent↔工具 / 上下文协议,不作为 Phase 5 的 Agent↔Agent 主通道。

## 候选方案

### 方案 A — 走 IM 消息总线
- 优点:最有群聊感,所有协作都对人可见。
- 缺点:核心协作语义耦合 Telegram;未来换 IM 通道时会重复实现。
- 复杂度:低。

### 方案 B — 直接实现 A2A HTTP 服务
- 优点:更接近开放协议,未来跨进程 / 跨框架更自然。
- 缺点:当前 Adapter 都在同一进程内,立刻引入 HTTP 服务、Agent Card、SSE 会扩大 Phase 5 MVP。
- 复杂度:中高。

### 方案 C — 内部 A2A-inspired 协作指令
- 优点:核心先定义“source persona → target persona → task payload”的协作语义;复用现有 TaskBus、审批、审计、状态机;以后可映射到 A2A。
- 缺点:不是完整 A2A 兼容实现,当前只支持文本协作指令。
- 复杂度:低。

### 方案 D — RPC 直接调用 Adapter
- 优点:最简单。
- 缺点:绕过 TaskBus,失去审批、审计和群聊可观测性;也失去“真实团队协作”的感觉。
- 复杂度:低。

## 决策

选择 **方案 C — 内部 A2A-inspired 协作指令**。

## 决策理由

- 新协作任务仍是普通 `Task`,因此自动复用风险识别、审批、审计和状态机。
- 不耦合 Telegram Channel;Telegram 只负责展示“Collaboration requested”。
- 不直接实现完整 A2A HTTP 服务,避免 Phase 5 一开始就变成协议工程。
- 协作指令采用显式语法 `@persona: request`,足够贴近“AI 之间互相 @”的产品体验。

## Phase 5 MVP 行为

当 Adapter 输出文本行形如:

```text
@reviewer: inspect this implementation for missing tests
```

`Orchestrator` 会:

1. 识别为协作请求。
2. 在 IM 中发送 `Collaboration requested: implementer -> reviewer`。
3. 生成目标 persona 的普通 `Task`,payload 包含来源 persona 和请求内容。
4. 通过 `TaskBus` 派发,并把目标 persona 输出回同一会话。

## 后果

### 正面后果
- Phase 5 可以马上真实 dogfooding,不需要部署新服务。
- 协作链路具备审批、审计、状态可观测能力。
- 后续实现 A2A HTTP 时,可以把内部协作请求映射到 A2A task/message。

### 负面后果
- 目前只支持单层协作,避免无限递归。
- 协作指令依赖 Adapter 按约定输出文本,不是强 schema。
- 暂不支持 artifact / file / multimodal 协作。

### 我们接受这些代价是因为
- Phase 5 需要先证明“AI 能请求另一个 AI 协作”的闭环,不是一次性完成跨厂商协议互通。

## 不再做的事

- Phase 5 MVP 不把 Telegram 作为内部协作总线。
- Phase 5 MVP 不直接实现完整 A2A HTTP server/client。
- 不绕过 `TaskBus` 直接 RPC 调用 Adapter。

## 相关链接

- ROUNDS Round 19
- BLOCKERS B-002
- A2A specification:https://google-a2a.github.io/A2A/specification/
- ACP migration:https://docs.beeai.dev/community-and-support/acp-a2a-migration-guide
- 相关代码:`src/aico/core/collaboration.py`, `src/aico/core/orchestrator.py`
