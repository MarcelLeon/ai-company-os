# Current Handoff

## Goal

Turn SME Agent from a governed metadata prototype into a week-one sellable, service-backed AI business diagnosis product for Taobao/Qianniu cold start.

## Done

- Project constitution, status, alignment loop, and journal were created.
- An AICO team configuration assigns lead, domain, runtime, test, review, and challenge roles.
- Typed metadata assets and relations can be registered, searched, and traversed in memory.
- A real revenue question is grounded through glossary, metric, explicit filters, dimensions, warehouse source, entity, and knowledge references.
- Relation signatures, version changes, metadata approval, and steward/source evidence are enforced.
- Lead and Challenger independently reviewed the slice; their valid objections were incorporated.
- Commercial launch kit, LLM/human division, user-input checklist, week-one plan, and Xiaohongshu week-one content plan were added.
- Ecommerce week-one sample data, deterministic diagnosis rules, Markdown renderer, delivery SOP, and sample report were added.
- Default launch pricing was fixed at 199 / 699 / 1999 RMB.
- Taobao/Qianniu listing copy was upgraded to a publish-ready, premium-trust version.
- Xiaohongshu plan now contains seven complete posts, not just a calendar.
- Delivery code now creates customer workspaces, writes evidence manifests, and flags obvious personal-data headers.
- Delivery runner now generates workspace, diagnosis draft, evidence manifest, and redaction checklist from CSV paths.
- Static SVG listing assets were added for premium main image, pain-driven main image, and detail-page preview.
- Taobao PNG exports and seven Xiaohongshu cover PNGs were generated.
- Product quality review documented and fixed stale price ranges, inconsistent labels, low-premium wording, and cover-text overflow.
- Domain templates were added for live/content commerce, local services, and performance advertising, with live-commerce dimensions and metrics aligned to merchant diagnosis needs.
- Live-commerce validation loop now maps Chinese platform-style headers, computes traceable live-room metrics, renders a human-review diagnosis draft, and documents acceptance gates.
- Public-web-derived dogfood fixture was added with source caveats, CSV inputs, expected metrics, and a generated evidence report.
- Dogfood deployment and usage are documented in `docs/operations/dogfood-deployment-usage.md`, including local setup, browser workbench/self-serve intake, live-commerce diagnosis, ecommerce delivery package generation, and the current lack of cloud/IM/SaaS product interaction.
- Local browser workbench was added. Run `PYTHONPATH=projects/sme-agent/src uv run python -m sme_agent.commercialization.workbench` and open `http://127.0.0.1:8767` to choose live-commerce samples, view mapped metrics/findings, and copy the delivery report.
- Workbench explanation was expanded so the owner can understand the pain point, sample data model, entity relationships, business process, output logic, and next steps before reading conclusions.
- Findings were upgraded from generic advice to deterministic attribution. Current reports identify the top refund SKU and the low-performing live session/category/anchor behind GPM and conversion issues. External causes such as region, holiday, World Cup, summer vacation, campaign, traffic source, product click, add-to-cart, and dwell-time effects remain unsupported until those fields are present.
- The week-one sample has 2026-06-19 paid orders with blank `支付金额`. The loader now rejects those rows explicitly. Do not answer "why did 6-19 drop versus 6-18" as a business conclusion until those blanks are fixed or intentionally documented.
- Two-session comparison is now implemented for the week-one sample. It explains that 6-19 dropped because paid GMV and GPM fell while paid orders/buyers stayed flat, and it attributes the paid GMV drop to SKU-C, SKU-A, and SKU-B.
- Self-serve local intake is now implemented in the workbench. A merchant can select or paste `live_sessions.csv` and `orders.csv`; complete evidence produces the governed diagnosis, while insufficient evidence produces concrete field questions and no paid conclusion. Intake is bounded and remains in memory.
- Governed live-commerce customer delivery is now implemented as `sme-agent-live-commerce-deliver`. Each authorization-referenced run has an immutable customer/run path, mapping/questions/redaction/status/manifest artifacts, and a diagnosis only when ready.
- The browser workbench now previews that same governed package without creating a workspace: six always-written governance artifacts plus a conditional diagnosis draft. It explicitly states that previewing creates no authorization record, retains no raw CSV, and persists no checklist state.
- Workbench privacy enforcement now matches the runner. Direct-personal-data headers produce `blocked_redaction` and suppress metrics, findings, report display/copy, and the commercial acceptance checklist.
- A five-item page-local `199 RMB` merchant-owner checklist covers clarity, evidence trace, privacy gating, actionability, and willingness to pay. Browser automation exercised progress but intentionally left willingness to pay for the human owner.
- The AICO project config now declares a bounded `commercial-evidence-loop` standing charter. Idle recovery surfaces can create one persistent reviewable proposal, but only explicit boss acceptance creates a normal governed lead task.
- Evidence manifests now support source SHA-256, row count, retention state, and workspace path. Raw live-commerce exports are not retained by default and cannot be retained for missing-field/no-row/redaction-blocked runs.
- Private-domain commercialization plan exists at `docs/commercialization/private-domain-growth-plan.md`.
- Paid-user acquisition campaign package exists at `docs/commercialization/paid-user-acquisition-campaign.md`. It is the first explicit Xiaohongshu -> WeChat -> paid diagnosis campaign: positioning, ICP, offer ladder, five publishable post drafts, DM scripts, WeChat onboarding, 14-day action plan, lead scoring, daily operator checklist, and first-customer delivery SOP. It uses owner-provided WeChat `17610788906` for conversion, but external posting/sending requires human approval.
- First-post launch pack exists at `docs/commercialization/first-post-launch-pack.md`. It packages the recommended opening post, cover options, first comment, keyword reply, WeChat welcome, field-enough/field-missing replies, and first-24-hour checklist.
- Growth operations playbook exists at `docs/commercialization/growth-operations-playbook.md`. It defines the after-post operating loop: lead state machine, push cadence, private nurture, WeChat group/Moments rhythm, channel expansion, conversion scripts, CRM schema, weekly review, and 30-day targets.
- Lead-log template exists at `docs/commercialization/lead-log-template.md`. It is the first-stage CRM for source, keyword, pain, fields, score, state, next action, paid status, objections, missing fields, and case candidates.
- Weekly growth review template exists at `docs/commercialization/weekly-growth-review-template.md`. It keeps the campaign focused on funnel numbers, lead quality, conversion blockers, product learning, case candidates, and one next-week growth decision.
- First-post execution attempt exists at `docs/commercialization/launch-execution-log.md`. A new cover SVG/PNG was created, the Xiaohongshu Creator Center publish page was opened in Chrome, the logged-in account reached `发布笔记`, and the page was switched to `上传图文`. After the human owner enabled Chrome extension file-URL access, the cover was uploaded, the title/body/CTA/hashtags were filled, and `发布` was clicked. The new note appears in `笔记管理` with status `审核中`; Creator Center note manager was left open in Chrome for handoff.
- First-post review has passed. Creator Center `笔记管理` shows the note `这场直播比上一场差，不一定是没人买`, created at `2026-07-07 16:34`, with current visible metrics: 3 views, 0 comments, 0 likes, 0 favorites, and 0 shares.
- The public note id is `6a4cba32000000001603fd2f`, but `https://www.xiaohongshu.com/explore/6a4cba32000000001603fd2f` redirects desktop web to an App-scan page, so browser automation could not add the prepared first comment. This is recorded as blocker B-002.
- A five-day Codex heartbeat follow-up named `SME Agent 小红书首帖跟进` is active from 2026-07-08 10:00 to keep checking metrics and lead signals.
- The 2026-07-08 10:00 heartbeat found the note at 10 views, 0 comments, 0 likes, 0 favorites, and 0 shares. Desktop public access still redirects to Xiaohongshu's App-scan page; first-comment posting remains a manual/App action. No comment lead was visible in note management; private-message leads were not exposed in the checked Creator Center surface.
- The 2026-07-09 10:00 heartbeat found no metric movement: 10 views, 0 comments, 0 likes, 0 favorites, and 0 shares. Desktop public access still redirects to the App-scan page. Next marketing action should not be more passive observation: add the prepared first comment through the App and prepare the second Xiaohongshu post.
- SME Agent `AGENTS.md` now records that `projects/` is for product workspaces and `benchmarks/` is for AICO validation scorecards/evidence trails.

