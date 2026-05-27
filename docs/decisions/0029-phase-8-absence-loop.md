# ADR-0029: Phase 8 Absence Loop

**状态**:Accepted
**日期**:2026-05-26
**决策者**:Wang / Codex
**相关 Round**:Round 118

---

## 背景与问题

Round 112 将 AICO 的核心差异化明确为老板缺席操作模型:老板经常不在电脑前,但本地 AI CLI 团队仍然要能被 IM 指挥、推进、审批、叫停、交接和追责。

Phase 8 已经有 `/overnight`、Goal Brief、lead decision、SQLite state、quiet heartbeat 和 `/inbox` 第一切片。新的问题是:后续把 persistent memory、Dream cycle、self-improving、outcome grading、hybrid retrieval 都接进来时,如果没有统一执行合同,Agent 很容易把它们做成互不相干的功能点,偏离“睡前下任务,早上看结果”。

## 候选方案

### 方案 A — 继续按功能列表推进
- 优点:实现自由度高,每项可以独立开发。
- 缺点:Dream、memory、grader、inbox 容易各自为政;下一轮 Agent 会优先做自己熟悉的技术点,而不是闭环。
- 复杂度:低。

### 方案 B — 一次性设计完整无人值守公司循环
- 优点:理论上覆盖多 step、多 agent、自动审批、自动复盘。
- 缺点:范围过大,容易绕过审批和审计边界;也不利于真实 IM dogfooding。
- 复杂度:高。

### 方案 C — 定义 Phase 8 Absence Loop,按 sprint 小步交付
- 优点:把所有新能力都绑定到同一条老板缺席闭环,每个 sprint 都有 IM 验收路径。
- 缺点:需要在文档中持续维护执行顺序,短期不能随意跳到更酷的 memory backend。
- 复杂度:中。

## 决策

选择 **方案 C:Phase 8 Absence Loop**。

Phase 8 的短期执行合同是:

```text
老板下任务
  -> agent 执行
  -> 风险暂停审批
  -> reviewer/grader 验收
  -> 结果进入 inbox / morning report
  -> 经验进入 dream candidates / runbook memory
  -> 下一次任务自动召回
```

## Sprint 队列

### Sprint 1 — Actionable Inbox

`/inbox` 不只是状态列表,而是老板回来后的第一处理入口。每条 item 必须带下一步动作,优先覆盖 approvals、running、failed/interrupted/rejected、overnight、Goal Brief、lead decision 和 collaboration follow-up。

### Sprint 2 — Morning Handoff

先做手动 `/morning` 或 `/daily` 强化,再考虑定时推送。早报必须汇总 done、blocked、risks、next actions、approvals,让老板不用翻 `/tasks` 才能接手项目。

### Sprint 3 — Outcome Grader

Goal Brief 的 `done` 不能只靠执行 agent 自报。任务完成后应能派 reviewer/tester 按 acceptance rubric 给出 pass/fail/gaps,并把结果写回 `/task` 和 `/inbox`。

### Sprint 4 — Dream and Runbook Memory

Dream cycle 读取 audit、task、memory、offline records 和 raw episodes,产出 candidate memories、contradictions、stale items 和 project/role runbook 建议。第一版必须 reviewable,不能直接覆盖 active memory。

### Sprint 5 — Hybrid Retrieval

在不改变 MemoryGovernor / scope / purpose 边界的前提下,把检索后端升级为可插拔的 SQLite FTS、embedding、graph rerank 或其它 scorer/index 组合。

## 执行护栏

- 每轮只推进一个 sprint;跨 sprint 内容只能写成下一轮建议。
- 没有 IM 验收路径的功能不算完成。
- Dream 不能直接覆盖 active memory,只能产出 candidate / reviewable diff。
- Outcome grader 不能绕过 approval policy。
- Retrieval backend 只能替换 scorer / index,不能绕过 MemoryStore、MemoryRetriever、MemoryGovernor。
- 任何自动继续执行都必须可 `/interrupt`,并进入 `/inbox` 可见。
- 每轮仍必须更新 `STATUS.md` 和 `docs/journal/ROUNDS.md`。

## 后果

### 正面后果

- Phase 8 后续功能不再是散点,而是围绕老板缺席闭环递进。
- Agent 接手时能直接从 sprint 队列知道短期该做什么。
- Dream/self-improving 被约束为“帮助交接和下次执行”的产品能力,不是泛化的研究功能。

### 负面后果

- P4 hybrid retrieval 等技术升级会被推迟到 inbox、morning、grader 闭环之后。
- 每次实现都要补 IM 验收脚本和状态文档,交付成本更高。

### 我们接受这些代价是因为

AICO 的 Phase 8 目标是“睡前下任务,早上看结果”,不是展示最多 agent-memory 论文概念。先把老板缺席时的接手、审批、验收和复盘闭环做好,比先换更聪明的记忆后端更符合北极星。

## 不再做的事

- 不把 `/overnight` 扩展成绕过审批的无人值守 YOLO。
- 不让 Dream 自动改写主记忆。
- 不先做泛化 vector DB / graph DB 重构。
- 不把 morning handoff 做成只能在本机 GUI 看的报告。

## 相关链接

- `NORTH_STAR.md`
- `STATUS.md`
- `docs/playbooks/phase-8-absence-loop.md`
- `src/aico/core/inbox.py`
