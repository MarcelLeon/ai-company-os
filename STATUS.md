# STATUS.md — 当前状态

> 这个文件高频更新。每一轮 AI 工作或人类工作结束都要更新这里。
> 阅读顺序:从上往下,前面的信息时效性最高。

**最后更新**:2026-05-18
**当前轮次**:Round 93(Release Room Stage 3 real GIF)
**当前阶段**:🟡 Phase 8 进行中 — 离线托管 + 开源主 Demo

---

## 项目宏大叙事(一句话)

把开发者 Mac 上散落的 AI 工具收编成一个可远程指挥的"虚拟公司",通过 IM 异步协作,让"AI 团队"成为开发者真正的生产力杠杆。

---

## 阶段地图

| 阶段 | 名称 | 状态 | 验收标准 |
|---|---|---|---|
| Phase 0 | 项目立项与文档体系 | 🟢 完成 | 文档体系建立,北极星确立 |
| Phase 1 | 核心协议与单 Adapter MVP | 🟢 完成 | 1 个 AI(Claude Code)能从 1 个 IM(Telegram)接收任务并返回结果 |
| Phase 2 | 多 Adapter + 状态机 | 🟢 完成 | 至少 2 个 AI 接入,状态可在 IM 中查询 |
| Phase 3 | 人格化层 + 群聊编排 | 🟢 完成 | AI 有差异化人设,群聊能 broadcast 任务 |
| Phase 4 | 审批与审计 | 🟢 完成 | 危险操作可推送审批,所有行为有 trace |
| Phase 5 | AI 间协作 | 🟢 完成 | AI 之间可以互相 @ 协作,任务编排成型 |
| Phase 6 | 可观测看板 | 🟢 完成 | 工时/KPI/token 消耗可视化 |
| Phase 7 | 共享记忆层 | 🟢 完成 | 所有 AI 共享上下文记忆 |
| Phase 8 | 离线托管模式 | 🟡 进行中 | 睡前下任务,早上看结果 |

图例:🟢 完成 / 🟡 进行中 / ⚪ 未开始 / 🔴 阻塞

---

## 近期高优产品方向

> 人类在 2026-05-07 明确:当前文档中的既有计划继续按进度推进,但近期要高优支持“更多可用 agents”和“更多 IM Channel”。

### A. Adapter 扩展:让 `/agents` 有更多真实成员

- [x] 新增 CodeFlicker Adapter MVP(可选启用、默认只读)。
- [x] 新增 Cursor Adapter MVP(可选启用、默认只读)。
- [x] Cursor / CodeFlicker 升级为审批保护下的完整 Adapter 能力(`code_edit` / `shell_exec`)。
- [x] 新增 Trae CLI Adapter(可选启用,完整能力走 AICO 审批门禁)。
- [x] 新增 Gemini CLI Adapter(可选启用,完整能力走 AICO 审批门禁)。
- [x] `/agents` / `/agent <agent>` 能展示这些新 Adapter 对应的可用 agent/persona,让 Telegram 里的“虚拟公司成员池”明显变丰富。
- [x] 保持可扩展可插拔:新增 Adapter 只能通过 `AIAdapter`、`AdapterRegistry`、persona/project 配置接入,不能在核心编排里写某个工具专属分支。
- [x] 为后续 OpenClaw 等 Adapter 留同样接入路径;先复制既有 Claude/Codex Adapter 模式,不要为了未来工具过早重构协议。
- [x] 进入实现前先做 CLI / API 形态核验,并补 Adapter mock 单测。
- [ ] Cursor / CodeFlicker / Trae / Gemini 真实 smoke test。

### B. Channel 扩展:降低 Telegram 单入口依赖

- [x] 从飞书、钉钉、QQ、微信中选择 1 个先接入:优先飞书。
- [x] Feishu Channel 第一切片:文本发送、编辑/删除、URL verification、`im.message.receive_v1` 文本事件解析。
- [x] Feishu webhook runtime:新增 `AICO_CHANNEL=feishu`、`aico-feishu-webhook`、`/healthz` 和可配置事件回调路径。
- [x] Feishu 事件幂等:按 v2 `header.event_id` / v1 `uuid` 做本地 TTL 去重,避免平台重试重复触发任务。
- [ ] 选择优先级按对接成本和协议标准化程度决定:官方 Bot/OpenAPI 是否稳定、是否支持文本收发、消息编辑或动作回调、鉴权/回调部署成本、群聊可用性、真实 dogfooding 门槛。
- [ ] 先做最小文本收发 + 平台无关 render contract 映射;如果目标 IM 不支持编辑消息或 inline action,Channel 内部降级为新消息/纯文本动作提示,核心不感知平台差异。
- [ ] 暂不承诺四个 IM 全量支持;QQ/微信等非标准或高摩擦协议只有在成本可控、合规明确后再进入实现。
- [x] 新 Channel 必须实现 `IMChannel`,并用 mock HTTP/API 测试覆盖入站解析、发送、编辑/降级和回调/动作入口。
- [ ] Feishu 开放平台真实 URL verification / 端到端 smoke test。

### C. Open-source Showcase:让用户第一眼理解 AICO

- [x] 选定主 demo 为 Release Room:在 IM 中远程管理 AI 团队完成小型开源 CLI 的 v0.2 release。
- [x] 新增 `examples/release-room/notes-cli` 示例仓库,包含 v0.1 可用 CLI、v0.2 issue、状态文档、journal、release notes 草稿和 release contract tests。
- [x] 新增 `examples/release-room/aico-project.json`,把 pm / implementer / tester / reviewer / release-manager 映射为项目团队 appointment。
- [x] 新增 `docs/examples/release-room.md`、`docs/playbooks/release-room-demo.md`、demo script 和录屏 storyboard。
- [x] 新增配置回归单测,确认 release-room config 能被当前 project assignment 模型加载,并指向完整示例仓库。
- [x] Stage 2:用 fake adapters 跑 release-room 本地端到端 transcript,覆盖 `/team`、`/remember`、`/ask`、`/approve`、`/overnight`、`/daily`、`/tasks`、`/metrics`、`/audit`。
- [x] Stage 3 录屏准备:把 transcript 压成 30-60 秒 shot rhythm,并补 `ffmpeg` GIF 转换脚本。
- [x] Stage 3 真实 Telegram dogfooding 第一段:project office、team、project memory、interrupt 跑通;provider 输出问题已记录为 B-003。
- [x] Stage 3 Codex 输出清理:修复跨 provider session resume、role 改任命 session 复用和 CLI warning/HTML 噪音入镜问题;真实 Telegram dry run 可用。
- [x] Stage 3:真实 IM + Claude/Codex dogfooding 录屏,生成 README 首页可嵌入 GIF。

---

## 当前进度详细

### Phase 0 进度

- [x] 北极星三句话确立
- [x] 文档体系骨架搭建
- [x] AGENTS.md / README.md / NORTH_STAR.md 三入口建立
- [x] journal 体系(ROUNDS / PITFALLS / BLOCKERS)初始化
- [x] 文档目录按 `docs/agent` / `docs/journal` / `docs/architecture` / `docs/human` 归位
- [x] 技术栈选型决策(ADR-0001:Python 3.11+ / FastAPI / asyncio / Pydantic v2)
- [x] 核心协议草案(Adapter 接口、IM 通道接口、任务消息格式)
- [x] 第一个 ADR(架构决策记录)输出
- [x] Python 工程基础设施(`pyproject.toml` / `uv.lock` / ruff / mypy / pytest)
- [x] CI 骨架(GitHub Actions 跑 pytest / ruff / mypy)

### Phase 1 进度

- [x] ADR-0002 Adapter / Channel 协议定稿
- [x] 最小 Router / TaskBus / Orchestrator 假链路
- [x] FakeChannel + FakeAdapter 端到端单测
- [x] Phase 1 MVP 范围 ADR / playbook 明确
- [x] Telegram Channel 文本 MVP
- [x] Claude Code Adapter MVP
- [x] Phase 1 本地启动入口
- [x] Telegram → 编排核心 → Claude Code → Telegram 真实链路验收

### Phase 2 进度

- [x] AdapterRegistry 多 Adapter 注册与按 persona 路由
- [x] `/status` 文本命令返回 Adapter 状态快照
- [x] Codex Adapter 文本 MVP(默认 read-only sandbox)
- [x] Telegram 中启用双 Adapter 后的真实状态查询验收
- [x] `/codex` / `@codex` / `codex:` 文本唤醒路由
- [x] 第二个真实 AI 任务链路验收
- [x] 更明确的任务状态机(running / done / failed / interrupted / rejected)

### Phase 3 进度

- [x] Phase 3 范围 ADR / Playbook
- [x] Persona 最小模型与注册表
- [x] `/broadcast <task>` 最小链路
- [x] Telegram 真实 persona / broadcast 验收
- [x] Persona 外部配置文件入口

### Phase 4 进度

- [x] Phase 4 范围 ADR / Playbook
- [x] 危险操作识别模型(`read_only` / `write_files` / `shell_exec` / `destructive`)
- [x] `waiting_approval` 任务状态
- [x] Telegram `/approve <task_id>` / `/reject <task_id>` 最小审批命令
- [x] 内存审计事件模型
- [x] `/audit` 最近审计事件只读查询
- [x] `/approve` / `/reject` 无 task id 快捷审批
- [x] 审批权限策略(默认 requester,可配置额外 reviewer)
- [x] Adapter 风险能力门禁(read-only Adapter 拒绝危险任务)
- [x] Claude Code 远程审批后免本机二次授权
- [x] `/audit` 多行可读输出
- [x] Telegram 真实审批 smoke test
- [x] 审计事件 JSONL 持久化

### Phase 5 进度

