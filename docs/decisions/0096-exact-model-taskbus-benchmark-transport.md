# ADR-0096: Exact-Model TaskBus Benchmark Transport

**状态**:Accepted
**日期**:2026-07-23
**决策者**:Wang / Codex(协作)
**相关 Round**:Round 263

---

## 背景与问题

ADR-0094定义了restart-safe managed role runner，但此前runtime仍是fake transport。现有preauthorized Codex边界只强制只读和
token上限，没有把frozen exact model/reasoning effort写入Task metadata与真实CLI命令。即使角色链跑通，也不能证明两侧使用
相同模型；provider完成后、runner提交checkpoint前崩溃还需要一个可跨进程读取的dispatch receipt。

## 候选方案

### 方案 A — benchmark harness直接调用Codex subprocess

- 优点：实现短。
- 缺点：绕开TaskBus、Adapter capability gate与统一usage，形成第二套执行语义。

### 方案 B — 复用TaskBus，但只在contract文档声明model/effort

- 优点：兼容现有调用。
- 缺点：Adapter可静默使用默认模型，公平合同无法机器验证。

### 方案 C — exact model进入preauthorization合同，以TaskBus作为唯一真实transport并持久化产物/receipt

- 优点：复用生产任务状态、Adapter capability和provider usage；跨runtime可按dispatch id对账。
- 缺点：正式run仍需真实role-to-agent assignment、独立scenario collector与owner模型预算授权。

## 决策

选择 **方案 C**：

1. benchmark task必须成对携带exact model与reasoning effort；Adapter缺少或拒绝该能力时，provider调用前fail closed。
2. Codex Adapter把exact model写入`--model`，把effort写入strict config；standing-autonomy旧任务未携带该合同则保持兼容。
3. AICO role通过真实`TaskBus.submit/stream_output/task_usage`执行；每个role仍使用shared remaining-token limit和exact output约束。
4. frozen role映射到不同`agent_id`；下一role只读取前一内容寻址artifact的exact SHA。
5. provider成功后先写owner-only durable observation receipt，再把结果交还runner；新runtime按稳定dispatch id恢复，不重复调用provider。
6. provider outcome不明且没有receipt时保持`dispatch_ambiguous`；不能用自动重放换取表面完成率。
7. 明确preflight拒绝发生在pending intent前，避免把确定性能力拒绝误记为未知provider crash。
8. runtime在每次preflight检查timezone-aware时钟与expiry；跨重启后的过期授权不得继续派发。

## 当前证据

- TaskBus runtime单测覆盖exact model/effort、shared budget、distinct agents、artifact传递、0600 receipt和preflight拒绝。
- restart集成测试由第二个runtime instance读取同一state/artifact目录继续reviewer，最终role chain complete且无provider replay。
- 本机Codex CLI只解析烟测接受`--model gpt-5.6-sol`与`model_reasoning_effort="high"`；本轮未调用模型。

## 残余边界

- 配置中的不同`agent_id`目前只证明AICO编排身份，不证明真实project assignment或不同provider session；正式collector必须绑定两者。
- durable receipt关闭“完成后runner崩溃”的重放窗口；provider已接受但receipt未写成时仍会fail closed为ambiguous。
- runtime transport不是formal benchmark成绩；尚缺独立filesystem/process/approval/Telegram/source observer和Codex native host adapter。

## 相关链接

- `src/aico/app/boss_absent_aico_taskbus_runtime.py`
- `src/aico/core/preauthorized_execution.py`
- `src/aico/adapter/codex.py`
- ADR-0094
- ADR-0095
