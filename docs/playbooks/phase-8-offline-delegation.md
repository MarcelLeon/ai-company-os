# Playbook: Phase 8 Offline Delegation Smoke Test

## 适用场景

当 `/overnight`、项目 lead 托管、早报验收路径或离线托管 prompt 变化时,用本 Playbook 验证 Phase 8 第一切片。

## 前置条件

- 已启动 AICO。
- 已配置 `AICO_PROJECT_CONFIG_PATH`,且目标项目有 appointment。
- 建议同时配置 `AICO_AUDIT_LOG_PATH` 和 `AICO_MEMORY_PATH`,便于重启后排障和共享记忆召回。

## 步骤

1. 进入项目办公室。

   ```text
   /project aico
   /team
   ```

   确认输出里有 lead/default role,例如 `implementer -> claude`。

2. 下发离线托管目标。

   ```text
   /overnight 梳理 Phase 8 下一步,早上给我 done/blocked/risks/next actions
   ```

3. 验证系统返回托管工单。

   预期包含:
   - `Overnight delegation queued: night-...`
   - `project: aico`
   - `lead: <role> -> <agent>`
   - `tracking: /task <id>`
   - `Morning: /daily aico` 和 `/tasks`

4. 验证风险门禁。

   如果目标包含写文件、执行命令或破坏性动作,应进入 `Approval required`。此时不要因为它是 `/overnight` 就绕过审批,仍按普通流程 `/approve <task_id>` 或 `/reject <task_id>`。

5. 查看当前托管记录。

   ```text
   /overnight
   ```

   预期能看到当前 active project 下最近的托管工单和早报入口。

6. 早上验收。

   ```text
   /daily aico
   /tasks
   /task <id>
   ```

   `/daily` 看项目级进展和风险,`/tasks` 找最近工单,`/task <id>` 看单任务状态和可用动作。

## 验证

- 没有 active project 时,`/overnight <goal>` 提示先 `/project <project>`。
- 有 active project 时,`/overnight <goal>` 派给当前 lead/default role。
- 托管任务 payload 包含 morning handoff 要求。
- 风险任务仍进入 `/approve`。
- `/overnight` 可列出当前进程内最近托管工单。

## 失败回滚

- 不使用 `/overnight` 即可回到普通 `/ask <role> <task>` 或项目 plain message。
- 如果托管 prompt 误触发审批,优先检查 `src/aico/core/offline_delegation.py` 的 `Current task` 文案,不要改 `TextRiskAssessor` 放宽风险规则。
- 如果需要重启恢复托管记录,先用 `/tasks` / audit JSONL 排障;持久化托管记录留给后续 Phase 8 切片。

## 相关

- ADR-0024
- `src/aico/core/offline_delegation.py`
- `tests/unit/test_orchestrator.py`