## Evidence

- `tests/unit/test_catalog.py`
- `tests/unit/test_grounding.py`
- `tests/unit/test_sme_agent_project.py` in the parent AICO repository
- `tests/unit/test_standing_proposal.py` in the parent AICO repository, including the real SME config + temporary SQLite dogfood
- `docs/evidence/round-1.md`
- `tests/unit/test_commercialization.py`
- `docs/commercialization/sample-report-ecommerce.md`
- `docs/commercialization/taobao-listing.md`
- `docs/commercialization/taobao-visual-pack.md`
- `docs/commercialization/visual-assets.md`
- `docs/commercialization/assets/taobao-main-premium.svg`
- `docs/commercialization/assets/taobao-main-pain.svg`
- `docs/commercialization/assets/taobao-detail-preview.svg`
- `docs/commercialization/assets/exported/`
- `docs/commercialization/assets/xiaohongshu/`
- `docs/commercialization/product-quality-review.md`
- `docs/commercialization/xiaohongshu-calendar.md`
- `docs/commercialization/report-generation-runbook.md`
- `docs/architecture/domain-templates.md`
- `docs/commercialization/live-commerce-validation.md`
- `docs/evidence/public-web-dogfood-report.md`
- `docs/operations/dogfood-deployment-usage.md`
- `src/sme_agent/commercialization/workbench.py`
- `src/sme_agent/commercialization/live_commerce_comparison.py`
- `docs/commercialization/private-domain-growth-plan.md`
- `docs/commercialization/paid-user-acquisition-campaign.md`
- `docs/commercialization/first-post-launch-pack.md`
- `docs/commercialization/growth-operations-playbook.md`
- `docs/commercialization/lead-log-template.md`
- `docs/commercialization/weekly-growth-review-template.md`
- `docs/commercialization/launch-execution-log.md`
- `docs/commercialization/assets/xiaohongshu/08-live-session-drop.svg`
- `docs/commercialization/assets/xiaohongshu/exported/08-live-session-drop.png`
- `docs/decisions/0002-domain-templates-for-vertical-fit.md`
- `src/sme_agent/domains/templates.py`
- `src/sme_agent/domains/mapping.py`
- `src/sme_agent/commercialization/live_commerce_diagnosis.py`
- `src/sme_agent/commercialization/live_commerce_intake.py`
- `src/sme_agent/commercialization/live_commerce_delivery.py`
- `src/sme_agent/commercialization/live_commerce_delivery_cli.py`
- `tests/unit/test_workbench.py`
- `tests/unit/test_live_commerce_intake.py`
- `tests/unit/test_live_commerce_delivery.py`
- `tests/unit/test_live_commerce_comparison.py`
- `tests/unit/test_domain_templates.py`
- `tests/unit/test_live_commerce_diagnosis.py`
- `sample_data/ecommerce_week_one/`
- `sample_data/live_commerce_week_one/`
- `sample_data/live_commerce_public_dogfood/`
- `docs/goals/self-serve-live-commerce-intake.md`
- `docs/goals/live-commerce-customer-workspace.md`
- `docs/commercialization/live-commerce-delivery-runbook.md`
- `docs/decisions/0003-immutable-customer-delivery-runs.md`
- Round 22 organization-plane gates: real SME config + temporary SQLite proposal dogfood; parent `559 passed, 1 skipped`; Ruff, mypy, touched format, structure, and `git diff --check` pass. Full-root format still reports the unrelated pre-existing `projects/data-agent-v1/src/data_agent_v1/engine.py`.

