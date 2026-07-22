# Playbook: Phase 8 Absence Loop

## 适用场景

当 Phase 8 的 inbox、morning handoff、outcome grading、Dream cycle、runbook memory 或 hybrid retrieval 变化时,用本 Playbook 防止实现跑偏。

核心验收不是“功能存在”,而是老板不在电脑前时能否形成闭环:

```text
下任务 -> 执行 -> 审批/叫停 -> 验收 -> 早上接手 -> 经验沉淀 -> 下次召回
```

Round 200 起,这个闭环还有一个前置条件:**runtime 不能依赖一个持续打开的 terminal**。macOS 本地部署先按
`docs/human/quickstart.md` 使用 `aico-service`;Round 201 后 `doctor` 必须同时看到 launchctl loaded、process
fresh 和 required components healthy。可选 Adapter 可 degraded,但真实 IM/provider 仍需下面的
Agent/human sample,不能用 synthetic health 替代。

Round 202 起,新 runtime 接管 SQLite 时会先把旧 `RUNNING` 对账为 `INTERRUPTED`,写一次恢复审计,再暴露
`/tasks`、`/inbox`、`/morning` 等 read model。`WAITING_APPROVAL` 仍可由授权 reviewer 决策,终态不变;
没有幂等与副作用契约前不自动 replay。

Round 203 起,reconciliation snapshot 与完整 audit intent 通过 SQLite transactional outbox 原子提交。sink 失败或
JSONL append 后尚未 ack 的 crash 会用同一 event id 重试;内置 JSONL 最终保持一条。验收必须同时检查状态、audit
line 和 pending outbox,不能只看 `/tasks`。

Round 223起，durable audit不再把普通JSONL追加冒充不可篡改：event形成SHA-256 previous/head chain，独立checkpoint
锚定tail，writer用file lock串行化。runtime/doctor发现修改、重排、截断或半写时必须fail closed；只允许完整链已经
fsync而checkpoint尚未更新的crash window自动收敛。legacy必须由owner核对后显式seal，且audit与checkpoint必须成组备份。

Round 224起，成组备份不再等于分别复制两个live文件：`aico-audit backup`在同一writer lock内生成单文件恢复点，
`verify-backup`脱离live路径materialize并复用production verifier。验收必须记录outer SHA并在独立副本上强制比对；
这仍不是全资产restore、加密off-device存储或自动高频backup，不能关闭B-013。

Round 225起，audit artifact必须先用`drill-backup`在disposable workspace走production materializer；live restore要求
expected SHA、真实AICO state DB owner fence、new preservation path和显式`--yes`。有效live先生成verified safety，
损坏live只进入`unverified_quarantine`。ledger/checkpoint第二次replace前崩溃必须让startup/verify fail closed，并可
用同一备份加新preservation路径重跑收敛；restore不得由scheduler或“自动选latest”触发。

Round 226起，state/audit不能只靠相似文件名组成“一次备份”：`aico-recovery capture`把同一bounded window内生成的两个
component artifact与固定coverage ledger绑定，`verify`深入运行两套production verifier，`drill`再运行两套production
materializer。manifest必须保持`global_transaction=false`和`business_restore_ready=false`，并持续暴露memory/config/
secret/grant/receiver缺项；core set只降低错配漏件风险，不是full-asset DR或combined restore授权。

Round 227起，memory JSONL也使用process writer lock、hash chain与tail checkpoint；旧JSONL必须owner显式seal。
`aico-memory backup|verify-backup|drill-backup|restore`提供与audit同级的component恢复合同，recovery-set v2按
state→audit→memory绑定三个point并把memory标为captured。它仍保持`global_transaction=false`和
`business_restore_ready=false`，不能替代config/secret/grant/receiver及off-device业务演练。

