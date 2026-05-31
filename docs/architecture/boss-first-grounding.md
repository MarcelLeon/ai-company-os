# Boss-First Grounding — 痛点、分层与近期基础加固设计

> 本文档是 AICO 一次"对自己实事求是"的总结。
>
> 它来自 2026-05-28 / 2026-05-29 与人类老板的两轮脑暴,目的是:
>
> 1. 把项目当前真实痛点写下来(基于源码核实,不是凭印象);
> 2. 把"近期高优:Memory + Experience、Audit + Rollback、Absence Loop"三块基础能力的设计统一沉淀;
> 3. 把跨层架构画清楚,让所有 agent(人类 / AI)接手时不需要重新拼图;
> 4. 把暂不实现但已经讨论过的方向标记为 Future,避免再被反复提案。
>
> **本文档不替代 NORTH_STAR / STATUS / ADR**。当本文和 ADR 冲突时,以 ADR 为准并提 PR 修订本文。

---

## 0. 阅读指引

| 你是谁 | 怎么读 |
|---|---|
| 第一次接手的 agent | 顺序读 §1 → §2 → §3 → §6,跳过 §4/§5(实现细节) |
| 即将落地某个 sprint | 直接读 §4 对应 sprint 切片 + §5 落地路线图 |
| 老板 / 产品视角 | 只读 §1 + §3.4 + §6 |
| 准备改架构图 | §5 嵌入了完整 drawio xml,复制到 https://app.diagrams.net 即可编辑 |

---

## 1. 真实痛点(实事求是,基于代码核实)

> 每条痛点都标注了"事实依据"(可在仓库中验证),不是空对空。

### P1:老板命令爆炸 — 视觉负担超过"管团队"承诺

**事实**:`src/aico/core/commands.py` 中 `CommandName` 枚举已经定义了 **46 个内置命令**(`/help` 到 `/interrupt`)。其中大多数是 lead/role 内务(`/appoint`、`/unappoint`、`/skills`、`/tools`、`/sessions`、`/bind` 等),但老板在 Telegram 里看到的是平铺的命令面板。

**为什么是痛点**:NORTH_STAR 第一句要求"像管理一个真实团队一样"。真实老板**不会记 46 个命令**——他只会喊"做了没?为什么?撤掉。"。AICO 把"lead 的内务工具"和"老板的核心动作"塞在同一个命令空间,违背了 boss-first。

### P2:lead 没有"主动机制" — 完全依赖老板先开口

**事实**:所有 task 入口都来自 IM 命令解析(`Router` → `TaskBus`)。仓库里没有任何时间触发 / 事件触发 / 阻塞超时触发的 trigger 模块——`grep -rn "cron\|schedule\|trigger" src/aico/core/` 只出现在测试和文档里。

**为什么是痛点**:absence-first 当前只解决了"老板下指令的异步化",没解决"老板根本不开口的那段时间"。Lead 在老板沉默时无法基于职责主动推进,即使他知道 blocker 已经躺了 3 天。

### P3:Memory 没有 Experience 维度 — 经验等于事实

**事实**:`MemoryAtom`(`src/aico/core/memory.py:143`)的维度是 `purpose_tags`(GENERAL_CONTEXT / PUBLIC_BROADCAST / TASK_KEY_PROGRESS / TASK_PRIVATE / DECISION_REVIEW)+ `scope` + `sensitivity` + `confidence`。**没有 `kind=experience` 字段,没有"被注入哪个 role prompt"的 trigger,没有"被注入后效果如何"的回写链路**。

`/dream`(`src/aico/core/dream.py`)生成的 candidate memory 是普通 atom,不会自动进入 role system prompt,也不会随 Grader verdict 修正 confidence。

**为什么是痛点**:Role 当前只带通用岗位 prompt + 老板手写的项目记忆。"做过的活、踩过的坑"散落在 task snapshots 里,新接班的 role 从零开始。

### P4:Audit 在 IM 内的表达上限低 — trace 糊成一团

**事实**:`InMemoryAuditLog`(`src/aico/core/audit.py:46`)以 `AuditEvent` 为单位写 JSONL,事件之间没有 `trace_id` 串联(只有 `task_id`);memory 写入和 audit 写入是独立链路;`/audit` 命令的输出是文本行。

**为什么是痛点**:老板想问"昨晚那个 PR 是怎么来的",当前需要在 `/tasks`、`/audit`、`/recall` 三个命令之间手动拼接 ID。IM 文本框对树状/时序结构有天然表达上限。

### P5:Rollback 边界不清 — 撤销语义会被无限放大

**事实**:仓库当前**没有 `/rollback` 命令**(`grep -n "ROLLBACK\|rollback" src/aico/core/commands.py` 无结果)。已有的"逆向操作"是 memory 的 `archive(reason)`(`memory.py:333`)和 task 的 `/interrupt`,二者不构成完整撤销语义。

**为什么是痛点**:一旦上 `/rollback`,如果不写死"能撤什么 / 不能撤什么",用户期望会迅速膨胀到"撤掉 task 已经写到磁盘 / 已经跑过的 shell"——这两件事归 git 和文件系统管,AICO 撤不了,但用户会以为撤了。

### P6:Phase 8 自己 dogfood 效果不佳 — 项目对自己最严的判罚

**事实**:STATUS.md Round 126(2026-05-27)明确写:"Phase 8 Absence Loop 真实 IM dogfood 已由人类执行;**效果不佳且暂不继续投入 native output 方向**,当前 dogfood 使用 `AICO_PREFER_NATIVE_CHANNEL_FORMAT=false`"。STATUS.md 第 291-292 行的"多 step / 多 agent 夜间自动编排"和"早报自动生成或定时推送"仍是 `[ ]`。

