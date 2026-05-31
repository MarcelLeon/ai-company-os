# Quickstart - 5 分钟跑起来

> 给人类看的快速上手文档。当前最小公开路径是 Telegram -> AICO 编排核心 -> Claude Code / Codex。

---

## 当前阶段说明

项目当前处于 Phase 8:离线托管 + 开源主 Demo。Telegram 主控、Claude Code / Codex
Adapter、项目办公室、审批审计、共享记忆、任务观测和 Release Room Demo 都已经落地。
Cursor / CodeFlicker / Trae / Gemini Adapter 已完成真实 smoke test,可作为已登录本机
CLI 后的可选成员启用。Feishu Channel 已有实现切片,但仍需要真实生产 smoke test 后再作为
稳定公开路径推荐。

---

## 5 步快速上手

### 不配置 token 先看效果

第一次看项目时,可以先跑本地 deterministic Release Room demo。它使用 fake adapters,
不需要 Telegram Bot Token,也不会调用 Claude / Codex / 任何付费 provider:

```bash
git clone https://github.com/MarcelLeon/ai-company-os.git
cd ai-company-os

env UV_CACHE_DIR=/tmp/aico-uv-cache uv sync --python 3.11
env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python 3.11 aico-release-room-demo
```

如果这条链路能看懂,再配置真实 Telegram runtime。

### 前置依赖

- macOS / Linux
- Python 3.11+
- `uv`
- Telegram Bot Token([如何创建](https://core.telegram.org/bots/tutorial))
- Claude Code 已安装并能在命令行使用
- Codex CLI 已安装并能在命令行使用(启用 Codex Adapter 时需要)

```bash
# 1. clone 仓库
git clone https://github.com/MarcelLeon/ai-company-os.git
cd ai-company-os

# 2. 配置环境变量
export AICO_TELEGRAM_BOT_TOKEN="你的 Telegram Bot Token"
export AICO_CLAUDE_WORKING_DIRECTORY="$PWD"
export AICO_ENABLE_CODEX_ADAPTER=true
export AICO_PERSONA_CONFIG_PATH="config/personas.example.json"
export AICO_PROJECT_CONFIG_PATH="config/projects.example.json"
export AICO_AUDIT_LOG_PATH="/tmp/aico-audit.jsonl"
export AICO_MEMORY_PATH="/tmp/aico-memory.jsonl"
export AICO_STATE_DB_PATH="/tmp/aico-state.db"

# 3. 安装依赖
env UV_CACHE_DIR=/tmp/aico-uv-cache uv sync --python 3.11

# 4. 启动 Telegram runtime
env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python 3.11 aico-phase1

# 5. 在 Telegram 找你的 Bot,发送命令
# /help
```

### 常用命令

```text
/help
/status
/project aico
/team
/roles
/ask pm summarize the next release plan in 3 bullets
/remember This project prefers small, reviewable changes.
/recall project preferences
/tasks
/metrics
/audit
/overnight 梳理当前项目下一步,早上给我 done/blocked/risks/next actions
```

预期效果:

- Bot 把请求派发给对应 persona / Adapter,执行结果回到 Telegram。
- `/status` 展示 Adapter 状态和最近任务状态。
- `/project` / `/team` 展示当前项目办公室和团队任命。
- 写文件、shell 或 destructive 任务会先进入 `/approve` / `/reject` 审批流。
- 指定 `AICO_MEMORY_PATH` 后,`/remember` / `/recall` / `/forget` 使用本地 JSONL
  共享记忆;如果启动时没带这个环境变量,运行中的 Bot 需要重启后才会启用记忆。
- 指定 `AICO_STATE_DB_PATH` 后,task records、task snapshots、pending approval
  和 `/overnight` 托管工单会写入 SQLite;重启后 `/tasks`、`/task <id>`、`/approve`
  和 `/overnight` 能恢复 AICO 业务状态。
- 开发期如果只想快速启用本地状态库,也可以设置 `AICO_STATE_DB_PATH=true`;
  AICO 会映射到 `.aico/state.db`,避免在仓库根目录生成名为 `true` 的数据库文件。
  用 `aico-state --db .aico/state.db` 可以查看 schema version 和各状态表行数。

---

## 启动 aico-view(只读 Web 视图)

`aico-view` 是一个独立的 FastAPI 进程,它**不挂 channel/adapter**,只打开
orchestrator 写出的 JSONL/SQLite,提供 Timeline / Task Trace / Memory Tree
三个手机友好视图。所有写操作仍走 IM(/undo、/why、/experience 等),aico-view 自身
是只读的(任何 POST/PUT/DELETE 都会返回 405)。

```bash
export AICO_AUDIT_LOG_PATH="/tmp/aico-audit.jsonl"
export AICO_MEMORY_PATH="/tmp/aico-memory.jsonl"
export AICO_STATE_DB_PATH="/tmp/aico-state.db"
export AICO_VIEW_PROJECT_IDS="aico"     # 可选,逗号分隔
export AICO_VIEW_HOST="127.0.0.1"        # 默认 127.0.0.1,只允许本机访问
export AICO_VIEW_PORT="8765"

uv run aico-view
# 浏览 http://127.0.0.1:8765
```

要让手机访问需要隧道(ngrok / Cloudflare tunnel)和 **`AICO_VIEW_TOKEN`**。
绑非 loopback host 时没设 token 会全请求 401(有意防误暴露)。完整部署形态、
安全模型和 env 速查见 [`aico-view-deploy.md`](aico-view-deploy.md)。

---

## 启用更多 Adapter

这些 Adapter 默认关闭,适合在本机 CLI 已安装并登录后再开启:

```bash
export AICO_ENABLE_CURSOR_ADAPTER=true
export AICO_ENABLE_CODEFLICKER_ADAPTER=true
export AICO_ENABLE_TRAE_ADAPTER=true
export AICO_ENABLE_GEMINI_ADAPTER=true
```

公开 README 当前仍把 Claude Code / Codex 作为最低门槛快速路径。Cursor / CodeFlicker /
Trae / Gemini 已完成真实 smoke test,但使用前仍需要确认本机 CLI 已安装并登录;详见
[`STATUS.md`](../../STATUS.md)。

---

## 跑不起来怎么办

参见 [`troubleshooting.md`](troubleshooting.md) 和 [`daily-ops.md`](daily-ops.md)。
