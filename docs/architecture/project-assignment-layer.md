# Project Team and Appointment Layer — 项目团队与任命层

> 这一层把裸 session 升级为“老板管理 AI 团队”的语义:进入项目办公室、查看团队任命、任命员工、把任务交给岗位、设置默认负责人。

---

## 为什么需要这一层

用户日常推进的是完整项目,不是孤立的 Claude/Codex session。只暴露 session 会让 Telegram 像远程 CLI,而不是 AI 公司。

这一层的目标:

- 让用户按项目管理 AI 工作,而不是按 session 猜上下文。
- 让 Agent 像员工:可以被任命到多个项目,但每个项目里的岗位、资源、权限和上下文独立。
- 让 Role prompt 通用,但允许项目按自己的特殊性覆盖。
- 让日报、周报、风险、项目简报、未来看板和灵动岛都有统一数据源。

---

## 老板视角的核心语言

### Agent — 员工

Agent 是公司员工名册中的人,例如 `claude`、`codex`、未来的 `openclaw` 或公司内部 CLI。

Agent 描述全局能力:

- provider:`claude-code` / `codex`
- 全局能力:写代码、review、读仓库、shell、长任务等
- base prompt:员工本身的工作风格和边界
- provider session 能力:new / resume / bind-only

Agent 不直接保存项目状态,也不直接保存项目里的 provider session。

### RoleTemplate — 通用岗位模板

RoleTemplate 是跨项目复用的岗位职责。它回答“这个岗位一般负责什么”,不回答“在某个具体项目里有什么特殊规则”。

建议内置角色:

| Role | 中文名 | 默认职责 | 默认权限倾向 |
|---|---|---|---|
| `implementer` | 开发负责人 | 实现功能、修 bug、更新测试和项目状态 | 可读写,高风险需审批 |
| `reviewer` | 审查负责人 | 审查设计风险、代码问题、测试缺口和可维护性 | 只读 |
| `tester` | 测试负责人 | 设计测试策略、补充用例、跑验证、报告失败原因 | 通常可执行测试,写测试需审批或授权 |
| `pm` | 项目经理 | 拆任务、维护进度、写日报/周报、识别阻塞 | 只读或写文档 |
| `architect` | 架构师 | 做抽象边界、ADR、模块拆分、演化路线评估 | 只读或写设计文档 |
| `security` | 安全审查 | 审查权限、密钥、危险操作、供应链风险 | 只读 |
| `docs` | 文档负责人 | 维护 README、操作手册、交接文档、变更说明 | 写文档 |
| `ops` | 运维负责人 | 启动、部署、日志、告警、故障排查 | shell 需审批 |
| `analyst` | 分析师 | 市场/竞品/需求/数据分析,产出结构化结论 | 只读,可联网需显式授权 |
| `designer` | 产品/交互设计 | 设计用户流程、命令语义、界面信息架构 | 只读或写设计文档 |

MVP 不要求每个项目都有全部角色。项目只声明自己需要的 role。

### Project — 项目办公室

Project 是老板真正管理的业务上下文:

- 项目名:`aico`
- repo path
- north star / status doc / journal doc
- 当前阶段
- 项目特殊规则
- 项目需要哪些 role
- 默认接活 role

进入项目办公室后,普通消息默认交给该项目的默认 role。

### Appointment — 任命

Appointment 是老板做出的任命:

```text
Claude 被任命到 AICO 项目担任 implementer。
Codex 被任命到 AICO 项目担任 reviewer。
```

代码里可以继续叫 `Assignment`,但用户界面和文档应优先使用“Appointment / 任命”。它持有:

- project:所属项目
- role:项目内岗位
- agent:被任命的员工
- resources:repo/workspace、文档、允许读取的上下文
- permissions / scope:岗位工作范围,优先使用 `docs` / `code` / `tests` / `ops` / `audit`;危险操作仍走 risk level 与 `/approve`
- prompt stack:agent base + role template + project override + appointment contract + runtime context
- provider session ref
- 当前状态和最近任务
- 内部 seat id,例如 `aico-implementer`

`seat` 是内部稳定 id,用于持久化、日志和排障。正常老板交互不应该要求用户记住它。

---

## 推荐命令语义

主路径命令:

```text
/project aico
/team
/who implementer
/appoint claude as implementer
/unappoint tester
/ask reviewer 检查这个方案
/lead implementer
/brief
/risks
/blockers
/next
/daily
/weekly
/roles
/role propose 需要一个增长分析岗位
/role confirm
```

### `/project aico`

进入 AICO 项目办公室,并展示项目上下文、团队任命、默认负责人。
已进入项目后,再次发送 `/project` 会重新展示当前项目办公室。

期望输出:

```text
已进入项目办公室: AICO

项目: AI Company OS
阶段: Phase 5 - AI 间协作
Repo: /Users/wangzq/VsCodeProjects/ai-company-os
默认接活角色: implementer -> Claude

团队:
- implementer: Claude, 可读写,高风险需审批
- reviewer: Codex, 只读,负责审查风险和设计问题
```

### `/team`

查看当前项目的团队任命。也支持 `/team aico`。

