# ADR-0003: Phase 3 Persona 与 Broadcast 边界

**状态**:Accepted
**日期**:2026-04-28
**决策者**:Codex
**相关 Round**:Round 11

---

## 背景与问题

Phase 3 的验收标准是 AI 有差异化人设,群聊能 broadcast 任务。这里的“人设”必须服务于管理真实团队,而不是做娱乐化换皮。因此需要先确定 Persona 和 broadcast 的最小边界。

## 候选方案

### 方案 A — 只做 prompt 文案人设
- 优点:实现最快。
- 缺点:没有稳定路由和职责边界,无法支撑群聊编排。
- 复杂度:低。

### 方案 B — Persona 映射到 Adapter + 职责前缀
- 优点:能把 `implementer` / `reviewer` 这类管理角色映射到具体 AI Adapter,同时保持 Adapter 协议不变。
- 缺点:当前仍是静态配置,还没有复杂策略能力。
- 复杂度:中低。

### 方案 C — 引入完整 PersonaStrategy / 工作流引擎
- 优点:扩展能力强。
- 缺点:Phase 3 早期样本不足,会过早抽象。
- 复杂度:高。

## 决策

选择 **方案 B — Persona 映射到 Adapter + 职责前缀**。

## 决策理由

- 符合北极星的“像管理真实团队一样”:用户面对的是职责角色,不是裸 CLI 名称。
- 保持可插拔:Adapter 仍只实现 `AIAdapter`,Persona 层只负责路由和任务上下文补充。
- 避免过早抽象:暂不引入策略框架、工作流引擎或长期记忆。
- broadcast 可以拆成多个普通 `Task`,复用现有状态机和 `/status`。

## 后果

### 正面后果
- `/broadcast <task>` 可以发送给当前启用的 persona。
- `/claude`、`/codex` 等旧入口可作为 persona alias 继续工作。
- `/status` 能继续展示每个拆分任务的生命周期。

### 负面后果
- Persona 配置仍是代码内默认值,不是外部配置文件。
- 同一个 Adapter 承载多个 persona 时仍受 Adapter 单任务限制影响。
- broadcast 当前只是并发派发,不是完整 AI 间协作协议。

### 我们接受这些代价是因为
- Phase 3 的目标是先完成可 dogfooding 的群聊编排入口。
- Phase 5 才需要解决 AI 间协作协议 B-002。

## 不再做的事

- 不把人格化做成纯娱乐文案。
- 不在本阶段引入完整工作流引擎。
- 不把 broadcast 实现成绕过 `TaskBus` 的特殊任务通道。

## 相关链接

- ROUNDS Round 11
- `src/aico/core/persona_registry.py`
- `src/aico/core/orchestrator.py`
