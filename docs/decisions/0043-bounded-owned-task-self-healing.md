# ADR-0043: Bounded In-Process Recovery for Owned Background Tasks

**状态**:Accepted
**日期**:2026-07-21
**决策者**:Codex
**相关 Round**:Round 205

**修订关系**:本 ADR 延续 ADR-0039“不因外部依赖失败重启进程”的边界，并在 ADR-0042 的
single-runtime ownership 内增加本地 owned task 恢复。

## 背景

component heartbeat 已能发现 Telegram polling 或 morning scheduler task 死亡，但进程和 heartbeat
task 仍存活时，launchd 不会采取动作。老板缺席期间，这会成为持续静默失联。另一方面，现有统一
`HealthStatus.FAILED` 同时表示本地 task 死亡与外部网络/provider 失败，不能直接作为重启依据。

## 候选方案

### A. 任一 required component 失败就退出进程

拒绝。外部依赖失败不会因进程重启必然恢复，反而会形成 crash-loop、放大限流并破坏诊断窗口。

### B. 完全依赖 operator 看 doctor 后手工恢复

拒绝。它只能满足有人值守，不符合 human-absent/boss-absent 北极星。

### C. 当前 owner 对自有后台 task 做有界进程内恢复

采用。恢复触发源与 generic health 分离，只纳入 lifecycle 由当前进程直接拥有的 Telegram polling
和 morning scheduler。恢复必须经过尝试上限、稳定期和熔断冷却；外部依赖失败只进入 health。

### D. 新增 sidecar supervisor

拒绝。现阶段没有独立部署或故障隔离收益，增加第二进程会与单 owner、heartbeat 和 launchd 形成
多套真相源。

## 决策

- 在 app runtime 层建立 owned-task supervisor，不扩展所有 Channel/Adapter 公共协议。
- Telegram 与 morning scheduler 显式提供 owned task liveness 和 async restart；shutdown 后不可重启。
- 首次发现死亡立即尝试恢复，单次 restart 最长 5 秒，task 存活 60 秒才视为稳定。
- 稳定前再次死亡累计尝试；三次后熔断 15 分钟，冷却后才开启下一轮。
- heartbeat 增加 secret-free self-healing snapshot；recovering 为 WARN，open 为 FAIL。
- synthetic Channel/Adapter health 不参与恢复决策，业务 Task 也绝不自动重试。

## 后果

### 正面

- process 仍活着时，本地后台 task 的单次异常可自动恢复。
- 永久代码错误不会形成 tight loop；诊断状态可由 heartbeat/doctor 保留。
- Telegram polling 与 Feishu webhook 的部署差异继续清晰，外部抖动不会触发修复。

### 代价

- 熔断打开期间对应能力保持不可用，当前仍缺少第二 Channel 主动告警。
- 恢复是 task-level，不修复进程级 event-loop 卡死；后者仍由 stale heartbeat + launchd/operator 处理。
- 固定阈值优先保证行为可预测，后续只有真实运行证据证明需要时才开放配置。

## 不再做的事

- 不用 generic `FAILED` 触发自动恢复。
- 不因外部 API/provider 不可达重启 task 或进程。
- 不在 heartbeat 保存 exception text 或配置值。
- 不自动重放因进程/Adapter 中断的业务 Task。