Round 228起，source-control restore也不能只写“用同一版本”：capture必须接收独立选择的full reviewed commit，证明Git root
clean并绑定HEAD tree与active Project/Persona config blob/hash。recovery-set v3不嵌入配置正文，而以
`recovery_contract_ready=true`标记revision合同；隔离恢复必须额外运行`verify-checkout`。当前HEAD不是review authority，
commit/hash也不等于平台review签名或remote可取得证明。

Round 229起，`.env`和standing grant也不能靠复制正文或普通hash进入恢复包。recovery-set v4只绑定control-plane secret
slot/channel与grant enabled mode；灾后owner可轮换secret、重新签发grant，但必须用safe decision reference生成`0600`、
new-path reinjection receipt，再按独立receipt SHA运行`verify-reinjection`。receipt会复用production service/grant preflight，
不保存值/hash/identity/grant正文；AI provider远端认证仍是独立unresolved asset，presence不等于live authentication。

Round 230起，第二故障域receiver拥有独立`aico-dead-man-recovery`合同：service lifespan与restore竞争同一DB kernel lock；
online backup允许worker继续运行，offline verify深验exact schema和monitor/outage/outbox语义，drill走production restore。
receiver restore只在receiver自身事故时由owner显式执行，有效live先留verified safety，无法验证的DB/WAL/SHM进入quarantine。
core schema v5只标记`external_component_recovery`合同就绪，保持`included=false`；AICO恢复绝不能同步回滚observer。

Round 231起，provider binary/config presence不再被当作远端认证。recovery-set v6固定required provider集合，并用
`requires_post_restore_evidence`区分“恢复方法已就绪”和“本次证据已提供”。灾后先绑定reinjection receipt，再运行受限
Claude/Codex随机challenge；必须同时看到exact response、terminal success和usage，才生成30分钟owner-only receipt。
receipt不保存challenge/prompt/output/error/credential；offline verify不重放probe。unsupported provider、过期、scope/command/
reinjection漂移全部fail closed，`business_restore_ready=false`保持。

Round 204 起,同一 canonical state DB 必须先取得 single-runtime kernel owner lock,再执行 recovery/Channel/scheduler。
竞争进程必须在任何 state mutation 前失败;crash 自动释放。`doctor` 还要证明 owner PID 与 launchd PID 一致,
不能只看到 lock 文件或 loaded label 就判健康。

Round 205 起,heartbeat 还监督当前 runtime 自己拥有的 Telegram polling / morning scheduler task。单次死亡
会原地恢复,60 秒后才算稳定;三次未稳定会熔断 15 分钟并让 doctor FAIL。验收必须证明外部 API/provider
失败不触发 task/process 重启,避免用 crash-loop 伪装无人值守。

Round 206 起,owned-task circuit open/healthy transition 可进入独立 runtime-alert SQLite outbox,通过 owner 配置的
secondary HTTPS sink 发送 open/resolved。验收必须证明重复 snapshot/进程 restart 不重复建 incident、sink 失败
按 1/5/15 分钟退避、open 不被 resolved 越序、HTTP accept-before-ack 重投同一 `Idempotency-Key`,且 generic
health不驱动自动修复。Round 239起，required component连续三份时间递增FAILED也进入同一incident/outbox；optional、
DEGRADED和瞬时失败不open，OK才resolved，与同名owned-task circuit去重。未配置secondary sink时doctor必须WARN，不能把
disabled当健康；health incident也不授权restart、provider replay或restore。

Round 207 起,整进程/整机失联改由独立 receiver 的 dead-man TTL 判断。AICO startup 立即发送带 stable runtime id、
fresh boot id 和 sequence 的 ephemeral pulse,失败只在内存重试同一 identity,不写无限 outbox 历史。receiver 从
acceptance time 计 TTL并独立生成 outage open/resolved；普通 stop 不自动 disarm,永久卸载必须由 owner 先显式
disarm。Mac sleep/网络分区超过 TTL 按 unavailable 处理。本机 heartbeat v5 只证明 publisher 最近交付状态,
不得当成远端可用性证据。

