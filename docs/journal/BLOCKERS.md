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

## 当前活跃与近期归档卡点

### [B-010] Durable runtime 已完成 owner 配置、真实安装和 IM 常驻验收

**状态**:🟢 RESOLVED
**提出于**:Round 200
**最后更新**:2026-07-22(Round 252)
**影响**:基础本机Runtime已完成owner-bound配置、真实用户级LaunchAgent安装和新鲜Telegram常驻E2E；Dead-Man、secondary alert、
strict absence和owner手机已读仍由独立高级blocker跟踪，不是基础Quickstart前置条件。

**问题描述**
Round 251已用真实owner凭据生成`0600` `.env`，安装并重启macOS user LaunchAgent；稳定态doctor确认plist current、
launchctl loaded、owner PID与launchd一致，heartbeat v5确认Telegram polling及required Adapter健康。Round 252在owner授权的
`ai_co`私聊中真实发送`/status`、`/project aico`、`/inbox`，Web Telegram均显示新鲜回包；runtime日志分别以raw ref
`1426`、`1428`、`1430`记录incoming、command、sendMessage和handler finished。旁路`getUpdates=0`是active long polling已消费
update时的预期现象，不能据此否定已由UI和runtime日志共同证明的E2E。

**已完成的机器证据**
- fake launchctl 覆盖 install/restart/status/uninstall、bootstrap failure 和 recoverable backup。
- plist 通过 `plutil -lint`,且 golden test 证明不含 token/key value。
- scheduler lifecycle、fresh/stale/stopped heartbeat、doctor secret safety 均有回归。
- Round 201 进一步覆盖 required/optional component health、Telegram polling task death、scheduler task death、timeout 和异常脱敏;不再把 process fresh 当 fully healthy。
- durable service 已按 Channel 选择 Telegram polling 或 Feishu webhook entrypoint,两条入口共用 heartbeat lifespan。
- Round 202 把 crash restart 后失去执行所有权的持久化 `RUNNING` 对账为 `INTERRUPTED`,保留 pending approval/终态并写一次恢复审计;不会自动 replay 未知副作用任务。
- Round 203 用 SQLite transactional outbox 关闭 interrupted snapshot 与 recovery JSONL 的 crash 双写窗口;sink 失败/append-before-ack 均以同 event id 收敛,不 replay task。
- Round 204 用同 state DB kernel owner lock 拒绝重复 runtime,且 doctor 校验 owner PID=launchd PID;强杀 owner 的多进程 dogfood 可自动释放并安全接管。
- Round 205 将本地 owned-task liveness 与外部 dependency health 分开;Telegram polling/morning scheduler
  可有界原地恢复,连续失败熔断,外部失败不触发 crash-loop。
- Round 206 增加独立 runtime alert incident/outbox 和 secondary HTTPS sink,open/resolved 可 durable 重试;
  未配置 endpoint 时 doctor 明确 WARN,不冒充已经有第二通道。
- Round 220 将风险approval改为创建时冻结deadline的bounded lease；startup/老板视图/审批动作会事务性回收过期
  approval/task并通过outbox审计，doctor在install前拒绝无界配置。该机器安全边界仍不证明LaunchAgent或真实IM已运行。
- Round 221 在Orchestrator业务入口前同时绑定configured channel、owner sender和trusted target；陌生sender不能查询、
  派发或自批任务，owner在错误群也不会触发回复。doctor要求显式binding并拒绝identity discovery常驻安装，但当前仍
  没有真实owner ID/chat与Telegram/Feishu回包证据。
- Round 222以SQLite high-water + monotonic elapsed阻止approval/standing authorization因wall-clock回拨延长；该本地
  fence仍不证明LaunchAgent、owner账号或真实IM/provider链已运行。
- Round 223让audit history修改/重排/截断在runtime与doctor前fail closed，并提供legacy seal/verify；它仍未创建真实
  `.env`、安装LaunchAgent或产生trusted IM样本。
- Round 232让scheduled morning在发送前持久化exact envelope，失败有界重试、崩溃标记duplicate possibility、耗尽使
  runtime health失败，并保留secret-free平台ACK receipt。它关闭了“task活着却静默丢晨报”的机器假绿色，但当前仍无
  `.env`、LaunchAgent和真实platform ACK；平台ACK也不等于老板已读。
- Round 233为ACK后的standing autonomy新增独立durable intent；重启有accepted proposal/task证据时不重跑provider，
  无证据才有界重试，耗尽使health失败。它关闭本地ACK后崩溃窗口，但仍未产生真实owner/IM/provider样本。
- Round 238把dispatch后的terminal outcome加入exact-envelope outbox；失败/重启只重发通知、不重跑provider，耗尽进入
  required health。它关闭了另一处本地静默失败，但仍不能证明LaunchAgent或真实IM ACK已发生。
- Round 244增加显式`AICO_ABSENCE_ADMISSION_MODE=strict`：alerts、liveness、scheduled recovery + drill与standing autonomy任一
  未OK时install不会调用launchctl，避免把开发WARN配置当成老板可离开的部署。strict成功仍不证明真实`.env`已安装、外部ACK或IM回包。
- Round 245让Phase1Settings显式消费同一mode并在每次Telegram/Feishu启动前执行strict；LaunchAgent自动重启无法绕过install门禁，
  standing/recovery binding漂移在Channel/state构造前失败，settings错误不回显dotenv raw input。
- Round 249再把`runtime commissioning`加入strict：owner-only receipt绑定reviewed Git config、loaded dotenv代际与当前strict dead-man
  evidence，doctor/startup离线复核，运行中expiry/漂移进入required health。它仍没有创建owner `.env`、LaunchAgent或真实IM样本。

**解锁证据**
1. owner-only `.env`存在且权限为`0600`；LaunchAgent plist current/loaded，runtime owner PID与launchd PID一致。
2. Web Telegram真实私聊发送三条只读命令并收到对应回包；runtime日志将每条入站、命令、出站和完成绑定到同一raw ref。
3. 验收后的`aico doctor`继续显示Telegram channel、launchctl和runtime owner为OK；全程未联系其他Telegram用户或公开发布。

**剩余边界**
- Mac sleep、合盖断网和远程唤醒不在本 blocker 的解决范围。
- 若owner选择商用absence高级档，仍需按B-011/B-012/B-013/B-014补独立receiver、secondary alert、strict evidence、provider和恢复样本；
  这些能力不阻塞基础本机Runtime。

**相关链接**
- ADR-0038
- ADR-0058
- ADR-0059
- Goal Brief `docs/superpowers/specs/2026-07-21-durable-local-runtime-service.md`
- ROUNDS Round 200
- P-055
- P-056
- P-058
- P-059
- P-060
- P-061
- P-062
- P-076
- P-077

### [B-011] Out-of-band runtime alert 仍缺 owner endpoint 配置和真实样本

**状态**:🟡 DEFERRED
**提出于**:Round 205
**最后更新**:2026-07-22(Round 254)
**影响**:AICO 已有 owned-task及confirmed required-component的durable open/resolved event与secondary HTTPS sink机器契约；真实
Telegram/Provider主链已通过，但当前`.env`仍未配置独立alert endpoint/credential，也没有primary Channel断开后的远端收件证据。