- [x] Phase 5 协作协议 ADR / Playbook
- [x] B-002 AI 间协作协议形态决策
- [x] 轻量 `@persona: request` 协作指令解析
- [x] Adapter 输出触发目标 persona 子任务
- [x] 协作任务审计事件增强
- [x] Agent Session / Harness 边界 ADR
- [x] Session 命令 MVP(`/sessions` / `/new` / `/use`)
- [x] Claude Provider Session Resume MVP
- [x] Codex `exec resume` 命令形态评估与 Adapter 构造支持
- [x] Telegram 流式输出 no-op edit 容错
- [x] Codex provider session 显式绑定命令(`/bind`)
- [x] Agent 能力体验命令(`/agents` / `/agent` / `/skills` / `/tools`)
- [x] Agent 能力体验命令 Telegram 真实验收(`/agents` / `/skills` / `/tools`)
- [x] `/agents` 默认展示改为工具入口名优先,避免岗位名和工具名混用。
- [x] `/agents` / `/agent` 输出追加短 Next 指导命令,引导查看详情、任命或创建 session。
- [x] Next 指导命令保留 Telegram 可识别的裸 `/command` 文本,避免富文本 code span 影响触碰发送。
- [x] Project Assignment Layer 设计决策(Agent / Project / Assignment)
- [x] 面向技术读者的架构图与核心概念工作流图(draw.io)
- [x] Project Assignment Layer MVP 第一切片(配置模型、项目命令、project-scoped session)
- [x] Project Team / Appointment 老板视角命令设计与 Role 体系完善
- [x] Project Team / Appointment 命令 MVP(`/project` / `/team` / `/who` / `/appoint` / `/ask` / `/lead`)
- [x] `/project` / `/team` 输出追加短 Next 指导命令,引导看 brief/team/next/daily/weekly、追问 role 或设置 lead。
- [x] Project roles view MVP(`/roles`)
- [x] Project roles view 紧凑化:默认只展示核心/专家岗位,详情进入 `/role <id>`,全量进入 `/roles all`。
- [x] `/roles` / `/role <id>` 输出追加短 Next 指导命令,引导查看 agent、appoint、ask、lead 或调整 scope。
- [x] Role proposal confirmation MVP(`/role propose` / `/role confirm` / `/role discard`)
- [x] Project unappoint MVP(`/unappoint`)
- [x] RoleTemplate / ProjectRoleOverride / Appointment 配置模型 MVP
- [x] Appointment Prompt Stack MVP
- [x] Project lead / role 普通咨询只按 `Current task` 做风险识别,避免 role prompt 中的 write/run 词误触发审批。
- [x] Project brief / risks MVP(`/brief` / `/risks`)
- [x] Project daily / weekly 本地报告 MVP(`/daily` / `/weekly`)
- [x] Project blockers MVP(`/blockers`)
- [x] Project next actions MVP(`/next`)
- [x] Project Team 本地验收流
- [x] Project appointment 同 role 去重与 `/team` lead 可见性
- [x] Project Team / Appointment Telegram 真实验收
- [x] Role proposal confirmation Telegram 真实验收
- [x] Orchestrator role proposal helper 拆分
- [x] Platform-neutral IM render contract 第一切片(`spans` / `actions`)
- [x] Project office key messages 使用 render hints
- [x] Telegram callback query 转入现有命令通路
- [x] Project status LLM summary MVP(`/brief` / `/risks` / `/blockers` / `/next`)
- [x] Project summary Markdown 转 render spans
- [x] Project report LLM summary MVP(`/daily` / `/weekly`)
- [x] Project status Facts 小节 / slash command render spans
- [x] IM 远程中断命令(`/interrupt`)
- [x] `/interrupt <task_id>` 可取消 `waiting_approval` 任务,用于清理未 approve/reject 的待审批项。
- [x] ProjectRoleCommandHandler 结构拆分
- [x] ProjectStatusCommandHandler 结构拆分
- [x] `/interrupt` Telegram 真实复验
- [x] `/blockers` Telegram 真实复验
- [x] Codex output idle timeout MVP
- [x] Project Facts bullet / inline Markdown render spans
- [x] Project Facts Markdown heading render spans
- [x] Task trace commands(`/tasks` / `/task`)
- [x] `/task` collaboration parent / child trace
- [x] Phase 5 feature complete handoff
- [ ] Telegram 真实协作 smoke test(作为 Phase 6 回归验收保留)
- [x] Prompt 分层渲染

### Phase 6 进度

- [x] ADR-0014 Phase 6 Observability Scope
- [x] IM-first `/metrics` MVP
- [x] MVP product entrypoints 判断(IM 主控 + macOS glance + CLI 排障)
- [x] Phase 6 `/metrics` smoke test playbook
- [x] ADR-0015 Observability Event Replay
- [x] audit JSONL 启动回放
- [x] `/metrics` audit-backed task snapshot 重建
- [x] MetricsReport 稳定查询模型(glance / summaries / token-cost 状态)
- [x] `aico-metrics` CLI text/json 排障入口
- [x] ADR-0016 Status Island and Usage Boundary
- [x] macOS Status Island / glance 数据原型(`aico-glance`)
- [x] token / cost usage 审计事件接入边界
- [x] Phase 6 无 token 本地验收样例:覆盖 `/metrics` live done / waiting approval / collaboration。
- [x] Phase 6 无 token 重启恢复验收:只从 audit JSONL 恢复 `/metrics` 历史指标。
- [x] Phase 6 无 token CLI/glance 验收:`aico-metrics` / `aico-glance` text+json 同源验证。
- [x] Phase 6 真实模型 token golden:Codex CLI 极简任务完成后验证 `/metrics` live、audit replay 和 `aico-metrics`。
- [x] `/metrics` Telegram 真实验收替代:无 token acceptance 覆盖 live `/metrics` 命令路径。
- [x] `/metrics` 重启后 Telegram 真实验收替代:audit JSONL replay acceptance 覆盖恢复路径。
- [x] 可观测状态持久化第一切片(audit replay)
- [x] Phase 6 集中真实验收通过后进入 Phase 7

### Phase 7 进度

- [x] ADR-0020 Phase 7 Shared Memory Scope
- [x] Phase 7 shared memory playbook
- [x] ADR-0021 Phase 7 记忆由 agent 主动维护,命令作为纠错和排障入口
- [x] ADR-0022 A2A Memory Fabric
- [x] A2A Memory Fabric 架构说明
- [x] MemoryAtom / MemoryStore 核心模型
- [x] JsonlMemoryStore 本地可审计记忆账本
- [x] `AICO_MEMORY_PATH` 配置入口
- [x] `/remember` / `/recall` / `/forget` IM 命令 MVP
- [x] Prompt Stack 读取当前项目少量高置信记忆
- [x] Boss feedback 自动抽取与 candidate 记忆 MVP
- [x] Team Broadcast 与 A2A memory refs 实验 MVP
- [x] Phase 7 共享记忆本地验收流

### Phase 8 进度

- [x] ADR-0024 Phase 8 Offline Delegation Scope
- [x] Phase 8 offline delegation playbook
- [x] `/overnight <goal>` 离线托管工单 MVP
- [x] `/overnight` 当前项目托管工单查看
- [x] 托管工单复用当前项目 lead/default role、appointment prompt、memory 和 provider session
- [x] 托管工单危险动作继续走 `/approve` 门禁
- [ ] 托管工单持久化与重启恢复
- [ ] 多 step / 多 agent 夜间自动编排
- [ ] 早报自动生成或定时推送

### 开源 Demo 进度

- [x] Release Room Stage 1 static package:示例仓库、项目配置、playbook、demo script、录屏 storyboard。
- [x] Release Room Stage 2 local acceptance transcript。
- [x] Release Room Stage 3 recording rhythm and GIF conversion path。
- [x] Release Room Stage 3 real Telegram dogfooding first pass, with provider-output blocker recorded。
- [x] Release Room Stage 3 Codex provider-output cleanup and real Telegram dry run。
- [ ] Release Room Stage 3 public GIF / README showcase。

---

## 上一轮做了什么

**Round 92**(2026-05-18,Codex):
- 对齐 Release Room GIF 卡点:确认 AICO 默认 Claude Adapter 已使用 Claude Code CLI (`claude -p`,本机版本 `2.1.143`);本机 `cc` 是 `/usr/bin/cc`,不是 Claude Code CLI。
- 定位 Codex 噪音根因:role 重新任命后 assignment session 复用旧 agent session,以及 Codex Adapter 对非 Codex provider session 也尝试 resume,导致 `thread/resume failed`;CLI warning/HTML/stdout 噪音又被原样流到 Telegram。
- 修复 `ClaudeCodeAdapter`:只在 provider session 名称匹配当前 adapter 时才使用 `--session-id` / `--resume`,并增加 stdout/error 处理 hook。
- 修复 `CodexAdapter`:忽略非 Codex provider session,过滤典型 Codex CLI warning、HTML 片段、`sqlx::query` 噪音和 thread resume error。
- 修复 `Orchestrator._ensure_assignment_session()`:同一 role 改任命到不同 agent/adapter 后关闭旧 assignment session 并重建,避免沿用旧 provider ref。
- 新增/更新单测:Codex 噪音过滤、跨 provider session 忽略、role 改任命后 session 重建。
- 真实 Telegram dry run 通过:重新 `/use project release-room`、`/appoint codex as pm docs audit`、`/ask pm Give a 3-bullet release plan...`,Telegram 只显示干净 3-bullet release plan,没有 warning/HTML/resume error。
- B-003 从 BLOCKING 调整为 DEFERRED:Codex 短输出镜头不再阻塞;Claude 长输出仍不建议入镜。

**Round 91**(2026-05-18,Codex):
- 继续执行 Release Room Stage 3 真实 Telegram dogfooding。
- 停掉重复 `aico-phase1` 实例,解决 Telegram `409 Conflict`;用真实 Telegram Bot API 启动单实例,并将 polling timeout 降到 3 秒避免 long-polling 空白 warning。
- 通过 Telegram App 发送 `/use project release-room`、`/team` 和 3 条 `/remember`,验证 project office、team lead、project-scoped memory 均能真实回包。
- 发送 `/ask pm ...` 后发现真实 Claude CLI 在当前无 Pro / 输出不稳定环境下长时间不回包;用 `/interrupt 4c0b914a` 成功中断任务,验证可中断性。
- 临时 `/appoint codex as pm docs audit` 后重试 PM 拆工,发现 Codex CLI 原始输出包含大量 plugin warning、HTML 片段和 thread resume 错误,不适合 public GIF 入镜。
- 新增 B-003 和 P-017,明确真实 provider 输出目前阻塞“直接录真实 Claude/Codex public GIF”;public showcase 应先走 transcript-driven 稳定素材。
- 新增 P-018 并修复日志安全问题:`configure_logging()` 将 `httpx` / `httpcore` 降到 WARNING,避免 INFO 日志把 Telegram Bot token URL 写进 `logs/aico.log`;补充 `test_phase1_logging_suppresses_http_client_info_logs`。
- Stage 3 真实 Telegram dogfooding 第一段完成,但 README GIF 仍未生成。

**Round 90**(2026-05-18,Codex):
- 按人类要求启动 Release Room Stage 3 的镜头节奏准备;人类环境为本机有 Telegram App、Claude CLI(无 Claude Pro)/Codex,没有单独 GIF 转换工具。
- 确认本机已有 `/opt/homebrew/bin/ffmpeg`,无需先安装 `gifski`。
- 新增 `examples/release-room/shot-rhythm.md`,把 Stage 2 transcript 压成 56 秒 README GIF 时间线:project office、shared memory、PM split、approval gate、independent checks、overnight handoff、daily/audit traceability。
- 新增 `examples/release-room/make-gif.sh`,用 `ffmpeg` palettegen/paletteuse 从 `.mov/.mp4` 转出 `docs/assets/release-room-demo.gif`,支持 `AICO_GIF_FPS` 和 `AICO_GIF_WIDTH`。
- 更新 release-room README、录屏 storyboard、examples 文档、playbook 和 CHANGELOG,把“无 gifski 也可转 GIF”的路径写清楚。
- Stage 3 真实 IM dogfooding / 录屏仍未完成;下一步是按 `shot-rhythm.md` 在 Telegram 中录 30-60 秒主 GIF,再嵌入 README。

**Round 89**(2026-05-18,Codex):
- 继续推进 Release Room Stage 2,把主 demo 从静态资产升级为本地可验收 transcript。
- 新增 `tests/unit/test_release_room_acceptance.py`,使用真实 `examples/release-room/aico-project.json`、`ProjectAssignmentDirectory`、`Orchestrator`、`TaskBus` 和 `JsonlMemoryStore`,只把底层 Claude/Codex 替换为 deterministic fake adapters。
- Stage 2 acceptance flow 覆盖:`/use project release-room`、`/team`、3 条 `/remember`、`/ask pm`、`/ask implementer`、`/approve`、`/ask tester`、`/ask reviewer`、`/ask release-manager`、`/overnight`、`/daily`、`/tasks`、`/metrics`、`/audit`。
- 验证点包括:team lead 可见、project memory 进入后续 PM/implementer prompt、implementer 写文件/跑测试任务先进入审批、审批后才派发、tester/reviewer 独立验收、overnight task 带 `offline_delegation` metadata、daily report 有 Boss summary、audit 记录 approval requested/approved。
- 新增 `examples/release-room/transcript.md`,作为无真实 token 的本地预览和后续 GIF/README 素材。
- 更新 release-room docs、playbook、README、STATUS 和 CHANGELOG,将 Stage 2 标记完成。
- 目标验证通过:`uv run pytest tests/unit/test_release_room_acceptance.py tests/unit/test_release_room_example.py`;示例仓库测试通过:`uv run pytest examples/release-room/notes-cli/tests`(2 passed,3 skipped);目标 `ruff check`、`ruff format --check`、`mypy` 通过。

