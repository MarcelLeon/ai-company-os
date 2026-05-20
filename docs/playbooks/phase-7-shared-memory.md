# Playbook: Phase 7 Shared Memory

## 适用场景

用于 Phase 7 共享记忆层的实现和验收。目标是让同一项目下的多个 AI 能看到同一组可审计事实,
而不是依赖各自 Provider 的私有 session 记忆。

## 前置条件

- Phase 6 已收口:`/metrics`、audit replay、`aico-metrics`、`aico-glance` 均通过本地验收。
- 已阅读 ADR-0020。
- 不引入向量库或数据库作为第一切片。

## 第一切片范围

### 产品基调

Phase 7 的记忆层不是让老板高频维护 `/remember`、`/recall`、`/forget`。
这些命令必须存在,但主要定位是纠错、补充、排障和验收入口。日常大比例触发应来自 agent:

- agent 在任务完成、项目交接、风险确认、日报/周报沉淀时主动写入稳定事实。
- agent 在接到项目任务前自动召回当前项目少量高置信记忆。
- 老板通过自然的项目管理命令指挥团队,不需要为了每个任务先手动记忆或召回。
- 所有 agent 写入都必须带 source、created_by、confidence 和写入理由,避免黑箱自动记忆。

### A2A Memory Fabric 基调

按 ADR-0022,Phase 7 的记忆层必须能服务 lead agent 与 team agent 的 A2A 协作:

- A2A 子任务必须带 project 或 team 作用域,不能创建无归属的共享记忆。
- boss 会话完成后要能抽取候选记忆,并由 LLM 判断它属于 boss global、project、team、role 还是 agent working memory。
- 重要记忆可以通过统一 `MemoryBroadcast` 广播到 team,老板显式开会和 agent 自发共识走同一底层机制。
- 允许试验用 memory refs + MemoryPacket 减少 A2A 长消息传递,但必须保留 citations,且不能越过治理策略。

1. 新增 `MemoryAtom` 模型:
   - `memory_id`
   - `claim`
   - `evidence`
   - `scope`: `boss` / `project` / `team` / `role` / `agent`
   - `tags`
   - `source`
   - `confidence`
   - `created_by`
   - `created_at`
   - `archived_at`
   - `ttl`
   - `sensitivity`
   - `status`: `candidate` / `active` / `archived` / `superseded`
2. 新增 `MemoryStore` 接口:
   - `append(record)`
   - `list(project_id, include_archived=False)`
   - `search(project_id, query)`
   - `archive(memory_id)`
3. 新增 `JsonlMemoryStore`:
   - 配置 `AICO_MEMORY_PATH` 后写入 JSONL。
   - 默认无持久化配置时不启用共享记忆,现有任务行为保持不变。
4. 新增 IM 命令:
   - `/remember <text>`
   - `/recall [query]`
   - `/forget <memory_id>`
5. 新增 A2A Memory Fabric 触发边界:
   - 任务完成后可把稳定项目事实写入 memory store。
   - 项目报告/交接时可写入高置信结论,但不能把临时推测当事实。
   - A2A 子任务发起前自动召回当前 project/team/role 的 `MemoryPacket`。
   - boss feedback 会话结束后进入记忆抽取,由 LLM 判断 scope。
   - 重要 team 共识通过 `MemoryBroadcast` 写入并生成 receipt。
   - 写入必须可审计,并能通过 `/recall` 查看、通过 `/forget` 归档。
6. Prompt Stack 只注入当前项目的少量高置信记忆。

## 5 个迭代内的落地路线

### Iteration 1 — 记忆领域模型与 JSONL 权威源

目标:让 AICO 拥有可审计、可恢复、可检索的最小 Memory Fabric 内核。

TDD 验收:
- `MemoryAtom` 必须包含 claim、evidence、scope、confidence、created_by、ttl、sensitivity 和 status。
- 非 boss 记忆必须绑定 project 或 team 作用域;A2A 子任务相关记忆不能无 project/team 归属。
- `JsonlMemoryStore` append 后能 list/search/archive,重启后能从 JSONL 恢复。
- search 使用可插拔 `MemorySemanticScorer`:默认本地 semantic scorer 支持中文长句和常见中英项目术语,后续可替换为 embedding / LLM rerank。

### Iteration 2 — Prompt Stack 自动召回

目标:老板自然发项目命令时,lead agent 和目标 role 自动收到当前 project/team/role 的少量高置信记忆。