**问题描述**
Round 206 已把 owned-task first open 与后续 healthy 转成独立 SQLite incident/outbox,通过可插拔 HTTPS sink
至少一次投递。重复 heartbeat/restart 不重复建 incident,sink failure 按 1/5/15 分钟退避,open/resolved
保持顺序,accept-before-ack 重投同一 `Idempotency-Key`;URL/token/exception 不进入 durable evidence。
Round 239又把进程仍活着的required component连续三次FAILED转换成同一类incident；计数跨restart持久化，OK才resolved，
optional/DEGRADED/瞬时失败不告警，同名owned-task circuit去重且不触发自动repair。剩余缺口是owner选择真实独立失效域的
receiver并提供授权配置。
Round 240再把alert delivery snapshot压缩进dead-man pulse v2；pending/failed pulse只排序、不续租，持续超过TTL后由独立
receiver生成`alert_delivery_unhealthy` outage，避免失败sink被fresh pulse掩盖。该本地合同仍不能证明真实endpoint/owner收件。
Round 254重启LaunchAgent并完成Telegram/Codex真实E2E，证明primary链当前可用；doctor仍明确`runtime alerts: disabled`。这不是
secondary path样本，因此B-011继续DEFERRED，但阻塞已准确收窄为独立endpoint与故障注入证据。

**已完成的机器证据**
- incident + outbox transaction rollback、重复 open/healthy/rebuild 去重和新 incident cycle 回归。
- sink failure/restart retry、持久化 backoff、队首顺序、accept-before-ack 同 key 和异常脱敏回归。
- heartbeat v5 / doctor 覆盖 alert disabled、pending、failed 以及 liveness disabled/healthy/degraded/failed；
  `aico-state` 覆盖 pending count/reset。
- required component FAILED经三份时间递增snapshot确认后进入同一transactional incident/outbox；重复时间、restart、
  outbox insert rollback、unsafe component name脱敏、OK resolved和owned-task重叠去重均有回归。
- generic health仍不驱动restart/provider replay/restore；optional、DEGRADED和business Task audit/storage不受影响。
- alert sink pending/failed跨TTL时receiver durable open、restart保持reason、healthy pulse same-reason resolved；v1→v2迁移、
  evidence v2和recovery exact-schema/domain verifier均有回归。
- Round 246在service/runtime增加跨字段隔离：incident URL不得与pulse URL相同，两侧bearer均存在时token也不得复用；冲突在
  launchctl/Channel前FAIL且不回显原值。该机器规则不证明真实endpoint已部署或owner收件。

**需要什么才能解开**
1. owner 部署/选择支持 HTTPS JSON 和 `Idempotency-Key` 去重的 receiver,且其失效域独立于 primary Channel。
2. 在 owner-only `.env` 配置 `AICO_RUNTIME_ALERT_WEBHOOK_URL` 和可选 bearer token,保持 state DB/heartbeat enabled。
3. 显式安装 runtime 后,分别制造primary owned polling circuit和required component持续FAILED；确认前者只收到一条open，
   后者第三份heartbeat后只收到一条`health:*` open；恢复到OK后只收到same incident的一条resolved。
4. 断开 receiver 后确认 pending/backoff,恢复 receiver 后确认顺序收敛；全程检查 endpoint/token 未进入日志/状态。
5. 只断开runtime-alert endpoint但保持liveness pulse可达超过TTL；确认receiver只生成一组
   `alert_delivery_unhealthy` open/resolved，并保存owner sink ACK与evidence v2。

**当前 workaround**
- 未配置 endpoint 时,operator 仍只能运行 `aico-service doctor` 或监控 heartbeat；doctor 会明确显示
  `runtime alerts: disabled`,不会把该状态报告成 fully healthy。

**相关链接**
- ADR-0044
- ADR-0077
- ADR-0078
- Goal Brief `docs/superpowers/specs/2026-07-21-durable-out-of-band-runtime-alerts.md`
- Goal Brief `docs/superpowers/specs/2026-07-22-confirmed-required-component-runtime-alerts.md`
- P-061
- P-062
- P-095
- P-096
- B-010

### [B-012] 整个 runtime / Mac 失联时无法由进程内告警自证

**状态**:🟡 DEFERRED(owner-paused;非当前个人开发者产品目标)
**提出于**:Round 206
**最后更新**:2026-07-22(Round 255)
**影响**:external publisher、persistent receiver与signed evidence机器契约保留，但独立部署不再属于当前个人开发者产品声明或
发布门槛；系统只承诺本机LaunchAgent与手工重启，不承诺整机失联后自动告警。

**问题描述**
该能力是可选高级可靠性档，不是普通AICO用户的启动前提。没有第二台电脑或云服务器时，用户仍可使用本机Runtime、
LaunchAgent与进程内health；只是不能声称整台Mac失联后仍能被独立发现和通知。

Round 255 owner明确暂停继续投入：目标用户是个人开发者，第二故障域/TLS/独立通知出口的部署门槛和使用比例不匹配；本机中断后
允许用户手工启动。已有receiver、签名与恢复原语保留为可选插件和未来复用资产，但不再进入近期优先级、默认Quickstart、发布阻塞
或持续dogfood清单。只有owner以后明确重新选择“整机失联也必须自动告警”的产品档位时才重启本项。

Round 207 已实现 secret-free ephemeral pulse:stable runtime id、fresh boot id、sequence、interval/TTL 和稳定
`Idempotency-Key`;failed send 只在内存保留同一 pulse,不写 incident outbox。reference receiver tracker 会在 arm 后
从未收到 pulse 或最后 acceptance-time TTL 到期时只 open 一次,并在有效新 pulse 后只 resolved 一次；duplicate、
out-of-order 和旧 boot 不延期。正常 stop 不自动 disarm,Mac sleep/网络分区超过 TTL 保守视为 unavailable。

Round 208 已新增 standalone FastAPI/CLI receiver、专用 SQLite armed/current/outage/outbox、分离 pulse/admin token、
restart immediate reconcile、严格有序至少一次 notification 和 non-root `/data` 容器契约。AICO 同时改用专用
liveness URL/token,不再错误复用 incident-alert strict endpoint。这些 machine gates 仍不能替代真正独立失效域：
若 receiver 与 AICO 跑在同一 Mac,整机故障时两者会一起消失。

Round 209 进一步关闭 receiver 自身假健康：`/readyz` 同时要求 SQLite 与 monotonic worker progress,连续第三次
内部失败或三个 sweep interval无成功 pass时返回通用 503并交由 container supervisor restart；downstream
pending/backoff不误判为 worker death。它提升部署后的自治恢复,但仍不替代第二故障域真实样本。

Round 210 新增 admin-only evidence bundle与离线 verifier：可以按完整outage group导出open/resolved、local
delivery/retry和current monitor,严格检查最低完成数/all-delivered并记录artifact SHA-256。它让真实演练可机器复核,
但不证明receiver实际位于第二故障域、TLS已配置或物理fault确实执行。

Round 230为receiver自身增加独立online backup、domain deep verify、disposable drill和worker-fenced restore，避免
receiver主机故障后丢失armed monitor/outage/outbox，也避免AICO恢复时误回滚外部observer。该本地合同不改变本卡点：
真实第二故障域、TLS、owner sink及outage open/resolved样本仍需部署证据。

Round 240把receiver/pulse/evidence/recovery schema升级v2：receiver可区分`pulse_expired`与
`alert_delivery_unhealthy`，并且pending/failed pulse不会续租。它关闭机器合同中的alert-path false green，但没有部署第二
故障域或生成真实kill/network/alert-path样本，因此本卡点仍保持DEFERRED。

