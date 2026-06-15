# Launch Playbook — AI Company OS

> 老板私房口袋里的"上线 GitHub 通往 1k–10k star"作战清单。
> 不复制粘贴这一套,star 增长靠运气;按这套依次走,90 天内做到 500–2k star 是合理预期。

---

## 0. 前置假设

- 仓库已经处于 **可被陌生开发者 30 秒看懂** 的状态
  (no-token demo + README 首屏 + How-it-compares 表格)。✅ README 文案、no-token demo 和
  README GIF 已完成;GIF 首帧是 IM 产品画面,并展示 `/morning` + `/view`。
- `LICENSE` / `CONTRIBUTING.md` / `SECURITY.md` / `CODE_OF_CONDUCT.md` /
  `.github/PULL_REQUEST_TEMPLATE.md` / good-first-issue 模板齐全。✅ 已完成
- CI workflow 和徽章已配置;最新 pushed `main` 需要在发布前重新确认 CI 绿。当前未提交变更只能用本地
  gate 证明,不能替代 push 后的 GitHub Actions。
- README 有 1 行定位、How-it-compares 表格和 Star History chart。✅ 已完成
- 仓库 GitHub 页 description / topics / social preview 配齐并在 public 前复核(详见
  [`docs/human/github-publication.md`](../human/github-publication.md))。⚠️ social preview PNG 已生成,
  仍需要仓库 owner 在 UI 中最终上传 / 确认

如果上面任何一项是 ❌,**先回去把它做完**。提前点火只会浪费弹药。

---

## 1. 上线日 D0 — 24 小时关键窗口

### 一定要在同一天做的事

- 09:00 本地 — 切到 `main` 创建 `v0.1.0` 标签 + GitHub Release(release notes 见 §5)。
- 09:30 本地 — 把仓库的 GitHub UI Description / Topics / Social Preview 检查一遍。
- 10:00 美东 / 22:00 北京 — Show HN 发帖(模板见 §2)。
- 10:00 美东之后立刻 — 在 r/LocalLLaMA、r/programming、r/ChatGPTCoding、r/Anthropic
  各发一帖(模板见 §3),内容互不重复。
- 同一时间窗 — 在 X / Twitter、Hacker News 之外的 Bluesky、LinkedIn、Mastodon、
  V2EX、Lobste.rs 各发 1 条(模板见 §4)。
- 全天值守评论区,每条评论 30 分钟内回复。
- D0 结束前 — 写 dev.to / 知乎 / 少数派 长文(模板见 §6),时间留 D1 也行,但不能拖。

### 一定 **不要** 做的事

- 不要在 24 小时内做大功能改动。bug fix 和文档可以,新特性会让 README 与 Show HN 描述
  不一致。
- 不要在评论区上对线。任何"和 X 比怎么样" "这不就是 Y 吗"的评论都用三段式回复:
  (a) 承认相似点 (b) 解释 wedge 的不同 (c) 给具体证据链接。
- 不要在多个平台同一时间贴一模一样的标题。HN / Reddit / Twitter / 公众号都重写一遍。

---

## 2. Hacker News — Show HN 模板

> HN 是 1k → 10k star 路径上 **回报最高且最难复刻** 的杠杆。**只发一次,失败别再发同主题**。

**标题(60 字符以内)**:
```
Show HN: AICO – Run your local AI coding agents like a remote team from Telegram
```

备选标题(为不同类型读者各准备一条,A/B 用):
- `Show HN: I turned Claude Code, Codex, and Cursor into a remote team I can manage from my phone`
- `Show HN: An IM-first orchestration layer for the AI CLIs already on your laptop`
- `Show HN: AI Company OS – approval, audit, and morning handoff for local AI agents`

**首条评论(必须由作者本人在发帖后 1 分钟内贴上)**:

```
Author here. The original itch was simple: I have Claude Code and Codex
running locally, but the moment I leave the desk they stop being useful.
A long task either dies when the laptop sleeps, or runs unsupervised
with no real approval or audit boundary.

AICO is a thin orchestration layer that turns those CLIs into a project
team I can manage from Telegram. There are appointments (PM, tester,
reviewer, implementer), shared project memory, an /approve gate before
file/shell writes, an audit log, /interrupt for stuck tasks, /overnight
for offline delegation, and /morning for the report when I wake up.

Things I made non-negotiable:
- No `if tool == "claude_code"` in core. Every CLI is a plugin (AIAdapter).
- Approval boundary lives in the orchestrator, not the adapter — Codex
  cannot be tricked into shell_exec just because the prompt looks safe.
- Append-only JSONL + SQLite means restarts and audits actually work.

There's a 30-second no-token demo that shows the whole flow with fake
adapters (deterministic, no Telegram bot, no LLM spend):

    git clone https://github.com/MarcelLeon/ai-company-os.git
    cd ai-company-os
    env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python 3.11 \
        aico-release-room-demo

Happy to answer anything about the design tradeoffs, especially:
- why I refused to make this a chat UI / web app
- how the Adapter / Channel / TaskBus boundary held up across 6 CLIs
- why "absence-first" turned out to be a much sharper product wedge than
  "multi-agent" once I dogfooded it for 3 months
```

**评论应对剧本**:
- "How is this different from CrewAI / AutoGen / LangGraph?"
  → 回 wedge:他们做 agent **构建** 框架;AICO 做 agent **运营** 层。我加一张
  README 里的 How-it-compares 表格当链接。
- "Why Telegram?"
  → 因为离开电脑的常用 IM 是手机 IM。Feishu(飞书)第一片 channel slice 也已合入,
  Slack/Discord 是欢迎贡献的方向。
- "Approval gate doesn't really stop a malicious agent."
  → 同意。AICO 是 control layer,不是 sandbox。SECURITY.md 写明了边界;
  对真实 sandbox 的需求是单独的工程。
- "Looks heavy. I just want one agent."
  → README 的"For Personal Developers"段落正是写给你的:如果你只想坐在电脑前用一个
  agent,AICO 太重。

**绝对不要**:
- 不要在标题加 emoji。
- 不要发"我刚发布了 1.0!"——HN 用户对版本号不敏感,但对"AICO orchestrates X without Y"
  这种结构敏感。
- 不要在 12 小时内连续发多次。HN 反作弊会处理。

---

## 3. Reddit — 4 个子版位的差异化模板

### r/LocalLLaMA

**标题**:`I built a layer that turns my local Claude Code + Codex + Cursor into a team I can manage from Telegram (open source)`

**正文**:
```
Long-running local agents are great until you walk away from the laptop.
I built AI Company OS (AICO) to fix that for myself — it sits in front of
the AI CLIs you already have (Claude Code, Codex, Cursor, Gemini, Trae,
CodeFlicker, or anything that streams to stdout) and gives them a real
team workflow:

- Roles: PM, implementer, tester, reviewer, release manager
- /approve gate before any file write or shell exec, from your phone
- /interrupt to kill a stuck task
- /overnight to leave work + /morning to read the handoff
- Append-only memory (JSONL) so context survives restarts
- 100% local; no data leaves your machine unless your CLI does

Adapter contract is one Protocol — adding your own CLI is a single file.
There's a no-token demo so you can see the whole flow in 30 seconds.

Not a chat UI, not a sandbox, not a frontier-model wrapper. Just a thin
operating layer that makes the agents you have manageable like a team.

GitHub: https://github.com/MarcelLeon/ai-company-os
Demo (no token): one shell command, see README

Curious if anyone here has a similar pain. What's the longest unattended
task you've trusted a local agent with so far?
```

### r/programming

**标题**:`How I designed a plugin architecture for local AI CLIs (Claude Code / Codex / Cursor) that survives 18 months of Anthropic + OpenAI breaking changes`

**正文**(技术导向,讲架构而不是产品功能):
```
Three architectural rules I made non-negotiable when building AI Company
OS, after watching enough "if tool == 'claude_code'" code rot:

1. Adapters declare capabilities (read_repo / code_edit / shell_exec /
   destructive). The orchestrator never special-cases a vendor.
2. Approval policy lives in the orchestrator, with risk classification
   driven from the prompt — not the adapter. This means a read-only
   reviewer can safely receive context that mentions `git push` without
   getting auto-rejected as a shell command.
3. State (tasks, audit, memory) is append-only on disk; restart and
   resume are first-class. Mocked subprocesses in tests; never spin up a
   real Claude CLI.

The trade-offs and where the model strained are documented in
docs/decisions/ (37 ADRs so far). The interesting one is ADR-0011 on
why the Project Assignment Layer binds prompts to *appointments*, not
to agents.

Code is MIT, Python 3.11+, full mypy strict.

https://github.com/MarcelLeon/ai-company-os
```