TDD 验收:
- `/ask <role> ...` 生成的 task prompt 包含 governed `MemoryPacket`。
- 目标 agent 只能看到同 project/team 下允许披露的记忆。
- `/forget` 归档后的记忆不再注入 prompt stack。

### Iteration 3 — IM 控制入口

目标:把 `/remember`、`/recall`、`/forget` 做成老板纠错/排障入口,而不是主工作流。

TDD 验收:
- `/remember <text>` 写入当前 project/team scope,返回短 id、scope 和 Next。
- `/recall [query]` 展示 claim、scope、confidence、source 和 evidence 摘要。
- `/forget <memory_id>` 只归档,不物理删除 JSONL 历史。
- 配置 `AICO_MEMORY_PATH` 后,`aico-phase1` runtime 使用同一 `JsonlMemoryStore`
  供命令和 Prompt Stack 自动召回复用。

### Iteration 4 — Boss Feedback 抽取与候选记忆

目标:boss 对话结束或任务完成后,agent 能识别偏好/feedback 并给出记忆层级。

TDD 验收:
- boss 明确偏好会被抽取为 boss global 或 project memory。
- scope 不确定或置信度不足时进入 `candidate`,不直接影响 prompt stack。
- `/recall` 能看到 candidate 的 reason,方便老板或 lead 确认。
- Orchestrator 在非命令老板消息路由前自动 capture;命令入口不重复抽取。
- project task prompt 可按 query 召回 boss global 偏好。

### Iteration 5 — Team Broadcast 与 A2A Token-saving 实验

目标:重要共识能广播给同 team agent,并试验用 memory refs 减少 A2A 长消息。

TDD 验收:
- `MemoryBroadcast` 写入 `broadcast_to` edge,并为 team appointment 生成 receipt。
- `MemoryBroadcast` 同步写入 `memory_broadcasted` 审计事件,detail 中包含 receipt、source memory、broadcast memory、team scope、recipients 和 reason。
- 同 team agent 后续任务自动召回广播共识。
- A2A 子任务可传 `memory_refs + delta`,目标 agent 召回 governed `MemoryPacket`。
- token-saving 模式必须可关闭;召回失败时回退显式消息传递。
- 第一版先落内部 service 和 payload builder;不把 broadcast 做成老板必须手动操作的主命令。

### Iteration 6 — 可解释记忆检索契约

目标:让 `/recall`、Prompt Stack 和后续 A2A memory refs 使用同一套检索契约,并能解释“为什么召回”。

TDD 验收:
- `MemoryRetrievalQuery` 统一承载 query、scopes、role、agent、task kind、top_k 和 token budget。
- `MemoryRetriever.retrieve()` 返回 `MemoryRetrievalHit`,包含 semantic/scope/recency/confidence/evidence/graph/final score。
- `MemoryRetriever.retrieve_packet()` 只负责把 governed hits 投影为 `MemoryPacket`,不再单独维护另一套排序。
- `/recall` 展示 reason,用于老板纠错和 agent 排障。
- role / agent scope 记忆在同等语义匹配下优先于 project scope。
- token budget 生效,过长记忆不会挤掉更紧凑的高相关记忆。
- candidate、archived、restricted 和跨 project 记忆仍不能因为分数高进入普通 prompt。

### Iteration 7 — Graph expansion 与 task-aware 召回

目标:让检索能利用已沉淀的 memory graph 和 role/task 上下文,同时保持一跳、同 scope、可解释。

TDD 验收:
- `supports` / `derived_from` / `broadcast_to` graph 邻居可被一跳召回。
- graph 邻居必须已经在本次 allowed scopes 中,不能跨 project / team 泄漏。
- `role_id` / `agent_id` / `task_kind` 会作为 query hints 参与 semantic scoring。
- tester / reviewer / release-manager 能更优先召回 test / review / release 相关记忆。
- `/recall` 展示 final / semantic / scope / graph score 分项,方便真实 IM 验收。

## 验收

### 本地单测

```bash
uv run pytest tests/unit/test_phase7_memory_acceptance.py
uv run pytest tests/unit/test_memory.py tests/unit/test_orchestrator.py
uv run ruff check .
uv run ruff format --check .
uv run mypy src tests
git diff --check
```

