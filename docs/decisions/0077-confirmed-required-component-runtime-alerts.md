# ADR-0077: Confirmed Required-Component Runtime Alerts

**状态**:Accepted
**日期**:2026-07-22
**决策者**:Codex
**相关 Round**:Round 239
**Supersedes**:ADR-0044 中“generic Channel/Adapter health不参与incident”的边界；其durable outbox、secondary sink与
at-least-once交付决策继续有效。

## 背景

ADR-0044只把owned background task的recovery circuit转换成外部incident。Round 238之后，morning outcome delivery、
recovery backup/custody/drill等组件即使已经永久失败，也可能保持task和process存活。heartbeat会持续刷新，dead-man receiver
也持续收到pulse；若老板缺席且没人主动运行doctor，这类商业主路径失败会静默存在。

## 候选方案

### A. 所有非OK health立即告警

拒绝。optional adapter和瞬时dependency波动会制造告警疲劳，DEGRADED也不等于主路径不可用。

### B. FAILED直接触发自动重启

拒绝。P-061已证明generic health不是安全repair signal；重启可能重放外部副作用，也不能修复exhausted outbox或损坏artifact。

### C. required FAILED的durable确认边沿进入既有incident/outbox

采用。只有required组件连续三份、时间递增的FAILED snapshot才open；OK才resolved。optional、DEGRADED和单次失败不open，
owned-task circuit与同名health故障去重。

## 决策

- `RuntimeAlertCoordinator`同时观察self-healing与component health，health检查先于alert delivery。
- required组件的连续失败计数写入`runtime_health_alert_observations`；第三次确认、active incident和outbox event在同一SQLite
  transaction提交。相同或倒退时间的snapshot不增加计数，重启继续原计数。
- outbound component使用`health:<kind>:<safe-name>`；不安全名称只发送稳定hash，不发送原值。event仍不含异常、URL、token、
  target或业务正文。
- FAILED后的DEGRADED保持incident open；只有OK或组件被显式改为optional才resolved。
- 与OPEN/RECOVERING owned-task同名的scheduler health不再创建第二incident；该变化只通知，不授权restart、provider replay、
  restore、grant消费或业务副作用。
- state schema升级v13，backup/reset与`aico-state`覆盖confirmation table；CLI只显示candidate数量。

## 后果

进程存活但required业务组件失败时，老板可通过独立secondary sink收到有界去重的open/resolved，不再依赖手工doctor。
告警仍是at-least-once且需要owner配置真实receiver；三次确认带来最多约三个heartbeat周期的检测延迟。整机失联继续由独立
dead-man receiver判断，本地机器Gate不证明真实远端收件或老板已读。

## 相关链接

- ROUNDS Round 239
- PITFALLS P-095
- B-011
- `src/aico/app/runtime_alerts.py`
- `src/aico/app/runtime_heartbeat.py`
