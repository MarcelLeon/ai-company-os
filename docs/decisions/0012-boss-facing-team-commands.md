# ADR-0012: Boss-Facing Team Commands and Role System

**状态**:Accepted
**日期**:2026-05-04
**决策者**:Wang / Codex(协作)
**相关 Round**:Round 32
**Refines**:ADR-0011 Project Assignment Layer

---

## 背景与问题

ADR-0011 引入了 Agent / Project / Assignment,但第一切片把 `assignment`、`seat`、`/use assignment` 这类内部工程语义暴露给用户。真实老板视角并不是“使用一个工位 id”,而是“进入项目办公室、查看团队、任命员工、把任务交给某个岗位、设置默认负责人”。

需要把 Project Assignment Layer 的用户界面改成公司管理语言,同时补齐 role 体系,避免项目长期只有 implementer / reviewer 两个窄角色。

## 候选方案

### 方案 A — 保留 `/assignment <seat>` 作为主入口
- 优点:实现最简单,延续 Round 31 代码。
- 缺点:`seat` 是内部稳定 id,不是人类老板的自然语言;用户不理解任命关系。
- 复杂度:低。

### 方案 B — 把 Assignment 在产品层表达为 Appointment / Team
- 优点:符合“老板派发任命”的直觉;`seat` 保留为内部 id,但命令面向项目、团队、岗位和任命。
- 缺点:需要新增命令语义和文档,后续代码要做兼容迁移。
- 复杂度:中。

### 方案 C — 做完整组织架构管理系统
- 优点:可表达部门、职级、汇报线、权限组。
- 缺点:个人 dogfooding 过重,偏离当前 Phase 5 的协作主线。
- 复杂度:高。

## 决策

选择 **方案 B:把 Assignment 的产品层表达改为 Appointment / Team**。

核心命令面向老板语言:

```text
/project aico
/team
/who implementer
/appoint claude as implementer
/ask reviewer 检查这个方案
/lead implementer
```

`Assignment` 仍作为内部领域模型保留,含义调整为 Appointment 的持久化记录:`agent + project + role + resources + permissions + prompt context + provider session`。`seat` 仅作为内部稳定 id,正常交互不要求用户理解或输入。

## 决策理由

- 北极星要求“像管理真实团队一样”。老板不会说“use assignment seat”,只会说“任命 Claude 做开发负责人”。
- Project 是上下文边界,Team 是项目里的人员编制,Role 是岗位模板,Appointment 是具体任命。
- Role prompt 需要通用,但项目要能覆盖特殊规则;因此 role 体系必须显式建模,不能只在 assignment 上挂一段 prompt。
- implementer / reviewer 只覆盖开发和审查,不足以支撑长期项目运营;需要至少覆盖 PM、测试、架构、安全、文档、运维等常见职能。

## 后果

### 正面后果

- Telegram 交互更接近真实老板管理项目。
- 新项目可以自动生成默认团队任命,用户再按需调整。
- 后续 `/brief`、`/risks`、日报、周报可以围绕 Team / Role 聚合,不是围绕裸 session。

### 负面后果

- Round 31 的 `/assignments` / `/assignment <seat>` 需要降级为兼容或调试命令。
- 需要新增 role template 和 project role override 的配置模型。
- `/appoint` 如果支持写配置,必须处理审批、审计和持久化;MVP 可以先做内存任命或生成建议配置。

### 我们接受这些代价是因为

这是从“AI CLI session 管理器”走向“AI 公司操作系统”的产品语言校正。概念如果不符合老板直觉,后续功能越多越难用。

## 不再做的事

- 不把 `/use assignment <seat>` 作为主路径。
- 不要求用户记住 `aico-implementer` 这类 seat id。
- 不把 role prompt 复制到每个 appointment 中。
- 不在 Phase 5 里扩展成完整 HR / 组织架构系统。

## 相关链接

- ADR-0011
- `docs/architecture/project-assignment-layer.md`
- ROUNDS Round 32