**Round 88**(2026-05-18,Codex):
- 按人类反馈重做主 demo 方向:放弃“AI 开源维护者的一晚”这种单 issue demo,改成更能体现团队/角色/记忆/审批/审计/早报的 Release Room。
- 新增 `docs/examples/README.md` 和 `docs/examples/release-room.md`,明确主 demo 是“在 IM 中远程开一个 AI release room,管理 AI team 完成小型开源 CLI 的 v0.2 release”。
- 新增 `examples/release-room/notes-cli` 示例仓库:包含 v0.1 可运行 CLI、v0.2 release issue、STATUS/NORTH_STAR/journal、release notes 草稿、v0.1 测试和 v0.2 合约测试。
- 新增 `examples/release-room/aico-project.json`,配置 release-room 项目团队:pm、implementer、tester、reviewer、release-manager,并把 Claude/Codex 映射到对应 appointment。
- 新增 `examples/release-room/demo-script.md` 和 `recording-storyboard.md`,把 `/project`、`/team`、`/remember`、`/ask`、`/role propose`、`/overnight`、`/daily`、`/audit` 串成录屏脚本。
- 新增 `docs/playbooks/release-room-demo.md`,给出启动环境变量、IM 操作步骤、验证点和 fallback。
- README 和 playbook index 加入 Release Room 入口。
- 新增 `tests/unit/test_release_room_example.py`,验证 demo project config 能被当前模型加载,且示例仓库的项目办公室文档完整。
- 目标验证通过:`uv run pytest tests/unit/test_release_room_example.py`;示例仓库测试通过:`uv run pytest examples/release-room/notes-cli/tests`(2 passed,3 skipped);目标 `ruff check` 和 `ruff format --check` 通过。

**Round 87**(2026-05-18,Codex):
- 按人类要求启动 Phase 8,先做“睡前下任务,早上看结果”的第一切片。
- 新增 ADR-0024 `Phase 8 Offline Delegation Scope`,明确先做 project-scoped offline delegation work order,暂不做无人值守调度器或绕过审批的夜间授权。
- 新增 `/overnight <goal>` 命令:需要 active project,自动派给当前项目 lead/default role,复用 appointment prompt、shared memory、provider session 和现有 TaskBus。
- `/overnight` 不带目标时展示当前 active project 在本进程内最近托管工单,并提示 `/daily <project>`、`/tasks` 作为早报入口。
- 托管 prompt 要求 lead 留下 morning handoff:done、blocked、risks、next actions。
- 风险目标仍进入 Phase 4 审批门禁,例如 `/overnight update docs` 会返回 `Approval required`,不会因为“离线托管”而越权执行。
- 新增 `src/aico/core/offline_delegation.py` 和 Orchestrator 接线;扩展命令解析、help、daily ops、playbook、CHANGELOG 和 ADR 索引。
- 目标验证通过:`tests/unit/test_commands.py` 和 3 个 `/overnight` Orchestrator 单测;目标 `ruff`、`ruff format`、`mypy` 通过。

**Round 86**(2026-05-18,Codex):
- 在飞书开放平台真实 smoke 前补齐 webhook 生产化短板:事件回调幂等。
- 依据飞书事件结构和推送机制:2.0 事件使用 `header.event_id` 唯一标识,1.0 事件使用 `uuid`;平台失败重试和至少一次投递都可能导致重复事件。
- `FeishuChannel` 新增本地 TTL 去重缓存,默认保留 8 小时、最多 4096 个 event id。
- 重复事件不会再次派发给 Orchestrator,避免重复创建 AICO 任务或重复回复。
- 保持缺少 event id / uuid 的事件继续按原路径处理,避免因为非标准 payload 直接丢消息。
- 新增单测覆盖 v2 `event_id` 去重、v1 `uuid` 去重和 TTL 到期后允许重新处理。
- 目标验证通过:`tests/unit/test_feishu_channel.py`、`tests/unit/test_feishu_webhook.py`;目标 `ruff`、`ruff format --check`、`mypy` 均通过。

**Round 85**(2026-05-18,Codex):
- 按人类要求开发飞书 Channel,对齐当前 Telegram 的 runtime 接入形态。
- `Phase1Settings` 新增 `AICO_CHANNEL=telegram|feishu` 和飞书 App ID / App Secret / Verification Token / webhook host / port / path 配置。
- `build_phase1_runtime()` 现在按 channel 构造 `TelegramChannel` 或 `FeishuChannel`;Telegram 仍是默认主控入口。
- 新增 `aico-feishu-webhook` FastAPI 入口,提供 `GET /healthz` 和 `POST /feishu/events` 默认事件回调路由。
- 飞书 URL verification 会直接返回 challenge;`im.message.receive_v1` 文本事件进入现有 Orchestrator,复用项目、审批、记忆和报告能力。
- 新增 webhook 单测覆盖 healthz、URL verification 和 verification token 拒绝路径。
- 目标验证通过:`tests/unit/test_feishu_channel.py`、`tests/unit/test_feishu_webhook.py`、Feishu runtime 相关 `test_phase1_app.py`;目标 `ruff`、`ruff format --check`、`mypy` 均通过。
- 真实飞书开放平台 smoke test 仍需企业自建应用凭据和公网 HTTPS callback URL。

**Round 84**(2026-05-18,Codex):
- 按人类验收反馈升级 Phase 7 记忆召回:从关键词/子串过滤提升为可插拔 semantic scorer 排序。
- 新增 `MemorySemanticScorer` 接口和默认 `LocalSemanticMemoryScorer`,支持中文长句复述和常见中英项目管理术语别名。
- `JsonlMemoryStore.search()` 和 `MemoryRetriever` 改为按 scope 收集候选后进行 semantic score 排序;`MemoryGovernor` 继续负责 active / candidate / sensitivity / confidence 投影。
- 新增 ADR-0023 `Memory Semantic Retrieval`,明确后续 embedding / LLM rerank 只替换 scorer,不绕过 scope、governor 和 citation。
- 测试覆盖:“汇报当前项目进度,并告诉我还有几阶段”可召回“我更喜欢汇报进度时告诉我还有几阶段”;“法务检查”可召回英文 `legal review` 记忆。
- 验证通过:244 个单测、1 个 golden skipped、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check`。

**Round 83**(2026-05-18,Codex):
- 处理真实使用 `/remember` 时出现的 `Memory store is not configured. Set AICO_MEMORY_PATH first.`。
- 确认根因:当前运行的 `aico-phase1` 进程启动时没有配置 `AICO_MEMORY_PATH`,因此 Orchestrator 未注入 `JsonlMemoryStore`。
- 将 IM 报错改为可执行提示:说明需要在启动 `aico-phase1` 前设置 `AICO_MEMORY_PATH` 并重启,同时给出后续 `/use project` / `/remember` 操作。
- 更新 `docs/human/quickstart.md`,把 `AICO_PROJECT_CONFIG_PATH` 和 `AICO_MEMORY_PATH` 纳入快速启动环境变量,并补充 memory smoke 命令。
- 验证通过:242 个单测、1 个 golden skipped、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check`。

**Round 82**(2026-05-17,Codex):
- 完成 Phase 7 共享记忆本地验收流,新增 `tests/unit/test_phase7_memory_acceptance.py`。
- 验收流覆盖企业/团队管理常见场景:项目级合同/法务记忆、跨项目隔离、老板全局汇报偏好、项目级 candidate 反馈不注入、team broadcast 共识、JSONL 重启恢复、A2A `memory_refs + delta` 可关闭回退。
- 更新 Phase 7 playbook 和 daily ops,明确 `/remember` / `/recall` / `/forget` 是纠错/排障入口,老板日常主路径仍是自然管理项目和 agent。
- 记录 deterministic 中文检索边界:第一版是 scope + 子串/标签匹配,长中文句需要使用稳定关键词验收;语义检索留到后续增强。
- 验证通过:241 个单测、1 个 golden skipped、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check`。

**Round 81**(2026-05-17,Codex):
- 按 TDD 完成 Phase 7 Iteration 5:Team Broadcast 与 A2A memory refs 实验 MVP。
- 新增 `MemoryBroadcastService` 和 `MemoryBroadcastReceipt`,可把 project / boss / team 记忆广播为 team-scoped consensus atom。
- `JsonlMemoryStore` 增加 `get_atom()`,broadcast 服务会写入 team memory,并追加 `broadcast_to` edge 作为 receipt。
- broadcast 会拒绝跨 project team scope,避免把一个项目的记忆直接广播到另一个项目。
- project task Prompt Stack 召回 scope 增加 `team:<project>/default`,同 team agent 后续任务能自动看到广播共识。
- `collaboration_payload()` 新增可关闭的 `memory_refs + delta` 格式;无 refs 时回退原显式消息。
- 验证通过:240 个单测、1 个 golden skipped、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check`。

**Round 80**(2026-05-15,Codex):
- 按 TDD 完成 Phase 7 Iteration 4:Boss feedback 抽取与 candidate memory MVP。
- 新增 `MemoryCaptureService`,从老板自然消息中识别明确偏好/feedback,自动写入 `MemoryAtom`。
- scope 明确指向项目时写入 current project memory;无项目上下文或全局表达时写入 boss global memory。
- 语气不确定的反馈写成 `candidate`,不会进入 Prompt Stack;明确偏好写成 active。
- Orchestrator 在非命令消息路由前调用 capture service;命令仍走原处理链,避免把 `/remember` 等命令重复抽取。
- project task 召回 scope 扩展为 boss global + project + role + agent,让老板全局偏好能按 query 自动进入 agent prompt。
- 验证通过:235 个单测、1 个 golden skipped、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check`。

**Round 79**(2026-05-15,Codex):
- 按 TDD 完成 Phase 7 Iteration 3:IM 控制入口。
- 新增 `MemoryCommandHandler`,把 `/remember`、`/recall`、`/forget` 做成 project-scoped 纠错/排障入口,不调用 provider。
- `Phase1Settings` 新增 `AICO_MEMORY_PATH`;配置后 `aico-phase1` runtime 会创建 `JsonlMemoryStore` 并接入 Orchestrator prompt 自动召回。
- `/remember <text>` 默认写当前 active project scope;没有 active project 时提示先 `/project <project>`。
- `/recall [query]` 展示 claim、scope、confidence、source/evidence 摘要和短 Next。
- `/forget <memory_id>` 只归档 JSONL 记忆,不物理删除历史;测试覆盖归档后 prompt stack 不再注入。
- 验证通过:228 个单测、1 个 golden skipped、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check`。

**Round 78**(2026-05-15,Codex):
- 按 TDD 完成 Phase 7 Iteration 2:Prompt Stack 自动召回。
- 先新增红灯测试:
  - `MemoryRetriever` + `MemoryGovernor` 只能从指定 project/team scope 召回 active 且允许披露的记忆。
  - candidate、archived、restricted 或其它 project 记忆不会进入 `MemoryPacket`。
  - `render_appointment_prompt()` 会把 `MemoryPacket` 渲染到 `Current task` 之前。
  - Orchestrator 在 active project 普通任务中自动注入当前 project 记忆,且不会串入其它 project。
- 新增 `MemoryPacketItem`、`MemoryCitation`、`MemoryPacket`、`MemoryGovernor`、`MemoryRetriever`。
- `render_appointment_prompt()` 支持可选 `memory_packet`。
- `Orchestrator` 支持可选 `memory_store`,project-scoped task 会按 project/role/agent scope 自动召回少量受控记忆。
- 验证通过:memory、prompt_stack、orchestrator 目标单测,目标 ruff、目标 format check、目标 mypy。

