# Playbook: Phase 8 Offline Delegation Smoke Test

## 适用场景

当 `/overnight`、项目 lead 托管、早报验收路径或离线托管 prompt 变化时,用本 Playbook 验证 Phase 8 第一切片。

## 前置条件

- 已启动 AICO。
- 已配置 `AICO_PROJECT_CONFIG_PATH`,且目标项目有 lead appointment 和 challenger appointment。
- 建议同时配置 `AICO_STATE_DB_PATH`、`AICO_AUDIT_LOG_PATH` 和 `AICO_MEMORY_PATH`,便于重启后恢复托管工单、排障和共享记忆召回。

## 步骤

1. 进入项目办公室。

   ```text
   /project aico
   /team
   ```

   确认输出里有 lead,例如 `implementer -> claude`,且 `team readiness: complete`。
   如果缺 challenger,先执行 `/appoint <agent> as challenger`。

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
   - `morning: /morning` 和 `exact trace: /task <id>`

4. 验证风险门禁。

   如果目标包含写文件、执行命令或破坏性动作,应进入 `Approval required`。此时不要因为它是 `/overnight` 就绕过审批,仍按普通流程 `/approve <task_id>` 或 `/reject <task_id>`。

5. 查看当前托管记录。

   ```text
   /overnight
   ```

   预期能看到当前 active project 下最近的托管工单和早报入口。

6. 早上验收。

   ```text
   /inbox
   /morning
   /task <id>
   ```

   `/inbox` 先接住 approvals、running quiet tasks、failed/interrupted tasks、托管工单、Goal Brief 和 decision follow-up;`/morning` 看 done / blocked / risks / next actions,`/task <id>` 看单任务状态、原始输出和可用动作。

## 验证

- 没有 active project 时,`/overnight <goal>` 提示先 `/project <project>`。
- 有 active project 且 team readiness complete 时,`/overnight <goal>` 派给当前 lead。
- 缺 challenger 时,`/overnight <goal>` 提示补齐 `/appoint <agent> as challenger`,不会派发 Adapter 任务。
- 托管任务 payload 包含 morning handoff 要求。
- 风险任务仍进入 `/approve`。
- `/overnight` 可列出最近托管工单;配置 `AICO_STATE_DB_PATH` 后,重启并重新进入同一 project 后仍可列出。
- `/inbox` 只展示当前 active project 的事项;不会跨项目混入其它 project scope 的 task。
- 长沉默 Adapter 任务应周期性显示 `Still running: no adapter output for <Ns>`,但这只是 quiet heartbeat,不应写入最终决策 memo 或 Goal Brief 输出。

## Lead Decision Workflow 验收

当验证 Stage 3 lead 决策流时,使用同一个 active project 和 team readiness 前置条件。

1. 准备决策上下文。

   - 用 `/team` 确认 lead + challenger ready。
   - 建议已有 `public_broadcast`、`task_key_progress` 或 `decision_review` 记忆;普通 `general_context` 不应进入决策包。

2. 下发明确决策任务给当前 lead。

   ```text
   decide whether release Stage 3 now
   ```

   也可以显式指定 lead role:

   ```text
   /ask <lead-role> decide whether release Stage 3 now
   ```

3. 预期流程。

   - AICO 先派发 challenger consultation。
   - 如果 reviewer 已 appointment,也会派发 reviewer consultation。
   - Lead 最后收到 decision memo prompt,必须输出 Decision、Why、Evidence / memory refs、Consulted roles、Rejected alternatives、Risks / approval need、Next actions。

4. 验证审计和记忆。

   ```text
   /audit
   /recall decision
   /inbox
   ```

   预期 `/audit` 可见 `lead_decision_recorded`;`/recall decision` 可见由该 memo 写回的 `decision_review` memory;`/inbox` 可把 running / failed / decision follow-up 聚到当前项目入口。

## Goal Brief v0 验收

当验证轻量目标契约时,使用同一个 active project 前置条件。Goal Brief v0 不做长期 Ralph loop,只验证 `/goal`、保守 `/ask` 自动附加和 `/task` 可见性。

1. 显式下发可验证目标。

   ```text
   /goal implementer inspect release plan 验收: summarize blockers
   ```

   预期返回:

   - `Goal queued. goal-...`
   - `owner: implementer -> <agent>`
   - `objective: inspect release plan`
   - `acceptance:` 中包含 `summarize blockers`
   - `tracking: /task <id>`

2. 验证 `/ask` 保守升级。

   ```text
   /ask tester run release contract tests, 必须给出通过/失败证据
   ```

   预期返回 `Verifiable task detected. Goal brief attached. goal-...`;如果是普通咨询或头脑风暴,不应自动附加 goal brief。

3. 查看任务详情。

   ```text
   /task <id>
   /goal
   /inbox
   ```

   预期 `/task` 显示 `Goal brief:` 的 id、objective、acceptance;`/goal` 从最近任务中列出 goal brief;`/inbox` 会在 `Decision / goal follow-up` 中列出当前项目 goal task。

## 失败回滚

- 不使用 `/overnight` 即可回到普通 `/ask <role> <task>` 或项目 plain message。
- 不使用 `/goal`,且 `/ask` 文本不写明确验收/停止/证据 marker,即可回到普通 project role task。
- 如果托管 prompt 误触发审批,优先检查 `src/aico/core/offline_delegation.py` 的 `Current task` 文案,不要改 `TextRiskAssessor` 放宽风险规则。
- 如果重启后 `/overnight` 看不到托管记录,先确认启动时仍使用同一个 `AICO_STATE_DB_PATH`,并且重新 `/project <project>` 进入同一项目。

## 相关

- ADR-0024
- ADR-0025
- `src/aico/core/offline_delegation.py`
- `src/aico/core/goal_brief.py`
- `src/aico/core/goal_brief_commands.py`
- `tests/unit/test_orchestrator.py`
