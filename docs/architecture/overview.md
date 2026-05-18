# Architecture Overview — 系统全景

> 本项目的高层架构。技术细节在子文档,本文只画大图。

---

## 一句话架构

> **三层架构 + 双向通信**:IM 通道层 ↔ 编排核心层 ↔ AI 适配器层,每层都可插拔。

---

## 系统图(文字版)

```
┌─────────────────────────────────────────────────────────────┐
│                       人类用户(IM 端)                       │
│  Telegram / 飞书 / QQ / 企微 / Slack ...                     │
└─────────────────────────────────────────────────────────────┘
                              ↑↓
┌─────────────────────────────────────────────────────────────┐
│                   IM 通道层(可插拔)                         │
│  TelegramChannel / FeishuChannel / QQChannel ...            │
│  实现 IMChannel 接口                                         │
└─────────────────────────────────────────────────────────────┘
                              ↑↓
┌─────────────────────────────────────────────────────────────┐
│                      编排核心层                              │
│  ┌────────────┐  ┌────────────┐  ┌──────────────────────┐  │
│  │  Router    │  │  TaskBus   │  │  Persona Engine      │  │
│  │  (路由)     │  │  (任务总线) │  │  (人格化)            │  │
│  └────────────┘  └────────────┘  └──────────────────────┘  │
│  ┌────────────┐  ┌────────────┐  ┌──────────────────────┐  │
│  │  Approval  │  │  Memory    │  │  Audit & Trace       │  │
│  │  (审批)     │  │  (记忆)     │  │  (审计追踪)           │  │
│  └────────────┘  └────────────┘  └──────────────────────┘  │
│  ┌────────────────────────────────────────────────────────┐│
│  │                 EventBus(状态广播)                     ││
│  └────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
                              ↑↓
┌─────────────────────────────────────────────────────────────┐
│                  AI 适配器层(可插拔)                        │
│  ClaudeCodeAdapter / CodexAdapter / OpenClawAdapter / ...   │
│  实现 AIAdapter 接口                                         │
└─────────────────────────────────────────────────────────────┘
                              ↑↓
┌─────────────────────────────────────────────────────────────┐
│                  本地 AI 工具(实际进程)                      │
│  Claude Code CLI / Codex CLI / OpenClaw / 内部 CLI          │
└─────────────────────────────────────────────────────────────┘
```

---

## 可编辑架构图

- [`aico-layered-architecture.drawio`](aico-layered-architecture.drawio):分层技术架构图,偏基础层在下、偏应用层在上。
- [`aico-concepts-workflow.drawio`](aico-concepts-workflow.drawio):核心概念、角色分工与项目工作流图。

---

## 四个核心抽象

### 1. IMChannel — IM 通道接口
统一 IM 平台差异。
**详见**:[`adapter-protocol.md`](adapter-protocol.md)

### 2. AIAdapter — AI 适配器接口
统一各 AI 工具差异。
**详见**:[`adapter-protocol.md`](adapter-protocol.md)

### 3. Persona — 职责化策略
为 AI 注入职责身份和任务前缀。
- 当前最小实现是 `PersonaRegistry`:职责名 / alias → Adapter + role instruction
- 后续再演进为更完整的 system prompt + 行为策略

### 4. Project Team / Appointment — 项目团队与任命层
把 Agent、Role、Project 和 provider session 连接成“老板任命员工推进项目”的产品语义。
- Agent 是员工,Role 是通用岗位模板,Project 是项目办公室,Appointment 是具体任命。
- provider session、资源、权限、role prompt、工作目录和当前状态都绑定到任命,不裸挂在 Agent 上。
- `seat` 只是内部稳定 id;主路径命令应使用 `/project`、`/team`、`/who`、`/appoint`、`/ask`、`/default`。
- 详见 [`project-assignment-layer.md`](project-assignment-layer.md)、ADR-0011 和 ADR-0012。

