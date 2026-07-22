# Goal Brief: Reviewed Configuration Revision Recovery

## Goal

保证AICO业务数据恢复后，只能在owner/CI独立选定的同一Git commit、clean worktree及相同active Project/Persona配置上继续运行，
同时不把源码、配置正文或secret复制进core recovery set。

## Acceptance

- capture要求完整expected revision；当前HEAD、tree、tracked/untracked状态或active config blob不匹配即拒绝且不发布artifact。
- manifest只保存relative path、commit/tree/blob OID、size/hash和persona来源，不保存绝对路径或配置正文。
- offline verify继续只验证artifact；`verify-checkout`额外验证目标worktree和配置，dirty/wrong revision/config drift均fail closed。
- recovery-set schema v3区分`included`与`recovery_contract_ready`，config合同完成不会被误写成配置文件已打包。
- output必须在reviewed checkout之外；外部SHA、off-device clone和隔离业务恢复仍是独立验收。

## Non-goals

- 不证明GitHub/GitLab review、commit签名或remote availability。
- 不嵌入`.env`、standing grant、receiver DB或源码包。
- 不自动checkout、reset、pull或执行combined restore。
