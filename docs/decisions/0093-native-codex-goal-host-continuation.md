# ADR-0093: Native Codex Goal Host Continuation Boundary

**状态**:Accepted
**日期**:2026-07-23
**决策者**:Wang / Codex(协作)
**相关 Round**:Round 260

---

## 背景与问题

ADR-0092证明persistent app-server thread可以承载Goal状态、预算和usage，但0.144.5 protocol没有continuation method。`turn/start`
要求调用方提交input；若benchmark runner在每个turn后自造“继续”prompt，测到的是AICO编写的外部loop，而不是当前Codex Goal宿主能力。

正式baseline还必须区分三类输入：一次frozen initial task、Codex宿主原生continuation、owner/harness事件。否则人工救场、故障注入或
benchmark专用提示词可能被隐藏成无人值守能力。

## 候选方案

### 方案 A — runner固定发送自定义continue prompt

- 优点：可以直接通过standalone app-server循环turn。
- 缺点：prompt和停止策略由AICO项目决定，污染baseline，无法回答“当前Codex Goal”的实际能力。

### 方案 B — 只测单个Goal turn

- 优点：实现简单，usage易采集。
- 缺点：遗漏Goal最关键的跨turn持续推进能力，不满足boss-absent目标。

### 方案 C — native Codex host负责continuation，runner只观察并形成无原文账本

- 优点：不替被测系统发明续跑策略；仍能审计turn链、人工介入、Goal/provider usage和terminal状态。
- 缺点：正式runner必须接入第一方Codex宿主并冻结host build，不能只靠CLI app-server独立完成。

## 决策

选择 **方案 C**：

1. app-server只被视为Goal control plane和turn/usage observation surface，不被视为自动续跑宿主。
2. 正式Codex baseline必须先提交host capability receipt：第一方host build、native continuation、persistent resume、isolated state、
   provider usage可观察及default capability边界全部成立。
3. runner不得构造continuation input。续跑input由native Codex host拥有，结果只记录有界SHA，不保存或复制raw prompt。
4. 每个turn receipt区分`initial_task`、`native_host_continuation`、`owner_takeover`和`harness_injection`；只有owner takeover计一次
   human intervention。任何其他隐式人工输入都不能进入无人值守成绩。
5. turn链必须sequence连续、previous SHA相接、Goal tokens连续，且每turn Goal delta与provider total完全一致；status不再active后
   禁止继续。缺失、漂移或超frozen token budget均fail closed。
6. host admission和turn ledger只证明baseline身份与证据完整性，不证明任务完成，更不产生AICO胜出结论。

## 当前证据

- 本机0.144.5 generated schema有Goal state API、`turn/start`与turn notification，但没有continuation request/notification。
- Round 266新增`probe-codex-goal-host`，现场生成experimental schema并绑定bundle SHA。当前真实receipt为
  `356a6f6bb546f89d464df44effd103622538b340d059e61d57287f32bf6b7b94`：Goal控制面、persistent resume和remote-control
  transport存在，`turn/start`仍强制client input，continuation候选为空，formal admission为false。
- 当前`get_goal`只能返回objective/status/tokens/time，不暴露host continuation prompt或调度器合同。
- offline host admission/ledger tests覆盖standalone app-server、runner自造input、能力缺失、usage/chain漂移和terminal后续跑拒绝。

## 残余边界

- 尚未取得可供isolated formal runner调用的第一方Codex host adapter/build receipt，因此formal run仍未admit；B-015跟踪该唯一
  baseline host阻塞。
- opaque input SHA只能证明观察到的bytes identity，不能解释host内部prompt质量；公平性依赖exact host build与同一frozen task合同。
- owner/harness输入是场景事件，不是native continuation；评分时必须保留其来源和人工介入计数。

## 相关链接

- `src/aico/app/boss_absent_codex_goal_host.py`
- `tests/unit/test_boss_absent_codex_goal_host.py`
- ADR-0091
- ADR-0092
