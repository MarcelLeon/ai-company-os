# Boss-First Grounding — 痛点、分层与近期基础加固设计

> 本文档是 AICO 一次"对自己实事求是"的总结。
>
> 它来自 2026-05-28 / 2026-05-29 与人类老板的两轮脑暴,目的是:
>
> 1. 把项目当前真实痛点写下来(基于源码核实,不是凭印象);
> 2. 把"近期高优:Memory + Experience、Audit + Rollback、Absence Loop"三块基础能力的设计统一沉淀;
> 3. 把跨层架构画清楚,让所有 agent(人类 / AI)接手时不需要重新拼图;
> 4. 把暂不实现但已经讨论过的方向标记为 Future,避免再被反复提案。
>
> **本文档不替代 NORTH_STAR / STATUS / ADR**。当本文和 ADR 冲突时,以 ADR 为准并提 PR 修订本文。

---

## 0. 阅读指引

| 你是谁 | 怎么读 |
|---|---|
| 第一次接手的 agent | 顺序读 §1 → §2 → §3 → §6,跳过 §4/§5(实现细节) |
| 即将落地某个 sprint | 直接读 §4 对应 sprint 切片 + §5 落地路线图 |
| 老板 / 产品视角 | 只读 §1 + §3.4 + §6 |
| 准备改架构图 | §5 嵌入了完整 drawio xml,复制到 https://app.diagrams.net 即可编辑 |

---

## 1. 真实痛点(实事求是,基于代码核实)

> 每条痛点都标注了"事实依据"(可在仓库中验证),不是空对空。

### P1:老板命令爆炸 — 视觉负担超过"管团队"承诺

**事实**:`src/aico/core/commands.py` 中 `CommandName` 枚举已经定义了 **46 个内置命令**(`/help` 到 `/interrupt`)。其中大多数是 lead/role 内务(`/appoint`、`/unappoint`、`/skills`、`/tools`、`/sessions`、`/bind` 等),但老板在 Telegram 里看到的是平铺的命令面板。

**为什么是痛点**:NORTH_STAR 第一句要求"像管理一个真实团队一样"。真实老板**不会记 46 个命令**——他只会喊"做了没?为什么?撤掉。"。AICO 把"lead 的内务工具"和"老板的核心动作"塞在同一个命令空间,违背了 boss-first。

### P2:~~lead 没有"主动机制" — 完全依赖老板先开口~~(Round 199 第一切片已解决)

**当前事实**:项目可声明显式 standing charter;`/inbox`、`/morning` 和定时 morning push 在项目空闲且团队完整时最多生成一个持久化 candidate。默认 candidate 不创建 task，老板可用 `/proposal accept <id>` 进入正常任务链。Round 213 另提供可选的 external owner-bound grant：只有 scheduled morning、精确 target/project/charter、未过期/未耗尽预算和 Codex hard-read-only boundary 的交集才可自动执行一个 inspection；interactive surfaces 不消费。更广的 blocker 超时、事件触发、写操作和自由规划仍未实现。

**为什么是痛点**:absence-first 当前只解决了"老板下指令的异步化",没解决"老板根本不开口的那段时间"。Lead 在老板沉默时无法基于职责主动推进,即使他知道 blocker 已经躺了 3 天。

### P3:Memory 没有 Experience 维度 — 经验等于事实

**事实**:`MemoryAtom`(`src/aico/core/memory.py:143`)的维度是 `purpose_tags`(GENERAL_CONTEXT / PUBLIC_BROADCAST / TASK_KEY_PROGRESS / TASK_PRIVATE / DECISION_REVIEW)+ `scope` + `sensitivity` + `confidence`。**没有 `kind=experience` 字段,没有"被注入哪个 role prompt"的 trigger,没有"被注入后效果如何"的回写链路**。

`/dream`(`src/aico/core/dream.py`)生成的 candidate memory 是普通 atom,不会自动进入 role system prompt,也不会随 Grader verdict 修正 confidence。

**为什么是痛点**:Role 当前只带通用岗位 prompt + 老板手写的项目记忆。"做过的活、踩过的坑"散落在 task snapshots 里,新接班的 role 从零开始。

### P4:Audit 在 IM 内的表达上限低 — trace 糊成一团

**事实**:`InMemoryAuditLog`以`AuditEvent`为单位写JSONL，event已有`trace_id`，Round 223增加本地SHA-256历史链和
tail checkpoint，Round 224可导出一致、离线可验证的单文件恢复点，Round 225可做disposable materialization并在
owner fence下保留现场后恢复；Round 227又把memory升级为独立process-locked hash-chain ledger，支持portable recovery，
Round 228再把独立选择的reviewed Git commit、clean tree与active config blob/hash绑定进core set，并提供恢复checkout复核；
Round 229又增加无值control-plane secret slot/grant mode合同和owner decision reinjection receipt；Round 230为第二故障域
receiver增加独立online backup、domain deep verify、disposable drill和worker-fenced restore，同时刻意不把它并入core combined
restore；Round 231再用受限Claude/Codex随机challenge和30分钟secret-free receipt补齐provider live-auth恢复合同，并明确拆出
`post_restore_evidence_assets`；Round 232让scheduled morning以exact-envelope SQLite outbox、bounded retry和secret-free
platform ACK receipt区分task liveness、transport与standing result；Round 234再把core set capture升级为默认关闭的durable
scheduled intent、immediate deep verify、crash reconciliation与RPO health，但明确不自动restore/delete，也不attest目标目录的
off-device/encryption/retention；Round 235再增加destination identity continuity和独立periodic custody deep verify，让artifact
删除、篡改、权限放宽、目录替换或复验过期不再保持false-green health。Round 236增加默认关闭、owner显式授权的bounded
retention：先落PRUNING与policy SHA、删前deep verify、保留最新代际并按最老优先有限清理，崩溃按artifact/sidecar矩阵恢复且
永久保留secret-free PRUNED tombstone；它不代表外部storage policy已配置。Round 237再增加默认关闭的scheduled disposable
drill，以独立cadence实际运行state/audit/memory production materializer，durable retry/health与retention保护避免恢复路径腐化或
失败现场被清理，但仍不触碰live state或冒充full business recovery。Round 238再把scheduled autonomy终态投影为独立
exact-envelope outbox：dispatch结果、缺证或失败会跨重启有界投递，通知失败
不会重跑provider，started提示失败也不再阻断TaskBus submit；平台ACK、dispatch、terminal outcome和human read仍分开。
Round 239再关闭“process/pulse fresh但required业务组件永久失败”的静默窗口：required health连续三次FAILED会以durable
confirmation触发secondary open，OK后发same-incident resolved；optional/DEGRADED/瞬时失败不告警，同名owned-task circuit去重，
且generic health仍不具备自动repair权限。
当前checkout没有真实owner/provider/IM/storage样本，kernel fingerprint也不是volume/provider证明，整体仍不是global transaction、平台review签名、
连续provider可用性或full DR。
memory写入和audit写入仍是独立链路，`/audit`命令仍只输出最近文本块。

**为什么是痛点**:完整性提升解决“历史有没有静默变”，没有解决“老板能否一眼理解昨晚那个PR怎么来的”。当前仍需在
`/tasks`、`/audit`、`/recall`间按trace拼接，IM文本框对树状/时序结构有天然表达上限。

### P5:Rollback 边界不清 — 撤销语义会被无限放大

**事实**:仓库当前**没有 `/rollback` 命令**(`grep -n "ROLLBACK\|rollback" src/aico/core/commands.py` 无结果)。已有的"逆向操作"是 memory 的 `archive(reason)`(`memory.py:333`)和 task 的 `/interrupt`,二者不构成完整撤销语义。

**为什么是痛点**:一旦上 `/rollback`,如果不写死"能撤什么 / 不能撤什么",用户期望会迅速膨胀到"撤掉 task 已经写到磁盘 / 已经跑过的 shell"——这两件事归 git 和文件系统管,AICO 撤不了,但用户会以为撤了。

### P6:Phase 8 自己 dogfood 效果不佳 — 项目对自己最严的判罚

