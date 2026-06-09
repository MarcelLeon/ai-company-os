# Playbook: Release Room Demo

## 适用场景

用于向开源用户展示 AI Company OS 的主场景:在 IM 中远程管理一个 AI 团队,
完成小型开源项目的 v0.2 release。

这个剧本不是压力测试,也不是承诺底层 AI 一定一次完成所有实现。它验证的是 AICO
是否能把现实项目协作中的分工、记忆、审批、审计、观测和交接串成一条可管理链路。

## 前置条件

- 已能启动 `aico-phase1`。
- Telegram 或 Feishu 至少一个 Channel 可用。
- Claude Code Adapter 可用。
- Codex Adapter 建议启用,用于 reviewer / tester 角色。

从仓库根目录启动:

```bash
export AICO_TELEGRAM_BOT_TOKEN="your-token"
export AICO_ENABLE_CODEX_ADAPTER=true
export AICO_CLAUDE_WORKING_DIRECTORY="$PWD"
export AICO_PERSONA_CONFIG_PATH="config/personas.example.json"
export AICO_PROJECT_CONFIG_PATH="examples/release-room/aico-project.json"
export AICO_MEMORY_PATH="/tmp/aico-release-room-memory.jsonl"
export AICO_AUDIT_LOG_PATH="/tmp/aico-release-room-audit.jsonl"
env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python /opt/homebrew/bin/python3.11 aico-phase1
```

## 步骤

1. 进入项目办公室:

```text
/use project release-room
/project
/brief
```

预期:看到 Notes CLI Release Room,当前阶段和下一步入口。

2. 查看团队和岗位:

```text
/roles
/team
```

预期:看到 pm、implementer、reviewer、challenger、tester、release-manager 等岗位,
看到当前 lead,并看到 `team readiness: complete`。

3. 写入项目共识:

```text
/remember v0.2 不接受没有测试的功能。
/remember README 必须面向第一次使用 CLI 的开源用户。
/remember release notes 必须包含 Added / Fixed / Changed / Verification。
/recall release notes
```

预期:`/recall` 能召回 release notes 相关共识。后续 project-scoped 任务 prompt
会带入这些记忆。

4. 让 PM 拆解 release:

```text
/ask pm 阅读 STATUS.md 和 issues/003-v02-release.md，把 v0.2 拆成角色任务、验收标准和风险清单。
```

预期:PM 输出 release plan,并应引用 demo repo 中的状态文档和 issue。

5. 让 implementer 开始实现:

```text
/ask implementer 实现 v0.2 的 tags/search/export JSON，修复 unknown id done 的退出码问题，并补测试。
```

预期:如果底层 Adapter 需要写文件或执行命令,AICO 仍按风险策略进入 `/approve`。

6. 让 tester、reviewer 和 challenger 独立验收:

```text
/ask tester 根据 tests/test_v02_contract.py 设计回归验证，运行必要测试并报告失败项。
/ask reviewer review v0.2 改动，重点检查行为回归、测试缺口、README/CHANGELOG 是否一致。
/ask challenger 从反方视角挑战 v0.2 release 方案，重点检查隐藏前提、机会成本和长期维护风险。
```

预期:tester / reviewer 不应只复述 implementer 输出,而应各自给出验证和风险。
challenger 应给出 oppose / conditional support / support 之一,并说明改变判断所需证据。

7. 托管剩余 release 工作:

```text
/overnight 推进 v0.2 release room：收敛实现、测试、文档和 release notes，早上给我 done/blocked/risks/next actions。
```

预期:托管工单派给当前 lead/default role,危险动作仍需审批。

8. 早上验收:

```text
/morning
/tasks
/metrics
/audit
```

预期:

- `/morning` 给出 done / blocked / risks / next actions。
- `/tasks` 能看到 pm、implementer、tester、reviewer、overnight 等任务。
- `/metrics` 能看到 open work、完成和失败概况。
- `/audit` 能看到审批、派发、完成、失败和协作事件。

## 录屏建议

先看 [`examples/release-room/transcript.md`](../../examples/release-room/transcript.md)
确认无 token 的本地验收路径,再按
[`examples/release-room/shot-rhythm.md`](../../examples/release-room/shot-rhythm.md)
压缩镜头节奏,最后录真实 IM。

录屏不要展示底层 AI 长文本细节,重点展示管理面:

1. 进入 project office,显示 `/team`。
2. 写入三条 `/remember`,随后 `/ask pm` 自动使用项目共识。
3. Implementer 触发审批,老板用 `/approve`。
4. Reviewer / tester / challenger 独立验收。
5. `/overnight` 后用 `/morning` 收早报。
6. 最后用 `/audit` / `/task` 证明可追溯。

如果没有 GIF 转换工具,但本机有 `ffmpeg`,录出 `.mov` 或 `.mp4` 后执行:

```bash
bash examples/release-room/make-gif.sh /path/to/recording.mov docs/assets/release-room-demo.gif
```

## 验证

- Project config 能被 `ProjectAssignmentConfig` 加载。
- 示例仓库存在 `NORTH_STAR.md`、`STATUS.md`、`docs/journal/*` 和 v0.2 issue。
- Stage 2 本地 transcript 覆盖团队、记忆、审批、托管、早报、任务、指标和审计。
- `/team` 展示 lead 和多 role appointment。
- `/team` 展示 challenger,且 team readiness complete。
- `/remember` 的 project-scoped 记忆能被后续 project task 召回。
- 危险动作不会因为 demo 或 `/overnight` 绕过审批。
- 早报不是营销文案,必须列出 done、blocked、risks、next actions。

## 失败回滚

- 如果 Codex 未启用,先把 reviewer / tester 临时 `/appoint claude as reviewer` 和
  `/appoint claude as tester`,但录屏脚本应标注这是单 Adapter fallback。
- 如果 `AICO_MEMORY_PATH` 未配置,`/remember` 会提示重启配置;设置后重启进程。
- 如果真实 AI 输出过长或卡住,用 `/interrupt <task_id>` 中断,再用 `/task <task_id>`
  记录状态。

## 相关

- [`docs/examples/release-room.md`](../examples/release-room.md)
- [`examples/release-room/demo-script.md`](../../examples/release-room/demo-script.md)
- ADR-0011 Project Assignment Layer
- ADR-0020 Phase 7 Shared Memory Scope
- ADR-0024 Phase 8 Offline Delegation Scope