Round 240起，pulse v2把本轮secondary alert delivery压缩为`disabled/healthy/pending/failed`。receiver仍接受并排序
`pending/failed`，但不刷新续租anchor；持续到TTL后以`alert_delivery_unhealthy`开单，后续healthy/disabled新pulse再用
同reason结单。这关闭“alert sink已坏但fresh pulse持续续租”的false green；pulse不包含incident/异常/endpoint/正文，
也不因此获得restart、restore或provider replay权限。真实验收必须断开alert endpoint超过TTL并保存远端open/resolved ACK。

Round 241起，receiver downstream不再只能配置单一通知出口：owner可增加different-origin fallback，两路并发接收exact event，
默认1-of-2 ACK结算，也可显式要求2-of-2。quorum miss继续由原outbox按stable event id有界重试，receiver readiness不因外部
backoff进入restart loop。机器验收必须覆盖主路失败/备路成功、双路失败后恢复和token/origin隔离；真实验收仍需证明provider、
账号与网络故障域，而不是把两个URL字符串冒充commercial HA。
receiver schema v3还会持久化当前策略、在event创建时冻结route count/quorum，并在存在pending时拒绝策略变化。这样2-of-2
不会因重启时改成1-of-2而静默降级；需先按原策略drain。evidence/recovery同时验证当前与逐事件策略。
Round 242的schema v4进一步把aggregate quorum拆成member health：main event保存ACK vector，slot维护
unknown/healthy/degraded，partial ACK同事务生成durable degraded edge并通过任一尚存route发送；后续真实event ACK生成recovered。
edge不会驱动restart/repair，也不会反向作为route probe。它关闭event-driven false green，但不替代周期silent canary。
Round 243的schema v5补上显式opt-in canary：只有两个bridge都实现`silent-route-probe-v1`时，receiver才复用真实URL/token/POST发送
持久化probe；首次失败为suspect，连续失败达阈值才复用既有degraded/recovered edge。默认disabled，probe不能展示给老板、触发
incident或获得repair authority；真实provider日志与手机无噪声仍需dogfood。

Round 244起，`aico-service`把“可做开发安装”和“可让老板离开”分成显式准入层。默认
`AICO_ABSENCE_ADMISSION_MODE=optional`只WARN；owner选择`strict`后，runtime alerts、external liveness、scheduled recovery、
disposable drill和owner-bound standing autonomy必须沿同一readiness图全部OK，install才可执行launchctl。strict不新建shadow
checker，也不认证外部endpoint、off-device存储、platform ACK或human read；B-010至B-014仍需真实样本。

Round 245修复一次性门禁绕过：Phase1Settings现在显式消费admission mode，service/runtime共享固定合同名；strict缺enable项在
settings阶段失败，standing/recovery binding再于build第一步复用production preflight。Telegram/Feishu均在Channel/state前停止，
LaunchAgent重启不能回落optional。生产settings loader禁止把含dotenv raw input的Pydantic ValidationError写入stderr，只提示运行doctor。

Round 246把P-064的文档隔离升级为机器合同：incident alert和dead-man pulse URL必须exact-distinct，两侧都使用bearer时token也必须
distinct。service/runtime共享secret-free validator，strict aggregate包含`runtime endpoint isolation`；冲突在launchctl或
Channel/state前失败。同origin不同strict path仍允许，但不能据此声称第二故障域或provider独立。

Round 208 起,reference tracker 已收口为可独立部署的 persistent receiver:admin 显式 arm/disarm,独立 pulse
credential 只能刷新 liveness；SQLite 原子保存 monitor、active outage 与 immutable notification outbox。receiver
restart 会立即补判 expiry并续投 pending event；迟到 pulse 即使抢在 sweep 前到达,也必须先按序形成同一 outage 的
open/resolved。AICO 使用专用 liveness URL/token,不得把 strict pulse 发到 incident-alert endpoint。容器默认
non-root 并把状态放在 `/data`;只有部署在第二故障域、接好 TLS/owner notification并采集真实 outage 样本后,
才可声明外部 dead-man 已上线。

