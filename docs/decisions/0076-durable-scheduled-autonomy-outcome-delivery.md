# ADR-0076: Durable Scheduled Autonomy Outcome Delivery

**状态**:Accepted
**日期**:2026-07-22
**决策者**:Codex / Round 238

## 背景

ADR-0071让晨报ACK后的自治dispatch拥有独立durable intent，但自治最终结果仍由`StandingAutonomyCoordinator`直接调用IM发送。
平台失败或进程在结果生成后、发送确认前崩溃时，dispatch intent会依据accepted proposal/task保守SETTLED，老板只能等下一次
`/morning`或`/inbox`才发现done、interrupted或`evidence_missing`。这会让“provider不盲重跑”退化成“公司静默”。另一个窗口是
非关键started通知发生在TaskBus submit前；该通知失败会阻断真正工作，却留下accepted proposal。

## 候选方案

- 继续依赖下一次晨报查询：否决；结果交付重新依赖老板主动回来。
- IM发送失败时重跑provider：否决；通知可重试不代表provider副作用可重演。
- 只捕获发送异常并写日志：否决；进程存活与老板收到结果仍然无法区分。
- 独立exact-envelope outcome outbox，按authoritative proposal/task/result投影：采用。

## 决策

1. `DISPATCH_RECORDED` intent结算后，从既有`StandingProposal + TaskSnapshot + StandingResultReceipt`生成bounded outcome envelope；
   source status、outcome、criteria、sources、evidence/failure与run receipt/content SHA一起冻结，不保存provider正文。
2. 任何IM发送前写入`scheduled_autonomy_outcome_outbox`。PENDING/SENDING/RETRYING/DELIVERED/EXHAUSTED按1/5/15/15分钟、
   最多五次推进；平台ACK只保存message id SHA并校验exact trusted target。
3. SENDING重启恢复为同一notification immediate RETRYING并标记`duplicate_possible=true`。重试只发送同一envelope，绝不重新
   调用provider或消费grant。outbox open使health DEGRADED，EXHAUSTED使health FAILED。
4. intent已SETTLED但outbox尚未创建时，single-owner scheduler在新工作前补建。RUNNING/WAITING不是terminal outcome，保持
   DEGRADED并最多每60秒复核，不冻结为绿色终态。NOT_APPLICABLE/HOLD不新增结果outbox；hold沿用
   现有发送/重试语义，只有实际dispatch需要terminal outcome receipt。
5. started通知仍是best-effort progress hint；普通transport异常会脱敏记录但不能阻断TaskBus submit。取消与进程终止继续传播，
   不把通知失败变成继续执行的万能豁免。若TaskBus已dispatch后其它IM transport失败，bounded runner会interrupt仍为RUNNING的
   task，避免无人消费输出的本地zombie；缺少terminal usage/result时outcome按既有合同保守报告`evidence_missing`。

## 后果

- 老板缺席时，自治结果或缺证状态会主动、有界、跨重启地投递；发送失败进入required health，不再只藏在下一次查询里。
- 平台不支持端到端幂等时仍是bounded at-least-once，`duplicate_possible`必须保留；DELIVERED不等于老板已读。
- accepted proposal写入后、TaskBus真正dispatch前的at-most-once窗口仍不自动重跑，outcome会明确投递`evidence_missing`。
- state schema升级v12；该改动不创建真实grant/provider/IM样本，B-014保持DEFERRED。

## 相关链接

- ROUNDS Round 238
- ADR-0053
- ADR-0070
- ADR-0071
- PITFALLS P-094
- Goal Brief `docs/superpowers/specs/2026-07-22-durable-autonomy-outcome-delivery.md`
- `src/aico/app/scheduled_autonomy_delivery.py`
- `src/aico/app/morning_scheduler.py`
