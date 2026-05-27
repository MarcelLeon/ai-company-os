# Playbook: Optional Agent Adapters 验收

## 适用场景

当 Cursor / CodeFlicker / Trae / Gemini Adapter 新增、改命令、改能力边界后,用本 Playbook 验证它们能进入 `/agents` 并完成最小任务。

## 前置条件

- AICO 本地 Telegram Bot 链路可启动。
- Cursor 验收需要本机安装并登录 `cursor-agent`。
- CodeFlicker 验收需要本机 `flickcli` 可用并完成 SSO 登录。
- Trae 验收需要本机 `trae-cli` 可用并完成登录 / token 配置。
- Gemini 验收需要本机 `gemini` 可用并完成登录 / API key 配置。
- 建议配置 `AICO_AUDIT_LOG_PATH`,便于 `/metrics` 和日志排查。

## 步骤

1. 检查本机 CLI。

   ```bash
   which cursor-agent
   cursor-agent --version
   which flickcli
   flickcli --version
   flickcli --help
   which trae-cli
   trae-cli --help
   which gemini
   gemini --help
   ```

2. 启动 AICO,按需开启 Adapter。

   ```bash
   export AICO_TELEGRAM_BOT_TOKEN="你的 Telegram Bot Token"
   export AICO_CLAUDE_WORKING_DIRECTORY="/Users/wangzq/VsCodeProjects/ai-company-os"
   export AICO_ENABLE_CURSOR_ADAPTER=true
   export AICO_ENABLE_CODEFLICKER_ADAPTER=true
   export AICO_ENABLE_TRAE_ADAPTER=true
   export AICO_ENABLE_GEMINI_ADAPTER=true
   export AICO_AUDIT_LOG_PATH="/tmp/aico-audit.jsonl"
   env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python /opt/homebrew/bin/python3.11 aico-phase1
   ```

3. 在 Telegram 中检查 agent 名录。

   ```text
   /agents
   /agent cursor
   /agent codeflicker
   /agent trae
   /agent gemini
   /status
   ```

4. 发送 read-only smoke task。

   ```text
   /cursor summarize this repo in one sentence, do not edit files
   /codeflicker summarize this repo in one sentence, do not edit files
   /trae summarize this repo in one sentence, do not edit files
   /gemini summarize this repo in one sentence, do not edit files
   ```

5. 发送写能力 smoke task,确认 AICO 先要求审批。

   ```text
   /cursor create a tiny scratch note under /tmp explaining this repo
   /codeflicker create a tiny scratch note under /tmp explaining this repo
   /trae create a tiny scratch note under /tmp explaining this repo
   /gemini create a tiny scratch note under /tmp explaining this repo
   ```

   Telegram 应返回 `Approval required: <task_id>`。确认是预期任务后再 `/approve <task_id>`。

6. 查询任务状态。

   ```text
   /tasks
   /status
   /metrics
   ```

## 验证

- `/agents` 展示已启用的 `cursor`、`codeflicker`、`trae`、`gemini`。
- `/agent <agent>` 的 capabilities 包含 `code_edit` / `shell_exec` / `code_review` / `interruptible`。
- 只读任务能 accepted 并最终 done / failed;如果 CLI 无输出,默认 1800 秒左右会触发 idle timeout,Adapter 释放并发槽位。需要长时间托管时可把对应 `AICO_*_OUTPUT_IDLE_TIMEOUT_SECONDS` 设为 `0` 禁用自动 idle timeout。
- `/agents` / `/agent <agent>` 会展示当前运行数和最大并发。默认单 adapter 最多 5 个运行中任务,建议不要给同一个 agent 任命超过 5 个高频 role。
- 写文件或 shell 类任务必须先进入 AICO 审批,批准后才派发到底层 CLI。

## 失败回滚

- 关闭对应 `AICO_ENABLE_*_ADAPTER`,重启 AICO 即可回到原 Claude/Codex 路径。
- Cursor 未安装或未登录时,先不要开启 `AICO_ENABLE_CURSOR_ADAPTER`。
- CodeFlicker 未登录或内网不可用时,先不要开启 `AICO_ENABLE_CODEFLICKER_ADAPTER`。
- Trae 未登录或本机 keyring/token 不可用时,先不要开启 `AICO_ENABLE_TRAE_ADAPTER`。
- Gemini 未登录或 API key 不可用时,先不要开启 `AICO_ENABLE_GEMINI_ADAPTER`。

## 相关

- ADR-0017
- ADR-0018
- ROUNDS Round 66
- ROUNDS Round 67
- `src/aico/adapter/cursor.py`
- `src/aico/adapter/codeflicker.py`
- `src/aico/adapter/trae.py`
- `src/aico/adapter/gemini.py`
