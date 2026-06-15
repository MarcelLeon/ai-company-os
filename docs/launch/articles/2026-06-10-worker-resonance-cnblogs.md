# 人不在电脑前,项目还得往前走:我为什么做 AI Company OS

![Release Room demo](../../assets/release-room-demo.gif)

这篇文章想讲的不是"我又做了一个 AI 工具"。

我真正想解决的是一个很土、很打工人、但每天都会遇到的问题:

> 我不在电脑前的时候,电脑里的 AI agents 能不能像一个小团队一样继续推进项目?

今天的 AI coding 工具已经很强。Claude Code、Codex、Cursor、Gemini、Trae 各有各的能力。但我的日常体感是:工具越多,我越像一个人肉调度器。

这种痛感不发生在 demo 里,发生在很普通的工作日里。

中午去吃饭,agent 还在跑测试;走到电梯口,群里有人问"这个 release 今天能不能发";晚上洗完澡准备睡觉,突然想起还有 release notes、风险点和测试结果没整理;第二天早上坐到电脑前,第一件事不是继续推进,而是翻终端、翻日志、翻聊天记录,重新拼昨晚到底发生了什么。

这时候 AI 不是不强,而是它没有被组织起来。

所以 AI Company OS(AICO) 从第一天就不是想做一个更酷的聊天 UI。它想做的是一个更小、更硬的东西:

> 把本机 AI CLI 收编成一个能通过 IM 远程管理的项目办公室。

当前稳定入口以 Telegram 为主。飞书已经有第一片 Channel 实现,但还没完成生产 smoke test,所以我不会把它写成稳定公开入口。AICO 也不是云端沙箱,它是本机 AI CLI 前面的控制层:真正执行的仍是你电脑上的 Claude Code、Codex、Cursor、CodeFlicker、Trae、Gemini 等 adapter。

## 真正的痛点

我把痛点拆成 6 个,下面按真实优先级讲,保留 P 编号是为了和后面的解法一一对齐。

### P3:多个 agent 反而把我变成调度器

多一个 agent 不等于多一个团队成员。没有项目、岗位、负责人和上下文边界时,多个 agent 只是多个聊天窗口。

这件事的痛感非常像日常工作:我本来只是想把一个 release 往前推,结果一个窗口问"要不要补测试",一个窗口问"这个风险怎么判断",另一个窗口又让我确认"下一步写不写文件"。最后不是 AI 在帮我分担,而是我在给几个 AI 排班、补背景、拍小决定。

一个查问题,一个写代码,一个做 review,听起来很好。但如果它们都直接来问我"下一步做什么",那不是多 agent,那是我多了几个需要随时盯着的下属窗口。所有 agent 都找老板,老板就成了瓶颈。

### P6:风险动作不能默认放飞

写文件、跑 shell、`git push`、删除文件,这些不是普通聊天。AI 再聪明,只要它能碰本机文件和命令,我就不可能把所有动作都默认放行。

这也是我睡前最不敢托管任务的原因:不是怕它不会干,而是怕它在我刷牙、洗澡、睡着以后,替我做了一个不可逆决定。离线托管如果绕过审批,就会从"帮我干活"变成"替我冒险"。

我希望 AI 能替我推进,但高风险动作必须等我拍板。

### P2:我需要看到局面,不是看到内部过程

手机上最需要的不是完整终端日志,而是一张局面图:

- 谁在干什么?
- 哪些完成了?
- 哪些卡住了?
- 哪些需要我拍板?
- 有没有一段可以直接回群里的进度?

很多 AI 工具把过程输出得很完整,但我真正缺的是"压缩后的现场"。大厂工作里人最累的不是不知道怎么写代码,而是一天被十几个上下文撕开,每次都要重新进入现场。

### P5:离开电脑后,项目经常停在半路

坐在 Mac 前时,我可以盯终端、复制上下文、手动重试、看 diff。问题是人不可能一直坐在 Mac 前。

中午去吃饭,agent 还在跑测试;刚进电梯,群里问"这个 release 今天能不能发";晚上躺下了,突然想起还有风险点没整理。最烦的不是收不到通知,而是我明明知道电脑里还有事在跑,却没法像在办公室一样继续交代、审批、打断、接手。

所以问题不是"手机能不能收到消息",而是"我人离开电脑以后,还能不能继续管理项目"。

### P1:长任务最怕不可接手

一个 agent 跑了 20 分钟,最怕的不是失败。失败至少明确。

真正烦的是它给我一整屏混杂输出:一半是过程,一半是结论,中间夹着 warnings、测试日志、建议和未确认风险。我不知道哪些做完了、哪些卡住了、下一步该谁接。

真实工作里,"可接手"比"看起来很努力"重要。否则我离开电脑 1 小时,回来反而要花 20 分钟读它到底干了什么。

