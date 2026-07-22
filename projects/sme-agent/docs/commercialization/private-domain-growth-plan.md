# Private-domain growth plan

This plan turns the local diagnosis workbench into a sellable service loop.

For the first focused paid-lead campaign, use
[`paid-user-acquisition-campaign.md`](paid-user-acquisition-campaign.md). This
file is the evergreen private-domain model; the campaign file is the
day-by-day Xiaohongshu -> WeChat -> paid diagnosis operating package.

## Offer

Week-one offer:

- `199 RMB`: live-room mini check, one sample export, one-page finding.
- `699 RMB`: standard diagnosis, field mapping, metric report, SKU/session
  attribution, review call or voice-note explanation.
- `1999 RMB`: deep assistant trial, two-week tracking, two-period comparison,
  follow-up questions, and one improvement checklist.

Do not sell it as a fully automatic SaaS yet. Sell it as a human-reviewed AI
business diagnosis.

## Xiaohongshu funnel

Publish content that makes the pain obvious before asking for data.

Post families:

1. `GMV looks fine, but paid GMV is weak`
   - Hook: "直播间 GMV 没差，老板为什么还是觉得不赚钱？"
   - Demo: show paid GMV, refund rate, GPM, and conversion.
   - CTA: "评论/私信 直播诊断，发你字段清单。"
2. `Refund SKU finder`
   - Hook: "退款率高，不要先骂主播，先找哪个 SKU 在退。"
   - Demo: top refund SKU contribution.
   - CTA: "想看你的 SKU，私信 退款。"
3. `Why this session dropped`
   - Hook: "这场比上一场差，不一定是没人买。"
   - Demo: paid orders unchanged, paid GMV dropped, SKU-C/SKU-A/SKU-B dragged.
   - CTA: "私信 两场对比，给你样例表头。"
4. `Missing data is a diagnosis too`
   - Hook: "支付金额为空时，AI 不能装懂。"
   - Demo: show missing-field question instead of fake conclusion.
   - CTA: "私信 字段体检。"

## WeChat conversion

DM script:

```text
我先不让你发完整后台。你只需要准备两张导出：
1. 直播场次表：场次ID、主播、观看人数
2. 订单支付表：场次ID、商品、订单、支付金额、退款金额、匿名买家ID

我会先做字段体检。字段不够不会硬诊断；字段够了再给你一页老板能看懂的报告。
```

Group entry:

```text
欢迎进群。这个群只做中小商家直播/电商经营诊断：
- 不看玄学 GMV
- 先看字段够不够
- 再看支付 GMV、GPM、退款率、转化
- 最后定位到场次、主播、SKU 或缺失字段
```

## Group operating rhythm

Daily:

- Share one anonymized finding: one SKU, one session, one metric.
- Ask one practical question: "你们导出里有没有支付金额？"
- Collect one lead: "愿意试 199 体检的私信我。"

Weekly:

- Pick 3 free field-check examples.
- Convert 1-2 into paid `699` standard diagnosis.
- Ask paid users for permission to publish anonymized before/after findings.

## Product gates before paid delivery

Before charging:

- The workbench can explain pain, data model, entity relationship, and business
  process.
- The workbench can answer "why this session dropped versus last session" with
  deterministic evidence.
- Missing required fields produce questions, not fake conclusions.

After charging:

- Create a customer workspace.
- Save raw inputs locally.
- Save field mapping report.
- Save diagnosis report.
- Save evidence manifest.
- Save redaction checklist.
- Deliver Markdown first; PDF can come later.

## Current entry product

Use the implemented self-serve CSV selection or paste flow in the local
workbench for the 199 RMB field-check/mini-diagnosis offer.

Implemented behavior:

- User uploads/pastes live-session and order/payment data.
- System maps columns.
- If required fields are missing, it shows exact missing-field questions.
- If fields are enough, it runs the governed diagnosis. The bundled week-one
  path also supports two-session comparison.
- It keeps all data local unless the human explicitly chooses to export.

The next product slice is the customer-facing live-commerce workspace runner,
which should persist mapping, evidence, redaction, questions, and the reviewed
delivery draft only after an authorized operator chooses that workflow.
