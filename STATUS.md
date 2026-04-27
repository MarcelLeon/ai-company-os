# STATUS.md — 当前状态

> 这个文件高频更新。每一轮 AI 工作或人类工作结束都要更新这里。
> 阅读顺序:从上往下,前面的信息时效性最高。

**最后更新**:2026-04-27
**当前轮次**:Round 2(文档归位)
**当前阶段**:🟡 Phase 0 — 项目立项与文档体系搭建

---

## 项目宏大叙事(一句话)

把开发者 Mac 上散落的 AI 工具收编成一个可远程指挥的"虚拟公司",通过 IM 异步协作,让"AI 团队"成为开发者真正的生产力杠杆。

---

## 阶段地图

| 阶段 | 名称 | 状态 | 验收标准 |
|---|---|---|---|
| Phase 0 | 项目立项与文档体系 | 🟡 进行中 | 文档体系建立,北极星确立 |
| Phase 1 | 核心协议与单 Adapter MVP | ⚪ 未开始 | 1 个 AI(Claude Code)能从 1 个 IM(Telegram)接收任务并返回结果 |
| Phase 2 | 多 Adapter + 状态机 | ⚪ 未开始 | 至少 2 个 AI 接入,状态可在 IM 中查询 |
| Phase 3 | 人格化层 + 群聊编排 | ⚪ 未开始 | AI 有差异化人设,群聊能 broadcast 任务 |
| Phase 4 | 审批与审计 | ⚪ 未开始 | 危险操作可推送审批,所有行为有 trace |
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
- [ ] 技术栈选型决策(Java + Spring AI? Python + FastAPI? 还是混合?)
- [ ] 核心协议草案(Adapter 接口、IM 通道接口、任务消息格式)
- [ ] 第一个 ADR(架构决策记录)输出
- [ ] 仓库基础设施(.gitignore、CI 骨架、commit 规范)

---

## 上一轮做了什么

**Round 2**(2026-04-27,人 + Codex 协作):
- 将扁平化文档归位到 `docs/agent` / `docs/journal` / `docs/architecture` / `docs/human`
- 补回 `docs/decisions/README.md` 和 `docs/playbooks/README.md`
- 记录 P-002:文档文件被扁平化导致 AGENTS 路径失效
- 记录技术栈倾向:优先 Python,不选 Java 的核心原因是代码量和长期维护成本偏高

详见 [`docs/journal/ROUNDS.md`](docs/journal/ROUNDS.md)

---

## 下一轮建议做什么(优先级从高到低)

> Agent 接手时,如果没有明确任务,从这里挑最高优先级。

1. **【高】技术栈选型 ADR**:写 `docs/decisions/0001-tech-stack-selection.md`,建议确认 Python 3.11+ / FastAPI / asyncio / Pydantic v2 / pytest / ruff / mypy。明确否决 Java 的主要理由:代码量和维护成本偏高。
2. **【高】Python 项目骨架**:ADR-001 接受后,创建 `src/aico/`、`tests/`、`pyproject.toml`,先跑通 ruff / mypy / pytest。
3. **【高】Adapter 协议草案**:定义 `AIAdapter` Protocol 的最小可用版本(receive_task / status / stream_output / interrupt / capabilities)。
4. **【高】IM 通道协议草案**:定义 `IMChannel` Protocol,先以 Telegram Bot API 为参考实现验证。
5. **【中】Phase 1 MVP 范围明确**:只做"Telegram → 编排核心 → Claude Code → Telegram"这一条最小链路。
6. **【中】仓库基础设施**:CI / commit lint / pre-commit hooks。
7. **【低】UI 原型**:先不做,Phase 1 全部用 Telegram 完成验收。

---

## 当前卡点

参见 [`docs/journal/BLOCKERS.md`](docs/journal/BLOCKERS.md)。本轮无新增卡点。

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
