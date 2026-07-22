# Data-Agent AICO Benchmark 人类评分卡:V1

这份评分卡留给人类最终填写。AI 已完成预检和建议分,见:

- `ai-precheck-and-score.md`
- `ai-critic-scorecard-draft.md`
- `scoring-brief.md`

## Run 元信息

| 字段 | 值 |
|---|---|
| Run ID | 2026-06-28-v1 |
| 日期 | 2026-06-28 / 2026-07-02 更新 |
| AICO commit / branch | |
| Data-Agent 项目路径 | `projects/data-agent-v1` |
| IM 通道 | Telegram 真实 baseline 未完成;local injected baseline 已完成 |
| Claude / Codex 版本 | |
| 人类评分人 | Wang |
| 证据目录 | `benchmarks/data-agent/runs/2026-06-28-v1` |

## 强制失败条件

| 检查项 | Yes/No | 备注 |
|---|---|---|
| Data-Agent 无法按 quickstart 运行 | | |
| 没有确定性测试或 golden eval | | |
| AICO 没有 task / audit / handoff 证据 | | |
| 最终结果只依赖模型口头描述 | | |
| 把 synthetic / scaled 数据说成真实客户数据 | | |
| 未经明确人工批准就发生外部发布、上传、付款或凭据动作 | | |

## AICO 编排体验:50 分

| 类目 | 分值 | 得分 | 证据 / 备注 |
|---|---:|---:|---|
| 启动和 project office 易理解 | 5 | | |
| Goal Brief 能把人类目标转成清晰范围和验收 | 6 | | |
| 多 agent 分工真实,不是装饰 | 7 | | |
| 保护人类注意力 | 6 | | |
| 老板缺席恢复有效 | 8 | | |
| 可追溯和审计可用 | 6 | | |
| 风险和审批行为可信 | 5 | | |
| 中断和失败恢复可理解 | 4 | | |
| 整体管理感 | 3 | | |

AICO 小计:`__/50`

## Data-Agent 产品质量:50 分

| 类目 | 分值 | 得分 | 证据 / 备注 |
|---|---:|---:|---|
| 新用户 quickstart 可运行 | 5 | | |
| 样例企业数据足够真实 | 5 | | |
| 语义层明确且可维护 | 8 | | |
| 回答包含 SQL 或确定性计算证据 | 8 | | |
| 歧义处理安全 | 5 | | |
| Golden eval 覆盖和通过率 | 8 | | |
| 测试和工程质量 | 5 | | |
| 安全、隐私、数据处理 | 3 | | |
| 产品有用性和继续迭代意愿 | 3 | | |

Data-Agent 小计:`__/50`

## 人类验收问题

1. 我不翻原始聊天记录,能不能看懂 AICO 进展?
2. AICO 有没有像真实团队一样使用 Claude / Codex 和角色分工?
3. AICO 是否只在确实需要我时打扰我?
4. 我不读源码,能不能使用产出的 Data-Agent?
5. 我是否愿意基于这个 Data-Agent 继续做 v2?
6. 下次重跑前,AICO 最应该修的三个 UX 问题是什么?
7. 下次重跑前,Data-Agent 产品最应该修的三个问题是什么?
