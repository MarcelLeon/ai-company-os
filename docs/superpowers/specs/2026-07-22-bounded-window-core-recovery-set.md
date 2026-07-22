# Bounded-Window Core Recovery Set — Goal Brief

**Round**:226
**Status**:Implemented
**Goal**:把同一操作窗口内生成的state/audit恢复点绑定成可离线验证和组合演练的core set，并机器暴露全部未覆盖资产。

## Problem

两个component artifact分别verify通过，仍可能来自不同时间或遗漏其它业务资产。目录、文件名和人工清单不能绑定字节；
“打一个全量包”又会掩盖memory没有一致snapshot、secret不能复制和receiver处于独立故障域的事实。

## Contract

- `aico-recovery capture`必须从live state DB与sealed audit生成新artifact；先state后audit，manifest记录整体开始/完成与两个
  component完成时间。只声称bounded sequential window，不声称同一事务或同一精确时刻。
- artifact是`0600`、no-overwrite、固定三member ZIP_STORED：`recovery-set.json`、standalone `state.db`和portable
  `audit.zip`。manifest/member/outer hash分层验证，不保存live绝对路径或业务正文。
- schema强制`core_state_and_audit_only`、`global_transaction=false`、`business_restore_ready=false`；固定asset ledger不得
  删除memory/config/secret/grant/receiver缺口，也明确排除runtime lock/heartbeat等ephemeral文件。
- `verify`强制expected outer SHA，materialize后调用production SQLite integrity/schema verifier与audit backup/chain verifier。
- `drill`在private disposable workspace进一步调用state restore与audit materializer，可输出atomic owner-only JSON报告；
  不打开live source，也不提供combined destructive restore。

## Acceptance Evidence

- capture/verify输出同一outer SHA、state schema/table counts、audit count/head与capture window；manifest无payload/path。
- top artifact固定三member、owner-only；existing output、unsealed audit、live sidecar output均在发布前拒绝。
- 攻击者修改内嵌state并同步更新manifest/outer SHA时，production SQLite verifier仍拒绝。
- 把`business_restore_ready`改true、增加member或启用压缩均fail closed。
- combined drill实际运行两个production component materializer，清理workspace且report不泄漏正文/path。
- wrong SHA、宽权限、symlink和report publication race不覆盖旧证据。

## Stop Conditions

- 本集合只包含state/audit，不能称full asset、commercial DR或globally consistent snapshot。
- memory仍缺writer-locked/tamper-evident recovery point；config、secret、standing grant和receiver state仍由独立authority恢复。
- artifact包含完整SQLite与audit正文，`0600`不是加密；必须复制到owner批准的off-device encrypted storage。
- combined restore保持未实现；owner必须在隔离checkout持续保持runtime停止，按component合同恢复并完成业务验收。