Round 241为receiver downstream增加可选different-origin fallback和1-of-2/2-of-2 ACK quorum；primary失败时可由fallback
结算同一durable event，两路都miss才继续backoff。它降低单通知provider/credential故障，但没有证明两个真实provider、账号、
网络或物理故障域，也没有owner手机收件样本，因此本卡点仍保持DEFERRED。
receiver schema v3会冻结逐事件策略并拒绝pending期间改变quorum，避免2-of-2在重启后静默降级；这仍只是本地结算合同，
不增加真实provider或终端证据。

Round 242把aggregate quorum继续拆成逐route事实：schema v4保存event ACK bitmask与slot健康，partial ACK会通过尚存route发送
durable degraded edge，后续真实event ACK再发recovered；admin/evidence/recovery可复核且不暴露endpoint/secret。它关闭“1-of-2
成功掩盖坏fallback”的event-driven false green，但没有周期silent canary；无outbound event时不能声称continuous route health。

Round 243新增schema v5默认关闭的`silent-route-probe-v1`：显式opt-in后复用真实双route URL/token/POST，exact intent跨restart，
一个失败窗口为suspect/PENDING，连续达阈值才degraded并主动发edge，ACK后recovered。它关闭机器侧“长期无事故就不观察route”的缺口，
但当前没有两个真实bridge对silent事件的兼容/无展示证明，也没有provider日志或owner手机无噪声样本；因此不能把本地fake ACK写成
continuous commercial health，本卡点仍DEFERRED。

Round 246把incident alert与pulse的dedicated endpoint/credential从文档纪律升级为service/runtime机器准入；same URL或双方same token
均fail closed，same origin/different strict path仍允许。这防止协议误配，但没有创建第二故障域、真实receiver或owner通知样本。

Round 248把dead-man artifact验收分成历史审计与显式current-health模式：可限制bundle年龄、按验收时刻重算已完成silent probe的freshness，
并要求所有route healthy。它关闭“陈旧bundle永久复用”的机器false-green，但artifact仍无receiver签名，且当前没有真实host/TLS/provider/
手机/fault-action样本；因此本卡点仍保持DEFERRED。

Round 249用expiring commissioning receipt把该strict artifact继续绑定到safe runtime id、clean reviewed Git config和最终`.env`代际，
并纳入strict install/startup及持续required health。它防止A配置证据被B配置复用或运行中过期仍全绿，但local receipt仍非receiver签名，
也没有生成任何真实第二故障域样本；因此本卡点仍保持DEFERRED。

Round 254在owner确认ADR-0088后实现signed evidence：receiver可用owner-only Ed25519私钥签domain-separated exact bundle；offline
verifier与strict commissioning只信owner-pinned SPKI公钥，receipt schema v2绑定envelope、payload与key identity，unsigned旧bundle和
silent key replacement均fail closed。该机器链路已通过wrong-key、tamper、unsigned、permission与rotation对抗测试，但当前仍未在真实
第二故障域生成签名样本；签名只证明trusted key possession，不证明私钥所在物理host、TLS、fault action、provider ACK或手机展示。

**仅在 owner 重新开启该产品目标时需要**
1. owner 按 `deploy/dead-man-receiver/README.md` 在独立主机部署现有 receiver,配置 TLS、persistent `/data`、
   独立 pulse/admin secret 和至少一个owner notification endpoint；商用验收应再配不同provider/账号的fallback，token不得复用，
   默认1-of-2，只有owner要求双ACK时才设2-of-2。按同一 runtime identity/TTL 显式 arm。
2. 在 owner-only `.env` 配置 URL/token、`AICO_RUNTIME_LIVENESS_ENABLED=true`、safe monitor id、interval/TTL,
   explicit install 后确认 doctor 和 heartbeat v5 publisher healthy。
3. 从receiver的signed endpoint导出envelope，将独立复制的owner-pinned SPKI公钥写入最终strict配置并创建schema v2 receipt。
   分别完成 kill process后 launchd replacement、持续 launch failure、断网超过 TTL再恢复三类样本；每类应只有
   一次 outage open 和一次 resolved,duplicate idempotency key 不重复通知。每类后导出evidence bundle并离线运行
   signature verifier；commission验收必须组合maximum-age、fresh completed probe和all-routes-healthy三项，保存envelope/payload/key
   SHA-256与独立host/TLS/fault操作日志。私钥rotation必须显式换公钥、重新导出和recommission。
4. 永久 uninstall 前先在 receiver 显式 disarm。普通 restart/stop、Mac sleep 和网络分区都不得自动解除监控。
5. receiver按独立cadence生成`aico-dead-man-recovery backup`并保存off-device SHA；定期跑disposable drill。只有receiver
   自身事故才允许停worker后显式restore，不能由AICO恢复触发。
6. 分别制造primary通知route失败、两route同时失败再恢复；保存stable event id、configured quorum、平台ACK与owner终端展示。
   核对schema v5 degraded/recovered edge、逐event/probe ACK向量与admin route status。若两个bridge都确认支持silent v1，再显式启用
   低频probe并保存provider请求日志、连续失败/恢复和手机无probe噪声样本；否则保持disabled。different-origin和local probe ACK本身
   不能替代真实provider/账号/网络隔离证据。

**当前 workaround**
- launchd 负责本机 crash restart；heartbeat v5 / doctor 可查看 publisher 最近成功或 degraded/failed。未部署独立
  receiver 前,这些仍不能替代远端 dead-man monitor。

**相关链接**
- ADR-0038
- ADR-0044
- ADR-0045
- ADR-0046
- ADR-0047
- ADR-0048
- ADR-0068
- ADR-0081
- ADR-0078
- ADR-0079
- ADR-0080
- P-055
- P-062
- P-064
- P-065
- P-066
- P-096
- P-097
- P-063
- B-010
- B-011

### [B-013] 主状态库仍缺少 off-device 备份策略与真实恢复演练

**状态**:🟡 DEFERRED(owner-paused;非当前个人开发者产品目标)
**提出于**:Round 211
**最后更新**:2026-07-22(Round 255)
**影响**:本地backup/verify/restore/drill原语保留，但off-device商用DR不再属于当前个人开发者产品声明或发布门槛；
整盘损坏、Mac丢失时允许用户手工重新部署与配置。

**问题描述**
Round 211实现`aico-state backup|verify|restore`：live DB可生成consistent standalone artifact，restore先校验
expected SHA、拒绝active runtime、创建pre-restore safety backup并原子替换。machine round trip证明实现边界，
但没有owner选择的独立存储、加密/密钥、retention、自动调度或off-device业务恢复演练。当前命令还只覆盖
AICO SQLite business state，不覆盖audit/memory JSONL、Project/Persona配置、`.env`、日志和dead-man receiver DB。

Round 255 owner明确暂停商用disaster-recovery闭环：个人开发者可以在故障后手工重启/重新配置，真实off-device存储、加密、retention、
隔离恢复与RPO/RTO演练的成本暂不符合当前产品采用率。已有本地backup/verify/restore/drill代码继续维护但不扩展，不再把真实off-device
演练列为发布或主线goal阻塞；只有未来出现明确用户需求或不可接受的数据损失成本时再重启。

