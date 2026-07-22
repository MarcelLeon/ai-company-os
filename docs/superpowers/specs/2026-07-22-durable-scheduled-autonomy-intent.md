# Goal Brief: Durable Scheduled Autonomy Intent

## Objective

关闭晨报platform ACK之后、standing autonomy决策被安全记录之前的静默窗口；重启后无证据时继续有界推进，已有持久
dispatch-decision证据时不重复派发，并让未形成result的at-most-once窗口继续可见。

## Acceptance

- 每个scheduled delivery在任何外发前持久化稳定autonomy intent，并与delivery/project/binding绑定。
- accepted proposal和task在provider dispatch前携带同一intent；重启时用该证据结算，不重跑provider。
- 没有accepted证据时才有界重试；中断与notification歧义可见，五次耗尽使runtime health失败。
- `aico-state`分别展示morning delivery和secret-free autonomy摘要；raw target/message/proposal/task identity不泄露。
- SQLite schema/backup/reset、Phase1 wiring、orchestrator contract、operator文档和崩溃窗口测试同步更新。

## Stop conditions

- 不把platform ACK、autonomy dispatch、human read或result outcome合并成单一成功状态。
- 不声称exactly-once notification、provider side effect rollback或跨系统事务。
- 没有真实owner配置时不安装runtime、不发送IM、不消费provider。
