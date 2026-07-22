# AICO 证据记录

这份文件记录 `data-agent-v1` baseline 的 AICO 侧证据。人类评分时,AICO 编排半边看这里和真实 IM transcript;Data-Agent 产品半边看 `data-agent-eval.md`。

## Runtime

- AICO project config:`projects/data-agent-v1/aico-project.json`
- Audit path:`.aico/data-agent-v1-audit.jsonl`
- Memory path:`.aico/data-agent-v1-memory.jsonl`
- State DB:`.aico/data-agent-v1-state.db`
- View project IDs:`data-agent-v1`

启动命令:

```bash
env \
  AICO_PROJECT_CONFIG_PATH=projects/data-agent-v1/aico-project.json \
  AICO_AUDIT_LOG_PATH=.aico/data-agent-v1-audit.jsonl \
  AICO_MEMORY_PATH=.aico/data-agent-v1-memory.jsonl \
  AICO_STATE_DB_PATH=.aico/data-agent-v1-state.db \
  AICO_VIEW_PROJECT_IDS=data-agent-v1 \
  AICO_ENABLE_CODEX_ADAPTER=true \
  AICO_CLAUDE_WORKING_DIRECTORY=/Users/wangzq/VsCodeProjects/ai-company-os \
  UV_CACHE_DIR=/tmp/aico-uv-cache \
  uv run --python /opt/homebrew/bin/python3.11 aico-phase1
```

不要把 Telegram bot token 或模型 provider token 粘贴到证据文件里。

## 当前事实

- 已启动过专用 AICO runtime,并使用独立的 `.aico/data-agent-v1-*` state / audit / memory 路径。
- Telegram Desktop 能被读屏,并能看到 `ai_co` bot 对话。
- 本机还存在第二个 Telegram app 实例,但它不是可靠的已登录 baseline 客户端。
- Computer Use 可渲染 Telegram 截图,但不能稳定点击/输入;macOS scripting 和 `open` 也不能可靠控制 Telegram。
- 因此,当前没有真实 Telegram transcript。不能把 local injected baseline 写成真实 Telegram baseline。

## Local Injected IM Baseline

因为真实 Telegram 发送被本地 UI 控制问题挡住,已通过 AICO 的真实 `Orchestrator`、`ProjectAssignmentDirectory`、命令处理器、offline delegation 和 `/view` handler 跑了一次本地注入 baseline。

- Transcript:`benchmarks/data-agent/runs/2026-06-28-v1/local-im-baseline-transcript.md`
- Local view snapshot:`benchmarks/data-agent/runs/2026-06-28-v1/local-view-snapshots/aico-view-data-agent-v1.html`
- 结果:20 sent messages,9 edited messages,3 Claude fake tasks,6 Codex fake tasks,27 audit events。
- 它证明 AICO 命令合同可跑,不证明真实 Telegram UX 可用。
- 评分时不能当成完整 IM 证据。

## 独立挑刺

- 草稿:`benchmarks/data-agent/runs/2026-06-28-v1/ai-critic-scorecard-draft.md`
- 挑刺草稿给分:AICO `4/50`,Data-Agent `38/50`,总分 `42/100`。
- 核心提醒:不要让 Data-Agent 产品能跑这件事,抬高 AICO 编排分。

## IM 证据 checklist

真实 Telegram:

- [ ] `/project data-agent-v1`
- [ ] `/team`
- [ ] `/goal lead ...`
- [ ] `/ask challenger ...`
- [ ] `/ask lead ...`
- [ ] `/overnight ...`
- [ ] `/morning`
- [ ] `/inbox`
- [ ] `/task <short_id>`
- [ ] `/view`

Local injected IM:

- [x] `/project data-agent-v1`
- [x] `/team`
- [x] `/goal lead ...`
- [x] `/ask challenger ...`
- [x] `/ask lead ...`
- [x] `/ask tester ...`
- [x] `/ask reviewer ...`
- [x] `/overnight ...`
- [x] `/morning`
- [x] `/inbox`
- [x] `/tasks`
- [x] `/view`

## 真实 Telegram 要发送的命令

按顺序发给已登录的 `ai_co` Telegram 聊天:

```text
/project data-agent-v1
```

```text
/team
```

```text
/goal lead 研发企业级 data-agent v1。验收: 本地可运行; 有语义层; 能回答20个golden业务问题; 回答必须给出SQL或确定性计算依据; 遇到歧义必须追问; 有测试、README、quickstart、handoff和AICO证据。停止: 需要真实外部账号、付费、上传第三方、或无法确定企业语义口径。
```

```text
/ask challenger 按企业级 data-agent 标准挑战当前目标，指出范围、验收、商业价值和玩具化风险，只读审查，不改文件。
```

```text
/ask lead 综合 challenger 意见，给出最终切片计划、角色分工、验收证据和第一步任务。
```

然后发 bounded absence-first slice:

```text
/overnight 按最终切片计划推进 data-agent-v1 的最小可运行版本。验收: 能本地启动; 3个样例业务问题有SQL或确定性计算依据; tester给出失败/通过证据; reviewer指出未解决风险; lead留下done/blocked/risks/next actions。
```

回来后发:

```text
/morning
/inbox
/view
```

如果 `/inbox` 或 `/morning` 里出现 task id,再查最关键的一个:

```text
/task <short_id>
```

## 人类粘贴真实 IM 证据的位置

- `/morning` 第一屏摘要:
- `/inbox` 第一屏摘要:
- 最重要的 `/task <short_id>`:
- `/view` 文件名或体验说明:
- 是否出现审批:
- 是否有失败、中断或接手困惑:

## AICO 打分提示

- 如果真实 Telegram 命令跑通,且 `/morning` 足够让人接手,AICO boss-absent recovery 可以给较高分。
- 如果必须翻聊天记录才能理解进展,boss-absent recovery 要扣重分。
- 如果 lead / challenger / tester / reviewer 有清晰分工和 task 证据,多 agent 分可以上去。
- 如果只是一个 agent 在说漂亮话,多 agent 分要低。
- 如果风险操作会等审批,本地安全动作能继续,风险分可以给。
- 如果没有真实 `/task` 或 `/view` 证据,即使 Data-Agent 能跑,AICO traceability 也不能高分。
