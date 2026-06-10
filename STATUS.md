# STATUS.md — 当前状态

> 这个文件高频更新。每一轮 AI 工作或人类工作结束都要更新这里。
> 阅读顺序:从上往下,前面的信息时效性最高。

**最后更新**:2026-06-10
**当前轮次**:Round 151(readme-showcase-command-review)
**当前阶段**:🟡 Phase 8 进行中 — 离线托管 + 老板缺席操作模型
**当前路线图**:近期高优三块基础能力(Memory+Experience / Audit+Rollback / aico-view)详见
[`docs/architecture/boss-first-grounding.md`](docs/architecture/boss-first-grounding.md)。Lead 主动机制和 Team Karpathy Loop 已记入 Future,暂不实现。

---

## 项目宏大叙事(一句话)

把开发者 Mac 上散落的 AI CLI 收编成一个可通过 IM 远程指挥的"虚拟公司",让老板不在电脑前时,AI 团队仍能异步推进、审批、叫停、交接和早报。

## 老板不在场假设

AICO 的产品边界是 absence-first:

- OMC 更像在浏览器里经营 AI 公司,CoWork OS 更像在桌面上做 AI super app;AICO 假设老板经常不在电脑前。
- IM 不是通知层,而是老板远程下达任务、查看状态、审批风险、叫停任务和接收早报的管理层。
- 本地 AI CLI 不是按钮集合,而是被任命到项目角色里的团队成员:lead、challenger、implementer、tester、reviewer 等。
- Phase 8 的 `/overnight`、operator inbox、morning handoff、lead decision、memory/audit/state 持久化,都服务于同一件事:老板离开 Mac 后,项目仍可推进且可接手。
- 新能力优先级先问 5 个问题:只靠 IM 能不能下达?离开后能不能推进?风险能不能等审批?早上能不能看懂?出问题能不能审计、叫停、恢复?

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
- [x] Cursor / CodeFlicker / Trae / Gemini 真实 smoke test。

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
- [x] README GIF D0 复剪:新增 transcript-driven public GIF,`docs/assets/release-room-demo.gif`
  约 36 秒、`960 x 540`;Round 149 已把首帧 / social preview 改为明确 boss-absent 假设,
  并展示 `/morning` + `/view`。
- [x] GitHub social preview 资产生成:`docs/assets/social-preview.png`,`1280 x 640`,小于 1 MB,
  public 前需仓库 owner 在 GitHub UI 上传 / 确认(Round 148)。
- [x] 开源首屏第一版:英文主 README、中文 README、痛点/差异化/当前可用能力、Quickstart 状态修正、MIT License、SECURITY 和 issue templates。
- [x] 开源首屏第二版:同步 Cursor / CodeFlicker / Trae / Gemini smoke test 已完成状态,补安全模型图、今日使用场景和 GitHub publication 手动配置指南。
- [x] GitHub UI metadata 首轮配置验收:description、topics、social preview 已由人类在 GitHub UI 配置验证;
  public 前仍需仓库 owner 按 `docs/human/github-publication.md` 做最终复核。
- [x] 开源首屏第三版:新增无 token Release Room demo CLI、PR template 和 good-first-issue template。

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
- [x] Agent reply language command(`/language [en|zh]`):默认英文,可按 IM chat 作用域限制后续 agent 回复语言,不改变内置命令语言。
- [x] Phase 5 feature complete handoff
- [x] Telegram 真实协作 smoke test(人类确认真实 IM 下可触发;后续不再作为高优待办)
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
- [x] Team Broadcast 可追踪审计:广播 receipt、source/broadcast memory、team scope、recipients 和 reason 写入 `memory_broadcasted` audit event。
- [x] 可解释记忆检索契约:MemoryRetrievalQuery / MemoryRetrievalHit、综合排序、token budget 和 `/recall` reason。
- [x] 记忆检索 graph / task-aware 升级:一跳 graph expansion、role/task query hints 和 `/recall` score 分项。
- [x] Phase 7 共享记忆本地验收流

### Phase 8 进度

- [x] ADR-0024 Phase 8 Offline Delegation Scope
- [x] Phase 8 offline delegation playbook
- [x] `/overnight <goal>` 离线托管工单 MVP
- [x] `/overnight` 当前项目托管工单查看
- [x] 托管工单复用当前项目 lead/default role、appointment prompt、memory 和 provider session
- [x] 托管工单危险动作继续走 `/approve` 门禁
- [x] Goal-mode 交互和 prompt 契约设计(ADR-0025 Accepted)
- [x] Goal-mode 支持 agent capability 分层:native goal / adapter sugar / managed Ralph loop。
- [x] Lead decision team contract Stage 1:强化 lead 决策责任、默认新增 challenger,并让 `/overnight` 要求 lead + challenger。
- [x] Memory purpose 标签:区分 public broadcast / task key progress / task private / decision review。
- [x] Lead decision workflow:决策类任务自动召回记忆、咨询 challenger/reviewer、输出 decision memo 并写 audit。
- [x] Goal Brief v0:`/goal` 和带明确验收/停止/证据 marker 的 `/ask` 可附加轻量目标契约,并在 `/task` 中可见。
- [x] SQLite task state store 第一切片:`AICO_STATE_DB_PATH` 可持久化 task records、task snapshots 和 pending approvals。
- [x] Core structure cleanup:B-004 已收口,`Orchestrator` / `TaskBus` 类体重新低于 500 行,命令分发函数低于 100 行。
- [x] 托管工单持久化与重启恢复:`AICO_STATE_DB_PATH` 可恢复 `/overnight` 最近托管工单列表。
- [x] SQLite 快速迭代治理:`aico_schema` metadata、`aico-state` inspect/reset 工具和 bool-like path 兜底。
- [x] 长静默 Adapter 任务 quiet heartbeat:provider 无 stdout 但进程仍运行时,IM 会显示 `Still running...`,并保留 `/interrupt` 与 idle timeout 兜底。
- [x] `/inbox` 当前项目老板收件箱第一切片:聚合待审批、running/failed/interrupted、离线托管、Goal Brief / lead decision 和协作 follow-up。
- [x] CLI Adapter 非交互 stdin 收口:子进程启动时显式 `stdin=DEVNULL`,避免 Codex 等待 inherited stdin 的额外输入。
- [x] CLI Adapter stderr drain:子进程运行期间持续读取 stderr,避免 Codex 运行日志写满 pipe 后反压阻塞 stdout。
- [x] ADR-0029 Phase 8 Absence Loop:把 actionable inbox、morning handoff、outcome grader、Dream/runbook memory 和 hybrid retrieval 固定为短期 sprint 队列。
- [x] Phase 8 Absence Loop playbook:每个 sprint 都有直接可问的 IM 验收路径和防跑偏护栏。
- [x] `/inbox` actionable 化第一切片:新增 First action,并把审批、running、失败恢复、handoff、Goal/decision、协作 follow-up 都渲染为可直接执行的下一步命令。
- [x] `/morning` 手动早报第一切片:按 active project 汇总 done、blocked、risks、overnight handoffs 和 next actions。
- [x] Outcome Grader 第一切片:Goal Brief 执行完成后自动派 tester / reviewer 验收,并把 grader task 标记为 `outcome_grader` follow-up。
- [x] `/dream` Dream/runbook memory 第一切片:从 waiting approval / running / failed / interrupted / rejected 任务生成 reviewable candidate memory,默认不注入 prompt。
- [x] Hybrid Memory Retrieval 第一切片:默认本地 scorer 从纯 semantic 升级为 exact phrase + phrase overlap + semantic alias fallback,保留 MemoryGovernor 边界。
- [x] Telegram native output pilot:`AICO_PREFER_NATIVE_CHANNEL_FORMAT=true` 时 agent 优先输出 Telegram HTML,验证失败自动回退 rich text。
- [x] Phase 8 Absence Loop 真实 IM dogfood 已由人类执行;效果不佳且暂不继续投入 native output 方向,当前 dogfood 使用 `AICO_PREFER_NATIVE_CHANNEL_FORMAT=false`。
- [ ] 多 step / 多 agent 夜间自动编排
- [ ] 早报自动生成或定时推送
- [x] Sprint M1 — MemoryAtom 加 `kind=fact|experience` + `ExperienceMeta`;Dream 输出改为 candidate experience(Round 128)。
- [x] Sprint A1 — AuditEvent/Task/MemoryAtom 增加 `trace_id`;新增 `UnifiedEventIndex` 派生只读层;ADR-0030(Round 129)。
- [x] Sprint M2 — `/experience review|list|promote|archive` lead 内务命令;`prompt_stack` 加 ExperienceLayer;task metadata 写出 `aico.injected_experience_ids`;ADR-0031(Round 130)。
- [x] Sprint M3 — Outcome Grader `parse_verdict` + `apply_verdict_to_owner_experiences` 回写 confidence/hits/misses/injection_count;grader task trace_id 继承 owner trace_id(Round 131)。
- [x] Sprint A2 — boss-only `/undo` + `/why` + `/inbox` `/morning` 内嵌 Recent activity;ADR-0032(Round 132)。
- [x] Sprint V1 — `aico-view` 只读 FastAPI 三视图 + `aico-view` entrypoint;ADR-0033(Round 133)。
- [x] Sprint V2 — aico-view 三视图加 IM deep-link 按钮(Telegram `t.me/<bot>?text=`)+ Feishu cmd-copy 降级(Round 134)。
- [x] Sprint A3 — lead 内务 `/timeline` + `/rollback memory|experience|task`;新增 `ROLLBACK_PERFORMED` AuditEventType;ADR-0034(Round 135)。
- [x] Sprint V3 — `aico-view` `AICO_VIEW_TOKEN` 鉴权 + 部署文档(localhost / ngrok / Cloudflare);ADR-0035(Round 136)。
- [x] Sprint V4 — `AICO_VIEW_ENABLED=true` 启用 IM `/view` HTML 快照,通过 Telegram `sendDocument` 发送自包含只读文件,不启动本机 HTTP 服务;ADR-0036(Round 137)。
- [x] `/overnight` dogfood 修复:协作子任务用 `Current task:` 标记真实委托内容,避免 reviewer/Codex 因 parent context 中的 `git` / `run` 词被误判为 `shell_exec`(Round 138)。
- [x] `/overnight` handoff 完整性兜底:CLI exit 0 但输出过短或缺少 done/blocked/risks/next actions 时,任务改标 failed 并回 IM 提示不完整,避免半句输出伪装成成功(Round 139)。
- [x] Delegate agent 输出 IM 可读性兜底:流式 agent 结果进入 Telegram/native renderer 前会拆分粘连 `<b>Heading</b>`、已知 section label 和 `• High/Medium/...` 列表,避免 implementer/reviewer 结果糊成一整段(Round 141)。
- [x] `/overnight` 老板秘书动线:回执明确 now `/inbox`、morning `/morning`、exact trace `/task`、visual snapshot `/view`;`/aico-view` 作为 `/view` 别名;流式输出按 1400 字移动端阅读上限分段(Round 142)。
- [x] Dogfooding 验收分层:机器 Gate 先覆盖父子 agent 委派、handoff、render、命令和审计等确定性 contract;Agent 能访问本机 Telegram / provider 时先跑真实样本,人工 dogfood 只抽样确认体感和接手便利性(Round 143,Round 145 修正)。
- [x] Phase 8 human sample 前置 contract gate:在 `docs/playbooks/phase-8-absence-loop.md` 固化当前 41-test gate,覆盖父子委派、`/overnight` handoff、delegate 分片、老板动线、`/view` 附件上传和 Telegram long-poll timeout(Round 144-145)。
- [x] 本机真实 Telegram/provider 样本:Mac Telegram App 中 `ai_co` bot 可收发;`/project aico` 实回;真实 `implementer/claude-code` 输出触发 `source=implementer target=reviewer`,reviewer/codex 子任务完成;同时修复 Telegram long-poll 默认 timeout 太短导致的空 warning(Round 145)。
- [x] Release candidate 收口:README / release notes / no-token Release Room demo 已对齐 `/inbox` -> `/morning` -> `/task` 的老板接手动线;Phase 8 gate、full pytest、ruff、mypy 和 no-token demo 均通过(Round 146)。

