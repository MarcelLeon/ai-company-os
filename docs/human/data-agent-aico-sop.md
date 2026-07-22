# Data-Agent AICO 操作 SOP

> 用 AICO 研发并验收企业级 Data-Agent benchmark 产品的人类操作手册。

## 什么时候用

当你想判断 AICO 是否足够好,能在“人类基本缺席”的情况下管理一个复杂产品构建时,使用这套 SOP。

目标不是演示聊天,而是产出一个可运行、可评分、后续可和 `data-agent-v2` 对比的 Data-Agent。

## 人类角色

你扮演老板和最终客户,只做四件事:

1. 设定结果。
2. 批准或拒绝风险动作。
3. 做真实产品取舍。
4. 给 AICO run 和 Data-Agent 产品打分。

如果系统需要你微操实现步骤,那就是 AICO 体验失败,应该在 scorecard 里扣分。

## 前置条件

第一轮 run 前,agent 应准备好:

- `projects/data-agent-v1/` 项目入口文档。
- AICO project config,包含 lead / architect / implementer / tester / reviewer / challenger。
- benchmark run 目录:`benchmarks/data-agent/runs/`。
- 评分卡:`benchmarks/data-agent/scorecard.md`。

Runtime 条件:

- Telegram bot token 或另一个已配置 IM channel。
- 本地 Claude Code 和 Codex CLI 已安装并登录。
- `AICO_STATE_DB_PATH`、`AICO_AUDIT_LOG_PATH`、`AICO_MEMORY_PATH` 指向本 benchmark 的独立文件。
- 如果要验 `/view`,设置 `AICO_VIEW_ENABLED=true`。

## 启动 AICO

在仓库根目录执行:

```bash
export AICO_TELEGRAM_BOT_TOKEN="<token>"
export AICO_ENABLE_CODEX_ADAPTER=true
export AICO_CLAUDE_WORKING_DIRECTORY="/Users/wangzq/VsCodeProjects/ai-company-os"
export AICO_PROJECT_CONFIG_PATH="projects/data-agent-v1/aico-project.json"
export AICO_AUDIT_LOG_PATH=".aico/data-agent-v1-audit.jsonl"
export AICO_MEMORY_PATH=".aico/data-agent-v1-memory.jsonl"
export AICO_STATE_DB_PATH=".aico/data-agent-v1-state.db"
export AICO_VIEW_ENABLED=true
export AICO_VIEW_PROJECT_IDS=data-agent-v1
uv run --python /opt/homebrew/bin/python3.11 aico-phase1
```

保持进程运行。停止整个 runtime 用 `Ctrl-C`;停止单个任务在 IM 里用 `/interrupt <short_id>`。

## 第一组 IM 消息

在 IM 客户端发送:

```text
/project data-agent-v1
/team
/goal lead 研发企业级 data-agent v1。验收: 本地可运行; 有语义层; 能回答20个golden业务问题; 回答必须给出SQL或确定性计算依据; 遇到歧义必须追问; 有测试、README、quickstart、handoff和AICO证据。停止: 需要真实外部账号、付费、上传第三方、或无法确定企业语义口径。
/ask challenger 按企业级 data-agent 标准挑战当前目标，指出范围、验收、商业价值和玩具化风险，只读审查，不改文件。
/ask lead 综合 challenger 意见，给出最终切片计划、角色分工、验收证据和第一步任务。
```

lead 给出 bounded slice 且 challenger 挑出主要风险前,不要批准实现。

## 跑一个 bounded build slice

只用带清晰验收证据的 `/overnight`:

```text
/overnight 按最终切片计划推进 data-agent-v1 的最小可运行版本。验收: 能本地启动; 3个样例业务问题有SQL或确定性计算依据; tester给出失败/通过证据; reviewer指出未解决风险; lead留下done/blocked/risks/next actions。
```

如果出现风险任务:

```text
/inbox
/task <short_id>
/approve <short_id>
```

只批准预期内的本地写文件或安全测试。遇到不清楚、破坏性、外部账号、凭据、付款、上传,直接拒绝或暂停。

## 早上接手

回来后只看:

```text
/morning
/inbox
/view
/task <short_id>
```

不要靠翻聊天记录重建进度。如果这些命令不足以让你理解发生了什么、下一步该做什么,就在 “boss-absent recovery” 扣分。

## 产品验收

AICO 声称 Data-Agent ready 后:

1. 打开 Data-Agent quickstart。
2. 像新用户一样运行产品。
3. 至少问三条业务问题:
   - “本月华东区收入为什么下降？”
   - “广告 ROAS 低是哪个渠道拖累的？”
   - “退款率上升主要来自哪些商品或客户分群？”
4. 确认每个回答都有 evidence、公式或 SQL、caveat,遇到歧义会追问。
5. 跑或检查 20 条 golden eval。
6. 填 `benchmarks/data-agent/runs/<run>/human-scorecard.md`。

## Computer Use / UX 检查

可以让 agent 检查这些 UI 面:

- Telegram Desktop 里 `/morning`、`/inbox`、`/task` 的第一屏。
- `/view` HTML snapshot。
- Data-Agent 本地 Web UI,如果有。

agent 可以点击、滚动、截图本地 UI。但遇到外部发布、登录跳转、文件上传、付款、账号创建或敏感数据输入,必须停下等人工确认。

## 完成规则

只有同时满足以下条件,一个 run 才算完成:

- Data-Agent 能按 quickstart 运行。
- Golden eval 结果已记录。
- AICO 证据已记录。
- tester 和 reviewer 有独立 verdict。
- 人类 scorecard 已填写。
- 下一轮 AICO 改进目标已列出。

缺任何一项,就保持 run open 或标记 failed。不要用 “mostly done” 的模型话术软化 benchmark。
