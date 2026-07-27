# CHANGELOG.md

> 遵循 [Keep a Changelog](https://keepachangelog.com/) 规范。
> 版本号采用 [Semantic Versioning](https://semver.org/)。

---

## [Unreleased]

### Added
- Human-on-the-loop appointment contract:所有project-scoped Agent都被明确要求在当前任务和任命权限内直接推进，
  遇到证据不足、指令冲突、未知/意外或即将越界时停止并找owner；Prompt同时声明不能绕过AICO审批门禁或
  Adapter强制边界，并新增回归测试。
- Personal HOTL relaunch pack:README中英文首屏明确AICO是个人、本机优先而非企业多租户平台；新增核心能力地图、
  10人design-partner陪跑计划、真实3分钟案例分镜和对应social preview素材。
- Tool-free budgeted standing evidence pack:standing charter可配置exact section allowlist；系统在派发前生成不超过64 KiB、
  带完整源SHA和原始path/line的证据包。preauthorized Codex显式禁用所有tool/web/multi-agent能力，并把owner
  `max_total_tokens`写入rollout/context门禁；超预算usage保留但result不采信，morning/inbox/outcome显示budget状态。
- Boss-absent vs Codex Goal benchmark v1:新增五类冻结task、contract/result schema、canonical SHA绑定、deterministic scorer与
  `aico-benchmark freeze|score`离线CLI；缺task/usage/evidence不能移出分母，AICO绝对门槛与五项相对指标同时通过才返回win，
  equal-observation `dry-run`固定产生non-win，并真实terminate/resume fake helper生成restart receipt；synthetic测试不冒充正式对比成绩。
- Codex Goal baseline admission:`aico-benchmark probe-codex-goal`使用run-isolated Codex home验证persistent app-server
  Goal set/get/clear、exact model/token budget、read-only/no-network与zero usage，再删除thread；`0600` cleanup intent支持断线后重连清理，
  普通`codex exec`不再被允许冒充Goal baseline。offline turn supervisor再绑定model/effort/completion，并用Goal token delta交叉验证
  matching provider usage notification，覆盖interrupt和跨app-server resume；owner-only auth symlink完成无模型local login admission。
- Native Codex Goal host contract:明确app-server只负责Goal控制面，正式baseline必须由第一方Codex host拥有continuation；新增
  fail-closed host admission和无raw prompt turn ledger，拒绝standalone loop、runner自造续跑input、能力/usage/chain漂移、超预算及
  terminal后续跑，并把owner takeover与harness injection从无人值守continuation中分离。
- Codex Goal host surface attestation:`probe-codex-goal-host`现场生成当前CLI experimental schema，绑定contract/version/schema
  SHA并机器验证Goal控制面、persistent resume、client-required turn input、remote-control transport和continuation候选；输出永远
  不是native-host admission，缺第一方host build receipt时formal baseline继续fail closed。
- Signed Codex App Goal host candidate:`probe-codex-app-host`验证App与内嵌CLI的Apple code signature、OpenAI Team ID、
  bundle/build、完整CDHash和experimental schema SHA；识别`thread/fork.deferGoalContinuation`明确声明的initial/normal automatic
  continuation语义。candidate receipt保持formal false，直到独立live continuation与isolated run state被观测。
- Independent Codex Goal live host observer:`aico-codex-goal-observer start|finish`把签名App candidate、exact desktop app-server
  process、owner-only frozen Goal budget与per-thread session JSONL绑定；只接受append-only同inode历史、真实PID更换、旧host退出、
  restart后`source="goal"`自动turn、完成态、Goal/provider usage推进及capability context不漂移。observer只发
  `thread/goal/get`，不拥有`turn/start`写通道；不满足任一条件不生成formal admission。
- Independent Codex Goal scenario finalization:`aico-benchmark finalize-codex-goal`把native host admission/run与外部scenario
  receipt绑定为唯一可评分结果；required role逐项分开绑定Agent identity、provider execution、runtime instance、source turn、
  fixture和artifact消费链，防止单一Goal线程更换角色标签冒充multi-agent，并对称验证五类场景。
- Native Codex Goal role/scenario observer:只读解析Codex Desktop parent `spawn_agent/sub_agent_activity`与child
  `session_meta/task_started/turn_context/task_complete`，从第一方JSONL派生Agent/execution/runtime/source-turn/artifact消费链；
  hidden/extra或nested Agent、模型/权限/终态漂移全部拒绝。场景事实写入owner-only hash-chain ledger，再由
  `finalize-codex-goal-observations`派生正式receipt。
- Native Codex Goal host-run observer:`aico-codex-goal-observer run-start|run-sample|run-finish`冻结zero-usage Goal与
  append-only session前缀，从exact initial/owner envelope、自动Goal transition、逐turn provider usage和签名Desktop runtime
  样本派生host-run receipt；scenario/result finalizer不再接受裸`host-run.json`。
- Restart-safe AICO benchmark runner:核心按frozen roles编排不同Agent，所有role共享同一remaining-token budget并消费前一artifact
  SHA；provider调用前原子保存稳定dispatch intent，跨进程只按id对账、unknown outcome禁止重放，restart必须更换runtime instance。
  scorer同步拒绝单Agent更换role label的伪协作；超预算provider usage即使不采信checkpoint也完整计入budget loss证据。
- Independent AICO scenario finalization:`aico-benchmark finalize-aico`把durable role state与独立harness receipt绑定为task result；再次验证
  terminal checkpoint、distinct agents、shared usage，并分别强制restart no-replay、approval fence、drift rejection、irrelevant source
  isolation和IM takeover成本。执行者、观察者、scorer保持三层分离，fake receipt不具备正式成绩资格。
- Exact-model TaskBus benchmark transport:AICO frozen roles通过真实TaskBus/Adapter合同执行，preauthorization与Codex CLI显式绑定
  exact model/reasoning effort和shared remaining-token budget；内容寻址artifact与owner-only dispatch receipt支持新runtime按id恢复，
  确定性能力拒绝在provider前fail closed，未知outcome不自动重放。
- Frozen-fixture independent AICO harness:五类task把实际bounded fixture纳入canonical SHA并贯穿role prompt/checkpoint/receipt；
  `advance-aico`在clean exact-revision checkout一次推进一个真实TaskBus role，外部harness可跨进程继续。owner-only hash-chain observer
  从artifact、dispatch receipt、filesystem generation、external checks、usage、takeover和terminal事实派生scenario receipt，
  `finalize-aico-observations`不再接受SUT自报场景结论，所有benchmark输出为fresh 0600文件。
- Approval-gated benchmark mutation:approval task在implementer后持久停于`approval_pending`，exact owner grant与action receipt之前
  reviewer零派发。isolated executor从frozen fixture解析target/content，intent先于写入；write后crash只对账不重写，预存target无intent、
  expired/wrong grant或receipt/state SHA漂移全部fail closed。
- Owner-bound benchmark IM exchange:`collect-aico-approval-im|collect-aico-takeover-im`以0600 durable intent、Telegram platform ACK、
  exact owner inbound和hash-chain action ledger生成不可手写替代的decision receipt；send/ACK崩溃窗口不盲重发，grant与takeover
  receipt逐SHA绑定decision、owner fingerprint、actions和elapsed seconds。
- Formal benchmark Agent identity:contract冻结project config与project ID，role逐项绑定exact appointment；Codex Adapter从真实
  `thread.started`采集provider-issued execution ID并只持久化SHA。runner/observer/finalizer同时拒绝Agent复用、provider execution
  复用、assignment漂移与缺失execution identity。
- Signed dead-man evidence:独立receiver可用owner-only Ed25519私钥签发domain-separated evidence envelope；离线verifier与strict
  commissioning只信owner-pinned公钥，绑定exact envelope、payload和key identity。unsigned endpoint保留历史审计兼容，signature
  success仍明确不证明receiver物理host、TLS、fault action、provider ACK或human read。

### Fixed
- macOS LaunchAgent lifecycle race:`service install`在bootout后有界确认卸载并重试transient bootstrap；
  `service restart`遇到未加载service时从当前plist重新bootstrap，再kickstart。真实Telegram独占polling dogfood后的
  `Input/output error`/service-not-found恢复路径已在本机复现并闭环。
- Codex standing-autonomy compatibility:预授权与live-auth probe不再传递Codex 0.144.5已删除的
  `experimental_network` strict-config键；安全边界继续由`--sandbox read-only`、`never` approval、忽略user config/rules、
  ephemeral session和output schema强制。子进程stdout/stderr显式使用1 MiB单行上限，避免合法的大JSONL事件触发asyncio默认64 KiB失败。
- Risk negation false positive:明确的`Do not read or modify files`/`不要修改`约束不再被substring分类为`write_files`；同一task中
  后续真实update/run/delete仍按原风险阶梯升级，避免安全提示反而让Codex只读任务被拒绝。
- Project phase drift:`config/projects.example.json`与无配置fallback现在统一报告
  `Phase 8 - 离线托管 + 老板缺席操作模型`，避免公开`aico init`生成的LaunchAgent继续在`/project aico`展示已完成的Phase 5/6。
- Runtime commissioning drift:strict install/startup现在要求owner-only、checkout-external的expiring commissioning receipt，绑定reviewed
  Git config、`.env` metadata generation fingerprint与strict dead-man exact bytes。运行中expiry或任一binding漂移会使required
  `configuration:commissioning-receipt` FAILED并进入既有confirmed alert；不联网、不保存dotenv内容/hash，也不自动restart/replay。
- Strict runtime dotenv drift:production loader冻结不含内容/hash的`.env`文件元数据代际；运行中编辑、替换或删除会让required
  `configuration:dotenv-generation`进入FAILED和既有confirmed alert。系统不自动reload/restart，避免旧进程被磁盘新配置冒充。
- Runtime webhook authority false-green:incident alert与dead-man pulse现在必须使用不同exact URL；双方配置bearer时token也必须不同。
  service strict aggregate和Phase1 runtime共享secret-free cross-field validator，在launchctl/Channel/state前拒绝且不回显原值；
  same-origin different-path仍允许，不冒充第二故障域。
- Strict admission restart bypass:`AICO_ABSENCE_ADMISSION_MODE`现在由Phase1Settings显式读取，Telegram/Feishu每次runtime启动都会
  在Channel/state构造前执行同一strict enable gate与standing/recovery production preflight；LaunchAgent重启不能回落optional。
  生产settings loader把可能包含dotenv raw input的Pydantic错误收敛为secret-safe doctor提示。
- Scheduled autonomy silent terminal window:dispatch结算后的done/failed/interrupted/evidence-missing现在先冻结为exact outcome
  envelope并写入独立SQLite outbox，再按1/5/15/15分钟最多五次投递；重启与ACK歧义只重发通知，不重跑provider或消费grant。
  wrong-target ACK拒绝落DELIVERED，耗尽进入required health；非关键started提示失败不再阻断TaskBus submit。
- Recovery backup false-green custody:latest scheduled artifact/receipt现在按独立cadence重新deep verify，并以secret-free
  destination fingerprint约束目录identity连续性；删除、篡改、receipt drift、权限放宽、目录替换或custody stale都会持久
  FAILED并进入required health。heartbeat只做cheap continuity gate，不同步hash大文件；异常不触发restore/delete/rebind。
- Scheduled autonomy ACK crash window:每份scheduled morning在任何外发前写入独立durable intent；重启时若存在同intent的
  accepted proposal/task证据就直接结算且不重跑provider，无证据才有界重试。已ACK晨报不重发，intent耗尽使health FAILED，
  hold notification歧义以稳定intent id显式暴露。
- Scheduled morning false health:晨报现在发送前持久化exact content，失败按1/5/15/15分钟最多五次重试；发送中崩溃
  显式标记`duplicate_possible`，耗尽后scheduler health为FAILED。平台ACK先于standing autonomy记录，后者失败不会重发
  已确认晨报；同一日重启与`push_on_start`复用稳定delivery id。
- Standing autonomy terminal-state contamination:preauthorized task不再复用`/overnight` handoff grader；普通只读输出
  保持DONE，只有自身timeout/restart等真实终态才显示interrupted/failed。
- Dead-man receiver false readiness:`/readyz` 现在同时验证 SQLite 与后台 expiry/delivery worker 的 monotonic
  progress；连续第三次内部失败或三个 sweep interval无成功进展时返回通用 503，恢复成功后自动转绿。downstream
  notification pending/backoff 不误触发 restart，`/healthz` 继续只表达进程存活。
- Bounded owned-task self-healing:heartbeat v3 会原地恢复死亡的 Telegram polling / morning scheduler task,
  通过 restart timeout、稳定期、尝试上限和冷却熔断避免 tight loop;外部 Channel/provider failure 不触发恢复,
  doctor 对 recovering/open 分别报告 WARN/FAIL。
- Single-runtime ownership:同一 SQLite state 的 Telegram/Feishu runtime 在任何 recovery 前竞争 kernel lock;重复进程 fail closed,crash 自动释放,doctor 校验 owner PID 与 launchd PID,避免 live task 被误判 orphan 或重复消费 IM。
- Recovery audit crash consistency:SQLite transactional outbox 原子提交 interrupted snapshot 与稳定 `AuditEvent`,sink 失败或 append-before-ack 后按 event id 幂等重试,避免恢复状态与审计证据永久分裂。
- Crash restart task reconciliation:新 runtime 接管 SQLite 时把失去执行所有权的持久化 `running` 任务改为 `interrupted`,写一次恢复审计并要求重试前核对外部副作用;pending approval 与终态保持不变。

### Added
- Unified public CLI:`aico demo|init|run|doctor|service`复用既有authoritative runtime/service合同；
  `aico init`以隐藏输入和一次性exact private-chat命令自动发现owner/chat，生成最小Telegram配置并原子创建`0600` `.env`；
  已知identity可显式传入。公开Quickstart明确本地Runtime是默认形态，
  独立Dead-Man Receiver只是需要整机失联告警时的可选高级组件。
- `aico-commission create|verify`:生成/复核secret-free runtime commissioning receipt；expiry取bundle maximum age与completed silent-probe
  TTL较早值，receipt SHA可由owner外部归档。local receipt固定`business_absence_ready=false`，不冒充receiver签名、provider ACK或human read。
- Strict absence install admission:`AICO_ABSENCE_ADMISSION_MODE=strict`会复用同一service readiness图，把runtime alerts、external
  liveness、scheduled recovery、disposable drill和owner-bound standing autonomy提升为launchd安装门禁；默认`optional`保持开发
  兼容。输出只列固定合同名，成功仍明确external evidence未认证，不声称commercial ready、off-device或human read。
- Durable silent notification route probes:receiver schema v5新增默认关闭的`silent-route-probe-v1`，复用真实双route URL/token/POST，
  先持久化stable probe再发送。首次失败只标suspect/PENDING，连续达到阈值才生成既有degraded edge，后续ACK生成recovered；
  不追赶窗口、不递归更新健康。admin/evidence/recovery v5验证probe checkpoint、source-tagged edge与v4保守迁移；bridge不能保证
  ACK且不展示probe时必须保持disabled。
- Durable notification route health edges:receiver schema v4保存逐event ACK bitmask、slot级unknown/healthy/degraded状态与
  独立健康边沿outbox。1-of-2部分成功会通过尚存route主动发送`notification_route_degraded`，后续真实event恢复时发送
  `notification_route_recovered`；edge按any-route ACK有界重试且不触发restart。evidence/recovery v4和admin-only route status
  同步覆盖，v3历史ACK保持unknown，不伪造成功route。
- Quorum dead-man notification routes:independent receiver可选配置different-origin fallback，两路并发投递同一event/idempotency key；
  默认1-of-2 ACK即可结算，owner可显式要求2-of-2。quorum miss继续复用原durable 1/5/15分钟退避；settings拒绝同origin、
  route token复用及notification token复用pulse/admin authority。receiver/evidence/recovery schema升级v3，当前策略与逐事件策略
  durable保存；pending期间拒绝策略漂移，防止2-of-2重启后被1-of-2降级结算。delivered仍不表示老板已读。
- Alert-delivery-aware dead-man renewal:pulse/receiver/evidence schema升级v2；heartbeat把secondary alert delivery压缩为
  `disabled/healthy/pending/failed`，其中pending/failed pulse只排序、不续租，持续超过TTL由独立receiver创建
  `alert_delivery_unhealthy` outage，恢复后healthy pulse写入same-reason resolved。receiver SQLite v1可保守迁移，backup
  verifier检查新checkpoint、枚举与reason一致性；payload不含incident、异常、endpoint、target或正文，也不授权自动repair。
- Confirmed required-component runtime alerts:state schema v13新增durable health confirmation table；required Channel/default
  Adapter/scheduler连续三份时间递增FAILED后，才通过既有secondary incident/outbox发送`health:*` open，OK后发送same-incident
  resolved。optional、DEGRADED、瞬时/重复snapshot不告警，与owned-task circuit去重；unsafe plugin name外发前hash，
  `aico-state`只显示candidate数量。该路径不授权restart、provider replay或restore。
- Durable scheduled autonomy outcome receipts:state schema v12新增terminal outcome outbox；receipt绑定run/content SHA、source/outcome、
  criteria/source/evidence/failure与平台message id SHA。`aico-state`显示secret-free attempt/ACK摘要，不显示正文、target、raw message id
  或raw proposal/task identity；settled-without-outbox会在下一次scheduler工作前补建。
- Durable scheduled disposable recovery drill:state schema v11新增默认关闭的drill intent/receipt；按独立cadence对latest
  VERIFIED + custody VERIFIED artifact实际执行state/audit/memory production materializer，五次有界重试并将due/open/
  exhausted/stale投影到required health。crash同ID恢复且不花失败预算，open/latest exhausted目标跨配置切换受retention保护；
  receipt只输出secret-free component evidence并保持`business_restore_ready=false`。
- Bounded crash-consistent recovery retention:state schema v10新增默认关闭的owner opt-in retention；只选择超过age、最新代际之外且
  custody VERIFIED的scheduled pair，先持久化`PRUNING`与policy SHA，再deep verify并按artifact/sidecar顺序有界删除。
  restart按文件存在矩阵收敛，artifact-only fail closed；`PRUNED`保留secret-free receipt/policy tombstone，关闭开关不取消既有intent。
- Continuous recovery artifact custody:scheduled receipt schema v2和state schema v9新增destination fingerprint SHA、custody
  status/check time/failure count；backup与custody cadence独立，改变备份频率不能重置storage baseline。`aico-state`展示
  secret-free custody证据，service config支持独立check interval/max age。
- Durable scheduled core recovery backup:默认关闭的Phase1 scheduler为每个窗口先写SQLite intent，再生成core set并立即deep
  verify；artifact/receipt崩溃矩阵可复验收敛，1/5/15/15分钟最多五次，RPO stale/exhausted进入required health failure。
  schema v8与`aico-state`保存secret-free SHA receipt，service doctor拒绝缺失、checkout内或非owner-only目标。scheduler永不
  restore/delete/create missing mount，也不声称目标已off-device、加密或具备retention。
- Durable scheduled autonomy receipts:主SQLite schema v7新增scheduled autonomy intent表和
  PENDING/RUNNING/RETRYING/SETTLED/EXHAUSTED状态；provider dispatch前把intent绑定到proposal/task。
  `aico-state`分别展示secret-free intent状态、attempt/disposition和proposal/task identity SHA；backup/reset覆盖新表。
- Durable scheduled morning receipts:SQLite schema v6新增morning delivery outbox；每份晨报绑定稳定delivery id、内容SHA与
  所含standing receipt指纹，只保存平台message id的SHA。`aico-state`输出secret-free最近投递状态，不显示target、正文或
  原始message id；正式morning push现在强制配置state DB。
- Live provider authentication receipts:recovery-set schema v6固定required provider集合，并以`post_restore_evidence_assets`
  区分合同就绪与本次证据；`provider-auth-receipt`对Claude/Codex运行tool-free、non-persistent、bounded随机challenge，要求
  exact response、terminal success和usage。30分钟owner-only receipt绑定set/reinjection/revision/executable hash，且不保存
  challenge、prompt、output、error或credential；offline verify不会重放付费probe，unsupported provider保持fail closed。
- Independent dead-man receiver recovery:`aico-dead-man-recovery`提供online backup、exact schema/domain offline verify、
  disposable production restore drill和owner-fenced explicit restore；receiver lifespan持有同一kernel lock，有效live先做
  verified safety、无法验证的DB/WAL/SHM进入quarantine。core schema v5只记录外部合同就绪，不同步回滚observer。
- Secret-free runtime reinjection receipts:recovery-set schema v4只记录control-plane secret slot/channel与standing grant
  enabled mode；`reinjection-receipt`/`verify-reinjection`复用production preflight并绑定set/revision/owner decision，允许灾后
  轮换credential但不保存值/hash/identity/grant正文。AI provider远端认证单列为unresolved，不把presence冒充live auth。
- Reviewed configuration revision recovery:`aico-recovery capture`现在要求独立提供full reviewed Git commit，并验证clean
  HEAD/tree及active Project/Persona config blob/hash；schema v3区分配置未嵌入与恢复合同已就绪。新增`verify-checkout`
  在隔离恢复时拒绝wrong revision、dirty tree和config drift，不自动checkout/reset或打包secret。
- Tamper-evident memory recovery:`JsonlMemoryStore`现在用process lock、SHA-256 chain和tail checkpoint串行durable append，
  写失败不发布phantom索引，legacy需显式`aico-memory seal`。新CLI支持backup/offline verify/disposable drill/owner-fenced
  restore与corrupt-live quarantine；recovery-set schema v2按state→audit→memory绑定三个component，但仍不声明全局事务或full DR。
- Bounded-window core recovery set:`aico-recovery capture`在一个记录窗口内生成并绑定state/audit/memory component
  artifacts；fixed manifest强制`global_transaction=false`、`business_restore_ready=false`并列出config/secret/grant/
  receiver缺口。`verify`深入运行三套production verifier，`drill`再运行三套materializer；不提供combined restore。
- Owner-fenced audit restore:`aico-audit drill-backup`在disposable workspace复用production materializer并可输出
  owner-only evidence；`restore`强制expected SHA、AICO state DB owner fence、new preservation artifact和`--yes`。
  有效live先生成verified safety，损坏live进入unverified quarantine；双文件替换中断后fail closed且可重跑收敛。
- Portable audit recovery point:`aico-audit backup`在writer lock内把matching ledger/checkpoint导出为owner-only、
  no-overwrite单文件artifact；`verify-backup`可脱离live路径流式校验outer/member SHA、固定member contract，并在私有
  temp中复用production chain/checkpoint verifier。该artifact仍含明文审计正文，不替代off-device encryption/retention。
- Tamper-evident local audit ledger:JSONL event保持可读顶层字段并加入SHA-256 previous/head chain，owner-only
  checkpoint检测tail截断，process lock串行化writer；append-fsync/checkpoint原子更新的crash window可安全收敛。
  `aico-audit verify|seal`提供显式legacy迁移，runtime与service doctor遇到修改、重排、半写或权限异常时fail closed。
- Persisted authorization clock rollback fence:主SQLite保存authorization high-water，同进程结合monotonic elapsed；
  超过5秒的wall-clock回拨会事务性废止pending approval，并阻止新risk approval、direct preauthorization和scheduled
  standing grant直到时间追平。该机制不联网校时，也不声称TPM、签名或恶意主机防护。
- Owner-bound IM ingress:正式Phase 1 runtime在command解析、state/audit mutation和provider dispatch前同时校验
  configured channel、owner sender与trusted reply target；陌生sender无法自提自批风险任务，owner在错误群也不会收到
  状态回复。doctor/install要求显式binding，并禁止将临时identity discovery模式装成长驻服务。
- Bounded approval lease:risky task在创建approval时冻结默认24小时、可配置5分钟到7天的deadline；startup、老板视图
  与审批动作前会fail closed回收过期票据。SQLite原子写`approval=expired`、`task=rejected`和audit outbox，sink失败
  可重投；旧审批不能因重启后放大配置而延长，也不会自动重跑。
- Standing evidence fingerprint and drift gate:successful result保存最多16个repo-relative source的path/line/file
  SHA-256/size manifest，单文件最大256KiB；SQLite restart后老板面与下一次scheduled run会重算并将变化/缺失投影为
  drifted/missing、停止dispatch。正文/path/hash不进入老板IM，hash不冒充签名或业务真值。
- Bounded standing result envelope:owner-preauthorized结果总长固定32K，并限制criteria/stop/source/list/text/path；
  charter配置、JSON Schema、Pydantic、Codex Adapter和Orchestrator capture共同fail closed。超长、schema drift与
  duplicate key只留下bounded failure receipt，不进入老板IM或proposal raw state；该能力不声称provider token硬上限。
- Repository-grounded standing result contract:preauthorized Codex固定加载versioned output schema，按charter的
  `A*`/`S*`条目验证complete/blocked、repo-relative file/line存在性并持久化bounded receipt；raw JSON不进入老板IM，
  prior result missing/invalid/blocked会停止后续scheduled run。该校验不声称source语义真实。
- Provider-grounded standing usage circuit breaker:preauthorized Codex改用JSONL，在`turn.completed`记录实际token usage并
  写TaskBus audit/持久proposal receipt；owner grant新增必填`token_stop_threshold`，后续run在累计实测达到阈值或
  任一已消费run缺usage时fail closed。该能力明确是post-run熔断，不声称当前run硬token/cost上限。
- Restart-safe standing autonomy receipts:从既有accepted proposal与matching TaskSnapshot派生done/running/failed/
  interrupted/rejected/evidence-missing，投影到`/inbox`和`/morning`；不新增outcome表、不保存provider正文、不自动
  retry/refund，full identity只显示short ref。
- Non-mutating standing-autonomy deployment preflight:`aico-service doctor`现在复用真实Phase 1 Adapter/persona/project/
  grant binding validator，install前拒绝empty、target drift、unknown/missing charter seat、Codex disabled/wrapper和
  malformed config；成功只显示bounded count，失败不泄露identity/path/command。检查不打开state或调用provider。
- Owner-bound read-only standing autonomy:可选 external `0600` grant 精确绑定 owner IM identity、scheduled morning
  target、project/charter、expiry、persistent max-runs和duration；只有固定 Codex read-only/no-network/no-resume/
  no-collaboration command可在定时晨报后执行一个 inspection。interactive surfaces不消费，broad Adapter与配置漂移
  fail closed；本轮未创建真实grant或调用provider。
- Disposable AICO state restore drill:`aico-state drill`不打开live `--db`，在private temp中调用production restore、
  重新验证schema/table-count parity并自动清理；可选`0600`、atomic no-overwrite JSON report保存bounded evidence。
  local report不冒充off-device或full-asset disaster recovery。
- Owner-fenced AICO state recovery:`aico-state backup`使用SQLite online backup API生成`0600`一致单文件并输出
  SHA-256；`verify`只读检查integrity/schema；`restore --expected-sha256 --yes`拒绝active runtime、先生成
  pre-restore safety backup再原子替换。`reset --yes`现在也受同一runtime owner lock保护。
- Dead-man outage evidence bundle:admin可按完整 outage group导出 bounded、secret-free JSON,包含 current monitor、
  immutable open/resolved与local delivery/retry状态；`aico-dead-man-evidence` 可离线严格验证 runtime、顺序、最低
  complete outage数和all-delivered,并输出artifact精确字节SHA-256。显式strict验收还可限制artifact年龄、要求验收时刻仍fresh且
  已完成的silent probe，以及所有route healthy；默认历史审计语义保持兼容。pulse/public authority不能读取,hash不冒充来源签名。
- Deployable dead-man receiver:新增独立 FastAPI/CLI 服务、专用 SQLite monitor/outage/outbox、分离的
  pulse/admin credentials、receiver-time TTL、原子 late-recovery open/resolved、持久 1/5/15 分钟重试和
  non-root `/data` 容器契约；AICO liveness 改用独立 HTTPS URL/token,不再与 incident alert strict endpoint
  复用。真实独立主机、TLS、owner notification endpoint 和 outage 样本仍需部署侧验收。
- External dead-man runtime liveness:heartbeat v5 可向独立 HTTPS receiver 发送 secret-free ephemeral pulse,
  stable runtime id、per-process boot id、sequence 和稳定 `Idempotency-Key` 支持 bounded retry；receiver reference
  contract 按 acceptance-time TTL 独立生成 outage open/resolved。pulse 不写 SQLite/outbox,正常 stop 不自动
  disarm,Mac sleep/网络分区超过 TTL 保守视为 unavailable。
- Durable out-of-band runtime alerts:owned-task circuit open/healthy transition 通过独立 SQLite incident/outbox
  原子记录并由可插拔 HTTPS sink 至少一次投递 open/resolved;稳定 `Idempotency-Key`、严格队首顺序和持久化
  1/5/15 分钟退避关闭重复 heartbeat、sink failure、restart 与 accept-before-ack 窗口,heartbeat v4/doctor
  同时报告 disabled/healthy/pending/failed,且不保存 URL/token/exception。
- Runtime component health:heartbeat schema v2 以 required/optional 分级记录 Channel、默认/可选 Adapter 和 morning scheduler 状态;`aico-service doctor` 区分 process stale、primary path failed、optional degraded 和 legacy unknown,不持久化异常详情或 secret。
- Channel-aware durable entrypoint:`aico-service` 为 Telegram 启动 polling runtime、为 Feishu 启动 webhook runtime,两者共用 component-health heartbeat lifecycle。
- `aico-service` macOS durable runtime operator:secret-free LaunchAgent render/install/restart/status/doctor/uninstall,登录启动、异常重启、可恢复 plist 替换/移除和 runtime heartbeat。
- Lead standing-charter proposal queue:项目空闲时由显式 charter 生成一个可审核候选并进入 `/inbox`、`/morning` 和 SQLite;只有 `/proposal accept <id>` 才走正常任务/风险/审批链,拒绝或查看不会执行。
- `/view` project-scoped Boss Brief:自包含 HTML 第一屏按审批、阻塞、运行中、夜间托管给出确定性 First action,并提供回 IM 的 `/approve`、`/reject`、`/task`、`/inbox`、`/morning` 动作。
- `projects/sme-agent/`:独立的中小企业 Agent 项目骨架,包含可持续人机对齐协议、AICO Lead/多角色团队配置、项目状态与 handoff 账本,以及术语/知识/指标/维度/数仓资产/实体关系的首个可测试元数据垂直切片。
- SME Agent week-one commercial delivery slice:新增电商样例 CSV、客户 intake 评估、经营诊断报告模板、确定性收入/退款/广告/库存诊断规则、Markdown 报告渲染、交付 SOP 和样例报告,支撑淘宝/千牛服务商品冷启动。
- SME Agent premium commercial assets:默认 199 / 699 / 1999 RMB 价格梯度、淘宝/千牛发布级商品页、小红书 7 篇完整正文、详情页视觉文案包、客户项目目录、evidence manifest 和脱敏字段扫描。
- SME Agent ecommerce delivery runner:从订单/广告/库存 CSV 路径生成客户 workspace、诊断草稿、evidence manifest 和脱敏检查结果,并新增 report generation runbook。
- SME Agent Taobao visual assets:新增高级信任主图、收入下降痛点主图和详情页长图预览 SVG,用于淘宝/千牛服务商品上架前视觉验证。
- SME Agent commercial quality pack:导出淘宝 PNG 和小红书 7 张封面 SVG/PNG,新增小红书封面生成脚本与产品质量审查记录,统一价格口径并修复低质感措辞、标签不一致和封面溢出问题。
- SME Agent domain templates:新增直播/内容电商、本地生活和商业化广告行业模板,覆盖业务过程、维度、指标、敏感字段、人工核对点和扩展入口,用于验证商家数据能否被非玩具化纳入诊断。
- SME Agent live-commerce validation loop:新增中文导出表头映射、直播/订单拟真样例、支付 GMV/GPM/退款率/支付转化确定性计算和人工复核 Markdown 报告。
- SME Agent public dogfood fixture:新增基于 KuaiLive / OnlineGMV 公开来源形态的直播电商缩放样例、来源说明和 evidence 报告,用于业务效果验收。
- SME Agent self-serve local intake:直播诊断工作台支持选择或粘贴两份脱敏 CSV,在 localhost 进程内完成受治理字段映射;缺证据时只追问字段,证据完整时复用确定性诊断和交付报告。
- SME Agent governed live-commerce delivery:新增 `sme-agent-live-commerce-deliver`,按 customer/run-id 生成 authorization-referenced mapping、questions、redaction、SHA-256 evidence manifest、delivery status 和条件式诊断;raw CSV 默认不保留。
- SME Agent merchant-owner acceptance console:本地 workbench 预览真实受治理交付包,并提供不持久化的 `199 RMB` 五项验收清单;是否值得付费仍由真实老板决定。
- OSS 上线治理资产:新增 `CODE_OF_CONDUCT.md`(Contributor Covenant 2.1 中英双语)、
  `.github/FUNDING.yml`(占位)、`.github/dependabot.yml`(weekly pip + monthly
  GitHub Actions 升级)。
- `docs/contributors/quickstart.md`:30 分钟内完成第一次 PR 的 Contributor Quickstart,
  零 Telegram bot / 零 LLM token 路径。
- `docs/launch/playbook.md`:面向 1k–10k star 的上线作战书(Show HN / Reddit / X / dev.to
  模板,D0–D90 节奏,反指标清单)。
- `docs/launch/v0.1.0-release-notes.md`:v0.1.0 GitHub Release notes 草稿,可直接贴。
- README 增加 Contributing 段落对 Contributor Quickstart 与 Code of Conduct 的链接。
- `.github/ISSUE_TEMPLATE/config.yml` 新增 Discussions 与 Contributor Quickstart 联系链接。
- `SECURITY.md` 明确响应 SLA(72 小时确认 / 14 天修复)和私有 advisory 链接。
- `CONTRIBUTING.md` 顶部加 Code of Conduct 引用 + first-time contributor 入口。

### Fixed
- Telegram active polling task 或 morning scheduler task 意外退出时不再继续报告 healthy;关闭流程会安全消费后台异常,健康检查 timeout/插件异常只转成脱敏状态。
- Feishu LaunchAgent 不再错误启动没有 webhook listener 的 `aico-phase1`;webhook lifespan 现在也写 running/stopped component heartbeat。
- Phase 1 runtime 不再在非阻塞 Channel 启动返回后立刻停止 morning push scheduler;定时早报现在保持到 runtime stop,启动失败仍会清理 scheduler。
- `/view <project>` 不再把其它项目的 task payload、失败原因、audit event 或 overnight goal 混入当前项目附件;task/audit/memory/offline-delegation truth 先按 project 投影再渲染。
- SME Agent 客户交付 runner 不再复用可被重试覆盖的单一报告路径,也不会在缺字段、无数据或直接个人信息风险时生成诊断/复制 raw CSV。
- SME Agent workbench 不再只用文案提醒隐私风险;直接个人信息表头现在与交付 runner 一致地硬阻断指标、finding、报告展示/复制和商业验收控件。
- SME Agent 不再把缺字段、只有表头或畸形 CSV 当作零经营表现;这些状态现在稳定返回补数问题或可读错误,不生成虚假指标和结论。
- Provider session 正被其它任务占用时,老板侧即时回复、恢复摘要与 aico-view 现在显示可执行的
  role-busy 指引,不再泄漏 `Session ID`;原始诊断仍保留在 TaskBus 与显式 `/task`,未知错误保持可见。
- `/ask --exact <role> <task>` 和明确的“只输出本条/不要请求协作”约束现在会形成可审计的
  non-delegating task contract:跳过 lead decision / Goal Brief 自动扩展,禁止 `@role` 生成协作子任务;
  `/ask lead` 解析到实际岗位时会先显示路由说明,避免短验收被静默扩成多 Agent 链。
- Telegram 紧凑表格现在会把末行后粘连的详情文案从表格列中分离,避免误生成 `补充1`,并将重复的 `/view` 提示收敛为一条。
- Telegram Bot API 出站请求遇到 TLS 建连 `ConnectTimeout` 时会有限重试一次,避免一次握手抖动中断已完成的 agent 结果;不会重试更可能导致重复消息的 read/write timeout。
- 风险识别不再把“输出详情命令”这类展示要求误判为 shell 执行,显式运行命令和测试仍保持审批门禁。
- Telegram long polling default client timeout now exceeds the Bot API poll timeout, preventing empty timeout warnings during normal `getUpdates` waits.
- Streamed agent output now uses a mobile-readable 1400-character split target with readable boundaries, so long reviewer handoffs no longer wait until Telegram's API limit before splitting.
- `/overnight` queued / listing / incomplete messages now explain the boss route: `/inbox` for current attention, `/morning` for handoff, `/task` for exact trace, `/view` for HTML snapshot, and `/brief` only for project context.
- `/aico-view` is now accepted as an alias for `/view`.
- Delegate agent 的流式 Telegram 输出现在会在进入 native HTML / rich text renderer 前拆分粘连 heading、section label 和 `• High/Medium/...` 列表,避免 implementer / reviewer handoff 糊成一整段。
- `/overnight` 现在会校验最终 handoff 是否可交接:CLI exit 0 但输出过短或缺少 done / blocked / risks / next actions 时,任务会改标 failed 并回 IM 提示不完整,避免半句输出伪装成成功。
- `/goal` / Outcome Grader / `/dream` / `/recall` 等 Phase 8 内置命令消息现在统一走 IM rich text renderer,标题、列表、字段 label 和 slash command 能正确格式化。
- `/dream` 输出从逐条任务日志改为按阻塞/失败原因聚合的 reusable lesson candidates,并显式说明 candidate memory 不会自动注入 prompt。
- IM rich text renderer 现在会统一规范化模型 Markdown 输出:拆分粘连 heading、渲染 Markdown table 为等宽表格、保留 fenced code block,并通过 Telegram HTML parse mode 展示。
- Telegram native HTML fallback 现在会拦截 `<pre>` 中的 Markdown pipe table,回退到紧凑表格 + `/view` 懒加载详情,避免 raw `|---|` 直通 Bot API payload。
- Telegram Channel 现在会将紧凑表格的连续整行 code spans 合并为单个 `<pre>` 块,客户端可对齐显示并整块复制;行内 `/view` 仍保持独立 `<code>`。
- `Collaboration requested` 提示改为结构化富文本输出,显示 source / target。
- IM rich text fallback 现在能正确处理单行 fenced code,例如 ```uv run pytest``` 不再被吞。
- Telegram native HTML sanitizer 现在会保留 `<pre>` / `<code>` 中的 `<id>` / `<task_id>` 文本占位符,不再因此把整条 native HTML 回退成裸标签文本。
- quiet heartbeat(`Still running...`)现在只作为临时状态提示展示,不会进入最终 agent 输出缓冲,避免污染 Telegram native HTML 结果。

### Added
- 项目立项,北极星三句话确立
- `AICO_VIEW_ENABLED=true` IM 快照模式:新增 `/view [project]`,在 `aico-phase1`
  内生成自包含 `aico-view-<project>.html` 并通过 Telegram `sendDocument` 发送;
  不启动本机 HTTP 服务、不要求手机访问 localhost。详见 ADR-0036。
- `AICO_VIEW_TOKEN` 鉴权:`aico-view` 在非 loopback host 部署时**必须**设 token,否则所有请求 401;loopback 部署无 token 时保持便利访问;客户端可以走 `X-AICO-Token` header 或 `?token=` query。详见 ADR-0035 和 `docs/human/aico-view-deploy.md`。
- `/timeline [--since 24h --source memory|task|audit --limit 30 --trace <id>]` lead 内务命令:UnifiedEventIndex 的过滤视图。
- `/rollback memory|experience|task <id>` lead 内务命令:精确撤销 AICO 内部状态,每次都写一条 `rollback_performed` audit;`/rollback task` 只写 audit 标记,**不级联**撤 memory 副作用;永远不撤 git/shell/file。详见 ADR-0034。
- `aico-view` read-only 移动端 Web:Timeline / Task Trace / Memory Tree 三视图,挂在 `AICO_AUDIT_LOG_PATH` / `AICO_MEMORY_PATH` / `AICO_STATE_DB_PATH` 上;所有路由 GET-only,写操作全部回 IM。默认 `127.0.0.1:8765`,V3 会加 token 鉴权后再支持隧道。
- `/undo` boss-only 命令:撤销最近一次 AICO 内部状态变更(memory append / experience promote / archive),**不撤** git / shell / file。每次回复都明确边界。
- `/why [short_id]` boss-only 命令:从 UnifiedEventIndex 取该 trace 的全部事件;空参数返回最近一条事件的 trace。
- `/inbox` 和 `/morning` 输出在末尾追加 "Recent activity" 摘要,并提示 `/why <short_id>` 用法。
- `/experience review|list|promote|archive` lead 内务命令:管理 Dream 生成的 candidate experience 晋升 / 列表 / 失效;active experience 会按 role 自动注入 role system prompt。
- `/language [en|zh]` agent 回复语言命令:默认英文,可按 IM chat 作用域限制后续 agent 回复语言,不改变内置命令语言。
- `AICO_PREFER_NATIVE_CHANNEL_FORMAT=true` Telegram native output pilot:agent 可优先输出 Telegram HTML,通过白名单验证后直接发送;验证失败自动回退 rich text。
- 完整文档体系骨架(README / AGENTS / NORTH_STAR / STATUS / journal 等)
- Agent 接手协议(AGENTS.md 强制阅读路径)
- 踩坑录、轮次记录、卡点跟踪三大演化文档
- `docs/decisions/README.md` 与 `docs/playbooks/README.md` 索引文档
- ADR-0001 技术栈选型,确认 Python 3.11+ / FastAPI / asyncio / Pydantic v2
- Python 项目骨架、`AIAdapter` / `IMChannel` 协议草案和值对象单测
- ADR-0002 Adapter / Channel 协议定稿
- 最小 Router / TaskBus / Orchestrator 假链路和端到端单测
- GitHub Actions CI 骨架,执行 pytest / ruff / mypy
- Phase 1 MVP 单链路验收 Playbook
- Telegram Channel 文本 MVP,支持 long polling、文本发送、消息编辑和删除
- Claude Code Adapter MVP,支持 CLI 文本任务、流式输出和中断
- `aico-phase1` 本地启动入口,串接 Telegram Channel、编排核心和 Claude Code Adapter
- Phase 1 真实 Telegram Bot 端到端验收通过
- AdapterRegistry 多 Adapter 注册与按 persona 路由
- `/status` 文本命令,可在 IM 中查询 Adapter 状态
- Codex Adapter 文本 MVP,默认 read-only sandbox
- `/help`、`/claude <task>`、`/codex <task>`、`@codex <task>`、`codex: <task>` 文本命令
- Phase 2 多 Adapter 状态与路由验收 Playbook
- 任务生命周期状态机,支持 `running` / `done` / `failed` / `interrupted` / `rejected`
- ADR-0003 Phase 3 Persona 与 Broadcast 边界
- PersonaRegistry 最小实现,支持 `implementer` / `reviewer` 职责映射
- `/broadcast <task>` 文本命令,可把任务派发给当前启用的 persona
- Phase 3 Persona 与 Broadcast 验收 Playbook
- ADR-0004 Persona 外部配置
- `AICO_PERSONA_CONFIG_PATH` 配置入口和 `config/personas.example.json` 示例文件
- ADR-0005 Phase 4 审批与审计边界
- ADR-0006 审批权限策略
- ADR-0007 远程审批与 Adapter 能力边界
- ADR-0009 Phase 5 AI 间协作协议
- 危险任务风险识别模型,覆盖 `read_only` / `write_files` / `shell_exec` / `destructive`
- `/approve <task_id>` 与 `/reject <task_id>` 审批命令
- 内存审计事件模型,记录任务提交、审批结果、Adapter 派发和任务完成/失败/中断
- `/audit` 只读命令,可在 IM 中查看最近审计事件
- `AICO_APPROVAL_REVIEWER_IDS` 配置入口,可指定额外审批人
- Adapter 风险能力门禁,read-only Adapter 会拒绝写文件 / shell / destructive 任务
- `AICO_AUDIT_LOG_PATH` 配置入口,可将审计事件追加写入 JSONL 文件
- Phase 5 轻量协作指令,支持 Adapter 输出 `@persona: request` 触发目标 persona 子任务
- `collaboration_requested` 审计事件,记录 AI 间协作的 parent task 与 child task 关系
- 独立 command parser,统一解析 `/help`、`/status`、`/audit`、`/broadcast`、`/approve`、`/reject`
- 后台运行日志,默认写入 `logs/aico.log`,覆盖 Telegram 入站、命令 / 任务路由、Adapter 进程、流式输出和长文本分片
- ADR-0010 Agent Session 与 Harness 边界,明确 AICO 薄 harness 只做会话和能力门面
- `AgentCard` / `AgentSession` / `ProviderSessionRef` 与内存 `AgentSessionStore` 骨架
- `/sessions`、`/new <agent>`、`/use <session_id>` 会话命令 MVP,支持在 IM 中创建会话引用并把普通消息续到当前 active session
- Claude provider session resume MVP:`/new claude` 创建的 AICO session 会在首次普通消息使用 `--session-id`,后续普通消息使用 `--resume`
- Codex provider resume 命令构造支持:当 session 已有 Codex provider ref 时,Adapter 会使用 `codex exec resume <session_id> <prompt>`
- `/bind <session_id|agent> <provider_session_id>` 显式 provider session 绑定,用于把已有 Codex/Claude 会话挂到 AICO session
- `/agents`、`/agent <agent>`、`/skills <agent>`、`/tools <agent>` agent 体验命令;skills/tools 由底层 provider 自己回答
- `/agents` 和 `/agent <agent>` 输出末尾追加短 `Next` 指导命令,引导查看详情、任命或创建 session
- Project Assignment Layer MVP:新增 `agents` / `projects` / `assignments` 配置模型、`AICO_PROJECT_CONFIG_PATH`、`config/projects.example.json` 和项目任命查看命令
- `/projects`、`/project <project>`、`/use project <project>`、`/assignments [project]`、`/assignment <seat>` 项目/工位命令
- project-scoped session 绑定:普通消息在 active project 下会路由到默认 assignment seat,provider session ref 挂在 assignment 上
- Project Team / Appointment 命令 MVP:新增 `/team`、`/who <role>`、`/appoint <agent> as <role>`、`/ask <role> <task>`、`/lead <role>`
- RoleTemplate / ProjectRoleOverride / Appointment 配置模型,内置 implementer、reviewer、tester、pm、architect、security、docs、ops、analyst、designer 等岗位模板
- Appointment prompt stack MVP:project-scoped 任务会注入 Agent、RoleTemplate、Project、Appointment Contract 和当前任务上下文
- `/brief [project]` 和 `/risks [project]` 项目办公室只读简报命令,基于本地 project/team/task/audit 状态生成摘要和风险列表
- `/brief` 现在会读取配置中的 north star / status / journal 文档短片段,`/risks` 会读取 blockers / pitfalls 文档短片段
- `/daily [project]` 和 `/weekly [project]` 本地项目报告命令,按 24 小时 / 7 天窗口聚合团队、完成项、未完成项、风险和项目文档短片段
- `/blockers [project]` 项目卡点命令,用于展示等待审批、失败/拒绝/中断任务和未知 persona 等当前卡住的工作
- `/next [project]` 下一步动作建议命令,基于本地 project/team/task/audit 状态给出待审批、失败恢复或 lead role 派工建议
- `/roles [project]` 项目岗位命令,展示 role 模板、默认权限和已任命 / 未任命状态
- `/roles` 紧凑岗位板、`/roles all` 全量岗位板和 `/role <id>` 岗位详情,让 IM 中默认只显示核心/专家岗位
- `/project`、`/team`、`/roles`、`/role <id>` 输出末尾追加短 `Next` 指导命令,让项目办公室流程更顺滑
- Role scope 词表收敛为 `docs` / `code` / `tests` / `ops` / `audit`,并让 `/appoint <agent> as <role>` 默认继承岗位 scope
- `/role propose <诉求>`、`/role confirm`、`/role discard` 岗位草案确认流,由当前项目 lead role 起草新 role,用户确认后加入当前项目进程内 roles
- `/unappoint <role>` 项目撤任命令,用于撤销当前项目某个 role 的进程内 appointment
- 平台无关 IM render contract 第一切片:`MessageContent` 支持文本 spans 和 actions,Telegram Channel 可映射为 HTML 与 inline keyboard
- ADR-0013 Platform-Neutral IM Render Contract
- Telegram callback query 会转换为普通 `IncomingMessage`,按钮 action 可复用现有 slash command 通路
- `/brief`、`/risks`、`/blockers`、`/next` 顶部老板摘要 MVP,由当前项目 lead 基于本地事实包生成只读 summary
- `/daily`、`/weekly` 顶部老板摘要 MVP,复用项目状态 summary 的事实保留和失败降级策略
- `/interrupt <task_id>` 远程中断命令,支持用 task id 前缀停止 running 任务
- Codex output idle timeout MVP,默认无 stdout 自动终止底层 CLI 并释放 `codex: busy`;Round 98 默认阈值调整为 300 秒
- `/tasks [limit]` 和 `/task <task_id>` 任务追踪命令,用于在 IM 中查看最近任务、单任务详情和可用动作
- `/task <task_id>` 详情现在展示协作 parent / child trace,可从父任务跳到 reviewer 子任务,也可从子任务回看发起它的 persona 和父任务
- ADR-0014 Phase 6 可观测范围决策,确定先做 IM-first `/metrics` MVP,再评估 Mac / Web 可视入口
- `/metrics` 本地可观测命令,展示 24h / 7d 任务状态、agent 接活数、open work、协作次数和平均终态耗时
- ADR-0015 Observability Event Replay,确定先复用 audit JSONL 为 `/metrics` 提供重启后历史指标恢复
- MetricsReport 结构化观测模型,包含 summaries、glance 状态和 token/cost 可用性,供 IM / CLI / 后续 macOS 或 Web 入口复用
- `aico-metrics` CLI,可从 audit JSONL 输出 text 或 JSON 指标,用于本地排障和未来 glance 原型
- ADR-0016 Status Island and Usage Boundary,确定 Phase 6 以 glance 数据原型和 usage 审计事件边界收口
- `aico-glance` CLI,可从 audit JSONL 输出本地 Status Island text/json 快照,包含最近任务和 `/task` / `/approve` / `/reject` / `/interrupt` 命令提示
- `task_usage_recorded` 审计事件类型与 usage JSON detail 约定,供 Adapter 未来上报真实 token/cost
- ADR-0017 Optional Agent Adapters,确定 Cursor / CodeFlicker 第一切片默认作为可选只读 Adapter 接入
- Cursor Adapter MVP,通过 `AICO_ENABLE_CURSOR_ADAPTER=true` 启用后可进入 `/agents`
- CodeFlicker Adapter MVP,通过 `AICO_ENABLE_CODEFLICKER_ADAPTER=true` 启用后可进入 `/agents`
- ADR-0018 Full Agent Adapters and Feishu First Channel,确定在 AICO 审批门禁下开放 Cursor / CodeFlicker / Trae / Gemini 完整 CLI 能力,并选择飞书作为第一个非 Telegram Channel
- Trae Adapter,通过 `AICO_ENABLE_TRAE_ADAPTER=true` 启用后可进入 `/agents`
- Gemini Adapter,通过 `AICO_ENABLE_GEMINI_ADAPTER=true` 启用后可进入 `/agents`
- Feishu Channel 第一切片,支持 tenant token、文本发送、消息编辑/删除、URL verification 和 `im.message.receive_v1` 文本事件解析
- 默认 AI Company role 模板扩展 PM、Senior Architect、Golden Tester、Market Risk、Legal Compliance 等有效公司岗位
- Phase 7 共享记忆第一迭代:新增 `MemoryAtom` / `MemoryScope` / `MemoryEvidence` / `MemoryEdge` / `MemoryStore` / `JsonlMemoryStore`,以 append-only JSONL 作为 A2A Memory Fabric 的可审计权威源
- Phase 7 共享记忆第二迭代:新增 `MemoryPacket` / `MemoryRetriever` / `MemoryGovernor`,project-scoped task prompt 可自动注入受控共享记忆
- Phase 7 共享记忆第三迭代:新增 `AICO_MEMORY_PATH` 和 `/remember` / `/recall` / `/forget` IM 控制入口,作为 project-scoped 记忆纠错、补充和排障通道
- Phase 7 共享记忆第四迭代:新增 boss feedback 自动抽取,明确偏好可写入 boss global 或 project memory,不确定反馈进入 candidate 且不注入 prompt
- Phase 7 共享记忆第五迭代:新增 `MemoryBroadcastService` / team receipt / `broadcast_to` edge,并提供可关闭的 A2A `memory_refs + delta` payload 实验
- Phase 7 共享记忆验收流:新增企业/团队管理 acceptance test,覆盖跨项目隔离、老板偏好、candidate 不注入、team broadcast、JSONL 重启恢复和 A2A memory refs 回退
- `/remember` 未启用 `AICO_MEMORY_PATH` 时返回可执行的重启配置提示,Quickstart 也默认展示 memory path 配置
- Phase 7 记忆召回升级为可插拔 `MemorySemanticScorer`,默认支持中文长句复述和常见中英项目管理术语别名
- Phase 7 记忆检索升级为可解释 retrieval contract:新增 `MemoryRetrievalQuery` / `MemoryRetrievalHit`,保留 semantic、scope、recency、confidence、evidence、graph 和 final score。
- Phase 7 记忆检索支持保守 graph expansion 和 role/task-aware query hints,`/recall` 会展示 final / semantic / scope / graph score 分项。
- Phase 8 lead 决策记忆基础:新增 `MemoryPurpose` / `MemoryAtom.purpose_tags`,支持 `general_context`、`public_broadcast`、`task_key_progress`、`task_private` 和 `decision_review`;普通检索默认排除 `task_private`,`/recall` 和 Prompt Stack 会展示 purpose。
- Phase 8 lead decision workflow:决策类 lead/default role 任务会优先召回 `public_broadcast` / `task_key_progress` / `decision_review` 记忆,自动咨询 challenger 和 reviewer,要求 lead 输出固定 decision memo,并写入 `lead_decision_recorded` audit 与 `decision_review` memory。
- Phase 8 Goal Brief v0:新增 `/goal [role] <objective>` 轻量目标契约;带明确验收/停止/证据 marker 的 `/ask` 会保守附加 `AICO Goal Brief`,并在 `/task` 中展示 goal id、objective 和 acceptance。
- `AICO_STATE_DB_PATH` / `SQLiteTaskStateStore` 第一切片:task records、task snapshots 和 pending approvals 可写入 SQLite,重启后继续支持 `/tasks`、`/task` 和 `/approve` 的 AICO 业务状态恢复。
- ADR-0029 Phase 8 Absence Loop:把 actionable inbox、morning handoff、outcome grader、Dream/runbook memory 和 hybrid retrieval 固定为可逐轮验收的老板缺席闭环 sprint 队列。
- Phase 8 Absence Loop playbook:新增每个 sprint 的直接 IM 验收脚本和防跑偏护栏。
- `/inbox` actionable 化:新增 `First action`,并把审批、running、失败恢复、handoff、Goal/decision、协作 follow-up 都渲染为可直接执行的下一步命令。
- `/morning` 手动早报命令:按 active project 汇总 done、blocked、risks、overnight handoffs 和 next actions。
- Outcome Grader 第一切片:Goal Brief 完成后自动派 tester / reviewer 验收,grader task 会进入 `/task` 和 `/inbox` follow-up。
- `/dream` Dream/runbook memory 第一切片:从近期项目任务信号生成 reviewable candidate memory,默认不注入 prompt。
- 本地 hybrid memory scorer:MemoryStore / MemoryRetriever 默认支持 exact phrase、phrase overlap 和 semantic alias fallback。
- `aico-release-room-demo` 无 token 本地 demo:使用 deterministic fake adapters 跑 Release Room 管理链路,不需要 Telegram Bot Token 或真实 LLM/CLI provider。
- GitHub PR template 和 good-first-issue issue template,降低公开后外部贡献者参与门槛。
- Telegram / IM rich text 输出继续打磨:`/agents` 等普通列表会渲染为 `•` 列表,`agent_title:` / `role:` / `adapter:` 等字段 label 左侧会加粗。
- Core structure cleanup:新增 `OrchestratorTaskFactory` 和 `TaskStateRepository`,让 `Orchestrator` / `TaskBus` 重新低于项目单类尺寸硬约束。
- 长静默 Adapter 任务 quiet heartbeat:底层 CLI 真实运行但长时间没有 stdout 时,IM 会周期性显示 `Still running...`,并继续保留 `/interrupt` 和 no-output idle timeout 兜底。
- `/inbox` 当前项目老板收件箱第一切片:聚合待审批、running/failed/interrupted、离线托管、Goal Brief / lead decision 和协作 follow-up,作为老板回来看项目的 IM 入口。
- CLI Adapter 子进程启动时显式关闭 stdin,避免 Codex 0.125 在非交互任务里等待 inherited stdin 的额外输入而长期无 stdout。
- CLI Adapter 子进程 stderr 持续后台 drain,避免 Codex 运行日志/进度写满 stderr pipe 后反压阻塞 stdout。
- `/overnight` 托管工单持久化:配置 `AICO_STATE_DB_PATH` 后,最近托管工单可跨重启恢复。
- `aico-state` 本地状态库工具:可查看 SQLite schema version / 表行数,也可显式 reset 已知状态表;`AICO_STATE_DB_PATH=true` 会映射到 `.aico/state.db`。
- Claude/Codex/Cursor/CodeFlicker/Trae/Gemini CLI adapter 支持可配置并发,默认最多 5 个运行中任务;`/agents` 和 `/appoint` 会展示并发与建议任命上限。
- Feishu webhook runtime:新增 `AICO_CHANNEL=feishu`、`aico-feishu-webhook`、`/healthz` 和默认 `/feishu/events` 事件回调入口,飞书文本事件可进入现有 Orchestrator。
- Feishu webhook 事件幂等:按 v2 `header.event_id` 或 v1 `uuid` 做本地 TTL 去重,避免平台重试重复触发 AICO 任务。
- Phase 8 离线托管第一切片:新增 `/overnight <goal>` project-scoped 托管工单,派给当前 lead/default role,并固定早报验收入口 `/daily`、`/tasks`、`/task`。
- Lead decision team contract 第一阶段:默认角色库新增 `challenger` / Critical Philosopher,项目办公室和 `/team` 展示 team readiness,project lead prompt 增强为可在授权范围内替 boss 做低风险决策。
- `/overnight` 现在要求当前项目团队至少有 appointed lead 和 challenger;缺 challenger 时会提示 `/appoint <agent> as challenger`,不会派发托管任务。
- Release Room 主 demo 第一阶段:新增 `examples/release-room` 示例项目、AICO project/team 配置、demo script、录屏 storyboard、`docs/examples/release-room.md` 和 release-room playbook,用于展示 project/team/role/memory/approval/audit/overnight handoff 的完整协作路径。
- Release Room 主 demo 第二阶段:新增本地 acceptance test 和 `examples/release-room/transcript.md`,用 fake adapters 验证 `/team`、`/remember`、`/ask`、`/approve`、`/overnight`、`/daily`、`/tasks`、`/metrics`、`/audit` 管理链路。
- Release Room Stage 3 录屏准备:新增 `shot-rhythm.md` 和 `make-gif.sh`,把 Stage 2 transcript 压成 30-60 秒 README GIF 镜头节奏,并用本机 `ffmpeg` 完成 GIF 转换。
- Release Room Stage 3 真实 Telegram dogfooding 记录:project office、team、project memory 和 `/interrupt` 跑通;真实 provider 输出阻塞 public GIF 已记录为 B-003 / P-017。
- Release Room Stage 3 Codex 输出清理:避免 Codex resume 非 Codex provider session,过滤 CLI warning / HTML / resume error 噪音,并在同一 role 改任命到不同 agent 后重建 assignment session。

### Changed
- 将扁平化文档归位到 `docs/agent` / `docs/journal` / `docs/architecture` / `docs/human`
- 将 role proposal 内部任务提交和输出收集从 `Orchestrator` 拆到 `RoleProposalCoordinator`,保持 `/role propose` / `/role confirm` 用户语义不变
- 将 `/role propose` / `/role confirm` / `/role discard` 命令处理从 `ProjectCommandHandler` 拆到 `ProjectRoleCommandHandler`,降低项目命令类体积
- 将 `/brief` / `/risks` / `/blockers` / `/next` / `/daily` / `/weekly` 命令处理从 `ProjectCommandHandler` 拆到 `ProjectStatusCommandHandler`,集中项目状态与报告逻辑
- `AICO_CODEX_OUTPUT_IDLE_TIMEOUT_SECONDS` 可配置 Codex accepted 后无 stdout 的空闲超时秒数;默认从 90 秒放宽到 300 秒。
- Cursor / CodeFlicker Adapter 从只读 MVP 升级为完整 `code_edit` / `shell_exec` 能力,危险任务仍先走 AICO `/approve`
- `configure_logging()` 现在将 `httpx` / `httpcore` logger 降到 WARNING,避免 INFO 日志把 Telegram Bot API token URL 写入文件日志。
- 项目办公室关键消息现在使用 render hints 标记首行标题,`/role propose` 消息带 Confirm / Discard actions
- 项目状态 LLM summary 会保留完整 `Facts` 原文;summary 失败时降级为原事实消息,不阻塞状态查询
- Boss summary 中的轻量 Markdown 会转换为 render spans,避免 `**bold**`、反引号和列表标记在 Telegram 中裸露
- 项目状态命令的 Facts 区域现在会为小节标题和 slash command 生成 render spans,`/blockers` 即使没有 summary 也能展示基础格式
- 项目状态命令的 Facts 区域现在会把 `- ` / `* ` 规范化为 `• `,并将 `**bold**`、反引号和斜体 Markdown 转为 render spans
- 流式 provider 输出和内置命令输出会先经过平台无关 rich text renderer,将轻量 Markdown 标题、小节标题、加粗/斜体/代码和 slash command 转成 spans;Telegram 渲染为 HTML,标题前自动留出结构空行。
- 项目状态命令的 Facts 文档片段现在会把 Markdown heading `#` / `##` / `###` 转为加粗标题,不再裸露井号
- `/status` 现在会展示 Adapter 状态和最近任务状态
- 危险任务现在会先进入 `waiting_approval`,批准后才派发给 Adapter
- 审批交互支持直接发送 `/approve` / `/reject` 处理唯一待审批任务,并支持短 task id
- Claude Code 默认命令使用 `--permission-mode bypassPermissions`,由 AICO `/approve` 作为远程审批入口
- `/audit` 输出改为多行块格式,提高 Telegram 可读性
- 流式长输出超过单条消息安全长度时会拆成多条 IM 消息继续发送
- 风险识别改为可测试规则表,后续新增中英文风险 marker 不需要改核心判断流程
- 将 agent / project / assignment 命令处理拆到 `orchestrator_commands.py`,保持 `Orchestrator` 小于 500 行硬约束
- `/project <project>` 现在作为进入项目办公室的主入口;旧 `/use project`、`/assignments`、`/assignment <seat>` 保留为兼容或排障命令
- `/default <role>` 改为兼容别名,主路径使用老板视角更自然的 `/lead <role>`
- `/risks` 收窄为真正项目交付风险,不再把普通 `write_files` 审批请求或 `unknown adapter/persona` 路由噪音直接当成项目风险
- Project/Team/Report 命令消息渲染拆到 `project_messages.py`,保持通用命令消息和项目状态面解耦
- `/project` 在已有 active project 时会重新展示当前项目办公室;`/project <project>` 仍用于进入指定项目
- Project Team 主流程新增本地 acceptance flow 单测,覆盖项目办公室、状态面、任命、派活、牵头 role、撤任和普通消息回退
- `Orchestrator` 命令分发瘦身,大段 command dispatch 移出类体,保持单类行数低于硬约束
- Project appointment 现在按 project + role 保持唯一负责人;重复 `/appoint` 同一 role 会覆盖原任命,不会在 `/team` 里追加重复成员
- `/team` 现在展示当前 lead role,并在对应团队成员行标记 `[lead]`
- 配置 `AICO_AUDIT_LOG_PATH` 后,启动时会回读旧 audit JSONL;`/metrics` 会从审计事件重建历史 task 指标,再与当前进程内 task 状态合并
- `/metrics` 现在包含 `glance` 小节,快速展示当前 24h 的 open / running / waiting approval / failed 状态
- `MetricsReport` 现在包含 recent tasks 和真实 usage audit events 汇总出的 token/cost 字段;无真实 usage 时仍显示 unavailable
- `MemoryRetriever` 现在先生成可解释 hits,再投影为 `MemoryPacket`;排序综合 semantic match、scope closeness、confidence、recency、evidence 和预留 graph signal。
- `/recall` 现在复用 `MemoryRetriever`,并展示每条记忆的召回 reason,方便纠错和排障。
- `MemoryRetriever` 现在会沿 `supports` / `derived_from` / `broadcast_to` 扩展一跳同 scope graph 邻居,并把 `role_id` / `agent_id` / `task_kind` 作为检索提示参与排序。
- `MemoryBroadcastService` 现在可接入 audit log,每次 team broadcast 会记录 `memory_broadcasted` 审计事件和 receipt 详情。
- 默认 project agent id 现在优先使用 persona 名;同时 project appointment 可在唯一匹配时按 provider 名解析 agent,避免 `codeflicker` / `flicker` 这类 alias 漂移。
- Codex / Cursor / CodeFlicker / Trae / Gemini optional CLI adapter 默认 no-output idle timeout 从 300 秒放宽到 1800 秒;`AICO_*_OUTPUT_IDLE_TIMEOUT_SECONDS=0` 可禁用自动 idle timeout。

### Deprecated
- (无)

### Removed
- (无)

### Fixed
- 修复 `/appoint Claude as tester ...` 因 agent / role 输入大小写与配置 key 不一致而返回 `Cannot appoint` 的问题
- 修复多次任命同一 role 或配置中出现同 project+role 多个 seat 时,`/team` 可能显示多个 tester 的问题
- 修复真实 Telegram 审批时完整 task id 难复制,容易返回 `unknown pending approval` 的问题
- 修复 Codex/read-only Adapter 经审批后才报沙箱写权限错误的问题
- 修复 Claude Code 任务经 Telegram 审批后仍要求本机二次授权的问题
- 修复 Telegram 长文本流式返回超过 4096 字符后像“被吞掉”的问题
- 修复 Telegram `editMessageText` no-op 400 导致流式输出只收到开头、Adapter 看起来 busy 的问题
- 修复 `/blockers` 和项目状态 Facts 区域缺少小节 / 命令样式的问题
- 修复 reviewer/Codex 子任务卡住时没有 IM 侧中断入口的问题
- 修复 reviewer/Codex 子任务 accepted 后无 stdout 导致 `codex: busy` 无限占用的问题
- 修复 `/appoint codeflicker as tester` 因默认 agent alias 与 provider/persona 名不一致而返回 `Cannot appoint` 的问题
- 修复同一 CLI adapter 只能同时执行 1 个任务,导致同一 agent 被任命为 reviewer / tester 后第二个 `/ask` 立即 `Task busy` 的问题
- 修复 `/ask lead ...` 不能稳定按当前项目 lead/default role 解析的问题。
- 修复 Adapter 输出先给计划、后续行再写 `@reviewer: ...` 时不能触发 reviewer 子任务的问题,并保留非指令正文展示。
- 修复 reviewer 输出 `@implementer: reflect (a)-(d) ...` 这类二次协作时 child task 只收到短指令、丢失父输出上下文的问题;协作提示也会优先显示 project assignment role。

### Security
- 默认只有任务发起人或配置的额外审批人可以批准 / 拒绝危险任务,未授权尝试会记录 `approval_denied` 审计事件
