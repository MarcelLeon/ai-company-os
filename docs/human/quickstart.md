# Quickstart — 5 分钟跑起来

> 给人类看的快速上手文档。当前最小链路是 Telegram → 编排核心 → Claude Code / Codex。

---

## 当前阶段说明

项目当前处于 Phase 3 早期:Phase 1 单链路和 Phase 2 双 Adapter 已通过真实 Telegram 验收,Phase 3 已有 Persona 与 `/broadcast` 的本地实现,等待真实 Telegram smoke test。

---

## 5 步快速上手

### 前置依赖
- macOS / Linux
- Python 3.11+(见 ADR-0001)
- Telegram Bot Token([如何创建](https://core.telegram.org/bots/tutorial))
- Claude Code 已安装并能在命令行使用
- Codex CLI 已安装并能在命令行使用(启用双 Adapter / broadcast 时需要)

```bash
# 1. clone 仓库
git clone <repo-url>
cd ai-company-os

# 2. 配置环境变量
export AICO_TELEGRAM_BOT_TOKEN="你的 Telegram Bot Token"
export AICO_ENABLE_CODEX_ADAPTER=true
export AICO_CLAUDE_WORKING_DIRECTORY="/Users/wangzq/VsCodeProjects/ai-company-os"
export AICO_PERSONA_CONFIG_PATH="config/personas.example.json"

# 3. 安装依赖
env UV_CACHE_DIR=/tmp/aico-uv-cache uv sync --python /opt/homebrew/bin/python3.11

# 4. 启动服务
env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python /opt/homebrew/bin/python3.11 aico-phase1

# 5. 在 Telegram 找你的 Bot,发送命令
# /help
```

常用命令:

```text
/status
/claude summarize this repo in one sentence
/codex summarize this repo in one sentence
/broadcast summarize this repo in one sentence
```

预期效果:Bot 把请求派发给对应 persona / Adapter,执行结果回到 Telegram。`/status` 会显示 Adapter 状态和最近任务状态。

---

## 跑不起来怎么办

参见 [`troubleshooting.md`](troubleshooting.md)。
