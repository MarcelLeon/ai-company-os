# ADR-0094: Restart-Safe Managed Multi-Agent Benchmark Runner

**状态**:Accepted
**日期**:2026-07-23
**决策者**:Wang / Codex(协作)
**相关 Round**:Round 261

---

## 背景与问题

AICO现有standing-autonomy为了守住单次只读边界，会禁用Agent输出的collaboration directive，并让Codex执行tool-free single response。
这适合一个standing charter，但不能直接证明新目标要求的跨Agent协作。简单放开`@role`或provider内置multi-agent又会让Agent自行扩张预算和任务树，
破坏owner总预算与可审计性。

benchmark runner还面临provider调用的crash window：若进程在provider完成后、receipt持久化前崩溃，重启后盲目重跑会重复消费预算；
若直接跳过，则会丢usage和结果。

## 候选方案

### 方案 A — 允许首个Agent自行生成协作directive

- 优点：复用现有Orchestrator协作语法。
- 缺点：角色数量、调用顺序和预算由模型输出决定；断线后难以证明exact checkpoint consumption。

### 方案 B — 单Agent依次扮演多个角色

- 优点：调用少、实现简单。
- 缺点：不是真实跨Agent协作；旧scorer只看role label会产生假满分。

### 方案 C — AICO核心按frozen roles编排不同Agent，共享一个硬预算并持久化dispatch intent

- 优点：角色、顺序、预算和恢复由系统决定；每个Agent只消费前一checkpoint；provider crash可按稳定dispatch id对账而不盲重放。
- 缺点：需要独立runtime adapter把真实AICO TaskBus/Adapter接入该Protocol，并继续补齐五类scenario terminal evidence。

## 决策

选择 **方案 C**：

1. AICO benchmark runtime必须通过exact model/effort、isolated state、managed role orchestration、hard remaining-token cap、provider usage
   observation和durable dispatch reconciliation准入。
2. runner按frozen `required_roles`顺序派发；每个role request携带共享预算余额和前一artifact SHA，不允许为每个角色重置预算。
3. collaboration task的每个required role必须由不同`agent_id`完成；正式scorer同步拒绝一个Agent换多个role label的伪协作。
4. 每次provider调用前先原子写入owner-only `0600` pending intent和稳定dispatch id。重启发现pending时只调用`recover_role`；
   无receipt则保持`dispatch_ambiguous`，禁止provider replay。
5. provider usage超过remaining cap仍完整写入failed observation和total tokens，不能因checkpoint未采信而隐藏budget loss。
6. restart scenario在首个checkpoint后进入`restart_pending`；后续checkpoint必须来自不同runtime instance SHA，且继续消费exact prior artifact。
7. `role_chain_complete`只表示角色链完成，不等于benchmark terminal complete；source/test/acceptance/IM/approval/scenario evidence未封口前不得生成成绩。

## 当前证据

- JSON state使用同目录temporary、`0600`、fsync、atomic replace和directory fsync；拒绝非owner regular file与symlink。
- 定向测试覆盖共享预算、checkpoint consumption、真实新runtime identity、crash后reconciliation、unknown outcome不重放、超预算留证、
  admission drift与单Agent伪协作拒绝。
- scorer新增distinct agent gate；synthetic harness原本已为每个role生成不同agent id，因此公平fixture仍成立。

## 残余边界

- 当前runtime Protocol由fake实现做no-model contract验收，尚未连接真实TaskBus/Codex Adapter，不是formal AICO run。
- approval fence、evidence drift、IM takeover、test/acceptance terminal receipts仍需下一切片接入，`role_chain_complete`不可计分。
- hard remaining-token capability最终必须由真实Adapter/provider设置证明；post-response比较只能作为budget-loss证据，不能冒充事前hard cap。

## 相关链接

- `src/aico/app/boss_absent_aico_runner.py`
- `src/aico/core/boss_absent_benchmark.py`
- `tests/unit/test_boss_absent_aico_runner.py`
- ADR-0091
- ADR-0093
