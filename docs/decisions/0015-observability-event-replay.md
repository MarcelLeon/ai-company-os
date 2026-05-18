# ADR-0015: Observability Event Replay

**状态**:Accepted
**日期**:2026-05-07
**决策者**:Codex
**相关 Round**:Round 62

---

## 背景与问题

Round 61 的 `/metrics` MVP 只汇总当前进程内的 `TaskSnapshot` 和 `AuditEvent`。这让第一版很轻,但重启后 24h / 7d 指标会清空。Phase 6 需要让指标具备基本历史连续性,否则明天早上看不到昨晚 agent 做过什么。

项目已经有 `AICO_AUDIT_LOG_PATH` 和审计事件 JSONL 持久化。问题是是否应该马上引入新的 Task repository / SQLite,还是先复用审计事件做轻量回放。

## 候选方案

### 方案 A — 新增 TaskSnapshot JSONL
- 优点:指标读取简单,直接保存最新 snapshot。
- 缺点:会和 audit JSONL 形成两份事实来源,需要处理一致性。
- 复杂度:中。

### 方案 B — SQLite Task / Audit repository
- 优点:适合长期趋势、查询和未来 Web / Mac UI。
- 缺点:当前 Phase 6 指标口径还在 dogfooding,直接上数据库偏重。
- 复杂度:中高。

### 方案 C — 回放现有 audit JSONL 重建 metrics task snapshot
- 优点:复用已有审计事实来源;不引入新依赖;重启后能恢复 completed / failed / interrupted / rejected / waiting approval 等指标。
- 缺点:重建出的 snapshot 是 metrics 视图,不是完整任务记录;payload 不会恢复。
- 复杂度:低。

## 决策

选择 **方案 C:回放现有 audit JSONL 重建 metrics task snapshot**。

具体做法:
- `InMemoryAuditLog` 支持启动时注入 `initial_events`。
- `read_jsonl_audit_events(path)` 从 `AICO_AUDIT_LOG_PATH` 读取旧事件。
- `metrics.py` 从 audit events 重建 task snapshot,再和当前进程内 task snapshot 合并。
- 当前进程内 snapshot 优先于 replay snapshot。

## 决策理由

- 审计事件已经是“AI 行为可审计”的事实来源,用它做可观测回放符合北极星第三句。
- 不新增数据库,保持 Phase 6 第一阶段轻量。
- `/metrics` 最需要的是状态、agent、耗时和协作次数;这些都能从 audit events 推导。
- 未来如果进入 Web / Mac UI 和长期趋势,仍可用新 ADR 引入 SQLite 或其他 repository。

## 后果

### 正面后果

- 重启后 `/metrics` 仍能看到最近 24h / 7d 历史任务指标。
- 不需要新增配置;继续使用 `AICO_AUDIT_LOG_PATH`。
- 避免 task snapshot JSONL 与 audit JSONL 双写不一致。

### 负面后果

- `/tasks` 仍只展示当前进程内任务,不会从 audit JSONL 恢复完整任务列表。
- 从 audit 重建的 snapshot 没有原始 payload。
- 如果过去没有开启 `AICO_AUDIT_LOG_PATH`,历史仍不可恢复。

### 我们接受这些代价是因为

Phase 6 当前要先验证指标价值。完整任务仓储和长期趋势图等到指标口径稳定后再做。

## 不再做的事

- 当前阶段不新增第二份 task snapshot JSONL。
- 当前阶段不引入 SQLite / Postgres。
- 不尝试从 audit JSONL 伪造任务 payload 或完整会话历史。

## 相关链接

- ROUNDS Round 62
- ADR-0014
- `src/aico/core/audit.py`
- `src/aico/core/metrics.py`
