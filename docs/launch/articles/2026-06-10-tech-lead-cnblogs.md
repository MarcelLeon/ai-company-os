# 给每个项目任命一个 AI Lead:Agent 应用的新视角

![Release Room demo](../../assets/release-room-demo.gif)

过去谈 agent,大家很容易从模型能力开始:

- 能不能自动写代码?
- 能不能自己规划任务?
- 能不能调用工具?
- 能不能多 agent 协作?

这些当然重要。但我在自己同时处理多个项目时,越来越觉得另一个问题更核心:

> agent 应用真正难的不是"单次任务能不能做",而是"多个项目、多个 agent、多个风险动作能不能被长期运营"。

一个人同时维护几个项目时,最稀缺的是注意力和上下文。最典型的场景不是写代码,而是被打断:

上午还在查 A 项目的 CI,午饭前被问 B 项目 release 能不能发,下午又要回 C 项目的 PR review。每次切换项目,你都要重新加载:

- 当前目标是什么。
- 上次做到哪一步。
- 哪些坑已经踩过。
- 哪些事情可以让 AI 自己查。
- 哪些动作必须我审批。
- 哪个 agent 更适合做 implementer、tester、reviewer。

如果所有 agents 都直接问老板,老板会被小决策淹没。更合理的模型是:

```text
Boss -> Project Lead -> Implementer / Tester / Reviewer / Specialist
```

这篇文章从技术角度讲:为什么我认为"给每个项目任命一个 AI Lead"是 agent 应用下一阶段很重要的视角,以及 AICO 当前是怎么建模的。

## 业界痛点:从 agent demo 到 agent operations

多 agent 并不是新概念。AutoGen 很早就把 multi-agent conversation 作为核心模式;CrewAI 把 agents、crews、flows、tasks/processes 作为基本概念;LangGraph / LangSmith 开始强调 durable execution、human review、streaming、tracing、auth、memory、MCP/A2A。

这说明行业共识在变化:

> agent 不只是 prompt + tool calling,还需要运行时、权限、状态、记忆、观察和人类介入。

我把这个问题叫 agent operations。它和构建 agent 是两层问题:

| 层次 | 关心什么 | 典型问题 |
|---|---|---|
| Agent construction | 怎么写 agent、接工具、接模型、编排流程 | 能不能完成任务 |
| Agent operations | 怎么长期管理 agents、授权、追踪、恢复、复盘 | 能不能放心托付 |

AICO 不是要替代 LangGraph、CrewAI 或 AutoGen。AICO 的切入点更窄:开发者电脑上已经有一堆 AI CLI,我先把它们组织成一个 IM-first 的项目办公室。

这也是为什么 AICO 里会有 Project / Role / Appointment / Task / Approval / Audit / Memory / View 这些看起来偏"管理"的概念。它们不是为了好看,而是为了解决长期运营问题。

## 痛点和解法要对齐

先把问题说严谨。

| 技术痛点 | 如果不解决会怎样 | AICO 的模型 |
|---|---|---|
| 多项目上下文串线 | 一个 agent 在 A 项目的经验污染 B 项目 | Project + Appointment-scoped session |
| 角色职责不稳定 | PM、reviewer、tester 语义靠 prompt 临时维持 | RoleProfile + ProjectRoleOverride |
| 所有 agent 都找老板 | 老板成为调度瓶颈 | Lead responsibility + default role |
| 经验不能复用 | 每个 role 从零开始踩坑 | MemoryKind fact/experience + ExperienceLayer |
| 协作不可追踪 | 子任务和父任务关系丢失 | Collaboration child task + audit event |
| 权限不可控 | read-only reviewer 被派去执行 shell 或危险动作 | RiskLevel + ApprovalPolicy + capability gate |
| 长任务不可恢复 | 进程退出后不知道任务状态 | TaskSnapshot + AuditLog + SQLite state |
| IM 输出不可读 | 手机上看到的是一整屏日志 | `/inbox` / `/morning` / `/view` |

这张表里我最看重的其实是后两项:长任务能不能恢复、IM 能不能读懂。因为它们决定了我敢不敢把项目交给 lead,而不是只在电脑前演示一下。

这张表是文章后面所有技术决策的索引。

## 领域模型:Role、Agent、Team 到底是什么关系

AICO 里不要把 role 和 agent 混在一起。

Agent 是执行实体,例如 Claude Code、Codex、Cursor、Gemini。Role 是项目职责,例如 PM、implementer、tester、reviewer。Project 是上下文边界。Appointment 是"某个 agent 在某个 project 里担任某个 role"。

```text
Agent 1 --- n Appointment n --- 1 Project
                  |
                Role
```

draw.io XML:

[aico-domain-model.drawio](diagrams/aico-domain-model.drawio)

为什么要多一个 Appointment?

因为同一个 agent 在不同项目里应该有不同的:

- 工作目录。
- provider session。
- role prompt。
- project brief。
- 权限边界。
- 最近任务和 audit trace。

