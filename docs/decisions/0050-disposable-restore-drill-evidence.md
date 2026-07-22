# ADR-0050: Disposable Restore Drill as Recovery Evidence

**状态**:Accepted
**日期**:2026-07-21
**决策者**:Codex / Round 212

## 背景

ADR-0049 已提供 AICO 主 SQLite 的 online backup、read-only verify 与 owner-fenced restore。但
`integrity_check=ok`、schema 和 SHA 只能证明 artifact 本身可读，不能证明 production restore path 能把它物化、
清理 sidecar 并再次打开。要求 operator 每次拿 live state 试恢复又会引入不必要的破坏风险。

## 决策

1. 新增 `aico-state drill`，对已选 artifact 再次验证 expected SHA，然后在私有临时目录调用同一个
   `restore_state_backup()` production primitive。
2. drill 不接收 live target；CLI 的全局 `--db` 不得被 drill 打开、创建、lock 或修改。
3. materialized DB 必须再次 read-only verify，并与输入 artifact 比较 schema 与所有已存在的 known-table count。
4. temporary DB、owner lock、WAL/SHM 和目录在成功/失败时都删除。
5. 可选 evidence report 是 new-path、`0600`、fsync、atomic no-overwrite JSON；只含 artifact basename、schema、
   counts、input/materialized SHA/size和完成时间，不含payload、secret、异常或绝对路径。
6. 该报告只证明本机 artifact + restore implementation。off-device storage、全资产恢复、RPO/RTO和真实IM仍由
   B-013的外部演练证明。

## 否决方案

- **把 `verify` 当 restore drill**：没有运行replace/sidecar/owner-lock/materialization路径，证据范围过窄。
- **对 live DB 做定期 test restore**：破坏性高，且会与human-absent runtime ownership冲突。
- **复制一份 restore 实现给 drill**：测试的是第二套代码，不能证明生产恢复路径。
- **保留临时 DB 供人工检查**：扩大payload暴露和磁盘retention；机器证据应bounded并自动清理。
- **报告覆盖固定 latest.json**：重跑会抹掉历史证据，也可能覆盖operator选择的文件。
- **用本机报告关闭B-013**：没有证明artifact离开故障域，也未覆盖JSONL/config/secrets/receiver state。

## 后果

### 正面

- operator无需停止live runtime即可反复验证备份是否真的能走生产恢复路径。
- evidence report可归档、diff和进入后续off-device演练清单。
- failure不会留下带业务payload的临时数据库。

### 代价与剩余风险

- drill需要至少容纳一份materialized DB的临时磁盘空间。
- schema/table count parity不等于业务E2E；最终DR仍需独立存储、credential重建和代表性IM样本。
- 本轮不自动调度drill、不删除旧report，也不接入云存储。

## 验证

- live owner active时drill成功且live DB不变。
- wrong hash/corrupt/missing workspace/report conflict与publish race fail closed。
- injected restore failure后workspace为空，无report。
- packaged CLI真实物化、report `0600`、live `--db`不存在且未被创建。
- 全量pytest、Ruff、mypy、结构、Compose和diff Gate。