**Round 77**(2026-05-15,Codex):
- 将 Phase 7 A2A Memory Fabric 拆成 5 个 TDD 迭代:
  - Iteration 1:MemoryAtom / MemoryScope / MemoryEvidence / MemoryEdge / JsonlMemoryStore。
  - Iteration 2:Prompt Stack 自动召回。
  - Iteration 3:/remember / /recall / /forget 控制入口。
  - Iteration 4:boss feedback 抽取与 candidate memory。
  - Iteration 5:team broadcast 与 A2A token-saving 实验。
- 按 TDD 完成 Iteration 1:
  - 先新增 `tests/unit/test_memory.py`,锁定 evidence、project/team scope、JSONL 恢复、archive 和 edge 持久化契约。
  - 新增 `src/aico/core/memory.py`,实现 `MemoryAtom`、`MemoryScope`、`MemoryEvidence`、`MemoryEdge`、`MemoryStore` Protocol 和 `JsonlMemoryStore`。
  - `JsonlMemoryStore` 使用 append-only JSONL 作为权威源,启动时重建内存索引;召回使用可插拔 semantic scorer。
- 验证通过:memory/model/audit 相关单测、目标 ruff、目标 format check、目标 mypy。

**Round 76**(2026-05-15,Codex):
- 按人类要求设计符合 A2A 的 Phase 7 记忆架构,参考 `attack-on-memory` 的 Memory Atom、evidence、scope、graph edge、time-window retrieval、selective disclosure 和 BranchWorldModel 思路。
- 新增 ADR-0022 `A2A Memory Fabric`,把 `/remember` / `/recall` 从孤立 IM 命令升级为 lead agent、team agent 和 boss 共享的记忆基础设施。
- 新增 `docs/architecture/a2a-memory-fabric.md`,定义 MemoryAtom、MemoryEvidence、MemoryScope、MemoryEdge、MemoryPacket、MemoryStore、MemoryRetriever、MemoryGovernor、MemoryCaptureService、MemoryBroadcastService。
- 明确记忆分层:boss global、project、team、role、agent working memory;默认禁止跨 project / team 共享。
- 明确四个核心场景:agent 间协作有记忆、boss 会话抽取偏好/feedback、team 共识广播、用 memory refs + MemoryPacket 试验减少 A2A 长消息传递。
- 本轮为文档/决策更新,未改代码。

**Round 75**(2026-05-15,Codex):
- 按人类明确基调修正 Phase 7 记忆层产品方向:记忆命令可以存在,但大比例触发应来自 agent,不是老板手动维护。
- 新增 ADR-0021 `Agent-Driven Memory Ownership`,确定 `/remember` / `/recall` / `/forget` 是纠错、补充、排障和验收入口,不是老板主工作流。
- 更新 Phase 7 playbook:agent 在任务完成、交接、风险确认、日报/周报沉淀时主动写入稳定事实;接项目任务前自动召回当前项目少量高置信记忆。
- 下一轮实现 Phase 7 第一切片时,验收不能只测三个 slash command,还要覆盖“老板自然发项目命令,agent 自动使用记忆”的路径。
- 本轮为文档/决策更新,未改代码。

**Round 70**(2026-05-14,Codex):
- 按人类要求让项目查看类命令更有指导性,减少“看完不知道下一步干嘛”的断点。
- 在查看类输出末尾追加短 `Next:` 指导命令:
  - `/agents`:提示 `/agent <agent>`、`/roles`、`/appoint <agent> as <role>`。
  - `/agent <agent>`:idle 时提示 `/roles`、`/appoint <agent> as <role>`、`/new <agent>`;非 idle 时提示 `/tasks`、`/status`、`/agent <agent>`。
  - `/project`:提示 `/brief`、`/team`、`/next`、`/daily`、`/weekly`。
  - `/team`:已有 lead 时提示 `/ask <lead-role> <task>`、`/who <lead-role>`、`/roles`、`/lead <role>`;无任命时提示 `/roles`、`/agents`、`/appoint <agent> as <role>`。
  - `/roles`:提示 `/role <role>`、`/agents`、`/appoint <agent> as <role>`、`/roles all`。
  - `/role <id>`:未任命时提示 `/agents`、`/appoint <agent> as <role>`、`/roles`;已任命时提示 `/ask <role> <task>`、`/lead <role>`、`/appoint <agent> as <role> <scope>`、`/unappoint <role>`。
- 没有新增新命令;role scope 调整先复用已有 `/appoint` 覆盖语义,避免过早设计 `/scope`。
- 新增/更新单测覆盖 project / team / roles / role / agents guidance。
- 验证通过:215 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check`。

**Round 69**(2026-05-13,Codex):
- 修复 project-scoped lead / role 普通咨询误触发审批的问题:
  - `render_appointment_prompt()` 会把 Agent、Role、Project、Appointment Contract 和 `Current task` 拼成完整 prompt。
  - 过去 `TextRiskAssessor` 扫整段 prompt,因此 role summary 里的 `write` / `run tests` 等词可能让“团队分工是什么?”这类只读问题进入 `waiting_approval`。
  - 现在风险识别在 appointment prompt 中只检查 `Current task:` 之后的真实用户请求;如果真实请求要求 `run pytest` / `update STATUS.md` 等,仍会触发审批。
- 修复待审批任务清理体验:
  - `/interrupt <task_id>` 现在可以取消 `waiting_approval` 任务,会把任务状态记为 `interrupted`,并移出 pending approval 队列。
  - 多个 pending approvals 时,用户可以用 `/interrupt <short_task_id>` 清理不想执行的项,再继续 `/approve <short_task_id>` 或 `/reject <short_task_id>`。
- 新增回归测试覆盖:
  - appointment prompt scaffolding 中出现 write/run 时,只读团队/项目问题不触发审批。
  - `Current task` 真实要求执行命令或更新文件时仍触发审批。
  - `/interrupt` 可取消 `waiting_approval` 并记录 approval rejected / task interrupted 审计事件。
- 验证通过:212 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check`。

**Round 68**(2026-05-13,Codex):
- 按人类反馈收敛 `/agents` / `/roles` 的产品语义:
  - `/agents` 现在优先展示工具入口名,如 `claude -> claude-code [role: implementer]`,避免 `implementer` / `reviewer` 与 `cursor` / `codeflicker` 混在同一命名层。
  - `/roles` 默认变为紧凑岗位板,只展示 Core / Specialists;`tester`、`docs`、`ops`、`analyst`、`designer` 等支持岗位默认隐藏到 `/roles all`。
  - 新增 `/role <id>` 详情视图,展示 owner、scope、approval 和 risk ladder。
- 收敛权限词表为三层:
  - Adapter capability: `code_review` / `code_edit` / `shell_exec` / `long_running` / `stream_output` / `interruptible`。
  - Role scope: `docs` / `code` / `tests` / `ops` / `audit`。
  - Risk level: `read_only` / `write_files` / `shell_exec` / `destructive`。
- `/appoint <agent> as <role>` 不传 scope 时,现在自动继承 role 默认 scope。
- 新增 ADR-0019,明确本轮不是引入完整 RBAC;role scope 仍是岗位契约,真实危险动作继续由 risk assessor、adapter capability 和 `/approve` 控制。
- 验证通过:208 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check`。

**Round 67**(2026-05-12,Codex):
- 按人类要求把 Cursor / CodeFlicker 从“可选只读 MVP”升级为审批保护下的完整能力:
  - Cursor 默认命令改为 `cursor-agent -p --force --output-format text`。
  - CodeFlicker 默认命令改为 `flickcli -q --approval-mode yolo --output-format text`。
  - 两者 capabilities 现在包含 `code_edit` / `shell_exec`;写文件、shell、destructive 任务仍先走 AICO 风险识别和 `/approve`。
- 新增 `TraeAdapter`:
  - 默认命令 `trae-cli --print --yolo`。
  - 通过 `AICO_ENABLE_TRAE_ADAPTER=true` 启用。
  - 支持 AICO provider session 新建 / resume 元数据映射到 `--session-id` / `--resume`。
- 新增 `GeminiAdapter`:
  - 默认命令 `gemini --approval-mode yolo --output-format text`。
  - 通过 `AICO_ENABLE_GEMINI_ADAPTER=true` 启用。
  - 支持已绑定 provider session 用 `--resume` 继续。
- 默认 AI Company role 模板扩充 PM、Senior Architect、Golden Tester、Market Risk、Legal Compliance,并保留 implementer / reviewer / tester / security / docs / ops / analyst / designer 等有明确 AI 公司产出的岗位。
- 在飞书、钉钉、QQ、微信中选择飞书作为第一个非 Telegram Channel:
  - 新增 `FeishuChannel`,覆盖 tenant token、文本发送、编辑/删除、URL verification、`im.message.receive_v1` 文本事件解析。
  - 新增 Feishu Channel playbook;真实公网 callback server 留给下一轮部署层切片。
- 新增 ADR-0018,记录完整 Adapter 能力、role 扩充和 Feishu Channel 选择。
- 验证通过:207 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`。
- 本机 CLI 状态:
  - `cursor-agent` 当前未安装。
  - `flickcli` 已存在,help 确认支持 `--approval-mode`、`--cwd`、`--tools`、`--output-format`。
  - `trae-cli` 已存在,help 会先报本机 keyring token store 不支持,但随后展示 `--print`、`--yolo`、`--session-id`、`--resume`。
  - `gemini` 已存在,help 确认支持 `--approval-mode`、`--output-format`、`--resume`。

**Round 66**(2026-05-07,Codex):
- 按近期高优方向启动 Adapter 扩展第一切片。
- 新增 ADR-0017,确定 Cursor / CodeFlicker 先作为可选只读 Adapter 接入,默认不授予写文件或 shell 能力。
- 新增 `CursorAdapter`:
  - 默认命令 `cursor-agent -p --output-format text`。
  - 通过 `AICO_ENABLE_CURSOR_ADAPTER=true` 启用。
  - 启用后内置 persona `cursor` 会进入 `/agents`。
- 新增 `CodeFlickerAdapter`:
  - 默认命令 `flickcli -q --output-format text --tools '{"bash":false,"write":false}'`。
  - 通过 `AICO_ENABLE_CODEFLICKER_ADAPTER=true` 启用。
  - 启用后内置 persona `codeflicker` 会进入 `/agents`。
  - 有 `AICO_CLAUDE_WORKING_DIRECTORY` 时会在命令中补 `--cwd <path>`。
- 新增单测覆盖两个 Adapter 默认命令、能力边界、CodeFlicker `--cwd` 注入和 `aico-phase1` 可选启用路径。
- 新增 `docs/playbooks/optional-agent-adapters.md`,记录 Cursor / CodeFlicker 真实 smoke test 步骤。
- 本机核验:
  - `cursor-agent` 当前未安装,所以 Cursor 真实 smoke test 待安装登录后执行。
  - `flickcli` 已存在,版本 `0.5.1`,help 确认支持 `-q`、`--cwd`、`--tools` 和 `--output-format`。
