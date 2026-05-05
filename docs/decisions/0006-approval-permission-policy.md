# ADR-0006: 审批权限策略

**状态**:Accepted
**日期**:2026-04-28
**决策者**:Codex
**相关 Round**:Round 16

---

## 背景与问题

Phase 4 已经有危险任务审批门禁,但 Round 13-15 的审批入口只校验 pending task,没有校验“谁可以审批”。在 Telegram 群聊场景里,任意用户只要看到 task id 或短 ID,就可能发送 `/approve` 或 `/reject` 影响任务。这违反北极星第三句里 AI 行为必须“可审批、可审计、可中断”的安全边界。

## 候选方案

### 方案 A — 继续允许任意 Telegram 用户审批
- 优点:实现最简单,不影响现有 smoke test。
- 缺点:群聊里没有权限边界,知道 task id 就能批准危险操作。
- 复杂度:低。

### 方案 B — 默认仅任务发起人可审批,并支持配置额外审批人
- 优点:单人 dogfooding 不需要额外配置;群聊里不会被任意成员审批;需要多人审批时可用配置扩展。
- 缺点:暂时只能配置静态 reviewer id,不支持角色、群组管理员或动态权限。
- 复杂度:低。

### 方案 C — 立即接入 Telegram 群管理员 / ACL 权限系统
- 优点:更接近真实 IM 权限模型。
- 缺点:会把 Telegram 细节带入核心审批逻辑,也需要额外 Bot API 调用和缓存策略。
- 复杂度:中高。

## 决策

选择 **方案 B — 默认仅任务发起人可审批,并支持配置额外审批人**。

## 决策理由

- 它把权限判断放在核心 `TaskBus` 的审批入口,而不是散落在 Telegram 命令解析里。
- 默认允许 requester 审批,保留单人远程 dogfooding 的低摩擦体验。
- 额外审批人通过 `AICO_APPROVAL_REVIEWER_IDS` 配置,满足最小多人场景,不引入数据库或 Telegram 特定 ACL。
- 未授权审批会记录 `approval_denied` 审计事件,方便后续排查和审计。

## 后果

### 正面后果
- 任意 Telegram 用户知道 task id 也不能审批别人的危险任务。
- 审批策略成为可替换的 `ApprovalPolicy`,后续可演进到更强 ACL。
- 真实群聊 smoke test 可以覆盖权限拒绝路径。

### 负面后果
- 当前配置仍依赖 Telegram sender id,人类需要先知道自己的 ID。
- 还不支持“群管理员自动可审批”等 IM 原生权限。

### 我们接受这些代价是因为
- Phase 4 当前目标是最小审批闭环,不是完整企业 IAM。
- 核心先保住默认安全边界,复杂权限可以在更多真实 dogfooding 后再设计。

## 不再做的事

- 不再允许默认任意用户审批危险任务。
- 暂不把 Telegram 管理员权限直接耦合进核心审批逻辑。

## 相关链接

- ROUNDS Round 16
- 相关代码:`src/aico/core/approval.py`, `src/aico/core/task_bus.py`
