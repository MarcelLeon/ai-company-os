# ADR-0058: Bounded Approval Lease and Transactional Expiry

**状态**:Accepted
**日期**:2026-07-22
**决策者**:Codex / Round 220

## 背景

AICO会把写文件、shell和destructive任务停在`waiting_approval`，并跨SQLite restart恢复。但审批此前永久有效：老板
离开数天后，一条上下文、代码或外部条件已经变化的旧`/approve`仍会直接dispatch。安全等待因此变成了无期限能力票据。

审批过期还涉及三份事实：approval、task snapshot和audit。逐份写入会在crash时留下“approval已过期但task仍等待”或
“task已拒绝但approval仍可执行”的分裂状态。

## 决策

1. 每个新approval request在创建时冻结aware `expires_at`；默认24小时，可由owner在300..604800秒内配置。修改配置
   只影响新审批，不追溯延长已有lease。
2. 到期边界为`now >= expires_at`。旧SQLite记录没有`expires_at`时，按当前bounded policy从`created_at`保守推导；
   naive legacy timestamp直接视为过期。
3. startup reconciliation、`task_snapshot(s)`、pending approval查询、`/approve`和`/reject`前都执行lazy sweep。
   不需要常驻timer：任何可能展示或消费approval的入口都会先过期检查。
4. 过期后approval写为`expired`，task写为`rejected`并使用稳定恢复文案；不dispatch、不自动重提、不自动批准。
5. SQLite在一个`BEGIN IMMEDIATE`事务内更新approval、task snapshot并写`approval_expired`审计intent；复用现有
   reconciliation outbox和稳定event id投递。audit sink失败时保留pending并在下次startup/access重投。
6. `aico-service doctor`在install前验证lease范围；无效值只显示bounded错误，不回显原始环境变量值。

## 否决方案

- **审批永久有效**：最简单，但旧上下文能在老板缺席后突然获得写权限。
- **只在`/approve`时拒绝，不改状态**：安全但inbox会永久展示一个实际不可执行的待审批项。
- **只在内存设置timer**：restart后丢失，Mac sleep/事件循环停顿还会造成不同语义。
- **重启时用当前配置重算所有deadline**：配置放大会追溯延长旧票据；deadline必须在创建时冻结。
- **过期后自动重提任务**：新任务可能仍有副作用或成本，不能替代owner重新确认上下文。
- **分别更新approval/task/audit**：无法满足crash consistency；必须复用transactional outbox。

## 后果

### 正面

- 风险审批从无限期口头同意变成可审计、跨重启、不可追溯延长的短期能力票据。
- 老板早报和inbox不会继续建议批准已过期任务，而会要求查看旧task并提交新的明确意图。
- audit sink故障不会吞掉过期事实，也不会让旧approval重新变为可执行。

### 代价与剩余风险

- 合法但长时间未处理的审批会失效，owner必须重新提交任务；这是刻意的fail-closed成本。
- persisted lease使用wall-clock，因为monotonic time不能跨restart；系统时钟回拨可能延迟expiry，商用主机仍需可靠校时。
- 该lease只约束AICO approval，不撤销外部平台已经授予的credential，也不是多人审批或密码学owner signature。

## 验证

- 单测覆盖精确到期边界、frozen deadline、旧记录迁移语义、老板视图、SQLite restart和无重复audit。
- transaction trigger证明outbox insert失败时approval与task snapshot一起rollback。
- sink失败后state保持expired/rejected、outbox保持pending，恢复后按同event id只投递一次。
