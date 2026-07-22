# ADR-0055: Repository-grounded Standing Result Contract

**状态**:Accepted
**日期**:2026-07-21
**决策者**:Codex / Round 217

## 背景

Round 215/216 已能证明预授权任务的 transport 终态与 provider usage，但 `TaskStatus.DONE` 仍只表示进程正常结束。
一段空泛、blocked、自相矛盾或引用不存在文件的正文也可能被显示成 done，不足以支持老板缺席后的继续自治。

Codex CLI 提供 `exec --output-schema`，可以约束最终消息形状；但官方维护者已明确移除并暂无计划恢复可配置的
`model_max_output_tokens`，因此本轮不能把结果合同包装成单次硬 token SLA：
[openai/codex#4138](https://github.com/openai/codex/issues/4138)。

## 决策

1. owner-preauthorized Codex 固定命令必须加载仓库内 versioned JSON Schema，并只接受 JSON 最终结果。
2. prompt 将 charter acceptance/stop 条目稳定编号为 `A1..An`、`S1..Sn`；本地校验要求编号和顺序精确覆盖。
3. 每个 acceptance 条目必须给出 repository-relative path 与 1-based line；本地只验证路径未越界、文件与行存在。
4. `complete` 仅在全部 criteria 为 met 且 gaps 为空时成立；否则只能是带 gap 的 `blocked`。矛盾结果记为
   `invalid`。
5. proposal 持久化 bounded result receipt，不保存第二张 outcome 表，也不把 provider 原始 JSON 写入老板 IM。
6. transport status 与 outcome status 分离。prior result missing/invalid/blocked 时，下一 scheduled run fail closed。
7. `/inbox`、`/morning`展示 outcome、criteria coverage、verified source count；不展示原始正文、完整身份或路径。

## 否决方案

- **把 DONE 当验收通过**：只能证明 TaskBus 完成，不能证明 charter 结果。
- **再调用一个 LLM grader**：增加无人成本与第二个不确定结果，且 standing boundary 明确禁止协作扩张。
- **只依赖 JSON Schema**：schema 能约束形状，不能验证 charter 数量、complete 一致性或本地证据存在。
- **声称 source 存在即语义真实**：文件/行存在不是业务事实、时效性或论证正确性的证明。
- **invalid/blocked 自动重试**：会在结果不健康时继续消耗授权与 provider 成本。

## 后果

### 正面

- 老板视图不再把 transport done 冒充业务通过，重启后仍可重建结果合同状态。
- provider 漂移、崩溃缺证、blocked 与引用越界都会停止后续无人执行。
- 原始结构化输出不进入 IM，只暴露 bounded、可恢复的回执。

### 代价与剩余风险

- 本地 source verifier 只证明文件位置存在，不证明内容足以支持 criterion；真实业务验收仍需 owner sample。
- Codex schema/CLI 行为必须在 B-014 的真实版本与付费样本中验证。
- 单次 token/cost 硬上限仍不存在，继续沿用 Round 216 的 post-run cumulative circuit breaker。

## 验证

- 单测覆盖 complete、blocked、invalid JSON、条目错位、stop mismatch、路径穿越、绝对路径、缺文件/缺行和结果矛盾。
- orchestration E2E 覆盖 schema prompt、raw JSON suppression、durable receipt、boss view 与下一 run fail closed。
- wheel 检查必须确认 versioned schema 被打包。
