# ADR-0014: Phase 6 Observability Scope

**状态**:Accepted
**日期**:2026-05-07
**决策者**:Wang / Codex(协作)
**相关 Round**:Round 61

---

## 背景与问题

Phase 5 已经让多个 Agent 可以通过 IM 被任命、派工、协作、审批和中断。下一步自然进入“可观测看板”:老板需要知道这家公司现在有多少活在跑、谁在干、哪里失败、协作是否真的发生。

同时,项目最初还有一个私人产品动机:对齐 CodeIsland 那类 Mac 上能看到多个 agent 线程正在干活的掌控感。但北极星第一句仍然要求远程异步优先,不能把本地 GUI 作为唯一入口。

## 候选方案

### 方案 A — 直接做 Mac 浮窗 / 菜单栏 UI
- 优点:最接近 CodeIsland 的“掌控感”。
- 缺点:会把验收绑定到 Mac 桌面,偏离远程异步;还需要先解决状态数据源。
- 复杂度:高。

### 方案 B — 先做 IM-first `/metrics` MVP
- 优点:继续服务 Telegram dogfooding;复用现有 `TaskSnapshot` / `AuditEvent`;最快验证哪些指标真的有用。
- 缺点:视觉掌控感弱,更像运营报表。
- 复杂度:低。

### 方案 C — 先做 HTTP API + Web dashboard
- 优点:以后可被 Mac UI、网页和 IM 共用。
- 缺点:需要新增服务面、鉴权和前端;在指标口径还未验证前容易做重。
- 复杂度:中高。

## 决策

选择 **方案 B:先做 IM-first `/metrics` MVP**。

Phase 6 第一切片只从当前进程内状态汇总:
- 24h / 7d task 数。
- 各状态计数。
- 各 adapter / agent 接活数。
- open work。
- collaboration request 数。
- 平均终态耗时。
- token/cost 先明确显示 unavailable。

## 决策理由

- 符合北极星第一句:人在外面仍能通过 IM 管理“虚拟公司”。
- 符合北极星第三句:先让行为可观测,再谈更漂亮的本地 UI。
- 指标口径还在形成,先用 Telegram 文本快速 dogfood,避免提前投入 Web / macOS UI。
- 未来 Mac 浮窗或菜单栏不应该直接读取 Adapter 内部状态,而应该消费 Phase 6 形成的稳定观测模型。

## 后果

### 正面后果

- Phase 6 可以立刻开始,不引入新依赖。
- `/metrics` 能和 `/status`、`/tasks`、`/audit` 形成 IM 侧运营闭环。
- 后续产品入口可以复用同一套指标,减少重复实现。

### 负面后果

- 第一版没有 CodeIsland 那种强视觉存在感。
- 当前数据只在进程内,重启后丢失;长期趋势需要后续持久化。
- token/cost 依赖底层 CLI 暴露能力,当前只能标记 unavailable。

### 我们接受这些代价是因为

真正的 MVP 先验证“老板需要看哪些状态”,而不是先验证“窗口长什么样”。当 `/metrics` 的指标稳定后,再把同一套状态投到 Mac 菜单栏、桌面浮窗或 Web 页面。

## 不再做的事

- Phase 6 第一切片不做 Mac GUI。
- Phase 6 第一切片不新增数据库或 HTTP API。
- 不伪造 token/cost 数据;拿不到就明确显示 unavailable。

## 相关链接

- ROUNDS Round 61
- `src/aico/core/metrics.py`
- `src/aico/core/command_messages.py`
