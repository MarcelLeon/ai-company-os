# Bounded Recovery Retention — Goal Brief

**Round**:236
**Status**:Implemented
**Goal**:让长期boss-absent runtime在不依赖operator定期清盘的前提下，有界、可恢复、可审计地清理已验真的旧恢复点。

## Problem

Round 234/235能持续capture并证明artifact custody，却不会释放旧代际。长期无人值守会使恢复目标无界增长，最终因容量耗尽阻断
新的恢复点。普通目录轮转无法证明删除对象已经deep verify，也无法解释artifact与receipt之间的崩溃窗口。

## Contract

- 默认关闭；只有owner显式开启才创建新prune intent。策略同时约束age、至少两个最新代际、check cadence和单轮最大删除数。
- 候选必须是同一binding下的VERIFIED + custody VERIFIED记录；先保留最新N份，再从满足age的旧记录中按最老优先选择。
- SQLite先持久化`PRUNING`与policy SHA，再复验artifact/sidecar，按artifact→fsync→sidecar→fsync删除，最后写`PRUNED`。
- tombstone永久保留receipt/artifact/policy SHA与时间证据；`aico-state`不显示artifact path或destination raw identity。
- 重启收敛pair/sidecar-only/neither三种安全状态；artifact-only fail closed。既有PRUNING即使开关关闭也必须恢复且health FAILED。
- 不restore、不删除FAILED/未知文件、不mkdir/rebind，不声明外部storage lifecycle、encryption、WORM或commercial DR。

## Acceptance Evidence

- 默认关闭时即使artifact过龄也不删除；启用后age与minimum-generation双门槛均生效，单轮不超过配置上限。
- 删除前字节漂移会留下两份文件、durable PRUNING与FAILED health；custody FAILED记录永不成为候选。
- crash发生在删除artifact后、删除pair后均能重启结算；receipt先丢而artifact仍在时保留artifact并失败。
- 关闭retention后，已有PRUNING仍能完成收敛；开关只影响新授权，不能抹掉既有intent。
- state schema v10和CLI暴露secret-free tombstone字段；Phase1/service config完整透传且拒绝不足的保留窗口。

## Stop Conditions

- 本轮不创建`.env`、真实storage artifact或LaunchAgent，不调用provider/IM，也不自动restore。
- 本机retention tombstone不是storage provider删除证明、数字签名、第二故障域或restore rehearsal。
- 未获得真实外部storage/retention/RPO/RTO证据前，B-013和`business_restore_ready=false`保持。
