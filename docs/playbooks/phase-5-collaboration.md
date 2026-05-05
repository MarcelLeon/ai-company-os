# Playbook: Phase 5 AI 间协作 smoke test

## 适用场景

用于验证 Phase 5 第一版 AI 间协作:一个 persona 在输出中显式 `@reviewer: ...`,编排核心会把它转成另一个 persona 的普通任务,并把结果回到同一 Telegram 会话。

## 前置条件

- 已能正常启动 `aico-phase1`。
- Telegram Bot 已可收发消息。
- 建议启用双 Adapter 和 persona 配置:

```bash
export AICO_TELEGRAM_BOT_TOKEN="你的 Telegram Bot Token"
export AICO_ENABLE_CODEX_ADAPTER=true
export AICO_CLAUDE_WORKING_DIRECTORY="/Users/wangzq/VsCodeProjects/ai-company-os"
export AICO_PERSONA_CONFIG_PATH="config/personas.example.json"
export AICO_AUDIT_LOG_PATH="/tmp/aico-audit.jsonl"
env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python /opt/homebrew/bin/python3.11 aico-phase1
```

## 步骤

1. 确认双 persona 可用:

```text
/status
/agents
/agent claude
```

预期:
- `/status` 能看到 `claude-code` 和 `codex`。
- `/agents` 能看到 `implementer -> claude-code` 和 `reviewer -> codex`。
- `/agent claude` 能看到 implementer 的 role、provider、capabilities、skills/tools 来源。

可选能力探测:

```text
/skills claude
/tools codex
```

预期:问题会被路由给底层 provider 自己回答,AICO 不复制一份 skills/tools registry。

2. 发送一个明确要求 implementer 请求 reviewer 协作的任务:

```text
/claude 请先简要分析这个仓库的 Phase 5 协作方案，然后输出一行 @reviewer review the Phase 5 collaboration plan for risks and missing tests
```

预期:
- Claude 输出中出现 `@reviewer ...` 或 `@reviewer: ...` 这一行时,Telegram 收到 `Collaboration requested: implementer -> reviewer`。
- 系统随后创建 reviewer 子任务,并显示 `Task accepted: <task_id> [reviewer]`。
- Codex/reviewer 的输出会回到同一 Telegram 会话。

3. 查询状态:

```text
/status
```

预期:最近任务里能看到 parent task 和 reviewer child task 的状态。

4. 查询审计:

```text
/audit
```

预期:
- 能看到 `collaboration_requested` 事件。
- 该事件的 `task` 是 reviewer child task,`actor` 是源 persona,如 `implementer`。
- `detail` 中包含 `parent_task=<parent_task_id>`。
- 随后还能看到 reviewer child task 的 `task_submitted` 和 `adapter_dispatched` 等事件。

## 验证

- 协作指令必须是明确行首语法:`@persona request` 或 `@persona: request`。
- 协作子任务仍走 `TaskBus`,因此风险任务仍会进入审批或被能力门禁拒绝。
- 协作关系会进入审计流,不需要从 Telegram 文本里手工推断 parent / child。
- 当前只支持单层协作,避免 AI 之间无限递归。
- 协作不依赖 Telegram 作为内部总线;Telegram 只展示协作过程。
- 长文本结果应自动拆成多条 Telegram 消息,不会因为单条 4096 字符限制中断。

5. 可选:绑定已有 Codex provider session。

如果已经从 Codex CLI 或后续日志中拿到了可 resume 的 provider session id:

```text
/bind codex <provider_session_id>
继续 review 刚才的 Phase 5 风险
```

预期:
- Telegram 返回 `Provider session bound: ... [reviewer]`。
- 后续普通消息路由到 reviewer/Codex。
- 日志中 Codex Adapter 命令使用 `provider_session_mode=resume`。

## 失败排查

- 如果没有触发协作,检查 Adapter 输出是否真的以 `@reviewer ` 或 `@reviewer:` 开头;普通文本中的 `@reviewer` 不会触发。
- 如果 reviewer 未启用,检查 `AICO_ENABLE_CODEX_ADAPTER=true` 和 `AICO_PERSONA_CONFIG_PATH`。
- 如果 reviewer 子任务被拒绝,检查协作 payload 是否被风险识别为写文件 / shell / destructive。
- 如果长文本仍然只收到一部分,确认进程已包含 Round 21 的 `StreamedMessageWriter` 修复。
- 如果 `/bind codex ...` 后普通消息没有进入 Codex,先确认当前聊天是否收到 `Provider session bound`,再用 `/sessions` 看 active session。

## 相关

- ADR-0009
- ROUNDS Round 19
- `docs/human/daily-ops.md`
