# ADR-0091: Evidence-First Boss-Absent Comparative Benchmark

**状态**:Accepted
**日期**:2026-07-22
**决策者**:Wang / Codex(协作)
**相关 Round**:Round 258

---

## 背景与问题

新目标要求AICO在相同模型、任务集和预算下强于当前Codex Goal。只写能力清单或挑选成功样本无法证明比较结论；多Agent还容易通过
Agent数量放大预算，漏失任务、漏usage和缺证据也可能被从分母中静默删除。

同时，当前还没有owner授权正式模型调用。实现阶段必须能验证计分合同，又不能把synthetic fixture冒充真实成绩。

## 候选方案

### 方案 A — 人工阅读两侧日志后给结论

- 优点：实现成本低。
- 缺点：口径会漂移，私有日志不可公开复核，漏样本和预算聚合难以发现。

### 方案 B — 只比较五项聚合分数

- 优点：报告简单。
- 缺点：AICO可以在部分任务缺失、预算仍失控或关键restart/approval证据缺失时凭相对分数获胜。

### 方案 C — 运行前冻结合同，逐任务记录有界证据，确定性计分并叠加绝对门槛

- 优点：任务漂移、漏样本、重复结果、预算缺口和证据缺口都可机器拒绝；同一artifact可离线复算。
- 缺点：harness必须准确采集usage、角色checkpoint和故障注入receipt；不能直接复用任意聊天日志。

## 决策

选择 **方案 C**：

1. 正式run前使用`aico-benchmark freeze`冻结model、reasoning effort、repo revision、两侧版本、wall window、共享
   `max_total_tokens`和task set canonical SHA。冻结后不得编辑。
2. v1 task set固定覆盖normal completion、cross restart、evidence drift、approval required和budget pressure五类场景；每个正式run
   两侧使用相同task对象和harness事件。
3. 每个system/task只允许一条`BossAbsentTaskResult`。结果必须绑定canonical contract SHA；unknown task、duplicate或task drift拒绝计分。
4. evidence只接受`present|failed|missing`：present/failed必须携带receipt SHA，missing不得携带SHA。artifact不保存raw prompt、token、
   chat identity、absolute path或private log正文。
5. 漏task继续留在completion/evidence分母；漏usage或超共享上限计入budget loss；漏takeover evidence按cap+1惩罚。AICO多Agent
   usage必须合并为该task唯一的`total_tokens`。
6. 相对胜出要求五项至少四项严格更优、无回退，且无人值守完成率与预算失控率严格更优；此外AICO必须全task dispatch/complete、
   required collaboration全完成、零预算失控、complete样本全证据，并提供restart、IM takeover和approval证据。
7. CLI退出`0`仅表示全部门槛通过，`1`表示有效non-win，`2`表示artifact invalid。synthetic fixture只验证机器合同，不得写为正式成绩。

## 安全与口径边界

- canonical SHA绑定exact JSON合同，不证明artifact采集者诚实；正式run仍需要独立harness和owner-safe receipt。
- `total_tokens`是provider usage口径，不等同美元账单；两侧必须使用同一provider/model usage定义。
- Codex Goal baseline只按冻结版本和实际可观察能力计分，不推断其内部不存在的能力，也不把普通Codex multi-agent自动算入Goal。
- 当前只完成离线runner和synthetic验证；没有实际模型调用，因此不能声称AICO已经胜出。

## 后果

### 正面后果

- benchmark结论可由同一contract/results离线重算，缺失与失败不会被成功样本掩盖。
- 相对指标和AICO最低商业可用线分离，避免“比基线少失败但自身仍不可用”。
- 正式运行前就能发现任务、预算与版本不公平。

### 负面后果

- harness实现和证据采集成为下一切片；在它完成前只能做synthetic dry-run。
- v1口径变更需要新version/task fingerprint，不能修改历史run合同。
- 正式模型benchmark会消费owner预算，仍需单独授权。

## 相关链接

- `benchmarks/boss-absent-v1/tasks.json`
- `benchmarks/boss-absent-v1/README.md`
- `src/aico/core/boss_absent_benchmark.py`
- `src/aico/app/boss_absent_benchmark_cli.py`
- `docs/benchmarks/boss-absent-vs-codex-goal.md`
