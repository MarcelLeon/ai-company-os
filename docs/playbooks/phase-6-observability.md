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
- 返回 `Metrics (local process)`。
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

- `/metrics` 不应派发新 Adapter 任务。
- `/metrics` 只汇总当前本地进程内状态;重启后清空是当前预期。
- 24h / 7d 第一版使用 task `updated_at` 和 audit event `timestamp` 过滤。

## 失败排查

- 如果 `/metrics` 返回未知命令,确认进程已包含 Round 61 后代码。
- 如果指标和 `/tasks` 明显不一致,先确认任务是否在当前进程内创建,重启前后的状态不会自动合并。
- 如果 token/cost 是 unavailable,这是当前预期,不要手工填假数据。

## 相关

- ADR-0014
- ROUNDS Round 61
- `docs/architecture/product-entrypoints.md`
