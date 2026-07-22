# Screenshots Or UI Notes

Use this file for Computer Use or human notes about:

- Telegram Desktop first screen for `/morning`.
- Telegram Desktop first screen for `/inbox`.
- `/task <short_id>` readability.
- `/view` HTML snapshot usability.
- Data-Agent local CLI or UI quickstart.

Do not paste secrets, tokens, customer data, or private chat content here.

## 2026-06-28 Computer Use Notes

- `/Applications/Telegram.app` opened successfully and showed a logged-in chat
  list containing the `ai_co` bot conversation.
- `/Applications/Telegram 2.app` also exists but showed a QR-code login screen;
  it is not the correct client for this benchmark.
- The Computer Use screenshot/read path worked, but click actions against the
  logged-in Telegram app returned a tool activation error. If this remains true,
  the human should paste the commands from `aico-evidence.md` manually into
  `ai_co`, then paste first-screen notes back here.
- No screenshot file was saved in the repo in order to avoid accidentally
  storing private chat content.

## 2026-06-30 Computer Use / Telegram Notes

- A separate critic sub-agent was created and produced
  `ai-critic-scorecard-draft.md`.
- The stuck prior `aico-phase1` polling process was stopped, then a dedicated
  data-agent runtime was started and later stopped.
- Computer Use could still render the Telegram chat list, including `ai_co`,
  but click and key tools reported that Computer Use was not active for the app.
- `open /Applications/Telegram.app` and direct executable launch were not
  reliable from the terminal. Computer Use could show a Telegram screenshot even
  when the process was not scriptable through System Events.
- Therefore real Telegram message sending was not completed. This is a tool /
  local environment limitation, not a successful Telegram baseline.

## Data-Agent CLI UX Notes

- CLI accepts natural-language Chinese questions as a single argument.
- Answers expose intent, answer, evidence, calculation, SQL-style trace, and
  follow-up questions.
- There is no Web UI in `data-agent-v1`; score product UX as CLI-first.
