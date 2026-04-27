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

### [B-001] 技术栈选型

**状态**:🟡 DEFERRED(必须 Phase 1 之前解决)
**提出于**:Round 1
**最后更新**:2026-04-26
**影响**:阻塞所有后续编码工作

**问题描述**
编排核心使用 Java / Python / TypeScript 中的哪一个尚未决定。每种都有取舍:
- Java + Spring AI:Wang 已有 `claw-code-java` 经验,但 AI CLI 生态对 Java 支持薄弱
- Python + FastAPI:AI 生态最成熟,但 Wang 的 Java 经验复用有限
- TypeScript + Node:接 Telegram Bot / 各 AI CLI 最丝滑,但偏离 Wang 主战场

**已尝试的方向**
- Round 2 人类明确偏向 Python 技术栈,主要原因是不选 Java:代码量偏多、维护负担偏高。
- Round 2 Agent 初步建议:核心用 Python 3.11+、FastAPI、asyncio、Pydantic v2、typing.Protocol、pytest/ruff/mypy。该建议尚未写成 ADR,因此本卡点未关闭。

**需要什么才能解开**
- 列清楚每个 AI CLI(Claude Code、Codex、OpenClaw、内部 CLI)各语言下的接入成本
- 评估 IM 通道(Telegram、飞书、QQ)各语言下的 SDK 成熟度
- 写成 ADR-001

**当前 workaround**
- 文档先写,代码不动,等 ADR-001 正式确认 Python 技术栈后再创建代码骨架

**相关链接**
- STATUS.md 下一轮建议 #1

---

### [B-002] AI 间协作协议形态待定

**状态**:🟡 DEFERRED(Phase 5 之前解决即可)
**提出于**:Round 1
**最后更新**:2026-04-26
**影响**:不阻塞 Phase 1-4,但 Phase 5(AI 间协作)之前必须有方向

**问题描述**
当 AI A 想 @ AI B 协作时,通信机制是什么?
- 选项 1:走 IM 消息总线(AI A 在群里发消息,AI B 监听)→ 简单但耦合 IM
- 选项 2:走内部 Agent2Agent 协议(类似 A2A 标准)→ 解耦但复杂
- 选项 3:走 RPC 调用 → 失去"群聊感"

**已尝试的方向**
- (无)

**需要什么才能解开**
- 调研 A2A、ACP 等开放协议的成熟度
- 跑一个最小 demo:AI A 发消息 → AI B 接收 → AI B 处理 → 返回到群

**当前 workaround**
- Phase 1-4 均不依赖此协议,先单 AI 跑通

---

## 已归档卡点

(暂无)

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
