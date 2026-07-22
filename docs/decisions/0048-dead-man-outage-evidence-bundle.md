# ADR-0048: Exportable Dead-Man Outage Evidence Bundle

**状态**:Superseded by ADR-0078
**日期**:2026-07-21
**决策者**:Codex
**相关 Round**:Round 210

## 背景

B-012 要求在第二故障域完成 kill、持续 launch failure、network isolation 三类真实 outage sample。现有 receiver
能持久记录 open/resolved和交付状态，但 owner只能看 downstream通知或直接查 SQLite；截图不可机器复核，直查 DB
又耦合内部 schema并容易暴露路径/运维细节。

## 候选方案

### A. 只保留通知截图

拒绝。截图不能严格验证 event identity、open/resolved顺序、retry状态或 disarm/restart后的持久性。

### B. 让验收脚本直接读取 receiver SQLite

拒绝。它暴露部署路径和内部表结构，无法安全地从独立主机导出，也把 verifier耦合到存储实现。

### C. public evidence endpoint

拒绝。outage history和monitor identity属于运维证据，pulse/public authority不应获得读取权限。

### D. admin-only versioned bundle + offline strict verifier

采用。receiver导出 bounded、secret-free JSON；本地 CLI离线验证 schema、identity、outage/event顺序和delivery
约束，并输出精确字节 SHA-256供归档比对。

## 决策

- 新增 admin-only `/v1/monitors/{runtime_id}/evidence`;pulse/missing/wrong token均无读取权限。
- export先按 receiver time执行 expiry evaluation,再导出 current monitor和最近 N 个完整 outage group。
- 每组固定一条 opened和可选 resolved；包含 event identity/time、local delivered、failure attempt count和pending
  next-attempt time，不含 transport/config/request/exception/operator note。
- response按 outage count截断而不是 raw event count,不能把 resolved与其 opened切开。
- immutable events在 disarm后仍可导出；runtime既无 monitor也无 event时返回 404。
- `aico-dead-man-evidence` 只读本地 JSON,严格验证并可要求最低 complete outage数和all-delivered。
- verifier输出 artifact exact-byte SHA-256。它只支持后续完整性比对，不是来源签名，也不证明物理故障或独立部署。

## 后果

### 正面

- 外部 outage验收可以保存为稳定机器证据，不再依赖截图或内部 DB查询。
- restart/disarm、delivery retry和open-before-resolved都能由同一 artifact复核。
- verifier可在与 receiver隔离的环境运行,无需持有任何 receiver credential。

### 代价

- admin endpoint仍需 owner通过 TLS安全获取；artifact本身应按运维证据保护。
- bundle只能证明 receiver记录的事实和local sink ack,不能证明 host位置、fault操作或downstream exactly-once。
- 当前没有签名密钥体系；若未来需要第三方不可否认性,必须另立 key-management ADR。

## 不再做的事

- 不把通知截图、hash或valid bundle单独称为B-012完成。
- 不让 pulse/public authority读取 outage history。
- 不在 bundle保存URL、token、路径、exception或任意人工备注。
- 不让 verifier联网、arm/disarm或触发故障。
