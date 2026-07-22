# Infinity Castle Raid Room — Collaboration Audit + Dream Showcase

> Inspired by the operational structure of a high-stakes castle raid story. This is an original AICO verification case and does not use official characters, images, dialogue, or assets.

## Why This Case

The familiar hook is a shifting battlefield where every team member has partial intelligence. One missed route, one unreviewed plan, or one unsafe approval boundary can break the raid.

AICO's product claim:

> A real AI company should keep shared intelligence, ask teammates to review risky plans, and turn blocked operations into reusable experience.

## Verification Story

Project: `infinity-castle`

Roles:
- `scout`: maps shifting routes and asks for review.
- `reviewer`: audits blind spots and approval gaps.
- `swordsman`: executes follow-up work only after approval boundaries are clear.

Commands:

```text
/project infinity-castle
/remember The castle route shifts after every encounter; preserve last known safe exits.
/ask scout prepare the first raid plan using safe exits
```

Expected visible effect:
- The scout task prompt contains `Shared memory:`.
- The safe-exit memory appears in the task prompt.
- The phrasing intentionally includes "safe exits" because memory retrieval should be explainable, not magical.

The scout output includes a collaboration directive:

```text
@reviewer: inspect the raid plan for blind spots and missing approvals.
```

Expected visible effect:
- A reviewer child task is created.
- Audit contains one `collaboration_requested` event.
- The event records source `scout`, target `reviewer`, and `parent_task=<scout-task-id>`.
- The reviewer payload includes `Context from scout output so far`.

Then create a blocked execution task:

```text
/ask swordsman update the raid route notes before approval
/dream
```

Expected visible effect:
- `/dream` creates a candidate experience about approval-blocked work.
- The candidate is not injected yet.

Promote the experience:

```text
/experience promote <candidate-id> as swordsman
/ask swordsman prepare the next strike
```

Expected visible effect:
- The swordsman prompt contains `Reusable experience (promoted lessons):`.
- The promoted candidate id appears in the prompt.

## Objective-Reality Review

- This case must not claim combat intelligence or domain reasoning. It verifies AICO orchestration mechanics: memory recall, collaboration handoff, audit trace, dream candidate generation, and experience injection.
- The reviewer child task currently keeps `target_persona=reviewer`; project assignment metadata is not guaranteed on collaboration children. Audit still records the source and target roles, which is the boss-facing trace that matters.
- The case only promotes candidate experience after an explicit command. That is deliberate: AICO should not auto-harden every stressful event into future behavior.

## Product Optimization Found

This case forced the test to respect retrieval reality. A generic request like "prepare raid plan" may not recall a memory about "safe exits"; the boss or lead should include the operative clue in the task or rely on future richer retrieval.

It also confirmed the collaboration audit shape is strong enough for publicity, while leaving a future improvement: collaboration child tasks could optionally preserve project assignment metadata for richer `/task` displays.

## Promotional Angle

Headline:

> 如果无限变化的城里没有共享记忆，团队只会反复迷路。

Short copy:

> AICO 让每个 AI 角色带着项目记忆行动：侦察员共享路线情报，审查员接住协作请求，审计链记录谁让谁检查了什么，夜里卡住的审批会被 `/dream` 变成候选经验，确认后再注入下一次任务。

Proof line:

> 这个 case 已用机器测试验证：shared memory 注入、reviewer child task、`collaboration_requested` audit、dream candidate、promoted experience 全链路可复现。

Safety note:

> Public material should use original "shifting castle raid room" visuals and avoid official screenshots, logos, character names, or copied lines.