- 验证通过:193 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check`。

**Round 65**(2026-05-07,Codex):
- 人类补充近期方向:既有 Phase 6 / Phase 7 计划继续推进,但近期要高优支持更多 Adapter 和更多 IM Channel。
- 已把近期高优方向记录到 `STATUS.md`:
  - Adapter 扩展:优先 CodeFlicker Adapter、Cursor Adapter,目标是让 Telegram `/agents` 出现更多真实可用 agents,并保持可插拔,为 Trae、OpenClaw 等后续 Adapter 留同一路径。
  - Channel 扩展:从飞书、钉钉、QQ、微信里按对接成本和协议标准化程度选择 1-2 个先做,不追求一次性全量接入。
- 决策边界:本轮只记录计划,不做实现;后续实现前需要核验目标工具/IM 的最新官方 CLI/API/Bot 能力,并分别补 ADR/playbook/mock 测试。

**Round 64**(2026-05-07,Codex):
- 人类要求把 Phase 6 规划的核心能力都开发完,随后集中验收,验收通过后进入 Phase 7。
- 补齐 Phase 6 代码侧核心能力:
  - 新增 ADR-0016,明确 Phase 6 不做完整 Mac GUI / Web dashboard,先完成 `aico-glance` 数据原型和 usage 审计事件接入边界。
  - 新增 `StatusIslandSnapshot` / `StatusIslandTask`,从 `MetricsReport` 生成本地 glance 视图,包含 active agents、open/running/waiting/failed、最近任务和 `/task` / `/approve` / `/reject` / `/interrupt` 命令提示。
  - 新增 `aico-glance` CLI,支持从 `--audit-log` 或 `AICO_AUDIT_LOG_PATH` 读取 audit JSONL,输出 text 或 JSON,供 macOS/xbar/后续原生菜单栏原型消费。
  - 新增 `task_usage_recorded` 审计事件类型、`usage_audit_detail()` 和 `usage_records_from_audit_events()`,Adapter 未来上报真实 usage 后即可汇总 token/cost。
  - `MetricsReport.token_cost` 在有 usage 审计事件时展示 input/output/total tokens 和 cost;没有真实 usage 时继续明确 unavailable。
- 新增单测覆盖:
  - Status Island snapshot text/json 与动作命令。
  - `aico-glance` text/json 输出。
  - usage audit detail 解析与 token/cost 汇总。
- 验证通过:184 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check`。
- 当前 Phase 6 代码侧核心能力已完成;剩余是集中真实验收项。

**Round 63**(2026-05-07,Codex):
- 继续 Phase 6 观测模型收口,先不做 Mac GUI / Web API,把 `/metrics` 背后的数据模型提炼为可复用结构:
  - 新增 `MetricsReport` / `MetricsGlance` / `TokenCostSummary`,统一承载 generated_at、source、24h/7d summaries、glance 状态和 token/cost unavailable 原因。
  - `/metrics` 改为渲染 `MetricsReport`,新增 `glance` 小节,快速显示 `needs_approval` / `working` / `attention` / `quiet` 与 open/running/waiting/failed 数。
  - 新增 `metrics_report_to_dict()`,为后续 macOS Status Island / Web / 脚本消费提供稳定 JSON 形态。
  - 新增 `aico-metrics` CLI,可从 `--audit-log` 或 `AICO_AUDIT_LOG_PATH` 读取 audit JSONL,输出 text 或 JSON,作为 CLI 排障与本地 glance 原型的数据入口。
- 新增单测覆盖:
  - Metrics report glance 和 token/cost unavailable 状态。
  - Metrics JSON 序列化中的枚举 / 时间字段。
  - `aico-metrics` text/json 输出。
  - `/metrics` IM 输出中的 glance 小节。
- 验证通过:179 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check`。

**Round 62**(2026-05-07,Codex):
- 人类暂时没空验收新功能,要求先继续迭代,明天白天再验收能力。
- 继续 Phase 6 可观测持久化第一切片:
  - 新增 ADR-0015,决定先复用 audit JSONL replay,不新增 task snapshot JSONL 或 SQLite。
  - `InMemoryAuditLog` 支持 `initial_events`,启动时可注入历史审计事件。
  - 新增 `read_jsonl_audit_events(path)`,从 `AICO_AUDIT_LOG_PATH` 读取历史 JSONL 审计事件。
  - `aico-phase1` 配置 `AICO_AUDIT_LOG_PATH` 后,启动时会回读旧审计事件。
  - `/metrics` 会从 audit events 重建 metrics 用 task snapshot,并与当前进程内 task snapshot 合并;当前进程内状态优先。
- 新增单测覆盖:
  - audit JSONL 读取与恢复。
  - 从 audit events 重建 task snapshot 最新状态。
  - `/metrics` 同时统计重启前 audit 恢复任务和当前进程内 open work。
  - phase1 runtime 启动时加载已有 audit JSONL。

**Round 61**(2026-05-07,Codex):
- 人类认为 `/task` parent / child trace 用户价值不大,询问 Phase 5 是否还有大功能,并同意进入 Phase 6。
- 已提交并推送 Phase 5 收口提交:`031e41e Complete phase 5 collaboration observability`。
- 开启 Phase 6:
  - 新增 ADR-0014,确定第一切片先做 IM-first `/metrics`,不直接跳 Mac GUI / Web dashboard。
  - 新增 `src/aico/core/metrics.py`,基于当前进程内 `TaskSnapshot` / `AuditEvent` 汇总 24h / 7d 指标。
  - 新增 `/metrics` 命令,展示任务数、状态分布、agent/adaptor 接活数、open work、协作次数和平均终态耗时;token/cost 当前明确显示 unavailable。
  - 记录 MVP 产品入口判断:IM 主控 + macOS glance + CLI 排障;Mac 状态岛后续消费 Phase 6 指标模型。
  - 新增 Phase 6 `/metrics` smoke test playbook。
- 新增命令解析和 Orchestrator 单测覆盖 `/metrics` 不派发 Adapter 任务。

**Round 60**(2026-05-06,Codex):
- 人类已验证 `/task` / `/tasks` 相关命令,要求继续后续功能开发。
- 增强 `/task <task_id>` 协作追踪详情:
  - child task 详情会展示 `requested by` 和 parent task 的 `/task <short_id>` 入口。
  - parent task 详情会展示已触发的 child task 列表、目标 persona 和对应 `/task <short_id>` 入口。
  - 该能力复用既有 `collaboration_requested` 审计事件,没有改 TaskBus 存储模型或引入新仓储。
- 新增 Orchestrator 单测覆盖 `@reviewer` 协作后查询 parent / child task 详情。
- 定向验证通过:43 个 `test_orchestrator.py` 单测、改动文件 `ruff check`。

**Round 59**(2026-05-06,Codex):
- 人类在 Telegram 验证 Project Facts heading render 效果良好,要求继续开发后续能力。
- 新增 IM 任务追踪命令:
  - `/tasks [limit]`:展示最近任务,默认 10 条,最多 20 条。
  - `/task <task_id>`:支持完整或短 task id 前缀,展示单个任务详情。
  - waiting approval 任务会给出 `/approve <short_id>` / `/reject <short_id>` 动作提示。
  - running 任务会给出 `/interrupt <short_id>` 动作提示。
- `TaskBus` 新增只读 `task_snapshot(task_ref)` 查询入口,复用既有 task id 前缀匹配语义。
- 更新 help、daily ops 和 changelog;新增命令解析与 Orchestrator 单测。
- 完整验证通过:170 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check`。

**Round 58**(2026-05-06,Codex):
- 人类复验 `/brief` 后反馈整体好了很多,但文档 snippet 中的 Markdown 标题仍裸露,截图中可见 `# NORTH_STAR.md`、`## 第一句`、`### 状态变化`。
- 修复 Project Facts Markdown heading 渲染:
  - `_heading_message()` 现在会识别行首 `#` / `##` / `###` 等 Markdown 标题。
  - 标题会去掉 `#` 前缀,保留原标题文本并生成 `MessageTextSpan(BOLD)`。
  - 该能力作用于 `/brief`、`/risks`、`/blockers`、`/next`、`/daily`、`/weekly` 的 facts 文档片段。
- 新增单测覆盖文档 snippet 中的 Markdown heading 渲染。
- 完整验证通过:166 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check`。

**Round 57**(2026-05-06,Codex):
- 人类复测 Phase 5 `@reviewer` 真实协作 smoke test:
  - Telegram 收到 `Task accepted: 1481a413-f886-46bc-b7d4-98cccf295218 [reviewer]`。
  - `/status` 显示 `claude-code: idle`, `codex: busy`。
  - 结论:协作解析和 child task 创建成功,卡点仍是 Codex CLI accepted 后长期无 stdout。
- 修复 Codex busy 自动释放:
  - `ClaudeCodeAdapter` 增加可选 `output_idle_timeout_seconds`。
  - `CodexAdapter` 默认 90 秒无 stdout 自动终止底层 CLI,输出 `adapter output idle timeout after 90s`,并释放 busy。
  - `Phase1Settings` 新增 `AICO_CODEX_OUTPUT_IDLE_TIMEOUT_SECONDS`。
- 修复 Project Facts 无序列表 / inline Markdown 渲染:
  - `_heading_message()` 现在会规范化 facts 中的 `- ` / `* ` 为 `• `。
  - facts 中 `**bold**`、`` `code` ``、`*italic*` 也会转成 render spans,不再裸露 Markdown 标记。
- 更新 PITFALL P-014、Phase 5 collaboration playbook 和 daily ops。
- 完整验证通过:165 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check`。

**Round 56**(2026-05-06,Codex):
- 人类已完成真实复验:
  - `/interrupt` 可用。
  - `/blockers` 格式可用。
- 收口 Round 55 的结构拆分验证:
  - `ProjectStatusCommandHandler` 拆分后仍保持 `/brief`、`/risks`、`/blockers`、`/next`、`/daily`、`/weekly` 用户语义不变。
  - 完整验证通过:162 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check`。
- 代码侧下一步不建议继续堆项目命令;若继续开发,优先二选一:
  - 完成 Phase 5 `@reviewer` collaboration smoke test,若 Codex 子任务仍无 stdout,再设计 timeout / heartbeat。
  - 拆 Project team/assignment handler,继续降低 `ProjectCommandHandler` 门面复杂度。

**Round 55**(2026-05-06,Codex):
- 人类要求继续开发后续功能;真实复验仍需人类重启 AICO 服务并在 Telegram 操作。
- 继续处理 Project 命令结构债:
  - 新增 `ProjectStatusCommandHandler`,承接 `/brief`、`/risks`、`/blockers`、`/next`、`/daily`、`/weekly`。
  - 状态 / 报告 handler 集中负责本地 facts 构造、文档 snippet 聚合、summary callback 和 summary 失败降级。
  - `ProjectCommandHandler` 保持 Orchestrator 的项目命令门面,对应 handle 方法改为薄代理。
- 结构结果:
  - `src/aico/core/project_commands.py` 从 476 行降到 349 行。
  - `src/aico/core/project_status_commands.py` 为 195 行。
  - `src/aico/core/project_role_commands.py` 保持 108 行。
- 完整验证已在 Round 56 补齐。

**Round 54**(2026-05-06,Codex):
- 人类要求继续开发;真实 `/interrupt`、Project status render 和 Phase 5 collaboration smoke 复验都需要人类重启服务和 Telegram 操作。
- 按下一轮代码侧高优先级处理结构债:
  - 新增 `ProjectRoleCommandHandler`,承接 `/role propose`、`/role confirm`、`/role discard` 以及 role draft 暂存。
  - `ProjectCommandHandler.handle_role()` 改为薄代理,用户可见语义不变。
  - `ProjectCommandHandler` 不再持有 `_role_drafts` 和 `_propose_role` 运行细节。
- 结构结果:
  - `src/aico/core/project_commands.py` 从 544 行降到 475 行。
  - `src/aico/core/project_role_commands.py` 为 108 行。
- 完整验证通过:162 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`。

**Round 53**(2026-05-06,Codex):
- 人类执行 Phase 5 协作 smoke test 后反馈:
  - Telegram 收到 `Collaboration requested: claude -> reviewer`。
  - 随后停在 `Task accepted: 31e559c3-bd7c-4e1b-9385-024431f8635a [reviewer]`。
- 日志定位:
  - 协作解析和 child task 创建成功。
  - reviewer 子任务已派发到 `codex`,并进入 `Stream start`。
  - 没有后续 `Stream output` / `Adapter process exited`,进程表显示 Codex CLI 子进程仍在运行。
  - 根因不是 Telegram render 或协作协议,而是底层 Codex CLI 长时间无 stdout。
- 修复远程可中断缺口:
  - 新增 `/interrupt <task_id>` 命令。
  - `TaskBus.interrupt()` 支持 task id 前缀匹配,会拒绝 unknown / ambiguous / non-running task。
  - Orchestrator 返回 `Task interrupted: <short_id>` 或明确失败原因。
  - 中断 running 任务会继续更新 `interrupted` 状态并记录 `task_interrupted` 审计事件。
