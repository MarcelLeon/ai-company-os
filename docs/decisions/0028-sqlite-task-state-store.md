# ADR-0028: SQLite Task State Store

**状态**:Accepted
**日期**:2026-05-21
**决策者**:Codex
**相关 Round**:Round 106, Round 108

---

## 背景与问题

Phase 8 已经把 AICO 推到“离线托管 + 早上看结果”的产品语义。仅靠进程内
`TaskBus` 状态会让 `/tasks`、`/task`、pending approval 和托管工单在重启后丢失,
这不符合企业级、真实可用、可提效的目标。

已有 `AICO_AUDIT_LOG_PATH` 和 `AICO_MEMORY_PATH` 分别覆盖审计和共享记忆,但任务
状态、审批队列和 operator inbox 仍缺一个可恢复业务状态层。

## 候选方案

### 方案 A — 继续只用内存
- 优点:实现最简单。
- 缺点:重启即丢,不适合 Phase 8。

### 方案 B — 全量引入外部数据库(Postgres)
- 优点:更接近多人/服务端部署。
- 缺点:个人开发者本地使用门槛明显升高,也会过早扩大运维面。

### 方案 C — SQLite 作为本地默认持久化后端
- 优点:Python 标准库可用,无额外服务,适合 local-first 产品,也能用接口替换为其它后端。
- 缺点:不是多实例并发数据库,后续服务化仍需 Postgres/remote backend。

## 决策

选择 **方案 C:SQLite 作为本地默认持久化后端**,并通过 `TaskStateStore` 协议接入。

第一切片持久化任务记录、任务快照和审批请求;Round 108 扩展到 `/overnight`
托管工单记录,并新增 shared SQLite state metadata 和 `aico-state` inspect/reset 工具。
它们均由 `AICO_STATE_DB_PATH` 可选启用。
审计仍由 `AuditLog` / JSONL 负责,共享记忆仍由 `MemoryStore` 负责。

## 决策理由

- 它直接解决当前最痛的重启恢复问题,尤其是 pending approval 和 `/task` 查询。
- SQLite 不增加部署依赖,更适合个人开发者和开源试用。
- `TaskStateStore` 保留可插拔边界,未来可新增 Postgres、Redis 或托管后端,不污染
  `TaskBus` 的核心语义。
- 开发期快速迭代时,`aico_schema` metadata、`aico-state` 表计数和 reset 工具可以让
  schema / 数据演进更可见,避免手动猜 SQLite 文件里有什么。

## 后果

### 正面后果
- 重启后可以恢复 task snapshots、task records、approval requests 和 `/overnight`
  delegation records。
- `/approve` 可以继续处理重启前的 pending approval。
- 后续 operator inbox 可以复用同一业务状态层。
- `AICO_STATE_DB_PATH=true` 会映射到 `.aico/state.db`,避免误生成仓库根目录 `true`
  数据库文件。

### 负面后果
- 运行中的 provider 子进程不能跨重启继续流式输出;恢复的是 AICO 业务状态,不是底层
  CLI 进程。
- `TaskBus` 仍需要后续结构拆分,避免持久化逻辑继续挤在一个大类里。

## 不再做的事

- 不把 audit JSONL 当作唯一业务状态库。
- 不在当前阶段强制用户安装 Postgres。
- 不把 SQLite 细节暴露到 Adapter 或 Channel 层。

## 相关链接

- `src/aico/core/task_store.py`
- `src/aico/core/offline_delegation.py`
- `src/aico/core/sqlite_state.py`
- `src/aico/app/state_cli.py`
- `src/aico/core/task_bus.py`
- `src/aico/app/phase1.py`
