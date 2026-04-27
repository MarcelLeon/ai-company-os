# Adapter Protocol — 适配器协议

> 本文定义两个核心接口的草案:`AIAdapter`(AI 工具适配器)和 `IMChannel`(IM 通道)。
>
> ADR-0002 已接受 Phase 1 最小接口。本文保留语言中立说明,Python 代码见 `src/aico/adapter/base.py` 和 `src/aico/channel/base.py`。

---

## 设计原则

1. **接口最小化**:只放共性方法,易变性封装在实现内
2. **流式优先**:输出用流而不是阻塞返回
3. **异步优先**:接收任务立即返回 ack,实际执行异步进行
4. **可中断**:每个长操作都必须能被中断

---

## AIAdapter 接口草案

### 概念性签名(语言中立)

```
interface AIAdapter:
    name() -> String
    capabilities() -> Set<Capability>
    receiveTask(task: Task) -> TaskAck
    streamOutput(taskId: TaskId) -> Stream<TaskOutput>
    status() -> AdapterStatus
    interrupt(taskId: TaskId) -> Void
    healthCheck() -> HealthStatus
```

### 各方法语义

#### `name() -> String`
适配器的唯一标识符,如 `"claude-code"`、`"codex"`。

#### `capabilities() -> Set<Capability>`
该适配器能干什么。`Capability` 是枚举:
- `CODE_EDIT`(改代码)
- `CODE_REVIEW`(审查代码)
- `SHELL_EXEC`(执行 shell)
- `WEB_BROWSE`(浏览网页)
- `LONG_RUNNING`(支持长任务)
- `STREAM_OUTPUT`(支持流式输出)
- `INTERRUPTIBLE`(支持中断)
- ... 由实际接入的 AI 工具决定

#### `receiveTask(task: Task) -> TaskAck`
接收任务。**立即返回**,不阻塞。
- 返回 `TaskAck.ACCEPTED` / `BUSY` / `REJECTED`
- 实际执行异步进行,通过 EventBus 上报状态

#### `streamOutput(taskId: TaskId) -> Stream<TaskOutput>`
订阅某任务的流式输出。
- Java 用 `Flux<TaskOutput>`
- Python 用 `AsyncIterator[TaskOutput]`
- TypeScript 用 `AsyncGenerator<TaskOutput>`

#### `status() -> AdapterStatus`
当前适配器状态:
- `IDLE`(空闲)
- `BUSY`(执行中)
- `BLOCKED`(被卡住,等待外部输入)
- `WAITING_APPROVAL`(等待审批)
- `OFFLINE`(离线)

#### `interrupt(taskId: TaskId) -> Void`
中断指定任务。
- **必须**在 5 秒内响应
- 中断后任务状态置 `INTERRUPTED`
- 不能保证"无副作用",仅保证"尽快停止"

#### `healthCheck() -> HealthStatus`
存活检查。返回 `OK` / `DEGRADED` / `FAILED`。

---

## IMChannel 接口草案

### 概念性签名

```
interface IMChannel:
    name() -> String
    start() -> Void
    stop() -> Void
    sendMessage(target: ChannelTarget, content: MessageContent) -> MessageId
    editMessage(target: ChannelTarget, messageId: MessageId, content: MessageContent) -> Void
    deleteMessage(target: ChannelTarget, messageId: MessageId) -> Void
    onIncoming(handler: IncomingMessageHandler) -> Void
    healthCheck() -> HealthStatus
```

### 各方法语义

#### `name() -> String`
通道唯一标识,如 `"telegram"`、`"feishu"`。

#### `start() / stop()`
通道生命周期管理。`start` 启动接收(轮询或 Webhook 监听),`stop` 优雅停止。

#### `sendMessage / editMessage / deleteMessage`
- **关键**:`editMessage` 是流式输出 UX 的核心——通过持续编辑同一条消息显示进度,这是模拟"灵动岛"的方案
- `deleteMessage` 仅在错误恢复时使用

#### `onIncoming(handler)`
注册消息接收回调。`IncomingMessage` 包含:
- 来源(私聊 / 群聊 ID)
- 发送者
- @ 谁(如有)
- 消息内容(可能多模态:文本 / 图片 / 文件)
- 时间戳

#### `healthCheck()`
通道是否仍连接 IM 平台。

---

## 通用数据类型

### `Task`
```
Task:
    taskId: TaskId
    payload: String           # 任务内容
    requesterId: UserId       # 谁发起的
    targetPersona: PersonaId  # 给哪个 AI 人格
    contextRef: ContextRef?   # 关联的对话上下文(用于记忆层)
    metadata: Map<String, Any>
    createdAt: Instant
```

### `TaskOutput`
```
TaskOutput:
    taskId: TaskId
    sequence: Int              # 输出序号(用于排序)
    type: OutputType           # TEXT / TOOL_CALL / ERROR / DONE
    content: String
    timestamp: Instant
```

### `IncomingMessage`
```
IncomingMessage:
    channelName: String
    sourceId: ChannelTarget    # 群 / 私聊唯一标识
    senderId: UserId
    mentions: List<PersonaId>  # @ 了哪些 Persona
    content: MessageContent    # 多模态
    timestamp: Instant
    rawRef: String             # 原始消息 ID,用于回复或编辑
```

---

## 协议演化原则

### 添加方法(向后兼容)
- 加新方法到接口 → 默认实现抛 `UnsupportedOperationException` 或返回 `Optional.empty`
- 等所有实现都跟进后,移除默认实现

### 修改方法签名(破坏性变更)
- **必须写 ADR**
- 必须列出受影响的所有实现
- 必须批量迁移,不允许长期共存两个版本

### 弃用方法
- 标 `@Deprecated` / `DeprecationWarning`
- 在 `CHANGELOG.md` 标记
- 给出迁移指南
- 至少 2 个 Phase 后才能删除

---

## 实现 Adapter 时的检查清单

新接入一个 AI 工具时,实现 Adapter 必须:

- [ ] 实现 `AIAdapter` 全部方法
- [ ] 提供 `capabilities()` 真实返回(不要谎报能力)
- [ ] 流式输出真正流式(不要先收齐再吐)
- [ ] 实现可中断(测试:能 5 秒内响应中断)
- [ ] 实现 health check
- [ ] 单测覆盖 receive / stream / interrupt 三条主路径
- [ ] 集成测试用真实 AI 工具至少跑一个 hello world
- [ ] 加入 PITFALLS 关于这个 AI 工具的特性 / 坑(如 token 限制、CLI 行为)

---

## 实现 Channel 时的检查清单

新接入一个 IM 时:

- [ ] 实现 `IMChannel` 全部方法
- [ ] `editMessage` 真的能更新(用于流式 UX)
- [ ] 处理 IM 平台的限流策略(指数退避)
- [ ] 长消息分段(超过 IM 平台单条上限时)
- [ ] 单测 + 集成测试
- [ ] 加入 PITFALLS 关于这个 IM 的特性

---

## 这个协议不会做的事

为了保持简洁,**协议层不解决**以下问题:

- AI 之间的协作(那是更高层的"协作协议",见 BLOCKERS B-002)
- 跨 Channel 的消息同步(应该在编排核心层解决)
- 持久化(应该在 Repository 层解决)
- 鉴权(应该在 Channel 实现内 + 编排核心的 AccessControl 中解决)
