# ADR-0001: 技术栈选型

**状态**:Accepted
**日期**:2026-04-27
**决策者**:Wang / Codex(协作)
**相关 Round**:Round 3

---

## 背景与问题

Phase 1 需要跑通"Telegram -> 编排核心 -> Claude Code -> Telegram"的最小链路。进入编码前必须先确定编排核心技术栈,否则 Adapter、Channel、配置、测试和部署约定都会分叉。

项目北极星要求协议优先、AI 适配器化、状态可观测、能力可插拔。因此技术栈要优先服务异步 IO、CLI/HTTP 集成、类型约束、测试速度和长期维护成本。

## 候选方案

### 方案 A — Python 3.11+ / FastAPI / asyncio / Pydantic v2

- 优点:AI/CLI/HTTP 生态成熟,异步 IO 和流式输出表达直接,代码量小,适合快速 dogfooding。
- 缺点:大型工程约束需要靠 mypy/ruff/测试纪律维持,团队若偏 Java 需要适应 Python 工程化。
- 复杂度:中。

### 方案 B — Java / Spring Boot / Spring AI

- 优点:工程化强,类型系统稳,适合长期服务化。
- 缺点:接 AI CLI 和 IM Bot 的样板代码多,Phase 1 迭代成本高,当前维护者已明确担心代码量和维护负担。
- 复杂度:高。

### 方案 C — TypeScript / Node.js

- 优点:Telegram Bot、进程管理和异步流生态顺手,CLI 集成自然。
- 缺点:偏离当前技术偏好,长期类型与运行时边界仍需大量纪律,Python AI 生态复用更弱。
- 复杂度:中。

## 决策

我们选择 **方案 A:Python 3.11+ / FastAPI / asyncio / Pydantic v2**。

配套约定:
- 包管理优先使用 `uv`。
- 核心接口使用 `typing.Protocol`。
- 值对象使用 Pydantic v2 的 frozen model。
- 测试使用 `pytest` / `pytest-asyncio`。
- 静态质量门禁使用 `ruff` / `mypy --strict`。

## 决策理由

- Phase 1 的主要风险是外部 AI CLI 和 IM API 接入不稳定,Python 能用更少代码把易变部分封装在 Adapter/Channel 内。
- asyncio 与流式输出模型匹配,有利于实现可中断、可观测的远程异步协作。
- Pydantic v2 能为任务、消息、状态等协议对象提供清晰边界,减少接口漂移。
- Java 的工程化优势真实存在,但当前阶段更需要低样板代码和快速 dogfooding。
- TypeScript 对 Bot/CLI 友好,但不是当前维护者明确偏好的路线,且对 AI 生态复用不如 Python。

## 后果

### 正面后果

- Phase 1 可以更快进入可运行 MVP。
- Adapter/Channel 协议能用较少代码表达并测试。
- 后续接入 FastAPI 管理端、Webhook、健康检查更自然。

### 负面后果

- 必须严格执行类型检查、lint 和测试,否则 Python 代码会退化。
- 默认系统 Python 可能低于 3.11,本地开发需要明确解释器或 `uv` 环境。
- 若未来需要复杂企业级部署,可能要补更多工程化设施。

### 我们接受这些代价是因为

- 当前项目还在 Phase 0/1,最稀缺的是快速闭环和长期可维护的最小实现,不是重量级框架能力。
- North Star 的"远程异步指挥 AI 工具"更依赖稳定协议和 Adapter 边界,不依赖某个大型服务框架。

## 不再做的事

在 ADR-0001 有效期间:
- 不用 Java/Spring Boot 作为编排核心默认栈。
- 不用 TypeScript/Node.js 作为编排核心默认栈。
- 不引入多语言 Sidecar 作为 Phase 1 默认架构。

除非出现以下情况,否则不重新讨论技术栈:
- Python 无法可靠集成目标 AI CLI 或 IM Channel。
- 类型、并发或部署问题已经阻塞 dogfooding,且无法用局部工程化解决。

## 相关链接

- ROUNDS Round 3
- BLOCKERS B-001
- 相关代码:`pyproject.toml`, `src/aico/`
