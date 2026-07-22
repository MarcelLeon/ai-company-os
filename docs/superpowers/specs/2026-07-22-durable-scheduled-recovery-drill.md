# Durable Scheduled Recovery Drill — Goal Brief

**Round**:237
**Status**:Implemented
**Goal**:让boss-absent runtime按独立cadence实际走通disposable production materialization路径，而不是只持续验证备份字节。

## Problem

现有scheduler能capture、deep verify、custody和retention，但`aico-recovery drill`仍需要operator记得执行。长期无人值守时，
restore/materializer代码回归、内部语义不兼容或临时恢复路径失败不会被SHA检查发现，真实事故时才暴露。

## Contract

- 默认关闭；只有scheduled backup已启用时才能开启，interval与max age独立于backup/custody/retention cadence。
- 最新VERIFIED + custody VERIFIED artifact先绑定durable drill intent，再在worker thread调用既有production drill。
- workspace使用自动清理的private temp；可选路径必须预先存在、absolute、owner-only且与checkout/output隔离。
- receipt绑定artifact、backup receipt、policy SHA与component evidence；只输出secret-free摘要，保持business readiness为false。
- 五次有界重试；crash中的RUNNING以同一ID恢复且不消费失败预算。due/open为DEGRADED，exhausted/stale为FAILED。
- open/latest exhausted drill保护目标不被retention删除；关闭drill不允许retention遗忘旧intent。
- 不调用live restore、不修改业务state、不生成provider/IM调用，也不声称off-device或RPO/RTO完成。

## Acceptance Evidence

- 默认关闭不创建drill；启用后callback观察到RUNNING已先持久化，成功receipt精确绑定最新backup。
- cadence到期前不重复，下一周期选择最新verified backup；receipt stale与exhausted分别进入健康失败。
- evidence drift不写假receipt并进入RETRYING；五次失败EXHAUSTED，重启RUNNING恢复为同ID且不花attempt。
- open drill目标在跨“drill关闭、retention开启”配置切换后仍不被清理。
- state schema v11、backup/reset和`aico-state`覆盖drill table，且不泄露artifact/workspace/config raw值。
- recovery scheduler完成结构拆分，所有类与方法继续满足项目硬约束。

## Stop Conditions

- 本轮不创建真实`.env`、recovery artifact或LaunchAgent，不执行真实provider/IM或live restore。
- local disposable drill只证明captured state/audit/memory materializer，不覆盖checkout、secret reinjection、provider live auth、
  receiver独立恢复和代表性业务IM验收。
- 未取得真实off-device来源和隔离业务恢复证据前，B-013与`business_restore_ready=false`保持。