### 开源 Demo 进度

- [x] Release Room Stage 1 static package:示例仓库、项目配置、playbook、demo script、录屏 storyboard。
- [x] Release Room Stage 2 local acceptance transcript。
- [x] Release Room Stage 3 recording rhythm and GIF conversion path。
- [x] Release Room Stage 3 real Telegram dogfooding first pass, with provider-output blocker recorded。
- [x] Release Room Stage 3 Codex provider-output cleanup and real Telegram dry run。
- [x] Release Room Stage 3 public GIF / README showcase。
- [x] Release Room README GIF D0 复剪:按 `examples/release-room/shot-rhythm.md` 展示
  `/morning` 和 `/view`,首帧直接进入 boss-absent 产品画面(Round 149)。
- [x] README 发布前事实审校:中英文 README 已收紧 Feishu 稳定性边界,避免把尚待生产
  smoke 的 Feishu Channel 写成与 Telegram 同等稳定公开入口(Round 150)。
- [x] README 展示面收口:移除 GitHub 发布页配置段,补充 `aico-phase1` 是长驻 runtime,
  并实际验证 README 中可运行命令和 Telegram 命令测试覆盖(Round 151)。
- [x] Release Room no-token demo 发布前对齐 `/morning` 接手入口,避免公开 demo 继续教旧 `/daily` 路线(Round 146)。

---

## 上一轮做了什么

**Round 151**(2026-06-10,Codex — readme showcase command review):
- 人类指出 README 中“GitHub 发布页怎么配置”与项目展示无关,要求删除,并要求 README
  中的 cmd 命令经得起推敲,不能给错命令影响第一印象。
- README 展示面调整:
  - 英文 `GitHub Publication Checklist` 段落删除。
  - 中文 `GitHub 发布页怎么配置` 段落删除。
  - 中英文 Quickstart 均补充 `aico-phase1` 是长驻 Telegram runtime,需要保持运行,
    停止时按 `Ctrl-C`。
  - 中文开头把 OpenClaw / 公司内部 CLI 从当前已收编对象改为后续可按 Adapter 协议接入,
    避免把未实现 Adapter 写成当前能力。
  - 英文能力点再次标注 Feishu first slice 仍待 production smoke。
- README 命令验证:
  - `env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python 3.11 aico-release-room-demo`
    本地跑通。
  - `env UV_CACHE_DIR=/tmp/aico-uv-cache uv sync --python 3.11` 本地跑通。
  - `env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python 3.11 aico-phase1 --help`
    本地跑通,确认 entrypoint 存在;真实 `aico-phase1` 仍需要 Telegram token 并会长驻运行。
  - `env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python 3.11 aico-state --db /tmp/aico-readme-state.db`
    本地跑通。
  - Telegram README 命令由 `tests/unit/test_commands.py`、`tests/unit/test_orchestrator.py`
    和 Release Room acceptance 覆盖。

**Round 150**(2026-06-10,Codex — readme factual review):
- 按人类要求 review 中英文 README,核对当前实现状态和公开发布口径。
- 发现并修正两处容易造成外部误解的表述:
  - 英文 README 不再写成 `Telegram or Feishu` 同等稳定入口,改为 Telegram today;
    Feishu 是 first non-Telegram channel slice,仍待 production smoke。
  - 英文 README 不再写 `with no laptop required`,改为不用坐在电脑前;中文 README 同步说明
    当前主入口是 Telegram,飞书待生产 smoke 后再作为稳定入口推荐。
- 其余 README 主张与当前状态一致:boss-absent 叙事、Release Room demo、`/morning`、
  `/view`、审批审计、Cursor / CodeFlicker / Trae / Gemini smoke 状态均与 STATUS / quickstart
  口径一致。

**Round 149**(2026-06-10,Codex — boss-absent public assets):
- 人类指出 Round 148 生成的 `social-preview.png` 和 GIF 虽有 `while you are away`、`/morning`
  和 `/view`,但没有把 boss-absent 假设作为第一视觉信号;要求判断这是能力不足还是疏忽。
- 判断:这是表达疏忽,不是能力不足。当前能力已经有 `/overnight`、`/morning`、`/view`、
  审批和审计链路,足以支撑 boss-absent 叙事。
- 更新 `examples/release-room/generate-public-gif.py`:
  - GIF 首帧 title 改为 `Boss-Absent Mode`。
  - 顶部副标题改为 `Boss-absent release room`。
  - 右侧面板改为 `Boss-absent loop` / `What still works while you are away`。
  - footer 改为 `Boss absent - local agents still work - approval and audit stay visible`。
  - social preview 主文案改为 `Boss absent. Local agents still work.`。
  - social preview 大字改为 `Leave the laptop. Keep the team moving.`。
- 重新生成资产:
  - `docs/assets/release-room-demo.gif`:36 秒、`960 x 540`、约 278 KB。
  - `docs/assets/social-preview.png`:`1280 x 640`、约 48 KB。
- 视觉复核:
  - `/tmp/aico_absent_first_frame.png`:首帧明确 boss-absent。
  - `/tmp/aico_absent_contact.png`:8 帧均可读,后段包含 `/morning` 和 `/view`。
  - `/tmp/aico_absent_social.png`:social preview 首屏明确 boss-absent。

**Round 148**(2026-06-10,Codex — public assets and pre-public checks):
- 按人类要求继续 public 前收口,优先解决 Round 147 标出的 README GIF 首印象 blocker。
- 新增稳定资产生成器:
  - `examples/release-room/generate-public-gif.py` 从当前 Release Room shot rhythm 生成 transcript-driven
    public GIF,不依赖真实 Telegram 录屏、provider token 或手工剪辑。
  - 同时生成 GitHub Social preview 静态图。
- 生成并替换发布资产:
  - `docs/assets/release-room-demo.gif`:约 36 秒、`960 x 540`、约 279 KB、8 个场景;首帧为当前
    IM 产品画面,并覆盖 `/team`、`/remember`、`/ask`、`/approve`、`/overnight`、`/morning`、
    `/view`、`/audit`。
  - `docs/assets/social-preview.png`:`1280 x 640`、约 51 KB,用于 GitHub Social preview 上传。
- 文档口径同步:
  - README / README.zh-CN 移除"待复剪 GIF" roadmap 项。
  - `docs/human/github-publication.md` 指向新的 `social-preview.png`,并更新 GIF 尺寸 / 时长口径。
  - `docs/launch/playbook.md` 把 README GIF 从待办改为完成,但保留 GitHub UI social preview 上传 / 确认。
  - release-room docs / playbook / shot rhythm 记录可重复生成命令。
  - `docs/agent/09-github-release-ops.md` 更新 public 前资产复核结论。
  - P-039 标记 RESOLVED。
- GitHub public 前 metadata live 复核:
  - 仓库仍是 `PRIVATE`,默认分支 `main`。
  - description / homepage 已配置。
  - issues enabled,wiki disabled。
  - topics 已补齐 19 个,包括 `ai-coding`、`audit-log`、`memory`、`llm`、`fastapi`、`mcp`。
  - 本地 `v0.1.0` tag 为空,GitHub Release 列表为空。
- public 前剩余人工 UI 动作:上传 / 确认 `docs/assets/social-preview.png`,然后由仓库 owner 改 public。

**Round 147**(2026-06-09,Codex — GitHub release ops and README review):
- 复核 GitHub 状态:
  - `gh` 在当前桌面环境中可用,但普通沙箱读不到 macOS keyring;需要用提权方式执行 `gh ...`。
  - `gh repo view MarcelLeon/ai-company-os` 显示仓库仍是 `PRIVATE`,默认分支 `main`。
  - 本地和远端都未创建 `v0.1.0` tag,GitHub Release 列表为空。
- 审阅 README:
  - 英文 / 中文 README 的主体叙事、no-token demo、`/inbox` / `/morning` / `/task` / `/audit`
    口径已对齐当前 RC。
  - 发现 README GIF 是当前最大首印象缺口:现有 `docs/assets/release-room-demo.gif` 约 95 秒、
    `360 x 730`,首帧不是 Telegram 产品画面,且没有前置展示 `/morning` 和 `/view`。
- 新增 Agent GitHub 运维入口:
  - `docs/agent/09-github-release-ops.md` 固化 public / tag / GitHub Release / D0 的检查顺序。
  - `AGENTS.md` Step 7 和自检清单接入该 SOP。
- 更新发布材料:
  - README / README.zh-CN roadmap 标出 README GIF D0 复剪要求。
  - `docs/human/github-publication.md` 修正当前 GIF 体积和 social preview 口径。
  - `docs/launch/playbook.md` 不再把 GIF / GitHub UI 复核写成无条件完成。
  - `docs/examples/release-room.md` 和 `examples/release-room/shot-rhythm.md` 明确 `/view` 镜头和 D0 复剪标准。
- 记录 P-039:README GIF 首帧和最新能力比文件是否存在更重要。
- 本轮仅改文档,不改运行代码;`git diff --check` clean;未执行 public / tag / GitHub Release。

**Round 146**(2026-06-09,Codex — release-candidate closure):
- 按发布助理口径收口 `launch/oss-public-readiness` 分支,先把当前未提交的 Round 141-145 修复纳入同一 RC 范围,没有启动新功能。
- 校正公开材料:
  - README / README.zh-CN 的 overnight 接手路径从旧 `/daily` / `/tasks` 改为 `/inbox` / `/morning` / `/task` / `/audit`。
  - `docs/launch/v0.1.0-release-notes.md` 和 launch playbook 的测试数更新为 **428 passed / 1 skipped**,journal 更新为 Round 145。
  - no-token Release Room demo、transcript、shot rhythm、recording storyboard 和 release-room playbook 改为用 `/morning` 做早上接手入口。
- 发现并记录 P-038:公开 demo 会在产品动线变化后滞后,发布前必须跑 demo 而不只是跑 pytest。
- 发布前验证:
  - Phase 8 contract gate: **41 passed in 0.94s**。
  - full clean env pytest: **428 passed / 1 skipped**。
  - Release Room no-token demo 可执行,输出包含 `/morning` handoff 和 `/audit`。
  - `uv run ruff check .`;`uv run ruff format --check .`;`uv run mypy src tests`;`git diff --check` 全绿。
- 当前 RC 仍未执行不可逆动作:未改 GitHub public/private,未打 `v0.1.0` tag,未发 GitHub Release。

**Round 145**(2026-06-09,Codex — local Telegram/provider validation first):
- 人类纠正验收边界:真实 Telegram 手机端观感和真实 provider 是否稳定触发 implementer -> reviewer 协作,在当前 Mac 有 Telegram App 和运行凭据时,Agent 必须先验,不能默认交给 human。
- 已把验收分层从"机器 Gate -> human sample"修正为"机器 Gate -> Agent 本机真实样本 -> human 体感 sample"。human 只看是否顺、是否方便接手、是否信任交接。
- 本机实测:
  - Telegram App 可打开 `ai_co` bot;`/project aico` 被真实 bot 收到并回包。
  - 真实协作样本 parent `9efe8b4c-bd03-47ee-8f99-cc7dde5af17a`:target=implementer,adapter=claude-code,done。
  - 日志明确记录 `Collaboration directive: parent_task=9efe8b4c... source=implementer target=reviewer payload_chars=170`。
  - reviewer child `a27d61ef-ea41-44b3-8a81-a4ad74d40a01`:target=reviewer,adapter=codex,done。
  - Telegram 输出触发移动端分片,reviewer 输出被拆为 message `1278` 和后一条短消息;最终截图保存在 `/tmp/aico_telegram_collab_done.png`。
