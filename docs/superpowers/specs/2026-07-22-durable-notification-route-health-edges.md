# Goal Brief: Durable Notification Route Health Edges

## Goal

当1-of-2 outage通知由一路ACK、另一路失败时，receiver不能false green；它必须跨重启保存逐路结果，并通过尚存route主动通知
缺席老板“通知冗余已降级”，后续真实event证明恢复时再发恢复边沿。

## Non-goals

- 不声称不同route位于不同云、账号、网络或物理故障域。
- 不把local ACK解释为平台展示或老板已读。
- 不用route failure驱动receiver restart、provider replay、restore或授权消费。
- 本轮不发送周期canary；没有outbound event时不宣称连续验证route健康。

## Contract

1. main delivery返回1至2个bounded ACK结果；异常详情、URL、token和response不持久化。
2. event ACK checkpoint、route状态、main settle/defer和新健康边沿同事务提交。
3. first failure生成stable degraded edge，degraded后的success生成stable recovered edge；重复失败不重复开边沿。
4. route-health edge使用独立durable outbox，按any-route ACK结算并复用1/5/15分钟退避，不受main 2-of-2阻塞。
5. meta-alert不递归更新route健康；单route失败不创建无法送达的自我告警。
6. pending main或route-health edge期间禁止改变route/quorum策略。
7. schema v4 evidence/recovery验证逐event ACK、当前route状态和edge trigger；v3历史ACK保持unknown。

## Machine acceptance

- 1-of-2部分成功后main delivered、失败slot degraded、surviving route收到一个degraded edge。
- 后续真实event双ACK后失败slot healthy，并发送一个recovered edge；duplicate failure不重复开单。
- 两路同时失败时main与两个degraded edge跨restart保留；任一路恢复后main和edge分别收敛，不递归生成无限event。
- 未投递route-health edge阻止策略切换；admin endpoint与evidence不暴露URL、token、response或异常正文。
- v3→v4保守迁移、exact recovery DDL/domain、ACK mask与edge metadata tamper均有回归。

## External acceptance boundary

owner仍需用两个真实provider制造partial ACK、双断和恢复，保存平台ACK及终端展示。当前route状态是event-driven observation；
真实商业continuous health还需要未来silent canary或provider-native可验证probe合同。