Round 212新增`aico-state drill`：不接触live `--db`，在private temp中调用production restore、再次校验
schema/table-count parity并自动清理，可生成`0600` evidence report。它关闭“verify冒充restore rehearsal”的本机
工具缺口，但artifact尚未来自off-device storage，也没有credential/full-asset/IM业务恢复样本。

Round 223把audit JSONL升级为SHA-256链并增加owner-only checkpoint，使本地修改、重排和tail截断可检测；这同时明确
恢复资产不能只复制JSONL。当前`aico-state`仍不打包audit/checkpoint，owner也尚未选择off-device目标或做整组恢复。

Round 224增加writer-locked audit recovery point：matching ledger/checkpoint进入一个owner-only ZIP，offline verifier
流式核对outer/member hash并materialize生产账本验证。它关闭“两文件人工复制不一致”缺口，但没有restore primitive、
off-device目标/加密/retention，也未覆盖memory/config/secret/receiver DB或跨truth-source RPO。

Round 225增加disposable audit drill与owner-fenced restore：恢复要求expected SHA、真实AICO state DB fence、显式确认和
pre-restore preservation；有效live进入标准safety backup，损坏live原字节进入unverified quarantine。双文件替换中断会
fail closed且可用同一artifact重跑收敛。它关闭本机audit restore primitive缺口，但artifact仍未来自off-device，也没有
全资产、credential或代表性IM业务恢复证据。

Round 226增加bounded-window core recovery set：一次操作按state→audit生成两个既有verified component artifact，并用
固定outer manifest绑定hash/size/summary、整体capture window与完整coverage ledger；combined drill实际走两套production
materializer。schema强制`global_transaction=false`和`business_restore_ready=false`，所以关闭了手工错配/漏件假阳性，
但也机器确认memory/config/secret/grant/receiver尚未覆盖。

Round 227把memory JSONL升级为process-locked、hash-chained、checkpointed ledger，并增加portable backup、offline verify、
disposable drill与owner-fenced restore。recovery set schema v2按state→audit→memory绑定三个component，memory不再是缺项；
但配置revision、secret/grant reinjection、receiver DB以及off-device full-business演练仍未覆盖。

Round 228将project/persona配置恢复绑定到独立提供的reviewed full Git commit、clean HEAD/tree与active config blob/hash；
`verify-checkout`可在恢复目标上重新核对revision、worktree和配置，schema v3明确配置未嵌入但恢复合同已就绪。当前内部缺口
收窄为runtime secret、standing grant reinjection receipt和dead-man receiver DB恢复合同。

Round 229增加secret-free runtime reinjection合同：schema v4只记录control-plane secret slot/channel和standing grant enabled
mode，不保存值、hash、identity或grant正文；灾后`reinjection-receipt`要求exact checkout、production service/grant preflight及
owner decision reference，`verify-reinjection`再按独立receipt SHA重验当前material。coverage现把AI provider远端认证与
dead-man receiver DB列为两个required unresolved assets；前者需要B-014真实provider样本，后者仍是下一本地恢复合同缺口。

Round 230增加独立receiver恢复合同：receiver service全生命周期持有DB owner lock，新增online backup、exact schema/domain
offline verify、disposable production restore drill及owner-fenced restore；有效live先做verified safety，无法验证的
DB/WAL/SHM进入unverified quarantine。core schema v5只把receiver标为`external_component_recovery`合同就绪，保持
`included=false`，避免AICO恢复时同步回滚外部证据源。现在唯一required unresolved contract是AI provider live authentication；
但receiver真实off-device副本/独立SHA/RPO演练，以及整套全业务恢复证据仍未完成。

Round 231增加真实provider认证恢复合同：schema v6固定required provider集合，灾后`provider-auth-receipt`以受限Claude/Codex
随机challenge要求exact response、terminal success与usage，并将30分钟回执绑定set/reinjection SHA、revision、owner decision及
executable hash；不记录prompt/output/error/credential。coverage现在没有“缺少恢复方法”的required unresolved asset，但新增
`post_restore_evidence_assets`明确列出每次恢复仍必须提供的checkout、reinjection、provider和receiver证据。当前checkout没有
`.env`/owner授权，因此本轮没有真实付费probe；off-device、IM和RPO/RTO也仍未完成，B-013保持DEFERRED。

Round 254已有真实owner `.env`、LaunchAgent、Telegram与当前Codex provider成功样本，但没有从off-device artifact执行恢复；也未生成
绑定recovery set/reinjection的provider-auth receipt、独立receiver backup或业务RPO/RTO证据。因此它证明“当前运行”，不证明“灾后恢复”。

Round 234增加默认关闭的scheduled core backup：每个窗口先持久化intent，再capture并立即deep verify；artifact/receipt
崩溃矩阵可复验收敛，五次耗尽或verified age超过RPO max age会使required runtime health FAILED。目标目录必须已存在、
absolute、owner-only、checkout外，缺失mount不会被自动创建；该轮scheduler尚不restore或删除旧artifact。这关闭了“operator
必须记得手动capture”的本地编排缺口，但当前checkout没有启用配置，且目录检查不能证明off-device、加密、retention或外部SHA。
因此B-013继续DEFERRED。

Round 235关闭“创建后artifact丢失仍false green”的本机custody缺口：receipt绑定secret-free destination fingerprint，
独立cadence周期重开并deep verify最新artifact/sidecar；missing、tamper、receipt drift、权限放宽、目录identity变化或custody
age超限都会持久FAILED并进入required runtime health。backup cadence变化不能重置destination baseline，下一次capture也不能在
被替换目录上静默重建基线。但kernel fingerprint不是volume UUID/provider签名，当前仍无真实off-device storage、加密、retention、
外部SHA或隔离restore证据，所以B-013继续DEFERRED。

Round 236关闭“长期无人值守时本机scheduled artifact无界增长”的机器合同缺口：owner可显式启用age + minimum generations +
per-run limit策略；scheduler先持久化PRUNING/policy SHA，再复验并按固定顺序删除，重启按pair存在矩阵收敛，PRUNED保留
secret-free tombstone。默认仍关闭，当前checkout没有真实storage policy配置；本地tombstone也不证明provider lifecycle、WORM、
加密、第二故障域或restore drill，所以B-013继续DEFERRED。

Round 237关闭“恢复materializer只靠operator手工演练”的机器合同缺口：默认关闭的scheduled drill先持久化intent，再对最新
VERIFIED + custody VERIFIED artifact在private disposable workspace执行state/audit/memory production materializer；失败有界
重试并进入health，open/latest exhausted目标受retention保护，success receipt仍固定`business_restore_ready=false`。当前没有
真实off-device artifact、启用配置或隔离业务恢复样本，因此本机scheduled drill不能关闭B-013。

**需要什么才能解开**
1. owner确定off-device存储与数据分类策略，配置独立于AICO Mac的加密位置、凭据管理和访问审计。
2. 定义RPO/RTO、backup cadence、retention与过期删除规则；Round 236已提供默认关闭的bounded local retention state machine，仍需
   owner配置真实目标、显式开启策略并验证RPO/retention receipt。restore不得由该scheduler执行，provider-side lifecycle/WORM
   也不能由本机PRUNED tombstone替代。
3. 按独立receiver合同从第二故障域生成artifact、保存外部SHA并做disposable drill；只有receiver自身事故才执行restore，
   不得与AICO core combined restore。恢复control-plane后运行`provider-auth-receipt`，在30分钟内复验并保存独立SHA；
   不能用本地secret presence、过期receipt或offline verify冒充实时provider接受。