**为什么是痛点**:NORTH_STAR 第三句"Dogfooding 是唯一的验收标准"。Phase 8 是 absence-first 的兑现入口,但项目自己没用顺。根因推测(待验证):**经验没复用 + 留痕不可视,导致老板早上不敢直接接手 AI 跑过的结果**——这正是 §2 三块基础能力要解决的。

---

## 2. 解法总览(痛点 → 分层 → 命令归属)

| 痛点 | 解法 | 命令归属 |
|---|---|---|
| P1 命令爆炸 | **命令分层**:boss / lead / role / harness 四档,老板只看 6 个核心动作 | §3.4 |
| P2 lead 不主动 | **延后做**:Lead Standing Charter + Proposal Queue(Future F-1) | §6 |
| P3 经验等于事实 | **Memory 与 Experience 分层**:同存储不同 kind,Experience 才会按 trigger 注入 role prompt | §3.1 |
| P4 audit 糊 | **统一 trace_id 事件流**;IM 侧只暴露 `/why`,深度查询走 aico-view | §3.2 + §3.3 |
| P5 rollback 边界不清 | **/undo 智能撤销**,语义边界写死:**只撤 AICO 内部状态(memory/experience/assignment),不撤 git/shell/file** | §3.2 |
| P6 Phase 8 dogfood 不顺 | **基础三件先做强**(Memory+Experience / Audit+Rollback / aico-view),再回到 Phase 8 完善 | §5 |

**贯穿原则**:
- **Boss-first + Absence-first**:老板手机/地铁/床上可用,写操作收口于 IM,只读视图收口于 aico-view。
- **写在 IM、看在 Web**:IM 是命令面,Web 是展示面;老板不切换工具做决策。
- **每个新机制必须能审、能撤、能溯**:不增加无法回滚的能力。

---

## 3. 三块基础能力 + aico-view 详细设计

### 3.1 Memory + Experience 分层 (Priority 1)

**核心区分**:

| | Memory(事实) | Experience(经验) |
|---|---|---|
| 来源 | `/remember`、agent 写入、`/dream` candidate | 由 Memory 经审批晋升 |
| 是否注入 prompt | **默认否**,按 retrieval 召回 | **是**,按 role + trigger 自动注入 system prompt |
| 生命周期 | active / archived | candidate → reviewed → active → archived |
| 治理 | scope / purpose / sensitivity / confidence | 同上 + applies_to + trigger + injection_history |

**数据模型新增**(对 `MemoryAtom` 的最小扩展,不另起一张表):
- `kind: MemoryKind = "fact" | "experience"`(默认 fact,与现有 `purpose_tags` 正交)
- `experience: ExperienceMeta | None`:
  - `applies_to`: 哪些 role(`tuple[RoleId, ...]`)
  - `triggers`: 哪些条件下注入(goal 包含 X / task type Y / risk capability Z)
  - `injection_count`: 累计注入次数
  - `verdict_hits` / `verdict_misses`: Grader 反馈
  - `lifecycle_state`: candidate / reviewed / active / archived

**新命令**(全部归 **lead 内务**,老板不直接用):
- `/experience review` — 审批 candidate(`/dream` 输出落到这里)
- `/experience list [role]` — 查看 active experience
- `/experience archive <short_id>` — 主动失效

**Sprint 切片**:
- **M1**:数据模型扩展 + `/dream` 输出改写为 `kind=experience, lifecycle=candidate`
- **M2**:`/experience review|list|archive` + role prompt 条件注入(在现有 `prompt_stack.py` 内加一层 ExperienceLayer)
- **M3**:Grader verdict → confidence + verdict_hits 回写;按 confidence 排序

### 3.2 Audit + Rollback(IM 侧极简版) (Priority 2)

**核心理念**:IM 不承担深度可视化,只承担"老板想问一句的 6 秒动作"。深度可视化走 aico-view(§3.3)。

**统一 trace_id 事件流**:
- 新增 `unified_event` 索引层,**不动现有 JSONL**(audit / memory / task state 仍各自写,只增加跨源 event_id 索引和 trace_id 串联)
- 一个 task 的所有副作用(prompt 注入 → 子任务 → memory 写入 → approval → grader verdict)共享同一 `trace_id`

**短 ID 改造**:全系统 ID 在 IM 内显示为 `mem#a3f` / `tsk#b7c` / `exp#d2e`,7 位短哈希,IM 内可读,Web 内点击展开全 ID。

**老板核心命令(只 2 个新命令)**:
- `/undo` — 智能撤销上一步,自动识别"最近的 AICO 内部状态变更",不需要老板手输 ID
- `/why <在 IM 中引用某条消息>` — 反向追溯该消息的 trace,返回简短文字摘要 + aico-view 深度链接

**`/undo` 语义边界(必须在文档和命令帮助里写死)**:
- ✅ 可撤:memory 写入 / experience 状态变更 / appointment 任命 / dream candidate 生成
- ❌ 不可撤:已经写到磁盘的文件、已经跑过的 shell 命令、已经发出去的 IM 消息(归 git/文件系统/IM 平台管)
- 撤销本身是一条新事件,不是物理回退;原事件保留可查

**lead 内务命令**:
- `/timeline --since 24h --role <id>` — 细粒度时间线过滤
- `/rollback memory|experience|task <short_id>` — 精细撤销(老板平时不碰)

**Sprint 切片**:
- **A1**:统一 event stream + trace_id 串联 + 短 ID 改造
- **A2**(老板线):`/undo` + `/why` + `/morning` 和 `/inbox` 内嵌 timeline 摘要
- **A3**(lead 线):`/timeline`、`/rollback` 精细操作 + 边界文档

### 3.3 aico-view — Mobile-friendly Read-only Web (Priority 2,与 A3 并行)

**为什么不破 absence-first**:NORTH_STAR 原文是"无论身处何地""老板不在 Mac 前",**没有禁止可视化**。手机网页正好契合 absence-first(地铁、饭桌、床上都能看)。

