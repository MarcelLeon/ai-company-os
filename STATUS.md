# STATUS.md — 当前状态

> 这个文件高频更新。每一轮 AI 工作或人类工作结束都要更新这里。
> 阅读顺序:从上往下,前面的信息时效性最高。

**最后更新**:2026-07-23
**当前轮次**:Round 272(Native Codex host-run observation)
**当前阶段**:🟢 Phase 8 功能收口 — 离线托管 + 老板缺席操作模型
**当前路线图**:近期高优三块基础能力(Memory+Experience / Audit+Rollback / aico-view)详见
[`docs/architecture/boss-first-grounding.md`](docs/architecture/boss-first-grounding.md)。当前主线是个人开发者可直接使用的远程IM指挥、
owner-bound standing autonomy、durable result/outcome delivery与真实日常dogfood。新目标已启动：在相同模型、任务集和总预算下，
让boss-absent AICO在无人值守完成率、跨Agent协作、接手成本、预算失控率和证据完整度上优于当前Codex Goal基线。风险审批、owner ingress、
授权时钟、tamper-evident ledger、scheduled backup/custody/retention/drill和required component incident均已形成机器合同；所有local
receipt继续不冒充off-device来源、full business recovery或老板已读。当前state schema v13、receiver/evidence schema v5，
recovery-set schema v6仍固定`business_restore_ready=false`。默认与交互入口不自执行；Round 200-249累计补齐durable runtime、
recovery/alert/dead-man、component DR primitive和bounded/auditable autonomy，Team Karpathy Loop仍在Future。

公开用户默认形态现已固定为checkout内的本机Runtime：`aico init|doctor|run`完成前台验证，macOS再用
`aico service install`进入用户级LaunchAgent。Dead-Man Receiver只在用户主动要求整机失联检测时作为异机/云端高级能力，
不再是普通Quickstart或`optional`模式安装前提。

Round 241为独立receiver增加可选different-origin fallback与1-of-2/2-of-2 ACK quorum；schema v3持久化当前策略并冻结逐事件策略，pending期间拒绝配置漂移，原2-of-2事件不能在重启后被1-of-2降级结算。单通知provider或credential失效不再必然切断老板通知，但不同URL、local ACK和unit test仍不冒充真实provider/账号/网络独立或human read。

Round 242把aggregate quorum继续拆成逐route健康事实。Round 243再增加默认关闭、显式opt-in的`silent-route-probe-v1`：复用真实双route URL/token/POST，exact intent跨restart；一个失败窗口为suspect/PENDING，连续达到阈值才通过既有edge主动告警，ACK后恢复。bridge不能证明silent handling时必须保持disabled，local ACK不冒充human read或commercial HA。Round 244新增strict install admission，Round 245让它贯穿每次runtime启动；Round 246再要求incident alert与dead-man pulse使用不同exact URL及不同非空bearer，防止两个strict协议共用authority却判绿。Round 247检测运行中dotenv代际漂移；Round 248让dead-man当前验收显式拒绝超龄artifact、过期/未完成probe和非healthy route；Round 249把reviewed config、dotenv generation与strict evidence绑定成expiring commissioning receipt并持续纳入required health。Round 200-249累计合同以本段和下方最新Round为准。

---

## Round 272 完成:Native Codex host-run observation

- [x] 新增`run-start`：要求exact contract/task/admission、active Goal、相同hard token budget且zero usage，冻结owner-safe
  session inode/size/prefix SHA与provider累计用量。
- [x] initial/owner client turn必须使用exact marked envelope；native continuation必须是相邻
  `task_complete → task_started → turn_context → source="goal"`且5秒内自动开始，普通client复制Goal marker不能冒充。
- [x] 每turn从native session派生provider delta并与最终read-only Goal usage相等；exact model/effort、never approval、
  read-only/no-network和唯一签名Desktop runtime窗口全部fail closed。
- [x] `aico-codex-goal-observer`新增`admit|run-start|run-sample|run-finish`；scenario/result finalizer改为绑定完整
  `host-run-observation`，不再接受裸`host-run.json`。
- [x] Gate：boss-absent定向`145 passed`；raw root严格只有用户既有空release-room JSON导致
  `3 failed, 1186 passed, 1 skipped`，精确排除后`1186 passed, 1 skipped, 3 deselected`；SME`53 passed`。
  Ruff、root/SME mypy(267/37 files)、format(267/38 files)、production structure、tracked JSON、CLI与diff通过。
- [ ] 真实isolated capability与五task model run仍未获授权/执行；机器观察链完整不等于已有AICO胜出结论。

---

## Round 271 完成:Native Codex subagent + scenario evidence

- [x] 从真实Codex Desktop session确认原生事实链：parent `spawn_agent` function call与`sub_agent_activity`给出provider child
  thread，child `session_meta`绑定parent/path，`task_started/turn_context/task_complete`给出execution、模型、权限与最终产物。
- [x] 新增只读role observer：required child必须收到exact frozen role assignment envelope；Agent identity与provider execution
  分别从child thread/turn派生，source turn必须存在于host run，runtime必须与该host turn一致。
- [x] parent隐藏/额外subagent、child嵌套委派、复用child、错误parent、错误model/effort、非read-only或network-enabled、
  assignment/前序artifact/terminal message漂移、unsafe/duplicate JSON全部fail closed。
- [x] 新增Codex Goal scenario hash-chain ledger：从raw role sessions、fixture/drift、approval fence、irrelevant source scan、
  external acceptance/test、provider budget、真实IM decision与terminal事实派生receipt；不再要求手写scenario flags。
- [x] CLI新增`finalize-codex-goal-observations`；host turn新增runtime instance SHA，approval owner turn必须实际消费exact IM grant。
- [x] Gate：boss-absent定向`137 passed`；raw root严格只有用户既有空release-room JSON导致
  `3 failed, 1178 passed, 1 skipped`，精确排除后`1178 passed, 1 skipped, 3 deselected`；SME`53 passed`。
  Ruff、root/SME mypy(265/37 files)、format(265/38 files)、production structure、tracked JSON、CLI与diff通过。
- [ ] live capability/formal model run仍需精确预算与App重启授权；本轮机器合同通过不等于已有正式胜负结果。

---

## Round 270 完成:Codex Goal formal task-result finalizer

- [x] 新增`CodexGoalScenarioEvidenceReceipt`与`finalize_codex_goal_benchmark_result`，把ADR-0093 native host admission/run、
  frozen task和独立scenario observer闭合为唯一可评分的`system=codex_goal`结果。
- [x] 每个required role必须分别绑定真实Agent identity与provider execution SHA、runtime instance、source host turn、frozen
  fixture与前序artifact；collaboration task逐role Agent和execution都必须不同，单一Goal/main thread只换label不能获得协作分。
- [x] restart要求首个handoff前后runtime instance不同且零replay；approval、IM takeover、evidence drift、budget pressure与AICO
  finalizer使用对称门禁。initial turn必须收到canonical frozen task；任一SHA漂移、unobserved turn、usage超预算或缺budget receipt
  均fail closed；approval identity必须绑定host run中唯一owner turn。
- [x] 新增`aico-benchmark finalize-codex-goal`，只读取owner-safe receipt并fresh 0600输出task result；它不调用模型、不生成
  scenario证据，也不能把当前未授权的live样本变成正式成绩。
- [x] Gate：相关finalizer/host对称测试`34 passed`；raw root严格只有用户既有空release-room JSON导致
  `3 failed, 1164 passed, 1 skipped`，精确排除后`1164 passed, 1 skipped, 3 deselected`；SME`53 passed`。
  Ruff、root/SME mypy(261/37 files)、format(261/38 files)、production structure、JSON、CLI与diff通过。
- [ ] B-015仍只差owner授权的isolated Goal fork + App restart真实capability sample；五task两侧model run也仍需另行授权，
  当前没有AICO胜出结论。

---

## Round 269 完成:Independent Codex Goal live host observer

- [x] 新增独立`aico-codex-goal-observer start|finish`，开始阶段冻结candidate SHA、Goal预算/usage、desktop host PID/start、
  per-thread session inode/size/prefix SHA、provider usage与capability context；输出为fresh owner-only 0600 intent。
- [x] finish要求同inode session只追加、旧host退出且新PID/同签名命令在intent后启动；restart后必须出现相邻
  `task_complete → task_started → turn_context → source="goal"`，新turn完成且capability context不漂移。
- [x] Goal只通过独立app-server执行`thread/goal/get`；runner协议写入固定为0。Goal与provider usage都必须推进，预算和thread
  identity不得漂移；成功receipt才能转换为ADR-0093既有formal host admission。
- [x] 当前真实Goal/session/host完成负向验收：因当前目标`tokenBudget=null`被拒绝，未生成intent；证明日常聊天不能反向冒充
  frozen benchmark baseline。
- [x] Gate：Codex Goal/observer定向`58 passed`；raw root仅用户既有空release-room JSON导致
  `3 failed, 1154 passed, 1 skipped`，精确排除后`1154 passed, 1 skipped, 3 deselected`；SME`53 passed`。
  Ruff、root/SME mypy(259/37 files)、format、production class/function结构与diff通过。
- [ ] 代码已具备实跑入口，但尚未重启Codex App或消费isolated capability run模型预算；B-015只剩一次明确授权的破坏性较低
  live fork/restart执行，不得用synthetic fixture关闭。

---

## Round 268 完成:Signed Codex App native Goal host candidate

- [x] 发现PATH CLI与当前Codex App不是同一build：PATH仍是`0.144.5`；App `com.openai.codex`
  `26.715.72359 (5718)`内嵌`codex-cli 0.145.0-alpha.30`。
- [x] 新schema不再只有Goal控制面：`ThreadForkParams.deferGoalContinuation`明确说明可延迟initial automatic continuation，
  下一显式turn后normal automatic continuation恢复；`turn/start`仍要求client input，因此runner不能伪造native continuation。
- [x] 新增`probe-codex-app-host`：验证App/内嵌CLI均通过`codesign --verify --deep --strict`，Team ID为`2DC432GLL2`，
  notarization ticket stapled，并绑定bundle/build、两个完整CDHash、contract与schema SHA。
- [x] 真实no-model candidate receipt为0600：contract SHA
  `8d2b4caf98520d5d3842c37064f77a32b363acc3981acb98954c1f50cb84e47d`，schema SHA
  `e4b6f57e97436d617719daa1802430889dbafbb2a4dc8ff6ea65ab9946584d4b`。
- [x] candidate仍固定`formal_run_admitted=false`；B-015已从“缺第一方build/continuation出口”收窄为
  `live_native_continuation_observation_required`与`isolated_run_state_observation_required`。
- [x] Gate：本轮定向`29 passed`；raw root仍严格只有用户既有空release-room JSON导致的3项失败，精确排除后
  `1142 passed, 1 skipped, 3 deselected`；SME`53 passed`。Ruff、root/SME mypy(255/37 files)、format、
  production class/function结构与diff通过。
- [ ] 不能把当前线程确实发生的自动Goal续跑反向手写成正式receipt；下一步需要一次owner授权的隔离Goal fork，
  由独立observer捕获host自动发起的turn、跨host restart resume与usage链。

---

## Round 267 完成:真实 owner IM dogfood + launchd lifecycle recovery

- [x] 在独占Telegram polling窗口完成两条真实owner-bound决策：approval与takeover均由Bot API真实发送、Telegram Web当前
  owner点击、collector接收exact inbound callback；两者均只有1次有效action。
- [x] approval产出platform ACK、inbound ACK、hash-chain action ledger、decision receipt与0600 grant；takeover产出同等级
  decision链和terminal takeover receipt。raw token、sender/chat ID与provider thread ID均未进入score artifact。
- [x] 两条dogfood使用显式synthetic/no-model benchmark state，只验证ADR-0099的外部IM transport/decision协议；没有调用模型、
  没有执行approval mutation，也不产生formal benchmark成绩。
- [x] dogfood恢复常驻服务时复现`bootout`尚未完成就`bootstrap`的launchd竞态，以及已卸载服务只执行`kickstart`无法恢复的问题。
  `service install`现在有界等待卸载；bootstrap有约2秒有界重试；`service restart`检测未加载后会从当前plist重新bootstrap。
- [x] 真实Mac验收覆盖`install → restart → doctor`及“collector bootout后直接restart”；最终plist current、launchctl loaded、
  runtime owner PID与launchd一致；另一次紧邻`bootout → restart`无需人工等待即恢复。启动后约1秒内owner lock尚未出现，
  立即doctor可能短暂失败，复查即正常。
- [x] Gate：相关定向`101 passed`；raw root仅用户既有空release-room JSON导致`3 failed, 1136 passed, 1 skipped`，
  精确排除这3项后`1136 passed, 1 skipped, 3 deselected`；SME`53 passed`。Ruff、root/SME mypy(255/37 files)、
  format、结构与diff通过。
- [ ] 正式模型benchmark仍未运行；Round 268已找到签名native host出口，但B-015的live isolated observation仍是公平对比的
  唯一blocking边界。

---

## Round 266 完成:Codex Goal host surface machine attestation

- [x] 新增`probe-codex-goal-host`：从冻结contract读取exact CLI版本，现场生成experimental app-server schema，限制文件数、
  单文件/总大小并拒绝symlink、duplicate JSON和不完整Goal surface。
- [x] receipt绑定contract SHA、CLI版本与完整schema bundle SHA；机器确认Goal set/get/clear、persistent thread resume、
  `turn/start`仍强制client input，并单独记录remote-control transport与任何future continuation候选。
- [x] app-server surface receipt固定`formal_run_admitted=false`；即使未来发现continuation-named method，没有第一方native host
  build receipt仍拒绝入场，benchmark runner不能借机自造续跑prompt。
- [x] 本机`codex-cli 0.144.5`真实no-model attestation：schema SHA
  `356a6f6bb546f89d464df44effd103622538b340d059e61d57287f32bf6b7b94`，Goal控制面/resume/remote-control存在，
  continuation候选为空；blocking=`native_continuation_surface_absent,native_host_build_receipt_required`。
- [x] Gate：Codex Goal/benchmark定向`45 passed`；排除用户既有空release-room JSON对应3项后，full root
  `1133 passed, 1 skipped, 3 deselected`，不排除时严格只有这3项失败；SME`53 passed`。Ruff、root/SME
  mypy(255/38 files)、format、结构与diff通过。
- [x] Round 268已取得第一方signed build与native continuation surface；B-015仅剩live isolated continuation/restart/usage观察。
  当前结果仍不产生baseline成绩，也不能据此宣称AICO胜出。

---

## Round 265 完成:Owner-bound IM + formal provider execution evidence

- [x] 新增one-shot formal IM collector：外发前0600 immutable intent，正常保存Telegram platform ACK；send后/ACK前崩溃时重启
  不盲重发，可由exact owner inbound callback完成delivery reconciliation。
- [x] owner、target、thread、request token和有效期逐项绑定；匹配request的无效操作进入hash-chain action ledger并计入接手成本，
  wrong owner与无关消息忽略，terminal decision只能闭合一次。
- [x] `collect-aico-approval-im`只从环境读取bot token，approved decision才生成grant；grant、mutation executor与observer逐SHA
  复核IM decision。`collect-aico-takeover-im`把final checkpoint、delivery/inbound ACK、owner fingerprint、actions和seconds闭合。
- [x] benchmark contract新增frozen `project.json` SHA与project ID；role target必须匹配exact appointment，Task携带project/seat/role。
- [x] Codex Adapter从真实JSONL `thread.started`采集provider-issued execution ID，role receipt只存SHA；runner/finalizer同时要求
  distinct Agent与distinct provider execution，防止一个thread换多个标签冒充协作。
- [x] 新增ADR-0099、Goal Brief和P-123/P-124；定向`80 passed`；排除用户工作区既有空
  `examples/release-room/aico-project.json`对应3项后，full root`1129 passed, 1 skipped, 3 deselected`，不排除时严格只有
  这3项JSON parse失败。SME`53 passed`；Ruff、root/SME mypy(253/38 files)、format、结构、project JSON和diff通过。
- [x] Round 267已完成真实owner Telegram approval/takeover dogfood；它不调用模型、不执行mutation，也不产生benchmark成绩。
  下一步只剩Codex native host admission与两侧formal token预算。

---

## Round 264 完成:Frozen-fixture independent AICO harness

- [x] 修复benchmark公平性缺口：五个frozen task都内嵌actual bounded fixture，fixture进入canonical task-set SHA；当前SHA为
  `f0acbd3317466f8709cf408ba1403bc0dbda17f0f5367cbd21630861c9462031`。
- [x] fixture贯穿role request/prompt、provider observation与durable checkpoint；runner加载、independent observer和finalizer都复核
  exact fixture SHA，不能用相同objective配另一份实际输入。
- [x] 新增`advance-aico`：验证absolute clean checkout与contract exact Git revision，一次只推进一个真实TaskBus/Codex role；
  state/artifact/receipt在CLI调用之间持久，外部harness可真正终止进程、换runtime instance后继续。
- [x] 新增owner-only atomic hash-chain observer ledger；从actual 0600 role artifact/dispatch receipt、fixture bytes、process generation、
  external acceptance/test receipt、provider usage、takeover ACK和terminal consumption派生scenario evidence。
- [x] drift observer比较真实前后bytes；approval fence同时绑定target与父目录inode/ctime/mtime，能拒绝审批前mutation和临时修改后回滚；
  budget pressure验证large irrelevant source存在且所有role receipt只绑定frozen fixture。
- [x] approval task首role后进入durable`approval_pending`；无exact checkpoint重复advance也不会派reviewer。新增intent-first isolated
  mutation executor：未过期grant绑定request，target/content来自frozen fixture，write后crash只对账不重写，预存target无intent拒绝。
- [x] action receipt固定`execution_count=1`并与runner state、observer的request/grant/action SHA闭合；手工填任意hash不能封口。
- [x] 新增`finalize-aico-observations`，从完整ledger生成ADR-0095 receipt；benchmark JSON/JSONL/Markdown统一fresh 0600输出。
- [x] 新增ADR-0097/0098、Goal Brief与P-120/P-121/P-122；定向`61 passed`；精确排除外部0字节配置影响的3条release-room测试后root
  `1121 passed, 1 skipped, 3 deselected`；SME`53 passed`；Ruff、root/SME mypy(251/37 files)、format、结构与diff通过。
- [ ] 本轮仍是no-model机器验收，不产生benchmark成绩。Telegram真实send/inbound owner decision与takeover、formal agent/session
  binding和Codex native host adapter仍是正式run前缺口。

---

## Round 263 完成:Exact-model TaskBus benchmark transport

- [x] preauthorized task新增可选且成对的exact model/reasoning effort合同；benchmark缺Adapter机器能力时provider调用前拒绝，
  既有standing-autonomy未携带该metadata的任务保持兼容。
- [x] Codex Adapter的benchmark只读命令显式传递`--model`与`model_reasoning_effort` strict config；本机仅运行`--help`
  参数解析烟测，不调用模型、不消费token。
- [x] 新增真实`TaskBusAicoBenchmarkRuntime`：role经TaskBus/Adapter提交和收集，provider usage缺失或非DONE拒绝；
  frozen role映射不同agent id，下一role只读取前一内容寻址artifact的exact SHA。
- [x] artifact与observation receipt均owner-only；provider成功后先持久receipt再返回runner，新runtime可按stable dispatch id恢复。
  确定性preflight拒绝或授权已过期时不再写pending intent，未知provider outcome仍保持`dispatch_ambiguous`且禁止盲重放。
- [x] restart集成测试由第二个runtime instance读取同一0600 state/artifact/receipt继续reviewer，完成distinct-agent role chain、
  exact checkpoint消费和shared usage记账。
- [x] 新增ADR-0096、Goal Brief与P-119；定向`45 passed`；精确排除外部0字节配置影响的3条release-room测试后root
  `1104 passed, 1 skipped, 3 deselected`，未排除时仅这3条失败；SME `53 passed`。Ruff、root/SME mypy(247/37 files)、
  root/SME format、结构、CLI no-model参数解析与diff通过。
- [ ] 当前role target仍是runtime配置身份，尚未绑定正式project assignment/独立provider session；scenario receipt也仍缺真实
  filesystem/process/approval/Telegram/source collector。因此本轮不产生benchmark成绩，不宣称已强于Codex Goal。

---

## Round 262 完成:Independent AICO scenario evidence finalization

- [x] 新增独立harness scenario receipt与纯finalizer；绑定contract/task/role-state/observer/events SHA，执行系统不再用自身
  `role_chain_complete`直接声称task complete。
- [x] finalizer再次验证frozen role order、distinct agent、checkpoint chain、terminal消费final artifact、shared provider usage与present
  budget receipt，再生成schema-valid `BossAbsentTaskResult`。
- [x] 五类scenario机器门禁完成：restart要求不同runtime/exact一次generation/零dispatch replay；approval要求exact request+grant、
  审批前零mutation和一个人工介入；drift要求injected+detected且不发布stale；budget pressure要求暴露但不消费irrelevant source；
  IM takeover要求actions/seconds/evidence完整。
- [x] 新增`aico-benchmark finalize-aico`：bounded regular JSON输入、frozen task-set SHA/identity复核、fresh output-only；不调用模型、不改state。
- [x] 新增ADR-0095、Goal Brief与P-118；AICO evidence/runner/benchmark定向`37 passed`；exact deselect外部0字节配置影响的3条
  release-room tests后root `1096 passed, 1 skipped, 3 deselected`，SME `53 passed`；Ruff、root/SME mypy(245/37 files)、
  35个变更Python与SME format、CLI help和diff通过。
- [ ] 当前scenario receipt仍由no-model fake harness生成；下一切片需实现真实fault/filesystem/approval/Telegram collector与TaskBus/Adapter
  transport，fixture不得进入正式成绩。

---

## Round 261 完成:Restart-safe AICO managed multi-agent runner

- [x] 明确standing-autonomy single-response安全边界不能直接证明multi-agent；新增AICO benchmark runtime Protocol与admission，
  绑定exact model/effort、isolated state、managed roles、hard remaining-token cap、provider usage和durable reconciliation。
- [x] runner按frozen `required_roles`顺序派发不同Agent；每个role消费前一artifact SHA，所有role共享一个task总预算，
  `remaining_tokens`随已观察provider usage递减，禁止按角色扩预算。
- [x] provider调用前原子落owner-only `0600` stable dispatch intent；runner crash后只按dispatch id调用`recover_role`，unknown outcome保持
  `dispatch_ambiguous`且不重放provider。state拒绝symlink、identity/pending/checkpoint drift。
- [x] restart task在首checkpoint后进入`restart_pending`，后续checkpoint必须来自不同runtime instance SHA；超预算或blocked/failed
  observation保留实际usage和observation SHA，不因checkpoint未采信而隐藏budget loss。
- [x] 修复benchmark协作指标漏洞：每个required role必须恰有一个checkpoint且来自不同`agent_id`；单Agent切换role label不再得分。
- [x] 新增ADR-0094、Goal Brief与P-117；runner+benchmark定向`26 passed`；exact deselect外部0字节配置影响的3条
  release-room tests后root `1085 passed, 1 skipped, 3 deselected`，SME `53 passed`；Ruff、root/SME mypy(243/37 files)、
  33个变更Python与SME format、diff通过。
- [ ] `role_chain_complete`仍是中间态，不是可评分terminal result；下一切片需接入approval/evidence-drift/budget-pressure/IM takeover及
  terminal/source/test/acceptance receipts，再连接真实TaskBus/Codex Adapter runtime。

---

## Round 260 完成:Native Codex Goal host continuation contract

- [x] generated 0.144.5 app-server schema审计确认：Goal API只提供objective/status/budget/usage；协议没有automatic continuation方法，
  `turn/start`仍要求调用方提交input。app-server因此只算control plane/observation surface，不能独立代表Codex Goal宿主。
- [x] 新增ADR-0093与native host admission：formal baseline必须冻结第一方host build，并证明native continuation、persistent resume、
  isolated state、provider usage observation与default capability边界；standalone app-server或runner constructed input直接拒绝。
- [x] 新增无raw prompt turn/run ledger：只保存opaque input/turn SHA、来源、Goal状态、双usage与介入次数；initial task、native host
  continuation、owner takeover、harness injection严格分源，只有owner takeover计human intervention。
- [x] sequence、previous SHA、跨turn token continuity、Goal delta/provider total、frozen budget和terminal stop全部fail closed；
  host admission/ledger只证明baseline身份和证据完整性，不产生任务完成或胜出结论。
- [x] 新增Goal Brief与P-116；Codex Goal/benchmark定向`37 passed`；exact deselect外部0字节配置影响的3条release-room tests后
  root `1074 passed, 1 skipped, 3 deselected`，SME `53 passed`；Ruff、root/SME mypy(241/37 files)、变更文件format与diff通过。
  全仓format只报告未触碰的既有`projects/data-agent-v1/src/data_agent_v1/engine.py`。
- [ ] formal runner仍缺可编程的第一方Codex host adapter/build receipt；在此之前不允许用standalone app-server自造continue loop替代。
- [ ] 尚未启动任何正式模型benchmark；当前仍没有AICO vs Codex Goal真实成绩，禁止“强于Codex Goal”声明。

---

## Round 259 完成:Persistent Codex Goal baseline admission

- [x] 本机`codex-cli 0.144.5`能力审计确认：`codex exec`没有Goal接口；真实baseline必须走app-server
  `thread/start`、`thread/goal/set|get|clear`与后续`turn/start`，否则测到的是错误对象。
- [x] schema与live no-model探测确认Goal拒绝ephemeral thread。新增`aico-benchmark probe-codex-goal`，从frozen contract绑定exact
  CLI/model/token budget，创建persistent read-only/no-network thread，要求active/0 tokens/0 seconds，再clear Goal和delete thread。
- [x] 直接共享桌面`CODEX_HOME`出现过SQLite state runtime初始化失败；probe改用run-isolated owner-only Codex home，成功receipt不含
  thread ID/path/prompt/identity，正常结束删除全部isolated state。
- [x] thread创建后立即落`0600` cleanup intent；断线保留intent+isolated home，下次启动先重连删除旧thread。新增ADR-0092、
  Goal Brief与P-115；external create/local intent不可原子提交的微小crash window保持公开。
- [x] installed CLI live验收：persistent=true、model=`gpt-5.6-sol`、budget=50,000、tokens/time=0、goal cleared、thread deleted、
  isolated home/cleanup intent均已删除；未调用`turn/start`、未消费模型token。
- [x] 新增app-server turn transport接口与offline supervisor：固定exact model/effort/never approval，等待matching `turn/completed`和
  `thread/tokenUsage/updated`，再以Goal tokens delta交叉验证provider total；缺失、非complete或不一致fail closed。
- [x] supervisor继续覆盖`turn/interrupt`的durable interrupted确认，以及新app-server `thread/resume`后model/sandbox/approval与
  Goal tokens保留；当前仍不自动猜测Codex host的continuation prompt。
- [x] isolated owner-only home挂载现有`auth.json`符号链接的local status probe返回`Logged in using ChatGPT`；未复制secret、未发模型请求，
  Codex临时helper与home均已删除。正式turn仍需owner预算授权。
- [x] benchmark/Goal admission+turn定向`25 passed`；exact deselect外部0字节配置影响的3条release-room tests后root
  `1062 passed, 1 skipped, 3 deselected`；SME`53 passed`；Ruff、root/SME mypy(239/37 files)、format、结构、JSON和diff通过。
- [ ] 正式Codex Goal runner仍缺owner-authorized isolated credential injection、turn supervision、continuation与scenario receipt采集；
  admission receipt不产生任何胜负结论。

---

## Round 258 完成:Evidence-first boss-absent benchmark runner

- [x] 冻结`benchmarks/boss-absent-v1/tasks.json`五类scenario，canonical SHA为
  `cb4898fed0a958a5778dd8744bbe910c2e179a3918a03153ed07cabd14ef9f34`；两侧共享model、reasoning、revision、window和
  单一总token budget，AICO多Agent usage必须聚合到task。
- [x] 新增contract/result/summary/verdict机器合同与deterministic scorer；漏task保留在completion/evidence分母，漏usage/超预算计
  budget loss，漏takeover按cap+1惩罚，unknown/duplicate/drifted result和伪造checkpoint/evidence hash fail closed。
- [x] `aico-benchmark freeze|score`完成有界non-symlink输入、duplicate-key/non-finite JSON拒绝、新目录only输出和0/1/2退出语义；
  installed CLI实跑完成help、freeze和拒绝二次覆盖。新增Accepted ADR-0091、Goal Brief与harness/result记录说明。
- [x] 新增equal-observation `dry-run`：两侧各5条result、100条synthetic scenario events经同一scorer得到`aico_wins=false`/0项更优；
  另为两侧启动helper、落durable checkpoint、真实SIGTERM并由新进程校验exact SHA，receipt绑定result；不冒充被测系统恢复或正式成绩。
- [x] 胜出同时要求五项至少四项严格更优、无人值守和预算严格更优，并要求AICO全task dispatch/complete、全协作、零预算失控、
  complete样本全证据和restart/IM/approval独立证据；relative score不能绕过商业可用绝对线。
- [x] benchmark定向`14 passed`；排除外部0字节release-room配置直接导致的exact 3 tests后root`1051 passed, 1 skipped,
  3 deselected`；SME`53 passed`；Ruff、root/SME mypy(235/37 source files)、root/SME format、变更JSON与diff通过。
- [ ] 当前只完成synthetic scorer/CLI/event harness与fake process restart probe，不产生正式胜负结论；下一切片仍需isolated
  system executor采集真实usage/checkpoint/drift/approval/budget receipts，
  正式两侧模型benchmark必须owner另行授权。
- [ ] `examples/release-room/aico-project.json`仍是外部0字节改动；最近一次未deselect full root准确结果为`3 failed, 1048 passed,
  1 skipped`（随后新增3条benchmark tests已单独/排除外因后通过），本轮未恢复、未stage，也不把这3条失败归因于benchmark代码。

---

## Round 257 完成:Tool-free budgeted standing evidence pack + benchmark contract

- [x] grant schema升级v2并强制`max_total_tokens`；Phase 1 preflight同时验证read-only与budget Adapter能力。Codex预授权命令把owner
  limit写入rollout budget/context window，并显式禁用shell、unified exec、multi-agent、apps、browser、computer、image与web工具。
- [x] standing charter新增bounded `evidence_sources`；系统生成最多8源、1 MiB/源、384行/片段、64 KiB总量的fingerprinted pack，
  prompt只含allowlisted原始path/line。absolute/traversal/symlink/non-UTF8/marker ambiguity/oversize/drift全部fail closed。
- [x] result只能引用pack列出的行；provider terminal usage超过`max_total_tokens`时usage仍durable保存但result不采信，outcome/morning/
  inbox明确显示`budget=within_limit|exceeded`。`token_stop_threshold`继续只表示下一run前累计熔断。
- [x] 当前AICO/SME真实配置pack分别约29.0K/40.8K字符；326 KiB的AICO `STATUS.md`只暴露116行目标片段，不再整文件进模型。
- [x] 新增Accepted ADR-0090、Goal Brief和`boss-absent-vs-codex-goal` benchmark v1；冻结五项指标、公平合同和胜出条件，
  当前不宣称已优于Codex Goal。
- [x] 定向339 tests、full root`1040 passed, 1 skipped`、SME`53 passed`、Ruff、root/SME mypy(230/37 source files)、
  format、133生产文件/2725 definitions、JSON、Compose与diff通过；本轮未创建grant、调用付费provider、发送Telegram、
  修改`.env`/LaunchAgent。
- [ ] gate后出现非本轮并发改动：`examples/release-room/aico-project.json`被清为0字节，最终full rerun因此有3条JSON parse失败；
  排除该文件对应3个test files后`1035 passed, 1 skipped`。本轮不擅自恢复、不纳入交付，后续stage/commit必须显式排除。
- [ ] B-014只剩一次owner-authorized v2真实定时复验：必须同时得到`budget=within_limit`、`outcome=complete`、
  `evidence=current`和delivery/criteria/source全覆盖；Codex response后记账及美元quota残余边界保持诚实。

---

## Round 256 完成:Standing autonomy real acceptance — control plane pass, business outcome fail

- [x] owner选择一次性真实验收；创建checkout-external、owner-only `0600` grant，精确绑定当前Telegram owner/私聊、`aico`、
  `absence-evidence-audit`、Codex read-only、两小时expiry、`max_runs=1`、300秒timeout与50,000累计token停止阈值。
- [x] 真实scheduled morning、Telegram平台ACK、preauthorized proposal/task、Codex进程、usage、terminal outcome与durable intent/outbox
  全链执行；Web Telegram逐条显示started、失败、terminal outcome和第二次`run budget exhausted`。第二次触发前注入同charter隔离候选，
  task总数仍为1，证明没有第二次Provider调用。
- [x] dogfood先后发现并修复两个production兼容缺陷：Codex 0.144.5已移除`experimental_network`旧strict config键；Codex JSONL
  单行可超过asyncio默认64 KiB。预授权/probe继续强制`--sandbox read-only --ask-for-approval never --ignore-user-config
  --ignore-rules --ephemeral --strict-config`，子进程流改用显式1 MiB单行上限。
- [ ] 商业结果严格不通过：修复后Codex任务return code 0、status=done，但实际usage为227,252 tokens，超过50,000阈值4.5倍；
  模型引用了超过256 KiB的`STATUS.md`，result receipt为`invalid/source_too_large`、criteria `0/3`、sources `0`。当前threshold只在
  下一run前检查，不是单次硬token/cost cap；bounded output也不等于bounded input/context。
- [x] 验收后已删除`.env`中的morning/grant/临时state配置并恢复原`.aico/state.db`；LaunchAgent重启后doctor确认standing autonomy
  disabled、runtime owner PID与launchd一致。三份checkout-external验收artifact保留为owner-only短期证据，不参与运行时。
- [x] Gate：standing/phase/Adapter定向`116 passed`；full root`1030 passed, 1 skipped`；Ruff lint、mypy(132 source files)和本轮文件
  format通过。全仓format仍只报告未触碰的既有`projects/data-agent-v1/src/data_agent_v1/engine.py`。

---

## Round 255 完成:Personal-developer scope reset

- [x] owner明确暂停“整机失联告警”和“商用灾难恢复”后续投入：第二故障域/TLS/独立通知出口、off-device加密存储与RPO/RTO
  对个人开发者采用门槛过高；允许故障后手工启动/重新配置。
- [x] B-012/B-013改为`owner-paused`，不再属于近期优先级、默认Quickstart、发布阻塞或长期goal完成条件；已有receiver、签名、
  backup/verify/restore/drill能力保留，不删除、不扩展，未来只有明确用户需求时才重开。
- [x] Boss-absent standing autonomy仍保留为待owner决策的核心候选：它复用现有Mac、Telegram和Codex，不要求新服务器；当前保持
  disabled，不创建grant、不触发定时provider调用。本轮仅解释授权边界，不替owner启用。
- [x] 本轮只调整产品范围与连续性文档；没有修改production code、`.env`、LaunchAgent、外部系统或Git状态。

---

## Round 254 完成:Signed receiver evidence + external dogfood

- [x] owner确认ADR-0088；新增Ed25519 signed evidence envelope。receiver只持owner-only PKCS#8私钥，AICO只信
  checkout-external owner-pinned SPKI公钥；domain-separated签名绑定exact payload，envelope不携带trust anchor。
- [x] receiver新增可选admin-only`/signed-evidence`；unsigned endpoint继续服务历史审计。离线verifier新增
  `--trusted-public-key`；strict commissioning升级schema v2并绑定exact envelope、payload与key identity，unsigned、wrong key、
  tamper和silent rotation全部fail closed。
- [x] private signing volume、key generation/export/rotation与recommission runbook已补齐；ADR-0088转Accepted，新增P-109并更新B-012。
- [x] Dogfood重启真实LaunchAgent，`/status`页面与raw ref `1434`闭环；Codex Provider任务`ceed4a4c…`返回exact
  `AICO_ROUND254_PROVIDER_OK`。随后发现`Do not … modify files`被误判write_files，新增bounded negation handling与P-110；exact原句
  复验task `ee2aac16…`/raw ref `1440`返回`AICO_ROUND254_NEGATION_OK`。
- [x] Gate：targeted signing/commissioning/service`155 passed`，risk/orchestrator`147 passed`；full root`1030 passed, 1 skipped`、
  SME`53 passed`；Ruff、root/SME mypy(228/37 files)、format、132生产文件/2696 definitions、9 JSON、Compose、139-member
  offline wheel与diff通过。
- [ ] 当前真实`.env`仍是基础optional档：runtime alerts、external liveness、recovery、commissioning、standing autonomy未配置。
  本轮没有第二故障域receiver/TLS/fault action/provider notification/owner手机已读样本；B-012至B-014与长期goal保持未完成。

---

## Round 253 完成:Project phase source alignment

- [x] 复核Codex现状：PATH中实际CLI为`0.144.5`，B-008已记录同一`gpt-5.6-sol`最小调用和真实`/ask reviewer`成功；
  `/status`展示的是历史失败任务正文，不是当前provider故障。本轮纠正Round 252表述，不做无依据的Adapter改动。
- [x] 确认项目阶段确有配置漂移：公开`aico init`固定加载的`config/projects.example.json`仍为Phase 5，无外部配置fallback仍为Phase 6。
- [x] 两个事实源统一为`Phase 8 - 离线托管 + 老板缺席操作模型`，并新增example config与fallback回归断言。
- [x] Gate：Phase1/project assignment定向`83 passed`；Ruff、format、JSON、mypy和diff检查通过。
- [x] 重启真实用户级LaunchAgent后doctor保持required合同OK；Web Telegram再次发送`/project aico`，页面显示Phase 8，runtime raw ref
  `1432`完成incoming、command、sendMessage和handler finished。

---

## Round 252 完成:Real Telegram E2E closeout

- [x] owner授权后，仅在已登录的`ai_co` Bot私聊发送只读`/status`、`/project aico`、`/inbox`；三条均在Web Telegram收到新鲜回包。
- [x] runtime日志逐条闭环`Telegram incoming text`、`Command received`、`Telegram sendMessage`、`handler finished`，raw refs分别为
  `1426`、`1428`、`1430`；LaunchAgent验收后仍由launchd持有且owner PID一致。
- [x] 更正Round 251误判：LaunchAgent正在消费long polling时，旁路`getUpdates=0`不能证明消息未送达；页面中无关账号状态文本也不能
  替代当前Bot私聊的可见回包与runtime日志。
- [x] B-010关闭；基础本机Runtime已具备owner配置、真实LaunchAgent安装和新鲜IM常驻证据。Dead-Man、secondary alert、strict absence及
  owner手机已读仍是独立高级验收，不影响基础Quickstart。
- [x] Round 253复核确认`/status`中的Codex错误只是历史任务正文，当前CLI/model已有成功证据；`/project aico`的Phase 5配置漂移已修复并
  通过真实Telegram Phase 8回包复验。

---

## Round 251 完成:Unified local onboarding + real LaunchAgent dogfood

- [x] 新增单一公开CLI `aico demo|init|run|doctor|service`，复用既有runtime/service事实源；`init`原子创建`0600`最小配置。
- [x] `init`新增一次性exact private-chat pairing，只接受匹配随机码的private update；已知owner/chat可显式提供，失败不泄露token或Bot API细节。
- [x] 修复配置隔离：显式settings与service preflight不再隐式吸入checkout ambient`.env`，production loader仍显式读取并绑定文件代际。
- [x] README/Quickstart/Daily Ops/部署文档将本机Runtime固定为默认形态；Dead-Man明确为异机整机失联检测的可选高级组件。
- [x] 新增Accepted ADR-0089与P-106；拒绝把本机核心Docker化或让shell脚本形成第二套策略源。
- [x] 真实生成owner-only`.env`，doctor基础合同通过；安装并重启用户级LaunchAgent，稳定态pid与owner lock一致，heartbeat v5中
  Telegram polling、Claude、Codex component health均为OK。
- [x] Gate：targeted phase/service/CLI/Telegram`148 passed`；full root`1020 passed, 1 skipped`；Ruff、mypy(226 files)、
  226-file format与diff通过。
- [x] Round 252已完成指定`ai_co` Bot私聊的新鲜入站/回包验收，并以页面回复与runtime同一轮日志双证据纠正本轮误判；B-010已关闭。
- [ ] ADR-0088仍是独立密码学提案；本轮没有因为Dead-Man降为可选就静默实现、接受或删除它。

---

## Round 250 proposal:Signed dead-man evidence envelope(Round 254已确认并实现)

- [x] 审计确认Round 249 exact-byte SHA只能检测已固定artifact漂移，不能证明bundle由独立receiver签发；同用户进程仍可伪造新bundle并重新commission。
- [x] 新增Goal Brief与Proposed ADR-0088：receiver用owner预生成Ed25519私钥签exact bundle bytes，AICO只持owner-pinned公钥；拒绝HMAC、自制密码学、envelope自带trust anchor和TLS证书替代artifact签名。
- [x] 固定兼容/边界：unsigned endpoint仅保留历史审计；strict只接受signed envelope；signature成功仍不证明receiver host/TLS/fault action/provider ACK/human read，`business_absence_ready=false`。
- [x] Round 254 owner确认后已完成代码、测试、dependency lock与运维文档更新；ADR-0088状态为Accepted。

---

## Round 249 完成:Expiring runtime commissioning receipt

- [x] 新增`aico-commission create|verify`；owner-only、checkout-external receipt绑定safe runtime id、clean reviewed Git config、
  dotenv metadata generation fingerprint和strict dead-man exact bytes。
- [x] expiry取bundle maximum age与completed silent-probe TTL较早值；evidence/receipt/config/dotenv/runtime identity任一漂移均fail closed。
- [x] strict admission新增`runtime commissioning`：doctor/install及Telegram/Feishu startup在launchctl/Channel/state前复核。
- [x] 运行中新增required `configuration:commissioning-receipt`；expiry/漂移进入既有confirmed alert，不联网、不自动reload/restart/replay。
- [x] receipt不记录dotenv path/metadata/content/content hash，固定`business_absence_ready=false`；新增ADR-0087、Goal Brief与P-105并更新
  env、receiver/运维/架构文档、CHANGELOG、B-010/B-012、STATUS/ROUNDS。
- [x] Gate：targeted`130 passed`，full root`1009 passed, 1 skipped`、SME`53 passed`；Ruff、root/SME mypy(224/37 files)、
  224/37-file format、130个生产文件/2652 definitions、repo JSON、Compose、137-member offline wheel与diff通过。
- [ ] local receipt/hash不是detached owner signature，也没有真实receiver host/TLS/provider ACK/fault action/owner手机样本；
  当前checkout没有真实`.env`或LaunchAgent，B-010/B-012与goal保持active。

---

## Round 248 完成:Bounded current dead-man evidence acceptance

- [x] `aico-dead-man-evidence`新增正有限`maximum evidence age`；超龄与future-generated bundle fail closed。
- [x] strict probe条件按验收时刻重新计算，要求enabled、settled且至少有一次完成checkpoint；生成时fresh但验收时过期同样失败。
- [x] strict route条件要求所有当前slot为healthy，unknown/degraded均失败；三项可组合且不修改evidence/summary schema、不联网。
- [x] 新增ADR-0086、Goal Brief、P-104并更新receiver部署、Quickstart、Daily Ops、Troubleshooting、absence playbook、architecture、
  CHANGELOG、B-012与STATUS。
- [x] Gate：targeted`8 passed`，full root`1001 passed, 1 skipped`、SME`53 passed`；Ruff、root/SME mypy(221/37 files)、
  221/37-file format、128个生产文件/2625 definitions、repo JSON、Compose、135-member offline wheel与diff通过。
- [ ] strict offline acceptance仍信任输入artifact；没有receiver签名、真实host/TLS/provider/platform ACK、owner手机或fault-action证据，
  也尚未生成配置代际绑定的commission receipt。B-012与goal保持active。

---

## Round 247 完成:Runtime dotenv generation drift health

- [x] production settings loader冻结`.env`文件元数据代际，不读取、哈希或持久化内容/path/metadata。
- [x] strict heartbeat新增required `configuration:dotenv-generation`；编辑、替换或删除文件会FAILED并进入既有confirmed alert。
- [x] 漂移不自动reload/restart/provider replay；旧进程维持已加载known-good配置，等待owner完成新配置验收后显式切换。
- [x] 新增ADR-0085、Goal Brief、P-103并更新env/运维文档、CHANGELOG与STATUS。
- [x] Gate：targeted`74 passed`，full root`999 passed, 1 skipped`、SME`53 passed`；Ruff、mypy(221 files)、format、
  128个生产文件/2623 definitions、Compose、135-member offline wheel与diff通过。全仓format仍仅既有
  `projects/data-agent-v1/src/data_agent_v1/engine.py`。
- [ ] metadata代际不抵抗恶意mtime/inode伪造，也不证明新配置external recommission；真实部署证据仍缺，goal保持active。

---

## Round 246 完成:Runtime webhook authority isolation

- [x] incident alert与dead-man pulse URL同时配置时必须exact-distinct；双方bearer均非空时也必须distinct。same origin/different
  strict path仍允许，不把字符串差异冒充第二故障域。
- [x] shared pure validator不返回原值；`aico-service`新增`runtime endpoint isolation`并纳入strict aggregate，冲突在launchctl前FAIL。
- [x] Phase1Settings复用同一cross-field policy，每次Telegram/Feishu启动均在Channel/state前FAIL；existing production loader继续
  屏蔽可能包含dotenv input的raw validation error。
- [x] 新增ADR-0084、Goal Brief、P-102，更新`.env.example`、Quickstart、Daily Ops、Troubleshooting、absence playbook、
  architecture、CHANGELOG及B-011/B-012。
- [x] Gate：Phase/service targeted`113 passed`，full root`997 passed, 1 skipped`、SME isolated`53 passed`；Ruff、root mypy
  (220 source files)、SME strict mypy(37 source files)、220个AICO/tests format、127个生产文件/2619 definitions结构、repo JSON、
  dead-man Compose、134-member offline wheel与diff通过。全仓format仍只报告未触碰的既有
  `projects/data-agent-v1/src/data_agent_v1/engine.py`。
- [ ] 当前仍无真实alert/liveness endpoint、receiver、LaunchAgent、provider/storage或owner手机样本；本轮未联网探测或外发。
  endpoint/credential机器隔离不关闭B-011/B-012，goal保持active。

---

## Round 245 完成:Runtime-enforced strict absence admission

- [x] 抽出service/runtime共享的fixed contract names和gap aggregation；Phase1Settings显式声明
  `absence_admission_mode: optional|strict`，dotenv strict不再被`extra=ignore`静默丢弃。
- [x] strict enable项漂移在settings构造时FAIL；`build_phase1_runtime`第一步复用standing routing与recovery destination的真实
  preflight，失败前不构造Channel/state/audit、不调用provider。
- [x] Telegram与Feishu生产入口统一使用secret-safe settings loader；Pydantic raw ValidationError可能携带dotenv input，因此只输出
  通用doctor指引，不把token/URL/target写进LaunchAgent stderr。
- [x] 新增ADR-0083、Goal Brief、P-101，更新`.env.example`、Quickstart、Daily Ops、Troubleshooting、absence playbook、
  architecture、CHANGELOG与B-010。
- [x] Gate：Phase/service/Feishu targeted`113 passed`，full root`993 passed, 1 skipped`、SME isolated`53 passed`；Ruff、
  root mypy(220 source files)、SME strict mypy(37 source files)、220个AICO/tests format、127个生产文件/2615 definitions结构、
  repo JSON、dead-man Compose、134-member offline wheel与diff通过。全仓format仍只报告未触碰的既有
  `projects/data-agent-v1/src/data_agent_v1/engine.py`。
- [ ] 当前仍无真实`.env`、LaunchAgent、外部receiver/provider/storage或owner IM样本；本轮未安装服务、外发、调用provider或执行
  真实backup/restore。持续strict门禁不关闭B-010至B-014，goal保持active。

---

## Round 244 完成:Strict absence install admission

- [x] 新增`AICO_ABSENCE_ADMISSION_MODE=optional|strict`；默认optional保持开发安装兼容，同时明确WARN“关键absence合同不是
  install gate”。非法值fail closed且不回显原值。
- [x] strict直接聚合同一轮真实readiness结果，要求runtime alerts、external liveness、scheduled recovery和owner-bound
  standing autonomy均OK，并额外要求disposable recovery drill启用；任一缺失都在launchctl前拒绝install。
- [x] 没有新建production shadow checker，也没有把破坏性的retention授权塞进准入。输出只列固定合同名；OK固定声明external
  evidence未认证，不声称commercial ready、off-device、platform delivery或human read。
- [x] 新增ADR-0082、Goal Brief、P-100，更新`.env.example`、Quickstart、Daily Ops、Troubleshooting、absence playbook、
  architecture、CHANGELOG与B-010。
- [x] Gate：service targeted`46 passed`，full root`990 passed, 1 skipped`、SME isolated`53 passed`；Ruff、root mypy
  (219 source files)、SME strict mypy(37 source files)、219个AICO/tests format、126个生产文件/2611 definitions结构、
  repo JSON、dead-man Compose、133-member offline wheel与diff通过。全仓format仍只报告未触碰的既有
  `projects/data-agent-v1/src/data_agent_v1/engine.py`。
- [ ] 当前checkout仍无真实`.env`、LaunchAgent、外部receiver/provider/storage或owner IM样本；本轮未安装服务、发送外部请求、
  调用provider或执行真实备份/restore。strict机器门禁不关闭B-010至B-014，goal保持active。

---

## Round 243 完成:Durable silent notification route probes

- [x] 新增strict `notification_route_probe`与默认disabled字面合同`silent-route-probe-v1`；仅双route可启用，复用真实URL、credential、
  POST与`Idempotency-Key`，不使用HEAD、旁路URL/token或普通outage消息。
- [x] schema v5持久化probe cadence/failure threshold/max age、pending exact payload、next window、last ACK mask；send-before-record崩溃后
  重放同一identity，不追赶历史窗口。pending probe/main/edge期间配置变化fail closed。
- [x] 首次probe失败保留suspect并使delivery PENDING，连续达阈值才degraded；成功清零并按需发送recovered。probe edge带
  `silent_probe`来源与bounded ACK vector，meta-alert仍不递归更新route健康，全断不触发restart/repair。
- [x] admin/evidence/recovery升级v5，包含secret-free probe与per-route checkpoint；v4保守迁移默认disabled并重建canonical table，
  verifier拒绝probe payload、ACK/source/route/edge漂移。新增ADR-0081、Goal Brief、P-099并更新B-012及运维/部署文档。
- [x] Gate：targeted`56 passed`，full root`986 passed, 1 skipped`、SME isolated`53 passed`；Ruff、root mypy
  (219 source files)、SME strict mypy(37 source files)、219个AICO/tests format、126个生产文件/2610 definitions结构、
  19份JSON、dead-man Compose、133-member offline wheel与diff通过。全仓format仍只报告未触碰的既有
  `projects/data-agent-v1/src/data_agent_v1/engine.py`。
- [ ] 当前仍无真实`.env`、第二故障域receiver、双provider bridge对silent v1的兼容证明、平台请求日志或owner手机无probe噪声样本；
  默认仍disabled，不能把fake ACK写成continuous commercial route health。B-012与goal保持active。

---

## Round 242 完成:Durable notification route health edges

- [x] webhook/quorum sink返回bounded per-route ACK；main event结算、最后ACK bitmask/time、slot unknown/healthy/degraded和新健康
  边沿在同一事务提交，不保存URL、token、provider、response或异常正文。
- [x] partial quorum生成stable`notification_route_degraded`并经任一尚存route主动发送；后续真实outage event ACK生成
  `notification_route_recovered`。edge使用独立durable outbox与1/5/15分钟退避，main 2-of-2不会压住降级通知。
- [x] main quorum miss时同一sweep不重复发送edge；edge后续独立推进。meta-alert不反向更新route状态，单route全断不制造
  无法送达的自我告警，`/readyz`也不因downstream degraded进入restart loop。
- [x] receiver/evidence/recovery schema升级v4：新增route状态与health outbox，main event增加ACK mask/attempt time；v3历史ACK
  保持unknown。offline verifier拒绝route checkpoint、edge trigger、ACK/quorum和pending policy drift。
- [x] admin-only`GET /v1/notification-routes`提供secret-free策略、slot状态和pending edge数量；evidence CLI同步统计route health，
  `--require-all-delivered`同时覆盖outage和health edge。
- [x] 新增ADR-0080、Goal Brief、P-098并更新ADR-0079、B-012、deploy/operator/troubleshooting/absence/architecture与CHANGELOG。
- [x] Gate：targeted`52 passed`，full root`982 passed, 1 skipped`、SME isolated`53 passed`；Ruff、root mypy
  (219 source files)、SME strict mypy(37 source files)、219个AICO/tests format、126个生产文件/2585 definitions结构、
  9份JSON、dead-man Compose、133-member offline wheel与diff通过。全仓format仍只报告未触碰的既有
  `projects/data-agent-v1/src/data_agent_v1/engine.py`。
- [ ] 当前仍无真实`.env`、第二故障域receiver、双provider/账号/网络和owner终端样本；route health只由真实outbound event观察，
  没有silent canary时不能声称无事故期间continuous healthy。B-012与goal保持active。

---

## Round 241 完成:Quorum dead-man notification routes

- [x] 新增`QuorumDeadManNotificationSink`：配置fallback后，两条route并发发送相同immutable event和
  `Idempotency-Key`；默认1-of-2 ACK结算，owner可显式要求2-of-2。
- [x] quorum miss继续复用既有SQLite outbox、open-before-resolved队首顺序与1/5/15分钟backoff；恢复后重投exact event，
  不restart receiver、不重放provider任务。单route配置继续使用原窄sink。
- [x] receiver schema v3以singleton保存当前route/quorum，并在event创建事务内冻结策略；存在pending event时，启动配置改变
  必须fail closed。v1/v2历史保守迁移为1-of-1，已delivered历史可保留旧策略。
- [x] evidence/recovery schema v3验证当前与逐事件策略，拒绝pending policy drift；`delivered`仅证明该event冻结的local ACK
  quorum，不证明all-route成功或老板已读。
- [x] settings要求fallback为不同HTTPS origin、quorum不超过route count、primary/fallback token不同且均不复用pulse/admin
  authority。异常保持通用，不保存URL、token、response body或异常正文。
- [x] 新增ADR-0079、Goal Brief、P-097并更新B-012、operator/troubleshooting/absence/architecture、receiver deploy env/README
  与CHANGELOG；ADR-0079取代ADR-0078的receiver/evidence/recovery schema部分。
- [x] Gate：receiver/evidence/recovery定向`46 passed`，full root`976 passed, 1 skipped`、SME isolated`53 passed`；
  Ruff、root mypy(219 source files)、SME strict mypy(37 source files)、219个AICO/tests format、126个生产文件/
  2546 definitions结构、9份JSON、dead-man Compose、133-member offline wheel与diff通过。全仓format仍只报告未触碰的
  既有`projects/data-agent-v1/src/data_agent_v1/engine.py`。
- [ ] external-state仍无真实`.env`、第二故障域receiver、两个真实notification provider或owner收件样本；机器failover合同不关闭
  B-012，goal保持active。

---

## Round 240 完成:Alert-delivery-aware dead-man renewal

- [x] liveness pulse schema v2增加secret-free `alert_delivery_status`；heartbeat把同轮secondary alert delivery传给publisher。
  disabled/healthy pulse排序并续租，pending/failed只排序、不更新最后成功续租anchor；pending retry冻结exact payload。
- [x] persistent receiver跨restart按TTL形成`alert_delivery_unhealthy`或`pulse_expired` outage；healthy/disabled新pulse原子生成
  same-reason resolved并恢复续租。receipt/status暴露renewed、last pulse和reason，不携带endpoint/异常/正文。
- [x] receiver/evidence schema升级v2；v1 DB保守迁移last pulse、disabled状态与历史pulse-expired reason。offline recovery verifier
  同步exact DDL/domain invariant，拒绝非法status、partial checkpoint和open/resolved reason drift。
- [x] 新增ADR-0078、Goal Brief、P-096并更新B-011/B-012、operator/troubleshooting/absence/architecture、receiver deployment
  README与CHANGELOG。`SQLiteDeadManReceiverStore`类体拆回447行，保持硬约束。
- [x] Gate：定向receiver/liveness/heartbeat/Phase回归`121 passed`，full root`968 passed, 1 skipped`、SME isolated
  `53 passed`；Ruff、root mypy(219 source files)、SME strict mypy(37 source files)、219个AICO/tests format、126个AICO
  生产文件/2529 definitions结构、9份JSON、dead-man Compose、133-member offline wheel与diff通过。全仓format仍只报告
  未触碰的既有`projects/data-agent-v1/src/data_agent_v1/engine.py`。
- [ ] external-state仍无真实`.env`、runtime alert endpoint、LaunchAgent或第二故障域receiver；本轮没有外发、provider调用、
  auto-restart或live restore。机器合同不关闭B-011/B-012，goal保持active。

---

## Round 239 完成:Confirmed required-component runtime alerts

- [x] required Channel/default Adapter/scheduler连续三份时间递增FAILED后才创建`health:*` incident；计数跨restart持久化，
  相同/倒退snapshot不放大。optional、DEGRADED和瞬时失败不open，FAILED后只有OK或显式改为optional才resolved。
- [x] 第三次确认、active incident和immutable outbox event同SQLite transaction提交；sink继续复用稳定event id、队首顺序与
  1/5/15分钟持久重试。unsafe component name只外发hash，不保存异常、endpoint、secret、target或业务正文。
- [x] owned-task OPEN/RECOVERING与同名scheduler health去重；health incident只通知，不触发restart、provider replay、restore、
  grant消费或业务副作用。heartbeat改为health先于alert，dead-man pulse继续独立。
- [x] state schema升级v13；backup/reset和`aico-state`覆盖confirmation table，CLI只显示candidate数量。新增ADR-0077、Goal Brief、
  P-095并更新ADR-0044、B-011、operator/troubleshooting/absence docs与CHANGELOG。
- [x] Gate：required-component/heartbeat/Phase/state/recovery回归`136 passed`，full root`964 passed, 1 skipped`、
  SME isolated`53 passed`；Ruff、root mypy(219 source files)、SME strict mypy(37 source files)、219个AICO/tests format、
  126个AICO生产文件结构、9份JSON、dead-man Compose、133-member wheel与diff通过。全仓format仍只报告未触碰的既有
  `projects/data-agent-v1/src/data_agent_v1/engine.py`。
- [ ] external-state仍无真实`.env`、runtime alert endpoint、LaunchAgent或remote receiver ACK；本轮没有外发、provider调用、
  auto-restart或live restore。机器incident合同不关闭B-011，goal保持active。

---

## Round 238 完成:Durable scheduled autonomy outcome delivery

- [x] `DISPATCH_RECORDED`终态从authoritative proposal/task/result投影成bounded exact envelope，绑定run/content SHA、
  source/outcome、criteria/source/evidence/failure；provider正文、target与raw message id不进入operator输出。
- [x] 新outbox按PENDING/SENDING/RETRYING/DELIVERED/EXHAUSTED推进，1/5/15/15分钟最多五次；重启与ACK歧义只重发
  同一内容，不调用provider、不创建第二task或再次消费grant。wrong-target ACK拒绝落DELIVERED。
- [x] settled-without-outbox会在新工作前补建；open为DEGRADED、EXHAUSTED为required health FAILED。非关键started通知
  普通transport失败只脱敏记录，不再阻断enforced read-only TaskBus submit；dispatch后的IM异常会interrupt残留RUNNING task，
  RUNNING/WAITING不冻结成terminal envelope。
- [x] state schema升级v12；Phase1/state backup/reset/`aico-state`接线完成。新增ADR-0076、Goal Brief、P-094并更新
  B-010/B-014、operator/troubleshooting/absence docs与CHANGELOG。
- [x] Gate：full root`958 passed, 1 skipped`、SME isolated`53 passed`；Ruff、root mypy(219 source files)、
  SME strict mypy(37 source files)、219个AICO/tests format、126个AICO生产文件结构、9份JSON、dead-man Compose、
  133-member wheel与diff通过。全仓format仍只报告未触碰的既有`projects/data-agent-v1/src/data_agent_v1/engine.py`。
- [ ] external-state仍无真实`.env`、owner grant、LaunchAgent或paid provider/IM样本；本轮没有外发、provider调用或live restore。
  outcome ACK合同不关闭B-010/B-014，goal保持active。

---

## Round 237 完成:Durable scheduled disposable recovery drill

- [x] 新增独立默认关闭的owner opt-in drill cadence/max age；只选择latest VERIFIED + custody VERIFIED recovery artifact，
  先写稳定intent，再在线程和private disposable workspace运行既有state/audit/memory production materializer。
- [x] drill状态为PENDING/RUNNING/RETRYING/VERIFIED/EXHAUSTED，失败按1/5/15/15分钟最多五次；RUNNING重启以同ID立即
  retry且不消费attempt。due/open为DEGRADED，EXHAUSTED或success receipt stale为required health FAILED。
- [x] receipt绑定artifact、backup receipt与policy SHA、component counts/heads、config revision和post-restore缺项，固定
  `business_restore_ready=false`。open/latest exhausted目标受retention保护，即使当前关闭drill也不会因配置切换遗忘现场。
- [x] state schema升级v11；Phase1/service/env/doctor和`aico-state`覆盖drill policy、intent与secret-free receipt。
  scheduler拆成456行主类+181行coordinator，继续满足类/方法硬约束。新增ADR-0075、Goal Brief、P-093并更新B-013与runbook。
- [x] Gate：full root`948 passed, 1 skipped`、SME isolated`53 passed`；Ruff、root mypy(218 source files)、
  SME strict mypy(37 source files)、218个AICO/tests format、125个AICO生产文件结构、9份JSON、dead-man Compose、
  132-member wheel与diff通过。全仓format仍只报告未触碰的既有`projects/data-agent-v1/src/data_agent_v1/engine.py`。
- [ ] external-state复核确认仍无真实`.env`、off-device artifact、LaunchAgent或provider/IM样本；本轮没有执行live restore、
  外发或provider调用。scheduled local drill不关闭B-013，goal保持active。

---

## Round 236 完成:Bounded crash-consistent recovery retention

- [x] 新增独立默认关闭的owner opt-in retention；age、至少保留两个最新VERIFIED代际、check interval与单轮prune上限共同
  约束候选，只处理同一destination binding下custody VERIFIED的scheduled pair，并按最老优先。
- [x] 删除前事务性落`PRUNING`、开始时间和policy SHA，再重新deep verify artifact/sidecar；artifact→directory fsync→sidecar→
  directory fsync后才写`PRUNED`，SQLite永久保留receipt/artifact/policy SHA和时间tombstone。
- [x] restart覆盖pair、sidecar-only、neither、artifact-only矩阵；前三者安全收敛，artifact-only/字节漂移保留现场并使health FAILED。
  owner关闭开关只阻止新intent，不能取消已落盘的破坏性intent；到期候选未推进时health DEGRADED。
- [x] state schema升级v10；Phase1/service/env增加完整retention policy，`aico-state`输出secret-free intent/tombstone字段且不显示
  artifact path/destination raw identity。新增ADR-0074、Goal Brief、P-092并更新B-013、operator/troubleshooting/architecture。
- [x] Gate：full root`937 passed, 1 skipped`、SME isolated`53 passed`；Ruff、root mypy(217 source files)、
  SME strict mypy(37 source files)、217个AICO/tests format、124个AICO生产文件结构、9份JSON、dead-man Compose、
  131-member wheel与diff通过。全仓format仍只报告未触碰的既有`projects/data-agent-v1/src/data_agent_v1/engine.py`。
- [ ] live external-state复核确认当前checkout仍没有`.env`、真实storage policy/artifact、LaunchAgent、owner binding/grant或
  外部IM/provider样本；本轮没有执行真实artifact删除、外发或provider调用，B-013保持DEFERRED。

---

## Round 235 完成:Continuous recovery artifact custody attestation

- [x] scheduled receipt schema v2绑定secret-free destination fingerprint；同一output binding后续capture要求目录
  device/filesystem/inode identity连续，改变backup cadence不会创建新storage baseline。
- [x] 新增独立periodic custody deep verify：在worker thread重开latest artifact/sidecar，验证regular/owner-only、receipt SHA、
  artifact SHA和完整production recovery-set；成功/失败时间与failure count durable落盘。
- [x] missing/tamper/receipt drift、权限放宽、目录替换和custody max age超限均投影为required runtime health FAILED；
  heartbeat只做cheap stat/identity gate，不会每30秒同步hash大artifact。
- [x] state schema升级v9；`aico-state`增加secret-free custody status/check time/failure count，不显示destination fingerprint/path。
  service/env支持独立custody interval/max age，doctor继续明确storage class未attest。
- [x] scheduler仍不restore/delete/mkdir/rebind。新增ADR-0073、Goal Brief、P-091；更新B-013、operator/troubleshooting/
  architecture、`.env.example`、CHANGELOG与ROUNDS。
- [x] Gate：full root`925 passed, 1 skipped`、SME isolated`53 passed`；Ruff、root mypy(217 source files)、
  217个AICO/tests format、124个AICO生产文件结构、9份JSON、dead-man Compose、131-member wheel与diff通过。
  全仓format仍只报告未触碰的既有`projects/data-agent-v1/src/data_agent_v1/engine.py`。
- [ ] 当前checkout仍无`.env`、真实storage/LaunchAgent/owner binding/grant或外部IM/provider样本；kernel identity不证明
  volume UUID、加密、第二故障域、retention、RPO/RTO或commercial DR，B-013保持DEFERRED。

---

## Round 234 完成:Durable scheduled core recovery backup

- [x] 新增默认关闭的core recovery backup scheduler：每个窗口先持久化稳定intent，再生成唯一artifact、立即deep verify并发布
  owner-only receipt；PENDING/RUNNING/RETRYING/VERIFIED/EXHAUSTED按1/5/15/15分钟最多五次。
- [x] 启动恢复覆盖artifact/sidecar存在矩阵：两者都有则复验，artifact-only补receipt，receipt-only失败，两者都无才capture；
  不覆盖已有文件，不从文件名猜成功。
- [x] 纳入Phase1 lifecycle、heartbeat required health和bounded owned-task self-healing；无verified receipt为DEGRADED，
  RPO age超限或EXHAUSTED为FAILED。schema v8、state backup/reset和`aico-state`覆盖新表且只输出SHA证据。
- [x] 启用配置要求完整reviewed revision及已存在、absolute、owner-only、非symlink、checkout外目标；service doctor在install前
  fail closed，并明确`storage class not attested`。缺失mount不创建，scheduler永不restore或delete。
- [x] 新增ADR-0072、Goal Brief、P-090；更新B-013、operator/troubleshooting/architecture、`.env.example`、CHANGELOG与ROUNDS。
- [x] Gate：full root`917 passed, 1 skipped`、SME isolated`53 passed`；Ruff、root mypy(217 source files)、
  217个AICO/tests format、124个AICO生产文件结构、9份JSON、dead-man Compose、131-member wheel与diff通过。
  全仓format仍只报告未触碰的既有`projects/data-agent-v1/src/data_agent_v1/engine.py`。
- [ ] 当前checkout仍无`.env`、真实备份目标、LaunchAgent、owner binding/grant或外部IM/provider/storage样本；未生成真实artifact。
  本地scheduler不证明off-device encryption、retention、RPO/RTO或commercial DR，B-013保持DEFERRED。

---

## Round 233 完成:Durable scheduled autonomy intent recovery

- [x] 每个scheduled morning delivery在任何IM外发前写入稳定autonomy intent；主SQLite schema v7保存
  PENDING/RUNNING/RETRYING/SETTLED/EXHAUSTED、attempt/backoff、歧义与bounded run receipt。
- [x] standing coordinator在provider dispatch前把同一intent写入accepted proposal和task metadata；重启发现RUNNING时，
  有matching accepted proposal/task即结算且不重跑provider，无证据才按1/5/15/15分钟最多五次有界重试。
- [x] 已ACK晨报不因自治失败或恢复重发；open intent使health DEGRADED，EXHAUSTED使health FAILED。
  hold notification可能有界重复并沿用visible intent id，不冒充exactly-once。
- [x] `aico-state`新增recent scheduled autonomy摘要，只显示intent/status/attempt/disposition及proposal/task ID SHA；
  backup/reset覆盖新表，不显示project、target、消息或raw proposal/task identity。
- [x] 新增ADR-0071、Goal Brief、P-089；更新B-010/B-014、operator/troubleshooting/absence docs、CHANGELOG与ROUNDS。
- [x] Gate：full root`902 passed, 1 skipped`、SME isolated`53 passed`；Ruff、root mypy(214 source files)、
  214个AICO/tests format、122个AICO生产文件结构、9份JSON、dead-man Compose、129-file wheel与diff通过。
  全仓format仍只报告未触碰的既有`projects/data-agent-v1/src/data_agent_v1/engine.py`。
- [ ] 当前checkout仍无`.env`、owner binding/grant、LaunchAgent或真实IM/provider样本；本轮未发送真实消息、未调用provider。
  机器恢复合同不关闭B-010/B-014，也不证明human read、provider exactly-once或商业DR。

---

## Round 232 完成:Durable scheduled morning delivery receipts

- [x] 新增SQLite morning outbox与schema v6：首次发送前固化daily delivery id、exact `MessageContent`、content SHA和所含
  standing autonomy receipt SHA；同binding同一天重启或`push_on_start`不重新渲染。
- [x] 发送失败按1/5/15/15分钟最多五次重试；发送中崩溃恢复为retrying并标记`duplicate_possible=true`，耗尽后
  scheduler/runtime health为FAILED，不再把background task存活冒充delivery健康。
- [x] 平台ACK后立即持久化DELIVERED与raw message id SHA，随后才运行standing autonomy；自治异常不会重发已确认晨报。
  平台缺乏端到端幂等时只声明bounded at-least-once，不声称exactly-once或老板已读。
- [x] `aico-state`新增recent morning receipt视图，只输出delivery/status/attempts/duplicate/content SHA/receipt count/time，
  不显示target、正文或raw message id；正式morning push强制`AICO_STATE_DB_PATH`。
- [x] 新增ADR-0070、Goal Brief、P-088；更新B-010/B-014、operator/troubleshooting/absence docs、`.env.example`、
  CHANGELOG与ROUNDS。
- [x] Gate：scheduled相关`221 passed`、full root`897 passed, 1 skipped`、SME isolated`53 passed`；Ruff、root mypy
  (213 source files)、213个AICO/tests format、121个AICO生产文件结构、9份JSON、dead-man Compose、128-file wheel与diff通过。
  全仓format仍只报告未触碰的既有`projects/data-agent-v1/src/data_agent_v1/engine.py`。
- [ ] 当前checkout仍无`.env`、owner binding/grant、LaunchAgent或真实IM/provider样本；本轮未发送真实消息。delivery machine
  contract不关闭B-010/B-014，也不证明human read、platform展示持久性或商业DR。

---

## Round 231 完成:Live provider authentication receipts

- [x] runtime reinjection schema v2固定`claude-code`及所有enabled optional adapter的canonical provider集合；capture/verify间
  provider启停漂移fail closed，receipt/manifest不保存credential或provider identity。
- [x] 新增可插拔provider authentication probe；内建Claude关闭customization/tools/Chrome/session，Codex忽略user config/rules、
  ephemeral、read-only/no-network。两者只从配置取official executable，不继承bypass/yolo参数。
- [x] probe在private empty cwd运行独立process group，移除`AICO_*` child env，限制90秒和stdout/stderr各256 KiB；必须同时
  返回随机challenge exact response、terminal success与provider usage，timeout/overflow/缺usage/unsupported provider不落回执。
- [x] 新增`aico-recovery provider-auth-receipt|verify-provider-auth`：owner-only atomic new-path receipt绑定set SHA、
  reinjection receipt SHA、revision、owner decision、provider scope与probe executable hash，30分钟过期；只存challenge SHA，
  不存challenge/prompt/output/error/credential。offline verify明确不重放付费probe。
- [x] recovery-set升级schema v6；AI provider改为`post_restore_live_probe`合同就绪，并新增
  `requires_post_restore_evidence`/`post_restore_evidence_assets`。`unresolved_assets=()`不提升`business_restore_ready=false`。
- [x] 新增Goal Brief、ADR-0069、P-087；更新B-013/B-014、operator/architecture/absence docs、CHANGELOG、STATUS与ROUNDS。
- [x] Gate：provider/recovery定向`27 passed`、full repo`889 passed, 1 skipped`、SME isolated`53 passed`；Ruff、root
  mypy(212 source files)、212个AICO/tests format、120个AICO生产文件结构、9份JSON、dead-man Compose、127-file wheel
  与diff通过。全仓format仍只报告未触碰的既有`projects/data-agent-v1/src/data_agent_v1/engine.py`。
- [ ] 当前checkout仍无`.env`、owner grant、durable runtime或真实provider/IM样本；本轮未消费付费provider。独立receiver、
  encrypted off-device、RPO/RTO/full-business验收仍缺；B-010/B-012/B-013/B-014保持。

---

## Round 230 完成:Independent dead-man receiver recovery

- [x] receiver SQLite增加schema version 1；service lifespan全程持有DB path-derived kernel owner lock，第二个receiver与
  active-worker restore均在写入前fail closed，不能通过删除lock metadata绕过。
- [x] 新增`aico-dead-man-recovery backup|verify`：在线backup生成`0600` standalone artifact；offline verifier要求exact
  DDL/constraints、拒绝trigger/view/user index，并深验monitor checkpoint、outage/event/payload/delivery/time语义。
- [x] 新增disposable `drill`：实际调用production restore、比较semantic counts、清理workspace，可发布owner-only、
  runtime/event/payload/path-free JSON evidence report。
- [x] 新增显式`restore --expected-sha256 --yes`：active worker拒绝；有效live先生成verified safety backup，无法验证的
  DB/WAL/SHM保留到owner-only quarantine，再替换standalone DB并清理stale sidecar。
- [x] recovery-set升级schema v5；receiver state保持`included=false`，但以`external_component_recovery`标记独立合同就绪。
  AICO恢复不捕获、不授权也不触发receiver同步回滚；AI provider live authentication仍是唯一required unresolved contract。
- [x] 新增Goal Brief、ADR-0068、P-086；更新B-012/B-013、receiver deploy runbook、quickstart/daily/troubleshooting、
  architecture、CHANGELOG、STATUS与ROUNDS。
- [x] Gate：receiver/recovery定向`43 passed`、full repo`880 passed, 1 skipped`、SME isolated`53 passed`；Ruff、root
  mypy(209 source files)、209个AICO/tests format、118个AICO生产文件结构、8份JSON、Compose、125-file wheel与diff通过。
- [ ] 真实第二故障域receiver部署/backup/outage样本、encrypted off-device位置、AI provider认证和隔离full-business
  RPO/RTO/IM样本仍缺；B-010/B-012/B-013/B-014保持。

---

## Round 229 完成:Secret-free runtime reinjection receipts

- [x] 新增runtime reinjection contract：capture要求checkout根目录`.env`为owner-only、Git未跟踪、regular non-symlink、bounded且无
  duplicate key，并复用production service readiness检查channel/required key、alert/liveness、IM ingress与approval lease。
- [x] manifest只记录active control-plane secret slot名称、channel和standing grant enabled mode；不保存secret值/hash、
  owner/target identity、grant正文/ID或绝对路径。灾后允许轮换credential，不允许slot/mode静默漂移。
- [x] standing grant启用时复用真实Project/Persona/Adapter/morning target preflight；灾后可重新签发，但必须非空、owner-only、
  位于managed repo外并保持hard read-only binding。
- [x] 新增`aico-recovery reinjection-receipt`：先deep verify set和exact clean checkout，再要求safe owner decision reference，
  以`0600`、atomic、new-path JSON绑定set SHA/revision/slot/grant count/time；发布失败不留ambiguous artifact。
- [x] 新增`verify-reinjection`：要求独立receipt SHA并重跑当前material checks；拒绝hash/permission/symlink/forgery/slot drift/
  invalid grant，允许同slot的secret轮换。receipt固定`business_restore_ready=false`。
- [x] recovery-set升级schema v4；`control_plane_secrets`与`standing_grant`合同就绪但未内嵌。`ai_provider_authentication`单列
  required unresolved且receipt固定`external_authentication_live_verified=false`，不把presence冒充远端认证。
- [x] 新增Goal Brief、ADR-0067、P-085；更新ADR-0066状态、B-013、quickstart/daily/troubleshooting、absence playbook、
  architecture、`.env.example`、CHANGELOG、STATUS与ROUNDS。
- [x] Gate：production-preflight/recovery交叉`135 passed`、full root`873 passed, 1 skipped`、SME isolated`53 passed`；
  Ruff、root mypy(206 source files)、206个AICO/tests format、116个AICO生产文件结构、8份JSON、Compose、123-file wheel与diff通过。
- [ ] AI provider真实认证、dead-man receiver DB recovery、encrypted off-device位置、隔离full-business RPO/RTO/IM样本及
  owner-bound LaunchAgent/provider仍缺；B-010/B-013/B-014保持。

---

## Round 228 完成:Reviewed configuration revision recovery

- [x] 新增reviewed configuration evidence：capture必须接收owner/CI在独立信任面选定的完整Git commit，并验证checkout是
  worktree root、HEAD精确匹配、全工作树clean、tree object稳定；当前HEAD本身不再被当作review authority。
- [x] active Project/Persona JSON必须位于checkout内、是regular non-symlink tracked file且字节与reviewed commit blob一致；
  evidence绑定relative path、blob OID、size与SHA-256。未传persona文件时明确记录`built_in_at_revision`。
- [x] recovery-set升级schema v3与scope`core_state_audit_memory_config_revision`；配置正文不进入artifact，project/persona
  以`included=false`、`recovery_contract_ready=true`表达“从精确版本恢复”，不能把未打包偷换成缺口或已内嵌。
- [x] 新增`aico-recovery verify-checkout`：先深验outer/component artifact，再拒绝wrong revision、dirty tree和config drift；
  不自动checkout/pull/reset。capture输出强制位于checkout外，避免新artifact让clean-tree检查自我失败。
- [x] required unresolved assets从五项收敛为三项：runtime secret、standing grant与dead-man receiver state；仍固定
  `global_transaction=false`、`business_restore_ready=false`，不声明平台review签名、remote availability或full DR。
- [x] 新增Goal Brief、ADR-0066、P-084；更新ADR-0065状态、B-013、quickstart/daily/troubleshooting、absence playbook、
  architecture、`.env.example`、CHANGELOG、STATUS与ROUNDS。
- [x] Gate：新增配置/recovery-set定向`18 passed`、full root`865 passed, 1 skipped`、SME isolated`53 passed`；
  Ruff、root mypy(203 source files)、203个AICO/tests format、114个AICO生产文件结构、8份JSON、Compose、121-file wheel与diff通过。
- [ ] 真实encrypted off-device位置、secret/grant reinjection receipt、receiver DB recovery、隔离full-business RPO/RTO/IM样本，
  以及owner-bound LaunchAgent/provider仍缺；B-010/B-013/B-014保持。

---

## Round 227 完成:Tamper-evident memory recovery

- [x] `JsonlMemoryStore`改用独立memory ledger：process file lock内刷新tail，canonical SHA-256 previous/head chain与owner-only
  checkpoint检测修改、重排、截断和半写；append+fsync先于checkpoint，索引只在durable写成功后重建。
- [x] 保留同`memory_id`多版本最后生效语义及peer writer可见性；legacy JSONL必须owner核对后显式`aico-memory seal`，
  checkpoint lag只在唯一合法crash window自动收敛，未知损坏继续fail closed。
- [x] 新增`aico-memory verify|seal|backup|verify-backup|drill-backup|restore`：fixed-member owner-only artifact、outer SHA、
  domain model深验、disposable production materialization、runtime owner fence及verified safety/unverified quarantine完整闭环。
- [x] recovery-set升级schema v2，按state→audit→memory生成fixed-four-member artifact；scope固定
  `core_state_audit_memory`，三套production verifier/materializer均通过，memory从coverage缺项变为captured。
- [x] 新增Goal Brief、ADR-0065、P-083；更新B-013、quickstart/daily/troubleshooting、absence playbook、architecture、
  `.env.example`、CHANGELOG、STATUS与ROUNDS。
- [x] Gate：恢复相关`127 passed`、full root`856 passed, 1 skipped`、SME isolated`53 passed`；Ruff、root/SME
  mypy(201/37 source files)、201个AICO/tests format、113个AICO结构、8份JSON、Compose、120-file wheel与diff通过。
- [ ] core set仍是明文sequential window，config/secret/grant/receiver、off-device
  encryption/retention、combined business restore及真实owner/runtime/provider/IM证据仍缺；B-010/B-013/B-014保持。

---

## Round 226 完成:Bounded-window core recovery set

- [x] 新增`aico-recovery capture`：按state→audit顺序复用既有online/writer-locked backup原语，生成`0600`、new-path、
  fixed-three-member ZIP_STORED，outer manifest绑定component hash/size/summary与整体capture start/end。
- [x] schema强制`scope=core_state_and_audit_only`、`consistency=sequential_component_snapshots`、
  `global_transaction=false`、`business_restore_ready=false`；不能把bounded window冒充同一事务或完整DR。
- [x] 固定coverage ledger列出state/audit captured、memory snapshot primitive缺失、project/persona config从source control
  恢复、runtime secret/standing grant重新注入、receiver state独立备份及ephemeral runtime排除。
- [x] `verify`强制expected outer SHA并深入运行SQLite integrity/schema与audit archive/chain verifier；`drill`在private
  disposable workspace实际运行两套production materializer并可发布atomic owner-only report，不触碰live或提供combined restore。
- [x] member/manifest/inner component/outer hash、false readiness、extra/compressed member、existing output、live sidecar、
  permission/symlink/report race和CLI隐私边界均由red-green覆盖。
- [x] 新增Goal Brief、ADR-0064、P-082；更新B-013、quickstart/daily/troubleshooting、absence playbook、architecture、
  `.env.example`和CHANGELOG。
- [x] Gate：恢复相关`103 passed`、full root`845 passed, 1 skipped`、SME isolated`53 passed`；Ruff、root/SME
  mypy(196/37 source files)、196个AICO/tests format、110个AICO结构、9份JSON、Compose、117-file wheel与diff通过。
- [ ] set含明文state/audit且只提供sequential bounded window；memory/config/secret/grant/receiver与off-device
  encryption/retention、combined business restore仍缺，B-013保持。真实owner binding/LaunchAgent/paid provider/IM仍缺。

---

## Round 225 完成:Owner-fenced audit restore and drill

- [x] 新增`materialize_audit_backup()`与`aico-audit drill-backup`：强制expected outer SHA，在private disposable
  workspace走production pair replacement和chain/checkpoint verifier；可发布`0600`、atomic new-path evidence report，
  不触碰live audit且成功失败都清理workspace。
- [x] 新增`aico-audit restore`：必须显式提供真实AICO state DB、expected SHA、new preservation output和`--yes`；
  校验state identity并取得同一runtime owner lock，active runtime、错误DB/SHA或已有输出均在覆盖前fail closed。
- [x] live完整时先生成标准verified safety backup；live损坏/unsealed时writer-locked复制原始owned regular bytes到
  `unverified_quarantine`，manifest只含固定member name/size/hash，不把损坏现场包装成可信恢复点。
- [x] ledger/checkpoint staged pair先完整验证再分别replace+directory fsync；故障注入证明第二次replace失败后严格reader
  拒绝半恢复现场，复用同一可信备份和新的preservation路径可重跑收敛。
- [x] 新增Goal Brief、ADR-0063、P-081；更新B-013、quickstart/daily/troubleshooting、absence playbook、architecture、
  `.env.example`和CHANGELOG。
- [x] Gate：恢复相关`94 passed`、full root`836 passed, 1 skipped`、SME isolated`53 passed`；Ruff、root/SME
  mypy(193/37 source files)、193个AICO/tests format、108个AICO结构、9份JSON、Compose、115-file wheel与diff通过。
- [ ] 这是owner-triggered local component restore，不是automatic restore、off-device加密/retention、跨truth-source一致
  snapshot或隔离checkout业务RTO/RPO证据；B-013保持。真实owner binding/LaunchAgent/paid provider/scheduled IM仍缺。

---

## Round 224 完成:Portable audit recovery point

- [x] 新增`copy_audit_ledger_snapshot()`：在既有process writer lock内验证live ledger、收敛唯一合法checkpoint lag，
  再复制matching ledger/checkpoint；初始化空ledger同样可形成恢复点，live后续追加不改变artifact。
- [x] `aico-audit backup --output`生成`0600`、new-path、fixed-three-member ZIP_STORED；manifest记录schema/time、
  event count、ledger size/head和两个member hash，summary输出独立artifact SHA且不含source path/payload。
- [x] `verify-backup`无需live path，拒绝symlink/宽权限/额外/压缩member，流式校验size/hash并在private temp中调用
  production chain/checkpoint verifier；可强制比对另一信任位置记录的expected SHA。
- [x] publication使用same-directory temp + hard-link no-overwrite + file/directory fsync；现有output、legacy未seal、
  member/manifest/outer hash篡改和发布失败均fail closed且不留下自己的半成品。
- [x] 新增Goal Brief、ADR-0062、P-080；更新B-013、quickstart/daily/troubleshooting、absence playbook、architecture、
  `.env.example`和CHANGELOG。
- [x] Gate：相关`163 passed, 1 skipped`、full root`827 passed, 1 skipped`、SME isolated`53 passed`；Ruff、
  root/SME mypy(190/37 source files)、190个AICO/tests format、106个AICO结构、9份JSON、Compose、113-file wheel和
  diff通过。
- [ ] artifact含明文audit正文且全量copy期间短时锁writer；没有destructive restore、off-device加密/retention、
  全资产bundle或隔离业务恢复，B-013保持。真实owner binding/LaunchAgent/paid provider/scheduled IM仍缺。

---

## Round 223 完成:Tamper-evident local audit ledger

- [x] 新audit event保留顶层业务字段并加入canonical SHA-256 previous/head link；owner-only checkpoint锚定count、
  byte size和chain head，检测字段修改、插入、重排、tail截断与torn record。
- [x] process file lock串行化writer；event append+fsync先于checkpoint原子replace+fsync。唯一允许的checkpoint lag可在
  restart收敛，同event retry保持幂等且duplicate id/collision fail closed。
- [x] `aico-audit verify|seal`提供运维入口；legacy必须owner核对后显式seal且不重写event bytes，错误路径不会生成伪
  baseline。ledger/checkpoint/lock拒绝symlink、非regular、非owner与宽权限。
- [x] Phase 1 replay与`aico-service doctor/install`统一校验完整性，损坏历史不会进入metrics、recovery或老板视图；
  新增Goal Brief、ADR-0061、P-079及quickstart/daily/troubleshooting/absence/DR文档。
- [x] Gate：相关`151 passed, 1 skipped`、full root`815 passed, 1 skipped`、SME isolated`53 passed`；Ruff、
  root/SME mypy(188/37 source files)、188个AICO/tests format、105个AICO结构、9份JSON、Compose、112-file wheel和
  diff通过。
- [ ] 这是owner-local tamper evidence，不是数字签名、TPM、远端时间戳、WORM或恶意同主机防护；真实owner binding、
  LaunchAgent、paid provider、scheduled IM与audit+checkpoint off-device恢复仍缺，B-010/B-013/B-014保持。

---

## Round 222 完成:Persisted authorization clock rollback fence

- [x] 新增共享`AuthorizationClockGuard`/store接口；主SQLite schema 5持久一行authorization high-water，跨重启不丢。
- [x] 同进程用monotonic elapsed推导最低wall time，跨进程用持久high-water；允许5秒小幅校时，明显回拨不降低锚点。
- [x] rollback会把全部pending approval事务性收口为`expired/rejected`并写既有audit outbox；旧短ID不能批准。
- [x] 新risk approval、direct preauthorized task和scheduled standing grant全部fail closed；standing只发hold，不创建accepted
  proposal、不dispatch provider，wall time追平后仅允许新的authorization。
- [x] state backup/verify/reset覆盖`authorization_clock_state`；新增Goal Brief、ADR-0060、P-078及operator/architecture文档。
- [x] Gate：相关`169 passed`、full root`799 passed, 1 skipped`、SME isolated`53 passed`；Ruff、root/SME mypy
  (185/37 source files)、185个AICO/tests format、103个AICO结构、9份JSON、Compose、110-file wheel和diff通过。
- [ ] 这是owner-local rollback fence，不是NTP、签名、TPM或恶意主机防护；真实owner binding、LaunchAgent、paid provider
  和scheduled IM样本仍缺，B-010/B-014保持。

---

## Round 221 完成:Owner-bound IM ingress before orchestration

- [x] 正式Phase 1 runtime在command解析前同时精确校验configured channel、owner sender和trusted reply target；任一
  binding为空即deny all，陌生sender与owner所在错误群都不能进入业务路径。
- [x] 未授权普通消息及`/approve`均silent drop，不发送reply、不创建task、不修改approval/memory/audit、不调用
  Adapter；owner之后仍可处理原waiting approval。
- [x] identity list最多16项、每项256字符，placeholder/unknown/控制字符fail closed；额外approval reviewer必须
  属于owner sender，enabled morning target必须属于trusted target。
- [x] denial log默认不含identity/content并按累计1/2/4/8...限流；显式foreground discovery仍拒绝业务，只把escaped
  sender/target写本地日志，`doctor/install`在discovery开启时FAIL。
- [x] 新增可插拔`IngressAuthorizer`/`IngressGuard`；可复用Orchestrator保留显式allow-all兼容，正式runtime必注入
  owner-bound policy。必要的memory capture helper提取后`Orchestrator`保持497行。
- [x] 新增Goal Brief、ADR-0059、P-077；更新B-010/B-014、operator docs、architecture、absence playbook、
  `.env.example`和CHANGELOG。
- [x] Gate：相关`260 passed`、full root`791 passed, 1 skipped`、SME isolated`53 passed`；Ruff、mypy
  (183 source files)、183个AICO/tests format、102个AICO结构、9份JSON、Compose、109-file wheel contract和diff通过。
- [ ] sender ID依赖IM平台账号/事件真实性，不是密码学owner签名或账号接管防护；真实owner binding、LaunchAgent和
  Telegram/Feishu常驻样本仍缺，B-010/B-014保持。

---

## Round 220 完成:Bounded approval lease and transactional expiry

- [x] 新risk approval创建时冻结aware `expires_at`；默认24小时，只允许`AICO_APPROVAL_MAX_AGE_SECONDS=300..604800`，
  后续放大配置不能追溯延长旧票据。
- [x] startup、`task_snapshot(s)`、pending query和`/approve`/`/reject`前lazy sweep；精确到期即
  `approval=expired`、`task=rejected`，不dispatch、不自动批准或重提。
- [x] SQLite在同一`BEGIN IMMEDIATE`事务更新approval/task并写`approval_expired` reconciliation outbox；insert
  失败全回滚，audit sink失败保留pending并按稳定event id跨重启重投。
- [x] legacy无deadline记录按当前bounded policy保守推导，naive timestamp fail closed；老板inbox不再给过期task展示
  `/approve`，而是给出`/task`恢复路径。
- [x] `aico-service doctor`在install前拒绝非整数/越界lease且不回显原值；审批时间职责抽到
  `ApprovalLeaseCoordinator`，`TaskBus`类保持492行。
- [x] 新增Goal Brief、ADR-0058、P-076；更新B-010、operator docs、architecture、playbook、`.env.example`和CHANGELOG。
- [x] Gate：相关`235 passed`、full root`775 passed, 1 skipped`、SME isolated`53 passed`；Ruff、mypy
  (181 source files)、181个AICO/tests format、101个AICO结构、9份JSON、Compose、wheel contract和diff通过。
- [ ] lease只约束AICO approval，不是多人审批/owner签名/外部credential撤销；真实`.env`、LaunchAgent和IM常驻样本
  仍缺，B-010保持。

---

## Round 219 完成:Standing evidence fingerprint and drift gate

- [x] complete result持久化bounded source manifest：canonical repo-relative path、line、file size/SHA-256与aggregate
  digest；不保存source正文，不在老板IM展示path/hash。
- [x] 每个结果最多16个distinct source、单文件256KiB；同文件多行只读取/hash一次，单次result最坏约4MiB IO。
- [x] SQLite restart后可重算`evidence=current/drifted/missing`；文件变化/删除分别投影`outcome=drifted/missing`。
- [x] 下一次dispatch只复核同grant最近成功结果，老板面只复核最近5份receipt；检查成本不随全部历史无界增长。
- [x] drift/missing均停止后续scheduled dispatch；invalid/blocked/history missing contract规则保持不变。
- [x] 新增Goal Brief、ADR-0057、P-075；更新B-014、operator docs、architecture、playbook和CHANGELOG。
- [x] Gate：相关`167 passed`、full root`766 passed, 1 skipped`、SME isolated`53 passed`；Ruff、mypy
  (181 source files)、181个AICO/tests format、AICO structure、9份JSON、Compose、wheel contract和diff通过。
- [ ] SHA-256是本地漂移锚点，不是签名/业务语义/provider/IM证据；真实owner grant和scheduled paid sample仍缺。

---

## Round 218 完成:Bounded standing result envelope

- [x] preauthorized result总长固定32,768字符；Codex Adapter与Orchestrator最多保留32,769字符用于确定性超限判定，
  raw正文不进入IM或proposal。
- [x] schema/model限制16 criteria、16 stops、每criterion 8 sources、各类list 16项、正文2,000字符、path 512字符；
  同步测试防双份合同漂移。
- [x] `StandingCharterItem`在配置入口同步拒绝超量criteria/stop/text，避免生成一个永远无法满足的standing任务。
- [x] JSON语法、duplicate/schema overflow、总长overflow分别记录`invalid_json`、`result_schema_invalid`、
  `result_too_large`，全部停授且receipt保持bounded。
- [x] 新增Goal Brief、ADR-0056、P-074；更新B-014、operator docs、architecture、playbook和CHANGELOG。
- [x] Gate：相关`159 passed`、full root`758 passed, 1 skipped`、SME isolated`53 passed`；Ruff、mypy
  (181 source files)、105个format、AICO structure、19份JSON、Compose、wheel schema和diff通过。
- [ ] 该边界保护本地接收/持久化资源，不是provider生成期token/cost cap；真实owner grant、付费provider和scheduled
  IM样本仍缺，B-014保持。

---

## Round 217 完成:Repository-grounded standing result contract

- [x] preauthorized Codex固定命令增加versioned `--output-schema`；charter acceptance/stop稳定编号为
  `A1..An`/`S1..Sn`，只接收结构化complete/blocked结果。
- [x] 本地验证精确条目覆盖、complete/blocked一致性、repo-relative path边界、文件与1-based行存在；invalid JSON、
  路径穿越、缺文件/行、矛盾结果全部记`invalid`。
- [x] durable proposal新增bounded result receipt；不新增outcome表，不保存/展示原始JSON。transport done与outcome
  complete明确分离。
- [x] `/inbox`、`/morning`显示`outcome`、criteria coverage和verified source count；prior result
  missing/invalid/blocked会阻断后续scheduled run。
- [x] raw standing JSON不进入老板IM；provider错误仍按原错误路径可见。新增Goal Brief、ADR-0055、P-073并更新B-014。
- [x] Gate：相关`137 passed`、full root`749 passed, 1 skipped`、SME isolated`53 passed`；Ruff、mypy
  (181 source files)、AICO structure、19份JSON、Compose、wheel schema packaging和diff通过。
- [x] 本地source verification只证明位置存在，不证明业务语义真实；Codex没有可配置max-output硬限额，本轮未调用付费
  provider或创建真实grant，B-014保持。

---

## Round 216 完成:Post-run provider usage circuit breaker

- [x] preauthorized Codex固定命令启用`--json`；只把completed agent message送入现有stream，thread/tool/status JSONL不泄漏。
- [x] 解析`turn.completed.usage`的input/output/cached/cache-write/reasoning，TaskBus在DONE前写结构化
`TASK_USAGE_RECORDED`；不填猜测的`cost_usd`。
- [x] accepted preauthorized proposal持久化`TaskUsage + recorded_at`；SQLite restart仍能重建terminal token receipt。
- [x] external grant新增必填`token_stop_threshold`；下一次dispatch前按同grant累计实测total熔断，任何已消费run缺usage
  直接fail closed，不把unknown当0，不retry/refund。
- [x] `/inbox`、`/morning` terminal receipt显示bounded`tokens=N`；matching task但usage缺失同样显示`evidence_missing`。
- [x] 新增Goal Brief、ADR-0054、P-072；更新B-014、operator docs、absence playbook、architecture和CHANGELOG。
- [x] Gate：相关`122 passed`、service/phase/metrics`81 passed`、full root`735 passed, 1 skipped`、SME`53 passed`；
  Ruff、mypy(179 source files)、AICO structure、3份JSON、Compose和diff通过。
- [ ] 这是post-run cumulative circuit breaker，不是当前run硬token/cost上限；本轮未调用付费provider，B-014保持。

---

## Round 215 完成:Standing autonomy execution receipts

- [x] 新增derived receipt：只从accepted preauthorized proposal与matching task/proposal/grant metadata、authoritative
  TaskSnapshot投影，不新增表/schema或第二份outcome truth。
- [x] 覆盖running/waiting/done/failed/interrupted/rejected；无task/snapshot或metadata不一致显示`evidence_missing`，
  保留at-most-once语义，不自动retry/refund。
- [x] `/inbox`与interactive/scheduled`/morning`展示short proposal/task/auth ref、charter、status和terminal elapsed；
  不显示owner/target、payload/output/reason/path/secret。
- [x] failed/interrupted/rejected/missing进入恢复优先级，running进入monitor；done保留证据但不伪造待处理事项。
- [x] SQLite restart从既有proposal/task rows重建完全相同receipt，没有receipt table或render mutation。
- [x] receipt E2E发现并修复既存缺陷：preauthorized standing task不再复用overnight handoff grader，正常只读输出
  从假FAILED恢复为DONE；timeout仍INTERRUPTED且第二个morning tick不重复派发。
- [x] 新增Goal Brief、ADR-0053、P-071；更新B-014、operator docs、architecture、playbook和CHANGELOG。
- [x] Gate：receipt`9 passed`、相关`129 passed`、full root`731 passed, 1 skipped`、SME`53 passed`；Ruff、
  mypy(179 source files)、7个touched format、AICO structure、derived-only table check、JSON、Compose、diff通过。
- [ ] receipt是本地durable orchestration evidence，不是provider质量/成本/远端IM证据；真实owner sample仍待B-014。

---

## Round 214 完成:Standing autonomy deployment preflight

- [x] 新增`preflight_standing_autonomy()`：只构造内存Adapter/persona/agent/project control plane并调用production
  grant binding validator，不构造Channel/Orchestrator，不打开SQLite/JSONL/log/lock/heartbeat，不spawn CLI或联网。
- [x] `aico-service doctor`从owner-only`.env`只投影相关字段；project/persona/workspace相对路径按`--repo`解析，
  与launchd WorkingDirectory一致。
- [x] configured empty grant、target/thread/project drift、unknown project/charter、missing seat/persona、Codex disabled、
  non-Codex wrapper、malformed project/settings全部在install前FAIL。
- [x] success从旧`grant file verified`提升为`owner-bound runtime binding verified`；failure统一安全分类，不泄露
  owner/grant/target、path、command、token或raw parser input。
- [x] red-green新增/扩展10个standing doctor cases，并让同一Phase 1 valid fixture同时通过preflight和runtime build；
  preflight后`.aico`保持不存在。
- [x] 新增Goal Brief、ADR-0052、P-070；B-014收窄为真正owner config + durable provider/IM external sample。
- [x] Gate：full root`722 passed, 1 skipped`；SME`53 passed`；Ruff、mypy、4个touched format、AICO structure、
  JSON、Compose和`git diff --check`通过；真实doctor仍如实FAIL `.env` missing且未产生本地配置/state。
- [ ] preflight不是Codex登录、定时触发或IM送达证据；当前真实`.env`/grant/LaunchAgent仍不存在，goal保持active。

---

## Round 213 完成:Owner-bound read-only standing autonomy

- [x] 新增 strict versioned grant：owner/channel/target/thread/project/charter、aware expiry、`max_runs`、duration；
  只接受 repo 外、current-user-owned、`0600`、regular non-symlink 文件，拒绝占位符/重复绑定/宽权限/目标漂移。
- [x] scheduled morning 是唯一自动触发器；手工 `/inbox`、`/morning`、`/proposals`、startup 不消费授权。
- [x] proposal decision 在 dispatch 前以 `PREAUTHORIZED + grant_id` 持久化；SQLite restart 不重置预算，失败/timeout
  不自动返还 run。
- [x] TaskBus fail closed：只接受 read-only risk、collaboration disabled、无 provider session、且 Adapter 自己声明并
  实现 hard boundary 的任务；伪造 metadata 不能让 broad Adapter opt in。
- [x] 当前仅真实 `codex` executable 支持；固定 command 丢弃配置中的 bypass/write/search flags，强制 approval never、
  sandbox read-only、ignore config/rules、ephemeral、strict config、network disabled、no resume。
- [x] AICO wall-clock budget 超时会 interrupt TaskBus 并取消 waiter；start/hold 消息不泄露 grant path、owner id 或 payload。
- [x] SME `commercial-evidence-loop` 已校准为 Codex reviewer 的只读 evidence inspection；example config也有只读 charter。
- [x] 新增 Goal Brief、ADR-0051、P-069、B-014；更新 quickstart/daily ops/troubleshooting、architecture、absence playbook
  与 CHANGELOG。
- [x] Gate：focused `178 passed`；full root `712 passed, 1 skipped`；SME isolated `53 passed`；Ruff、mypy、
  touched format、AICO production structure、JSON、Compose和`git diff --check`通过；fixed Codex command仅做`--help`解析。
- [ ] 当前仍没有真实 owner grant、`.env`、LaunchAgent、付费 provider call 或定时 IM 样本；`0600` 也不是同一
  OS 用户恶意进程下的密码学 owner signature。B-014 保持 deferred，不能声称商用自治已部署。

---

## 当前补充验收:Telegram IM 老板可读性 Golden Loop

人类要求在不影响主链路的前提下,把 Telegram 中 Markdown 表格、无序列表、native HTML fallback、
`/ask`、`/inbox`、`/view` 等展示问题纳入可闭环验证,最多 3 个迭代完成。

- [x] 迭代 1:新增 Telegram UX golden 回归,覆盖中文编号标题粘连、`FindingsHigh:`、
  `Risks / approval need-`、inline Markdown bullets、unsupported `<ul>/<li>` fallback。
- [x] 迭代 2:修复 renderer / native output:
  - Telegram/IM 不再裸发 pipe Markdown 表格;
  - 小表、宽表、坏表尽量渲染为紧凑等宽 Telegram 表格;
  - 长单元格自动截断,并追加 `详情: /view 查看完整表格` 懒加载入口;
  - 行列不齐或缺表头的额外列使用 `补充1/补充2` 等稳定列名,不再重复 `补充`;
  - `补充`、`风险`、`建议`、`结论`、`下一步` 等中文字段在 Telegram HTML 中加粗;
  - HTML list fallback 转成 `• ` bullets,避免 `<ul>/<li>` 原样漏到 IM;
  - native Telegram prompt 要求优先使用紧凑 Telegram 表格,长内容细节交给 `/view` / `/task`。
- [x] 迭代 3:新增 Telegram Channel payload golden,在 mock Bot API 层验证实际 `sendMessage`
  payload 中 Markdown 表格会变为等宽紧凑表格,HTML list fallback 不含 unsupported tags。
- [x] Round 189 补齐 native Telegram HTML 端到端缺口:
  - `<pre>` 中包着 Markdown pipe table 时,不再作为 native HTML 直通 Telegram;
  - 回退后仍走紧凑等宽表格 + `详情: /view 查看完整表格`,且 `/view` 不被 code block 吃掉;
  - mock Bot API payload golden 确认最终 `sendMessage` HTML 不含 raw `|---|`。
- [x] Round 191 修复真实 Telegram 表格块格式:
  - Channel 将连续、整行、仅以换行相邻的 code spans 合并为一个 `<pre>`;
  - 表格不再渲染成多个割裂的 `<code>`,行内 `/view` 仍保持 `<code>` 并位于表格块外;
  - 真实 Bot API 发送成功,Telegram Web DOM 确认为单个 `PRE > CODE`,客户端显示等宽对齐表格和复制控件;
  - Chrome Telegram Web 已可用 contenteditable DOM 路径发送真实命令,P-046 / B-007 的 UI tooling 阻塞已缓解。
- [x] Round 192 关闭真实 role agent 与表格验收缺口:
  - PATH 中 Codex CLI 从 `0.142.4` 升级到 `0.144.5`,同一全局 `gpt-5.6-sol` 最小调用返回成功,B-008 关闭;
  - 风险识别不再把“输出详情命令”这类展示文案误判成 shell 执行,但包含自然中文“执行”的真实操作仍需审批;
  - 表格末行后粘连的 `详情命令: /view` 会从表格列中分离,不再生成虚假的 `补充1`,且与自动详情提示去重;
    省略末尾 pipe 的真实额外列仍保留 `补充N` 兼容行为;
  - Telegram Bot API 对 TLS 建连 `ConnectTimeout` 仅重试一次,不重试 read/write timeout 或业务错误;
  - 真实 `/ask reviewer` 经 Telegram Web 入站、Codex Adapter、流式编辑和最终气泡完整通过,任务 `d7ac4939-...` 状态 done;
  - 最新 `ROUND192C` 气泡为四列单 `<pre>` 表格,无 `补充1`,块外仅一条 `/view`。
- [x] Round 193 修复短验收被多 Agent 协作链放大:
  - 新增 `/ask --exact <role> <task>`,一次性任务跳过 lead decision / Goal Brief 自动扩展;
  - prompt 明确“只输出本条”“不要请求协作”“do not delegate”等约束时自动启用 exact-output;
  - task metadata 写入 `aico.collaboration_mode=disabled`,即使 provider 仍输出 `@role`,也不会生成 child task 或 collaboration audit;
  - `/ask lead` / `/ask default` 解析到实际岗位时先显示 `Routing: lead -> <role> (<agent>)`,不再静默换岗;
  - P-044 从 OPEN 降为 MITIGATED,剩余 provider session busy 的老板可读降级另行收口。
- [x] Round 194 关闭 provider session busy 的原始错误泄漏:
  - 识别 `Session ID ... is already in use` 后,即时 IM 返回“Role is busy”与 `/tasks`、`/interrupt`、重试路径;
  - `/tasks`、`/audit`、`/inbox`、`/morning`、项目摘要和 aico-view 不再暴露 provider session id;
  - TaskBus snapshot / audit 与显式 `/task <id>` 保留原始错误,未知 provider 错误仍原样可见;
  - 选择可执行提示而非自动新建 session,避免静默丢失当前岗位的会话连续性;P-044 关闭。
- [x] 根据真实 Telegram 验收反馈修正策略:
  - Round 187 的纯字段列表虽然避免错乱,但人类不可读;
  - Round 188 改为“紧凑表格 + 截断 + /view 懒加载详情”。
- [x] 本地验证通过:
  - 相关链路:53 passed;
  - 全量测试:522 passed / 1 skipped;
  - mypy 通过;
  - touched-file Ruff check / format check 通过;
  - `git diff --check` 通过。
- [x] 真实 runtime 已重启到新代码,完成一条 Telegram Web 真实入站命令和一条确定性 Bot API 表格样例;
  验收后已停止 runtime,避免继续打扰。
- [x] `/ask reviewer` 真实 role agent 正文已通;Codex CLI/model 兼容问题已在 Round 192 解决并关闭 B-008。
- [x] Round 193 机器 Gate:新增 3 条 orchestration red-green E2E;相关回归 112 passed;
  full pytest 526 passed / 1 skipped;ruff、mypy、touched-file format、`git diff --check` 通过。
- [x] Round 194 机器 Gate:新增 provider busy 即时输出、恢复摘要、project/aico-view 脱敏与未知错误回归;
  相关回归 122 passed;full pytest 531 passed / 1 skipped;ruff、mypy、`git diff --check` 通过。
- [ ] 桌面 `/Applications/Telegram.app` 12.8 启动后约 0.1 秒主动以 exit 0 退出,无 crash report;
  数据库打开和网络握手已开始,但日志无明确 fatal。未冒险重置账号数据,当前使用 Web Telegram 兜底。

## 当前补充验收:热点叙事化 Memory + Dream Showcase

人类要求借助熟悉的热门动漫叙事来验证并宣传 AICO 的共享记忆和 `/dream` 候选经验能力,同时如果产品能力露怯,
要反哺优化自身。

- [x] Round 190 补齐 boss-absent candidate review 动线:
  - `/dream` 产出的 candidate experience 会进入当前项目 `/inbox` 的“经验候选”区;
  - `/morning` 早晨恢复摘要也会提示 `Experience candidates` 和 `/experience review`;
  - 老板/lead 同意时执行 `/experience promote <candidate-id> as <role>`,候选消失并变为 active,后续注入对应 role prompt;
  - 老板/lead 不同意时执行 `/experience archive <candidate-id>`,候选消失且不会注入 role prompt。
- [x] 新增芙莉莲式“长记忆旅队”case 文档:`docs/showcase/frieren-memory-dream-case.md`。
- [x] 新增鬼灭无限城式“作战会议”case 文档:`docs/showcase/infinity-castle-memory-dream-case.md`。
- [x] 新增中文测试验证报告:`docs/showcase/pop-culture-memory-dream-validation-report.md`,记录测评构建、执行命令、结果、
  分析、产品自省和后续宣传建议。
- [x] 新增机器 E2E:`tests/unit/test_pop_culture_memory_dream_showcase.py`,覆盖:
  - project shared memory 注入角色任务;
  - `/dream` 产出 `kind=experience` + `status=candidate`;
  - `/experience promote` 后经验进入 `Reusable experience` prompt layer;
  - 协作指令创建 reviewer child task 并写 `collaboration_requested` audit。
- [x] 产品自省修复:
  - `MemoryGovernor` 只把 `kind=fact` 放进 Shared memory packet,避免 promoted experience 同时混入 Shared memory 和 Experience layer;
  - `/dream` 下一步从 `/remember <accepted lesson>` 改为 `/experience review` + `/experience promote <candidate-id> as <role>`。
- [x] Round 190 验证通过:新增红灯先失败;showcase + inbox 5 passed;相关回归 101 passed;
  full pytest 516 passed / 1 skipped;mypy 通过;touched-file Ruff check / format check 通过;`git diff --check` 通过。
- [x] Round 185 验证通过:showcase 2 passed;相关回归 98 passed; full pytest 503 passed / 1 skipped; mypy 通过;
  ruff check 通过;touched-file format check 通过;`git diff --check` 通过。
- [ ] 后续如果用于公开传播,必须使用原创化“inspired-by”视觉和文案,不要使用官方截图、Logo、角色名做商业物料。

## 项目宏大叙事(一句话)

把开发者 Mac 上散落的 AI CLI 收编成一个可通过 IM 远程指挥的"虚拟公司",让老板不在电脑前时,AI 团队仍能异步推进、审批、叫停、交接和早报。

## 老板不在场假设

AICO 的产品边界是 absence-first:

- OMC 更像在浏览器里经营 AI 公司,CoWork OS 更像在桌面上做 AI super app;AICO 假设老板经常不在电脑前。
- IM 不是通知层,而是老板远程下达任务、查看状态、审批风险、叫停任务和接收早报的管理层。
- 本地 AI CLI 不是按钮集合,而是被任命到项目角色里的团队成员:lead、challenger、implementer、tester、reviewer 等。
- Phase 8 的 `/overnight`、operator inbox、morning handoff、lead decision、memory/audit/state 持久化,都服务于同一件事:老板离开 Mac 后,项目仍可推进且可接手。
- 新能力优先级先问 5 个问题:只靠 IM 能不能下达?离开后能不能推进?风险能不能等审批?早上能不能看懂?出问题能不能审计、叫停、恢复?

---

## 阶段地图

| 阶段 | 名称 | 状态 | 验收标准 |
|---|---|---|---|
| Phase 0 | 项目立项与文档体系 | 🟢 完成 | 文档体系建立,北极星确立 |
| Phase 1 | 核心协议与单 Adapter MVP | 🟢 完成 | 1 个 AI(Claude Code)能从 1 个 IM(Telegram)接收任务并返回结果 |
| Phase 2 | 多 Adapter + 状态机 | 🟢 完成 | 至少 2 个 AI 接入,状态可在 IM 中查询 |
| Phase 3 | 人格化层 + 群聊编排 | 🟢 完成 | AI 有差异化人设,群聊能 broadcast 任务 |
| Phase 4 | 审批与审计 | 🟢 完成 | 危险操作可推送审批,所有行为有 trace |
| Phase 5 | AI 间协作 | 🟢 完成 | AI 之间可以互相 @ 协作,任务编排成型 |
| Phase 6 | 可观测看板 | 🟢 完成 | 工时/KPI/token 消耗可视化 |
| Phase 7 | 共享记忆层 | 🟢 完成 | 所有 AI 共享上下文记忆 |
| Phase 8 | 离线托管模式 | 🟢 完成 | 睡前下任务,早上看结果 |

图例:🟢 完成 / 🟡 进行中 / ⚪ 未开始 / 🔴 阻塞

---

## 当前最高优先级:AICO Data-Agent Benchmark

人类在 2026-06-28 明确认可:复杂动态任务的终局是多 Agent 编排,而 AICO 的 `human-absent`
假设先进但当前不好用。后续要用“让 AICO 研发企业级 Data-Agent”作为产品体验和能力强弱的直观验收。

- [x] 新增 benchmark 契约文档:`docs/benchmarks/data-agent-aico-benchmark.md`。
- [x] 新增人类操作 SOP:`docs/human/data-agent-aico-sop.md`。
- [x] 新增 100 分评分卡:`benchmarks/data-agent/scorecard.md`。
- [x] 新增设计说明:`docs/superpowers/specs/2026-06-28-data-agent-aico-benchmark-design.md`。
- [x] 创建 `projects/data-agent-v1/` 和对应 AICO project config,定义 lead / architect / implementer / tester / reviewer / challenger。
- [x] 准备企业数据样例、20 条 golden eval 和 run evidence 目录。
- [x] 新增 deterministic Data-Agent V1 CLI / semantic layer / query engine / eval runner / tests。
- [x] 本地 gate 通过:targeted 7 tests passed, golden eval 20/20, ruff, mypy, full root pytest 478 passed / 1 skipped。
- [x] 新增 `projects/data-agent-v1/sample_data/enterprise_week_one/README.md`,用业务过程图、ER 图、表粒度、join key 和指标公式解释样例数据底层模型。
- [x] 新增 `benchmarks/data-agent/runs/2026-06-28-v1/scoring-brief.md`,并把三条人工验收问题、golden eval、Telegram 桌面可读性和 runtime 启动状态写入 evidence。
- [x] 创建挑刺子 agent 完成只读验收草稿:`benchmarks/data-agent/runs/2026-06-28-v1/ai-critic-scorecard-draft.md`,草稿分 AICO 4/50、Data-Agent 38/50。
- [x] 跑通 local injected IM baseline:`benchmarks/data-agent/runs/2026-06-28-v1/local-im-baseline-transcript.md`,覆盖 `/project`、`/team`、`/goal`、角色 asks、`/overnight`、`/morning`、`/inbox`、`/tasks`、`/view`;结果 20 sent / 9 edited / 3 Claude fake tasks / 6 Codex fake tasks / 27 audit events。
- [x] 将 scoring/operation 关键材料中文化,包括 `scorecard.md`、`human-scorecard.md`、`scoring-brief.md`、`aico-evidence.md`、`ai-critic-scorecard-draft.md`、`data-agent-eval.md` 和 `docs/human/data-agent-aico-sop.md`。
- [x] 新增 `benchmarks/data-agent/runs/2026-06-28-v1/ai-precheck-and-score.md`,完成非人类必要的客观验证、UX/审美初评和建议分:AICO 8/50 或严格 4/50,Data-Agent 38/50。
- [x] 新增 `benchmarks/data-agent/runs/2026-06-28-v1/human-remaining-actions.md`,把人类剩余动作压缩为确认 AICO 低分口径、确认 Data-Agent 产品分、填写 scorecard。
- [x] 复核真实 Telegram Web `@ai_co_telegram_bot` data-agent-v1 聊天记录并对照 `logs/aico.log`:真实 `/ask lead`、`/inbox`、`/view` 链路已跑通,但输出仍像后台 dump,出现 `Findings1.` 粘连、Markdown 表格/本地路径裸露、微型分片和 `/view` 附件缺上下文说明。
- [x] 修复 AICO IM 老板可读性第一切片:
  - agent 输出归一化拆分 `Findings1.`、`Missing Tests未...`、`Verdict:` 等粘连结构;
  - stream writer 避免接近上限时发送 3 字符/几十字符尾片;
  - `/inbox` 改为老板摘要,空状态不再展示一堆 `none` 和 audit dump;
  - `/view` 发送附件前先解释用途、替代命令和接手路径。
- [x] 新增回归测试覆盖真实 Telegram 坏样本:`tests/unit/test_native_output.py`、`tests/unit/test_streaming.py`、`tests/unit/test_inbox.py`、`tests/unit/test_view_snapshot_commands.py`、`tests/unit/test_orchestrator.py`。
- [x] 补齐 Round B/C:
  - stream writer 支持按 Summary / Findings / Decision / Risks / Next Actions 等老板语义卡片切分,卡片超长时再退回长度切分;
  - native output 将本地 Markdown 文件链接简化为 `path:line`,避免 Telegram 暴露 `/Users/...` 绝对路径;
  - 新增 `tests/unit/test_telegram_ux_regression.py`,集中回归真实坏签名:`Findings1.`、`.2.` 粘连、`Missing Tests未...`、本地路径链接和 Markdown 表格分隔符。
- [x] 修复真实 Telegram 抽样暴露出的二阶 UX 问题:
  - Markdown 表格统一降级为手机 IM 可读的 key-value 列表,不再保留裸 pipe 表格;
  - 兼容标题和 Markdown 表格粘在同一行的坏输出,例如 `本轮角色分工| 角色 | ... ||---|...`;
  - `/view` HTML 快照新增 `recent tasks` 区,从 task record payload / metadata 中抽取任务描述,并给出可点回 IM 的 `open /task <short-id>` 深链;
  - 已用真实 `.aico/data-agent-v1-state.db` 生成 `/tmp/aico-view-data-agent-v1-fixed.html`,确认任务卡含角色、适配器、状态、描述和深链。
- [x] 修复 data-agent-v1 真实 E2E 暴露的问题:
  - 表格 renderer 改为无裸表格策略:所有 Markdown 表格降级为字段列表;
  - malformed table 的额外列不再显示 `col 4`,改为老板可读的 `补充`;
  - Phase1 runtime 构建 `ProjectAssignmentDirectory` 时启用单项目默认 project,避免单项目 runtime 重启后第一次 `/ask` 仍要求 `/project`;
  - 普通测试目录默认不启用该恢复逻辑,避免多项目/显式选择场景被隐式污染。
- [x] 重新跑 `data-agent-v1` 真实 Telegram E2E sample:
  - 发送 4 条以内消息完成抽样,并在测试后停止 runtime;
  - 首条重启后直接 `/ask lead ...` 成功进入 data-agent-v1,未再出现 `No active project`,验证单项目默认 project 恢复生效;
  - 真实反馈表明 2 列小表格在 Telegram 中仍会错乱;Round 187 已改为所有表格降级为字段列表;
  - 4 列角色表在 Telegram 中继续降级为字段列表;
  - 行列不齐表格最终显示 `补充: 补充说明必须可读`,未出现新的 `col 4`;
  - 新暴露体验问题:短验收 prompt 仍会自动触发 challenger / reviewer / implementer 多任务链;`/ask lead` 可能路由到 reviewer/codex;provider session 并发时出现 `Session ID ... is already in use`;部分输出仍有 `今日验收 3 条要点1.`、`FindingsHigh:`、`Risks / approval need-` 粘连。
- [x] Round 193 修复 data-agent-v1 Telegram E2E 暴露的协作/路由问题:短格式验收已有
  `no-collab / exact-output` 通道,`/ask lead|default` 会给出实际 role / agent 路由说明;
  标题粘连由 Round 186-192 golden loop 覆盖。剩余 session busy 原始错误翻译继续列为下一轮。

## 当前高优并行:SME Agent 商业化冷启动

人类在 2026-06-23 明确:SME Agent 后续要面向淘宝/千牛售卖,并且现在就开始小红书发文、私信沟通、产品设计和 AICO 研发迭代并行推进。

- [x] 新增 SME Agent 商业化 launch kit,将第一周可卖形态定义为"AI 经营诊断服务",不是全自动 SaaS。
- [x] 新增 LLM/人类分工文档,把市场研究、内容、私信、数据录入、报告、审核和迭代拆到可执行责任边界。
- [x] 新增用户输入清单,明确需要淘宝/千牛页面、类目、店铺约束、样例数据、小红书账号和交付偏好。
- [x] 新增一周上线计划和小红书 7 天内容计划。
- [x] 不等待真实样例数据,新增电商 week-one 样例 CSV、交付 SOP 和样例诊断报告,用于商品页展示与内部交付演练。
- [x] 新增 SME Agent 商业化代码切片:CSV 加载、收入/退款/广告/库存指标计算、保守诊断规则和 Markdown 报告渲染。
- [x] 按默认价格 199 / 699 / 1999 RMB 完成可直接粘贴的淘宝/千牛商品页、详情页视觉文案包、小红书 7 篇正文和私信脚本。
- [x] 新增客户项目目录生成、evidence manifest 和脱敏字段扫描,让“证据链交付”和“数据安全边界”有代码支撑。
- [x] 新增 library runner 和报告生成 runbook,从 CSV 路径生成客户 workspace、诊断草稿、evidence manifest 和脱敏检查。
- [x] 新增淘宝/千牛静态 SVG 视觉资产:高级信任主图、痛点主图和详情页长图预览。
- [x] 导出淘宝 PNG 图、小红书 7 张封面 SVG/PNG,并完成产品质量审查:修复旧价格、低质感措辞、标签不一致和封面溢出。
- [x] 新增 SME Agent 行业模板能力,把直播/内容电商定义为第一严肃垂类:行业、卖家、内容、直播间、商品、订单、支付、GMV/支付 GMV/GPM/退款率/支付转化等指标,并预留本地生活和商业化广告扩展模板。
- [x] 新增直播电商闭环验证切片:中文平台导出表头映射覆盖率、拟真直播/订单样例、支付 GMV/GPM/退款率/支付转化确定性计算、人工复核报告和验收说明。
- [x] 新增公开网页来源 dogfood 数据包:基于 KuaiLive / OnlineGMV 公开来源形态和聚合信息构造缩放样例,写明非真实商家后台,并生成可验收诊断报告。
- [x] Round 195 新增 SME Agent 本地自助 CSV intake:
  - 商家可在浏览器选择或粘贴直播场次表与订单表,数据只进入 localhost 进程内存,该路径不持久化;
  - 缺字段或只有表头时只返回明确补数问题,不生成指标、finding 或付费报告;
  - 完整证据复用受治理的字段映射与确定性诊断,畸形/重复表头/超限输入稳定失败;
  - Chrome 实机覆盖缺证据和完整诊断,390 x 844 无横向溢出;SME full gate 44 passed。
- [x] Round 196 新增 SME Agent 不可变客户交付 run:
  - `sme-agent-live-commerce-deliver` 按 customer/run-id 写授权引用、mapping、补字段问题、脱敏检查、delivery status、SHA-256 evidence manifest 和条件式诊断;
  - 同 run ID 在写入前失败,避免重试覆盖旧证据;缺字段/无数据/直接个人信息风险都保留可接手 blocked artifact,不写诊断;
  - raw CSV 默认不保留,只有显式 opt-in 且 ready 时才复制;blocked run 即使 opt-in 也不复制;
  - 真实 CLI dogfood 生成 7 个交付 artifact、记录 2/7 行和输入指纹,确认 raw 目录为空;SME 50 passed,parent 544 passed / 1 skipped。
- [x] Round 198 新增 SME Agent 商家老板交付验收面:
  - workbench 用与 delivery runner 相同的 readiness/redaction 规则预览 6 个治理 artifact 和条件式诊断草稿,但不创建 workspace、授权记录或 raw CSV 副本;
  - `手机号` 等直接个人信息表头会进入 `blocked_redaction`,不再展示指标、finding、报告/复制按钮或商业验收控件;
  - 页面内 5 项 `199 RMB` 验收清单只保留当前页进度,自动化只验证交互,没有替老板勾选“愿意支付”;
  - desktop/390px mobile 的 ready/blocked Browser QA 无横向溢出、console 为空;SME 53 passed,parent 549 passed / 1 skipped。
- [x] Round 199 新增 boss-absent Lead 主动提案第一切片:
  - 项目配置可声明 objective、role、验收证据、停止条件和 cooldown 的 standing charter;
  - 项目空闲且 lead/challenger 团队完整时,`/inbox`、`/morning` 和定时早报最多生成一个持久化候选;
  - `/proposal accept <id>` 才创建正常项目任务并继续经过 TaskBus、风险审批、审计、记忆和中断链;reject 只记录原因并进入冷却;
  - 真实 SME 配置 + 临时 SQLite dogfood 证明候选跨重启存在且浏览候选不会执行任务;全量 `559 passed, 1 skipped`。
- [x] Round 200 新增 durable macOS runtime service:
  - 修复 `Phase1Runtime.start()` 在 non-blocking Channel 返回后立刻停止 morning scheduler 的生命周期错误;scheduler 现在持续到 runtime stop。
  - 新增原子、无秘密的 runtime heartbeat;只记录 state、PID 和时间,不把 `.env`、token 或 provider 配置复制进状态文件。
  - 新增 `aico-service render|install|restart|status|doctor|uninstall`,使用当前用户 LaunchAgent、崩溃重启、绝对路径、日志、可恢复 plist backup/Trash uninstall。
  - install/doctor 检查 macOS、checkout、venv executable、`.env` 0600、必需变量名及占位值;plist 只含 PATH/PYTHONUNBUFFERED。
  - 当前 checkout dry-run 如实返回 `.env` 缺失、plist/heartbeat 未安装;`render | plutil -lint -` 通过,未改真实 LaunchAgent。
  - 全量 `572 passed, 1 skipped`,SME `53 passed`,Ruff 和 mypy 通过。
- [x] Round 201 新增 runtime component health:
  - heartbeat schema v2 并发检查 active Channel、默认/可选 Adapter 和 enabled morning scheduler;每个检查有 timeout。
  - Channel、default Adapter、enabled scheduler 是 required,失败聚合为 `failed`;optional Adapter 失败只聚合为 `degraded`。
  - Telegram active polling task 意外结束时即使 `getMe` 可达也返回 FAILED;scheduler task 异常同样可见且 stop 安全消费异常。
  - durable service 按 `.env` 的 Channel 选择入口:Telegram 启动 `aico-phase1`,Feishu 启动 `aico-feishu-webhook`;两者共用同一 runtime+heartbeat lifespan。
  - install 在触碰 launchctl 前拒绝未知 Channel,避免错误 entrypoint 进入 restart loop。
  - heartbeat 只写 kind/name/required/status 和 checked_at;插件 exception、命令、target、URL、token/环境值不落盘。
  - doctor 区分 process stale、required failed、optional degraded、legacy health unavailable;synthetic health 不冒充 provider 登录或 IM E2E。
  - 全量 `588 passed, 1 skipped`,SME `53 passed`,Ruff 和 mypy 通过。
- [x] Round 202 新增 restart task reconciliation:
  - 新 TaskBus 接管持久化 SQLite 时,所有旧 `RUNNING` snapshot 在任何 read model 暴露前写回 `INTERRUPTED`。
  - recovery reason 明确“runtime restarted / execution ownership lost / 重试前核对外部副作用”,不声称底层 CLI 一定停止。
  - 每个本轮对账任务写一条 `TASK_INTERRUPTED` audit;再次重启不会重复对账或重复审计。
  - `WAITING_APPROVAL` 保持 pending 且仍走授权 reviewer;`DONE` 等终态保持不变;Adapter、risk、metadata、created time 全部保留。
  - `/inbox`、`/morning` 将 orphan task 展示为 recover/blocked,不再展示 ghost running;本轮不新增自动 replay/retry。
  - 全量 `590 passed, 1 skipped`,SME `53 passed`,相关 `177 passed`,Ruff 和 mypy 通过。
- [x] Round 203 新增 recovery audit transactional outbox:
  - SQLite schema v3 在一个 `BEGIN IMMEDIATE` transaction 内同时提交 `RUNNING → INTERRUPTED` snapshot 与完整不可变 recovery `AuditEvent`。
  - outbox 保存稳定 event id、task/trace、Adapter、risk、reason 和 timestamp;即使 snapshot 已 interrupted,未投递事件仍能在下次 startup 恢复。
  - `InMemoryAuditLog.record_existing()` 与内置 `JsonlAuditSink` 按 event id 幂等;同 id 不同内容直接报错,不会静默覆盖。
  - sink 成功后才标 delivered;sink 失败或 JSONL append 后尚未 ack 的 crash 均会重试同一 event,支持的单 runtime 路径最终只保留一行 JSONL。
  - outbox 只协调交付,不替代 SQLite business state 或 JSONL audit truth,也绝不 replay Adapter task。
  - 全量 `598 passed, 1 skipped`,SME `53 passed`,相关 `77 passed`,Ruff 和 mypy 通过。
- [x] Round 204 新增 single runtime ownership:
  - 同一 canonical state DB 派生同一个 `<db>.owner.lock`;未配置 DB 时使用当前 checkout `.aico/runtime-owner.lock`。
  - kernel `flock(LOCK_EX|LOCK_NB)` 在 task reconciliation 前获取,持有至 heartbeat、Channel、scheduler 全部停止后;process crash 自动释放。
  - `TaskBus.__init__` 不再抢先对账;正式 runtime 在 owner acquisition 后显式 `recover_startup_state()`。
  - 竞争 runtime fail closed,不等待、不 kill、不改 live `RUNNING`;原 owner 退出后替代者才能接管并做 orphan reconciliation。
  - lock metadata 仅含 schema/state/PID/time/resource;lock-file existence 不算 active owner。
  - `aico-service doctor` 校验 kernel owner PID 与 launchd PID,可识别 loaded-without-owner 和 manual-owner/launchd mismatch,避免假绿。
  - Telegram CLI 与 Feishu FastAPI 共用相同 lifespan;shutdown 顺序固定 heartbeat → Channel/scheduler → owner release。
  - 全量 `604 passed, 1 skipped`,SME `53 passed`,相关 `91 passed`,Ruff 和 mypy 通过。
- [x] Round 205 新增 bounded owned-task self-healing:
  - heartbeat 将 generic Channel/Adapter health 与本进程 owned-task liveness 分开;只有 Telegram polling 和 enabled morning scheduler 可触发恢复。
  - task 死亡时原地 restart,不重启进程、不重放业务 Task;单次 restart 最长 5 秒,存活 60 秒才清零。
  - 连续 3 次未稳定后熔断 15 分钟,冷却期间不 tight retry,到期后才开启下一轮有界尝试。
  - heartbeat schema v3 写 secret-free healthy/recovering/open、attempts 和 checked_at;doctor 对 recovering/open 分别 WARN/FAIL。
  - Telegram API/provider 或 fake external Channel 即使 health FAILED 也不会进入 supervisor;shutdown 后 restart 不会复活 task。
  - 全量 `616 passed, 1 skipped`,SME `53 passed`,相关 `71 passed`,Ruff、mypy、touched format、结构和 diff 检查通过。
- [x] Round 206 新增 durable out-of-band runtime alerts:
  - owned-task first open / active incident healthy 转成独立 incident_opened / incident_resolved;recovering 不误报 resolved。
  - active incident 与 immutable outbox event 在同一 SQLite transaction 写入,重复 heartbeat、coordinator rebuild 和 restart 不重复建单。
  - `RuntimeAlertSink` 插件隔离外部系统,generic HTTPS sink 发送 secret-free JSON 和稳定 `Idempotency-Key`;URL/token 只在进程内。
  - sink failure 保持 pending并持久化 1/5/15 分钟封顶退避;未到期/失败队首阻止 resolved 越序,HTTP accept-before-ack 重投同一 event id。
  - heartbeat schema v4 / doctor 区分 alerting disabled/healthy/pending/failed;启用 webhook 必须有 state DB 和 heartbeat loop。
  - SQLite schema v4 / `aico-state` 增加 runtime alert incident/outbox、pending count/reset;Task audit/outbox truth boundary 不变。
  - 全量 `631 passed, 1 skipped`,SME `53 passed`,Ruff、mypy、touched format、结构和 diff 检查通过。
- [x] Round 207 新增 external dead-man runtime liveness contract:
  - `RuntimeLivenessPublisher` startup 立即发送 stable runtime id + fresh boot id + sequence 1；失败只在内存保留
    同一 pulse/idempotency key有界重试,成功后才推进 sequence,不写 SQLite/outbox。
  - strict pulse 只含 schema/event、safe runtime/boot identity、sequence、sent_at、interval/TTL；URL、token、
    exception、hostname、路径和 arbitrary label 不进入 payload/heartbeat/log。
  - reference receiver tracker 必须显式 arm；从未收到首 pulse 或 acceptance-time TTL 到期只 open 一次,
    后续有效 pulse 只 resolved 一次；duplicate/out-of-order/旧 boot 不延期,explicit disarm 后不告警。
  - heartbeat schema v5 / doctor 区分 liveness disabled/healthy/degraded/failed；启用时强制 HTTPS transport、
    safe monitor id、pulse interval 不快于 heartbeat、TTL 至少三倍 interval。
  - 普通 stop/restart 不自动 disarm；永久 uninstall 前由 owner 在 receiver 显式 disarm。Mac sleep/网络分区
    超过 TTL 默认视为 unavailable。
  - 全量 `647 passed, 1 skipped`,SME `53 passed`,相关 `98 passed`,Ruff、mypy、touched format、结构和 diff
    检查通过；full-root format 仍只报告未触碰的既有 data-agent 文件。
- [x] Round 208 新增 deployable persistent dead-man receiver:
  - standalone FastAPI/CLI receiver 以独立 SQLite 保存 armed monitor、receiver acceptance-time expiry、active
    outage 和 immutable notification outbox；不共享 AICO Task/runtime state schema。
  - pulse/admin bearer 分离且强制不同；public health/readiness 不泄露 identity/endpoint/event,strict validation
    对错误请求只返回通用信息。
  - restart immediate reconcile、late recovery 原子 ordered open/resolved、duplicate/out-of-order 不延期；notification
    以稳定 event id 至少一次投递,持久化 1/5/15 分钟退避并保持 head-of-line。
  - AICO 改用专用 liveness URL/token/timeout；strict incident alert 与 pulse endpoint 不再因共用 HTTPS 而错误复用。
  - 新增 non-root `/data` Docker/Compose contract 与独立部署/arm/disarm/outage runbook；真实第二故障域部署仍在 B-012。
  - 全量 `667 passed, 1 skipped`,SME `53 passed`,receiver `18 passed`,Ruff、mypy(171 files)、touched format、
    structure、Compose config 和 diff 通过；本机 Docker daemon 不可用,未虚假声称完成 live image build。
- [x] Round 209 关闭 dead-man receiver worker 假健康:
  - `/healthz` 只表达 process/event-loop liveness；`/readyz` 同时要求 SQLite 和 expiry/delivery worker progress。
  - startup必须先完成 immediate coordinator pass；worker用 monotonic clock记录最近成功和连续内部失败,
    不把 wall-clock校时当进展证据。
  - 允许两个连续内部失败；第三次或三个 sweep interval无成功 pass时返回无细节 503,后续成功自动恢复。
  - downstream notification失败已进入 durable pending/backoff时仍算 worker推进,避免外部抖动触发 restart storm。
  - Compose继续探测 `/readyz` 并 `restart: unless-stopped`;worker progress不持久化,新 process不能继承旧健康。
  - 全量 `671 passed, 1 skipped`,SME `53 passed`,receiver `22 passed`,Ruff、mypy(171 files)、touched format、
    structure、CLI、Compose和diff通过；B-012仍只缺第二故障域真实部署与 outage样本。
- [x] Round 210 新增可导出、可离线验证的 dead-man outage evidence:
  - admin-only endpoint按最近完整outage group导出versioned bundle；pulse/public authority不能读取,disarm后历史仍在。
  - bundle只含safe runtime/current monitor、immutable open/resolved和local delivery attempts/next retry；不含
    URL、token、path、exception、request或operator note。
  - 按outage而非raw event截断,不会把resolved与其opened分离；export前先按receiver time补判expiry。
  - `aico-dead-man-evidence` 离线strict verify runtime、identity、chronology、open-before-resolved、delivery order、
    minimum complete outages和all-delivered,并输出artifact exact-byte SHA-256。
  - hash明确不是origin signature；valid bundle不冒充第二故障域、TLS或物理fault evidence,B-012仍保持external pending。
  - 全量 `678 passed, 1 skipped`,SME `53 passed`,receiver/evidence `29 passed`,Ruff、mypy(173 files)、touched
    format、structure、两条CLI、Compose和diff通过。
- [x] Round 211 新增主SQLite可执行恢复原语:
  - `aico-state backup`使用SQLite online backup API，允许live runtime生成transaction-consistent standalone artifact；
    output必须new path、`0600`、integrity/schema通过并返回exact-byte SHA-256。
  - `verify`以read-only immutable connection校验，不bootstrap/migrate；corrupt、wrong schema和hash mismatch fail closed。
  - `restore --expected-sha256 --yes`复用runtime owner lock，active owner拒绝；替换前生成verified pre-restore safety
    backup，再same-directory temp/fsync/atomic replace并在fence内清理WAL/SHM。
  - `reset --yes`也取得owner fence；JSON summary不含payload、secret、raw exception或source absolute path。
  - 全量 `685 passed, 1 skipped`,SME `53 passed`,targeted `9 passed`,Ruff、mypy(175 files)、touched format、
    structure、packaged CLI、Compose和diff通过；B-013继续跟踪off-device策略和业务restore exercise。
- [x] Round 212 新增non-invasive disposable restore drill evidence:
  - `aico-state drill`再次校验artifact expected SHA，在private temp中调用同一production restore primitive；
    CLI全局`--db`不会被打开、创建、lock或修改，live runtime可保持active。
  - materialized DB重新read-only验证schema/known-table counts；成功或失败都清理temporary DB、owner lock和sidecar。
  - optional report为`0600`、same-directory temp/fsync、atomic no-overwrite JSON，只含artifact basename、
    input/materialized SHA/size、schema/count和完成时间，不含payload/secret/exception/absolute path。
  - 全量 `688 passed, 1 skipped`,SME `53 passed`,targeted `12 passed`,Ruff、mypy(175 files)、touched format、
    structure、packaged real CLI、Compose和diff通过；B-013只剩off-device/full-asset/business restore evidence。
- [ ] 下一切片优先做浏览器辅助检查淘宝/千牛发布流;如果仍不能登录,则准备首发操作 checklist,不要先扩成通用 SaaS。
- [ ] 下一切片把直播电商诊断接入客户 workspace 交付 runner,并支持平台字段 override / 缺字段追问。
- [ ] 只有在需要真实发布/登录/类目选择/付款/授权时再要求人类介入。

## 近期高优产品方向

> 人类在 2026-05-07 明确:当前文档中的既有计划继续按进度推进,但近期要高优支持“更多可用 agents”和“更多 IM Channel”。

### A. Adapter 扩展:让 `/agents` 有更多真实成员

- [x] 新增 CodeFlicker Adapter MVP(可选启用、默认只读)。
- [x] 新增 Cursor Adapter MVP(可选启用、默认只读)。
- [x] Cursor / CodeFlicker 升级为审批保护下的完整 Adapter 能力(`code_edit` / `shell_exec`)。
- [x] 新增 Trae CLI Adapter(可选启用,完整能力走 AICO 审批门禁)。
- [x] 新增 Gemini CLI Adapter(可选启用,完整能力走 AICO 审批门禁)。
- [x] `/agents` / `/agent <agent>` 能展示这些新 Adapter 对应的可用 agent/persona,让 Telegram 里的“虚拟公司成员池”明显变丰富。
- [x] 保持可扩展可插拔:新增 Adapter 只能通过 `AIAdapter`、`AdapterRegistry`、persona/project 配置接入,不能在核心编排里写某个工具专属分支。
- [x] 为后续 OpenClaw 等 Adapter 留同样接入路径;先复制既有 Claude/Codex Adapter 模式,不要为了未来工具过早重构协议。
- [x] 进入实现前先做 CLI / API 形态核验,并补 Adapter mock 单测。
- [x] Cursor / CodeFlicker / Trae / Gemini 真实 smoke test。

### B. Channel 扩展:降低 Telegram 单入口依赖

- [x] 从飞书、钉钉、QQ、微信中选择 1 个先接入:优先飞书。
- [x] Feishu Channel 第一切片:文本发送、编辑/删除、URL verification、`im.message.receive_v1` 文本事件解析。
- [x] Feishu webhook runtime:新增 `AICO_CHANNEL=feishu`、`aico-feishu-webhook`、`/healthz` 和可配置事件回调路径。
- [x] Feishu 事件幂等:按 v2 `header.event_id` / v1 `uuid` 做本地 TTL 去重,避免平台重试重复触发任务。
- [ ] 选择优先级按对接成本和协议标准化程度决定:官方 Bot/OpenAPI 是否稳定、是否支持文本收发、消息编辑或动作回调、鉴权/回调部署成本、群聊可用性、真实 dogfooding 门槛。
- [ ] 先做最小文本收发 + 平台无关 render contract 映射;如果目标 IM 不支持编辑消息或 inline action,Channel 内部降级为新消息/纯文本动作提示,核心不感知平台差异。
- [ ] 暂不承诺四个 IM 全量支持;QQ/微信等非标准或高摩擦协议只有在成本可控、合规明确后再进入实现。
- [x] 新 Channel 必须实现 `IMChannel`,并用 mock HTTP/API 测试覆盖入站解析、发送、编辑/降级和回调/动作入口。
- [ ] Feishu 开放平台真实 URL verification / 端到端 smoke test。

### C. Open-source Showcase:让用户第一眼理解 AICO

- [x] 选定主 demo 为 Release Room:在 IM 中远程管理 AI 团队完成小型开源 CLI 的 v0.2 release。
- [x] 新增 `examples/release-room/notes-cli` 示例仓库,包含 v0.1 可用 CLI、v0.2 issue、状态文档、journal、release notes 草稿和 release contract tests。
- [x] 新增 `examples/release-room/aico-project.json`,把 pm / implementer / tester / reviewer / release-manager 映射为项目团队 appointment。
- [x] 新增 `docs/examples/release-room.md`、`docs/playbooks/release-room-demo.md`、demo script 和录屏 storyboard。
- [x] 新增配置回归单测,确认 release-room config 能被当前 project assignment 模型加载,并指向完整示例仓库。
- [x] Stage 2:用 fake adapters 跑 release-room 本地端到端 transcript,覆盖 `/team`、`/remember`、`/ask`、`/approve`、`/overnight`、`/daily`、`/tasks`、`/metrics`、`/audit`。
- [x] Stage 3 录屏准备:把 transcript 压成 30-60 秒 shot rhythm,并补 `ffmpeg` GIF 转换脚本。
- [x] Stage 3 真实 Telegram dogfooding 第一段:project office、team、project memory、interrupt 跑通;provider 输出问题已记录为 B-003。
- [x] Stage 3 Codex 输出清理:修复跨 provider session resume、role 改任命 session 复用和 CLI warning/HTML 噪音入镜问题;真实 Telegram dry run 可用。
- [x] Stage 3:真实 IM + Claude/Codex dogfooding 录屏,生成 README 首页可嵌入 GIF。
- [x] README GIF D0 复剪:新增 transcript-driven public GIF,`docs/assets/release-room-demo.gif`
  约 36 秒、`960 x 540`;Round 149 已把首帧 / social preview 改为明确 boss-absent 假设,
  并展示 `/morning` + `/view`。
- [x] GitHub social preview 资产生成:`docs/assets/social-preview.png`,`1280 x 640`,小于 1 MB,
  public 前需仓库 owner 在 GitHub UI 上传 / 确认(Round 148)。
- [x] 开源首屏第一版:英文主 README、中文 README、痛点/差异化/当前可用能力、Quickstart 状态修正、MIT License、SECURITY 和 issue templates。
- [x] 开源首屏第二版:同步 Cursor / CodeFlicker / Trae / Gemini smoke test 已完成状态,补安全模型图、今日使用场景和 GitHub publication 手动配置指南。
- [x] GitHub UI metadata 首轮配置验收:description、topics、social preview 已由人类在 GitHub UI 配置验证;
  public 前仍需仓库 owner 按 `docs/human/github-publication.md` 做最终复核。
- [x] 开源首屏第三版:新增无 token Release Room demo CLI、PR template 和 good-first-issue template。

---

## 当前进度详细

### Phase 0 进度

- [x] 北极星三句话确立
- [x] 文档体系骨架搭建
- [x] AGENTS.md / README.md / NORTH_STAR.md 三入口建立
- [x] journal 体系(ROUNDS / PITFALLS / BLOCKERS)初始化
- [x] 文档目录按 `docs/agent` / `docs/journal` / `docs/architecture` / `docs/human` 归位
- [x] 技术栈选型决策(ADR-0001:Python 3.11+ / FastAPI / asyncio / Pydantic v2)
- [x] 核心协议草案(Adapter 接口、IM 通道接口、任务消息格式)
- [x] 第一个 ADR(架构决策记录)输出
- [x] Python 工程基础设施(`pyproject.toml` / `uv.lock` / ruff / mypy / pytest)
- [x] CI 骨架(GitHub Actions 跑 pytest / ruff / mypy)

### Phase 1 进度

- [x] ADR-0002 Adapter / Channel 协议定稿
- [x] 最小 Router / TaskBus / Orchestrator 假链路
- [x] FakeChannel + FakeAdapter 端到端单测
- [x] Phase 1 MVP 范围 ADR / playbook 明确
- [x] Telegram Channel 文本 MVP
- [x] Claude Code Adapter MVP
- [x] Phase 1 本地启动入口
- [x] Telegram → 编排核心 → Claude Code → Telegram 真实链路验收

### Phase 2 进度

- [x] AdapterRegistry 多 Adapter 注册与按 persona 路由
- [x] `/status` 文本命令返回 Adapter 状态快照
- [x] Codex Adapter 文本 MVP(默认 read-only sandbox)
- [x] Telegram 中启用双 Adapter 后的真实状态查询验收
- [x] `/codex` / `@codex` / `codex:` 文本唤醒路由
- [x] 第二个真实 AI 任务链路验收
- [x] 更明确的任务状态机(running / done / failed / interrupted / rejected)

### Phase 3 进度

- [x] Phase 3 范围 ADR / Playbook
- [x] Persona 最小模型与注册表
- [x] `/broadcast <task>` 最小链路
- [x] Telegram 真实 persona / broadcast 验收
- [x] Persona 外部配置文件入口

### Phase 4 进度

- [x] Phase 4 范围 ADR / Playbook
- [x] 危险操作识别模型(`read_only` / `write_files` / `shell_exec` / `destructive`)
- [x] `waiting_approval` 任务状态
- [x] Telegram `/approve <task_id>` / `/reject <task_id>` 最小审批命令
- [x] 内存审计事件模型
- [x] `/audit` 最近审计事件只读查询
- [x] `/approve` / `/reject` 无 task id 快捷审批
- [x] 审批权限策略(默认 requester,可配置额外 reviewer)
- [x] Adapter 风险能力门禁(read-only Adapter 拒绝危险任务)
- [x] Claude Code 远程审批后免本机二次授权
- [x] `/audit` 多行可读输出
- [x] Telegram 真实审批 smoke test
- [x] 审计事件 JSONL 持久化

### Phase 5 进度

- [x] Phase 5 协作协议 ADR / Playbook
- [x] B-002 AI 间协作协议形态决策
- [x] 轻量 `@persona: request` 协作指令解析
- [x] Adapter 输出触发目标 persona 子任务
- [x] 协作任务审计事件增强
- [x] Agent Session / Harness 边界 ADR
- [x] Session 命令 MVP(`/sessions` / `/new` / `/use`)
- [x] Claude Provider Session Resume MVP
- [x] Codex `exec resume` 命令形态评估与 Adapter 构造支持
- [x] Telegram 流式输出 no-op edit 容错
- [x] Codex provider session 显式绑定命令(`/bind`)
- [x] Agent 能力体验命令(`/agents` / `/agent` / `/skills` / `/tools`)
- [x] Agent 能力体验命令 Telegram 真实验收(`/agents` / `/skills` / `/tools`)
- [x] `/agents` 默认展示改为工具入口名优先,避免岗位名和工具名混用。
- [x] `/agents` / `/agent` 输出追加短 Next 指导命令,引导查看详情、任命或创建 session。
- [x] Next 指导命令保留 Telegram 可识别的裸 `/command` 文本,避免富文本 code span 影响触碰发送。
- [x] Project Assignment Layer 设计决策(Agent / Project / Assignment)
- [x] 面向技术读者的架构图与核心概念工作流图(draw.io)
- [x] Project Assignment Layer MVP 第一切片(配置模型、项目命令、project-scoped session)
- [x] Project Team / Appointment 老板视角命令设计与 Role 体系完善
- [x] Project Team / Appointment 命令 MVP(`/project` / `/team` / `/who` / `/appoint` / `/ask` / `/lead`)
- [x] `/project` / `/team` 输出追加短 Next 指导命令,引导看 brief/team/next/daily/weekly、追问 role 或设置 lead。
- [x] Project roles view MVP(`/roles`)
- [x] Project roles view 紧凑化:默认只展示核心/专家岗位,详情进入 `/role <id>`,全量进入 `/roles all`。
- [x] `/roles` / `/role <id>` 输出追加短 Next 指导命令,引导查看 agent、appoint、ask、lead 或调整 scope。
- [x] Role proposal confirmation MVP(`/role propose` / `/role confirm` / `/role discard`)
- [x] Project unappoint MVP(`/unappoint`)
- [x] RoleTemplate / ProjectRoleOverride / Appointment 配置模型 MVP
- [x] Appointment Prompt Stack MVP
- [x] Project lead / role 普通咨询只按 `Current task` 做风险识别,避免 role prompt 中的 write/run 词误触发审批。
- [x] Project brief / risks MVP(`/brief` / `/risks`)
- [x] Project daily / weekly 本地报告 MVP(`/daily` / `/weekly`)
- [x] Project blockers MVP(`/blockers`)
- [x] Project next actions MVP(`/next`)
- [x] Project Team 本地验收流
- [x] Project appointment 同 role 去重与 `/team` lead 可见性
- [x] Project Team / Appointment Telegram 真实验收
- [x] Role proposal confirmation Telegram 真实验收
- [x] Orchestrator role proposal helper 拆分
- [x] Platform-neutral IM render contract 第一切片(`spans` / `actions`)
- [x] Project office key messages 使用 render hints
- [x] Telegram callback query 转入现有命令通路
- [x] Project status LLM summary MVP(`/brief` / `/risks` / `/blockers` / `/next`)
- [x] Project summary Markdown 转 render spans
- [x] Project report LLM summary MVP(`/daily` / `/weekly`)
- [x] Project status Facts 小节 / slash command render spans
- [x] IM 远程中断命令(`/interrupt`)
- [x] `/interrupt <task_id>` 可取消 `waiting_approval` 任务,用于清理未 approve/reject 的待审批项。
- [x] ProjectRoleCommandHandler 结构拆分
- [x] ProjectStatusCommandHandler 结构拆分
- [x] `/interrupt` Telegram 真实复验
- [x] `/blockers` Telegram 真实复验
- [x] Codex output idle timeout MVP
- [x] Project Facts bullet / inline Markdown render spans
- [x] Project Facts Markdown heading render spans
- [x] Task trace commands(`/tasks` / `/task`)
- [x] `/task` collaboration parent / child trace
- [x] Agent reply language command(`/language [en|zh]`):默认英文,可按 IM chat 作用域限制后续 agent 回复语言,不改变内置命令语言。
- [x] Phase 5 feature complete handoff
- [x] Telegram 真实协作 smoke test(人类确认真实 IM 下可触发;后续不再作为高优待办)
- [x] Prompt 分层渲染

### Phase 6 进度

- [x] ADR-0014 Phase 6 Observability Scope
- [x] IM-first `/metrics` MVP
- [x] MVP product entrypoints 判断(IM 主控 + macOS glance + CLI 排障)
- [x] Phase 6 `/metrics` smoke test playbook
- [x] ADR-0015 Observability Event Replay
- [x] audit JSONL 启动回放
- [x] `/metrics` audit-backed task snapshot 重建
- [x] MetricsReport 稳定查询模型(glance / summaries / token-cost 状态)
- [x] `aico-metrics` CLI text/json 排障入口
- [x] ADR-0016 Status Island and Usage Boundary
- [x] macOS Status Island / glance 数据原型(`aico-glance`)
- [x] token / cost usage 审计事件接入边界
- [x] Phase 6 无 token 本地验收样例:覆盖 `/metrics` live done / waiting approval / collaboration。
- [x] Phase 6 无 token 重启恢复验收:只从 audit JSONL 恢复 `/metrics` 历史指标。
- [x] Phase 6 无 token CLI/glance 验收:`aico-metrics` / `aico-glance` text+json 同源验证。
- [x] Phase 6 真实模型 token golden:Codex CLI 极简任务完成后验证 `/metrics` live、audit replay 和 `aico-metrics`。
- [x] `/metrics` Telegram 真实验收替代:无 token acceptance 覆盖 live `/metrics` 命令路径。
- [x] `/metrics` 重启后 Telegram 真实验收替代:audit JSONL replay acceptance 覆盖恢复路径。
- [x] 可观测状态持久化第一切片(audit replay)
- [x] Phase 6 集中真实验收通过后进入 Phase 7

### Phase 7 进度

- [x] ADR-0020 Phase 7 Shared Memory Scope
- [x] Phase 7 shared memory playbook
- [x] ADR-0021 Phase 7 记忆由 agent 主动维护,命令作为纠错和排障入口
- [x] ADR-0022 A2A Memory Fabric
- [x] A2A Memory Fabric 架构说明
- [x] MemoryAtom / MemoryStore 核心模型
- [x] JsonlMemoryStore 本地可审计记忆账本
- [x] `AICO_MEMORY_PATH` 配置入口
- [x] `/remember` / `/recall` / `/forget` IM 命令 MVP
- [x] Prompt Stack 读取当前项目少量高置信记忆
- [x] Boss feedback 自动抽取与 candidate 记忆 MVP
- [x] Team Broadcast 与 A2A memory refs 实验 MVP
- [x] Team Broadcast 可追踪审计:广播 receipt、source/broadcast memory、team scope、recipients 和 reason 写入 `memory_broadcasted` audit event。
- [x] 可解释记忆检索契约:MemoryRetrievalQuery / MemoryRetrievalHit、综合排序、token budget 和 `/recall` reason。
- [x] 记忆检索 graph / task-aware 升级:一跳 graph expansion、role/task query hints 和 `/recall` score 分项。
- [x] Phase 7 共享记忆本地验收流

### Phase 8 进度

- [x] ADR-0024 Phase 8 Offline Delegation Scope
- [x] Phase 8 offline delegation playbook
- [x] `/overnight <goal>` 离线托管工单 MVP
- [x] `/overnight` 当前项目托管工单查看
- [x] 托管工单复用当前项目 lead/default role、appointment prompt、memory 和 provider session
- [x] 托管工单危险动作继续走 `/approve` 门禁
- [x] Goal-mode 交互和 prompt 契约设计(ADR-0025 Accepted)
- [x] Goal-mode 支持 agent capability 分层:native goal / adapter sugar / managed Ralph loop。
- [x] Lead decision team contract Stage 1:强化 lead 决策责任、默认新增 challenger,并让 `/overnight` 要求 lead + challenger。
- [x] Memory purpose 标签:区分 public broadcast / task key progress / task private / decision review。
- [x] Lead decision workflow:决策类任务自动召回记忆、咨询 challenger/reviewer、输出 decision memo 并写 audit。
- [x] Goal Brief v0:`/goal` 和带明确验收/停止/证据 marker 的 `/ask` 可附加轻量目标契约,并在 `/task` 中可见。
- [x] SQLite task state store 第一切片:`AICO_STATE_DB_PATH` 可持久化 task records、task snapshots 和 pending approvals。
- [x] Core structure cleanup:B-004 已收口,`Orchestrator` / `TaskBus` 类体重新低于 500 行,命令分发函数低于 100 行。
- [x] 托管工单持久化与重启恢复:`AICO_STATE_DB_PATH` 可恢复 `/overnight` 最近托管工单列表。
- [x] SQLite 快速迭代治理:`aico_schema` metadata、`aico-state` inspect/reset 工具和 bool-like path 兜底。
- [x] 长静默 Adapter 任务 quiet heartbeat:provider 无 stdout 但进程仍运行时,IM 会显示 `Still running...`,并保留 `/interrupt` 与 idle timeout 兜底。
- [x] `/inbox` 当前项目老板收件箱第一切片:聚合待审批、running/failed/interrupted、离线托管、Goal Brief / lead decision 和协作 follow-up。
- [x] CLI Adapter 非交互 stdin 收口:子进程启动时显式 `stdin=DEVNULL`,避免 Codex 等待 inherited stdin 的额外输入。
- [x] CLI Adapter stderr drain:子进程运行期间持续读取 stderr,避免 Codex 运行日志写满 pipe 后反压阻塞 stdout。
- [x] ADR-0029 Phase 8 Absence Loop:把 actionable inbox、morning handoff、outcome grader、Dream/runbook memory 和 hybrid retrieval 固定为短期 sprint 队列。
- [x] Phase 8 Absence Loop playbook:每个 sprint 都有直接可问的 IM 验收路径和防跑偏护栏。
- [x] `/inbox` actionable 化第一切片:新增 First action,并把审批、running、失败恢复、handoff、Goal/decision、协作 follow-up 都渲染为可直接执行的下一步命令。
- [x] `/morning` 手动早报第一切片:按 active project 汇总 done、blocked、risks、overnight handoffs 和 next actions。
- [x] Outcome Grader 第一切片:Goal Brief 执行完成后自动派 tester / reviewer 验收,并把 grader task 标记为 `outcome_grader` follow-up。
- [x] `/dream` Dream/runbook memory 第一切片:从 waiting approval / running / failed / interrupted / rejected 任务生成 reviewable candidate memory,默认不注入 prompt。
- [x] Hybrid Memory Retrieval 第一切片:默认本地 scorer 从纯 semantic 升级为 exact phrase + phrase overlap + semantic alias fallback,保留 MemoryGovernor 边界。
- [x] Telegram native output pilot:`AICO_PREFER_NATIVE_CHANNEL_FORMAT=true` 时 agent 优先输出 Telegram HTML,验证失败自动回退 rich text。
- [x] Phase 8 Absence Loop 真实 IM dogfood 已由人类执行;效果不佳且暂不继续投入 native output 方向,当前 dogfood 使用 `AICO_PREFER_NATIVE_CHANNEL_FORMAT=false`。
- [x] 多 step / 多 agent 夜间自动编排安全切片:`/overnight` lead handoff 合格后自动派 challenger / reviewer checkpoint review,并保留审批、审计和 `Current task:` 风险边界(Round 164)。
- [x] 早报自动生成或定时推送安全切片:新增默认关闭的 morning push scheduler,按 `AICO_MORNING_PUSH_*` 配置把 `/morning` 同口径早报推送到指定 IM chat(Round 164)。
- [x] Sprint M1 — MemoryAtom 加 `kind=fact|experience` + `ExperienceMeta`;Dream 输出改为 candidate experience(Round 128)。
- [x] Sprint A1 — AuditEvent/Task/MemoryAtom 增加 `trace_id`;新增 `UnifiedEventIndex` 派生只读层;ADR-0030(Round 129)。
- [x] Sprint M2 — `/experience review|list|promote|archive` lead 内务命令;`prompt_stack` 加 ExperienceLayer;task metadata 写出 `aico.injected_experience_ids`;ADR-0031(Round 130)。
- [x] Sprint M3 — Outcome Grader `parse_verdict` + `apply_verdict_to_owner_experiences` 回写 confidence/hits/misses/injection_count;grader task trace_id 继承 owner trace_id(Round 131)。
- [x] Sprint A2 — boss-only `/undo` + `/why` + `/inbox` `/morning` 内嵌 Recent activity;ADR-0032(Round 132)。
- [x] Sprint V1 — `aico-view` 只读 FastAPI 三视图 + `aico-view` entrypoint;ADR-0033(Round 133)。
- [x] Sprint V2 — aico-view 三视图加 IM deep-link 按钮(Telegram `t.me/<bot>?text=`)+ Feishu cmd-copy 降级(Round 134)。
- [x] Sprint A3 — lead 内务 `/timeline` + `/rollback memory|experience|task`;新增 `ROLLBACK_PERFORMED` AuditEventType;ADR-0034(Round 135)。
- [x] Sprint V3 — `aico-view` `AICO_VIEW_TOKEN` 鉴权 + 部署文档(localhost / ngrok / Cloudflare);ADR-0035(Round 136)。
- [x] Sprint V4 — `AICO_VIEW_ENABLED=true` 启用 IM `/view` HTML 快照,通过 Telegram `sendDocument` 发送自包含只读文件,不启动本机 HTTP 服务;ADR-0036(Round 137)。
- [x] `/overnight` dogfood 修复:协作子任务用 `Current task:` 标记真实委托内容,避免 reviewer/Codex 因 parent context 中的 `git` / `run` 词被误判为 `shell_exec`(Round 138)。
- [x] `/overnight` handoff 完整性兜底:CLI exit 0 但输出过短或缺少 done/blocked/risks/next actions 时,任务改标 failed 并回 IM 提示不完整,避免半句输出伪装成成功(Round 139)。
- [x] Delegate agent 输出 IM 可读性兜底:流式 agent 结果进入 Telegram/native renderer 前会拆分粘连 `<b>Heading</b>`、已知 section label 和 `• High/Medium/...` 列表,避免 implementer/reviewer 结果糊成一整段(Round 141)。
- [x] `/overnight` 老板秘书动线:回执明确 now `/inbox`、morning `/morning`、exact trace `/task`、visual snapshot `/view`;`/aico-view` 作为 `/view` 别名;流式输出按 1400 字移动端阅读上限分段(Round 142)。
- [x] Dogfooding 验收分层:机器 Gate 先覆盖父子 agent 委派、handoff、render、命令和审计等确定性 contract;Agent 能访问本机 Telegram / provider 时先跑真实样本,人工 dogfood 只抽样确认体感和接手便利性(Round 143,Round 145 修正)。
- [x] Phase 8 human sample 前置 contract gate:在 `docs/playbooks/phase-8-absence-loop.md` 固化当前 41-test gate,覆盖父子委派、`/overnight` handoff、delegate 分片、老板动线、`/view` 附件上传和 Telegram long-poll timeout(Round 144-145)。
- [x] 本机真实 Telegram/provider 样本:Mac Telegram App 中 `ai_co` bot 可收发;`/project aico` 实回;真实 `implementer/claude-code` 输出触发 `source=implementer target=reviewer`,reviewer/codex 子任务完成;同时修复 Telegram long-poll 默认 timeout 太短导致的空 warning(Round 145)。
- [x] Release candidate 收口:README / release notes / no-token Release Room demo 已对齐 `/inbox` -> `/morning` -> `/task` 的老板接手动线;Phase 8 gate、full pytest、ruff、mypy 和 no-token demo 均通过(Round 146)。

### 开源 Demo 进度

- [x] Release Room Stage 1 static package:示例仓库、项目配置、playbook、demo script、录屏 storyboard。
- [x] Release Room Stage 2 local acceptance transcript。
- [x] Release Room Stage 3 recording rhythm and GIF conversion path。
- [x] Release Room Stage 3 real Telegram dogfooding first pass, with provider-output blocker recorded。
- [x] Release Room Stage 3 Codex provider-output cleanup and real Telegram dry run。
- [x] Release Room Stage 3 public GIF / README showcase。
- [x] Release Room README GIF D0 复剪:按 `examples/release-room/shot-rhythm.md` 展示
  `/morning` 和 `/view`,首帧直接进入 boss-absent 产品画面(Round 149)。
- [x] README 发布前事实审校:中英文 README 已收紧 Feishu 稳定性边界,避免把尚待生产
  smoke 的 Feishu Channel 写成与 Telegram 同等稳定公开入口(Round 150)。
- [x] README 展示面收口:移除 GitHub 发布页配置段,补充 `aico-phase1` 是长驻 runtime,
  并实际验证 README 中可运行命令和 Telegram 命令测试覆盖(Round 151)。
- [x] 中文传播文章包:按打工人共鸣 / 技术 lead 两个视角,分别产出博客园风格和小红书风格
  Markdown,并记录外部开源传播模式可借鉴点(Round 152)。
- [x] 博客园长文硬核化:按人类反馈重写共鸣版和技术 Lead 版,补齐痛点-解法对齐、领域建模、
  task/权限/跨 agent 委派/`/view`/Memory+Experience 的 why,并新增两张 draw.io XML 图(Round 153)。
- [x] 发布前 MCN 审稿:调整共鸣版博客园痛点优先级为长任务接手 / 局面压缩优先,补强日常代入感,
  并同步优化四篇文章的发布口吻、表格和小红书字数边界(Round 154)。
- [x] 中文发布素材索引:新增 `docs/launch/articles/README.md`,汇总四篇文章、draw.io 图源、发布顺序、
  口径检查、推荐标题和评论区应对,把中文内容分发从散文件变成可执行台账(Round 155)。
- [x] 中文发布社交图源:补齐痛点首图、boss-absent loop、项目 Lead 组织关系三张 draw.io XML,
  并接入 `docs/launch/articles/README.md` 图源清单(Round 156)。
- [x] 发布前事实与测试门禁复核:修复本机 dogfood `AICO_*` 环境变量污染 unit tests 的问题,
  重跑完整测试和 Phase 8 absence-loop gate,并校准 v0.1.0 release notes 的 rounds / pitfalls / Feishu
  稳定性口径(Round 157)。
- [x] Release readiness audit:新增 `docs/launch/readiness-audit.md`,把 no-token demo、完整本地测试、
  Phase 8 gate、ruff/format/mypy、GitHub Actions 最新 pushed main 状态、中文文章图源和公开 claim 边界汇总成
  发布前 Go / No-Go 台账;同步收紧 launch playbook 的 CI 口径和 release notes 的易漂移 rounds 数字(Round 158)。
- [x] Pushed CI coverage:release-readiness / 中文文章 / 测试隔离改动已提交并 push 到 `main`;
  pushed commit `958aa61` 的 GitHub Actions CI 已成功(Round 159)。
- [x] 中文文章发布前总审稿:按人类反馈把共鸣版博客园痛点叙事重排为“多 agent 调度成本 / 风险动作”
  优先,再到局面压缩、离开电脑、长任务接手和经验复用;同步优化技术 Lead 长文痛点-解法表、
  两篇小红书稿和文章索引,保持小红书 1000 字以内且不扩大 Feishu / `/view` 等公开承诺(Round 160)。
- [x] GitHub social preview 发布门禁机器化:新增 `aico-github-social-preview` 只读 CLI,
  用 GitHub `openGraphImageUrl` 下载当前 OG 图并识别疑似默认 repository card;当前 live check 返回
  `status: needs-owner-upload`,明确 tag / Release 前仍需 owner 上传 `docs/assets/social-preview.png`。
  同步更新 release notes / readiness / playbook 测试数为 `433 passed, 1 skipped`(Round 161)。
- [x] GitHub Actions Node 24 预检:CI job 设置 `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true`,
  提前验证 `actions/checkout@v4`、`actions/setup-python@v5`、`astral-sh/setup-uv@v5`
  在 GitHub 即将默认切换 Node 24 后仍能跑 release gate(Round 162)。
- [x] 中文文章发布前二次 MCN 复审:按人类最新反馈把共鸣版博客园 P1 改成早上接不上昨晚工作的生活化痛点,
  并明确 P3/P6、P2/P5、P1/P4 的叙事优先级;同步复审四篇文章的 AI 味、痛点-解法对齐、
  小红书字数和 Feishu / `/overnight` / `/view` 等公开口径(Round 163)。
- [x] Release Room no-token demo 发布前对齐 `/morning` 接手入口,避免公开 demo 继续教旧 `/daily` 路线(Round 146)。

---

## 上一轮做了什么

**Round 212**(2026-07-21,Codex — Disposable AICO state restore drill evidence):
- completion audit确认Round 211 `verify`只证明artifact可读，没有执行production restore materialization；不能写成
  “恢复演练通过”。同时审计否决直接auto-accept standing charter：morning target缺可靠boss requester identity，
  当前provider权限也不能靠read-only prompt证明不会写入。
- 新增`aico-state drill`：不接触live`--db`，在private temp中调用owner-fenced production restore、重新校验
  schema/table-count parity并在成功/失败后清理DB/lock/sidecar。
- optional evidence report采用`0600`、fsync和atomic no-overwrite publish，只投影bounded machine facts；existing/race
  不覆盖，payload、secret、raw exception和absolute path不进入report。
- 新增Goal Brief、ADR-0050、P-068并收窄B-013；更新architecture、absence playbook、quickstart、daily ops、
  troubleshooting和CHANGELOG。
- 机器Gate:`688 passed, 1 skipped`,SME `53 passed`,targeted `12 passed`,Ruff、mypy(175 files)、touched format、
  structure、packaged real CLI、Compose和diff通过；当前仍无off-device/full-asset/business restore exercise。

**Round 211**(2026-07-21,Codex — Owner-fenced AICO state backup and restore):
- completion audit确认主SQLite虽已持久化业务状态，但daily ops备份/恢复仍为空注释；raw copy会遗漏WAL，
  active runtime restore/reset会破坏owner边界。
- 新增`aico-state backup|verify|restore`：online backup生成一致单文件，read-only verify校验integrity/schema/SHA，
  restore先验证expected SHA并拒绝active owner。
- restore替换前创建verified timestamped safety backup，通过same-directory temp、fsync和atomic replace恢复，
  stale WAL/SHM只在owner fence内清理；reset也纳入同一fence。
- 新增Goal Brief、ADR-0049、P-067、B-013并更新architecture、absence playbook、quickstart、daily ops、
  troubleshooting和CHANGELOG；明确主SQLite之外资产和off-device DR不在本轮claim内。
- 机器Gate:`685 passed, 1 skipped`,SME `53 passed`,targeted `9 passed`,Ruff、mypy(175 files)、touched format、
  structure、packaged CLI、Compose和diff通过；当前仍无`.env`/真实安装/独立receiver/off-device restore drill。

**Round 210**(2026-07-21,Codex — Exportable dead-man outage evidence):
- completion audit确认B-012真实验收仍依赖通知截图/直查SQLite,缺少可移植、bounded、机器可复核的evidence projection。
- 新增admin-only `/v1/monitors/{runtime_id}/evidence`,按最近完整outage分组导出monitor、open/resolved和local
  delivery/retry事实；export先补判receiver-time expiry,disarm不删除immutable evidence。
- 新增strict evidence models与invariants:unique outage/event、chronological open→resolved、resolved delivery不越过
  opened、生成时间不早于detection；extra字段fail closed。
- 新增offline `aico-dead-man-evidence`:不联网、不接token,可要求runtime、最低complete outage和all-delivered,
  输出compact JSON与artifact精确字节SHA-256。
- 新增Goal Brief、ADR-0048、P-066并更新B-012、architecture/playbook/ops/troubleshooting/deploy docs。
- 机器 Gate:`678 passed, 1 skipped`,SME `53 passed`,receiver/evidence `29 passed`,Ruff、mypy(173 files)、
  touched format、structure、两条CLI、Compose和diff通过；真实independent host/TLS/fault exercise仍未伪造完成。

**Round 209**(2026-07-21,Codex — Dead-man receiver worker readiness):
- 完成度审计发现 `/readyz` 只 ping SQLite；expiry/delivery worker持续内部失败时仍返回 200,observer会二阶假健康。
- 新增 process-local `ReceiverWorkerHealth`:startup immediate pass建立初始证据,后续用 monotonic elapsed和连续失败
  判断 progress；第三次内部失败或三个 sweep interval无成功 pass时 fail closed。
- `/healthz` 保持 process liveness；`/readyz` 对 DB/worker failure只返回通用 503,不泄露异常、路径、monitor/event
  或 endpoint。恢复 pass会重置 failure并重新 ready。
- durable downstream notification pending/backoff仍算 coordinator pass成功,不会把外部 endpoint抖动变成容器
  restart storm；Compose现有 ready probe和restart policy形成无人值守恢复闭环。
- 新增 Goal Brief、ADR-0047、P-065并更新 B-012、architecture/playbook/ops/troubleshooting/deploy docs。
- 机器 Gate:`671 passed, 1 skipped`,SME `53 passed`,receiver `22 passed`,Ruff、mypy(171 files)、touched
  format、structure、CLI、Compose和diff通过；真实第二故障域/TLS/owner sink/outage sample仍未伪造完成。

**Round 208**(2026-07-21,Codex — Deployable persistent dead-man receiver):
- 将 Round 207 的 in-memory reference tracker 收口为独立 FastAPI/CLI 服务；专用 SQLite 持久化 monitor、outage
  与 immutable notification outbox,receiver restart 后立即补判 expiry 并续投 pending event。
- 冻结 admin/pulse 双 authority、receiver acceptance-time TTL、same-TTL idempotent arm、different-TTL conflict、
  explicit disarm、duplicate/out-of-order no-extension 和 atomic late-recovery open/resolved contract。
- notification sink 使用稳定 event id / `Idempotency-Key`、严格队首顺序与持久 1/5/15 分钟退避；数据库 transaction
  failure 测试证明 monitor/outage 与 event intent 不会分裂。
- 修正 Round 207 transport 假设：新增专用 liveness URL/token/timeout；incident-alert 与 pulse strict wire protocol
  分离,并用 sender → receiver ASGI integration 证明兼容边界。
- 新增 non-root `/data` Docker/Compose contract、独立部署/arm/status/disarm/outage runbook、Goal Brief、ADR-0046、
  P-064；B-012 只剩第二故障域/TLS/owner endpoint 和真实 kill/launch-failure/network 样本。
- 机器 Gate:`667 passed, 1 skipped`,SME `53 passed`,receiver `18 passed`,Ruff、mypy(171 files)、touched format、
  structure、CLI、Compose config 和 diff 通过；Docker daemon 当前不可用,只声明 static container gate。

**Round 207**(2026-07-21,Codex — External dead-man runtime liveness):
- 审计确认 durable incident webhook 仍依赖 Python event loop,无法在 launch failure、整进程或整机失联时自报。
- 新增 strict secret-free pulse、独立 `RuntimeLivenessSink` / HTTPS sink 和 stable `Idempotency-Key`;按 Rule of Three
  保持与 alert webhook 的两份窄实现,不提前引入 generic webhook framework。
- publisher 每个 process 使用 fresh boot id并立即发送 sequence 1；failed delivery 保留同一内存 pulse bounded retry,
  最近成功在 TTL 内为 degraded,从未成功或 TTL 到期为 failed；没有 durable pulse history。
- 新增 receiver reference tracker:explicit arm/disarm、首次 pulse 缺失、acceptance-time TTL、single open/resolved、
  duplicate/out-of-order/replacement boot 机器契约。
- heartbeat 升为 schema v5,执行顺序固定 recovery → incident alert → liveness pulse → component health；本机状态
  只作 publisher 诊断,不冒充外部 monitor truth。
- settings/doctor 强制 HTTPS、safe monitor id、interval/TTL bound并保持 secret-safe；正常 stop 不 auto-disarm,
  Mac sleep/网络分区超过 TTL 保守判 unavailable。
- 新增 Goal Brief、ADR-0045、P-063；B-012 收窄为独立 receiver 部署、持久 monitor state 与真实 outage sample。
- 机器 Gate:`647 passed, 1 skipped`,SME `53 passed`,相关 `98 passed`,Ruff、mypy、touched format、structure 和
  diff 通过；当前 checkout doctor 仍如实报告 `.env` missing、plist/owner/heartbeat 未安装。

**Round 206**(2026-07-21,Codex — Durable out-of-band runtime alerts):
- 审计拒绝 heartbeat 每轮直接 POST 和复用 primary Channel:前者会告警风暴/越序,后者没有独立失效域。
- 新增 runtime alert incident/outbox,first open 与后续 healthy 原子记录且跨进程去重;recovering 保持 incident active。
- 新增 `RuntimeAlertSink` + vendor-neutral HTTPS实现,稳定 event id 同时作为 payload identity 与 `Idempotency-Key`。
- sink failure 不 ack,按持久化 1/5/15 分钟退避并保持 head-of-line;accept-before-ack 只会重投同一 immutable event。
- heartbeat 升为 schema v4,alerting disabled/pending/failed 对 doctor 分别可见；未配置 endpoint 不冒充 fully healthy。
- webhook URL/bearer 使用 SecretStr,启用时强制 HTTPS、state DB 和 heartbeat；service readiness 只输出 key/状态,不泄漏 value。
- 新增 Goal Brief、ADR-0044、P-062；B-011 收窄为 owner endpoint/真实样本，新增 B-012 跟踪整个 runtime/Mac 失联的 dead-man 盲区。
- 机器 Gate:`631 passed, 1 skipped`,SME `53 passed`,Ruff、mypy、touched format、structure 和 diff 检查通过。

**Round 205**(2026-07-21,Codex — Bounded owned-task self-healing):
- 审计确认 `HealthStatus.FAILED` 同时包含本地 task 死亡和外部 dependency failure,不能直接驱动 restart。
- 新增 app-layer `BoundedOwnedTaskSupervisor`,以 5 秒 restart timeout、60 秒稳定期、3 次上限和 15 分钟 cooldown 监督本进程直接拥有的 task。
- Telegram polling 与 morning scheduler 显式提供 liveness/restart,安全消费旧 task 异常且 shutdown 后拒绝复活;live task 不会重复创建。
- Runtime heartbeat 先恢复 owned task 再执行 component health,并升级 schema v3;recovering/open 可由 heartbeat/doctor 看到,异常 detail 不落盘。
- generic external Channel/Adapter failure 不进入 supervisor,避免 API/provider 抖动被放大成 crash-loop;业务 Task 不自动 replay。
- 新增 Goal Brief、ADR-0043、P-061 和 B-011;当前剩余关键缺口是熔断后的 second-channel/out-of-band notification。
- 机器 Gate:`616 passed, 1 skipped`,SME `53 passed`,相关 `71 passed`,Ruff、mypy、touched format、structure 和 diff 检查通过;full-root format 仍只有既有 data-agent 文件。

**Round 204**(2026-07-21,Codex — Single runtime ownership):
- 审计确认 Round 202/203 的 single-runtime 假设未被代码强制;第二个 terminal/LaunchAgent/webhook 可误中断第一 owner 的 live task。
- 新增 app-layer `RuntimeOwnerLock`,按 canonical state DB 派生 lock path,用 kernel advisory lock 持有完整 runtime lifetime;stale metadata 不阻塞 crash recovery。
- recovery 从 TaskBus 构造期延迟到 Phase1 start 的持锁区间;竞争者在任何 SQLite mutation、scheduler 或 Channel start 前失败。
- 修正 shutdown race:heartbeat 必须先停止,再停 Channel/scheduler,最后 release owner,避免旧 heartbeat 覆盖新 owner 状态。
- doctor 将 launchctl PID 与 owner PID 对齐;manual owner 占锁但 launchd loaded/crash-loop 时不再显示健康。
- 真实多进程 dogfood:竞争者 rejected 时 state 保持 running;强杀 owner 后替代者取得 lock 并把 orphan state 收口 interrupted。
- 机器 Gate:`604 passed, 1 skipped`,SME `53 passed`,相关 `91 passed`,Ruff、mypy、touched format、structure 和 diff 检查通过;真实 install/IM 仍由 B-010 跟踪。

**Round 203**(2026-07-21,Codex — Recovery audit transactional outbox):
- 审计发现 Round 202 仍有 SQLite snapshot commit → JSONL append 的顺序双写窗口:两步之间 crash 会永久丢恢复审计。
- SQLite schema v3 新增专用 recovery outbox;同一 transaction 写 interrupted snapshot 和完整 `AuditEvent`,失败 trigger 回归证明两者一起 rollback。
- TaskBus startup 投递 pending event,成功后才 ack;失败 sink 保留 intent,下一次启动使用相同 event id 重试。
- 内存 audit 与内置 JSONL sink 建 event-id index,同事件 no-op、碰撞报错;startup 一次扫描,正常 append/去重为 O(1)。
- Phase1 连续两次真实组装和临时 append-before-ack crash dogfood 均得到 `interrupted`、audit_count=1、pending_outbox=0。
- 机器 Gate:`598 passed, 1 skipped`,SME `53 passed`,相关 `77 passed`,Ruff、mypy、touched format、structure 和 diff 检查通过;真实 install/IM 仍由 B-010 跟踪。

**Round 202**(2026-07-21,Codex — Restart task reconciliation):
- 审计确认 LaunchAgent crash restart 后,SQLite 会原样恢复 `RUNNING`,但新进程没有旧 Adapter subprocess、stdout stream 或 interrupt handle,会形成永久 ghost running。
- `TaskStateRepository` 在加载持久化状态后立即把旧 `RUNNING` 写回 `INTERRUPTED`;确定性原因要求先核对外部副作用再提交新任务。
- `TaskBus` 为每个本轮恢复项记录 `TASK_INTERRUPTED`;JSONL sink 回归证明第二次重启不会重复写审计。
- 待审批任务继续 pending,终态不变;恢复保留 task record、Adapter、risk、metadata、created time 和 trace 来源。
- `/inbox`、`/morning` 恢复视图不再把 orphan task 当作运行中;ADR-0040 明确拒绝无幂等/副作用契约的自动 replay。
- 临时 SQLite + JSONL dogfood 证明首次 owner `running → interrupted` 且 audit count=1,第二次 owner 不重复审计。
- 机器 Gate:`590 passed, 1 skipped`,SME `53 passed`,相关 `177 passed`,Ruff、mypy、touched format、structure 和 diff 检查通过;真实 install/IM 仍由 B-010 跟踪。

**Round 201**(2026-07-21,Codex — Runtime component health):
- 审计确认 Round 200 heartbeat 仍可能假健康:Python process/heartbeat task 活着时,Telegram polling、默认 Adapter 或 morning scheduler 可能已不可用。
- 新增 app-layer `RuntimeHealthProbe`,复用现有 plugin `health_check()` 并发收集,每组件 timeout;没有修改 Adapter/Channel protocol。
- heartbeat 升为 schema v2;required failure → FAIL,optional Adapter failure → WARN/DEGRADED,legacy component data missing → WARN。
- Telegram health 现在检查 active polling task ownership;Telegram/scheduler stop 会消费异常并只记录异常类型,不扩散潜在敏感 detail。
- 修复 Feishu 常驻入口错配:`aico-service` 现在按 Channel 选择 webhook entrypoint,Feishu FastAPI lifespan 与 Telegram CLI 共用 runtime heartbeat supervisor。
- heartbeat 在 runtime components 启动成功后才启动,避免 startup window 误报;health exception/timeout 只写脱敏 FAILED。
- 机器 Gate:`588 passed, 1 skipped`,SME `53 passed`,相关 `97 passed`,Ruff、mypy、touched format、structure 和 diff 检查通过;真实 install/IM 仍由 B-010 跟踪。

**Round 200**(2026-07-21,Codex — Durable macOS runtime service):
- 发现并修复 morning scheduler 伪常驻:Channel `start()` 返回后旧 `finally` 会立即 stop scheduler;现在 scheduler 只在 runtime stop 或启动失败时清理。
- 新增 secret-free 原子 heartbeat 和健康判定,运行态写 fresh/stale/stopped,doctor 不输出任何环境变量值。
- 新增 macOS user LaunchAgent operator CLI,覆盖 render/install/restart/status/doctor/uninstall;plist 使用 absolute venv/repo/log path、RunAtLoad 和 crash-only KeepAlive。
- 安装前拒绝缺失/宽松权限/占位 `.env`;替换 plist 留 `.previous`,卸载移入 Trash;未引入跨平台 service 抽象或云部署。
- 真实 checkout dry-run 证明当前尚无 `.env`、plist、heartbeat,所以没有冒充端到端常驻已通过;未执行真实安装或 launchctl mutation。
- 机器 Gate:`572 passed, 1 skipped`,SME `53 passed`,Ruff、mypy、touched format、structure、plist lint 和 diff 检查通过;full-root format 仅保留既有 data-agent 文件问题。

**Round 199**(2026-07-21,Codex — Lead standing-charter proposal queue):
- 将 Future F-1 收敛为显式 standing charter → reviewable candidate → boss accept 三段式,ADR-0037 明确“提议权不等于授权”。
- `/inbox`、手动/定时 `/morning` 在项目空闲且团队完整时刷新最多一个候选;审批、失败、运行中和夜间交接仍优先。
- 新增 `/proposals`、`/proposal accept|reject`;accept 才走既有 project role/TaskBus/risk/approval/audit/memory/interrupt 链,reject 不建 task。
- proposal 状态进入 SQLite schema v2,支持重启恢复和 state reset;SME 配置新增商业证据 standing charter 及外部动作/支付/真实数据停止条件。
- 机器 Gate:真实 SME 配置 SQLite dogfood、全量 `559 passed, 1 skipped`,Ruff、mypy、format、structure 和 diff 检查通过。
- 真实 Telegram 未伪造完成:当前运行态/凭据不可用,且浏览器策略明确禁止使用 Telegram Web;Round 200 后统一由 B-010 跟踪真实常驻和客户端样本。

**Round 198**(2026-07-21,Codex — SME Agent merchant-owner delivery acceptance):
- 在不连接持久化 runner 的前提下,把不可变客户交付契约预览到本地 workbench:ready 时列出 intake、mapping、questions、redaction、manifest、status 和 diagnosis 7 项。
- 复用 delivery runner 的 readiness/redaction,修复 direct PII 仅有警告文案但仍能展示/复制付费报告的风险;`blocked_redaction` 现在完整压制商业输出。
- 新增 5 项页面内 `199 RMB` 验收清单;只验证了 1 项进度交互,“是否愿意支付”明确留给真实商家老板,且页面不持久化任何决定。
- Browser 实机覆盖桌面/390px mobile 的 ready 与 `手机号` blocked 两态,无横向溢出、console 为空。
- TDD 新增 preview/privacy/UI contract;SME `53 passed`,parent `549 passed / 1 skipped`,Ruff、strict mypy、SME format、structure 和 diff 通过。
- full-root format 仍只报告未触碰的既有 `projects/data-agent-v1/src/data_agent_v1/engine.py`;同步更新 Goal Brief、README、runbook、P-005、两级 STATUS/ROUNDS 和 handoff。

**Round 197**(2026-07-21,Codex — aico-view project-scoped Boss Brief):
- `/view <project>` 第一屏已从通用事件统计改为审批、阻塞、运行中、夜间托管四类老板注意力,并按 approval → blocker → running → overnight → quiet 稳定给出唯一 First action。
- 审批卡直接提供 `/approve`、`/reject`、`/task`;阻塞和夜间交接卡给出任务回看入口,原 recent tasks / Timeline / Trace / Memory 下沉为证据层。
- 修复项目附件可能混入其它项目 task/audit 的隔离风险;task、audit、memory、overnight 现在都按目标 project 投影后再生成 HTML。
- 新增 2 条 red-green 场景并扩展既有 snapshot tests;定向 22 passed,完整 `546 passed / 1 skipped`,Ruff/mypy/structure/diff 通过。
- touched-file format 通过;full-root format 仍只报告本轮未触碰的既有 `projects/data-agent-v1/src/data_agent_v1/engine.py`,未扩大范围顺手修改。
- Browser 插件拒绝打开本地 `file://` attachment;按安全策略未用 localhost/其它浏览器绕过,真实 desktop/mobile screenshot 证据记录为 B-009,不冒充已通过。

**Round 196**(2026-07-21,Codex — SME Agent immutable customer delivery runs):
- 把 Round 195 的临时浏览器 intake 接成可审计客户交付能力:每次诊断使用唯一 customer/run-id,不再复用一个会被覆盖的报告路径。
- runner 强制记录 authorization reference,并为 ready/blocked 两类结果都写 mapping、questions、redaction、manifest 和 status;只有 ready 才写诊断。
- evidence manifest 新增源文件 SHA-256、行数、raw retention 状态;raw 默认不保留,个人信息/缺字段/无数据时禁止复制。
- 新增 6 条 red-green 测试、CLI、runbook、ADR-0003 和 P-004;SME 50 passed,parent 544 passed / 1 skipped,Ruff/mypy/SME format/structure/diff 通过。
- 真实安装后的 CLI 样本生成完整 run-scoped workspace 并确认 `RAW_NOT_RETAINED`;full-root format 仍只报告未触碰的既有 data-agent 文件。

**Round 195**(2026-07-21,Codex — SME Agent self-serve local intake):
- 商家可在本地工作台选择或粘贴两份脱敏 CSV;localhost intake 只在内存分析,该路径不写客户 workspace 或日志。
- 先做受治理字段映射和 row readiness:缺字段/只有表头只返回补数问题,完整证据才复用确定性指标、finding、human checks 和报告。
- TDD 增加 intake service、HTTP/UI contract 和边界回归;SME `44 passed`,parent `538 passed / 1 skipped`,Ruff check、mypy、SME format、diff check 通过。
- Chrome 实机验收缺证据与完整报告两条路径;390 x 844 无横向溢出。full-root format 仍只报告本轮未触碰的 `projects/data-agent-v1/src/data_agent_v1/engine.py`,未扩大范围顺手修改。
- 下一本地产品切片是 live-commerce customer workspace runner;真实客户数据、平台语义和外部发布继续停在人类授权边界。

**Round 194**(2026-07-21,Codex — provider session busy boss recovery):
- 关闭 P-044:provider session 并发失败不再把 `Session ID ... is already in use` 原样发送给老板。
- 即时 IM 返回 role busy、查找运行任务、等待或中断、重试和显式详情路径;老板恢复面与 aico-view 使用同一安全摘要。
- 原始诊断仍保存在 TaskBus snapshot/audit 和显式 `/task`;未知错误维持原样,没有以“友好提示”为名吞掉故障证据。
- TDD 红灯先复现即时输出和各恢复面泄漏;修复后相关回归 122 passed,full pytest 531 passed / 1 skipped,
  ruff、mypy、diff check 全绿。
- 未自动创建 provider session:该策略会静默切断岗位连续上下文;本轮选择最小、安全、可操作的老板提示。
- 因没有针对 AICO bot 发送外部测试消息的明确授权,未发送真实 Telegram 样本,不把机器 Gate 冒充真实 IM 证据。

**Round 193**(2026-07-21,Codex — exact-output / no-collab contract):
- 关闭 P-044 的主要产品缺口:新增 `/ask --exact`,并识别“只输出本条/不要请求协作/do not delegate”等自然语言约束。
- exact-output 会形成持久 task metadata,跳过 lead decision / Goal Brief 自动扩展,且流式输出中的 `@role` 不会派生 child task。
- `/ask lead|default` 解析到实际岗位时,IM 先显示 role / agent 路由,避免老板以为任务仍由抽象 lead 身份处理。
- TDD 红灯先复现“flag 无法解析”“自然语言仍产生两个任务”“lead exact 进入决策链”;修复后相关回归 112 passed,
  full pytest 526 passed / 1 skipped,ruff、mypy、touched-file format、diff check 全绿。
- Chrome 只读检查确认 Telegram Web 有登录态,但当前页不是 AICO bot;因本轮没有针对发送外部测试消息的明确授权,未伪造真实 IM 证据。
- P-044 标为 MITIGATED;剩余 provider session busy 错误翻译为老板可执行提示。

**Round 175**(2026-06-28,Codex — Data-Agent AICO Benchmark):
- 人类认可用“当前 AICO 编排 Claude/Codex 多角色团队研发企业级 Data-Agent”作为 AICO 产品体验验证母题。
- 新增 `docs/benchmarks/data-agent-aico-benchmark.md`,把 benchmark 定义为 baseline v1 → 人类评分 → AICO 优化 → v2 复测的周期性产品基准。
- 新增 `docs/human/data-agent-aico-sop.md`,把老板侧操作收敛到 `/project`、`/team`、`/goal`、`/ask challenger`、`/overnight`、`/morning`、`/inbox`、`/view`、`/task`。
- 新增 `benchmarks/data-agent/scorecard.md`,将评分拆成 AICO orchestration 50 分和 Data-Agent product quality 50 分,并加入 mandatory fail conditions。
- 新增 `docs/superpowers/specs/2026-06-28-data-agent-aico-benchmark-design.md`,记录设计边界:本轮只定义 benchmark 和 SOP,不创建 `data-agent-v1` 产品工程。
- 本轮不改运行代码,不新增测试;验证以文档自检、占位扫描和 diff check 为准。

**Round 176**(2026-06-28,Codex — Data-Agent V1 baseline scaffold):
- 创建 `projects/data-agent-v1/` 独立 benchmark 产品工程,包含 AGENTS / North Star / Status / Goal Brief / handoff / journal / evidence 文档。
- 新增 `projects/data-agent-v1/aico-project.json`,用 Claude 承担 lead / architect / implementer,用 Codex 承担 tester / reviewer / challenger。
- 新增 deterministic Data-Agent V1:
  - 企业样例 CSV:orders、ad spend、refunds、inventory、customers。
  - 语义层:paid revenue、refund rate、ROAS、inventory months 和维度/source authority。
  - CLI / engine / eval runner,回答必须带 intent、answer、evidence、calculation、SQL、caveats 和 follow-up questions。
  - 20 条 golden eval。
- 新增 `benchmarks/data-agent/runs/2026-06-28-v1/` evidence 模板和本地 eval 结果。
- 验证:
  - `PYTHONPATH=projects/data-agent-v1/src uv run pytest projects/data-agent-v1/tests tests/unit/test_data_agent_project.py -q`:7 passed。
  - `PYTHONPATH=projects/data-agent-v1/src uv run python -m data_agent_v1.eval_runner`:20/20 passed。
  - `uv run ruff check ...`:通过。
  - `uv run mypy --config-file projects/data-agent-v1/pyproject.toml ...`:通过。
  - `PYTHONPATH=projects/data-agent-v1/src uv run pytest -q`:478 passed,1 skipped。

**Round 177**(2026-06-28,Codex — Data-Agent V1 data model view):
- 人类追问 canonical seed question 和背后样例数据,要求在 `enterprise_week_one` 中画清楚数据底层关系、业务过程和实体。
- 新增 `projects/data-agent-v1/sample_data/enterprise_week_one/README.md`:
  - 业务过程图:Marketing spend → Customer → Paid order → Refund, Inventory 作为商品供给上下文。
  - Mermaid ER 图:Customer / Order / Refund / Product / Inventory / Ad Spend。
  - 表粒度、主键、join keys 和用途。
  - paid revenue、revenue drop、ROAS、refund rate、inventory months of cover 指标公式。
  - 展开说明“本月华东区收入为什么下降?”如何由 `orders.csv` 算出 120000 → 84000、下降 30.0%、最大拖累 Douyin -17000。
- 更新 `projects/data-agent-v1/README.md` 链接到样例数据模型说明。
- 本轮只改文档,未跑 pytest;执行 `git diff --check` 通过。

**Round 166**(2026-06-18,Codex + Lead + Challenger — SME Agent metadata contract):
- 使用两个受控协作 Agent 对 SME Agent Phase 1 做独立 Lead / Challenger 审查;有效意见不是停留在评论,而是回写到代码、Goal Brief、handoff 和 evidence manifest。
- 完成“华东区本月收入为什么下降”元数据 grounding 链路:术语 `DEFINES` 指标、显式维度过滤、指标维度/数仓/实体/知识关系和稳定 evidence IDs。
- 新增关系类型矩阵、版本递增、metadata governance status、source refs 和具名 human steward 审批;避免把错误语义持久化。
- 新增 one-writer-per-slice 与独立 Reviewer/Tester 约束,并在 CI 增加 SME Agent strict-mypy step。
- 发现本机已有 AICO Telegram runtime 使用旧项目配置;未静默中断,将真实 project-office + restart/morning sample 登记为下一操作 Gate。
- 验证:`uv run pytest -q` 452 passed,1 skipped;ruff、format、AICO mypy、SME Agent strict mypy、diff check 全绿。

**Round 165**(2026-06-18,Codex — SME Agent durable project foundation):
- 新增独立项目目录 `projects/sme-agent/`,业务代码不进入 AICO core;AICO 只承担 AI Lead、团队任命、审批、审计和交接的组织治理层。
- 建立可跨天持续迭代的项目办公室:独立 `AGENTS.md`、北极星、状态、Round/Pitfall/Blocker、ADR、当前 handoff 和人机对齐协议。
- 新增 `projects/sme-agent/aico-project.json`,任命 lead、metadata engineer、knowledge engineer、runtime engineer、tester、reviewer 和 challenger,并为角色绑定最小资源、权限和 workspace。
- 实现第一条元数据垂直切片:不可变术语/知识/指标/维度/数仓资产/业务实体模型、关系模型、`MetadataRepository` 端口、内存 Adapter、注册/搜索/关系校验/邻接查询。
- 验证:新项目与 AICO 配置 7 tests passed;根 pytest Gate 已纳入 SME Agent tests,完整回归 447 passed,1 skipped;ruff、format、mypy 和 diff check 通过。

**Round 164**(2026-06-15,Codex — Phase 8 final slices + Orchestrator registry cleanup):
- 收口 B-005 工程债:
  - 新增并接通 `OrchestratorCommandRegistry`,把 command handler 实例化、slash command 分发表、`/inbox`、`/morning`、审批/中断/broadcast 等命令处理从 `Orchestrator` 主体迁出。
  - `Orchestrator` 保留 IM 入站、任务提交、流式输出、协作派发和少量 runtime 协调职责。
- 完成 Phase 8 两个剩余安全切片:
  - `/overnight` lead handoff 合格后自动排 challenger / reviewer checkpoint review,形成多 step / 多 agent 夜间编排,但不绕过审批或审计。
  - 新增默认关闭的 morning push scheduler,可通过 `AICO_MORNING_PUSH_ENABLED=true`、`AICO_MORNING_PUSH_TARGET_ID`、`AICO_MORNING_PUSH_PROJECT`、`AICO_MORNING_PUSH_TIME` 定时推送 `/morning` 同口径早报。
- 修复本轮发现的 prompt 风险边界问题:
  - `/overnight` wrapper 使用 `Current task:` 标记真实老板目标,避免系统提示词里的工作流描述被误判成 `shell_exec` / `write_files`。
- 文档:
  - 更新 Feishu smoke playbook 和 daily ops,给出 Mac 飞书 App 已登录后的开放平台、callback、URL verification 和文本收发验收步骤。
- 验证:
  - `uv run pytest -q`:440 passed,1 skipped。
  - Phase 8 contract gate:41 passed。
  - `uv run ruff check .`,`uv run ruff format --check .`,`uv run mypy src tests`:通过。
  - 结构扫描:`Orchestrator` 447 行,`OrchestratorCommandRegistry` 414 行,未发现单方法 >=100 行。

**Round 162**(2026-06-15,Codex — CI Node 24 preflight):
- 继续推进长期目标,当前远端 CI 对 `21c6d5a` 已成功,但 GitHub Actions 给出 Node.js 20 actions deprecation
  warning:2026-06-16 起 JavaScript actions 默认切 Node 24,2026-09-16 移除 Node 20。
- 更新 `.github/workflows/ci.yml`:
  - 在 `python` job 上设置 `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: "true"`。
  - 目的不是绕过 CI,而是在 release 前主动让 `actions/checkout@v4`、`actions/setup-python@v5`、
    `astral-sh/setup-uv@v5` 按 Node 24 runtime 跑一次,提前发现兼容性问题。
- 本轮不改运行代码和发布文案;只改 CI runtime preflight。

**Round 161**(2026-06-15,Codex — social preview verifier):
- 继续推进长期目标,当前公开发布前最大的 owner-only 卡点是 GitHub social preview 仍显示默认 repository card。
- 新增 `aico-github-social-preview` console script:
  - 读取 `gh repo view --json openGraphImageUrl`。
  - 下载当前 GitHub OG 图并解析 PNG / GIF / JPEG 尺寸。
  - 对 `opengraph.githubassets.com` + `1200 x 600` 做“疑似默认 repository card”启发式判断。
  - 命中默认卡片时返回 `status: needs-owner-upload` 和 exit code 2,避免 tag / Release 前只靠人工猜测。
- 新增 `tests/unit/test_social_preview_cli.py`:
  - 覆盖 PNG 尺寸解析、默认卡片启发式、needs-owner-upload exit code、非默认 preview 的 ok 分支。
- 更新 `docs/human/github-publication.md`、`docs/agent/09-github-release-ops.md` 和
  `docs/launch/readiness-audit.md`,把上传后复核命令接入 owner / Agent 发布流程。
- 更新当前发布测试数:
  - `docs/launch/v0.1.0-release-notes.md`:433 unit tests passing,1 skipped。
  - `docs/launch/readiness-audit.md`:full local tests 433 passed,1 skipped。
  - `docs/launch/playbook.md`:433 unit tests。
- 验证:
  - `uv run pytest -q`:433 passed,1 skipped。
  - `uv run ruff check .`:通过。
  - `uv run ruff format --check .`:通过。
  - `uv run mypy src tests`:通过。
  - `uv run aico-github-social-preview`:返回 `status: needs-owner-upload`,符合当前 GitHub live state。

**Round 160**(2026-06-15,Codex — launch article final edit):
- 人类要求从 MCN 助理角度审查四篇中文发布稿,重点修正共鸣版博客园:
  - 原 P1 “AI 很强,但人离开电脑后链路断了”代入感不够,要更日常、更直接。
  - 6 个痛点叙事优先级应为原 P3 / P6 最重要,再到 P2 / P5,最后 P1 / P4。
  - 四篇文章要在发布前去掉 AI 味,并继续保证口径准确。
- 更新 `docs/launch/articles/2026-06-10-worker-resonance-cnblogs.md`:
  - 保留 P 编号用于和解法表对齐,但按真实传播优先级重排为 P3、P6、P2、P5、P1、P4。
  - 将“离开电脑链路断”改成午饭、电梯、睡前、早上接手这些日常场景,强调“能不能继续管理项目”。
  - 解法总览和 release room 场景闭环表同步按新优先级排序。
- 更新 `docs/launch/articles/2026-06-10-tech-lead-cnblogs.md`:
  - 将技术痛点表重排为 lead 调度瓶颈、权限不可控、IM 可读性、长任务恢复优先。
  - 补充为什么前两项决定能不能任命 lead,中间两项决定离开电脑后能不能接手。
- 更新两篇小红书稿:
  - 共鸣版改成更生活化的“我还是得一直盯着它们”,优先呈现多 agent 调度、风险审批、局面压缩。
  - 技术 Lead 版改成“反复切现场”的多项目管理痛点,保留 Telegram / Adapter / 审批 / 审计边界。
- 更新 `docs/launch/articles/README.md`:
  - 同步主诉求和推荐标题,避免发布索引仍使用旧痛点口径。
- 复核 `docs/launch/readiness-audit.md`:
  - GitHub live audit 仍显示仓库 `PUBLIC`,description / homepage / 19 个 topics 已配置。
  - `openGraphImageUrl` 仍指向 GitHub 默认 repository card;下载的 OG 图为 `1200 x 600`,
    本地 `docs/assets/social-preview.png` 为 `1280 x 640`,说明自定义 social preview 仍需 owner 上传。
  - 将 latest pushed CI 口径改成“tag 前必须按当前 release-candidate HEAD 重新 live check”,
    避免 hardcode 某个会过期的 CI commit。
- 已提交并 push 中文文章终稿:
  - commit:`5e88ff2` (`docs: finalize chinese launch articles`)
  - GitHub Actions run:`27544306617`
  - conclusion:`success`
- 本轮只改发布 Markdown,未改运行代码;未进入 GitHub tag / Release。

**Round 159**(2026-06-15,Codex — pushed CI coverage):
- 持续推进长期目标,本轮把 Round 152-158 的本地 release-readiness 改动从“只在本机通过”推进到
  “可由 GitHub Actions 覆盖”的状态。
- 更新 `docs/launch/readiness-audit.md`:
  - 移除会在提交后立刻过期的 hardcoded `HEAD inspected: 564e598` 和 “当前 worktree uncommitted”口径。
  - 改为 2026-06-15 local release-candidate audit window,并明确 local gates 只证明当前 workspace;
    release candidate 只有在相同改动 commit + push 后 CI 绿才成立。
  - 在 tag 前清单中新增:push 后记录 pushed commit SHA 和 CI result 到 `STATUS.md` / `ROUNDS.md`。
- 本轮本地 release gates 已通过:
  - `uv run pytest -q`:428 passed,1 skipped。
  - `uv run ruff check .`:通过。
  - `uv run ruff format --check .`:通过。
  - `uv run mypy src tests`:通过。
  - Phase 8 absence-loop gate:41 passed。
  - `uv run aico-release-room-demo`:通过。
  - draw.io XML 5 张解析通过;launch Markdown 本地链接 17 个检查通过;`git diff --check` 通过。
- 已提交并 push:
  - commit:`958aa61` (`docs: add launch readiness audit`)
  - GitHub Actions run:`27521858307`
  - conclusion:`success`
- 本轮仍不进入 `v0.1.0` tag / Release:GitHub UI public / description / topics / social preview 仍需 owner 最终确认。

**Round 158**(2026-06-15,Codex — release readiness audit):
- 持续推进长期目标,本轮不新增功能和宣传稿,而是把公开发布前最容易漂移的事实证据整理成可复用审计台账。
- 新增 `docs/launch/readiness-audit.md`:
  - 记录当前 scope:branch `main`,HEAD `564e598`,并明确当前 worktree 有未提交变更。
  - 记录证据:无 token demo 通过、完整本地测试 428 passed / 1 skipped、Phase 8 gate 41 passed、
    ruff / format / mypy / diff hygiene 通过、中文文章链接和 draw.io XML 通过。
  - 记录 GitHub Actions 事实:最新 pushed `main` CI 成功,但时间早于当前未提交变更;发布前必须 push 后等新 CI 绿。
  - 记录 claim boundaries:Telegram primary、Feishu first slice still pending production smoke、AICO 不是 sandbox/cloud、
    OpenClaw/company CLI 不是已实现 adapter、`/overnight` 不是完整 autonomous scheduler、`/view` 不是默认 Web console。
  - 写入 `v0.1.0` tag 前 Go / No-Go 清单。
- 更新 `docs/launch/v0.1.0-release-notes.md`:
  - 把易漂移的 exact rounds 数字改为 `150+ documented development rounds`。
  - 保留当前实测 `428 unit tests passing, 1 skipped` 和 P-040。
  - 修正 release notes 作为 `docs/launch/` 内 Markdown 文件时的本地相对链接。
- 更新 `docs/launch/playbook.md`:
  - 将“CI 绿 ✅ 已完成”改成 CI workflow / badge 已配置,但 latest pushed main 需要发布前重新确认 CI 绿;
    当前未提交变更只能用本地 gate 证明。
- 更新 `docs/launch/articles/README.md`:
  - 当前验证状态改为引用 `../readiness-audit.md`,避免文章索引继续维护过期 Round 号。
- 验证:
  - `uv run aico-release-room-demo`:通过,仍展示 `/morning` 和 `/view` 动线。
  - `gh run list --limit 5`:最新 pushed `main` CI 为 success,但不覆盖当前 uncommitted worktree。
  - `uv run pytest -q`:428 passed,1 skipped。
  - Phase 8 absence-loop gate:41 passed。
  - `uv run ruff check .`,`uv run ruff format --check .`,`uv run mypy src tests`,`git diff --check`:均通过。
  - draw.io XML 5 张解析通过;launch Markdown 本地链接 17 个检查通过。

**Round 157**(2026-06-14,Codex — test env isolation + release facts):
- 持续推进长期目标,优先做能支撑“实事求是公开发布”的当前-state 验证,而不是继续增加宣传材料。
- 先重跑 Phase 8 absence-loop AI 前置 contract gate:
  - `41 passed in 0.90s`,覆盖父子 agent 委派、`/overnight` handoff、移动端分片、
    `/aico-view` alias、`/view` HTML snapshot 和 Telegram `sendDocument` 上传路径。
- 随后跑完整 `uv run pytest -q`,发现当前本机 dogfood shell 中的真实 `AICO_*` 环境变量会污染 unit tests:
  - aico-view 路由测试被 `AICO_VIEW_TOKEN` 影响,返回 401。
  - Phase1 runtime 默认值测试被 `AICO_VIEW_ENABLED=true` 影响,意外启用 view snapshot handler。
- 新增 `tests/unit/conftest.py`:
  - autouse fixture 在每个 unit test 前清理当前进程 `AICO_*` 环境变量。
  - 需要测试环境读取行为的用例仍可在函数内用 `monkeypatch.setenv(...)` 显式设置。
- 更新 `docs/journal/PITFALLS.md`:
  - 新增 P-040,记录本机 dogfood 环境变量污染单测的症状、根因、修复方式和避免方式。
- 更新 `docs/launch/v0.1.0-release-notes.md`:
  - 保留当前实测 `428 passed, 1 skipped`。
  - 将 pitfalls 索引更新为 P-040。
  - 将 development rounds 更新为 156。
  - 收紧 Feishu 兼容性口径:Telegram primary;Feishu first slice 已实现,但仍需生产 callback smoke 后再当作同等稳定公开 Channel。
- 验证:
  - `uv run pytest -q`:428 passed,1 skipped。
  - Phase 8 absence-loop gate:41 passed。
  - `uv run ruff check .`:通过。
  - `uv run ruff format --check .`:通过。
  - `uv run mypy src tests`:通过。
  - `git diff --check`:通过。
  - draw.io XML 解析 5 张图通过。
  - `docs/launch/articles/README.md` 本地链接检查通过。

**Round 156**(2026-06-14,Codex — social diagram sources):
- 持续推进中文发布素材包收口,承接 Round 155 README 中“建议补 3 张面向社交平台静态图”的待办。
- 新增三张 draw.io XML 图源:
  - `docs/launch/articles/diagrams/social-pain-cover.drawio`:共鸣版痛点首图,用中午吃饭、路上被问 release、
    睡前托管等场景强化日常代入。
  - `docs/launch/articles/diagrams/boss-absent-loop.drawio`:展示 `/overnight`、operator inbox、`/morning`、
    `/task`、`/audit`、`/view` 的老板不在场接手链路。
  - `docs/launch/articles/diagrams/project-lead-org.drawio`:展示 Boss 任命 Project Lead,Lead 再协调
    implementer / tester / reviewer 的项目组织关系。
- 更新 `docs/launch/articles/README.md`:
  - 将 3 张社交图从“建议额外补”改成正式图源清单。
  - 为每张图写明推荐发布位置:共鸣版小红书首图、共鸣长文解释图、技术 Lead 版组织关系图。
  - 更新验证状态,注明五张 draw.io XML 均已解析通过,`git diff --check` 在 Round 156 通过。
- 验证:
  - `/usr/bin/python3` 解析 `docs/launch/articles/diagrams/*.drawio` 通过。
  - `/usr/bin/python3` 检查 `docs/launch/articles/README.md` 本地 Markdown 链接通过。
  - `git diff --check` 通过。
  - 本轮只改 Markdown / draw.io XML,未跑 Python 单测。

**Round 155**(2026-06-14,Codex — launch article index):
- 持续推进“围绕北极星目标做实事求是 AI 闭环迭代”的长期目标,选择不依赖 GitHub owner / 真机 IM 环境的下一步:
  把已完成的中文文章、图源和发布口径整理成可执行素材索引。
- 新增 `docs/launch/articles/README.md`:
  - 汇总四篇中文文章及推荐平台、主诉求、使用方式。
  - 汇总两张 draw.io 图源和发布建议。
  - 给出发布顺序:GitHub public + v0.1.0 Release 后先发共鸣长文,再发技术 Lead 长文,
    小红书短文分开发。
  - 增加发布前口径检查:Telegram 稳定入口、飞书待 smoke、OpenClaw 未实现、AICO 不是云端运行/安全沙箱、
    `/overnight` 还不是完整自动调度器、`/view` 是只读 HTML snapshot。
  - 增加推荐标题和评论区应对,覆盖 CrewAI / AutoGen / LangGraph 对比、Telegram 原因、安全边界、
    单 agent 是否太重、Codex 是否必要。
- 清理 `docs/launch/articles/.DS_Store` 未跟踪系统文件,避免素材目录带 macOS 杂物。
- 验证:
  - `find docs/launch/articles -maxdepth 2 -type f` 确认目录只含文章、README、draw.io 和 research notes。
  - `/usr/bin/python3` 解析两张 draw.io XML 通过。
  - 小红书字数复核:共鸣版 817 字符,技术 Lead 版 838 字符。
  - 本轮只改 Markdown / 清理未跟踪系统文件,未跑 Python 单测。

**Round 154**(2026-06-10,Codex — prepublish MCN review):
- 人类指出共鸣版博客园痛点部分仍不够日常,`P1:AI 很强,但人离开电脑后链路断了`
  代入感弱;同时指出 6 个问题的叙事优先级应调整为 P3 / P6 最重要,再到 P2 / P5,
  最后才是 P1 / P4。
- 以“发布前 MCN 助理审稿”视角优化四篇文章:
  - 共鸣版博客园开头补中午吃饭、路上被问 release、睡前托管、第二天翻现场等更日常的痛点场景。
  - 共鸣版博客园 6 个痛点重排为:
    1. 长任务不可接手。
    2. 只想看局面,不是看日志。
    3. 多 agent 增加调度成本。
    4. 项目知识和经验不能每次重讲。
    5. 离开电脑后链路断。
    6. 风险动作不能默认放飞。
  - 同步调整“解法总览”和“睡前托管 release room”场景里的痛点-解法表,保持前后一致。
  - 技术 Lead 版博客园补“上午查 A 项目 CI / 午饭前被问 B 项目 release / 下午回 C 项目 PR”
    的多项目打断场景,并强调长任务恢复和 IM 可读性是能否托付 lead 的关键。
  - 两篇小红书同步补更日常的打断场景,并保留 1000 字以内。
- 发布前校对:
  - 修复共鸣版博客园“解法总览”表头重复问题。
  - 将公开稿里的“一坨/一大坨”改为“一屏混杂输出 / 一整屏日志”。
  - 扫描 `这个产品|一个具体场景|打中|赋能|颠覆|极致|全自动万能|无缝|行业领先|闭环|智能化`
    等词,除正常表头外无不当命中。
  - 小红书字数:共鸣版 816 字符,技术 Lead 版 839 字符。
  - `git diff --check` 通过。
  - 本轮只改 Markdown,未跑 Python 单测。

**Round 153**(2026-06-10,Codex — cnblogs article hardening):
- 人类指出共鸣版博客园文章需要更工整严谨:
  - 前面提出的痛点要在后文逐项回答。
  - 第一视角口吻要更自然,避免“这个产品真正打中的痛点”等客观 AI 腔。
  - 博客园文章可以技术硬核,要深挖技术核心决策背后的动机。
  - 需要回答 role/agent/team 关系、role 记忆和经验、lead 为什么能管理经验、`/view` 为什么存在、
    跨 agent 委派如何实现、task 架构、权限如何管控。
  - 涉及图要补 draw.io XML。
- 重写两篇博客园长文:
  - `docs/launch/articles/2026-06-10-worker-resonance-cnblogs.md`
  - `docs/launch/articles/2026-06-10-tech-lead-cnblogs.md`
- 新增两张 draw.io XML 图:
  - `docs/launch/articles/diagrams/aico-domain-model.drawio`
  - `docs/launch/articles/diagrams/aico-task-flow.drawio`
- 文章新增/强化内容:
  - 行业通用痛点:durable execution、human review、guardrails、memory、observability、RBAC、
    multi-agent runtime、MCP/A2A 等,并引用 LangSmith / LangGraph、CrewAI、AutoGen 官方文档。
  - 领域模型:Agent / Role / Project / Appointment / Team / Lead 的边界和为什么 Appointment 是关键抽象。
  - Memory 与 Experience 分层:fact 按 query 召回,experience 按 role 注入,避免把项目事实和经验 lesson 混在一起。
  - Task 架构:IMChannel -> MessageRouter -> OrchestratorTaskFactory -> TaskBus -> AIAdapter -> Audit/View。
  - 跨 agent 委派:解析 `@reviewer:` 指令,child task 记录 parent audit,并用 `Current task:` 区分 context 与 instruction。
  - 权限模型:RiskLevel、ApprovalPolicy、adapter capability gate 三层边界。
  - `/view`:只读 HTML snapshot 经 IM `sendDocument` 发送,不默认让手机访问 localhost / tunnel。
- 验证:
  - `/usr/bin/python3` 解析两张 draw.io XML 通过。
  - `rg` 扫描不再出现“这个产品”“一个具体场景”等被点名的 AI 腔表达。
  - `git diff --check` 通过。
  - 本轮仅改 Markdown / draw.io XML,未跑 Python 单测。

**Round 152**(2026-06-10,Codex — launch article pack):
- 人类要求围绕 AICO 核心内容写四篇宣传文章:
  - 打工人共鸣视角:从真实公司 boss-absent 仍能运转,引出多个 agents 是否也能被组织起来继续执行。
  - 技术视角:从一个人多项目精力上限出发,引出项目 lead 作为上下文、风险和 agent 指挥层。
  - 两个视角均分别写博客园风格和小红书风格;小红书正文不超过 1000 字。
- 新增 `docs/launch/articles/` 宣传文章包:
  - `2026-06-10-worker-resonance-cnblogs.md`
  - `2026-06-10-worker-resonance-xiaohongshu.md`
  - `2026-06-10-tech-lead-cnblogs.md`
  - `2026-06-10-tech-lead-xiaohongshu.md`
  - `promotion-research-notes.md`
- 文章事实边界:
  - 当前稳定公开入口仍写 Telegram;飞书只写 first slice / 待生产 smoke。
  - 不把 OpenClaw 或公司内部 CLI 写成已实现 Adapter。
  - 不把 lead 主动机制写成完全自主 CEO;明确当前已实现的是项目/岗位/任命、审批审计、共享记忆、
    `/overnight`、`/morning`、`/task`、`/audit`、`/view` 等 Phase 8 能力。
- 外部传播调研提炼:
  - Ollama / Dify / LangChain / Supabase 的共性是首屏窄定位、quickstart 证据、社区入口和场景先行。
  - AICO 后续传播应继续把 boss-absent 作为第一信号,并反复给 no-token demo 命令。
- 验证:
  - 两篇小红书稿 `wc -m` 分别为 728 / 775 字符;扣掉图片行后 670 / 717,均低于 1000。
  - 检查了 README GIF 相对路径存在。
  - 以关键词扫描方式审掉了不合事实或过度营销的表述;本轮仅改 Markdown 文档,未跑 Python 单测。

**Round 151**(2026-06-10,Codex — readme showcase command review):
- 人类指出 README 中“GitHub 发布页怎么配置”与项目展示无关,要求删除,并要求 README
  中的 cmd 命令经得起推敲,不能给错命令影响第一印象。
- README 展示面调整:
  - 英文 `GitHub Publication Checklist` 段落删除。
  - 中文 `GitHub 发布页怎么配置` 段落删除。
  - 中英文 Quickstart 均补充 `aico-phase1` 是长驻 Telegram runtime,需要保持运行,
    停止时按 `Ctrl-C`。
  - 中文开头把 OpenClaw / 公司内部 CLI 从当前已收编对象改为后续可按 Adapter 协议接入,
    避免把未实现 Adapter 写成当前能力。
  - 英文能力点再次标注 Feishu first slice 仍待 production smoke。
- README 命令验证:
  - `env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python 3.11 aico-release-room-demo`
    本地跑通。
  - `env UV_CACHE_DIR=/tmp/aico-uv-cache uv sync --python 3.11` 本地跑通。
  - `env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python 3.11 aico-phase1 --help`
    本地跑通,确认 entrypoint 存在;真实 `aico-phase1` 仍需要 Telegram token 并会长驻运行。
  - `env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python 3.11 aico-state --db /tmp/aico-readme-state.db`
    本地跑通。
  - Telegram README 命令由 `tests/unit/test_commands.py`、`tests/unit/test_orchestrator.py`
    和 Release Room acceptance 覆盖。

**Round 150**(2026-06-10,Codex — readme factual review):
- 按人类要求 review 中英文 README,核对当前实现状态和公开发布口径。
- 发现并修正两处容易造成外部误解的表述:
  - 英文 README 不再写成 `Telegram or Feishu` 同等稳定入口,改为 Telegram today;
    Feishu 是 first non-Telegram channel slice,仍待 production smoke。
  - 英文 README 不再写 `with no laptop required`,改为不用坐在电脑前;中文 README 同步说明
    当前主入口是 Telegram,飞书待生产 smoke 后再作为稳定入口推荐。
- 其余 README 主张与当前状态一致:boss-absent 叙事、Release Room demo、`/morning`、
  `/view`、审批审计、Cursor / CodeFlicker / Trae / Gemini smoke 状态均与 STATUS / quickstart
  口径一致。

**Round 149**(2026-06-10,Codex — boss-absent public assets):
- 人类指出 Round 148 生成的 `social-preview.png` 和 GIF 虽有 `while you are away`、`/morning`
  和 `/view`,但没有把 boss-absent 假设作为第一视觉信号;要求判断这是能力不足还是疏忽。
- 判断:这是表达疏忽,不是能力不足。当前能力已经有 `/overnight`、`/morning`、`/view`、
  审批和审计链路,足以支撑 boss-absent 叙事。
- 更新 `examples/release-room/generate-public-gif.py`:
  - GIF 首帧 title 改为 `Boss-Absent Mode`。
  - 顶部副标题改为 `Boss-absent release room`。
  - 右侧面板改为 `Boss-absent loop` / `What still works while you are away`。
  - footer 改为 `Boss absent - local agents still work - approval and audit stay visible`。
  - social preview 主文案改为 `Boss absent. Local agents still work.`。
  - social preview 大字改为 `Leave the laptop. Keep the team moving.`。
- 重新生成资产:
  - `docs/assets/release-room-demo.gif`:36 秒、`960 x 540`、约 278 KB。
  - `docs/assets/social-preview.png`:`1280 x 640`、约 48 KB。
- 视觉复核:
  - `/tmp/aico_absent_first_frame.png`:首帧明确 boss-absent。
  - `/tmp/aico_absent_contact.png`:8 帧均可读,后段包含 `/morning` 和 `/view`。
  - `/tmp/aico_absent_social.png`:social preview 首屏明确 boss-absent。

**Round 148**(2026-06-10,Codex — public assets and pre-public checks):
- 按人类要求继续 public 前收口,优先解决 Round 147 标出的 README GIF 首印象 blocker。
- 新增稳定资产生成器:
  - `examples/release-room/generate-public-gif.py` 从当前 Release Room shot rhythm 生成 transcript-driven
    public GIF,不依赖真实 Telegram 录屏、provider token 或手工剪辑。
  - 同时生成 GitHub Social preview 静态图。
- 生成并替换发布资产:
  - `docs/assets/release-room-demo.gif`:约 36 秒、`960 x 540`、约 279 KB、8 个场景;首帧为当前
    IM 产品画面,并覆盖 `/team`、`/remember`、`/ask`、`/approve`、`/overnight`、`/morning`、
    `/view`、`/audit`。
  - `docs/assets/social-preview.png`:`1280 x 640`、约 51 KB,用于 GitHub Social preview 上传。
- 文档口径同步:
  - README / README.zh-CN 移除"待复剪 GIF" roadmap 项。
  - `docs/human/github-publication.md` 指向新的 `social-preview.png`,并更新 GIF 尺寸 / 时长口径。
  - `docs/launch/playbook.md` 把 README GIF 从待办改为完成,但保留 GitHub UI social preview 上传 / 确认。
  - release-room docs / playbook / shot rhythm 记录可重复生成命令。
  - `docs/agent/09-github-release-ops.md` 更新 public 前资产复核结论。
  - P-039 标记 RESOLVED。
- GitHub public 前 metadata live 复核:
  - 仓库仍是 `PRIVATE`,默认分支 `main`。
  - description / homepage 已配置。
  - issues enabled,wiki disabled。
  - topics 已补齐 19 个,包括 `ai-coding`、`audit-log`、`memory`、`llm`、`fastapi`、`mcp`。
  - 本地 `v0.1.0` tag 为空,GitHub Release 列表为空。
- public 前剩余人工 UI 动作:上传 / 确认 `docs/assets/social-preview.png`,然后由仓库 owner 改 public。

**Round 147**(2026-06-09,Codex — GitHub release ops and README review):
- 复核 GitHub 状态:
  - `gh` 在当前桌面环境中可用,但普通沙箱读不到 macOS keyring;需要用提权方式执行 `gh ...`。
  - `gh repo view MarcelLeon/ai-company-os` 显示仓库仍是 `PRIVATE`,默认分支 `main`。
  - 本地和远端都未创建 `v0.1.0` tag,GitHub Release 列表为空。
- 审阅 README:
  - 英文 / 中文 README 的主体叙事、no-token demo、`/inbox` / `/morning` / `/task` / `/audit`
    口径已对齐当前 RC。
  - 发现 README GIF 是当前最大首印象缺口:现有 `docs/assets/release-room-demo.gif` 约 95 秒、
    `360 x 730`,首帧不是 Telegram 产品画面,且没有前置展示 `/morning` 和 `/view`。
- 新增 Agent GitHub 运维入口:
  - `docs/agent/09-github-release-ops.md` 固化 public / tag / GitHub Release / D0 的检查顺序。
  - `AGENTS.md` Step 7 和自检清单接入该 SOP。
- 更新发布材料:
  - README / README.zh-CN roadmap 标出 README GIF D0 复剪要求。
  - `docs/human/github-publication.md` 修正当前 GIF 体积和 social preview 口径。
  - `docs/launch/playbook.md` 不再把 GIF / GitHub UI 复核写成无条件完成。
  - `docs/examples/release-room.md` 和 `examples/release-room/shot-rhythm.md` 明确 `/view` 镜头和 D0 复剪标准。
- 记录 P-039:README GIF 首帧和最新能力比文件是否存在更重要。
- 本轮仅改文档,不改运行代码;`git diff --check` clean;未执行 public / tag / GitHub Release。

**Round 146**(2026-06-09,Codex — release-candidate closure):
- 按发布助理口径收口 `launch/oss-public-readiness` 分支,先把当前未提交的 Round 141-145 修复纳入同一 RC 范围,没有启动新功能。
- 校正公开材料:
  - README / README.zh-CN 的 overnight 接手路径从旧 `/daily` / `/tasks` 改为 `/inbox` / `/morning` / `/task` / `/audit`。
  - `docs/launch/v0.1.0-release-notes.md` 和 launch playbook 的测试数更新为 **428 passed / 1 skipped**,journal 更新为 Round 145。
  - no-token Release Room demo、transcript、shot rhythm、recording storyboard 和 release-room playbook 改为用 `/morning` 做早上接手入口。
- 发现并记录 P-038:公开 demo 会在产品动线变化后滞后,发布前必须跑 demo 而不只是跑 pytest。
- 发布前验证:
  - Phase 8 contract gate: **41 passed in 0.94s**。
  - full clean env pytest: **428 passed / 1 skipped**。
  - Release Room no-token demo 可执行,输出包含 `/morning` handoff 和 `/audit`。
  - `uv run ruff check .`;`uv run ruff format --check .`;`uv run mypy src tests`;`git diff --check` 全绿。
- 当前 RC 仍未执行不可逆动作:未改 GitHub public/private,未打 `v0.1.0` tag,未发 GitHub Release。

**Round 145**(2026-06-09,Codex — local Telegram/provider validation first):
- 人类纠正验收边界:真实 Telegram 手机端观感和真实 provider 是否稳定触发 implementer -> reviewer 协作,在当前 Mac 有 Telegram App 和运行凭据时,Agent 必须先验,不能默认交给 human。
- 已把验收分层从"机器 Gate -> human sample"修正为"机器 Gate -> Agent 本机真实样本 -> human 体感 sample"。human 只看是否顺、是否方便接手、是否信任交接。
- 本机实测:
  - Telegram App 可打开 `ai_co` bot;`/project aico` 被真实 bot 收到并回包。
  - 真实协作样本 parent `9efe8b4c-bd03-47ee-8f99-cc7dde5af17a`:target=implementer,adapter=claude-code,done。
  - 日志明确记录 `Collaboration directive: parent_task=9efe8b4c... source=implementer target=reviewer payload_chars=170`。
  - reviewer child `a27d61ef-ea41-44b3-8a81-a4ad74d40a01`:target=reviewer,adapter=codex,done。
  - Telegram 输出触发移动端分片,reviewer 输出被拆为 message `1278` 和后一条短消息;最终截图保存在 `/tmp/aico_telegram_collab_done.png`。
- 运行坑修复:真实验收发现 Telegram long polling 每约 6 秒打印空 warning。原因是默认 `httpx.AsyncClient` read timeout 约 5 秒,短于 Telegram `getUpdates timeout=30`;已把默认 read timeout 改为 `poll_timeout_seconds + 5` 并补单测。
- 验证通过:targeted 25 passed in 0.46s;Phase 8 gate **41 passed in 0.36s**。

**Round 144**(2026-06-09,Codex — Phase 8 contract gate before human sample):
- 对当前北极星 Dogfooding 分层和 `STATUS.md` human sample 队列做二次收口:需要人类看的功能主要剩 `/overnight` delegate 真实 IM 体感、老板查看动线、`/view` Telegram 附件/手机打开体验。
- 盘点现有测试后确认 AI 可以前置验证更多确定性 contract:父子 agent 委派 payload、`Current task:` 风险边界、只读 reviewer 不被 risky parent context 误判、`/overnight` handoff 完整性、移动端分片、`/aico-view` alias、自包含 HTML snapshot 和 Telegram `sendDocument` multipart 上传。
- `docs/playbooks/phase-8-absence-loop.md` 新增 "AI 前置 Contract Gate",写入当前可直接执行的 targeted pytest 命令、覆盖范围表和 human sample 剩余职责。
- 本轮实际执行 contract gate:40 passed in 0.30s。
- 决策:下一轮或后续修同类问题时,先跑 playbook 里的 gate;只有 gate 通过后,才请人类跑 1 条代表性真实 IM 样本。

**Round 143**(2026-06-09,Codex — dogfood validation ladder):
- 人类指出北极星里的"人工 dogfooding"不应理解为每次修复后都靠人完整重跑长链路;父子 agent 委派、`/overnight` 和真实 IM 输出修复周期长,需要机器测试尽量先覆盖。
- 决策:不改北极星三句话本体,只在第三句下新增 Dogfooding 验收分层。Dogfooding 仍是最终标准,但顺序变成机器 Gate → 人工 Sample → 人工 Blocking。
- `docs/agent/06-testing-guide.md` 固化同一规则:确定性 contract 先单测 / 集成 / 模拟 E2E;人工只抽样验证手机体感、真实 provider / Channel 漂移和老板是否知道下一步。
- `docs/journal/BLOCKERS.md` 新增并关闭 B-006,说明当前待测队列不再因为"必须完整人工复验同一长链路"而阻塞。
- 当前 `/overnight` delegate 输出和老板动线复验从"最高优人工完整回归"降级为"机器 Gate 后 1 条代表性真实 IM 样本";如果样本失败,必须留下 `/task <id>`、截图/原始输出、预期效果和实际偏差。
- 本轮仅改文档,未改运行代码;`git diff --check` clean,未跑 Python 单测。

**Round 142**(2026-06-05,Codex — secretary route + mobile readable handoff):
- 人类复验最近一次 `/overnight` 和 implementer -> reviewer 协作,反馈 `Collaboration requested` 后 reviewer 文案仍然是手机上看不动的大块输出。
- 进一步定位:Round 141 解决了“粘连 heading / bullet 换行”,但 Telegram API 3900 字安全上限不等于老板手机阅读上限;约 1800 字 reviewer 审阅仍会形成一整面长墙。
- `StreamedMessageWriter` 改为先复用 `normalize_agent_output_for_im()` 归一化当前累计输出,再按 1400 字移动端阅读上限分段;分段优先选择空行、换行、句号或空格,避免按字符硬切。
- `agent_output_message()` 的 severity bullet 归一化从单换行改为 bullet 前空行,让 `• High` / `• Medium` 变成真正的审阅卡片分隔。
- `/overnight` 回执改成“老板秘书动线”:现在看 `/inbox`,回来接手看 `/morning`,查精确原文看 `/task <id>`,需要 HTML 看 `/view`,项目背景才看 `/brief`。
- `/aico-view` 现在是 `/view` 的别名,避免老板按产品名输入时被当成 unknown persona / adapter。
- 验证通过:targeted 25 passed;full clean env `env -u AICO_VIEW_TOKEN -u AICO_VIEW_ENABLED uv run pytest` **427 passed / 1 skipped**;`ruff check .`;`ruff format --check .`;`mypy src tests`;`git diff --check`。

**Round 141**(2026-06-04,Codex — delegate Telegram readability):
- 人类复验 `/overnight 为我准备好上线github的全部工作...` 后指出两类真实 IM 问题:
  implementer handoff 中 `<b>Heading</b><b>Heading</b>`、`<b>Decision</b>正文` 粘成一段;
  reviewer 输出中 `• High ...。• Medium ...` 多条 finding 被拼到同一行。
- 日志确认 task `4667de18-8bfd-40b1-911d-04a7bfec1c86` 正常完成,reviewer 子任务
  `5499a5ea-f184-452a-a555-86dc4cbaee85` 也正常完成;问题不是任务失败,而是 agent 流式
  chunk 被 `StreamedMessageWriter` 忠实累加后缺少 IM 结构分隔。
- 修复 `agent_output_message()`:agent 输出在进入 Telegram HTML sanitizer 或 rich text fallback 前,
  先做保守 IM normalization,只拆明显粘连的 native heading、已知 section label 和 `•` bullet。
- 不把规则写进 Telegram Channel,保持 core 继续输出平台无关 `MessageContent`;Telegram 仍只负责
  native HTML / spans 映射。
- 新增 native output + streaming 回归测试,覆盖 implementer 截图里的 `<b>Goal received</b>"..."`
  / `<b>Decision</b>正文` 以及 reviewer 文案里的 `。• High` 列表粘连。
- 验证通过:`env -u AICO_VIEW_TOKEN -u AICO_VIEW_ENABLED uv run pytest` **425 passed / 1 skipped**;
  `uv run ruff check .`;`uv run ruff format --check .`;`uv run mypy src tests`;`git diff --check`。

**Round 140**(2026-06-04,Claude — OSS public-launch readiness):
- 老板任务"为我准备好上线 GitHub 的全部工作,要奔着 1k 或 10k star 方向去设计和发力"。
- 收口 Round 137-139 三轮代码改动到 `launch/oss-public-readiness` 分支(包括
  Round 137 IM HTML snapshot、Round 138 协作风险边界修复、Round 139 `/overnight`
  handoff completeness guard)。
- 补齐 OSS 治理资产:`CODE_OF_CONDUCT.md`(Contributor Covenant 2.1 中英双语)、
  `.github/FUNDING.yml` 占位、`.github/dependabot.yml`(weekly pip + monthly Actions)。
- 新增 `docs/contributors/quickstart.md`:30 分钟内完成第一次 PR 的零门槛路径,完全
  跑在 no-token Release Room demo 上。
- 新增 `docs/launch/playbook.md`:面向 1k–10k star 的上线作战书,包括 Show HN /
  4 个 Reddit 子版位 / X / Bluesky / LinkedIn / dev.to 长文模板,D0 → D90 节奏,
  反指标清单和老板缺席护栏。
- 新增 `docs/launch/v0.1.0-release-notes.md`:v0.1.0 GitHub Release notes 草稿,
  可直接贴到 GitHub Release。
- README 增加 Contributing 段对 Contributor Quickstart + CoC 的引用,并把 Roadmap
  near-term 部分对齐到当前真实状态。
- `.github/ISSUE_TEMPLATE/config.yml` 增加 Discussions / Contributor Quickstart 入口。
- `SECURITY.md` 明确响应 SLA(72 小时确认 / 14 天修复)。
- `CONTRIBUTING.md` 顶部增加 first-time contributor 入口和 CoC 引用。
- 验证通过:`env -u AICO_VIEW_TOKEN -u AICO_VIEW_ENABLED uv run pytest` **422
  passed / 1 skipped**;`ruff check .`;`ruff format --check .`(141 files);
  `mypy src tests`(136 source files)。
- 关键决策:不在本轮做新功能,不动 v0.1.0 范围。所有上线工作通过文档 + 模板支撑,
  代码 surface 保持冻结,避免 Show HN 描述与实际产品不一致。

**Round 139**(2026-06-04,Codex — `/overnight` incomplete handoff guard):
- 人类复验 `/overnight 为我准备好上线github的全部工作...` 后,任务 `3f7d57c2` 只在 IM 打出半句 `Community 文件：写一个简短 Code of Conduct...`。
- 日志确认 Claude CLI 运行约 8 分钟后 return code 0,但 stdout 只有 1 个 chunk / 64 字符;SQLite snapshot 却被标成 `done`。这不是 Telegram 截断,而是 AICO 把“CLI 成功退出 + 任意 stdout”误当作可交接成功。
- 新增 offline delegation completion guard:仅对 `/overnight` 任务生效;当最终 `DONE` 输出过短或缺少 done / blocked / risks / next actions 基本段落时,改标 `failed` 并向 IM 发送 `Overnight delegation output incomplete`。
- `/goal` 继续走自己的 Outcome Grader,不复用 overnight handoff 验收;等待审批的 `/overnight` 也不会因空输出被误判失败。
- 验证通过:`env -u AICO_VIEW_TOKEN -u AICO_VIEW_ENABLED uv run pytest` **422 passed / 1 skipped**;`ruff check .`;`ruff format --check .`;`mypy src tests`;`git diff --check`。

**Round 138**(2026-06-03,Codex — `/overnight` collaboration risk boundary fix):
- 人类验收 `/overnight` 时触发真实失败:`Collaboration requested: implementer -> reviewer` 后 reviewer/Codex 子任务被拒绝为 `adapter codex cannot handle shell_exec tasks; use /claude`。
- 根因是协作 payload 带有 parent output context,但真实委托段使用 `Request:` 标签;`TextRiskAssessor` 只识别 `Current task:`,因此把 context 中的 `run pytest` / `git push` / `命令` 等词也纳入风险判定。
- 修复 `collaboration_payload()` 在带 source context 时用 `Current task:` 标记实际委托内容,保持 Codex read-only capability 边界不变,也不绕过 `/approve`。
- 新增回归测试覆盖 TaskBus 与 Orchestrator 两层:parent context 含 `run pytest` / `git push`,但 reviewer 只做风险审阅时仍按 read-only 派给 Codex;真正 shell/write 委托仍由现有风险门禁处理。
- 验证通过:`env -u AICO_VIEW_TOKEN -u AICO_VIEW_ENABLED uv run pytest` **419 passed / 1 skipped**;`ruff check .`;`ruff format --check .`;`mypy src tests`;`git diff --check`。未清理当前 shell 的 view env 时,旧 view 测试会因 401/默认启用预期失败,这是环境变量污染而非本轮代码失败。

**Round 137**(2026-06-02,Codex — aico-view IM HTML snapshot):
- 根据人类安全反馈修正 aico-view 产品入口:`AICO_VIEW_ENABLED=true` 不再表达"自动启动可访问 Web 服务",而是启用 IM 内 `/view [project]` 发送自包含 HTML 快照。
- 新增 `DocumentChannel` 可选附件协议;`TelegramChannel.send_document()` 通过 Bot API `sendDocument` 上传 `.html` 文件,不发送 localhost / 127.0.0.1 链接。
- 新增 `src/aico/view/snapshot.py`:生成 Boss Brief / recent timeline / trace details / memory 的单文件 HTML,内联 CSS,无外部静态资源。
- 新增 `src/aico/view/commands.py`:按当前 active project 生成 snapshot;非附件 Channel 降级为写入 `AICO_VIEW_OUTPUT_DIR` 并回 IM 提示路径。
- `src/aico/app/phase1.py` 新增 `AICO_VIEW_ENABLED` / `AICO_VIEW_OUTPUT_DIR`;`uv run aico-view` HTTP 服务仍保留为显式本机排障/隧道 dogfood,不会由 `AICO_VIEW_ENABLED` 自动启动。
- 新增 ADR-0036 `aico-view IM-delivered HTML snapshot`:写死安全边界——不开入站端口;但 HTML 内容会进入 Telegram 聊天记录,只发可信私聊/小群。
- 验证通过:`uv run pytest` **417 passed / 1 skipped**;`ruff check .`;`ruff format --check .`;`mypy src tests`;`git diff --check`。

**Round 136**(2026-05-31,Claude — Sprint V3 + 路线图全部完成):
- 落地 boss-first-grounding §6 Sprint V3:`aico-view` token 鉴权 + 部署文档 + 安全模型。**§6 路线图 9 个 sprint 全部完成**。
- 新增 `src/aico/view/auth.py`(< 90 行):`TokenGuard.from_env()` 三态决策——token 已设则验证;loopback 无 token 放行(本机便利);**非 loopback 无 token 全请求 401**(刻意拒绝裸暴露)。token 比较走 `secrets.compare_digest` 防 timing。
- `src/aico/view/app.py`:`build_view_app(..., token_guard=None)` 注入 guard;三个受保护路由 `/`、`/trace/{id}`、`/memory` 调 `guard.check(request)`;`/healthz` 和 `/static/style.css` 不受保护(liveness probe + 公开样式)。
- 新增 ADR-0035 `aico-view token auth posture`(Accepted):写死行为矩阵 + 不做的事(无多用户、无 OIDC、无 rate limit)。
- 新增 `docs/human/aico-view-deploy.md`:三种形态(localhost / ngrok / Cloudflare tunnel)+ 安全模型 + env 速查 + "不要做的事" 清单。
- 验证通过:`uv run pytest` **411 passed / 1 skipped**(原 394 + 17 V3);ruff / format / mypy 全绿。
- CHANGELOG 加 `AICO_VIEW_TOKEN` 说明;quickstart 链到 deploy 文档。
- 在 `docs/architecture/boss-first-grounding.md` §6 表格给 V3 标 ✅ 引用 Round 136。
- **路线图状态**:M1 ✅ / M2 ✅ / M3 ✅ / A1 ✅ / A2 ✅ / A3 ✅ / V1 ✅ / V2 ✅ / V3 ✅。Phase 8 复盘 / Future F-1 F-2 / Orchestrator 拆分(B-005)留作下一阶段。

**Round 135**(2026-05-31,Claude — Sprint A3):
- 落地 boss-first-grounding §6 Sprint A3:lead 内务 `/timeline` 和 `/rollback memory|experience|task`,以及新增 `AuditEventType.ROLLBACK_PERFORMED`。
- 新增 `src/aico/core/timeline_rollback_commands.py`(< 300 行):
  - `TimelineCommandHandler` 支持 `--since 24h --source audit|memory|task --limit 30 --trace <prefix>`;解析失败给 Usage,过滤不到事件给 "no events in window"。
  - `RollbackCommandHandler`:`/rollback memory <id>` archive fact;`/rollback experience <id>` active→CANDIDATE;`/rollback task <id>` 只写 ROLLBACK_PERFORMED audit,**不级联**撤 memory/experience(避免假装撤了 file/shell)。
- `src/aico/core/models.py` AuditEventType 加 `ROLLBACK_PERFORMED`。
- `src/aico/core/task_bus.py` 加 `audit_log()` accessor 暴露给 RollbackCommandHandler。
- `src/aico/core/orchestrator.py`:`_setup_boss_and_lead_handlers` 加 2 个 handler 实例化,命令分发加 2 个 elif(遵守 B-005 workaround,主体 +4 行,新逻辑全部进新模块)。
- `src/aico/core/commands.py`:`TIMELINE` / `ROLLBACK`;`TIMELINE` 进 lowered 短命令集;help 加两行。
- 新增 ADR-0034 `Rollback granularity boundary`(Accepted):写死 `/rollback task` 只 audit、不级联;永远不撤 git/shell/file。
- 验证通过:`uv run pytest` **394 passed / 1 skipped**(原 385 + 9 A3);ruff / format / mypy 全绿。
- CHANGELOG 加 `/timeline` `/rollback` 说明;`docs/human/daily-ops.md` 新增 "Lead 内务命令" 段。
- 在 `docs/architecture/boss-first-grounding.md` §6 表格给 A3 标 ✅ 引用 Round 135。

**Round 134**(2026-05-31,Claude — Sprint V2):
- 落地 boss-first-grounding §6 Sprint V2:aico-view 三视图末尾追加 IM deep-link 按钮。
- 新增 `src/aico/view/deep_link.py`(< 90 行):`DeepLinkSettings(telegram_bot_username)` + `load_deep_link_settings_from_env()` 读 `AICO_VIEW_TELEGRAM_BOT_USERNAME`(可选);`render_command_link` 在有 bot 时生成 `https://t.me/<bot>?text=<url-encoded>`,无 bot 时降级为 `cmd-copy` 文本提示(老板复制粘贴)。
- `src/aico/view/app.py` 三视图都接 `deep_link_settings`:Timeline 末尾给 `/inbox` `/morning` `/undo`;Trace 末尾给 `/why <short>` `/task <short>`;Memory 每条 atom 给 promote / archive / forget(按 status + kind 选)。CSS 加 `.cmd-links` `.cmd-link` `.cmd-copy` 样式(pill 按钮 + 暗色)。
- 关键边界:**仍然只读**。deep link 只是把命令预填到 IM 输入框,实际写入仍走 IM(Channel + 现有审批/审计)。Feishu 暂用 cmd-copy 降级(Feishu 无标准 deep link)。
- 验证通过:`uv run pytest` **385 passed / 1 skipped**(原 377 + 8 V2);ruff / format / mypy 全绿。
- 不开 ADR(V2 是 V1 + ADR-0033 的延伸,不引入新决策)。
- 在 `docs/architecture/boss-first-grounding.md` §6 表格给 V2 标 ✅ 引用 Round 134。

**Round 133**(2026-05-31,Claude — Sprint V1):
- 落地 boss-first-grounding §6 Sprint V1:`aico-view` 只读 FastAPI Web,三视图 mobile-first。
- 新增 `src/aico/view/app.py`(< 300 行):`build_view_app(settings)` 返回 FastAPI app;Timeline `/`、Task Trace `/trace/{trace_id}`(支持短 ID 前缀匹配)、Memory Tree `/memory`、`/healthz`、`/static/style.css`。
- 新增 `src/aico/app/view_cli.py` + `pyproject.toml [project.scripts]` `aico-view = "aico.app.view_cli:main"`;env 配置 `AICO_AUDIT_LOG_PATH` / `AICO_MEMORY_PATH` / `AICO_STATE_DB_PATH` / `AICO_VIEW_PROJECT_IDS` / `AICO_VIEW_HOST` / `AICO_VIEW_PORT`。
- 直接复用 ADR-0030 UnifiedEventIndex,每次请求重建 index(JSONL 解析快、避免缓存失效);Memory Tree 区分 experience(在前)和 fact(在后)。
- 关键边界:**Read-only**(任何 POST/PUT/DELETE 都 405)、**不挂 phase1 runtime/channel/adapter**、**无 Jinja2/JS framework**(f-string + html.escape);默认 `127.0.0.1`,不上公网鉴权(V3 加 token)。
- 新增 ADR-0033 `aico-view read-only mobile web surface`(Accepted)。
- 验证通过:`uv run pytest` **377 passed / 1 skipped**(原 365 + 12 V1);`uv run ruff check .`;`uv run ruff format --check .`;`uv run mypy src tests`。
- CHANGELOG 加 `aico-view` 说明;`docs/human/quickstart.md` 加启动指引。
- 在 `docs/architecture/boss-first-grounding.md` §6 表格给 V1 标 ✅ 引用 Round 133。

**Round 132**(2026-05-31,Claude — Sprint A2):
- 落地 boss-first-grounding §6 Sprint A2:boss-only `/undo` 和 `/why`,`/inbox` 和 `/morning` 内嵌 Recent activity 摘要。
- 新增 `undo_why_commands.py`(< 280 行):`UndoCommandHandler` 撤销最近 24 小时内 AICO 内部 memory 变更(experience promote → CANDIDATE / archive → ACTIVE / fact append → archive),回复显式写明"不撤 git / shell / file";`WhyCommandHandler` 按 short_id 前缀匹配走 UnifiedEventIndex 的 trace 序列。
- `inbox.py` / `morning.py` 加可选 `recent_events` 参数,渲染 "Recent activity" 段 + 一行 `/why <short_id>` 提示。
- `orchestrator.py` 新增 `_build_event_index` 私有方法 + 模块级 helper `_build_orchestrator_event_index`(派生只读 UnifiedEventIndex,不写真相);`__init__` 拆为 `_setup_command_handlers` → `_setup_coordinators` / `_setup_boss_and_lead_handlers` / `_setup_workflow_handlers` 三个子方法(每个 <40 行,满足 100 行硬限)。
- `commands.py` 加 `CommandName.UNDO` / `WHY`,help 加两行。
- 新增 ADR-0032 `Undo and Why scope boundary`(Accepted)。
- 新增 BLOCKER B-005 `Orchestrator class size regression`(🟡 DEFERRED):类规模重新涨到 ~585 行,后续 sprint 加 handler 必须遵守"主体不变"边界,V3 完成后做独立拆分。
- 验证通过:`uv run pytest` **365 passed / 1 skipped**;ruff / format / mypy 全绿。
- CHANGELOG 加 `/undo` / `/why` / Recent activity 说明。
- 在 `docs/architecture/boss-first-grounding.md` §6 表格给 A2 标 ✅ 引用 Round 132。

**Round 131**(2026-05-31,Claude — Sprint M3):
- 落地 boss-first-grounding §6 Sprint M3:Outcome Grader verdict 反向回写 experience confidence / verdict_hits / verdict_misses / injection_count。
- `outcome_grader.py`:新增 `GraderVerdict` StrEnum + `parse_verdict(output)` 容错解析(大小写、Markdown emphasis 都接受);未匹配返回 `None`,**不猜测**。
- `memory.py`:`MemoryStore` Protocol + `JsonlMemoryStore` 实现 `update_experience_meta(memory_id, *, confidence_delta, verdict_hits_delta, verdict_misses_delta, injection_count_delta)`,clamp 到 [0, 1]。
- 新增 `experience_feedback.py`(< 90 行):`injected_experience_ids(task)` + `apply_verdict_to_owner_experiences(store, owner_task, verdict)`;PASS→+0.05、PARTIAL→0、FAIL→-0.10;PASS/PARTIAL 计 hit、PARTIAL/FAIL 计 miss;每次都 injection_count+1。
- `goal_brief_commands.py`:GoalBriefCommandHandler 注入 `memory_store`,grader 跑完后捕获 output → parse_verdict → apply_verdict;**同时把 grader task trace_id 接到 owner_task.trace_id**(完成 ADR-0030 留给 M3 的 grader trace 续接)。
- `orchestrator.py`:GoalBriefCommandHandler 实例化传入 memory_store(主体仅 +1 行)。
- 验证通过:`uv run pytest` **360 passed / 1 skipped**(原 347 + 12 feedback 单测 + 1 E2E);ruff / format / mypy 全绿。
- 关键边界:experience meta 反向回写**只在 grader 完成时发生**,普通 task 注入不主动 +1 injection_count(否则未被验收的注入会污染 confidence)。
- 不开 ADR(M3 是 M1+M2+ADR-0030 留作业的兑现,不引入新决策)。
- 在 `docs/architecture/boss-first-grounding.md` §6 表格给 M3 标 ✅ 引用 Round 131。

**Round 130**(2026-05-31,Claude — Sprint M2):
- 落地 boss-first-grounding §6 Sprint M2:`/experience` 命令 + ExperienceLayer prompt 注入。
- `MemoryStore` Protocol 加 `promote_experience(memory_id, *, applies_to, triggers)` + `list_experiences(scope, *, role_id, trigger_keys, statuses)`;`JsonlMemoryStore` 实现完整。
- `prompt_stack.py` 增加 `_experience_section`,在 `_memory_section` 后、`_runtime_section` 前;形成"事实 → 经验 → 任务"认知链。
- `orchestrator_task_factory.py`:`task_for_assignment` 装配前调 `list_experiences(role_id=assignment.role)`,装配后把 memory_ids 写到 task metadata key `aico.injected_experience_ids`(M3 grader 反向回写的前置)。
- 新增 `experience_commands.py` ExperienceCommandHandler:`review`(列 candidate)/`list [role]`(列 active)/`promote <id> [as <role,role>]`(candidate → active 并记录 applies_to)/`archive <id>`(active → archived)。
- 关键边界:严格 lead 内务,boss-first 命令组不包含 `/experience`;experience 与 fact 共用存储但走独立注入通道(避免污染 retrieval governance)。
- 新增 ADR-0031 `Experience as injectable memory`(Accepted)。
- 验证通过:`uv run pytest` **347 passed / 1 skipped**;`uv run ruff check .`;`uv run ruff format --check .`;`uv run mypy src tests`。
- CHANGELOG 加 `/experience` 命令说明。
- 在 `docs/architecture/boss-first-grounding.md` §6 表格给 M2 标 ✅ 引用 Round 130。

**Round 129**(2026-05-31,Claude — Sprint A1):
- 落地 boss-first-grounding §6 路线图 Sprint A1:Audit + trace_id + Unified Event Index。
- `src/aico/core/models.py`:`AuditEvent`、`Task` 都新增 `trace_id: str | None = None`(default None,向后兼容)。
- `src/aico/core/memory.py`:`MemoryAtom` 新增 `trace_id: str | None = None`。
- `src/aico/core/audit.py`:`record(...)` 和 `record_event(...)` 自动从 `task.trace_id || task.task_id` 取 trace_id,默认全链路传播;memory_broadcast 等 task-less 调用 fallback 到 `task_id` 参数本身。
- 新增 `src/aico/core/unified_event.py`(< 150 行):`UnifiedEvent` / `UnifiedEventIndex` Protocol / `InMemoryUnifiedEventIndex`,把 audit / memory / task 三源按 trace_id 聚合;`short_event_id` / `short_memory_id` / `short_trace_id` 三个 IM 渲染辅助函数(复用现有 `short_id_text`)。
- 关键边界(写进 ADR-0030):Index **派生只读、不拥有真相**;真相仍在 audit JSONL / memory JSONL / SQLite task store;一旦运行新代码,JSONL 升级是单向门(`FrozenModel.extra="forbid"` 阻止老代码读新字段)。
- 新增 ADR-0030 `Unified Event Index — read-only cross-source trace view`,Accepted。
- PITFALLS 新增 P-033 "Memory/Audit JSONL 升级是单向门",索引新增"持久化与 schema 兼容"分类。
- 子任务 trace_id 通过 `task.model_copy(update=...)` 免费继承;**唯一例外是 Grader follow-up**,它是新顶层 task,trace 默认 = 自己 task_id,留 M3 把它接到 graded_task 的 trace。
- 验证通过:`uv run pytest` **338 passed / 1 skipped**(330 + 3 unified_event + 3 audit + 2 task_bus);`uv run ruff check .`;`uv run ruff format --check .`;`uv run mypy src tests`。
- 在 `docs/architecture/boss-first-grounding.md` §6 表格给 A1 标 ✅ 引用 Round 129。

**Round 128**(2026-05-31,Claude — Sprint M1):
- 落地 boss-first-grounding §6 路线图 Sprint M1:Memory + Experience 数据层分层。
- `src/aico/core/memory.py`:新增 `MemoryKind` enum(`fact` / `experience`)和 `ExperienceMeta` 模型(`applies_to` / `triggers` / `injection_count` / `verdict_hits` / `verdict_misses`);`MemoryAtom` 增加 `kind` 与 `experience` 两字段 + validator(experience kind 必须带 meta、fact kind 不得带 meta)。
- `src/aico/core/dream.py`:Dream 输出从普通 candidate memory 升级为 `kind=EXPERIENCE` 的 candidate experience,`experience.triggers` 携带 candidate key(如 `failed:adapter_idle_timeout`)。文案 `candidate memory only` → `candidate experience only`,提示晋升后才注入 prompt。
- 关键边界:M1 仅做数据层,**不**注入 prompt(留 M2),**不**做 grader 反馈回写(留 M3)。
- JSONL 向后兼容已验证:老记录无 `kind` 字段 → 默认 `FACT`(测试 `test_jsonl_store_loads_legacy_atom_without_kind` 覆盖)。
- 验证通过:`uv run pytest` 330 passed / 1 skipped;`uv run ruff check .`;`uv run ruff format --check .`;`uv run mypy src tests`。
- 不开 ADR(只是字段扩展,ADR-0020/0021/0022 已覆盖范围)。
- 在 `docs/architecture/boss-first-grounding.md` §6 表格给 M1 标 ✅ 引用 Round 128。

**Round 127**(2026-05-29,Claude):
- 与人类两轮脑暴 absence-first 边界、lead 主动机制、Memory/Experience 分层、Audit/Rollback 可视化和命令爆炸问题。
- 决策:近期高优为三块基础能力——Memory + Experience 分层、Audit + Rollback(+ aico-view 移动只读 web)、之后再回 Absence Loop 加固。Lead 主动机制(Standing Charter / Proposal Queue)和 Team Karpathy Loop 标记为 Future,暂不实现。
- 输出 [`docs/architecture/boss-first-grounding.md`](docs/architecture/boss-first-grounding.md):基于源码核实的痛点 P1-P6、解法 §3、L1-L6 分层架构图(drawio xml 嵌入)、sprint 路线图 M1/M2/M3/A1/A2/A3/V1/V2/V3 和新会话落地操作指引。
- 关键 boss-first 决策:命令分层(老板只看 6 个核心动作);`/undo` 与 `/why` 替代多 ID 命令;trace 深度可视化走 aico-view(只读,写操作回 IM,符合 absence-first)。
- 关键边界:`/undo` 与 `/rollback` 只撤 AICO 内部状态(memory / experience / appointment),不撤 git / shell / file。
- 在 README 和 `docs/architecture/overview.md` 加入了对新设计文档的入口指针。
- 本轮只新增设计文档与索引,未改运行代码,未跑测试。

**Round 126**(2026-05-27,Codex):
- 按人类真实 IM dogfood 反馈校准当前待办:Phase 8 Absence Loop 验收已执行,但效果不佳,暂不继续投入该方向;运行侧改回 `AICO_PREFER_NATIVE_CHANNEL_FORMAT=false`。
- 关闭 Phase 5 真实协作 smoke test 高优待办:人类确认真实 IM 下协作能触发,后续不再把它作为下一轮回归项。
- 保留 Lead decision workflow、Goal Brief v0、Release Room、Feishu、Codex bind / Claude resume 和 usage 上报等原待办。
- 将“开源首屏二次验收:AI agent 开发者 / 个人开发者视角”提升为下一轮最高优先级。
- 本轮只更新状态与交接文档,未改运行代码,未跑测试。

**Round 125**(2026-05-27,Codex):
- 人类反馈真实 Telegram 输出把 `Still running: no adapter output for 120s...` 和后续 native HTML 结果拼到同一条消息里,导致 `<b>` / `<code>` 等标签裸露,列表也粘成一段。
- 根因确认:`OutputType.STATUS` quiet heartbeat 过去通过 `StreamedMessageWriter.append()` 写入 `_current_text`;后续 agent 输出到达时,状态行和 native HTML 混在同一缓冲区,`/task <id>` 的 `<id>` 还会让 native HTML 验证失败并回退。
- 修复 `StreamedMessageWriter.show_status()`:heartbeat 只临时编辑当前消息,不进入最终输出缓冲区;真实输出到达后会替换 heartbeat。
- `Orchestrator` 对 `OutputType.STATUS` 改为 `show_status()` 后 `continue`,确保 status 不进入 captured output、native HTML 验证或最终 IM 内容。
- 补充 Telegram native output prompt:标题、段落、列表项要分行,bullet 使用 `•`,不要使用 Markdown `- ` bullet。
- 新增 `tests/unit/test_streaming.py`,覆盖 heartbeat 不污染 native final output,以及输出开始后 late status 不覆盖结果。
- 验证通过:`uv run pytest` 325 passed / 1 skipped;`uv run ruff check .`;`uv run ruff format --check .`;`uv run mypy src tests`;`git diff --check`。

**Round 124**(2026-05-27,Codex):
- 人类真实 dogfood `/goal implementer inspect inbox handoff ...` 后,Telegram 收到裸 `<b>` / `<blockquote>` / `<pre>` 标签,说明 native Telegram HTML 输出被打回 fallback。
- 根因确认:模型输出整体是合法 Telegram HTML,但 `<pre>` 文本里包含 `/task <id>`、`/task <id>` 这类占位符;Python HTML parser 把 `<id>` 当 unknown tag,旧 sanitizer 因 unsupported tag 拒绝整条 native 输出。
- 修复 Telegram HTML sanitizer:在 `<pre>` / `<code>` literal block 内遇到 unknown tag 或 placeholder 时,安全转义为文本保留;literal block 外的 unsupported HTML 仍会失败并回退。
- 新增单测覆盖 `<pre>/task <id></pre>` 会变成 `<pre>/task &lt;id&gt;</pre>` 并继续走 native Telegram HTML。
- 验证通过:`uv run pytest` 323 passed / 1 skipped;`uv run ruff check .`;`uv run ruff format --check .`;`uv run mypy src tests`;`git diff --check`。

**Round 123**(2026-05-27,Codex):
- 人类指出 `rich_text_message()` 适配模型输出到 Telegram spans 的 case 可能无限膨胀,要求另起一条链路验证“让模型直接输出 Channel 支持格式,失败再回退”。
- 新增 opt-in native output contract:`AICO_PREFER_NATIVE_CHANNEL_FORMAT=true` 时,Telegram task prompt 会要求 agent 使用 Telegram Bot API HTML 子集,而不是 Markdown。
- 新增 `MessageNativeFormat.TELEGRAM_HTML` 和 `native_output.py`;agent 输出先经过 Telegram HTML 白名单 sanitizer,只允许安全标签且不允许属性/unsupported tag。
- `StreamedMessageWriter` 优先发送 native Telegram HTML;如果模型输出 Markdown table、fenced code 或 unsupported HTML,自动回退到 `rich_text_message()`。
- Telegram Channel 支持 `MessageContent.native_format=telegram_html` 时直接发送 HTML parse mode,不再把 native HTML 当 spans 重写。
- 修复 fallback 中单行 fenced code(```uv run pytest```)被吞的问题。
- 验证通过:`uv run pytest` 322 passed / 1 skipped;`uv run ruff check .`;`uv run ruff format --check .`;`uv run mypy src tests`;`git diff --check`。

**Round 122**(2026-05-27,Codex):
- 人类确认 Telegram 侧返回格式仍有较大问题:collaboration requested 没有富文本化;模型复杂 Markdown 输出没有被稳定转为 Telegram HTML;`/recall` 中带粘连 `## DecisionYes` 的记忆内容难读。
- 确认当前架构:核心不直接输出 Telegram Markdown,而是输出 `MessageContent.text + MessageTextSpan`;Telegram Channel 在有 spans 时用 `parse_mode=HTML` 发送。
- 将 renderer 从“逐命令补 spans”升级为通用 IM Markdown normalization + span rendering:先修正模型常见 Markdown 结构,再生成平台无关 spans。
- `rich_text_message()` 新增粘连 Markdown heading 拆分、已知 heading 内容拆分、Markdown table 到等宽 IM table、fenced code block code span、大小写无关 label span。
- `Collaboration requested` 内置提示改为结构化富文本消息,显示 source / target。
- 新增单测覆盖粘连 heading、Markdown table、fenced code block、Telegram HTML 输出和 collaboration requested spans。
- 验证通过:`uv run pytest` 315 passed / 1 skipped;`uv run ruff check .`;`uv run ruff format --check .`;`uv run mypy src tests`;`git diff --check`。

**Round 121**(2026-05-27,Codex):
- 人类反馈纯英文 agent 回复有时阅读吃力,要求新增一个通用语言切换命令,能力只限制 agent 回复语言,默认英文。
- 新增 `/language [en|zh]` 命令;`/language` 查看当前 chat 的 agent response language,`/language zh` 设置为简体中文,`/language en` 恢复默认英文。
- 新增 `ResponseLanguageStore`,按 `session_scope` 记录偏好;所有真正提交给 agent 的 task 在 `_run_task()` 前统一注入 `Response language` 约束,覆盖 plain task、project role task、Goal、broadcast 和 collaboration。
- 语言约束只作用于 agent payload,不强制翻译 AICO 内置命令、代码、CLI 片段、路径、日志、标识符、协议关键字和严格 JSON/schema。
- 修复实现中发现的一个风险:语言提示词不能包含 `shell command` 等风险关键词,否则会让普通任务误触发 approval gate;最终提示词改为 `CLI snippets` 并保留 schema 约束。
- 验证通过:`uv run pytest` 311 passed / 1 skipped;`uv run ruff check .`;`uv run ruff format --check .`;`uv run mypy src tests`;`git diff --check`。

**Round 120**(2026-05-27,Codex):
- 人类 dogfood 确认 `/inbox` 和 `/morning` 没问题,但反馈 `/goal`、Outcome Grader 和 `/recall` 返回没有 IM Markdown/富文本格式化,`/dream` 输出也难以判断是否正确。
- 修复 Goal Brief、Outcome Grader、Dream review、Memory remembered/recall/archived/no-result 等内置命令消息,统一走 `rich_text_message()`,让标题、无序列表、字段 label 和 slash command 在 Telegram/IM 中可格式化。
- 扩展 `message_rendering` 的 label keys,覆盖 `owner`、`tracking`、`goal`、`grader`、`graded_task`、`query`、`purpose`、`evidence` 等 Phase 8 输出字段。
- 优化 `/dream`:从“逐条吐旧 task 候选”改为按阻塞/失败原因聚合成 reusable lesson candidate,并在输出中解释 Meaning / Effect / Next,明确 candidate memory 不会自动注入 prompt。
- 新增/更新单测覆盖 Goal/Dream/Recall 富文本 spans 和 Dream 聚合候选。
- 验证通过:`uv run pytest` 309 passed / 1 skipped;`uv run ruff check .`;`uv run ruff format --check .`;`uv run mypy src tests`;`git diff --check`。

**Round 119**(2026-05-26,Codex):
- 人类要求把刚新增的四个 Sprint 按顺序执行,并给出 human 可逐条 dogfood 的问题样例、预期观测指标和效果。
- Sprint 2 完成:`/morning` 新增 active-project 手动早报,汇总 done、blocked、risks、overnight handoffs 和 next actions,让老板早上不必翻 `/tasks`。
- Sprint 3 完成:Goal Brief 任务完成后自动寻找 tester / reviewer 生成 Outcome Grader 任务;grader prompt 要求 verdict、evidence、gaps 和 boss_next_action,且被标记为内部只读验收任务。
- Sprint 4 完成:`/dream` 从当前项目任务状态生成 candidate runbook memory,只写 `candidate` 状态,默认不会进入 Prompt Stack。
- Sprint 5 完成:MemoryStore / MemoryRetriever 默认使用本地 hybrid scorer,支持 exact phrase、短语 overlap 和中英 alias fallback,治理边界仍由 scope / purpose / sensitivity / confidence 控制。
- 验证通过:`uv run pytest` 309 passed / 1 skipped;`uv run ruff check .`;`uv run ruff format --check .`;`uv run mypy src tests`;`git diff --check`。

**Round 118**(2026-05-26,Codex):
- 人类确认把 Phase 8 后续 P0-P4 全部纳入短期可落地计划,并要求写入文档后直接进入研发。
- 新增 ADR-0029 `Phase 8 Absence Loop`,把 Phase 8 明确为“下任务 -> 执行 -> 审批/叫停 -> 验收 -> 早上接手 -> 经验沉淀 -> 下次召回”的老板缺席闭环。
- 新增 `docs/playbooks/phase-8-absence-loop.md`,把 Sprint 1 actionable inbox、Sprint 2 morning handoff、Sprint 3 outcome grader、Sprint 4 Dream/runbook memory、Sprint 5 hybrid retrieval 写成直接可问的 IM 验收路径。
- 更新 playbook / ADR 索引,让后续 Agent 接手时先按 sprint 队列执行,不要把 Dream、self-improving 和 retrieval backend 一锅炖。
- 进入 Sprint 1 研发:`/inbox` 新增 `First action`,并把待审批、running、failed/interrupted/rejected、overnight handoff、Goal/decision、collaboration follow-up 都改成带明确下一步命令的动作项。
- 验证通过:`uv run pytest` 305 passed / 1 skipped,`uv run ruff check .`,`uv run ruff format --check .`,`uv run mypy src tests`,`git diff --check`。

**Round 117**(2026-05-26,Codex):
- 人类继续追问 reviewer/Codex 为什么同一条 `/ask reviewer review whether the Phase 8 inbox plan violates approval or audit boundaries...` 仍然 120/240 秒只有 heartbeat。
- 日志确认新 task `3be492f3` 已 accepted 并进入 `Stream start`;SQLite 显示 payload 约 1996 字符;`ps` 确认 Codex 子进程确实在跑且命令中包含完整 reviewer prompt。
- 产品判断:这不是问题太难,也不是 `/ask` 没交给 Codex;短 read-only boundary review 不应 6 分钟没有任何 stdout。
- 根因判断:Round 116 关闭 stdin 后仍卡住,下一层是 stderr pipe。Codex CLI 会把运行头、hook、工具日志和 warning 写 stderr;AICO 过去只在进程退出后读 stderr,可能导致 pipe 写满后反压阻塞,stdout 永远出不来。
- 修复 `_run_task()` 在子进程启动后立即后台 drain stderr,仅保留 tail 用于失败错误内容;成功任务不把 stderr 噪音推给 IM。
- 新增单测构造“stderr 不被读取则 process.wait 不返回”的场景,确认 adapter 会并发 drain stderr。
- 验证通过:`uv run pytest` 305 passed / 1 skipped,`uv run ruff check .`,`uv run ruff format --check .`,`uv run mypy src tests`,`git diff --check`;结构扫描无单类 >500 或单函数 >100。
- 人类真实 IM 复验确认改动有效,reviewer/Codex 长任务卡住问题关闭。

**Round 116**(2026-05-26,Codex):
- 人类验证 Round 115 heartbeat 生效,但新 task `0e72ac63` 连续显示 `Still running...` 到 1680 秒仍没有结果。
- 日志和 SQLite 状态确认该任务已被 Codex 接收并进入 `Stream start`,payload 约 1996 字符,不是异常巨大的 prompt;没有任何 `type=text` 输出。
- 最小 Codex CLI smoke 在相同用户权限下 4 秒返回 `AICO_SMOKE_OK`,说明不是 Codex CLI、账号或网络整体不可用。
- 根因判断:Adapter 启动子进程时未显式关闭 stdin;Codex 0.125 `exec` 会尝试读取 stdin 作为 additional input,若继承到不会 EOF 的 stdin,会长期等待而没有 stdout。
- 修复 `_create_process()` 为 `stdin=DEVNULL`,让 Claude/Codex/optional CLI adapter 都以真正非交互形态启动。
- 新增单测覆盖子进程创建时 stdin 关闭,并更新 CHANGELOG、Phase 5 playbook 和 P-026。
- 验证通过:`uv run pytest` 304 passed / 1 skipped,`uv run ruff check .`,`uv run ruff format --check .`,`uv run mypy src tests`,`git diff --check`。
- 注意:当前已经 running 的 `0e72ac63` 不会自动获得修复,需要 `/interrupt 0e72ac63` 后重启 AICO 再提交。

**Round 115**(2026-05-26,Codex):
- 排查人类真实 IM 长任务 `01ddaa36`:日志确认 Codex adapter 已接收任务、CLI 进程已启动并进入 `Stream start`,但 14 分钟以上没有 stdout chunk 或退出事件;这不是路由提交失败,而是 provider 长静默导致 IM 缺少活性反馈。
- 产品判断:Round 114 放宽 idle timeout 后,长任务不应被 5 分钟误杀,但 absence-first 仍要求老板离开后能看到“员工还在工作”、能从 IM 汇总待处理事项、能随时 `/interrupt`。
- 新增 Adapter quiet heartbeat:底层进程存活但长时间无 stdout 时产出 `OutputType.STATUS`,IM 显示 `Still running...`;TaskBus 保持任务 `running`,并把 status 写入 reason。
- `OutputType.STATUS` 不进入普通任务 captured output,避免污染 lead decision memo、Goal Brief 结果或协作上下文。
- 新增 `/inbox` 只读命令,按当前 active project 汇总待审批、running 静默任务、failed/interrupted/rejected、`/overnight` 工单、Goal Brief / lead decision 和协作 follow-up。
- 同步更新 daily ops、Phase 5 / Phase 8 playbook、CHANGELOG 和 P-025。
- 验证通过:`uv run pytest` 303 passed / 1 skipped,`uv run ruff check .`,`uv run ruff format --check .`,`uv run mypy src tests`,`git diff --check`。

**Round 114**(2026-05-25,Codex):
- 排查人类下午真实 IM dogfood:`/ask reviewer review whether the Phase 8 inbox plan violates approval or audit boundaries...` 再次返回 `ERROR: adapter output idle timeout after 300s`。
- 产品判断:5 分钟对“公司员工”不是异常长任务;在 absence-first 场景里,no-output timeout 不能等同于 task runtime limit,否则老板不在时会误杀正常长 review / dogfooding。
- 将 Codex / Cursor / CodeFlicker / Trae / Gemini optional CLI adapter 默认 `output_idle_timeout_seconds` 从 300 秒放宽到 1800 秒。
- `Phase1Settings` 允许 `AICO_*_OUTPUT_IDLE_TIMEOUT_SECONDS=0`,启动 runtime 时会转换为 `None`,即禁用自动 no-output idle timeout;仍可用 `/interrupt <task_id>` 远程叫停。
- 更新 daily ops、Phase 5 collaboration playbook、optional adapter playbook 和 PITFALL P-014 / P-022,明确默认 1800 秒、`0` 禁用、这是 no-output guard 不是任务总时长限制。
- 新增/更新测试覆盖 optional adapter 默认 1800 秒和 `0` 禁用。
- 验证通过:`uv run pytest` 301 passed / 1 skipped,`ruff check .`,`ruff format --check .`,`mypy src tests`,`git diff --check`。

**Round 113**(2026-05-25,Codex):
- 排查人类真实 IM dogfood:`/ask reviewer review whether the Phase 8 inbox plan violates approval or audit boundaries...` 首次任务 `f9d9990f` 被临时任命到 `claude-code`,新 provider session 启动后 7 分钟无 stdout,被人类 `/interrupt` 后收口为 `failed / task interrupted`。
- 继续排查后续成功输出任务 `f8e6c321`:reviewer 输出了 `@implementer: please reflect (a)-(d) ...`,系统触发 `Collaboration requested: implementer -> implementer`,但 child task 只收到短指令,没有收到 reviewer 前文中定义的 (a)-(d),导致 implementer 回答“缺少上下文”。
- 修复协作 handoff:触发 child task 时会把父任务截至协作指令前的可见输出作为 `Context from ... output so far` 注入 child payload,避免引用型短指令丢上下文。
- 修复协作来源展示:project appointment 任务优先用 `aico.assignment_role` 作为协作来源和 audit actor,避免 reviewer 被底层 claude/implementer persona 显示成 `implementer -> implementer`。
- 新增回归测试覆盖 parent context 传递和 assignment role 来源展示。
- 验证通过:`uv run pytest` 300 passed / 1 skipped,`ruff check .`,`ruff format --check .`,`mypy src tests`,`git diff --check`。

**Round 112**(2026-05-25,Codex):
- 按人类选择的方案 C,新增并强化 AICO 的"老板不在场假设",但不改写北极星三句话正文。
- `NORTH_STAR.md` 在第一句业务价值下新增"老板缺席操作模型(Absence-first)",明确 AICO 默认老板不在电脑前,通过 IM 指挥本地 AI CLI 团队继续工作。
- 将 AICO 与 OMC / CoWork OS 的边界写清:OMC 偏浏览器里经营 AI 公司,CoWork OS 偏桌面 AI super app,AICO 偏离开电脑后的远程异步托管和交接。
- 新增 5 个后续功能取舍问题:只靠 IM 能不能下达、离开后能不能推进、风险能不能等审批、早上能不能看懂、出问题能不能审计/叫停/恢复。
- `STATUS.md` 更新宏大叙事和"老板不在场假设",并把 Phase 8 operator inbox / morning handoff 重新锚定为 absence-first 的关键拼图。
- 本轮只更新产品目标与交接文档,未改运行代码,未跑单测。

**Round 111**(2026-05-24,Codex):
- 排查人类真实 IM 反馈:两条验证命令只留下 `4697ce83... [codex]: running` 与 `4c31d567... [codex]: running`。
- 日志确认两条任务均由 Codex 接收后 300 秒无 stdout,最终触发 idle timeout;当时没有产生 lead decision memo 或 reviewer child task 的可见结果。
- 修复 `/ask lead ...` 语义:`lead` / `default` 现在会解析到当前项目 default assignment,使老板可用自然 lead 说法触发 lead decision workflow。
- 修复协作指令解析:Adapter 输出中的 `@reviewer: ...` 不再必须是第一条非空行;模型先输出计划、后输出 reviewer 指令也能触发 child task。
- 修复协作输出展示:含协作指令的多行输出会保留非指令正文,不会为了触发 child task 把前面的计划正文吞掉。
- 新增回归测试覆盖 lead alias、后续行协作指令、正文保留和现有 lead decision / collaboration 行为。
- 验证通过:`pytest` 298 passed / 1 skipped,`ruff check .`,`ruff format --check .`,`mypy src tests`。

**Round 109**(2026-05-22,Codex):
- 按人类最新反馈校准待办状态:Adapter appointment / concurrency 真实 IM 回归已由人类验证完成,不再放在下一轮高优队列。
- Memory Retrieval 真实 IM 验收已由人类验证完成,不再放在下一轮高优队列。
- 将剩余真实 IM 待办改写为“真实问题列表 + 预期效果”,避免下一轮只按标题重复执行。
- 本轮只更新状态与交接文档,未改运行代码,未跑测试。

**Round 108**(2026-05-21,Codex):
- 人类完成 Telegram render 复验:`/agents` 和 `/appoint codex as tester` 观感“好很多”,本轮关闭该问题状态。
- 继续推进高优能力:实现 `/overnight` 托管工单持久化与重启恢复。
- 新增 `OfflineDelegationStore` 协议和 `SQLiteOfflineDelegationStore`,复用 `AICO_STATE_DB_PATH` 对应 SQLite 文件保存 `offline_delegations` 表。
- 新增共享 SQLite state layer:`SQLiteStateDatabase` 统一维护 `aico_schema` metadata、schema version、表计数和已知状态表 reset。
- 新增 `aico-state --db <path>` CLI:默认输出 schema version 和状态表行数;`reset --yes` 可清空已知 AICO 状态表,适合开发期快速迭代。
- `AICO_STATE_DB_PATH=true` 现在映射到 `.aico/state.db`,`false` / `0` / `off` 视为关闭,避免再次生成仓库根目录 `true` 数据库文件;`.aico/` 已加入 `.gitignore`。
- `OfflineDelegationCommandHandler` 支持可选 store;未配置时仍保持内存行为,配置后 `/overnight` 写入 SQLite,重启并重新进入同一 project 后 `/overnight` 可列出历史托管工单。
- `Phase1Runtime` 在配置 `AICO_STATE_DB_PATH` 时同时启用 task state store 和 offline delegation store。
- README / README.zh-CN / Quickstart / daily ops / Phase 8 playbook / ADR-0028 同步更新,不再把 `/overnight` persistence 标为进行中。
- 新增回归测试覆盖 SQLite 恢复 overnight delegation,并确认恢复列表不会再次派发 Adapter 任务。
- 验证通过:`pytest` 293 passed / 1 skipped,`ruff check .`,`ruff format --check .`,`mypy src tests`,`git diff --check`,结构扫描无单类 >=500 行或单函数 >=100 行。

**Round 107**(2026-05-21,Codex):
- 按人类要求拆 `Orchestrator` / `TaskBus`:新增 `OrchestratorTaskFactory` 承载 project/session/memory task 构造,新增 `TaskStateRepository` 承载 task records、snapshots、approvals 和 adapter mapping。
- `Orchestrator` 类体从约 646 行降到 480 行;`TaskBus` 类体从约 566 行降到 448 行;模块级命令分发拆成 project / role / directory / memory helper 后不再超过 100 行。
- 继续修 Telegram 可读性:`rich_text_message()` 会把普通 `-` / `*` 列表转成 `•`,并对 `agent_title:`、`role:`、`adapter:` 等字段左侧 label 加粗;`/agents` 和 `/appoint` 的真实输出会更像结构化 IM 消息。
- 维持 render contract 边界:核心仍只输出平台无关 `MessageTextSpan`,Telegram Channel 只做 HTML 映射,没有把 Telegram Markdown 方言塞回核心。
- 更新测试覆盖 `/agents` 列表、字段 label 加粗、`/appoint` label 加粗和结构拆分后的回归。
- 验证通过:`pytest` 289 passed / 1 skipped,`ruff check .`,`ruff format --check .`,`mypy src tests`,`git diff --check`,结构扫描无单类 >=500 行或单函数 >=100 行。

**Round 106**(2026-05-21,Codex):
- 按人类确认,将 GitHub UI metadata(description、topics、social preview)视为已验收,不再作为公开发布缺口。
- 改善 Telegram 消息体感:新增平台无关 rich text renderer,流式 provider 输出和内置命令输出会把轻量 Markdown 标题、小节标题、inline bold/code/italic 和 slash command 转成 `MessageTextSpan`,Telegram 渲染为 HTML;标题前自动留出结构空行。
- 决策并落地 SQLite 持久化第一切片:新增 ADR-0028、`TaskStateStore` 协议和 `SQLiteTaskStateStore`;通过 `AICO_STATE_DB_PATH` 可持久化 task records、task snapshots 和 pending approvals,重启后继续支持 `/tasks`、`/task` 和 pending `/approve`。
- 从 1k stars 缺口和 GitHub 公开高优事项中选择两个最关键点落地:
  - 新增 `aico-release-room-demo` 无 token Release Room 本地 demo,陌生开发者不用 Telegram Bot Token 或 LLM provider 也能看到团队/记忆/审批/日报/审计链路。
  - 新增 `.github/PULL_REQUEST_TEMPLATE.md` 和 `.github/ISSUE_TEMPLATE/good_first_issue.yml`,降低公开后外部贡献者参与门槛。
- README / README.zh-CN / Quickstart / daily ops 同步新增 no-token demo 和 `AICO_STATE_DB_PATH` 配置说明。
- 新增 B-004,记录 `Orchestrator` / `TaskBus` 超过单类尺寸硬约束的公开前结构债。

**Round 105**(2026-05-21,Codex):
- 按人类“先别做重”的判断,把 ADR-0025 收敛为轻量 Goal Brief v0:先验证 `/goal` + 可验证 `/ask` 的目标/验收 prompt 价值,完整 `GoalCapability` / `GoalExecutor` / managed Ralph loop 暂缓。
- 新增 `/goal [role] <objective>` 命令;未指定 role 时使用当前 project lead/default role,`/goal` 可列出最近带 goal brief 元数据的任务。
- `/ask <role> <task>` 仅在文本出现明确验收、停止、通过/失败、证据等 marker 时保守附加 `AICO Goal Brief`;普通咨询不升级。
- Goal Brief 会注入 objective、acceptance、verification hints、stop conditions 和“没有证据不得 claim done”的规则;Task metadata 写入 `aico.intent=goal_brief`、`aico.goal_id`、`aico.goal_objective`、`aico.goal_acceptance`。
- `/task <id>` 详情新增 `Goal brief:` 区块,展示 goal id、objective 和 acceptance。
- 新增 `GoalBriefCommandHandler`,避免把 goal 逻辑继续塞进 Orchestrator;同步更新 ADR-0025、CHANGELOG 和 Phase 8 playbook。
- 验证通过:目标 command/orchestrator 单测、完整 `tests/unit/test_commands.py tests/unit/test_orchestrator.py`、定向 ruff / format / mypy。

**Round 104**(2026-05-21,Codex):
- 完成 lead decision workflow Stage 3:当前项目 lead/default role 收到明确决策类任务时,会进入只读决策流程。
- 决策流程优先召回 `public_broadcast`、`task_key_progress`、`decision_review` purpose 的记忆,不把 `task_private` 和普通 `general_context` 混入 decision packet。
- 自动咨询 challenger,并在 reviewer 已任命时同时咨询 reviewer;咨询任务复用 appointment prompt、provider session、普通 TaskBus 和协作审计 trace。
- Lead 最终任务会收到固定 decision memo 输出契约:Decision、Why、Evidence / memory refs、Consulted roles、Rejected alternatives、Risks / approval need、Next actions。
- 新增 `lead_decision_recorded` audit event,detail 记录 project、lead、boss task、memory refs、consulted roles 和 memo 摘要;memo 会写回 project memory,并标记 `decision_review`。
- 验证通过:98 个相关测试覆盖 Orchestrator、Memory、TaskBus、Audit 和 Phase 7 acceptance;定向 ruff / format / mypy 通过。

**Round 103**(2026-05-21,Codex):
- 继续执行 lead 决策能力 Stage 2,新增 ADR-0027 `Memory Purpose Tags`。
- `MemoryAtom` 新增 `purpose_tags`,旧记录默认 `general_context`,并新增 `MemoryPurpose`: `general_context`、`public_broadcast`、`task_key_progress`、`task_private`、`decision_review`。
- `MemoryRetriever` 默认排除 `task_private`,只有显式 `allowed_purposes` 时才会召回内部短期记忆。
- Team broadcast 生成的 team memory 会标记 `public_broadcast`,并丢弃源记忆中的 `task_private`。
- `/remember` 和 boss feedback 写入 `general_context`;`/recall` 输出展示 purpose。
- Prompt Stack 的 Shared memory 行展示 purpose,让 lead / agent 能区分公共共识、任务进展和决策评审。
- 验证通过:26 个 memory 目标测试覆盖 JSONL 兼容、purpose 过滤、broadcast purpose、`/recall` purpose、Phase 7 acceptance 和 Release Room acceptance。

**Round 102**(2026-05-21,Codex):
- 按人类确认开始落地 lead 决策团队契约第一阶段,新增 ADR-0026 `Lead Decision Team Contract`。
- 默认角色库新增 `challenger` / Critical Philosopher,职责是从反方视角挑战方案前提、机会成本和长期风险。
- 默认项目配置和 Release Room 配置补齐 challenger appointment;`/roles` 默认核心岗位会显示 challenger。
- 项目办公室和 `/team` 输出新增 `team readiness`,用于明确当前团队是否具备 lead + challenger。
- project lead 的 appointment prompt 增加责任约束:减少 boss 认知负担、基于记忆和团队意见做低风险决策、高风险事项升级 boss。
- `/overnight` 现在要求当前项目团队完整;缺 challenger 时提示 `/appoint <agent> as challenger`,不会派发托管任务。
- 验证通过:57 个目标测试覆盖 project assignment、prompt stack、project messages、phase1 runtime、orchestrator overnight、Release Room 示例和 acceptance。

**Round 100**(2026-05-21,Codex):
- 调研 Codex `/goal`:本机 Codex CLI 为 `0.125.0`,未包含该实验命令;OpenAI Developers 文档确认 `/goal` 需要 `features.goals`,用于带明确停止条件和验证循环的长任务。
- 新增 ADR-0025 `Goal Mode Orchestration`,定义 AICO `/goal` 的显式命令、`/ask` 自动升级规则、boss 分配流程、lead 子目标流程、目标状态和 prompt 模板。
- 设计结论:goal-mode 是 `/ask` 与 `/overnight` 之间的通用目标契约层,不绕过 `/approve`,并要求 goal 状态写入 audit、可在 `/goal`、`/tasks`、`/task`、`/daily` 中追踪。
- 本轮只做设计文档,未改运行代码;下一轮优先实现 GoalRecord 持久化、parser、render/audit 和单测。

**Round 101**(2026-05-21,Codex):
- 按人类反馈重构 ADR-0025:不同 agent 不能统一走 AICO loop,应先生成统一 `GoalContract`,再按 Adapter `GoalCapability` 选择执行器。
- 新增 `GoalCapability` 分层:`native_goal`、`adapter_goal_sugar`、`managed_ralph_loop`、`no_goal`。
- 对 Codex / Claude Code 等支持 goal 的 agent,由 Adapter 封装语法糖并传入明确目标、验收标准和停止条件;core 不硬编码具体 agent 语法。
- 对不支持 goal 的 agent,由 AICO 托管 managed Ralph loop:通过长期目标 prompt、hook 输出契约、continuation task、预算和审批边界避免模型过早结束或失控。
- 本轮仍只改设计文档;下一轮实现应先做 Adapter capability 模型和 GoalExecutor 分发,再做 managed loop。

**Round 96**(2026-05-20,Codex):
- 落地记忆检索 Stage 1+2:新增 `MemoryRetrievalQuery` / `MemoryRetrievalHit`,让检索 query、scope、top_k、token budget 和可解释 hit 成为稳定契约。
- `MemoryRetriever` 现在先生成 ranked hits,再投影为 `MemoryPacket`;排序综合 semantic、scope closeness、confidence、recency、evidence 和预留 graph score。
- `/recall` 改为复用 `MemoryRetriever`,并展示 reason,让记忆召回能被老板和下一轮 agent 排障。
- 新增测试覆盖 role scope 优先于 project scope、retrieval reason、token budget、candidate/restricted/cross-project 不进入 prompt 的既有治理。
- 更新 ADR-0023、Phase 7 playbook、CHANGELOG、ROUNDS 和 STATUS。
- 验证通过:266 passed / 1 skipped,`ruff check .`, `ruff format --check .`, `mypy src tests`, `git diff --check`。

**Round 97**(2026-05-20,Codex):
- 继续推进记忆检索到可验收态:新增保守 graph expansion,仅沿 `supports` / `derived_from` / `broadcast_to` 扩展一跳同 scope 邻居。
- `MemoryRetrievalQuery.role_id` / `agent_id` / `task_kind` 现在会作为 query hints 参与 semantic scoring,让 tester / reviewer / release-manager 更容易召回各自相关记忆。
- `/recall` 输出增加 final / semantic / scope / graph score 分项,便于 Telegram 真实验收和后续调权。
- 新增测试覆盖 graph 邻居召回不跨项目、role/task hints 排序、score/reason 展示路径。
- 验证通过:目标 memory/orchestrator/Phase7 tests、全量 `pytest`、`ruff check`、`ruff format --check`、`mypy` 和 `git diff --check`。

**Round 98**(2026-05-20,Codex):
- 排查人类真实 IM 反馈:`/appoint codeflicker as tester` 返回 `Cannot appoint`,根因是默认 project config 早先把 CodeFlicker agent id 落成 `flicker` alias,而用户输入的是 provider/persona 名 `codeflicker`。
- 修复 Project Assignment agent 解析:先按 configured agent id 匹配,再在唯一匹配时按 `CompanyAgentProfile.provider` 匹配;默认项目配置中 CodeFlicker / Cursor / Trae / Gemini 也使用 persona 名作为 agent id。
- 将 Claude/Codex/Cursor/CodeFlicker/Trae/Gemini CLI adapter 从单槽位改为可配置并发,默认 `max_concurrent_tasks=5`;达到上限才返回 busy。
- `/agents` / `/agent` 现在展示 `running/max` 与 `max_concurrent`,`/appoint` 成功回执展示 `agent_max_concurrent` 和建议任命上限。
- 将 Codex / optional CLI adapter 默认 output idle timeout 从 90 秒放宽到 300 秒,避免长思考或无中间 stdout 的正常任务过早失败。
- 验证通过:目标 adapter/project/orchestrator 测试 71 passed;全量 `pytest` 270 passed / 1 skipped;`ruff check`、`ruff format --check`、`mypy src tests`、`git diff --check` 全部通过。

**Round 92**(2026-05-18,Codex):
- 对齐 Release Room GIF 卡点:确认 AICO 默认 Claude Adapter 已使用 Claude Code CLI (`claude -p`,本机版本 `2.1.143`);本机 `cc` 是 `/usr/bin/cc`,不是 Claude Code CLI。
- 定位 Codex 噪音根因:role 重新任命后 assignment session 复用旧 agent session,以及 Codex Adapter 对非 Codex provider session 也尝试 resume,导致 `thread/resume failed`;CLI warning/HTML/stdout 噪音又被原样流到 Telegram。
- 修复 `ClaudeCodeAdapter`:只在 provider session 名称匹配当前 adapter 时才使用 `--session-id` / `--resume`,并增加 stdout/error 处理 hook。
- 修复 `CodexAdapter`:忽略非 Codex provider session,过滤典型 Codex CLI warning、HTML 片段、`sqlx::query` 噪音和 thread resume error。
- 修复 `Orchestrator._ensure_assignment_session()`:同一 role 改任命到不同 agent/adapter 后关闭旧 assignment session 并重建,避免沿用旧 provider ref。
- 新增/更新单测:Codex 噪音过滤、跨 provider session 忽略、role 改任命后 session 重建。
- 真实 Telegram dry run 通过:重新 `/use project release-room`、`/appoint codex as pm docs audit`、`/ask pm Give a 3-bullet release plan...`,Telegram 只显示干净 3-bullet release plan,没有 warning/HTML/resume error。
- B-003 从 BLOCKING 调整为 DEFERRED:Codex 短输出镜头不再阻塞;Claude 长输出仍不建议入镜。

**Round 91**(2026-05-18,Codex):
- 继续执行 Release Room Stage 3 真实 Telegram dogfooding。
- 停掉重复 `aico-phase1` 实例,解决 Telegram `409 Conflict`;用真实 Telegram Bot API 启动单实例,并将 polling timeout 降到 3 秒避免 long-polling 空白 warning。
- 通过 Telegram App 发送 `/use project release-room`、`/team` 和 3 条 `/remember`,验证 project office、team lead、project-scoped memory 均能真实回包。
- 发送 `/ask pm ...` 后发现真实 Claude CLI 在当前无 Pro / 输出不稳定环境下长时间不回包;用 `/interrupt 4c0b914a` 成功中断任务,验证可中断性。
- 临时 `/appoint codex as pm docs audit` 后重试 PM 拆工,发现 Codex CLI 原始输出包含大量 plugin warning、HTML 片段和 thread resume 错误,不适合 public GIF 入镜。
- 新增 B-003 和 P-017,明确真实 provider 输出目前阻塞“直接录真实 Claude/Codex public GIF”;public showcase 应先走 transcript-driven 稳定素材。
- 新增 P-018 并修复日志安全问题:`configure_logging()` 将 `httpx` / `httpcore` 降到 WARNING,避免 INFO 日志把 Telegram Bot token URL 写进 `logs/aico.log`;补充 `test_phase1_logging_suppresses_http_client_info_logs`。
- Stage 3 真实 Telegram dogfooding 第一段完成,但 README GIF 仍未生成。

**Round 90**(2026-05-18,Codex):
- 按人类要求启动 Release Room Stage 3 的镜头节奏准备;人类环境为本机有 Telegram App、Claude CLI(无 Claude Pro)/Codex,没有单独 GIF 转换工具。
- 确认本机已有 `/opt/homebrew/bin/ffmpeg`,无需先安装 `gifski`。
- 新增 `examples/release-room/shot-rhythm.md`,把 Stage 2 transcript 压成 56 秒 README GIF 时间线:project office、shared memory、PM split、approval gate、independent checks、overnight handoff、daily/audit traceability。
- 新增 `examples/release-room/make-gif.sh`,用 `ffmpeg` palettegen/paletteuse 从 `.mov/.mp4` 转出 `docs/assets/release-room-demo.gif`,支持 `AICO_GIF_FPS` 和 `AICO_GIF_WIDTH`。
- 更新 release-room README、录屏 storyboard、examples 文档、playbook 和 CHANGELOG,把“无 gifski 也可转 GIF”的路径写清楚。
- Stage 3 真实 IM dogfooding / 录屏仍未完成;下一步是按 `shot-rhythm.md` 在 Telegram 中录 30-60 秒主 GIF,再嵌入 README。

**Round 89**(2026-05-18,Codex):
- 继续推进 Release Room Stage 2,把主 demo 从静态资产升级为本地可验收 transcript。
- 新增 `tests/unit/test_release_room_acceptance.py`,使用真实 `examples/release-room/aico-project.json`、`ProjectAssignmentDirectory`、`Orchestrator`、`TaskBus` 和 `JsonlMemoryStore`,只把底层 Claude/Codex 替换为 deterministic fake adapters。
- Stage 2 acceptance flow 覆盖:`/use project release-room`、`/team`、3 条 `/remember`、`/ask pm`、`/ask implementer`、`/approve`、`/ask tester`、`/ask reviewer`、`/ask release-manager`、`/overnight`、`/daily`、`/tasks`、`/metrics`、`/audit`。
- 验证点包括:team lead 可见、project memory 进入后续 PM/implementer prompt、implementer 写文件/跑测试任务先进入审批、审批后才派发、tester/reviewer 独立验收、overnight task 带 `offline_delegation` metadata、daily report 有 Boss summary、audit 记录 approval requested/approved。
- 新增 `examples/release-room/transcript.md`,作为无真实 token 的本地预览和后续 GIF/README 素材。
- 更新 release-room docs、playbook、README、STATUS 和 CHANGELOG,将 Stage 2 标记完成。
- 目标验证通过:`uv run pytest tests/unit/test_release_room_acceptance.py tests/unit/test_release_room_example.py`;示例仓库测试通过:`uv run pytest examples/release-room/notes-cli/tests`(2 passed,3 skipped);目标 `ruff check`、`ruff format --check`、`mypy` 通过。

**Round 88**(2026-05-18,Codex):
- 按人类反馈重做主 demo 方向:放弃“AI 开源维护者的一晚”这种单 issue demo,改成更能体现团队/角色/记忆/审批/审计/早报的 Release Room。
- 新增 `docs/examples/README.md` 和 `docs/examples/release-room.md`,明确主 demo 是“在 IM 中远程开一个 AI release room,管理 AI team 完成小型开源 CLI 的 v0.2 release”。
- 新增 `examples/release-room/notes-cli` 示例仓库:包含 v0.1 可运行 CLI、v0.2 release issue、STATUS/NORTH_STAR/journal、release notes 草稿、v0.1 测试和 v0.2 合约测试。
- 新增 `examples/release-room/aico-project.json`,配置 release-room 项目团队:pm、implementer、tester、reviewer、release-manager,并把 Claude/Codex 映射到对应 appointment。
- 新增 `examples/release-room/demo-script.md` 和 `recording-storyboard.md`,把 `/project`、`/team`、`/remember`、`/ask`、`/role propose`、`/overnight`、`/daily`、`/audit` 串成录屏脚本。
- 新增 `docs/playbooks/release-room-demo.md`,给出启动环境变量、IM 操作步骤、验证点和 fallback。
- README 和 playbook index 加入 Release Room 入口。
- 新增 `tests/unit/test_release_room_example.py`,验证 demo project config 能被当前模型加载,且示例仓库的项目办公室文档完整。
- 目标验证通过:`uv run pytest tests/unit/test_release_room_example.py`;示例仓库测试通过:`uv run pytest examples/release-room/notes-cli/tests`(2 passed,3 skipped);目标 `ruff check` 和 `ruff format --check` 通过。

**Round 87**(2026-05-18,Codex):
- 按人类要求启动 Phase 8,先做“睡前下任务,早上看结果”的第一切片。
- 新增 ADR-0024 `Phase 8 Offline Delegation Scope`,明确先做 project-scoped offline delegation work order,暂不做无人值守调度器或绕过审批的夜间授权。
- 新增 `/overnight <goal>` 命令:需要 active project,自动派给当前项目 lead/default role,复用 appointment prompt、shared memory、provider session 和现有 TaskBus。
- `/overnight` 不带目标时展示当前 active project 在本进程内最近托管工单,并提示 `/daily <project>`、`/tasks` 作为早报入口。
- 托管 prompt 要求 lead 留下 morning handoff:done、blocked、risks、next actions。
- 风险目标仍进入 Phase 4 审批门禁,例如 `/overnight update docs` 会返回 `Approval required`,不会因为“离线托管”而越权执行。
- 新增 `src/aico/core/offline_delegation.py` 和 Orchestrator 接线;扩展命令解析、help、daily ops、playbook、CHANGELOG 和 ADR 索引。
- 目标验证通过:`tests/unit/test_commands.py` 和 3 个 `/overnight` Orchestrator 单测;目标 `ruff`、`ruff format`、`mypy` 通过。

**Round 86**(2026-05-18,Codex):
- 在飞书开放平台真实 smoke 前补齐 webhook 生产化短板:事件回调幂等。
- 依据飞书事件结构和推送机制:2.0 事件使用 `header.event_id` 唯一标识,1.0 事件使用 `uuid`;平台失败重试和至少一次投递都可能导致重复事件。
- `FeishuChannel` 新增本地 TTL 去重缓存,默认保留 8 小时、最多 4096 个 event id。
- 重复事件不会再次派发给 Orchestrator,避免重复创建 AICO 任务或重复回复。
- 保持缺少 event id / uuid 的事件继续按原路径处理,避免因为非标准 payload 直接丢消息。
- 新增单测覆盖 v2 `event_id` 去重、v1 `uuid` 去重和 TTL 到期后允许重新处理。
- 目标验证通过:`tests/unit/test_feishu_channel.py`、`tests/unit/test_feishu_webhook.py`;目标 `ruff`、`ruff format --check`、`mypy` 均通过。

**Round 85**(2026-05-18,Codex):
- 按人类要求开发飞书 Channel,对齐当前 Telegram 的 runtime 接入形态。
- `Phase1Settings` 新增 `AICO_CHANNEL=telegram|feishu` 和飞书 App ID / App Secret / Verification Token / webhook host / port / path 配置。
- `build_phase1_runtime()` 现在按 channel 构造 `TelegramChannel` 或 `FeishuChannel`;Telegram 仍是默认主控入口。
- 新增 `aico-feishu-webhook` FastAPI 入口,提供 `GET /healthz` 和 `POST /feishu/events` 默认事件回调路由。
- 飞书 URL verification 会直接返回 challenge;`im.message.receive_v1` 文本事件进入现有 Orchestrator,复用项目、审批、记忆和报告能力。
- 新增 webhook 单测覆盖 healthz、URL verification 和 verification token 拒绝路径。
- 目标验证通过:`tests/unit/test_feishu_channel.py`、`tests/unit/test_feishu_webhook.py`、Feishu runtime 相关 `test_phase1_app.py`;目标 `ruff`、`ruff format --check`、`mypy` 均通过。
- 真实飞书开放平台 smoke test 仍需企业自建应用凭据和公网 HTTPS callback URL。

**Round 84**(2026-05-18,Codex):
- 按人类验收反馈升级 Phase 7 记忆召回:从关键词/子串过滤提升为可插拔 semantic scorer 排序。
- 新增 `MemorySemanticScorer` 接口和默认 `LocalSemanticMemoryScorer`,支持中文长句复述和常见中英项目管理术语别名。
- `JsonlMemoryStore.search()` 和 `MemoryRetriever` 改为按 scope 收集候选后进行 semantic score 排序;`MemoryGovernor` 继续负责 active / candidate / sensitivity / confidence 投影。
- 新增 ADR-0023 `Memory Semantic Retrieval`,明确后续 embedding / LLM rerank 只替换 scorer,不绕过 scope、governor 和 citation。
- 测试覆盖:“汇报当前项目进度,并告诉我还有几阶段”可召回“我更喜欢汇报进度时告诉我还有几阶段”;“法务检查”可召回英文 `legal review` 记忆。
- 验证通过:244 个单测、1 个 golden skipped、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check`。

**Round 83**(2026-05-18,Codex):
- 处理真实使用 `/remember` 时出现的 `Memory store is not configured. Set AICO_MEMORY_PATH first.`。
- 确认根因:当前运行的 `aico-phase1` 进程启动时没有配置 `AICO_MEMORY_PATH`,因此 Orchestrator 未注入 `JsonlMemoryStore`。
- 将 IM 报错改为可执行提示:说明需要在启动 `aico-phase1` 前设置 `AICO_MEMORY_PATH` 并重启,同时给出后续 `/use project` / `/remember` 操作。
- 更新 `docs/human/quickstart.md`,把 `AICO_PROJECT_CONFIG_PATH` 和 `AICO_MEMORY_PATH` 纳入快速启动环境变量,并补充 memory smoke 命令。
- 验证通过:242 个单测、1 个 golden skipped、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check`。

**Round 82**(2026-05-17,Codex):
- 完成 Phase 7 共享记忆本地验收流,新增 `tests/unit/test_phase7_memory_acceptance.py`。
- 验收流覆盖企业/团队管理常见场景:项目级合同/法务记忆、跨项目隔离、老板全局汇报偏好、项目级 candidate 反馈不注入、team broadcast 共识、JSONL 重启恢复、A2A `memory_refs + delta` 可关闭回退。
- 更新 Phase 7 playbook 和 daily ops,明确 `/remember` / `/recall` / `/forget` 是纠错/排障入口,老板日常主路径仍是自然管理项目和 agent。
- 记录 deterministic 中文检索边界:第一版是 scope + 子串/标签匹配,长中文句需要使用稳定关键词验收;语义检索留到后续增强。
- 验证通过:241 个单测、1 个 golden skipped、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check`。

**Round 81**(2026-05-17,Codex):
- 按 TDD 完成 Phase 7 Iteration 5:Team Broadcast 与 A2A memory refs 实验 MVP。
- 新增 `MemoryBroadcastService` 和 `MemoryBroadcastReceipt`,可把 project / boss / team 记忆广播为 team-scoped consensus atom。
- `JsonlMemoryStore` 增加 `get_atom()`,broadcast 服务会写入 team memory,并追加 `broadcast_to` edge 作为 receipt。
- broadcast 会拒绝跨 project team scope,避免把一个项目的记忆直接广播到另一个项目。
- project task Prompt Stack 召回 scope 增加 `team:<project>/default`,同 team agent 后续任务能自动看到广播共识。
- `collaboration_payload()` 新增可关闭的 `memory_refs + delta` 格式;无 refs 时回退原显式消息。
- 验证通过:240 个单测、1 个 golden skipped、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check`。

**Round 80**(2026-05-15,Codex):
- 按 TDD 完成 Phase 7 Iteration 4:Boss feedback 抽取与 candidate memory MVP。
- 新增 `MemoryCaptureService`,从老板自然消息中识别明确偏好/feedback,自动写入 `MemoryAtom`。
- scope 明确指向项目时写入 current project memory;无项目上下文或全局表达时写入 boss global memory。
- 语气不确定的反馈写成 `candidate`,不会进入 Prompt Stack;明确偏好写成 active。
- Orchestrator 在非命令消息路由前调用 capture service;命令仍走原处理链,避免把 `/remember` 等命令重复抽取。
- project task 召回 scope 扩展为 boss global + project + role + agent,让老板全局偏好能按 query 自动进入 agent prompt。
- 验证通过:235 个单测、1 个 golden skipped、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check`。

**Round 79**(2026-05-15,Codex):
- 按 TDD 完成 Phase 7 Iteration 3:IM 控制入口。
- 新增 `MemoryCommandHandler`,把 `/remember`、`/recall`、`/forget` 做成 project-scoped 纠错/排障入口,不调用 provider。
- `Phase1Settings` 新增 `AICO_MEMORY_PATH`;配置后 `aico-phase1` runtime 会创建 `JsonlMemoryStore` 并接入 Orchestrator prompt 自动召回。
- `/remember <text>` 默认写当前 active project scope;没有 active project 时提示先 `/project <project>`。
- `/recall [query]` 展示 claim、scope、confidence、source/evidence 摘要和短 Next。
- `/forget <memory_id>` 只归档 JSONL 记忆,不物理删除历史;测试覆盖归档后 prompt stack 不再注入。
- 验证通过:228 个单测、1 个 golden skipped、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check`。

**Round 78**(2026-05-15,Codex):
- 按 TDD 完成 Phase 7 Iteration 2:Prompt Stack 自动召回。
- 先新增红灯测试:
  - `MemoryRetriever` + `MemoryGovernor` 只能从指定 project/team scope 召回 active 且允许披露的记忆。
  - candidate、archived、restricted 或其它 project 记忆不会进入 `MemoryPacket`。
  - `render_appointment_prompt()` 会把 `MemoryPacket` 渲染到 `Current task` 之前。
  - Orchestrator 在 active project 普通任务中自动注入当前 project 记忆,且不会串入其它 project。
- 新增 `MemoryPacketItem`、`MemoryCitation`、`MemoryPacket`、`MemoryGovernor`、`MemoryRetriever`。
- `render_appointment_prompt()` 支持可选 `memory_packet`。
- `Orchestrator` 支持可选 `memory_store`,project-scoped task 会按 project/role/agent scope 自动召回少量受控记忆。
- 验证通过:memory、prompt_stack、orchestrator 目标单测,目标 ruff、目标 format check、目标 mypy。

**Round 77**(2026-05-15,Codex):
- 将 Phase 7 A2A Memory Fabric 拆成 5 个 TDD 迭代:
  - Iteration 1:MemoryAtom / MemoryScope / MemoryEvidence / MemoryEdge / JsonlMemoryStore。
  - Iteration 2:Prompt Stack 自动召回。
  - Iteration 3:/remember / /recall / /forget 控制入口。
  - Iteration 4:boss feedback 抽取与 candidate memory。
  - Iteration 5:team broadcast 与 A2A token-saving 实验。
- 按 TDD 完成 Iteration 1:
  - 先新增 `tests/unit/test_memory.py`,锁定 evidence、project/team scope、JSONL 恢复、archive 和 edge 持久化契约。
  - 新增 `src/aico/core/memory.py`,实现 `MemoryAtom`、`MemoryScope`、`MemoryEvidence`、`MemoryEdge`、`MemoryStore` Protocol 和 `JsonlMemoryStore`。
  - `JsonlMemoryStore` 使用 append-only JSONL 作为权威源,启动时重建内存索引;召回使用可插拔 semantic scorer。
- 验证通过:memory/model/audit 相关单测、目标 ruff、目标 format check、目标 mypy。

**Round 76**(2026-05-15,Codex):
- 按人类要求设计符合 A2A 的 Phase 7 记忆架构,参考 `attack-on-memory` 的 Memory Atom、evidence、scope、graph edge、time-window retrieval、selective disclosure 和 BranchWorldModel 思路。
- 新增 ADR-0022 `A2A Memory Fabric`,把 `/remember` / `/recall` 从孤立 IM 命令升级为 lead agent、team agent 和 boss 共享的记忆基础设施。
- 新增 `docs/architecture/a2a-memory-fabric.md`,定义 MemoryAtom、MemoryEvidence、MemoryScope、MemoryEdge、MemoryPacket、MemoryStore、MemoryRetriever、MemoryGovernor、MemoryCaptureService、MemoryBroadcastService。
- 明确记忆分层:boss global、project、team、role、agent working memory;默认禁止跨 project / team 共享。
- 明确四个核心场景:agent 间协作有记忆、boss 会话抽取偏好/feedback、team 共识广播、用 memory refs + MemoryPacket 试验减少 A2A 长消息传递。
- 本轮为文档/决策更新,未改代码。

**Round 75**(2026-05-15,Codex):
- 按人类明确基调修正 Phase 7 记忆层产品方向:记忆命令可以存在,但大比例触发应来自 agent,不是老板手动维护。
- 新增 ADR-0021 `Agent-Driven Memory Ownership`,确定 `/remember` / `/recall` / `/forget` 是纠错、补充、排障和验收入口,不是老板主工作流。
- 更新 Phase 7 playbook:agent 在任务完成、交接、风险确认、日报/周报沉淀时主动写入稳定事实;接项目任务前自动召回当前项目少量高置信记忆。
- 下一轮实现 Phase 7 第一切片时,验收不能只测三个 slash command,还要覆盖“老板自然发项目命令,agent 自动使用记忆”的路径。
- 本轮为文档/决策更新,未改代码。

**Round 70**(2026-05-14,Codex):
- 按人类要求让项目查看类命令更有指导性,减少“看完不知道下一步干嘛”的断点。
- 在查看类输出末尾追加短 `Next:` 指导命令:
  - `/agents`:提示 `/agent <agent>`、`/roles`、`/appoint <agent> as <role>`。
  - `/agent <agent>`:idle 时提示 `/roles`、`/appoint <agent> as <role>`、`/new <agent>`;非 idle 时提示 `/tasks`、`/status`、`/agent <agent>`。
  - `/project`:提示 `/brief`、`/team`、`/next`、`/daily`、`/weekly`。
  - `/team`:已有 lead 时提示 `/ask <lead-role> <task>`、`/who <lead-role>`、`/roles`、`/lead <role>`;无任命时提示 `/roles`、`/agents`、`/appoint <agent> as <role>`。
  - `/roles`:提示 `/role <role>`、`/agents`、`/appoint <agent> as <role>`、`/roles all`。
  - `/role <id>`:未任命时提示 `/agents`、`/appoint <agent> as <role>`、`/roles`;已任命时提示 `/ask <role> <task>`、`/lead <role>`、`/appoint <agent> as <role> <scope>`、`/unappoint <role>`。
- 没有新增新命令;role scope 调整先复用已有 `/appoint` 覆盖语义,避免过早设计 `/scope`。
- 新增/更新单测覆盖 project / team / roles / role / agents guidance。
- 验证通过:215 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check`。

**Round 69**(2026-05-13,Codex):
- 修复 project-scoped lead / role 普通咨询误触发审批的问题:
  - `render_appointment_prompt()` 会把 Agent、Role、Project、Appointment Contract 和 `Current task` 拼成完整 prompt。
  - 过去 `TextRiskAssessor` 扫整段 prompt,因此 role summary 里的 `write` / `run tests` 等词可能让“团队分工是什么?”这类只读问题进入 `waiting_approval`。
  - 现在风险识别在 appointment prompt 中只检查 `Current task:` 之后的真实用户请求;如果真实请求要求 `run pytest` / `update STATUS.md` 等,仍会触发审批。
- 修复待审批任务清理体验:
  - `/interrupt <task_id>` 现在可以取消 `waiting_approval` 任务,会把任务状态记为 `interrupted`,并移出 pending approval 队列。
  - 多个 pending approvals 时,用户可以用 `/interrupt <short_task_id>` 清理不想执行的项,再继续 `/approve <short_task_id>` 或 `/reject <short_task_id>`。
- 新增回归测试覆盖:
  - appointment prompt scaffolding 中出现 write/run 时,只读团队/项目问题不触发审批。
  - `Current task` 真实要求执行命令或更新文件时仍触发审批。
  - `/interrupt` 可取消 `waiting_approval` 并记录 approval rejected / task interrupted 审计事件。
- 验证通过:212 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check`。

**Round 68**(2026-05-13,Codex):
- 按人类反馈收敛 `/agents` / `/roles` 的产品语义:
  - `/agents` 现在优先展示工具入口名,如 `claude -> claude-code [role: implementer]`,避免 `implementer` / `reviewer` 与 `cursor` / `codeflicker` 混在同一命名层。
  - `/roles` 默认变为紧凑岗位板,只展示 Core / Specialists;`tester`、`docs`、`ops`、`analyst`、`designer` 等支持岗位默认隐藏到 `/roles all`。
  - 新增 `/role <id>` 详情视图,展示 owner、scope、approval 和 risk ladder。
- 收敛权限词表为三层:
  - Adapter capability: `code_review` / `code_edit` / `shell_exec` / `long_running` / `stream_output` / `interruptible`。
  - Role scope: `docs` / `code` / `tests` / `ops` / `audit`。
  - Risk level: `read_only` / `write_files` / `shell_exec` / `destructive`。
- `/appoint <agent> as <role>` 不传 scope 时,现在自动继承 role 默认 scope。
- 新增 ADR-0019,明确本轮不是引入完整 RBAC;role scope 仍是岗位契约,真实危险动作继续由 risk assessor、adapter capability 和 `/approve` 控制。
- 验证通过:208 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check`。

**Round 67**(2026-05-12,Codex):
- 按人类要求把 Cursor / CodeFlicker 从“可选只读 MVP”升级为审批保护下的完整能力:
  - Cursor 默认命令改为 `cursor-agent -p --force --output-format text`。
  - CodeFlicker 默认命令改为 `flickcli -q --approval-mode yolo --output-format text`。
  - 两者 capabilities 现在包含 `code_edit` / `shell_exec`;写文件、shell、destructive 任务仍先走 AICO 风险识别和 `/approve`。
- 新增 `TraeAdapter`:
  - 默认命令 `trae-cli --print --yolo`。
  - 通过 `AICO_ENABLE_TRAE_ADAPTER=true` 启用。
  - 支持 AICO provider session 新建 / resume 元数据映射到 `--session-id` / `--resume`。
- 新增 `GeminiAdapter`:
  - 默认命令 `gemini --approval-mode yolo --output-format text`。
  - 通过 `AICO_ENABLE_GEMINI_ADAPTER=true` 启用。
  - 支持已绑定 provider session 用 `--resume` 继续。
- 默认 AI Company role 模板扩充 PM、Senior Architect、Golden Tester、Market Risk、Legal Compliance,并保留 implementer / reviewer / tester / security / docs / ops / analyst / designer 等有明确 AI 公司产出的岗位。
- 在飞书、钉钉、QQ、微信中选择飞书作为第一个非 Telegram Channel:
  - 新增 `FeishuChannel`,覆盖 tenant token、文本发送、编辑/删除、URL verification、`im.message.receive_v1` 文本事件解析。
  - 新增 Feishu Channel playbook;真实公网 callback server 留给下一轮部署层切片。
- 新增 ADR-0018,记录完整 Adapter 能力、role 扩充和 Feishu Channel 选择。
- 验证通过:207 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`。
- 本机 CLI 状态:
  - `cursor-agent` 当前未安装。
  - `flickcli` 已存在,help 确认支持 `--approval-mode`、`--cwd`、`--tools`、`--output-format`。
  - `trae-cli` 已存在,help 会先报本机 keyring token store 不支持,但随后展示 `--print`、`--yolo`、`--session-id`、`--resume`。
  - `gemini` 已存在,help 确认支持 `--approval-mode`、`--output-format`、`--resume`。

**Round 66**(2026-05-07,Codex):
- 按近期高优方向启动 Adapter 扩展第一切片。
- 新增 ADR-0017,确定 Cursor / CodeFlicker 先作为可选只读 Adapter 接入,默认不授予写文件或 shell 能力。
- 新增 `CursorAdapter`:
  - 默认命令 `cursor-agent -p --output-format text`。
  - 通过 `AICO_ENABLE_CURSOR_ADAPTER=true` 启用。
  - 启用后内置 persona `cursor` 会进入 `/agents`。
- 新增 `CodeFlickerAdapter`:
  - 默认命令 `flickcli -q --output-format text --tools '{"bash":false,"write":false}'`。
  - 通过 `AICO_ENABLE_CODEFLICKER_ADAPTER=true` 启用。
  - 启用后内置 persona `codeflicker` 会进入 `/agents`。
  - 有 `AICO_CLAUDE_WORKING_DIRECTORY` 时会在命令中补 `--cwd <path>`。
- 新增单测覆盖两个 Adapter 默认命令、能力边界、CodeFlicker `--cwd` 注入和 `aico-phase1` 可选启用路径。
- 新增 `docs/playbooks/optional-agent-adapters.md`,记录 Cursor / CodeFlicker 真实 smoke test 步骤。
- 本机核验:
  - `cursor-agent` 当前未安装,所以 Cursor 真实 smoke test 待安装登录后执行。
  - `flickcli` 已存在,版本 `0.5.1`,help 确认支持 `-q`、`--cwd`、`--tools` 和 `--output-format`。
- 验证通过:193 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check`。

**Round 65**(2026-05-07,Codex):
- 人类补充近期方向:既有 Phase 6 / Phase 7 计划继续推进,但近期要高优支持更多 Adapter 和更多 IM Channel。
- 已把近期高优方向记录到 `STATUS.md`:
  - Adapter 扩展:优先 CodeFlicker Adapter、Cursor Adapter,目标是让 Telegram `/agents` 出现更多真实可用 agents,并保持可插拔,为 Trae、OpenClaw 等后续 Adapter 留同一路径。
  - Channel 扩展:从飞书、钉钉、QQ、微信里按对接成本和协议标准化程度选择 1-2 个先做,不追求一次性全量接入。
- 决策边界:本轮只记录计划,不做实现;后续实现前需要核验目标工具/IM 的最新官方 CLI/API/Bot 能力,并分别补 ADR/playbook/mock 测试。

**Round 64**(2026-05-07,Codex):
- 人类要求把 Phase 6 规划的核心能力都开发完,随后集中验收,验收通过后进入 Phase 7。
- 补齐 Phase 6 代码侧核心能力:
  - 新增 ADR-0016,明确 Phase 6 不做完整 Mac GUI / Web dashboard,先完成 `aico-glance` 数据原型和 usage 审计事件接入边界。
  - 新增 `StatusIslandSnapshot` / `StatusIslandTask`,从 `MetricsReport` 生成本地 glance 视图,包含 active agents、open/running/waiting/failed、最近任务和 `/task` / `/approve` / `/reject` / `/interrupt` 命令提示。
  - 新增 `aico-glance` CLI,支持从 `--audit-log` 或 `AICO_AUDIT_LOG_PATH` 读取 audit JSONL,输出 text 或 JSON,供 macOS/xbar/后续原生菜单栏原型消费。
  - 新增 `task_usage_recorded` 审计事件类型、`usage_audit_detail()` 和 `usage_records_from_audit_events()`,Adapter 未来上报真实 usage 后即可汇总 token/cost。
  - `MetricsReport.token_cost` 在有 usage 审计事件时展示 input/output/total tokens 和 cost;没有真实 usage 时继续明确 unavailable。
- 新增单测覆盖:
  - Status Island snapshot text/json 与动作命令。
  - `aico-glance` text/json 输出。
  - usage audit detail 解析与 token/cost 汇总。
- 验证通过:184 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check`。
- 当前 Phase 6 代码侧核心能力已完成;剩余是集中真实验收项。

**Round 63**(2026-05-07,Codex):
- 继续 Phase 6 观测模型收口,先不做 Mac GUI / Web API,把 `/metrics` 背后的数据模型提炼为可复用结构:
  - 新增 `MetricsReport` / `MetricsGlance` / `TokenCostSummary`,统一承载 generated_at、source、24h/7d summaries、glance 状态和 token/cost unavailable 原因。
  - `/metrics` 改为渲染 `MetricsReport`,新增 `glance` 小节,快速显示 `needs_approval` / `working` / `attention` / `quiet` 与 open/running/waiting/failed 数。
  - 新增 `metrics_report_to_dict()`,为后续 macOS Status Island / Web / 脚本消费提供稳定 JSON 形态。
  - 新增 `aico-metrics` CLI,可从 `--audit-log` 或 `AICO_AUDIT_LOG_PATH` 读取 audit JSONL,输出 text 或 JSON,作为 CLI 排障与本地 glance 原型的数据入口。
- 新增单测覆盖:
  - Metrics report glance 和 token/cost unavailable 状态。
  - Metrics JSON 序列化中的枚举 / 时间字段。
  - `aico-metrics` text/json 输出。
  - `/metrics` IM 输出中的 glance 小节。
- 验证通过:179 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check`。

**Round 62**(2026-05-07,Codex):
- 人类暂时没空验收新功能,要求先继续迭代,明天白天再验收能力。
- 继续 Phase 6 可观测持久化第一切片:
  - 新增 ADR-0015,决定先复用 audit JSONL replay,不新增 task snapshot JSONL 或 SQLite。
  - `InMemoryAuditLog` 支持 `initial_events`,启动时可注入历史审计事件。
  - 新增 `read_jsonl_audit_events(path)`,从 `AICO_AUDIT_LOG_PATH` 读取历史 JSONL 审计事件。
  - `aico-phase1` 配置 `AICO_AUDIT_LOG_PATH` 后,启动时会回读旧审计事件。
  - `/metrics` 会从 audit events 重建 metrics 用 task snapshot,并与当前进程内 task snapshot 合并;当前进程内状态优先。
- 新增单测覆盖:
  - audit JSONL 读取与恢复。
  - 从 audit events 重建 task snapshot 最新状态。
  - `/metrics` 同时统计重启前 audit 恢复任务和当前进程内 open work。
  - phase1 runtime 启动时加载已有 audit JSONL。

**Round 61**(2026-05-07,Codex):
- 人类认为 `/task` parent / child trace 用户价值不大,询问 Phase 5 是否还有大功能,并同意进入 Phase 6。
- 已提交并推送 Phase 5 收口提交:`031e41e Complete phase 5 collaboration observability`。
- 开启 Phase 6:
  - 新增 ADR-0014,确定第一切片先做 IM-first `/metrics`,不直接跳 Mac GUI / Web dashboard。
  - 新增 `src/aico/core/metrics.py`,基于当前进程内 `TaskSnapshot` / `AuditEvent` 汇总 24h / 7d 指标。
  - 新增 `/metrics` 命令,展示任务数、状态分布、agent/adaptor 接活数、open work、协作次数和平均终态耗时;token/cost 当前明确显示 unavailable。
  - 记录 MVP 产品入口判断:IM 主控 + macOS glance + CLI 排障;Mac 状态岛后续消费 Phase 6 指标模型。
  - 新增 Phase 6 `/metrics` smoke test playbook。
- 新增命令解析和 Orchestrator 单测覆盖 `/metrics` 不派发 Adapter 任务。

**Round 60**(2026-05-06,Codex):
- 人类已验证 `/task` / `/tasks` 相关命令,要求继续后续功能开发。
- 增强 `/task <task_id>` 协作追踪详情:
  - child task 详情会展示 `requested by` 和 parent task 的 `/task <short_id>` 入口。
  - parent task 详情会展示已触发的 child task 列表、目标 persona 和对应 `/task <short_id>` 入口。
  - 该能力复用既有 `collaboration_requested` 审计事件,没有改 TaskBus 存储模型或引入新仓储。
- 新增 Orchestrator 单测覆盖 `@reviewer` 协作后查询 parent / child task 详情。
- 定向验证通过:43 个 `test_orchestrator.py` 单测、改动文件 `ruff check`。

**Round 59**(2026-05-06,Codex):
- 人类在 Telegram 验证 Project Facts heading render 效果良好,要求继续开发后续能力。
- 新增 IM 任务追踪命令:
  - `/tasks [limit]`:展示最近任务,默认 10 条,最多 20 条。
  - `/task <task_id>`:支持完整或短 task id 前缀,展示单个任务详情。
  - waiting approval 任务会给出 `/approve <short_id>` / `/reject <short_id>` 动作提示。
  - running 任务会给出 `/interrupt <short_id>` 动作提示。
- `TaskBus` 新增只读 `task_snapshot(task_ref)` 查询入口,复用既有 task id 前缀匹配语义。
- 更新 help、daily ops 和 changelog;新增命令解析与 Orchestrator 单测。
- 完整验证通过:170 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check`。

**Round 58**(2026-05-06,Codex):
- 人类复验 `/brief` 后反馈整体好了很多,但文档 snippet 中的 Markdown 标题仍裸露,截图中可见 `# NORTH_STAR.md`、`## 第一句`、`### 状态变化`。
- 修复 Project Facts Markdown heading 渲染:
  - `_heading_message()` 现在会识别行首 `#` / `##` / `###` 等 Markdown 标题。
  - 标题会去掉 `#` 前缀,保留原标题文本并生成 `MessageTextSpan(BOLD)`。
  - 该能力作用于 `/brief`、`/risks`、`/blockers`、`/next`、`/daily`、`/weekly` 的 facts 文档片段。
- 新增单测覆盖文档 snippet 中的 Markdown heading 渲染。
- 完整验证通过:166 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check`。

**Round 57**(2026-05-06,Codex):
- 人类复测 Phase 5 `@reviewer` 真实协作 smoke test:
  - Telegram 收到 `Task accepted: 1481a413-f886-46bc-b7d4-98cccf295218 [reviewer]`。
  - `/status` 显示 `claude-code: idle`, `codex: busy`。
  - 结论:协作解析和 child task 创建成功,卡点仍是 Codex CLI accepted 后长期无 stdout。
- 修复 Codex busy 自动释放:
  - `ClaudeCodeAdapter` 增加可选 `output_idle_timeout_seconds`。
  - `CodexAdapter` 最初默认 90 秒无 stdout 自动终止底层 CLI;Round 98 已将默认阈值放宽到 300 秒,并按并发槽位释放。
  - `Phase1Settings` 新增 `AICO_CODEX_OUTPUT_IDLE_TIMEOUT_SECONDS`。
- 修复 Project Facts 无序列表 / inline Markdown 渲染:
  - `_heading_message()` 现在会规范化 facts 中的 `- ` / `* ` 为 `• `。
  - facts 中 `**bold**`、`` `code` ``、`*italic*` 也会转成 render spans,不再裸露 Markdown 标记。
- 更新 PITFALL P-014、Phase 5 collaboration playbook 和 daily ops。
- 完整验证通过:165 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check`。

**Round 56**(2026-05-06,Codex):
- 人类已完成真实复验:
  - `/interrupt` 可用。
  - `/blockers` 格式可用。
- 收口 Round 55 的结构拆分验证:
  - `ProjectStatusCommandHandler` 拆分后仍保持 `/brief`、`/risks`、`/blockers`、`/next`、`/daily`、`/weekly` 用户语义不变。
  - 完整验证通过:162 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check`。
- 代码侧下一步不建议继续堆项目命令;若继续开发,优先二选一:
  - 完成 Phase 5 `@reviewer` collaboration smoke test,若 Codex 子任务仍无 stdout,再设计 timeout / heartbeat。
  - 拆 Project team/assignment handler,继续降低 `ProjectCommandHandler` 门面复杂度。

**Round 55**(2026-05-06,Codex):
- 人类要求继续开发后续功能;真实复验仍需人类重启 AICO 服务并在 Telegram 操作。
- 继续处理 Project 命令结构债:
  - 新增 `ProjectStatusCommandHandler`,承接 `/brief`、`/risks`、`/blockers`、`/next`、`/daily`、`/weekly`。
  - 状态 / 报告 handler 集中负责本地 facts 构造、文档 snippet 聚合、summary callback 和 summary 失败降级。
  - `ProjectCommandHandler` 保持 Orchestrator 的项目命令门面,对应 handle 方法改为薄代理。
- 结构结果:
  - `src/aico/core/project_commands.py` 从 476 行降到 349 行。
  - `src/aico/core/project_status_commands.py` 为 195 行。
  - `src/aico/core/project_role_commands.py` 保持 108 行。
- 完整验证已在 Round 56 补齐。

**Round 54**(2026-05-06,Codex):
- 人类要求继续开发;真实 `/interrupt`、Project status render 和 Phase 5 collaboration smoke 复验都需要人类重启服务和 Telegram 操作。
- 按下一轮代码侧高优先级处理结构债:
  - 新增 `ProjectRoleCommandHandler`,承接 `/role propose`、`/role confirm`、`/role discard` 以及 role draft 暂存。
  - `ProjectCommandHandler.handle_role()` 改为薄代理,用户可见语义不变。
  - `ProjectCommandHandler` 不再持有 `_role_drafts` 和 `_propose_role` 运行细节。
- 结构结果:
  - `src/aico/core/project_commands.py` 从 544 行降到 475 行。
  - `src/aico/core/project_role_commands.py` 为 108 行。
- 完整验证通过:162 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`。

**Round 53**(2026-05-06,Codex):
- 人类执行 Phase 5 协作 smoke test 后反馈:
  - Telegram 收到 `Collaboration requested: claude -> reviewer`。
  - 随后停在 `Task accepted: 31e559c3-bd7c-4e1b-9385-024431f8635a [reviewer]`。
- 日志定位:
  - 协作解析和 child task 创建成功。
  - reviewer 子任务已派发到 `codex`,并进入 `Stream start`。
  - 没有后续 `Stream output` / `Adapter process exited`,进程表显示 Codex CLI 子进程仍在运行。
  - 根因不是 Telegram render 或协作协议,而是底层 Codex CLI 长时间无 stdout。
- 修复远程可中断缺口:
  - 新增 `/interrupt <task_id>` 命令。
  - `TaskBus.interrupt()` 支持 task id 前缀匹配,会拒绝 unknown / ambiguous / non-running task。
  - Orchestrator 返回 `Task interrupted: <short_id>` 或明确失败原因。
  - 中断 running 任务会继续更新 `interrupted` 状态并记录 `task_interrupted` 审计事件。
- 新增 PITFALL P-014,记录 reviewer accepted 后 Codex 长时间无 stdout 且 IM 无中断入口的问题。
- 更新 Phase 5 collaboration playbook 和 daily ops。
- 验证通过:定向 66 个单测;完整验证见本轮交接。

**Round 52**(2026-05-06,Codex):
- 人类补充真实 Telegram 验收结果:
  - `/project`、`/team`、`/roles` 首行加粗和 `/role propose` Confirm / Discard 按钮均已验证通过。
  - `/blockers` 仍缺少格式。
  - `/brief`、`/next` 的 `Boss summary` 部分格式正确,但 `Facts` 部分缺少结构化样式。
- 修复项目状态 Facts 渲染:
  - `_heading_message()` 不再只给首行加粗,会为项目消息中的小节标题生成 `MessageTextSpan(BOLD)`。
  - 对事实文本里的 slash command 片段生成 `MessageTextSpan(CODE)`,例如 `/approve`、`/reject`、`/ask`、`/blockers`。
  - `project_summary_message()` 继续把 facts spans 平移到 `Facts` 区域,因此 summary + facts 组合消息也能保留 facts 样式。
- 新增 `tests/unit/test_project_messages.py` 覆盖 `/blockers` 小节 / 命令 spans,以及 summary 组合消息保留 facts spans。
- 在 `docs/human/daily-ops.md` 补充 Phase 5 `@reviewer` 真实协作 smoke test 推荐 prompt。
- 验证通过:159 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`。

**Round 51**(2026-05-06,Codex):
- 人类验证 `/brief` 等 Boss summary 能力有效,指出主要问题是 summary 内部 `**bold**`、反引号、无序列表等 Markdown 文法没有渲染。
- 修复 `project_summary_message()`:
  - summary 里的 `- ` / `* ` 列表前缀转换为 `• `。
  - `**bold**` 转为干净文本 + `MessageTextSpan(BOLD)`。
  - `` `code` `` 转为干净文本 + `MessageTextSpan(CODE)`。
  - `*italic*` 转为干净文本 + `MessageTextSpan(ITALIC)`。
  - 继续保留 `Boss summary` / `Facts` heading spans 和完整 Facts 原文。
- 在已验证短状态 summary 基本可用后,将同样 summary 机制扩展到 `/daily` / `/weekly`;仍保留完整 Facts。
- 新增 `tests/unit/test_project_messages.py`,覆盖 summary Markdown 到 spans 的转换。
- 本地定向测试已通过;完整验证见本轮交接。

**Round 50**(2026-05-06,Codex):
- 人类确认 Round 49 的 Telegram render / button 能力有效,要求继续开发后续能力。
- 新增 `ProjectSummaryCoordinator`,为 `/brief`、`/risks`、`/blockers`、`/next` 生成顶部 `Boss summary`:
  - 输入只使用现有本地事实消息。
  - 通过当前项目 lead appointment/provider session 发起只读 summary task。
  - 输出保留完整 `Facts` 原文,摘要只是顶部管理视角说明。
- 新增 `aico.intent=project_summary` 内部元数据,风险识别将 project summary task 视为 read-only,避免事实文本中出现 `/approve`、`run tests`、`write docs` 等词时误触发审批。
- summary task 如果没有 lead、provider busy、adapter 拒绝或输出失败,命令会直接发送原本的事实消息,不让摘要失败影响状态查询。
- `project_summary_message()` 会把 `Boss summary` 和 `Facts` 作为独立 heading span,Telegram 可加粗展示。
- 本轮未给 `/daily` / `/weekly` 加 LLM summary,避免扩大范围;它们仍是本地事实报告。
- 本地 156 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests` 全绿。

**Round 49**(2026-05-06,Codex):
- 按下一轮最高优先级,将 ADR-0013 的 IM render contract 用到项目办公室关键消息。
- `project_messages.py` 为项目办公室、团队、岗位、任命、撤任、lead、role proposal 等消息首行增加 `MessageTextSpan(BOLD)`,Telegram 会映射为 HTML 加粗;纯文本 `text` 保持不变。
- `role_proposal_message()` 增加 `MessageAction`:
  - `Confirm` → `/role confirm`
  - `Discard` → `/role discard`
- Telegram Channel 支持 `callback_query`:按钮点击会被转换为 `IncomingMessage(content.text=<callback data>)`,复用现有命令解析;同时调用 `answerCallbackQuery` 避免 Telegram 客户端一直转圈。
- 新增回归测试覆盖 role proposal actions 和 callback query 转入命令消息。
- 本地 154 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests` 全绿。

**Round 48**(2026-05-05,Codex):
- 人类确认 Project Team / Appointment 与 Role proposal confirmation 的真实 Telegram 验收均已通过:
  - 重复 `/appoint ... as tester ...` 不再让 `/team` 出现多个 tester。
  - `/lead tester` 后 `/team` 能看到 lead。
  - `/role propose` 后 `/role confirm`,新增 role 能在 `/roles` 中看到。
- 按下一轮高优先级先做结构拆分,新增 `RoleProposalCoordinator`,把 role proposal 的内部任务提交、输出收集、provider session busy/idle 和 JSON 解析流程从 `Orchestrator` 移到 `src/aico/core/role_proposal.py`。
- `Orchestrator` 只保留接线逻辑,类体从 482 行降到 439 行,继续满足单类 <500 行硬约束。
- 修复拆分时暴露的 `risk -> role_proposal -> task_bus -> risk` 循环导入,`TaskBus` 在 role proposal 模块中改为 type-checking only import。
- 本轮没有改变 `/role propose`、`/role confirm`、`/role discard` 的用户可见语义。
- 继续完成 IM 文案渲染层第一切片: `MessageContent` 增加平台无关 `MessageTextSpan` / `MessageAction`,Telegram Channel 将 spans 映射为 HTML、actions 映射为 inline keyboard;纯文本消息不变。
- 新增 ADR-0013,记录不把 Telegram HTML / reply_markup 写进核心消息层的决策。
- 本地 153 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests` 全绿。

**Round 19**(2026-04-28,Codex):
- 调研 A2A / ACP / MCP 当前状态,决定 Phase 5 MVP 采用内部 A2A-inspired 轻量协作指令,不直接实现 HTTP A2A。
- 新增 `src/aico/core/collaboration.py`,支持解析 Adapter 输出中的 `@persona: request`。
- `Orchestrator` 识别协作指令后创建目标 persona 子任务,复用现有 TaskBus、审批、审计和状态机。
- 默认 implementer persona 提示增加 reviewer 协作指令说明。
- 新增 ADR-0009 和 Phase 5 playbook,并解决 B-002。
- 本地 88 个单测、`ruff check`、`ruff format --check`、`mypy` 全绿。

详见 [`docs/journal/ROUNDS.md`](docs/journal/ROUNDS.md)

**Round 20**(2026-04-28,Codex):
- 人类真实测试发现 `@reviewer review一下...` 没触发 Codex/reviewer,因为协作解析只支持 `@reviewer: ...` 冒号语法。
- 协作指令解析扩展为同时支持 `@persona request` 和 `@persona: request`,仍要求行首触发以避免误判。
- 修复 Telegram polling 串行 await 长任务 handler 的问题;现在每条 incoming message 会后台分发,长任务运行时 `/status` / `/audit` 不再被 polling 阻塞。
- 新增 PITFALL P-008 / P-009,更新 Phase 5 playbook 和 daily ops。
- 本地 90 个单测、`ruff check`、`ruff format --check`、`mypy` 全绿。

**Round 21**(2026-04-28,Codex):
- 人类真实使用中发现 Telegram 长文本只收到部分信息。
- 定位为流式输出持续编辑同一条消息,超过 Telegram 4096 字符限制后 Bot API 失败,handler 中断。
- 新增 `StreamedMessageWriter`,按 3900 字符保守上限拆分长输出;当前消息装满后继续发送下一条消息,避免内容被截断。
- 梳理并向人类说明 AICO 对 prompt 的实际加工:路由前缀剥离、persona role instruction 前置、协作子任务 payload 包装、协作指令行消费、Claude/Codex CLI 权限参数差异。
- 新增 PITFALL P-010,更新 troubleshooting / daily ops / playbook / changelog。

**Round 22**(2026-04-29,Codex):
- 新增 `collaboration_requested` 审计事件,在 AI 间协作触发 reviewer 子任务前记录 parent task 与 child task 的关系。
- 新增 `src/aico/core/commands.py`,把内置 IM 命令解析从 `Orchestrator` 拆出,并支持 `/approve@bot abcdef12` 这类 Telegram bot suffix。
- `Orchestrator` 从 364 行降到 318 行,降低后续命令扩展风险;`TaskBus` 保持 496 行,未突破硬上限。
- 风险识别从散落 marker tuple 改为 `RiskRule` 规则表,新增单测覆盖多规则命中时保留原因。
- 本地 targeted tests 已通过;完整验证见本轮交接。

**Round 23**(2026-04-29,Codex):
- 人类反馈 `/claude` 超长文本请求没有收到结果,怀疑卡住或长文本仍有问题。
- 新增后台日志配置:`AICO_LOG_LEVEL`、`AICO_LOG_PATH`,默认写 `logs/aico.log` 并同步输出控制台。
- 在 Telegram Channel、Orchestrator、Claude/Codex Adapter、StreamedMessageWriter 记录关键链路日志,包括入站消息、任务路由、ack、CLI 进程启动/退出、stdout chunk 长度、Telegram send/edit 长度和长文本分片。
- 记录 P-011,明确长任务没结果时先用日志区分 busy、CLI 未退出、无 stdout、Telegram 出口失败。

**Round 24**(2026-04-29,Codex):
- 人类确认 Adapter 层和 Loop 层方向,要求 Agent Harness 薄层继续简化:tools/skills 由 Claude/Codex provider 自己拥有,AICO 仅通过 Adapter 翻译和展示。
- 新增 ADR-0010,明确原话边界:`AICO Agent Harness is a session and capability facade, not a tool execution runtime.`
- 新增 `src/aico/core/agent_session.py`,定义 `AgentCard`、`ProviderSessionRef`、`AgentSession` 和 `InMemoryAgentSessionStore`。
- `Phase1Runtime` 挂载空的 `session_store`,为后续 `/sessions`、`/use`、provider session resume 做准备,不改变当前 Telegram 行为。

**Round 25**(2026-04-29,Codex):
- 基于 `InMemoryAgentSessionStore` 增加 `/sessions`、`/new <agent>`、`/use <session_id>` 命令。
- `AgentSessionStore` 增加按 channel / chat / sender 作用域保存 active session 的能力。
- `Orchestrator` 在普通消息没有显式 `/agent`、`@agent`、`agent:` 或 Telegram mention 时,会优先路由到当前 active session 的 agent。
- `Phase1Runtime` 将同一个 session store 注入 Orchestrator,让 Telegram 命令和运行时共享会话状态。
- 本轮没有接 provider resume;Claude/Codex CLI 原生会话恢复仍是下一步。

**Round 26**(2026-04-29,Codex):
- 用本机 CLI help 确认 Claude 支持 `--session-id`、`--resume`、`--continue`,Codex 支持 `codex exec resume [SESSION_ID] [PROMPT]`。
- `ProviderSessionRef` 增加 `initialized`,并新增 task metadata helper,让 active session task 能携带 provider session id 与 `new/resume` 模式。
- `Orchestrator` 将 active session 的 provider ref 注入 Task metadata;首轮成功派发后标记 provider ref initialized,后续同 session 任务自动进入 resume 模式。
- `ClaudeCodeAdapter` 首轮使用 `--session-id <uuid>`,后续使用 `--resume <uuid>`;自定义命令若已有 session 参数则不重复追加。
- `CodexAdapter` 已支持已有 provider ref 时构造 `codex exec resume <session_id> <prompt>`,并把默认 `exec --sandbox read-only` 安全提升到 resume 可接受的全局参数位置。
- `Phase1Runtime` 为 Claude persona / alias 创建 provider session ref;Codex 暂不自动创建 provider ref,等待后续 session id 捕获或显式绑定。
- 本地 114 个单测、`ruff check`、`ruff format --check`、`mypy`、`git diff --check` 全绿。

**Round 27**(2026-04-29,Codex):
- 人类反馈 `/codex inspect this` 卡住,以及 Claude 回答技能列表时只收到开头一句。
- 查 `logs/aico.log` 定位为 Telegram `editMessageText` 返回 HTTP 400 后 handler 异常退出;这不是 Codex “指定新 session id”能力缺失导致的。
- 修复 Telegram `_post()` 的错误解析顺序,先读取 Bot API JSON `description`,再处理 HTTP / business error。
- `edit_message()` 对 `Bad Request: message is not modified` 做 no-op 容错,避免尾部空白/换行 chunk 把流式输出打断。
- 新增 P-012,记录 no-op edit 400 导致长文本像被吞掉、Adapter 看起来 busy 的坑。
- 本地 Telegram Channel 单测已覆盖 HTTP 400 description 和 no-op edit 容错。

**Round 28**(2026-04-30,Codex):
- 人类要求继续迭代后续两个阶段,然后交给人类验收和审查。
- 选择 Phase 5 中两个可本地闭环的后续阶段:Codex provider session 显式绑定、agent 能力/职责可见性。
- 新增 `/bind <session_id|agent> <provider_session_id>`;支持 `/bind codex <provider_session_id>` 创建并激活 reviewer/Codex session,后续普通消息以 `resume` 模式进入 provider session。
- 新增 `AgentDirectory` 和 agent card 构建,从 persona + adapter 生成只读能力门面,不复制 provider tools/skills registry。
- 新增 `/agents`、`/agent <agent>` 展示角色、adapter、provider、status、capabilities 和 skills/tools 来源。
- 新增 `/skills <agent>`、`/tools <agent>`,把能力探测问题路由给底层 provider 自己回答。
- 把命令输出渲染移动到 `command_messages.py`,让 `Orchestrator` 保持在 500 行以下。
- 本地定向单测已覆盖命令解析、agent directory、provider bind 和 skills introspection。

**Round 29**(2026-05-04,Codex):
- 人类已真实验收 `/agents`、`/skills`、`/tools`,并指出下一阶段痛点不是裸 session,而是多项目长期迭代时缺少项目进展、风险、日报/周报等公司语义。
- 确定 Project Assignment Layer:Agent 是员工,Project 是项目,Assignment 是员工在项目里的岗位/工位;provider session、权限、role prompt、工作目录和状态都绑定到 Assignment/seat。
- 决定 Assignment 主要通过配置文件维护;MVP slash command 只做查看和切换,不做 `/assign ...` 这类聊天内组织架构修改。
- Prompt 模板分为 Agent Base Prompt、Role Prompt、Project Brief、Runtime Context 四层,避免每个 Assignment 复制大段 prompt。
- `/handoff` 暂不进入 MVP,因为项目中途换 Agent 涉及上下文迁移和未完成假设传递,复杂度高。
- 新增 ADR-0011 和 `docs/architecture/project-assignment-layer.md`,并同步 README / 架构总览 / ADR 索引。

**Round 30**(2026-05-04,Codex):
- 人类要求产出两张可向用户和技术读者介绍项目的 draw.io 图:一张分层技术架构图,一张核心概念和角色分工工作流程图。
- 新增 `docs/architecture/aico-layered-architecture.drawio`,按用户体验/应用运行时/公司模型与治理/协议适配器/本地 provider 与持久化自上而下分层。
- 新增 `docs/architecture/aico-concepts-workflow.drawio`,解释 Human Manager、Project、Agent Catalog、Assignment/seat、provider session、prompt stack、审批审计和 AI 间协作流程。
- 更新 `docs/architecture/overview.md`,加入两张可编辑图的入口链接。
- 使用 XML 解析验证两个 `.drawio` 文件格式有效。

**Round 31**(2026-05-04,Codex):
- 开始实现 Project Assignment Layer MVP 的第一切片。
- 新增 `src/aico/core/project_assignment.py`,定义 `CompanyAgentProfile`、`ProjectProfile`、`AssignmentProfile`、`ProjectAssignmentConfig` 和 `ProjectAssignmentDirectory`,支持配置校验、active project、默认 assignment 和 task metadata 注入。
- 新增 `config/projects.example.json` 和 `AICO_PROJECT_CONFIG_PATH` 配置入口;未配置时会基于当前 persona/agent 自动生成默认 `aico` 项目 assignment。
- 新增 `/projects`、`/project <project>`、`/use project <project>`、`/assignments [project]`、`/assignment <seat>` 命令。
- `/use project aico` 后,当前聊天 + 发送者的普通消息会路由到项目默认 assignment,provider session ref 绑定到 assignment seat;显式 `/claude` / `/codex` / `@reviewer` 仍优先。
- 将 agent/project/session 类命令处理拆到 `src/aico/core/orchestrator_commands.py`,让 `Orchestrator` 回到 467 行,低于单类 500 行硬约束。
- Targeted tests 53 个通过;ruff 和 mypy targeted checks 通过。

**Round 32**(2026-05-04,Codex):
- 人类指出 `assignment/seat/use role` 不符合唯一老板派发任命的直觉,要求在正式使用前直接改成老板视角设计。
- 决定把 Assignment 的产品层表达改为 Appointment / Team:`seat` 保留为内部稳定 id,主路径命令改为 `/project`、`/team`、`/who`、`/appoint`、`/ask`、`/lead`。
- 新增 ADR-0012,明确 boss-facing team commands 和 role system,并否决 `/use assignment <seat>` 作为主路径。
- 重写 `docs/architecture/project-assignment-layer.md`,补齐 RoleTemplate / Project Role Override / Appointment Contract / Prompt Stack / 新项目默认任命设计。
- 完善 role 体系:除 implementer / reviewer 外,加入 tester、pm、architect、security、docs、ops、analyst、designer 等可选岗位。

**Round 33**(2026-05-04,Codex):
- 实现 boss-facing Project Team 命令 MVP:`/project <project>` 进入项目办公室,`/team` 查看团队,`/who <role>` 查看岗位负责人,`/appoint <agent> as <role>` 任命员工,`/ask <role> <task>` 单次派活,`/lead <role>` 设置默认牵头角色。
- `ProjectAssignmentConfig` 新增 `roles`、`ProjectProfile.roles`、`appointments`,旧 `assignments` 字段继续兼容。
- `ProjectAssignmentDirectory` 支持 runtime appointment upsert、按 role 查 appointment、设置默认 role,并继续为旧 assignment/seat 命令提供兼容。
- `config/projects.example.json` 改成 roles / project role override / appointments 示例,包含 implementer、reviewer、tester、pm 等岗位。
- 新增/更新单测覆盖命令解析、appointment runtime 更新、`/ask` 路由到 role appointment、`/lead` 后普通消息走新默认 role。
- 本地 133 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests` 全绿。

**Round 34**(2026-05-04,Codex):
- 人类真实执行 `/appoint Claude as tester read_repo run_tests` 返回 `Cannot appoint Claude as tester`。
- 定位为命令层能用大小写不敏感的 `AgentDirectory.resolve()` 识别 `Claude`,但 `ProjectAssignmentDirectory.upsert_appointment()` 再用原始 `Claude` 精确查配置 key `claude`,导致任命被拒。
- 修复 `ProjectAssignmentDirectory` 的 agent / role / project lookup,统一使用大小写不敏感、下划线/横线兼容的 ref 解析;runtime appointment 会写入 canonical `claude` / `tester`。
- 新增单测覆盖 `/appoint` 中 `Claude` / `Tester` 这类人类自然输入。
- 本地 133 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests` 全绿。

**Round 35**(2026-05-04,Codex):
- 人类指出 `/default tester` 仍偏工程视角,要求改成更像老板语言的 `/lead tester`,并继续开发。
- 新增 `CommandName.LEAD`,主路径使用 `/lead <role>` 设置当前项目默认牵头 role;`/default <role>` 保留为兼容别名。
- 命令输出从 `Default role` 改为 `Lead role`,强调“由哪个岗位牵头”。
- 新增 `src/aico/core/prompt_stack.py`,实现 Appointment prompt stack MVP。
- 走 project appointment 的任务会渲染 Agent、RoleTemplate、Project、ProjectRoleOverride、Appointment Contract 和 Current task;显式 `/claude`、`/codex`、`@reviewer` 等非 appointment 路由仍走原 persona prompt。
- `RoleProfile` 增加 `inline_prompt`,`ProjectRoleProfile` 增加 `inline_prompt_override`,`ProjectProfile` 增加 `brief`,为后续配置内 prompt 文案和项目简报做准备。
- 本地 133 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests` 全绿。

**Round 36**(2026-05-04,Codex):
- 继续向后开发 Project Team / Appointment 验收面,新增项目办公室只读摘要能力。
- 新增 `/brief [project]`,基于本地 Project 配置、team appointments、lead role、最近 task snapshots 和 audit events 生成项目简报。
- 新增 `/risks [project]`,从最近失败/拒绝/中断/等待审批任务、高风险任务和风险审计事件生成风险列表。
- `/brief` 和 `/risks` 不调用 provider、不假装已有共享记忆层;当前是本地状态摘要 MVP。
- 新增单测覆盖 `/brief`、`/risks` 命令解析和 orchestrator 输出。
- 本地 134 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests` 全绿。

**Round 37**(2026-05-04,Codex):
- 人类开始验证,同时要求继续开发。
- 新增 `src/aico/core/project_docs.py`,提供受限 project document snippet 读取能力。
- `ProjectProfile` 新增 `blockers_doc` 和 `pitfalls_doc`;默认 AICO 项目和 `config/projects.example.json` 配置 `BLOCKERS.md` / `PITFALLS.md`。
- `/brief` 会读取 north star / status / journal 文档短片段;`/risks` 会读取 blockers / pitfalls 文档短片段。
- 文档读取限制为每个文件最多 4 行、单行最多 140 字符;文件不存在或读取失败时安静跳过,不会让 Telegram 命令失败。
- 新增 `tests/unit/test_project_docs.py`,覆盖文档片段读取和缺失文件跳过。
- 本地 136 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests` 全绿。

**Round 38**(2026-05-04,Codex):
- 人类继续 Telegram 验证,同时要求继续向后开发。
- 新增 `/daily [project]` 和 `/weekly [project]` 本地项目报告命令,分别按最近 24 小时 / 7 天窗口聚合团队、牵头 role、完成项、未完成项、风险和项目文档短片段。
- 报告命令复用 Project Team / Appointment 语义,仍只基于当前 AICO 进程内 task/audit 状态和受限文档片段,不调用 provider,不伪造长期共享记忆。
- 更新架构文档、daily ops、CHANGELOG 和 draw.io 图,把 `/daily` / `/weekly` 从设计态推进到已实现的项目状态面。
- 新增单测覆盖命令解析和 Orchestrator 日报/周报输出。
- 本地 137 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check` 全绿;draw.io XML 解析通过。

**Round 39**(2026-05-05,Codex):
- 人类真实使用 `/risks` 后指出输出混入 `write_files` 审批、`unknown adapter/persona` 等底层信号,不符合“项目风险”的直觉。
- 将 `/risks` 收窄为真正项目交付风险:失败/中断任务、破坏性任务和 blockers / pitfalls 文档片段;普通写文件审批、`approval_requested` 审计事件和未知 persona 路由噪音不再展示。
- 新增 `/blockers [project]`,专门展示当前卡住的工作和待决策项,包括等待审批、失败/拒绝/中断任务、未知 persona 等执行/系统问题和 blockers 文档片段。
- 新增回归测试覆盖人类遇到的 `write_files + unknown persona` 噪音场景,确认 `/risks` 不展示这些项,而 `/blockers` 能展示它们。
- 更新 `CHANGELOG.md`、`docs/human/daily-ops.md` 和 Project Team 设计文档。
- 本地 138 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check` 全绿;draw.io XML 解析通过。

**Round 40**(2026-05-05,Codex):
- 人类确认 `/risks` 新语义验收没问题,要求继续开发后续能力。
- 先把 Project/Team/Report 命令消息渲染拆到 `src/aico/core/project_messages.py`,让通用 `command_messages.py` 不再承载项目状态面输出。
- 将 `DirectoryCommandHandler` 的 report 发送辅助逻辑移出类体,使 `Orchestrator` 和 `DirectoryCommandHandler` 类体继续低于 500 行硬约束。
- 新增 `/next [project]`,基于本地 project/team/task 状态给出下一步建议动作:优先处理待审批、失败/中断/拒绝任务和路由/配置问题;没有卡点时建议把任务交给当前 lead role。
- `/next` 只支持 slash command,不把普通英文 `next` 当命令,避免误吞用户任务。
- 新增单测覆盖 `/next` 命令解析、待审批动作建议和普通 `next` 任务不被误吞。
- 更新 `CHANGELOG.md`、`docs/human/daily-ops.md`、Project Team 设计文档和两张 draw.io 图。
- 本地 139 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check` 全绿;draw.io XML 解析通过。

**Round 41**(2026-05-05,Codex):
- 人类授权若无重大决策则持续开发,并设置小时级 heartbeat 自动化催促当前线程继续推进。
- 新增 `/roles [project]`,展示当前项目 role 模板、默认权限和已任命 / 未任命状态,补齐 `/team` 和 `/who` 之外的岗位缺口视图。
- `/roles` 支持当前 active project,也支持 `/roles aico` 显式查看指定项目。
- 新增单测覆盖命令解析和 Orchestrator roles 输出,确认 implementer 已任命、tester 未任命。
- 拆分 `ProjectCommandHandler`,把项目办公室命令从通用 `DirectoryCommandHandler` 移出,保持单类 <500 行约束。
- 更新 `CHANGELOG.md`、`docs/human/daily-ops.md`、Project Team 设计文档和两张 draw.io 图。
- 本地 140 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check` 全绿;draw.io XML 解析通过。

**Round 42**(2026-05-05,Codex):
- Heartbeat 唤醒后继续推进,选择补齐老板任命闭环里的撤任能力,不触碰持久化配置写入。
- 新增 `/unappoint <role>`,可撤销当前 active project 某个 role 的进程内 appointment。
- `ProjectAssignmentDirectory` 新增 `remove_appointment_for_role()`,撤销当前 lead role 时会回退到剩余 appointment。
- 新增撤任确认消息,撤任后 `/roles` 会显示该 role 回到 `unappointed`, `/who <role>` 会提示未任命。
- 新增单测覆盖命令解析、目录撤任与默认 lead 回退、Orchestrator 撤任输出。
- 更新 `CHANGELOG.md`、`docs/human/daily-ops.md` 和 Project Team 设计文档。
- 本地 142 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check` 全绿;draw.io XML 解析通过。

**Round 43**(2026-05-05,Codex):
- Heartbeat 唤醒后继续推进,最高优先级真实 Telegram 验收仍需人类环境配合,因此选择一个不需拍板的项目办公室体验小修。
- `/project <project>` 继续用于进入指定项目;已有 active project 时,发送 `/project` 会重新展示当前项目办公室。
- 未进入任何项目时,`/project` 会提示 `No active project. Use /project <project> first.`。
- 新增单测覆盖未进入项目时的提示、进入项目后的 `/project` 复显,并确认不会派发 Adapter 任务。
- 更新 help 文案、`CHANGELOG.md`、`docs/human/daily-ops.md` 和 Project Team 设计文档。
- 本地 143 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check` 全绿;draw.io XML 解析通过。

**Round 44**(2026-05-05,Codex):
- Heartbeat 唤醒后继续推进;真实 Telegram 验收仍需人类重启服务和发命令,因此补齐本地 Project Team acceptance flow。
- 新增 `test_orchestrator_project_team_acceptance_flow`,串起 `/project aico`、`/project`、`/brief`、`/risks`、`/blockers`、`/next`、`/daily`、`/weekly`、`/roles`、`/team`、`/who implementer`、`/appoint claude as tester read_repo run_tests`、`/ask tester ...`、`/lead tester`、普通消息、`/unappoint tester`、`/roles`、`/who tester` 和撤任后的普通消息回退。
- 验收流确认状态面不派发 Adapter 任务,`/ask tester` 和 tester lead 普通消息带 tester assignment metadata,撤任后普通消息回退到 implementer。
- 更新 `CHANGELOG.md` 和 `docs/human/daily-ops.md`,加入本地验收流命令。
- 本地 144 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check` 全绿;draw.io XML 解析通过。

**Round 45**(2026-05-05,Codex):
- Heartbeat 唤醒后继续推进;真实 Telegram 验收仍需人类环境配合,本轮优先处理 `Orchestrator` 类体接近 500 行硬约束的问题。
- 将大段命令 if/elif 分发从 `Orchestrator._handle_command()` 移到模块级 `_handle_command()` 函数,类内只保留薄代理。
- 行为不变,仍复用现有 ProjectCommandHandler、DirectoryCommandHandler、审批、拒绝和 broadcast 路径。
- `Orchestrator` 实际类体从 491 行降到 422 行,为后续能力扩展留出空间。
- 本地 144 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check` 全绿;draw.io XML 解析通过。

**Round 46**(2026-05-05,Codex):
- 人类 Telegram 验收发现多次 `/appoint ... as tester ...` 后 `/team` 可能出现多个 tester,并追问 role 扩展、lead 可见性、Telegram 文案适配和 LLM 总结。
- 将 Project appointment 的唯一语义下沉到 `ProjectAssignmentDirectory`:同一 project + role 只保留一个 appointment;重复任命会覆盖,历史/配置中重复 role 初始化时按最后一个生效。
- `/team` 现在显示当前 lead,并在对应团队成员行标记 `[lead]`。
- 新增 P-013 记录同 role 多 appointment 的坑。
- 本轮没有把“LLM 生成 role 并确认新增”“IM 独立富文本渲染”“/brief 等顶部 LLM 总结”硬塞进现有命令;这三项需要下一轮按 provider 调用、确认流和 channel render contract 设计后实现。
- 本地 145 个单测、`ruff check .`、`ruff format --check .`、`mypy src tests`、`git diff --check` 全绿。

**Round 47**(2026-05-05,Codex):
- 继续执行高优先级的 Role 创建确认流。
- 新增 `/role propose <诉求>`:当前项目 lead role 会收到只读 role proposal prompt,要求输出 JSON role 草案。
- 新增 `/role confirm` / `/role discard`:草案按当前 Telegram chat + sender 作用域暂存,确认后只加入当前进程内 project roles,不写配置文件。
- `ProjectAssignmentDirectory` 支持 runtime project role,`/roles` 能展示确认后的新 role 且默认未任命。
- 内部 role proposal task 增加 `aico.intent=role_proposal` 元数据,风险识别将其视为 read-only,避免“起草一个能跑测试的岗位”误触发 shell/write 审批。
- 本轮后 `Orchestrator` 类体已接近 500 行硬约束;继续做 IM render 或 LLM summary 前应先拆出 role proposal / task collection helper。
- 本地 targeted tests、`ruff check .`、`mypy src tests` 已通过;完整验证见本轮交接。

---

## 下一轮建议做什么(优先级从高到低)

> Agent 接手时,如果没有明确任务,从这里挑最高优先级。

1. **【最高】Boss-absent isolated system turn runner**:
   - Round 259已证明Codex Goal必须走persistent app-server并完成no-model admission；Round 260进一步冻结native Codex host
     continuation边界；Round 258已有frozen tasks/scorer/dry-run。
     当前仍没有真实AICO/Codex turn结果，禁止提前写“强于Codex Goal”。
   - AICO managed role runner、五类scenario finalizer、exact-model TaskBus transport、frozen actual fixture、single-role CLI与
     independent file/receipt observer、approval runner pause与at-most-once isolated mutation已完成；owner grant与takeover
     receipt的真实Telegram ACK/inbound dogfood也已通过，role target已绑定project assignment/provider execution。
     Codex侧signed App host candidate已取得；仍须等待owner授权的live isolated Goal fork observation，禁止自创continuation prompt。
   - receipt采集与scorer分离；Goal tokensUsed、turn/provider usage任一缺失或不一致都按budget loss，不能信被测系统自报。
   - 任何正式模型benchmark需owner另行授权，且必须使用冻结contract和真实provider usage，见
     `docs/benchmarks/boss-absent-vs-codex-goal.md`与ADR-0091。
2. **【OWNER 真实授权后】B-014 v2 standing autonomy 一次性复验**:
   - 机器缺口已由ADR-0090关闭；签发新的external `0600` schema-v2 grant，`max_runs=1`，只跑一次当前AICO pack。
   - 必须看到delivery/intent/outcome delivered、`status=done`、`budget=within_limit`、`outcome=complete`、
     `evidence=current`和criteria/source全覆盖；任何越界/usage缺失按失败留证，不换grant重跑。
   - 通过后才关闭B-014并讨论默认启用层级；token envelope不升级为美元hard quota。
3. **【OWNER 已暂停】独立 dead-man receiver 部署 + 真实 outage sample**:
   - Round 255起不再跟进、不作为发布或goal阻塞；以下内容只保留未来重开时的历史上下文。
   - Round 210 已完成可部署 receiver、持久 armed/current/outage/outbox、auth、worker-progress readiness、evidence export/verifier、容器和 runbook；当前只缺
     第二故障域、TLS/secret/owner notification endpoint 与真实 kill/launch-failure/network open-resolved 样本,见 B-012。
   - 只有owner把整机失联检测列为目标时，才按`deploy/dead-man-receiver/README.md`部署到独立主机，挂载persistent`/data`，生成互异pulse/admin
     secret,配置 owner notification sink并显式 arm；不要把 receiver 与 AICO 放在同一 Mac。
   - 验收 kill process后 launchd replacement、持续 launch failure、断网超过 TTL再恢复；每类只允许一次 open +
     一次 resolved。每类导出bundle并用strict offline verifier及`aico-commission`绑定当前runtime generation，同时保存host/TLS/fault操作证据；
     永久 uninstall 前显式 disarm,普通 stop/restart不解除监控。
   - ADR-0088已Accepted并完成Ed25519 signed evidence envelope；它不改变本项owner-paused状态，也不阻塞普通用户启动。
4. **【OWNER 已暂停】全资产 off-device 备份策略 + 隔离checkout业务恢复演练**:
   - Round 255起不再跟进、不作为发布或goal阻塞；以下内容只保留未来出现明确数据损失成本时的历史上下文。
   - Round 211-212 已完成主SQLite recovery primitive；Round 223-225完成tamper-evident audit与owner-fenced recovery；
     Round 227完成同等级memory recovery并用bounded-window core set绑定三者；Round 228绑定独立reviewed Git revision/config；
     Round 229增加control-plane secret/standing grant reinjection receipt；Round 230补齐receiver独立恢复合同；Round 231
     增加Claude/Codex live-auth receipt。schema v6的`unresolved_assets=()`只表示方法齐备，receiver artifact仍不在core set内，
     `post_restore_evidence_assets`仍要求逐项交付。
     它仍不是full DR，见B-013。
   - owner选择独立于AICO Mac的加密存储和credential方案，定义RPO/RTO、cadence、retention；scheduler只能自动
     backup+verify，不能无人值守restore。
   - 从第二故障域receiver生成独立backup并保存外部SHA/跑drill；恢复后依次运行
     `reinjection-receipt|verify-reinjection|provider-auth-receipt|verify-provider-auth`，保存两份独立receipt SHA。
     从core off-device副本跑`aico-recovery verify|verify-checkout|drill`，显式component restore后再跑
     `reinjection-receipt|verify-reinjection`，核对capture window、
     SHA/schema/count/head、`/tasks`/`/inbox`、approval/outbox和代表性IM；保存证据后才可提升DR口径。
4. **【最高】SME Agent Phase 1 Goal Brief + 真实 AICO project office dogfood**:
   - 配置入口:`projects/sme-agent/aico-project.json`;项目连续性入口:`projects/sme-agent/AGENTS.md`。
   - Goal Brief、企业样例和 metadata grounding contract 已完成本地机器 Gate及 Lead/Challenger 审查。
   - Round 195 已补本地自助 CSV intake,Round 196 已补 immutable live-commerce customer workspace runner,Round 198 已补与 runner 同规则的交付包预览和 `199 RMB` 老板验收清单。下一步先由真实商家老板完成意愿判断;只有明确认可后,才通过显式 authorization-referenced operator action 连接 workbench 与 runner。真实商家数据、外部发布和语义口径确认仍需人类授权。
   - 旧 runtime 已有意识停止;当前没有确认仍在运行的 SME-configured AICO 进程或本轮可用 bot token。启动时必须继续使用独立 state/memory/audit 路径。
   - 本机 Telegram Desktop 在当前自动化环境中启动后退出,且本任务浏览器策略禁止 Telegram Web;请从手机/客户端发送 `/use project sme-agent`、`/team`、`/inbox`、`/proposals`,再完成 proposal decision、Lead → Challenger、重启恢复和 `/morning` 证据。
   - 由人类 finance/data steward 确认收入公式、地区/月语义和 source authority 后,才进入持久化 Adapter;不要先上 Web UI、向量库或微服务。
   - 每轮必须更新 SME Agent 的 `STATUS.md`、`docs/journal/ROUNDS.md`、`docs/handoffs/current.md`,让第二天从事实和证据恢复,不依赖聊天记录。
5. **【最高】GitHub social preview owner 上传 + 机器复核**:
   - 仓库已是 `PUBLIC`,description / homepage / topics 已可由 `gh repo view` 看到。
   - `docs/assets/social-preview.png` 已生成,但 `uv run aico-github-social-preview` 仍返回
     `status: needs-owner-upload`;owner 需要在 GitHub UI 的 Social preview 上传 / 确认。
   - 上传后重新跑 `uv run aico-github-social-preview`,必须不再返回 `needs-owner-upload`;
     然后 owner 肉眼确认分享卡片正确。
6. **【最高】v0.1.0 tag + GitHub Release**(操作必须由老板亲自点确认):
   - 确认当前工作区 clean、最新 `main` CI 绿、`git tag --list v0.1.0` 为空且 `gh release list`
     没有 `v0.1.0`。
   - `git tag v0.1.0 && git push --tags`。
   - 用 [`docs/launch/v0.1.0-release-notes.md`](docs/launch/v0.1.0-release-notes.md)
     创建 GitHub Release。
   - 全流程按 [`docs/agent/09-github-release-ops.md`](docs/agent/09-github-release-ops.md) 执行。
7. **【高】Feishu 真实 URL verification / 端到端 smoke**:
   - 按 [`docs/playbooks/feishu-channel.md`](docs/playbooks/feishu-channel.md) 执行。
   - Mac App 登录只证明用户侧可收消息;仍需要开放平台自建应用、机器人能力、App ID / Secret、
     Verification Token、公网 HTTPS callback 和 `im.message.receive_v1` 事件订阅。
   - 验收通过后,再把 Feishu 从 “first slice / pending production smoke” 提升为更稳定公开入口。
8. **【高】按 [`docs/launch/playbook.md`](docs/launch/playbook.md) 执行 D0 上线**:
   - HN Show HN 单次上线只有一次机会,失败不能复发同主题。
   - HN 帖子贴出后 1 分钟内贴作者首条评论,30 分钟内开始值守评论区。
   - 同窗口 Reddit r/LocalLLaMA / r/programming / r/ChatGPTCoding / r/Anthropic
     各发 1 帖,内容互不重复(模板见 playbook §3)。
   - 中文平台可从 `docs/launch/articles/` 选择博客园 / 小红书稿先发;小红书稿已控制在
     1000 字以内,博客园稿更适合做知乎 / 博客园长文底稿。
9. **【中】Phase 8 新切片真实 IM sample**:
   - 直接可问的问题:
     - `/project aico`
     - `/overnight <小目标>`
     - `/view`
     - `/morning`
     - `/inbox`
     - `/why <short_id>`
   - 预期效果:`/overnight` lead 完成后自动排 challenger / reviewer checkpoint review;`/morning`
     能看到 lead 和 review 的可接手状态。若启用 `AICO_MORNING_PUSH_*`,指定 chat 到点收到同口径早报。
   - 验收口径:机器 Gate 先行;human 只判断手机第一屏是否方便接手、是否发到可信聊天、是否看得顺。
10. **【中】aico-view Boss Brief 产品化**:
   - Round 197 已完成确定性第一屏和跨项目隔离:审批、阻塞、昨夜产出、第一行动优先于原始 Timeline。
   - 下一步只补 B-009 的真实附件 desktop/mobile 视觉证据;不要为截图改变“IM 自包含附件、无本地服务”的产品边界。
   - 暂不自动 `/project` 后发送;如真实体验需要,再加 `AICO_VIEW_AUTO_SEND_ON_PROJECT=true`。
11. **【中】Feishu 文件附件能力评估**:
   - 若 Feishu dogfood 需要 `/view`,新增 Feishu 文件上传 Channel capability。
   - 不要在 core 中写平台分支;复用 `DocumentChannel`。
12. **【中】Lead proposal queue 真实 IM 与触发质量验收**:
   - Round 199 已完成确定性第一切片。下一步只验证 SME standing charter 的候选是否值得老板接受、冷却是否合适、手机早报是否可读;不要扩成自动执行或自由文本自主规划。
   - 真实 runtime/Telegram 样本仍按 B-010 由人类客户端触发;未取得发送授权时只做机器 Gate。
13. **【低】Future F-2**:
   - Team Karpathy Loop 只在 Phase 8 与 proposal queue 的真实 dogfood 稳定后再启动。

---

## 当前卡点

参见 [`docs/journal/BLOCKERS.md`](docs/journal/BLOCKERS.md)。B-005 已在 Round 164 通过
`OrchestratorCommandRegistry` 拆分关闭为 RESOLVED。B-006 已把"人工 dogfood 待测队列缺少机器验收分层"
关闭为 RESOLVED;当前没有 🔴 BLOCKING 卡点。长链路待测默认按机器 Gate → Agent 本机真实样本 →
1 条 human 体感 Sample 执行,不再把本机可验证事项或完整人工回归当成阻塞。B-010 是当前最高优
DEFERRED:机器 service/component-health/self-healing/secondary-alert/external-liveness/persistent-receiver/worker-readiness/evidence contract 已完成,但 owner `.env`、
真实安装和 terminal 关闭后的 IM 样本尚未完成。B-011 跟踪 owner endpoint 与真实 incident open/resolved 收件样本；
B-012 已收窄为第二故障域 receiver 部署、TLS/owner sink 和整进程/Mac outage open/resolved 真实证据。
B-013 跟踪全资产off-device加密备份策略与隔离checkout业务恢复；当前core set已绑定同机state/audit/memory、reviewed
config、reinjection与provider live-auth合同，receiver有独立恢复合同但不入set；`unresolved_assets=()`不代表post-restore
evidence已提供，所有artifact仍缺真实off-device/RPO证据，不能声称commercial disaster recovery ready。B-014的真实owner grant、trusted
scheduled target、paid provider、Telegram ACK和`max_runs=1`已在Round 256取证；剩余阻塞是单次硬token/cost边界与
`outcome=complete/evidence=current`的bounded source样本。

---

## 当前已知风险

| 风险 | 影响 | 当前应对 |
|---|---|---|
| 各 AI CLI 接口不稳定(Claude Code/Codex 都在快速演进) | Adapter 频繁返工 | 协议层做厚,把"易变"封装在 Adapter 内部 |
| 个人项目长期维护动力衰减 | 项目烂尾 | Dogfooding 强制——自己用,自己优化 |
| 范围蔓延(看到什么酷功能都想加) | 进度失控 | 北极星 + Phase 严格门禁 |
| Owner IM账号或平台凭据被接管 | 攻击者继承合法sender身份 | 当前sender+target fail closed；更高等级需平台侧撤销与密码学二次授权 |

---

## 元信息

- **项目仓库**:https://github.com/MarcelLeon/ai-company-os
- **主要维护者**:Wang
- **协作 AI**:Claude(本轮)、未来不限
