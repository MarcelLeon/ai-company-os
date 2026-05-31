# ADR-0031: Experience as injectable memory (M2)

**状态**:Accepted
**日期**:2026-05-31
**决策者**:Wang / Claude
**相关 Round**:Round 130
**相关文档**:[`docs/architecture/boss-first-grounding.md`](../architecture/boss-first-grounding.md) §3.1

---

## 背景与问题

ADR-0020 ~ ADR-0023 + ADR-0027 已经定义了 Memory Fabric:`MemoryAtom` + scope + purpose + sensitivity + confidence + status。

Round 128(Sprint M1)在 `MemoryAtom` 上加了 `kind=fact|experience` 和 `ExperienceMeta`,把 Dream 输出从普通 candidate memory 升级为 candidate experience。但**这些 experience 仍然只是"被存下来",不会进入任何 prompt**——因为 ADR-0023 的 MemoryGovernor 只会在 retrieval(call site = `_memory_packet_for_assignment`)里挑出 fact,**experience 默认不召回**。

`boss-first-grounding.md` §3.1 要求:
- experience 应该按 role + trigger **自动注入** role system prompt
- experience 生命周期是 candidate → active → archived,只有 `active` 才注入
- 命令归属于 lead 内务(老板不直接用 `/experience`)

## 候选方案

### 方案 A — 另起独立 `ExperienceStore` 与独立注入通道
- 优点:语义清晰,experience 与 memory 完全解耦。
- 缺点:scope / sensitivity / confidence / audit 治理要再写一遍;Dream 输出要双写;违反 boss-first-grounding §3.1 "对 MemoryAtom 的最小扩展,不另起一张表"。
- 复杂度:高。

### 方案 B — experience 仍是 `MemoryAtom`(kind=experience),但靠 `MemoryGovernor` 自动召回时升权
- 优点:复用现有 retrieval 链路。
- 缺点:语义混乱——experience 是 "经验性 lesson",和 fact 性 "项目知识" 检索逻辑完全不同(experience 是按 role 触发,fact 是按 query 相关性);把两者揉进同一个 scorer 会让 governance / debugging 都更难。
- 复杂度:中。

### 方案 C — experience 仍是 `MemoryAtom`(kind=experience),**单独走 ExperienceLayer 注入**
- 优点:retrieval 走 packet/governor;experience 走独立 list_experiences;两条注入通道在 prompt_stack 里分两段渲染,职责清晰。
- 缺点:`MemoryStore` Protocol 需要加 `promote_experience` + `list_experiences` 两个方法;mock store 要跟上(但实际 codebase 里没有独立 mock store,都用 JsonlMemoryStore,影响为零)。
- 复杂度:中。

## 决策

选择 **方案 C:experience 共用 MemoryAtom + 独立 ExperienceLayer 注入**。

### 关键决策点

1. **共用 `MemoryAtom` 存储,通过 `kind` 区分**:retrieval 链路里 governor 默认只看 `kind=fact`(experience 由 prompt_stack 的 ExperienceLayer 单独处理),scope / sensitivity / archive / audit 链路共用。
2. **`/experience` 命令是 lead 内务**:老板不直接调,不进 boss-first 命令组(NORTH_STAR §第一句"像管理一个真实团队":真实老板不审"经验晋升")。
3. **`MemoryStatus.CANDIDATE → ACTIVE → ARCHIVED` 三态**:复用 M1 已有的 status 枚举,不新建 lifecycle 字段。
4. **PromptStack 的 `_experience_section` 在 `_memory_section` 之后、`_runtime_section` 之前**:experience 放在已知 fact 之后,任务之前,让 prompt 形成"事实 → 经验 → 任务"的认知链。
5. **`_experiences_for_assignment` 调用 `list_experiences(scope, role_id=assignment.role)`**:experience 按 role 过滤,不按 query 文本相关性过滤(experience 是无条件适用 lesson,不需要 semantic match)。
6. **注入的 experience memory_ids 写入 task metadata `aico.injected_experience_ids`**:这是 **M3 verdict 回写的必要前置**——M3 grader 完成后要知道这次 task 用了哪些 experience,才能给 confidence / verdict_hits 反向回写。

### 该 sprint 不做的事(明确范围边界)

- ❌ Grader verdict 回写到 `verdict_hits` / `verdict_misses`(留 M3 sprint)
- ❌ `/undo` 撤销 promote(留 A2)
- ❌ aico-view 可视化 experience tree(留 V1)
- ❌ trigger-based 召回(experience 现在只按 role 过滤,trigger keys 字段存了但不参与召回)——留作未来精细化

## 结果

- `src/aico/core/memory.py`:`MemoryStore` Protocol 增加 `promote_experience` + `list_experiences`;`JsonlMemoryStore` 实现完整。
- `src/aico/core/prompt_stack.py`:`render_appointment_prompt(..., experiences=())` 新增 experiences 参数,新增 `_experience_section` 段。
- `src/aico/core/orchestrator_task_factory.py`:`task_for_assignment` 装配前调 `list_experiences(scope, role_id=role)`,装配后把 memory_ids 写入 task metadata。
- 新增 `src/aico/core/experience_commands.py`:`ExperienceCommandHandler`(< 280 行,严格遵守类 <500 行限制)。
- `src/aico/core/commands.py`:CommandName 加 `EXPERIENCE`,/help 加一行。
- `src/aico/core/orchestrator.py`:注入 `ExperienceCommandHandler`,加一行命令分发(Orchestrator 主体不写新逻辑)。
- 新增测试:`test_experience_commands.py`(5 用例)、`test_prompt_stack_experience.py`(3 用例)、`test_orchestrator.py` 加一个 E2E(dream→promote→ /ask 看 payload)。
- 验证:`uv run pytest` **347 passed / 1 skipped**;ruff / format / mypy 全绿。

## 后续相关 ADR / Sprint

- M3 sprint:Outcome Grader verdict 解析 + 通过 task metadata 中的 `aico.injected_experience_ids` 反向回写 confidence / verdict_hits / verdict_misses。
- A2 sprint:`/undo` 智能撤销可以撤掉 `promote_experience`(把 status 改回 CANDIDATE)。
- A3 sprint:`/rollback experience <id>` 精细操作。
- V1 sprint:aico-view 的 Memory Tree 视图同时展示 fact + experience。