- 运行坑修复:真实验收发现 Telegram long polling 每约 6 秒打印空 warning。原因是默认 `httpx.AsyncClient` read timeout 约 5 秒,短于 Telegram `getUpdates timeout=30`;已把默认 read timeout 改为 `poll_timeout_seconds + 5` 并补单测。
- 验证通过:targeted 25 passed in 0.46s;Phase 8 gate **41 passed in 0.36s**。

**Round 144**(2026-06-09,Codex — Phase 8 contract gate before human sample):
- 对当前北极星 Dogfooding 分层和 `STATUS.md` human sample 队列做二次收口:需要人类看的功能主要剩 `/overnight` delegate 真实 IM 体感、老板查看动线、`/view` Telegram 附件/手机打开体验。
- 盘点现有测试后确认 AI 可以前置验证更多确定性 contract:父子 agent 委派 payload、`Current task:` 风险边界、只读 reviewer 不被 risky parent context 误判、`/overnight` handoff 完整性、移动端分片、`/aico-view` alias、自包含 HTML snapshot 和 Telegram `sendDocument` multipart 上传。
- `docs/playbooks/phase-8-absence-loop.md` 新增 "AI 前置 Contract Gate",写入当前可直接执行的 targeted pytest 命令、覆盖范围表和 human sample 剩余职责。
- 本轮实际执行 contract gate:40 passed in 0.30s。
- 决策:下一轮或后续修同类问题时,先跑 playbook 里的 gate;只有 gate 通过后,才请人类跑 1 条代表性真实 IM 样本。

**Round 143**(2026-06-09,Codex — dogfood validation ladder):
- 人类指出北极星里的"人工 dogfooding"不应理解为每次修复后都靠人完整重跑长链路;父子 agent 委派、`/overnight` 和真实 IM 输出修复周期长,需要机器测试尽量先覆盖。
- 决策:不改北极星三句话本体,只在第三句下新增 Dogfooding 验收分层。Dogfooding 仍是最终标准,但顺序变成机器 Gate → 人工 Sample → 人工 Blocking。
- `docs/agent/06-testing-guide.md` 固化同一规则:确定性 contract 先单测 / 集成 / 模拟 E2E;人工只抽样验证手机体感、真实 provider / Channel 漂移和老板是否知道下一步。
- `docs/journal/BLOCKERS.md` 新增并关闭 B-006,说明当前待测队列不再因为"必须完整人工复验同一长链路"而阻塞。
- 当前 `/overnight` delegate 输出和老板动线复验从"最高优人工完整回归"降级为"机器 Gate 后 1 条代表性真实 IM 样本";如果样本失败,必须留下 `/task <id>`、截图/原始输出、预期效果和实际偏差。
- 本轮仅改文档,未改运行代码;`git diff --check` clean,未跑 Python 单测。

**Round 142**(2026-06-05,Codex — secretary route + mobile readable handoff):
- 人类复验最近一次 `/overnight` 和 implementer -> reviewer 协作,反馈 `Collaboration requested` 后 reviewer 文案仍然是手机上看不动的大块输出。
- 进一步定位:Round 141 解决了“粘连 heading / bullet 换行”,但 Telegram API 3900 字安全上限不等于老板手机阅读上限;约 1800 字 reviewer 审阅仍会形成一整面长墙。
- `StreamedMessageWriter` 改为先复用 `normalize_agent_output_for_im()` 归一化当前累计输出,再按 1400 字移动端阅读上限分段;分段优先选择空行、换行、句号或空格,避免按字符硬切。
- `agent_output_message()` 的 severity bullet 归一化从单换行改为 bullet 前空行,让 `• High` / `• Medium` 变成真正的审阅卡片分隔。
- `/overnight` 回执改成“老板秘书动线”:现在看 `/inbox`,回来接手看 `/morning`,查精确原文看 `/task <id>`,需要 HTML 看 `/view`,项目背景才看 `/brief`。
- `/aico-view` 现在是 `/view` 的别名,避免老板按产品名输入时被当成 unknown persona / adapter。
- 验证通过:targeted 25 passed;full clean env `env -u AICO_VIEW_TOKEN -u AICO_VIEW_ENABLED uv run pytest` **427 passed / 1 skipped**;`ruff check .`;`ruff format --check .`;`mypy src tests`;`git diff --check`。

**Round 141**(2026-06-04,Codex — delegate Telegram readability):
- 人类复验 `/overnight 为我准备好上线github的全部工作...` 后指出两类真实 IM 问题:
  implementer handoff 中 `<b>Heading</b><b>Heading</b>`、`<b>Decision</b>正文` 粘成一段;
  reviewer 输出中 `• High ...。• Medium ...` 多条 finding 被拼到同一行。
- 日志确认 task `4667de18-8bfd-40b1-911d-04a7bfec1c86` 正常完成,reviewer 子任务
  `5499a5ea-f184-452a-a555-86dc4cbaee85` 也正常完成;问题不是任务失败,而是 agent 流式
  chunk 被 `StreamedMessageWriter` 忠实累加后缺少 IM 结构分隔。
- 修复 `agent_output_message()`:agent 输出在进入 Telegram HTML sanitizer 或 rich text fallback 前,
  先做保守 IM normalization,只拆明显粘连的 native heading、已知 section label 和 `•` bullet。
- 不把规则写进 Telegram Channel,保持 core 继续输出平台无关 `MessageContent`;Telegram 仍只负责
  native HTML / spans 映射。
- 新增 native output + streaming 回归测试,覆盖 implementer 截图里的 `<b>Goal received</b>"..."`
  / `<b>Decision</b>正文` 以及 reviewer 文案里的 `。• High` 列表粘连。
- 验证通过:`env -u AICO_VIEW_TOKEN -u AICO_VIEW_ENABLED uv run pytest` **425 passed / 1 skipped**;
  `uv run ruff check .`;`uv run ruff format --check .`;`uv run mypy src tests`;`git diff --check`。

**Round 140**(2026-06-04,Claude — OSS public-launch readiness):
- 老板任务"为我准备好上线 GitHub 的全部工作,要奔着 1k 或 10k star 方向去设计和发力"。
- 收口 Round 137-139 三轮代码改动到 `launch/oss-public-readiness` 分支(包括
  Round 137 IM HTML snapshot、Round 138 协作风险边界修复、Round 139 `/overnight`
  handoff completeness guard)。
- 补齐 OSS 治理资产:`CODE_OF_CONDUCT.md`(Contributor Covenant 2.1 中英双语)、
  `.github/FUNDING.yml` 占位、`.github/dependabot.yml`(weekly pip + monthly Actions)。
- 新增 `docs/contributors/quickstart.md`:30 分钟内完成第一次 PR 的零门槛路径,完全
  跑在 no-token Release Room demo 上。
- 新增 `docs/launch/playbook.md`:面向 1k–10k star 的上线作战书,包括 Show HN /
  4 个 Reddit 子版位 / X / Bluesky / LinkedIn / dev.to 长文模板,D0 → D90 节奏,
  反指标清单和老板缺席护栏。
- 新增 `docs/launch/v0.1.0-release-notes.md`:v0.1.0 GitHub Release notes 草稿,
  可直接贴到 GitHub Release。
- README 增加 Contributing 段对 Contributor Quickstart + CoC 的引用,并把 Roadmap
  near-term 部分对齐到当前真实状态。
- `.github/ISSUE_TEMPLATE/config.yml` 增加 Discussions / Contributor Quickstart 入口。
- `SECURITY.md` 明确响应 SLA(72 小时确认 / 14 天修复)。
- `CONTRIBUTING.md` 顶部增加 first-time contributor 入口和 CoC 引用。
- 验证通过:`env -u AICO_VIEW_TOKEN -u AICO_VIEW_ENABLED uv run pytest` **422
  passed / 1 skipped**;`ruff check .`;`ruff format --check .`(141 files);
  `mypy src tests`(136 source files)。
- 关键决策:不在本轮做新功能,不动 v0.1.0 范围。所有上线工作通过文档 + 模板支撑,
  代码 surface 保持冻结,避免 Show HN 描述与实际产品不一致。

**Round 139**(2026-06-04,Codex — `/overnight` incomplete handoff guard):
- 人类复验 `/overnight 为我准备好上线github的全部工作...` 后,任务 `3f7d57c2` 只在 IM 打出半句 `Community 文件：写一个简短 Code of Conduct...`。
- 日志确认 Claude CLI 运行约 8 分钟后 return code 0,但 stdout 只有 1 个 chunk / 64 字符;SQLite snapshot 却被标成 `done`。这不是 Telegram 截断,而是 AICO 把“CLI 成功退出 + 任意 stdout”误当作可交接成功。
- 新增 offline delegation completion guard:仅对 `/overnight` 任务生效;当最终 `DONE` 输出过短或缺少 done / blocked / risks / next actions 基本段落时,改标 `failed` 并向 IM 发送 `Overnight delegation output incomplete`。
- `/goal` 继续走自己的 Outcome Grader,不复用 overnight handoff 验收;等待审批的 `/overnight` 也不会因空输出被误判失败。
- 验证通过:`env -u AICO_VIEW_TOKEN -u AICO_VIEW_ENABLED uv run pytest` **422 passed / 1 skipped**;`ruff check .`;`ruff format --check .`;`mypy src tests`;`git diff --check`。

**Round 138**(2026-06-03,Codex — `/overnight` collaboration risk boundary fix):
- 人类验收 `/overnight` 时触发真实失败:`Collaboration requested: implementer -> reviewer` 后 reviewer/Codex 子任务被拒绝为 `adapter codex cannot handle shell_exec tasks; use /claude`。
- 根因是协作 payload 带有 parent output context,但真实委托段使用 `Request:` 标签;`TextRiskAssessor` 只识别 `Current task:`,因此把 context 中的 `run pytest` / `git push` / `命令` 等词也纳入风险判定。
- 修复 `collaboration_payload()` 在带 source context 时用 `Current task:` 标记实际委托内容,保持 Codex read-only capability 边界不变,也不绕过 `/approve`。
- 新增回归测试覆盖 TaskBus 与 Orchestrator 两层:parent context 含 `run pytest` / `git push`,但 reviewer 只做风险审阅时仍按 read-only 派给 Codex;真正 shell/write 委托仍由现有风险门禁处理。
- 验证通过:`env -u AICO_VIEW_TOKEN -u AICO_VIEW_ENABLED uv run pytest` **419 passed / 1 skipped**;`ruff check .`;`ruff format --check .`;`mypy src tests`;`git diff --check`。未清理当前 shell 的 view env 时,旧 view 测试会因 401/默认启用预期失败,这是环境变量污染而非本轮代码失败。

**Round 137**(2026-06-02,Codex — aico-view IM HTML snapshot):
- 根据人类安全反馈修正 aico-view 产品入口:`AICO_VIEW_ENABLED=true` 不再表达"自动启动可访问 Web 服务",而是启用 IM 内 `/view [project]` 发送自包含 HTML 快照。
- 新增 `DocumentChannel` 可选附件协议;`TelegramChannel.send_document()` 通过 Bot API `sendDocument` 上传 `.html` 文件,不发送 localhost / 127.0.0.1 链接。
- 新增 `src/aico/view/snapshot.py`:生成 Boss Brief / recent timeline / trace details / memory 的单文件 HTML,内联 CSS,无外部静态资源。
- 新增 `src/aico/view/commands.py`:按当前 active project 生成 snapshot;非附件 Channel 降级为写入 `AICO_VIEW_OUTPUT_DIR` 并回 IM 提示路径。
- `src/aico/app/phase1.py` 新增 `AICO_VIEW_ENABLED` / `AICO_VIEW_OUTPUT_DIR`;`uv run aico-view` HTTP 服务仍保留为显式本机排障/隧道 dogfood,不会由 `AICO_VIEW_ENABLED` 自动启动。
- 新增 ADR-0036 `aico-view IM-delivered HTML snapshot`:写死安全边界——不开入站端口;但 HTML 内容会进入 Telegram 聊天记录,只发可信私聊/小群。
- 验证通过:`uv run pytest` **417 passed / 1 skipped**;`ruff check .`;`ruff format --check .`;`mypy src tests`;`git diff --check`。

