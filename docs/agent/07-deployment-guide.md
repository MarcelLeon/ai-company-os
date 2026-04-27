# 07 — 部署与测试环境

> 本项目的部署形态、环境、CI/CD 规范。

---

## 部署形态(Phase 演化)

### Phase 1-2:本地单机
- 一个进程跑编排核心 + 所有 Adapter + 所有 Channel
- 数据用 SQLite / 文件
- 主机:Wang 自己的 Mac

### Phase 3-5:本地 + Sidecar
- 编排核心一个进程
- 重型 Adapter(如 OpenClaw 浏览器自动化)拆 Sidecar
- 数据用 SQLite 或本地 Postgres

### Phase 6+:可选云端
- 编排核心放云端服务器(VPS)
- 长任务异步队列
- IM Webhook 走云端,本地 Adapter 通过反向通道执行

**纪律**:不要在 Phase 1 提前做 Phase 6 的架构。每个 Phase 用最简单可行的部署形态,问题暴露后再演化。

---

## 环境分层

| 环境 | 用途 | 数据 | 自动部署 |
|---|---|---|---|
| `local` | 本地开发 | 内存 / SQLite | N/A |
| `dev` | 开发自测 | 独立 SQLite | commit 触发 |
| `staging` | 集成测试 | 独立 DB | tag 触发 |
| `prod` | 生产(Wang 自用) | 持久化 DB | 手动审批触发 |

---

## CI/CD

### CI 流程(每个 PR 触发)
```
1. checkout
2. lint(spotless / ruff format --check)
3. static analysis(spotbugs / mypy --strict)
4. unit tests + 覆盖率
5. integration tests(用 mock IM / mock AI CLI)
6. build artifact
7. 评论 PR:测试结果 + 覆盖率变化
```

任何一步失败,PR 红灯,不允许合并。

### CD 流程(合并到主干后)
```
1. CI 全绿
2. 构建 Docker 镜像 / Jar / wheel
3. 部署到 dev
4. 跑 smoke test(基础链路自检)
5. tag 后部署到 staging
6. 跑 e2e
7. 手动 approve 后部署 prod
```

---

## Docker 化原则

### 每个进程一个镜像
- `aico-core`:编排核心
- `aico-adapter-{name}`:每个 AI Adapter(如有 sidecar 需求)
- `aico-channel-{name}`:每个 IM Channel(如有 sidecar 需求)

### Dockerfile 规范
- 用官方 base 镜像(`eclipse-temurin:21-jre` / `python:3.11-slim`)
- 多阶段构建(builder + runtime)
- 不以 root 运行
- 不要把 secret 写进镜像

### 镜像大小目标
- Java:< 300MB
- Python:< 200MB

超过即审视依赖。

---

## 配置与 Secret

### 配置
- 默认值写在代码 / 应用配置文件
- 环境特定值写在 `application-{env}.yml` 或 `.env.{env}`
- 不要把环境特定值 commit 到主分支

### Secret
- 永远不要 commit 到 git
- 本地用 `.env`(在 `.gitignore`)
- 生产用 secret manager(1Password CLI / Vault / 云端 KMS)
- CI 用 secret 注入

---

## 监控与告警

### 必须暴露的指标
- 任务接收数 / 完成数 / 失败数
- 各 Adapter 调用次数 / P99 延迟 / 错误率
- 各 Channel 消息收发数
- token 消耗量 / 成本(按 Adapter 维度)
- 当前 OPEN 任务数
- 审批等待数

### 实现
- Java:Spring Boot Actuator + Micrometer + Prometheus
- Python:`prometheus-client`
- 日志:JSON 结构化,送到本地 file / Loki

### 告警(Phase 6+)
- 错误率 > 5% 持续 5 分钟
- 某 Adapter 卡死 > 10 分钟
- 审批超时未处理

---

## 本地开发跑起来

详见 [`docs/human/quickstart.md`](../human/quickstart.md)。

---

## 关于 Dogfooding

按北极星第三句:**我们自己每天用它来开发它**。

具体:
- Phase 1 跑通后,Wang 应每天通过 Telegram 给本项目的 Claude Code Adapter 派发"修个 bug / 加个测试"任务
- 用得不爽的地方 → 立刻提 issue → 下一轮优先解决
- 这种闭环是项目能持续演化的核心机制

**不 dogfood 的功能视为不存在的功能**——这是合并标准。
