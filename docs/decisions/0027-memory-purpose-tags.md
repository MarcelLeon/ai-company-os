# ADR-0027: Memory Purpose Tags

**状态**:Accepted
**日期**:2026-05-21
**决策者**:Wang / Codex
**相关 Round**:Round 103

---

## 背景与问题

ADR-0026 确定 lead agent 要在授权范围内替 boss 做判断,并在重要决策前调取团队经验和 challenger / reviewer 意见。原有 `MemoryAtom.tags` 是自由标签,适合检索和分类,但不足以表达“这条记忆能否进入 lead 决策上下文”。

如果不区分用途,lead 可能读取过多 agent 内部 scratchpad,上下文变脏;如果只靠 scope,又无法区分 team 共识、任务关键进展、内部短期记忆和决策评审。

## 候选方案

### 方案 A — 继续只用自由 `tags`

- 优点:无需 schema 变化。
- 缺点:缺少稳定治理语义,不同 agent 可能写出不同标签,难以保证 `task_private` 不进入 lead 决策包。

### 方案 B — 新增单值 `purpose`

- 优点:模型简单。
- 缺点:一条记忆可能既是 broadcast,也是 task key progress;单值会丢失组合语义。

### 方案 C — 新增枚举型 `purpose_tags`

- 优点:保留组合能力,同时让检索和 prompt 注入能按稳定枚举过滤。
- 缺点:需要为旧 JSONL 记录提供默认值,并同步 `/recall`、broadcast 和 prompt 投影。

## 决策

选择 **方案 C**。

`MemoryAtom` 新增 `purpose_tags: tuple[MemoryPurpose, ...]`,默认旧记录为 `general_context`。第一批用途:

- `general_context`:通用项目事实、老板偏好或手动 `/remember`。
- `public_broadcast`:来自 team broadcast 的公共共识。
- `task_key_progress`:当前任务关键进展,用于汇报和 lead 调取。
- `task_private`:当前任务内部短期记忆,默认不进入普通检索包或 lead prompt。
- `decision_review`:challenger / reviewer / architect 等给 lead 决策使用的评审意见。

## 规则

- 普通 `MemoryRetriever` 默认排除 `task_private`。
- 只有显式 `allowed_purposes=(task_private,)` 的检索才可召回内部短期记忆。
- Team broadcast 生成的新记忆必须带 `public_broadcast`,并丢弃源记忆中的 `task_private`。
- `/recall` 必须展示 purpose,方便 boss 和下一轮 agent 判断记忆用途。
- Prompt Stack 可以展示 purpose,但仍只使用 `MemoryPacket` 投影,不暴露完整 store metadata。

## 后续

- Lead decision workflow 应优先召回 `public_broadcast`、`task_key_progress`、`decision_review`。
- Agent 自动写入任务总结时应把 stable progress 写为 `task_key_progress`,把 scratchpad 写为 `task_private`。
- Challenger / reviewer 的结论应写为 `decision_review`,供 lead 决策 memo 引用。

## 相关链接

- ADR-0022 A2A Memory Fabric
- ADR-0026 Lead Decision Team Contract
- `src/aico/core/memory.py`
- `src/aico/core/memory_broadcast.py`
- `src/aico/core/memory_commands.py`
