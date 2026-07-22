# Goal Brief: Alert-Delivery-Aware Dead-Man Renewal

## Goal

当runtime仍能发送dead-man pulse、但承诺的secondary runtime alert持续无法交付时，独立receiver必须停止续租并在TTL后形成可投递outage，不能让“进程活着”掩盖“老板告警路径已失效”。

## Non-goals

- 不新增第三个外部服务或供应商绑定。
- 不把pending/failed状态、receiver ACK或evidence artifact解释为老板已读。
- 不自动restart、restore、重跑provider或消费standing grant。
- 不在pulse中包含incident、异常、URL、token、target或业务正文。

## Contract

1. heartbeat按self-healing→health→alert→liveness推进，并把本轮alert delivery snapshot映射到pulse v2。
2. `disabled/healthy`新pulse续租；`pending/failed`新pulse只排序、不更新续租anchor。
3. receiver TTL到期时按最近已排序状态生成`alert_delivery_unhealthy`或`pulse_expired`，只open一次。
4. 后续healthy/disabled pulse先补齐必要open，再原子resolved并续租；duplicate/older pulse不延期。
5. pulse ACK前冻结exact payload；状态切换允许至多一个pending retry加一个interval的传播延迟。
6. receiver/evidence/recovery schema统一升级v2，v1迁移使用保守默认且不改写历史event payload。

## Machine acceptance

- publisher证明pending payload在失败重试期间不变，ACK后下一pulse传播healthy。
- reference tracker与SQLite store都证明pending/failed只排序、不续租，跨restart后TTL open，healthy后same-reason resolved。
- v1 monitor迁移保留续租/active outage并补`disabled`/`pulse_expired`。
- evidence v2严格要求open/resolved reason一致；backup verifier拒绝非法status、partial checkpoint和reason drift。
- Phase1证明alert snapshot进入pulse；heartbeat证明alert先于liveness。

## External acceptance boundary

owner仍需升级并部署独立receiver，制造真实alert endpoint断路超过TTL，保存`alert_delivery_unhealthy` open/resolved与owner sink ACK。当前本地SQLite、fake webhook和unit tests不关闭B-011/B-012。