## Not done

- Persistent storage, API, authentication, document ingestion, passage retrieval, agent loop, and LLM calls.
- Real Telegram project-office proposal decision and restart/morning recovery dogfood; machine persistence is proven, but human-client value/readability is not.
- Human finance/data-steward acceptance of the sample semantics.
- Real Douyin/Kuaishou merchant exports have not been mapped yet; only realistic local sample exports are covered.
- The public-web dogfood fixture is source-linked and scaled down, but it is not a raw merchant export and must not be presented as customer data.
- The self-serve browser intake and governed delivery CLI are not yet connected by an explicit operator action; CLI use is documented separately.
- The real merchant owner has not yet made the subjective `199 RMB` willingness-to-pay decision; automation did not select it.
- Browser-backed Taobao/Qianniu publish-flow inspection has not been completed.
- Platform-specific upload dimensions have not been confirmed.
- There is no console script wrapper yet; workbench starts via `python -m sme_agent.commercialization.workbench`.
- There is no cloud SaaS console, Telegram product surface, or Taobao/Qianniu plugin UI yet. The self-serve flow is intentionally localhost-only and has no authentication or tenancy.
- The first paid acquisition campaign has passed Xiaohongshu review and is visible in Creator Center. The first comment still needs to be added from the App or another available comment surface because desktop web blocks public note browsing.

## First action next round

Continue with minimum human intervention. First obtain one human Telegram client sample for `/inbox` → proposal accept/reject → `/morning`; machine dogfood must not be reported as real IM acceptance. Ask only for login, external publication/comment action, payment, final promise changes, or real customer data authorization. The merchant owner still needs to decide whether the offer is worth `199 RMB`; only after explicit owner acceptance may browser intake connect to the delivery runner through an authorization-referenced operator action.
