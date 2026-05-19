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
export AICO_MEMORY_PATH="/tmp/aico-memory.jsonl"
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
Round 62 起,启动时也会读取这个 JSONL 文件里的历史审计事件;`/metrics` 会用这些事件重建历史任务指标,因此重启后 24h / 7d 的 done / failed / interrupted 等统计不会直接清空。`/tasks` 仍只展示当前进程内任务。

`AICO_MEMORY_PATH` 可省略;指定后,Phase 7 shared memory 会写入 append-only JSONL,并在 project-scoped task prompt 中自动召回当前项目少量高置信记忆。`/remember` / `/recall` / `/forget` 是纠错、补充、排障和验收入口,不是要求老板日常手动维护记忆。

### 启用 Cursor / CodeFlicker / Trae / Gemini 可选 Adapter

这些 Adapter 默认不启用。需要让 `/agents` 展示更多可用成员时,在启动前打开对应开关:

```bash
export AICO_ENABLE_CURSOR_ADAPTER=true
export AICO_ENABLE_CODEFLICKER_ADAPTER=true
export AICO_ENABLE_TRAE_ADAPTER=true
export AICO_ENABLE_GEMINI_ADAPTER=true
export AICO_CURSOR_OUTPUT_IDLE_TIMEOUT_SECONDS=90
export AICO_CODEFLICKER_OUTPUT_IDLE_TIMEOUT_SECONDS=90
export AICO_TRAE_OUTPUT_IDLE_TIMEOUT_SECONDS=90
export AICO_GEMINI_OUTPUT_IDLE_TIMEOUT_SECONDS=90
```

默认命令:

```bash
export AICO_CURSOR_COMMAND="cursor-agent -p --force --output-format text"
export AICO_CODEFLICKER_COMMAND="flickcli -q --approval-mode yolo --output-format text"
export AICO_TRAE_COMMAND="trae-cli --print --yolo"
export AICO_GEMINI_COMMAND="gemini --approval-mode yolo --output-format text"
```

Cursor 需要本机安装并登录 `cursor-agent`;CodeFlicker 需要本机 `flickcli` 可用并完成 SSO 登录;Trae 需要 `trae-cli`;Gemini 需要 `gemini` CLI。Round 67 起这些 Adapter 声明完整 `code_edit` / `shell_exec` 能力,底层 CLI 使用非交互批准模式避免卡在本机确认。远程安全边界由 AICO 的风险识别、`/approve`、审计和 `/interrupt` 承担;不要绕过 AICO 直接在 IM 里长期使用裸 YOLO 命令。

写文件、shell 或 destructive 任务发给这些 Adapter 时,应先进入 `waiting_approval`。确认任务无误后再 `/approve <short_task_id>`;如果只是分析/总结,请在 prompt 里明确 `do not edit files`。

### Feishu Channel

Round 67 选择飞书作为第一个非 Telegram Channel,原因是官方 Server API 和事件订阅文档较完整,企业自建应用 + bot 的文本收发路径清晰。

当前已实现 `FeishuChannel` 插件和 webhook runtime,覆盖:
- `tenant_access_token` 获取。
- 通过 chat id 发送文本消息。
- 文本消息编辑 / 删除。
- URL verification challenge。
- `im.message.receive_v1` 文本事件转 `IncomingMessage`。
- `aico-feishu-webhook` FastAPI 入口,提供 `/healthz` 和默认 `/feishu/events` 事件回调。
- Feishu 事件幂等:2.0 事件按 `header.event_id` 去重,1.0 事件按 `uuid` 去重,默认本地保留 8 小时。

飞书启动示例:

```bash
export AICO_CHANNEL=feishu
export AICO_FEISHU_APP_ID="你的 Feishu App ID"
export AICO_FEISHU_APP_SECRET="你的 Feishu App Secret"
export AICO_FEISHU_VERIFICATION_TOKEN="你的 Verification Token"
export AICO_FEISHU_EVENT_PATH="/feishu/events"
export AICO_FEISHU_WEBHOOK_HOST="0.0.0.0"
export AICO_FEISHU_WEBHOOK_PORT=8080
export AICO_CLAUDE_WORKING_DIRECTORY="/Users/wangzq/VsCodeProjects/ai-company-os"
export AICO_PERSONA_CONFIG_PATH="config/personas.example.json"
export AICO_PROJECT_CONFIG_PATH="config/projects.example.json"
export AICO_AUDIT_LOG_PATH="/tmp/aico-audit.jsonl"
export AICO_MEMORY_PATH="/tmp/aico-memory.jsonl"
env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python /opt/homebrew/bin/python3.11 aico-feishu-webhook
```

Feishu 不是 long polling,需要把公网 HTTPS callback 转到本机或部署实例的 `http://<host>:8080/feishu/events`,然后在飞书开放平台事件订阅里配置这个 URL。URL verification 通过后,订阅 `im.message.receive_v1`,向机器人所在聊天发送文本,应能收到 AICO 的文本回复。Telegram 仍可继续用 `aico-phase1` 作为默认主控入口;飞书是独立 webhook 进程。

