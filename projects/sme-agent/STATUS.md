# STATUS.md

**Last updated**: 2026-07-21
**Current round**: Round 22
**Current phase**: Commercialization sprint — merchant-owner delivery acceptance + AICO lead proposal dogfood

## Product boundary

SME Agent is a standalone business product developed by an AICO team. AICO owns project organization, delegation, approval, audit, and handoff. SME Agent owns metadata, knowledge retrieval, skills, tools, agent execution, business memory, context compression, and LLM routing.

## Commercialization boundary

The week-one sellable version is a service-backed AI business diagnosis product, not a fully automatic SaaS. The buyer-facing promise is: human-reviewed AI diagnosis from customer-provided business data, with traceable assumptions and evidence.

## Phase map

| Phase | Outcome | Status |
|---|---|---|
| 0 | Project constitution, alignment loop, AICO team, quality gates | Complete |
| 1 | Governed metadata catalog vertical slice | In progress: local contract complete, real AICO dogfood pending |
| 2 | Commercial offer, data intake, report delivery, Xiaohongshu cold start | In progress |
| 3 | Knowledge ingestion and cited retrieval | Not started |
| 4 | Skill and tool registries with policy enforcement | Not started |
| 5 | Bounded agent loop, memory, and context compression | Not started |
| 6 | Multi-LLM routing, evaluation, and production hardening | Not started |

## Current evidence

