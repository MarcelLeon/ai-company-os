# 热点叙事化 Memory + Dream Showcase 测试验证报告

**日期**:2026-07-07
**范围**:芙莉莲式“长记忆旅队”case、鬼灭无限城式“作战会议”case
**结论**:通过。两个 case 已用机器 E2E 验证 AICO 的共享记忆、`/dream` 候选经验、经验晋升注入、协作审计链路。验证过程还发现并修复了两个产品边界问题。

> 说明:本文中的“芙莉莲式”“无限城式”只表示叙事结构借鉴。测试与宣传素材均使用原创项目、角色和文本,不使用官方截图、Logo、角色台词或商业授权素材。

---

## 1. 测评目标

本次测评不是单纯证明代码能跑,而是验证 AICO 能否把一个大众熟悉、适合传播的故事场景转化为真实产品能力:

1. **共享记忆**:项目里已经写下的事实,是否会进入后续角色任务 prompt。
2. **Dream 候选经验**:`/dream` 是否能从近期任务状态中提炼 candidate experience。
3. **经验晋升**:`/experience promote` 后,经验是否进入指定角色的 `Reusable experience` prompt layer。
4. **协作审计**:角色输出 `@reviewer: ...` 后,是否创建 reviewer child task 并记录 `collaboration_requested` audit。
5. **产品自省**:如果 case 暴露产品能力表达不清或边界不对,是否修正产品而不是只改文案。

---

## 2. 测评构建方式

### 2.1 为什么选这两个 case

**芙莉莲式长记忆旅队**

这个场景天然适合测共享记忆。故事钩子是“长时间之后才意识到队友说过的话很重要”。AICO 的对应产品命题是:

> AI 团队不应该等很久以后才想起老板和队友说过什么。

它主要验证:

- project-scoped fact memory 能进入 `Shared memory`;
- blocked task 能被 `/dream` 提炼成 candidate experience;
- promote 后的经验能进入 implementer 的下一次任务。

**无限城式作战会议**

这个场景适合测协作和审计。故事钩子是“战场在变化,每个角色只有局部情报,必须共享信息、审查风险、复盘阻塞”。AICO 的对应产品命题是:

> 真正的 AI 公司要能共享情报、让队友审查计划、把夜里卡住的任务变成下一次可复用的经验。

它主要验证:

- fact memory 能被 scout 任务召回;
- scout 输出 `@reviewer` 后创建 reviewer child task;
- audit 里保留 source、target、parent task;
- approval-blocked task 能进入 `/dream` candidate experience;
- promote 后经验进入 swordsman 下一次任务。

### 2.2 测试实现文件

核心机器测试:

- `tests/unit/test_pop_culture_memory_dream_showcase.py`

配套 showcase 文档:

- `docs/showcase/frieren-memory-dream-case.md`
- `docs/showcase/infinity-castle-memory-dream-case.md`

产品边界修复:

- `src/aico/core/memory.py`
- `src/aico/core/dream.py`

相关回归测试:

- `tests/unit/test_memory.py`
- `tests/unit/test_orchestrator.py`

---

## 3. 执行过程

### 3.1 聚焦 showcase 测试

命令:

```bash
uv run pytest tests/unit/test_pop_culture_memory_dream_showcase.py -vv
```

结果:

```text
tests/unit/test_pop_culture_memory_dream_showcase.py::test_fantasy_party_case_validates_shared_memory_dream_and_experience PASSED
tests/unit/test_pop_culture_memory_dream_showcase.py::test_infinity_castle_case_validates_collaboration_audit_and_dream PASSED

2 passed in 0.17s
```

验证含义:

- 两个 case 都能跑过真实 AICO Orchestrator / TaskBus / JsonlMemoryStore 链路。
- 不是纯文档,也不是 mock 一个“看起来像产品”的结果。

### 3.2 相关回归测试

命令:

```bash
uv run pytest tests/unit/test_pop_culture_memory_dream_showcase.py tests/unit/test_orchestrator.py tests/unit/test_memory.py -q
```

结果:

```text
98 passed in 0.28s
```

验证含义:

- 新增 showcase 没有破坏既有 memory / orchestrator 行为。
- `/dream` 和 experience prompt 注入的旧测试仍可通过。

### 3.3 全量测试

命令:

```bash
uv run pytest -q
```

结果:

```text
503 passed, 1 skipped in 0.96s
```

验证含义:

- 本轮产品修复未引入全仓测试回归。
- skipped 项为既有跳过项,本轮未新增跳过测试。

### 3.4 类型检查

命令:

```bash
uv run mypy src tests
```

结果:

```text
Success: no issues found in 147 source files
```

验证含义:

- 新增测试 helper 和 core 修改通过类型检查。

### 3.5 Lint 与格式

命令:

```bash
uv run ruff check .
```

结果:

```text
All checks passed!
```

命令:

```bash
uv run ruff format --check src/aico/core/dream.py src/aico/core/memory.py tests/unit/test_memory.py tests/unit/test_orchestrator.py tests/unit/test_pop_culture_memory_dream_showcase.py
```

结果:

```text
5 files already formatted
```

验证含义:

- 全仓 lint 通过。
- touched code/test files 格式检查通过。

### 3.6 Diff 空白检查

命令:

```bash
git diff --check
```

结果:通过,无输出。

验证含义:

- 没有尾随空格、冲突标记或明显 diff 格式问题。

---

## 4. 结果分析

### 4.1 已证明的能力

**能力 1:共享记忆可进入角色任务**

芙莉莲式 case 中,先执行:

```text
/remember The party promised to write down companion preferences before accepting a new village request.
/ask lead plan the winter village request
```

测试断言 lead task payload 中存在:

```text
Shared memory:
companion preferences
```

无限城式 case 中,先执行:

```text
/remember The castle route shifts after every encounter; preserve last known safe exits.
/ask scout prepare the first raid plan using safe exits
```

测试断言 scout task payload 中存在:

```text
Shared memory:
last known safe exits
```

结论:project-scoped fact memory 可以进入后续角色任务 prompt。

**能力 2:`/dream` 能产生 candidate experience**

两个 case 都通过一个 approval-blocked task 触发 `/dream`。测试断言 candidate:

- `kind is MemoryKind.EXPERIENCE`
- `status is MemoryStatus.CANDIDATE`
- `source == "dream_review"`

结论:`/dream` 不是只生成文本提示,而是实际写入可 review 的 candidate experience。

**能力 3:promote 后经验会进入角色 prompt**

执行:

```text
/experience promote <candidate-id> as implementer
/ask implementer plan the retry
```

或:

```text
/experience promote <candidate-id> as swordsman
/ask swordsman prepare the next strike
```

测试断言后续任务 prompt 中存在:

```text
Reusable experience (promoted lessons):
<candidate-id>
```

并且 metadata 中存在:

```text
aico.injected_experience_ids=<candidate-id>
```

结论:经验不会自动污染下一轮任务,但经 promote 后会进入指定角色的 Experience layer。

**能力 4:协作审计链路可追溯**

无限城式 case 中,scout 输出:

```text
@reviewer: inspect the raid plan for blind spots and missing approvals.
```

测试断言:

- reviewer child task 被创建;
- reviewer payload 包含 `Context from scout output so far`;
- audit 中存在 1 条 `collaboration_requested`;
- audit 记录:
  - `actor_id == "scout"`
  - `target_persona == "reviewer"`
  - `detail == "parent_task=castle-task-001"`

结论:AICO 能把角色间协作变成可审计的 child task,不是简单把文本转发出去。

---

## 5. 产品自省与优化

### 5.1 发现的问题 1:`/dream` 下一步引导错误

旧行为:

`/dream` 已经生成 candidate experience,但消息 Next 仍提示:

```text
/remember <accepted lesson>
```

问题:

这会把用户带回“事实记忆”入口,破坏 Dream → Experience Review → Promote 的产品闭环。

修复:

`/dream` Next 改为:

```text
/experience review
/experience promote <candidate-id> as <role>
```

验证:

`test_orchestrator_dream_writes_reviewable_candidate_memory` 已覆盖。

### 5.2 发现的问题 2:promoted experience 可能混入 Shared memory

旧行为:

`MemoryGovernor` 没有过滤 `kind=experience`,因此 promoted experience 可能同时出现在:

- `Shared memory`
- `Reusable experience`

问题:

事实记忆和经验教训混在一起,会让产品概念变脏,也会让宣传时说不清楚。

修复:

`MemoryGovernor.allows()` 只允许 `MemoryKind.FACT` 进入 Shared memory packet。

验证:

`test_memory_retriever_excludes_experience_from_shared_memory_packet` 已覆盖。

### 5.3 发现的问题 3:记忆召回不能被宣传成“读心”

在无限城 case 中,如果任务只写:

```text
/ask scout prepare the first raid plan
```

记忆 claim 是:

```text
preserve last known safe exits
```

这时召回不稳定,因为 query 和记忆没有足够明确的关联。

修正后的任务是:

```text
/ask scout prepare the first raid plan using safe exits
```

结论:

AICO 现在能做“可解释召回”,但不能宣传成“无论你怎么说,它都知道你想召回哪条记忆”。这条边界已经写入 showcase 文档。

---

## 6. 当前不能证明的事

本次测试不能证明:

1. 真实 Telegram 手机端最终展示效果一定好看。本次主要是机器 E2E,不是手机截图验收。
2. AICO 能理解官方动漫剧情。本 case 使用原创化映射,验证的是 AICO 能力,不是动漫知识问答。
3. `/dream` 能从任意自然语言里推理复杂人生经验。当前 dream 候选主要来自 task 状态信号,例如 approval blocked、failed、interrupted。
4. 协作 child task 会完整继承 project assignment metadata。当前可确认的是 audit source/target/parent trace,这已经足够证明协作审计,但不是完整组织图谱继承。

---

## 7. 宣传可用结论

可以宣传:

> AICO 可以把项目事实写进 Shared Memory,把任务阻塞复盘成 Dream Candidate,经确认后变成指定角色的 Reusable Experience,并把角色协作写入审计链。

不建议宣传:

> AICO 会自动理解所有动漫剧情,自动学会所有经验,自动召回所有上下文。

推荐中文标题:

```text
别等五十年后,才想起队友说过什么。
```

```text
如果无限变化的城里没有共享记忆,团队只会反复迷路。
```

推荐证明句:

```text
这不是概念视频:我们用机器 E2E 跑通了 shared memory 注入、dream candidate、experience promote、reviewer child task 和 collaboration audit。
```

---

## 8. 后续优化建议

1. **真实 IM dogfood**:把两个 showcase 做成临时 project config,在 Telegram 中跑 4-6 条命令,用 `/view` 附件展示 Memory / Experience / Audit 证据。
2. **召回解释**:在 `/recall` 或 `/why` 中补“为什么召回这条记忆/为什么没召回”,让宣传 case 更可信。
3. **协作 metadata 丰富化**:collaboration child task 可考虑保留 project assignment metadata,让 `/task` 和 `/view` 展示更完整组织上下文。
4. **宣传素材原创化**:公开物料使用原创“长记忆旅队”和“变化城堡作战室”视觉,不要使用官方动漫截图、Logo 或角色台词。
