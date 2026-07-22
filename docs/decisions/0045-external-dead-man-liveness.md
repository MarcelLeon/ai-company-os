# ADR-0045: External Dead-Man Runtime Liveness

**状态**:Superseded by ADR-0078
**日期**:2026-07-21
**决策者**:Codex
**相关 Round**:Round 207

**修订关系**:本 ADR 补齐 ADR-0044 无法覆盖“告警发送者本身已死”的边界；不改变 durable runtime
incident outbox，也不把 AICO 本机变成自己的外部监控器。

## 背景

Round 206 可以在 Python event loop 仍运行时可靠发送 owned-task open/resolved。但 event loop 卡死、
LaunchAgent 持续启动失败、Mac 断电或离线时，sender 无法创建告警。老板完全缺席时，只有独立失效域能根据
周期信号缺失推断 outage。

## 候选方案

### A. 继续依赖本机 heartbeat / launchd

拒绝。二者都在同一台 Mac；它们能重启或留下事后证据，不能在整机失联时主动通知远端。

### B. 正常 stop 时发送 stopped/disarm

拒绝。sender 无法可靠区分滚动重启、临时维护与永久卸载；自动 disarm 会把 stop 后未成功重启伪装成健康。

### C. 每个 pulse 写 durable outbox

拒绝。liveness 是可覆盖的周期状态，不是必须永久保存的业务事实；无限历史会放大存储和重放噪声。

### D. 低频 ephemeral pulse + 独立 receiver TTL

采用。AICO 只发送带 stable runtime identity、per-process boot identity 和 sequence 的脉冲；receiver 按接收
时间独立过期并生成 open/resolved，永久停用由 owner 在 receiver 显式 disarm。

## 决策

- 引入独立 `RuntimeLivenessSink` 协议。当前是第二个 HTTPS webhook 用例，按 Rule of Three 保持两份窄实现，
  不提前抽象通用 webhook framework。
- pulse 不落 SQLite，只在进程内保留一个 pending pulse；失败重投同一个 idempotency key，成功后才推进 sequence。
- publisher startup 立即发送新 boot 的 sequence 1；之后按固定 interval 发送，TTL 至少为 interval 三倍。
- receiver 以 acceptance time + TTL 判 stale，不能依赖 sender clock；sender timestamp 只用于保守拒绝明显更旧的
  replacement boot。
- Mac sleep / 网络分区超过 TTL 均视为 unavailable。正常 stop 不发送 disarm；永久卸载必须先在 receiver 显式 disarm。
- heartbeat v5 仅暴露 publisher delivery 状态。它是本机诊断，不是远端 liveness 的 truth source。
- 复用 owner 配置的 runtime HTTPS URL/token，但 payload/协议和 incident alert 分离；没有 owner 配置不外发。

## 后果

### 正面

- 整个 Python runtime 或 Mac 消失时，远端仍可独立形成 outage evidence。
- restart 通过新 boot id 立即恢复；失败重试不会制造 pulse identity 风暴。
- 本地没有无限 pulse 表，也不会污染 runtime incident、Task audit 或业务视图。

### 代价

- 真正可用性仍取决于 owner 部署独立 receiver 并配置其通知出口；本仓库只能冻结和验证协议。
- 笔记本休眠会在 TTL 后告警，这是 availability-first 的保守选择。
- replacement boot 排序使用 sender timestamp；若本机时钟严重回拨，receiver 会保守保持旧状态直到其过期。

## 不再做的事

- 不用本机 doctor/heartbeat 冒充外部 dead-man monitor。
- 不自动 disarm，不把 clean shutdown 当成“计划停机已证明”。
- 不持久化 pulse 历史，不让 liveness retry 进入 incident outbox。
- 不猜测或自动创建真实 receiver、credential、告警供应商。
