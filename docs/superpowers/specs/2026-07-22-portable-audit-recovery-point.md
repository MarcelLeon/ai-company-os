# Portable Audit Recovery Point — Goal Brief

**Round**:224
**Status**:Implemented
**Goal**:把live audit JSONL与matching checkpoint作为一个一致、可移交、可离线验证的恢复点，而不是让operator分别复制。

## Problem

Round 223让ledger/checkpoint能检测篡改，但daily ops仍要求人工复制两个文件。runtime可能恰好在两次复制之间追加event，
得到各自合法但彼此不匹配的恢复资产；只保存JSONL、运行时lock或重新seal都不能修复这个问题。

## Contract

- `aico-audit backup --output <new.zip>`在既有audit writer lock内验证并复制ledger/checkpoint；仅允许完整sealed历史，
  唯一合法的checkpoint lag会先推进后再取快照。
- recovery point是`0600`、new-path、单文件ZIP，固定只含`manifest.json`、`audit.jsonl`和
  `audit.jsonl.checkpoint.json`；不包含live lock或绝对源路径。
- manifest记录schema、aware creation time、event count、ledger size/head以及两个member的size/SHA-256；artifact输出
  独立outer SHA-256供owner在另一信任位置记录。
- `verify-backup`不需要live audit路径：拒绝symlink/宽权限/多余、重复、加密或压缩member，流式核对member hash，
  materialize到private temp并调用production ledger verifier，最后比对manifest与chain/checkpoint summary。
- 发布使用同目录temporary + hard-link no-overwrite + file/directory fsync；已有artifact不覆盖，发布失败不留下半成品。

## Acceptance Evidence

- 有event与初始化空ledger均可backup/verify；backup后live继续追加不会改变artifact point-in-time。
- event已fsync而checkpoint失败的合法crash window在snapshot前收敛，artifact内无checkpoint lag。
- member修改、manifest同步改hash、额外/压缩member、outer SHA mismatch、宽权限和symlink全部fail closed。
- live文件删除后仍能离线verify；summary/manifest不泄漏payload或绝对源路径。
- output已存在、source缺失/legacy未seal、directory fsync失败均不覆盖既有数据或留下published artifact。

## Stop Conditions

- ZIP包含完整审计正文，`0600`不是静态加密；off-device目标、加密、凭据、retention和访问审计仍由owner/B-013决定。
- self-consistent manifest不是签名；outer SHA必须记录在独立信任位置，否则同主机攻击者仍可重写artifact和manifest。
- 本轮没有实现destructive restore或整资产恢复演练，也没有把state/memory/config/receiver DB打进同一个bundle。
- snapshot为一致性在复制期间持有audit writer lock；大ledger应在维护窗口导出，rotation/增量备份属于后续容量设计。
