# CONTRIBUTING.md

> 不论你是人还是 AI,提交代码前请通读本文。

> 我们遵循 [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md);参与本项目即表示
> 你同意在所有交流场景中遵守该守则。

## First-time contributors / 首次贡献者

新手最容易上手的两条路径:

1. **No-token Release Room demo** —
   `env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python 3.11 aico-release-room-demo`,
   不需要 Telegram bot token、Claude/Codex 账号或任何付费 API,即可看到完整产品流。
2. **good-first-issue** —
   见 [GitHub good first issue 列表](https://github.com/MarcelLeon/ai-company-os/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22)
   或 [`docs/contributors/quickstart.md`](docs/contributors/quickstart.md) 中精选的 30 分钟可完成任务。

写新 Adapter 之前请先读 [`docs/agent/adapter-authoring.md`](docs/agent/adapter-authoring.md)。

---

## 提交前必答三问

1. 这次变更对应 [`NORTH_STAR.md`](NORTH_STAR.md) 三句话的哪一句?
2. 我有没有在 [`docs/journal/PITFALLS.md`](docs/journal/PITFALLS.md) 检查过相关坑?
3. 完成后我有没有更新 [`STATUS.md`](STATUS.md) 和 [`docs/journal/ROUNDS.md`](docs/journal/ROUNDS.md)?

任何一问回答"否",请先处理再提交。

---

## Commit 规范

采用 [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

**type**:
- `feat`:新功能
- `fix`:bug 修复
- `docs`:仅文档变更
- `refactor`:不改变行为的重构
- `test`:新增/修改测试
- `chore`:构建、工具、依赖
- `adr`:新增架构决策记录

**scope** 示例:
- `core`:编排核心
- `adapter`:AI 适配器
- `channel`:IM 通道
- `persona`:人格化
- `approval`:审批流
- `journal`:演化日志

**示例**:
```
feat(adapter): add Claude Code adapter MVP

Implements AIAdapter interface with receive_task, stream_output,
report_status. Tested against Claude Code CLI v1.x.

Refs: STATUS.md Phase 1
```

---

## PR 规范

每个 PR 必须包含以下章节(可复制 PR 模板):

```markdown
## 北极星对齐
本变更对应 NORTH_STAR.md 的第 X 句,因为 ...

## 变更摘要
- 做了 A
- 改了 B

## 自检清单
- [ ] 单类 < 500 行,单方法 < 100 行
- [ ] 新增/修改的接口都有抽象
- [ ] 单测覆盖 ≥ 80%
- [ ] 已更新 STATUS.md
- [ ] 已更新 ROUNDS.md
- [ ] 如踩新坑已记入 PITFALLS.md
- [ ] 如有架构决策已写 ADR

## 风险与回滚
- 风险:...
- 回滚:`git revert <sha>` 即可,或 ...
```

---

## 代码风格

详见 [`docs/agent/02-coding-standards.md`](docs/agent/02-coding-standards.md)。

核心硬约束:
- 单类 < 500 行
- 单方法 < 100 行
- 面向接口编程
- 可插拔/插件化

---

## 抽象时机

不要过早抽象。详见 [`docs/agent/03-design-patterns.md`](docs/agent/03-design-patterns.md)。

经验法则:
- **第 1 次写**:直接写,不抽象
- **第 2 次写**:复制粘贴,标记 TODO
- **第 3 次写**:这时再抽象

"Rule of three" 是底线,不是上限。

---

## 测试要求

详见 [`docs/agent/06-testing-guide.md`](docs/agent/06-testing-guide.md)。

- 核心模块单测覆盖率 ≥ 80%
- Adapter / Channel 必须有 mock 测试
- 集成测试针对每条端到端链路至少一个

---

## 文档更新义务

任何代码变更涉及以下情况必须同步更新文档:

| 变更类型 | 必须更新 |
|---|---|
| 任何代码变更 | `STATUS.md` + `docs/journal/ROUNDS.md` |
| 新增/修改架构决策 | `docs/decisions/` 加 ADR |
| 踩了新坑 | `docs/journal/PITFALLS.md` |
| 遇到无法解决的卡点 | `docs/journal/BLOCKERS.md` |
| 新增运维操作 | `docs/human/daily-ops.md` |
| 修复了 troubleshooting 里的问题 | `docs/human/troubleshooting.md` 标记已解决 |

---

## 不被接受的提交

- 没有单测的新功能
- 单类 > 500 行 / 单方法 > 100 行(除非有 ADR 论证为何例外)
- 任何 `if (tool == "xxx")` 这类硬编码 AI 名字的代码
- 范围蔓延(任务是 A,顺手改了无关的 B)
- 没更新文档的代码变更
- 用 `// TODO` / `// FIXME` 把问题藏起来不写到 BLOCKERS 的
