# Goal Brief: Approval-Gated Benchmark Mutation

## Goal

让approval场景在runner层真正停住，并只在exact owner grant后对isolated fixture执行一次可跨崩溃对账的确定性mutation。

## Acceptance

- implementer checkpoint后phase为`approval_pending`，无checkpoint不得派reviewer。
- request SHA稳定绑定contract/task/fixture。
- grant必须owner-only、未过期并匹配exact request。
- action target/content来自frozen fixture，只能写owner-only isolated root。
- intent先于mutation；预存target无intent拒绝。
- write后crash可生成receipt并恢复state，但不得重写target。
- state、action receipt和independent observer按request/grant/action SHA闭合。
- 单测覆盖正常、重复、崩溃对账、过期、预存target和runner pause；不调用模型或IM。

## Stop Conditions

- 不依赖模型自觉停在审批边界。
- 不接受任意hash解锁runner。
- 不把observer事后发现替代执行前阻断。
- 不把isolated fixture mutation扩大为仓库或外部副作用授权。

## Evidence

- ADR-0098记录runner pause与intent-first executor。
- approval/runner/observer/finalizer tests通过。
