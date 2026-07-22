# Growth operations playbook

This playbook starts after the first Xiaohongshu post goes live. The goal is to
turn public attention into WeChat relationships, field submissions, paid
diagnoses, anonymized cases, and product iteration.

## Operating thesis

The first post is only the hook. Revenue comes from the follow-up loop:

```text
Public pain content
  -> keyword interaction
  -> WeChat add
  -> private qualification
  -> field triage
  -> 199 RMB mini diagnosis
  -> 699 RMB standard diagnosis
  -> anonymized case
  -> stronger public content
```

Do not optimize for views alone. Optimize for people who can answer three
questions:

1. What business question do they need to explain?
2. What tables can they export?
3. Are they willing to pay for an evidence-backed diagnosis if the fields are
   enough?

## After-post day zero

Run this checklist within the first `24` hours after publishing a post.

```text
[ ] Pin or save the post link in the lead log.
[ ] Prepare the matching keyword reply.
[ ] Reply to every relevant comment with a short public answer.
[ ] Move high-intent users to private chat.
[ ] Move qualified private chats to WeChat 17610788906.
[ ] Ask for fields only, not full sensitive data.
[ ] Score every lead 0-5.
[ ] Record every objection as future content.
[ ] Send 199 mini-diagnosis offer only to score-4/5 leads.
```

Public comment reply style:

```text
这个要先看字段够不够。至少要能关联：场次 ID、支付金额、SKU、退款金额。你可以私信「两场对比」，我发你字段清单。
```

Private DM reply style:

```text
我先不让你发完整后台。你先发字段名就行，我判断能不能诊断。
如果字段够，再建议你做 199 小体检；字段不够，我直接告诉你缺什么。
```

## User state machine

Every lead should live in exactly one state.

| State | Meaning | Next move |
|---|---|---|
| `AWARE` | Saw public content but did not interact | Keep posting pain content |
| `COMMENTED` | Commented keyword or asked a public question | Reply publicly, invite DM |
| `DM_STARTED` | Private chat started | Ask one question and table availability |
| `WECHAT_ADDED` | Added WeChat with remark | Send field-triage script |
| `FIELD_TRIAGE` | Sent field names or redacted sample | Score analyzability |
| `QUALIFIED` | Has pain + data + willingness | Push 199 or 699 |
| `PAID_MINI` | Bought 199 mini diagnosis | Deliver one-page report |
| `PAID_STANDARD` | Bought 699 standard diagnosis | Deliver report + explanation |
| `NURTURE` | Interested but not ready | Weekly case push |
| `REJECTED` | Bad fit or unsafe request | Politely close |

## Push cadence

### Public channels

Xiaohongshu:

- `3-5` posts per week.
- Use one post per pain, not one post per product feature.
- Repeat winning topics with a new example instead of constantly inventing new
  categories.

WeChat Moments:

- `1` short post per day during the first `14` days.
- Mix proof, field education, and open slots.
- Do not make every post a sales pitch.

WeChat group:

- `1-2` useful pushes per day.
- Morning: field self-check.
- Evening: anonymized pattern or open diagnosis slot.

Private chats:

- Reply within `12` hours.
- After field submission, follow up within `24` hours.
- If the user is score `4-5`, do not keep educating forever; ask for the paid
  next step.

### Private nurture sequence

Use this sequence for leads who added WeChat but have not sent fields.

Day 0:

```text
欢迎。你先不用发完整后台，先发字段名就行。我看能不能回答你的问题。
```

Day 1:

```text
我给你一个自查顺序：场次 ID 能否关联订单？订单有没有支付金额？SKU 和退款金额是否齐？这三个够了，很多直播复盘就能先看一版。
```

Day 3:

```text
很多场次下滑不是没人买，而是支付 GMV 或商品结构变了。如果你愿意，我可以先帮你做字段体检，不够就不收诊断费。
```

Day 7:

```text
这周我还留 1-2 个 199 小体检名额，只看一个问题：某场为什么比上一场差。适合有场次表和订单支付表的小团队。
```

## Channel expansion

Do channels in this order. Do not open every channel at once.

### Channel 1: Xiaohongshu

Purpose: pain discovery and first trust.

Best content:

- "这场直播为什么比上一场差"
- "退款率高先找 SKU"
- "支付金额为空时 AI 不能装懂"
- "老板不要只看 GMV"

Primary CTA:

```text
私信关键词，拿字段清单。合适再加微信 17610788906。
```

### Channel 2: WeChat Moments

Purpose: prove that this is an ongoing service, not a one-off post.

Content mix:

- 40% field education.
- 30% anonymized diagnosis pattern.
- 20% open slots or seed-user call.
- 10% behind-the-scenes product progress.

Example:

```text
今天看一个很典型的问题：订单数没少，但支付 GMV 掉了。
这种情况别先判断主播不行，先看高客单 SKU 是否少卖、优惠/退款是否吃掉支付额。
我这周还接 2 个 199 直播诊断小体检，只看字段够不够和一场对比问题。
```

### Channel 3: WeChat group

Purpose: warm leads and reduce repeated explanation.

Do not let the group become a free-consulting room. Use a fixed format:

