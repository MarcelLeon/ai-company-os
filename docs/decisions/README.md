# Architecture Decision Records (ADR)

> 重要架构决策的记录处。**ADR 不是文档,是决策快照**——做完决策那一刻写下来,**之后不再改动**(除非用新 ADR 推翻旧 ADR)。

---

## 为什么要写 ADR

ADR 回答的核心问题:**"为什么我们用 X 而不是 Y?"**

代码告诉你"做了什么",ROUNDS 告诉你"什么时候做的",ADR 告诉你"为什么这么做、否决了什么"。

后两者重合度高,但 ADR 是**精炼版的决策考古**——下一个 AI / 人类不需要爬整本 ROUNDS,看 ADR 索引就能 5 分钟掌握所有架构决策。

---

## ADR 索引

| 编号 | 标题 | 状态 | 日期 |
|---|---|---|---|
| ADR-0000 | (示例)使用 Markdown 写 ADR | Accepted | 2026-04-26 |
| ADR-0001 | 技术栈选型 | Accepted | 2026-04-27 |
| ADR-0002 | Adapter / Channel 协议 | Accepted | 2026-04-27 |
| ADR-0003 | Phase 3 Persona 与 Broadcast 边界 | Accepted | 2026-04-28 |
| ADR-0004 | Persona 外部配置 | Accepted | 2026-04-28 |
| ADR-0005 | Phase 4 审批与审计边界 | Accepted | 2026-04-28 |
| ADR-0006 | 审批权限策略 | Accepted | 2026-04-28 |
| ADR-0007 | 远程审批与 Adapter 能力边界 | Accepted | 2026-04-28 |
| ADR-0008 | 审计事件 JSONL 持久化 | Accepted | 2026-04-28 |
| ADR-0009 | Phase 5 AI 间协作协议 | Accepted | 2026-04-28 |
| ADR-0010 | Agent Session 与 Harness 边界 | Accepted | 2026-04-29 |
| ADR-0011 | Project Assignment Layer | Accepted | 2026-05-04 |
| ADR-0012 | Boss-Facing Team Commands and Role System | Accepted | 2026-05-04 |
| ADR-0013 | Platform-Neutral IM Render Contract | Accepted | 2026-05-05 |
| ADR-0014 | Phase 6 Observability Scope | Accepted | 2026-05-07 |
| ADR-0015 | Observability Event Replay | Accepted | 2026-05-07 |
| ADR-0016 | Status Island and Usage Boundary | Accepted | 2026-05-07 |
| ADR-0017 | Optional Agent Adapters | Accepted | 2026-05-07 |
| ADR-0018 | Full Agent Adapters and Feishu First Channel | Accepted | 2026-05-12 |
| ADR-0019 | Role Scope Vocabulary and Compact Team Views | Accepted | 2026-05-13 |
| ADR-0020 | Phase 7 Shared Memory Scope | Accepted | 2026-05-15 |
| ADR-0021 | Agent-Driven Memory Ownership | Accepted | 2026-05-15 |
| ADR-0022 | A2A Memory Fabric | Accepted | 2026-05-15 |
| ADR-0023 | Memory Semantic Retrieval | Accepted | 2026-05-18 |
| ADR-0024 | Phase 8 Offline Delegation Scope | Accepted | 2026-05-18 |
| ADR-0025 | Goal Mode Orchestration | Accepted | 2026-05-21 |
| ADR-0026 | Lead Decision Team Contract | Accepted | 2026-05-21 |
| ADR-0027 | Memory Purpose Tags | Accepted | 2026-05-21 |
| ADR-0028 | SQLite Task State Store | Accepted | 2026-05-21 |
| ADR-0029 | Phase 8 Absence Loop | Accepted | 2026-05-26 |

**状态图例**:
- `Proposed`(提议中)
- `Accepted`(已接受)
- `Rejected`(已拒绝,但保留记录)
- `Deprecated`(已弃用,被新 ADR 取代)
- `Superseded by ADR-XXXX`(被另一个 ADR 取代)

---

## ADR 模板

新建 ADR 时:

1. 文件名:`NNNN-short-title.md`(NNNN 为 4 位编号,从 0001 开始)
2. 复制以下模板:

```markdown
# ADR-NNNN: 标题

**状态**:Proposed / Accepted / Rejected / Deprecated / Superseded by ADR-XXXX
**日期**:YYYY-MM-DD
**决策者**:Wang / Claude(协作)
**相关 Round**:Round N

---

## 背景与问题

我们面临什么问题?为什么现在要决策?

## 候选方案

### 方案 A — XXX
- 优点
- 缺点
- 复杂度

### 方案 B — YYY
- 优点
- 缺点
- 复杂度

### 方案 C — ZZZ
- 优点
- 缺点
- 复杂度

## 决策

我们选择 **方案 X**。

## 决策理由

为什么选 X 而不是 Y、Z?

- 关键考量 1
- 关键考量 2
- 关键考量 3

## 后果

### 正面后果
- ...

### 负面后果
- ...

### 我们接受这些代价是因为
- ...

## 不再做的事

(选了 X 之后,我们承诺不会再去考虑 Y 和 Z,除非:
- 新增的约束让 X 不可行
- 出现了 X 完全没法解决的问题)

## 相关链接

- ROUNDS Round N
- PITFALLS P-XXX
- 相关代码:`path/to/affected/files`
```

---

## ADR 写作纪律

### 必须写 ADR 的场景
- 选了某语言 / 框架 / 库
- 选了某通信协议(同步 vs 异步、REST vs RPC)
- 选了某持久化策略
- 改了核心接口签名
- 引入了任何"在 NORTH_STAR 里没明确,但你做了选择"的事情

### 不需要写 ADR 的场景
- 修 bug
- 重命名变量
- 加日志
- 写测试
- 单纯的代码风格调整

### ADR 的语气
- **客观**:列方案、列理由,不要立场词
- **简洁**:300-800 字够了,不写小说
- **决断**:写完就是决策,不要"我可能选 A 或者 B 看心情"

### ADR 是不可变的(几乎)
ADR 一旦 Accepted,**不再修改原文**。如果决策变了:
1. 创建新 ADR(ADR-XXXX)
2. 在新 ADR 里写"Supersedes ADR-YYYY"
3. 在旧 ADR 里把状态改成 "Superseded by ADR-XXXX"
4. 不要删除旧 ADR——它是历史

例外:typo / 链接失效 / 格式问题可以原地改。
