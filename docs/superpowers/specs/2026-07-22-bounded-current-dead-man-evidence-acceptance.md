# Goal Brief: Bounded Current Dead-Man Evidence Acceptance

## Goal

让dead-man离线证据既可保留历史审计用途，也能在显式strict验收中拒绝陈旧bundle、过期/未完成silent probe和非healthy route。

## Acceptance

- verifier/CLI可要求正有限的最大bundle年龄，并拒绝future-generated artifact。
- fresh probe按验收时刻重新计算，且必须enabled、settled、至少完成一次。
- all-routes-healthy把unknown与degraded都fail closed。
- 三项可组合，不修改evidence/summary schema，不联网、不读取credential。
- full tests、Ruff/mypy/format/structure/Compose/wheel/diff通过。

## Non-goals

- 不签名artifact，不证明receiver host/TLS、provider/platform ACK、human read或真实fault action。
- 不自动生成commission receipt，不在runtime startup联网，不改变历史bundle的默认离线校验行为。