4. 将`aico-recovery capture`的outer SHA保存到独立authority；从off-device副本运行`verify`和`drill`，再在隔离AICO
   checkout持续保持runtime停止并显式执行component restore。核对capture window、SHA、schema/count、audit head/count、
   `/tasks`/`/inbox`、pending approval/outbox和代表性IM，保存结果与RPO/RTO证据。
5. 可启用Round 237的scheduled disposable drill持续验证本地materializer，但仍必须周期性从真实off-device副本完成隔离checkout、
   reinjection、provider、receiver与代表性IM业务恢复，并验证旧artifact按policy删除；在此之前不得声明commercial DR ready。

**当前 workaround**
- operator可用`aico-recovery capture`生成绑定state/audit/memory、reviewed config revision、无值reinjection requirements和
  required provider集合的core set，记录outer SHA并复制到owner批准的加密独立位置。恢复后依次生成reinjection与30分钟
  provider-auth receipt。manifest的`unresolved_assets=()`只表示全部required asset已有恢复合同；必须继续读取
  `post_restore_evidence_assets`，receiver仍需自己的off-device artifact与演练。完成外部证据和隔离业务恢复前，只算local contracts。
  restore保持人工确认和owner fence，不允许无人值守自动执行。
- owner也可在确认真实存储故障域后启用`AICO_RECOVERY_BACKUP_ENABLED=true`；`aico-state`的recent recovery backup和heartbeat
  只证明本机capture/verify/RPO状态。doctor明确不attest storage class，目标mount缺失会fail closed而不是回落到本地目录。

**相关链接**
- ADR-0049
- ADR-0050
- ADR-0068
- ADR-0069
- ADR-0075
- Goal Brief `docs/superpowers/specs/2026-07-21-aico-state-backup-restore.md`
- Goal Brief `docs/superpowers/specs/2026-07-21-aico-state-disposable-restore-drill.md`
- ADR-0061
- Goal Brief `docs/superpowers/specs/2026-07-22-tamper-evident-audit-ledger.md`
- ADR-0062
- Goal Brief `docs/superpowers/specs/2026-07-22-portable-audit-recovery-point.md`
- ADR-0063
- Goal Brief `docs/superpowers/specs/2026-07-22-owner-fenced-audit-restore.md`
- ADR-0064
- Goal Brief `docs/superpowers/specs/2026-07-22-bounded-window-core-recovery-set.md`
- ADR-0065
- Goal Brief `docs/superpowers/specs/2026-07-22-tamper-evident-memory-recovery.md`
- ADR-0066
- Goal Brief `docs/superpowers/specs/2026-07-22-reviewed-config-revision-recovery.md`
- ADR-0067
- Goal Brief `docs/superpowers/specs/2026-07-22-secret-free-runtime-reinjection-receipts.md`
- P-067
- P-093
- P-068
- P-079
- P-080
- P-081
- P-082
- P-083
- P-084
- P-085
- P-087
- P-088
- ADR-0072
- Goal Brief `docs/superpowers/specs/2026-07-22-durable-scheduled-core-recovery-backup.md`
- P-090
- ADR-0073
- Goal Brief `docs/superpowers/specs/2026-07-22-continuous-recovery-artifact-custody.md`
- P-091

### [B-014] Owner-bound standing autonomy 等待v2预算/证据合同真实复验

**状态**:🟡 DEFERRED
**提出于**:Round 213
**最后更新**:2026-07-22(Round 257)
**影响**:真实owner grant、scheduled morning、Telegram ACK、只读Codex、usage/outcome receipt与`max_runs=1`第二次阻断已经通过；
Round 257已补grant v2单次token envelope、tool-free Codex与bounded evidence pack机器合同，但尚未获得新的
`budget=within_limit + outcome=complete + evidence=current`真实定时样本，不能声明boss-absent autonomy上线。

**问题描述**
Round 213 实现 external owner-only grant、exact morning binding、persistent run budget、TaskBus fail-closed gate、
fixed Codex read-only/no-network command 和 timeout interrupt。机器测试没有创建真实授权，也没有消耗付费模型。
此外，`0600 + current uid` 防项目 Agent/误提交，不是抵抗同一 OS 用户恶意进程的密码学 owner authentication。

Round 214 关闭了最后一个本地部署前假阳性：`aico-service doctor`现在会用Phase 1真实Adapter/persona/project/grant
路径验证exact morning target、charter appointment和Codex executable hard boundary；preflight不打开任何state或网络。
因此本blocker剩余部分已收窄为owner配置与真实外部样本，不再缺本地静态/binding工具。

Round 215又补齐结果接手证据：inbox/morning从既有proposal/task SQLite truth派生restart-safe receipt，显示done、running、
failed、interrupted、rejected或accepted-without-matching-task的`evidence_missing`。同时修复preauthorized runner误套
overnight handoff grader导致正常输出被标FAILED。该receipt仍不证明provider/IM真实执行，B-014保持DEFERRED。

Round 216补上provider usage本地链：preauthorized Codex JSONL的terminal usage进入TaskBus audit和durable proposal，
`token_stop_threshold`会在下一次run前按累计实测量熔断，缺usage停授。由于usage只在turn完成后出现，这不是当前run
硬token/cost上限；且本轮没有付费provider样本，所以B-014仍保持DEFERRED。

Round 217再把transport completion与result acceptance拆开：Codex output schema、本地charter coverage、
repo-relative file/line存在性和complete/blocked一致性生成durable bounded outcome；missing/invalid/blocked会停授。
这仍只证明结构与本地位置，不证明引用内容的业务语义或真实远端执行；且Codex无可配置max-output硬限额，所以真实
owner/provider/IM样本仍不可省略。

Round 218封住本地资源放大：charter/schema/model、Codex返回值、Orchestrator capture和durable receipt现在都有固定
字符/数量上限，超长、duplicate key或schema overflow只留下bounded invalid receipt并停授。这保护本地runtime/state，
仍不限制provider已生成的token或证明真实scheduler/IM，因此不改变B-014的外部验收性质。

Round 219把成功结果绑定到bounded source fingerprint，并在老板接手或下一次调度前重算；内容变化/文件缺失会显示
`drifted/missing`并停授。该hash只验证owner-local文件字节是否变化，不是远端provider、真实scheduler/IM送达、来源
签名或业务语义证据，因此仍不能替代B-014的真实外部样本。

Round 221要求scheduled morning target同时属于runtime trusted target，避免有效grant把结果发到未授权chat；真实owner
sender/target仍未配置，且平台sender ID不是密码学签名，所以该门禁不能替代真实授权与IM样本。

Round 222让standing grant在wall-clock明显回拨时fail closed，并跨重启保留high-water；它不创建真实grant、不调用
paid provider，也不证明scheduler和IM送达，因此B-014仍保持DEFERRED。

Round 231补齐了灾后provider live-auth取证工具：required provider集合进入recovery合同；Claude/Codex用tool-free、
non-persistent、bounded随机challenge生成30分钟owner-only receipt，且offline verify不会重放付费probe。这关闭了“如何证明当前
credential被远端接受”的本地协议缺口，但当前checkout仍无`.env`、owner grant或durable runtime，本轮没有调用真实provider，
也没有定时standing result/usage/IM样本；B-014继续DEFERRED。

