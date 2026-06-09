# Release Room Demo

## 一句话

Release Room 展示的是:一个开发者用 IM 远程开一个 AI 项目作战室,让多个 AI agent
按真实软件发布流程协作完成一个小型开源项目的 v0.2 release。

## 为什么选这个 Demo

原来的“修一个 issue”只能展示离线托管,不能体现 AI Company OS 的核心壁垒。
Release Room 更像真实工作:

- PM / lead 拆范围、吸收团队意见并做低风险决策。
- Implementer 改代码和文档。
- Tester 设计回归和 release contract。
- Reviewer 查风险、测试缺口和维护性。
- Challenger / Critical Philosopher 挑战方案前提、机会成本和长期风险。
- Release Manager 维护 changelog、release notes 和早报。
- 老板只在 IM 中派工、审批、验收和追问。

这能把项目已完成的大部分能力串起来:

- Project office: `/project`, `/brief`, `/next`, `/daily`, `/weekly`
- Team / role: `/roles`, `/team`, `/appoint`, `/lead`, `/ask`, `/role propose`
- Shared memory: `/remember`, `/recall`, project/team-scoped prompt injection
- Collaboration: agent 输出 `@persona: ...` 后创建子任务
- Approval / audit: `/approve`, `/reject`, `/audit`
- Observability: `/tasks`, `/task`, `/metrics`
- Offline delegation: `/overnight`

## Demo 资产

- AICO 配置: [`examples/release-room/aico-project.json`](../../examples/release-room/aico-project.json)
- 示例仓库: [`examples/release-room/notes-cli`](../../examples/release-room/notes-cli)
- 操作脚本: [`examples/release-room/demo-script.md`](../../examples/release-room/demo-script.md)
- 本地 transcript: [`examples/release-room/transcript.md`](../../examples/release-room/transcript.md)
- 录屏分镜: [`examples/release-room/recording-storyboard.md`](../../examples/release-room/recording-storyboard.md)
- 镜头节奏: [`examples/release-room/shot-rhythm.md`](../../examples/release-room/shot-rhythm.md)
- 验收 Playbook: [`docs/playbooks/release-room-demo.md`](../playbooks/release-room-demo.md)

## 用户第一眼应该看到什么

1. `/team` 展示当前项目团队和 lead,像真实项目办公室。
2. `/team` 显示 lead + challenger,并显示 team readiness。
3. `/remember` 写入项目共识,后续角色任务自动继承这些约束。
4. `/ask pm ...` 把模糊 release 目标拆成职责、验收和风险。
5. `/ask challenger ...` 在重要取舍前提出反方意见和隐藏成本。
6. `/ask implementer ...` 进入真实代码仓库,需要写文件或执行命令时仍走审批。
7. `/ask reviewer ...` / `/ask tester ...` 做交付前检查,不是同一个 AI 自说自话。
8. `/overnight ...` 把剩余 release 工作托管给 lead,早上 `/morning` 验收。
9. `/audit` / `/task` 证明发生过的动作可追溯、可回看、可中断。

## 分阶段落地

### Stage 1: Static Demo Package

当前阶段已落地:

- 一个真实可读的小型 CLI 仓库。
- 一份 release-room project/team 配置。
- 一份 IM 操作脚本和录屏 storyboard。
- 配置加载单测,避免 demo 配置和当前模型漂移。

### Stage 2: Local Acceptance

当前阶段已落地:

- 用 fake adapters 驱动 release-room 全流程 acceptance test。
- 覆盖 `/team`、`/remember`、`/ask`、`/approve`、`/overnight`、`/morning`、
  `/tasks`、`/metrics`、`/audit`。
- 生成无真实 token 的本地文本 transcript,作为 README/GIF 脚本素材。

### Stage 3: Public Showcase

当前阶段已落地:

- 录制过真实 Telegram dogfooding GIF,用于证明 Release Room 可以进入真实 IM dogfood。
- README 首页已嵌入 `docs/assets/release-room-demo.gif`。
- 没有 `gifski` 时可用 `examples/release-room/make-gif.sh` 调 `ffmpeg` 转 GIF。

后续可继续优化:

- D0 前复剪 README GIF:首帧必须是当前 IM 产品画面,控制在 30-60 秒,并前置展示
  `/morning` 和 `/view`。
- 补更清晰的 approval gate 镜头。
- 可选:脚本化生成 demo audit JSONL,用于 `/metrics` / `aico-glance` 展示。