**事实**:STATUS.md Round 126(2026-05-27)明确写:"Phase 8 Absence Loop 真实 IM dogfood 已由人类执行;**效果不佳且暂不继续投入 native output 方向**,当前 dogfood 使用 `AICO_PREFER_NATIVE_CHANNEL_FORMAT=false`"。STATUS.md 第 291-292 行的"多 step / 多 agent 夜间自动编排"和"早报自动生成或定时推送"仍是 `[ ]`。

**为什么是痛点**:NORTH_STAR 第三句"Dogfooding 是唯一的验收标准"。Phase 8 是 absence-first 的兑现入口,但项目自己没用顺。根因推测(待验证):**经验没复用 + 留痕不可视,导致老板早上不敢直接接手 AI 跑过的结果**——这正是 §2 三块基础能力要解决的。

---

## 2. 解法总览(痛点 → 分层 → 命令归属)

| 痛点 | 解法 | 命令归属 |
|---|---|---|
| P1 命令爆炸 | **命令分层**:boss / lead / role / harness 四档,老板只看 6 个核心动作 | §3.4 |
| P2 lead 不主动 | **第一切片已实现**:显式 Standing Charter + reviewable Proposal Queue(Round 199) | §4 |
| P3 经验等于事实 | **Memory 与 Experience 分层**:同存储不同 kind,Experience 才会按 trigger 注入 role prompt | §3.1 |
| P4 audit 糊 | **统一 trace_id 事件流**;IM 侧只暴露 `/why`,深度查询走 aico-view | §3.2 + §3.3 |
| P5 rollback 边界不清 | **/undo 智能撤销**,语义边界写死:**只撤 AICO 内部状态(memory/experience/assignment),不撤 git/shell/file** | §3.2 |
| P6 Phase 8 dogfood 不顺 | **基础三件先做强**(Memory+Experience / Audit+Rollback / aico-view),再回到 Phase 8 完善 | §5 |

**贯穿原则**:
- **Boss-first + Absence-first**:老板手机/地铁/床上可用,写操作收口于 IM,只读视图收口于 aico-view。
- **写在 IM、看在 Web**:IM 是命令面,Web 是展示面;老板不切换工具做决策。
- **每个新机制必须能审、能撤、能溯**:不增加无法回滚的能力。

---

## 3. 三块基础能力 + aico-view 详细设计

### 3.1 Memory + Experience 分层 (Priority 1)

**核心区分**:

| | Memory(事实) | Experience(经验) |
|---|---|---|
| 来源 | `/remember`、agent 写入、`/dream` candidate | 由 Memory 经审批晋升 |
| 是否注入 prompt | **默认否**,按 retrieval 召回 | **是**,按 role + trigger 自动注入 system prompt |
| 生命周期 | active / archived | candidate → reviewed → active → archived |
| 治理 | scope / purpose / sensitivity / confidence | 同上 + applies_to + trigger + injection_history |

**数据模型新增**(对 `MemoryAtom` 的最小扩展,不另起一张表):
- `kind: MemoryKind = "fact" | "experience"`(默认 fact,与现有 `purpose_tags` 正交)
- `experience: ExperienceMeta | None`:
  - `applies_to`: 哪些 role(`tuple[RoleId, ...]`)
  - `triggers`: 哪些条件下注入(goal 包含 X / task type Y / risk capability Z)
  - `injection_count`: 累计注入次数
  - `verdict_hits` / `verdict_misses`: Grader 反馈
  - `lifecycle_state`: candidate / reviewed / active / archived

**新命令**(全部归 **lead 内务**,老板不直接用):
- `/experience review` — 审批 candidate(`/dream` 输出落到这里)
- `/experience list [role]` — 查看 active experience
- `/experience archive <short_id>` — 主动失效

**Sprint 切片**:
- **M1**:数据模型扩展 + `/dream` 输出改写为 `kind=experience, lifecycle=candidate`
- **M2**:`/experience review|list|archive` + role prompt 条件注入(在现有 `prompt_stack.py` 内加一层 ExperienceLayer)
- **M3**:Grader verdict → confidence + verdict_hits 回写;按 confidence 排序

### 3.2 Audit + Rollback(IM 侧极简版) (Priority 2)

**核心理念**:IM 不承担深度可视化,只承担"老板想问一句的 6 秒动作"。深度可视化走 aico-view(§3.3)。

**统一 trace_id 事件流**:
- 新增 `unified_event` 索引层,**不动现有 JSONL**(audit / memory / task state 仍各自写,只增加跨源 event_id 索引和 trace_id 串联)
- 一个 task 的所有副作用(prompt 注入 → 子任务 → memory 写入 → approval → grader verdict)共享同一 `trace_id`

**短 ID 改造**:全系统 ID 在 IM 内显示为 `mem#a3f` / `tsk#b7c` / `exp#d2e`,7 位短哈希,IM 内可读,Web 内点击展开全 ID。

**老板核心命令(只 2 个新命令)**:
- `/undo` — 智能撤销上一步,自动识别"最近的 AICO 内部状态变更",不需要老板手输 ID
- `/why <在 IM 中引用某条消息>` — 反向追溯该消息的 trace,返回简短文字摘要 + aico-view 深度链接

**`/undo` 语义边界(必须在文档和命令帮助里写死)**:
- ✅ 可撤:memory 写入 / experience 状态变更 / appointment 任命 / dream candidate 生成
- ❌ 不可撤:已经写到磁盘的文件、已经跑过的 shell 命令、已经发出去的 IM 消息(归 git/文件系统/IM 平台管)
- 撤销本身是一条新事件,不是物理回退;原事件保留可查

**lead 内务命令**:
- `/timeline --since 24h --role <id>` — 细粒度时间线过滤
- `/rollback memory|experience|task <short_id>` — 精细撤销(老板平时不碰)

**Sprint 切片**:
- **A1**:统一 event stream + trace_id 串联 + 短 ID 改造
- **A2**(老板线):`/undo` + `/why` + `/morning` 和 `/inbox` 内嵌 timeline 摘要
- **A3**(lead 线):`/timeline`、`/rollback` 精细操作 + 边界文档

### 3.3 aico-view — Mobile-friendly Read-only View (Priority 2,与 A3 并行)

**为什么不破 absence-first**:NORTH_STAR 原文是"无论身处何地""老板不在 Mac 前",**没有禁止可视化**。手机网页正好契合 absence-first(地铁、饭桌、床上都能看)。

**严格边界**:
- **只读**。所有写操作回到 IM。
- **默认不让老板手机访问 Mac 本机服务**。老板路径优先是 `/view` 发送自包含 HTML snapshot 到 IM。
- **HTTP 服务只做显式本机排障 / 可选隧道 dogfood**。若暴露到隧道,必须设 token。
- **不替代 IM**。aico-view 的每个视图都有"回 IM 操作"按钮或命令提示,通过 Telegram deep link 预填命令,或降级为复制命令。

**三个视图**:
1. **Boss Brief** — 当前项目的可接手摘要、最近事件、经验/事实数量和高频回 IM 操作。
2. **Timeline / Trace** — 按项目 / 时间展示事件流,并可展开单 task 全貌。
3. **Memory Tree** — memory 与 experience 的关系图(`derived_from` / `supersedes` / `contradicts`)

**Round 197 落地校准**:IM snapshot 的 Boss Brief 不再把“最近事件/记忆数量”当首屏主角,而是按
approval → blocker → running → overnight → quiet 选出唯一 First action,再展示 Approval needed、
Blockers、Overnight results 三块注意力卡。task、audit、memory 和 offline delegation 必须先按目标
project 投影,否则标题写着一个项目但正文混入另一项目事实,既破坏老板判断也形成附件数据泄漏。

**Sprint 切片**:
- **V1**:最小 FastAPI 服务 + 三视图 read-only(直接读 unified_event 索引)
- **V2**:Telegram deep link 回 IM 命令预填
- **V3**:本地 token 鉴权 + ngrok 风格隧道部署文档
- **V4**:IM `/view` HTML snapshot,通过 Telegram `sendDocument` 发送,不启动本机 HTTP 服务

### 3.4 命令分层(P1 痛点直接解法,不需要新 sprint)

