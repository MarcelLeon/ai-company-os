# Goal Brief: Native Codex Goal Host Contract

## Goal

冻结Codex Goal自动续跑的真实所有权与证据合同，确保正式baseline使用native Codex host，而不是由benchmark runner给standalone
app-server编造continuation prompt。

## Acceptance

- 明确app-server只提供Goal control plane和turn observation，不声称拥有自动continuation。
- formal admission拒绝standalone app-server、runner constructed input、非隔离state、不可观察provider usage和非default capability。
- turn ledger不保存raw prompt，只保存opaque input SHA、turn chain、Goal status/usage与provider usage。
- initial/native continuation/owner takeover/harness injection来源分离，owner takeover准确计入human interventions。
- sequence、previous turn SHA、跨turn token continuity、Goal/provider delta、token budget和terminal stop全部fail closed。
- 单测覆盖正常native continuation及每类边界拒绝；不调用模型、不发送IM。

## Stop Conditions

- 不把standalone app-server loop命名为Codex Goal baseline。
- 不逆向、猜测或复制Codex host raw continuation prompt。
- 没有native host adapter/build receipt前不启动formal model benchmark。
- 不触碰外部0字节release-room示例；不恢复dead-man/DR投入。

## Evidence

- ADR-0093记录native host continuation边界与被否决方案。
- `boss_absent_codex_goal_host.py`提供host admission、turn receipt和run ledger机器合同。
- generated 0.144.5 app-server schema没有continuation API；37条Codex Goal/benchmark定向测试通过。
