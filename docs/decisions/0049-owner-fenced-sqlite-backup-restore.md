# ADR-0049: Owner-Fenced SQLite Online Backup and Restore

**状态**:Accepted
**日期**:2026-07-21
**决策者**:Codex / Round 211

## 背景

`AICO_STATE_DB_PATH` 已承载 task、approval、overnight、recovery audit outbox 和 runtime alert
等业务状态，但运维文档中的备份/恢复仍是空注释。直接复制主 DB 会遗漏 WAL 中已提交事务；让 restore
与 active runtime 并发则可能把新旧 DB、WAL/SHM 和进程内 owner 混成不可解释状态。仅有持久化不等于可恢复。

## 决策

1. 备份使用 SQLite online backup API，从 live source 生成单文件、transaction-consistent artifact；备份是只读
   操作，允许 runtime owner 活跃时执行。
2. artifact 必须是新路径、`0600`、当前 schema、`integrity_check=ok`，并返回 exact-byte SHA-256。verify
   使用 read-only/immutable SQLite URI，不运行 schema bootstrap 或 migration。
3. restore 必须先验证 artifact、schema 和 owner 提供的 expected SHA，再获取与 runtime 相同的 canonical
   kernel owner lock。active runtime 时 fail closed。
4. 替换前先对当前 target 创建并验证 timestamped pre-restore safety backup。选定 artifact 经 SQLite backup
   写入 target 同目录 temp DB，验证/fsync 后 atomic replace；WAL/SHM 仅在 owner fence 内清理。
5. `reset --yes` 同样取得 owner fence。restore/reset 仍要求显式确认，不进入 autonomous scheduler。
6. JSON summary 只暴露 artifact basename、schema/count/size/hash，不暴露业务 payload、secret、原始异常、
   lock metadata 或 source absolute path。

## 否决方案

- **直接 `cp state.db`**：WAL mode 下可能得到不一致或缺事务的 artifact，且不能证明 standalone。
- **停机后才允许 backup**：安全但破坏 boss-absent 在线运行；SQLite 已提供一致的在线 backup contract。
- **active runtime 内热 restore**：即使 SQLite 文件替换原子，旧连接、WAL 和进程内状态仍可能继续写旧事实。
- **restore 时跳过当前库 safety backup**：误选 artifact 或 operator error 后没有本机回退点。
- **verify 时通过 `SQLiteStateDatabase` 打开**：该 helper 有 schema bootstrap 责任，不符合只读证据校验。
- **本轮同时做云备份/保留策略/自动 restore**：会引入凭据、第二故障域、删除策略和无人值守破坏性动作，
  超出本地恢复原语的可验证边界。

## 后果

### 正面

- AICO 主业务状态首次具备可执行、可机器复核的 backup/verify/restore round trip。
- backup 不要求停止长期运行的本地公司；restore/reset 不会与 runtime owner 竞争。
- hash、safety artifact 和 atomic replacement 给 operator 提供明确选择与回退证据。

### 代价与剩余风险

- 当前只覆盖 AICO SQLite business state，不覆盖 audit/memory JSONL、项目配置、`.env`、日志或 dead-man
  receiver DB。
- local artifact 与 local restore test 不等于 disaster recovery。商用容灾仍需要 off-device 加密存储、保留
  策略和 disposable-host restore drill，登记为 B-013。
- 当前只接受相同 schema，跨版本恢复需要未来显式 migration contract。

## 验证

- online backup 在 runtime owner active 时保持 point-in-time consistency。
- corrupt/wrong-schema/wrong-hash/existing-output/active-owner 均 fail closed。
- restore round trip 创建 safety backup、恢复旧状态、删除 stale sidecar。
- CLI confirmation、JSON redaction、Ruff、mypy、结构和全量测试 Gate。
