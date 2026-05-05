# ADR-0008: 审计事件 JSONL 持久化

**状态**:Accepted
**日期**:2026-04-28
**决策者**:Codex
**相关 Round**:Round 18

---

## 背景与问题

Phase 4 已经支持 `/audit` 查询最近审计事件,但它依赖进程内 `InMemoryAuditLog`。进程重启后,任务提交、审批结果、Adapter 派发和拒绝记录都会丢失。北极星第三句要求 AI 行为可审计,因此需要一个比内存视图更可追溯的最小落盘方式。

## 候选方案

### 方案 A — 继续只保留内存 `/audit`
- 优点:实现最简单,无文件权限问题。
- 缺点:重启丢失,无法满足长期审计追溯。
- 复杂度:低。

### 方案 B — 配置 JSONL append-only 审计文件
- 优点:无需新增依赖;每行一个事件,便于 `tail` / `jq` / 日志采集;保留 `/audit` 的内存近实时查询。
- 缺点:没有索引、查询、轮转和并发写保护。
- 复杂度:低。

### 方案 C — 引入 SQLite/Postgres 审计仓储
- 优点:查询能力强,适合长期运营。
- 缺点:会引入 Repository 抽象、迁移和备份策略,对当前 Phase 4 收口过重。
- 复杂度:中高。

## 决策

选择 **方案 B — 配置 JSONL append-only 审计文件**。

## 决策理由

- 当前只需要“重启后仍能追溯发生过什么”,JSONL 已足够。
- `AICO_AUDIT_LOG_PATH` 让持久化可按环境启用,不破坏已有本地运行方式。
- `JsonlAuditSink` 作为 sink 接在 `InMemoryAuditLog` 后面,后续可追加结构化日志、SQLite 或远端 sink。
- 不新增数据库依赖,符合 Phase 4 小步收口。

## 后果

### 正面后果
- `/audit` 继续展示最近事件,JSONL 文件提供跨重启追溯。
- 人类可直接 `tail -n 20 /tmp/aico-audit.jsonl` 查看最新审计事件。
- 后续接日志采集或可观测看板时有稳定结构化事件源。

### 负面后果
- 暂不处理日志轮转、压缩和并发写。
- JSONL 文件路径配置错误会导致审计写入失败并暴露运行时错误。

### 我们接受这些代价是因为
- 当前是单机 dogfooding 阶段,并发和日志生命周期可以在 Phase 6 可观测阶段再系统化。

## 不再做的事

- Phase 4 不引入 SQLite/Postgres 审计仓储。
- 不让 `/audit` 伪装成完整历史查询;它仍只是进程内最近事件视图。

## 相关链接

- ROUNDS Round 18
- 相关代码:`src/aico/core/audit.py`, `src/aico/app/phase1.py`