**严格边界**:
- **只读**。所有写操作回到 IM。
- **只在已登录的老板设备上可访问**(MVP 阶段用本地 token + ngrok 风格隧道,不上公网鉴权)。
- **不替代 IM**。aico-view 的每个视图都有"回 IM 操作"按钮,通过 `tg://resolve?...&text=/undo` 深度链接跳回 Telegram 预填命令。

**三个视图**:
1. **Timeline** — 按项目 / 角色 / 时间过滤的事件流
2. **Task Trace** — 单 task 的全貌:输入 prompt → 注入了哪些 memory/experience → 输出 → 触发了哪些 approval → grader verdict
3. **Memory Tree** — memory 与 experience 的关系图(`derived_from` / `supersedes` / `contradicts`)

**Sprint 切片**:
- **V1**:最小 FastAPI 服务 + 三视图 read-only(直接读 unified_event 索引)
- **V2**:Telegram deep link 回 IM 命令预填
- **V3**:本地 token 鉴权 + ngrok 风格隧道部署文档

### 3.4 命令分层(P1 痛点直接解法,不需要新 sprint)

**boss-only(6 个核心动作)**:
- `/ask`(下任务)
- `/approve` / `/reject`(审危险)
- `/interrupt`(叫停)
- `/morning`(早上接手)
- `/inbox`(看待办,内含 First action)
- `/why`(问一句为什么)+ `/undo`(撤错的)

**lead 内务**:`/appoint`、`/lead`、`/team`、`/experience *`、`/timeline`、`/rollback`、`/sessions`、`/bind`...

**role 内务**:`/skills`、`/tools`、`/use`...

**实现方式**:不删命令,**在 `/help` 输出时按受众分组**;老板查看 `/help` 时默认只显示 boss-only 6 项,`/help all` 才展开全部。这是零代码风险的渐进改造。

### 3.5 Absence Loop 加固 (Priority 3,等 Memory+Experience 和 Audit+Rollback 完成)

不在本文细化 sprint,只确认方向:
- 多 step / 多 agent 夜间自动编排(STATUS 291 行)
- 早报自动生成或定时推送(STATUS 292 行)
- 基于 Experience 注入,让 lead 夜间任务自动用上历史经验
- `/morning` 拼 `/timeline --since overnight` + 深度链接到 aico-view

等 §3.1 + §3.2 + §3.3 落地后,回到 Phase 8 dogfood 验证根因是否被解决。

---

## 4. 未来方向(暂不实现,只记录)

### Future F-1:Lead Self-Driving / Standing Charter

让 lead 在三种触发条件下生成 proposal(blocker 超期 / charter 项无进展 / memory 中有未到期承诺),只写入 inbox 不创建 task。老板 `/accept` 后才进入正式 task 链路;`/reject` 写入 negative memory。

**前置依赖**:§3 全部完成 + Phase 8 dogfood 跑通。
**触发北极星修订**:需要明确"lead 提议权 vs 老板决策权",这件事要新开 ADR。

### Future F-2:Team-level Karpathy Loop / AutoResearch

`/dream` 作为团队级自我进化入口的论点延伸。

**差异化论点(待验证)**:单 agent + self-evolving skill 缺少**协作纠错维度**;AICO 的 **team + lead + experience + memory** 多了两个维度——经验跨任务复用 + lead 仲裁防单点漂移。这是值得验证的产品论点,但**必须在 absence loop 真正稳之后做**,否则就是在不稳之上叠不稳。

---

## 5. 分层架构图(drawio xml,嵌入式)

> 将下方 xml 整段复制到 https://app.diagrams.net 即可打开编辑。
>
> 偏底层在下、偏老板体验在上。绿色 = 已实现,黄色虚线 = 本文档新增/规划,蓝色 = 老板/外部世界。

