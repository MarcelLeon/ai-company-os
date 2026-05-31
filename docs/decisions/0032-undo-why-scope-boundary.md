# ADR-0032: /undo and /why scope boundary (A2)

**状态**:Accepted
**日期**:2026-05-31
**决策者**:Wang / Claude
**相关 Round**:Round 132
**相关文档**:[`docs/architecture/boss-first-grounding.md`](../architecture/boss-first-grounding.md) §3.2

---

## 背景与问题

`boss-first-grounding.md` §1 痛点 P5 是 "Rollback 边界不清,撤销语义会被无限放大"。一旦上 `/undo`,用户会迅速期望它能撤掉 task 已经写到磁盘的文件、已经跑过的 shell 命令、已经发到群里的 IM 消息——这三件事归 git、文件系统、IM 平台管,AICO 撤不了,但**如果文档没写死边界,用户会认为撤了**。

同样的边界问题对 `/why` 也存在:用户会期望 `/why` 能解释任何 IM 输出"为什么"是这样,但 AICO 真正能解释的只是 AICO 自己创建过的事件(audit / memory / task state)。

## 候选方案

### 方案 A — 让 `/undo` 尽量靠近用户直觉,允许它"提示" git rollback / IM 撤回
- 优点:用户体验"看起来" 一致。
- 缺点:责任边界模糊,失败模式无限多(git 有冲突? IM 平台已超过撤回时限?);第一次用户以为"撤了" 但实际没撤,就是一次绕过审批/审计的事故。
- 复杂度:中。

### 方案 B — `/undo` 严格只撤 AICO 内部状态,**在每次回复里都写明边界**
- 优点:边界写在产品语言里,用户每次操作都被提醒;失败模式可枚举;符合 NORTH_STAR 第三句"可审、可撤、可溯,但不能 YOLO"。
- 缺点:用户会问"为什么不撤文件"——但这是产品诚实,不是产品缺陷。
- 复杂度:低。

### 方案 C — 不提供 `/undo`,只提供 `/rollback memory <id>` 之类显式精细命令
- 优点:无歧义。
- 缺点:违反 boss-first(老板要记 ID + 记命令);把锅推给老板。
- 复杂度:低。

## 决策

选择 **方案 B:`/undo` 严格只撤 AICO 内部状态,边界写在每个回复里**。

### 关键边界(必须出现在 `/undo` 每次回复里)

✅ **可撤**(AICO 内部状态):
- `memory.append_atom` —— 老板刚 `/remember` 写下的 fact memory
- `memory.archive` —— 老板刚 `/forget` 的 fact memory
- `experience.promote` —— lead 刚把 candidate 推到 active 的 experience
- (未来)`appointment` 任命变更

❌ **不可撤**(AICO 外部副作用):
- 已经写到磁盘的文件 → git 管
- 已经跑过的 shell 命令 → 操作系统管(已发生即不可逆)
- 已经发出去的 IM 消息 → IM 平台管(Telegram 有 48h 限制等)
- 已经触发的 webhook 调用 → 远端服务管

### `/undo` 的"反向"语义

撤销不是物理回退,而是**写一条新的反向事件**:
- promote → CANDIDATE 时,append 一个新版本 atom(status=CANDIDATE)
- archive → ACTIVE 时,append 一个新版本 atom(status=ACTIVE,clear archived_at/reason)
- append → archive 时,调 `store.archive(reason="boss /undo")`

老的事件保留在 JSONL 中,审计链不丢。

### `/why` 的查询语义

- `/why <short_id>` — 在 UnifiedEventIndex 中前缀匹配 trace_id / short_id / event_id,返回整条 trace 的事件序列(oldest first)
- `/why`(无参) — 返回最近一条事件所在 trace 的全部事件
- 找不到任何匹配时,回复 "no events found" + 用法提示,**不返回错误**

### 该 sprint 不做的事(明确范围边界)

- ❌ `/rollback memory|experience|task <id>` 精细命令(留 A3)
- ❌ aico-view Web UI(留 V1/V2)
- ❌ `/why <reply-to-message>` 隐式 reply 解析:IncomingMessage 当前没有 reply 元数据,需要 channel 层先扩展,**留作后续**
- ❌ 全面拆分 Orchestrator 类(类规模渐增,记入 BLOCKER B-005,留后续重构)

## 结果

- 新增 `src/aico/core/undo_why_commands.py`(< 280 行):`UndoCommandHandler` + `WhyCommandHandler`。
- 新增 `src/aico/core/orchestrator.py` 中 `_build_event_index` 方法 + 模块级 helper `_build_orchestrator_event_index`(派生只读 UnifiedEventIndex)。
- `inbox_message` / `morning_message` 接受可选 `recent_events`,在标准段后追加 "Recent activity" 摘要 + 一行 `/why <short_id>` 提示。
- `CommandName` 加 `UNDO` / `WHY`;`/undo` 进 lowered 短命令集;help_text 加两行。
- `Orchestrator.__init__` 拆出 `_setup_command_handlers` → `_setup_coordinators` / `_setup_boss_and_lead_handlers` / `_setup_workflow_handlers` 三个子方法,确保每个方法 <100 行(类总规模仍然超 500,记入 BLOCKER B-005)。
- 新增测试 `tests/unit/test_undo_why_commands.py`(5 用例,覆盖 nothing-to-undo / 撤 promote / 撤 fact append / why 空 / why 短 ID)。
- CHANGELOG 加 `/undo` `/why` 说明。

## 后续相关 ADR / Sprint

- A3 sprint:`/rollback memory|experience|task <id>` 精细操作 + ADR-0034 边界细化。
- V1 sprint:aico-view 三视图直接读 UnifiedEventIndex。
- 独立重构 sprint:Orchestrator 类拆分(见 BLOCKER B-005)。
- 未来:channel 层加 reply-to-message 元数据,`/why` 可以隐式从被 reply 的消息取 short_id。
