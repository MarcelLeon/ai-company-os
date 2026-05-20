# ADR-0023: Memory Semantic Retrieval

**状态**:Accepted
**日期**:2026-05-18
**决策者**:Wang / Codex
**相关 Round**:Round 84

---

## 背景与问题

Phase 7 第一版共享记忆已经有 `MemoryAtom`、`JsonlMemoryStore`、`MemoryRetriever` 和
`MemoryGovernor`,但召回主要依赖 query 子串 / token overlap。人类验收时指出:
这种方式不符合实际团队管理场景,老板或 agent 往往会用自然语言复述同一件事,例如
“我更喜欢汇报进度时告诉我还有几阶段”和“汇报当前项目进度,并告诉我还有几阶段”。

记忆召回需要升级为语义检索,但仍要保持 AICO 的治理边界:
- 不能跨 project / team 泄漏。
- candidate / archived / restricted 记忆不能因为语义分数高就进入 prompt。
- 召回结果必须能保留 citation,不能变成不可解释黑箱。
- token-saving 不能让每次普通任务都额外消耗一次不受控 LLM 调用。

## 候选方案

### 方案 A — 继续关键字检索
- 优点:实现简单、完全确定性。
- 缺点:中文长句、近义词、跨语言项目术语召回弱,不满足企业/团队管理体感。
- 复杂度:低。

### 方案 B — 每次召回都调用 LLM 判断相关性
- 优点:语义能力强。
- 缺点:延迟和 token 成本不可控;模型输出需要结构化校验;失败时会影响所有 project task。
- 复杂度:中高。

### 方案 C — 可插拔 `MemorySemanticScorer`,本地语义 scorer 先落地
- 优点:立即改善中文长句和常见中英术语召回;保留 scope/governor/citation;未来可替换为 embedding 或 LLM rerank。
- 缺点:本地 scorer 仍不是完整语义模型,领域别名需要持续扩展。
- 复杂度:中。

## 决策

选择 **方案 C**。

新增 `MemorySemanticScorer` 接口,`JsonlMemoryStore.search()` 和 `MemoryRetriever` 使用 semantic score
而不是只按 query 子串过滤。第一版默认实现 `LocalSemanticMemoryScorer`:
- ASCII token / CJK n-gram 切分。
- 常见项目管理术语和中英别名扩展,例如 `法务` ↔ `legal review`、`汇报/进度/阶段` ↔ `report/progress/stage`。
- `MemoryRetriever` 先按 scope 收集候选,再按 semantic score 排序。
- `MemoryGovernor` 仍负责 active / sensitivity / confidence 过滤。

后续如果接 embedding 或 LLM reranker,只替换 `MemorySemanticScorer` 实现,不改变
`MemoryAtom`、`MemoryPacket`、`MemoryGovernor` 和 Orchestrator 的上层契约。

## 后果

- `/recall` 和 Prompt Stack 可召回自然语言复述的中文偏好。
- 中文查询“法务检查”可以召回英文项目事实 “legal review”。
- 召回仍受 project/team scope 和 governor 限制。
- 当前默认实现不是外部模型调用;它是 model-ready 的本地 semantic scorer。真实 embedding / LLM rerank
  需要后续在成本、延迟、失败回退和可审计 citation 上再做一轮设计。

## 落地更新:2026-05-20

Round 96 将 ADR-0023 从“semantic scorer”推进到可解释检索契约:

- 新增 `MemoryRetrievalQuery`:统一承载 query、scopes、role、agent、task kind、top_k 和 token budget。
- 新增 `MemoryRetrievalHit`:保留 atom、semantic/scope/recency/confidence/evidence/graph/final score 和 reason。
- `MemoryRetriever.retrieve()` 先产出可解释 hits,`retrieve_packet()` 再把 hits 投影为 `MemoryPacket`。
- 排序使用本地加权模型:

```text
final_score =
  semantic_score * 0.45
+ scope_score * 0.20
+ confidence_score * 0.15
+ recency_score * 0.10
+ evidence_score * 0.05
+ graph_score * 0.05
```

- scope closeness 按 agent > role > team > project > boss global 排序;boss global 仍只作为偏好/工作方式类记忆进入普通项目 prompt。
- `/recall` 改为复用 `MemoryRetriever`,并展示 reason,让老板和下一轮 agent 能知道为什么召回某条记忆。
- 第一版 `graph_score` 先保留为 0.0,后续可沿 `supports` / `derived_from` / `broadcast_to` 关系扩展邻居,但不能绕过 scope 和 governor。

Round 97 继续落地 graph / task-aware 检索:

- `MemoryRetriever` 会对直接命中的记忆沿 `supports` / `derived_from` / `broadcast_to` 扩展一跳 graph 邻居。
- graph 邻居必须已经位于本次 retrieval query 允许的 scopes 中,并通过 `MemoryGovernor`;跨 project / team 记忆不会因为 edge 被带入。
- `MemoryRetrievalQuery.role_id`、`agent_id`、`task_kind` 会扩展为本地 query hints,例如 `tester` 补充 `test / qa / regression / checklist`,`release` 补充 `release / changelog / release notes`。
- `/recall` 输出增加 final / semantic / scope / graph score,便于真实 IM 验收和后续调权。

## 相关

- ADR-0022:A2A Memory Fabric
- PITFALLS P-019
- `src/aico/core/memory.py`
- `tests/unit/test_memory.py`
