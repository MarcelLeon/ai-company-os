# Playbook: Phase 6 Observability Smoke Test

## 适用场景

用于验证 Phase 6 第一版 IM-first `/metrics` 可观测入口。

## 前置条件

- 已能正常启动 `aico-phase1`。
- Telegram Bot 已可收发消息。
- 建议启用双 Adapter 和项目配置:

```bash
export AICO_TELEGRAM_BOT_TOKEN="你的 Telegram Bot Token"
export AICO_ENABLE_CODEX_ADAPTER=true
export AICO_CLAUDE_WORKING_DIRECTORY="/Users/wangzq/VsCodeProjects/ai-company-os"
export AICO_PERSONA_CONFIG_PATH="config/personas.example.json"
export AICO_PROJECT_CONFIG_PATH="config/projects.example.json"
env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python /opt/homebrew/bin/python3.11 aico-phase1
```

## 步骤

1. 启动后先查空状态:

```text
/metrics
```

预期:
- 返回 `Metrics (local state + audit replay)`。
- 包含 `glance` 小节;没有任务时 `status: quiet`,`open: 0`。
- 24h / 7d 两个窗口都可见。
- 没有任务时 `tasks: 0`,`open work: - none`。
- token/cost 显示 unavailable。

2. 制造一个完成任务:

```text
/claude summarize this repo in one sentence
```

等待完成后:

```text
/metrics
```

预期:
- `tasks` 增加。
- `done` 至少为 1。
- `agents` 中能看到 `claude-code`。

3. 制造一个待审批任务:

```text
/claude modify src/aico/core/metrics.py by adding a harmless comment
```

不要立刻 approve,先发送:

```text
/metrics
```

预期:
- `waiting_approval` 至少为 1。
- `glance` 显示 `status: needs_approval`。
- `open work` 展示该 task。

4. 可选:制造协作事件:

```text
/claude 请输出一行:
@reviewer review the current metrics MVP for obvious risks
```

随后:

```text
/metrics
```

预期:
- `collaboration` 至少为 1。

## 验证

- 省 token 本地验收:

```bash
uv run pytest tests/unit/test_phase6_metrics_acceptance.py
```

这个验收样例不调用任何真实 LLM/CLI Provider。它用 fake Telegram channel 和
`NoTokenAdapter` 生成:
- 1 个 done task。
- 1 个 waiting approval task。
- 1 条 collaboration request audit event。
- 1 份临时 audit JSONL。

然后依次验证:
- live `/metrics` 文本包含 `glance`、24h/7d、open work 和 collaboration。
- “重启后”只从 audit JSONL 恢复 `/metrics` 历史指标。
- `aico-metrics --audit-log ...` text/json 与 `/metrics` 口径一致。
- `aico-glance --audit-log ...` text/json 能输出 waiting approval 动作命令。

- 真实模型 token golden 验收:

```bash
env AICO_RUN_TOKEN_GOLDEN=1 AICO_TOKEN_GOLDEN_COMMAND='codex --ask-for-approval never exec --sandbox read-only --color never' uv run pytest tests/golden/test_phase6_metrics_token_golden.py
```

这个 golden 默认跳过,只有显式设置 `AICO_RUN_TOKEN_GOLDEN=1` 才会消耗 provider token。
它会通过真实 Codex CLI 发起一个极短只读任务,验证:
- 模型输出包含 `AICO_METRICS_TOKEN_SMOKE_OK`。
- live `/metrics` 把该任务统计为 `done=1`。
- “重启后”只从 audit JSONL 恢复同一条 done task。
- `aico-metrics --audit-log ...` 与 live `/metrics` 口径一致。

注意:token golden 的 prompt 必须保持极短、无风险词。不要在 smoke prompt 中写
`run`、`modify`、`edit` 等词,即便是否定句也会被风险识别按危险词处理,导致任务进入审批而不是发给 provider。

- `/metrics` 不应派发新 Adapter 任务。
- 配置 `AICO_AUDIT_LOG_PATH` 后,重启再发送 `/metrics`,历史 done / failed / interrupted / rejected / waiting approval 指标应能从 audit JSONL 恢复。
- `/tasks` 仍只展示当前本地进程内任务,不会从 audit JSONL 恢复完整任务列表。
- 24h / 7d 第一版使用 task `updated_at` 和 audit event `timestamp` 过滤。
- 本地 CLI 可读取同一份 audit JSONL:

```bash
env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python /opt/homebrew/bin/python3.11 aico-metrics --audit-log "$AICO_AUDIT_LOG_PATH"
env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python /opt/homebrew/bin/python3.11 aico-metrics --audit-log "$AICO_AUDIT_LOG_PATH" --format json
env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python /opt/homebrew/bin/python3.11 aico-glance --audit-log "$AICO_AUDIT_LOG_PATH"
env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python /opt/homebrew/bin/python3.11 aico-glance --audit-log "$AICO_AUDIT_LOG_PATH" --format json
```

预期 text 输出和 Telegram `/metrics` 的历史指标口径一致;JSON 输出包含 `glance`、`summaries` 和 `token_cost`。
`aico-glance` 预期输出更紧凑的 Status Island 快照,包含:
- `AICO needs approval` / `AICO working` / `AICO needs attention` / `AICO quiet`。
- active agents、open/running/waiting/failed 数。
- 最近任务及 `/task`、`/approve`、`/reject`、`/interrupt` 命令提示。
- 可选验证 usage 接入边界:

如果某个 Adapter 后续能上报 usage,它应记录 `task_usage_recorded` 审计事件,`detail` 使用 JSON:

```json
{"input_tokens":10,"output_tokens":20,"total_tokens":30,"cost_usd":0.03}
```

预期:
- `/metrics` / `aico-metrics` 会展示真实 token/cost 汇总。
- 没有 `task_usage_recorded` 时继续显示 unavailable,不要手工估算。

## 失败排查

- 如果 `/metrics` 返回未知命令,确认进程已包含 Round 61 后代码。
- 如果指标和 `/tasks` 明显不一致,先确认是否经历过重启;`/metrics` 会回放 audit JSONL,`/tasks` 不会。
- 如果重启后 `/metrics` 没有历史指标,确认启动时设置了 `AICO_AUDIT_LOG_PATH`,且该路径下已有 JSONL 审计事件。
- 如果 `aico-metrics` 输出为空,确认传入的 `--audit-log` 路径和 AICO 进程使用的是同一个 `AICO_AUDIT_LOG_PATH`。
- 如果 `aico-glance` 没有动作命令,确认 audit JSONL 中存在 waiting approval 或 running 任务事件。
- 如果 token/cost 是 unavailable,这是当前预期,不要手工填假数据。

## 相关

- ADR-0014
- ADR-0016
- ROUNDS Round 61
- ROUNDS Round 63
- ROUNDS Round 64
- `docs/architecture/product-entrypoints.md`
