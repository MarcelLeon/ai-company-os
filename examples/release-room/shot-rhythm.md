# Release Room Shot Rhythm

目标:把 `transcript.md` 压成 30-60 秒 README GIF。观众应该在第一遍就看懂:

- AICO 是远程项目办公室,不是多 AI 转发器。
- AI 被任命到真实项目岗位:PM、实现、测试、评审、发布。
- 记忆、审批、审计和早报是管理面的一部分,不是装饰。

## 录制原则

- 拍管理动作,不拍长篇 AI 输出。
- 每个镜头只保留 1 个主信息点。
- 命令可以粘贴,不需要慢慢打字。
- AI 回复只保留首屏摘要;长输出用剪切跳过。
- README GIF 优先 45 秒左右;长版视频可以保留 70-90 秒。
- 如果真实 Claude CLI 额度不足,先用 Stage 2 transcript 做无 token 展示稿;真实 IM 录屏只作为 dogfooding 证据补拍。

Round 148 已用 `generate-public-gif.py` 生成 transcript-driven public GIF:
`docs/assets/release-room-demo.gif` 约 36 秒、`960 x 540`,首帧为当前 IM 产品画面,并展示
`/morning` 和 `/view`。同轮还生成 `docs/assets/social-preview.png` 用于 GitHub Social preview。

## README GIF 节奏

| 时间 | 镜头 | 保留的 transcript 内容 | 画面重点 | 字幕 |
|---|---|---|---|---|
| 0-5s | Project Office | `/use project release-room` + `/team` | 项目名、team、lead: pm | Open a release room from IM. |
| 5-12s | Shared Memory | 3 条 `/remember` + `Memory saved` | 团队规则被写入项目共识 | Shared memory keeps team rules alive. |
| 12-20s | PM Split | `/ask pm ...` + release plan 一行摘要 | PM 拆成 implementer/tester/reviewer/release-manager | Turn a goal into role-based work. |
| 20-30s | Approval Gate | `/ask implementer ...` + `Approval required` + `/approve` | 写文件/跑测试要审批 | Risky actions still need approval. |
| 30-39s | Independent Checks | `/ask tester ...` + `/ask reviewer ...` | 测试和 review 分离 | Testing and review are separate jobs. |
| 39-48s | Overnight | `/overnight ...` + morning handoff 摘要 | 睡前派工,早上有交接 | Wake up to a handoff. |
| 48-58s | Traceability | `/morning` + `/view` + `/audit` | handoff / HTML snapshot / audit events | No mystery work. Every action is traceable. |

## 精简命令清单

录 GIF 时只发下面这些,避免把画面拖长:

```text
/use project release-room
/team
/remember v0.2 不接受没有测试的功能。
/remember README 必须面向第一次使用 CLI 的开源用户。
/remember release notes 必须包含 Added / Fixed / Changed / Verification。
/ask pm 阅读 STATUS.md 和 issues/003-v02-release.md，把 v0.2 拆成角色任务、验收标准和风险清单。
/ask implementer update src/notes_cli/__main__.py, README and CHANGELOG, then run pytest for v0.2.
/approve
/ask tester 检查 tests/test_v02_contract.py 的回归策略并报告失败项。
/ask reviewer review v0.2 release risk, test gaps, README and CHANGELOG consistency.
/overnight 推进 v0.2 release room，早上给我 done/blocked/risks/next actions。
/morning
/view
/audit
```

## 画面取舍

保留:

- `/team` 中的 `lead: pm -> claude`。
- `/remember` 的三次 `Memory saved`。
- PM 输出中的四类 role handoff。
- `Approval required` 和 `/approve` 这组安全边界。
- tester / reviewer 的不同结论。
- `/morning` 的 Done / Blocked / Risks / Next actions。
- `/view` 发送的只读 HTML snapshot 附件或降级提示。
- `/audit` 中的 `approval_requested` / `approval_approved` / `task_completed`。

删掉:

- `/project`、`/roles`、`/metrics` 的完整输出;它们适合长版视频,不适合 README GIF。
- 底层 AI 大段推理或代码 diff。
- 等待真实 CLI 输出的空白时间。
- role proposal;这是长版 demo 的可选镜头。

## 真实 IM 录制建议

首选 Telegram App。窗口宽度控制在 900-1100 px,字体放大到观众能看清命令和首行回复。

Round 91 真实 dogfooding 发现:provider 原始输出不能不加处理直接作为 public GIF。
Round 92 修复后,Codex PM 短输出已经能干净入镜;Claude 在无 Pro 环境下仍可能长时间
不回包,因此 Claude 镜头优先拍 approval gate / task accepted,不要拍长输出。

如果 Claude CLI 没有 Pro 或额度不稳定:

- PM / implementer 可以先用短 prompt,只要求摘要和交接,不要要求真实大改代码。
- tester / reviewer 可以优先走 Codex。
- 真正的 README GIF 可以先使用 Stage 2 transcript 驱动的稳定内容;真实 IM 录屏用于后续补充 dogfooding 证据。

## GIF 交付路径

稳定 transcript-driven 资产可直接生成:

```bash
python3 examples/release-room/generate-public-gif.py
```

README GIF 最终产物放在:

```text
docs/assets/release-room-demo.gif
```

GitHub Social preview 推荐上传:

```text
docs/assets/social-preview.png
```

README 首屏引用:

```markdown
![Release Room demo](docs/assets/release-room-demo.gif)
```