### r/ChatGPTCoding

**标题**:`Open-source: I treat my local agents (Claude Code + Codex + Cursor) like employees, with appointments, approvals, and morning reports`

(产品向、生活化语气;少 jargon、多场景描述。)

### r/Anthropic

**标题**:`Open-source orchestration that lets Claude Code keep working after I close the laptop, with /approve from Telegram`

(强调与 Claude Code 的契合,引用 ADR-0007 capability boundary。)

---

## 4. 短社交模板

### X / Twitter

**主推贴**:
```
I built a thin layer that turns my local AI coding agents
(Claude Code, Codex, Cursor, Gemini…) into a remote team I can manage
from Telegram.

Roles. Project memory. /approve before any write. /overnight when I'm
asleep. /morning when I wake up.

Open source, MIT, no-token demo:
https://github.com/MarcelLeon/ai-company-os
```

**线程跟帖**(每条独立成立、不依赖前一条):
- "Why IM-first instead of a web UI? Because the moment I'm at the
  laptop I don't need AICO. The moment I'm not, every existing tool
  fails."
- "The wedge is Adapter+Channel+Approval, not 'multi-agent'. Multi-agent
  is a side effect, not the product."
- "Plugin architecture — `if tool == 'claude_code'` is a banned pattern.
  Every CLI implements one Protocol, registered via config."
- "Audit log is append-only JSONL. Boring on purpose. Recovery and
  rollback get easier in proportion to how boring storage is."

### LinkedIn

更职业语气;强调"远程工作 / absence-first / 团队管理"。

### Bluesky / Mastodon

把 Twitter 主推贴重发,加上一行"为什么不是另一个 chat 框架"。

### V2EX / 少数派 / 知乎

中文向,长文优先。把 §6 的中文长文摘要贴出来,附 GitHub 链接。

---

## 5. v0.1.0 GitHub Release 模板

```
# AI Company OS v0.1.0 — Public Launch

The first public, dogfooded release of AICO.

## What's in 0.1.0

- IM-first orchestration: Telegram primary, Feishu (text + webhook) MVP
- Adapters: Claude Code (full), Codex (read-only by default), Cursor,
  CodeFlicker, Trae, Gemini (all opt-in, all under the same approval
  matrix)
- Project office: /project, /team, /roles, /appoint, /lead, /ask,
  /brief, /risks, /blockers, /next, /daily, /weekly
- Safety / ops: /approve, /reject, /interrupt, /tasks, /task, /metrics,
  /audit, /undo, /why, /timeline, /rollback (lead-only)
- Memory: A2A memory fabric, /remember, /recall, /forget,
  /experience, semantic+graph retrieval, candidate→active workflow
- Offline delegation: /overnight, /morning, /inbox, /dream, Outcome
  Grader, /goal Goal Brief
- aico-view: read-only mobile web + IM-delivered HTML snapshot
- Restart-aware state: SQLite task store + JSONL audit + JSONL memory
- 433 unit tests, mypy strict, ruff, MIT license

## What this release explicitly does NOT do

- It does not run a sandbox. AICO sits *in front of* local CLIs.
- It does not embed an LLM. You bring your own Claude / Codex / Cursor.
- It is not a chat UI. The terminal CLI is for ops, not for everyday use.

## Try it in 30 seconds, no tokens

    git clone https://github.com/MarcelLeon/ai-company-os.git
    cd ai-company-os
    env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python 3.11 \
        aico-release-room-demo

## What's next

See STATUS.md and docs/architecture/boss-first-grounding.md.

## Star history

If AICO solves a real pain for you, star helps; if it doesn't, please
open an issue describing what you wanted instead — that's more useful.
```

---

## 6. dev.to / 知乎 / 个人博客 长文

