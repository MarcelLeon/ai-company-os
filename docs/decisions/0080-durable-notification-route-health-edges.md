# ADR-0080: Durable Notification Route Health Edges

**状态**:Superseded by ADR-0081(receiver/evidence/recovery schema and continuous-observation boundary only)
**日期**:2026-07-22
**决策者**:Codex
**相关 Round**:Round 242
**Supersedes**:ADR-0079的receiver/evidence/recovery schema v3部分；其different-origin、ACK quorum与策略围栏继续有效

## 背景

ADR-0079允许1-of-2结算，但aggregate quorum会吞掉逐路事实。primary ACK、fallback失败时，outage event会被标为delivered，
SQLite、evidence和老板都看不到冗余已经降级。若primary随后也失效，系统才第一次暴露两路全断，违反absence-first的
false-green边界。

## 候选方案

- 只把aggregate delivered改成degraded：否决；没有逐路事实、持久边沿或老板通知，restart后仍无法解释。
- 让`/readyz`因任一路失败返回503：否决；外部provider故障不应触发receiver restart storm。
- 立即增加周期canary：本轮否决；vendor-neutral webhook没有silent probe合同，直接发送会制造老板噪声。先固化真实业务event的
  逐路ACK与边沿，周期端到端探测单独设计。
- 为每次业务event持久化bounded route outcome，并把降级/恢复边沿通过尚存route主动通知老板：采用。

## 决策

1. production webhook sink返回route ACK结果；quorum error也只携带`(true|false)`向量，不携带URL、token、response或异常正文。
2. main event结算、逐route状态和新健康边沿在一个`BEGIN IMMEDIATE`事务内提交。event保存最后一次ACK bitmask与attempt time，
   route只保存slot 1/2、unknown/healthy/degraded、连续失败和时间。
3. `unknown|healthy -> degraded`创建`notification_route_degraded`；`degraded -> healthy`创建
   `notification_route_recovered`。edge id由slot/type/trigger event稳定派生，独立outbox有1/5/15分钟退避。
4. route-health edge按any-route ACK结算，即使main policy为2-of-2，也优先通过任一尚存route报告通知基础设施降级。
5. main quorum未达成的同一sweep不立刻再次发送edge；edge durable保留，后续worker sweep独立推进。单route全断不创建
   自我告警event，因为同一路无法证明自身故障；原main event继续pending，route状态仍记degraded。
6. meta-alert delivery不反向更新route健康，避免observer用自己的告警递归证明自己；route健康只来自immutable outage event的
   实际投递结果。它是边沿通知，不是周期probe。
7. receiver/evidence/recovery schema升级v4。v3历史event的ACK向量保持unknown，不伪造成功route；offline verifier验证
   route set、checkpoint、bitmask/quorum、edge trigger和pending policy一致性。
8. admin-only`GET /v1/notification-routes`输出secret-free当前策略、slot健康和pending edge数量；`/readyz`继续只表示内部worker/DB。

## 后果

- 1-of-2不再把fallback失败写成全绿；尚存route会收到独立降级/恢复event，恢复与备份后仍可解释。
- evidence能证明某次event最后一次本地ACK向量，但仍不能证明平台最终展示、老板已读或物理故障域独立。
- 没有业务event时，长期坏route仍可能保持unknown/旧healthy；周期silent canary仍是明确剩余缺口。
- v3部署升级前必须备份receiver；schema v4新增两表与两个outbox checkpoint列。

## 不再做的事

- 不把aggregate quorum success等同于所有route健康。
- 不用receiver restart修复downstream provider。
- 不保存endpoint、provider、credential、response body或异常详情。
- 不把route-health edge冒充continuous end-to-end canary。
