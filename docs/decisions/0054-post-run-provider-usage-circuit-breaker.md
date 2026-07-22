# ADR-0054: Post-run Provider Usage Circuit Breaker

**状态**:Accepted
**日期**:2026-07-21
**决策者**:Codex / Round 216

## 背景

standing grant已有`max_runs`和wall-clock timeout，但没有真实token证据。项目虽定义了
`TASK_USAGE_RECORDED`和metrics解析器，任何Adapter都没有写入该事件。Codex的machine-readable usage位于
`--json`流末尾的`turn.completed`；这能证明完成后的实测用量，不能在本次调用花费发生前提供硬截断。

官方协议依据：
- [Codex exec event schema](https://github.com/openai/codex/blob/main/codex-rs/exec/src/exec_events.rs)
- [Codex SDK streaming example](https://github.com/openai/codex/blob/main/sdk/typescript/README.md)

## 决策

1. preauthorized Codex固定命令启用`--json`，只把`item.completed/agent_message`正文送入现有输出流。
2. 只接受`turn.completed.usage`中的非负整数；记录input/output/total/cached/cache-write/reasoning token。
3. TaskBus在DONE时先写`TASK_USAGE_RECORDED`，再写`TASK_COMPLETED`；不根据token数猜美元成本。
4. accepted preauthorized proposal保存provider usage和recorded timestamp，作为同一授权跨重启累计的事实。
5. grant新增必填`token_stop_threshold`。每次新调度前检查此前同grant实测总量；达到阈值停止后续run。
6. 任何此前已消费run缺usage evidence时直接停授；不把未知当0，不自动retry/refund。
7. receipt对terminal task同时要求matching usage，显示bounded total tokens；缺失时显示`evidence_missing`。
8. 对外统一称“post-run cumulative circuit breaker/完成后累计熔断”，禁止称per-run hard token cap。

## 否决方案

- **把threshold描述成单次硬预算**：usage只在turn完成时出现，无法阻止当前run越界。
- **按模型价格推算`cost_usd`**：CLI事件不提供可靠model/auth/tier/billing contract，价格也会变化。
- **读取非ephemeral session rollout**：standing task故意ephemeral；私有session文件不是稳定consumer API。
- **usage缺失按0继续**：崩溃、协议漂移或provider错误都会变成无限制后续执行。
- **另建usage ledger表**：proposal已经是grant consumption事实；新增表会制造双写漂移。

## 后果

### 正面

- metrics与standing receipt首次使用provider实际usage，而不是fixture或人工估值。
- 跨重启累计阈值可停止后续无人调用；解析失败和崩溃窗口保守停授。
- JSONL噪音、tool event和thread identity不会泄漏到boss IM。

### 代价与剩余风险

- 一个run仍可能越过threshold；单次硬成本上限需要provider-native pre-run/max-token/spend contract。
- CLI JSON schema可能演进；当前parser对新增字段兼容，但缺关键字段会fail closed。
- 没有真实付费调用，B-014仍需owner样本验证本机版本的实际usage与远端IM receipt。

## 验证

- fake Codex JSONL覆盖message、cached/cache-write/reasoning和total计算。
- TaskBus audit覆盖usage-before-completed事件与结构化detail。
- SQLite proposal restart、receipt token显示、threshold reached和missing evidence停授均有测试。
