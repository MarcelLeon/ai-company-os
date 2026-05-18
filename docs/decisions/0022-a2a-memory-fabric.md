# ADR-0022: A2A Memory Fabric

**状态**:Accepted
**日期**:2026-05-15
**决策者**:Wang / Codex
**相关 Round**:Round 76

---

## 背景与问题

ADR-0020 定义了 Phase 7 第一版共享记忆使用本地可审计账本。ADR-0021 进一步明确:
记忆应该主要由 agent 主动维护,`/remember`、`/recall`、`/forget` 只是老板的控制权和排障入口。

新的问题是:如果 `/remember`、`/recall` 只作为 IM 命令被做进 Orchestrator,
lead agent 与其他 agent 之间的记忆交互会变成旁路功能,无法支撑真正的 A2A 协作。

Phase 7 需要一个符合 A2A 语义的记忆架构:
- agent 与 agent 之间的协作任务有项目 / 团队作用域记忆。
- boss 与 agent 的会话能抽取偏好、反馈和项目事实。
- 重要记忆能通过统一基础设施广播给 team 下 agent,而不是靠人工逐个转述。
- 在合适场景下,记忆广播可以减少 A2A 长消息传递,降低 token 消耗。

## 参考

- A2A 的核心边界是 Agent Card、Task、Message、Part、Artifact、Context 和异步更新。
- A2A 不要求暴露 agent 内部记忆;协作应交换任务、消息、artifact 和受控上下文。
- Attack on Memory 提供了可迁移的记忆治理思路:Memory Atom、evidence、scope、graph edge、time-window retrieval、selective disclosure、branch world model。

## 候选方案

### 方案 A — IM 命令驱动记忆
- 优点:实现最小,直接在 `/remember`、`/recall`、`/forget` 上收口。
- 缺点:lead agent 与其他 agent 无法自然共享记忆;老板仍会被迫维护记忆;不符合 A2A task / artifact 语义。
- 复杂度:低。

### 方案 B — 每个 agent 自己维护私有记忆
- 优点:对现有 A2A 消息链路影响小。
- 缺点:Claude、Codex、Cursor 等上下文割裂;lead agent 难以建立 team 共识;跨 agent 交接会继续烧 token。
- 复杂度:低。

### 方案 C — A2A Memory Fabric
- 优点:把记忆作为 AICO 的可治理基础设施,通过 A2A-compatible task、artifact、context 和 event 连接 lead agent、team agent 与 boss。
- 缺点:需要新增领域模型、治理策略和广播流程,第一版实现面比命令 MVP 大。
- 复杂度:中。

## 决策

选择 **方案 C:A2A Memory Fabric**。

Phase 7 的记忆层升级为 AICO 内部 A2A-compatible Memory Fabric,第一版不要求立刻暴露完整
HTTP A2A server,但内部模型必须能映射到 A2A:

- `MemoryAtom`:最小可验证记忆单元,记录 claim、evidence、scope、confidence、source、ttl、sensitivity。
- `MemoryScope`:必须包含 `owner_type` 和 `owner_id`,其中 owner 只能是:
  - `boss`:老板全局偏好 / 反馈。
  - `project`:项目级事实、约束、决策。
  - `team`:项目内 team 共识。
  - `role`:项目内某 role 的长期工作偏好或边界。
  - `agent`:某 agent 在某 project/team 下的局部交接信息。
- `MemoryEdge`:表达 `supports`、`contradicts`、`derived_from`、`broadcast_to`、`supersedes`。
- `MemoryIntent`:agent 或 boss 发起的记忆动作,例如 `capture`、`recall`、`broadcast`、`forget`、`consensus_request`。
- `MemoryArtifact`:A2A task 的结构化产物,承载写入结果、召回包、广播 receipt 或共识结果。
- `MemoryGovernor`:按 project / team / role / sensitivity / confidence 做选择性披露。
- `MemoryBroadcast`:统一广播机制,把重要记忆发布到同 project + team 下的 agent 收件箱和 prompt stack cache。