Round 209 起,receiver 的 container readiness不再等同于 SQLite ping。`/healthz` 只证明 request loop可响应；
`/readyz` 还要求 worker 用 monotonic evidence在最近三个 sweep interval内成功完成 pass,且连续内部失败少于三次。
持续失败返回无细节 503并由 supervisor restart；已持久化的 downstream pending/backoff仍算 worker正常推进,
不能把通知系统抖动升级成 receiver restart storm。

Round 210 起,真实 dead-man exercise必须导出admin-only、versioned evidence bundle并用
`aico-dead-man-evidence` 离线验收。bundle按完整 outage group截断,保存 opened/resolved identity/time和local
delivery/retry事实,不保存transport、secret、path、exception或operator note。verifier可以要求最低完整outage数和
all-delivered并输出artifact SHA-256；它只能证明receiver记录与artifact完整性,不能证明第二故障域或物理故障动作。

Round 248 起,commission/recommission必须再组合`--maximum-evidence-age-seconds`、
`--require-fresh-notification-probe`和`--require-all-routes-healthy`。verifier按验收时刻重算probe freshness，拒绝从未完成的probe、
future/超龄bundle和unknown/degraded route。默认校验继续服务历史审计；没有这三个显式条件的旧bundle不能写成当前外部健康。

Round 249 起,strict install/runtime还必须提供`aico-commission`生成的expiring receipt。owner先固定最终`.env`中的checkout-external
evidence/receipt路径，再由create绑定clean reviewed Git config、dotenv stat代际fingerprint、strict evidence exact bytes与最早TTL。
doctor/startup离线复核，heartbeat持续投影为required health；任何漂移/expiry都告警但不自动restart/replay。receipt不含dotenv
path/content/content hash，且固定`business_absence_ready=false`；它不是receiver签名或老板已读证明。

Round 211 起,AICO 主 SQLite 状态必须用 `aico-state backup` 的 online backup artifact保护，不能复制 live DB。
verify 必须只读校验 integrity/schema/SHA；restore/reset 必须先停止 runtime并取得同一 owner lock。restore要先
创建 pre-restore safety backup，再同目录原子替换。机器 Gate 只证明本机恢复原语；没有 off-device artifact与
disposable-target drill时，不能声明 disaster recovery。

Round 212 起,artifact verify之后还要用`aico-state drill`调用production restore primitive，在private temp中物化、
重新read-only校验schema/table-count parity并自动清理。optional evidence report必须`0600`且new-path。drill不得
打开CLI的live `--db`，也不能把local materialization升级成off-device/full-asset/business restore evidence。

Round 213 起,scheduled morning可选择消费一个owner-bound standing grant，但必须同时满足external owner-only file、
exact owner/target/project/charter、expiry、persistent run budget、read-only risk、no collaboration/resume和
Adapter-owned hard boundary。当前仅真正的Codex executable使用固定read-only/no-network/ephemeral command；interactive
`/morning`、`/inbox`、`/proposals`仍不执行。没有真实grant时保持禁用；`0600`不冒充密码学owner signature。

Round 214 起,`aico-service doctor`不能只lint grant file。它通过non-mutating Phase 1 preflight沿真实Adapter registry、
persona/agent directory、project/charter appointment与exact scheduled target验证binding；empty、drift、unknown、
missing、disabled或wrapper均FAIL。preflight不得初始化state/lock/log/Channel或provider，OK也不冒充真实定时E2E。

Round 215 起,预授权结果必须由accepted proposal + matching task/proposal/grant metadata + authoritative TaskSnapshot派生
receipt，并进入inbox/morning。不得新增第二份outcome表，也不得从LLM正文猜DONE。accepted无matching task显示
`evidence_missing`且禁止自动retry/refund。preauthorized runner只复用TaskBus stream/timeout，不得继承overnight handoff
grader等另一意图的终态policy。

