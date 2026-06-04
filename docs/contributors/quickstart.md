# Contributor Quickstart

> 30 分钟内,在自己的 Mac 或 Linux 上跑通 AI Company OS,并完成一次能 PR 的最小贡献。

如果你的目标是先理解项目而不是写代码,直接读
[`README.md`](../../README.md) → [`docs/examples/release-room.md`](../examples/release-room.md)
→ [`docs/architecture/boss-first-grounding.md`](../architecture/boss-first-grounding.md)
就够。

如果你打算贡献代码,本指南帮你少走弯路。

## 0. 你只需要

- macOS 或 Linux
- Python 3.11+
- [`uv`](https://github.com/astral-sh/uv)
- 30 分钟空余时间

> Telegram bot token、Claude / Codex 账号都 **不是必需**。第一次 PR 完全可以基于
> deterministic fake adapters 完成。

## 1. Fork、clone、装依赖(5 分钟)

```bash
gh repo fork MarcelLeon/ai-company-os --clone --remote
cd ai-company-os
env UV_CACHE_DIR=/tmp/aico-uv-cache uv sync --python 3.11
```

跑一次 no-token demo 验证环境能跑:

```bash
env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python 3.11 aico-release-room-demo
```

终端应看到 `/team`、`/remember`、`/ask`、`/approve`、`/overnight`、`/daily` 等命令的完整
transcript。看到这一段说明本机环境就绪。

## 2. 跑测试基线(2 分钟)

```bash
env -u AICO_VIEW_TOKEN -u AICO_VIEW_ENABLED uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy src tests
```

四个命令都应该通过。如果有失败,先把失败修复或在 Issue 里反馈,这本身已经是一次有价值的
PR。

## 3. 选一个能在 30 分钟内做完的小任务(15 分钟)

**最容易上手的任务类型**:

| 类型 | 看哪些文件 | 适合谁 |
|---|---|---|
| 修复一个 PITFALL 文档错别字、补 PITFALL 的"如何避免" | `docs/journal/PITFALLS.md` | 第一次提交 PR |
| 给一个内置命令加更友好的错误提示 | `src/aico/core/orchestrator.py` + `src/aico/core/command_messages.py` | 想了解命令分发的人 |
| 给 README 中文版补一个英文版已有的小节 | `README.zh-CN.md` | 双语贡献者 |
| 写一个新 Adapter (Cursor 已有,Aider 没有) | `docs/agent/adapter-authoring.md` + `src/aico/adapter/cursor.py` | 想接入自家 CLI 的人 |
| 给 `aico-glance` 增加一个 JSON 字段 | `src/aico/core/metrics.py` | Python 数据结构爱好者 |

挑一个开始。如果不知道怎么选,在 Issue 里写 `looking for a starter task: <你想擅长的方向>`,
我们会指一个。

## 4. 写代码 + 测试(8 分钟)

AICO 的硬约束:

- 单类 < 500 行,单方法 < 100 行
- 任何新 Adapter / Channel 都必须实现 Protocol,不准在 core 写 `if tool == "xxx"`
- 必须有单测;Adapter / Channel 必须用 `unittest.mock.AsyncMock` mock 子进程或 HTTP

最容易复用的测试模板:`tests/unit/test_orchestrator.py` 里有约 80 个 fake-adapter
端到端测试,直接拷贝最接近的一个改起。

跑你刚改的那一组测试:

```bash
uv run pytest tests/unit/test_<file>.py -k <test_name>
```

## 5. 自查清单(在你 push 之前做)

- [ ] `uv run pytest` 全部通过
- [ ] `uv run ruff check .`、`uv run ruff format --check .`、`uv run mypy src tests` 通过
- [ ] `STATUS.md` 已追加一行 "Round N+1" 简述本轮做了什么
- [ ] `docs/journal/ROUNDS.md` 已追加一段(包括"为什么没选另一种方案")
- [ ] 如果踩到新坑,`docs/journal/PITFALLS.md` 已记录
- [ ] PR 描述回答了 "对应 NORTH_STAR.md 的哪一句"

完整模板见 [`.github/PULL_REQUEST_TEMPLATE.md`](../../.github/PULL_REQUEST_TEMPLATE.md)。

## 6. 提交 PR

```bash
git checkout -b <kebab-case-feature>
git add ...
git commit -m "feat(scope): subject"
gh pr create --fill
```

CI 会跑 `pytest` / `ruff` / `mypy`。绿灯之后,等 reviewer 拉过去看就行。

## 7. 想做大点儿的工作?

读这两篇再动手:

- [`AGENTS.md`](../../AGENTS.md) — 老 AI / 新 AI 接手项目的入口
- [`docs/agent/02-coding-standards.md`](../agent/02-coding-standards.md)
- [`docs/agent/03-design-patterns.md`](../agent/03-design-patterns.md)

如果你的工作要新增一个 Adapter、Channel 或 storage backend,先开 ADR 草案
(`docs/decisions/`) 比较省时间——避免实现完才发现方向不对。

## 8. 我卡住了

- 看 [`docs/journal/PITFALLS.md`](../journal/PITFALLS.md);90% 的"奇怪报错"都已经被前人踩过。
- 看 [`docs/journal/ROUNDS.md`](../journal/ROUNDS.md);重大决策为什么这样定都写在那里。
- 仍然不行,直接开 Issue,标题里带 `[help wanted]`。

## 9. 我想成为 maintainer

提 5 个能合并的 PR + 在 Issue / discussion 里持续回复别人 6 周以上,我们会给你 maintainer
权限。这条标准刻意写明,避免不透明。

---

欢迎来。
