# Playbook: Phase 2 多 Adapter 状态与路由验收

## 适用场景

当 `aico-phase1` 已能同时注册 Claude Code 和 Codex Adapter 时,用本 Playbook 验证 Phase 2 能力:状态可查询、任务可点名路由、任务生命周期可观测。

## 前置条件

- Phase 1 真实 Telegram Bot 端到端链路已通过。
- 本机可运行 `claude` 和 `codex` CLI。
- 环境变量已配置真实 Telegram Bot Token。

## 步骤

1. 启动双 Adapter 本地入口。

   ```bash
   export AICO_TELEGRAM_BOT_TOKEN="你的 Telegram Bot Token"
   export AICO_ENABLE_CODEX_ADAPTER=true
   export AICO_CLAUDE_WORKING_DIRECTORY="/Users/wangzq/VsCodeProjects/ai-company-os"
   env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python /opt/homebrew/bin/python3.11 aico-phase1
   ```

2. 在 Telegram Bot 会话中查询状态。

   ```text
   /status
   ```

   预期看到:

   ```text
   claude-code: idle
   codex: idle
   ```

3. 点名 Claude Code。

   ```text
   /claude summarize this repo in one sentence
   ```

4. 点名 Codex。

   ```text
   /codex summarize this repo in one sentence
   ```

5. 验证非 slash 形式也能唤醒 Codex。

   ```text
   @codex summarize this repo in one sentence
   codex: summarize this repo in one sentence
   ```

6. 再次查询状态。

   ```text
   /status
   ```

   预期除了 Adapter 状态外,还能看到最近任务状态,例如:

   ```text
   claude-code: idle
   codex: idle

   Recent tasks:
   task-... [codex]: done
   ```

## 验证

- `/status` 能返回至少 `claude-code` 和 `codex` 两个 Adapter。
- `/claude <task>` 路由到 Claude Code。
- `/codex <task>` 路由到 Codex。
- 任务正文中不应包含 `/codex`、`@codex`、`codex:` 等唤醒前缀。
- Codex 默认 read-only sandbox,不应默认写文件。
- `/status` 能展示最近任务的 `running` / `done` / `failed` / `interrupted` / `rejected` 状态。

## 失败回滚

- `/status` 只有 `claude-code`:确认 `AICO_ENABLE_CODEX_ADAPTER=true` 是否在同一个 shell 中导出。
- `/codex` 返回 unknown adapter:确认服务已重启,旧进程可能仍在运行。
- Codex 没有输出:先在终端运行 `codex --ask-for-approval never exec --sandbox read-only --color never "hello"`。
- Telegram 命令无响应:先用 `/help` 查看当前进程支持的命令。

## 相关

- `docs/playbooks/phase-1-mvp.md`
- `docs/architecture/adapter-protocol.md`
- `docs/journal/ROUNDS.md` Round 7 / Round 8 / Round 10