```xml
<mxfile host="app.diagrams.net" modified="2026-05-29T00:00:00.000Z" agent="Claude" version="24.7.17">
  <diagram id="boss-first-grounding" name="Boss-First Grounding">
    <mxGraphModel dx="1600" dy="1200" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1700" pageHeight="1400" math="0" shadow="0">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>

        <mxCell id="title" value="AICO Boss-First Grounding — Layered Architecture (2026-05-29)" style="text;html=1;strokeColor=none;fillColor=none;fontSize=22;fontStyle=1;align=left;fontColor=#111827;" vertex="1" parent="1">
          <mxGeometry x="40" y="20" width="1100" height="36" as="geometry"/>
        </mxCell>
        <mxCell id="subtitle" value="Higher layers = boss-facing surfaces. Lower layers = LLM providers and protocols. Cross-layer arrows show what flows between." style="text;html=1;strokeColor=none;fillColor=none;fontSize=12;fontColor=#6B7280;" vertex="1" parent="1">
          <mxGeometry x="40" y="54" width="1500" height="20" as="geometry"/>
        </mxCell>

        <mxCell id="legendDone" value="Implemented" style="rounded=1;whiteSpace=wrap;html=1;arcSize=12;strokeColor=#0F766E;fillColor=#CCFBF1;fontSize=11;fontColor=#134E4A;" vertex="1" parent="1">
          <mxGeometry x="1220" y="22" width="120" height="24" as="geometry"/>
        </mxCell>
        <mxCell id="legendNew" value="Planned (this doc)" style="rounded=1;whiteSpace=wrap;html=1;arcSize=12;strokeColor=#B45309;fillColor=#FEF3C7;fontSize=11;fontColor=#78350F;dashed=1;" vertex="1" parent="1">
          <mxGeometry x="1350" y="22" width="140" height="24" as="geometry"/>
        </mxCell>
        <mxCell id="legendBoss" value="Boss / External" style="rounded=1;whiteSpace=wrap;html=1;arcSize=12;strokeColor=#1E40AF;fillColor=#DBEAFE;fontSize=11;fontColor=#1E3A8A;" vertex="1" parent="1">
          <mxGeometry x="1500" y="22" width="120" height="24" as="geometry"/>
        </mxCell>

        <mxCell id="L6" value="L6 — Boss Surfaces (write in IM, view in Web)" style="swimlane;html=1;rounded=0;startSize=30;fontStyle=1;fontSize=14;horizontal=1;fillColor=#EFF6FF;strokeColor=#2563EB;fontColor=#1E3A8A;" vertex="1" parent="1">
          <mxGeometry x="40" y="90" width="1620" height="140" as="geometry"/>
        </mxCell>
        <mxCell id="L6_boss" value="Human Boss&#10;(phone / metro / bed)" style="rounded=1;whiteSpace=wrap;html=1;arcSize=10;strokeColor=#1E40AF;fillColor=#DBEAFE;fontSize=12;fontColor=#1E3A8A;" vertex="1" parent="1">
          <mxGeometry x="80" y="135" width="200" height="70" as="geometry"/>
        </mxCell>
        <mxCell id="L6_im" value="IM write surface&#10;(Telegram / Feishu)&#10;6 boss commands:&#10;/ask /approve /reject&#10;/interrupt /morning /inbox&#10;/why /undo" style="rounded=1;whiteSpace=wrap;html=1;arcSize=10;strokeColor=#0F766E;fillColor=#CCFBF1;fontSize=11;fontColor=#134E4A;" vertex="1" parent="1">
          <mxGeometry x="320" y="125" width="280" height="95" as="geometry"/>
        </mxCell>
        <mxCell id="L6_view" value="aico-view&#10;(mobile read-only web)&#10;Timeline / Task Trace / Memory Tree&#10;→ deep link back to IM" style="rounded=1;whiteSpace=wrap;html=1;arcSize=10;strokeColor=#B45309;fillColor=#FEF3C7;fontSize=11;fontColor=#78350F;dashed=1;" vertex="1" parent="1">
          <mxGeometry x="640" y="125" width="280" height="95" as="geometry"/>
        </mxCell>
        <mxCell id="L6_lead_ui" value="Lead / Role internal commands&#10;/appoint /lead /team&#10;/experience review /timeline&#10;/rollback /sessions /bind ..." style="rounded=1;whiteSpace=wrap;html=1;arcSize=10;strokeColor=#0F766E;fillColor=#CCFBF1;fontSize=11;fontColor=#134E4A;" vertex="1" parent="1">
          <mxGeometry x="960" y="125" width="300" height="95" as="geometry"/>
        </mxCell>
        <mxCell id="L6_help" value="/help is grouped:&#10;default = boss-only&#10;/help all = full" style="rounded=1;whiteSpace=wrap;html=1;arcSize=10;strokeColor=#B45309;fillColor=#FEF3C7;fontSize=11;fontColor=#78350F;dashed=1;" vertex="1" parent="1">
          <mxGeometry x="1300" y="135" width="200" height="70" as="geometry"/>
        </mxCell>

        <mxCell id="L5" value="L5 — Application Semantics (Commands · Inbox · Morning · Why · Undo)" style="swimlane;html=1;rounded=0;startSize=30;fontStyle=1;fontSize=14;horizontal=1;fillColor=#ECFDF5;strokeColor=#059669;fontColor=#064E3B;" vertex="1" parent="1">
          <mxGeometry x="40" y="250" width="1620" height="140" as="geometry"/>
        </mxCell>
        <mxCell id="L5_cmd" value="Command parser&#10;(commands.py · 46 cmds)&#10;dispatched to handlers" style="rounded=1;whiteSpace=wrap;html=1;arcSize=10;strokeColor=#0F766E;fillColor=#CCFBF1;fontSize=11;fontColor=#134E4A;" vertex="1" parent="1">
          <mxGeometry x="80" y="290" width="220" height="80" as="geometry"/>
        </mxCell>
        <mxCell id="L5_inbox" value="/inbox · /morning · /daily&#10;First action rendering&#10;(actionable next-step)" style="rounded=1;whiteSpace=wrap;html=1;arcSize=10;strokeColor=#0F766E;fillColor=#CCFBF1;fontSize=11;fontColor=#134E4A;" vertex="1" parent="1">
          <mxGeometry x="320" y="290" width="220" height="80" as="geometry"/>
        </mxCell>
        <mxCell id="L5_why" value="/why · /undo&#10;trace_id resolver&#10;smart-undo scope guard" style="rounded=1;whiteSpace=wrap;html=1;arcSize=10;strokeColor=#B45309;fillColor=#FEF3C7;fontSize=11;fontColor=#78350F;dashed=1;" vertex="1" parent="1">
          <mxGeometry x="560" y="290" width="220" height="80" as="geometry"/>
        </mxCell>
        <mxCell id="L5_exp" value="/experience review|list|archive&#10;(candidate → active)&#10;Lead internal" style="rounded=1;whiteSpace=wrap;html=1;arcSize=10;strokeColor=#B45309;fillColor=#FEF3C7;fontSize=11;fontColor=#78350F;dashed=1;" vertex="1" parent="1">
          <mxGeometry x="800" y="290" width="240" height="80" as="geometry"/>
        </mxCell>
        <mxCell id="L5_rollback" value="/rollback memory|experience|task&#10;(strict scope: AICO state only,&#10;NOT git / shell / file)" style="rounded=1;whiteSpace=wrap;html=1;arcSize=10;strokeColor=#B45309;fillColor=#FEF3C7;fontSize=11;fontColor=#78350F;dashed=1;" vertex="1" parent="1">
          <mxGeometry x="1060" y="290" width="260" height="80" as="geometry"/>
        </mxCell>
        <mxCell id="L5_charter" value="(Future F-1) /charter · Proposal Queue&#10;Lead self-driving&#10;NOT in current sprint" style="rounded=1;whiteSpace=wrap;html=1;arcSize=10;strokeColor=#9CA3AF;fillColor=#F3F4F6;fontSize=11;fontColor=#374151;dashed=1;" vertex="1" parent="1">
          <mxGeometry x="1340" y="290" width="280" height="80" as="geometry"/>
        </mxCell>

        <mxCell id="L4" value="L4 — Orchestration Runtime (Router · TaskBus · Approval · Audit · EventBus)" style="swimlane;html=1;rounded=0;startSize=30;fontStyle=1;fontSize=14;horizontal=1;fillColor=#FEF3F2;strokeColor=#DC2626;fontColor=#7F1D1D;" vertex="1" parent="1">
          <mxGeometry x="40" y="410" width="1620" height="170" as="geometry"/>
        </mxCell>
        <mxCell id="L4_router" value="Router&#10;(commands → tasks)" style="rounded=1;whiteSpace=wrap;html=1;arcSize=10;strokeColor=#0F766E;fillColor=#CCFBF1;fontSize=11;fontColor=#134E4A;" vertex="1" parent="1">
          <mxGeometry x="80" y="455" width="180" height="60" as="geometry"/>
        </mxCell>
        <mxCell id="L4_taskbus" value="TaskBus + TaskStateRepository&#10;(SQLite persistent state)" style="rounded=1;whiteSpace=wrap;html=1;arcSize=10;strokeColor=#0F766E;fillColor=#CCFBF1;fontSize=11;fontColor=#134E4A;" vertex="1" parent="1">
          <mxGeometry x="280" y="455" width="220" height="60" as="geometry"/>
        </mxCell>
        <mxCell id="L4_approval" value="Approval gate&#10;(risk capability matrix)" style="rounded=1;whiteSpace=wrap;html=1;arcSize=10;strokeColor=#0F766E;fillColor=#CCFBF1;fontSize=11;fontColor=#134E4A;" vertex="1" parent="1">
          <mxGeometry x="520" y="455" width="180" height="60" as="geometry"/>
        </mxCell>
        <mxCell id="L4_audit" value="Audit JSONL + unified event index&#10;(trace_id, short_id)" style="rounded=1;whiteSpace=wrap;html=1;arcSize=10;strokeColor=#B45309;fillColor=#FEF3C7;fontSize=11;fontColor=#78350F;dashed=1;" vertex="1" parent="1">
          <mxGeometry x="720" y="455" width="240" height="60" as="geometry"/>
        </mxCell>
        <mxCell id="L4_grader" value="Outcome Grader&#10;(verdict → experience confidence)" style="rounded=1;whiteSpace=wrap;html=1;arcSize=10;strokeColor=#0F766E;fillColor=#CCFBF1;fontSize=11;fontColor=#134E4A;" vertex="1" parent="1">
          <mxGeometry x="980" y="455" width="240" height="60" as="geometry"/>
        </mxCell>
        <mxCell id="L4_eventbus" value="EventBus (state broadcast)" style="rounded=1;whiteSpace=wrap;html=1;arcSize=10;strokeColor=#0F766E;fillColor=#CCFBF1;fontSize=11;fontColor=#134E4A;" vertex="1" parent="1">
          <mxGeometry x="1240" y="455" width="220" height="60" as="geometry"/>
        </mxCell>
        <mxCell id="L4_dream" value="Dream candidate generator&#10;(task failures → experience candidates)" style="rounded=1;whiteSpace=wrap;html=1;arcSize=10;strokeColor=#0F766E;fillColor=#CCFBF1;fontSize=11;fontColor=#134E4A;" vertex="1" parent="1">
          <mxGeometry x="1480" y="455" width="180" height="60" as="geometry"/>
        </mxCell>

        <mxCell id="L3" value="L3 — Company Model · Memory + Experience Fabric · Project Assignment" style="swimlane;html=1;rounded=0;startSize=30;fontStyle=1;fontSize=14;horizontal=1;fillColor=#F5F3FF;strokeColor=#7C3AED;fontColor=#4C1D95;" vertex="1" parent="1">
          <mxGeometry x="40" y="600" width="1620" height="180" as="geometry"/>
        </mxCell>
        <mxCell id="L3_project" value="ProjectAssignmentDirectory&#10;(project · role · agent · appointment)" style="rounded=1;whiteSpace=wrap;html=1;arcSize=10;strokeColor=#0F766E;fillColor=#CCFBF1;fontSize=11;fontColor=#134E4A;" vertex="1" parent="1">
          <mxGeometry x="80" y="640" width="260" height="70" as="geometry"/>
        </mxCell>
        <mxCell id="L3_memory" value="MemoryFabric (kind=fact)&#10;atoms · edges · packets · broadcast&#10;scope / purpose / sensitivity / confidence" style="rounded=1;whiteSpace=wrap;html=1;arcSize=10;strokeColor=#0F766E;fillColor=#CCFBF1;fontSize=11;fontColor=#134E4A;" vertex="1" parent="1">
          <mxGeometry x="360" y="640" width="300" height="80" as="geometry"/>
        </mxCell>
        <mxCell id="L3_exp" value="ExperienceFabric (kind=experience)&#10;applies_to · triggers · lifecycle&#10;injection_history · verdict_hits" style="rounded=1;whiteSpace=wrap;html=1;arcSize=10;strokeColor=#B45309;fillColor=#FEF3C7;fontSize=11;fontColor=#78350F;dashed=1;" vertex="1" parent="1">
          <mxGeometry x="680" y="640" width="300" height="80" as="geometry"/>
        </mxCell>
        <mxCell id="L3_prompt" value="PromptStack&#10;base prompt + memory recall + ExperienceLayer&#10;(conditional injection by trigger)" style="rounded=1;whiteSpace=wrap;html=1;arcSize=10;strokeColor=#B45309;fillColor=#FEF3C7;fontSize=11;fontColor=#78350F;dashed=1;" vertex="1" parent="1">
          <mxGeometry x="1000" y="640" width="320" height="80" as="geometry"/>
        </mxCell>
        <mxCell id="L3_lead" value="Lead Decision · Goal Brief · Collaboration&#10;(challenger / reviewer / tester contracts)" style="rounded=1;whiteSpace=wrap;html=1;arcSize=10;strokeColor=#0F766E;fillColor=#CCFBF1;fontSize=11;fontColor=#134E4A;" vertex="1" parent="1">
          <mxGeometry x="1340" y="640" width="320" height="80" as="geometry"/>
        </mxCell>

        <mxCell id="L2" value="L2 — Protocol &amp; Adapter Boundary (AIAdapter · IMChannel)" style="swimlane;html=1;rounded=0;startSize=30;fontStyle=1;fontSize=14;horizontal=1;fillColor=#FFF7ED;strokeColor=#EA580C;fontColor=#7C2D12;" vertex="1" parent="1">
          <mxGeometry x="40" y="800" width="1620" height="130" as="geometry"/>
        </mxCell>
        <mxCell id="L2_aiadapter" value="AIAdapter protocol&#10;ClaudeCode · Codex · Cursor · CodeFlicker · Trae · Gemini&#10;capabilities: read_repo / code_edit / shell_exec / destructive" style="rounded=1;whiteSpace=wrap;html=1;arcSize=10;strokeColor=#0F766E;fillColor=#CCFBF1;fontSize=11;fontColor=#134E4A;" vertex="1" parent="1">
          <mxGeometry x="80" y="840" width="720" height="75" as="geometry"/>
        </mxCell>
        <mxCell id="L2_channel" value="IMChannel protocol&#10;Telegram (dogfooded) · Feishu (webhook ready, smoke test pending)&#10;platform-neutral render contract" style="rounded=1;whiteSpace=wrap;html=1;arcSize=10;strokeColor=#0F766E;fillColor=#CCFBF1;fontSize=11;fontColor=#134E4A;" vertex="1" parent="1">
          <mxGeometry x="820" y="840" width="600" height="75" as="geometry"/>
        </mxCell>
        <mxCell id="L2_view_api" value="aico-view read API&#10;(FastAPI, read-only)" style="rounded=1;whiteSpace=wrap;html=1;arcSize=10;strokeColor=#B45309;fillColor=#FEF3C7;fontSize=11;fontColor=#78350F;dashed=1;" vertex="1" parent="1">
          <mxGeometry x="1440" y="840" width="220" height="75" as="geometry"/>
        </mxCell>

        <mxCell id="L1" value="L1 — Local Providers / LLMs / Persistence (bottom layer per project convention)" style="swimlane;html=1;rounded=0;startSize=30;fontStyle=1;fontSize=14;horizontal=1;fillColor=#F9FAFB;strokeColor=#6B7280;fontColor=#374151;" vertex="1" parent="1">
          <mxGeometry x="40" y="950" width="1620" height="170" as="geometry"/>
        </mxCell>
        <mxCell id="L1_clis" value="Local AI CLIs (subprocess)&#10;claude · codex · cursor-agent · codeflicker · trae · gemini" style="rounded=1;whiteSpace=wrap;html=1;arcSize=10;strokeColor=#6B7280;fillColor=#F3F4F6;fontSize=11;fontColor=#374151;" vertex="1" parent="1">
          <mxGeometry x="80" y="995" width="500" height="65" as="geometry"/>
        </mxCell>
        <mxCell id="L1_llm" value="Underlying LLM APIs&#10;Anthropic · OpenAI · Google · ..." style="rounded=1;whiteSpace=wrap;html=1;arcSize=10;strokeColor=#6B7280;fillColor=#F3F4F6;fontSize=11;fontColor=#374151;" vertex="1" parent="1">
          <mxGeometry x="80" y="1070" width="500" height="40" as="geometry"/>
        </mxCell>
        <mxCell id="L1_storage" value="Persistence&#10;JSONL: audit / memory / experience&#10;SQLite: task state, snapshots, approvals (.aico/state.db)&#10;Config: personas.json / projects.json / .env" style="rounded=1;whiteSpace=wrap;html=1;arcSize=10;strokeColor=#6B7280;fillColor=#F3F4F6;fontSize=11;fontColor=#374151;" vertex="1" parent="1">
          <mxGeometry x="600" y="995" width="540" height="115" as="geometry"/>
        </mxCell>
        <mxCell id="L1_workspace" value="Workspace&#10;target git repos, working_directory per appointment" style="rounded=1;whiteSpace=wrap;html=1;arcSize=10;strokeColor=#6B7280;fillColor=#F3F4F6;fontSize=11;fontColor=#374151;" vertex="1" parent="1">
          <mxGeometry x="1160" y="995" width="500" height="50" as="geometry"/>
        </mxCell>
        <mxCell id="L1_unified" value="Unified Event Index&#10;cross-source trace_id store&#10;(reads from JSONL + SQLite, never owns truth)" style="rounded=1;whiteSpace=wrap;html=1;arcSize=10;strokeColor=#B45309;fillColor=#FEF3C7;fontSize=11;fontColor=#78350F;dashed=1;" vertex="1" parent="1">
          <mxGeometry x="1160" y="1050" width="500" height="60" as="geometry"/>
        </mxCell>

        <mxCell id="e_boss_im" style="endArrow=classic;html=1;rounded=0;exitX=1;exitY=0.5;entryX=0;entryY=0.5;strokeColor=#1E40AF;" edge="1" parent="1" source="L6_boss" target="L6_im">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
        <mxCell id="e_boss_view" style="endArrow=classic;dashed=1;html=1;rounded=0;strokeColor=#1E40AF;" edge="1" parent="1" source="L6_boss" target="L6_view">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
        <mxCell id="e_view_back" value="deep-link prefilled commands" style="endArrow=classic;dashed=1;html=1;rounded=0;strokeColor=#B45309;fontSize=10;" edge="1" parent="1" source="L6_view" target="L6_im">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>

        <mxCell id="e_im_cmd" value="parsed commands" style="endArrow=classic;html=1;rounded=0;exitX=0.5;exitY=1;entryX=0.5;entryY=0;strokeColor=#0F766E;fontSize=10;" edge="1" parent="1" source="L6_im" target="L5_cmd">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>

        <mxCell id="e_cmd_router" value="dispatch" style="endArrow=classic;html=1;rounded=0;exitX=0.5;exitY=1;entryX=0.5;entryY=0;strokeColor=#0F766E;fontSize=10;" edge="1" parent="1" source="L5_cmd" target="L4_router">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
        <mxCell id="e_why_audit" value="trace_id lookup" style="endArrow=classic;dashed=1;html=1;rounded=0;strokeColor=#B45309;fontSize=10;" edge="1" parent="1" source="L5_why" target="L4_audit">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
        <mxCell id="e_exp_expfab" value="lifecycle ops" style="endArrow=classic;dashed=1;html=1;rounded=0;strokeColor=#B45309;fontSize=10;" edge="1" parent="1" source="L5_exp" target="L3_exp">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>

        <mxCell id="e_router_task" value="Task create" style="endArrow=classic;html=1;rounded=0;strokeColor=#0F766E;fontSize=10;" edge="1" parent="1" source="L4_router" target="L4_taskbus">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
        <mxCell id="e_task_approval" style="endArrow=classic;html=1;rounded=0;strokeColor=#0F766E;" edge="1" parent="1" source="L4_taskbus" target="L4_approval">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
        <mxCell id="e_approval_audit" style="endArrow=classic;html=1;rounded=0;strokeColor=#0F766E;" edge="1" parent="1" source="L4_approval" target="L4_audit">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
        <mxCell id="e_grader_exp" value="verdict → confidence" style="endArrow=classic;dashed=1;html=1;rounded=0;strokeColor=#B45309;fontSize=10;" edge="1" parent="1" source="L4_grader" target="L3_exp">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
        <mxCell id="e_dream_exp" value="candidate generation" style="endArrow=classic;html=1;rounded=0;strokeColor=#0F766E;fontSize=10;" edge="1" parent="1" source="L4_dream" target="L3_exp">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>

        <mxCell id="e_task_prompt" value="assemble role prompt" style="endArrow=classic;html=1;rounded=0;strokeColor=#0F766E;fontSize=10;" edge="1" parent="1" source="L4_taskbus" target="L3_prompt">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
        <mxCell id="e_mem_prompt" value="recall" style="endArrow=classic;html=1;rounded=0;strokeColor=#0F766E;fontSize=10;" edge="1" parent="1" source="L3_memory" target="L3_prompt">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
        <mxCell id="e_exp_prompt" value="conditional inject" style="endArrow=classic;dashed=1;html=1;rounded=0;strokeColor=#B45309;fontSize=10;" edge="1" parent="1" source="L3_exp" target="L3_prompt">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>

        <mxCell id="e_prompt_adapter" value="prompt + capability" style="endArrow=classic;html=1;rounded=0;strokeColor=#0F766E;fontSize=10;" edge="1" parent="1" source="L3_prompt" target="L2_aiadapter">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
        <mxCell id="e_im_channel" value="incoming / outgoing" style="endArrow=classic;html=1;rounded=0;strokeColor=#0F766E;fontSize=10;" edge="1" parent="1" source="L6_im" target="L2_channel">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
        <mxCell id="e_view_api" value="read JSON" style="endArrow=classic;dashed=1;html=1;rounded=0;strokeColor=#B45309;fontSize=10;" edge="1" parent="1" source="L6_view" target="L2_view_api">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>

        <mxCell id="e_adapter_cli" value="subprocess spawn / stream" style="endArrow=classic;html=1;rounded=0;strokeColor=#6B7280;fontSize=10;" edge="1" parent="1" source="L2_aiadapter" target="L1_clis">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
        <mxCell id="e_cli_llm" value="HTTPS" style="endArrow=classic;html=1;rounded=0;strokeColor=#6B7280;fontSize=10;" edge="1" parent="1" source="L1_clis" target="L1_llm">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
        <mxCell id="e_audit_storage" value="append JSONL" style="endArrow=classic;html=1;rounded=0;strokeColor=#6B7280;fontSize=10;" edge="1" parent="1" source="L4_audit" target="L1_storage">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
        <mxCell id="e_task_storage" value="persist state" style="endArrow=classic;html=1;rounded=0;strokeColor=#6B7280;fontSize=10;" edge="1" parent="1" source="L4_taskbus" target="L1_storage">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
        <mxCell id="e_mem_storage" value="append JSONL" style="endArrow=classic;html=1;rounded=0;strokeColor=#6B7280;fontSize=10;" edge="1" parent="1" source="L3_memory" target="L1_storage">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
        <mxCell id="e_exp_storage" value="append JSONL" style="endArrow=classic;dashed=1;html=1;rounded=0;strokeColor=#B45309;fontSize=10;" edge="1" parent="1" source="L3_exp" target="L1_storage">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
        <mxCell id="e_view_unified" value="trace queries" style="endArrow=classic;dashed=1;html=1;rounded=0;strokeColor=#B45309;fontSize=10;" edge="1" parent="1" source="L2_view_api" target="L1_unified">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
        <mxCell id="e_unified_sources" value="indexes" style="endArrow=classic;dashed=1;html=1;rounded=0;strokeColor=#B45309;fontSize=10;" edge="1" parent="1" source="L1_unified" target="L1_storage">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>

      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
```

