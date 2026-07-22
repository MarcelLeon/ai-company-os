# Goal Brief: Durable Scheduled Morning Delivery

## Objective

让boss-absent runtime能区分“scheduler task活着”“IM平台已确认晨报”和“standing autonomy结果成立”，并在发送失败、
进程崩溃与重启后有界收敛。

## Acceptance

- 发送前持久化稳定daily identity与exact content；同日重启不重新渲染或重复创建。
- 失败有界退避，发送中崩溃显式标记duplicate possibility，耗尽使runtime health失败。
- 平台ACK保留secret-free receipt，自治失败不重发已确认晨报。
- operator可查看delivery/status/attempt/content与standing receipt fingerprint计数，不暴露target、正文或raw message id。
- SQLite backup/reset/schema、Phase1 config、runtime health与单元/E2E回归同步更新。

## Stop conditions

- 不声称exactly-once、人类已读、平台持久展示或standing result业务正确。
- 不新增外部队列、Web UI或平台特定核心分支。
- 没有真实owner配置时不安装runtime、不发送IM、不消费provider。
