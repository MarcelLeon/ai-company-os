# ADR-0086: Bounded Current Dead-Man Evidence Acceptance

**状态**:Accepted
**日期**:2026-07-22
**决策者**:Codex
**相关 Round**:Round 248

## 背景

`aico-dead-man-evidence`已经验证bundle schema、runtime identity、完整outage和local delivery，但历史bundle可无限期重复通过。
生成时fresh的silent probe也可能在验收时已经过期，unknown/degraded route则不会阻止基础校验成功。这样的artifact适合历史审计，
不能直接作为配置切换或商用commissioning的当前外部健康输入。

## 备选方案

1. 修改bundle schema并给所有artifact固定TTL：会破坏历史审计用途，也把不同环境的传输窗口写死在producer。
2. verifier默认联网回查receiver：离线验收会获得credential和网络副作用，且把证据验证绑定到当前服务可用性。
3. 保留历史校验默认行为，增加显式、可组合的严格验收条件：由operator声明最大artifact年龄、已完成且按验收时刻fresh的silent probe、
   以及所有当前route为healthy。

## 决策

采用方案3。`--maximum-evidence-age-seconds`必须为正有限数，拒绝未来或超龄`generated_at`；
`--require-fresh-notification-probe`要求probe已启用、无pending、至少完成一次，且按verification time仍fresh；
`--require-all-routes-healthy`把unknown/degraded都视为不满足。三个条件不改变bundle或summary schema，commissioning必须组合使用。

这些检查仍然信任输入artifact，不验证receiver签名、host/TLS、provider ACK、human read或物理故障动作；SHA-256只绑定精确字节。

## 相关链接

- ROUNDS Round 248
- PITFALLS P-104
- Goal Brief `docs/superpowers/specs/2026-07-22-bounded-current-dead-man-evidence-acceptance.md`
- ADR-0048
- ADR-0081
