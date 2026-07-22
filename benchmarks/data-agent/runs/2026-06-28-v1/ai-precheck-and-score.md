# AI 预检与建议打分

这份文件由 Codex 代做人类非必要工作:客观验证、证据整理、UX/审美初评和建议分。它不是最终 human scorecard。

## 本轮 AI 已完成

- 复验 Data-Agent golden eval:`20/20 passed`。
- 复验 targeted tests:`7 passed`。
- 复验两条核心 CLI 问题:
  - “本月华东区收入为什么下降？”
  - “广告 ROAS 低是哪个渠道拖累的？”
- 检查 `/view` local snapshot HTML。
- 中文化评分卡、评分说明、AICO evidence、挑刺草稿、SOP 和 eval 证据。
- 整理人类剩余动作到 `human-remaining-actions.md`。

## AI 可代判的事实

| 项 | 结论 |
|---|---|
| Data-Agent 是否能跑 | 能跑。 |
| Golden eval | 20/20。 |
| Targeted tests | 7/7。 |
| 三条业务问题 | 已有 evidence / calculation / SQL-like trace / follow-up。 |
| 样例数据是否冒充真实客户数据 | 没有,文档说明是 synthetic benchmark data。 |
| 是否有真实 Telegram baseline | 没有。 |
| local injected baseline 是否可用 | 可作为命令合同证据,不能作为真实 Telegram UX 证据。 |
| `/view` 快照是否有价值 | 价值有限,当前 snapshot 显示 0 recent events / 0 experiences / 0 facts。 |

## UX / 审美初评

### Telegram / IM

真实 Telegram transcript 缺失,所以不能评价手机端第一屏真实体感。当前只能评价 local injected transcript:

- 优点:命令链完整,能看到 project office、team、goal、overnight、morning、inbox、view。
- 缺点:文本仍偏工程化,对老板来说信息密度高;`/task data-age` 这种短 id 可用但不够自然。
- 评分建议:没有真实 Telegram 前,不要给高分。

### `/view` HTML snapshot

当前 local snapshot 的视觉基础是可读的:深色背景、卡片、命令按钮、移动宽度 720px 内约束都还算干净。

但作为老板接手面板,它现在不合格:

- boss brief 显示 `0 recent events`、`0 experiences`、`0 facts`。
- Latest 是 `No events yet`,无法解释刚才的 baseline 发生了什么。
- trace details 和 memory 都为空。
- 这说明 `/view` 在 local injected baseline 中没有接到足够状态数据,不应给 traceability 高分。

### Data-Agent CLI

- 优点:输出结构稳定,包含 intent、answer、evidence、calculation、SQL、follow-up questions。
- 缺点:英文标签和中文回答混排;对中文用户还不够自然。
- 缺点:没有 Web UI,产品体验偏 benchmark / developer tool。

## 建议分

这是 AI 建议分,供人类参考:

| 区域 | 建议分 | 理由 |
|---|---:|---|
| AICO 编排 | 8/50 | local injected baseline 比最初挑刺稿多了一点命令合同证据,但真实 Telegram 缺失是硬伤。 |
| Data-Agent 产品 | 38/50 | 能跑、有 eval、有语义层、有证据,但样例小、CLI-only、非生产级。 |
| 总分 | 46/100 | 这是一个有用的 benchmark scaffold,不是成功的 AICO real-IM baseline。 |

如果你只承认真实 Telegram 证据,AICO 编排可按挑刺草稿的 `4/50` 处理。

## 不建议人类再花时间做的事

- 不需要重新读全部源码。
- 不需要重新整理样例数据模型。
- 不需要重新跑所有测试。
- 不需要手动审查 local injected transcript 的每一行;看摘要即可。
- 不需要给英文文档做翻译;已中文化关键评分材料。

## 仍必须由人类决定

- 是否接受 “真实 Telegram 缺失” 导致 AICO 编排低分。
- Data-Agent 的样例数据是否足够接近你心中的“企业级”。
- 你是否愿意基于这个产品继续做 v2。
- 下一轮先修 AICO 体验,还是先扩 Data-Agent 产品能力。
