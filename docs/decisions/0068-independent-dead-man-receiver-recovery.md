# ADR-0068: Independent Dead-Man Receiver Recovery

**状态**:Superseded by ADR-0078(receiver schema/recovery verification only;independent recovery contract remains accepted)
**日期**:2026-07-22
**决策者**:Codex / Round 230
**Supersedes**:ADR-0067的recovery-set v4 coverage范围；secret-free reinjection决策继续有效

## 背景

core recovery set已覆盖AICO主机上的state/audit/memory、reviewed config与runtime reinjection合同，但独立receiver的
SQLite仍只有“挂持久卷并备份”的文字要求。直接复用主DB工具会漏掉armed monitor、active outage、immutable outbox和worker
停止语义；把receiver DB塞入core set又会把两个故障域错误同步：AICO故障时receiver正是应持续保留和投递证据的一方。

## 候选方案

- 把receiver DB作为core ZIP第五个member同步capture/restore：否决；跨主机没有共享事务，且AICO恢复可能回滚仍有效的外部证据。
- 直接让`aico-state`接受receiver路径：否决；AICO schema/table counts不验证receiver domain semantics，也没有receiver worker fence。
- receiver停机后用文件复制/替换：否决；WAL可能漏写，无法深验或证明restore路径，且active worker可与替换并发。
- 独立online backup/deep verify/drill/owner-fenced restore合同：采用。

## 决策

1. receiver DB引入schema version 1；service lifespan持有与恢复工具相同的path-derived kernel lock，第二个worker或restore在
   active worker存在时fail closed。lock metadata不是authority，kernel lock才是。
2. `aico-dead-man-recovery backup`使用SQLite online backup生成standalone `0600` new-path artifact；在线backup不要求停服务。
3. offline verifier除integrity/user version外，还要求exact table DDL、拒绝trigger/view/user index，并解析全部monitor/event
   domain state，验证partial checkpoint、payload mismatch、outage ordering、delivery overtake与naive timestamp。
4. drill必须在disposable目录调用production restore，按monitor/open/outage/event/pending semantic counts比较，并只输出bounded
   counts、artifact basename和SHA；不泄露runtime/event/payload/path。
5. restore必须提供expected SHA和CLI `--yes`，取得receiver lock后才materialize。live可验证时创建标准safety backup；否则把
   DB/WAL/SHM原字节保留到owner-only unverified quarantine，再替换并清理stale sidecar。
6. receiver恢复按独立cadence和事故条件执行；AICO主机恢复不得触发或授权receiver restore，也不得自动选择latest artifact。
7. recovery-set schema v5只把`dead_man_receiver_state`改为`included=false`、
   `recovery_contract_ready=true`、`external_component_recovery`。manifest不绑定receiver字节或同一时间点；
   `business_restore_ready=false`仍由AI provider live authentication和外部RPO/RTO/IM证据保持。

## 取舍与后果

- receiver在线backup与AICO core capture拥有不同RPO和artifact authority；operator必须分别保存SHA、加密off-device副本与演练证据。
- exact DDL验证使未知migration fail closed；后续schema变化必须显式升级version、verifier和迁移，不接受“表名差不多”。
- 单文件SQLite与WAL/SHM不能作为一组跨崩溃原子rename；restore先保存live现场并让中断显式失败，operator用同一可信artifact重跑。
- unverified quarantine只证明保留了原字节，不证明其一致或可恢复；本地SHA也不是host/TLS/owner身份签名。