### 5. A2A Memory Fabric — 项目 / 团队级共享记忆
把 Phase 7 记忆层从单独 slash command 升级为 A2A-compatible 的项目 / 团队记忆基础设施。
- 记忆以 `MemoryAtom` 为最小可验证单元,带 evidence、scope、confidence 和治理状态。
- 作用域必须绑定 boss / project / team / role / agent,默认不跨 project 或 team 共享。
- lead agent 和 team agent 通过受控 `MemoryPacket` 共享上下文,不暴露彼此内部记忆。
- 重要共识通过 `MemoryBroadcast` 发布到 team,后续 prompt stack 自动召回。
- 详见 [`a2a-memory-fabric.md`](a2a-memory-fabric.md)、ADR-0020、ADR-0021 和 ADR-0022。

---

## 编排核心的职责

| 组件 | 职责 |
|---|---|
| **Router** | 把 IM 消息解析成 Task,根据 @ 谁、人格、能力路由到 Adapter |
| **TaskBus** | 任务的提交、状态机、重试、中断 |
| **Persona Engine** | 渲染 AI 的职责上下文,注入身份 |
| **Project Team / Appointment** | 管理项目团队、岗位模板、员工任命、项目内 session 和 prompt 上下文 |
| **Approval** | 危险操作触发审批,等待人类确认 |
| **Memory** | 跨 AI 的共享上下文(项目知识库) |
| **Audit & Trace** | 所有 AI 行为的日志,可回溯 |
| **EventBus** | 状态变化广播,驱动 IM 推送和看板更新 |

**纪律**:这些组件都是核心,但**它们之间也有清晰边界**——通过 EventBus 解耦。

---

## 数据流(典型场景)

### 场景:用户在 Telegram 群里 @老张 让他改代码

```
1. Telegram 收到消息
   → TelegramChannel 解析 → 转成 IncomingMessage 事件
2. EventBus 广播 IncomingMessage
   → Router 监听
3. Router:
   → 解析 @老张(Persona ID)
   → 解析意图("改代码")
   → 查找 Persona "老张" 对应的 Adapter(可能是 Claude Code)
   → 创建 Task,加入 TaskBus
4. Persona Engine:
   → 渲染老张的 system prompt
   → 把 prompt 包进 Task
5. Approval:
   → 检查老张策略(老张是"严谨型",修改 > 50 行需要审批)
   → 这次改动 < 50 行,放行
6. ClaudeCodeAdapter:
   → receiveTask(task)
   → 调用 claude CLI
   → streamOutput 把输出 chunk 发到 EventBus
7. EventBus:
   → TelegramChannel 监听 → 编辑消息持续刷新进度
   → Audit 监听 → 写入审计日志
8. 任务完成:
   → TaskBus 把状态置 COMPLETED
   → EventBus 广播
   → TelegramChannel 推送最终结果到群
```

---

## 关键架构决策(链接 ADR)

- ADR-0001:技术栈选型(Accepted)
- ADR-0002:Adapter / Channel 协议(Accepted)
- ADR-0003:Phase 3 Persona 与 Broadcast 边界(Accepted)
- ADR-0004:Persona 外部配置(Accepted)
- ADR-0005:Phase 4 审批与审计边界(Accepted)
- ADR-0010:Agent Session 与 Harness 边界(Accepted)
- ADR-0011:Project Assignment Layer(Accepted)
- ADR-0012:Boss-Facing Team Commands and Role System(Accepted)

详见 [`../decisions/`](../decisions/)。

---

## 何时偏离这个架构

如果你发现一个需求**无法用这个架构表达**,那是两种可能:

1. **架构有问题,需要演化**:写 ADR 说明,经过 review 后调整
2. **需求与北极星不符**:回到 NORTH_STAR,大概率应该砍需求

**绝对不要**在不调整架构的情况下偷偷绕过架构(如直接在 Channel 里调 Adapter)。这是"normalization of deviance"的开始。
