# 01 — 开发闭环工作流(Agent SOP)

> 本文是 Agent 在本项目里执行任务的标准操作流程。**每一轮工作必须严格遵循**。

---

## 8 步工作闭环

```
[1.接任务] → [2.阅读] → [3.规划] → [4.实现] → [5.测试] → [6.自检] → [7.更新文档] → [8.交接]
                                                              ↑
                                                              └─ 任何步骤遇到卡点
                                                                 → 写到 BLOCKERS.md
                                                                 → 不要硬解
```

---

## Step 1 — 接任务

### 任务来源
- 人类直接指派
- `STATUS.md` 的"下一轮建议"
- `BLOCKERS.md` 中你能解决的卡点

### 接任务时必须明确
- [ ] 任务的输入是什么
- [ ] 任务的产出是什么(代码?文档?决策?)
- [ ] 任务的边界在哪(什么是范围内,什么是范围外)
- [ ] 验收标准是什么

如果任何一项不明确,**先和发起者澄清**,不要靠猜动手。

---

## Step 2 — 阅读

按 [`00-how-to-read-this-repo.md`](00-how-to-read-this-repo.md) 的对应场景读。

**最少阅读量**:
- `STATUS.md` 的最新一轮记录
- `docs/journal/PITFALLS.md` 中与任务关键词相关的条目
- 与代码任务相关的现有代码文件

---

## Step 3 — 规划

### 输出一份规划草稿(写在你的回复里,不入仓)
- 我打算做什么(具体到文件粒度)
- 我打算用什么模式(参考 [`03-design-patterns.md`](03-design-patterns.md))
- 预期改动的代码量
- 是否需要新增依赖
- 风险点

### 规划自检
- [ ] 这个规划对应北极星哪一句?
- [ ] 我有没有过早抽象?(参考"Rule of Three")
- [ ] 我的改动范围有没有蔓延?
- [ ] 是否有更小的版本能验证想法?(MVP 思维)

如果改动比较大(>200 行)或涉及架构,**先把规划写出来等确认,再动手**。

---

## Step 4 — 实现

### 实现纪律
- **小步快跑**:一次一个小变更,不要憋大招
- **接口先行**:写实现前先写接口
- **可运行优先**:每一小步都要能跑能测
- **遵守硬约束**:单类 < 500 行,单方法 < 100 行

### 实现时反复回看
- [ ] 我有没有违反 [`02-coding-standards.md`](02-coding-standards.md)?
- [ ] 我有没有把"易变"封装在 Adapter 内部,核心只依赖接口?

---

## Step 5 — 测试

详见 [`06-testing-guide.md`](06-testing-guide.md)。

### 最低要求
- 单测覆盖核心逻辑(目标 ≥ 80%)
- Adapter / Channel 必有 mock 测试
- 至少 1 个端到端集成测试

### 测试先于提交
- [ ] `mvn test` / `pytest` / `npm test` 全绿
- [ ] 没有跳过的测试(`@Ignore` / `@pytest.mark.skip`)

---

## Step 6 — 自检

执行 [`AGENTS.md`](../../AGENTS.md) 末尾的"完成工作前的自检清单"。

**任何一项"否"都不能进入下一步**。

---

## Step 7 — 更新文档(必做,不可跳过)

这是最容易被跳过、也是最重要的一步。

### 必更新
1. **`STATUS.md`**:
   - 当前轮次 +1
   - 上一轮做了什么(简短描述)
   - 下一轮建议(更新顺序)
   - 进度地图相关项打勾
2. **`docs/journal/ROUNDS.md`**:
   - 追加本轮记录(用模板)
   - **重点写否决方案的理由**

### 视情况更新
3. **`docs/journal/PITFALLS.md`**:踩了新坑就加
4. **`docs/journal/BLOCKERS.md`**:遇到卡点就加,解决了就标 RESOLVED
5. **`docs/decisions/`**:做了重要架构决策就写 ADR
6. **`CHANGELOG.md`**:面向用户的功能变更
7. **`docs/human/daily-ops.md`**:新增了运维命令

详见 [`08-self-update-protocol.md`](08-self-update-protocol.md)。

---

## Step 8 — 交接

### 交接产出
- 一份本轮总结(写在你的最终回复里):
  - 完成了什么
  - 卡在哪里(如有)
  - 下一轮建议优先级
  - 需要人类确认的点(如有)

### 交接质量自检
- [ ] 下一个 Agent 看 `STATUS.md` 能立刻知道下一步做什么吗?
- [ ] 下一个 Agent 看 `ROUNDS.md` 能理解我为什么这么做吗?
- [ ] 我留下的代码在没有我解释的情况下,下一个 Agent 看得懂吗?

---

## 反模式

❌ **没读文档直接写代码**
❌ **写代码不写测试**
❌ **写完代码不更新文档**
❌ **遇到卡点不写 BLOCKERS,选择硬塞 hack**
❌ **任务范围蔓延**
❌ **用 `// TODO` 把不确定性藏在代码里**
❌ **抽象在第 1 个实现样本时就出现**(违反 Rule of Three)

---

## 一个好的工作循环范例

```
[人类]:实现 Telegram Channel Adapter,只需要支持文本消息收发。

[Agent Step 1]:任务边界明确——只做文本,不涉及多媒体、不涉及群组管理。

[Agent Step 2]:读 STATUS.md(Phase 1 MVP)、PITFALLS.md(无相关坑)、ROUNDS Round 1(确认 Phase 1 范围)、architecture/adapter-protocol.md(看 IMChannel 接口定义)

[Agent Step 3 规划]:
- 新建 src/main/java/.../channel/telegram/TelegramChannel.java
- 实现 IMChannel 接口
- 用 Telegram Bot Java SDK
- 单测用 MockBotApi
- 集成测试需要真 Bot Token,放 docs/playbooks/test-telegram.md

[Agent Step 4 实现]:小步提交...

[Agent Step 5 测试]:单测 + 集成测试通过

[Agent Step 6 自检]:全部打勾

[Agent Step 7 文档更新]:
- STATUS.md:Phase 1 进度 +1 项,下一轮建议改为"实现 Claude Code Adapter"
- ROUNDS.md 追加 Round 2 记录:写明为什么选 Bot SDK 而不是裸 HTTP
- PITFALLS.md 新增 P-00X:Telegram Bot 长连接 vs Webhook 选择踩了一个小坑

[Agent Step 8 交接]:
"本轮完成 Telegram Channel Adapter,单测覆盖 87%。下一轮建议实现 Claude Code Adapter,
可以参考 TelegramChannel 的接口实现思路。注意 P-00X 记录的 Webhook 坑。"
```
