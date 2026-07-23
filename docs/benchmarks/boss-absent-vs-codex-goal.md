# Boss-Absent AICO vs Codex Goal Benchmark v1

## Purpose

验证 AICO 是否在相同模型、任务集和 owner token budget 下，比当前 Codex Goal 更适合老板长期缺席的个人公司。该 benchmark
不比较模型聪明程度，只比较持续编排、跨重启接手、预算控制和证据交付。

## Frozen Baseline

历史admission基线为PATH中的`codex-cli 0.144.5` app-server Goal合同。当前正式候选已更新为签名Codex App
`26.715.72359 (5718)`内嵌的`codex-cli 0.145.0-alpha.30`：persistent thread上的objective/status、token/time usage与
`thread/fork.deferGoalContinuation`声明的automatic continuation。正式run必须重新冻结exact候选版本；`codex exec`没有Goal接口，
不能用一次性exec冒充baseline。不要把Codex普通multi-agent或其他产品能力自动算进Goal基线，也不要声称其不存在未经观测的内部能力。

0.144.5 standalone app-server本身不是continuation宿主；新签名App build已经给出native Goal生命周期语义，但`turn/start`仍要求
调用方提交input。正式baseline必须由ADR-0093 live isolated host admission证明automatic continuation；benchmark runner禁止自造
continue prompt，只能记录opaque input SHA、turn chain、来源、人工介入与Goal/provider usage。candidate build receipt不是正式成绩。

每个正式 run 必须记录 exact CLI version、model、reasoning effort、task revision、token budget、开始时间和原始状态证据。
运行前必须通过ADR-0092 no-model admission；正式Goal thread使用run-isolated Codex home，不能与桌面Codex state DB竞争。

## Fairness Contract

- 同一模型、reasoning effort、初始仓库 revision、task contract、wall-clock window 和 owner max total tokens。
- 禁止一方获得另一方没有的人工提示、隐藏文件或事后修复。
- AICO 的角色分工只允许共享同一总 token budget；不能按 Agent 数量放大预算。
- 网络、账号、外部副作用默认禁用；需要时两侧使用同一显式 owner approval。
- 每项至少 5 个 tasks，包含正常完成、跨重启、证据漂移、需要审批和预算压力场景。

## Five Primary Metrics

1. **无人值守完成率** = 在 window 内达到全部 acceptance 且无人工介入的 tasks / eligible tasks。
2. **跨 Agent 协作完成率** = required role checkpoints 全部具名、有产物、有下游引用的 tasks / 要求协作的 tasks。
   每个required role必须恰有一个checkpoint、来自frozen project appointment中的不同`agent_id`，并绑定不同provider-issued
   execution fingerprint；一个Agent或一个provider thread更换role label都不算跨Agent协作，两侧都必须提供可审计identity与消费链。
3. **接手成本** = owner 从 IM/状态入口判断 done/blocked/next action 所需的中位操作数；同时记录中位秒数，操作数为主指标。
4. **预算失控率** = provider usage缺失或 `total_tokens > owner max` 的 runs / dispatched runs。已经发生但被拒绝采信仍算失控，不能洗掉。
5. **证据完整度** = 满足 terminal state、每项 acceptance、source fingerprint/current、test gate、budget receipt 五类证据的项数 / 应有项数。

## Win Condition

AICO 只有同时满足以下条件才可声称“强于当前 Codex Goal 基线”：

- 五项指标中至少四项严格更优，且另一项不回退；
- 无人值守完成率和预算失控率必须严格更优；
- AICO必须五类任务全部dispatch并完成、预算失控率为0、required collaboration全部完成；
- 所有 AICO complete 样本 evidence completeness = 100%；
- 结果至少包含一次跨进程重启和一次 owner 从 IM 接管；
- approval场景必须有独立审批证据；
- 报告公开失败样本、超预算样本和缺失证据，不只展示成功案例。

## Required Artifact Per Run

```text
docs/benchmarks/runs/<date>-boss-absent-v1/
  contract.json
  task-results.jsonl
  aico-summary.json
  codex-goal-summary.json
  verdict.json
  verdict.md
```

`contract.json`必须在运行前冻结。raw private logs不提交仓库，只在artifact中保存owner-safe hash/path；任何无法独立复核的主张记为
missing evidence。

`task-results.jsonl`每行必须符合`BossAbsentTaskResult`机器合同并绑定`benchmark_id`、canonical contract SHA、system和task ID。
只有真实观察到的证据可以写`present + SHA-256`；`missing`不能携带hash，`failed`必须引用失败receipt的hash。AICO多Agent的provider
usage必须合并成该task唯一的`total_tokens`。漏行、漏usage、超预算、未dispatch、未知task、重复结果和contract/task漂移都不能从分母中消失。

`aico-benchmark score`退出码：`0`表示所有相对指标与AICO绝对门槛同时通过；`1`表示artifact有效但AICO未胜出；`2`表示输入
invalid、drifted、duplicate、oversized或不安全，不能产生胜负结论。

## Current Status

Round 258已完成frozen task set、result schema、deterministic scorer、离线CLI与equal-observation artifact dry-run，并用真实helper
process terminate/new-process resume receipt替换restart synthetic hash，但仍不证明AICO/Codex Goal本身跨重启，也不产生胜负结论。
Round 259再完成真实Codex Goal persistent app-server no-model admission与isolated home/cleanup intent。Round 263完成AICO exact-model
TaskBus/Adapter transport及跨runtime role handoff机器验收。Round 264把actual bounded fixture纳入task-set SHA，增加一次一role的
clean-checkout runtime CLI和owner-only independent observation ledger/finalization。Round 265冻结project assignment并把每个role
绑定exact appointment与provider-issued execution fingerprint；approval/takeover均接入durable intent、Telegram platform ACK、
owner-bound inbound action ledger和exact decision receipt。当前仍未执行真实Telegram/model dogfood，也未获得Codex native host build，
因此Round 265结束时没有正式成绩。
Round 267已补齐真实Telegram approval与takeover transport dogfood：两次都由当前owner在Telegram Web执行1次操作，并产生0600
platform ACK/inbound/decision/grant或takeover receipt。该样本使用synthetic/no-model state，未执行mutation，只关闭IM协议的
外部可用性缺口；Round 267结束时正式model run与Codex native host build仍未发生，因此仍无正式成绩。
Round 268进一步找到并绑定签名Codex App build与明确automatic continuation surface；正式缺口已收窄为live isolated Goal fork、
跨host restart和usage观测，candidate receipt仍不参与评分。
Round 269已实现独立live observer与formal admission桥：它不写`turn/start`，只接受签名desktop host真实PID更换、append-only
per-thread session、restart后`source="goal"`完整turn、Goal/provider usage推进和capability context稳定。当前日常Goal因没有冻结
token budget被正确拒绝；尚缺owner授权的isolated fork/restart真实样本。
首次正式对比仍须另行授权实际模型调用并由isolated harness注入五类事件；
不能把protocol receipt、实现测试或synthetic fixture反向当成benchmark成绩。
