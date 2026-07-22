# ADR-0066: Reviewed Configuration Revision Recovery

**状态**:Superseded by ADR-0067
**日期**:2026-07-22
**决策者**:Codex / Round 228
**Supersedes**:ADR-0065的recovery-set v2传输范围；memory ledger/recovery决策继续有效

## 背景

State、audit和memory都能恢复后，AICO仍可能在另一份代码或配置上启动：相同数据配合不同Project/Persona规则会改变角色、
授权和任务路由。把配置正文复制进recovery ZIP会重复source control并诱导打包secret；只记录capture时的当前HEAD又会把任意
本地commit自动称为“reviewed”。B-013需要可验证的revision/checkout合同，而不是口头要求“恢复同一版本”。

## 候选方案

- 把整个checkout或两个配置文件嵌入recovery set：否决；重复源码、放大明文面，并绕开reviewed source control。
- capture自动信任当前HEAD：否决；当前commit存在不证明owner/CI选择过它。
- 只记录commit SHA：不足；dirty tracked/untracked文件和active config路径仍可能改变运行行为。
- 由独立参数提供reviewed full commit，再绑定clean HEAD/tree和active config blob/hash：采用。

## 决策

1. capture必须获得`AICO_REVIEWED_CONFIG_REVISION`或`--expected-config-revision`中的完整40/64位commit；它与checkout HEAD
   不同、格式错误或缺失时fail closed。artifact记录authority类型为`operator_supplied_revision`，不伪称签名证明。
2. checkout必须是Git worktree root且`git status --porcelain --untracked-files=all`为空；recovery输出必须在checkout之外。
3. active project config必须是checkout内、非symlink、有效JSON且字节与该commit blob一致；显式persona config同样验证，
   未配置时persona来源固定为`built_in_at_revision`。
4. recovery-set升级schema v3，manifest绑定commit、tree、object format、relative path、blob OID、size与SHA-256；不嵌入配置正文。
5. `aico-recovery verify-checkout`先深验outer/inner artifact，再要求目标checkout HEAD/tree、clean status及active config完全匹配。
6. asset ledger新增`recovery_contract_ready`：project/persona config可标为合同已就绪但`included=false`；secret、standing grant
   和receiver DB仍未就绪，`business_restore_ready=false`保持不变。

## 取舍与后果

- 自动backup必须由部署流程维护reviewed revision锚点；新版本发布后不更新锚点会故意阻止capture。
- clean检查不包含Git ignored运行数据；`.aico`、日志和venv仍按各自恢复/ephemeral合同处理，不属于源码证明。
- commit/hash不是代码评审平台签名，也不证明remote仍可取得对象；outer SHA authority、off-device clone和业务演练仍由B-013跟踪。
