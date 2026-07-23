# Goal Brief: Codex Goal Baseline Admission

## Goal

在任何正式模型调用前，证明frozen Codex CLI能够用与benchmark一致的model/token budget创建真实持久Goal，并在零usage下完整清理，
从而避免把普通`codex exec`误当成Codex Goal基线。

## Acceptance

- exact CLI version与contract匹配；不接受silent version fallback。
- isolated Codex home启动app-server，persistent read-only/no-network thread创建成功。
- Goal set/get返回active、exact token budget、`tokensUsed=0`、`timeUsedSeconds=0`。
- goal clear、thread delete成功；receipt不包含thread id、path、prompt或用户身份。
- cleanup intent为`0600`；连接失败后保留isolated home并可在下一次启动前重连清理。
- unit tests覆盖正常lifecycle、ephemeral/usage漂移拒绝、cleanup callback和stale intent recovery；installed CLI live smoke通过。
- offline turn supervisor绑定model/effort并交叉验证matching provider notification与Goal token delta；不一致fail closed。

## Stop Conditions

- 不调用`turn/start`，不消费模型token，不把admission receipt当benchmark成绩。
- 不复用桌面Codex state DB，不复制`auth.json`；只允许owner-only symlink挂载，正式turn仍需owner预算授权。
- 不触碰外部0字节release-room示例，不重开dead-man/DR。

## Evidence

- ADR-0092记录app-server persistent Goal边界、隔离home与cleanup语义。
- `aico-benchmark probe-codex-goal`生成owner-safe receipt并清理全部临时状态。
- 本机0.144.5 live receipt显示exact model/budget、0 tokens/seconds、goal cleared/thread deleted。
