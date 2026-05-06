# Daily Ops — 日常运维速查

> 高频运维操作速查。按场景组织,不按命令组织。
> 当前已有本地验证命令。真实启动 / 任务 / Adapter 运维命令将在 Phase 1 链路完成后填充。

---

## 启动 / 停止

```bash
export AICO_TELEGRAM_BOT_TOKEN="你的 Telegram Bot Token"
export AICO_CLAUDE_WORKING_DIRECTORY="/Users/wangzq/VsCodeProjects/ai-company-os"
env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python /opt/homebrew/bin/python3.11 aico-phase1
```

停止时用 `Ctrl-C`。

### 启用 Phase 2 双 Adapter 状态查询

```bash
export AICO_TELEGRAM_BOT_TOKEN="你的 Telegram Bot Token"
export AICO_ENABLE_CODEX_ADAPTER=true
export AICO_CLAUDE_WORKING_DIRECTORY="/Users/wangzq/VsCodeProjects/ai-company-os"
export AICO_PERSONA_CONFIG_PATH="config/personas.example.json"
export AICO_PROJECT_CONFIG_PATH="config/projects.example.json"
export AICO_APPROVAL_REVIEWER_IDS=""
export AICO_AUDIT_LOG_PATH="/tmp/aico-audit.jsonl"
export AICO_LOG_LEVEL="INFO"
export AICO_LOG_PATH="logs/aico.log"
# 可选:默认 90 秒。Codex accepted 后无 stdout 会自动失败并释放 busy。
export AICO_CODEX_OUTPUT_IDLE_TIMEOUT_SECONDS=90
env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python /opt/homebrew/bin/python3.11 aico-phase1
```

`AICO_PERSONA_CONFIG_PATH` 可省略;省略时使用内置默认 persona。指定后,配置文件中的 `adapter_name` 必须引用当前已启用的 Adapter。

`AICO_PROJECT_CONFIG_PATH` 可省略;省略时使用内置默认 AICO 项目和当前 persona 生成 project team appointment。指定后,配置文件中的 `agents.*.provider` 必须引用当前已启用的 Adapter,`appointments.*.agent` 或兼容字段 `assignments.*.agent` 必须能解析到当前 agent/persona alias。示例见 `config/projects.example.json`。

`AICO_APPROVAL_REVIEWER_IDS` 可省略;默认只有任务发起人可以 `/approve` 或 `/reject` 自己触发的危险任务。需要额外审批人时填 Telegram sender id,逗号分隔。

默认 `AICO_CLAUDE_COMMAND` 使用 `claude -p --output-format text --permission-mode bypassPermissions`。远程场景由 AICO 的 `/approve` 负责审批,避免 Claude Code 在本机再弹出无法通过 Telegram 处理的授权提示。

`AICO_CODEX_OUTPUT_IDLE_TIMEOUT_SECONDS` 默认 90 秒;Codex CLI 进程已 accepted 但一直没有 stdout 时,AICO 会终止该进程并返回 `adapter output idle timeout after 90s`,避免 `/status` 长时间停在 `codex: busy`。

`AICO_AUDIT_LOG_PATH` 可省略;指定后,每条审计事件会追加写入 JSONL 文件,同时 `/audit` 仍展示进程内最近事件。

`AICO_LOG_PATH` 默认是 `logs/aico.log`;如果设置为空则只输出到控制台。`AICO_LOG_LEVEL` 默认 `INFO`。排查长任务没回包时先看:

```bash
tail -f logs/aico.log
```

复测 Claude session resume 时,连续发送同一 active session 的两条普通消息,日志中应先出现 `provider_session_mode=new`,之后出现 `provider_session_mode=resume`。日志只记录 session mode 和 session id 前缀,不会打印完整 prompt。

启动后在 Telegram Bot 会话中发送 `/status`,应看到 `claude-code` 和 `codex` 两个 Adapter。跑过任务后再次发送 `/status`,还会看到最近任务状态。

常用 Telegram 命令:

```text
/help
/status
/tasks
/task <short_task_id>
/audit
/projects
/project aico
/brief
/risks
/blockers
/next
/daily
/weekly
/roles
/role propose 需要一个增长分析岗位
/role confirm
/team
/who implementer
/appoint claude as tester read_repo run_tests
/unappoint tester
/ask reviewer 检查这个方案
/lead implementer
/use project aico
/assignments aico
/assignment aico-implementer
/agents
/agent claude
/skills claude
/tools codex
/sessions
/new claude
/use <session_id>
/bind codex <provider_session_id>
/claude summarize this repo in one sentence
/codex summarize this repo in one sentence
@codex summarize this repo in one sentence
codex: summarize this repo in one sentence
/broadcast summarize this repo in one sentence
/approve
/approve <short_task_id>
/reject
/reject <short_task_id>
/interrupt <short_task_id>
```