- 新增 PITFALL P-014,记录 reviewer accepted 后 Codex 长时间无 stdout 且 IM 无中断入口的问题。
- 更新 Phase 5 collaboration playbook 和 daily ops。
- 验证通过:定向 66 个单测;完整验证见本轮交接。

**Round 52**(2026-05-06,Codex):
- 人类补充真实 Telegram 验收结果:
  - `/project`、`/team`、`/roles` 首行加粗和 `/role propose` Confirm / Discard 按钮均已验证通过。
  - `/blockers` 仍缺少格式。
  - `/brief`、`/next` 的 `Boss summary` 部分格式正确,但 `Facts` 部分缺少结构化样式。
- 修复项目状态 Facts 渲染:
  - `_heading_message()` 不再只给首行加粗,会为项目消息中的小节标题生成 `MessageTextSpan(BOLD)`。
  - 对事实文本里的 slash command 片段生成 `MessageTextSpan(CODE)`,例如 `/approve`、`/reject`、`/ask`、`/blockers`。
  - `project_summary_message()` 继续把 facts spans 平移到 `Facts` 区域,因此 summary + facts 组合消息也能保留 facts 样式。
- 新增 `tests/unit/test_project_messages.py` 覆盖 `/blockers` 小节 / 命令 spans,以及 summary 组合消息保留 facts spans。
- 在 `docs/human/daily-ops.md` 补充 Phase 5 `@reviewer` 真实协作 smoke test 推荐 prompt。
- 验证通过:159 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`。

**Round 51**(2026-05-06,Codex):
- 人类验证 `/brief` 等 Boss summary 能力有效,指出主要问题是 summary 内部 `**bold**`、反引号、无序列表等 Markdown 文法没有渲染。
- 修复 `project_summary_message()`:
  - summary 里的 `- ` / `* ` 列表前缀转换为 `• `。
  - `**bold**` 转为干净文本 + `MessageTextSpan(BOLD)`。
  - `` `code` `` 转为干净文本 + `MessageTextSpan(CODE)`。
  - `*italic*` 转为干净文本 + `MessageTextSpan(ITALIC)`。
  - 继续保留 `Boss summary` / `Facts` heading spans 和完整 Facts 原文。
- 在已验证短状态 summary 基本可用后,将同样 summary 机制扩展到 `/daily` / `/weekly`;仍保留完整 Facts。
- 新增 `tests/unit/test_project_messages.py`,覆盖 summary Markdown 到 spans 的转换。
- 本地定向测试已通过;完整验证见本轮交接。

**Round 50**(2026-05-06,Codex):
- 人类确认 Round 49 的 Telegram render / button 能力有效,要求继续开发后续能力。
- 新增 `ProjectSummaryCoordinator`,为 `/brief`、`/risks`、`/blockers`、`/next` 生成顶部 `Boss summary`:
  - 输入只使用现有本地事实消息。
  - 通过当前项目 lead appointment/provider session 发起只读 summary task。
  - 输出保留完整 `Facts` 原文,摘要只是顶部管理视角说明。
- 新增 `aico.intent=project_summary` 内部元数据,风险识别将 project summary task 视为 read-only,避免事实文本中出现 `/approve`、`run tests`、`write docs` 等词时误触发审批。
- summary task 如果没有 lead、provider busy、adapter 拒绝或输出失败,命令会直接发送原本的事实消息,不让摘要失败影响状态查询。
- `project_summary_message()` 会把 `Boss summary` 和 `Facts` 作为独立 heading span,Telegram 可加粗展示。
- 本轮未给 `/daily` / `/weekly` 加 LLM summary,避免扩大范围;它们仍是本地事实报告。
- 本地 156 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests` 全绿。

**Round 49**(2026-05-06,Codex):
- 按下一轮最高优先级,将 ADR-0013 的 IM render contract 用到项目办公室关键消息。
- `project_messages.py` 为项目办公室、团队、岗位、任命、撤任、lead、role proposal 等消息首行增加 `MessageTextSpan(BOLD)`,Telegram 会映射为 HTML 加粗;纯文本 `text` 保持不变。
- `role_proposal_message()` 增加 `MessageAction`:
  - `Confirm` → `/role confirm`
  - `Discard` → `/role discard`
- Telegram Channel 支持 `callback_query`:按钮点击会被转换为 `IncomingMessage(content.text=<callback data>)`,复用现有命令解析;同时调用 `answerCallbackQuery` 避免 Telegram 客户端一直转圈。
- 新增回归测试覆盖 role proposal actions 和 callback query 转入命令消息。
- 本地 154 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests` 全绿。

**Round 48**(2026-05-05,Codex):
- 人类确认 Project Team / Appointment 与 Role proposal confirmation 的真实 Telegram 验收均已通过:
  - 重复 `/appoint ... as tester ...` 不再让 `/team` 出现多个 tester。
  - `/lead tester` 后 `/team` 能看到 lead。
  - `/role propose` 后 `/role confirm`,新增 role 能在 `/roles` 中看到。
- 按下一轮高优先级先做结构拆分,新增 `RoleProposalCoordinator`,把 role proposal 的内部任务提交、输出收集、provider session busy/idle 和 JSON 解析流程从 `Orchestrator` 移到 `src/aico/core/role_proposal.py`。
- `Orchestrator` 只保留接线逻辑,类体从 482 行降到 439 行,继续满足单类 <500 行硬约束。
- 修复拆分时暴露的 `risk -> role_proposal -> task_bus -> risk` 循环导入,`TaskBus` 在 role proposal 模块中改为 type-checking only import。
- 本轮没有改变 `/role propose`、`/role confirm`、`/role discard` 的用户可见语义。
- 继续完成 IM 文案渲染层第一切片: `MessageContent` 增加平台无关 `MessageTextSpan` / `MessageAction`,Telegram Channel 将 spans 映射为 HTML、actions 映射为 inline keyboard;纯文本消息不变。
- 新增 ADR-0013,记录不把 Telegram HTML / reply_markup 写进核心消息层的决策。
- 本地 153 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests` 全绿。

**Round 19**(2026-04-28,Codex):
- 调研 A2A / ACP / MCP 当前状态,决定 Phase 5 MVP 采用内部 A2A-inspired 轻量协作指令,不直接实现 HTTP A2A。
- 新增 `src/aico/core/collaboration.py`,支持解析 Adapter 输出中的 `@persona: request`。
- `Orchestrator` 识别协作指令后创建目标 persona 子任务,复用现有 TaskBus、审批、审计和状态机。
- 默认 implementer persona 提示增加 reviewer 协作指令说明。
- 新增 ADR-0009 和 Phase 5 playbook,并解决 B-002。
- 本地 88 个单测、`ruff check`、`ruff format --check`、`mypy` 全绿。

详见 [`docs/journal/ROUNDS.md`](docs/journal/ROUNDS.md)

**Round 20**(2026-04-28,Codex):
- 人类真实测试发现 `@reviewer review一下...` 没触发 Codex/reviewer,因为协作解析只支持 `@reviewer: ...` 冒号语法。
- 协作指令解析扩展为同时支持 `@persona request` 和 `@persona: request`,仍要求行首触发以避免误判。
- 修复 Telegram polling 串行 await 长任务 handler 的问题;现在每条 incoming message 会后台分发,长任务运行时 `/status` / `/audit` 不再被 polling 阻塞。
- 新增 PITFALL P-008 / P-009,更新 Phase 5 playbook 和 daily ops。
- 本地 90 个单测、`ruff check`、`ruff format --check`、`mypy` 全绿。

**Round 21**(2026-04-28,Codex):
- 人类真实使用中发现 Telegram 长文本只收到部分信息。
- 定位为流式输出持续编辑同一条消息,超过 Telegram 4096 字符限制后 Bot API 失败,handler 中断。
- 新增 `StreamedMessageWriter`,按 3900 字符保守上限拆分长输出;当前消息装满后继续发送下一条消息,避免内容被截断。
- 梳理并向人类说明 AICO 对 prompt 的实际加工:路由前缀剥离、persona role instruction 前置、协作子任务 payload 包装、协作指令行消费、Claude/Codex CLI 权限参数差异。
- 新增 PITFALL P-010,更新 troubleshooting / daily ops / playbook / changelog。

**Round 22**(2026-04-29,Codex):
- 新增 `collaboration_requested` 审计事件,在 AI 间协作触发 reviewer 子任务前记录 parent task 与 child task 的关系。
- 新增 `src/aico/core/commands.py`,把内置 IM 命令解析从 `Orchestrator` 拆出,并支持 `/approve@bot abcdef12` 这类 Telegram bot suffix。
- `Orchestrator` 从 364 行降到 318 行,降低后续命令扩展风险;`TaskBus` 保持 496 行,未突破硬上限。
- 风险识别从散落 marker tuple 改为 `RiskRule` 规则表,新增单测覆盖多规则命中时保留原因。
- 本地 targeted tests 已通过;完整验证见本轮交接。

**Round 23**(2026-04-29,Codex):
- 人类反馈 `/claude` 超长文本请求没有收到结果,怀疑卡住或长文本仍有问题。
- 新增后台日志配置:`AICO_LOG_LEVEL`、`AICO_LOG_PATH`,默认写 `logs/aico.log` 并同步输出控制台。
- 在 Telegram Channel、Orchestrator、Claude/Codex Adapter、StreamedMessageWriter 记录关键链路日志,包括入站消息、任务路由、ack、CLI 进程启动/退出、stdout chunk 长度、Telegram send/edit 长度和长文本分片。
- 记录 P-011,明确长任务没结果时先用日志区分 busy、CLI 未退出、无 stdout、Telegram 出口失败。

**Round 24**(2026-04-29,Codex):
- 人类确认 Adapter 层和 Loop 层方向,要求 Agent Harness 薄层继续简化:tools/skills 由 Claude/Codex provider 自己拥有,AICO 仅通过 Adapter 翻译和展示。
- 新增 ADR-0010,明确原话边界:`AICO Agent Harness is a session and capability facade, not a tool execution runtime.`
- 新增 `src/aico/core/agent_session.py`,定义 `AgentCard`、`ProviderSessionRef`、`AgentSession` 和 `InMemoryAgentSessionStore`。
- `Phase1Runtime` 挂载空的 `session_store`,为后续 `/sessions`、`/use`、provider session resume 做准备,不改变当前 Telegram 行为。

**Round 25**(2026-04-29,Codex):
- 基于 `InMemoryAgentSessionStore` 增加 `/sessions`、`/new <agent>`、`/use <session_id>` 命令。
- `AgentSessionStore` 增加按 channel / chat / sender 作用域保存 active session 的能力。
- `Orchestrator` 在普通消息没有显式 `/agent`、`@agent`、`agent:` 或 Telegram mention 时,会优先路由到当前 active session 的 agent。
- `Phase1Runtime` 将同一个 session store 注入 Orchestrator,让 Telegram 命令和运行时共享会话状态。
- 本轮没有接 provider resume;Claude/Codex CLI 原生会话恢复仍是下一步。

**Round 26**(2026-04-29,Codex):
- 用本机 CLI help 确认 Claude 支持 `--session-id`、`--resume`、`--continue`,Codex 支持 `codex exec resume [SESSION_ID] [PROMPT]`。
- `ProviderSessionRef` 增加 `initialized`,并新增 task metadata helper,让 active session task 能携带 provider session id 与 `new/resume` 模式。
- `Orchestrator` 将 active session 的 provider ref 注入 Task metadata;首轮成功派发后标记 provider ref initialized,后续同 session 任务自动进入 resume 模式。
- `ClaudeCodeAdapter` 首轮使用 `--session-id <uuid>`,后续使用 `--resume <uuid>`;自定义命令若已有 session 参数则不重复追加。
- `CodexAdapter` 已支持已有 provider ref 时构造 `codex exec resume <session_id> <prompt>`,并把默认 `exec --sandbox read-only` 安全提升到 resume 可接受的全局参数位置。
- `Phase1Runtime` 为 Claude persona / alias 创建 provider session ref;Codex 暂不自动创建 provider ref,等待后续 session id 捕获或显式绑定。
- 本地 114 个单测、`ruff check`、`ruff format --check`、`mypy`、`git diff --check` 全绿。

