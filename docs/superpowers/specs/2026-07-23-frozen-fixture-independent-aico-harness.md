# Goal Brief: Frozen-Fixture Independent AICO Harness

## Goal

把实际任务输入纳入frozen task-set，并让独立harness从真实文件与receipt派生AICO scenario evidence，形成可跨CLI进程推进的正式运行入口。

## Acceptance

- 五个task各自内嵌bounded fixture，canonical task-set SHA稳定且测试锁定。
- fixture进入每个role prompt、observation和checkpoint；runner、observer、finalizer拒绝漂移。
- `advance-aico`只接受clean exact-revision checkout，一次只推进一个TaskBus/Codex role。
- observer ledger owner-only、atomic、hash-chain，可由新observer实例恢复。
- observer验证actual artifact/dispatch receipt、fixture drift、approval mutation generation、irrelevant source、external checks、budget、
  takeover ACK和terminal consumption。
- `finalize-aico-observations`只从完整ledger生成ADR-0095 receipt；所有CLI artifact为fresh 0600。
- 五类正例和receipt tamper、approval mutation/revert负例通过；本轮不调用模型或IM。

## Stop Conditions

- 不把objective/acceptance列表冒充完整task input。
- 不让system-under-test自报scenario flags。
- 不把两次content相同冒充期间无mutation。
- 不把no-model transport/collector测试写成benchmark成绩。

## Evidence

- ADR-0097记录fixture、single-step runtime和independent observer边界。
- task-set SHA锁定为`f0acbd3317466f8709cf408ba1403bc0dbda17f0f5367cbd21630861c9462031`。
- targeted observer/benchmark/runner tests与全量gate通过。
