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
# 可选:逗号分隔的额外审批人 Telegram sender id。任务发起人默认可审批自己的任务。
export AICO_APPROVAL_REVIEWER_IDS=""
# 可选:审计事件 JSONL 追加文件。配置后重启进程也能追溯历史事件。
export AICO_AUDIT_LOG_PATH="/tmp/aico-audit.jsonl"
env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python /opt/homebrew/bin/python3.11 aico-phase1
```

## 步骤

1. 发送一个只读任务:

```text
/codex summarize this repo in one sentence
```

预期:任务直接 accepted 并返回结果。

2. 向 Codex 发送一个写文件类任务:

```text
/codex create /tmp/readme.md
```

预期:任务直接 rejected,提示 `adapter codex cannot handle write_files tasks; use /claude`。Codex 是 read-only reviewer,不应进入写任务审批流程。

3. 发送一个 Claude 写文件类任务:

```text
/claude modify docs/human/daily-ops.md to mention approval
```

预期:不会直接执行,Telegram 返回 `Approval required: <short_task_id>`,并提示可直接发送 `/approve`。

4. 查询状态:

```text
/status
```

预期:最近任务中出现 `waiting_approval (write_files)`。

5. 查询审计事件:

```text
/audit
```

预期:返回多行格式的最近审计事件,至少包含 `task_submitted` 和 `approval_requested`,并能看到 task id、actor、target、adapter、risk。

6. 在群聊中用另一个未授权账号尝试批准同一个待审批任务:

```text
/approve
```

预期:返回 `Task rejected: approver not authorized`,任务仍保持 `waiting_approval`,不会派发给 Adapter。`/audit` 能看到 `approval_denied`。

7. 用任务发起人或配置过的额外审批人批准任务:

```text
/approve
```

预期:如果当前只有一个待审批任务,任务开始派发,随后正常流式返回。若有多个待审批任务,返回短 ID 列表,再用 `/approve <short_task_id>`。

8. 再发送一个破坏性任务:

```text
/claude delete generated output
```

预期:返回 `Approval required: <short_task_id>`,风险等级为 `destructive`。

9. 拒绝任务:

```text
/reject
```

预期:如果当前只有一个待审批任务,且发送者是任务发起人或 `AICO_APPROVAL_REVIEWER_IDS` 里的审批人,任务状态变为 `rejected`,不会派发给 Adapter。若有多个待审批任务,返回短 ID 列表,再用 `/reject <short_task_id>`。

10. 再次查询审计事件:

```text
/audit
```

预期:能看到 `approval_approved` / `adapter_dispatched` / `approval_rejected` / `task_rejected` 等事件。

11. 如果配置了 `AICO_AUDIT_LOG_PATH`,在本机查看 JSONL 文件:

```bash
tail -n 20 /tmp/aico-audit.jsonl
```

预期:每行都是一个审计事件 JSON 对象,包含 `event_id`、`event_type`、`task_id`、`actor_id`、`risk_level` 等字段。

## 验证

- 只读任务不需要审批。
- Codex/read-only Adapter 的写文件 / shell / destructive 任务直接拒绝,提示使用 `/claude`。
- 写文件 / shell / destructive 任务进入 `waiting_approval`。
- Claude 写任务经 AICO `/approve` 后不应再要求到电脑本机处理 Claude Code 权限提示。
- `/approve` 或 `/approve <short_task_id>` 后才会调用 Adapter。
- `/reject` 或 `/reject <short_task_id>` 后不会调用 Adapter。
- 非任务发起人且不在 `AICO_APPROVAL_REVIEWER_IDS` 里的用户无法审批或拒绝任务。
- `/audit` 能展示最近审计 trace,便于人工确认危险任务没有绕过门禁。
- 配置 `AICO_AUDIT_LOG_PATH` 后,审计事件会追加写入 JSONL 文件。
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
- ADR-0006
- ADR-0007
- ROUNDS Round 13
- ROUNDS Round 16
- ROUNDS Round 17
- `docs/human/daily-ops.md`
