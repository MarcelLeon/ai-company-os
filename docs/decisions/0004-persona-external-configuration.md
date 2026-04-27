# ADR-0004: Persona 外部配置

**状态**:Accepted
**日期**:2026-04-28
**决策者**:Codex
**相关 Round**:Round 12

---

## 背景与问题

Round 11 已经实现 PersonaRegistry,但默认 persona 仍写在 `aico-phase1` 代码里。真实 Telegram 验收通过后,继续把 persona 固定在代码中会让新增职责角色必须改代码,不符合“能力可插拔”的北极星。

## 候选方案

### 方案 A — 继续硬编码默认 persona
- 优点:简单。
- 缺点:新增 persona 要改代码,不利于 dogfooding。
- 复杂度:低。

### 方案 B — JSON 文件配置 persona
- 优点:标准库即可解析,结构清晰,适合本地 dogfooding。
- 缺点:没有 YAML 注释能力,也还不是动态 reload。
- 复杂度:中低。

### 方案 C — 引入数据库或配置中心
- 优点:后续可做 UI 管理和动态更新。
- 缺点:当前 Phase 3 过重,会引入持久化与运维复杂度。
- 复杂度:高。

## 决策

选择 **方案 B — JSON 文件配置 persona**。

## 决策理由

- 不新增依赖,只使用 Python 标准库和现有 Pydantic 模型。
- `PersonaProfile` 已经是稳定的结构化模型,适合直接从 JSON 解析。
- 启动时 fail-fast 校验 persona 引用的 Adapter 是否已启用,避免运行中静默丢任务。
- 当前不做动态 reload,保持本地运行入口简单。

## 后果

### 正面后果
- 用户可以通过 `AICO_PERSONA_CONFIG_PATH` 指定 persona 配置文件。
- 新增职责角色不再需要改核心代码。
- 配置错误会在启动时暴露。

### 负面后果
- 修改 persona 需要重启进程。
- JSON 不适合写长篇注释。
- 暂无 per-chat / per-project persona 配置。

### 我们接受这些代价是因为
- Phase 3 的目标是验证 Persona 和 broadcast 的真实可用性,不是做配置平台。
- 后续如果需要动态管理,可在 Phase 7 共享记忆或 Phase 6 看板阶段再设计持久化。

## 不再做的事

- 不在当前阶段引入数据库、配置中心或动态 reload。
- 不让配置文件绕过 AdapterRegistry 校验。

## 相关链接

- ROUNDS Round 12
- `config/personas.example.json`
- `src/aico/app/phase1.py`