预期:
- `/remember` 不调用 provider,只写 AICO memory store。
- `/recall` 可列出当前项目记忆。
- `/forget` 只归档,不物理删除 JSONL 历史。
- 重启后从 `AICO_MEMORY_PATH` 恢复记忆。
- Prompt Stack 中只出现当前项目相关记忆。
- agent 执行项目任务时可以自动召回当前项目少量高置信记忆,老板不需要先手动 `/recall`。
- agent 自动写入记忆时必须保留来源、操作者和写入理由,并能被 `/recall` 检查。
- A2A 子任务创建时必须带 project/team scope,且目标 agent 只能收到 MemoryGovernor 投影后的 `MemoryPacket`。
- boss feedback 抽取时能区分 boss global 与 project/team memory;低置信结果进入 candidate。
- candidate boss feedback 不进入 Prompt Stack,直到后续确认或升格。
- team broadcast 后,同 team 下其它 agent 后续任务能自动召回该共识。
- team broadcast 后,`/audit` 或 `AICO_AUDIT_LOG_PATH` JSONL 中能追踪 `memory_broadcasted` 事件和 receipt id。
- A2A `memory_refs + delta` 只是可关闭优化;没有 refs 时仍发送完整显式 payload。

### 企业/团队管理验收场景

`tests/unit/test_phase7_memory_acceptance.py` 是 Phase 7 的收口验收流,要覆盖老板管理小中型项目时最常见的团队协作问题:

1. 项目事实沉淀:合同、法务、交付检查点这类项目规则可用 `/remember` 或后续 agent 自动写入进入 project memory。
2. 跨项目隔离:Payroll / HR 等其它项目记忆不会进入 AICO project prompt。
3. 老板偏好:老板说“我更喜欢汇报进度时告诉我还有几阶段”后,后续项目任务可自动召回 boss global 偏好。
4. 不确定反馈:老板说“可能/暂时/先看看”时写入 candidate,但不注入 Prompt Stack。
5. 团队共识:lead agent 把重要项目记忆 broadcast 到 team 后,QA / implementation 等同 team 后续任务可自动看到共识,且 audit 里能看到 `memory_broadcasted` 事件。
6. 重启恢复:使用同一 `AICO_MEMORY_PATH` 重新创建 `JsonlMemoryStore` 后,project/team memory 和 edge receipt 仍可恢复。
7. A2A token-saving:有 refs 时可发送 `memory_refs + delta`;无 refs 或关闭时回退完整显式 payload。

这条验收流故意不要求老板反复 `/recall`;老板只需要正常管理项目,记忆召回应由 agent 和 Prompt Stack 自动完成。

### IM 体感验收

```text
/project aico
/remember Phase 7 first slice is auditable project memory.
/recall phase 7
/forget <memory_id>
/recall phase 7
```

预期:
- `/remember` 返回短 id 和当前项目。
- `/recall` 能看到刚写入的事实。
- `/forget` 后默认 `/recall` 不再展示该事实。
- 所有命令都给出短 `Next:`。
- 用 `/ask <role> <task>` 等自然项目命令执行后,agent 能使用当前项目记忆,不要求老板手动维护记忆上下文。
- 用会议/广播入口显式发布 team 共识后,后续 `/ask <role> ...` 能体现这条共识。
- 语义检索仍先做 scope 过滤和 MemoryGovernor 投影;不要为了召回效果绕过 project/team 隔离、candidate 或 sensitivity 策略。
- `/recall <query>` 输出应包含 reason,能解释 semantic match、scope、sensitivity 和 confidence。
- `/recall <query>` 输出应包含 score 分项,能看到 final / semantic / scope / graph 对排序的贡献。

## 失败排查

- 如果记忆串项目,检查 `project_id` 是否来自 active project,不要默认全局共享。
- 如果 `/recall` 返回太多,先限制当前项目和未归档记忆,再做排序。
- 如果 Prompt Stack 过长,降低注入条数;不要把完整 memory JSON 塞进 prompt。
- 如果产品流要求老板频繁手动 `/remember` 或 `/recall`,说明实现偏离 ADR-0021,应把触发点移回 agent 任务链路。
- 如果 A2A 子任务没有 project/team scope,说明实现偏离 ADR-0022,应拒绝写入共享记忆或降级为 agent working memory。
- 如果 memory refs 导致目标 agent 召回不到必要上下文,回退到显式消息传递;token-saving 是实验,不能牺牲任务成功率。
- 如果需要语义搜索,先记录需求,不要在第一切片直接引入向量库。

## 相关

- ADR-0020
- ADR-0021
- ADR-0022
- ROUNDS Round 74
- ROUNDS Round 75
- ROUNDS Round 76
- ROUNDS Round 77
- ROUNDS Round 78
- ROUNDS Round 79
