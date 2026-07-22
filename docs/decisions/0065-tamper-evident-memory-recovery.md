# ADR-0065: Tamper-Evident Memory Recovery

**状态**:Superseded by ADR-0066
**日期**:2026-07-22
**决策者**:Codex / Round 227
**Supersedes**:ADR-0064的recovery-set v1传输范围

## 背景

Memory JSONL会影响后续prompt、经验注入与老板恢复面，但旧实现只有进程内索引和普通append：多进程writer可基于陈旧索引
继续写，写失败前已更新内存，合法JSON篡改/重排/截断不会被发现，也没有matching recovery point。Round 226因此只能在core
recovery set中把memory标为缺失资产。

## 候选方案

- 直接复制raw JSONL并在恢复后重新加载：否决；复制可能跨写入，且无法区分原始历史与被修改历史。
- 把memory迁入主SQLite：暂缓；这会扩大核心存储迁移和兼容范围，不是关闭当前DR缺口的最小变化。
- 只加进程文件锁：不足；能串行写入，但不能检测历史修改、tail截断或匹配checkpoint。
- 复用audit的安全语义，为memory保留独立domain model与artifact：采用。

## 决策

1. Memory record使用独立SHA-256 previous/head链、owner-only tail checkpoint和process file lock。append先写入并fsync JSONL，
   再原子发布checkpoint；进程索引只在durable append成功后重建。
2. writer每次append前刷新磁盘状态，保留同`memory_id`多版本“最后一条生效”语义；legacy JSONL必须owner核对后显式
   `aico-memory seal`，不自动把未知历史包装成可信baseline。
3. `aico-memory backup|verify-backup|drill-backup|restore`使用固定member、outer SHA、生产verifier/materializer、runtime owner
   fence和恢复前verified safety或unverified quarantine。restore必须显式SHA、preservation路径与`--yes`。
4. recovery set升级schema v2，按state→audit→memory顺序绑定三个独立component artifact，scope改为
   `core_state_audit_memory`；仍固定`global_transaction=false`与`business_restore_ready=false`。
5. 本决策不引入自动restore、secret/grant打包、跨组件事务或off-device存储承诺。

## 取舍与后果

- 每次memory读取会检查ledger identity，append后重建索引，换取跨进程可见性和fail-closed完整性；大规模memory后需用测量
  决定是否增加受校验的索引快照，不能先静默牺牲正确性。
- ledger与checkpoint仍是两个文件；发布中断会被检测并可重跑，不声称两次rename原子。
- core set现在少一个必需缺项，但配置revision、secret/grant reinjection、receiver DB与off-device业务演练仍未完成。
