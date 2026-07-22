# Goal Brief: Confirmed Required-Component Runtime Alerts

## Goal

当AICO进程、heartbeat和dead-man pulse仍正常，但required业务组件已经失败时，系统必须在老板缺席期间通过既有独立
runtime-alert sink创建durable incident，而不是等待人工运行doctor。

## Non-goals

- 不因generic health自动restart、restore、重跑provider或消费grant。
- 不告警optional组件、DEGRADED或单次瞬时失败。
- 不把platform ACK写成老板已读，也不替代整机dead-man receiver。
- 不在SQLite、heartbeat、CLI或webhook中保存异常、endpoint、secret、target或业务正文。

## Contract

1. 每份heartbeat先取得self-healing snapshot和component health，再推进alert coordinator。
2. 只有`required=true && status=FAILED`连续出现三次才确认；snapshot时间必须严格增加，restart不能清零，重复snapshot不能放大。
3. 第三次确认、active incident和immutable outbox open event必须同事务提交；失败全部回滚。
4. FAILED→DEGRADED不resolved；FAILED→OK或owner显式将组件改为optional才发同incident的resolved。
5. 同名owned-task OPEN/RECOVERING与health failure只能产生一个incident；Channel dependency health仍可独立于polling task告警。
6. event沿用stable event/incident identity和现有1/5/15分钟持久重试、队首顺序与`Idempotency-Key`。
7. unsafe plugin name发送`health:<kind>:id-<hash>`，不得把原名带到外部payload。
8. state schema v13将confirmation table纳入backup/reset；`aico-state`只输出candidate count。

## Machine acceptance

- transient、optional、DEGRADED均不open；三次distinct required FAILED才open。
- 计数跨store rebuild保留；相同时间重放不计数。
- outbox insert失败时confirmation/open/outbox全回滚。
- OK发送same-incident resolved；sink失败/restart仍重试相同event。
- matching owned-task circuit不重复告警；unsafe name不出现在payload。
- heartbeat集成证明process持续存活时required health failure仍能open/resolved。
- state backup/reset/CLI覆盖新表且不展示component raw value。

## External acceptance boundary

owner仍需配置独立HTTPS receiver并用真实required component故障验证只收到一组open/resolved；当前本地测试、SQLite event和
webhook fake均不能证明真实外部送达、整机可用或老板已读。