**Round 27**(2026-04-29,Codex):
- 人类反馈 `/codex inspect this` 卡住,以及 Claude 回答技能列表时只收到开头一句。
- 查 `logs/aico.log` 定位为 Telegram `editMessageText` 返回 HTTP 400 后 handler 异常退出;这不是 Codex “指定新 session id”能力缺失导致的。
- 修复 Telegram `_post()` 的错误解析顺序,先读取 Bot API JSON `description`,再处理 HTTP / business error。
- `edit_message()` 对 `Bad Request: message is not modified` 做 no-op 容错,避免尾部空白/换行 chunk 把流式输出打断。
- 新增 P-012,记录 no-op edit 400 导致长文本像被吞掉、Adapter 看起来 busy 的坑。
- 本地 Telegram Channel 单测已覆盖 HTTP 400 description 和 no-op edit 容错。

**Round 28**(2026-04-30,Codex):
- 人类要求继续迭代后续两个阶段,然后交给人类验收和审查。
- 选择 Phase 5 中两个可本地闭环的后续阶段:Codex provider session 显式绑定、agent 能力/职责可见性。
- 新增 `/bind <session_id|agent> <provider_session_id>`;支持 `/bind codex <provider_session_id>` 创建并激活 reviewer/Codex session,后续普通消息以 `resume` 模式进入 provider session。
- 新增 `AgentDirectory` 和 agent card 构建,从 persona + adapter 生成只读能力门面,不复制 provider tools/skills registry。
- 新增 `/agents`、`/agent <agent>` 展示角色、adapter、provider、status、capabilities 和 skills/tools 来源。
- 新增 `/skills <agent>`、`/tools <agent>`,把能力探测问题路由给底层 provider 自己回答。
- 把命令输出渲染移动到 `command_messages.py`,让 `Orchestrator` 保持在 500 行以下。
- 本地定向单测已覆盖命令解析、agent directory、provider bind 和 skills introspection。

**Round 29**(2026-05-04,Codex):
- 人类已真实验收 `/agents`、`/skills`、`/tools`,并指出下一阶段痛点不是裸 session,而是多项目长期迭代时缺少项目进展、风险、日报/周报等公司语义。
- 确定 Project Assignment Layer:Agent 是员工,Project 是项目,Assignment 是员工在项目里的岗位/工位;provider session、权限、role prompt、工作目录和状态都绑定到 Assignment/seat。
- 决定 Assignment 主要通过配置文件维护;MVP slash command 只做查看和切换,不做 `/assign ...` 这类聊天内组织架构修改。
- Prompt 模板分为 Agent Base Prompt、Role Prompt、Project Brief、Runtime Context 四层,避免每个 Assignment 复制大段 prompt。
- `/handoff` 暂不进入 MVP,因为项目中途换 Agent 涉及上下文迁移和未完成假设传递,复杂度高。
- 新增 ADR-0011 和 `docs/architecture/project-assignment-layer.md`,并同步 README / 架构总览 / ADR 索引。

**Round 30**(2026-05-04,Codex):
- 人类要求产出两张可向用户和技术读者介绍项目的 draw.io 图:一张分层技术架构图,一张核心概念和角色分工工作流程图。
- 新增 `docs/architecture/aico-layered-architecture.drawio`,按用户体验/应用运行时/公司模型与治理/协议适配器/本地 provider 与持久化自上而下分层。
- 新增 `docs/architecture/aico-concepts-workflow.drawio`,解释 Human Manager、Project、Agent Catalog、Assignment/seat、provider session、prompt stack、审批审计和 AI 间协作流程。
- 更新 `docs/architecture/overview.md`,加入两张可编辑图的入口链接。
- 使用 XML 解析验证两个 `.drawio` 文件格式有效。

**Round 31**(2026-05-04,Codex):
- 开始实现 Project Assignment Layer MVP 的第一切片。
- 新增 `src/aico/core/project_assignment.py`,定义 `CompanyAgentProfile`、`ProjectProfile`、`AssignmentProfile`、`ProjectAssignmentConfig` 和 `ProjectAssignmentDirectory`,支持配置校验、active project、默认 assignment 和 task metadata 注入。
- 新增 `config/projects.example.json` 和 `AICO_PROJECT_CONFIG_PATH` 配置入口;未配置时会基于当前 persona/agent 自动生成默认 `aico` 项目 assignment。
- 新增 `/projects`、`/project <project>`、`/use project <project>`、`/assignments [project]`、`/assignment <seat>` 命令。
- `/use project aico` 后,当前聊天 + 发送者的普通消息会路由到项目默认 assignment,provider session ref 绑定到 assignment seat;显式 `/claude` / `/codex` / `@reviewer` 仍优先。
- 将 agent/project/session 类命令处理拆到 `src/aico/core/orchestrator_commands.py`,让 `Orchestrator` 回到 467 行,低于单类 500 行硬约束。
- Targeted tests 53 个通过;ruff 和 mypy targeted checks 通过。

**Round 32**(2026-05-04,Codex):
- 人类指出 `assignment/seat/use role` 不符合唯一老板派发任命的直觉,要求在正式使用前直接改成老板视角设计。
- 决定把 Assignment 的产品层表达改为 Appointment / Team:`seat` 保留为内部稳定 id,主路径命令改为 `/project`、`/team`、`/who`、`/appoint`、`/ask`、`/lead`。
- 新增 ADR-0012,明确 boss-facing team commands 和 role system,并否决 `/use assignment <seat>` 作为主路径。
- 重写 `docs/architecture/project-assignment-layer.md`,补齐 RoleTemplate / Project Role Override / Appointment Contract / Prompt Stack / 新项目默认任命设计。
- 完善 role 体系:除 implementer / reviewer 外,加入 tester、pm、architect、security、docs、ops、analyst、designer 等可选岗位。

**Round 33**(2026-05-04,Codex):
- 实现 boss-facing Project Team 命令 MVP:`/project <project>` 进入项目办公室,`/team` 查看团队,`/who <role>` 查看岗位负责人,`/appoint <agent> as <role>` 任命员工,`/ask <role> <task>` 单次派活,`/lead <role>` 设置默认牵头角色。
- `ProjectAssignmentConfig` 新增 `roles`、`ProjectProfile.roles`、`appointments`,旧 `assignments` 字段继续兼容。
- `ProjectAssignmentDirectory` 支持 runtime appointment upsert、按 role 查 appointment、设置默认 role,并继续为旧 assignment/seat 命令提供兼容。
- `config/projects.example.json` 改成 roles / project role override / appointments 示例,包含 implementer、reviewer、tester、pm 等岗位。
- 新增/更新单测覆盖命令解析、appointment runtime 更新、`/ask` 路由到 role appointment、`/lead` 后普通消息走新默认 role。
- 本地 133 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests` 全绿。

**Round 34**(2026-05-04,Codex):
- 人类真实执行 `/appoint Claude as tester read_repo run_tests` 返回 `Cannot appoint Claude as tester`。
- 定位为命令层能用大小写不敏感的 `AgentDirectory.resolve()` 识别 `Claude`,但 `ProjectAssignmentDirectory.upsert_appointment()` 再用原始 `Claude` 精确查配置 key `claude`,导致任命被拒。
- 修复 `ProjectAssignmentDirectory` 的 agent / role / project lookup,统一使用大小写不敏感、下划线/横线兼容的 ref 解析;runtime appointment 会写入 canonical `claude` / `tester`。
- 新增单测覆盖 `/appoint` 中 `Claude` / `Tester` 这类人类自然输入。
- 本地 133 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests` 全绿。

**Round 35**(2026-05-04,Codex):
- 人类指出 `/default tester` 仍偏工程视角,要求改成更像老板语言的 `/lead tester`,并继续开发。
- 新增 `CommandName.LEAD`,主路径使用 `/lead <role>` 设置当前项目默认牵头 role;`/default <role>` 保留为兼容别名。
- 命令输出从 `Default role` 改为 `Lead role`,强调“由哪个岗位牵头”。
- 新增 `src/aico/core/prompt_stack.py`,实现 Appointment prompt stack MVP。
- 走 project appointment 的任务会渲染 Agent、RoleTemplate、Project、ProjectRoleOverride、Appointment Contract 和 Current task;显式 `/claude`、`/codex`、`@reviewer` 等非 appointment 路由仍走原 persona prompt。
- `RoleProfile` 增加 `inline_prompt`,`ProjectRoleProfile` 增加 `inline_prompt_override`,`ProjectProfile` 增加 `brief`,为后续配置内 prompt 文案和项目简报做准备。
- 本地 133 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests` 全绿。

**Round 36**(2026-05-04,Codex):
- 继续向后开发 Project Team / Appointment 验收面,新增项目办公室只读摘要能力。
- 新增 `/brief [project]`,基于本地 Project 配置、team appointments、lead role、最近 task snapshots 和 audit events 生成项目简报。
- 新增 `/risks [project]`,从最近失败/拒绝/中断/等待审批任务、高风险任务和风险审计事件生成风险列表。
- `/brief` 和 `/risks` 不调用 provider、不假装已有共享记忆层;当前是本地状态摘要 MVP。
- 新增单测覆盖 `/brief`、`/risks` 命令解析和 orchestrator 输出。
- 本地 134 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests` 全绿。

**Round 37**(2026-05-04,Codex):
- 人类开始验证,同时要求继续开发。
- 新增 `src/aico/core/project_docs.py`,提供受限 project document snippet 读取能力。
- `ProjectProfile` 新增 `blockers_doc` 和 `pitfalls_doc`;默认 AICO 项目和 `config/projects.example.json` 配置 `BLOCKERS.md` / `PITFALLS.md`。
- `/brief` 会读取 north star / status / journal 文档短片段;`/risks` 会读取 blockers / pitfalls 文档短片段。
- 文档读取限制为每个文件最多 4 行、单行最多 140 字符;文件不存在或读取失败时安静跳过,不会让 Telegram 命令失败。
- 新增 `tests/unit/test_project_docs.py`,覆盖文档片段读取和缺失文件跳过。
- 本地 136 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests` 全绿。

**Round 38**(2026-05-04,Codex):
- 人类继续 Telegram 验证,同时要求继续向后开发。
- 新增 `/daily [project]` 和 `/weekly [project]` 本地项目报告命令,分别按最近 24 小时 / 7 天窗口聚合团队、牵头 role、完成项、未完成项、风险和项目文档短片段。
- 报告命令复用 Project Team / Appointment 语义,仍只基于当前 AICO 进程内 task/audit 状态和受限文档片段,不调用 provider,不伪造长期共享记忆。
- 更新架构文档、daily ops、CHANGELOG 和 draw.io 图,把 `/daily` / `/weekly` 从设计态推进到已实现的项目状态面。
- 新增单测覆盖命令解析和 Orchestrator 日报/周报输出。
- 本地 137 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check` 全绿;draw.io XML 解析通过。

