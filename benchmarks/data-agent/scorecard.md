# Data-Agent AICO Benchmark 评分卡

每次 benchmark run 复制一份到:
`benchmarks/data-agent/runs/<YYYY-MM-DD>-v1/human-scorecard.md`。

评分原则:

- 总分 100 分。
- AICO 编排体验 50 分,Data-Agent 产品质量 50 分。
- 不要让 Data-Agent 产品能跑这件事,掩盖 AICO 编排体验没有跑通的问题。
- local injected baseline 只能算命令合同证据,不能当成真实 Telegram 体验证据。

## Run 元信息

| 字段 | 值 |
|---|---|
| Run ID | |
| 日期 | |
| AICO commit / branch | |
| Data-Agent 项目路径 | |
| IM 通道 | |
| Claude / Codex 版本 | |
| 人类评分人 | |
| 证据目录 | |

## 强制失败条件

只要任何一项为 Yes,本轮 benchmark 就不能算通过,即使数字分看起来不低。

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
| 启动和 project office 易理解 | 5 | | 看 `/project`、`/team`、启动摩擦 |
| Goal Brief 能把人类目标转成清晰范围和验收 | 6 | | 看 `/goal` 输出、owner 和 acceptance |
| 多 agent 分工真实,不是装饰 | 7 | | 看 lead / challenger / tester / reviewer 的任务链 |
| 保护人类注意力 | 6 | | 是否只打扰审批、取舍、主观验收 |
| 老板缺席恢复有效 | 8 | | 看 `/overnight`、`/morning`、`/inbox` 第一屏 |
| 可追溯和审计可用 | 6 | | 看 `/task`、`/view`、`/why`、audit/state |
| 风险和审批行为可信 | 5 | | 安全本地任务能推进,风险任务会暂停 |
| 中断和失败恢复可理解 | 4 | | 看 `/interrupt`、failed task handoff |
| 整体管理感 | 3 | | 是否像在管理一个真实团队 |

AICO 小计:`__/50`

## Data-Agent 产品质量:50 分

| 类目 | 分值 | 得分 | 证据 / 备注 |
|---|---:|---:|---|
| 新用户 quickstart 可运行 | 5 | | 命令或 UI 路径 |
| 样例企业数据足够真实 | 5 | | orders、收入、客户、广告、库存、退款 |
| 语义层明确且可维护 | 8 | | metrics、dimensions、entities、source authority |
| 回答包含 SQL 或确定性计算证据 | 8 | | 三条人工问题 + eval |
| 歧义处理安全 | 5 | | 不猜,会追问 |
| Golden eval 覆盖和通过率 | 8 | | 20 条 eval 结果 |
| 测试和工程质量 | 5 | | unit / integration tests、模块边界 |
| 安全、隐私、数据处理 | 3 | | 无敏感样例泄露,限制清楚 |
| 产品有用性和继续迭代意愿 | 3 | | 人类判断 |

Data-Agent 小计:`__/50`

## 总分

| 区域 | 得分 |
|---|---:|
| AICO 编排 | |
| Data-Agent 产品 | |
| 总分 | |

解释:

- `90-100`:强 dogfood 证明。
- `75-89`:循环有用,但仍要补弱项。
- `60-74`:有潜力,但还不够有说服力。
- `<60`:本轮 benchmark 失败。

## 人类验收问题

用自然语言回答:

1. 我不翻原始聊天记录,能不能看懂 AICO 进展?
2. AICO 有没有像真实团队一样使用 Claude / Codex 和角色分工?
3. AICO 是否只在确实需要我时打扰我?
4. 我不读源码,能不能使用产出的 Data-Agent?
5. 我是否愿意基于这个 Data-Agent 继续做 v2?
6. 下次重跑前,AICO 最应该修的三个 UX 问题是什么?
7. 下次重跑前,Data-Agent 产品最应该修的三个问题是什么?

## v2 对比

做 `data-agent-v2` 时复制上一轮分数:

| 指标 | v1 | v2 | Delta |
|---|---:|---:|---:|
| AICO 编排 | | | |
| Data-Agent 产品 | | | |
| 总分 | | | |
| Blocking fail conditions | | | |

v2 至少满足以下任一项才算 AICO 真的变强:

- 总分提升 10 分以上。
- 修掉一个阻塞性的 AICO 类问题,且总分不倒退。
