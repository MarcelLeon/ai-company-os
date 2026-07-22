# Telegram Native Pre Table Design

## Goal

Render compact table-like output as one Telegram HTML `<pre>` block so columns remain aligned in
Telegram Web and mobile clients. Keep existing business copy, headings, bullets, commands, and
lazy-detail links unchanged.

## Evidence

The current core renderer already converts Markdown tables into width-bounded, truncated rows.
Each row is represented as a full-line `MessageTextStyle.CODE` span. The Telegram Channel maps
every span independently to `<code>`, so a table becomes several unrelated inline code elements.
The real Telegram Web sample confirms that this loses the visual table container and makes wide
outputs harder to scan.

## Design

- Keep `MessageContent` and `MessageTextSpan` platform-neutral.
- In the Telegram Channel HTML mapping, recognize two or more consecutive full-line `CODE` spans
  separated only by a newline.
- Render such a run as one escaped `<pre>` block.
- Keep isolated or inline `CODE` spans as `<code>` so slash commands remain clickable-looking and
  compact.
- Preserve the existing table width caps, truncation marker, and `详情: /view 查看完整表格` escape
  hatch.
- Do not add dependencies or change provider routing, command copy, storage, or collaboration.

## Verification

1. Renderer golden: compact and wide tables still contain aligned rows and lazy detail routing.
2. Telegram payload golden: table payload contains one `<pre>` block and no per-row `<code>` tags.
3. Regression: inline `/view` remains `<code>/view</code>` outside the table block.
4. Full Python gates: pytest, mypy, Ruff, and `git diff --check`.
5. Real Web Telegram sample: send one real inbound command, then send a deterministic table through
   the production output path and inspect the new message bubble, not old history.

## Non-Goals

- Rewriting built-in AICO copy or changing its language.
- Introducing a native Telegram table API; Telegram Bot API does not expose one.
- Flattening tables into field lists or sending raw Markdown pipe tables.
- Resetting Telegram App account data while diagnosing its voluntary startup exit.
