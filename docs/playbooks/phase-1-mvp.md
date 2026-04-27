# Playbook: Phase 1 MVP 验收

## 适用场景

当 Phase 1 的 Telegram Channel、编排核心、Claude Code Adapter 都已接入后,用本 Playbook 验证真实单链路是否可用。

本 Playbook 只验收文本链路:

`Telegram 文本消息 -> 编排核心 -> Claude Code -> Telegram 文本 / 编辑消息`

## 前置条件

- 已完成 ADR-0001 和 ADR-0002。
- `TelegramChannel` 已实现文本 long polling、`sendMessage`、`editMessageText`。
- `ClaudeCodeAdapter` 已实现文本任务接收、流式输出和中断。
- 本机可运行 Claude Code CLI。
- 环境变量已配置真实 Telegram Bot Token。
- 运行环境能访问 Telegram Bot API。

## 范围内

- 私聊或测试群中的文本消息。
- 单个默认 Adapter:Claude Code。
- 单个 IM Channel:Telegram。
- 流式输出通过编辑同一条 Telegram 消息展示。
- 失败时返回一条可读的拒绝或错误消息。

## 范围外

- Webhook、反向代理和公网域名。
- 图片、文件、语音等多模态消息。
- 多 Adapter 路由、多 Channel 转发和 AI 间协作。
- 审批流、审计看板、持久化记忆。
- 生产部署和守护进程。

## 步骤

1. 安装依赖并运行本地检查。

   ```bash
   env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python /opt/homebrew/bin/python3.11 pytest
   env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python /opt/homebrew/bin/python3.11 ruff check .
   env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python /opt/homebrew/bin/python3.11 ruff format --check .
   env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python /opt/homebrew/bin/python3.11 mypy src tests
   ```

2. 确认 Telegram Bot Token 已设置。

   ```bash
   test -n "$AICO_TELEGRAM_BOT_TOKEN"
   ```

3. 确认 Claude Code CLI 可用。

   ```bash
   claude --version
   ```

4. 启动 Phase 1 本地入口。

   ```bash
   env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python /opt/homebrew/bin/python3.11 aico-phase1
   ```

   可选环境变量:

   ```bash
   export AICO_DEFAULT_PERSONA=claude-code
   export AICO_CLAUDE_COMMAND="claude -p --output-format text"
   export AICO_CLAUDE_WORKING_DIRECTORY="/Users/wangzq/VsCodeProjects/ai-company-os"
   ```

5. 在 Telegram 测试会话中发送一条文本任务。

   ```text
   hello, summarize this repository in one paragraph
   ```

6. 观察 Telegram 回复。

   - 应先出现一条已接收消息。
   - 随着 Claude Code 输出,同一条消息应被持续编辑。
   - 任务结束后,最终消息应包含完整结果。

7. 发送一条明显较短的第二个任务,确认通道仍可继续接收。

## 验证

验收通过必须同时满足:

- 本地 `pytest` / `ruff check` / `ruff format --check` / `mypy` 全绿。
- Telegram 文本消息能被转换成 `IncomingMessage` 并进入 `Orchestrator`。
- `Orchestrator` 只依赖 `IMChannel` 和 `AIAdapter` 协议,不直接依赖 Telegram 或 Claude Code 具体类。
- Claude Code Adapter 返回 `TaskAck.ACCEPTED` 后开始输出流。
- Telegram 至少发生一次 `sendMessage` 和一次 `editMessageText`。
- 出错时不会泄露 Bot Token、本机路径中的敏感片段或完整 traceback。
- 2026-04-28 人类已完成一次真实 Telegram Bot 端到端 smoke test。

## 失败回滚

- Telegram 无法收消息:先跑 `getMe` health check,再确认 Bot Token 和网络。
- Telegram 能收不能回:检查 `sendMessage` 返回体和 chat id 映射。
- 能回不能编辑:检查 `editMessageText` 的 message id 是否来自同一 chat。
- Claude Code 无输出:先用 fake subprocess 单测定位 Adapter,不要改核心协议。
- 编排链路断开:先用 FakeChannel + FakeAdapter 单测回归,再看真实插件。

## 相关

- `NORTH_STAR.md`
- `docs/decisions/0001-tech-stack-selection.md`
- `docs/decisions/0002-adapter-channel-protocol.md`
- `docs/architecture/adapter-protocol.md`
- `docs/journal/PITFALLS.md`
