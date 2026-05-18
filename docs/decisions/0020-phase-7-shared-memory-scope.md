# ADR-0020: Phase 7 Shared Memory Scope

**状态**:Accepted
**日期**:2026-05-15
**决策者**:Codex
**相关 Round**:Round 74

---

## 背景与问题

Phase 6 已用 `/metrics`、audit replay、`aico-metrics`、`aico-glance` 和 token golden
完成可观测基线。Phase 7 的目标是让多个 AI 在同一个项目里共享上下文记忆。

问题是:共享记忆如果一开始就做成向量库、全自动摘要和跨项目长期知识系统,会难以审计、难以纠错,
也容易让 AI 把不可靠内容当事实。

## 候选方案

### 方案 A — 直接引入向量库 / RAG
- 优点:语义检索能力强,后续扩展空间大。
- 缺点:新增依赖和索引维护;早期很难解释“为什么召回这条记忆”;删除和纠错复杂。
- 复杂度:高。

### 方案 B — 只依赖各 Provider 自己的会话记忆
- 优点:实现最少。
- 缺点:Claude、Codex、Cursor 等记忆互不共享;换工具或重启后 AICO 无法审计和迁移。
- 复杂度:低。

### 方案 C — 先做 AICO 本地可审计记忆账本
- 优点:复用 Phase 4/6 的审计思路;JSONL 可读可恢复;每条记忆有 scope、source、confidence 和 created_by;可先支持精确检索和人工纠错。
- 缺点:第一版不是语义搜索;需要用户或命令明确写入重要事实。
- 复杂度:中低。

## 决策

选择 **方案 C:先做 AICO 本地可审计记忆账本**。

Phase 7 第一切片定义为:
- `MemoryRecord`:记录 id、project、scope、text、tags、source、confidence、created_by、created_at。
- `MemoryStore` 接口:append、list、search、archive。
- `JsonlMemoryStore`:本地 JSONL 持久化,可由 `AICO_MEMORY_PATH` 配置。
- IM 命令 MVP:
  - `/remember <text>`:把当前项目事实写入记忆。
  - `/recall [query]`:查看当前项目相关记忆。
  - `/forget <memory_id>`:归档错误或过期记忆,不物理删除。
- Prompt Stack 第一版只注入少量高置信、当前项目相关记忆,并保留 Facts 原文。

## 决策理由

- 符合北极星第二句:多个 AI 共享的是 AICO 管理的项目记忆,不是某个 Provider 私有会话。
- 符合北极星第三句:记忆必须可审计、可中断、可纠错,不能变成不可解释的黑箱。
- 复用已有产品语义:Project / Team / Role / Appointment,避免新增太多用户要记的概念。
- 先做 JSONL 可以快速 dogfood;未来如果需要向量搜索,可以把 JSONL 当权威源再派生索引。

## 后果

### 正面后果
- Phase 7 可以小步实现,不用先引入数据库或向量依赖。
- 用户能看到、纠正和归档 AI 共享的事实。
- 后续 `/brief`、`/daily`、`/weekly` 可以基于受控记忆增强,减少重新读长文档。

### 负面后果
- 第一版召回能力偏精确匹配,不适合复杂语义搜索。
- 重要事实需要显式写入或后续规则提取,不会自动“记住所有对话”。
- 记忆注入 Prompt Stack 需要限制条数和长度,否则会增加 token 成本。

### 我们接受这些代价是因为

Phase 7 的核心风险不是“搜不到”,而是“记错了还没人知道”。先让记忆可见、可审计、可纠错,
再升级语义检索。

## 不再做的事

- Phase 7 第一切片不引入向量数据库。
- 不自动把所有聊天和模型输出都写入长期记忆。
- 不把 Provider 私有 session memory 当作 AICO 共享记忆源。
- 不在没有 source / created_by 的情况下生成不可追溯记忆。

## 相关链接

- ADR-0015
- ADR-0016
- ROUNDS Round 74