**Round 136**(2026-05-31,Claude — Sprint V3 + 路线图全部完成):
- 落地 boss-first-grounding §6 Sprint V3:`aico-view` token 鉴权 + 部署文档 + 安全模型。**§6 路线图 9 个 sprint 全部完成**。
- 新增 `src/aico/view/auth.py`(< 90 行):`TokenGuard.from_env()` 三态决策——token 已设则验证;loopback 无 token 放行(本机便利);**非 loopback 无 token 全请求 401**(刻意拒绝裸暴露)。token 比较走 `secrets.compare_digest` 防 timing。
- `src/aico/view/app.py`:`build_view_app(..., token_guard=None)` 注入 guard;三个受保护路由 `/`、`/trace/{id}`、`/memory` 调 `guard.check(request)`;`/healthz` 和 `/static/style.css` 不受保护(liveness probe + 公开样式)。
- 新增 ADR-0035 `aico-view token auth posture`(Accepted):写死行为矩阵 + 不做的事(无多用户、无 OIDC、无 rate limit)。
- 新增 `docs/human/aico-view-deploy.md`:三种形态(localhost / ngrok / Cloudflare tunnel)+ 安全模型 + env 速查 + "不要做的事" 清单。
- 验证通过:`uv run pytest` **411 passed / 1 skipped**(原 394 + 17 V3);ruff / format / mypy 全绿。
- CHANGELOG 加 `AICO_VIEW_TOKEN` 说明;quickstart 链到 deploy 文档。
- 在 `docs/architecture/boss-first-grounding.md` §6 表格给 V3 标 ✅ 引用 Round 136。
- **路线图状态**:M1 ✅ / M2 ✅ / M3 ✅ / A1 ✅ / A2 ✅ / A3 ✅ / V1 ✅ / V2 ✅ / V3 ✅。Phase 8 复盘 / Future F-1 F-2 / Orchestrator 拆分(B-005)留作下一阶段。

**Round 135**(2026-05-31,Claude — Sprint A3):
- 落地 boss-first-grounding §6 Sprint A3:lead 内务 `/timeline` 和 `/rollback memory|experience|task`,以及新增 `AuditEventType.ROLLBACK_PERFORMED`。
- 新增 `src/aico/core/timeline_rollback_commands.py`(< 300 行):
  - `TimelineCommandHandler` 支持 `--since 24h --source audit|memory|task --limit 30 --trace <prefix>`;解析失败给 Usage,过滤不到事件给 "no events in window"。
  - `RollbackCommandHandler`:`/rollback memory <id>` archive fact;`/rollback experience <id>` active→CANDIDATE;`/rollback task <id>` 只写 ROLLBACK_PERFORMED audit,**不级联**撤 memory/experience(避免假装撤了 file/shell)。
- `src/aico/core/models.py` AuditEventType 加 `ROLLBACK_PERFORMED`。
- `src/aico/core/task_bus.py` 加 `audit_log()` accessor 暴露给 RollbackCommandHandler。
- `src/aico/core/orchestrator.py`:`_setup_boss_and_lead_handlers` 加 2 个 handler 实例化,命令分发加 2 个 elif(遵守 B-005 workaround,主体 +4 行,新逻辑全部进新模块)。
- `src/aico/core/commands.py`:`TIMELINE` / `ROLLBACK`;`TIMELINE` 进 lowered 短命令集;help 加两行。
- 新增 ADR-0034 `Rollback granularity boundary`(Accepted):写死 `/rollback task` 只 audit、不级联;永远不撤 git/shell/file。
- 验证通过:`uv run pytest` **394 passed / 1 skipped**(原 385 + 9 A3);ruff / format / mypy 全绿。
- CHANGELOG 加 `/timeline` `/rollback` 说明;`docs/human/daily-ops.md` 新增 "Lead 内务命令" 段。
- 在 `docs/architecture/boss-first-grounding.md` §6 表格给 A3 标 ✅ 引用 Round 135。

**Round 134**(2026-05-31,Claude — Sprint V2):
- 落地 boss-first-grounding §6 Sprint V2:aico-view 三视图末尾追加 IM deep-link 按钮。
- 新增 `src/aico/view/deep_link.py`(< 90 行):`DeepLinkSettings(telegram_bot_username)` + `load_deep_link_settings_from_env()` 读 `AICO_VIEW_TELEGRAM_BOT_USERNAME`(可选);`render_command_link` 在有 bot 时生成 `https://t.me/<bot>?text=<url-encoded>`,无 bot 时降级为 `cmd-copy` 文本提示(老板复制粘贴)。
- `src/aico/view/app.py` 三视图都接 `deep_link_settings`:Timeline 末尾给 `/inbox` `/morning` `/undo`;Trace 末尾给 `/why <short>` `/task <short>`;Memory 每条 atom 给 promote / archive / forget(按 status + kind 选)。CSS 加 `.cmd-links` `.cmd-link` `.cmd-copy` 样式(pill 按钮 + 暗色)。
- 关键边界:**仍然只读**。deep link 只是把命令预填到 IM 输入框,实际写入仍走 IM(Channel + 现有审批/审计)。Feishu 暂用 cmd-copy 降级(Feishu 无标准 deep link)。
- 验证通过:`uv run pytest` **385 passed / 1 skipped**(原 377 + 8 V2);ruff / format / mypy 全绿。
- 不开 ADR(V2 是 V1 + ADR-0033 的延伸,不引入新决策)。
- 在 `docs/architecture/boss-first-grounding.md` §6 表格给 V2 标 ✅ 引用 Round 134。

**Round 133**(2026-05-31,Claude — Sprint V1):
- 落地 boss-first-grounding §6 Sprint V1:`aico-view` 只读 FastAPI Web,三视图 mobile-first。
- 新增 `src/aico/view/app.py`(< 300 行):`build_view_app(settings)` 返回 FastAPI app;Timeline `/`、Task Trace `/trace/{trace_id}`(支持短 ID 前缀匹配)、Memory Tree `/memory`、`/healthz`、`/static/style.css`。
- 新增 `src/aico/app/view_cli.py` + `pyproject.toml [project.scripts]` `aico-view = "aico.app.view_cli:main"`;env 配置 `AICO_AUDIT_LOG_PATH` / `AICO_MEMORY_PATH` / `AICO_STATE_DB_PATH` / `AICO_VIEW_PROJECT_IDS` / `AICO_VIEW_HOST` / `AICO_VIEW_PORT`。
- 直接复用 ADR-0030 UnifiedEventIndex,每次请求重建 index(JSONL 解析快、避免缓存失效);Memory Tree 区分 experience(在前)和 fact(在后)。
- 关键边界:**Read-only**(任何 POST/PUT/DELETE 都 405)、**不挂 phase1 runtime/channel/adapter**、**无 Jinja2/JS framework**(f-string + html.escape);默认 `127.0.0.1`,不上公网鉴权(V3 加 token)。
- 新增 ADR-0033 `aico-view read-only mobile web surface`(Accepted)。
- 验证通过:`uv run pytest` **377 passed / 1 skipped**(原 365 + 12 V1);`uv run ruff check .`;`uv run ruff format --check .`;`uv run mypy src tests`。
- CHANGELOG 加 `aico-view` 说明;`docs/human/quickstart.md` 加启动指引。
- 在 `docs/architecture/boss-first-grounding.md` §6 表格给 V1 标 ✅ 引用 Round 133。

**Round 132**(2026-05-31,Claude — Sprint A2):
- 落地 boss-first-grounding §6 Sprint A2:boss-only `/undo` 和 `/why`,`/inbox` 和 `/morning` 内嵌 Recent activity 摘要。
- 新增 `undo_why_commands.py`(< 280 行):`UndoCommandHandler` 撤销最近 24 小时内 AICO 内部 memory 变更(experience promote → CANDIDATE / archive → ACTIVE / fact append → archive),回复显式写明"不撤 git / shell / file";`WhyCommandHandler` 按 short_id 前缀匹配走 UnifiedEventIndex 的 trace 序列。
- `inbox.py` / `morning.py` 加可选 `recent_events` 参数,渲染 "Recent activity" 段 + 一行 `/why <short_id>` 提示。
- `orchestrator.py` 新增 `_build_event_index` 私有方法 + 模块级 helper `_build_orchestrator_event_index`(派生只读 UnifiedEventIndex,不写真相);`__init__` 拆为 `_setup_command_handlers` → `_setup_coordinators` / `_setup_boss_and_lead_handlers` / `_setup_workflow_handlers` 三个子方法(每个 <40 行,满足 100 行硬限)。
- `commands.py` 加 `CommandName.UNDO` / `WHY`,help 加两行。
- 新增 ADR-0032 `Undo and Why scope boundary`(Accepted)。
- 新增 BLOCKER B-005 `Orchestrator class size regression`(🟡 DEFERRED):类规模重新涨到 ~585 行,后续 sprint 加 handler 必须遵守"主体不变"边界,V3 完成后做独立拆分。
- 验证通过:`uv run pytest` **365 passed / 1 skipped**;ruff / format / mypy 全绿。
- CHANGELOG 加 `/undo` / `/why` / Recent activity 说明。
- 在 `docs/architecture/boss-first-grounding.md` §6 表格给 A2 标 ✅ 引用 Round 132。

**Round 131**(2026-05-31,Claude — Sprint M3):
- 落地 boss-first-grounding §6 Sprint M3:Outcome Grader verdict 反向回写 experience confidence / verdict_hits / verdict_misses / injection_count。
- `outcome_grader.py`:新增 `GraderVerdict` StrEnum + `parse_verdict(output)` 容错解析(大小写、Markdown emphasis 都接受);未匹配返回 `None`,**不猜测**。
- `memory.py`:`MemoryStore` Protocol + `JsonlMemoryStore` 实现 `update_experience_meta(memory_id, *, confidence_delta, verdict_hits_delta, verdict_misses_delta, injection_count_delta)`,clamp 到 [0, 1]。
- 新增 `experience_feedback.py`(< 90 行):`injected_experience_ids(task)` + `apply_verdict_to_owner_experiences(store, owner_task, verdict)`;PASS→+0.05、PARTIAL→0、FAIL→-0.10;PASS/PARTIAL 计 hit、PARTIAL/FAIL 计 miss;每次都 injection_count+1。
- `goal_brief_commands.py`:GoalBriefCommandHandler 注入 `memory_store`,grader 跑完后捕获 output → parse_verdict → apply_verdict;**同时把 grader task trace_id 接到 owner_task.trace_id**(完成 ADR-0030 留给 M3 的 grader trace 续接)。
- `orchestrator.py`:GoalBriefCommandHandler 实例化传入 memory_store(主体仅 +1 行)。
- 验证通过:`uv run pytest` **360 passed / 1 skipped**(原 347 + 12 feedback 单测 + 1 E2E);ruff / format / mypy 全绿。
- 关键边界:experience meta 反向回写**只在 grader 完成时发生**,普通 task 注入不主动 +1 injection_count(否则未被验收的注入会污染 confidence)。
- 不开 ADR(M3 是 M1+M2+ADR-0030 留作业的兑现,不引入新决策)。
- 在 `docs/architecture/boss-first-grounding.md` §6 表格给 M3 标 ✅ 引用 Round 131。

