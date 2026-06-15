# GitHub Publication Checklist

> 仓库 description、topics 和 social preview 是 GitHub 仓库 metadata。它们不会从
> README 自动同步,需要仓库管理员在 GitHub 页面手动配置。

---

## Recommended Description

GitHub 仓库 About 区域 description 建议填:

```text
Remote control room for local AI coding agents: manage Claude Code, Codex, Cursor and more from Telegram or Feishu with roles, approvals, audit, memory and overnight handoff.
```

更短版本:

```text
Remote IM control room for local AI coding agents.
```

## Recommended Website

如果暂时没有官网,建议先填:

```text
https://github.com/MarcelLeon/ai-company-os#readme
```

等后续有文档站或 demo page 后再替换。

## Recommended Topics

GitHub topics 最多 20 个,建议先填这组:

```text
ai-agents
agent-os
multi-agent
mcp
developer-tools
claude-code
codex
cursor
telegram-bot
feishu
local-first
automation
python
fastapi
llm
ai-coding
approval-workflow
audit-log
memory
```

如果需要更克制,第一优先级是:

```text
ai-agents
agent-os
multi-agent
developer-tools
claude-code
codex
telegram-bot
local-first
python
approval-workflow
```

## How To Set Description And Topics

1. 打开 `https://github.com/MarcelLeon/ai-company-os`。
2. 在仓库首页右侧 `About` 区域点齿轮图标。
3. 填写 `Description` 和 `Website`。
4. 在 `Topics` 输入框逐个添加上面的 topics。
5. 点击 `Save changes`。

GitHub 官方文档说明 topics 用来帮助别人发现和贡献项目,并建议选择和项目用途、主题、
社区或语言相关的标签。topic 名称需要小写、可用数字和连字符,单个 topic 50 字符以内,
最多 20 个。

## Social Preview

Social preview 需要在仓库 `Settings` 里上传图片。GitHub 官方建议:

- PNG / JPG / GIF。
- 文件小于 1 MB。
- 最佳显示尺寸为 `1280 x 640`。
- 如果用透明 PNG,要考虑深色 / 浅色背景兼容;不确定时用实底背景。

建议首版 social preview 文案:

```text
AI Company OS
Remote control room for your local AI coding agents
Telegram / Feishu · Claude Code / Codex / Cursor · Approval · Audit · Memory
```

画面建议:

- 左侧:项目名和一句话定位。
- 右侧:Telegram Release Room 截图或简化流程图。
- 底部:3 个短标签,例如 `IM-first`, `Local agents`, `Approval + audit`。

当前已生成可上传文件:

```text
docs/assets/social-preview.png
```

该文件为 `1280 x 640` PNG,小于 1 MB,用于 GitHub Social preview。

上传路径:

1. 打开仓库页面。
2. 点击 `Settings`。
3. 找到 `Social preview`。
4. 点击 `Edit` -> `Upload an image...`。
5. 上传 `1280 x 640` 且小于 1 MB 的 PNG / JPG / GIF。

上传后,回到本地仓库运行一次只读复核:

```bash
uv run aico-github-social-preview
```

如果输出 `status: needs-owner-upload`,GitHub 仍然看起来在使用默认 repository card。
如果输出 `status: ok`,再肉眼打开 GitHub 仓库或分享预览做一次 spot check,确认画面确实是
`AI Company OS` 的自定义首图。

当前 `docs/assets/release-room-demo.gif` 已在 Round 149 更新:约 278 KB、`960 x 540`、
36 秒,首帧明确 boss-absent 假设,并展示 `/morning` 和 `/view`。README 可继续引用该 GIF。
GitHub social preview 仍建议上传上面的静态 PNG,不要直接上传 README 动图。

Agent 负责 tag / GitHub Release / D0 运维时,还要读
[`docs/agent/09-github-release-ops.md`](../agent/09-github-release-ops.md)。

## References

- [GitHub Docs: Customizing your repository](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository)
- [GitHub Docs: Classifying your repository with topics](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/classifying-your-repository-with-topics)
- [GitHub Docs: Customizing your repository's social media preview](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/customizing-your-repositorys-social-media-preview)
