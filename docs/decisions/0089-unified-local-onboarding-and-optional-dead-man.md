# ADR-0089: Unified Local Onboarding and Optional Dead-Man Receiver

**状态**:Accepted
**日期**:2026-07-22
**决策者**:Wang / Codex(协作)
**相关 Round**:Round 251

---

## 背景与问题

AICO 的公开入口分散在 demo、runtime、service CLI 和大量环境变量中。与此同时，严格 absence
验收把外部 Dead-Man Receiver 写进了运维主路径，容易让开源用户误以为使用 AICO 必须准备第二台电脑
或云服务器。需要同时降低首次启动成本，并保留整机失联检测的真实故障域边界。

## 候选方案

### 方案 A — 本机 Runtime 默认容器化

- 优点：运行环境统一，便于镜像分发。
- 缺点：本地 AI CLI 登录态、仓库、文件权限、PTY 与 macOS LaunchAgent 都要额外挂载或桥接；首次使用更复杂。

### 方案 B — Quickstart shell 脚本直接管理全部配置

- 优点：命令短。
- 缺点：会复制配置校验和服务管理策略，脚本容易成为第二套事实源；交互、错误处理和跨版本测试较弱。

### 方案 C — 单一 `aico` CLI 门面 + 本机 Runtime

- 优点：复用已有 runtime/service 权威实现；可测试、可组合，并能安全创建 owner-only 配置。
- 缺点：v0.1 仍要求 checkout、Python 与 `uv`；暂时不是独立二进制安装体验。

## 决策

选择 **方案 C**。公开入口统一为 `aico demo|init|run|doctor|service`。当前稳定分发形态是
clone checkout 后通过 `uv run aico ...` 使用；本机 Runtime 是普通用户的默认形态，macOS 常驻由用户级
LaunchAgent 承担。

Dead-Man Receiver 是可选高级可靠性组件：只有用户明确需要在整台被监控 Mac 失联后仍得到告警时才部署，
且必须位于另一台主机或云服务才形成独立故障域。它保留 Docker Compose 分发，但不进入默认 Quickstart、
不阻止普通 `optional` 模式安装。`strict` absence admission 是高级验收档位，不是基础使用前提。

## 决策理由

- AICO 的核心价值是编排用户电脑上已登录的本地 AI 工具，本机进程天然更容易复用 CLI 凭据与仓库权限。
- 单一 CLI 只做安全引导与委托，不复制 runtime、doctor 或 LaunchAgent 的策略实现。
- Docker 适合无本地 CLI 登录态的独立 receiver，不适合当前本机核心默认路径。
- “能使用 AICO”和“能检测整机失联”是两个产品层级，文档和机器准入必须分别表达。

## 后果

### 正面后果

- 新用户有一条 5 分钟、无需第二台机器的路径。
- `.env` 以隐藏 token 输入、排他创建和 `0600` 权限生成。
- 高可靠用户仍可按独立 Compose runbook 增加 Dead-Man，不降低其证据要求。

### 负面后果

- 当前发布仍依赖源码 checkout 与 `uv sync`。
- LaunchAgent 仍绑定 checkout 内的虚拟环境和配置；移动或删除 checkout 前必须卸载/重装。
- Linux 的长期守护形态仍需后续单独设计，不能用 macOS 文档冒充支持。

## 不再做的事

- 不把 Dead-Man Receiver、第二台电脑或云服务器写成普通用户的安装前置条件。
- 不把本机 AICO Runtime 的 Docker 镜像作为当前默认分发形态。
- 不新增承载业务规则的 Quickstart shell 脚本；未来 bootstrap 只能安装依赖并委托给 `aico` CLI。
- 在 LaunchAgent 不再绑定 checkout 前，不宣称 `uv tool` / PyPI 安装已经稳定可用。

## 相关链接

- ROUNDS Round 251
- PITFALLS P-106
- `src/aico/app/cli.py`
- `docs/human/quickstart.md`
- `deploy/dead-man-receiver/README.md`