**Round 130**(2026-05-31,Claude — Sprint M2):
- 落地 boss-first-grounding §6 Sprint M2:`/experience` 命令 + ExperienceLayer prompt 注入。
- `MemoryStore` Protocol 加 `promote_experience(memory_id, *, applies_to, triggers)` + `list_experiences(scope, *, role_id, trigger_keys, statuses)`;`JsonlMemoryStore` 实现完整。
- `prompt_stack.py` 增加 `_experience_section`,在 `_memory_section` 后、`_runtime_section` 前;形成"事实 → 经验 → 任务"认知链。
- `orchestrator_task_factory.py`:`task_for_assignment` 装配前调 `list_experiences(role_id=assignment.role)`,装配后把 memory_ids 写到 task metadata key `aico.injected_experience_ids`(M3 grader 反向回写的前置)。
- 新增 `experience_commands.py` ExperienceCommandHandler:`review`(列 candidate)/`list [role]`(列 active)/`promote <id> [as <role,role>]`(candidate → active 并记录 applies_to)/`archive <id>`(active → archived)。
- 关键边界:严格 lead 内务,boss-first 命令组不包含 `/experience`;experience 与 fact 共用存储但走独立注入通道(避免污染 retrieval governance)。
- 新增 ADR-0031 `Experience as injectable memory`(Accepted)。
- 验证通过:`uv run pytest` **347 passed / 1 skipped**;`uv run ruff check .`;`uv run ruff format --check .`;`uv run mypy src tests`。
- CHANGELOG 加 `/experience` 命令说明。
- 在 `docs/architecture/boss-first-grounding.md` §6 表格给 M2 标 ✅ 引用 Round 130。

**Round 129**(2026-05-31,Claude — Sprint A1):
- 落地 boss-first-grounding §6 路线图 Sprint A1:Audit + trace_id + Unified Event Index。
- `src/aico/core/models.py`:`AuditEvent`、`Task` 都新增 `trace_id: str | None = None`(default None,向后兼容)。
- `src/aico/core/memory.py`:`MemoryAtom` 新增 `trace_id: str | None = None`。
- `src/aico/core/audit.py`:`record(...)` 和 `record_event(...)` 自动从 `task.trace_id || task.task_id` 取 trace_id,默认全链路传播;memory_broadcast 等 task-less 调用 fallback 到 `task_id` 参数本身。
- 新增 `src/aico/core/unified_event.py`(< 150 行):`UnifiedEvent` / `UnifiedEventIndex` Protocol / `InMemoryUnifiedEventIndex`,把 audit / memory / task 三源按 trace_id 聚合;`short_event_id` / `short_memory_id` / `short_trace_id` 三个 IM 渲染辅助函数(复用现有 `short_id_text`)。
- 关键边界(写进 ADR-0030):Index **派生只读、不拥有真相**;真相仍在 audit JSONL / memory JSONL / SQLite task store;一旦运行新代码,JSONL 升级是单向门(`FrozenModel.extra="forbid"` 阻止老代码读新字段)。
- 新增 ADR-0030 `Unified Event Index — read-only cross-source trace view`,Accepted。
- PITFALLS 新增 P-033 "Memory/Audit JSONL 升级是单向门",索引新增"持久化与 schema 兼容"分类。
- 子任务 trace_id 通过 `task.model_copy(update=...)` 免费继承;**唯一例外是 Grader follow-up**,它是新顶层 task,trace 默认 = 自己 task_id,留 M3 把它接到 graded_task 的 trace。
- 验证通过:`uv run pytest` **338 passed / 1 skipped**(330 + 3 unified_event + 3 audit + 2 task_bus);`uv run ruff check .`;`uv run ruff format --check .`;`uv run mypy src tests`。
- 在 `docs/architecture/boss-first-grounding.md` §6 表格给 A1 标 ✅ 引用 Round 129。

**Round 128**(2026-05-31,Claude — Sprint M1):
- 落地 boss-first-grounding §6 路线图 Sprint M1:Memory + Experience 数据层分层。
- `src/aico/core/memory.py`:新增 `MemoryKind` enum(`fact` / `experience`)和 `ExperienceMeta` 模型(`applies_to` / `triggers` / `injection_count` / `verdict_hits` / `verdict_misses`);`MemoryAtom` 增加 `kind` 与 `experience` 两字段 + validator(experience kind 必须带 meta、fact kind 不得带 meta)。
- `src/aico/core/dream.py`:Dream 输出从普通 candidate memory 升级为 `kind=EXPERIENCE` 的 candidate experience,`experience.triggers` 携带 candidate key(如 `failed:adapter_idle_timeout`)。文案 `candidate memory only` → `candidate experience only`,提示晋升后才注入 prompt。
- 关键边界:M1 仅做数据层,**不**注入 prompt(留 M2),**不**做 grader 反馈回写(留 M3)。
- JSONL 向后兼容已验证:老记录无 `kind` 字段 → 默认 `FACT`(测试 `test_jsonl_store_loads_legacy_atom_without_kind` 覆盖)。
- 验证通过:`uv run pytest` 330 passed / 1 skipped;`uv run ruff check .`;`uv run ruff format --check .`;`uv run mypy src tests`。
- 不开 ADR(只是字段扩展,ADR-0020/0021/0022 已覆盖范围)。
- 在 `docs/architecture/boss-first-grounding.md` §6 表格给 M1 标 ✅ 引用 Round 128。

**Round 127**(2026-05-29,Claude):
- 与人类两轮脑暴 absence-first 边界、lead 主动机制、Memory/Experience 分层、Audit/Rollback 可视化和命令爆炸问题。
- 决策:近期高优为三块基础能力——Memory + Experience 分层、Audit + Rollback(+ aico-view 移动只读 web)、之后再回 Absence Loop 加固。Lead 主动机制(Standing Charter / Proposal Queue)和 Team Karpathy Loop 标记为 Future,暂不实现。
- 输出 [`docs/architecture/boss-first-grounding.md`](docs/architecture/boss-first-grounding.md):基于源码核实的痛点 P1-P6、解法 §3、L1-L6 分层架构图(drawio xml 嵌入)、sprint 路线图 M1/M2/M3/A1/A2/A3/V1/V2/V3 和新会话落地操作指引。
- 关键 boss-first 决策:命令分层(老板只看 6 个核心动作);`/undo` 与 `/why` 替代多 ID 命令;trace 深度可视化走 aico-view(只读,写操作回 IM,符合 absence-first)。
- 关键边界:`/undo` 与 `/rollback` 只撤 AICO 内部状态(memory / experience / appointment),不撤 git / shell / file。
- 在 README 和 `docs/architecture/overview.md` 加入了对新设计文档的入口指针。
- 本轮只新增设计文档与索引,未改运行代码,未跑测试。

**Round 126**(2026-05-27,Codex):
- 按人类真实 IM dogfood 反馈校准当前待办:Phase 8 Absence Loop 验收已执行,但效果不佳,暂不继续投入该方向;运行侧改回 `AICO_PREFER_NATIVE_CHANNEL_FORMAT=false`。
- 关闭 Phase 5 真实协作 smoke test 高优待办:人类确认真实 IM 下协作能触发,后续不再把它作为下一轮回归项。
- 保留 Lead decision workflow、Goal Brief v0、Release Room、Feishu、Codex bind / Claude resume 和 usage 上报等原待办。
- 将“开源首屏二次验收:AI agent 开发者 / 个人开发者视角”提升为下一轮最高优先级。
- 本轮只更新状态与交接文档,未改运行代码,未跑测试。

**Round 125**(2026-05-27,Codex):
- 人类反馈真实 Telegram 输出把 `Still running: no adapter output for 120s...` 和后续 native HTML 结果拼到同一条消息里,导致 `<b>` / `<code>` 等标签裸露,列表也粘成一段。
- 根因确认:`OutputType.STATUS` quiet heartbeat 过去通过 `StreamedMessageWriter.append()` 写入 `_current_text`;后续 agent 输出到达时,状态行和 native HTML 混在同一缓冲区,`/task <id>` 的 `<id>` 还会让 native HTML 验证失败并回退。
- 修复 `StreamedMessageWriter.show_status()`:heartbeat 只临时编辑当前消息,不进入最终输出缓冲区;真实输出到达后会替换 heartbeat。
- `Orchestrator` 对 `OutputType.STATUS` 改为 `show_status()` 后 `continue`,确保 status 不进入 captured output、native HTML 验证或最终 IM 内容。
- 补充 Telegram native output prompt:标题、段落、列表项要分行,bullet 使用 `•`,不要使用 Markdown `- ` bullet。
- 新增 `tests/unit/test_streaming.py`,覆盖 heartbeat 不污染 native final output,以及输出开始后 late status 不覆盖结果。
- 验证通过:`uv run pytest` 325 passed / 1 skipped;`uv run ruff check .`;`uv run ruff format --check .`;`uv run mypy src tests`;`git diff --check`。

**Round 124**(2026-05-27,Codex):
- 人类真实 dogfood `/goal implementer inspect inbox handoff ...` 后,Telegram 收到裸 `<b>` / `<blockquote>` / `<pre>` 标签,说明 native Telegram HTML 输出被打回 fallback。
- 根因确认:模型输出整体是合法 Telegram HTML,但 `<pre>` 文本里包含 `/task <id>`、`/task <id>` 这类占位符;Python HTML parser 把 `<id>` 当 unknown tag,旧 sanitizer 因 unsupported tag 拒绝整条 native 输出。
- 修复 Telegram HTML sanitizer:在 `<pre>` / `<code>` literal block 内遇到 unknown tag 或 placeholder 时,安全转义为文本保留;literal block 外的 unsupported HTML 仍会失败并回退。
- 新增单测覆盖 `<pre>/task <id></pre>` 会变成 `<pre>/task &lt;id&gt;</pre>` 并继续走 native Telegram HTML。
- 验证通过:`uv run pytest` 323 passed / 1 skipped;`uv run ruff check .`;`uv run ruff format --check .`;`uv run mypy src tests`;`git diff --check`。

**Round 123**(2026-05-27,Codex):
- 人类指出 `rich_text_message()` 适配模型输出到 Telegram spans 的 case 可能无限膨胀,要求另起一条链路验证“让模型直接输出 Channel 支持格式,失败再回退”。
- 新增 opt-in native output contract:`AICO_PREFER_NATIVE_CHANNEL_FORMAT=true` 时,Telegram task prompt 会要求 agent 使用 Telegram Bot API HTML 子集,而不是 Markdown。
- 新增 `MessageNativeFormat.TELEGRAM_HTML` 和 `native_output.py`;agent 输出先经过 Telegram HTML 白名单 sanitizer,只允许安全标签且不允许属性/unsupported tag。
- `StreamedMessageWriter` 优先发送 native Telegram HTML;如果模型输出 Markdown table、fenced code 或 unsupported HTML,自动回退到 `rich_text_message()`。
- Telegram Channel 支持 `MessageContent.native_format=telegram_html` 时直接发送 HTML parse mode,不再把 native HTML 当 spans 重写。
- 修复 fallback 中单行 fenced code(```uv run pytest```)被吞的问题。
- 验证通过:`uv run pytest` 322 passed / 1 skipped;`uv run ruff check .`;`uv run ruff format --check .`;`uv run mypy src tests`;`git diff --check`。

