# Goal Brief: Independent Dead-Man Receiver Recovery

## Goal

让第二故障域中的dead-man receiver拥有与其monitor/outage/outbox语义匹配的独立online backup、offline deep verify、
disposable drill和owner-fenced restore，同时防止AICO主机恢复时把仍在工作的外部故障证据源一起回滚。

## Acceptance

- receiver进程全生命周期持有由DB路径派生的kernel owner lock；并发receiver与active-worker restore均fail closed。
- backup用SQLite online backup API生成`0600`、standalone、new-path artifact，允许receiver在线运行。
- verify要求exact schema version/DDL、无trigger/view/user index、integrity/foreign-key检查，并深验monitor checkpoint、
  payload-column identity、outage open/resolved顺序、delivery先后和aware timestamps。
- drill在private disposable workspace调用同一production restore primitive，比较恢复前后semantic counts，清理临时状态并可发布
  owner-only、secret/payload/path-free report。
- restore要求独立SHA与`--yes`，只有取得receiver owner lock后才执行；有效live先生成verified safety backup，无法验证的
  DB/WAL/SHM进入owner-only unverified quarantine，替换后清理stale sidecar。
- core recovery set升级schema v5；`dead_man_receiver_state`保持`included=false`，但以
  `external_component_recovery`标记独立合同已就绪。它不与主set同步snapshot或combined restore。

## Non-goals

- 不部署第二故障域、TLS、owner notification sink，不制造真实kill/network/outage样本。
- 不把receiver DB、monitor/runtime/event identity或通知payload嵌入AICO core recovery set。
- 不提供scheduler restore、自动选择latest、AICO恢复触发receiver restore或跨主机global transaction。
- 不把本地drill、artifact SHA或schema验证写成off-device retention、来源签名、RPO/RTO或商业DR完成。