**boss-only(6 个核心动作)**:
- `/ask`(下任务)
- `/approve` / `/reject`(审危险)
- `/interrupt`(叫停)
- `/morning`(早上接手)
- `/inbox`(看待办,内含 First action)
- `/why`(问一句为什么)+ `/undo`(撤错的)

**lead 内务**:`/appoint`、`/lead`、`/team`、`/experience *`、`/timeline`、`/rollback`、`/sessions`、`/bind`...

**role 内务**:`/skills`、`/tools`、`/use`...

**实现方式**:不删命令,**在 `/help` 输出时按受众分组**;老板查看 `/help` 时默认只显示 boss-only 6 项,`/help all` 才展开全部。这是零代码风险的渐进改造。

**Round 220 approval lease**:`/approve`不是永久能力票据。新request创建时冻结aware deadline，默认24小时且只允许
5分钟到7天；startup、task/inbox/morning视图与approval action前lazy sweep。SQLite用同一事务写
`approval=expired`、`task=rejected`和audit outbox，sink失败可重投。配置变化不追溯延长旧lease，过期后必须重新
提交当前意图；该机制不等于多人审批、owner签名或外部credential撤销。

**Round 221 owner-bound ingress**:requester自审批只在requester先被认证时安全。正式Phase 1 runtime因此在解析
command前同时绑定configured channel、owner sender和trusted reply target；陌生sender不能查询/派发/审批，owner在
错误群发命令也不会收到回复。空binding deny all，morning target与reviewer还要交叉校验。显式foreground discovery
只暴露本地escaped identity且仍拒绝业务，doctor禁止安装；sender ID不是密码学签名或账号接管防护。

**Round 222 authorization clock fence**:expiry只有在时间方向可信时才是安全边界。主SQLite保存authorization
high-water，同进程以monotonic elapsed推进最低应到时间；超过5秒的wall-clock回拨会废止全部pending approval，并阻止
新risk approval、direct preauthorization和scheduled standing grant，直到wall time追平。它不联网校时、不修改系统
时钟，也不是TPM/签名或恶意主机防护；旧authorization永不因追平而复活。

### 3.5 Absence Loop 加固 (Priority 3,等 Memory+Experience 和 Audit+Rollback 完成)

不在本文细化 sprint,只确认方向:
- 多 step / 多 agent 夜间自动编排(STATUS 291 行)
- 早报自动生成或定时推送(STATUS 292 行)
- 基于 Experience 注入,让 lead 夜间任务自动用上历史经验
- `/morning` 拼 `/timeline --since overnight` + 深度链接到 aico-view

等 §3.1 + §3.2 + §3.3 落地后,回到 Phase 8 dogfood 验证根因是否被解决。

**Round 200 运行底座进展**:macOS user LaunchAgent、secret-free heartbeat 和 `aico-service doctor` 已实现,
同时修复 non-blocking Channel 返回后 morning scheduler 被立即取消的问题。当前 checkout 尚未配置真实 `.env` 或
安装 LaunchAgent,所以本地 contract 已完成,terminal 关闭后的真实 IM 常驻样本仍是 B-010,不能标成端到端完成。

**Round 201 健康语义加固**:heartbeat v2 不再只看进程时间,而是并发检查 active Channel、default/optional
Adapter 和 enabled scheduler。required failure、optional degradation、legacy unknown 与 process stale 分开,
Telegram polling task 静默死亡也会被识别。该层仍是 synthetic observability,不替代 B-010 的真实 IM 样本。

**Round 202 状态恢复加固**:LaunchAgent crash restart 后,新进程无法继承旧 Adapter subprocess、输出流和
interrupt ownership。持久化 `RUNNING` 因此在 read model 暴露前统一对账为 `INTERRUPTED`,保留 task/Adapter/risk/
metadata 并写一次 audit;pending approval 与终态不变。AICO 明确要求核对外部副作用,不做无幂等契约的自动 replay。

**Round 203 恢复证据一致性**:SQLite schema v3 用专用 transactional outbox 在同一 transaction 提交 interrupted
snapshot 与完整、稳定 id 的 recovery `AuditEvent`;TaskBus 投递成功后才 ack。内存 audit 与内置 JSONL 按 event id
幂等,关闭 sink failure 和 append-before-ack crash 窗口。outbox 只协调交付,不改变 SQLite business state / JSONL
audit 的既有 truth boundary,也不是分布式或多 runtime exactly-once。

**Round 204 单 owner 加固**:同一 canonical SQLite state 派生一个 kernel advisory lock,并把 TaskBus recovery
从构造期延迟到 Phase1 runtime 持锁 startup。重复 terminal/LaunchAgent/Feishu process 在 state mutation 和 Channel
start 前 fail closed;process crash 自动释放,stale metadata 不阻塞。doctor 对齐 owner PID 与 launchd PID,避免手动
runtime 占锁时把 launchd crash-loop 误报健康。本层是 local single-host fencing,不是分布式 lease。

**Round 205 本地自愈加固**:heartbeat v3 将 generic dependency health 与 owned-task recovery 分开。当前
runtime 只会原地恢复自己拥有的 Telegram polling / morning scheduler,通过 5 秒 attempt timeout、60 秒
稳定期、3 次上限和 15 分钟熔断避免 tight loop;外部 Channel/provider failure 不触发恢复。熔断会由 doctor
明确报 FAIL,当前仍缺少 second-channel out-of-band notification。

**Round 206 独立告警交付**:heartbeat v4 将 owned-task incident delivery 与 primary Channel 解耦。open/healthy
transition 通过独立 SQLite active-incident + outbox 原子化,重复 heartbeat/restart 不重复建 incident；generic HTTPS
sink 按稳定 event id 至少一次投递 open/resolved,失败持久化 1/5/15 分钟退避并保持队首顺序。receiver 负责
`Idempotency-Key` 幂等,不宣称远端 exactly-once；真实 endpoint/credential/sample 仍由 owner 决定。

**Round 239 required component告警**:heartbeat先取得component health，再推进secondary alert与liveness pulse。只有required
组件连续三份时间递增FAILED才创建`health:*` incident；计数与incident/outbox跨restart持久化，OK才resolved，optional、
DEGRADED和瞬时失败不open。同名owned-task circuit去重；generic health仍只提供通知，不成为自动repair信号。

**Round 207 外部 dead-man liveness**:heartbeat v5 在component health与incident alert之后驱动低频
ephemeral pulse。stable runtime id + per-process boot id + sequence 构成幂等身份；失败只保留一个内存 pulse,
不污染 SQLite incident/outbox。独立 receiver 以 acceptance time + TTL 判 stale,首次超时开单、新 pulse 恢复
结单；正常 stop 不自动 disarm,永久停用需 owner 显式解除。这样 event loop、launch failure 或 Mac 离线不再要求
故障 sender 自报,但真实独立 receiver 的部署和 outage sample 仍是外部验收项。

**Round 240 alert-delivery-aware renewal**:pulse schema v2把secondary alert delivery状态带到独立receiver。
`disabled/healthy`既排序又续租，`pending/failed`只排序；后者持续超过TTL时生成`alert_delivery_unhealthy` outage，恢复后
healthy pulse以同reason resolved。由此dead-man不再只观察process reachability，还观察承诺的absence notification path是否
可用；仍不把local ACK冒充human read，也不让notification状态成为自动repair authority。

**Round 241 receiver notification quorum**:独立receiver可把immutable outage event并发发送到两个different-origin HTTPS route，
按owner选择的1-of-2或2-of-2 ACK quorum结算既有durable outbox。它降低单provider/credential失效导致的absence通知静默，
同时保持stable event id、队首顺序和backoff；different-origin、local quorum和delivered evidence都不等于物理独立或human read。
receiver/evidence/recovery schema v3持久化当前策略并冻结逐事件策略，pending期间拒绝策略改变，防止重启配置把2-of-2
静默降级成1-of-2；历史delivered event仍保留其原始结算合同。

**Round 242 route health edges**:schema v4把aggregate ACK拆成bounded per-route checkpoint和slot健康；partial quorum不再全绿，
而是在main settle同一事务创建degraded edge，经任一尚存route主动通知老板，后续真实event ACK再创建recovered。edge outbox、
admin status、evidence与recovery共享同一事实，但meta-alert不递归证明route健康，也不冒充continuous canary或human read。

