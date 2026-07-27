# AICO 自修复真实案例：公开入口文档漂移

> 采集时间：2026-07-27（Asia/Shanghai）
>
> 事实范围：真实 Telegram、真实 AICO Runtime、Claude Code Implementer、Codex Reviewer
>
> 隐私处理：不保存 Bot Token、Chat ID、Sender ID、历史聊天或 Provider 凭据。

## 要修的问题

`README.zh-CN.md` 的快速上手仍把旧 entry point `aico-phase1` 和一整组手工
`export AICO_*` 当作普通用户入口；当前公开入口已经是 `aico init|doctor|run|service`。

这是一个真实、低风险、结果可核对的小问题：只改公开文档，不改代码、配置、Release
或外部系统。

## 真实执行链

| 阶段 | 事实 |
|---|---|
| 首次派发 | `ca692ce1`，Implementer / Claude Code，风险 `shell_exec` |
| 人工决定 | Owner 在 Telegram 发送一次 `/approve ca692ce1` |
| 首次结果 | `failed`：LaunchAgent 环境中的 Claude Code 返回 `Not logged in` |
| 诊断 | 同一 Claude CLI 在正常用户环境只读探针成功；确认是运行环境差异，不冒充任务成功 |
| 再次派发 | `62a84f46`，同一任务、同一范围，风险 `shell_exec` |
| 人工决定 | Owner 在 Telegram 发送一次 `/approve 62a84f46` |
| 实现结果 | `README.zh-CN.md` 更新为 `aico demo` 与 `aico init|doctor|run|service install` |
| 独立复核 | Implementer 请求 `2a3553ee`，Codex Reviewer 以 `read_only` 风险检查文档链 |
| 终态 | 主任务与 Reviewer 子任务均为 `done`；`/morning` 和 `/audit` 可回溯 |

主任务从 `2026-07-27T14:04:28Z` 到 `14:11:15Z`，包含真实模型等待时间。宣传视频允许
剪掉等待，但必须保留首次失败、人工审批、独立复核和真实终态。

## AICO 证明了什么

- 写文件或运行检查不会因 Prompt 中的“主动推进”而自动越过审批。
- Owner 批准的是一条具体任务，不是给 Agent 无限权限。
- 已知范围内 Implementer 可以继续工作，并把独立检查委托给只读 Reviewer。
- 失败、协作、审批、派发和完成都有单任务状态和审计事件。
- `/morning` 能把当天的 `done`、`blocked`、`risks` 和下一步重新交还给 Owner。

## 它没有证明什么

- 没有证明所有 Mac 的 Provider 登录与 LaunchAgent 环境都已自动配置好。
- 没有证明 no-token demo 在当前 owner 的零字节 Release Room 配置下通过。
- 没有执行 commit、push、tag、Release 或任何不可逆发布动作。
- 这不是企业多租户审批平台案例；它验证的是个人开发者管理自己电脑上的 Agent。

## 可复核入口

```text
/task ca692ce1
/task 62a84f46
/task 2a3553ee
/audit 10
/morning
```

本案例的公开素材使用脱敏重绘，不直接展示 Telegram 历史聊天；短任务 ID、风险、角色、
状态和文档 diff 均来自上述真实记录。