### P4:项目知识和经验不能每次重讲

项目的测试命令、目录结构、发布坑、老板偏好、上次失败原因,不应该每次都塞进 prompt。人类团队靠文档和经验交接,AI 团队也一样。

一个 reviewer 可靠,不是因为它知道"reviewer 应该 review",而是它知道这个项目以前哪里漏过测试、哪里容易误判、哪类输出老板看不懂。

这 6 个问题不是 AICO 独有。业界也在往类似方向收敛:

- LangGraph / LangSmith 的 agent deployment 文档把 durable execution、实时 streaming、human review、MCP/A2A、auth、memory、tracing 放在生产级 agent runtime 里。
- CrewAI 文档强调 crews、flows、guardrails、memory、knowledge、observability、RBAC 和 human-in-the-loop。
- AutoGen 也把 multi-agent conversation、event-driven Core、extensions、Docker executor、distributed runtime 当成多 agent 应用的关键能力。

换句话说,大家都在面对同一类通用痛点:agent 不只是"会回答",还要能被编排、被观察、被授权、被追溯、被恢复。

AICO 的切入点更窄:我不先做一个通用 agent 平台,我先把开发者本机这些 AI CLI 管起来,而且默认老板经常不在电脑前。

## 解法总览:问题和 AICO 的回答

| 优先级 | 痛点 | AICO 的回答 | 为什么这样做 |
|---|---|---|---|
| 1 | P3 多 agent 增加调度成本 | Project / Role / Appointment / Team 领域模型 | 先建组织语义,再谈多 agent |
| 2 | P6 风险动作不可放飞 | RiskLevel + ApprovalPolicy + adapter capability gate | 离线托管不等于 YOLO |
| 3 | P2 只想看局面,不是看日志 | `/inbox` / `/morning` / `/view` | 手机先看 Boss Brief,深挖再进 trace |
| 4 | P5 人离开电脑后链路断 | IM-first:Telegram 里下任务、审批、打断、看早报 | IM 不是通知层,而是远程管理层 |
| 5 | P1 长任务不可接手 | Task / Audit / Snapshot / `/task` / `/audit` | 输出可以长,但接手入口必须短 |
| 6 | P4 项目知识反复重讲 | Memory + Experience 分层注入 prompt | fact 和 lesson 是两类东西 |

下面展开讲这些决策背后的动机。

## 领域模型:为什么要有 Agent、Role、Project、Appointment、Team

真实公司里,"张三"和"后端负责人"不是一回事。

同一个人可以在 A 项目做后端负责人,在 B 项目做 reviewer,在 C 项目只做顾问。如果我们把 agent 和项目直接绑定,很快会混乱:

- 同一个 Claude 在不同项目里的工作目录不同。
- 同一个 Codex 在某个项目里是 reviewer,在另一个项目里可能是 implementer。
- 一个角色的 prompt、权限、资源、session 都应该跟项目绑定,不能裸挂到 agent 全局。

所以 AICO 采用 Project Assignment Layer。核心关系是:

```text
Agent 1 --- n Appointment n --- 1 Project
                  |
                Role
```

文章配套 draw.io XML 图在这里:

[aico-domain-model.drawio](diagrams/aico-domain-model.drawio)

AICO 里的几个概念可以这样理解:

| 概念 | 含义 | 对应实现 |
|---|---|---|
| Agent | 可执行的 AI 工具成员,例如 Claude Code / Codex / Gemini | `CompanyAgentProfile` |
| Role | 项目里的职责,例如 PM / implementer / tester / reviewer | `RoleProfile` |
| Project | 工作上下文,包含 repo、状态文档、journal、默认 lead | `ProjectProfile` |
| Appointment | 某个 agent 在某个项目里担任某个 role 的任命/工位 | `AssignmentProfile` |
| Team | 一个项目内当前已任命的 roles 集合 | `/team` 输出 |
| Lead | 项目的默认牵头 role | `/lead`, `default_assignment` |

为什么不用 "session" 做主概念?因为 session 是底层 provider 的实现细节。老板不关心"当前活跃 session 是哪个",老板关心"这个项目谁负责,谁在 review,谁能测试"。

这也是我觉得 AICO 有公司味的地方:它不是让你操作一堆进程,而是让你管理一组岗位。

## 为什么 Role 要有记忆和经验

普通 memory 和 experience 在 AICO 里不是同一种东西。

Memory 更像事实:

- 这个项目当前 phase 是什么。
- 发布前要看哪个文档。
- 老板偏好中文汇报。
- 某个任务已经完成。

Experience 更像经验:

- reviewer 在这个项目里看到长输出时要按移动端可读性拆段。
- tester 要优先跑哪组回归。
- implementer 曾经因为某个风险误判踩过坑。

