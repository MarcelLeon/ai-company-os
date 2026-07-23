# Goal Brief: Boss-Absent Benchmark Runner

## Goal

把“强于Codex Goal”从能力描述变成可冻结、可复算、缺失不隐身的机器判定合同；本切片只完成离线artifact与scorer，不调用真实模型。

## Acceptance

- 冻结五类task set，并用canonical SHA绑定run前合同。
- result schema拒绝duplicate/unknown/drifted结果、伪造checkpoint关系和不一致evidence hash。
- 漏task保留在completion/evidence分母；漏usage/超预算计budget loss；漏takeover按有界惩罚计分。
- 五项相对指标与AICO全task、全协作、零预算、全证据、restart/IM/approval绝对门槛同时决定win。
- `aico-benchmark freeze|score`只读输入、有界解析、拒绝symlink/duplicate key/non-finite JSON，输出owner-safe JSON/Markdown。
- synthetic tests覆盖win、non-win、invalid artifact、缺task、预算缺口和关键绝对门槛；equal-observation dry-run生成事件、结果与报告，
  verdict固定non-win。

## Stop Conditions

- 不把synthetic fixture、单测或CLI exit 0称为正式benchmark成绩。
- 不调用真实provider、不创建standing grant、不发送Telegram；正式run需owner另行授权。
- 不恢复或覆盖外部清空的`examples/release-room/aico-project.json`。
- 不重开owner已暂停的整机失联告警和灾难恢复。

## Evidence

- ADR-0091记录freeze-before-run、missing denominator、shared usage与双层win gate。
- tracked task set与README记录五种确定性harness事件和result contract。
- unit tests、Ruff、mypy、format和CLI temp-directory freeze/dry-run smoke通过；dry-run真实terminate helper并由新进程校验durable
  checkpoint SHA，但不冒充被测AICO/Codex本身的restart证据。
- `STATUS.md`、`ROUNDS.md`、`PITFALLS.md`和CHANGELOG记录本轮边界与下一步harness缺口。