**Round 243 silent route probe**:schema v5新增默认关闭的`silent-route-probe-v1`。它复用真实route的URL、credential、POST schema与
幂等键，先持久化exact probe再发送；一个失败窗口只标suspect，达到连续阈值才通过既有edge主动告警，ACK后恢复。只有downstream
bridge能保证probe不展示、不触发incident时才可启用；local ACK、different origin与unit fake仍不等于commercial HA或human read。

**Round 244 strict absence admission**:`aico-service`新增显式`optional|strict`准入聚合。strict直接复用runtime alert、external
liveness、scheduled recovery、disposable drill与standing autonomy的真实preflight，在任何launchctl调用前fail closed；默认optional
保留开发路径。该门禁只证明本机machine contract配置完整，不把URL存在、local preflight或安装成功扩张成外部可用、off-device、
human read或commercial readiness。

**Round 245 runtime-enforced admission**:strict不再是一次性installer检查。共享的pure gap policy同时被service和Phase1Settings使用；
dotenv mode显式建模，关键enable漂移在settings阶段fail closed，standing/recovery external binding再于runtime construction第一步复用
production preflight。Telegram/Feishu都在Channel/state前停止，LaunchAgent restart不能静默回落optional；生产settings error也不会
把Pydantic raw dotenv input写入stderr。

**Round 246 webhook authority isolation**:incident alert和dead-man pulse不再只做各自HTTPS校验；共享cross-field policy要求exact URL
不同，双方bearer非空时credential也不同，并同时进入service strict aggregate与Phase1 runtime validation。same origin/different
strict path仍可用；该机器隔离不证明第二故障域、provider独立或真实delivery。

**Round 208 可部署 dead-man receiver**:独立 FastAPI/CLI 服务以专用 SQLite 持久化 armed monitor、receiver-time
expiry、active outage 和 immutable notification outbox；admin/pulse authority 分离,迟到恢复原子生成有序
open/resolved,下游用稳定 event id 至少一次投递并持久化 1/5/15 分钟退避。worker 在 restart 时立即 reconcile,
non-root 容器把状态限定在 `/data`。同时把 liveness transport 从 incident alert URL/token 中拆开,防止两个 strict
wire protocol 因“都是 webhook”而互相拒绝。剩余证据边界是第二故障域真实部署与 kill/launch-failure/network
样本,不是本机 receiver 算法。

**Round 209 receiver 自身进展探针**:`/healthz` 与 `/readyz` 分离；后者除 SQLite外还要求 expiry/delivery
worker 最近成功推进。progress使用 monotonic clock,连续第三次内部失败或超过三个 sweep interval无成功 pass时
fail closed为通用 503,让 Compose supervisor自动 restart；下游 notification pending/backoff仍属受控降级,
不会制造 restart storm。这样 observer 不再因 HTTP server仍活着而掩盖核心 worker静默死亡。

**Round 210 可导出 outage evidence**:receiver新增admin-only、versioned bundle,按最近完整outage分组导出current
monitor、immutable open/resolved和local delivery/retry状态；pulse/public authority不能读。离线 verifier严格校验
runtime、identity、chronology、open-before-resolved和delivery order,并输出artifact exact-byte SHA-256。该链路把
真实演练从截图提升为机器可复核证据,但hash不是签名,bundle也不冒充独立host/TLS/物理fault证明。

**Round 248 当前证据验收**:同一离线verifier增加显式、可组合的最大artifact年龄、验收时刻silent-probe freshness与
all-route-health条件。历史bundle仍可做审计，但不能无限期充当commissioning证据；生成时fresh而验收时过期、从未完成probe或任一
unknown/degraded slot都会fail closed。该层不联网、不改变bundle schema，也不把输入artifact升级为receiver签名或platform ACK。

**Round 249 expiring runtime commissioning**:`aico-commission`把clean owner-reviewed Git config evidence、`.env` stat代际fingerprint与
strict dead-man exact bytes冻结到checkout-external owner-only receipt；expiry取bundle age和completed probe TTL较早值。strict
service/runtime把它加入准入图，heartbeat持续报告required `configuration:commissioning-receipt`。这把三份独立绿灯变成同一代绑定，
同时保持startup离线、secret-free和no auto-replay；local receipt仍不是签名、provider ACK、fault action或human read。

**Round 254 signed receiver evidence**:receiver用checkout-external、owner-only Ed25519私钥对domain-separated exact bundle bytes签名；
AICO只持owner-pinned SPKI公钥。signed envelope固定payload、digest、signature和key id；offline verifier与commissioning schema v2
同时绑定exact envelope/payload/key并在运行中持续fail closed。unsigned endpoint仅供历史审计；签名证明key possession，不证明
key所在物理host、TLS、真实fault action、provider ACK或human read。

**Round 211 主状态恢复原语**:AICO SQLite business state 使用 online backup API生成transaction-consistent、
standalone、`0600` artifact，并以只读 integrity/schema/SHA校验作为选择证据。restore/reset与runtime复用同一
kernel owner fence；restore在原子替换前为现有target创建verified safety backup。该切片解决同机可恢复性，不覆盖
JSONL/config/secrets，也不冒充off-device disaster recovery。

**Round 212 disposable restore evidence**:`aico-state drill`不接触live target，而是在private temp中调用同一
owner-fenced production restore、重新read-only校验schema/known-table counts并自动清理。可选`0600` report保存
input/materialized SHA、size和完成时间；它把artifact verify提升为restore-code rehearsal，但仍不证明off-device
origin、全资产恢复或真实IM业务可用。

---

## 4. 主动机制与未来方向

### F-1:Lead Self-Driving / Standing Charter(⚠️ Round 213 只读预授权切片已实现)

当前实现只从项目配置中的显式 standing charter 取 objective、role、验收证据、停止条件和 cooldown。在项目空闲且团队完整时,恢复入口最多生成一个 SQLite candidate,写入 `/inbox`、`/morning`、`/proposals`;老板可用 `/proposal accept` 进入正式 task 链路。可选 external owner-only grant 还能让 scheduler morning 对一个精确绑定、未过期、预算内的 Codex read-only inspection 自动记录决定并执行；预算在 dispatch 前持久化，重启不重置。

部署前`aico-service doctor`会通过non-mutating Phase 1 preflight复用真实Adapter/persona/project/grant binding规则；
只有显示`owner-bound runtime binding verified`才证明静态routing可启动。该证据仍低于provider登录、scheduler tick和
真实IM receipt，不能关闭B-014。

执行后不新增receipt table；inbox/morning把accepted preauthorized proposal与matching TaskSnapshot做只读join，显示
terminal/running/evidence-missing状态。这样保留TaskBus单一事实源，并把“预算已扣但dispatch evidence缺失”的
at-most-once crash window显式交给owner，而不是自动重复成本未知的任务。

Round 257把standing inspection改为tool-free bounded context：charter列出exact source/section，系统生成带完整文件SHA、原始
path/line且不超过64 KiB的evidence pack；模型没有shell/web/browser/multi-agent工具，result只能引用pack白名单行。
owner grant v2新增`max_total_tokens`并同时进入Codex rollout/context配置；terminal provider usage超过它时保留证据但拒绝结果，
morning/inbox显示budget breach。`token_stop_threshold`仍只负责下一次dispatch前的累计熔断。两者都不从token估算美元账单，
Codex response后记账的残余边界仍由B-014真实样本验证。

Codex最终消息还受versioned result schema约束，并以charter `A*`/`S*`覆盖、状态一致性与repo-relative file/line存在
生成durable outcome receipt。老板面同时看task status和outcome；prior missing/invalid/blocked会停授，原始JSON不进入
IM。该deterministic层只证明shape/coverage/location，不能把引用存在写成业务语义正确。

result contract本身也不是无界正文：32K总长、criteria/stop/source/list/text/path固定上限从charter配置贯穿schema、
Adapter、Orchestrator capture与validator。超限或duplicate/schema drift只投影bounded failure，不保存raw结果；这是
本地runtime/state安全边界，不是provider生成期token/cost enforcement。

