# Tamper-Evident Audit Ledger — Goal Brief

**Round**:223
**Status**:Implemented
**Goal**:老板缺席期间，审计历史被修改、插入、重排、截断或半写时，runtime必须停止把它当成可信事实。

## Problem

`JsonlAuditSink`此前只追加普通JSONL。文件仍然可读不代表历史未被修改：有效JSON字段替换、整行删除或重排都能被
重放为“真实历史”，而老板早晨看到的metrics、task recovery和approval证据会因此失真。

## Contract

- 新记录保留原event顶层字段，并增加`_audit` SHA-256 previous/head link；链使用canonical event payload计算。
- 同目录`<audit>.checkpoint.json`保存event count、byte size和head，检测tail truncation；ledger、checkpoint和lock均为
  当前用户所有的regular non-symlink owner-only文件。
- process file lock串行化多个writer。event先append+fsync，再原子替换+fsync checkpoint；两步之间crash只产生可验证的
  checkpoint lag，下一次启动收敛，不重复event。
- 旧JSONL不会自动信任或重写。owner核对当前baseline后显式运行`aico-audit ... seal`，以现有字节建立检查点。
- runtime replay、`aico-service doctor/install`和`aico-audit verify`遇到篡改、截断、torn record、duplicate id、symlink或
  宽权限时fail closed，不显示event正文。

## Acceptance Evidence

- 修改同长度字段、删除tail、重排、插入和半行写入均被拒绝；active writer下一次append前也会重新验证外部变化。
- legacy未seal不能启动，seal不改event bytes且收紧到`0600`；错误路径不能创建一个伪造的空sealed ledger。
- 模拟event已fsync但checkpoint写失败，restart后能验证并推进checkpoint；同event retry保持exactly once。
- 两个sink交错写入仍保持单链；Phase 1和service doctor都拒绝损坏账本。

## Stop Conditions

- 这是owner-local tamper evidence，不是数字签名、TPM、远端时间戳、WORM或同主机恶意进程防护。
- legacy seal只锚定owner当时接受的baseline，不追溯证明seal前历史真实。
- audit JSONL与checkpoint必须作为同一个恢复资产；off-device保留与真实恢复仍由B-013跟踪。
