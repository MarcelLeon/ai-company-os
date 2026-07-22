# ADR-0088: Signed Dead-Man Evidence Envelope

**状态**:Accepted
**日期**:2026-07-22
**决策者**:Wang / Codex
**相关 Round**:Round 250 proposal, Round 254 implementation

## 背景与问题

ADR-0087把reviewed config、dotenv generation和exact dead-man evidence绑定成expiring commissioning receipt，但该receipt仍由AICO Mac本地operator生成。能写artifact的同用户进程可以伪造结构合法的bundle，再生成一张自洽的新receipt。SHA-256只能发现已固定字节后的漂移，不能证明producer identity。

## 候选方案

### 方案 A — 保持unsigned exact-byte hash

- 优点：零依赖、兼容现状。
- 缺点：不能证明receiver来源，商业威胁模型仍信任本地可写artifact。

### 方案 B — Receiver/AICO共享HMAC secret

- 优点：实现简单。
- 缺点：verifier持有伪造能力；AICO Mac泄露后攻击者可以生成新的合法evidence。

### 方案 C — Owner-pinned Ed25519 receiver signature

- 优点：AICO只持有公钥，能验证exact payload且没有签发能力；artifact可离线携带来源证明。
- 缺点：新增密码学依赖、密钥部署/轮换和schema v2迁移；receiver私钥被攻破后签名不再可信。

## 决策

采用方案C。receiver使用owner预生成、owner-only、checkout-external PKCS#8 PEM Ed25519私钥，对domain-separated exact bundle bytes签名；signed envelope携带payload、signature、payload SHA和公钥key id，但不携带trust anchor。AICO从最终配置固定的SubjectPublicKeyInfo PEM公钥验证。

unsigned evidence endpoint和offline历史审计保持兼容；strict commissioning只接受signed envelope。receipt绑定envelope/payload/key identity并持续验证，但继续固定`receiver_host_attested=false`和`business_absence_ready=false`。

实现使用维护中的`cryptography`库，不调用shell完成运行时签名，不实现自制密码学。key rotation必须显式更新配置、重新导出evidence并recommission；系统不自动生成、复制或轮换私钥。

## 后果

### 正面后果

- 本地AICO verifier不再具备伪造receiver evidence的密钥能力。
- bundle离开TLS连接后仍有可离线验证的producer-key provenance。
- wrong key、payload/signature移植和silent key rotation进入统一fail-closed路径。

### 负面后果

- receiver部署多一个必须备份和轮换的高价值私钥。
- strict用户必须保存独立公钥并在每次rotation后重新commission。
- 签名不证明私钥确实位于独立host，也不证明TLS、provider ACK、fault action或human read。

## 不再做的事

- 不用HMAC让AICO同时拥有验证和签发能力。
- 不信任envelope自带公钥，不把TLS证书当artifact signing authority。
- 不自制Ed25519实现，不把signature OK提升为商业就绪。

## 相关链接

- ADR-0087
- PITFALLS P-104/P-105
- B-012
- Goal Brief `docs/superpowers/specs/2026-07-22-signed-dead-man-evidence-envelope.md`
