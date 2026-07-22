# ADR-0044: Durable Out-of-Band Runtime Alerts

**状态**:Superseded by ADR-0077
**日期**:2026-07-21
**决策者**:Codex
**相关 Round**:Round 206

**修订关系**:本 ADR 延续 ADR-0043 的 owned-task recovery boundary，并复用 ADR-0041 的 transactional
outbox 原则；它不改变 Task audit outbox 的模型或 truth boundary。

## 背景

Round 205 能自动恢复 Telegram polling / morning scheduler，并在连续失败后把熔断写入 heartbeat/doctor。
但老板完全缺席且 primary Channel 本身失效时，不会有人查看本机 doctor。machine-visible failure 仍不是
human-absent incident loop。

## 候选方案

### A. 继续通过 primary IM Channel 发送告警

拒绝。polling task 或 Channel path 正是潜在故障点，同路径通知没有独立失效域。

### B. 每个 heartbeat open 都直接 POST webhook

拒绝。会产生告警风暴；HTTP accepted 后进程 crash 也无法判断是否重发，resolved 还可能越过 open。

### C. 独立 runtime incident + SQLite outbox + secondary sink

采用。single owner 把 owned-task transition 原子写成 incident/outbox；sink 按稳定 event id 至少一次投递，
receiver 通过 `Idempotency-Key` 去重。

### D. 复用 Task recovery audit outbox

拒绝。Task audit 的 payload、查询真相、ack API 和生命周期都属于业务 Task；混用会让 runtime incident
污染 `/audit`、metrics 和 recovery contract。

## 决策

- app runtime 新增 `RuntimeAlertSink` 插件协议和 generic HTTPS webhook 实现；外部依赖只通过该接口进入协调器。
- 只有 `RuntimeSelfHealingSnapshot.components` 的 `open → healthy` 状态机可产生 open/resolved；generic
  Channel/Adapter health 不参与。
- active incident 和 immutable outbox event 使用同一 SQLite transaction；重复 open/healthy idempotent。
- recovering 保持 incident open，避免 cooldown 后一次 restart 就过早发送 resolved。
- outbox 按 row order 发送，首个未到期 head 或失败即停止；失败按持久化 1/5/15 分钟封顶退避，成功返回后才 ack。远端 exactly-once 不承诺。
- webhook event 只含 schema、event/incident type/id、component、attempts、occurred_at；URL/token 仅在进程内。
- alerting 未配置为 WARN，pending 为 WARN，内部 store/probe failure 为 FAIL；状态进入 heartbeat v4。
- webhook 启用必须同时配置 durable state DB 与 heartbeat loop；没有 owner 授权不创建或发送真实 webhook。

## 后果

### 正面

- primary IM 故障时仍有独立、可重试的通知路径。
- open/resolved 成对、有 incident identity，重复 heartbeat 不制造噪声。
- sink failure、进程 restart 和 accept-before-ack 都保留稳定事件证据。

### 代价

- webhook delivery 是 at-least-once；receiver 必须实现 event-id 幂等。
- 当前只提供 vendor-neutral webhook，真实 SMS/email/Teams/PagerDuty 需要各自插件与 owner 配置。
- 若整机断电或网络长期不可达，SQLite 只能保留 pending，无法凭空送达。

## 不再做的事

- 不把 generic health failure 变成自动告警。
- 不复用 primary Channel、自发猜测 endpoint 或把 secret 写进 LaunchAgent/heartbeat/outbox。
- 不把 runtime alert 混入 Task audit 或老板业务视图。
- 不宣称远端 exactly-once，也不因告警失败自动重启 runtime。
