# ADR-0030: Unified Event Index — read-only cross-source trace view

**状态**:Accepted
**日期**:2026-05-31
**决策者**:Wang / Claude
**相关 Round**:Round 129
**相关文档**:[`docs/architecture/boss-first-grounding.md`](../architecture/boss-first-grounding.md) §3.2

---

## 背景与问题

`boss-first-grounding.md` §1 痛点 P4:audit 在 IM 内的表达上限低 — trace 糊成一团。

事实依据:

- `InMemoryAuditLog`(`src/aico/core/audit.py`)以 `AuditEvent` 为单位写 JSONL,事件之间没有跨源串联——同一个老板请求触发的 audit / memory write / task state change 是三条独立的线。
- 老板想问"昨晚那个 PR 是怎么来的",当前必须在 `/tasks`、`/audit`、`/recall` 之间手动拼 ID。
- §3.2 设计要求 `/why` 和 `/undo` 老板命令能在一次查询里返回 trace 全貌;§3.3 aico-view 的 Task Trace 视图也依赖跨源聚合。

但是 audit / memory / task state 各自的真相来源已经存在(audit JSONL / memory JSONL / SQLite task store),且都已经被 dogfood / 持久化 / 测试稳定使用。**重新设计统一存储会牵动太多组件,不符合 boss-first-grounding "不动现有 JSONL/SQLite 真相源" 的原则**。

## 候选方案

### 方案 A — 把 audit / memory / task 合并到一张统一表
- 优点:跨源查询自然,trace_id 是一级公民。
- 缺点:推翻 ADR-0008(audit JSONL)、ADR-0020-0023(memory JSONL)、ADR-0028(SQLite task state)三套已经稳定的持久化设计;改动面广、回滚风险高。
- 复杂度:高。

### 方案 B — 给每个源单独加 `trace_id`,在查询层做 ad-hoc 跨源拼接
- 优点:不引入新模块,改动最小。
- 缺点:每个调用方(`/why` 命令、aico-view 路由)都要重新实现一次拼接;违反 DRY,后续 V1 aico-view 难以复用。
- 复杂度:低。

### 方案 C — 给三个源都加 `trace_id` 字段;新增一个**派生只读** `UnifiedEventIndex` 层
- 优点:真相仍归 JSONL/SQLite 各自负责(零迁移);跨源聚合逻辑集中在 `unified_event.py` 一个模块;`/why`、`/undo`、aico-view 都直接用 index。
- 缺点:index 是派生数据,需要在内存里重建;一致性靠"重建周期" 而非订阅。
- 复杂度:中。

## 决策

选择 **方案 C:Unified Event Index — 派生只读层**。

### 关键边界(必须写死,避免后人误解)

1. **Index 不拥有真相**。`UnifiedEventIndex` 永远是 audit JSONL / memory JSONL / task SQLite 的**派生只读视图**。删除 index 不丢任何数据;任何"写"动作都直接走原 source。
2. **`trace_id` 是三源共有的串联键**。`AuditEvent.trace_id` / `Task.trace_id` / `MemoryAtom.trace_id` 三个字段都加,默认值 `None`,在使用时 fallback 到自身 id(`trace_id or task_id` / `trace_id or memory_id`)。
3. **JSONL 向后兼容是单向的**。新代码读老 JSONL 安全(老记录没有 trace_id,fallback 到 task_id);老代码读新 JSONL 会因 `extra="forbid"` 拒绝 → **升级是单向门**,记入 PITFALL。
4. **child task 通过 `model_copy` 自动继承父 trace_id**。本 sprint 不主动设置 trace_id;依赖 `task.model_copy(update=...)` 保留所有字段的语义。Grader follow-up 是例外(它是新顶层 task,trace_id 默认 = 自己 task_id),留 M3 把它接到 graded_task 的 trace。
5. **不订阅、不回写**。`InMemoryUnifiedEventIndex` 通过构造参数一次性接收三源快照;调用方需要时重建。本 sprint 不做长生命周期订阅、不做回写到真相源。

### 该 sprint 不做的事(明确范围边界)

- ❌ `/why` 和 `/undo` 命令(留 A2 sprint)
- ❌ aico-view web 路由(留 V1 sprint)
- ❌ `/timeline` `/rollback` 精细命令(留 A3 sprint)
- ❌ JSONL 文件级反向兼容(老代码不应读新 JSONL,要求版本一致升级)

## 结果

- 新增 `src/aico/core/unified_event.py`,定义 `UnifiedEvent` / `UnifiedEventIndex` Protocol / `InMemoryUnifiedEventIndex` 实现 / `short_event_id` / `short_memory_id` / `short_trace_id` 辅助函数。
- `AuditEvent`、`Task`、`MemoryAtom` 都增加 `trace_id: str | None = None` 字段。
- `InMemoryAuditLog.record(...)` / `record_event(...)` 自动从 `task.trace_id || task.task_id` 取 trace_id;子任务通过 `model_copy` 继承父 trace_id 是免费的。
- `tests/unit/test_unified_event.py`(3 用例)、`test_audit.py`(3 新用例)、`test_task_bus.py`(2 新用例)覆盖 trace_id 传播。
- 全套验证:`uv run pytest` **338 passed / 1 skipped**;ruff / format / mypy 全绿。

## 后续相关 ADR / Sprint

- A2 sprint:`/why` + `/undo` 老板命令,基于本 ADR 的 UnifiedEventIndex。
- V1 sprint:aico-view 三视图直接读 UnifiedEventIndex。
- A3 sprint:`/timeline` `/rollback` 精细命令,新增 `ROLLBACK_PERFORMED` audit event type。
- M3 sprint:Grader task 改为继承被验收 task 的 trace_id,让 `/why` 在 grader 上也能看到 owner 历史。
