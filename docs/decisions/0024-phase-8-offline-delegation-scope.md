# ADR-0024: Phase 8 Offline Delegation Scope

**状态**:Accepted
**日期**:2026-05-18
**决策者**:Codex
**相关 Round**:Round 87

---

## 背景与问题

Phase 8 的验收标准是“睡前下任务,早上看结果”。这不能退化成一个普通长任务命令,也不能变成绕过审批的无人值守自动执行器。它需要让老板用项目办公室语义托管一个目标,让 lead agent 在既有项目、团队、记忆、审批和审计边界内推进,并留下早报入口。

## 候选方案

### 方案 A — 直接实现无人值守调度器

- 优点:更接近“夜里自动干活”的想象。
- 缺点:需要调度、重启恢复、权限预算、失败恢复和多 agent 编排,容易绕过现有审批纪律。
- 复杂度:高。

### 方案 B — 只复用普通项目消息

- 优点:零新增复杂度。
- 缺点:没有“托管工单”语义,老板无法区分睡前派工和普通咨询,早上也缺少固定验收入口。
- 复杂度:低,但产品价值不足。

### 方案 C — 先做 project-scoped offline delegation work order

- 优点:形成 `/overnight <goal>` 的老板入口,复用当前项目 lead、appointment prompt、memory、approval、audit、task trace 和 `/daily`。
- 缺点:第一切片仍是单 lead 工单,不是完整夜间调度系统。
- 复杂度:中低。

## 决策

选择 **方案 C**。

## 决策理由

- 对齐北极星的“远程异步地指挥真实团队”:老板说目标,lead agent 接管并留早报。
- 不绕过 Phase 4 的审批门禁:风险任务仍进入 `/approve`。
- 不新增持久化和调度器,先复用已有 task/session/audit 体系,降低 Phase 8 第一切片风险。

## 后果

### 正面后果

- `/overnight <goal>` 成为 Phase 8 的明确入口。
- 普通项目团队、共享记忆、审批和报告能力可以立刻复用。
- 早上验收路径固定为 `/daily <project>`、`/tasks`、`/task <id>`。

### 负面后果

- 当前托管记录是进程内的,重启后只能从 audit/task 状态侧间接恢复。
- 第一切片只派给当前项目 lead/default role,还没有多 step 调度和多 agent 自动分派。

### 我们接受这些代价是因为

- Phase 8 的首要风险不是功能不够炫,而是无人值守时越权执行。
- 先把老板入口、项目边界和早报路径跑通,再加持久化与调度。

## 不再做的事

- 本阶段不实现绕过 `/approve` 的夜间自动授权。
- 本阶段不引入独立调度器或 cron worker。
- 本阶段不让 `/overnight` 跨 project/team 自动共享上下文。

## 相关链接

- ROUNDS Round 87
- 相关代码:`src/aico/core/offline_delegation.py`
