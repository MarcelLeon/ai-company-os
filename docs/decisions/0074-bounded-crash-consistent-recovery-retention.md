# ADR-0074: Bounded Crash-Consistent Recovery Retention

**状态**:Accepted
**日期**:2026-07-22
**决策者**:Codex / Round 236
**Supersedes**:ADR-0072中的“scheduler不自动删除旧artifact”决策

## 背景

scheduled backup与continuous custody已经约束恢复点新鲜度和当前可读性，但长期无人值守会无限累积artifact，最终可能耗尽目标盘，
反过来让新恢复点无法生成。直接按mtime或文件名清理又会删除未验真的恢复点，并在进程崩溃时留下无法解释的半删除pair。

## 候选方案

- 永不自动删除：否决；把磁盘耗尽留给缺席的operator，不满足长期boss-absent运行。
- 按目录mtime/数量直接删除：否决；目录不是truth source，也没有custody、intent或崩溃恢复证据。
- 默认关闭、owner显式授权的bounded retention state machine：采用。
- 自动restore或自动创建/重绑目标目录：否决；retention授权不扩大到恢复和storage迁移。

## 决策

1. retention独立默认关闭。owner启用时必须配置年龄、至少保留两个最新VERIFIED代际、检查间隔和单轮最大清理数；候选只来自
   同一destination binding下已有VERIFIED receipt且最新custody为VERIFIED的记录，并按最老优先处理。
2. 删除前先把`PRUNING` intent、开始时间和完整策略SHA事务性写入SQLite，再重新deep verify artifact/sidecar。验真失败保留
   两份文件与intent，并使required health FAILED，不回退为VERIFIED。
3. 删除固定顺序为artifact→目录fsync→sidecar→目录fsync，随后才写`PRUNED`。SQLite永久保留receipt SHA、artifact SHA、
   destination fingerprint SHA、policy SHA和时间戳作为tombstone；不把“文件不存在”冒充无历史。
4. 重启按存在矩阵收敛：pair都在则复验后重删；仅sidecar在则验证receipt后删除；两者都无则结算；仅artifact在视为不可能的
   receipt-loss状态并fail closed。owner关闭开关只能阻止新intent，不能取消已持久化的破坏性intent或隐藏其FAILED health。
5. retention不调用restore、不删除FAILED/未验真记录、不扫描/接管未知文件，也不mkdir/rebind storage。目录容量、加密、第二故障域、
   provider-side lifecycle/WORM和真实restore drill仍需外部证据。

## 后果

- 长期无人值守的本机恢复目录从无界增长变为显式授权、代际/年龄/批次有上限且可审计的清理闭环。
- crash可能暂时留下`PRUNING`和半个pair，但不会静默恢复绿色或猜测成功；artifact-only需要owner调查，不能自动删。
- state schema升级v10。ADR-0072的capture/verify/no-auto-restore决策继续有效，但其blanket no-delete决定由本ADR取代。
- B-013仍未关闭：本状态机不证明真实off-device storage policy已启用、provider retention已生效或商业RPO/RTO已演练。

## 相关链接

- ROUNDS Round 236
- ADR-0072
- ADR-0073
- PITFALLS P-092
- Goal Brief `docs/superpowers/specs/2026-07-22-bounded-recovery-retention.md`
- `src/aico/app/recovery_backup.py`
- `src/aico/app/recovery_backup_scheduler.py`
