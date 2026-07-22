# ADR-0041: Transactional Outbox for Restart Recovery Audit

**状态**:Accepted
**日期**:2026-07-21
**决策者**:Codex
**相关 Round**:Round 203

## 背景

ADR-0040 将 crash restart 时的持久化 `RUNNING` 对账为 `INTERRUPTED`,但 snapshot 和 audit JSONL
是顺序双写。若进程在 SQLite commit 后、JSONL append 前退出,后续进程只看到 `INTERRUPTED`,不会再生成
恢复审计;若先写 JSONL,则相反顺序会制造 stale state 或重复事件。

ADR-0028 和 ADR-0030 已规定 SQLite 继续拥有业务状态、JSONL 继续拥有 audit truth,不能为修复这一处故障窗口
推翻三源架构。

## 候选方案

### A. 接受极短故障窗口

拒绝。human-absent runtime 的恢复证据恰好在 crash 路径最重要;“概率低”不能证明商业可审计。

### B. 把全部 audit 搬进 SQLite

拒绝。会推翻 ADR-0008/0015/0028/0030,扩大迁移和查询面,也把一个局部交付问题变成统一存储重写。

### C. SQLite transactional outbox + event-id 幂等 JSONL

采用。Task snapshot 与完整 recovery `AuditEvent` 在同一 SQLite transaction 提交;TaskBus 只投递 pending
event,成功后确认。重试使用同一 event id,内存 audit 和内置 JSONL sink 都按 id 幂等。

## 决策

- `SQLiteTaskStateStore` 直接实现本用例,不新增通用 event-bus/outbox framework。
- outbox 只保存 restart reconciliation audit,不是 `/audit`、`/metrics` 或 aico-view 的查询来源。
- outbox payload 是完整不可变 `AuditEvent`,避免 retry 时重建 timestamp/trace/actor 导致内容漂移。
- SQLite transaction 使用单连接 `BEGIN IMMEDIATE`,同批更新 snapshot 并插入 outbox。
- `InMemoryAuditLog.record_existing()` 接受已分配 id 的事件;相同 id+内容 no-op,相同 id+不同内容报错。
- `JsonlAuditSink` 在 append 前按 event id 检查已有行。当前部署仍是单 runtime owner;跨进程并发 append 不在保证内。
- sink 成功后才把 outbox 标为 delivered。sink 抛错时 TaskBus startup 失败,但 intent 保留供下一次启动重试。

## 后果

### 正面

- crash 前后最终收敛为一个 interrupted snapshot 和一条稳定恢复审计。
- 不需要自动重放任务,也不引入 Postgres/broker。
- 保留现有 SQLite/JSONL truth boundary。

### 代价

- JSONL sink 启动时需线性读取现有事件建立 id index;后续 append/去重为 O(1)。大规模日志仍应轮转或换持久 audit backend。
- SQLite schema 增加专用 outbox 表和 delivery 状态。
- 任意第三方 sink 若自身产生“写成功后抛错”,仍需按 AuditSink 契约自行实现 event-id 幂等。

## 不再做的事

- 不用“先写哪个概率更安全”替代一致性设计。
- 不从 outbox 构建老板视图或指标。
- 不借 outbox 自动 retry Adapter task。
- 不把本方案宣传为多 runtime/distributed exactly-once。