- Project office documents and AICO team configuration exist.
- The metadata domain supports typed assets, relations, search, and neighbor lookup.
- A representative revenue question resolves glossary → metric → dimensions/filters → warehouse → entity → knowledge references.
- Relation signatures, version increments, steward approval, source references, ambiguity, and unrelated dimensions are enforced.
- Root CI now runs project tests and an explicit SME Agent strict-mypy step.
- Unit tests cover the first metadata slice.
- Commercial launch documents now define the week-one SKU, LLM/human division, required user inputs, week-one launch plan, Taobao listing draft, customer intake questionnaire, challenge log, and Xiaohongshu content plan.
- Week-one ecommerce delivery slice now has sample CSV data, deterministic CSV loaders, basic revenue/refund/ad/inventory diagnosis rules, Markdown report rendering, and a sample buyer-facing report.
- Default commercial pricing is now fixed for launch assets: 199 RMB intro diagnosis, 699 RMB standard report, and 1999 RMB deep assistant trial.
- Buyer-facing assets now include a premium Taobao/Qianniu listing, visual copy pack, seven complete Xiaohongshu posts, customer project workspace generation, evidence manifest writing, and redaction scanning.
- A library runner now generates a customer workspace, diagnosis draft, evidence manifest, and redaction checklist from CSV paths; the runbook documents the invocation.
- Static SVG listing assets now exist: premium main image, pain-driven main image, and a long detail-page preview. XML parsing and SME tests pass.
- PNG exports now exist for Taobao assets and seven Xiaohongshu covers. A product quality review fixed stale price ranges, low-premium wording, inconsistent labels, and a cover-text overflow.
- Domain templates now define the non-toy business spine for live/content commerce, local services, and performance advertising. The live-commerce template covers industry, seller, content, live room, product, order, payment, GMV, paid GMV, paid orders, paid buyers, AOV, refund rate, GPM, and payment conversion, with sensitive fields and human checks.
- Live-commerce validation now has a closed local loop: Chinese export headers map into the live-commerce template, sample live-session/order exports compute GMV, paid GMV, paid orders, paid buyers, AOV, refund rate, GPM, and payment conversion, and a Markdown report exposes mapping coverage, sensitive fields, findings, and human checks.
- A public-web-derived dogfood fixture now exists. It uses public KuaiLive/OnlineGMV source shapes and aggregate context, stores explicit source caveats, runs through the live-commerce agent, and produces a buyer-readable evidence report without pretending to be real merchant backend data.
- Dogfood deployment and usage are documented as an operator-run local workflow. SME Agent now has a browser workbench but still has no cloud SaaS, buyer authentication, IM product surface, or Taobao/Qianniu plugin UI; delivery remains human-reviewed.
- A local browser workbench now exists at `python -m sme_agent.commercialization.workbench`. It lets the owner choose bundled live-commerce samples, view field mapping, inspect key metrics, read evidence-backed findings, and copy the delivery report. This upgrades dogfooding from library/runbook-only to a product interaction surface.
- The workbench now explains the commercial pain point, sample data model, entity relationships, live-commerce business process, output logic, and post-validation next steps before showing diagnosis output.
- Findings now use deterministic entity attribution instead of generic threshold advice. Refund findings identify the top refund SKU; GPM and conversion findings identify the low-performing live session/category/anchor with view share, paid GMV share, session GPM, and conversion evidence. The report explicitly states when a claim is not LLM guessing.
- The 2026-06-19 week-one sample now acts as a data-quality case: paid orders with blank `支付金额` are rejected with a specific missing-pay-amount message instead of being treated as zero or guessed from order amount.
- Two-session comparison now answers "why did this live room drop versus last time?" for the week-one sample. It shows paid GMV, GPM, order/buyer deltas, SKU drag contributors, and data limits for missing external attribution fields.
- The local workbench now accepts a merchant's own two CSV files through browser file selection or pasted text. Intake stays in the localhost process and is not persisted by this path.
- Intake is evidence-gated: complete exports reuse the governed deterministic diagnosis, while missing columns or header-only exports return explicit follow-up questions and no metrics, findings, or report. Malformed, duplicate-header, oversized, and over-row-limit inputs fail deterministically.
- Round 19 rendered QA covered both missing-evidence and complete-diagnosis paths in Chrome, plus a 390 x 844 responsive check with no horizontal overflow. The SME project gate passes with 44 tests, Ruff, format, and strict mypy.
- A governed live-commerce delivery CLI now creates immutable `customer/runs/run-id` workspaces with authorization reference, mapping report, missing-field questions, redaction checklist, delivery status, SHA-256 evidence manifest, and a conditional diagnosis draft.
- Delivery is stateful and safe under owner absence: run ID collisions fail before overwrite; missing fields/no rows/privacy risk remain inspectable blocked artifacts; obvious direct-personal-data headers suppress diagnosis and raw retention.
- Raw merchant CSVs are not copied by default. Explicit retention works only for ready runs; evidence manifests record original filename, row count, content fingerprint, and retention state.
- Round 20 real CLI dogfood created a ready workspace from the public fixture, wrote all seven derived artifacts, reported rows 2/7 and stable SHA-256 values, and confirmed `RAW_NOT_RETAINED`. SME tests pass at 50; parent pytest passes at 544 with one skip.
- The local workbench now previews the exact seven governed delivery artifacts for ready evidence, including the conditional diagnosis draft, while explicitly stating that previewing creates no workspace, retains no raw CSV, and creates no authorization record.
- The workbench now shares readiness/redaction decisions with the delivery runner. A direct-personal-data header such as `手机号` produces `blocked_redaction` and suppresses metrics, findings, report display, report copy, and the commercial checklist instead of relying on warning copy.
- A five-item, page-local `199 RMB` acceptance checklist lets the merchant owner judge clarity, traceability, privacy, actionability, and willingness to pay. The final willingness-to-pay item remains unselected by automation and no checklist state is persisted.
- Round 21 Browser QA covered desktop and 390-pixel mobile ready/redaction-blocked states, one checklist interaction, no horizontal overflow, and an empty console. SME tests pass at 53; parent pytest passes at 549 with one skip; Ruff, strict mypy, touched format, structure, and diff checks pass.
- Round 22 adds the AICO organization-plane `commercial-evidence-loop` standing charter. When the project is idle, `/inbox` or `/morning` may surface one reviewable lead proposal, but no task runs until the boss explicitly accepts it. A real-config temporary-SQLite dogfood proves candidate persistence without task execution; parent pytest passes at 559 with one skip.
- Private-domain commercialization plan now defines Xiaohongshu post families, DM script, WeChat group onboarding, group operating rhythm, and paid conversion path.
- A paid-user acquisition campaign package now exists for the first Xiaohongshu -> WeChat -> paid diagnosis push. It defines positioning, target buyers, offer ladder, five ready-to-post Xiaohongshu scripts, DM replies, WeChat onboarding, a 14-day operator plan, lead scoring, daily checklist, delivery SOP, and success/pivot metrics. The campaign uses WeChat `17610788906` as the owner-provided conversion contact, but external sending/posting still requires explicit human approval.
- A first-post launch pack now exists for the recommended opening Xiaohongshu post: "这场直播比上一场差，不一定是没人买". It includes title, body, CTA, cover text options, first comment, keyword reply, WeChat welcome, 199 conversion reply, missing-field reply, and first-24-hour checklist.
- A growth operations playbook now defines the post-publication operating system: lead state machine, Xiaohongshu/WeChat/朋友圈/微信群 cadence, nurture sequence, channel expansion order, conversion scripts, CRM schema, weekly review, and 30-day targets.
- Lead-log and weekly-review templates now exist so the campaign can be operated as a measurable funnel rather than scattered chats. The lead log tracks source, keyword, pain, exportable fields, score, state, next action, paid status, objections, missing fields, and case candidates; the weekly review tracks funnel counts, content quality, conversion blockers, product learning, and the next week's single growth focus.
- First-post execution has started and the first Xiaohongshu note was submitted. A new 1080 x 1440 Xiaohongshu cover exists at `docs/commercialization/assets/xiaohongshu/exported/08-live-session-drop.png`; after the human owner enabled Chrome extension `Allow access to file URLs`, the cover was uploaded, the title/body/CTA/hashtags were filled, and `发布` was clicked. The new note appears in Xiaohongshu Creator Center `笔记管理` with status `审核中`. `docs/commercialization/launch-execution-log.md` records the submitted copy and next action.
- First-post review has passed. Xiaohongshu Creator Center `笔记管理` now lists the note under the published/all list with title `这场直播比上一场差，不一定是没人买`, created at `2026-07-07 16:34`, and current visible metrics of 3 views, 0 comments, 0 likes, 0 favorites, and 0 shares.
- Public desktop web access to the note id `6a4cba32000000001603fd2f` redirects to Xiaohongshu's "open App to scan" page, so the first comment could not be added from the current browser automation path. The prepared first comment remains the next manual/App action, and this platform limitation is recorded in `docs/journal/BLOCKERS.md`.
- A five-day Codex heartbeat follow-up named `SME Agent 小红书首帖跟进` is active from 2026-07-08 10:00. It will re-check Creator Center metrics, record leads, and update this project's commercialization logs.
- First heartbeat follow-up on 2026-07-08 10:00 found the note at 10 views, 0 comments, 0 likes, 0 favorites, and 0 shares. The direct desktop public URL still redirects to the App-scan page, so the prepared first comment remains a manual/App action. No comment lead exists in Creator Center; private-message leads were not exposed in the checked Creator Center note-management surface.
- Second heartbeat follow-up on 2026-07-09 10:00 found the note still at 10 views, 0 comments, 0 likes, 0 favorites, and 0 shares. Desktop public access still redirects to the App-scan page. Because engagement stayed flat for one full day, the next marketing action should move from passive watching to adding the prepared first comment through the App and preparing the second Xiaohongshu post from the launch pack.
- `projects/` versus `benchmarks/` boundary is recorded in this subproject's `AGENTS.md`: projects are product workspaces; benchmarks are AICO validation scorecards/evidence trails.

