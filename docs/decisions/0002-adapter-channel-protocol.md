# ADR-0002: Adapter / Channel 协议

**状态**:Accepted
**日期**:2026-04-27
**决策者**:Wang / Codex(协作)
**相关 Round**:Round 4

---

## 背景与问题

Phase 1 要跑通"Telegram 文本消息 -> 编排核心 -> Claude Code -> Telegram 文本/编辑消息"。在写具体插件之前,必须先固定核心依赖的协议边界,否则 Telegram 或 Claude Code 的特殊行为容易渗入核心。

北极星要求协议优先、AI 适配器化、状态可观测、能力可插拔。因此本 ADR 决定 `AIAdapter` 和 `IMChannel` 的 Phase 1 最小接口。

## 候选方案

### 方案 A — 同步阻塞接口

- 优点:实现简单,一次调用拿到最终结果。
- 缺点:不适合远程异步指挥,长任务无法及时汇报进度,中断和审批会变得别扭。
- 复杂度:低。

### 方案 B — 异步接收 + 流式输出 + 显式状态

- 优点:匹配 AI CLI 的流式输出和 IM 消息编辑,天然支持状态查询和中断。
- 缺点:测试和实现需要处理 async generator,比同步接口复杂。
- 复杂度:中。

### 方案 C — 事件总线优先,Adapter / Channel 只收发事件

- 优点:解耦最彻底,后续多 Adapter / 多 Channel 扩展空间大。
- 缺点:Phase 1 过重,会在还没有真实插件前引入事件模型和生命周期复杂度。
- 复杂度:高。

## 决策

我们选择 **方案 B:异步接收 + 流式输出 + 显式状态**。

`AIAdapter` Phase 1 接口:
- `name: str`
- `capabilities() -> frozenset[Capability]`
- `receive_task(task: Task) -> TaskAck`
- `stream_output(task_id: str) -> AsyncIterator[TaskOutput]`
- `status() -> AdapterStatus`
- `interrupt(task_id: str) -> None`
- `health_check() -> HealthStatus`

`IMChannel` Phase 1 接口:
- `name: str`
- `start() -> None`
- `stop() -> None`
- `send_message(target, content) -> SentMessage`
- `edit_message(target, message_id, content) -> None`
- `delete_message(target, message_id) -> None`
- `on_incoming(handler) -> None`
- `health_check() -> HealthStatus`

协议数据对象使用 Pydantic v2 frozen model,核心对象包括 `Task`、`TaskAck`、`TaskOutput`、`IncomingMessage`、`MessageContent`、`ChannelTarget` 和 `SentMessage`。

## 决策理由

- `receive_task` 立即返回 ack,可以让 IM 端快速反馈"已接收 / 忙 / 拒绝"。
- `stream_output` 保留真实 AI CLI 的增量输出,也能驱动 IM `edit_message` 做远程进度刷新。
- `status`、`health_check`、`interrupt` 是可观测、可中断的最小底座。
- `IMChannel` 明确保留 `edit_message`,因为 Phase 1 的 Telegram UX 要靠编辑同一条消息承载流式输出。
- 暂不把 EventBus 放进协议,避免 Phase 1 还没跑通时过早引入全局消息系统。

## 后果

### 正面后果

- 编排核心只依赖协议,不依赖 Telegram 或 Claude Code 具体实现。
- FakeAdapter / FakeChannel 可以完整测试任务流转。
- 后续接 Codex、OpenClaw、飞书、QQ 时有稳定边界。

### 负面后果

- 具体 Adapter 必须维护任务输出流,实现成本高于同步调用。
- Channel 必须实现消息编辑能力或清楚声明不支持对应 UX。
- 当前协议只支持文本消息模型,多模态需要后续 ADR 扩展。

### 我们接受这些代价是因为

- 远程异步协作的体验核心就是"能看到进度、能中断、能回放状态"。
- 文本单链路足够验证 Phase 1,多模态和复杂事件总线可以晚一点引入。

## 不再做的事

在 ADR-0002 有效期间:
- 不把具体 AI CLI 的参数、prompt、工作目录策略放进核心协议。
- 不把 Telegram Bot API 的 message/update 结构暴露给核心。
- 不在 Phase 1 引入全局 EventBus 作为 Adapter/Channel 的唯一通信方式。

除非真实 Telegram 或 Claude Code MVP 证明接口无法表达必要行为,否则不修改核心签名。

## 相关链接

- ROUNDS Round 4
- ADR-0001
- 相关代码:`src/aico/adapter/base.py`, `src/aico/channel/base.py`, `src/aico/core/models.py`
