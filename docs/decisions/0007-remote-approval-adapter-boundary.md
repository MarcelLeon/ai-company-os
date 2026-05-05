# ADR-0007: 远程审批与 Adapter 能力边界

**状态**:Accepted
**日期**:2026-04-28
**决策者**:Codex
**相关 Round**:Round 17

---

## 背景与问题

真实 Telegram smoke test 暴露了两个 Phase 4 边界问题:

1. Codex 默认运行在 read-only sandbox。即使 AICO `/approve` 通过,底层 Codex 仍无法写文件,会报“read-only 沙箱且不允许申请写权限”。
2. Claude Code 在非交互 `-p` 模式下仍可能触发自己的本机权限提示。Telegram 里已经 `/approve` 后,用户又被要求到电脑上授权,破坏远程异步体验。

这说明“人类批准危险任务”只是 AICO 的审批语义,还必须同时满足 Adapter 的能力边界和非交互运行要求。

## 候选方案

### 方案 A — 继续把任务派给 Adapter,让底层 CLI 自己失败
- 优点:核心代码最少。
- 缺点:用户已经批准后才失败,错误信息来自底层 CLI,体验差且不可预测。
- 复杂度:低。

### 方案 B — AICO 审批前校验 Adapter 能力,并让写能力 Adapter 非交互执行
- 优点:read-only Adapter 在核心层直接拒绝危险任务;Claude 远程入口不再要求本机二次授权。
- 缺点:风险识别仍依赖文本启发式,如果误判为 read-only,底层 bypass 权限会放大影响。
- 复杂度:低。

### 方案 C — 把 Claude/Codex 的原生权限提示转发到 Telegram
- 优点:保留底层 CLI 的原生审批语义。
- 缺点:需要 TTY / stdin 交互桥接,每个 CLI 的提示格式都不同,会把 Adapter 易变细节带入核心审批流。
- 复杂度:高。

## 决策

选择 **方案 B — AICO 审批前校验 Adapter 能力,并让写能力 Adapter 非交互执行**。

## 决策理由

- AICO 的 `/approve` 必须成为远程场景唯一的人类审批入口,否则“无论身处何地”不成立。
- Codex 当前定位是 reviewer/read-only,危险任务应在核心层拒绝并提示使用 `/claude`。
- Claude Code 是 implementer,经过 AICO 审批后应使用 `--permission-mode bypassPermissions` 避免本机二次授权。
- 不实现 TTY 转发,避免把不同 CLI 的交互协议扩散到核心。

## 后果

### 正面后果
- `/codex` 写文件 / shell / destructive 任务不再进入无效审批流程。
- `/claude` 危险任务在 Telegram `/approve` 后不再需要到电脑上处理 Claude 本机授权提示。
- `/audit` 能记录被能力门禁拒绝的任务。

### 负面后果
- Claude 远程入口更依赖 AICO 风险识别准确性。
- 如果人类绕过 AICO 直接运行 `aico-phase1` 配错命令,仍可能出现底层 CLI 权限行为差异。

### 我们接受这些代价是因为
- Phase 4 的目标是可远程审批、可审计,不是保留各 CLI 的本机交互体验。
- 后续应优先把风险识别从文本启发式升级为更明确的规则表。

## 不再做的事

- 不再让 read-only Adapter 在核心审批后才由底层 CLI 报写权限错误。
- 不在 Phase 4 实现 Claude/Codex 原生权限提示的 Telegram TTY 转发。

## 相关链接

- ROUNDS Round 17
- PITFALLS P-007
- 相关代码:`src/aico/core/risk_capability.py`, `src/aico/adapter/claude_code.py`
