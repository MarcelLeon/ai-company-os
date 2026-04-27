# CHANGELOG.md

> 遵循 [Keep a Changelog](https://keepachangelog.com/) 规范。
> 版本号采用 [Semantic Versioning](https://semver.org/)。

---

## [Unreleased]

### Added
- 项目立项,北极星三句话确立
- 完整文档体系骨架(README / AGENTS / NORTH_STAR / STATUS / journal 等)
- Agent 接手协议(AGENTS.md 强制阅读路径)
- 踩坑录、轮次记录、卡点跟踪三大演化文档
- `docs/decisions/README.md` 与 `docs/playbooks/README.md` 索引文档
- ADR-0001 技术栈选型,确认 Python 3.11+ / FastAPI / asyncio / Pydantic v2
- Python 项目骨架、`AIAdapter` / `IMChannel` 协议草案和值对象单测
- ADR-0002 Adapter / Channel 协议定稿
- 最小 Router / TaskBus / Orchestrator 假链路和端到端单测
- GitHub Actions CI 骨架,执行 pytest / ruff / mypy
- Phase 1 MVP 单链路验收 Playbook
- Telegram Channel 文本 MVP,支持 long polling、文本发送、消息编辑和删除
- Claude Code Adapter MVP,支持 CLI 文本任务、流式输出和中断
- `aico-phase1` 本地启动入口,串接 Telegram Channel、编排核心和 Claude Code Adapter
- Phase 1 真实 Telegram Bot 端到端验收通过
- AdapterRegistry 多 Adapter 注册与按 persona 路由
- `/status` 文本命令,可在 IM 中查询 Adapter 状态
- Codex Adapter 文本 MVP,默认 read-only sandbox
- `/help`、`/claude <task>`、`/codex <task>`、`@codex <task>`、`codex: <task>` 文本命令
- Phase 2 多 Adapter 状态与路由验收 Playbook
- 任务生命周期状态机,支持 `running` / `done` / `failed` / `interrupted` / `rejected`
- ADR-0003 Phase 3 Persona 与 Broadcast 边界
- PersonaRegistry 最小实现,支持 `implementer` / `reviewer` 职责映射
- `/broadcast <task>` 文本命令,可把任务派发给当前启用的 persona
- Phase 3 Persona 与 Broadcast 验收 Playbook
- ADR-0004 Persona 外部配置
- `AICO_PERSONA_CONFIG_PATH` 配置入口和 `config/personas.example.json` 示例文件
- ADR-0005 Phase 4 审批与审计边界
- 危险任务风险识别模型,覆盖 `read_only` / `write_files` / `shell_exec` / `destructive`
- `/approve <task_id>` 与 `/reject <task_id>` 审批命令
- 内存审计事件模型,记录任务提交、审批结果、Adapter 派发和任务完成/失败/中断

### Changed
- 将扁平化文档归位到 `docs/agent` / `docs/journal` / `docs/architecture` / `docs/human`
- `/status` 现在会展示 Adapter 状态和最近任务状态
- 危险任务现在会先进入 `waiting_approval`,批准后才派发给 Adapter

### Deprecated
- (无)

### Removed
- (无)

### Fixed
- (无)

### Security
- (无)
