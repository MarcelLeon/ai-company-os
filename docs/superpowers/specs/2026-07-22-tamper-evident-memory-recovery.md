# Goal Brief: Tamper-Evident Memory Recovery

## Goal

让会影响agent后续决策的memory JSONL在老板缺席期间具备可检测篡改、并发安全写入、可移交恢复点、无侵入演练和
owner-fenced恢复，并纳入bounded core recovery set。

## Acceptance

- 多进程writer在同一锁内刷新tail后追加，写失败不发布phantom内存状态。
- 修改、重排、截断、半写、unsealed legacy、checkpoint不匹配均fail closed；legacy只能显式seal。
- backup为owner-only/new-path/fixed-member artifact，offline verify同时核对outer/member hash、ledger chain/checkpoint与
  MemoryAtom/MemoryEdge domain model。
- drill走production materializer且不触碰live；restore要求真实state DB owner fence、expected SHA、显式确认和恢复前保全。
- recovery-set v2绑定state/audit/memory三个独立point，机器输出仍明确不是global transaction或full business restore。

## Non-goals

- 不自动选择或恢复最新artifact。
- 不把`.env`、standing grant或receiver DB塞入core set。
- 不声明本机测试等于off-device commercial DR。
