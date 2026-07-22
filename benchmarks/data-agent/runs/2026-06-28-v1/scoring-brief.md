# 评分说明

这份文件帮助人类在不读源码的情况下填写 `human-scorecard.md`。

## 本轮到底评什么

本 benchmark 分成两半:

1. **AICO 编排质量**:AI Company OS 能不能像一个 IM 项目办公室一样,用 lead / challenger / tester / reviewer 等角色推进复杂任务。
2. **Data-Agent 产品质量**:`data-agent-v1` 是否是一个可运行、可解释、有证据的企业数据代理 benchmark 产品。

不要让 Data-Agent 能跑这件事,掩盖 AICO 编排体验没有真实跑通的问题。

## 证据地图

| 评分区域 | 主要证据 |
|---|---|
| 启动和 project office | `aico-evidence.md`,真实 Telegram `/project`, `/team` |
| Goal Brief | `goal-brief.md`,真实 Telegram `/goal` 输出 |
| 多 agent 分工 | 真实 Telegram `/ask challenger`, `/ask lead`, `/task` trace |
| 人类注意力保护 | 审批/澄清次数和质量 |
| 老板缺席恢复 | 真实 Telegram `/overnight`, `/morning`, `/inbox` |
| 可追溯和审计 | 真实 Telegram `/task`, `/view`, `.aico/data-agent-v1-audit.jsonl` |
| 产品 quickstart | `projects/data-agent-v1/README.md` |
| 数据真实感 | `projects/data-agent-v1/sample_data/enterprise_week_one/README.md` |
| 语义层 | `projects/data-agent-v1/src/data_agent_v1/semantic_layer.py` |
| 回答证据 | `data-agent-eval.md` 的三条人工问题输出 |
| Golden eval | `data-agent-eval.md`, `projects/data-agent-v1/evals/golden_questions.json` |
| 工程质量 | 单测、ruff、mypy、root pytest 证据 |
| 本地命令合同 baseline | `local-im-baseline-transcript.md` |
| 独立 AI 挑刺草稿 | `ai-critic-scorecard-draft.md` |
| AI 预检与建议分 | `ai-precheck-and-score.md` |

## 强制失败条件参考

| 检查项 | 当前建议 |
|---|---|
| Data-Agent 无法按 quickstart 运行 | No。当前 targeted tests 和 CLI 命令通过。 |
| 没有确定性测试或 golden eval | No。20 条 golden eval 存在且通过。 |
| AICO 没有 task / audit / handoff 证据 | 真实 Telegram 证据仍缺失;local injected 证据存在但不能替代真实 IM。 |
| 最终结果只依赖模型口头描述 | 产品侧 No,因为有确定性 Python 逻辑和测试;AICO 编排侧要单独看 transcript。 |
| synthetic 数据冒充真实客户数据 | No。数据模型 README 明确是 synthetic benchmark data。 |
| 未授权外部发布、上传、付款、凭据动作 | No。当前未发生这类动作。 |

## Data-Agent 产品事实

- 产品是基于本地 CSV 的确定性 Python CLI,不是只靠 LLM 口头回答。
- 样例数据是 synthetic,且规模故意较小。
- 核心事实表是 `orders.csv`;支撑表是 `refunds.csv`、`ad_spend.csv`、`inventory.csv`、`customers.csv`。
- canonical 问题“本月华东区收入为什么下降？”可解释为:East paid revenue 从 2026-05 的 120000 降到 2026-06 的 84000。
- 最大渠道拖累是 Douyin:45000 降到 28000,delta -17000。
- 当前产品 gates:targeted tests 7/7,golden eval 20/20。
- local injected IM baseline 覆盖了 `/project`、`/team`、`/goal`、角色 asks、`/overnight`、`/morning`、`/inbox`、`/tasks`、`/view`,但它使用 fake adapters 和 recording channel。只能作为命令合同证据,不能作为真实 Telegram UX 证据。

## 严格扣分点

出现以下情况就要扣分:

- `/morning` 不能让人不翻聊天记录就看懂发生了什么。
- `/view` 缺失、为空、或不可帮助接手。
- 唯一 AICO transcript 是 local injected,没有真实 Telegram。
- AICO 角色只是标签,没有独立责任和因果链。
- Data-Agent 回答缺少证据、公式、SQL-like trace 或 caveat。
- 样例数据过小,无法支撑“企业级”判断。
- 系统要求人类微操实现细节,而不是只做审批/取舍/验收。

## 推荐评分流程

1. 先读 `ai-precheck-and-score.md`。
2. 再读 `ai-critic-scorecard-draft.md`,用它校准自己不要给高分。
3. 看 `aico-evidence.md`,确认真实 Telegram 证据是否存在。
4. 看 `local-im-baseline-transcript.md`,但只把它当成命令合同证据。
5. 看 `data-agent-eval.md` 和样例数据模型 README。
6. 先填强制失败条件。
7. 分开填 AICO 50 分和 Data-Agent 50 分。
8. 写下 AICO 和 Data-Agent 各自前三个要修的问题。
9. 在真实 Telegram 证据出来前,不要启动 `data-agent-v2` 作为正式对比。