Round 216 起,preauthorized Codex使用JSONL并在`turn.completed`后保存provider token usage。grant必须设置
`token_stop_threshold`；下一次scheduled run前按同grant已记录总量熔断，任何已消费run缺usage直接停授。该阈值是
post-run cumulative circuit breaker，不是当前run的hard token cap；单次run仍可能越界，美元成本也不能从token自行猜测。

Round 217 起,preauthorized Codex还必须通过versioned output schema返回charter-indexed结果。transport `done`与
`outcome=complete`分离；本地只验证`A*`/`S*`精确覆盖、complete/blocked一致性和repository-relative file/line存在。
missing、invalid或blocked outcome会停止后续scheduled run，raw JSON不进入老板IM。file/line存在不是语义真值，
真实owner验收必须抽查引用内容。

Round 218 起,result contract还是固定资源envelope：总长32K，criteria/stop/source/list/text/path均有上限；charter配置、
Codex Adapter、Orchestrator capture和validator各自执行同一fail-closed边界。超长、duplicate key或schema overflow只
留下bounded invalid receipt，不能进入老板IM或下一run。该边界不限制provider已经生成的token成本。

Round 219 起,complete result还保存最多16个source、单文件256KiB的path/line/size/full-file SHA-256 manifest。
下一次dispatch复核最近成功结果，inbox/morning只复核最近5份；内容变化或缺失显示`drifted/missing`并停授。
老板IM不显示path/hash/source正文。hash不是签名或业务语义真值；owner检查变更后应生成新的人工验收receipt，禁止
自动重跑或篡改旧proposal。

Round 220 起,所有风险approval都是创建时冻结deadline的bounded lease：默认24小时，owner只能配置5分钟到7天。
startup、老板视图和审批动作会先lazy sweep；过期后approval/task原子变为`expired/rejected`并写audit outbox，不能
dispatch或自动重提。重启后放大配置不能延长旧lease；老板必须核对旧`/task`并提交新的当前意图。

Round 221 起,正式Phase 1 IM入口必须同时匹配configured channel、owner sender和trusted target，且检查发生在command
解析、state/audit mutation与provider dispatch之前。陌生sender的普通消息和`/approve`都必须silent drop，owner在
非trusted群也不能触发回复；morning target和额外reviewer必须属于相应allowlist。bootstrap discovery仍deny all，
只在显式foreground模式把escaped identity写本地日志，doctor/install必须拒绝该模式。

Round 222 起,approval与standing grant共用authorization clock fence。SQLite记录已信任high-water，同进程结合
monotonic elapsed；wall clock落后应到时间超过5秒时，pending approval全部expired/rejected，新risk/preauthorized
任务拒绝，scheduled run只显示`Autonomy held: authorization clock rollback detected...`。先修复系统时间并等待追平，
再提交新任务；禁止改SQLite、放宽lease或重新加载grant来复活旧授权。

Round 233 起,scheduled morning在任何IM外发前还要落独立autonomy intent。平台ACK后崩溃时，重启必须先查同intent绑定的
accepted proposal/task：存在即结算且禁止重跑provider；不存在才按有界backoff重试。delivery ACK、dispatch receipt、human read
和result outcome必须分栏报告；notification可能重复要沿用visible intent id并显式标记，不能借此重复消费grant。

Round 238 起,`dispatch_recorded`还必须生成独立terminal outcome outbox。内容只能从proposal/task/result truth投影并在发送前冻结；
失败、wrong-target ACK和SENDING重启只能重发同一envelope，绝不能重跑provider。outbox open为DEGRADED、exhausted为FAILED；
accepted但缺task证据要主动投递`evidence_missing`。started progress提示不属于安全门禁，普通发送异常不能阻断TaskBus submit。

## AI 前置 Contract Gate

在要求人类做真实 IM / 手机 dogfood 前,Agent 必须先跑确定性 contract gate。它覆盖机器能稳定判断的部分。
如果当前 Mac 能打开 Telegram App、访问真实 provider 或读取 AICO 日志,Agent 还必须先跑本机真实样本。
human sample 只保留体感判断:老板是否看得顺、是否方便接手、是否信任这个交接。

