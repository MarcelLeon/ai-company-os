# ADR-0075: Durable Scheduled Disposable Recovery Drill

**状态**:Accepted
**日期**:2026-07-22
**决策者**:Codex / Round 237

## 背景

scheduled backup、continuous custody与bounded retention分别证明恢复点会生成、字节仍可读、磁盘增长受控，但它们没有持续执行
production restore/materialization路径。长期无人值守时，恢复代码或artifact内部语义可能腐化，而SHA与deep verify仍保持绿色；
若必须等operator手工运行`aico-recovery drill`，问题可能直到真实事故才暴露。

## 候选方案

- 继续只提供手工drill：否决；恢复路径健康重新依赖缺席的人。
- 自动restore到live state：否决；演练不授权破坏业务状态，也不能在runtime活跃时替换truth source。
- 默认关闭、durable intent驱动的disposable scheduled drill：采用。
- 每份daily backup都drill：否决；I/O与临时容量无界放大，应由独立cadence和max age约束。

## 决策

1. drill是scheduled backup下独立的owner opt-in策略，配置interval、max age和可选owner-only isolated workspace；默认使用系统私有
   临时子目录。max age不得短于interval，workspace不得与checkout或backup destination重叠。
2. 每次到期选择最新VERIFIED + custody VERIFIED backup，先写稳定`PENDING` intent，再进入RUNNING并调用既有
   `drill_recovery_set`。它在disposable目录实际执行state/audit/memory production materializer，不生成live restore路径。
3. 成功receipt绑定backup id、artifact/backup-receipt SHA、drill policy SHA、component counts/heads、config revision和仍需
   post-restore evidence数量；固定`business_restore_ready=false`。`aico-state`不显示artifact path、workspace或config值。
4. 失败按1/5/15/15分钟最多五次；RUNNING重启恢复为同一intent的immediate RETRYING且不消耗一次尝试，因为drill无外部副作用。
   open drill使health DEGRADED，EXHAUSTED或receipt超过max age使health FAILED。
5. open drill及当前最新EXHAUSTED drill的目标backup受retention保护。即使owner关闭drill，只要retention仍启用就必须加载durable
   drill store，避免配置切换后删除失败现场；后续新drill成功后，旧历史失败不永久阻塞retention。

## 后果

- boss-absent runtime可以持续发现“artifact字节没变，但production materialization已经失败”的恢复路径腐化。
- drill会消耗I/O、CPU和临时磁盘；默认关闭且cadence独立，owner必须结合backup大小和业务窗口配置。
- state schema升级v11。该receipt仍不是off-device来源、checkout/reinjection/provider/receiver复原、RPO/RTO或live业务恢复证明，
  B-013保持DEFERRED。

## 相关链接

- ROUNDS Round 237
- ADR-0050
- ADR-0073
- ADR-0074
- PITFALLS P-093
- Goal Brief `docs/superpowers/specs/2026-07-22-durable-scheduled-recovery-drill.md`
- `src/aico/app/recovery_drill.py`
- `src/aico/app/recovery_backup_scheduler.py`