成功结果还保存bounded source manifest：最多16个canonical repo-relative source、单文件256KiB，记录line、size与
full-file SHA-256而不保存正文。下一次dispatch只复核最近成功结果，老板面只复核最近5份；变化或缺失投影为
`drifted/missing`并停授，避免历史增长造成无界IO。path/hash不进入IM；hash只证明本地字节漂移，不是签名、Git
attestation或业务语义真值。

**边界**:不扫描 Markdown 猜工作；interactive surfaces 不自动 accept；grant 不能绕过 read-only risk、Adapter sandbox、no-network/no-resume/no-collaboration或预算；不把 charter/grant 当外部发布、支付、客户数据或法律授权。见 ADR-0037、ADR-0051。
**仍属 Future**:blocker 超期、事件触发、memory 承诺触发和 proposal 质量学习,必须先完成真实 IM dogfood。

### Future F-2:Team-level Karpathy Loop / AutoResearch

`/dream` 作为团队级自我进化入口的论点延伸。

**差异化论点(待验证)**:单 agent + self-evolving skill 缺少**协作纠错维度**;AICO 的 **team + lead + experience + memory** 多了两个维度——经验跨任务复用 + lead 仲裁防单点漂移。这是值得验证的产品论点,但**必须在 absence loop 真正稳之后做**,否则就是在不稳之上叠不稳。

---

## 5. 分层架构图(drawio xml,嵌入式)

> 将下方 xml 整段复制到 https://app.diagrams.net 即可打开编辑。
>
> 偏底层在下、偏老板体验在上。绿色 = 已实现,黄色虚线 = 本文档新增/规划,蓝色 = 老板/外部世界。

