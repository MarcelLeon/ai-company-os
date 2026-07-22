# ADR-0059: Owner-Bound IM Ingress Before Orchestration

**状态**:Accepted
**日期**:2026-07-22
**决策者**:Codex / Round 221

## 背景

Phase 1会把每条Telegram/Feishu消息直接交给`Orchestrator.handle_incoming()`。审批策略允许task requester批准自己的
风险任务，这是单owner交互的合理体验，但前提必须是requester已经通过控制面身份校验。此前没有统一sender allowlist：
任何能触达Bot的人都可能查询状态、消耗provider，或提交风险任务后以同一sender自行`/approve`。

只校验sender仍不够。owner如果在公共群或错误chat中发送`/inbox`，AICO会把公司状态回复到那个target，形成由合法
owner触发的数据泄漏。因此控制面授权必须同时绑定消息来源身份和回复目标。

## 决策

1. 新增可插拔`IngressAuthorizer`。可复用/测试Orchestrator保留显式allow-all默认；正式Phase 1 runtime始终注入
   `OwnerBoundIngressAuthorizer`。
2. production authorizer要求`message.channel_name`、`source.channel_name`都等于configured channel，sender属于
   `AICO_OWNER_SENDER_IDS`，target属于`AICO_TRUSTED_TARGET_IDS`。任一集合为空即deny all。
3. `IngressGuard`位于Orchestrator第一行业务逻辑之前。拒绝消息不解析command、不capture feedback、不读写业务
   state/audit、不调用Adapter，也不向攻击者回复。
4. identity list去重且固定最多16项、每项256字符；blank忽略，placeholder、`unknown`、空白/控制字符拒绝。
   configured approval reviewer必须是owner sender；enabled morning target必须是trusted target。
5. 默认拒绝日志不含channel/sender/target/content，只在累计拒绝数为2的幂时记录总数，防止重复消息线性放大日志。
   Telegram transport层也不再提前记录raw sender；identity只能由下一条显式discovery路径输出。
6. bootstrap使用显式`AICO_INGRESS_DISCOVERY_LOG_IDENTITIES=true`：空binding仍deny all，但本地日志可显示首条拒绝
   消息的escaped sender/target。`aico-service doctor/install`在该模式开启时必定FAIL；owner填好配置后必须关闭。

## 否决方案

- **把Bot Token/私密Bot链接当授权**：Token只认证AICO到平台，不能认证消息发送者。
- **只依赖requester自审批策略**：这是授权后的审批策略，不是入口身份认证；陌生sender会成为自己的requester。
- **只绑定sender**：合法owner在不可信群发命令时，结果仍会泄漏到该群。
- **只绑定chat**：trusted群里的其他成员仍可驱动provider或审批自己的任务。
- **在每个command handler分别检查**：普通文本、callback、新命令和未来插件容易漏检；必须在解析前统一拦截。
- **永久开放`/whoami`**：形成未授权回复面和spam放大；改为owner显式开启、install禁止的本地discovery。
- **每次拒绝都写durable audit**：公开Bot可被用来放大SQLite/JSONL；本轮用bounded local security log，不污染业务审计。

## 后果

### 正面

- 未知sender不能读取公司状态、消耗模型、创建任务或利用requester自批风险操作。
- 即使owner本人误在公共群发命令，AICO也不会把结果回复到未授权target。
- Telegram polling与Feishu webhook共享同一核心策略，新增Channel仍可通过接口接入。
- 首次配置有fail-closed discovery路径，不需要临时开放业务权限。

### 代价与剩余风险

- owner必须先获取并配置平台sender/chat ID；配置错误会表现为Bot静默，这是刻意的fail closed。
- identity discovery会把ID写入本地日志，因此只能显式、短时、前台使用，不能安装为常驻服务。
- sender ID依赖Telegram/Feishu已认证的事件；它不是密码学owner签名，无法抵御owner IM账号或平台凭据被接管。
- 当前集合形成owner×target组合，不提供每个owner独立target矩阵或细粒度RBAC；个人公司基线先保持简单可审计。

## 验证

- 单测覆盖精确channel/sender/target、空集合deny、owner错误target、陌生sender普通消息和`/approve`。
- 拒绝链证明Adapter、reply、TaskSnapshot和AuditEvent均不变化；owner随后仍可批准原任务。
- denial log覆盖默认脱敏、2的幂限流、discovery显式显示escaped identity且不含message content。
- Phase 1 wiring、reviewer subset、morning target和doctor/install secret-safe readiness均有回归。