### 当前 Phase 8 gate

```bash
env -u AICO_VIEW_TOKEN -u AICO_VIEW_ENABLED uv run pytest \
  tests/unit/test_collaboration.py \
  tests/unit/test_risk.py \
  tests/unit/test_task_bus.py::test_task_bus_keeps_collaboration_context_from_escalating_read_only_request \
  tests/unit/test_orchestrator.py::test_orchestrator_does_not_reject_read_only_reviewer_for_risky_parent_context \
  tests/unit/test_orchestrator.py::test_orchestrator_queues_overnight_delegation_to_project_lead \
  tests/unit/test_orchestrator.py::test_orchestrator_marks_short_overnight_handoff_failed \
  tests/unit/test_orchestrator.py::test_orchestrator_splits_long_stream_output_across_messages \
  tests/unit/test_offline_delegation.py \
  tests/unit/test_native_output.py \
  tests/unit/test_streaming.py \
  tests/unit/test_commands.py::test_parse_command_accepts_aico_view_alias \
  tests/unit/test_view_snapshot_commands.py \
  tests/unit/test_telegram_channel.py::test_telegram_channel_sends_document_as_multipart_upload \
  tests/unit/test_telegram_channel.py::test_telegram_channel_default_client_allows_long_poll_timeout \
  -q
```

Durable runtime 变化还必须追加运行:

```bash
uv run pytest \
  tests/unit/test_phase1_runtime_lifecycle.py \
  tests/unit/test_runtime_health.py \
  tests/unit/test_runtime_heartbeat.py \
  tests/unit/test_runtime_self_healing.py \
  tests/unit/test_runtime_alerts.py \
  tests/unit/test_service_cli.py \
  -q
uv run aico-service --repo . render | plutil -lint -
uv run aico-service --repo . doctor
```

State persistence / recovery 变化还必须追加运行:

```bash
uv run pytest tests/unit/test_state_backup.py tests/unit/test_state_cli.py -q
```

Scheduled morning delivery变化还必须追加运行：

```bash
uv run pytest \
  tests/unit/test_morning_scheduler.py \
  tests/unit/test_phase1_app.py \
  tests/unit/test_runtime_health.py \
  tests/unit/test_runtime_heartbeat.py \
  tests/unit/test_state_backup.py \
  tests/unit/test_state_cli.py -q
```

必须覆盖同日restart dedupe、exact content retry、accept-before-ack歧义、delivery与autonomy各自五次耗尽、ACK后intent恢复、
accepted evidence禁止provider重跑、无证据只重试自治和CLI privacy；
不能把platform ACK写成人类已读或exactly-once。

并用临时 DB 证明online backup、read-only verify、active-owner refusal、restore round trip、disposable drill和
failure cleanup；不得对真实生产state执行reset/restore作为自动化Gate。

Standing autonomy 变化还必须追加运行:

```bash
uv run pytest \
  tests/unit/test_standing_autonomy.py \
  tests/unit/test_codex_adapter.py \
  tests/unit/test_orchestrator.py \
  tests/unit/test_phase1_app.py \
  tests/unit/test_service_cli.py \
  -q
codex --ask-for-approval never --sandbox read-only exec \
  --ignore-user-config --ignore-rules --ephemeral --strict-config \
  -c experimental_network.enabled=false --help
```

CLI gate只能解析fixed command，不能在没有owner真实grant/credential时调用模型。还要证明manual surfaces不消费、
SQLite restart不重置`max_runs`、timeout interrupt以及broad Adapter/forged metadata在dispatch前被拒绝。

最后一条在未安装环境可以返回 fail/warn,但必须准确说明缺失项且不输出 secret value。只有 owner 显式安装后,
才要求它返回 loaded + fresh;不要在自动化回归里修改真实 LaunchAgent。

### 覆盖范围