**标题候选**:
- "Treating my local AI coding agents like employees, not chatbots"
- "Why I built an absence-first orchestration layer for Claude Code & Codex"
- "用 IM 远程指挥 6 个本地 AI CLI:我做了什么,以及为什么不是另一个 chat 框架"

**结构(英文 1500–2200 字)**:

1. The pain — 一段亲历:你睡了,Claude 半夜跑完了一个任务,但你不知道它跑成了
   还是失败了,要回到电脑前才能看出来。
2. The bet — agent 开发者不缺更聪明的 agent,缺一个能远程操作 agent 的薄层。
3. The wedge — Adapter / Channel / Approval / Audit / Memory / Task。每一项 1 段。
4. What I refused to add — chat UI、frontier model、sandbox、generic agent framework。
5. The 18-month dogfood — 我自己每天用它干自己的 OSS。
6. Architecture in 5 boundaries — 列 5 条契约,链接到 ADR。
7. What surprised me — absence-first 比 multi-agent 锐利得多。
8. What I want from you — 不是 star,是开 issue 告诉我你的真实场景。

---

## 7. 第 2 周到第 4 周 — 维持声量

- D+3:把 HN / Reddit 收到的高赞反馈写成 ROADMAP issue,在 README 顶部链接,展示
  "我在听"。
- D+5:发 Show HN 之后第一周的复盘短文,"这一周我学到了什么"。HN 用户喜欢这种诚意。
- D+7:发布第一个由社区贡献的 PR(挑选最容易的 good-first-issue 推一推)。
- D+10:在 r/Python、r/devops 二度宣传(从工程视角写新角度)。
- D+14:发布 v0.2.0,**不要** 在传播包没回血时压新版本。
- D+21:在 awesome-list(awesome-claude / awesome-llm-apps / awesome-ai-agents)
  各开一个 PR 把自己加进去。
- D+30:写第一份"用户故事"——找 3 个真实使用者短访谈,合成一篇博客 + Twitter 线程。
- D+45:第一次 livestream / 录屏(15 分钟,不要更长)。
- D+60:Hacker News Ask HN 复活——以"我做了 X,这两个月我学到了 Y"形式 follow-up。
- D+90:总结 90 天数据(star / 来源 / issue / PR / 用户类型),决定下一步聚焦哪个用户。

---

## 8. 反指标 / 不要走的路

- **不要花钱买推广**。star 数高但 issue 全空,reviewer 一眼看穿。
- **不要追求 1 周 1k**。这条路径有的是,但留存接近 0。AICO 想要长期社区,不要烟花。
- **不要每周改 README hero**。新读者看到不一致的产品定位会跑。
- **不要在传播期合任何降低质量的 PR**——哪怕来自第一个外部贡献者。先在 issue 里
  做完整 review,引导他改对了再合。
- **不要 ChatGPT 化你自己的 issue 回复**。社区一眼看出来,信任直接归零。

---

## 9. 老板缺席护栏

> 这是 AICO 项目本身的产品价值,也应当应用到你的 launch ops 上:

- 每天 09:00 跑一次 `aico-glance`,看昨晚有没有失败 / 待审批的 PR / Issue。
- 关键评论决策走 `/approve`(自己的 Telegram)— 不是因为你需要 approve,而是因为你
  会留下 audit。
- 24 小时之内不能立即决定的传播动作,标记为 `BLOCKERS.md` 候选,而不是仓促执行。

---

## 10. 数据看板

每周日记录:

| 周 | star | fork | issue 新开 | issue 关闭 | PR 收到 | PR 合并 | HN/Reddit 来源占比 | active dau |
|---|---|---|---|---|---|---|---|---|
| W1 | | | | | | | | |
| W2 | | | | | | | | |
| W4 | | | | | | | | |
| W8 | | | | | | | | |
| W12 | | | | | | | | |

低于预期 50% 时,**不要** 加大宣发,而是 **回到产品**:
读 issue 真心话 → 找 1 个最常见痛点 → 修掉 → 重新组织一次小规模发布。

---

## 11. 谁不该做这件事

如果你在三个月内不能持续投入到这个项目,就 **不要** 启动 launch playbook。star
膨胀但没人维护,比一直安静有更高的长期负面影响。

如果你能持续投入,而且 README 真的让一个陌生人 30 秒看懂你解决的问题,出击。