如果飞书事件日志显示重试,同一个 `header.event_id` 或 `uuid` 不应在 AICO 侧触发两次任务。该幂等缓存是进程内缓存,覆盖飞书常见重试窗口;进程重启后的极端重复投递仍可能重新进入 Orchestrator,后续如需要可升级为 audit / JSONL backed 去重。

本地排查同一份审计指标时可直接跑:

```bash
env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python /opt/homebrew/bin/python3.11 aico-metrics --audit-log "$AICO_AUDIT_LOG_PATH"
env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python /opt/homebrew/bin/python3.11 aico-metrics --audit-log "$AICO_AUDIT_LOG_PATH" --format json
env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python /opt/homebrew/bin/python3.11 aico-glance --audit-log "$AICO_AUDIT_LOG_PATH"
env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python /opt/homebrew/bin/python3.11 aico-glance --audit-log "$AICO_AUDIT_LOG_PATH" --format json
```

`aico-metrics` 不连接正在运行的 AICO 进程,只读取 audit JSONL,适合重启后排查历史指标和给后续本地 glance 原型消费 JSON。
`aico-glance` 同样只读取 audit JSONL,输出更紧凑的 Status Island 快照:active agents、open/running/waiting/failed、最近任务和可复制的 `/task` / `/approve` / `/reject` / `/interrupt` 命令。它适合先接 xbar/Swift 菜单栏原型,不替代 Telegram 主控台。

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
/metrics
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
/overnight 梳理当前项目下一步,早上给我 done/blocked/risks/next actions
/roles
/roles all
/role implementer
/role propose 需要一个增长分析岗位
/role confirm
/team
/who implementer
/appoint claude as tester
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
/remember Phase 7 记忆默认由 agent 主动维护
/recall phase 7
/forget <memory_id>
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

看本地运营指标时用 `/metrics`。当前会展示 `glance` 小节,快速说明 24h 内是否 `needs_approval` / `working` / `attention` / `quiet`,以及 open/running/waiting approval/failed 数;随后展示最近 24h / 7d 的任务总数、状态分布、agent/adaptor 接活数、open work、协作触发次数和平均终态耗时。若配置了 `AICO_AUDIT_LOG_PATH`,历史 done / failed / interrupted / rejected / waiting approval 指标会从 audit JSONL 恢复。token/cost 当前依赖底层 CLI 暴露能力,拿不到时会明确显示 unavailable。

Adapter 未来若能稳定提供 usage,应记录 `task_usage_recorded` 审计事件,`detail` 为 JSON:

```json
{"input_tokens":10,"output_tokens":20,"total_tokens":30,"cost_usd":0.03}
```

没有真实 usage 时不要估算或手填 token/cost;`/metrics` 和 `aico-metrics` 会继续显示 unavailable。

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
- `/agent <agent>` 查看角色、adapter、provider、capabilities、tools/skills 来源和 session 特性。输出末尾会给出简短 `Next` 指导命令,例如任命到 role 或创建 session。
- `/skills <agent>` 会把“列出你当前可用 skills”的只读问题路由给底层 provider 自己回答;AICO 不维护 skills registry。
- `/tools <agent>` 同理,由底层 provider 自己列出当前可调用工具。

当前 session 仍是 AICO 的薄门面,只保存 IM 侧 active session 和 provider session 引用位置;provider 的真实上下文仍由 Claude/Codex 自己保存,AICO 不复制对话历史。

Shared Memory 命令用于 Phase 7 记忆纠错和排障:
- `/remember <fact>` 把事实写入当前 active project scope;没有 active project 时会提示先 `/project <project>`。
- `/recall [query]` 查看当前项目未归档记忆,包含 memory id、scope、confidence、source 和 evidence 摘要。
- `/forget <memory_id>` 归档一条记忆,不物理删除 JSONL 历史;归档后普通项目任务不会再自动注入这条记忆。
- 老板自然消息里的明确偏好也会被自动抽取:带当前项目上下文时写入 project memory,无项目或全局表达时写入 boss global memory;语气不确定时先进入 `candidate`,不会注入后续 prompt。
- 日常主路径仍是 agent 在项目任务、交接、报告和后续抽取流程中主动维护记忆,老板只在需要纠偏、补充或验收时使用这些命令。
- 企业/团队管理验收重点:同一 project/team 能共享合同、法务、交付检查点等共识;其它 project 的敏感事实不会串入;lead agent 可把重要共识 broadcast 成 team memory;A2A `memory_refs + delta` 只是省 token 优化,必要时回退完整消息。
- `/recall` 和 Prompt Stack 召回使用可插拔语义 scorer。默认本地实现支持中文长句和常见中英项目术语,例如“法务检查”可召回 `legal review`;后续可替换为 embedding / LLM rerank。

