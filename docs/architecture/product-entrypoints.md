# Product Entrypoints

> 本文记录 AI Company OS 的 MVP 产品入口判断。核心问题:它应该只是 Telegram bot,还是也要有类似 macOS Dynamic Island 的本地掌控感?

---

## 北极星约束

AICO 的主价值不是“本地桌面好看”,而是:

- 人不在电脑前时,仍能远程异步管理 AI 团队。
- 多个 AI 工具被统一编排,状态可观测。
- 危险行为可审批、可审计、可中断。

因此,MVP 不能只有本地 Mac UI;否则会退回“坐在电脑前看工具”的产品。

---

## 推荐 MVP 入口组合

### 1. Telegram / IM — 主入口

定位:远程老板办公室。

负责:
- 下任务:`/ask`、普通项目消息、`/claude`、`/codex`。
- 审批:`/approve`、`/reject`。
- 中断:`/interrupt`。
- 状态面:`/status`、`/metrics`、`/tasks`、`/brief`、`/next`。
- 项目组织:`/project`、`/team`、`/roles`、`/lead`。

这是 MVP 必须优先打磨的入口,因为它直接对应“无论身处何地”。

### 2. macOS Status Island — 本地 glance 入口

定位:坐在电脑前时的“公司楼层大屏”,不是主控制台。

第一版只应该做:
- 显示 active agent 数。
- 显示 running / waiting approval / failed 数。
- 展示最近 3-5 个 task 的项目、persona、状态和耗时。
- 对 waiting approval 提供 approve / reject。
- 对 running task 提供 interrupt。
- 点击跳转到 Telegram command 或对应 terminal/session。

它消费 Phase 6 的 metrics / task 状态,不直接读取 Adapter 内部状态。

不在第一版做:
- 完整任务编排。
- 复杂聊天。
- role 管理。
- 项目配置编辑。

### 3. CLI / Local Debug — 维护入口

定位:开发者排障和本地启动。

负责:
- 启动/停止。
- 查看日志。
- 本地 smoke test。
- 后续可以补 `aicoctl status` / `aicoctl metrics`,但不是当前 MVP 主路径。

### 4. Web / Mobile — 后续入口

定位:当 IM 文本命令不够表达复杂状态时再做。

触发条件:
- `/metrics` 指标稳定。
- 需要趋势图或跨天历史。
- 需要多人/多项目浏览。
- 有持久化观测存储。

---

## 当前产品判断

MVP 不是“只有 IM”,而是:

```text
IM 主控 + macOS glance + 本地 CLI 排障
```

但实现顺序必须是:

```text
IM 指标口径 -> 稳定观测模型 -> macOS glance -> Web/mobile
```

这样既保住远程异步的北极星,也不丢掉本地掌控感。
