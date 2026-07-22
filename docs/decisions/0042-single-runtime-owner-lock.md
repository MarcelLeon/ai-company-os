# ADR-0042: OS Advisory Lock for Single Runtime Ownership

**状态**:Accepted
**日期**:2026-07-21
**决策者**:Codex
**相关 Round**:Round 204

## 背景

ADR-0040/0041 的 restart reconciliation 只有在“一份 SQLite state 只有一个 active runtime”时正确。当前代码
只是文档声明该假设,没有强制。若手动 `aico-phase1` 与 LaunchAgent、两个 terminal 或重复 Feishu server 同时启动,
后启动者会把前者仍在执行的 `RUNNING` 误判为 orphan,并可能重复消费/发送 IM。

互斥必须发生在 TaskBus recovery 之前。仅在 `runtime.start()` 后检查 PID、仅由 `aico-service install` 检查,或只锁
SQLite transaction 都太晚。

## 候选方案

### A. 普通 PID 文件 + 启动时检测进程

拒绝。crash 会留下 stale file,PID 会复用,且“文件存在”不是活跃 ownership 证据。

### B. SQLite heartbeat lease

暂不采用。它适合未来多进程/多主机,但需要 TTL、时钟、续租、fencing token 和失联策略;Phase 1 本地单机过重。

### C. OS advisory file lock,handle 持有整个生命周期

采用。`flock(LOCK_EX | LOCK_NB)` 是本机 kernel ownership;进程退出时自动释放,文件可保留只读诊断 metadata。

## 决策

- 新增 app-layer `RuntimeOwnerLock`;它不进入 Adapter/Channel/core plugin 协议。
- 配置 state DB 时,lock path 由 canonical DB path 派生为 `<db>.owner.lock`;未配置 state 时使用
  `<cwd>/.aico/runtime-owner.lock`。同 DB 即同 lock,不同 DB 可独立运行。
- lock metadata 只含 schema/state/PID/time/resource,不含 token、命令、项目 payload 或环境值。
- `TaskBus.__init__` 不再自动 reconciliation;新增显式 `recover_startup_state()`,由 `Phase1Runtime.start()` 在 acquire
  成功后调用。
- runtime start 顺序固定为 owner acquire → task recovery → orchestrator bind → scheduler → Channel → heartbeat;
  stop 反向清理并最终 release owner。
- competing acquire fail closed,不等待、不自动 kill owner,不触碰 task state。
- `aico-service doctor` 用 kernel lock 状态判断 owner active/free;metadata 只用于 PID/detail,不能替代 lock 事实。
- 当前只支持 Unix/macOS advisory lock;这与 Phase 1 macOS LaunchAgent 部署一致。第二个平台出现前不抽象分布式 lease。

## 后果

### 正面

- live task 不会被重复 runtime 误中断。
- Telegram long polling、Feishu webhook 和 morning scheduler 不会对同 state 重复启动。
- crash 后 kernel 自动释放,无需猜 stale PID。
- owner 状态进入 operator doctor,部署假设变成机器契约。

### 代价

- 网络文件系统的 advisory-lock 语义不在支持范围;state DB 本来也只支持本地 SQLite。
- 直接构造持久化 TaskBus 的测试/工具必须显式调用 recovery;正式 runtime 由 lifecycle 统一负责。
- 手动 runtime 占锁时 LaunchAgent 会 fail closed 并按 launchd 策略重试,operator 需要先停止原 owner。

## 不再做的事

- 不把 lock-file existence 当 active owner。
- 不在发现竞争 owner 时自动发送 signal/kill。
- 不允许 startup reconciliation 早于 owner acquisition。
- 不把本方案宣传为多主机 lease 或 leader election。
