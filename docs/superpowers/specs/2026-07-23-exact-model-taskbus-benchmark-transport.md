# Goal Brief: Exact-Model TaskBus Benchmark Transport

## Goal

让AICO frozen role chain通过真实TaskBus/Adapter合同执行，并把exact model/effort、shared token budget、跨runtime artifact与dispatch
receipt变成机器可验证边界。

## Acceptance

- preauthorized benchmark task成对绑定exact model与reasoning effort，Adapter能力缺失时provider调用前拒绝。
- Codex命令显式携带`--model`和reasoning effort strict config，旧standing task保持兼容。
- role通过TaskBus提交、收集terminal output并读取真实provider usage，不接受usage缺失。
- 每个role映射到不同agent id，下一role只消费前一内容寻址artifact的exact SHA。
- artifact、receipt和runner state均owner-only；新runtime可按dispatch id继续而不重复provider调用。
- 确定性preflight拒绝不创建pending intent，未知provider outcome不自动重放。
- 每次role preflight拒绝已过期授权，不能因runtime重启延长有效期。
- 单测覆盖正常链、restart、能力拒绝和持久恢复；CLI参数只做no-model解析烟测。

## Stop Conditions

- 不绕过TaskBus另建benchmark专用subprocess执行语义。
- 不把配置中的agent id直接写成正式独立Agent成绩。
- 不把post-response token gate冒充provider生成前的美元硬quota。
- 没有独立scenario collector与两侧正式样本前不宣称胜出。

## Evidence

- ADR-0096记录exact-model transport与dispatch receipt边界。
- TaskBus runtime跨第二runtime instance完成lead到reviewer交接。
- targeted lint、mypy、tests与Codex CLI no-model参数解析通过。