| Contract | 机器 gate 覆盖 | Agent 本机真实样本 | 仍需 human sample |
|---|---|---|---|
| 父子 agent 委派 | `@reviewer` 解析、父输出上下文、`Current task:` 边界、只读 reviewer 不被 risky parent context 误判为 `shell_exec` | 用真实 Telegram 发短 `/ask implementer ... @reviewer:` 样本;确认日志出现 `source=implementer target=reviewer`,parent/child task 均 done | 协作交接是否像老板能理解的工作交接,而不只是技术上触发 |
| `/overnight` handoff | active project / lead 派发、短输出失败、done/blocked/risks/next actions 合同、等待审批不误判失败 | 用 1 条短目标或历史 task 验证真实 provider 回包包含 done/blocked/risks/next actions,并能在 Telegram 读到 | 真实长任务结束后老板能否直接从手机接手 |
| delegate 输出可读性 | heading / severity bullet 归一化、1400 字移动端分片、分片边界不硬切 | 截取本机 Telegram App 窗口;确认长输出被拆成多条消息且没有明显粘连 | 手机上是否仍像长墙,是否需要 summary + trace 双层输出 |
| 老板查看动线 | `/inbox`、`/morning`、`/task`、`/view` / `/aico-view` 命令和回执合同 | Agent 发送 `/project aico`、`/inbox` 或 `/view`,用日志和 Telegram 回包确认命令实际生效 | 老板是否不用猜就知道现在看哪里、早上看哪里、深挖看哪里 |
| `/view` HTML snapshot | handler 注入、自包含 HTML、Telegram `sendDocument` multipart 上传、不发 localhost 链接 | Agent 发送 `/view`,确认 Telegram `sendDocument`、附件文件名、无 localhost 链接,并尽量打开附件检查首屏 | 手机端是否能打开附件,HTML 第一屏是否符合接手习惯,内容是否只发到可信聊天 |

### Agent 本机真实样本

- 不要把本机可验证事项交给人类。Mac 上有 Telegram App 时,Agent 先打开 bot 聊天、发送样本、看日志和截图。
- 父子协作最小样本:
  `/ask implementer Please output a short handoff, then on its own line @reviewer: Review this handoff in 3 bullets max.`
- 通过标准:
  - Telegram 日志出现 incoming text 和 parent task accepted。
  - parent task 是 `target=implementer` 且真实 adapter 接收。
  - 日志出现 `Collaboration directive: ... source=implementer target=reviewer`。
  - child task 是 `target=reviewer`,真实 adapter 接收并最终 done。
  - Telegram App 可见 `Collaboration requested`、reviewer accepted 和 reviewer 输出。
- 如果样本走到 lead decision / challenger 等非预期路由,不算 implementer -> reviewer 验收通过;换一个不含 decision 触发词的样本重跑。

### Human sample 只看什么

- 只跑 1 条代表性真实 IM 样本,除非 gate 或 Agent 本机真实样本失败。
- Agent 请求人类前必须给出:已验证结果、推荐重点验证点、验证问题、预期效果、后续步骤。
- 记录 `/task <id>`、截图/原始输出、预期效果和实际偏差。
- 如果新偏差能机器化,下一轮先把它补进 gate,再让人类复验。

## Sprint 队列

### Sprint 1: Actionable Inbox

目标:`/inbox` 是老板回来后的第一处理入口,不是纯状态列表。

直接可问:

```text
/project aico
/inbox
```

验收:

- 待审批项必须显示 `/approve <id>` 和 `/reject <id>`。
- 到期审批不得继续显示`/approve`；应显示rejected/recover路径，旧短ID再次批准必须返回稳定expired文案且不dispatch。
- running 项必须显示 `/task <id>` 和 `/interrupt <id>`。
- failed / interrupted / rejected 项必须显示 `/task <id>` 和恢复建议。
- runtime restart 恢复的 orphan task 必须显示 interrupted/blocked,reason 要求核对副作用;不得继续显示 running 或自动 replay。
- `/overnight` 工单必须显示对应 `/task <id>` 和 `/morning` 接手入口。
- Goal Brief / lead decision 必须显示 follow-up 命令。
- 协作 follow-up 必须能跳到 child task。
- 输出只包含 current active project,不能串其它 project。

