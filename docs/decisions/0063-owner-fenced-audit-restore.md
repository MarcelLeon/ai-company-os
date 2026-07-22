# ADR-0063: Owner-Fenced Audit Restore and Corrupt-Live Quarantine

**状态**:Accepted
**日期**:2026-07-22
**决策者**:Codex / Round 225

## 背景

ADR-0062定义了可移交的ledger/checkpoint恢复点，但“备份可验证”不等于“可以安全覆盖live”。审计恢复同时面对三个
风险：runtime仍在写、当前live已经损坏而无法生成普通安全备份、正文与checkpoint两次替换之间进程崩溃。

## 候选方案

- 解压后直接覆盖两文件：否决；没有runtime fence、恢复前留存和中途崩溃语义。
- 先删除live再复制：否决；扩大无审计窗口，失败后不可复跑。
- 损坏live一律拒绝恢复：安全但不可运营；真正事故时反而无法恢复，也会诱导operator手工删除证据。
- 自动选择最新备份并恢复：否决；备份选择与破坏性覆盖必须由owner显式确认。
- owner fence + mandatory preservation + staged pair replacement：采用。

## 决策

1. live restore必须显式提供expected artifact SHA、真实AICO state DB作为runtime owner fence、new-path preservation输出和
   `--yes`；active runtime、错误state identity或任一校验失败都不修改live。
2. 覆盖前若live可验证，生成标准portable safety backup；若live损坏或unsealed，复制owner-owned原始字节到标记为
   `unverified_quarantine`的固定artifact。quarantine只供取证，不可冒充可恢复备份。
3. 备份先在private temp中走production materializer。ledger与checkpoint在目标目录完成staging后依次`replace+fsync`；
   第二次替换前崩溃会留下明确不一致并fail closed，同一备份重跑可收敛。
4. `drill-backup`只在disposable workspace调用同一materialization primitive，复核chain/checkpoint parity并可发布
   owner-only、new-path evidence report；它不触碰live，也不取得live owner lock。
5. 不提供scheduled/automatic restore。component drill/restore仍不能替代off-device、加密、全资产和业务RTO/RPO演练。

## 取舍与后果

- 两文件无法用可移植单次rename事务发布；选择“中断后可检测、可重跑”而不是假装跨文件原子性。
- restore前留存增加时间与空间，但保留了回退或取证依据；preservation失败时拒绝覆盖。
- runtime fence绑定现有AICO state DB，要求operator准确提供与生产runtime相同的state path。
- quarantine含可能敏感或恶意的原始字节，仍需owner-only和外部加密，并应与正常恢复点隔离保管。
