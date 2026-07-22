# Owner-Fenced Audit Restore — Goal Brief

**Round**:225
**Status**:Implemented
**Goal**:让portable audit recovery point可以先演练、后由owner安全恢复，同时保留损坏现场并让中断恢复fail closed。

## Problem

Round 224只有backup/verify。operator若自行解压覆盖，可能与active runtime竞争、覆盖前丢失当前证据，或只成功替换
ledger/checkpoint其中一个。损坏live又无法生成普通verified safety backup，最容易诱发“先删掉再恢复”的不可逆操作。

## Contract

- `drill-backup`要求独立记录的expected SHA，在private disposable目录调用production materializer，重新验证
  chain/checkpoint parity；可生成`0600`、new-path、无payload/path的JSON报告，成功失败都清理workspace。
- `restore`要求live audit path、有效AICO state DB、expected SHA、new preservation path与`--yes`。恢复持有从同一
  state DB派生的runtime owner lock；active runtime、错误DB identity、已有输出或错误SHA都在覆盖前拒绝。
- 当前live完整时，preservation是可由`verify-backup`复核的标准safety artifact；live损坏/unsealed时，原始owned
  regular file字节进入`unverified_quarantine`，manifest只含固定member name/size/hash，不宣称ledger有效。
- production pair replacement先复制并验证staged pair，再替换ledger、fsync目录、替换checkpoint、再次fsync并复核。
  中途故障留下严格reader可发现的不一致；同一可信artifact可重跑收敛。
- 所有artifact/report均no-overwrite，错误输出不包含live path或审计payload。

## Acceptance Evidence

- disposable drill通过且不改变live，workspace清空、report为owner-only且无私密正文。
- 从较旧artifact恢复会生成包含当前较新历史的verified safety backup，再把live收敛到artifact count/head。
- 篡改live会生成包含原始损坏字节的unverified quarantine，随后恢复成功；manifest/summary不泄漏payload/path。
- 缺`--yes`、错误artifact SHA、非AICO state file或active runtime都不创建preservation、不修改live。
- 注入checkpoint replace失败后production verifier必须拒绝现场；恢复原语重跑后pair与source一致。

## Stop Conditions

- restore永远不由scheduler自动触发，也不自动选择“最新”artifact。
- quarantine是取证容器，不是签名、修复或可信恢复点；不能送入普通restore。
- 本地component drill不证明artifact确实来自off-device，也不覆盖memory/config/secret/receiver DB和IM业务恢复。
- owner仍需按B-013选择加密外部存储、独立SHA authority、RPO/RTO、retention和隔离checkout演练。