### Sprint 2: Morning Handoff

目标:老板早上不用主动翻 `/tasks`,系统能汇总 done、blocked、risks、next actions 和 approvals。

直接可问:

```text
/project aico
/morning
/inbox
```

验收:

- `/morning` 必须按 current active project 汇总 done、blocked、risks、overnight handoffs 和 next actions。
- blocked / risks 必须带回可执行命令,例如 `/approve <id>`、`/reject <id>`、`/task <id>`、`/interrupt <id>`。
- 输出末尾必须能回到 `/inbox` 和 `/dream`。
- 后续如果引入定时推送,必须仍可手动触发同一报告。

### Sprint 3: Outcome Grader

目标:Goal Brief 的 done 必须有 reviewer/tester/rubric 验收,不能只靠执行 agent 自报。

直接可问:

```text
/project aico
/goal implementer inspect inbox handoff 验收: list actionable items; explain blocked risks
/task <task_id>
/inbox
```

验收:

- goal task 有 acceptance。
- 执行完成后自动找 tester / reviewer 生成 `AICO Outcome Grader` 任务。
- reviewer/tester 验收结果必须给出 verdict / evidence / gaps / boss_next_action。
- outcome grader 任务进入 `/task` 和 `/inbox` 的 goal follow-up。
- 任何需要写文件或 shell 的修复仍走 `/approve`。

### Sprint 4: Dream and Runbook Memory

目标:老板不在时,agent 能整理经验、候选记忆、矛盾和过期项,但不自动污染 active memory。

直接可问:

```text
/project aico
/dream
/inbox
```

验收:

- Dream 输出是 reviewable candidates。
- raw audit/task/memory episodes 保留为 evidence。
- 第一切片至少能从 waiting approval / running / failed / interrupted / rejected 任务生成 runbook candidate。
- 批准前不进入 active prompt memory;当前实现写入 `candidate` 状态,不会被默认 `MemoryGovernor` 注入。
- 如果认可候选经验,由老板用 `/remember <accepted lesson>` 明确晋升为 active memory。

### Sprint 5: Hybrid Retrieval

目标:提升召回质量,但不改变治理边界。

验收:

- MemoryStore / MemoryRetriever / MemoryGovernor 边界不被绕过。
- scope、purpose、sensitivity、confidence 仍生效。
- `/recall` 仍能解释 reason / score,并受 MemoryGovernor 过滤。
- 没有 embedding provider 时使用本地 hybrid scorer:exact phrase > phrase overlap > semantic alias fallback。

直接可问:

```text
/project aico
/remember Morning handoff must show done, blocked, risks, and next actions.
/recall 早报接手
```

验收:

- 记忆能被中英文复述召回。
- reason / score 仍可见。

## 执行护栏

- 每轮只做一个 sprint。
- 每轮必须更新 `STATUS.md` 和 `docs/journal/ROUNDS.md`。
- 没有真实 IM 验收脚本,不得标完成。
- Dream 只能写 candidate / reviewable diff。
- Grader 不能绕过审批。
- 自动继续执行必须可 `/interrupt` 且进 `/inbox`。
- 本地 durable runtime 安装必须 owner 显式触发;plist 不得复制 `.env` secret,heartbeat 不得冒充 Channel 健康。
- P4 retrieval 只允许替换 scorer / index,不能改治理策略。

## 回归命令

```bash
uv run pytest tests/unit/test_orchestrator.py tests/unit/test_commands.py tests/unit/test_memory.py
uv run ruff check .
uv run ruff format --check .
uv run mypy src tests
git diff --check
```

## 相关

- ADR-0029
- `NORTH_STAR.md`
- `docs/playbooks/phase-8-offline-delegation.md`
- `src/aico/core/inbox.py`
