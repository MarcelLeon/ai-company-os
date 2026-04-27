# PITFALLS.md — 踩坑录

> 本项目踩过的所有坑。**踩同一个坑两次是不可接受的**。
>
> 每个坑必须有:简短标题、症状、根因、解决方案、状态、相关文件。
>
> Agent 接手任何任务前,先 grep 这里看相关关键词。

---

## 状态图例

- 🔴 **OPEN** — 已知问题,尚未解决
- 🟡 **MITIGATED** — 已绕过/缓解,根因未除
- 🟢 **RESOLVED** — 已彻底解决
- ⚫ **WONT_FIX** — 决定不修(留作记录)

---

## 索引(按主题分类)

### 文档与流程
- (待填充)

### 技术栈
- (待填充)

### Adapter 层
- (待填充)

### IM 通道
- (待填充)

### 人格化与状态
- (待填充)

### 部署与运维
- (待填充)

### Java / Spring AI 相关
- (待填充)

### Python 相关
- (待填充)

---

## 详细坑位记录

> 模板:
>
> ```markdown
> ### [P-XXX] 简短标题
>
> **状态**:🔴 OPEN / 🟡 MITIGATED / 🟢 RESOLVED / ⚫ WONT_FIX
> **首次踩中**:Round N
> **最后更新**:YYYY-MM-DD
> **影响范围**:`path/to/affected/files`
>
> **症状**
> 具体出现了什么现象、报错。
>
> **根因**
> 为什么会发生这个问题。
>
> **解决方案 / 缓解措施**
> 具体怎么处理的。代码示例放这里。
>
> **如何避免再次踩中**
> 给后人的具体可执行建议。
>
> **相关链接**
> - ROUNDS Round N
> - ADR-XXX
> - PR #YY
> ```

---

### P-001(示例) 抽象过早,Adapter 接口频繁返工

**状态**:🟢 RESOLVED(示例,演示用)
**首次踩中**:Round 0(示例)
**最后更新**:2026-04-26
**影响范围**:`docs/agent/03-design-patterns.md`(预防性记录)

**症状**
(示例)在没接入第二个 AI 之前就过早设计了大而全的 `AIAdapter` 抽象接口,接入第二个 AI 时发现 1/3 的接口方法用不上,1/3 需要改签名。

**根因**
(示例)违反 Rule of Three,在仅 1 个实现样本时就抽象。

**解决方案 / 缓解措施**
(示例)在 [`docs/agent/03-design-patterns.md`](../agent/03-design-patterns.md) 写明"抽象时机判定"硬规则:第 3 次出现相似代码时再抽象,第 1、2 次直接复制粘贴。

**如何避免再次踩中**
- PR 中抽象层超过 3 个接口方法的,review 时必须问"现在有几个实现样本"
- 接 Adapter 时按"先复制 Claude Code Adapter,改成 Codex Adapter"的方式做,不要一开始就大重构

**相关链接**
- (本条为示例条目,实际触发后填充真实链接)

---

<!-- 真实坑位从下方追加。每个新坑单独一条。 -->

### [P-002] 文档文件被扁平化导致 AGENTS 路径失效

**状态**:🟢 RESOLVED
**首次踩中**:Round 2
**最后更新**:2026-04-27
**影响范围**:`AGENTS.md`, `README.md`, `STATUS.md`, `docs/`

**症状**
`AGENTS.md` 要求读取 `docs/journal/ROUNDS.md`、`docs/agent/01-development-workflow.md` 等路径,但实际文件曾经全部堆在仓库根目录。Agent 按强制阅读路径执行时会找不到文档,只能靠猜测同名根目录文件。

**根因**
Round 1 设计的是 `docs/agent` / `docs/journal` / `docs/architecture` / `docs/human` 分层目录,但落盘或拷贝过程中只保留了扁平文件结构,导致文档契约和文件系统不一致。

**解决方案 / 缓解措施**
Round 2 已将文档归位:
- Agent 指南移动到 `docs/agent/`
- journal 三件套移动到 `docs/journal/`
- 架构文档移动到 `docs/architecture/`
- 人类操作文档移动到 `docs/human/`
- 补回 `docs/decisions/README.md` 和 `docs/playbooks/README.md`

**如何避免再次踩中**
- 新增文档时先确认它属于哪个目录,不要直接丢到根目录。
- 修改 `AGENTS.md` 或 `README.md` 的路径后,用 Markdown 链接检查脚本验证断链。
- 根目录只保留入口级文档:`README.md`、`AGENTS.md`、`NORTH_STAR.md`、`STATUS.md`、`CONTRIBUTING.md`、`CHANGELOG.md`。

**相关链接**
- ROUNDS Round 2
