# Daily Ops — 日常运维速查

> 高频运维操作速查。按场景组织,不按命令组织。
> 当前已有本地验证命令。真实启动 / 任务 / Adapter 运维命令将在 Phase 1 链路完成后填充。

---

## 启动 / 停止

```bash
export AICO_TELEGRAM_BOT_TOKEN="你的 Telegram Bot Token"
export AICO_CLAUDE_WORKING_DIRECTORY="/Users/wangzq/VsCodeProjects/ai-company-os"
env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python /opt/homebrew/bin/python3.11 aico-phase1
```

停止时用 `Ctrl-C`。

### 启用 Phase 2 双 Adapter 状态查询

```bash
export AICO_TELEGRAM_BOT_TOKEN="你的 Telegram Bot Token"
export AICO_ENABLE_CODEX_ADAPTER=true
export AICO_CLAUDE_WORKING_DIRECTORY="/Users/wangzq/VsCodeProjects/ai-company-os"
export AICO_PERSONA_CONFIG_PATH="config/personas.example.json"
env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python /opt/homebrew/bin/python3.11 aico-phase1
```

`AICO_PERSONA_CONFIG_PATH` 可省略;省略时使用内置默认 persona。指定后,配置文件中的 `adapter_name` 必须引用当前已启用的 Adapter。

启动后在 Telegram Bot 会话中发送 `/status`,应看到 `claude-code` 和 `codex` 两个 Adapter。跑过任务后再次发送 `/status`,还会看到最近任务状态。

常用 Telegram 命令:

```text
/help
/status
/claude summarize this repo in one sentence
/codex summarize this repo in one sentence
@codex summarize this repo in one sentence
codex: summarize this repo in one sentence
/broadcast summarize this repo in one sentence
/approve <task_id>
/reject <task_id> [reason]
```

写文件、shell 执行和破坏性任务会先进入审批状态。Telegram 返回 `Approval required: <task_id>` 后,用 `/approve <task_id>` 批准继续,或用 `/reject <task_id> [reason]` 拒绝。

默认 Persona:

| Persona | Adapter | Alias |
|---|---|---|
| `implementer` | `claude-code` | `/claude`, `/claude-code` |
| `reviewer` | `codex` | `/codex` |

---

## 本地验证

```bash
env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python /opt/homebrew/bin/python3.11 pytest
env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python /opt/homebrew/bin/python3.11 ruff check .
env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python /opt/homebrew/bin/python3.11 ruff format --check .
env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python /opt/homebrew/bin/python3.11 mypy src tests
```

---

## 日志查看

```bash
# 实时日志
# 按 traceId 过滤
# 按 taskId 过滤
```

---

## 任务管理

```text
/status
```

当前 `/status` 会展示 Adapter 状态和最近任务状态。任务状态包括:`running`、`waiting_approval`、`done`、`failed`、`interrupted`、`rejected`。危险任务会在状态行展示风险等级,如 `write_files` / `shell_exec` / `destructive`。

```bash
# 中断某个任务
# 重试失败任务
```

---

## Adapter 管理

```bash
# 列出所有已注册 Adapter
# 启用 / 禁用某个 Adapter
# 查看某 Adapter 状态
```

---

## Channel 管理

```bash
# 列出所有 IM 通道状态
# 重连 Telegram Webhook
```

---

## 配置变更

```bash
# 查看当前生效配置
# reload 配置(无需重启)
```

---

## 数据备份与恢复

```bash
# 备份当前任务历史
# 备份当前 Persona 配置
# 恢复到某个备份点
```

---

## 健康检查

```bash
# 自检命令
# 验证所有 Adapter 可达
# 验证所有 Channel 可达
```

---

## Dogfooding 推荐流程(Phase 1 完成后)

每天早晚两次 5 分钟:

**早上**(检查夜间任务):
1. 打开 Telegram"晨会群"
2. 看夜间各 AI 跑的任务汇总
3. 决定今天派什么新任务

**晚上**(下达夜间任务):
1. 整理白天没做完的事
2. 在 Telegram 群里发任务"今晚把 issue #X-#Y 看一遍"
3. 关电脑(Adapter 仍在跑)

---

## 月度运维

- [ ] 检查 token 消耗,看哪个 Adapter 性价比低
- [ ] 检查 PITFALLS 是否有可以转化为 ADR 的模式
- [ ] 检查 BLOCKERS 是否有长期未解决项,提升优先级
- [ ] 清理 Round 50+ 之前的归档(如有需要)