## A2A 映射

| AICO Memory Fabric | A2A 概念 | 说明 |
|---|---|---|
| Lead agent 请求 reviewer 协作 | Task | 协作仍是 stateful task,复用 TaskBus、审批、审计和中断 |
| 任务中的说明 / 追问 | Message | 只放当前任务必要说明,避免塞完整历史 |
| 记忆片段 / 证据引用 / 召回包 | Part | 用结构化 data part 表达 memory packet |
| agent 产出的方案 / 结论 / 记忆写入结果 | Artifact | 任务产物中可包含 `memory_artifact` |
| project/team/thread 逻辑分组 | Context | `context_id = project_id + team_id + conversation_id/task_id` |
| 记忆广播 / receipt / hook | Push / event extension | 内部先用 audit/event bus;未来可映射到 A2A push notification 或 extension |

AICO 不向下游 agent 暴露完整 memory store。agent 只能看到 MemoryGovernor 投影后的 `MemoryPacket`,
这符合 A2A “不需要访问对方内部状态、记忆或工具”的边界。

## 记忆分层

### Boss Memory
- 作用域:`boss:<boss_id>`。
- 内容:老板偏好、反馈、稳定工作习惯、审批偏好、产品语义偏好。
- 写入来源:boss 与 agent 的对话摘要抽取。
- 写入要求:LLM 必须判断这是 boss 全局偏好还是 project-specific feedback;低置信时进入候选态,需要 lead 或 boss 确认。

### Project Memory
- 作用域:`project:<project_id>`。
- 内容:北极星、阶段目标、架构决策、长期约束、已否决方案。
- 共享范围:同 project 下所有 team / role / agent 可经治理投影后读取。

### Team Memory
- 作用域:`team:<project_id>/<team_id>`。
- 内容:当前 team 的共识、约定、正在执行的策略、跨 role 交接。
- 共享范围:同 project + team 下所有 appointment。
- 禁止跨 project 或跨 team 默认共享。

### Role Memory
- 作用域:`role:<project_id>/<team_id>/<role_id>`。
- 内容:某岗位在该项目中的偏好、职责边界、常见坑和验收方式。
- 共享范围:该 role 与 lead agent;其他 role 需要 MemoryGovernor 投影。

### Agent Working Memory
- 作用域:`agent:<project_id>/<team_id>/<agent_id>`。
- 内容:某 agent 的短期工作状态、草稿、局部推理摘要。
- 默认不广播,只在交接、任务完成或 lead 要求时提取为 team/project memory。

## 核心流程

### 1. A2A 任务发起前召回

1. boss 或 lead agent 发起项目任务。
2. Orchestrator 构造 `MemoryIntent(recall)`。
3. Memory Fabric 按 boss + project + team + role 检索少量高置信记忆。
4. MemoryGovernor 生成 `MemoryPacket`。
5. Prompt Stack 注入 MemoryPacket,并保留 citations。

### 2. boss 会话摘要提取

1. boss 与 agent 对话结束或任务完成。
2. lead agent 触发 `MemoryIntent(capture)`。
3. LLM 抽取候选记忆并标注层级:
   - boss global
   - project
   - team
   - role
   - agent working
4. 低置信或敏感记忆进入 `candidate` 状态。
5. 高置信偏好 / feedback 写入 JSONL 账本,并记录 evidence、source、created_by、confidence、reason。

### 3. Team 记忆广播

1. agent 认为某条记忆会影响 team 协作,发起 `MemoryIntent(consensus_request)`。
2. lead agent 或策略判断是否可广播:
   - project/team scope 必须明确。
   - confidence 达标。
   - 不能越过 sensitivity 策略。
   - 与现有记忆冲突时先标 `contradicts`,不要直接覆盖。
3. 通过 `MemoryBroadcast` 写入 team memory,并给 team 下 appointment 生成 receipt。
4. 后续同 team agent 的 prompt stack 会自动包含该记忆摘要。