## Next round

1. From a human Telegram client, run `/use project sme-agent`, `/inbox`, and `/proposals`; decide the candidate with `/proposal accept|reject`, then inspect `/morning`. This is a real-client value/readability sample, not permission to send external merchant messages or accept the 199 RMB offer.
2. Add the prepared first comment via Xiaohongshu App or another Creator Center comment entry if it becomes available:
   `我先放一个字段自查...`.
3. Prepare and publish the second Xiaohongshu post from `docs/commercialization/first-post-launch-pack.md` or `paid-user-acquisition-campaign.md`, because the first note has stayed at 0 engagement after the 2026-07-09 check.
4. Re-check Xiaohongshu Creator Center metrics on the next heartbeat and record views, comments, likes, favorites, shares, and any lead signals in `docs/commercialization/launch-execution-log.md`.
5. Start logging every Xiaohongshu/WeChat lead with `docs/commercialization/lead-log-template.md`, then use objections and missing fields to improve product copy and diagnosis UX.
6. Have the real merchant owner complete the new local five-item acceptance checklist and decide whether the questions, evidence package, and report are strong enough for a `199 RMB` field-check/mini-diagnosis offer; automation must not select the willingness-to-pay item.
7. Run the weekly review template after the first 20 meaningful interactions or at the end of the first campaign week.
8. After owner acceptance, connect the workbench intake to an explicit operator-only "create delivery workspace" action that requires authorization reference and keeps raw retention off by default.
9. Add optional attribution dimensions for region, campaign, traffic source, event/holiday, product click, add-to-cart, and live-room dwell time; do not infer these causes until the data exists.