写文件、shell 执行和破坏性任务会先进入审批状态。Telegram 返回 `Approval required: <short_task_id>` 后,如果当前只有一个待审批任务,任务发起人或配置的额外审批人可直接发送 `/approve` 继续,或发送 `/reject` 拒绝。若同时有多个待审批任务,使用提示里的短 ID,如 `/approve abcdef12`。未授权用户审批会返回 `approver not authorized`,任务不会派发。

长任务卡住或 Adapter 长时间 busy 时,可先用 `/tasks` 找到最近任务,再用 `/task <short_task_id>` 查看状态和可用动作。running 任务会提示 `/interrupt <short_task_id>`,待审批任务会提示 `/approve <short_task_id>` / `/reject <short_task_id>`。协作任务还会在 `/task` 详情里展示 parent / child trace,可从 implementer 父任务跳到 reviewer 子任务,也可从子任务回看是谁发起。中断示例:`/interrupt 31e559c3`。中断会调用底层 Adapter 的 interrupt 能力,任务状态变为 `interrupted`,并记录审计事件。

Codex 默认是 read-only reviewer,不承接写文件 / shell / destructive 任务。这类任务请用 `/claude`;如果误发给 `/codex`,系统会在核心层直接拒绝,不会再进入无效审批。

Session 命令用于 IM 侧会话管理 MVP:
- `/sessions` 查看当前 AICO 进程内的 session 引用。
- `/new <agent>` 创建一个 AICO session 引用,例如 `/new claude`。
- `/use <session_id>` 将当前聊天 + 当前发送者的普通消息路由到该 session 的 agent。
- `/bind <session_id|agent> <provider_session_id>` 将已有 provider session 绑定到 AICO session;如果 `<agent>` 能匹配 agent card,会创建并激活一个新 session。
- `/bind <provider_session_id>` 会把 provider session id 绑定到当前 active session。

Agent 能力展示命令:
- `/agents` 查看当前 agent、adapter、实时状态。
- `/agent <agent>` 查看角色、adapter、provider、capabilities、tools/skills 来源和 session 特性。
- `/skills <agent>` 会把“列出你当前可用 skills”的只读问题路由给底层 provider 自己回答;AICO 不维护 skills registry。
- `/tools <agent>` 同理,由底层 provider 自己列出当前可调用工具。

当前 session 仍是 AICO 的薄门面,只保存 IM 侧 active session 和 provider session 引用位置;provider 的真实上下文仍由 Claude/Codex 自己保存,AICO 不复制对话历史。

