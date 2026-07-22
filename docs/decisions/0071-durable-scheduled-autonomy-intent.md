# ADR-0071: Durable Scheduled Autonomy Intent and Evidence-based Recovery

**状态**:Accepted
**日期**:2026-07-22
**决策者**:Codex / Round 233

## 背景

ADR-0070先持久化晨报平台ACK，再触发standing autonomy。进程若在ACK之后、自治调用之前崩溃，晨报已经是DELIVERED，
原scheduler不会再次触发自治；若无条件重跑，又可能在provider已接收任务后重复消费grant或产生第二个任务。

## 候选方案

- 把自治完成并入晨报ACK：否决；业务失败会重发已确认消息，再次混淆transport与execution。
- 重启后无条件调用自治：否决；不能证明上次provider dispatch是否已经发生。
- 只依赖TaskBus RUNNING状态：否决；通知/hold可能没有task，proposal与task的业务绑定也会丢失。
- 独立durable intent，并用accepted proposal/task证据对账：采用。

## 决策

1. 每个scheduled morning delivery派生稳定autonomy intent；必须在任何晨报外发前写入主SQLite。schema v7记录
   PENDING/RUNNING/RETRYING/SETTLED/EXHAUSTED、attempt、backoff、歧义和bounded run receipt。
2. standing coordinator在provider dispatch前把`intent_id`同时写入accepted proposal与task metadata。重启发现RUNNING intent时，
   若存在matching accepted proposal/task就直接SETTLED，不再调用provider；无该证据才允许1/5/15/15分钟、最多五次重试。
3. hold/notification或返回receipt后、scheduler落SETTLED前仍存在at-least-once窗口；重试时沿用同intent id，并标记
   `duplicate_notification_possible=true`。这不授权重复provider dispatch。
4. 晨报platform ACK、autonomy dispatch receipt、human read和standing result继续独立。任一intent未结算时health为DEGRADED，
   EXHAUSTED为FAILED；`aico-state`只展示intent/status/attempt/disposition及proposal/task ID哈希。

## 后果

- ACK后、dispatch decision落盘前崩溃不再永久漏触发scheduled autonomy，accepted dispatch也不会因恢复逻辑重复执行。
- accepted proposal/task记录的是dispatch decision，不是provider ACK；在其持久化后、provider真正接收前崩溃时，系统保守
  不重跑并由后续`evidence_missing`暴露at-most-once缺口。
- 主SQLite与backup/reset新增一张表；operator需要分别核对delivery和autonomy两段状态。
- 没有跨SQLite与IM/provider的全局事务，hold通知可能有界重复；系统明确暴露而不声称exactly-once。

## 相关链接

- ROUNDS Round 233
- ADR-0070
- PITFALLS P-089
- Goal Brief `docs/superpowers/specs/2026-07-22-durable-scheduled-autonomy-intent.md`
- `src/aico/app/scheduled_autonomy.py`
