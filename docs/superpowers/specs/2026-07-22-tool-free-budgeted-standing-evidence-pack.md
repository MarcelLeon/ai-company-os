# Goal Brief: Tool-Free Budgeted Standing Evidence Pack

## Goal

让一次 owner-preauthorized standing run 在派发前拥有确定的证据上下文和 token envelope；运行后只有 provider usage 未越界、
result 完整引用 allowlisted 当前证据时，系统才接受业务结果并允许老板通过 IM 接手。

## Acceptance

- external grant schema v2 强制 `max_total_tokens`，旧 grant fail closed。
- charter 强制配置 bounded evidence sources；系统生成不超过 64 KiB、带完整源 SHA 的 allowlisted pack。
- Codex preauthorized command tool-free、read-only、no-network、no-resume、no-collaboration，并写入 rollout/context budget。
- 结果只能引用 pack 中的原始 path/line；unlisted、oversize、missing、symlink、marker ambiguity和drift均拒绝。
- provider terminal usage超过 owner limit时保留usage、拒绝result，并在 outcome/morning/inbox显示budget exceeded。
- 单测覆盖上述边界，root Ruff、mypy和全量测试通过。

## Stop Conditions

- 不把 post-run usage gate 描述成 provider 美元 hard quota。
- 不创建真实 grant、不改 `.env`/LaunchAgent、不调用付费 provider、不发送 Telegram；真实复验需 owner 单独授权。
- 不扩大到 suspended dead-man receiver 或 disaster recovery。
- 若本机 Codex CLI 不接受 strict rollout config，保持 standing autonomy disabled并更新 B-014。

## Evidence

- ADR-0090 与五指标 benchmark 固定方案和口径。
- unit/integration tests证明 evidence pack、budget breach、preflight、receipt和配置合同。
- current AICO/SME charter可在真实仓库生成低于64 KiB的pack。
- `STATUS.md`、`ROUNDS.md`、`PITFALLS.md`、`BLOCKERS.md`和CHANGELOG完成连续性更新。
