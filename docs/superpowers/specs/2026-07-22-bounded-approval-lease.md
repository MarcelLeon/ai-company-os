# Goal Brief: Bounded Approval Lease

## Goal

让风险任务的人工审批成为有界、跨重启、不可追溯延长的能力票据，避免老板缺席后旧上下文被突然执行。

## In scope

- 新approval冻结`expires_at`，默认24小时、可配置5分钟到7天。
- startup、老板视图和approval action前lazy sweep。
- SQLite approval/task/audit intent事务一致与sink retry。
- expired老板文案、doctor preflight与旧记录兼容。

## Out of scope

- 自动批准、自动重提、approval reminder轰炸。
- 多人/quorum审批、密码学owner identity、外部credential撤销。
- NTP/系统时钟治理和已经dispatch任务的deadline。

## Acceptance

1. 新approval持久化immutable aware deadline，后续放大配置不能延长它。
2. `now >= expires_at`后任何查询或`/approve`都不dispatch，并投影expired/rejected。
3. restart后语义一致；audit sink失败可重投且不产生重复event。
4. outbox写失败时approval、task和audit intent全部rollback。
5. `/inbox`不再给expired task展示`/approve`，而是给出恢复/重新提交路径。
6. doctor拒绝300..604800秒之外或非整数配置，不泄漏原值。

## Stop conditions

- 不把expiry实现为自动reject后自动重跑。
- 不让配置变更追溯延长已有approval。
- 不以非事务双写换取实现简单。