如果把两者都当普通检索记忆,会有两个问题:

1. 事实需要按 query 相关性召回,经验则更像 role 的工作习惯,不一定每次 query 都显式命中。
2. 经验需要被验证和回写效果,例如 Outcome Grader 判断这条经验有没有帮上忙。

所以 AICO 后来把 `MemoryAtom` 加了 `kind=fact|experience`。fact 通过 `MemoryRetriever` 召回,experience 走独立 ExperienceLayer,按 role 注入 appointment prompt。

这就是为什么 `/experience` 被设计成 lead 内务,不是老板一线命令。真实公司里,老板通常不会每天维护"tester 经验库";项目 lead 或角色负责人更适合做这件事。老板只关心这些经验最终有没有让交付更可靠。

## 为什么 Lead 能操作其他 Role 的经验和记忆

Lead 不是更大的 implementer。Lead 的职责是降低老板认知负担。

在 AICO 的 prompt stack 里,如果某个 appointment 是当前项目 lead,会多一段 lead responsibility:

- 证据足够时做有边界的项目判断。
- 重要决策前咨询 challenger、reviewer 或相关角色。
- 遇到不可逆、高风险、公开发布、凭据、支付、破坏性动作时升级给 boss。
- 输出 decision / why / rejected alternatives / evidence / consulted roles / risks / next actions。

这意味着 lead 可以做三类事情:

1. 读项目/team/role/agent scope 的记忆。
2. 把经验晋升、归档、复盘作为内务处理。
3. 派其他 role 做只读审查或补充意见。

但 lead 不能越过权限边界。写文件、shell、destructive 仍然进入审批。memory promotion、rollback、公开发布这类动作也应该被审计。它的权力来自"组织协调",不是来自"无限授权"。

这和真实公司类似:项目负责人可以让 tester 补测试、让 reviewer 看风险、整理经验,但不能替老板做所有不可逆承诺。

## Task 架构:我到底怎么让任务跑起来

AICO 的 Task 是最小工作单元,包含:

- `task_id`
- `payload`
- `requester_id`
- `target_persona`
- `context_ref`
- `metadata`
- `trace_id`

任务从 IM 进来之后,大致经过这条链路:

1. `IMChannel` 收到 Telegram 文本。
2. `MessageRouter` 把消息解析成目标 persona 和 task payload。
3. 如果当前 chat 有 active project,`OrchestratorTaskFactory` 找到默认 lead / appointment。
4. factory 组装 appointment prompt:agent base、role prompt、lead responsibility、project brief、appointment contract、memory packet、experience、current task。
5. `TaskBus` 做风险识别和 adapter 选择。
6. 如果是 read-only 且 adapter 支持,直接 dispatch;如果是 write/shell/destructive,进入 `waiting_approval`。
7. 审批通过后,`TaskBus` 再派给 adapter。
8. 输出流回 IM,同时写 task snapshot 和 audit event。

配套 draw.io XML 图:

[aico-task-flow.drawio](diagrams/aico-task-flow.drawio)

这里的关键点是:Task 不是只代表"一段 prompt"。它还带着项目、role、appointment、provider session、risk、audit、collaboration metadata。否则你第二天无法追溯"谁让谁做了什么"。

## 跨 agent 委派是怎么做的

AICO 目前的跨 agent 协作不是复杂的 RPC,而是轻量指令:

```text
@reviewer: inspect this plan for release risk
```

当某个 agent 输出里出现这类指令时,`split_collaboration_directive()` 会解析出 target persona 和 payload。`Orchestrator` 会创建一个 child task,并记录 `COLLABORATION_REQUESTED` audit event。

这里有一个踩过坑后才变硬的细节:child task payload 会包含父任务到目前为止的 source context,但真正要 child 做的事会放在:

```text
Current task:
...
```

为什么要这样?因为风险识别只看 `Current task:` 后面的内容。否则 reviewer 子任务只是"请你审查风险",但父任务上下文里出现了 `git push`、`pytest`、`run command`,就会被误判成 shell_exec,导致只读 reviewer 被拒绝。

这就是工程里很典型的"组织语义影响安全边界":跨 agent 委派不是把父输出原样塞给下一个 agent,必须区分 context 和 instruction。

## 权限怎么管

AICO 的权限不是一个大而全 ACL,而是当前阶段够用的三层门禁:

### 第一层:文本风险识别

`TextRiskAssessor` 把任务分成:

- `read_only`
- `write_files`
- `shell_exec`
- `destructive`

如果 payload 里有 `Current task:`,风险识别只看它后面的真实委托内容。这和跨 agent 委派的边界直接相关。

### 第二层:Adapter 能力门禁

