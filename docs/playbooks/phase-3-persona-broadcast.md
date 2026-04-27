# Playbook: Phase 3 Persona 与 Broadcast 验收

## 适用场景

当 `aico-phase1` 已启用 PersonaRegistry 和 `/broadcast` 命令时,用本 Playbook 验证 Phase 3 的第一段能力:通过职责名管理 AI,并把同一任务广播给多个 persona。

## 前置条件

- Phase 2 多 Adapter 验收已通过。
- 本机可运行 `claude` 和 `codex` CLI。
- 环境变量已配置真实 Telegram Bot Token。
- 建议启用 Codex Adapter,否则 broadcast 只会发送给 `implementer`。

## 步骤

1. 启动双 Adapter 本地入口。

   ```bash
   export AICO_TELEGRAM_BOT_TOKEN="你的 Telegram Bot Token"
   export AICO_ENABLE_CODEX_ADAPTER=true
   export AICO_CLAUDE_WORKING_DIRECTORY="/Users/wangzq/VsCodeProjects/ai-company-os"
   export AICO_PERSONA_CONFIG_PATH="config/personas.example.json"
   env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python /opt/homebrew/bin/python3.11 aico-phase1
   ```

2. 查询帮助。

   ```text
   /help
   ```

   预期能看到 `/broadcast <task>`。

3. 按旧入口点名单个 AI。

   ```text
   /claude summarize this repo in one sentence
   /codex summarize this repo in one sentence
   ```

   预期仍能分别路由到 Claude Code 和 Codex。

4. 广播一个只读分析任务。

   ```text
   /broadcast summarize this repo in one sentence
   ```

   预期看到:
   - 一条 `Broadcast accepted: 2 targets`
   - `implementer` 和 `reviewer` 各自收到一个任务
   - 两个任务分别返回结果或错误

5. 查询状态。

   ```text
   /status
   ```

   预期看到最近任务中包含 `implementer` 和 `reviewer` 的任务状态。

## 验证

- `implementer` 默认映射到 `claude-code`。
- `reviewer` 默认映射到 `codex`。
- `/claude` 和 `/codex` 作为 alias 保持兼容。
- `/broadcast <task>` 不绕过 `TaskBus`,最近任务仍能在 `/status` 中看到。
- Persona 职责文本只用于指导任务,不改变 Adapter 接口。
- 指定 `AICO_PERSONA_CONFIG_PATH` 后,persona 来自 JSON 文件;不指定时使用内置默认值。

## 失败回滚

- `/broadcast` 无响应:先用 `/help` 确认当前进程是否为最新代码。
- 只看到 1 个 target:确认 `AICO_ENABLE_CODEX_ADAPTER=true` 是否生效。
- 启动时报 unknown adapter:确认 persona 配置里的 `adapter_name` 已经被当前进程启用。
- Codex 报参数错误:确认命令形态为 `codex --ask-for-approval never exec ...`。
- 某个任务 busy:当前 Adapter 仍是单任务占用,等待当前任务结束后重试。

## 相关

- `docs/decisions/0003-phase-3-persona-broadcast.md`
- `docs/decisions/0004-persona-external-configuration.md`
- `docs/playbooks/phase-2-multi-adapter.md`
- `docs/journal/ROUNDS.md` Round 11