```xml
<mxfile host="app.diagrams.net" modified="2026-05-29T00:00:00.000Z" agent="Claude" version="24.7.17">
  <diagram id="boss-first-grounding" name="Boss-First Grounding">
    <mxGraphModel dx="1600" dy="1200" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1700" pageHeight="1400" math="0" shadow="0">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>

        <mxCell id="title" value="AICO Boss-First Grounding — Layered Architecture (2026-05-29)" style="text;html=1;strokeColor=none;fillColor=none;fontSize=22;fontStyle=1;align=left;fontColor=#111827;" vertex="1" parent="1">
          <mxGeometry x="40" y="20" width="1100" height="36" as="geometry"/>
        </mxCell>
        <mxCell id="subtitle" value="Higher layers = boss-facing surfaces. Lower layers = LLM providers and protocols. Cross-layer arrows show what flows between." style="text;html=1;strokeColor=none;fillColor=none;fontSize=12;fontColor=#6B7280;" vertex="1" parent="1">
          <mxGeometry x="40" y="54" width="1500" height="20" as="geometry"/>
        </mxCell>

        <mxCell id="legendDone" value="Implemented" style="rounded=1;whiteSpace=wrap;html=1;arcSize=12;strokeColor=#0F766E;fillColor=#CCFBF1;fontSize=11;fontColor=#134E4A;" vertex="1" parent="1">
          <mxGeometry x="1220" y="22" width="120" height="24" as="geometry"/>
        </mxCell>
        <mxCell id="legendNew" value="Planned (this doc)" style="rounded=1;whiteSpace=wrap;html=1;arcSize=12;strokeColor=#B45309;fillColor=#FEF3C7;fontSize=11;fontColor=#78350F;dashed=1;" vertex="1" parent="1">
          <mxGeometry x="1350" y="22" width="140" height="24" as="geometry"/>
        </mxCell>
        <mxCell id="legendBoss" value="Boss / External" style="rounded=1;whiteSpace=wrap;html=1;arcSize=12;strokeColor=#1E40AF;fillColor=#DBEAFE;fontSize=11;fontColor=#1E3A8A;" vertex="1" parent="1">
          <mxGeometry x="1500" y="22" width="120" height="24" as="geometry"/>
        </mxCell>

        <mxCell id="L6" value="L6 — Boss Surfaces (write in IM, view in Web)" style="swimlane;html=1;rounded=0;startSize=30;fontStyle=1;fontSize=14;horizontal=1;fillColor=#EFF6FF;strokeColor=#2563EB;fontColor=#1E3A8A;" vertex="1" parent="1">
          <mxGeometry x="40" y="90" width="1620" height="140" as="geometry"/>
        </mxCell>
        <mxCell id="L6_boss" value="Human Boss&#10;(phone / metro / bed)" style="rounded=1;whiteSpace=wrap;html=1;arcSize=10;strokeColor=#1E40AF;fillColor=#DBEAFE;fontSize=12;fontColor=#1E3A8A;" vertex="1" parent="1">
          <mxGeometry x="80" y="135" width="200" height="70" as="geometry"/>
        </mxCell>
        <mxCell id="L6_im" value="IM write surface&#10;(Telegram / Feishu)&#10;6 boss commands:&#10;/ask /approve /reject&#10;/interrupt /morning /inbox&#10;/why /undo" style="rounded=1;whiteSpace=wrap;html=1;arcSize=10;strokeColor=#0F766E;fillColor=#CCFBF1;fontSize=11;fontColor=#134E4A;" vertex="1" parent="1">
          <mxGeometry x="320" y="125" width="280" height="95" as="geometry"/>
        </mxCell>
        <mxCell id="L6_view" value="aico-view&#10;(mobile read-only web)&#10;Timeline / Task Trace / Memory Tree&#10;→ deep link back to IM" style="rounded=1;whiteSpace=wrap;html=1;arcSize=10;strokeColor=#B45309;fillColor=#FEF3C7;fontSize=11;fontColor=#78350F;dashed=1;" vertex="1" parent="1">
          <mxGeometry x="640" y="125" width="280" height="95" as="geometry"/>
        </mxCell>
        <mxCell id="L6_lead_ui" value="Lead / Role internal commands&#10;/appoint /lead /team&#10;/experience review /timeline&#10;/rollback /sessions /bind ..." style="rounded=1;whiteSpace=wrap;html=1;arcSize=10;strokeColor=#0F766E;fillColor=#CCFBF1;fontSize=11;fontColor=#134E4A;" vertex="1" parent="1">
          <mxGeometry x="960" y="125" width="300" height="95" as="geometry"/>
        </mxCell>
        <mxCell id="L6_help" value="/help is grouped:&#10;default = boss-only&#10;/help all = full" style="rounded=1;whiteSpace=wrap;html=1;arcSize=10;strokeColor=#B45309;fillColor=#FEF3C7;fontSize=11;fontColor=#78350F;dashed=1;" vertex="1" parent="1">
          <mxGeometry x="1300" y="135" width="200" height="70" as="geometry"/>
        </mxCell>

        <mxCell id="L5" value="L5 — Application Semantics (Commands · Inbox · Morning · Why · Undo)" style="swimlane;html=1;rounded=0;startSize=30;fontStyle=1;fontSize=14;horizontal=1;fillColor=#ECFDF5;strokeColor=#059669;fontColor=#064E3B;" vertex="1" parent="1">
          <mxGeometry x="40" y="250" width="1620" height="140" as="geometry"/>
        </mxCell>
        <mxCell id="L5_cmd" value="Command parser&#10;(commands.py · 46 cmds)&#10;dispatched to handlers" style="rounded=1;whiteSpace=wrap;html=1;arcSize=10;strokeColor=#0F766E;fillColor=#CCFBF1;fontSize=11;fontColor=#134E4A;" vertex="1" parent="1">
          <mxGeometry x="80" y="290" width="220" height="80" as="geometry"/>
        </mxCell>
        <mxCell id="L5_inbox" value="/inbox · /morning · /daily&#10;First action rendering&#10;(actionable next-step)" style="rounded=1;whiteSpace=wrap;html=1;arcSize=10;strokeColor=#0F766E;fillColor=#CCFBF1;fontSize=11;fontColor=#134E4A;" vertex="1" parent="1">
          <mxGeometry x="320" y="290" width="220" height="80" as="geometry"/>
        </mxCell>
        <mxCell id="L5_why" value="/why · /undo&#10;trace_id resolver&#10;smart-undo scope guard" style="rounded=1;whiteSpace=wrap;html=1;arcSize=10;strokeColor=#B45309;fillColor=#FEF3C7;fontSize=11;fontColor=#78350F;dashed=1;" vertex="1" parent="1">
          <mxGeometry x="560" y="290" width="220" height="80" as="geometry"/>
        </mxCell>
        <mxCell id="L5_exp" value="/experience review|list|archive&#10;(candidate → active)&#10;Lead internal" style="rounded=1;whiteSpace=wrap;html=1;arcSize=10;strokeColor=#B45309;fillColor=#FEF3C7;fontSize=11;fontColor=#78350F;dashed=1;" vertex="1" parent="1">
          <mxGeometry x="800" y="290" width="240" height="80" as="geometry"/>
        </mxCell>
        <mxCell id="L5_rollback" value="/rollback memory|experience|task&#10;(strict scope: AICO state only,&#10;NOT git / shell / file)" style="rounded=1;whiteSpace=wrap;html=1;arcSize=10;strokeColor=#B45309;fillColor=#FEF3C7;fontSize=11;fontColor=#78350F;dashed=1;" vertex="1" parent="1">
          <mxGeometry x="1060" y="290" width="260" height="80" as="geometry"/>
        </mxCell>
        <mxCell id="L5_charter" value="Standing Charter · Proposal Queue&#10;/proposals · /proposal accept|reject&#10;candidate only until boss accepts" style="rounded=1;whiteSpace=wrap;html=1;arcSize=10;strokeColor=#0F766E;fillColor=#CCFBF1;fontSize=11;fontColor=#134E4A;" vertex="1" parent="1">
          <mxGeometry x="1340" y="290" width="280" height="80" as="geometry"/>
        </mxCell>

        <mxCell id="L4" value="L4 — Orchestration Runtime (Router · TaskBus · Approval · Audit · EventBus)" style="swimlane;html=1;rounded=0;startSize=30;fontStyle=1;fontSize=14;horizontal=1;fillColor=#FEF3F2;strokeColor=#DC2626;fontColor=#7F1D1D;" vertex="1" parent="1">
          <mxGeometry x="40" y="410" width="1620" height="170" as="geometry"/>
        </mxCell>
        <mxCell id="L4_router" value="Router&#10;(commands → tasks)" style="rounded=1;whiteSpace=wrap;html=1;arcSize=10;strokeColor=#0F766E;fillColor=#CCFBF1;fontSize=11;fontColor=#134E4A;" vertex="1" parent="1">
          <mxGeometry x="80" y="455" width="180" height="60" as="geometry"/>
        </mxCell>
        <mxCell id="L4_taskbus" value="TaskBus + TaskStateRepository&#10;(SQLite persistent state)" style="rounded=1;whiteSpace=wrap;html=1;arcSize=10;strokeColor=#0F766E;fillColor=#CCFBF1;fontSize=11;fontColor=#134E4A;" vertex="1" parent="1">
          <mxGeometry x="280" y="455" width="220" height="60" as="geometry"/>
        </mxCell>
        <mxCell id="L4_approval" value="Approval gate&#10;(risk capability matrix)" style="rounded=1;whiteSpace=wrap;html=1;arcSize=10;strokeColor=#0F766E;fillColor=#CCFBF1;fontSize=11;fontColor=#134E4A;" vertex="1" parent="1">
          <mxGeometry x="520" y="455" width="180" height="60" as="geometry"/>
        </mxCell>
        <mxCell id="L4_audit" value="Audit JSONL + unified event index&#10;(trace_id, short_id)" style="rounded=1;whiteSpace=wrap;html=1;arcSize=10;strokeColor=#B45309;fillColor=#FEF3C7;fontSize=11;fontColor=#78350F;dashed=1;" vertex="1" parent="1">
          <mxGeometry x="720" y="455" width="240" height="60" as="geometry"/>
        </mxCell>
        <mxCell id="L4_grader" value="Outcome Grader&#10;(verdict → experience confidence)" style="rounded=1;whiteSpace=wrap;html=1;arcSize=10;strokeColor=#0F766E;fillColor=#CCFBF1;fontSize=11;fontColor=#134E4A;" vertex="1" parent="1">
          <mxGeometry x="980" y="455" width="240" height="60" as="geometry"/>
        </mxCell>
        <mxCell id="L4_eventbus" value="EventBus (state broadcast)" style="rounded=1;whiteSpace=wrap;html=1;arcSize=10;strokeColor=#0F766E;fillColor=#CCFBF1;fontSize=11;fontColor=#134E4A;" vertex="1" parent="1">
          <mxGeometry x="1240" y="455" width="220" height="60" as="geometry"/>
        </mxCell>
        <mxCell id="L4_dream" value="Dream candidate generator&#10;(task failures → experience candidates)" style="rounded=1;whiteSpace=wrap;html=1;arcSize=10;strokeColor=#0F766E;fillColor=#CCFBF1;fontSize=11;fontColor=#134E4A;" vertex="1" parent="1">
          <mxGeometry x="1480" y="455" width="180" height="60" as="geometry"/>
        </mxCell>

        <mxCell id="L3" value="L3 — Company Model · Memory + Experience Fabric · Project Assignment" style="swimlane;html=1;rounded=0;startSize=30;fontStyle=1;fontSize=14;horizontal=1;fillColor=#F5F3FF;strokeColor=#7C3AED;fontColor=#4C1D95;" vertex="1" parent="1">
          <mxGeometry x="40" y="600" width="1620" height="180" as="geometry"/>
        </mxCell>
        <mxCell id="L3_project" value="ProjectAssignmentDirectory&#10;(project · role · agent · appointment)" style="rounded=1;whiteSpace=wrap;html=1;arcSize=10;strokeColor=#0F766E;fillColor=#CCFBF1;fontSize=11;fontColor=#134E4A;" vertex="1" parent="1">
          <mxGeometry x="80" y="640" width="260" height="70" as="geometry"/>
        </mxCell>
        <mxCell id="L3_memory" value="MemoryFabric (kind=fact)&#10;atoms · edges · packets · broadcast&#10;scope / purpose / sensitivity / confidence" style="rounded=1;whiteSpace=wrap;html=1;arcSize=10;strokeColor=#0F766E;fillColor=#CCFBF1;fontSize=11;fontColor=#134E4A;" vertex="1" parent="1">
          <mxGeometry x="360" y="640" width="300" height="80" as="geometry"/>
        </mxCell>
        <mxCell id="L3_exp" value="ExperienceFabric (kind=experience)&#10;applies_to · triggers · lifecycle&#10;injection_history · verdict_hits" style="rounded=1;whiteSpace=wrap;html=1;arcSize=10;strokeColor=#B45309;fillColor=#FEF3C7;fontSize=11;fontColor=#78350F;dashed=1;" vertex="1" parent="1">
          <mxGeometry x="680" y="640" width="300" height="80" as="geometry"/>
        </mxCell>
        <mxCell id="L3_prompt" value="PromptStack&#10;base prompt + memory recall + ExperienceLayer&#10;(conditional injection by trigger)" style="rounded=1;whiteSpace=wrap;html=1;arcSize=10;strokeColor=#B45309;fillColor=#FEF3C7;fontSize=11;fontColor=#78350F;dashed=1;" vertex="1" parent="1">
          <mxGeometry x="1000" y="640" width="320" height="80" as="geometry"/>
        </mxCell>
        <mxCell id="L3_lead" value="Lead Decision · Goal Brief · Collaboration&#10;(challenger / reviewer / tester contracts)" style="rounded=1;whiteSpace=wrap;html=1;arcSize=10;strokeColor=#0F766E;fillColor=#CCFBF1;fontSize=11;fontColor=#134E4A;" vertex="1" parent="1">
          <mxGeometry x="1340" y="640" width="320" height="80" as="geometry"/>
        </mxCell>

        <mxCell id="L2" value="L2 — Protocol &amp; Adapter Boundary (AIAdapter · IMChannel)" style="swimlane;html=1;rounded=0;startSize=30;fontStyle=1;fontSize=14;horizontal=1;fillColor=#FFF7ED;strokeColor=#EA580C;fontColor=#7C2D12;" vertex="1" parent="1">
          <mxGeometry x="40" y="800" width="1620" height="130" as="geometry"/>
        </mxCell>
        <mxCell id="L2_aiadapter" value="AIAdapter protocol&#10;ClaudeCode · Codex · Cursor · CodeFlicker · Trae · Gemini&#10;capabilities: read_repo / code_edit / shell_exec / destructive" style="rounded=1;whiteSpace=wrap;html=1;arcSize=10;strokeColor=#0F766E;fillColor=#CCFBF1;fontSize=11;fontColor=#134E4A;" vertex="1" parent="1">
          <mxGeometry x="80" y="840" width="720" height="75" as="geometry"/>
        </mxCell>
        <mxCell id="L2_channel" value="IMChannel protocol&#10;Telegram (dogfooded) · Feishu (webhook ready, smoke test pending)&#10;platform-neutral render contract" style="rounded=1;whiteSpace=wrap;html=1;arcSize=10;strokeColor=#0F766E;fillColor=#CCFBF1;fontSize=11;fontColor=#134E4A;" vertex="1" parent="1">
          <mxGeometry x="820" y="840" width="600" height="75" as="geometry"/>
        </mxCell>
        <mxCell id="L2_view_api" value="aico-view read API&#10;(FastAPI, read-only)" style="rounded=1;whiteSpace=wrap;html=1;arcSize=10;strokeColor=#B45309;fillColor=#FEF3C7;fontSize=11;fontColor=#78350F;dashed=1;" vertex="1" parent="1">
          <mxGeometry x="1440" y="840" width="220" height="75" as="geometry"/>
        </mxCell>

        <mxCell id="L1" value="L1 — Local Providers / LLMs / Persistence (bottom layer per project convention)" style="swimlane;html=1;rounded=0;startSize=30;fontStyle=1;fontSize=14;horizontal=1;fillColor=#F9FAFB;strokeColor=#6B7280;fontColor=#374151;" vertex="1" parent="1">
          <mxGeometry x="40" y="950" width="1620" height="170" as="geometry"/>
        </mxCell>
        <mxCell id="L1_clis" value="Local AI CLIs (subprocess)&#10;claude · codex · cursor-agent · codeflicker · trae · gemini" style="rounded=1;whiteSpace=wrap;html=1;arcSize=10;strokeColor=#6B7280;fillColor=#F3F4F6;fontSize=11;fontColor=#374151;" vertex="1" parent="1">
          <mxGeometry x="80" y="995" width="500" height="65" as="geometry"/>
        </mxCell>
        <mxCell id="L1_llm" value="Underlying LLM APIs&#10;Anthropic · OpenAI · Google · ..." style="rounded=1;whiteSpace=wrap;html=1;arcSize=10;strokeColor=#6B7280;fillColor=#F3F4F6;fontSize=11;fontColor=#374151;" vertex="1" parent="1">
          <mxGeometry x="80" y="1070" width="500" height="40" as="geometry"/>
        </mxCell>
        <mxCell id="L1_storage" value="Persistence&#10;JSONL: audit / memory / experience&#10;SQLite: task state, snapshots, approvals (.aico/state.db)&#10;Config: personas.json / projects.json / .env" style="rounded=1;whiteSpace=wrap;html=1;arcSize=10;strokeColor=#6B7280;fillColor=#F3F4F6;fontSize=11;fontColor=#374151;" vertex="1" parent="1">
          <mxGeometry x="600" y="995" width="540" height="115" as="geometry"/>
        </mxCell>
        <mxCell id="L1_workspace" value="Workspace&#10;target git repos, working_directory per appointment" style="rounded=1;whiteSpace=wrap;html=1;arcSize=10;strokeColor=#6B7280;fillColor=#F3F4F6;fontSize=11;fontColor=#374151;" vertex="1" parent="1">
          <mxGeometry x="1160" y="995" width="500" height="50" as="geometry"/>
        </mxCell>
        <mxCell id="L1_unified" value="Unified Event Index&#10;cross-source trace_id store&#10;(reads from JSONL + SQLite, never owns truth)" style="rounded=1;whiteSpace=wrap;html=1;arcSize=10;strokeColor=#B45309;fillColor=#FEF3C7;fontSize=11;fontColor=#78350F;dashed=1;" vertex="1" parent="1">
          <mxGeometry x="1160" y="1050" width="500" height="60" as="geometry"/>
        </mxCell>

        <mxCell id="e_boss_im" style="endArrow=classic;html=1;rounded=0;exitX=1;exitY=0.5;entryX=0;entryY=0.5;strokeColor=#1E40AF;" edge="1" parent="1" source="L6_boss" target="L6_im">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
        <mxCell id="e_boss_view" style="endArrow=classic;dashed=1;html=1;rounded=0;strokeColor=#1E40AF;" edge="1" parent="1" source="L6_boss" target="L6_view">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
        <mxCell id="e_view_back" value="deep-link prefilled commands" style="endArrow=classic;dashed=1;html=1;rounded=0;strokeColor=#B45309;fontSize=10;" edge="1" parent="1" source="L6_view" target="L6_im">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>

        <mxCell id="e_im_cmd" value="parsed commands" style="endArrow=classic;html=1;rounded=0;exitX=0.5;exitY=1;entryX=0.5;entryY=0;strokeColor=#0F766E;fontSize=10;" edge="1" parent="1" source="L6_im" target="L5_cmd">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>

        <mxCell id="e_cmd_router" value="dispatch" style="endArrow=classic;html=1;rounded=0;exitX=0.5;exitY=1;entryX=0.5;entryY=0;strokeColor=#0F766E;fontSize=10;" edge="1" parent="1" source="L5_cmd" target="L4_router">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
        <mxCell id="e_why_audit" value="trace_id lookup" style="endArrow=classic;dashed=1;html=1;rounded=0;strokeColor=#B45309;fontSize=10;" edge="1" parent="1" source="L5_why" target="L4_audit">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
        <mxCell id="e_exp_expfab" value="lifecycle ops" style="endArrow=classic;dashed=1;html=1;rounded=0;strokeColor=#B45309;fontSize=10;" edge="1" parent="1" source="L5_exp" target="L3_exp">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>

        <mxCell id="e_router_task" value="Task create" style="endArrow=classic;html=1;rounded=0;strokeColor=#0F766E;fontSize=10;" edge="1" parent="1" source="L4_router" target="L4_taskbus">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
        <mxCell id="e_task_approval" style="endArrow=classic;html=1;rounded=0;strokeColor=#0F766E;" edge="1" parent="1" source="L4_taskbus" target="L4_approval">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
        <mxCell id="e_approval_audit" style="endArrow=classic;html=1;rounded=0;strokeColor=#0F766E;" edge="1" parent="1" source="L4_approval" target="L4_audit">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
        <mxCell id="e_grader_exp" value="verdict → confidence" style="endArrow=classic;dashed=1;html=1;rounded=0;strokeColor=#B45309;fontSize=10;" edge="1" parent="1" source="L4_grader" target="L3_exp">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
        <mxCell id="e_dream_exp" value="candidate generation" style="endArrow=classic;html=1;rounded=0;strokeColor=#0F766E;fontSize=10;" edge="1" parent="1" source="L4_dream" target="L3_exp">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>

        <mxCell id="e_task_prompt" value="assemble role prompt" style="endArrow=classic;html=1;rounded=0;strokeColor=#0F766E;fontSize=10;" edge="1" parent="1" source="L4_taskbus" target="L3_prompt">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
        <mxCell id="e_mem_prompt" value="recall" style="endArrow=classic;html=1;rounded=0;strokeColor=#0F766E;fontSize=10;" edge="1" parent="1" source="L3_memory" target="L3_prompt">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
        <mxCell id="e_exp_prompt" value="conditional inject" style="endArrow=classic;dashed=1;html=1;rounded=0;strokeColor=#B45309;fontSize=10;" edge="1" parent="1" source="L3_exp" target="L3_prompt">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>

        <mxCell id="e_prompt_adapter" value="prompt + capability" style="endArrow=classic;html=1;rounded=0;strokeColor=#0F766E;fontSize=10;" edge="1" parent="1" source="L3_prompt" target="L2_aiadapter">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
        <mxCell id="e_im_channel" value="incoming / outgoing" style="endArrow=classic;html=1;rounded=0;strokeColor=#0F766E;fontSize=10;" edge="1" parent="1" source="L6_im" target="L2_channel">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
        <mxCell id="e_view_api" value="read JSON" style="endArrow=classic;dashed=1;html=1;rounded=0;strokeColor=#B45309;fontSize=10;" edge="1" parent="1" source="L6_view" target="L2_view_api">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>

        <mxCell id="e_adapter_cli" value="subprocess spawn / stream" style="endArrow=classic;html=1;rounded=0;strokeColor=#6B7280;fontSize=10;" edge="1" parent="1" source="L2_aiadapter" target="L1_clis">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
        <mxCell id="e_cli_llm" value="HTTPS" style="endArrow=classic;html=1;rounded=0;strokeColor=#6B7280;fontSize=10;" edge="1" parent="1" source="L1_clis" target="L1_llm">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
        <mxCell id="e_audit_storage" value="append JSONL" style="endArrow=classic;html=1;rounded=0;strokeColor=#6B7280;fontSize=10;" edge="1" parent="1" source="L4_audit" target="L1_storage">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
        <mxCell id="e_task_storage" value="persist state" style="endArrow=classic;html=1;rounded=0;strokeColor=#6B7280;fontSize=10;" edge="1" parent="1" source="L4_taskbus" target="L1_storage">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
        <mxCell id="e_mem_storage" value="append JSONL" style="endArrow=classic;html=1;rounded=0;strokeColor=#6B7280;fontSize=10;" edge="1" parent="1" source="L3_memory" target="L1_storage">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
        <mxCell id="e_exp_storage" value="append JSONL" style="endArrow=classic;dashed=1;html=1;rounded=0;strokeColor=#B45309;fontSize=10;" edge="1" parent="1" source="L3_exp" target="L1_storage">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
        <mxCell id="e_view_unified" value="trace queries" style="endArrow=classic;dashed=1;html=1;rounded=0;strokeColor=#B45309;fontSize=10;" edge="1" parent="1" source="L2_view_api" target="L1_unified">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
        <mxCell id="e_unified_sources" value="indexes" style="endArrow=classic;dashed=1;html=1;rounded=0;strokeColor=#B45309;fontSize=10;" edge="1" parent="1" source="L1_unified" target="L1_storage">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>

      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
```

