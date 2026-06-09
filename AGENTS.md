# AGENTS.md

> 你好。如果你是一个 LLM/Agent(Claude Code、Codex、Cursor、本地 CLI 等),这个文件是你接手本项目的**唯一正确入口**。
> 不要从 README.md 开始 — 那是给人看的。

---

## 你是谁,你在干什么

你正在协助开发一个名为 **AI Company OS** 的项目。这个项目的目标是把开发者电脑上散落的 AI 工具(Claude Code / Codex / OpenClaw / 公司内部 CLI)统一编排成一个"虚拟公司",通过 IM(Telegram 等)远程指挥。

你接手这个项目的时候,**很可能不是第一次有 AI 干这个**。前面可能有几十轮 AI 思考和修改的痕迹。你的任务是**站在前人肩膀上继续推进**,而不是推翻重来。

---

## 强制阅读顺序(不要跳)

请严格按这个顺序读完,每一步读完后再读下一步。**跳过任何一步都会导致你做出错误决策**。

### Step 1 — 北极星(2 分钟)
读 [`NORTH_STAR.md`](NORTH_STAR.md)
**目的**:知道这个项目存在的理由。后面所有决策都要回到这三句话。

### Step 2 — 当前状态(2 分钟)
读 [`STATUS.md`](STATUS.md)
**目的**:知道现在在哪个阶段、上一轮做了什么、下一轮该做什么。

### Step 3 — 思考轮次(5 分钟)
读 [`docs/journal/ROUNDS.md`](docs/journal/ROUNDS.md)
**目的**:知道前面的 AI 们想过什么、否决过什么、为什么否决。**这能避免你重新发明被否决过的方案**。

### Step 4 — 踩坑录(5 分钟)
读 [`docs/journal/PITFALLS.md`](docs/journal/PITFALLS.md)
**目的**:知道哪些坑已经踩过了、状态如何。**踩同一个坑两次是不可接受的**。

### Step 5 — 卡点难题(2 分钟)
读 [`docs/journal/BLOCKERS.md`](docs/journal/BLOCKERS.md)
**目的**:知道当前还没解决的卡点。如果你能解决其中任何一个,这是最高优先级。

### Step 6 — 开发规范(必读)
读 [`docs/agent/01-development-workflow.md`](docs/agent/01-development-workflow.md) 和 [`docs/agent/02-coding-standards.md`](docs/agent/02-coding-standards.md)
**目的**:知道"怎么写代码"才会被接受。

### Step 7 — 按需阅读
根据你接到的任务,读对应的指南:
- 写 Java → [`docs/agent/04-java-best-practices.md`](docs/agent/04-java-best-practices.md)
- 写 Python → [`docs/agent/05-python-best-practices.md`](docs/agent/05-python-best-practices.md)
- 写测试 → [`docs/agent/06-testing-guide.md`](docs/agent/06-testing-guide.md)
- 涉及部署 → [`docs/agent/07-deployment-guide.md`](docs/agent/07-deployment-guide.md)
- 涉及 GitHub 发布 / public / tag / Release → [`docs/agent/09-github-release-ops.md`](docs/agent/09-github-release-ops.md)
- 抽象设计 → [`docs/agent/03-design-patterns.md`](docs/agent/03-design-patterns.md)

---

## 你必须遵守的硬规则(违反则你的工作会被丢弃)

1. **回到北极星**:任何决策无法用 [`NORTH_STAR.md`](NORTH_STAR.md) 三句话之一解释,就不要做。
2. **单类 < 500 行,单方法 < 100 行**:超过就拆。这是物理硬约束,不是建议。
3. **面向接口编程**:任何 AI 工具适配器、IM 通道、存储后端都必须有接口抽象,核心逻辑只依赖接口。
4. **可插拔**:新增能力 = 新增插件,不是修改核心。
5. **不要在没读 `PITFALLS.md` 的情况下写代码**:大概率你想做的事别人踩过坑了。
6. **每完成一轮工作,必须更新 `STATUS.md` 和 `docs/journal/ROUNDS.md`**:见 [`docs/agent/08-self-update-protocol.md`](docs/agent/08-self-update-protocol.md)
7. **遇到卡点,写到 `BLOCKERS.md` 里,不要硬解**:把问题留给下一轮或人类比硬塞 hack 代码好。
8. **代码必须有单测**:见 [`docs/agent/06-testing-guide.md`](docs/agent/06-testing-guide.md)
9. **不要扩大任务范围**:接到的任务是 A,就做 A,不要顺手改 B。顺手改 B 是 PR 难以 review 的元凶。
10. **每次抽象前,先看 [`docs/agent/03-design-patterns.md`](docs/agent/03-design-patterns.md) 的"抽象时机判定"**:过早抽象比晚抽象更糟糕。

---

## 你完成工作前的自检清单

在你结束本轮工作、提交 PR 或交还控制权之前,必须自己回答下面所有问题。**任何一个回答"否"或"不确定",都不能提交**。

- [ ] 我做的事符合 `NORTH_STAR.md` 三句话之一吗?
- [ ] 我有没有在 `PITFALLS.md` 里检查过相关坑?
- [ ] 我新增/修改的类是否都 < 500 行?方法 < 100 行?
- [ ] 我引入的所有外部依赖(AI 工具/IM/存储)是否都通过接口抽象?
- [ ] 我写的代码有单测吗?单测能跑过吗?
- [ ] 我有没有更新 `STATUS.md`(写明本轮做了什么、下一轮建议做什么)?
- [ ] 我有没有更新 `docs/journal/ROUNDS.md`(追加本轮记录)?
- [ ] 如果我遇到卡点,有没有写到 `BLOCKERS.md`?
- [ ] 如果我踩了新坑,有没有写到 `PITFALLS.md`?
- [ ] 如果我做了重要架构决策,有没有写一个 ADR 到 `docs/decisions/`?
- [ ] 如果我做 GitHub 发布相关动作,有没有按 `docs/agent/09-github-release-ops.md` 核对 public / tag / Release / social preview?

---

## 当你不确定时

**不要硬猜,不要伪造**。三种合法的应对:

1. **回到北极星**:用三句话宪法判断方向。
2. **写进 BLOCKERS**:把不确定的问题明确写下来,留给人类或下一轮 AI。
3. **请求人类裁决**:在你的输出里明确说"我需要人类确认 X"。

最糟糕的应对是:猜一个看起来合理的方案,默默实现,把不确定性藏在代码里。这种代码会成为下一轮 AI 的 PITFALLS。

---

## 现在开始

读完上面的所有"强制阅读顺序"之后,再开始动手。如果你接到的任务在 `STATUS.md` 的"下一轮建议"里,优先做那个。
