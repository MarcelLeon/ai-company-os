# Release Room Recording Storyboard

目标:30-60 秒动态图或短视频,让开源用户立刻理解 AI Company OS 是“远程 AI
项目办公室”,不是多 AI 转发器。

README GIF 的具体时间线见 [`shot-rhythm.md`](shot-rhythm.md)。本文件保留高层分镜,
避免每次调整秒数时重复维护两份表。

## 镜头 1: 项目办公室

- 画面:IM 中输入 `/use project release-room`、`/team`。
- 重点:团队列表和 lead 标记。
- 字幕建议:Assign AI agents to real project roles.

## 镜头 2: 共享记忆

- 画面:输入三条 `/remember`,随后 `/recall release notes`。
- 重点:项目共识会被后续角色任务使用。
- 字幕建议:Shared memory keeps team rules alive.

## 镜头 3: PM 拆工

- 画面:`/ask pm ...` 输出 release plan。
- 重点:PM 负责拆解,不是写代码。
- 字幕建议:Turn a goal into role-based work.

## 镜头 4: 实现和审批

- 画面:`/ask implementer ...` 后出现 approval required,用户 `/approve`。
- 重点:远程执行不等于无权限边界。
- 字幕建议:Risky actions still need approval.

## 镜头 5: 独立验收

- 画面:`/ask tester ...` 和 `/ask reviewer ...`。
- 重点:测试和 review 分离。
- 字幕建议:Review and testing are separate jobs.

## 镜头 6: 早报和审计

- 画面:`/overnight ...`,切到 `/daily`,再展示 `/audit`。
- 重点:睡前派工,早上看 done / blocked / risks / next actions。
- 字幕建议:Wake up to a handoff, not a mystery.

## 不要拍

- 不要长时间展示底层 AI 生成大段文本。
- 不要只拍一个 agent 修 bug。
- 不要暗示 AICO 自己生成代码;AICO 管理和编排底层 AI 工具。

## 转 GIF

本机只需要 `ffmpeg`,不要求安装 `gifski`:

```bash
bash examples/release-room/make-gif.sh /path/to/recording.mov docs/assets/release-room-demo.gif
```
