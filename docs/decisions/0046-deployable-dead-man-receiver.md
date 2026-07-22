# ADR-0046: Deployable Persistent Dead-Man Receiver

**状态**:Superseded by ADR-0078
**日期**:2026-07-21
**决策者**:Codex
**相关 Round**:Round 208

**修订关系**:本 ADR 实现 ADR-0045 留下的 independent receiver boundary；pulse wire protocol不变，但修正
ADR-0045“复用 incident alert URL/token”的配置决定。receiver 使用自己的进程、SQLite 和 notification outbox。

## 背景

Round 207 已冻结 pulse/TTL/boot/stop contract，但 `RuntimeLivenessTracker` 只在内存中。receiver 重启会忘记
armed monitor，且没有 HTTP auth、周期 expiry worker、durable open/resolved notification 或部署形态。它只能证明
算法，不能承担老板缺席时的商用监控责任。

## 候选方案

### A. 把 receiver 放回 AICO Mac/进程

拒绝。event loop、launch path 或整机故障会同时杀死被监控者和 observer，违反独立失效域前提。

### B. 使用无状态 serverless handler，每次 pulse 只刷新外部 TTL

暂不采用。当前没有 owner 选择的云厂商/managed TTL primitive；无状态 handler 也无法自行证明 open/resolved
顺序、restart persistence 和 notification retry。

### C. 独立 FastAPI + dedicated SQLite + durable notification outbox

采用。现有 Python/FastAPI 栈无需新增依赖；单实例 SQLite 足以形成可部署 reference receiver，并能用 transaction
证明 monitor/outage/event 一致性。真实多副本扩展需后续迁移到带 fencing 的外部数据库，当前不虚构支持。

### D. 直接绑定某个 PagerDuty/Teams/短信供应商

拒绝。owner 尚未选择供应商；receiver 输出保持 vendor-neutral HTTPS sink，外部系统按 event id 幂等。

## 决策

- 新增独立 receiver entrypoint、settings、FastAPI app 和 non-root container，不与 AICO orchestration lifespan 合并。
- pulse/admin 使用不同 required bearer token；pulse 只能刷新已 armed monitor，admin 才能 arm/disarm/read status。
- AICO 使用专用 liveness webhook URL/token；incident alert 与 pulse 是两个 strict schema，不能共用一个 endpoint。
- dedicated SQLite transaction 同时维护 monitor、active outage 和 immutable notification outbox。
- receiver time 决定 expiry；sender `sent_at` 只拒绝旧 boot。late recovery 必须先补 open再 resolved，不能被 sweep
  timing 抹去。
- notification 是 at-least-once：稳定 event id、success-before-ack、row-order、1/5/15 分钟持久退避。
- background worker startup 立即 sweep/deliver，之后定时运行并响应 state-change wake-up。
- same-TTL arm idempotent且不重置窗口；TTL change必须 disarm→arm。disarm不生成虚假 resolved，也不删除既有 outbox。
- receiver 当前明确为 single-instance SQLite deployment；多副本、managed DB和真实云部署另行决策。

## 后果

### 正面

- receiver 自身重启后仍记得监控责任、active outage和待投递通知。
- process/Mac outage不再依赖故障 sender回调，scheduler晚一步也不会丢 outage edge。
- admin/pulse权限分离，永久停用与普通 runtime traffic不能相互冒充。

### 代价

- owner 仍需选择独立主机、TLS入口、持久卷、secret manager和最终通知 endpoint。
- SQLite reference receiver只支持单实例；不能水平扩容或宣称跨区高可用。
- downstream exactly-once仍需 event-id dedupe，receiver只能保证 immutable at-least-once intent。

## 不再做的事

- 不把 receiver 部署在同一 Mac或嵌入 AICO runtime。
- 不让 pulse自动 arm/disarm/change TTL。
- 不把 outage通知写入 AICO Task audit/runtime incident表。
- 不猜测真实云、供应商或凭据，也不宣称尚未完成的真实 outage sample。
