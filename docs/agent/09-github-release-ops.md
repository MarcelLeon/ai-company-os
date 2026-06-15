# 09 — GitHub 发布与仓库运维 SOP

> 本文给 Agent 使用。人类配置 GitHub About / topics / social preview 时,看
> [`docs/human/github-publication.md`](../human/github-publication.md)。

---

## 什么时候必须读

接到这些任务时,必须读本文:

- 把仓库从 private 准备为 public。
- 发布 `v0.1.0` tag 或 GitHub Release。
- 修改 GitHub About、topics、website、social preview 的发布材料。
- 做 launch / D0 / Show HN / Reddit 前的最后检查。
- 处理 release branch、PR、CI、tag、release notes、公开传播节奏。

---

## 总原则

GitHub public、tag、GitHub Release、HN / Reddit 发帖都是外部信号动作。它们和普通
commit 不一样:一旦做了,陌生开发者、搜索引擎、社交平台和 star 曲线都会开始记账。

所以 Agent 的默认顺序是:

1. 先确认本地和远端状态。
2. 再确认 README / demo / release notes / social preview 是否适合陌生人第一眼理解。
3. 再跑当前 release gate。
4. 最后才执行 public / tag / release。

如果任一项不确定,停在可逆步骤,把不确定写进 `STATUS.md` 或 `BLOCKERS.md`,并请求人类确认。

---

## Step 1 — 确认本地和远端状态

先跑:

```bash
git status -sb
git branch --show-current
git remote -v
git tag --list v0.1.0
```

再确认远端 `main` 和 GitHub 仓库状态:

```bash
git fetch origin main
git ls-remote origin main
gh auth status
gh repo view MarcelLeon/ai-company-os --json nameWithOwner,visibility,isPrivate,defaultBranchRef,description,url
gh release list --repo MarcelLeon/ai-company-os --limit 5
```

注意:

- 在 Codex 桌面沙箱里,`gh auth status` 可能读不到 macOS keyring。人类已登录时,可以用
  当前工具的提权方式重试 `gh ...`,不要据此判断人类没有登录。
- 如果仓库仍是 `PRIVATE`,不要创建公开 release 或启动 D0 宣发。
- 如果 `v0.1.0` tag 或 release 已存在,不要重复创建;先读 release 内容和远端 tag SHA。
- 如果工作树不干净,先判断哪些是本轮改动,不要回滚人类或其他 Agent 的改动。

---

## Step 2 — 做公开首印象检查

发布前不要只看测试绿不绿。陌生开发者第一眼主要看这些:

- README 首屏一句话是否说清楚 wedge:用 IM 远程管理本机 AI coding agents。
- 30 秒 no-token demo 是否可复制运行,且输出当前产品动线。
- README GIF 第一帧是否就是产品画面,而不是旧表格、分镜、终端噪音或聊天历史。
- README GIF 是否 30-60 秒内讲完 `/team`、`/remember`、`/ask`、`/approve`、`/overnight`、
  `/morning`、`/audit`;如果本次主推 `/view`,也要给一个清晰镜头。
- GitHub social preview 是否是 `1280 x 640` 左右的静态图,小于 1 MB。不要直接上传 README
  动图当 social preview。
- release notes 是否能独立解释 Added / Fixed / Changed / Verification。

social preview 上传后,用只读检查命令辅助确认 GitHub 不再返回默认仓库卡片:

```bash
uv run aico-github-social-preview
```

`status: needs-owner-upload` 表示仍疑似默认卡片,不能继续 tag / Release。`status: ok`
只说明不再命中默认卡片启发式,发布前仍要肉眼 spot check 一次图像内容。

2026-06-10 的 public 前复核结论:

- `docs/assets/release-room-demo.gif` 已重新生成:约 36 秒、`960 x 540`,首帧明确
  boss-absent 假设,并展示 `/morning` 和 `/view`。
- `docs/assets/social-preview.png` 已生成:GitHub 推荐比例 `1280 x 640`,小于 1 MB。
- 后续如果替换成真实 IM 精剪版,必须保持同等首帧质量、时长和 `/view` 展示。

---

## Step 3 — 跑 release gate

如果本轮改了运行代码,至少跑:

```bash
env -u AICO_VIEW_TOKEN -u AICO_VIEW_ENABLED uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy src tests
git diff --check
```

发布 RC 还要跑:

```bash
env -u AICO_VIEW_TOKEN -u AICO_VIEW_ENABLED uv run pytest \
  tests/unit/test_offline_delegation.py \
  tests/unit/test_task_bus.py \
  tests/unit/test_commands.py \
  tests/unit/test_view_snapshot.py \
  tests/unit/test_view_command.py \
  tests/unit/test_telegram_channel.py -q
uv run pytest tests/unit/test_release_room_acceptance.py tests/unit/test_release_room_demo.py -q
uv run aico-release-room-demo
```

如果本轮只改发布文档,至少跑:

```bash
git diff --check
```

---

## Step 4 — 提交、push、PR 或合并

默认用分支 + PR。只有在人类明确要求收口到 `main`,且当前改动已验证时,才直接推 `main`。

提交前自检:

- 只 stage 本轮需要的文件。
- 没有把 token、聊天导出、私有截图、临时 SQLite、`.env`、provider 日志提交进去。
- `STATUS.md` 和 `docs/journal/ROUNDS.md` 已更新。
- 新踩坑已写入 `docs/journal/PITFALLS.md`。

push 后记录:

- 当前 branch。
- commit SHA。
- GitHub PR URL 或 `main` 远端 SHA。
- CI 状态,或说明本轮没有触发 CI 的原因。

---

## Step 5 — public、tag、release

只有同时满足下面条件,Agent 才能继续 tag / release:

- 人类已明确确认可以公开。
- `gh repo view` 显示 `isPrivate=false`。
- `origin/main` 指向刚验收的 RC commit。
- `git tag --list v0.1.0` 为空,且 `gh release list` 没有 `v0.1.0`。
- README / no-token demo / release notes / GitHub metadata / social preview 已复核。
- `uv run aico-github-social-preview` 不再返回 `status: needs-owner-upload`,且 owner 已肉眼确认 preview 图。

推荐命令:

```bash
git switch main
git pull --ff-only origin main
git tag v0.1.0
git push origin v0.1.0
gh release create v0.1.0 \
  --repo MarcelLeon/ai-company-os \
  --title "v0.1.0 - AI Company OS" \
  --notes-file docs/launch/v0.1.0-release-notes.md
```

如果 tag 或 release 失败,不要删除远端 tag 后重试,除非人类明确要求。先记录失败原因和当前远端状态。

---

## Step 6 — D0 值守

D0 当天只允许:

- blocker bugfix。
- README / release notes / install 命令纠错。
- 安全边界澄清。
- 评论区答疑。

不要在 D0 加大功能。新功能会让 README、release notes、Show HN 首条评论和真实代码继续漂移。

D0 结束前,把这些写回 `STATUS.md` 和 `ROUNDS.md`:

- public 时间。
- tag / release URL。
- CI / release gate 结果。
- 首批反馈中真正需要改的 blocker。
- 没做但容易诱惑下一轮做的事项。
