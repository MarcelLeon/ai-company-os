# Goal Brief: AICO Isolated Multi-Agent Runner

## Goal

让AICO在同一frozen task和总token budget内，由核心系统编排多个不同Agent，跨进程恢复exact checkpoint，并为后续五场景正式
receipt采集建立不会重复provider调用的执行主干。

## Acceptance

- runtime admission绑定exact model/effort和五项执行能力，任一缺失fail closed。
- frozen required roles按顺序派发，不同role使用不同agent id并消费前一artifact SHA。
- 所有role共享一个remaining-token budget；超限usage仍持久化并计入total。
- provider调用前保存稳定dispatch intent；crash后只对账，不知道结果时保持ambiguous且不重放。
- restart task首checkpoint后暂停，新进程必须提供不同runtime instance SHA才能继续。
- state为owner-only、atomic、restart-safe，identity/pending/checkpoint漂移拒绝加载。
- `role_chain_complete`不冒充terminal benchmark result；本轮不调用模型或IM。

## Stop Conditions

- 不通过放开Agent自由协作来绕过managed budget。
- 不让一个Agent扮演多个角色取得协作分。
- 不在dispatch outcome不明时重跑provider。
- 未补齐scenario和terminal evidence前不写入正式task result。

## Evidence

- ADR-0094记录managed orchestration、dispatch reconciliation和distinct-agent决策。
- AICO runner与正式scorer共同执行distinct-agent/shared-budget/chain gate。
- 26条runner+benchmark定向测试通过。