如果这些直接挂在 Agent 上,上下文会串。如果直接挂在 Project 上,又无法表达同一个项目里多个角色的分工。Appointment 是中间层,也是"AI 公司"这个类比落到工程上的关键抽象。

实现上对应:

- `CompanyAgentProfile`:agent 的 provider、title、capabilities、并发上限。
- `RoleProfile`:role 的 title、summary、默认权限、approval_required、inline prompt。
- `ProjectProfile`:repo、north_star、status_doc、journal、default_role。
- `AssignmentProfile`:seat、project、agent、role、session_policy、risk_policy、workspace、permissions。
- `ProjectAssignmentDirectory`:负责解析 active project、default assignment、role appointment、runtime role。

这不是装饰性建模。它决定了 prompt 怎么拼、session 怎么复用、权限怎么判断、团队怎么展示。

## 为什么 Lead 是一个 Role,不是一个特殊 Agent

很多系统会把 lead 做成一个固定 agent。我没有这么做。

AICO 里 lead 是当前项目的 default role / default assignment。也就是说,lead 是一个 appointment 的职责状态,不是一个特殊 provider。

好处是:

1. 同一个 agent 可以在项目 A 当 lead,在项目 B 当 reviewer。
2. lead 的能力来自 role + project + appointment,不是来自模型名字。
3. 换 lead 不需要改核心代码,只是换任命关系。
4. lead 仍然走同一套 task、risk、approval、audit。

`prompt_stack.py` 里如果 `is_project_lead=True`,会注入一段 lead responsibility。它要求 lead:

- 降低老板认知负担。
- 证据足够时做有边界的项目判断。
- 重要决策前咨询 challenger、reviewer 或相关 roles。
- 不可逆、高风险、公开发布、凭据、支付、破坏性决策升级给 boss。
- 输出 decision、why、rejected alternatives、evidence、consulted roles、risks、approval need、next actions。

这就是 lead-first 的边界:lead 可以组织,但不能越权。

## 为什么 Role 要有 Memory 和 Experience

如果只给 role 一个固定 prompt,它很快会变成"岗位说明书",而不是"项目里的熟手"。

真实团队里,一个 senior reviewer 之所以可靠,不是因为他背了 reviewer 定义,而是因为他知道:

- 这个项目历史上哪里容易坏。
- 哪些测试以前漏过。
- 哪些输出老板看不懂。
- 哪些发布动作需要多确认一次。
- 哪些环境命令容易踩坑。

AICO 把这里拆成两层:

### Memory:事实型上下文

Memory 是 fact:

- 项目阶段。
- 老板偏好。
- 已完成任务。
- 某个决策结论。
- 某条跨 role 共识。

它走 `MemoryRetriever`,按 boss / project / team / role / agent scope 和 query 相关性召回少量高置信内容。

### Experience:经验型 lesson

Experience 是被验证过或待 review 的经验:

- tester 在这个 repo 先跑哪个 gate。
- reviewer 应该检查哪类风险。
- implementer 不要重复某个坏策略。

它仍然存成 `MemoryAtom`,但 `kind=experience`,并带 `ExperienceMeta(applies_to, triggers, injection_count, verdict_hits, verdict_misses)`。

为什么不把 experience 混进普通 retrieval?因为它的召回逻辑不同。fact 依赖 query;experience 更依赖 role 和场景。AICO 目前选择独立 ExperienceLayer:在 `OrchestratorTaskFactory.task_for_assignment()` 里先 `list_experiences(scope, role_id=assignment.role)`,再把经验渲染进 appointment prompt,并把注入的 `memory_id` 写到 task metadata 里,方便后续 grader 回写效果。

这也是为什么 lead 要能管理 experience。经验不是老板日常手填的东西,它更像项目内务:lead 复盘、晋升、归档,老板只在需要时看结果和审计。

## Task 架构:Lead 怎么指挥其他 Roles

draw.io XML:

[aico-task-flow.drawio](diagrams/aico-task-flow.drawio)

一个项目任务进入 AICO 后,大致是:

```text
IM message
  -> MessageRouter
  -> OrchestratorTaskFactory
  -> Task(payload + project/role/session/memory/experience metadata)
  -> TaskBus
  -> RiskAssessor / ApprovalPolicy / Adapter capability gate
  -> AIAdapter
  -> stream output
  -> TaskSnapshot + AuditEvent
```

如果 agent 输出跨 role 指令:

```text
@reviewer: inspect this implementation for release risks
```

`collaboration.py` 会解析出 target 和 payload。`Orchestrator` 创建 child task,并调用 `record_collaboration_requested(parent, child)`。`/task <parent>` 能看到 children,`/task <child>` 能看到 requested by 和 parent。

这里有一个很关键的安全细节:child task payload 会带父任务上下文,但真实委托放在 `Current task:` 后面。

原因是 `TextRiskAssessor` 只扫描 `Current task:` 之后的内容。这样 reviewer 可以看到父任务上下文里提到的 `git push` 或 `pytest`,但只要当前委托是"审查风险",就仍然是 read-only。否则跨 agent 协作会频繁误判成 shell_exec。

