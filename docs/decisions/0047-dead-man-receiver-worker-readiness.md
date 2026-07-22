# ADR-0047: Dead-Man Receiver Worker Progress Readiness

**状态**:Accepted
**日期**:2026-07-21
**决策者**:Codex
**相关 Round**:Round 209

## 背景

ADR-0046 的 receiver 已持久化监控责任并由后台 worker 处理 expiry 和 notification delivery，但 public
`/readyz` 只执行 SQLite ping。若 worker 持续内部失败或不再调度，HTTP server 仍会返回 ready，容器 healthcheck
不会触发 restart；这会让负责发现 AICO 失联的 observer 自己静默失效。

## 候选方案

### A. `/readyz` 继续只检查数据库

拒绝。它只能证明 request path 和 SQLite 可访问，不能证明核心 expiry/delivery loop 正在推进。

### B. 任意 downstream notification failure 都返回 not-ready

拒绝。外部 endpoint 抖动已由 durable outbox/backoff 建模；让它杀死 receiver 会把受控降级变成 restart loop。

### C. 持久化 worker health 到 receiver SQLite

拒绝。worker progress 是 process-local evidence；跨 restart 保留会把旧进程健康误当成新进程健康，并污染
monitor/outage truth boundary。

### D. 进程内 monotonic progress probe + fail-closed readiness

采用。startup 先完成一次 coordinator pass；之后每次 pass success/failure 更新内存 probe。连续第三次内部失败，
或超过三个 sweep interval 没有成功 pass，`/readyz` 返回通用 503。成功 pass 立即恢复 readiness。

## 决策

- `/healthz` 只表达 HTTP process/event-loop liveness；`/readyz` 表达 SQLite + worker progress readiness。
- progress elapsed time 使用 monotonic clock，不受 wall-clock 校时影响。
- 允许两个连续内部错误，第三个 fail closed；无成功进展超过三个 sweep interval同样 fail closed。
- downstream notification rejection若已被 coordinator转成 durable pending/backoff，仍算一次成功 coordinator pass。
- public 503 body固定为 `not ready`，不暴露 failure type、exception text、路径、monitor、event 或 endpoint。
- worker-health 不持久化；每个新 process必须先完成 immediate startup pass才可 ready。
- Compose 继续用 `/readyz` healthcheck和 `restart: unless-stopped`，由外部 supervisor处理持续 not-ready。

## 后果

### 正面

- worker 静默停滞或连续内部失败不再伪装成可用 receiver。
- transient failure 与 downstream outage 不会立即制造 restart storm。
- process restart 后 readiness只能由新进程自己的执行证据建立。

### 代价

- readiness 是单进程瞬时证据，不能替代第二故障域、host supervisor或真实 outage sample。
- 极端 event-loop stall会表现为 healthcheck timeout而非结构化 503；这正是 supervisor 应处理的故障。

## 不再做的事

- 不把 HTTP 200或 DB ping单独称为 receiver ready。
- 不把 downstream pending/backoff混成 worker death。
- 不在 public health endpoint暴露内部运维细节。
- 不为单个 concrete loop引入 generic health framework。
