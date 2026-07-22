# ADR-0064: Bounded-Window Core Recovery Set

**状态**:Superseded by ADR-0065
**日期**:2026-07-22
**决策者**:Codex / Round 226

## 背景

State DB与audit ledger已有各自的backup/verify/drill/restore原语，但operator仍可能从不同日期、不同运行阶段各取一个
“绿色artifact”并口头拼成同一次恢复。两个组件分别可信，不证明它们属于同一采集窗口，更不证明memory、配置、secret、
standing grant和独立receiver state已经覆盖。B-013需要一个机器可读的component RPO manifest，同时不能伪装全局事务。

## 候选方案

- 只写runbook要求文件名带同一日期：否决；命名不绑定字节，也不列缺失资产。
- 单独JSON sidecar引用两个外部路径：否决；跨设备容易漏文件，artifact替换后sidecar仍可看似有效。
- 停止所有系统后制造“全局事务快照”：否决；SQLite、audit、memory与独立receiver没有共享transaction coordinator，停机
  也不能追溯产生原子提交时刻。
- 把所有路径和`.env`直接打成全量包：否决；泄漏secret并把尚无一致快照合同的memory包装成已保护。
- 固定三member ZIP_STORED，嵌入两个既有verified component artifact与显式coverage ledger：采用。

## 决策

1. `aico-recovery capture`按state→audit顺序生成独立component recovery point，并封装为owner-only、new-path、固定
   `recovery-set.json`/`state.db`/`audit.zip`三member artifact。
2. manifest记录整体capture start/end、每个component completion、hash/size与业务摘要；schema固定声明
   `scope=core_state_and_audit_only`、`consistency=sequential_component_snapshots`、`global_transaction=false`、
   `business_restore_ready=false`。
3. 固定asset ledger列出state/audit captured，以及memory snapshot缺失、project/persona config从reviewed source control
   恢复、runtime secret/standing grant重新注入、receiver state独立备份、ephemeral runtime排除。缺项不能从manifest删除。
4. verify要求owner独立记录的outer SHA，流式materialize后调用现有state/audit production verifier并核对inner summary。
5. drill在disposable workspace继续调用两套production restore/materialization primitive并可发布owner-only report。
6. 本决策不提供combined restore。恢复顺序、runtime持续停机和未包含资产必须在隔离checkout由operator验收。

## 取舍与后果

- 单文件集合降低跨设备漏件/错配风险，但会再次复制内部artifact，增加IO和明文存储体积。
- capture允许live runtime继续运行，因此只证明两个snapshot都落在记录窗口内；窗口越长，cross-component skew风险越高。
- 固定false readiness阻止本地工具制造DR完成假阳性，但也意味着即便某部署未启用某资产，仍需在业务演练中显式裁决。
- outer hash和manifest不是签名；artifact仍需独立加密存储、SHA authority、retention和访问审计。
