# Goal Brief: Quorum Dead-Man Notification Routes

## Goal

独立dead-man receiver形成outage后，即使一个owner notification endpoint失效，也能通过另一独立HTTPS origin通知缺席老板；两路都未满足owner ACK策略时继续durable重试同一事件。

## Non-goals

- 不证明两个URL位于不同云、账号、网络或物理故障域。
- 不把platform ACK解释为老板已读或业务恢复。
- 不因downstream失败restart receiver、重放provider任务或修改monitor状态。
- 不把URL、token、response body或异常正文写入SQLite/evidence/log。

## Contract

1. fallback为可选；未配置时维持单route行为。
2. 两route必须为不同HTTPS origin；notification token彼此不同且不复用pulse/admin token。
3. 同一event携带相同payload和`Idempotency-Key`并发发送到所有route。
4. 默认1-of-2 ACK即可结算；可显式配置2-of-2，值不得超过route数量。
5. quorum miss使用现有durable 1/5/15分钟退避重试exact event，并保持open-before-resolved队首顺序。
6. delivered/evidence只表示configured quorum，不扩张为all-route、human-read或failure-domain证明。
7. 当前route count/quorum持久化；event创建时冻结自己的策略。存在pending event时，启动不得改变策略，避免2-of-2事件被新1-of-2配置降级结算。
8. receiver/evidence/recovery schema统一v3；v1/v2历史保守迁移为1-of-1，recovery拒绝pending event与当前策略漂移。

## Machine acceptance

- primary失败、fallback ACK时1-of-2 event落delivered，两route均被尝试。
- 同样故障在2-of-2下保持pending；恢复后重投相同event identity并收敛。
- 两个真实webhook sink收到相同payload/idempotency key；failure detail与credential不进入event。
- settings拒绝无URL的fallback token、同origin、相同route token、复用receiver authority和超过route count的quorum。
- 单route设置仍构造原窄sink；schema v3 evidence能区分当前策略和历史event策略。
- 2-of-2 pending后以1-of-2配置重启必须fail closed；原策略清空pending后才允许显式切换，历史evidence仍保留2-of-2。

## External acceptance boundary

owner仍需选择两个真实独立provider/账号并采集primary断路、fallback ACK、双路断路/recovery样本。different-origin和本地unit test不能证明真实故障域、手机展示、老板已读或商业HA。
