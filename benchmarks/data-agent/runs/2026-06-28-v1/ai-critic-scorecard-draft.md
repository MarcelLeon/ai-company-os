# AI 挑刺评分草稿

这是一份独立只读子 agent 产出的挑刺草稿。它故意严格,不能替代 `human-scorecard.md`。

## 摘要

- AICO 编排:`4/50`
- Data-Agent 产品:`38/50`
- 草稿总分:`42/100`

核心批评:Data-Agent 产品证据相对扎实,但 AICO 编排证据还不是一个真实 Telegram baseline。当前 benchmark 有“产品先被 scaffold 出来,再补 AICO 证据”的后验证明风险。

## AICO 编排:4 / 50

| 类目 | 分数 | 扣分原因 |
|---|---:|---|
| 启动和 project office | 1/5 | 有 runtime 和命令模板,但没有真实 Telegram `/project`、`/team` transcript。 |
| Goal Brief | 0/6 | 没有真实 `/goal` 输出证据。 |
| 多 agent 分工 | 0/7 | 没有来自真实 IM 的 lead / challenger / tester / reviewer 因果链。 |
| 人类注意力保护 | 1/6 | SOP 设计上保护注意力,但没有真实 run 证明。 |
| 老板缺席恢复 | 0/8 | 真实 `/overnight`、`/morning`、`/inbox` 缺失。 |
| 可追溯和审计 | 1/6 | 有 audit/state 路径,但真实 `/task`、`/view` 缺失。 |
| 风险和审批 | 1/5 | SOP 写了审批,但没有真实 approval prompt。 |
| 中断和失败恢复 | 0/4 | 没有 `/interrupt` 或 failed handoff 证据。 |
| 整体管理感 | 0/3 | 目前更像准备好的剧本,不像已验证的项目办公室。 |

## Data-Agent 产品:38 / 50

| 类目 | 分数 | 扣分原因 |
|---|---:|---|
| 新用户 quickstart | 5/5 | README 和 `data-agent-eval.md` 证明能跑。 |
| 样例数据真实感 | 3/5 | 覆盖 orders / refunds / ad_spend / inventory / customers,但规模很小。 |
| 语义层 | 6/8 | 数据模型 README 有指标、粒度、join key、公式;生产治理未证明。 |
| 回答证据 | 7/8 | 三个问题有 evidence、calculation、SQL-like trace、follow-up;但模板感强。 |
| 歧义处理 | 3/5 | 有 follow-up questions,但交互式追问没有深测。 |
| Golden eval | 8/8 | 20/20 passed。 |
| 测试和工程质量 | 4/5 | 有 targeted 和 root test 证据,但 benchmark 很小。 |
| 安全和隐私 | 2/3 | synthetic 数据标清楚;权限、PII、RLS 未覆盖。 |
| 产品有用性 | 0/3 | 是有用的 deterministic CLI benchmark,但不是企业部署级产品。 |

## 强制失败条件

| 条件 | 状态 |
|---|---|
| Data-Agent 无法 quickstart | 未触发。 |
| 没有确定性测试或 golden eval | 未触发。 |
| AICO 没有 task/audit/handoff 证据 | 真实 IM 层接近触发;local injected 证据存在,但不能替代真实 Telegram。 |
| 最终结果只依赖模型口头描述 | 产品侧未触发;AICO 编排侧仍弱。 |
| synthetic 数据冒充真实客户数据 | 未触发。 |
| 未授权外部动作 | 未触发。 |

## 尖锐批评

1. 当前 benchmark 最大风险是“产品先做出来,AICO 编排后补证据”。
2. 没有真实 Telegram transcript 时,AICO 证据就是空壳。
3. Data-Agent 可能过拟合 20 条 golden questions 和小样例。
4. “企业级”这个词现在偏虚,更准确是 enterprise-shaped benchmark。
5. 多 agent 是否真实协作仍未由真实 IM 证明。
6. AICO 的核心卖点是老板缺席,但真实 `/morning`、`/inbox`、`/view` 缺失。
7. human scorecard 必须分离“产品做成了”和“AICO 管成了”。

## 挑刺结论

人类可以把这份草稿作为保守参考,但不要用产品证据抬高 AICO 编排分。真实 Telegram transcript 仍然是缺失证明。
