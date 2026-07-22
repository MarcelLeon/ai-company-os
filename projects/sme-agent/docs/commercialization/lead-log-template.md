# Lead log template

Use this file as the first-stage CRM. Copy the tables into a spreadsheet or
keep them as Markdown until volume becomes too high.

## Daily lead log

| lead_id | date | source | keyword | platform | pain | available_fields | score | state | next_action | paid_status | case_permission | notes |
|---|---|---|---|---|---|---|---:|---|---|---|---|---|
| L-001 | 2026-07-07 | Xiaohongshu | 两场对比 | 快手 | 6/19 比 6/18 差 | 场次表、订单支付表 | 5 | FIELD_TRIAGE | Ask for field screenshots | 199_intent | no | Example row |

## State values

Use one of these exact values:

- `AWARE`
- `COMMENTED`
- `DM_STARTED`
- `WECHAT_ADDED`
- `FIELD_TRIAGE`
- `QUALIFIED`
- `PAID_MINI`
- `PAID_STANDARD`
- `NURTURE`
- `REJECTED`

## Score rules

| Score | Lead meaning | Required next action |
|---:|---|---|
| 5 | Has concrete question, exportable data, and paid intent | Push 199 or 699 |
| 4 | Has pain and data, but needs trust | Offer field triage and sample report |
| 3 | Has pain but data unclear | Ask for table headers |
| 2 | Interested but no urgent question | Put into nurture sequence |
| 1 | Wants generic free advice | Send one framework, no long consult |
| 0 | Bad fit, unsafe data, or guarantee request | Politely close |

## Daily summary

Fill this at the end of each day.

```text
Date:
Published content:
Post link:

Counts:
- Comments:
- DMs:
- WeChat adds:
- Field submissions:
- 199 intents:
- 199 paid:
- 699 intents:
- 699 paid:

Best signal:

Worst blocker:

Top missing field:

Tomorrow's action:
```

### Actual summary — 2026-07-07

```text
Date: 2026-07-07
Published content: 这场直播比上一场差，不一定是没人买
Post link: desktop web blocked; Creator Center note id 6a4cba32000000001603fd2f

Counts:
- Views: 3
- Comments: 0
- DMs: 0 observed
- WeChat adds: 0 observed
- Field submissions: 0
- 199 intents: 0
- 199 paid: 0
- 699 intents: 0
- 699 paid: 0

Best signal:
- Review passed and the note is visible in Creator Center.

Worst blocker:
- Desktop web cannot open the public note/comment surface; first comment needs Xiaohongshu App or another available comment entry.

Top missing field:
- No user fields yet.

Tomorrow's action:
- Re-check metrics, add the prepared first comment through App if still not available on desktop, and log any comments/DMs/WeChat adds.
```

### Actual summary — 2026-07-08 10:00

```text
Date: 2026-07-08 10:00
Published content: 这场直播比上一场差，不一定是没人买
Post link: desktop web still blocked; Creator Center note id 6a4cba32000000001603fd2f

Counts:
- Views: 10
- Comments: 0
- DMs: not exposed in checked Creator Center note-management surface
- WeChat adds: 0 observed
- Field submissions: 0
- 199 intents: 0
- 199 paid: 0
- 699 intents: 0
- 699 paid: 0

Best signal:
- The post picked up 7 additional views since the post-review baseline.

Worst blocker:
- Desktop web still cannot open the public note/comment surface; first comment needs Xiaohongshu App or another available comment entry.

Top missing field:
- No user fields yet.

Tomorrow's action:
- Keep the heartbeat metric check active; add the prepared first comment via App; prepare the second post if the next check still has 0 engagement.
```

### Actual summary — 2026-07-09 10:00

```text
Date: 2026-07-09 10:00
Published content: 这场直播比上一场差，不一定是没人买
Post link: desktop web still blocked; Creator Center note id 6a4cba32000000001603fd2f

Counts:
- Views: 10
- Comments: 0
- DMs: not exposed in checked Creator Center note-management surface
- WeChat adds: 0 observed
- Field submissions: 0
- 199 intents: 0
- 199 paid: 0
- 699 intents: 0
- 699 paid: 0

Best signal:
- No new lead signal; the useful signal is that passive distribution stalled.

Worst blocker:
- Desktop web still cannot open the public note/comment surface; first comment needs Xiaohongshu App or another available comment entry.

Top missing field:
- No user fields yet.

Tomorrow's action:
- Add the prepared first comment via App and prepare the second Xiaohongshu post instead of only waiting for this note to recover.
```

## Objection log

| date | objection | lead_score | response_used | should_be_content | product_implication |
|---|---|---:|---|---|---|
| 2026-07-07 | 不知道怎么导出场次表 | 4 | Field checklist | yes | Need export tutorial |

## Missing-field log

| date | missing_field | why_it_matters | affected_offer | follow_up |
|---|---|---|---|---|
| 2026-07-07 | 支付金额 | Needed for paid GMV, GPM, AOV | 199 mini diagnosis | Ask for payment export |

## Case candidate log

Only add anonymized cases. Do not include names, phone numbers, addresses,
order IDs, or raw customer data.

| case_id | source_lead_id | pattern | evidence_shape | permission_status | reusable_angle |
|---|---|---|---|---|---|
| C-001 | L-001 | 订单数没少但支付 GMV 下降 | SKU drag + GPM delta | requested | 两场对比 |
