# Goal Brief: Signed Dead-Man Evidence Envelope

## Goal

让strict runtime commissioning只接受由owner固定的receiver Ed25519公钥验证通过的exact-byte dead-man evidence，关闭“本地可写artifact可被重写后重新commission”的来源信任缺口。

## Threat Model

需要抵抗：

- evidence bundle离开receiver后被修改、替换或与另一签名拼接。
- AICO Mac上的普通同用户进程伪造一份新的、结构合法的receiver evidence。
- receiver换钥后继续用旧公钥或旧签名静默通过commissioning。
- unsigned historical bundle被误用为strict current-health evidence。

明确不抵抗：

- receiver私钥或receiver主机本身被攻破。
- owner把攻击者公钥错误固定进最终配置。
- TLS终止层、通知provider、owner账号或手机被攻破。
- 同一用户进程修改`.env`、公钥与receipt后同时控制owner的recommission操作。

## Proposed Wire Contract

新增`signed-dead-man-evidence-envelope-v1`，只包含：

- 固定schema/algorithm标识：`schema_version=1`、`algorithm=ed25519`。
- `payload_base64`：receiver导出的exact JSON bundle bytes，不重新解释或重新序列化后签名。
- `payload_sha256`：方便operator和日志做secret-free比对，必须与decoded bytes一致。
- `signature_base64`：Ed25519对domain-separated message的64-byte签名。
- `public_key_sha256`：DER SubjectPublicKeyInfo的SHA-256 key id，不嵌入公钥。

签名输入固定为：

```text
AICO-DEAD-MAN-EVIDENCE-V1\x00 || payload_bytes
```

domain separation防止同一receiver key未来被其他协议复用时发生cross-protocol signature confusion。Envelope使用Pydantic `extra=forbid`、有界base64字段和canonical JSON输出，但签名只覆盖decoded payload，不依赖envelope JSON键顺序。

## Key Lifecycle

- receiver只接受已存在的unencrypted PKCS#8 PEM Ed25519私钥文件；不在进程启动时自动生成。
- 私钥路径必须absolute、regular non-symlink、owner-owned、`0600`，且不得位于checkout；错误时receiver startup fail closed。
- owner使用离线`openssl genpkey -algorithm Ed25519`生成私钥，并用`openssl pkey -pubout`导出SubjectPublicKeyInfo PEM公钥。
- AICO只读取公钥；公钥可以公开，但本地文件仍要求regular non-symlink、owner-owned且不可group/world writable，防止静默替换。
- rotation必须生成新evidence envelope、更新最终`.env`公钥路径并生成新的commissioning receipt；旧运行进程因dotenv/receipt/key drift进入required health FAILED。
- 不允许一个envelope携带“信任哪个公钥”的完整公钥并自证；trust anchor必须来自owner固定的独立路径。

## Compatibility

- 现有`GET /v1/monitors/{runtime_id}/evidence`保持不变，用于历史审计和旧runbook。
- 新增`GET /v1/monitors/{runtime_id}/signed-evidence`；receiver未配置私钥时返回固定503，不回显路径或解析错误。
- `aico-dead-man-evidence`默认仍可验证unsigned历史bundle；只有显式`--trusted-public-key`才接受signed envelope并验证来源。
- `aico-commission create|verify`和`AICO_ABSENCE_ADMISSION_MODE=strict`必须提供trusted receiver public key；不提供、unsigned、key id漂移或signature失败均fail closed。
- Runtime commissioning receipt升级schema v2，绑定envelope exact-byte SHA、payload SHA和公钥key id；`receiver_evidence_signature_verified=true`，但`receiver_host_attested=false`、`human_read_attested=false`、`business_absence_ready=false`。

## Failure Semantics

- 私钥、公钥、PEM类型、权限、base64、payload hash或signature任一错误只返回固定secret-safe错误。
- verify先验证envelope结构、hash与signature，再执行现有bundle schema/runtime/age/outage/delivery/probe/route检查。
- signature成功不放宽任何现有strict evidence条件。
- 运行中公钥、envelope、receipt、dotenv、config或TTL漂移继续投影为required `configuration:commissioning-receipt` FAILED；不自动reload、restart、rotate key或replay provider task。
- receiver不得把私钥内容、私钥hash、路径或底层解析异常写进API、evidence、heartbeat或日志。

## Rejected Alternatives

- HMAC：AICO verifier必须持有同一secret，AICO Mac被同用户进程控制后即可伪造receiver evidence。
- 自制Ed25519实现：安全审计成本不可接受；使用维护中的`cryptography`库。
- 只签canonicalized model JSON：producer/consumer序列化差异可能改变签名语义；必须签实际导出的exact bytes。
- 在envelope内携带公钥并直接信任：只能证明“某个未知私钥签过”，不能证明owner信任的receiver签过。
- 让TLS证书代替artifact签名：bundle离开TLS连接后失去可携带的来源证明，且反向代理证书不等于receiver evidence authority。
- 签名成功即设置`business_absence_ready=true`：签名不证明第二故障域、TLS、故障动作、provider ACK或owner终端展示。

## Acceptance Matrix

- 合法Ed25519私钥生成signed envelope；owner固定的matching公钥验证通过。
- payload单bit修改、signature修改、key id修改、wrong key、non-Ed25519 PEM、invalid base64全部失败。
- signature从一个envelope移植到另一个payload失败；domain prefix缺失或变化失败。
- unsigned endpoint保持原schema；未配置signer时signed endpoint固定503且不泄露路径。
- private key权限过宽、symlink、checkout内路径和非owner文件导致startup失败。
- public key替换、permission放宽、envelope替换和receipt schema v1在strict commissioning中失败。
- valid signature + stale bundle、未完成probe、degraded route或pending delivery仍失败。
- doctor/install与Telegram/Feishu startup在launchctl/Channel/state前拒绝unsigned/mismatched evidence。
- heartbeat持续验证signature与key identity，失败进入现有confirmed required-component alert，不触发业务副作用。
- targeted、full root、SME、Ruff、mypy、format、structure、JSON、Compose、offline wheel与diff全部通过。

## Rollout Order

1. 引入`cryptography`并实现独立sign/verify primitive与adversarial tests。
2. 增加receiver optional signer和signed endpoint，保持unsigned endpoint兼容。
3. 扩展offline verifier输出signature facts，但不改变历史默认语义。
4. 升级commissioning schema/CLI/env/service/runtime strict binding。
5. 更新receiver部署、Quickstart、Daily Ops、Troubleshooting、absence playbook、ADR、PITFALLS、BLOCKERS、CHANGELOG、STATUS与ROUNDS。

## Human Confirmation Required

这是密码学依赖、receiver wire contract和strict deployment workflow的组合变更。按开发规范，进入实现前需要owner明确确认采用Ed25519 + `cryptography`方案。