**层级速读**:
- **L6 Boss Surfaces** — 写在 IM(6 个核心命令),看在 aico-view(只读 web)。
- **L5 Application Semantics** — 命令分组、`/inbox` / `/morning` / `/why` / `/undo` / `/experience *` 等动作层。
- **L4 Orchestration Runtime** — Router / TaskBus / Approval / Audit + 新增的 unified event index、Outcome Grader、Dream。
- **L3 Company Model** — Project Assignment、Memory(kind=fact)、**新增 Experience(kind=experience)** 、PromptStack(增加 ExperienceLayer)、Lead Decision。
- **L2 Protocol & Adapter** — AIAdapter / IMChannel / **新增 aico-view 读 API**。
- **L1 Local Providers** — CLI 子进程、底层 LLM API、JSONL/SQLite 持久化、workspace、**新增 Unified Event Index(只读索引,不拥有真相)**。

---

## 6. 落地路线图(sprint 视图)

按优先级:

| 编号 | 内容 | 依赖 | 估算 |
|---|---|---|---|
| **M1** | ✅ MemoryAtom 增加 `kind` + `ExperienceMeta`;Dream 输出改为 candidate experience(Round 128) | 无 | 1 sprint |
| **M2** | ✅ `/experience review/list/archive` + PromptStack 加 ExperienceLayer(Round 130) | M1 | 1 sprint |
| **M3** | ✅ Grader verdict → confidence 回写 + 排序(Round 131) | M1, M2 | 1 sprint |
| **A1** | ✅ Unified event index + trace_id 串联 + 短 ID 改造(Round 129) | 无(与 M1 可并行) | 1 sprint |
| **A2** | ✅ `/undo` + `/why` + `/morning` `/inbox` 内嵌 timeline 摘要(Round 132) | A1 | 1 sprint |
| **V1** | ✅ aico-view 最小 FastAPI + Timeline/Task Trace/Memory Tree 三视图(Round 133) | A1 | 1 sprint |
| **V2** | aico-view → IM deep-link 跳转 | V1 + A2 | 0.5 sprint |
| **A3** | `/timeline`(细粒度)+ `/rollback` 精细 + 边界文档 | A2, M2 | 1 sprint |
| **V3** | aico-view 本地 token 鉴权 + 隧道部署文档 | V1 | 0.5 sprint |
| **(Phase 8 复盘)** | 验证三块基础是否解决 dogfood 根因,再决定 Phase 8 后续 | M3, A3, V2 | 评估 |
| **(F-1 / F-2)** | Lead 主动机制 / Team Karpathy Loop | 全部上述 + Phase 8 dogfood 跑通 | TBD |

