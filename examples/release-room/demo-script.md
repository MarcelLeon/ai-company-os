# Release Room Demo Script

这个脚本用于 Telegram/Feishu 录屏。每一步都要让用户看到 AICO 的管理面,而不是只看
底层 AI 输出。

## 0. 启动

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

## 1. 打开项目办公室

```text
/use project release-room
/project
/roles
/team
```

镜头重点:

- 用户看到这是一个 release 项目,不是普通 chat。
- `/team` 显示 pm、implementer、tester、reviewer、release-manager。
- lead 是 pm,普通消息不会乱派给任意 agent。

## 2. 建立团队共识

```text
/remember v0.2 不接受没有测试的功能。
/remember README 必须面向第一次使用 CLI 的开源用户。
/remember release notes 必须包含 Added / Fixed / Changed / Verification。
/recall release notes
```

镜头重点:

- 记忆不是老板手动维护数据库,而是项目团队共识。
- 后续 role task 会自动带入这些共识。

## 3. 让 PM 拆解工作

```text
/ask pm 阅读 STATUS.md 和 issues/003-v02-release.md，把 v0.2 拆成角色任务、验收标准和风险清单。
```

镜头重点:

- PM 不写代码,只拆范围、验收、风险和交接。
- 输出中应包含 implementer/tester/reviewer/release-manager 分工。

## 4. 并行派工

```text
/ask implementer 实现 v0.2 的 tags/search/export JSON，修复 unknown id done 的退出码问题，并补测试。
/ask tester 根据 tests/test_v02_contract.py 设计回归验证，运行必要测试并报告失败项。
/ask reviewer review v0.2 release 风险，重点检查行为回归、测试缺口和 README/CHANGELOG 一致性。
```

镜头重点:

- 实现、测试、review 是不同 role,不是同一个输出冒充全流程。
- 写文件或执行命令需要审批时,用 `/approve` 展示安全边界。

## 5. 创建一个临时岗位

```text
/role propose 需要一个 release captain，负责最终发布检查、release notes 和 go/no-go 建议。
/role confirm
/roles
```

镜头重点:

- 新岗位由 lead 起草,老板确认,不是系统静默变更组织结构。
- 这一步可选;如果录屏太长,可以放到长版 demo。

## 6. 离线托管

```text
/overnight 推进 v0.2 release room：收敛实现、测试、文档和 release notes，早上给我 done/blocked/risks/next actions。
```

镜头重点:

- `/overnight` 是托管工单,不是越权脚本。
- 危险动作仍需审批。

## 7. 早报验收

```text
/daily release-room
/tasks
/metrics
/audit
```

镜头重点:

- `/daily` 是老板早上真正要看的东西。
- `/tasks` 和 `/task` 能追踪每个 role 的具体工作。
- `/audit` 证明 AI 行为不是黑箱。

