# STATUS.md — 当前状态

> 这个文件高频更新。每一轮 AI 工作或人类工作结束都要更新这里。
> 阅读顺序:从上往下,前面的信息时效性最高。

**最后更新**:2026-04-28
**当前轮次**:Round 13(Phase 4 审批与审计最小闭环)
**当前阶段**:🟡 Phase 4 进行中 — 审批与审计

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
| Phase 4 | 审批与审计 | 🟡 进行中 | 危险操作可推送审批,所有行为有 trace |
| Phase 5 | AI 间协作 | ⚪ 未开始 | AI 之间可以互相 @ 协作,任务编排成型 |
| Phase 6 | 可观测看板 | ⚪ 未开始 | 工时/KPI/token 消耗可视化 |
| Phase 7 | 共享记忆层 | ⚪ 未开始 | 所有 AI 共享上下文记忆 |
| Phase 8 | 离线托管模式 | ⚪ 未开始 | 睡前下任务,早上看结果 |

图例:🟢 完成 / 🟡 进行中 / ⚪ 未开始 / 🔴 阻塞

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
- [ ] Telegram 真实审批 smoke test
- [ ] 审计事件持久化或结构化日志输出

---

## 上一轮做了什么

**Round 13**(2026-04-28,Codex):
- 人类已验证 Telegram 中 `/broadcast`、`/status` 等命令没有问题,Phase 3 真实 smoke test 稳定。
- 新增 ADR-0005 和 Phase 4 smoke test Playbook,明确审批与审计先做 TaskBus 前置门禁、Telegram 手动审批、内存审计。
- 新增文本风险识别模型,覆盖 `read_only` / `write_files` / `shell_exec` / `destructive`。
- `TaskBus` 会把危险任务拦截为 `waiting_approval`,记录审计事件,通过 `/approve <task_id>` 批准后才派发给 Adapter。
- 新增 `/reject <task_id> [reason]`,可拒绝待审批任务。
- 单测从 55 个增加到 66 个,本地 `pytest` / `ruff check` / `ruff format --check` / `mypy` 全绿。

详见 [`docs/journal/ROUNDS.md`](docs/journal/ROUNDS.md)

---

## 下一轮建议做什么(优先级从高到低)

> Agent 接手时,如果没有明确任务,从这里挑最高优先级。

1. **【高】Phase 4 真实审批 smoke test**:按 `docs/playbooks/phase-4-approval-audit.md` 验证只读任务直通、危险任务 `waiting_approval`、`/approve` 和 `/reject`。
2. **【高】审计事件可观测输出**:把当前内存审计事件输出到结构化日志或 `/audit` 只读命令,方便人类确认 trace。
3. **【高】审批权限策略**:定义谁可以审批任务,避免任意 Telegram 用户知道 task id 就能 `/approve`。
4. **【中】风险识别迭代**:把纯文本启发式升级为可测试的规则表,减少误报/漏报。
5. **【中】Persona 配置真实 smoke test**:用 `AICO_PERSONA_CONFIG_PATH=config/personas.example.json` 重启后再跑 `/broadcast`。
6. **【中】真实链路集成测试设计**:在没有真实 Token / CLI 时先写可跳过的 integration harness,有环境变量再跑。
7. **【中】命令解析收口**:命令已增长到 help/status/broadcast/approve/reject,下一次新增命令前考虑小型 command parser。
8. **【低】UI 原型**:先不做,Phase 4 仍以 Telegram dogfooding 为准。

---

## 当前卡点

参见 [`docs/journal/BLOCKERS.md`](docs/journal/BLOCKERS.md)。B-001 已解决,当前仅 B-002(AI 间协作协议)为 Phase 5 前的延后卡点,不阻塞 Phase 3。

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
