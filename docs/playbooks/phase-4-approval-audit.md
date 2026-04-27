# Playbook: Phase 4 审批与审计 smoke test

## 适用场景

用于验证 Phase 4 第一版审批门禁:远程 Telegram 中的危险任务应进入 `waiting_approval`,人工批准后才派发给 Adapter。

## 前置条件

- 已能正常启动 `aico-phase1`。
- Telegram Bot 已可收发消息。
- 建议启用双 Adapter 和 persona 配置:

```bash
export AICO_TELEGRAM_BOT_TOKEN="你的 Telegram Bot Token"
export AICO_ENABLE_CODEX_ADAPTER=true
export AICO_CLAUDE_WORKING_DIRECTORY="/Users/wangzq/VsCodeProjects/ai-company-os"
export AICO_PERSONA_CONFIG_PATH="config/personas.example.json"
env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python /opt/homebrew/bin/python3.11 aico-phase1
```

## 步骤

1. 发送一个只读任务:

```text
/codex summarize this repo in one sentence
```

预期:任务直接 accepted 并返回结果。

2. 发送一个写文件类任务:

```text
/claude modify docs/human/daily-ops.md to mention approval
```

预期:不会直接执行,Telegram 返回 `Approval required: <task_id>`。

3. 查询状态:

```text
/status
```

预期:最近任务中出现 `waiting_approval (write_files)`。

4. 批准任务:

```text
/approve <task_id>
```

预期:任务开始派发,随后正常流式返回。

5. 再发送一个破坏性任务:

```text
/claude delete generated output
```

预期:返回 `Approval required: <task_id>`,风险等级为 `destructive`。

6. 拒绝任务:

```text
/reject <task_id> too broad
```

预期:任务状态变为 `rejected`,不会派发给 Adapter。

## 验证

- 只读任务不需要审批。
- 写文件 / shell / destructive 任务进入 `waiting_approval`。
- `/approve <task_id>` 后才会调用 Adapter。
- `/reject <task_id>` 后不会调用 Adapter。
- 本地测试通过:

```bash
env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python /opt/homebrew/bin/python3.11 pytest
env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python /opt/homebrew/bin/python3.11 ruff check .
env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python /opt/homebrew/bin/python3.11 ruff format --check .
env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python /opt/homebrew/bin/python3.11 mypy src tests
```

## 失败回滚

- 如果只读任务也被拦截,检查 `src/aico/core/risk.py` 的关键词是否过宽。
- 如果危险任务直接执行,检查 `TaskBus.submit()` 是否使用了默认 `TextRiskAssessor`。
- 如果 `/approve` 返回 `unknown pending approval`,确认 task id 来自同一进程内的 `Approval required` 消息。

## 相关

- ADR-0005
- ROUNDS Round 13
- `docs/human/daily-ops.md`
