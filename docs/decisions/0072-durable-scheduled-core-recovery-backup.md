# ADR-0072: Durable Scheduled Core Recovery Backup Without Automatic Restore

**状态**:Superseded by ADR-0074
**日期**:2026-07-22
**决策者**:Codex / Round 234

## 背景

`aico-recovery capture|verify|drill`已经能生成和验证core recovery set，但都依赖operator记得执行。boss-absent期间若
Mac持续运行而无人触发命令，真实RPO会无限增长；简单cron又会在崩溃、目标mount缺失或已有artifact时产生覆盖和假成功。

## 候选方案

- 继续只保留手动命令：否决；工具存在不能约束无人值守RPO。
- 由scheduler同时capture、retention和restore：否决；自动删除与恢复都是独立破坏性权限，不能随capture隐式授权。
- 默认关闭的durable capture + immediate verify：采用；外部存储、加密、retention和restore继续由独立owner策略负责。

## 决策

1. 每个到期窗口先在主SQLite写稳定backup intent，再创建固定new-path artifact；状态为
   PENDING/RUNNING/RETRYING/VERIFIED/EXHAUSTED，失败按1/5/15/15分钟最多五次。
2. artifact发布后立即运行production deep verifier，再原子写owner-only receipt sidecar和SQLite receipt。进程重启按
   artifact/sidecar存在矩阵复验并补齐，禁止覆盖已有文件或只凭文件名结算。
3. scheduler是Phase1拥有的后台任务，纳入heartbeat required health和bounded self-healing。无verified receipt为DEGRADED，
   超过配置max age或attempt耗尽为FAILED；`aico-state`只显示ID、状态和SHA。
4. 功能默认关闭。启用时目标必须已存在、absolute、owner-only、非symlink、位于checkout外；缺失mount直接fail closed，
   不自动创建目录。doctor只验证本机路径合同，不证明目标已加密、off-device或受retention保护。
5. scheduler永不调用restore，也不自动删除旧artifact。component/global consistency和
   `business_restore_ready=false`沿用recovery-set合同。

## 后果

- boss不在场时，core recovery set的capture意图、重试、复验和RPO freshness可由机器持续监督。
- state backup会先于当前成功receipt写入，因此artifact不会包含自己的最终VERIFIED行；这不是全局事务，也不影响外部receipt绑定。
- B-013仍需要owner选择真实第二存储故障域、加密/密钥、retention、外部SHA和隔离恢复演练；本ADR不关闭商业DR缺口。

## 相关链接

- ROUNDS Round 234
- ADR-0064
- PITFALLS P-090
- Goal Brief `docs/superpowers/specs/2026-07-22-durable-scheduled-core-recovery-backup.md`
- `src/aico/app/recovery_backup_scheduler.py`