老板显式开会也走同一机制:

```text
/meeting remember 这个项目后续不要把记忆设计成老板手动维护数据库
```

它只是 boss 主动发起的 `MemoryIntent(broadcast)`,底层仍复用 MemoryBroadcast。

### 4. 用记忆广播减少消息传递

对重复、稳定、会被多个 agent 用到的上下文,AICO 优先写入 team memory 并广播 receipt。
A2A task message 只传:

- task goal
- target role
- memory packet ids / citations
- delta context

目标 agent 再本地召回 MemoryPacket。这样避免 lead agent 每次把完整背景复制进消息。

适用场景:
- team 已达成的项目约束。
- boss 的稳定偏好。
- 已确认的架构决策。
- 跨 role 都要知道的验收标准。

不适用场景:
- 一次性临时讨论。
- 低置信推测。
- 需要对方立即逐字阅读的短内容。
- 敏感信息或只允许某 role 查看原文的证据。

## 实现切片

### Phase 7A — 可审计记忆模型
- 扩展 ADR-0020 的 `MemoryRecord` 为 `MemoryAtom` 形态。
- 增加 `MemoryScope`、`MemoryEvidence`、`MemoryEdge`、`MemoryIntent`、`MemoryArtifact`。
- `JsonlMemoryStore` 仍是权威源,先不引入图数据库和向量库。

### Phase 7B — Prompt Stack 召回
- 当前 project/team/role 自动召回少量高置信记忆。
- boss memory 只注入偏好摘要,不泄漏其它 project 私有事实。

### Phase 7C — Capture 与层级判断
- boss 对话结束和 task completion 后抽取候选记忆。
- LLM 给出 scope 建议与 reason;低置信走 candidate。

### Phase 7D — Team Broadcast
- 新增内部 `MemoryBroadcastService`。
- 支持 lead agent 发起共识广播。
- 支持老板会议命令触发同一广播路径。

### Phase 7E — Token-saving A2A experiment
- 在 A2A 协作任务中传 memory ids + delta context。
- 对比“完整背景消息”与“memory packet ids”两种模式的 token / 成功率 / 错误率。
- 仅在有回放验收后作为默认行为。

## 后果

### 正面后果
- `/remember` / `/recall` 不再是孤立命令,而是 Memory Fabric 的人工入口。
- lead agent 与 team agent 可以通过受控 MemoryPacket 共享上下文。
- boss 偏好与 feedback 可以沉淀为全局或项目记忆,而不是散在聊天里。
- 记忆广播给 A2A 协作提供了低 token 的上下文同步路径。

### 负面后果
- 第一版模型比简单 JSONL 记录更复杂。
- 需要更多测试覆盖 scope 隔离、治理投影和广播 receipt。
- LLM 抽取 boss 偏好可能误判 scope,必须有 confidence 和 candidate 状态兜底。

### 我们接受这些代价是因为

AI Company OS 的记忆层是让一个老板管理多个 agent 团队的协作底座,不是一个命令式笔记本。
如果没有 A2A-compatible Memory Fabric,Phase 7 很快会在 lead-agent 协作和 boss 偏好沉淀上返工。

## 不再做的事

- 不把跨 project / 跨 team 记忆默认共享。
- 不把 agent 私有 working memory 直接暴露给其他 agent。
- 不把记忆广播做成 IM 群发消息;IM 只是展示入口,基础能力在 Memory Fabric。
- 不为了节省 token 牺牲可审计性;memory packet 必须有 citations。
- 不在 Phase 7 第一版引入向量库或图数据库;JSONL 仍是权威源。

## 相关链接

- ADR-0009
- ADR-0020
- ADR-0021
- ROUNDS Round 76
- Attack on Memory:https://github.com/MarcelLeon/attack-on-memory
- A2A specification:https://a2a-protocol.org/v0.3.0/specification/