**层级速读**:
- **L6 Boss Surfaces** — 写在 IM(6 个核心命令),看在 aico-view(只读 web)。
- **L5 Application Semantics** — 命令分组、`/inbox` / `/morning` / `/why` / `/undo` / `/experience *` 等动作层。
- **L4 Orchestration Runtime** — Router / TaskBus / Approval / Audit + 新增的 unified event index、Outcome Grader、Dream。
- **L3 Company Model** — Project Assignment、Memory(kind=fact)、**新增 Experience(kind=experience)** 、PromptStack(增加 ExperienceLayer)、Lead Decision。
- **L2 Protocol & Adapter** — AIAdapter / IMChannel / **新增 aico-view 读 API**。
- **L1 Local Providers** — CLI 子进程、底层 LLM API、JSONL/SQLite 持久化、workspace、**新增 Unified Event Index(只读索引,不拥有真相)**。

---

## 6. 落地路线图(sprint 视图)

按优先级:

| 编号 | 内容 | 依赖 | 估算 |
|---|---|---|---|
| **M1** | ✅ MemoryAtom 增加 `kind` + `ExperienceMeta`;Dream 输出改为 candidate experience(Round 128) | 无 | 1 sprint |
| **M2** | ✅ `/experience review/list/archive` + PromptStack 加 ExperienceLayer(Round 130) | M1 | 1 sprint |
| **M3** | ✅ Grader verdict → confidence 回写 + 排序(Round 131) | M1, M2 | 1 sprint |
| **A1** | ✅ Unified event index + trace_id 串联 + 短 ID 改造(Round 129) | 无(与 M1 可并行) | 1 sprint |
| **A2** | ✅ `/undo` + `/why` + `/morning` `/inbox` 内嵌 timeline 摘要(Round 132) | A1 | 1 sprint |
| **V1** | ✅ aico-view 最小 FastAPI + Timeline/Task Trace/Memory Tree 三视图(Round 133) | A1 | 1 sprint |
| **V2** | ✅ aico-view → IM deep-link 跳转(Round 134) | V1 + A2 | 0.5 sprint |
| **A3** | ✅ `/timeline`(细粒度)+ `/rollback` 精细 + 边界文档(Round 135) | A2, M2 | 1 sprint |
| **V3** | ✅ aico-view 本地 token 鉴权 + 隧道部署文档(Round 136) | V1 | 0.5 sprint |
| **V4** | ✅ `AICO_VIEW_ENABLED=true` → `/view` IM HTML snapshot,Telegram `sendDocument`(Round 137) | V1, V2 | 0.5 sprint |
| **(Phase 8 复盘)** | 验证三块基础是否解决 dogfood 根因,再决定 Phase 8 后续 | M3, A3, V2 | 评估 |
| **(F-1 / F-2)** | Lead 主动机制 / Team Karpathy Loop | 全部上述 + Phase 8 dogfood 跑通 | TBD |

