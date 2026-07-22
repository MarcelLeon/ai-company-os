# ADR-0067: Secret-free Runtime Reinjection Receipts

**状态**:Superseded by ADR-0068(recovery-set v5 only; reinjection contract remains accepted)
**日期**:2026-07-22
**决策者**:Codex / Round 229
**Supersedes**:ADR-0066的recovery-set v3传输范围；reviewed configuration revision决策继续有效

## 背景

State、audit、memory和reviewed config都可验证后，灾后runtime仍需要重新注入IM/alert/liveness secret，并明确是否恢复
standing autonomy。把`.env`、secret值或grant正文放入recovery ZIP会扩大明文泄露面；记录普通SHA-256既可能支持低熵凭据
离线猜测，也会错误要求轮换后的secret与事故前相同。只跑`aico-service doctor`又不会留下绑定到某个recovery set的不可覆盖证据。

## 候选方案

- 把`.env`和grant文件嵌入recovery set：否决；复制secret和授权正文，违背最小披露与显式重新授权。
- 记录每个secret/grant文件的普通hash：否决；产生稳定关联和离线猜测面，也阻止合规轮换。
- 只要求operator口头确认已恢复：否决；没有机器可验的set/revision/runtime binding。
- capture保存无值slot/mode合同，灾后复用production preflight并生成owner-only receipt：采用。

## 决策

1. recovery capture读取checkout根目录owner-only且Git未跟踪的`.env`，复用`aico-service`生产preflight检查channel、required keys、
   alert/liveness、IM ingress、approval lease及standing autonomy；manifest只保存active secret slot名称和grant enabled mode。
2. secret值、secret hash、owner/target ID、grant正文和grant ID均不进入manifest或receipt。有效secret允许在灾后轮换；slot集合、
   channel和grant enabled mode必须与capture合同一致。
3. standing grant启用时，receipt要求外部owner-only grant非空，并通过真实Project/Persona/Adapter/morning target的完整preflight；
   grant可由owner重新签发，不要求与旧正文相同。
4. `aico-recovery reinjection-receipt`必须同时deep verify recovery set、exact clean checkout与当前runtime material，并要求
   safe `--owner-decision-ref`。输出是`0600`、atomic new-path JSON，绑定set SHA、config revision、slot/grant count与时间。
5. `verify-reinjection`必须使用独立保存的receipt SHA，再次运行全部当前materialization检查；wrong SHA、slot/mode drift、
   宽权限、symlink、receipt伪造或失效grant均fail closed。
6. recovery-set升级schema v4；`control_plane_secrets`与`standing_grant`标记`reinject_and_attest`合同就绪但不内嵌。
   `ai_provider_authentication`单列为未就绪，因为本地presence/preflight不证明Claude/Codex远端登录可用。
7. receipt永久保持`business_restore_ready=false`与`external_authentication_live_verified=false`；dead-man receiver state和
   AI provider真实认证仍需独立合同/样本。

## 取舍与后果

- recovery operator可轮换credential和重新签发grant，但必须留下owner decision reference；该reference是审计关联，不是数字签名。
- receipt证明当前文件、配置和本地binding通过检查，不证明secret远端有效、owner本人身份、AI provider额度或完整业务RTO/RPO。
- `.env`中的非secret身份值可在owner决策下重配，不承诺与事故前逐字节相同；若需要强身份连续性，应由外部secret/identity
  manager提供签名版本，而不是把低熵ID hash放入artifact。
