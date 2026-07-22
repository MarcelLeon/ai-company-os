# ADR-0079: Quorum Dead-Man Notification Routes

**状态**:Superseded by ADR-0080(receiver/evidence/recovery schema only)
**日期**:2026-07-22
**决策者**:Codex
**相关 Round**:Round 241
**Supersedes**:ADR-0078的receiver/evidence/recovery schema v2部分；其alert-delivery-aware pulse、续租与outage reason合同继续有效

## 背景

独立receiver能可靠形成outage并持久重试，但只有一个owner notification webhook。该出口长期故障时，receiver、SQLite、worker和outage evidence都可以健康推进，缺席老板却收不到任何通知。让`/readyz`因downstream失败而重启只会制造循环，无法修复外部出口。

## 候选方案

- downstream失败就让receiver readiness失败并重启：否决；durable backoff是受控降级，restart会放大流量且不增加通知路径。
- 只提供admin status，等老板主动查询：否决；重新依赖缺席的人发现事故。
- 为每个route新增独立SQLite delivery ledger：本轮否决；当前不需要保存route-level成功/失败历史，但owner quorum本身必须持久化并冻结到事件，避免重启后策略漂移。
- 可选双独立origin并发投递，按owner配置的ACK quorum结算既有outbox event：采用。

## 决策

1. 单route配置保持原窄sink；配置fallback后创建`QuorumDeadManNotificationSink`，对两路并发发送同一immutable event和`Idempotency-Key`。
2. fallback必须使用不同HTTPS origin；primary/fallback bearer不得相同，且都不得复用pulse/admin authority。
3. `minimum_acknowledgements`只能在已配置route数量内。默认1表示1-of-2 failover；owner可显式设2要求dual ACK。
4. 达到quorum后既有outbox event标delivered；未达到则按原1/5/15分钟durable backoff重试exact event。accept-before-local-ack仍可能重复，route必须按event id幂等。
5. 所有route都被尝试；错误只对内表现为通用quorum miss，不持久化或记录URL、token、response body与异常正文。
6. evidence中的`delivered=true`现在表示configured local ACK quorum已满足，不表示每条route都成功、老板已读或两个origin物理独立。
7. receiver schema v3以singleton保存当前route count/quorum，每个outbox event在创建事务内冻结当时策略。存在pending event时，启动配置若改变策略必须fail closed；先按原策略清空pending，才能切换。
8. evidence/recovery schema v3同时验证当前策略、逐事件策略与pending/current一致性；已delivered历史事件可保留旧策略，不能被新配置重写。

## 后果

- 一个通知provider或credential失效时，1-of-2配置仍可从另一路触达老板。
- 2-of-2提供更强双ACK证据，但任一路故障都会保持pending并重投，owner必须基于目标选择。
- receiver v1/v2会保守迁移到v3，历史event按单route 1-of-1解释；升级前仍应备份。策略更新与pending检查在`BEGIN IMMEDIATE`内完成。
- 同一DNS、账号、网络或上游provider仍可能形成共同失效；不同origin只是机器可验证下限，不是独立故障域证明。

## 不再做的事

- 不把restart loop当作notification failover。
- 不让fallback token复用receiver control-plane authority。
- 不把1-of-2 local ACK写成两路均送达、human read或commercial HA完成。
- 不在缺少route-level需求证据时提前引入动态route registry或per-route delivery receipt；当前只持久化结算所必需的策略事实。