```text
【问题】一句话业务问题
【平台】抖音/快手/淘宝/其他
【数据】能导出哪些表
【字段】只发字段名或脱敏样例
【希望】字段体检/199 小体检/699 标准诊断
```

### Channel 4: short video / video account

Purpose: reuse the same post as a spoken 60-second explanation.

Script template:

```text
很多老板问我：为什么这场直播比上一场差？
我一般不先看总 GMV。
我先看三个东西：支付 GMV、GPM、SKU 贡献。
如果订单数没少但支付 GMV 掉了，问题往往不是没人买，而是商品结构、支付口径或退款。
想自查的话，先看你有没有场次 ID、支付金额、SKU、退款金额。
字段够，才能诊断；字段不够，AI 不能装懂。
```

### Channel 5: Taobao/Qianniu service listing

Purpose: catch buyers who already have purchasing intent.

Only push after the first `1-3` diagnosis cases, because the listing needs
examples and credibility. Before that, use Xiaohongshu and WeChat to validate
language and objections.

## Conversion scripts

### From field triage to 199

Use when the lead has a concrete question and fields are probably enough.

```text
你的字段能先做一版小体检。

建议不要直接做大报告，先 199 看一个问题：
「这场为什么比上一场差？」

我会交付一页：
1. 支付 GMV/GPM/订单/买家变化；
2. 拖累最大的 SKU；
3. 结论能确定什么；
4. 哪些原因还需要补字段。

如果你觉得这一页有用，再升级 699 标准诊断。
```

### From 199 to 699

Use when the mini report reveals more than one meaningful issue.

```text
这版小体检已经能看出问题不止一个点。

如果继续做 699 标准诊断，我会补：
- 字段映射和口径说明；
- 场次/SKU/主播维度归因；
- 退款和支付链路拆解；
- 一页老板版结论；
- 一段语音解释下一步怎么复盘。

不建议你在字段还不齐时买大单；如果要继续，我会先列清楚还缺哪些字段。
```

### Rejection script

Use when the lead wants a guarantee or has no data.

```text
这个我先不建议你买。

我这边做的是基于字段和证据的经营诊断，不承诺 GMV 增长。
如果没有场次、订单、支付金额、SKU 这些基础字段，现在做结论容易误导。

你可以先把字段整理出来，后面适合了再看。
```

## Content recycling loop

Every user question becomes one of four assets.

| Input | Asset | Example |
|---|---|---|
| Repeated objection | Xiaohongshu post | "为什么我不先收钱，而是先看字段" |
| Missing field | WeChat group education | "支付金额为空为什么不能诊断 GPM" |
| Paid report finding | Case post | "订单数没少，支付 GMV 为什么掉" |
| Bad-fit lead | FAQ | "什么情况不适合做 AI 经营诊断" |

Weekly content review questions:

- Which hook brought the most field submissions?
- Which CTA brought the most WeChat adds?
- Which objection blocked payment most often?
- Which missing field appeared most often?
- Which product feature would reduce manual explanation next week?

## Data and CRM

For the first stage, use a simple local Markdown or spreadsheet log. Required
fields:

Start from [`lead-log-template.md`](lead-log-template.md), then move the same
columns into a spreadsheet only when manual Markdown becomes too slow.

| Field | Meaning |
|---|---|
| `lead_id` | Manual identifier |
| `date` | First interaction date |
| `source` | Xiaohongshu, WeChat Moments, group, referral, other |
| `keyword` | 直播诊断, 两场对比, 退款 SKU, 字段体检, 199 体检 |
| `pain` | One-sentence business question |
| `platform` | Douyin, Kuaishou, Taobao, other |
| `available_fields` | Field/table availability |
| `score` | 0-5 lead score |
| `state` | Current state from the state machine |
| `next_action` | The next single action |
| `paid_status` | none, 199_intent, 199_paid, 699_intent, 699_paid |
| `case_permission` | no, requested, approved |

## Weekly operating review

Run this review every Sunday night.

Use [`weekly-growth-review-template.md`](weekly-growth-review-template.md) as
the copyable review form.

```text
1. Leads
   - How many comments/DMs?
   - How many WeChat adds?
   - How many field submissions?
   - How many paid?

2. Conversion
   - Which post created the best leads?
   - Which script converted best?
   - Where did users hesitate?

3. Product
   - Which fields were missing most often?
   - Which diagnosis question appeared most often?
   - What should the workbench support next?

4. Content
   - Which anonymized pattern can become next week's post?
   - Which objection deserves a dedicated post?

5. Money
   - Revenue this week.
   - Best next paid offer.
   - Whether to push 199, 699, or pause and improve product.
```

## Thirty-day target

Minimum:

- `20` WeChat adds.
- `8` field submissions.
- `3` paid 199 RMB mini diagnoses.
- `1` anonymized case.

Good:

- `60` WeChat adds.
- `20` field submissions.
- `8` paid 199 RMB mini diagnoses.
- `2` paid 699 RMB standard diagnoses.
- `3` anonymized cases.

Great:

- The same three questions repeat across leads.
- The same missing fields repeat across leads.
- One paid user asks for continuous tracking.
- The next product slice becomes obvious from customer behavior, not guessing.
