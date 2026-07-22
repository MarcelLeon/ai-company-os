# ADR-0070: Durable At-least-once Scheduled Morning Delivery

**状态**:Accepted
**日期**:2026-07-22
**决策者**:Codex / Round 232

## 背景

原morning scheduler只检查后台task是否存活；IM发送异常被捕获后没有持久记录、重试或平台回执，heartbeat仍可为绿色。
进程也可能在平台已接受消息、AICO尚未记录结果时崩溃。对boss-absent系统，这会把“调度器活着”误写成“晨报已送达”。

## 候选方案

- 继续只写日志：否决；日志不是可重启投递状态，且无法驱动健康降级。
- 每次失败重新渲染并发送：否决；同一逻辑投递会随业务状态变化，无法证明重试的是同一内容。
- 声称exactly-once：否决；Telegram/Feishu发送接口没有AICO可控制的端到端幂等事务。
- 持久exact envelope、有界at-least-once与显式歧义：采用。

## 决策

1. 正式scheduled morning必须配置主SQLite；schema v6保存稳定daily delivery id、exact `MessageContent`、内容SHA、所含
   standing autonomy receipt SHA、状态、尝试次数和时间。
2. 重试只复用首次落盘的envelope。退避为1/5/15/15分钟，最多五次；发送中崩溃或任何未确认尝试都标记
   `duplicate_possible=true`，耗尽后scheduler health为FAILED。
3. delivery id写入消息正文，便于老板识别有界重复；同binding同一天包括`push_on_start`只创建一个逻辑投递。
4. 平台返回`SentMessage`后立即持久化DELIVERED，只保存message id SHA，不保存原始message id或target。随后独立触发standing
   autonomy；ACK target必须精确匹配configured target，自治失败不能把已确认晨报改回未送达。
5. `aico-state`只显示delivery id、status、attempts、duplicate flag、content SHA、receipt count和时间。平台ACK不等于人类已读，
   content/receipt SHA也不等于业务语义真实。

## 取舍与后果

- 极端accept-before-ack或崩溃窗口可能产生最多有界重复；系统如实暴露，不伪造exactly-once。
- 主SQLite会保存晨报正文，因为重试必须字节语义稳定；该DB继续按owner-only、backup/encryption规则保护。
- 当前只持久化晨报transport状态；standing autonomy仍由自身proposal/task/result/usage evidence表达，不合并成单一绿色结论。
