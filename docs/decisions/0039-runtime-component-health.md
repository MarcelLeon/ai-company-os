# ADR-0039: Runtime Component Health in the Local Heartbeat

**状态**:Accepted
**日期**:2026-07-21
**决策者**:Codex
**相关 Round**:Round 201

**修订关系**:本 ADR 对 ADR-0038 的 heartbeat semantics 和 Channel-specific service entrypoint 作增量修订;
ADR-0038 的 macOS user LaunchAgent、secret boundary 和 operator-explicit mutation 决策继续有效。

## 背景

Round 200 让 `aico-phase1` 可由 launchd 托管,并写进程 heartbeat。但进程存活不等于公司可用:
Telegram polling task 可能意外退出,Channel API 可能不可达,默认 Adapter 可能离线,定时早报 task 也可能死亡。
现有 doctor 只看 heartbeat 时间,会把这些状态报告成 fresh。

## 候选方案

### A. 继续只看 PID / heartbeat 时间

拒绝。它只能证明 event loop 仍有一个 heartbeat task,不能回答 AICO 是否还能接令、执行和早报。

### B. 任一健康检查失败就退出进程,交给 launchd 重启

拒绝。网络、Telegram 或 provider 外部故障不会因重启必然恢复,反而可能形成 crash loop、放大限流并抹掉诊断窗口。

### C. 在现有 heartbeat 中加入分级 component snapshot

采用。复用现有 `IMChannel.health_check()`、`AIAdapter.health_check()` 和 scheduler 自有 task 状态,
把 required failure、optional degradation 与 process freshness 分开表达。launchd 继续负责进程崩溃,
doctor 负责组合诊断;本轮不自动重启外部依赖故障。

## 决策

- heartbeat schema 升为 v2,保留原 process fields,新增 aggregate health 和 component status。
- active Channel、default Adapter、enabled morning scheduler 是 required;其它 Adapter 是 optional。
- 检查并发且有 timeout;异常只转成 FAILED,不保存 exception text。
- Telegram health 在 active polling task 已结束时直接 FAILED,不再只调用 `getMe`。
- local service 按 `AICO_CHANNEL` 选择真实入站 entrypoint:Telegram 使用 polling CLI,Feishu 使用 webhook server;
  两者复用同一个 runtime+heartbeat lifespan。
- legacy heartbeat 可读,但 component health 缺失只报告 WARN,不报告 fully healthy。
- 不扩展 Channel/Adapter protocol;健康编排留在 app runtime 层,插件仍只实现既有 `health_check()`。

## 后果

### 正面

- operator 能区分 process stale、required path failed、optional Adapter degraded 和 legacy unknown。
- 不需要新 daemon、云监控或 secret 扩散。
- 后续可在相同 snapshot 上接本地通知或第二 Channel,无需改组件健康语义。

### 代价

- health check 是 synthetic probe,不能证明真实任务或 IM 回包。
- Channel/Adapter API 检查会产生低频网络调用。
- 当前没有 out-of-band 告警;老板完全不查看时,故障仍需后续通知能力才能主动送达。

## 不再做的事

- 不把 fresh heartbeat 当成公司 fully healthy。
- 不在 heartbeat 里写 exception、URL、命令或 secret。
- 不因外部依赖瞬时失败自动 crash/restart。
- 不把 optional Adapter 离线升级成 primary path outage。
- 不假设所有 Channel plugin 都由同一个进程 entrypoint 接收入站。
