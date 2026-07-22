# Goal Brief: Secret-free Runtime Reinjection Receipts

## Goal

让灾后恢复的AICO在启动前，用不可泄密、可重复验证的机器证据确认控制面secret已经重新注入、standing grant已由owner明确
重新授权并与当前runtime binding一致，同时不把本地presence检查冒充AI provider远端认证。

## Acceptance

- capture要求owner-only、non-symlink、Git未跟踪的`.env`，拒绝缺失/占位/重复key、channel secret槽位错误及不安全grant；manifest不含值或hash。
- schema v4固定保存channel、secret slot集合、grant enabled mode及`post_restore_receipt_required=true`。
- `reinjection-receipt`先深验set与exact clean checkout，再复用production service/grant preflight；必须有安全owner decision reference。
- receipt使用atomic owner-only new-path发布并输出独立SHA；值、hash、owner/target、grant正文/ID和绝对路径均不可出现。
- `verify-reinjection`重新验证receipt SHA、set SHA、revision、当前slot/mode及grant binding；secret轮换允许，slot drift拒绝。
- coverage明确拆分control-plane secret与AI provider认证，任何输出都保持`business_restore_ready=false`。

## Non-goals

- 不备份或恢复secret manager本身，不记录secret/grant正文或普通hash。
- 不证明Telegram/Feishu/Claude/Codex远端credential真实可用、额度充足或owner decision具备数字签名。
- 不自动启动runtime、安装LaunchAgent、执行provider任务或恢复dead-man receiver DB。