Project Team / Appointment 命令用于项目办公室语义:
- `/projects` 查看配置中的项目列表;当前 active project 会以 `*` 标记。
- `/project [project]` 进入或查看项目办公室;已进入项目后发送 `/project` 会重新展示当前项目的 repo、阶段、默认接活角色和团队任命。
- `/brief [project]` 查看项目简报,包括 repo、阶段、团队、牵头 role、最近任务、最近审计事件,以及 north star / status / journal 文档短片段。顶部会尝试生成 `Boss summary`,下方 `Facts` 保留原始事实并渲染小节标题 / slash command 样式。
- `/risks [project]` 查看真正的项目交付风险,例如失败/中断任务、破坏性任务和 blockers / pitfalls 文档短片段;普通写文件审批和路由噪音不在这里展示。顶部会尝试生成 `Boss summary`,下方 `Facts` 保留原始事实并渲染小节标题 / slash command 样式。
- `/blockers [project]` 查看当前卡住的工作和待决策项,包括等待审批、失败/拒绝/中断任务、未知 persona 这类系统噪音,以及 blockers 文档短片段。顶部会尝试生成 `Boss summary`;如果 summary 不可用,原始 Facts 也会保留基础格式。
- `/next [project]` 查看下一步建议动作,优先提示待审批、失败任务、路由/配置问题;没有卡点时建议把任务交给当前 lead role。顶部会尝试生成 `Boss summary`,下方 `Facts` 保留原始事实并渲染小节标题 / slash command 样式。
- `/daily [project]` 查看日报式项目报告,聚合最近 24 小时本地 AICO 状态里的团队、完成项、未完成项、风险和项目文档短片段。顶部会尝试生成 `Boss summary`,下方 `Facts` 保留原始事实并渲染小节标题 / slash command 样式。
- `/weekly [project]` 查看周报式项目报告,聚合最近 7 天本地 AICO 状态里的团队、完成项、未完成项、风险和项目文档短片段。顶部会尝试生成 `Boss summary`,下方 `Facts` 保留原始事实并渲染小节标题 / slash command 样式。
- `/overnight <goal>` 创建 Phase 8 离线托管工单,把目标派给当前项目 lead/default role。它不是自动越权执行器;写文件、执行命令或破坏性动作仍会进入 `/approve`。早上用 `/daily <project>`、`/tasks`、`/task <id>` 验收。
- `/overnight` 不带目标时,展示当前 active project 在本进程内最近的托管工单和早报入口。
- `/project`、`/team`、`/roles`、`/role <id>` 这类查看命令末尾会给出简短 `Next` 指导命令,帮助顺手进入 brief/team/next/daily/weekly、appoint、ask、lead 等下一步。
- `/roles [project]` 查看紧凑项目岗位板,默认只展示核心/专家岗位;`/roles all` 展示支持岗位和全部 role。
- `/role <id>` 查看单个岗位详情,包括 owner、scope、approval 和 risk ladder;若该 role 已任命,可按 Next 提示用 `/appoint <agent> as <role> <scope>` 覆盖 scope。
- `/role propose <诉求>` 让当前项目 lead role 起草一个新岗位草案;系统会展示 role id、title、summary、默认权限、审批权限和 prompt。
- `/role confirm` 将上一条岗位草案加入当前项目的进程内 roles;不会直接写配置文件,重启后仍以配置文件为准。Telegram 中也可以点击岗位草案下方的 `Confirm` 按钮。
- `/role discard` 丢弃当前聊天里的待确认岗位草案。Telegram 中也可以点击岗位草案下方的 `Discard` 按钮。
- `/team [project]` 查看当前或指定项目的团队任命;输出会显示当前 lead,并在对应成员行标记 `[lead]`。
- `/who <role>` 查看当前项目某岗位由谁负责,以及权限、工作目录和内部 seat。
- `/appoint <agent> as <role> [scope]` 在当前项目里任命员工到岗位;不传 scope 时继承 role 默认 scope。同一项目的同一 role 只保留一个负责人,重复任命会覆盖而不是追加。当前实现是进程内 appointment,重启后仍以配置文件为准。
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

## 开源主 Demo:Release Room

主 demo 位于 `examples/release-room`,用于展示在 IM 中远程管理 AI team 完成小型
开源 CLI 的 v0.2 release。

```bash
export AICO_PROJECT_CONFIG_PATH="examples/release-room/aico-project.json"
export AICO_MEMORY_PATH="/tmp/aico-release-room-memory.jsonl"
export AICO_AUDIT_LOG_PATH="/tmp/aico-release-room-audit.jsonl"
```

按 [`docs/playbooks/release-room-demo.md`](../playbooks/release-room-demo.md) 执行。核心验收路径:

```text
/use project release-room
/team
/remember v0.2 不接受没有测试的功能。
/ask pm 阅读 STATUS.md 和 issues/003-v02-release.md，把 v0.2 拆成角色任务、验收标准和风险清单。
/ask implementer 实现 v0.2 的 tags/search/export JSON，修复 unknown id done 的退出码问题，并补测试。
/ask tester 根据 tests/test_v02_contract.py 设计回归验证，运行必要测试并报告失败项。
/ask reviewer review v0.2 release 风险，重点检查行为回归、测试缺口和 README/CHANGELOG 一致性。
/overnight 推进 v0.2 release room，早上给我 done/blocked/risks/next actions。
/daily release-room
/audit
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
