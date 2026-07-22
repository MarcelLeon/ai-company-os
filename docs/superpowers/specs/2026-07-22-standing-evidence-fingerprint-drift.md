# Goal Brief: Standing Evidence Fingerprint and Drift Gate

## Goal

让standing result从“完成时证据存在”提升为“老板接手和下一次自治时仍是同一份有界证据”，变化或缺失时自动停授。

## In scope

- repo-relative path/line/file SHA-256/size组成的bounded manifest。
- 16 source、256KiB/file与bounded revalidation window。
- SQLite restart重算、inbox/morning drift projection、next-run fail closed。
- 不保存正文、不在IM展示path/hash。

## Out of scope

- 业务语义正确性、来源签名、Git commit attestation。
- 自动恢复/重跑、文件锁或filesystem snapshot。
- off-device evidence、真实owner/provider/scheduled IM样本。

## Acceptance

1. complete result保存可重算manifest与aggregate digest，重复文件只读取一次。
2. 文件变化显示drifted，删除/root/legacy manifest显示missing。
3. drift/missing均阻止下一次scheduled dispatch。
4. 单次结果最多4MiB证据IO，老板面最多复核最近5份；历史增长不造成无界扫描。
5. SQLite round-trip保持证据状态，老板消息不含path/hash/raw source。

## Stop conditions

- 不把hash称为签名、语义真值或真实provider证据。
- 不保存source正文，不自动重跑。
- 不让revalidation成本随全部历史无限增长。
