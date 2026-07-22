# ADR-0040: Reconcile Persisted Running Tasks as Interrupted After Restart

**状态**:Accepted
**日期**:2026-07-21
**决策者**:Codex
**相关 Round**:Round 202

## 背景

TaskBus 会把 task record、snapshot、approval 和 Adapter name 写入 SQLite。新进程恢复时,当前实现原样载入
`RUNNING`,但 Adapter 的 subprocess handle、stdout stream、interrupt handle 都只存在于旧进程内。
LaunchAgent 重启因此会制造“数据库显示 running,实际无人拥有执行”的假状态。

## 候选方案

### A. 保留 RUNNING,等待任务自己完成

拒绝。新 runtime 已无法接收旧进程输出,任务永远不会自然变成 done/failed。

### B. 启动时自动重新 dispatch 原任务

拒绝。无法证明旧 CLI 没有产生部分或完整外部副作用;自动重放可能重复写文件、消息、发布、付款或数据修改。

### C. RUNNING → INTERRUPTED,保留审批和证据

采用。`INTERRUPTED` 表示 AICO 已失去执行所有权,不声称底层动作必然停止。snapshot 保留原 task/Adapter/risk/
metadata,reason 要求先核对副作用再提交新任务;新 runtime 写一条 `TASK_INTERRUPTED` audit。

## 决策

- `TaskStateRepository` 加载持久状态后立即对账所有 `RUNNING` snapshot,在暴露任何 read model 前写回 `INTERRUPTED`。
- reconciliation 只发生一次:状态写回后,后续 restart 不再重复处理。
- `TaskBus` 对每个本轮对账 task 记录 `TASK_INTERRUPTED` audit。
- `WAITING_APPROVAL` 保持 pending;它尚未 dispatch,新 runtime 可继续由授权 reviewer 决策。
- 不新增自动 retry/resume。未来只有具备 idempotency 与 side-effect contract 的 Adapter/operation 才能讨论恢复执行。
- 当前 SQLite state store 仍是单 runtime owner;多进程 lease/leader election 不在本 ADR 范围。

## 后果

### 正面

- `/inbox`、`/morning`、`/view` 不再展示幽灵 running task。
- crash/restart 后的事实、风险和恢复动作明确可审计。
- 避免自动重放带来的重复副作用。

### 代价

- 即使底层 CLI 在父进程退出后侥幸继续运行,AICO 仍会标 interrupted,因为控制与输出所有权已丢失。
- 老板需要核对实际副作用并手动提交新任务。
- 多 runtime 共用一个 DB 会把另一进程的任务误判为 orphan;该部署形态当前不受支持。

## 不再做的事

- 不把 persisted `RUNNING` 当成可恢复执行证据。
- 不在 startup 自动 replay。
- 不因 restart 取消尚未 dispatch 的 pending approval。
- 不把“execution ownership lost”写成“底层进程确定已停止”。
