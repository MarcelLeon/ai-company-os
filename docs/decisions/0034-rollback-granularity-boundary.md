# ADR-0034: Rollback granularity boundary (A3)

**状态**:Accepted
**日期**:2026-05-31
**决策者**:Wang / Claude
**相关 Round**:Round 135
**相关文档**:[`docs/architecture/boss-first-grounding.md`](../architecture/boss-first-grounding.md) §3.2;ADR-0032 / ADR-0033

---

## 背景与问题

ADR-0032 已经写死了 `/undo` 的边界:只撤 AICO-internal 状态,不撤 git/shell/file。`/undo` 的语义是"撤最近一步",省去老板记 ID 的负担。

A3 引入 `/rollback memory|experience|task <id>` 作为 lead 内务命令,需要精确指定 ID。两个语义需要厘清:

1. 与 `/undo` 的关系
2. `/rollback task <id>` 应该做到什么程度(撤 memory 写入? 撤 file? 撤 shell?)
3. 谁能用(老板还是只 lead)

## 候选方案

### 方案 A — `/rollback` 试图实现真正的"task 回到提交前"
- 让 `/rollback task <id>` 自动:撤掉该 task 触发的所有 memory 写入 + experience 状态变更 + child task。
- 优点:用户直觉对齐。
- 缺点:目前 task 元数据里没有可靠的 "produced memory_ids" 索引,只能通过 trace_id 扫;遗漏一条就破坏审计承诺;**还是不撤 file/shell**——用户期望落差更大。
- 复杂度:中等(scan trace_id + 级联撤销)。

### 方案 B — `/rollback task <id>` 只写一条 ROLLBACK_PERFORMED audit 标记
- 不实际撤内部状态,只记录"lead 把这个 task 标记为已回滚";后续 `/timeline` `/inbox` 可以根据这条 audit 改用渲染。
- 优点:语义清晰,失败模式为零(就是写一条 audit);不假装做更多。
- 缺点:用户得自行 `/rollback memory <id>` 撤具体的 memory 副作用。
- 复杂度:低。

### 方案 C — 不提供 `/rollback task` 子命令,只支持 memory/experience
- 优点:范围最小。
- 缺点:lead 失去对 "task 失败后清理标记"的统一入口;还要靠 `/forget` `/experience archive` 分别清。
- 复杂度:低。

## 决策

选择 **方案 B:`/rollback task` 只写 audit 标记;`/rollback memory|experience` 真撤**。

### 关键边界

1. **可撤的精细对象**(写真实状态变更):
   - `/rollback memory <id>` — 把 fact memory 标记为 archived(走 store.archive)
   - `/rollback experience <id>` — active experience → CANDIDATE(append 反向状态);archived experience 不变(语义上没有更早的状态可回)

2. **`/rollback task <id>` 只写 audit 标记**:不级联撤 memory/experience。理由:
   - 没有可靠的 task→memory_ids 反向索引
   - 用户期望"task 回滚"包含 file/shell,但 AICO 撤不了,所以最诚实的做法是不假装
   - 如果级联撤,失败/部分成功的处理路径复杂度爆炸
   - 后续如果要做真正级联,需要先建 trace_id → produced_memory_ids 索引(留作未来 sprint)

3. **每次 rollback 都写 `ROLLBACK_PERFORMED` AuditEvent**:
   - 新增的 `AuditEventType.ROLLBACK_PERFORMED`
   - actor_id = lead 的 IM sender_id;target_persona = "lead";risk_level = READ_ONLY(rollback 本身不引入新风险)
   - task_id = `memory:<id>` 或真实 task_id;detail 描述具体反向操作

4. **`/timeline` 是只读过滤视图**:支持 `--since <duration>`(h/d/m 后缀)、`--source audit|memory|task`、`--limit N`、`--trace <prefix>`。不暴露 audit 写入。

5. **命令归属**:`/rollback` 和 `/timeline` 都是 **lead 内务**,boss-only 6 命令不变。老板继续用 `/undo` 和 `/why` 即可。

### 该 sprint 不做的事(明确范围边界)

- ❌ 级联撤销 task 副作用(留作未来,前置:trace_id → produced_memory_ids 索引)
- ❌ `/rollback file` 或 `/rollback shell` — **永远不做**,这两件事归 git 和操作系统
- ❌ 撤销 `/rollback`(rollback 写的 audit 仅追加,不再被反向)
- ❌ aico-view 内做 rollback UI(view 永远只读)

## 结果

- `src/aico/core/models.py`:`AuditEventType` 加 `ROLLBACK_PERFORMED`。
- `src/aico/core/task_bus.py`:`audit_log()` accessor 暴露给 RollbackCommandHandler。
- 新增 `src/aico/core/timeline_rollback_commands.py`(约 290 行):`TimelineCommandHandler` + `RollbackCommandHandler`。
- `src/aico/core/commands.py`:`CommandName.TIMELINE` / `ROLLBACK`;help 加两行。
- `src/aico/core/orchestrator.py`:`_setup_boss_and_lead_handlers` 加 2 个 handler 实例化,命令分发加 2 个 elif(B-005 workaround:Orchestrator 主体只加 2 行实例化 + 2 行分发,新逻辑全部进新模块)。
- 新增测试 `tests/unit/test_timeline_rollback_commands.py`(9 用例)。
- CHANGELOG 加 `/timeline` `/rollback` 说明。
- `docs/human/daily-ops.md` 加 lead 命令组段。

## 后续相关 ADR / Sprint

- Sprint V3:aico-view token 鉴权 + 部署文档。
- 未来:`/rollback task <id>` 级联撤销 — 前置是 trace_id → produced_memory_ids 反向索引,本 sprint 不做。
- 未来:`/rollback` 之后的二次 `/undo` 行为(应该不做,但要在文档里写明)。