**Round 122**(2026-05-27,Codex):
- 人类确认 Telegram 侧返回格式仍有较大问题:collaboration requested 没有富文本化;模型复杂 Markdown 输出没有被稳定转为 Telegram HTML;`/recall` 中带粘连 `## DecisionYes` 的记忆内容难读。
- 确认当前架构:核心不直接输出 Telegram Markdown,而是输出 `MessageContent.text + MessageTextSpan`;Telegram Channel 在有 spans 时用 `parse_mode=HTML` 发送。
- 将 renderer 从“逐命令补 spans”升级为通用 IM Markdown normalization + span rendering:先修正模型常见 Markdown 结构,再生成平台无关 spans。
- `rich_text_message()` 新增粘连 Markdown heading 拆分、已知 heading 内容拆分、Markdown table 到等宽 IM table、fenced code block code span、大小写无关 label span。
- `Collaboration requested` 内置提示改为结构化富文本消息,显示 source / target。
- 新增单测覆盖粘连 heading、Markdown table、fenced code block、Telegram HTML 输出和 collaboration requested spans。
- 验证通过:`uv run pytest` 315 passed / 1 skipped;`uv run ruff check .`;`uv run ruff format --check .`;`uv run mypy src tests`;`git diff --check`。

**Round 121**(2026-05-27,Codex):
- 人类反馈纯英文 agent 回复有时阅读吃力,要求新增一个通用语言切换命令,能力只限制 agent 回复语言,默认英文。
- 新增 `/language [en|zh]` 命令;`/language` 查看当前 chat 的 agent response language,`/language zh` 设置为简体中文,`/language en` 恢复默认英文。
- 新增 `ResponseLanguageStore`,按 `session_scope` 记录偏好;所有真正提交给 agent 的 task 在 `_run_task()` 前统一注入 `Response language` 约束,覆盖 plain task、project role task、Goal、broadcast 和 collaboration。
- 语言约束只作用于 agent payload,不强制翻译 AICO 内置命令、代码、CLI 片段、路径、日志、标识符、协议关键字和严格 JSON/schema。
- 修复实现中发现的一个风险:语言提示词不能包含 `shell command` 等风险关键词,否则会让普通任务误触发 approval gate;最终提示词改为 `CLI snippets` 并保留 schema 约束。
- 验证通过:`uv run pytest` 311 passed / 1 skipped;`uv run ruff check .`;`uv run ruff format --check .`;`uv run mypy src tests`;`git diff --check`。

**Round 120**(2026-05-27,Codex):
- 人类 dogfood 确认 `/inbox` 和 `/morning` 没问题,但反馈 `/goal`、Outcome Grader 和 `/recall` 返回没有 IM Markdown/富文本格式化,`/dream` 输出也难以判断是否正确。
- 修复 Goal Brief、Outcome Grader、Dream review、Memory remembered/recall/archived/no-result 等内置命令消息,统一走 `rich_text_message()`,让标题、无序列表、字段 label 和 slash command 在 Telegram/IM 中可格式化。
- 扩展 `message_rendering` 的 label keys,覆盖 `owner`、`tracking`、`goal`、`grader`、`graded_task`、`query`、`purpose`、`evidence` 等 Phase 8 输出字段。
- 优化 `/dream`:从“逐条吐旧 task 候选”改为按阻塞/失败原因聚合成 reusable lesson candidate,并在输出中解释 Meaning / Effect / Next,明确 candidate memory 不会自动注入 prompt。
- 新增/更新单测覆盖 Goal/Dream/Recall 富文本 spans 和 Dream 聚合候选。
- 验证通过:`uv run pytest` 309 passed / 1 skipped;`uv run ruff check .`;`uv run ruff format --check .`;`uv run mypy src tests`;`git diff --check`。

**Round 119**(2026-05-26,Codex):
- 人类要求把刚新增的四个 Sprint 按顺序执行,并给出 human 可逐条 dogfood 的问题样例、预期观测指标和效果。
- Sprint 2 完成:`/morning` 新增 active-project 手动早报,汇总 done、blocked、risks、overnight handoffs 和 next actions,让老板早上不必翻 `/tasks`。
- Sprint 3 完成:Goal Brief 任务完成后自动寻找 tester / reviewer 生成 Outcome Grader 任务;grader prompt 要求 verdict、evidence、gaps 和 boss_next_action,且被标记为内部只读验收任务。
- Sprint 4 完成:`/dream` 从当前项目任务状态生成 candidate runbook memory,只写 `candidate` 状态,默认不会进入 Prompt Stack。
- Sprint 5 完成:MemoryStore / MemoryRetriever 默认使用本地 hybrid scorer,支持 exact phrase、短语 overlap 和中英 alias fallback,治理边界仍由 scope / purpose / sensitivity / confidence 控制。
- 验证通过:`uv run pytest` 309 passed / 1 skipped;`uv run ruff check .`;`uv run ruff format --check .`;`uv run mypy src tests`;`git diff --check`。

**Round 118**(2026-05-26,Codex):
- 人类确认把 Phase 8 后续 P0-P4 全部纳入短期可落地计划,并要求写入文档后直接进入研发。
- 新增 ADR-0029 `Phase 8 Absence Loop`,把 Phase 8 明确为“下任务 -> 执行 -> 审批/叫停 -> 验收 -> 早上接手 -> 经验沉淀 -> 下次召回”的老板缺席闭环。
- 新增 `docs/playbooks/phase-8-absence-loop.md`,把 Sprint 1 actionable inbox、Sprint 2 morning handoff、Sprint 3 outcome grader、Sprint 4 Dream/runbook memory、Sprint 5 hybrid retrieval 写成直接可问的 IM 验收路径。
- 更新 playbook / ADR 索引,让后续 Agent 接手时先按 sprint 队列执行,不要把 Dream、self-improving 和 retrieval backend 一锅炖。
- 进入 Sprint 1 研发:`/inbox` 新增 `First action`,并把待审批、running、failed/interrupted/rejected、overnight handoff、Goal/decision、collaboration follow-up 都改成带明确下一步命令的动作项。
- 验证通过:`uv run pytest` 305 passed / 1 skipped,`uv run ruff check .`,`uv run ruff format --check .`,`uv run mypy src tests`,`git diff --check`。

**Round 117**(2026-05-26,Codex):
- 人类继续追问 reviewer/Codex 为什么同一条 `/ask reviewer review whether the Phase 8 inbox plan violates approval or audit boundaries...` 仍然 120/240 秒只有 heartbeat。
- 日志确认新 task `3be492f3` 已 accepted 并进入 `Stream start`;SQLite 显示 payload 约 1996 字符;`ps` 确认 Codex 子进程确实在跑且命令中包含完整 reviewer prompt。
- 产品判断:这不是问题太难,也不是 `/ask` 没交给 Codex;短 read-only boundary review 不应 6 分钟没有任何 stdout。
- 根因判断:Round 116 关闭 stdin 后仍卡住,下一层是 stderr pipe。Codex CLI 会把运行头、hook、工具日志和 warning 写 stderr;AICO 过去只在进程退出后读 stderr,可能导致 pipe 写满后反压阻塞,stdout 永远出不来。
- 修复 `_run_task()` 在子进程启动后立即后台 drain stderr,仅保留 tail 用于失败错误内容;成功任务不把 stderr 噪音推给 IM。
- 新增单测构造“stderr 不被读取则 process.wait 不返回”的场景,确认 adapter 会并发 drain stderr。
- 验证通过:`uv run pytest` 305 passed / 1 skipped,`uv run ruff check .`,`uv run ruff format --check .`,`uv run mypy src tests`,`git diff --check`;结构扫描无单类 >500 或单函数 >100。
- 人类真实 IM 复验确认改动有效,reviewer/Codex 长任务卡住问题关闭。

**Round 116**(2026-05-26,Codex):
- 人类验证 Round 115 heartbeat 生效,但新 task `0e72ac63` 连续显示 `Still running...` 到 1680 秒仍没有结果。
- 日志和 SQLite 状态确认该任务已被 Codex 接收并进入 `Stream start`,payload 约 1996 字符,不是异常巨大的 prompt;没有任何 `type=text` 输出。
- 最小 Codex CLI smoke 在相同用户权限下 4 秒返回 `AICO_SMOKE_OK`,说明不是 Codex CLI、账号或网络整体不可用。
- 根因判断:Adapter 启动子进程时未显式关闭 stdin;Codex 0.125 `exec` 会尝试读取 stdin 作为 additional input,若继承到不会 EOF 的 stdin,会长期等待而没有 stdout。
- 修复 `_create_process()` 为 `stdin=DEVNULL`,让 Claude/Codex/optional CLI adapter 都以真正非交互形态启动。
- 新增单测覆盖子进程创建时 stdin 关闭,并更新 CHANGELOG、Phase 5 playbook 和 P-026。
- 验证通过:`uv run pytest` 304 passed / 1 skipped,`uv run ruff check .`,`uv run ruff format --check .`,`uv run mypy src tests`,`git diff --check`。
- 注意:当前已经 running 的 `0e72ac63` 不会自动获得修复,需要 `/interrupt 0e72ac63` 后重启 AICO 再提交。

**Round 115**(2026-05-26,Codex):
- 排查人类真实 IM 长任务 `01ddaa36`:日志确认 Codex adapter 已接收任务、CLI 进程已启动并进入 `Stream start`,但 14 分钟以上没有 stdout chunk 或退出事件;这不是路由提交失败,而是 provider 长静默导致 IM 缺少活性反馈。
- 产品判断:Round 114 放宽 idle timeout 后,长任务不应被 5 分钟误杀,但 absence-first 仍要求老板离开后能看到“员工还在工作”、能从 IM 汇总待处理事项、能随时 `/interrupt`。
- 新增 Adapter quiet heartbeat:底层进程存活但长时间无 stdout 时产出 `OutputType.STATUS`,IM 显示 `Still running...`;TaskBus 保持任务 `running`,并把 status 写入 reason。
- `OutputType.STATUS` 不进入普通任务 captured output,避免污染 lead decision memo、Goal Brief 结果或协作上下文。
- 新增 `/inbox` 只读命令,按当前 active project 汇总待审批、running 静默任务、failed/interrupted/rejected、`/overnight` 工单、Goal Brief / lead decision 和协作 follow-up。
- 同步更新 daily ops、Phase 5 / Phase 8 playbook、CHANGELOG 和 P-025。
- 验证通过:`uv run pytest` 303 passed / 1 skipped,`uv run ruff check .`,`uv run ruff format --check .`,`uv run mypy src tests`,`git diff --check`。

**Round 114**(2026-05-25,Codex):
- 排查人类下午真实 IM dogfood:`/ask reviewer review whether the Phase 8 inbox plan violates approval or audit boundaries...` 再次返回 `ERROR: adapter output idle timeout after 300s`。
- 产品判断:5 分钟对“公司员工”不是异常长任务;在 absence-first 场景里,no-output timeout 不能等同于 task runtime limit,否则老板不在时会误杀正常长 review / dogfooding。
- 将 Codex / Cursor / CodeFlicker / Trae / Gemini optional CLI adapter 默认 `output_idle_timeout_seconds` 从 300 秒放宽到 1800 秒。
- `Phase1Settings` 允许 `AICO_*_OUTPUT_IDLE_TIMEOUT_SECONDS=0`,启动 runtime 时会转换为 `None`,即禁用自动 no-output idle timeout;仍可用 `/interrupt <task_id>` 远程叫停。
- 更新 daily ops、Phase 5 collaboration playbook、optional adapter playbook 和 PITFALL P-014 / P-022,明确默认 1800 秒、`0` 禁用、这是 no-output guard 不是任务总时长限制。
- 新增/更新测试覆盖 optional adapter 默认 1800 秒和 `0` 禁用。
- 验证通过:`uv run pytest` 301 passed / 1 skipped,`ruff check .`,`ruff format --check .`,`mypy src tests`,`git diff --check`。

