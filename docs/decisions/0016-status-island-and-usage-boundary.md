# ADR-0016: Status Island and Usage Boundary

**状态**:Accepted
**日期**:2026-05-07
**决策者**:Codex
**相关 Round**:Round 64

---

## 背景与问题

Phase 6 还剩两个代码侧核心缺口:本地 glance 原型和 token/cost 数据接入边界。人类希望加快节奏,把 Phase 6 核心能力一次开发完后集中验收。

问题是:是否现在就做完整 macOS 菜单栏 / Dynamic Island UI,以及是否在 Adapter 未稳定提供 usage 时直接计算 token/cost。

## 候选方案

### 方案 A — 直接做 macOS GUI 和完整 usage 统计
- 优点:产品感最强。
- 缺点:会引入 GUI 技术栈、权限和发布复杂度;usage 来源不稳定时容易伪造指标。
- 复杂度:高。

### 方案 B — 做 `aico-glance` 数据原型和 usage 审计事件边界
- 优点:复用 `MetricsReport`;无新依赖;可被 xbar/Swift/菜单栏原型消费 JSON;usage 有清晰审计事件接入口但不伪造数据。
- 缺点:还不是最终视觉形态;真实 approve / interrupt 仍通过 IM 命令完成。
- 复杂度:低。

### 方案 C — 直接做 HTTP API / Web dashboard
- 优点:多入口复用更自然。
- 缺点:新增服务面、鉴权和前端,Phase 6 验收前过重。
- 复杂度:中高。

## 决策

选择 **方案 B:做 `aico-glance` 数据原型和 usage 审计事件边界**。

具体包括:
- `StatusIslandSnapshot` 作为本地 glance 数据模型。
- `aico-glance --format text|json` 从 audit JSONL 输出紧凑状态和可执行 IM 命令提示。
- 新增 `task_usage_recorded` 审计事件类型和 `usage_audit_detail()` JSON detail 约定。
- `MetricsReport.token_cost` 只在 audit events 中有真实 usage 时显示数值;否则继续 unavailable。

## 决策理由

- 符合北极星第一句:IM 仍是主控台,本地 UI 只是坐在电脑前的 glance。
- 符合北极星第二句:后续 macOS / Web 消费同一份状态模型,不直接读 Adapter 内部状态。
- 符合北极星第三句:token/cost 来自可审计事件,没有真实上报就不伪造。
- 当前阶段需要集中验收 Phase 6 核心能力,不适合引入 GUI / HTTP 新表面。

## 后果

### 正面后果
- Phase 6 代码侧核心能力闭环:IM metrics、audit replay、CLI metrics、local glance、usage 接入边界。
- 后续真正 macOS Status Island 可以先消费 `aico-glance --format json`。
- Adapter 未来只需记录 `task_usage_recorded` 审计事件即可进入 token/cost 汇总。

### 负面后果
- `aico-glance` 不是最终 macOS 原生 UI。
- 它从 audit JSONL 读取历史状态,不能直接对 running 进程执行 approve / interrupt;只输出 IM 命令提示。
- token/cost 仍依赖 Adapter 真实上报 usage。

### 我们接受这些代价是因为

Phase 6 当前的目标是让可观测模型可验收、可复用,不是完成最终桌面产品外观。

## 不再做的事

- Phase 6 不新增完整 Web dashboard。
- Phase 6 不引入 macOS GUI 依赖。
- 不手工估算或伪造 token/cost。

## 相关链接

- ADR-0014
- ADR-0015
- ROUNDS Round 64
- `src/aico/core/status_island.py`
- `src/aico/app/glance_cli.py`
