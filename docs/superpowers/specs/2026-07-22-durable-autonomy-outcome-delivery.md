# Durable Scheduled Autonomy Outcome Delivery — Goal Brief

**Round**:238
**Status**:Implemented
**Goal**:让boss-absent runtime主动、持久地交付scheduled autonomy终态，而不是只保证provider不会盲目重跑。

## Problem

scheduled morning、autonomy intent和accepted dispatch已经durable，但最终结果仍是一发即逝的IM调用。结果发送失败、ACK前崩溃
或accepted后缺少task evidence时，机器可能已结算dispatch，老板却只能在下一次主动查询时发现异常。

## Contract

- 只为`DISPATCH_RECORDED`创建outcome；内容从proposal/task/result authoritative truth投影，不保存provider正文或target。
- envelope绑定run receipt SHA、source/outcome status、criteria/source/evidence/failure摘要和content SHA。
- 发送前持久化稳定notification id与exact content；失败最多五次，重启复用同一记录并暴露duplicate possibility。
- ACK必须来自配置中的exact trusted target；只保存raw message id SHA。open为DEGRADED，exhausted为FAILED。
- settled-without-outbox在下一次scheduler工作前补建；outcome重试不能调用provider、创建第二task或再次消费grant。
- 非关键started提示失败不得阻断TaskBus submit；异常正文不进入日志、state或operator summary。
- RUNNING/WAITING不能冻结为terminal envelope；TaskBus dispatch后的IM异常必须interrupt本地RUNNING task或保持health DEGRADED。
- 不声明exactly-once、human read、provider执行成功或真实owner-bound scheduled样本。

## Acceptance Evidence

- recorded autonomy先创建outbox再发送；receipt包含content SHA与ACK SHA，不含raw message id/target/provider output。
- 第一次发送失败、重启后只重发exact envelope，morning与provider都不重跑；五次耗尽进入health FAILED。
- wrong-target ACK不能写DELIVERED；SENDING重启变为immediate RETRYING并标记duplicate possible。
- intent已SETTLED但outbox缺失时可自动补建；accepted-without-task投影为`evidence_missing`而不是绿色完成。
- started notification失败时，enforced read-only provider仍执行并产生可交付的terminal outcome。
- TaskBus已dispatch后task-ACK/stream transport失败时，RUNNING task被interrupt；缺usage/result时投影为`evidence_missing`，
  不留下绿色zombie。
- state schema v12、backup/reset和`aico-state`覆盖outbox，CLI不显示正文、target、raw message id或raw proposal/task identity。

## Stop Conditions

- 不自动重跑accepted provider dispatch，不修改hard-read-only standing boundary，不扩权到写操作或自由规划。
- 不创建真实`.env`、grant、LaunchAgent，不调用真实paid provider或外发IM。
- 平台ACK、provider dispatch、terminal outcome delivery与human read继续是不同事实；B-010/B-014不因本机gate关闭。
