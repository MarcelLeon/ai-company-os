# ADR-0052: Non-Mutating Standing Autonomy Deployment Preflight

**状态**:Accepted
**日期**:2026-07-21
**决策者**:Codex / Round 214

## 背景

Round 213 的 runtime 会在启动时验证 grant 与 scheduled target、project charter、appointment 和 Codex hard boundary。
但 `aico-service doctor` 只验证 grant 文件位置/owner/mode/JSON，因此一个目标漂移、charter 不存在、Codex 未启用或
command 被 wrapper 替换的配置仍会显示 `OK`，直到 LaunchAgent 启动后才失败。这不符合无人值守系统的部署前证据要求。

## 决策

1. Phase 1 暴露 `preflight_standing_autonomy(settings)`，只构造内存 Adapter registry、persona/agent directory、
   project directory，并调用与真实 runtime 相同的 grant binding validator。
2. preflight 不构造 Channel/Orchestrator，不打开 SQLite/JSONL/log/lock/heartbeat，不 spawn CLI、不联网、不消费预算。
3. `aico-service doctor` 只从 owner-only `.env` 投影 standing-autonomy 相关字段；project/persona/workspace 相对路径
   以 `--repo` 解析，匹配 launchd WorkingDirectory。
4. 配置 grant path 时，empty set、target/thread/project漂移、未知project/charter、缺appointment/persona、Codex
   disabled、non-Codex executable或配置解析失败都返回 FAIL。
5. 成功只输出 bounded grant count；失败只输出通用安全分类，不输出owner/grant/target、path、command、token或
   raw JSON/Pydantic exception。

## 否决方案

- **继续只检查 grant file**：证明不了实际 runtime eligibility，是假 readiness。
- **doctor 直接 build/start full runtime**：可能初始化 state、占 lock、创建日志或接入网络，违反诊断只读边界。
- **在 service CLI 重写 project/Adapter 规则**：会形成更松的 shadow policy并随 runtime 漂移。
- **通过运行一次 Codex 验证**：消耗provider、可能产生外部副作用，也不适合作为每次 install 前的确定性 Gate。
- **把 raw validation error 返回operator**：Pydantic input和配置路径可能泄露secret或owner identity。

## 后果

### 正面

- `doctor OK`从“授权文件可读”提升为“真实runtime绑定可启动”。
- owner可在LaunchAgent install前发现配置漂移，避免后台反复失败和错误自治口径。
- preflight与runtime复用同一 eligibility implementation，新增边界只需维护一处。

### 代价与剩余风险

- preflight仍只是本机静态/内存证据，不证明CLI登录、provider响应、定时触发或IM交付。
- grant真实性、同用户恶意进程与真实owner sample仍由B-014处理。
- 普通runtime未配置standing autonomy时继续WARN disabled，不阻塞部署。

## 验证

- valid doctor/preflight/runtime parity、relative project/persona path、empty/malformed/mismatch/unknown/missing/
  disabled/wrapper失败和身份脱敏均有回归。
- 测试证明preflight后`.aico`与所有stateful artifact仍不存在。
