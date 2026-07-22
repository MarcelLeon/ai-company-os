# Durable Scheduled Core Recovery Backup — Goal Brief

**Round**:234
**Status**:Implemented
**Goal**:在boss-absent运行期自动生成并立即深验core recovery set，以durable receipt和RPO health暴露失败，同时保持restore完全人工。

## Problem

已有恢复命令只证明operator触发时能工作，不能约束无人值守期间多久没有新恢复点。普通定时脚本缺少intent、重试、崩溃
对账和heartbeat，可能在artifact已发布但状态未写回时重复覆盖，也可能在外部mount缺失时把文件悄悄写到本机目录。

## Contract

- 默认关闭；启用需要state/audit/memory、clean reviewed checkout/config、完整revision和已存在的absolute owner-only外部目录。
- 每个窗口使用稳定backup id，先写SQLite intent，再生成唯一artifact；capture后立即deep verify并发布no-overwrite receipt。
- 启动时对RUNNING intent做有界恢复；artifact+receipt复验，artifact-only补receipt，receipt-only失败，两者皆无才capture。
- 1/5/15/15分钟最多五次；open/no receipt为DEGRADED，exhausted或verified age超过max age为FAILED。
- scheduler纳入Phase1 lifecycle、heartbeat和owned-task self-healing；`aico-state`只显示secret-free SHA证据。
- 永不自动restore、自动删除或创建缺失目标目录；不声明目录是off-device/encrypted，也不提升recovery-set readiness语义。

## Acceptance Evidence

- capture时可观察到RUNNING intent已持久化；成功后artifact、sidecar和SQLite receipt三者ID/SHA一致。
- artifact-only与artifact+sidecar crash矩阵不重复capture；sidecar-only、权限过宽、symlink和路径漂移fail closed。
- 五次失败进入EXHAUSTED，freshness超限使required runtime health FAILED；死亡scheduler可由owned-task supervisor重启。
- state schema v8首次加入新表，Round 235以v9追加custody evidence；backup/reset持续覆盖，CLI不泄露
  output/config/project/provider/raw path。
- service doctor在install前拒绝缺失、checkout内或非owner-only目标，并明确storage class未被attest。

## Stop Conditions

- 本轮不配置真实`.env`、不安装LaunchAgent、不发送IM、不调用provider，也不写任何真实备份目的地。
- 本地目录与mock receipt不能当作off-device encryption、retention、RPO/RTO或商业恢复证据。
- 不实现自动restore或retention deletion；二者需要独立授权、策略和事故演练。