**第一刀**:M1 + A1 并行(数据层加固),其他按上表顺序。

---

## 7. 文档生命周期(给未来 agent 看)

### 7.1 如何接手

新的 agent(人类或 AI)拿到任务后:

1. **必读顺序**(CLAUDE.md 已规定):NORTH_STAR → STATUS → ROUNDS → PITFALLS → BLOCKERS → AGENTS。
2. **在动这块基础能力前**,加一步:读本文件 §1 痛点 + §3 对应小节 + §5 架构图。
3. **不要重复在 ADR 里写本文的内容**;ADR 是"决策快照",本文是"跨切面活文档"。如果决策有变,先开 ADR,然后在本文添加"⚠️ 已被 ADR-XXXX 覆盖"标注,而不是默默改本文。

### 7.2 何时更新本文

| 触发条件 | 更新动作 |
|---|---|
| 痛点 §1 中的一条被解决 | 把该条改为 `~~已解决~~` 并加 ROUNDS 链接,不要删 |
| 新增基础痛点 | 在 §1 末尾追加 P7、P8...保持编号稳定 |
| §3 中某 sprint 落地 | 把对应 sprint 状态加上 ✅,引用 ROUNDS 编号 |
| 架构图变化 | 修改 §5 内的 drawio xml(同时把 xml 另存为 `boss-first-grounding.drawio` 旁边文件) |
| Future F-1 / F-2 进入实现 | 单独开 ADR,本文 §4 加"⚠️ 已进入实现"标注 |