每个 adapter 声明 capabilities。比如某个 adapter 没有 `SHELL_EXEC`,那 shell task 即使被批准,也不能派给它。`unsupported_risk_reason()` 会拒绝不匹配的 adapter。

### 第三层:审批策略

风险任务进入 `waiting_approval`。默认 `RequesterOrListedApproverPolicy` 允许 requester 或配置的 reviewer 处理 `/approve` / `/reject`。审批、拒绝、越权审批都会写 audit event。

这个模型不完美,但边界很清楚:AICO 是控制层,不是安全沙箱。真正的本机文件系统和 shell 风险仍然要靠审批、能力门禁、审计和未来更强 sandbox 一起承担。

## 为什么要有 `/view`

一开始我也想过:既然是 IM-first,是不是所有信息都发 Telegram 文本就好?

后来发现不够。手机聊天适合短动作:

- `/approve`
- `/reject`
- `/interrupt`
- `/task <id>`
- `/morning`

但它不适合承载一个完整项目视图。老板早上回来时,需要的是一个 Boss Brief:

- 当前项目状态。
- 最近任务和时间线。
- 重要 trace。
- memory / experience 摘要。

这就是 `/view` 的动机。

但 `/view` 没有走"让 Telegram 访问你本机 localhost"这条路。AICO 的设计是:

- `AICO_VIEW_ENABLED=true` 只启用 IM 里的 `/view [project]`。
- 生成一份自包含 HTML,内联 CSS,不含 localhost URL。
- 如果 Channel 支持 `DocumentChannel`,Telegram 通过 `sendDocument` 发送 `.html` 文件。
- 不支持附件的 Channel 降级为写本地文件并回路径。

为什么这么做?因为老板不在场时,默认不应该引导手机访问本机端口或公网 tunnel。HTML snapshot 是只读交付物,写操作仍然回到 IM 命令和审批。

这也是 AICO 的产品边界:可视化可以有,但不能把 Web 控制台变成主入口。主入口仍然是 IM。

## 睡前托管 release room

现在回到一开始的痛点。

假设我晚上要准备一个小型开源 release。AICO 里的流程不是"把一大段 prompt 扔给一个 agent":

```text
/project aico
/team
/ask pm summarize the next release plan in 3 bullets
/overnight prepare the release-room handoff and list remaining risks
```

它背后发生的是:

- 当前 chat 进入 `aico` project。
- `/team` 展示 lead、implementer、tester、reviewer 等 appointment。
- `/ask pm ...` 通过 PM role 的 prompt、project brief、memory packet 组装 task。
- `/overnight` 默认派给当前 lead/default role。
- 风险动作继续走 `/approve`。
- agent 输出如果请求 reviewer 协作,会生成 child task 并写 audit。
- 第二天我用 `/morning` 看交接,用 `/task` 看原始 trace,用 `/audit` 看责任链,需要视觉摘要时用 `/view`。

这就是前面 6 个痛点的闭合:

| 前面的问题 | 在这个场景里的回答 |
|---|---|
| 多 agent 调度成本高 | lead/default role + `/team` |
| 风险动作不可放飞 | `/approve` / `/reject` |
| 老板只想看局面 | `/inbox` / `/morning` / `/view` |
| 人离开电脑后链路断 | `/overnight` + `/morning` |
| 长任务不可接手 | handoff + `/task` trace |
| 项目知识反复重讲 | memory packet + experience layer |

## AICO 和业界多 agent 框架的关系

我不认为 AICO 要替代 LangGraph、CrewAI 或 AutoGen。

它们更像是 agent 应用/工作流构建框架,关注图、流程、工具、runtime、deployment、observability。

AICO 更像"本机 AI CLI 团队的管理层":

- 它不先定义一个通用 workflow DSL。
- 它先把开发者已经在用的 CLI adapter 化。
- 它把 IM 当老板管理入口。
- 它把 project、role、appointment、task、approval、audit、memory 建成领域模型。
- 它承认本机执行有风险,所以默认保守。

这也是为什么我觉得它有真实价值:它不是追一个大而全平台,而是把一个具体痛点打透。

## 先跑起来

不想配 Telegram token,可以先跑 no-token demo:

```bash
env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python 3.11 aico-release-room-demo
```

它会用 deterministic fake adapters 跑一遍 Release Room 链路,不调用 Telegram、Claude、Codex 或付费 provider。

仓库地址:

```text
https://github.com/MarcelLeon/ai-company-os
```

我做 AICO 的动机,说到底就是一句话:

> 人可以离开电脑,但项目不能永远等人回来才继续。

## 参考资料

- LangSmith / LangGraph agent deployment: <https://docs.langchain.com/langsmith/deployment>
- CrewAI documentation: <https://docs.crewai.com/>
- Microsoft AutoGen documentation: <https://microsoft.github.io/autogen/stable/>
