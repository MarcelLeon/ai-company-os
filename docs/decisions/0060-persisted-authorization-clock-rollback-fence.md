# ADR-0060: Persisted Authorization Clock Rollback Fence

**状态**:Accepted
**日期**:2026-07-22
**决策者**:Codex / Round 222

## 背景

ADR-0058把risk approval变成冻结deadline的bounded lease，ADR-0051给standing autonomy grant加入expiry。但两者都以
本机wall clock为准。若时间回拨，只比较`now >= expires_at`会延长授权窗口；仅比较approval `created_at`又无法发现
创建后、下一次观察前的时间倒退，也不能保护standing grant。

## 决策

1. 新增共享`AuthorizationClockGuard`与`AuthorizationClockStore`接口；production store在主SQLite中只保存一行
   authorization high-water，state schema升级为5。
2. 每次startup/lazy approval sweep、创建risk approval、preauthorized preflight和scheduled grant检查都先观察时钟。
   同进程用monotonic elapsed推导最低应到wall time，跨重启用SQLite high-water。
3. 允许5秒backward correction。超过后不降低high-water；pending approval事务性expired/rejected并写既有outbox，
   新risk approval与所有preauthorized execution返回稳定refusal，standing path只发hold。
4. wall time追平持续推进的high-water后可接受新的authorization；旧approval不可复活，必须提交新任务。
5. `aico-state reset/restore`仍是owner-fenced显式运维动作，允许重建/恢复该行；普通runtime不能提供绕过开关。

## 取舍

- 选择local monotonic + durable high-water，而非联网NTP：absence路径不增加网络依赖，且能跨进程crash保持保守边界。
- 5秒容差减少正常校时误报，但意味着小于等于5秒的回拨不会熔断。
- 未观察到的跨关机真实时间无法由本机单独证明；该机制是rollback fence，不是外部可信时间、硬件证明或主机入侵防护。

## 后果

- SQLite backup/verify必须使用schema 5并包含`authorization_clock_state`。
- 一次明显回拨会主动废止pending approval，换取不延长旧风险上下文。
- standing grant不会因时钟回拨重新获得执行机会；老板收到稳定hold原因后先修复系统时间，再提交/授权新工作。
