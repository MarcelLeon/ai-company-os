# ADR-0098: Approval-Gated At-Most-Once Benchmark Mutation

**状态**:Accepted
**日期**:2026-07-23
**决策者**:Wang / Codex(协作)
**相关 Round**:Round 264

---

## 背景与问题

ADR-0097的observer可以识别approval evidence，但旧runner会在implementer后直接派reviewer；harness即使最后发现审批缺失，也没有在执行前
阻止越界。直接接受任意grant/action hash同样不够：批准动作必须精确绑定frozen fixture，并在runner crash时不重复写入。

## 候选方案

### 方案 A — role chain完成后由observer检查是否有approval

- 优点：实现简单。
- 缺点：只能事后发现，不能阻止reviewer越过审批边界。

### 方案 B — runner持久`approval_pending`，独立executor以intent/receipt执行exact isolated mutation

- 优点：审批前不派下一role；write后崩溃可对账且不重写，state和observer绑定同一request/grant/action。
- 缺点：Telegram owner decision仍需作为grant生产者接入。

### 方案 C — 把写权限交给模型并依赖prompt要求先询问

- 优点：交互自然。
- 缺点：prompt不是权限边界，无法证明at-most-once或crash reconciliation。

## 决策

选择 **方案 B**：

1. approval task首role checkpoint后进入durable`approval_pending`并生成stable request SHA；重复advance只返回原state。
2. 只有匹配contract/task/request的未过期owner grant和action receipt才能记录`AicoApprovalCheckpoint`并恢复runner。
3. action由系统解析frozen fixture中的exact`action_id/target/content`；target只能位于owner-only isolated mutation root。
4. 写入前先持久0600 intent；没有既有intent却已有target时拒绝，防止把预存内容冒充本次执行。
5. intent存在且target为exact content时按“写后崩溃”对账，生成receipt但不重写；different content fail closed。
6. intent、target、receipt和runner state均fsync；receipt固定`execution_count=1`并绑定request/grant/target/content。
7. independent observer读取actual action receipt和mutation generation，并与runner checkpoint逐SHA匹配；手工填hash不能封口。

## 当前证据

- runner测试证明approval pending期间reviewer零派发，checkpoint后才恢复。
- executor测试覆盖正常一次写、重复调用幂等、write后crash reconciliation、过期grant和无intent预存target拒绝。
- observer/finalizer要求request、grant、action receipt与state完全一致。

## 残余边界

- grant目前由owner-only文件输入；尚未由真实Telegram owner sender/target/平台ACK/inbound command生成。
- mutation只作用于benchmark隔离目录，不授权仓库、生产服务或外部副作用。
- no-model测试不是formal benchmark成绩。

## 相关链接

- `src/aico/app/boss_absent_aico_approval.py`
- `src/aico/app/boss_absent_aico_runner.py`
- `src/aico/app/boss_absent_aico_observer.py`
- ADR-0097
