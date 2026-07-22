# Goal Brief: Standing Result Contract

## Goal

让 owner-preauthorized standing inspection 的“运行完成”和“结果可接受”成为两个可持久、可恢复、可停授的状态，
避免老板缺席时空泛或无证结果继续触发下一轮自治。

## In scope

- Codex `--output-schema`固定结果形状。
- charter acceptance/stop 条目编号与精确覆盖。
- repository-relative file/line 存在性校验。
- complete/blocked/invalid 本地一致性判定与 durable proposal receipt。
- inbox/morning bounded outcome projection；不健康结果阻断后续 run。

## Out of scope

- LLM 二次 grader、联网事实核验、语义真实性证明。
- 自动重试、授权退款、写文件或外部动作。
- 当前 run 的硬 token/cost cap 或 provider 账单证明。

## Acceptance

1. 合法 complete 与 blocked 可区分并跨 SQLite restart 保留。
2. invalid JSON、charter coverage drift、越界/缺失 source、状态矛盾全部 fail closed。
3. raw JSON 不进入老板 IM；回执只显示 outcome、coverage 与 source count。
4. prior missing/invalid/blocked result 不会继续 dispatch。
5. schema 随 wheel 打包，相关测试、Ruff、mypy、结构硬约束与整仓 gate 通过。

## Stop conditions

- 不把本地 file/line 存在性写成语义正确或真实业务验收。
- 不为结果验证增加第二次付费 provider 调用。
- 不把 post-run token receipt 写成当前 run 硬预算。