这个设计看起来小,但它回答了一个多 agent 系统常见问题:

> context 和 instruction 必须分离,否则权限系统会把上下文里的危险词当成行动意图。

## 权限和审批:不是信任 prompt,而是信任门禁

AICO 当前权限模型是三层。

### 1. RiskLevel

`TextRiskAssessor` 把任务分成:

- `read_only`
- `write_files`
- `shell_exec`
- `destructive`

它不是最终安全系统,但它能把远程审批的第一道门立起来。

### 2. Adapter capabilities

每个 adapter 声明能力。`unsupported_risk_reason()` 会拒绝 adapter 不支持的风险级别。比如 read-only reviewer 不该被派去 shell_exec。

### 3. ApprovalPolicy

非 read-only 任务进入 `waiting_approval`。默认策略是 requester 或配置的 reviewer 可以审批。批准、拒绝、越权都会写 audit。

这套模型的取舍是:它不是企业级 RBAC,也不是沙箱;但它在 IM-first、本机 CLI、个人开发者场景下足够清楚。危险动作不会因为 agent prompt 写得很自信就直接执行。

## `/view`:为什么不是 Web 控制台

AICO 有 `aico-view`,但我没有把它作为默认主入口。

原因很简单:产品北极星是老板不在电脑前,IM 才是管理层。如果默认让手机访问 Mac 的 localhost 或公网 tunnel,安全边界和使用心智都会变复杂。

所以 `/view` 的当前设计是 IM-delivered HTML snapshot:

- `AICO_VIEW_ENABLED=true` 启用 `/view [project]`。
- AICO 生成自包含 HTML,内联 CSS,没有 localhost URL。
- Telegram 通过 `DocumentChannel.send_document()` 发送 `.html`。
- HTML 是只读 Boss Brief / timeline / trace / memory 摘要。
- 写操作继续回 IM 命令,继续走审批和 audit。

`/view` 回答的是"我想快速看全局",不是"我要在网页里操作一切"。这也是和传统 Web dashboard 的边界。

## 技术 Lead 版核心场景:被追问进度

假设你下午突然被问:

> 昨晚 release 到哪了?还能不能今天发?

没有项目 lead 时,你要:

1. 打开终端。
2. 找昨晚 task。
3. 看 agent 输出。
4. 查测试结果。
5. 判断风险。
6. 组织一段能发出去的话。

有 AICO 后,理想链路是:

```text
/project aico
/morning
/task <id>
/view
```

背后是:

- lead 聚合最近 task、audit、memory。
- reviewer / challenger 可以作为 child task 给反方意见。
- risk action 仍然等待 approval。
- `/view` 给老板看全局,`/task` 给工程师看 trace。

这不是为了炫技,而是为了减少"重新进入现场"的时间。

## 和现有多 agent 框架怎么分工

我对 AICO 的定位是:

| 框架/系统 | 更像什么 | AICO 的位置 |
|---|---|---|
| LangGraph / LangSmith | agent runtime / deployment / durable workflow | 可被 AICO 借鉴或未来接入 |
| CrewAI | crews / flows / agents / tasks/processes | 可作为某类 adapter 或 workflow backend |
| AutoGen | multi-agent conversation / event-driven core / extensions | 可作为另一类 multi-agent backend |
| AICO | 本机 AI CLI 的 IM-first operating layer | 管理项目、岗位、审批、审计、记忆和交接 |

AICO 不应该把自己写成"比这些框架更强"。它解决的是另一层问题:

> 我已经有 Claude Code、Codex、Cursor 等工具,怎么把它们放进一个可远程指挥、可审批、可追溯、可接手的项目组织里?

## 当前边界

为了不把宣传写飘,我把边界也写清楚:

- 当前稳定 IM 入口是 Telegram;飞书 first slice 还待生产 smoke。
- `/overnight` 第一阶段主要派给当前 lead/default role,不是完整多 step 自动调度器。
- AICO 是本机 CLI 控制层,不是独立安全沙箱。
- lead 可以做 bounded decision 和只读协调,高风险动作仍要审批。
- experience 已经可按 role 注入,但 trigger-based 精细召回仍是未来方向。
- `/view` 是只读 HTML snapshot,不是完整 Web 控制台。

这些限制不是缺点,而是当前版本能可靠落地的边界。

## 先跑 demo

```bash
env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python 3.11 aico-release-room-demo
```

仓库地址:

```text
https://github.com/MarcelLeon/ai-company-os
```

我对下一阶段 agent 应用的判断是:

> 真正会留下来的,不是"能聊"的 agent,而是能被组织、被授权、被追踪、被复盘的 agent。

## 参考资料

- LangSmith / LangGraph agent deployment: <https://docs.langchain.com/langsmith/deployment>
- CrewAI documentation: <https://docs.crewai.com/>
- Microsoft AutoGen documentation: <https://microsoft.github.io/autogen/stable/>