Round 232补齐scheduled morning transport证据：exact content与standing receipt fingerprint在发送前落SQLite；失败有界重试，
platform ACK与standing autonomy execution分开记录，`aico-state`可核对secret-free receipt。这使真实样本可被机器复核，仍没有
产生owner-bound grant、provider result/usage或平台ACK，更不能证明老板已读；B-014继续DEFERRED。

Round 233再为每次scheduled delivery持久化独立autonomy intent，并在provider dispatch前把intent绑定到accepted proposal/task。
重启有证据即结算，不盲目重跑provider；无证据才有界重试，notification歧义与耗尽可见。这关闭本地ACK后漏执行/重复dispatch
恢复窗口；accepted持久化后、provider ACK前的at-most-once缺口仍由`evidence_missing`暴露。它仍不生成真实grant、付费provider
result/usage或平台样本；B-014继续DEFERRED。

Round 238补齐dispatch结算后的terminal outcome delivery：实际dispatch的authoritative proposal/task/result会投影成exact bounded
envelope，发送前进入独立SQLite outbox，失败有界重试且绝不重跑provider；wrong-target ACK、SENDING重启、五次耗尽和
settled-without-outbox均可见，后两者进入required health。started提示发送失败也不再阻断TaskBus submit。该合同关闭“安全地不重跑，
却静默不告知老板”的本机窗口，但当前仍没有owner grant、paid provider、LaunchAgent或真实IM ACK，所以B-014保持DEFERRED。

Round 254从真实Telegram手工`/ask --exact reviewer`两次完成Codex provider return-code 0与页面回包，关闭“当前Provider/IM是否可用”
的不确定性；但手工请求不消费standing grant、不由scheduler触发，也不产生morning/outcome delivery整套receipt。当前doctor仍显示
standing autonomy disabled，因此B-014剩余阻塞仅是owner授权和真实定时样本，而非基础Runtime或Provider连通性。

Round 256由owner显式选择一次性真实验收。真实scheduled morning与Telegram ACK后，前两次dispatch分别暴露Codex 0.144.5已移除
`experimental_network`旧配置键、asyncio默认64 KiB无法承载Codex JSONL单行；两处已最小修复并通过全量gate。第三次真实任务
return code 0、status=done、usage与terminal outcome均durable落盘并送达Telegram；第二个同charter intent在Adapter启动前返回
`run budget exhausted`，task数量不变，证明`max_runs=1`机器边界有效。

同一真实样本也否决了上线：50,000 `token_stop_threshold`只在下一run前检查，无法阻止本次227,252 tokens；`STATUS.md`当前324 KiB，
超过result validator的256 KiB source cap，模型仍选择该源，receipt因此`invalid/source_too_large`、criteria 0/3、sources 0。
这不是IM或Provider可用性问题，而是“单次成本不可硬界定”和“charter允许的证据源与validator上限冲突”两个产品合同缺口。

Round 257实现ADR-0090：grant schema v2强制`max_total_tokens`，Codex preauthorized command同时写入rollout budget与context
window，并显式禁用shell/unified exec/multi-agent/apps/browser/computer/image/web等工具。charter必须配置bounded evidence
source；系统只提供最多64 KiB的allowlisted原始path/line片段，同时用完整文件SHA检测派发/接手漂移。provider terminal usage
超过limit时仍durable保存但拒绝采信result，IM/晨报显示`budget=exceeded`。当前AICO与SME真实配置pack分别约29.0K/40.8K字符，
机器测试覆盖oversize、symlink、marker、drift、unlisted line和over-budget结果拒绝。

该机器合同关闭Round 256的本地设计缺口，但Codex rollout budget在response后记账，美元账单也不由AICO控制；因此B-014只收窄为
一次新的owner-authorized真实复验。超预算即使被拒绝采信仍算预算失控，不能用post-check把它写成成功。

**需要什么才能解开**
1. owner另行授权后签发新的v2 `max_runs=1`短期grant，只做一次真实定时复验；必须同时得到delivery/intent/outcome delivered、
   `status=done`、`budget=within_limit`、`outcome=complete`、`evidence=current`及criteria/source全覆盖。
2. 保存exact Codex CLI version、provider terminal usage、生成命令中的rollout/context配置与pack SHA；若usage越界或缺失，按失败样本
   保留并停止，不换grant重跑。
3. 只有真实样本证明当前CLI/provider遵守owner token envelope，才可关闭本blocker；口径仍是token预算，不提升为美元hard quota。
4. `max_runs=1`第二次hold已经通过；timeout/interrupt真实样本可在不扩大Provider成本的hanging-safe adapter fixture中补，不要求重复付费。
5. 若商业威胁模型包含同一用户下恶意进程，先选择detached owner signature、Keychain/managed policy或独立OS
   identity，再提升 authorization claim。

**当前 workaround**
- 不配置 `AICO_STANDING_AUTONOMY_GRANT_PATH` 时功能完全禁用；standing proposal 继续由 owner 手工
  `/proposal accept`。
- 本地 example 只是不可直接启用的模板；repo 内 grant 会被拒绝。
- doctor只有显示`owner-bound runtime binding verified`才可进入install；旧的“grant file verified”不再算ready。
- 真实样本后下一次`/morning`必须出现对应done/interrupted receipt；若`evidence_missing`，停止并人工核对，不重跑。
- 新真实样本必须同时确认`tokens=N`来自本机Codex版本、`budget=within_limit/N`且pack evidence current；
  run间`token_stop_threshold`与单次`max_total_tokens`必须分开解释，后者仍不是美元hard quota。
- 真实样本若显示`outcome=missing/invalid/blocked`，立即停止并检查`/task`、`/proposals`、schema/CLI版本与引用内容，
  不得换grant自动重试。
- 真实样本若显示`evidence=drifted/missing`，先由owner核对仓库变更或丢失文件；确认后通过新的人工验收生成新receipt，
  不得编辑旧proposal、伪造hash或自动重跑。

**相关链接**
- ADR-0051
- ADR-0052
- ADR-0053
- ADR-0054
- ADR-0055
- ADR-0056
- ADR-0057
- ADR-0069
- Goal Brief `docs/superpowers/specs/2026-07-21-owner-bound-readonly-standing-autonomy.md`
- Goal Brief `docs/superpowers/specs/2026-07-21-standing-autonomy-deployment-preflight.md`
- Goal Brief `docs/superpowers/specs/2026-07-21-standing-autonomy-execution-receipts.md`
- Goal Brief `docs/superpowers/specs/2026-07-21-post-run-provider-usage-circuit-breaker.md`
- Goal Brief `docs/superpowers/specs/2026-07-22-standing-evidence-fingerprint-drift.md`
- P-069
- P-070
- P-071
- P-072
- P-073
- P-074
- P-075
- P-087
- P-094
- ADR-0076
- B-010

### [B-015] Codex Goal签名native host缺live isolated observation

**状态**:🔴 BLOCKING
**提出于**:Round 266
**最后更新**:2026-07-23(Round 268)
**影响**:五项boss-absent对比不能生成公平的Codex Goal正式样本；第一方build/surface已找到，但live admission前不能宣称胜出。

**问题描述**
本机`codex-cli 0.144.5`有stable Goal feature、persistent app-server thread、Goal set/get/clear、token/time usage与
`thread/resume`。但experimental schema里的`turn/start`仍要求调用方提供`input`，没有continuation request/notification。
`remote-control`只提供app-server远程接入与配对，不证明谁拥有自动续跑。若AICO benchmark runner自行发送“继续”prompt，
测到的是AICO外置loop，不是当前Codex Goal能力。

