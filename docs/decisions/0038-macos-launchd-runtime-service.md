# ADR-0038: macOS launchd Durable Runtime Service

**状态**:Accepted;heartbeat semantics and Channel entrypoint amended by ADR-0039
**日期**:2026-07-21
**决策者**:Codex
**相关 Round**:Round 200

## 背景

AICO 的北极星要求老板离开后仍能接收、推进和早报。当前 `aico-phase1` 依赖前台终端;终端退出、
登录会话重启或进程崩溃后,IM 公司就消失。审计还发现 `Phase1Runtime.start()` 在非阻塞 Channel
启动返回后立即停止 morning scheduler,所以“定时早报已配置”不等于 scheduler 实际存活。

## 候选方案

### A. 继续用终端 / tmux 手工保持

拒绝。它没有 start-on-login、crash restart、统一状态和可恢复安装,不能作为 absence-first 产品契约。

### B. 提前迁移 Docker / 云端 supervisor

拒绝。当前部署指南明确是本地单进程阶段;云端会引入认证、反向通道、secret manager 和远端 Adapter
问题,超出当前证据。

### C. macOS LaunchAgent + runtime heartbeat + operator CLI

采用。目标机器就是个人 Mac,launchd 是零新增依赖的用户级监督器。CLI 只管理 AICO 自身 plist,
runtime heartbeat 提供进程内证据,原有 SQLite/audit/memory 继续承担业务恢复。

## 决策

- 新增 `aico-service` operator CLI,支持 render/install/restart/status/doctor/uninstall。
- LaunchAgent 运行仓库 `.venv/bin/aico-phase1`,WorkingDirectory 指向仓库,登录启动,异常退出重启,
  正常 stop 不循环重启。
- plist 只携带 PATH 和 unbuffered 标志等非 secret 环境;AICO credential 继续从仓库 `.env` 读取。
- `.env` 必须存在且不能对 group/other 开放;doctor 只输出 key 名是否存在,永不输出 value。
- runtime 原子写 `.aico/runtime-heartbeat.json`;fresh heartbeat 只证明进程 loop 活着,不证明 Telegram
  或 provider 可用。
- install 替换 plist 前写备份;uninstall 把 plist 移到 Trash。真实 install/uninstall 只由用户显式命令触发。
- 第一实现直接面向 launchd,不提前抽象跨平台 ServiceManager;Linux/systemd 第三个真实样本出现后再抽象。

## 后果

### 正面

- 终端关闭或进程异常不再天然终止 AICO 公司。
- operator 能区分“没安装、没加载、进程不活、heartbeat stale、配置不完整”。
- 无新增依赖,不把 token 扩散到 launchctl 元数据。

### 代价

- 第一切片仅支持 macOS user LaunchAgent。
- Mac sleep、断网、provider 登录过期仍会中断真实工作;heartbeat 不能掩盖这些问题。
- repo 或 `.venv` 路径变化后需要重新 install。

## 不再做的事

- 不把 `.env` 内容展开进 plist。
- 不把“launchctl loaded”或 heartbeat fresh 当成 Telegram E2E 成功。
- 不在正常 `aico-phase1` 启动时偷偷安装系统服务。
- 不为尚不存在的第二个平台提前设计通用 supervisor framework。
