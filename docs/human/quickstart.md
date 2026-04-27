# Quickstart — 5 分钟跑起来

> 给人类看的快速上手文档。Phase 1 之后跑通的最小链路。
> 当前项目处于 Phase 0(立项中),本文先占位,Phase 1 完成后会填充实际命令。

---

## 当前阶段说明

⚠️ 项目还在 Phase 0(项目立项与文档体系搭建)。代码尚未开始。
本文档将在 Phase 1 完成时(Telegram → Claude Code 单链路跑通)正式填充。

---

## 预期 Phase 1 完成后的快速上手(占位)

### 前置依赖
- macOS / Linux
- Java 21+ 或 Python 3.11+(取决于 ADR-001 选型)
- Telegram Bot Token([如何创建](https://core.telegram.org/bots/tutorial))
- Claude Code 已安装并能在命令行使用

### 5 步上手
```bash
# 1. clone 仓库
git clone <repo-url>
cd ai-company-os

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 填入 TELEGRAM_BOT_TOKEN

# 3. 安装依赖
# (Java) ./mvnw install
# (Python) uv sync

# 4. 启动服务
# (Java) ./mvnw spring-boot:run
# (Python) uv run aico

# 5. 在 Telegram 找你的 Bot,发送一条消息
# 例如: "@YourBot 帮我列一下这个目录的文件"
```

预期效果:Bot 把请求派发给 Claude Code,Claude Code 执行,结果回到 Telegram。

---

## 我现在能做什么(Phase 0)

由于代码还未开始,你现在能做的是:

1. **熟悉文档**:
   - 5 分钟读 [`README.md`](../../README.md)
   - 10 分钟读 [`NORTH_STAR.md`](../../NORTH_STAR.md) 和 [`STATUS.md`](../../STATUS.md)
2. **参与决策**:
   - 看 [`docs/journal/BLOCKERS.md`](../journal/BLOCKERS.md) 中的 B-001(技术栈选型)
   - 你的输入会影响 ADR-001
3. **派下一轮任务给 Agent**:
   - 看 `STATUS.md` 的"下一轮建议"
   - 选最高优先级的派给 Claude Code / Codex 等

---

## 跑不起来怎么办

参见 [`troubleshooting.md`](troubleshooting.md)。