**Round 39**(2026-05-05,Codex):
- 人类真实使用 `/risks` 后指出输出混入 `write_files` 审批、`unknown adapter/persona` 等底层信号,不符合“项目风险”的直觉。
- 将 `/risks` 收窄为真正项目交付风险:失败/中断任务、破坏性任务和 blockers / pitfalls 文档片段;普通写文件审批、`approval_requested` 审计事件和未知 persona 路由噪音不再展示。
- 新增 `/blockers [project]`,专门展示当前卡住的工作和待决策项,包括等待审批、失败/拒绝/中断任务、未知 persona 等执行/系统问题和 blockers 文档片段。
- 新增回归测试覆盖人类遇到的 `write_files + unknown persona` 噪音场景,确认 `/risks` 不展示这些项,而 `/blockers` 能展示它们。
- 更新 `CHANGELOG.md`、`docs/human/daily-ops.md` 和 Project Team 设计文档。
- 本地 138 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check` 全绿;draw.io XML 解析通过。

**Round 40**(2026-05-05,Codex):
- 人类确认 `/risks` 新语义验收没问题,要求继续开发后续能力。
- 先把 Project/Team/Report 命令消息渲染拆到 `src/aico/core/project_messages.py`,让通用 `command_messages.py` 不再承载项目状态面输出。
- 将 `DirectoryCommandHandler` 的 report 发送辅助逻辑移出类体,使 `Orchestrator` 和 `DirectoryCommandHandler` 类体继续低于 500 行硬约束。
- 新增 `/next [project]`,基于本地 project/team/task 状态给出下一步建议动作:优先处理待审批、失败/中断/拒绝任务和路由/配置问题;没有卡点时建议把任务交给当前 lead role。
- `/next` 只支持 slash command,不把普通英文 `next` 当命令,避免误吞用户任务。
- 新增单测覆盖 `/next` 命令解析、待审批动作建议和普通 `next` 任务不被误吞。
- 更新 `CHANGELOG.md`、`docs/human/daily-ops.md`、Project Team 设计文档和两张 draw.io 图。
- 本地 139 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check` 全绿;draw.io XML 解析通过。

**Round 41**(2026-05-05,Codex):
- 人类授权若无重大决策则持续开发,并设置小时级 heartbeat 自动化催促当前线程继续推进。
- 新增 `/roles [project]`,展示当前项目 role 模板、默认权限和已任命 / 未任命状态,补齐 `/team` 和 `/who` 之外的岗位缺口视图。
- `/roles` 支持当前 active project,也支持 `/roles aico` 显式查看指定项目。
- 新增单测覆盖命令解析和 Orchestrator roles 输出,确认 implementer 已任命、tester 未任命。
- 拆分 `ProjectCommandHandler`,把项目办公室命令从通用 `DirectoryCommandHandler` 移出,保持单类 <500 行约束。
- 更新 `CHANGELOG.md`、`docs/human/daily-ops.md`、Project Team 设计文档和两张 draw.io 图。
- 本地 140 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check` 全绿;draw.io XML 解析通过。

**Round 42**(2026-05-05,Codex):
- Heartbeat 唤醒后继续推进,选择补齐老板任命闭环里的撤任能力,不触碰持久化配置写入。
- 新增 `/unappoint <role>`,可撤销当前 active project 某个 role 的进程内 appointment。
- `ProjectAssignmentDirectory` 新增 `remove_appointment_for_role()`,撤销当前 lead role 时会回退到剩余 appointment。
- 新增撤任确认消息,撤任后 `/roles` 会显示该 role 回到 `unappointed`, `/who <role>` 会提示未任命。
- 新增单测覆盖命令解析、目录撤任与默认 lead 回退、Orchestrator 撤任输出。
- 更新 `CHANGELOG.md`、`docs/human/daily-ops.md` 和 Project Team 设计文档。
- 本地 142 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check` 全绿;draw.io XML 解析通过。

**Round 43**(2026-05-05,Codex):
- Heartbeat 唤醒后继续推进,最高优先级真实 Telegram 验收仍需人类环境配合,因此选择一个不需拍板的项目办公室体验小修。
- `/project <project>` 继续用于进入指定项目;已有 active project 时,发送 `/project` 会重新展示当前项目办公室。
- 未进入任何项目时,`/project` 会提示 `No active project. Use /project <project> first.`。
- 新增单测覆盖未进入项目时的提示、进入项目后的 `/project` 复显,并确认不会派发 Adapter 任务。
- 更新 help 文案、`CHANGELOG.md`、`docs/human/daily-ops.md` 和 Project Team 设计文档。
- 本地 143 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check` 全绿;draw.io XML 解析通过。

**Round 44**(2026-05-05,Codex):
- Heartbeat 唤醒后继续推进;真实 Telegram 验收仍需人类重启服务和发命令,因此补齐本地 Project Team acceptance flow。
- 新增 `test_orchestrator_project_team_acceptance_flow`,串起 `/project aico`、`/project`、`/brief`、`/risks`、`/blockers`、`/next`、`/daily`、`/weekly`、`/roles`、`/team`、`/who implementer`、`/appoint claude as tester read_repo run_tests`、`/ask tester ...`、`/lead tester`、普通消息、`/unappoint tester`、`/roles`、`/who tester` 和撤任后的普通消息回退。
- 验收流确认状态面不派发 Adapter 任务,`/ask tester` 和 tester lead 普通消息带 tester assignment metadata,撤任后普通消息回退到 implementer。
- 更新 `CHANGELOG.md` 和 `docs/human/daily-ops.md`,加入本地验收流命令。
- 本地 144 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check` 全绿;draw.io XML 解析通过。

**Round 45**(2026-05-05,Codex):
- Heartbeat 唤醒后继续推进;真实 Telegram 验收仍需人类环境配合,本轮优先处理 `Orchestrator` 类体接近 500 行硬约束的问题。
- 将大段命令 if/elif 分发从 `Orchestrator._handle_command()` 移到模块级 `_handle_command()` 函数,类内只保留薄代理。
- 行为不变,仍复用现有 ProjectCommandHandler、DirectoryCommandHandler、审批、拒绝和 broadcast 路径。
- `Orchestrator` 实际类体从 491 行降到 422 行,为后续能力扩展留出空间。
- 本地 144 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check` 全绿;draw.io XML 解析通过。

**Round 46**(2026-05-05,Codex):
- 人类 Telegram 验收发现多次 `/appoint ... as tester ...` 后 `/team` 可能出现多个 tester,并追问 role 扩展、lead 可见性、Telegram 文案适配和 LLM 总结。
- 将 Project appointment 的唯一语义下沉到 `ProjectAssignmentDirectory`:同一 project + role 只保留一个 appointment;重复任命会覆盖,历史/配置中重复 role 初始化时按最后一个生效。
- `/team` 现在显示当前 lead,并在对应团队成员行标记 `[lead]`。
- 新增 P-013 记录同 role 多 appointment 的坑。
- 本轮没有把“LLM 生成 role 并确认新增”“IM 独立富文本渲染”“/brief 等顶部 LLM 总结”硬塞进现有命令;这三项需要下一轮按 provider 调用、确认流和 channel render contract 设计后实现。
- 本地 145 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check` 全绿。

**Round 47**(2026-05-05,Codex):
- 继续执行高优先级的 Role 创建确认流。
- 新增 `/role propose <诉求>`:当前项目 lead role 会收到只读 role proposal prompt,要求输出 JSON role 草案。
- 新增 `/role confirm` / `/role discard`:草案按当前 Telegram chat + sender 作用域暂存,确认后只加入当前进程内 project roles,不写配置文件。
- `ProjectAssignmentDirectory` 支持 runtime project role,`/roles` 能展示确认后的新 role 且默认未任命。
- 内部 role proposal task 增加 `aico.intent=role_proposal` 元数据,风险识别将其视为 read-only,避免“起草一个能跑测试的岗位”误触发 shell/write 审批。
- 本轮后 `Orchestrator` 类体已接近 500 行硬约束;继续做 IM render 或 LLM summary 前应先拆出 role proposal / task collection helper。
- 本地 targeted tests、`ruff check .`、`mypy src tests` 已通过;完整验证见本轮交接。

---

## 下一轮建议做什么(优先级从高到低)

> Agent 接手时,如果没有明确任务,从这里挑最高优先级。

1. **【高】Release Room Stage 3 GIF 复剪 / README 体验复核**:
   - 已生成真实 Telegram dogfooding GIF: `docs/assets/release-room-demo.gif`,并嵌入 README。
   - 当前 GIF 是 35 秒实录剪辑,覆盖 `/use`、`/team`、project memory、Codex PM/tester 输出、`/daily` 和 `/audit`。
   - 下一轮可做一次更精剪版本:减少旧消息露出,补更清晰的 approval gate 镜头,并避免 read-only pytest 临时目录失败入镜。
   - 若继续录真实 CLI,优先让 Codex tester 使用可写临时目录或只做静态检查,不要在 read-only sandbox 里直接跑 pytest。
2. **【高】Phase 8 `/overnight` 持久化与重启恢复**:
   - 让托管工单列表可从 audit JSONL 恢复,避免重启后 `/overnight` 看不到昨晚托管记录。
   - 继续保持危险动作必须 `/approve`,不因为离线托管放大权限。
3. **【高】Cursor / CodeFlicker / Trae / Gemini 真实 smoke test**:
   - 安装并登录 `cursor-agent`,启动 `AICO_ENABLE_CURSOR_ADAPTER=true`,在 Telegram 发送 `/agents`、`/cursor summarize this repo in one sentence, do not edit files` 和一个写文件审批任务。
   - 确认 `flickcli` 已登录,启动 `AICO_ENABLE_CODEFLICKER_ADAPTER=true`,在 Telegram 发送 `/agents`、`/codeflicker summarize this repo in one sentence, do not edit files` 和一个写文件审批任务。
   - 确认 `trae-cli` 已登录 / token 可用,启动 `AICO_ENABLE_TRAE_ADAPTER=true`,跑只读和写能力审批 smoke test。
   - 确认 `gemini` 已登录 / API key 可用,启动 `AICO_ENABLE_GEMINI_ADAPTER=true`,跑只读和写能力审批 smoke test。
   - 观察 `/status`、`/tasks`、idle timeout 和日志,确认失败时能释放 busy。
4. **【高】Feishu Channel 部署层与真实 smoke test**:
   - 用 FastAPI route 或现有部署入口把飞书事件 callback 接到 `FeishuChannel.handle_event(payload)`。
   - 在飞书开放平台完成 URL verification,订阅 `im.message.receive_v1`。
   - 配置 App ID / App Secret / Verification Token,跑文本入站、回复、编辑/删除降级 smoke test。
5. **【高】Phase 5 真实协作 smoke test 作为后续回归项**:重新跑 `@reviewer ...`,确认 child task accepted 后要么有 reviewer 输出,要么 90 秒 idle timeout 后恢复 `codex: idle`。
6. **【中】Codex bind / Claude resume / 长文本复测**:继续确认 session 和长文本分片不被 Phase 6 命令影响。
7. **【低】Adapter usage 上报**:等 Claude/Codex Adapter 能稳定提供 usage 后,记录 `task_usage_recorded` 审计事件;当前只保留接入边界,不伪造数据。

---

## 当前卡点

参见 [`docs/journal/BLOCKERS.md`](docs/journal/BLOCKERS.md)。B-001、B-002 均已解决;当前没有阻塞 Phase 7 的活跃卡点。

---

## 当前已知风险

| 风险 | 影响 | 当前应对 |
|---|---|---|
| 各 AI CLI 接口不稳定(Claude Code/Codex 都在快速演进) | Adapter 频繁返工 | 协议层做厚,把"易变"封装在 Adapter 内部 |
| 个人项目长期维护动力衰减 | 项目烂尾 | Dogfooding 强制——自己用,自己优化 |
| 范围蔓延(看到什么酷功能都想加) | 进度失控 | 北极星 + Phase 严格门禁 |

---

## 元信息

- **项目仓库**:https://github.com/MarcelLeon/ai-company-os
- **主要维护者**:Wang
- **协作 AI**:Claude(本轮)、未来不限
