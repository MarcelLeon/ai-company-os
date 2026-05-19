# BLOCKERS.md — 卡点难题

> 当前未解决的卡点。**Agent 接手时,如果能解决其中任何一个,这是最高优先级**。
>
> 卡点和 PITFALLS 的区别:
> - PITFALLS = 已经踩了的坑(向后看,记录历史)
> - BLOCKERS = 还没解决但已挡住进度的问题(向前看,等待解决)

---

## 状态图例

- 🔴 **BLOCKING** — 当前直接挡住下一步进度
- 🟡 **DEFERRED** — 不立即挡路但需要在某个 Phase 之前解决
- 🟢 **RESOLVED** — 已解决(归档保留以供回溯)

---

## 当前活跃卡点

### [B-003] Release Room Stage 3 真实 provider 输出不适合作为 public GIF

**状态**:🟡 DEFERRED
**提出于**:Round 91
**最后更新**:2026-05-18(Round 92)
**影响**:不再阻塞 Codex 短输出镜头;仍不建议把 Claude/Codex 长输出直接录成 README GIF。

**问题描述**
真实 Telegram dogfooding 已跑通 project office、team、project memory、interrupt 等管理链路。第一轮发现底层 provider 输出不适合入镜:
- Claude CLI 在当前无 Pro / 输出不稳定环境下长时间不回包。
- Codex CLI 输出包含大量 plugin warning、HTML 片段和 thread resume 错误,会污染 Telegram 画面。

Round 92 已修复 Codex 侧主要问题:
- Codex Adapter 不再 resume 非 Codex provider session。
- 同一 role 重新任命给不同 agent 时,assignment session 会重建,避免沿用旧 provider session。
- Codex stdout 会过滤典型 CLI warning、HTML 片段、`sqlx::query` 噪音和 thread resume error。
- 真实 Telegram dry run 已验证 Codex PM 3-bullet 输出干净可入镜。

**已尝试的方向**
- 方向 A:直接用 Claude 做 PM 拆工。结果任务 accepted 后长时间无输出,需要 `/interrupt`。
- 方向 B:临时把 PM 任给 Codex。结果 Telegram 收到大量 CLI warning / HTML / resume error,无法作为 public GIF。
- 方向 C:修 Codex provider session 和 stdout 过滤后重测。结果 Codex PM 短输出可用。

**需要什么才能解开**
- 如要拍 Claude 实现长输出,仍需确认 Claude 当前登录/额度稳定,或只拍 approval gate 不拍长输出。
- 真实录屏前继续跑 `/ask pm ...` dry run,确保首屏是 role handoff 摘要。

**当前 workaround**
- README public GIF 可以使用真实 Telegram + Codex 短输出镜头。
- Claude 只用于 approval gate / implementer 任务 accepted 画面,不要把长输出作为主镜头。

**相关链接**
- ROUNDS Round 91
- PITFALL P-017

---

## 已归档卡点

### [B-002] AI 间协作协议形态待定

**状态**:🟢 RESOLVED(ADR-0009 Accepted)
**提出于**:Round 1
**最后更新**:2026-04-28
**影响**:曾阻塞 Phase 5 启动;Round 19 已确定最小协议形态

**问题描述**
当 AI A 想 @ AI B 协作时,通信机制是什么?
- 选项 1:走 IM 消息总线(AI A 在群里发消息,AI B 监听)→ 简单但耦合 IM
- 选项 2:走内部 Agent2Agent 协议(类似 A2A 标准)→ 解耦但复杂
- 选项 3:走 RPC 调用 → 失去"群聊感"

**已尝试的方向**
- Phase 1-4 暂时绕开了 AI 间协作,只做“人类 → 单/多 Adapter”任务派发。
- Round 18 后 Phase 4 收口,该问题从延后卡点升级为 Phase 5 入口卡点。
- Round 19 选择内部 A2A-inspired 轻量协作指令:`@persona: request`,暂不直接实现 HTTP A2A,也不把 IM 当内部总线。

**需要什么才能解开**
- 已解决:见 ADR-0009 和 `docs/playbooks/phase-5-collaboration.md`。

**当前 workaround**
- 无。

**相关链接**
- ADR-0009
- ROUNDS Round 19

### [B-001] 技术栈选型

**状态**:🟢 RESOLVED(ADR-0001 Accepted)
**提出于**:Round 1
**最后更新**:2026-04-27
**影响**:曾阻塞所有后续编码工作

**问题描述**
编排核心使用 Java / Python / TypeScript 中的哪一个尚未决定。每种都有取舍:
- Java + Spring AI:Wang 已有 `claw-code-java` 经验,但 AI CLI 生态对 Java 支持薄弱
- Python + FastAPI:AI 生态最成熟,但 Wang 的 Java 经验复用有限
- TypeScript + Node:接 Telegram Bot / 各 AI CLI 最丝滑,但偏离 Wang 主战场

**已尝试的方向**
- Round 2 人类明确偏向 Python 技术栈,主要原因是不选 Java:代码量偏多、维护负担偏高。
- Round 2 Agent 初步建议:核心用 Python 3.11+、FastAPI、asyncio、Pydantic v2、typing.Protocol、pytest/ruff/mypy。
- Round 3 已写 ADR-0001 并接受 Python 技术栈,同时创建 `pyproject.toml` 和最小 Python 骨架。

**需要什么才能解开**
- 已解决:见 `docs/decisions/0001-tech-stack-selection.md`。

**当前 workaround**
- 无。后续编码默认使用 ADR-0001 的 Python 技术栈。

**相关链接**
- STATUS.md 下一轮建议 #1
- ADR-0001

---

## 模板(新增卡点用)

```markdown
### [B-XXX] 卡点简短标题

**状态**:🔴 BLOCKING / 🟡 DEFERRED / 🟢 RESOLVED
**提出于**:Round N
**最后更新**:YYYY-MM-DD
**影响**:具体挡住了什么

**问题描述**
详细说明这是什么卡点。

**已尝试的方向**
- 方向 A:为什么没成
- 方向 B:为什么没成

**需要什么才能解开**
- 具体可执行的步骤

**当前 workaround**
- 现在用什么临时方案绕开

**相关链接**
- ROUNDS / PITFALLS / ADR
```