### 7.3 如何让模型执行落地(新会话操作指引)

新开 Claude Code 会话时,贴入下方提示词:

```
我要落地 docs/architecture/boss-first-grounding.md 的 §6 路线图中的 <Sprint 编号,例如 M1>。

请先:
1. 完整阅读 docs/architecture/boss-first-grounding.md;
2. 阅读 CLAUDE.md 中的"必读顺序";
3. 输出本 sprint 的实施计划(文件级别的改动列表 + 新增测试用例 + 文档更新清单);
4. 等我确认后再开始改代码;
5. 落地后按 docs/agent/08-self-update-protocol.md 更新 STATUS / ROUNDS / 必要时新增 ADR;
6. 完成后在本文档 §6 表格中给该 sprint 标 ✅ 并附 ROUNDS 编号。

严格遵守:不扩大 sprint 范围;不绕过 NORTH_STAR;不引入本文 §4 中的 Future 方向。
```

---

## 8. 引用与关联

- NORTH_STAR.md(项目宪法)
- STATUS.md(实时进度,Round 127 起引用本文)
- docs/architecture/overview.md(三层架构总览,本文是其细化)
- docs/architecture/a2a-memory-fabric.md(Memory 基础设施,本文 §3.1 在其上扩展 Experience)
- docs/architecture/project-assignment-layer.md(L3 ProjectAssignment 细节)
- ADR-0020 ~ ADR-0023(Memory 系列)
- ADR-0028(SQLite task state store)
- ADR-0029(Phase 8 Absence Loop)
- docs/journal/ROUNDS.md Round 127(本文创建轮次)