**Round 113**(2026-05-25,Codex):
- 排查人类真实 IM dogfood:`/ask reviewer review whether the Phase 8 inbox plan violates approval or audit boundaries...` 首次任务 `f9d9990f` 被临时任命到 `claude-code`,新 provider session 启动后 7 分钟无 stdout,被人类 `/interrupt` 后收口为 `failed / task interrupted`。
- 继续排查后续成功输出任务 `f8e6c321`:reviewer 输出了 `@implementer: please reflect (a)-(d) ...`,系统触发 `Collaboration requested: implementer -> implementer`,但 child task 只收到短指令,没有收到 reviewer 前文中定义的 (a)-(d),导致 implementer 回答“缺少上下文”。
- 修复协作 handoff:触发 child task 时会把父任务截至协作指令前的可见输出作为 `Context from ... output so far` 注入 child payload,避免引用型短指令丢上下文。
- 修复协作来源展示:project appointment 任务优先用 `aico.assignment_role` 作为协作来源和 audit actor,避免 reviewer 被底层 claude/implementer persona 显示成 `implementer -> implementer`。
- 新增回归测试覆盖 parent context 传递和 assignment role 来源展示。
- 验证通过:`uv run pytest` 300 passed / 1 skipped,`ruff check .`,`ruff format --check .`,`mypy src tests`,`git diff --check`。

**Round 112**(2026-05-25,Codex):
- 按人类选择的方案 C,新增并强化 AICO 的"老板不在场假设",但不改写北极星三句话正文。
- `NORTH_STAR.md` 在第一句业务价值下新增"老板缺席操作模型(Absence-first)",明确 AICO 默认老板不在电脑前,通过 IM 指挥本地 AI CLI 团队继续工作。
- 将 AICO 与 OMC / CoWork OS 的边界写清:OMC 偏浏览器里经营 AI 公司,CoWork OS 偏桌面 AI super app,AICO 偏离开电脑后的远程异步托管和交接。
- 新增 5 个后续功能取舍问题:只靠 IM 能不能下达、离开后能不能推进、风险能不能等审批、早上能不能看懂、出问题能不能审计/叫停/恢复。
- `STATUS.md` 更新宏大叙事和"老板不在场假设",并把 Phase 8 operator inbox / morning handoff 重新锚定为 absence-first 的关键拼图。
- 本轮只更新产品目标与交接文档,未改运行代码,未跑单测。

**Round 111**(2026-05-24,Codex):
- 排查人类真实 IM 反馈:两条验证命令只留下 `4697ce83... [codex]: running` 与 `4c31d567... [codex]: running`。
- 日志确认两条任务均由 Codex 接收后 300 秒无 stdout,最终触发 idle timeout;当时没有产生 lead decision memo 或 reviewer child task 的可见结果。
- 修复 `/ask lead ...` 语义:`lead` / `default` 现在会解析到当前项目 default assignment,使老板可用自然 lead 说法触发 lead decision workflow。
- 修复协作指令解析:Adapter 输出中的 `@reviewer: ...` 不再必须是第一条非空行;模型先输出计划、后输出 reviewer 指令也能触发 child task。
- 修复协作输出展示:含协作指令的多行输出会保留非指令正文,不会为了触发 child task 把前面的计划正文吞掉。
- 新增回归测试覆盖 lead alias、后续行协作指令、正文保留和现有 lead decision / collaboration 行为。
- 验证通过:`pytest` 298 passed / 1 skipped,`ruff check .`,`ruff format --check .`,`mypy src tests`。

**Round 109**(2026-05-22,Codex):
- 按人类最新反馈校准待办状态:Adapter appointment / concurrency 真实 IM 回归已由人类验证完成,不再放在下一轮高优队列。
- Memory Retrieval 真实 IM 验收已由人类验证完成,不再放在下一轮高优队列。
- 将剩余真实 IM 待办改写为“真实问题列表 + 预期效果”,避免下一轮只按标题重复执行。
- 本轮只更新状态与交接文档,未改运行代码,未跑测试。

**Round 108**(2026-05-21,Codex):
- 人类完成 Telegram render 复验:`/agents` 和 `/appoint codex as tester` 观感“好很多”,本轮关闭该问题状态。
- 继续推进高优能力:实现 `/overnight` 托管工单持久化与重启恢复。
- 新增 `OfflineDelegationStore` 协议和 `SQLiteOfflineDelegationStore`,复用 `AICO_STATE_DB_PATH` 对应 SQLite 文件保存 `offline_delegations` 表。
- 新增共享 SQLite state layer:`SQLiteStateDatabase` 统一维护 `aico_schema` metadata、schema version、表计数和已知状态表 reset。
- 新增 `aico-state --db <path>` CLI:默认输出 schema version 和状态表行数;`reset --yes` 可清空已知 AICO 状态表,适合开发期快速迭代。
- `AICO_STATE_DB_PATH=true` 现在映射到 `.aico/state.db`,`false` / `0` / `off` 视为关闭,避免再次生成仓库根目录 `true` 数据库文件;`.aico/` 已加入 `.gitignore`。
- `OfflineDelegationCommandHandler` 支持可选 store;未配置时仍保持内存行为,配置后 `/overnight` 写入 SQLite,重启并重新进入同一 project 后 `/overnight` 可列出历史托管工单。
- `Phase1Runtime` 在配置 `AICO_STATE_DB_PATH` 时同时启用 task state store 和 offline delegation store。
- README / README.zh-CN / Quickstart / daily ops / Phase 8 playbook / ADR-0028 同步更新,不再把 `/overnight` persistence 标为进行中。
- 新增回归测试覆盖 SQLite 恢复 overnight delegation,并确认恢复列表不会再次派发 Adapter 任务。
- 验证通过:`pytest` 293 passed / 1 skipped,`ruff check .`,`ruff format --check .`,`mypy src tests`,`git diff --check`,结构扫描无单类 >=500 行或单函数 >=100 行。

**Round 107**(2026-05-21,Codex):
- 按人类要求拆 `Orchestrator` / `TaskBus`:新增 `OrchestratorTaskFactory` 承载 project/session/memory task 构造,新增 `TaskStateRepository` 承载 task records、snapshots、approvals 和 adapter mapping。
- `Orchestrator` 类体从约 646 行降到 480 行;`TaskBus` 类体从约 566 行降到 448 行;模块级命令分发拆成 project / role / directory / memory helper 后不再超过 100 行。
- 继续修 Telegram 可读性:`rich_text_message()` 会把普通 `-` / `*` 列表转成 `•`,并对 `agent_title:`、`role:`、`adapter:` 等字段左侧 label 加粗;`/agents` 和 `/appoint` 的真实输出会更像结构化 IM 消息。
- 维持 render contract 边界:核心仍只输出平台无关 `MessageTextSpan`,Telegram Channel 只做 HTML 映射,没有把 Telegram Markdown 方言塞回核心。
- 更新测试覆盖 `/agents` 列表、字段 label 加粗、`/appoint` label 加粗和结构拆分后的回归。
- 验证通过:`pytest` 289 passed / 1 skipped,`ruff check .`,`ruff format --check .`,`mypy src tests`,`git diff --check`,结构扫描无单类 >=500 行或单函数 >=100 行。

**Round 106**(2026-05-21,Codex):
- 按人类确认,将 GitHub UI metadata(description、topics、social preview)视为已验收,不再作为公开发布缺口。
- 改善 Telegram 消息体感:新增平台无关 rich text renderer,流式 provider 输出和内置命令输出会把轻量 Markdown 标题、小节标题、inline bold/code/italic 和 slash command 转成 `MessageTextSpan`,Telegram 渲染为 HTML;标题前自动留出结构空行。
- 决策并落地 SQLite 持久化第一切片:新增 ADR-0028、`TaskStateStore` 协议和 `SQLiteTaskStateStore`;通过 `AICO_STATE_DB_PATH` 可持久化 task records、task snapshots 和 pending approvals,重启后继续支持 `/tasks`、`/task` 和 pending `/approve`。
- 从 1k stars 缺口和 GitHub 公开高优事项中选择两个最关键点落地:
  - 新增 `aico-release-room-demo` 无 token Release Room 本地 demo,陌生开发者不用 Telegram Bot Token 或 LLM provider 也能看到团队/记忆/审批/日报/审计链路。
  - 新增 `.github/PULL_REQUEST_TEMPLATE.md` 和 `.github/ISSUE_TEMPLATE/good_first_issue.yml`,降低公开后外部贡献者参与门槛。
- README / README.zh-CN / Quickstart / daily ops 同步新增 no-token demo 和 `AICO_STATE_DB_PATH` 配置说明。
- 新增 B-004,记录 `Orchestrator` / `TaskBus` 超过单类尺寸硬约束的公开前结构债。

**Round 105**(2026-05-21,Codex):
- 按人类“先别做重”的判断,把 ADR-0025 收敛为轻量 Goal Brief v0:先验证 `/goal` + 可验证 `/ask` 的目标/验收 prompt 价值,完整 `GoalCapability` / `GoalExecutor` / managed Ralph loop 暂缓。
- 新增 `/goal [role] <objective>` 命令;未指定 role 时使用当前 project lead/default role,`/goal` 可列出最近带 goal brief 元数据的任务。
- `/ask <role> <task>` 仅在文本出现明确验收、停止、通过/失败、证据等 marker 时保守附加 `AICO Goal Brief`;普通咨询不升级。
- Goal Brief 会注入 objective、acceptance、verification hints、stop conditions 和“没有证据不得 claim done”的规则;Task metadata 写入 `aico.intent=goal_brief`、`aico.goal_id`、`aico.goal_objective`、`aico.goal_acceptance`。
- `/task <id>` 详情新增 `Goal brief:` 区块,展示 goal id、objective 和 acceptance。
- 新增 `GoalBriefCommandHandler`,避免把 goal 逻辑继续塞进 Orchestrator;同步更新 ADR-0025、CHANGELOG 和 Phase 8 playbook。
- 验证通过:目标 command/orchestrator 单测、完整 `tests/unit/test_commands.py tests/unit/test_orchestrator.py`、定向 ruff / format / mypy。

**Round 104**(2026-05-21,Codex):
- 完成 lead decision workflow Stage 3:当前项目 lead/default role 收到明确决策类任务时,会进入只读决策流程。
- 决策流程优先召回 `public_broadcast`、`task_key_progress`、`decision_review` purpose 的记忆,不把 `task_private` 和普通 `general_context` 混入 decision packet。
- 自动咨询 challenger,并在 reviewer 已任命时同时咨询 reviewer;咨询任务复用 appointment prompt、provider session、普通 TaskBus 和协作审计 trace。
- Lead 最终任务会收到固定 decision memo 输出契约:Decision、Why、Evidence / memory refs、Consulted roles、Rejected alternatives、Risks / approval need、Next actions。
- 新增 `lead_decision_recorded` audit event,detail 记录 project、lead、boss task、memory refs、consulted roles 和 memo 摘要;memo 会写回 project memory,并标记 `decision_review`。
- 验证通过:98 个相关测试覆盖 Orchestrator、Memory、TaskBus、Audit 和 Phase 7 acceptance;定向 ruff / format / mypy 通过。

**Round 103**(2026-05-21,Codex):
- 继续执行 lead 决策能力 Stage 2,新增 ADR-0027 `Memory Purpose Tags`。
- `MemoryAtom` 新增 `purpose_tags`,旧记录默认 `general_context`,并新增 `MemoryPurpose`: `general_context`、`public_broadcast`、`task_key_progress`、`task_private`、`decision_review`。
- `MemoryRetriever` 默认排除 `task_private`,只有显式 `allowed_purposes` 时才会召回内部短期记忆。
- Team broadcast 生成的 team memory 会标记 `public_broadcast`,并丢弃源记忆中的 `task_private`。
- `/remember` 和 boss feedback 写入 `general_context`;`/recall` 输出展示 purpose。
- Prompt Stack 的 Shared memory 行展示 purpose,让 lead / agent 能区分公共共识、任务进展和决策评审。
- 验证通过:26 个 memory 目标测试覆盖 JSONL 兼容、purpose 过滤、broadcast purpose、`/recall` purpose、Phase 7 acceptance 和 Release Room acceptance。

