# Release Room Example

Release Room 是 AI Company OS 的主 demo。它不是“让一个 AI 修一个 bug”,而是
展示一个开发者如何在 IM 里远程管理 AI 团队,完成一个小型开源 CLI 的 v0.2 发布。

## 目录

- `aico-project.json`:AICO project/team/role 配置。
- `demo-script.md`:IM 中逐步执行的 demo 脚本。
- `transcript.md`:无真实 token 的本地验收 transcript。
- `recording-storyboard.md`:录制动态图或短视频时的镜头分镜。
- `shot-rhythm.md`:从 transcript 压缩出来的 30-60 秒 README GIF 镜头节奏。
- `generate-public-gif.py`:从稳定 transcript 节奏生成 README GIF 和 GitHub social preview。
- `make-gif.sh`:使用本机 `ffmpeg` 把 `.mov/.mp4` 录屏转成 README 可嵌入 GIF。
- `notes-cli/`:被 AI 团队接手的示例开源项目。

## 快速使用

从 AI Company OS 仓库根目录启动:

```bash
export AICO_PROJECT_CONFIG_PATH="examples/release-room/aico-project.json"
export AICO_MEMORY_PATH="/tmp/aico-release-room-memory.jsonl"
export AICO_AUDIT_LOG_PATH="/tmp/aico-release-room-audit.jsonl"
```

然后按 [`demo-script.md`](demo-script.md) 在 Telegram/Feishu 中操作。

录屏前先看 [`shot-rhythm.md`](shot-rhythm.md),按精简命令清单录 30-60 秒主 GIF。
如果只需要生成公开发布用的稳定 transcript-driven 资产,执行:

```bash
python3 examples/release-room/generate-public-gif.py
```

它会写出:

```text
docs/assets/release-room-demo.gif
docs/assets/social-preview.png
```

本机不需要额外安装 `gifski`;如果已有 `.mov` 或 `.mp4` 录屏,可用:

```bash
bash examples/release-room/make-gif.sh /path/to/recording.mov docs/assets/release-room-demo.gif
```

## Demo 边界

AICO 展示的是团队编排、记忆、审批、审计、观测和交接。底层代码实现质量取决于
你启用的 AI Adapter。录屏或 README 不能把底层 AI 的能力包装成 AICO 自己的能力。