Project Team / Appointment 命令用于项目办公室语义:
- `/projects` 查看配置中的项目列表;当前 active project 会以 `*` 标记。
- `/project [project]` 进入或查看项目办公室;已进入项目后发送 `/project` 会重新展示当前项目的 repo、阶段、默认接活角色和团队任命。
- `/brief [project]` 查看项目简报,包括 repo、阶段、团队、牵头 role、最近任务、最近审计事件,以及 north star / status / journal 文档短片段。顶部会尝试生成 `Boss summary`,下方 `Facts` 保留原始事实并渲染小节标题 / slash command 样式。
- `/risks [project]` 查看真正的项目交付风险,例如失败/中断任务、破坏性任务和 blockers / pitfalls 文档短片段;普通写文件审批和路由噪音不在这里展示。顶部会尝试生成 `Boss summary`,下方 `Facts` 保留原始事实并渲染小节标题 / slash command 样式。
- `/blockers [project]` 查看当前卡住的工作和待决策项,包括等待审批、失败/拒绝/中断任务、未知 persona 这类系统噪音,以及 blockers 文档短片段。顶部会尝试生成 `Boss summary`;如果 summary 不可用,原始 Facts 也会保留基础格式。
- `/next [project]` 查看下一步建议动作,优先提示待审批、失败任务、路由/配置问题;没有卡点时建议把任务交给当前 lead role。顶部会尝试生成 `Boss summary`,下方 `Facts` 保留原始事实并渲染小节标题 / slash command 样式。
- `/daily [project]` 查看日报式项目报告,聚合最近 24 小时本地 AICO 状态里的团队、完成项、未完成项、风险和项目文档短片段。顶部会尝试生成 `Boss summary`,下方 `Facts` 保留原始事实并渲染小节标题 / slash command 样式。
- `/weekly [project]` 查看周报式项目报告,聚合最近 7 天本地 AICO 状态里的团队、完成项、未完成项、风险和项目文档短片段。顶部会尝试生成 `Boss summary`,下方 `Facts` 保留原始事实并渲染小节标题 / slash command 样式。
- `/roles [project]` 查看项目岗位模板和任命缺口,例如哪些 role 已有人负责、哪些还没任命。
- `/role propose <诉求>` 让当前项目 lead role 起草一个新岗位草案;系统会展示 role id、title、summary、默认权限、审批权限和 prompt。
- `/role confirm` 将上一条岗位草案加入当前项目的进程内 roles;不会直接写配置文件,重启后仍以配置文件为准。Telegram 中也可以点击岗位草案下方的 `Confirm` 按钮。
- `/role discard` 丢弃当前聊天里的待确认岗位草案。Telegram 中也可以点击岗位草案下方的 `Discard` 按钮。
- `/team [project]` 查看当前或指定项目的团队任命;输出会显示当前 lead,并在对应成员行标记 `[lead]`。
- `/who <role>` 查看当前项目某岗位由谁负责,以及权限、工作目录和内部 seat。
- `/appoint <agent> as <role> [permissions]` 在当前项目里任命员工到岗位;同一项目的同一 role 只保留一个负责人,重复任命会覆盖而不是追加。当前实现是进程内 appointment,重启后仍以配置文件为准。
- `/unappoint <role>` 撤销当前项目某岗位的进程内任命;重启后仍以配置文件为准。
- `/ask <role> <task>` 把单次任务交给当前项目某岗位,不改变默认接活角色。
- `/lead <role>` 设置当前项目默认牵头角色;之后普通消息会交给这个 role。

走 Project Team / Appointment 的任务会自动渲染 prompt stack,包含 Agent、RoleTemplate、Project、Appointment Contract 和 Current task。显式 `/claude`、`/codex`、`@reviewer` 这类非项目任命路由仍走原 persona prompt。

兼容 / 排障命令:
- `/use project <project>` 仍可将当前聊天 + 当前发送者的普通消息路由到该项目默认 role。
- `/assignments [project]` 查看旧 assignment/seat 列表。
- `/assignment <seat>` 查看某个内部工位的 agent、provider、role、workspace、session policy 和 risk policy。
- `/default <role>` 是 `/lead <role>` 的兼容别名。

使用 `/project aico` 后,普通消息会走 `aico` 项目的默认 role,默认是 `implementer -> claude`。这个 appointment 会复用自己的 project-scoped provider session;第一次普通消息是 `new`,后续普通消息是 `resume`。显式 `/claude`、`/codex`、`@reviewer` 等路由仍优先于 active project。

Claude provider session 已接入最小恢复链路:默认配置下 `/new claude` 会用 AICO session UUID 作为 Claude session id;第一次普通消息使用 `claude ... --session-id <uuid> <prompt>`,之后同一 active session 的普通消息使用 `claude ... --resume <uuid> <prompt>`。如果自定义 `AICO_CLAUDE_COMMAND` 已经包含 `--session-id`、`--resume`、`--continue` 等 session 参数,AICO 不会再追加自己的 session 参数,避免重复。

Codex 已评估并实现 Adapter 侧 resume 命令构造:已有 Codex provider ref 时会走 `codex exec resume <session_id> <prompt>`。Codex `exec` 首轮仍没有稳定的“指定新 session id”入口,所以当前用显式绑定承接已有 Codex 会话:

```text
/bind codex <provider_session_id>
继续刚才那个 review 上下文
```

绑定后,当前聊天 + 发送者的普通消息会自动路由到该 Codex session,并使用 `resume` 模式。

AI 间协作使用显式行首指令:`@persona request` 或 `@persona: request`。例如 implementer 输出:

```text
@reviewer inspect this implementation for missing tests
```

推荐真实 smoke test 任务:

```text
/claude 请先用三条 bullet 简要说明当前 AICO Phase 5 项目办公室和协作链路的现状，然后在最后单独输出一行：
@reviewer review the current Phase 5 collaboration smoke test for risks, missing tests, and whether audit evidence is enough
```

