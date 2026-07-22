# Authorization Clock Rollback Fence — Goal Brief

**Round**:222
**Status**:Implemented
**Goal**:系统时间回拨时，不让旧审批或standing grant获得额外可执行窗口。

## Problem

Approval lease与standing grant都用wall clock判断expiry。Mac时间被手工修改、错误同步或VM snapshot回拨后，已信任的
时间可能倒退；仅检查`now < expires_at`会把风险授权延长，甚至让之前已观察为expired的grant重新看似有效。

## Contract

- 每次authorization-sensitive路径推进一个SQLite high-water timestamp；进程内再用monotonic elapsed推导最低应到时间。
- 允许最多5秒的小幅校时；超过后返回稳定refusal，pending approval全部事务性变为`expired/rejected`并写audit outbox。
- 新risk approval、direct preauthorized task和scheduled standing autonomy都拒绝执行，直到wall time追平高水位。
- clock fence跨重启保留；正常read-only任务不因该授权专用fence被阻断。
- 不依赖联网时间服务，不自动修改系统时间，不复活或自动重提旧任务。

## Acceptance Evidence

- 单进程monotonic elapsed能发现“wall只前进1秒、实际已过10秒”的回拨。
- SQLite重启后仍能发现低于已持久化high-water的wall time。
- rollback会使pending approval不可批准，新risk task被拒绝，scheduled grant只发hold且不dispatch。
- 5秒以内校时不误熔断；state backup/restore继续覆盖新schema/table。

## Stop Conditions

- 不把本地高水位称为外部可信时间、签名或防主机入侵能力。
- 不引入NTP/network依赖，不尝试无人值守修系统时钟，不绕过owner-fenced state reset/restore。
- 外部owner配置、LaunchAgent、paid provider和真实IM样本仍由B-010/B-014跟踪。
