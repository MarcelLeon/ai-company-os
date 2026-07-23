# ADR-0101: Native Codex Host-Run Observation

**状态**:Accepted
**日期**:2026-07-23
**决策者**:Wang / Codex(协作)
**相关 Round**:Round 272

---

## 背景与问题

ADR-0093定义了`CodexGoalHostRunReceipt`的turn、usage和人工介入合同，但此前正式finalizer仍直接读取该模型。即使字段内部一致，
外部脚本仍可手写turn source、runtime和provider delta，无法证明这些事实来自Codex Desktop原生session。

## 候选方案

### 方案 A — 继续信任host-run JSON

- 优点：流程简单。
- 缺点：只能证明schema一致，不能证明native continuation、runtime归属或真实usage。

### 方案 B — benchmark runner自行发送续跑input并记录turn

- 优点：容易生成完整ledger。
- 缺点：runner会成为continuation owner，测到AICO harness而不是Codex Goal。

### 方案 C — 运行前冻结，运行中采样，运行后只读派生

- 优点：runner不拥有续跑写通道；turn、输入来源、usage和runtime均来自第一方持久事实。
- 缺点：正式run需要在每个仍存活的Desktop runtime至少取一次签名进程样本。

## 决策

选择 **方案 C**：

1. `run-start`要求exact frozen contract/task/admission、active Goal、相同token budget且`tokens_used=0`，冻结owner-safe session
   inode/size/prefix SHA和provider累计用量。
2. 初始client turn必须携带exact `<aico_boss_absent_initial_task>` envelope；owner介入必须携带
   `<aico_boss_absent_owner_decision>`并绑定decision receipt SHA。其他client input一律拒绝。
3. native continuation必须呈现相邻`task_complete → task_started → turn_context → source="goal"`，5秒内自动开始；仅伪造Goal
   marker但从普通client turn启动不能归类为native continuation。
4. 每个turn要求exact model/effort、never approval、read-only/no-network；provider累计usage逐turn前进，并与最终read-only Goal
   usage完全相等。
5. `run-sample`只通过签名Codex App的exact Desktop app-server进程生成runtime observation。每个turn的开始与完成必须落在唯一
   runtime sample窗口内，runtime SHA不能由调用方直接指定。
6. scenario observer与最终result必须绑定完整`CodexGoalHostRunObservationReceipt` SHA；公开CLI不再接受裸
   `host-run.json`作为正式输入。

## 后果

- host admission、host run、native subagent、scenario和score形成逐层只读派生链。
- 原始thread ID、prompt和session内容仍留在owner-private文件；评分artifact只保存domain-separated SHA与bounded receipt。
- 该合同不生成真实成绩。B-015仍需owner授权的isolated Goal/App restart样本，五task模型run还需单独预算授权。

## 相关链接

- ADR-0093
- ADR-0100
- B-015
- P-131
- `src/aico/app/boss_absent_codex_goal_run_observer.py`
- `src/aico/app/boss_absent_codex_goal_observer_cli.py`