系统会把它转成 reviewer 的普通任务,并在 Telegram 中提示 `Collaboration requested: implementer -> reviewer`。当前只支持单层协作,避免无限递归。
同时 `/audit` 和 JSONL 审计文件会出现 `collaboration_requested` 事件,其中 `task` 是 reviewer 子任务,`actor` 是源 persona,`detail` 中记录 parent task。
也可以用 `/tasks` 找到 parent / child task,再分别执行 `/task <parent_short_id>` 和 `/task <child_short_id>` 查看协作上下游。

长文本输出会自动按安全长度拆成多条 Telegram 消息。第一条仍用于流式编辑,超过单条消息上限后会继续发送下一条,避免 Telegram 4096 字符限制导致后续内容丢失。

默认 Persona:

| Persona | Adapter | Alias |
|---|---|---|
| `implementer` | `claude-code` | `/claude`, `/claude-code` |
| `reviewer` | `codex` | `/codex` |

---

## 本地验证

```bash
env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python /opt/homebrew/bin/python3.11 pytest
env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python /opt/homebrew/bin/python3.11 ruff check .
env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python /opt/homebrew/bin/python3.11 ruff format --check .
env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python /opt/homebrew/bin/python3.11 mypy src tests
```

Project Team 主流程可以先跑本地验收流,再做 Telegram 真实验收:

```bash
env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python /opt/homebrew/bin/python3.11 pytest tests/unit/test_orchestrator.py -k project_team_acceptance_flow
```

---

## 日志查看

```bash
tail -f logs/aico.log
rg "task_id=<task_id>" logs/aico.log
rg "Adapter busy|Adapter process exited|Stream message split|Telegram editMessageText" logs/aico.log
```

长文本任务如果 Telegram 没回结果,重点看:
- 是否有 `Adapter process starting`:没有说明没有派发到 Claude/Codex。
- 是否有 `Adapter busy`:说明该 Adapter 已有任务在跑,当前请求被拒绝。
- 是否有 `Adapter process exited`:没有说明 CLI 还没结束或卡住。
- 是否有 `Stream output`:没有说明还没有 stdout chunk 进入编排层。
- 是否有 `Stream message split`:说明长文本分片已触发。
- 是否有 `Telegram sendMessage` / `Telegram editMessageText` 后的异常:说明 IM 出口失败。

---

## 任务管理

```text
/status
/audit
```

当前 `/status` 会展示 Adapter 状态和最近任务状态。任务状态包括:`running`、`waiting_approval`、`done`、`failed`、`interrupted`、`rejected`。危险任务会在状态行展示风险等级,如 `write_files` / `shell_exec` / `destructive`。

当前 `/audit` 会以多行块展示最近 10 条内存审计事件,包括事件类型、task id、actor、target、adapter、risk 和事件详情。重启进程后内存审计记录会清空;如已配置 `AICO_AUDIT_LOG_PATH`,完整历史可从 JSONL 文件追溯。
未授权审批会记录为 `approval_denied`。
AI 间协作会记录为 `collaboration_requested`,用于追踪 `implementer -> reviewer` 等子任务关系。

查看 JSONL 审计文件:

```bash
tail -n 20 /tmp/aico-audit.jsonl
```

```bash
# 中断某个任务
# 重试失败任务
```

---

## Adapter 管理

```bash
# 列出所有已注册 Adapter
# 启用 / 禁用某个 Adapter
# 查看某 Adapter 状态
```

---

## Channel 管理

```bash
# 列出所有 IM 通道状态
# 重连 Telegram Webhook
```

---

## 配置变更

```bash
# 查看当前生效配置
# reload 配置(无需重启)
```

---

## 数据备份与恢复

```bash
# 备份当前任务历史
# 备份当前 Persona 配置
# 恢复到某个备份点
```

---

## 健康检查

```bash
# 自检命令
# 验证所有 Adapter 可达
# 验证所有 Channel 可达
```

---

## Dogfooding 推荐流程(Phase 1 完成后)

每天早晚两次 5 分钟:

**早上**(检查夜间任务):
1. 打开 Telegram"晨会群"
2. 看夜间各 AI 跑的任务汇总
3. 决定今天派什么新任务

**晚上**(下达夜间任务):
1. 整理白天没做完的事
2. 在 Telegram 群里发任务"今晚把 issue #X-#Y 看一遍"
3. 关电脑(Adapter 仍在跑)

---

## 月度运维

- [ ] 检查 token 消耗,看哪个 Adapter 性价比低
- [ ] 检查 PITFALLS 是否有可以转化为 ADR 的模式
- [ ] 检查 BLOCKERS 是否有长期未解决项,提升优先级
- [ ] 清理 Round 50+ 之前的归档(如有需要)
