# Goal Brief: Expiring Runtime Commissioning Receipt

## Goal

把owner-reviewed配置、当前loaded dotenv代际与strict dead-man外部证据绑定为一个会失效的secret-free runtime准入事实。

## Acceptance

- create/verify绑定clean reviewed Git config、safe runtime identity、dotenv metadata generation fingerprint与exact evidence bytes。
- expiry不晚于bundle maximum age或completed silent-probe TTL，verify按当前时刻重跑strict evidence。
- receipt/evidence必须owner-only且位于checkout外；receipt不含dotenv path、metadata、content/content hash。
- strict doctor/install/runtime startup在任何launchctl/Channel/state前fail closed。
- 运行中漂移投影为required `configuration:commissioning-receipt` FAILED，不自动reload/restart/replay。
- full tests、Ruff/mypy/format/structure/JSON/Compose/wheel/diff通过。

## Non-goals

- 不联网commission，不签名artifact，不证明receiver host/TLS/provider ACK/fault action/human read。
- 不把receipt写成`business_absence_ready=true`，不自动覆盖旧receipt或修改`.env`。
