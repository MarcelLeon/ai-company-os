# Goal Brief: Durable Silent Notification Route Probes

## Goal

在没有outage event时持续、低噪声地验证双通知route的真实POST/credential/bridge链路；probe必须跨重启幂等，confirmed failure主动形成
降级边沿，恢复后形成恢复边沿，不能把探测消息展示给老板。

## Non-goals

- 不证明provider、账号、网络或物理故障域独立。
- 不证明老板终端展示或human read。
- 不兼容无法承诺silent handling的generic webhook；默认保持disabled。
- 不用probe触发repair、restart、restore、业务provider replay或授权消费。

## Contract

1. 仅显式`silent-route-probe-v1`启用，要求双route；payload使用独立event type和stable id，复用真实route URL/token/POST。
2. probe intent先持久化再发送；ACK歧义只重放exact payload/key，完成后按attempt time推进下一窗口，不catch up。
3. 首次probe失败标suspect/PENDING；连续失败达到2-10的持久阈值才degraded，成功清零并按需recovered。
4. probe-derived edge携带`silent_probe` observation source与bounded ACK vector；outage edge继续只引用真实outage event。
5. pending probe/edge围栏配置变化；disable默认与v4迁移都不生成或发送probe。
6. schema v5 evidence/admin/recovery输出secret-free policy、last completion/ACK与route probe checkpoint，拒绝partial/tampered state。

## Machine acceptance

- due probe先落盘；restart取得同一event id、payload与scheduled time。
- 一路连续一次失败只suspect，两次失败才degraded并经尚存route发送一个edge；重复失败不重复开边沿。
- 后续双ACK恢复route并发送一个recovered edge；probe消息本身保持strict event type。
- 双路全断不丢probe observation或edge；worker/readiness不因正常downstream degradation形成restart loop。
- v4→v5默认disabled迁移后的canonical DDL与fresh v5一致；probe/edge checkpoint tamper被offline verifier拒绝。

## External acceptance boundary

owner必须先确认两个真实downstream bridge对`notification_route_probe`只ACK、不展示、不触发事故自动化，再显式启用并保存平台请求日志、
admin/evidence v5与手机“无probe噪声”样本。unit fake ACK不能替代B-012真实provider/终端证据。