同一项目里的同一 role 只有一个负责人。重复 `/appoint <agent> as <role>` 会覆盖
这个 role 的负责人,不会在团队列表里追加多个同名岗位。`/team` 还应直接展示当前
lead role,让老板不需要再通过 `/lead` 的历史消息推断默认接活人。

期望输出:

```text
AICO 当前团队任命:
lead: tester -> Claude

- implementer -> Claude
  职责: 开发负责人
  权限: 可读写代码,高风险需审批
  资源: repo / status / journal

- tester -> Claude [lead]
  职责: 测试负责人
  scope: code, tests
  资源: repo / status / journal

- reviewer -> Codex
  职责: 审查负责人
  scope: code, docs, audit
  资源: repo / docs / audit
```

### `/roles`

查看当前项目需要哪些岗位、哪些岗位已经任命。默认只展示核心/专家岗位,支持岗位用 `/roles all` 展开,单个岗位详情用 `/role <id>`。
查看类命令会在末尾追加简短 `Next` 指导命令,只给 2-5 个最自然的后续动作,不替代 `/help`。

期望输出:

```text
Roles: aico [AI Company OS]

Core
- implementer | 开发负责人 | claude
- reviewer | 审查负责人 | codex

Specialists
- golden-tester | Golden Path Tester | open

Hidden: tester, docs, ops, analyst, designer
Use /roles all or /role <id>.

Next:
- /role <role>
- /agents
- /appoint <agent> as <role>
- /roles all
```

### `/role propose 需要一个增长分析岗位`

让当前项目的 lead role 起草一个新岗位草案。AICO 不允许 LLM 静默修改项目结构:
LLM 只能返回 role 草案,老板必须确认后才会加入当前项目。

当前 MVP 的确认流是进程内状态:

```text
/role propose 需要一个增长分析岗位
```

期望输出:

```text
Role proposal for aico
id: growth-analyst
title: Growth Analyst
summary: Analyze activation and retention opportunities.
scope: docs, audit
approval_required: destructive
prompt: Focus on measurable product opportunities.

Send /role confirm to add it to this project, or /role discard to cancel.
```

确认:

```text
/role confirm
```

确认后 `/roles` 会展示新增 role,但不会直接写 `AICO_PROJECT_CONFIG_PATH` 指向的配置文件。
正式持久化需要单独设计配置写入、审计和回滚策略。

### `/who implementer`

查看当前项目某个 role 由谁负责,以及他的资源、权限和 prompt 摘要。

期望输出:

```text
AICO / implementer

负责人: Claude
权限: 可读写代码,高风险需审批
工作目录: /Users/wangzq/VsCodeProjects/ai-company-os
职责: 实现功能、修复问题、更新测试和项目状态文档
内部 seat: aico-implementer
```

### `/appoint claude as implementer`

在当前项目里任命 Claude 担任 implementer。如果当前项目缺少这个 role,系统可以按 RoleTemplate 创建项目岗位;如果项目已有 implementer,则替换当前负责人。

MVP 可以先做内存任命或生成配置建议。正式持久化任命必须走审计。

期望输出:

```text
任命已生效

Claude,你在 AICO 项目里担任开发负责人。
工作目录:/Users/wangzq/VsCodeProjects/ai-company-os
权限:可读写代码,高风险操作需要老板审批
角色:implementer
职责:实现功能、修复问题、更新测试和项目状态文档
```

另一个例子:

```text
/appoint codex as reviewer readonly
```

期望输出:

```text
任命已生效

Codex,你在 AICO 项目里担任 reviewer。
工作目录:/Users/wangzq/VsCodeProjects/ai-company-os
权限:只读
角色:reviewer
职责:审查设计风险、代码问题、测试缺口和可维护性问题
```

### `/unappoint tester`

撤销当前项目某个 role 的任命。它只影响当前进程内 appointment 状态,不会直接改配置文件;重启后仍以 `AICO_PROJECT_CONFIG_PATH` 或内置默认配置为准。

期望输出:

```text
任命已撤销

Claude 不再担任 AICO 项目的 tester。
内部 seat:aico-tester
```

### `/ask reviewer 检查这个方案`

把这一次任务交给当前项目的 reviewer,不改变默认接活角色。

也支持:

```text
/ask implementer 修复这个 bug
/ask tester 设计回归测试
/ask pm 总结本周进展
```

这比 `/use role reviewer` 更自然,因为老板不是“切换自己使用的东西”,而是“把任务交给某个岗位”。

### `/lead implementer`

设置当前项目的默认牵头角色。之后普通消息默认发给该 role 的负责人。

期望输出:

```text
AICO 当前牵头角色已设置为 implementer -> Claude
之后普通消息会交给开发负责人处理。
```

### `/brief` / `/risks` / `/blockers` / `/next` / `/daily` / `/weekly`

项目办公室应提供老板能快速扫一眼的只读状态面:

- `/brief [project]`:项目简报,展示 repo、阶段、团队、牵头 role、最近任务、最近审计和项目文档短片段。
- `/risks [project]`:项目交付风险,展示失败/中断任务、破坏性任务和 blockers / pitfalls 文档短片段;普通写文件审批和未知 persona 这类底层噪音不进入项目风险。
- `/blockers [project]`:当前卡住的工作和待决策项,展示等待审批、失败/拒绝/中断任务、未知 persona 等系统/执行问题,以及 blockers 文档短片段。
- `/next [project]`:下一步动作建议,优先处理待审批、失败任务、路由/配置问题;没有卡点时建议把任务交给当前 lead role。
- `/daily [project]`:日报式报告,按最近 24 小时本地 AICO 状态聚合团队、完成项、未完成项、风险和文档短片段。
- `/weekly [project]`:周报式报告,按最近 7 天本地 AICO 状态聚合团队、完成项、未完成项、风险和文档短片段。

MVP 只基于本地进程状态和受限项目文档片段,不调用 provider,不假装拥有跨进程长期记忆。

---

## 兼容与降级命令

旧命令可以保留一段时间,但应降级为兼容或排障入口:

```text
/assignments aico
/assignment aico-implementer
/use project aico
```

推荐迁移:

| 旧命令 | 新命令 |
|---|---|
| `/use project aico` | `/project aico` |
| `/assignments aico` | `/team aico` |
| `/assignment aico-implementer` | `/who implementer` |
| `/use assignment aico-implementer` | 不作为主路径;用 `/ask <role>` 或 `/lead <role>` |

---

## 配置模型建议

示例形态:

```yaml
agents:
  claude:
    provider: claude-code
    title: Senior Implementer
    base_prompt: prompts/agents/claude.md
    capabilities:
      - code_edit
      - shell_exec
      - long_context

  codex:
    provider: codex
    title: Code Reviewer
    base_prompt: prompts/agents/codex.md
    capabilities:
      - code_review
      - repo_inspect

roles:
  implementer:
    title: 开发负责人
    prompt: prompts/roles/implementer.md
    default_permissions:
      - code
      - tests
      - docs
    approval_required:
      - shell_exec
      - destructive

  reviewer:
    title: 审查负责人
    prompt: prompts/roles/reviewer.md
    default_permissions:
      - code
      - docs
      - audit

  tester:
    title: 测试负责人
    prompt: prompts/roles/tester.md
    default_permissions:
      - code
      - tests

projects:
  aico:
    name: AI Company OS
    repo: /Users/wangzq/VsCodeProjects/ai-company-os
    north_star: NORTH_STAR.md
    status_doc: STATUS.md
    journal: docs/journal/ROUNDS.md
    default_role: implementer
    roles:
      implementer:
        prompt_override: prompts/projects/aico/implementer.md
        resources:
          - AGENTS.md
          - NORTH_STAR.md
          - STATUS.md
          - docs/journal/ROUNDS.md
      reviewer:
        prompt_override: prompts/projects/aico/reviewer.md
      pm:
        prompt_override: prompts/projects/aico/pm.md

appointments:
  - project: aico
    role: implementer
    agent: claude
    seat: aico-implementer
    permissions:
      - code
      - tests
      - docs

  - project: aico
    role: reviewer
    agent: codex
    seat: aico-reviewer
    permissions:
      - code
      - docs
      - audit
```

---

## Prompt 分层

Prompt 不能按 Appointment 复制大段文本。应分层拼装:

```text
1. Agent Base Prompt        员工本身的工作风格和能力边界
2. RoleTemplate Prompt      implementer / reviewer / tester / pm 等通用职责
3. Project Role Override    项目对该 role 的特殊要求
4. Appointment Contract     谁被任命到哪个项目、拥有哪些资源和权限
5. Runtime Context          当前任务、当前风险、最近进展、审计摘要
```

渲染结构:

```text
你是 {{agent.title}}

{{agent.base_prompt}}

通用岗位:
{{role.prompt}}

项目特殊要求:
{{project.roles[role].prompt_override}}

任命书:
{{agent.name}},你在 {{project.name}} 项目里担任 {{role.title}}。
工作目录:{{project.repo}}
权限:{{appointment.permissions}}
职责:{{role.summary}}

当前任务:
{{task}}
```

---

## 新项目默认任命

如果 `/project <id>` 指向一个新项目,系统可以按默认团队模板创建建议任命。

建议默认团队:

```text
implementer -> Claude
reviewer -> Codex
pm -> Claude 或未任命
tester -> 未任命
```

默认只自动启用 `implementer` 和 `reviewer`,其余 role 显示为“建议补齐”,避免新项目过度复杂。

期望输出:

```text
新项目 AICO 已创建默认团队:

- implementer -> Claude
- reviewer -> Codex
- tester -> 未任命
- pm -> 未任命

你可以使用:
/appoint claude as pm
/appoint codex as tester readonly
```

---

## 与现有 Session 层的关系

现有 Agent Session 仍有价值,但它应下沉为 Appointment 的技术实现:

- 旧语义:`Claude 当前 session 是 X`
- 新语义:`AICO 项目的 implementer 任命拥有 provider session X`

新功能优先围绕 Project / Team / Role / Appointment 建模。裸 session 命令继续保留给排障和高级场景。
