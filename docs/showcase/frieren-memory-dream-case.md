# Long Memory Fantasy Party — Shared Memory + Dream Showcase

> Inspired by the emotional structure of long-lived fantasy travel stories. This is an original AICO verification case and does not use official characters, images, dialogue, or assets.

## Why This Case

The familiar emotional hook is simple: a long-lived mage only understands years later that companions' small promises mattered. AICO turns that feeling into a product claim:

> The AI team should not wait fifty years to remember what the boss and teammates already learned.

This case is good for shared memory because the work depends on companion preferences and past promises. It is good for `/dream` because repeated blocked work should become a reusable runbook lesson rather than another forgotten trace.

## Verification Story

Project: `frieren-party`

Roles:
- `lead`: plans the journey and reduces boss cognitive load.
- `implementer`: updates the travel log after approval boundaries are clear.

Commands:

```text
/project frieren-party
/remember The party promised to write down companion preferences before accepting a new village request.
/ask lead plan the winter village request
```

Expected visible effect:
- The lead task prompt contains `Shared memory:`.
- The memory claim about companion preferences is present.
- This proves AICO can carry project-scoped facts into later role work.

Then create a realistic blocked task:

```text
/ask implementer update the travel log before asking the boss
/dream
```

Expected visible effect:
- `/dream` emits `candidate experience only`.
- The candidate has `kind=experience`, `status=candidate`, `source=dream_review`.
- `/dream` suggests `/experience review` and `/experience promote <candidate-id> as <role>`.

Promote the experience:

```text
/experience promote <candidate-id> as implementer
/ask implementer plan the retry
```

Expected visible effect:
- The new implementer task prompt contains `Reusable experience (promoted lessons):`.
- The task metadata contains `aico.injected_experience_ids=<candidate-id>`.

## Objective-Reality Review

- AICO does not magically remember unrelated information. The task query must be related enough to the stored fact for retrieval to be explainable.
- Candidate experience is intentionally not injected before promotion. This protects the system from turning every noisy failure into permanent behavior.
- `/dream` currently learns from task signals such as waiting approval, running, failed, interrupted, and rejected. It does not infer deep human emotion from arbitrary prose.

## Product Optimization Found

This case exposed that `/dream` should guide users to the experience lifecycle. AICO now points to `/experience review` and `/experience promote`, not `/remember`.

It also reinforced a product boundary: fact memory and promoted experience should appear in separate prompt sections. Shared memory is for facts; Experience is for reusable lessons.

## Promotional Angle

Headline:

> 别等五十年后，才想起队友说过什么。

Short copy:

> AICO 会把老板交代过的偏好、团队踩过的坑、夜里卡住的任务变成可追溯的记忆和可晋升的经验。事实进 Shared Memory，复盘进 Dream Candidate，确认后才进入下一次任务的 Experience Layer。

Proof line:

> 不是情怀滤镜：这个 case 有机器测试覆盖 shared memory 注入、dream candidate、experience promote 和下一轮 prompt 注入。

Safety note:

> Public material should use original travel-party visuals and "inspired by long-memory fantasy stories" wording. Do not use official anime screenshots, logos, or character names in commercial assets.
