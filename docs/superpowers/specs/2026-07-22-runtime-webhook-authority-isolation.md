# Goal Brief: Runtime Webhook Authority Isolation

## Goal

阻止runtime incident alert与dead-man pulse复用不兼容的strict endpoint或bearer authority后仍通过absence admission。

## Contract

- 两条URL同时配置时必须exact-distinct；允许同origin不同path。
- 两个bearer同时配置时必须exact-distinct；不在输出、exception、state或receipt中返回原值。
- service readiness与Phase1 runtime必须复用同一个pure validator。
- 冲突在install调用launchctl前、runtime构造Channel/state前失败。
- strict aggregate必须把endpoint isolation纳入机器合同，不得一边显示strict OK一边显示isolation FAIL。
- 不把不同URL/token称为物理故障域、真实provider独立或human read。

## Acceptance

1. same URL + distinct token：service和Phase1均FAIL。
2. distinct URL + same token：service和Phase1均FAIL。
3. distinct URL + distinct/单侧token：既有配置继续通过。
4. readiness输出不含URL/token；production loader继续secret-safe。
5. targeted/full tests、Ruff/mypy/format/structure、JSON/Compose/wheel/diff全绿。

## Non-goals

- 不联网探测endpoint，不部署receiver，不验证TLS证书或provider账号。
- 不要求两个endpoint必须different-origin；第二故障域由B-012外部证据处理。
- 不改变webhook payload schema、retry或delivery authority。