Round 268确认当前签名Codex App内嵌`0.145.0-alpha.30`新增
`thread/fork.deferGoalContinuation`，schema明确描述initial/normal automatic continuation。第一方出口已不再缺失；
现在缺的是在隔离formal harness中实际观察自动turn、restart resume与usage，而不是继续寻找方法名。

**已完成的机器证据**
- ADR-0093冻结native host ownership与turn source/usage/chain合同，standalone app-server不能通过admission。
- `probe-codex-goal`已证明隔离persistent Goal控制面、zero usage与安全cleanup。
- Round 266新增`probe-codex-goal-host`：现场生成并有界解析experimental schema，绑定contract、CLI version与完整bundle SHA。
- 当前真实schema SHA为`356a6f6bb546f89d464df44effd103622538b340d059e61d57287f32bf6b7b94`；Goal控制面、
  persistent resume与remote-control transport存在，client-required turn input成立，continuation候选为空。
- Round 266 surface receipt固定不等于host admission；当时即使出现continuation-named method，也仍要求exact first-party host
  build receipt。
- Round 268新`probe-codex-app-host`验证App/内嵌CLI code signature、Team ID、notarization、bundle/build、完整CDHash和schema SHA。
  真实candidate固定formal false，blocking只剩live continuation与isolated state observation。

**需要什么才能解开**
1. owner授权创建一个隔离Goal fork及极小live capability run；frozen contract绑定当前签名App/内嵌CLI build。
2. independent observer证明host自动发起continuation，runner没有提交continuation input，并区分initial/native/owner/harness来源。
3. persistent thread跨host restart继续，turn chain与Goal/provider usage可独立观察，默认能力和frozen model/effort/budget不漂移。
4. live capability receipt通过ADR-0093 admission后，再申请两侧相同预算的五task正式模型run。

**当前 workaround**
- 签名App candidate只用于build/surface admission；不运行runner-managed continuation，不把schema或当前聊天体验称作正式baseline。
- AICO侧真实Telegram approval/takeover transport dogfood已在Round 267完成；formal model run仍未授权/执行，
  scorer没有两侧完整样本时固定不能返回胜出。

**相关链接**
- ADR-0092
- ADR-0093
- `src/aico/app/boss_absent_codex_goal_capability.py`
- `src/aico/app/boss_absent_codex_goal_host.py`
- Round 266

### [B-009] aico-view 本地 attachment 缺少策略允许的真实浏览器截图入口

**状态**:🟡 DEFERRED
**提出于**:Round 197
**最后更新**:2026-07-21(Round 197)
**影响**:Boss Brief 的机器契约已通过,但 desktop/mobile screenshot、overflow 和真实点击证据尚未完成。

**问题描述**
`/view` 的产品边界是 IM 中的自包含 HTML attachment,不启动 localhost。Round 197 生成了代表性本地附件,
但 Browser 插件明确拒绝 `file://` URL。安全策略同时禁止通过临时 localhost、data URL 或其它浏览器表面
绕过该拒绝,因此本轮不能把静态 HTML/单测结果冒充真实视觉验收。

**已尝试的方向**
- 已完成 project isolation、DOM 顺序、动作链接和 empty-state 的 red-green 测试。
- Browser session 已按要求清理;没有发送真实 Telegram 附件,也没有绕过 URL policy。

**需要什么才能解开**
- 在获准的真实 Telegram `/view` attachment 下载页上做只读 desktop/mobile 验收;或
- Browser 插件未来原生允许受控本地 attachment 打开。

**当前 workaround**
- 机器 Gate 覆盖内容、顺序、项目隔离、自包含和 deep-link href;视觉 claim 保持 pending。

**相关链接**
- ROUNDS Round 197
- ADR-0036
- P-052

### [B-008] 当前 Codex CLI 版本不支持全局配置模型

**状态**:🟢 RESOLVED
**提出于**:Round 191
**最后更新**:2026-07-17(Round 192)
**影响**:已解除;Telegram `/ask <role>` 可通过 Codex Adapter 返回真实业务正文。

**问题描述**
Round 191 真实 Telegram Web E2E 发送 `/ask reviewer ...` 后,AICO 创建任务并返回 accepted,
但 Codex Adapter 子进程以 return code 1 退出。错误明确为:全局 `/Users/wangzq/.codex/config.toml`
配置 `model = "gpt-5.6-sol"`,而 PATH 中的 `codex-cli 0.142.4` 要求升级后才能调用该模型。

**解决过程**
- 真实 Telegram 入站和 AICO runtime 日志已证明 Channel / Orchestrator 正常,不是 Telegram 渲染故障。
- 经人类要求继续修复后,将 PATH 中 `@openai/codex` 从 `0.142.4` 升级到稳定版 `0.144.5`,未修改全局模型配置。
- 使用相同 `gpt-5.6-sol` 跑最小 `codex exec` 成功返回 `AICO_CODEX_OK`。
- 真实 Telegram Web 再次发送 `/ask reviewer`,Codex Adapter return code 0,流式输出结束且 Telegram handler 正常完成。

**关闭证据**
- `codex --version` → `codex-cli 0.144.5`。
- 同模型最小调用 → `AICO_CODEX_OK`。
- 真实任务 `d7ac4939-f49b-418b-8558-9d75523da152` → adapter return code 0、stream finished、handler finished。

**后续防回归**
- CLI 快速演进仍是已知风险;真实 dogfood 前先跑版本和同模型最小调用,再归因到 Adapter。
- 若后续频繁发生全局模型漂移,再评估 AICO 项目级 model override;本轮不扩大范围。

**相关链接**
- ROUNDS Round 191
- ROUNDS Round 192
- P-017
- P-044

### [B-007] Data-Agent real Telegram baseline cannot be sent by current UI tools

**状态**:🟢 RESOLVED
**提出于**:Round 178
**最后更新**:2026-07-15(Round 191)
**影响**:原 UI tooling 阻塞已解开;`data-agent-v1` 是否需要重新生成专用 transcript 不再受 Telegram 发送能力阻塞。

**问题描述**
`data-agent-v1` 的产品证据已经可本地验证,但 AICO orchestration 的 50 分需要真实 Telegram/project-office
链路。Round 179 人类已明确委托 agent 尝试继续发送,但当前本机 Telegram / Computer Use 只能读屏,不能可靠点击、
输入或脚本发送,因此真实 Telegram baseline 仍无法完成。

**已尝试的方向**
- 已启动专用 AICO runtime。
- 已确认 `/Applications/Telegram.app` 能读取到已登录聊天列表和 `ai_co` bot。
- 已确认 `/Applications/Telegram 2.app` 是未登录 QR code 页,不能用于本 baseline。
- Computer Use 读屏可用,但 click / key 动作返回 tool activation error。
- `open` / direct executable / System Events 均不能稳定操作 Telegram 进程。
- 已完成 local injected IM baseline,但明确不冒充真实 Telegram transcript。

**需要什么才能解开**
已解开:
- Chrome Telegram Web 可通过可见 DOM 中的 `contenteditable` composer 发送真实命令。
- AICO runtime 日志可确认入站 update / command / task ack。
- 确定性 Bot API harness 可发送指定 MessageContent,再由 Telegram Web DOM / 截图验收真实客户端形态。

