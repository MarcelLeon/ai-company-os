# ADR-0073: Continuous Recovery Artifact Custody Attestation

**状态**:Accepted
**日期**:2026-07-22
**决策者**:Codex / Round 235

## 背景

ADR-0072会在创建core recovery set后立即deep verify，但VERIFIED receipt之后，artifact仍可能被删除、篡改，目标目录可能
掉线/被替换，权限也可能变宽。若heartbeat只读取创建时SQLite receipt，在下一次capture前会错误保持绿色。

## 候选方案

- 只在下一次capture时发现：否决；最长一个backup interval内会产生false-green恢复健康。
- heartbeat每30秒同步hash整个artifact：否决；大artifact会阻塞事件循环并触发health timeout/I/O放大。
- 独立后台custody cadence + heartbeat cheap continuity gate：采用。
- 发现异常后自动restore或删除坏artifact：否决；custody检测不授予破坏性权限。

## 决策

1. scheduled receipt schema v2绑定目标目录的kernel-visible device/filesystem/inode指纹SHA；不保存raw path/device值，也不
   宣称这是storage provider签名或volume UUID。
2. 每份VERIFIED backup同时记录custody VERIFIED/check time。独立custody cadence在worker thread重新打开artifact/sidecar，
   校验owner-only regular file、sidecar SHA/receipt、artifact SHA并运行production recovery-set deep verifier。
3. 删除、字节漂移、receipt drift、权限放宽、目录身份变化或custody max age超限均使required runtime health FAILED；失败
   次数和最后检查时间持久化，`aico-state`只显示状态/次数/时间，不显示目标指纹。
4. heartbeat只做目录安全与身份连续性的cheap stat gate；大文件deep verify由scheduler执行。backup和custody使用独立cadence，
   更改backup频率不能创建新的destination identity binding。
5. destination identity变化时禁止下一次capture静默建立新基线。owner若有意迁移存储，应使用新的明确output path并重新走
   doctor/外部存储验收；scheduler仍不restore/delete/create missing mount。

## 后果

- “创建时可验证”提升为“无人值守期间持续证明最新恢复点仍在且字节可信”，storage loss不再最长一个备份周期false green。
- kernel指纹只能检测本机可见identity连续性，不证明加密、第二故障域、云端durability或同一物理介质；合法remount若identity
  变化也会保守失败，需要owner显式迁移/复核。
- state schema升级v9；recovery-set schema v6及`business_restore_ready=false`不变。B-013仍需真实off-device和restore演练。

## 相关链接

- ROUNDS Round 235
- ADR-0072
- PITFALLS P-091
- Goal Brief `docs/superpowers/specs/2026-07-22-continuous-recovery-artifact-custody.md`
- `src/aico/app/recovery_backup_scheduler.py`