**第一刀**:M1 + A1 并行(数据层加固),其他按上表顺序。

---

## 7. 文档生命周期(给未来 agent 看)

### 7.1 如何接手

新的 agent(人类或 AI)拿到任务后:

1. **必读顺序**(CLAUDE.md 已规定):NORTH_STAR → STATUS → ROUNDS → PITFALLS → BLOCKERS → AGENTS。
2. **在动这块基础能力前**,加一步:读本文件 §1 痛点 + §3 对应小节 + §5 架构图。
3. **不要重复在 ADR 里写本文的内容**;ADR 是"决策快照",本文是"跨切面活文档"。如果决策有变,先开 ADR,然后在本文添加"⚠️ 已被 ADR-XXXX 覆盖"标注,而不是默默改本文。

### 7.2 何时更新本文

| 触发条件 | 更新动作 |
|---|---|
| 痛点 §1 中的一条被解决 | 把该条改为 `~~已解决~~` 并加 ROUNDS 链接,不要删 |
| 新增基础痛点 | 在 §1 末尾追加 P7、P8...保持编号稳定 |
| §3 中某 sprint 落地 | 把对应 sprint 状态加上 ✅,引用 ROUNDS 编号 |
| 架构图变化 | 修改 §5 内的 drawio xml(同时把 xml 另存为 `boss-first-grounding.drawio` 旁边文件) |
| Future F-1 / F-2 进入实现 | 单独开 ADR,本文 §4 加"⚠️ 已进入实现"标注 |

### 7.3 如何让模型执行落地(新会话操作指引)

新开 Claude Code 会话时,贴入下方提示词:

```
我要落地 docs/architecture/boss-first-grounding.md 的 §6 路线图中的 <Sprint 编号,例如 M1>。

请先:
1. 完整阅读 docs/architecture/boss-first-grounding.md;
2. 阅读 CLAUDE.md 中的"必读顺序";
3. 输出本 sprint 的实施计划(文件级别的改动列表 + 新增测试用例 + 文档更新清单);
4. 等我确认后再开始改代码;
5. 落地后按 docs/agent/08-self-update-protocol.md 更新 STATUS / ROUNDS / 必要时新增 ADR;
6. 完成后在本文档 §6 表格中给该 sprint 标 ✅ 并附 ROUNDS 编号。

严格遵守:不扩大 sprint 范围;不绕过 NORTH_STAR;不引入本文 §4 中仍未实现的 Future 方向。
```

---

## 8. 引用与关联

- NORTH_STAR.md(项目宪法)
- STATUS.md(实时进度,Round 127 起引用本文)
- docs/architecture/overview.md(三层架构总览,本文是其细化)
- docs/architecture/a2a-memory-fabric.md(Memory 基础设施,本文 §3.1 在其上扩展 Experience)
- docs/architecture/project-assignment-layer.md(L3 ProjectAssignment 细节)
- ADR-0020 ~ ADR-0023(Memory 系列)
- ADR-0028(SQLite task state store)
- ADR-0029(Phase 8 Absence Loop)
- docs/journal/ROUNDS.md Round 127(本文创建轮次)