**当前 workaround**
- 无 UI tooling workaround。后续真实 E2E 按“payload golden -> Bot API message id -> Web DOM / 视觉”取证。

**相关链接**
- ROUNDS Round 178
- ROUNDS Round 179
- `benchmarks/data-agent/runs/2026-06-28-v1/aico-evidence.md`

### [B-006] 人工 dogfood 待测队列缺少机器验收分层

**状态**:🟢 RESOLVED
**提出于**:Round 143
**最后更新**:2026-06-09(Round 145)
**影响**:`/overnight`、父子 agent 委派、delegate 输出可读性和 `/view` 等长链路修复后,如果每次都要求人类完整重跑历史 prompt,会把验证周期变成新的进度阻塞。

**问题描述**
Round 138-142 连续修复了协作风险误判、`/overnight` handoff 完整性、delegate 输出粘连、移动端长墙和老板查看动线。每一项都有 targeted tests 或 full clean env 验证,但下一轮队列仍容易被理解成"必须先人工完整复验同一长链路",导致机器已覆盖的确定性 contract 仍反复占用人工时间。

**已尝试的方向**
- 方向 A:继续把真实 IM 复验放在最高优先级并要求重跑同一类 `/overnight`。问题是父子委派和 provider 长输出耗时不可控,每次修复后完整人工回归成本过高。
- 方向 B:取消人工 dogfooding,只看测试通过。问题是 AICO 的核心价值是老板手机上的可接手体感,真实 provider / Channel 漂移和移动端可读性不能只靠 mock 判断。
- 方向 C:引入验收分层。机器 Gate 先覆盖确定性 contract,人工 Sample 只验证真实 IM 体感和平台漂移。Round 145 后修正为:Agent 能访问本机 Telegram / provider 时先跑真实样本,人工只看体感和接手便利性。

**解决结果**
- `NORTH_STAR.md` 第三句下新增 "Dogfooding 的验收分层":Dogfooding 仍是最终验收,但不替代机器回归。
- `docs/agent/06-testing-guide.md` 新增 "Dogfooding 与机器验收的边界",把机器 Gate / 人工 Sample / 人工 Blocking 固化为默认顺序。
- `STATUS.md` 下一轮建议已按该规则重排:当前 `/overnight` delegate 输出和老板动线从"人工完整复验阻塞"降级为"机器 Gate 后 1 条代表性 IM 样本"。
- Round 144 在 `docs/playbooks/phase-8-absence-loop.md` 固化当前 Phase 8 AI 前置 contract gate;实测 40 passed in 0.30s。
- Round 145 将 playbook 修正为机器 Gate -> Agent 本机真实样本 -> human 体感 Sample,并实测真实 Telegram 中 `implementer/claude-code -> reviewer/codex` 协作链路完成;当前 gate 更新为 41 passed in 0.36s。

**当前 workaround**
- 无。后续若某条真实 IM 待测无法由当前 Agent 环境覆盖,必须把缺口显式写入 `STATUS.md` 或新 BLOCKER。

**相关链接**
- NORTH_STAR.md 第三句 Dogfooding 分层
- docs/agent/06-testing-guide.md Dogfooding 与机器验收的边界
- docs/playbooks/phase-8-absence-loop.md AI 前置 Contract Gate
- ROUNDS Round 143
- ROUNDS Round 144
- ROUNDS Round 145

### [B-005] Orchestrator class size regression

**状态**:🟢 RESOLVED
**提出于**:Round 132
**最后更新**:2026-06-15(Round 164)
**影响**:已通过 `OrchestratorCommandRegistry` 拆分解决;后续新增命令 handler 应继续放在 registry 或独立 handler 模块,不要回填到 `Orchestrator` 主体。

**问题描述**
B-004 在 Round 107 把 `Orchestrator` 拆到 480 行。M2/A2 各加了 1-2 个 command handler 实例化,加上模块级 `_build_orchestrator_event_index` helper 和 `_setup_*` 子方法,类总规模重新涨到约 585 行。每个方法已经被拆到 <100 行(`__init__` 37 / `_setup_command_handlers` 8 / `_setup_coordinators` 26 / `_setup_boss_and_lead_handlers` 36 / `_setup_workflow_handlers` 28),但类整体仍超 500 行硬限。

**已尝试的方向**
- Round 132 已经把 `__init__` 从 117 行拆成 4 个 <40 行的私有方法,satisfies 单方法限制,不满足类整体限制。
- 不在 A2 本 sprint 做大规模重构,以避免扩范围。

**需要什么才能解开**
已解开:
- Round 164 新增 `src/aico/core/orchestrator_command_registry.py`。
- command handler 实例化、slash command 分发表、`/inbox`、`/morning`、审批/中断/broadcast 等命令处理迁出 `Orchestrator`。
- `Orchestrator` 主体保留 IM 入站、任务提交、流式输出、协作派发和少量 runtime 协调职责。

**当前 workaround**
- 无。后续如新增命令,优先扩展 `OrchestratorCommandRegistry` 或新增专用 handler,保持 `Orchestrator` 主体不重新膨胀。

**相关链接**
- ROUNDS Round 107(B-004 RESOLVED 时的状态)
- ROUNDS Round 132(本卡点提出)
- ROUNDS Round 164(本卡点关闭)
- ADR-0032(A2 完成时识别问题)
- CLAUDE.md "Hard rules" 单类 <500 行限制

### [B-004] Core orchestration classes exceed project size hard limit

**状态**:🟢 RESOLVED
**提出于**:Round 106
**最后更新**:2026-05-21(Round 107)
**影响**:已不再阻塞公开前工程质量收口;保留归档给后续结构演进参考。

**问题描述**
项目规范要求单类 < 500 行、单方法 < 100 行。Round 106 扫描结果曾是:
- `src/aico/core/orchestrator.py`: `Orchestrator` 约 646 行,`_handle_command` 约 103 行。
- `src/aico/core/task_bus.py`: `TaskBus` 约 566 行。

Round 106 为了落地 SQLite task state store 第一切片,在 `TaskBus` 中接入了可选
`TaskStateStore`,让该类尺寸进一步超过硬限制。功能已由测试覆盖,但结构上需要后续拆分。

**已尝试的方向**
- 过去已将 project commands、role commands、status commands、goal brief、lead decision、
  offline delegation 等流程逐步拆出 `Orchestrator`。
- Round 106 先选择最小持久化切片,未同时进行大规模 `TaskBus` 拆分,避免把状态恢复和结构重构混在一轮。

**解决结果**
- Round 107 新增 `OrchestratorTaskFactory`,把 project/session/memory task 构造从 `Orchestrator` 移出。
- Round 107 新增 `TaskStateRepository`,把 task records、snapshots、approvals 和 adapter mapping 从 `TaskBus` 移出。
- 模块级命令分发拆成 project / role / directory / memory helper,单函数不再超过 100 行。
- 结构扫描结果:`Orchestrator` 480 行,`TaskBus` 448 行,无单类 >=500 行或单函数 >=100 行。
- 验证通过:`pytest` 289 passed / 1 skipped,`ruff check .`,`ruff format --check .`,`mypy src tests`,`git diff --check`。

**当前 workaround**
- 无。后续若继续扩展 TaskBus,优先拆 approval coordinator / adapter dispatch service,不要再把状态恢复逻辑塞回 TaskBus。

**相关链接**
- ROUNDS Round 106
- ROUNDS Round 107
- ADR-0028

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