**Round 102**(2026-05-21,Codex):
- 按人类确认开始落地 lead 决策团队契约第一阶段,新增 ADR-0026 `Lead Decision Team Contract`。
- 默认角色库新增 `challenger` / Critical Philosopher,职责是从反方视角挑战方案前提、机会成本和长期风险。
- 默认项目配置和 Release Room 配置补齐 challenger appointment;`/roles` 默认核心岗位会显示 challenger。
- 项目办公室和 `/team` 输出新增 `team readiness`,用于明确当前团队是否具备 lead + challenger。
- project lead 的 appointment prompt 增加责任约束:减少 boss 认知负担、基于记忆和团队意见做低风险决策、高风险事项升级 boss。
- `/overnight` 现在要求当前项目团队完整;缺 challenger 时提示 `/appoint <agent> as challenger`,不会派发托管任务。
- 验证通过:57 个目标测试覆盖 project assignment、prompt stack、project messages、phase1 runtime、orchestrator overnight、Release Room 示例和 acceptance。

**Round 100**(2026-05-21,Codex):
- 调研 Codex `/goal`:本机 Codex CLI 为 `0.125.0`,未包含该实验命令;OpenAI Developers 文档确认 `/goal` 需要 `features.goals`,用于带明确停止条件和验证循环的长任务。
- 新增 ADR-0025 `Goal Mode Orchestration`,定义 AICO `/goal` 的显式命令、`/ask` 自动升级规则、boss 分配流程、lead 子目标流程、目标状态和 prompt 模板。
- 设计结论:goal-mode 是 `/ask` 与 `/overnight` 之间的通用目标契约层,不绕过 `/approve`,并要求 goal 状态写入 audit、可在 `/goal`、`/tasks`、`/task`、`/daily` 中追踪。
- 本轮只做设计文档,未改运行代码;下一轮优先实现 GoalRecord 持久化、parser、render/audit 和单测。

**Round 101**(2026-05-21,Codex):
- 按人类反馈重构 ADR-0025:不同 agent 不能统一走 AICO loop,应先生成统一 `GoalContract`,再按 Adapter `GoalCapability` 选择执行器。
- 新增 `GoalCapability` 分层:`native_goal`、`adapter_goal_sugar`、`managed_ralph_loop`、`no_goal`。
- 对 Codex / Claude Code 等支持 goal 的 agent,由 Adapter 封装语法糖并传入明确目标、验收标准和停止条件;core 不硬编码具体 agent 语法。
- 对不支持 goal 的 agent,由 AICO 托管 managed Ralph loop:通过长期目标 prompt、hook 输出契约、continuation task、预算和审批边界避免模型过早结束或失控。
- 本轮仍只改设计文档;下一轮实现应先做 Adapter capability 模型和 GoalExecutor 分发,再做 managed loop。

**Round 96**(2026-05-20,Codex):
- 落地记忆检索 Stage 1+2:新增 `MemoryRetrievalQuery` / `MemoryRetrievalHit`,让检索 query、scope、top_k、token budget 和可解释 hit 成为稳定契约。
- `MemoryRetriever` 现在先生成 ranked hits,再投影为 `MemoryPacket`;排序综合 semantic、scope closeness、confidence、recency、evidence 和预留 graph score。
- `/recall` 改为复用 `MemoryRetriever`,并展示 reason,让记忆召回能被老板和下一轮 agent 排障。
- 新增测试覆盖 role scope 优先于 project scope、retrieval reason、token budget、candidate/restricted/cross-project 不进入 prompt 的既有治理。
- 更新 ADR-0023、Phase 7 playbook、CHANGELOG、ROUNDS 和 STATUS。
- 验证通过:266 passed / 1 skipped,`ruff check .`, `ruff format --check .`, `mypy src tests`, `git diff --check`。

**Round 97**(2026-05-20,Codex):
- 继续推进记忆检索到可验收态:新增保守 graph expansion,仅沿 `supports` / `derived_from` / `broadcast_to` 扩展一跳同 scope 邻居。
- `MemoryRetrievalQuery.role_id` / `agent_id` / `task_kind` 现在会作为 query hints 参与 semantic scoring,让 tester / reviewer / release-manager 更容易召回各自相关记忆。
- `/recall` 输出增加 final / semantic / scope / graph score 分项,便于 Telegram 真实验收和后续调权。
- 新增测试覆盖 graph 邻居召回不跨项目、role/task hints 排序、score/reason 展示路径。
- 验证通过:目标 memory/orchestrator/Phase7 tests、全量 `pytest`、`ruff check`、`ruff format --check`、`mypy` 和 `git diff --check`。

**Round 98**(2026-05-20,Codex):
- 排查人类真实 IM 反馈:`/appoint codeflicker as tester` 返回 `Cannot appoint`,根因是默认 project config 早先把 CodeFlicker agent id 落成 `flicker` alias,而用户输入的是 provider/persona 名 `codeflicker`。
- 修复 Project Assignment agent 解析:先按 configured agent id 匹配,再在唯一匹配时按 `CompanyAgentProfile.provider` 匹配;默认项目配置中 CodeFlicker / Cursor / Trae / Gemini 也使用 persona 名作为 agent id。
- 将 Claude/Codex/Cursor/CodeFlicker/Trae/Gemini CLI adapter 从单槽位改为可配置并发,默认 `max_concurrent_tasks=5`;达到上限才返回 busy。
- `/agents` / `/agent` 现在展示 `running/max` 与 `max_concurrent`,`/appoint` 成功回执展示 `agent_max_concurrent` 和建议任命上限。
- 将 Codex / optional CLI adapter 默认 output idle timeout 从 90 秒放宽到 300 秒,避免长思考或无中间 stdout 的正常任务过早失败。
- 验证通过:目标 adapter/project/orchestrator 测试 71 passed;全量 `pytest` 270 passed / 1 skipped;`ruff check`、`ruff format --check`、`mypy src tests`、`git diff --check` 全部通过。

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
  - `CodexAdapter` 最初默认 90 秒无 stdout 自动终止底层 CLI;Round 98 已将默认阈值放宽到 300 秒,并按并发槽位释放。
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

1. **【最高】GitHub UI 最终复核并改 public**:
   - README 文案、no-token demo、README GIF 和 social preview asset 已对齐当前 RC。
   - `docs/assets/release-room-demo.gif` 已是 36 秒、`960 x 540`,首屏明确 boss-absent,
     包含 `/morning` + `/view`。
   - `docs/assets/social-preview.png` 已生成,仓库 owner 需要在 GitHub UI 的 Social preview 上传 / 确认。
   - GitHub About description 可通过 `gh repo view` 看到;topics / visibility / social preview 仍需 public 前 live 复核。
   - public / tag / Release 按 [`docs/agent/09-github-release-ops.md`](docs/agent/09-github-release-ops.md)
     执行,不要在仓库仍 private 时抢先打 tag。
2. **【最高】按 Dogfooding 验收分层收口当前待测项**:
   - 先跑机器 Gate:见 [`docs/playbooks/phase-8-absence-loop.md`](docs/playbooks/phase-8-absence-loop.md)
     的 "AI 前置 Contract Gate"。Round 146 实测 **41 passed in 0.94s**。
   - Gate 覆盖父子 agent 委派、`/overnight` handoff、delegate 输出分段、`/aico-view` alias、老板动线、
     `/view` HTML snapshot 和 Telegram `sendDocument` 上传;后续修同类问题要先补/跑对应快速测试。
   - Agent 必须先跑本机真实样本:当前 Mac 有 Telegram App 时,先在 `ai_co` bot 中发短样本,
     用日志和截图确认真实 provider / Channel 行为。
   - Round 145 已验证真实 `implementer/claude-code -> reviewer/codex` 协作链路完成;后续只需在代码或 provider
     变更后重跑同类短样本,不把它默认交给 human。Telegram polling timeout 修复需要重启当前 AICO 进程后生效。
   - 代表性样本预期效果:reviewer 长审阅按移动端阅读上限拆成多条消息,`• High` / `• Medium`
     前有空行;排活后看 `/inbox`,早上接手看 `/morning`,深挖看 `/task <id>`,HTML 看 `/view` 或
     `/aico-view`;`/brief` 只用于项目背景。
   - 请求 human 时必须附上 Agent 已验证结果、推荐重点验证点、验证问题、预期效果、后续步骤。
   - 如果样本失败,必须留下 `/task <id>`、截图/原始输出、预期效果和实际偏差;不要只写“体验不好”。
3. **【最高】v0.1.0 公开打 tag + GitHub Release**(操作必须由老板亲自点确认):
   - `main` 已包含当前 RC;如果后续只改发布文档或资产,先提交并 push `main` 或通过 PR 合入。
   - `git tag v0.1.0 && git push --tags`。
   - 用 [`docs/launch/v0.1.0-release-notes.md`](docs/launch/v0.1.0-release-notes.md)
     创建 GitHub Release。
   - 检查 GitHub UI 的 description / topics / social preview(见
     [`docs/human/github-publication.md`](docs/human/github-publication.md))。
4. **【高】按 [`docs/launch/playbook.md`](docs/launch/playbook.md) 执行 D0 上线**:
   - HN Show HN 单次上线只有一次机会,失败不能复发同主题。
   - HN 帖子贴出后 1 分钟内贴作者首条评论,30 分钟内开始值守评论区。
   - 同窗口 Reddit r/LocalLLaMA / r/programming / r/ChatGPTCoding / r/Anthropic
     各发 1 帖,内容互不重复(模板见 playbook §3)。
5. **【高】Phase 8 dogfood 复盘 + `/view` 真实 IM human 体感 Sample**:
   - 直接可问的问题:
     - `/project aico`
     - `/view`
     - `/morning`
     - `/inbox`
     - `/why <short_id>`
   - 预期效果:老板不需要访问 Mac 本机端口,能在 Telegram 收到 `aico-view-aico.html`;HTML 能看懂 Boss Brief / Timeline / Trace / Memory,且敏感内容只出现在可信聊天里。
   - 验收口径:Agent 先验证真实 `sendDocument`、附件文件名、无 localhost 链接和可打开性;human 只判断手机第一屏是否方便接手、是否发到可信聊天、是否看得顺。
6. **【高】Orchestrator 类拆分(B-005)**:
   - 把 command handler 实例化 + 分发表迁到 `OrchestratorCommandRegistry` 或类似模块。
   - Orchestrator 主体回到 task 提交 / 流式输出 / 状态协调,恢复单类 <500 行硬约束。
7. **【中】aico-view Boss Brief 产品化**:
   - 根据 `/view` dogfood 调整 HTML 第一屏:审批、阻塞、昨夜产出、第一行动优先于原始 Timeline。
   - 暂不自动 `/project` 后发送;如真实体验需要,再加 `AICO_VIEW_AUTO_SEND_ON_PROJECT=true`。
8. **【中】Feishu 文件附件能力评估**:
   - 若 Feishu dogfood 需要 `/view`,新增 Feishu 文件上传 Channel capability。
   - 不要在 core 中写平台分支;复用 `DocumentChannel`。
9. **【低】Future F-1 / F-2**:
   - Lead 主动机制和 Team Karpathy Loop 只在 Phase 8 dogfood 确认三块基础体验跑顺后再启动。

---

## 当前卡点

参见 [`docs/journal/BLOCKERS.md`](docs/journal/BLOCKERS.md)。当前最高优工程债是 B-005
`Orchestrator class size regression`(🟡 DEFERRED)。B-006 已把"人工 dogfood 待测队列缺少机器验收分层"
关闭为 RESOLVED;当前长链路待测默认按机器 Gate → Agent 本机真实样本 → 1 条 human 体感 Sample 执行,
不再把本机可验证事项或完整人工回归当成阻塞。

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
