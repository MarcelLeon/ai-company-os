# ADR-0097: Frozen-Fixture Independent AICO Harness

**状态**:Accepted
**日期**:2026-07-23
**决策者**:Wang / Codex(协作)
**相关 Round**:Round 264

---

## 背景与问题

Round 263已经把exact model/effort和TaskBus transport接入AICO runner，但frozen task只有objective与acceptance，没有实际fixture。
首角色因此只能看到抽象要求，无法证明AICO与Codex Goal处理了同一份任务输入。ADR-0095的scenario receipt也仍由测试直接构造，
没有从runtime artifact、dispatch receipt、filesystem generation和外部check事实推导。

## 候选方案

### 方案 A — 正式运行时由harness临时生成fixture和receipt

- 优点：不改task schema。
- 缺点：输入不在task-set SHA内，运行后可漂移；observer仍可能只复制被测系统自报字段。

### 方案 B — fixture进入task contract，外部observer读取真实文件并派生receipt

- 优点：两侧输入可按同一SHA复核；执行者、observer、finalizer继续分离。
- 缺点：task-set fingerprint升级；真实Telegram ACK和批准后的写动作仍需后续adapter连接。

### 方案 C — 直接保存raw prompt、日志和IM内容

- 优点：排障直观。
- 缺点：泄露路径、身份和私有上下文，且日志存在不等于验收事实。

## 决策

选择 **方案 B**：

1. 每个`BossAbsentTask`必须内嵌不超过16 KiB的bounded fixture；fixture进入canonical task-set SHA，并随每个role request传递。
2. role observation/checkpoint保存fixture SHA；runner、restart加载、independent observer和finalizer都拒绝fixture漂移。
3. `advance-aico`一次只推进一个frozen role；执行前验证absolute clean checkout和exact Git revision，使用exact-model TaskBus/Codex
   runtime。外部harness可在CLI调用之间真正终止进程、更换runtime instance并继续同一state。
4. independent observer维护owner-only atomic hash-chain ledger；它读取实际0600 artifact/dispatch receipt、fixture、external
   acceptance/test receipt、provider usage、takeover ACK与terminal receipt，不接受最终result flags作为输入。
5. evidence-drift读取修改前后真实bytes；approval fence绑定target与父目录inode/ctime/mtime，识别临时写入后回滚。
6. budget-pressure observer验证large irrelevant source存在，同时每份role receipt只绑定frozen fixture；raw source、prompt、路径和IM身份
   不进入scenario receipt。
7. `finalize-aico-observations`从ledger派生ADR-0095 receipt；所有benchmark输出改为fresh owner-only 0600文件。

## 当前证据

- 五类scenario用真实临时文件、0600 role receipt和重建后的observer实例生成scoreable receipt。
- negative tests覆盖receipt篡改、审批前mutation及mutation后回滚。
- no-model `advance-aico`在clean临时Git checkout经TaskBus连续完成两个distinct role，并持久state/artifact/receipt。
- task-set新canonical SHA为`f0acbd3317466f8709cf408ba1403bc0dbda17f0f5367cbd21630861c9462031`。

## 残余边界

- no-model测试证明transport/observer，不是正式benchmark成绩；尚未执行owner-authorized provider run。
- takeover receipt schema尚未连接Telegram真实send ACK + owner inbound command；approval receipt尚未连接真实IM决策和批准后at-most-once
  mutation executor。未连接前只能证明collector拒绝坏证据，不能声称场景已live。
- 配置agent id与ephemeral provider调用仍需formal harness绑定project assignment/session evidence。
- Codex Goal侧仍缺第一方native continuation host adapter/build receipt。

## 相关链接

- `src/aico/app/boss_absent_aico_observer.py`
- `src/aico/app/boss_absent_benchmark_cli.py`
- `benchmarks/boss-absent-v1/tasks.json`
- ADR-0095
- ADR-0096
