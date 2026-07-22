# 人类剩余动作

目标:把人类要做的事压到最少。

## 你现在只需要做三件事

### 1. 决定 AICO 编排是否按缺真实 Telegram 证据低分

当前事实:

- 真实 Telegram baseline 没跑通。
- local injected baseline 跑通,但不能替代 Telegram UX。
- AI 挑刺建议:AICO 4/50。
- AI 预检建议:如果考虑 local injected command-contract evidence,AICO 可给 8/50;如果只认真实 Telegram,给 4/50。

你只需要选一个:

- 严格口径:AICO `4/50`。
- 宽松口径:AICO `8/50`。
- 你亲自补跑真实 Telegram 后再评分。

### 2. 给 Data-Agent 产品半边确认分

AI 建议:Data-Agent `38/50`。

你只需要判断:

- 样例数据小,但是否足够作为 v1 benchmark?
- CLI-only 是否能接受?
- 你愿不愿意基于它做 v2?

如果懒得细改,可以直接用 `38/50` 作为产品分。

### 3. 填 `human-scorecard.md`

打开:

`benchmarks/data-agent/runs/2026-06-28-v1/human-scorecard.md`

最小填写方式:

- Mandatory fail conditions。
- AICO 小计。
- Data-Agent 小计。
- 三条 AICO 主要问题。
- 三条 Data-Agent 主要问题。

## 推荐结论模板

可以直接写:

```text
本轮 data-agent-v1 benchmark 产品侧成立,但 AICO 真实 Telegram 编排侧不成立。
AICO orchestration 低分的主要原因是真实 /morning、/inbox、/task、/view transcript 缺失。
local injected baseline 只能证明命令合同,不能证明老板在 IM 上真的可接手。
下一轮先修真实 IM baseline 自动化和 /view 状态注入,再做 data-agent-v2。
```

## 后续流程

1. 先把本轮 scorecard 填完。
2. 如果 AICO 低于 30/50,不要立刻做 `data-agent-v2`。
3. 先修 AICO:
   - Telegram 真实发送和采证。
   - `/morning` 第一屏。
   - `/inbox` 第一屏。
   - `/task` 可追溯。
   - `/view` 不为空且能说明发生了什么。
4. 修完后重跑同样的 command sequence。
5. 再让 AICO 做 `data-agent-v2`。
6. 用同一张 scorecard 对比 v1 / v2。
