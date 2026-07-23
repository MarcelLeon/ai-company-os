# Daily Ops — 日常运维速查

> 高频运维操作速查。按场景组织,不按命令组织。
> 当前已有本地验证命令。真实启动 / 任务 / Adapter 运维命令将在 Phase 1 链路完成后填充。

---

## 启动 / 停止

```bash
uv run aico init      # 首次执行；创建owner-only .env
uv run aico doctor    # 配置与运行状态检查
uv run aico run       # 前台运行，Ctrl-C停止
```

停止时用 `Ctrl-C`。

### macOS 长驻服务

老板离开后需要继续收 IM 或定时发早报时,不要依赖一个前台 terminal。先按 Quickstart 配好仓库
`.env` 并执行 `chmod 600 .env`,再运行:

```bash
uv run aico doctor             # 安装前 readiness;不输出 secret value
uv run aico service install    # 显式安装并启动 LaunchAgent
uv run aico service status     # launchctl 原始状态
uv run aico doctor             # plist / loaded / heartbeat 综合检查
uv run aico service restart
uv run aico service uninstall
```

Dead-Man Receiver不是常驻AICO的必需组件。只有需要在整台Mac失联时仍由外部系统告警，才在另一台主机
或云服务部署它；与AICO运行在同一台Mac只能做接口测试，不能形成独立故障域。

默认`.env`使用`AICO_ABSENCE_ADMISSION_MODE=optional`，用于开发时保留可选能力。老板准备离开前改成`strict`并重新运行
doctor/install；`absence admission`必须为OK，否则launchctl不会执行。strict要求runtime alerts、external liveness、current runtime
commissioning、scheduled recovery、disposable recovery drill和standing autonomy均通过真实preflight。commission receipt必须在最终
`.env`写好signed evidence、owner-pinned receiver公钥和receipt三个checkout-external绝对路径后用`aico-commission create`生成，
绑定reviewed revision、dotenv generation、exact envelope/payload与key identity；具体命令见Quickstart。该OK只证明可信key签名，
仍不证明receiver物理host、off-device存储、平台送达或老板已读。
LaunchAgent后续异常重启也会执行strict：dotenv enable项缺失在settings加载时失败，standing/recovery外部binding漂移在
Channel/state构造前preflight失败。长期stderr不会打印Pydantic raw input；先运行secret-safe doctor，不要把strict改回optional消音。
strict进程运行中若`.env`被编辑、替换或删除，required `configuration:dotenv-generation`会FAILED并进入既有confirmed alert；
系统不会热加载或自动restart。先完成新配置外部验收，再显式restart/install。
receipt/evidence/Git config漂移或最早TTL到期时，`configuration:commissioning-receipt`也会FAILED；新一代必须使用新的artifact路径，
重新export/create/doctor后显式restart，不能覆盖旧receipt或扩大maximum age消音。

服务按 `.env` 的 `AICO_CHANNEL` 使用 `.venv/bin/aico-phase1`(Telegram)或
`.venv/bin/aico-feishu-webhook`(Feishu),所以切换 Channel、移动仓库或重建到其它路径后要重新
`install`。LaunchAgent
只在异常退出时自动重启,正常 uninstall 不会形成重启循环。stdout/stderr 在 `.aico/service/`,应用
日志仍由 `AICO_LOG_PATH` 控制。`.aico/runtime-heartbeat.json` 只含 schema、state、PID、时间戳和
脱敏 component status,不含异常详情、命令、target 或 secret。Channel、默认 Adapter、启用的 morning
scheduler 是 required;可选 Adapter 失败只标 degraded。即使 components healthy,也不等于真实任务/IM E2E。
同一 state DB 只能有一个 active runtime。owner lock 在 task recovery 前获取,由 kernel 在 crash 时自动释放;
lock 文件会保留 secret-free PID/time/resource metadata,但“文件存在”不代表仍被占用。`doctor` 会校验 active
owner PID 与 launchd PID。若手动 runtime 正在占锁,第二个 runtime 会 fail closed,不会 kill 原进程或修改 live state。

### 启用 Phase 2 双 Adapter 状态查询

```bash
export AICO_TELEGRAM_BOT_TOKEN="你的 Telegram Bot Token"
export AICO_ENABLE_CODEX_ADAPTER=true
export AICO_CLAUDE_WORKING_DIRECTORY="/Users/wangzq/VsCodeProjects/ai-company-os"
export AICO_PERSONA_CONFIG_PATH="config/personas.example.json"
export AICO_PROJECT_CONFIG_PATH="config/projects.example.json"
export AICO_OWNER_SENDER_IDS="你的 Telegram user id"
export AICO_TRUSTED_TARGET_IDS="你的 private chat id"
export AICO_APPROVAL_REVIEWER_IDS=""
export AICO_APPROVAL_MAX_AGE_SECONDS=86400
export AICO_AUDIT_LOG_PATH="/tmp/aico-audit.jsonl"
export AICO_MEMORY_PATH="/tmp/aico-memory.jsonl"
export AICO_LOG_LEVEL="INFO"
export AICO_LOG_PATH="logs/aico.log"
# 可选:默认 1800 秒。设为 0 可禁用 no-output idle timeout。
export AICO_CODEX_OUTPUT_IDLE_TIMEOUT_SECONDS=1800
# 可选:验证 Telegram native HTML 输出链路,失败会回退 rich text。
export AICO_PREFER_NATIVE_CHANNEL_FORMAT=false
env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python /opt/homebrew/bin/python3.11 aico-phase1
```

`AICO_PERSONA_CONFIG_PATH` 可省略;省略时使用内置默认 persona。指定后,配置文件中的 `adapter_name` 必须引用当前已启用的 Adapter。

`AICO_PROJECT_CONFIG_PATH` 可省略;省略时使用内置默认 AICO 项目和当前 persona 生成 project team appointment。指定后,配置文件中的 `agents.*.provider` 必须引用当前已启用的 Adapter,`appointments.*.agent` 或兼容字段 `assignments.*.agent` 必须能解析到当前 agent/persona alias。示例见 `config/projects.example.json`。

`AICO_OWNER_SENDER_IDS`和`AICO_TRUSTED_TARGET_IDS`是正式runtime控制面硬边界，最多各16项、逗号分隔。消息必须同时
匹配当前Channel、owner sender和trusted reply target；空配置会deny all。`AICO_APPROVAL_REVIEWER_IDS`可省略，默认
只有任务发起人能处理自己的危险任务；额外审批人也必须属于owner sender集合。

首次不知道ID时，只在前台临时设置`AICO_INGRESS_DISCOVERY_LOG_IDENTITIES=true`并保持两个binding为空。发送一条
消息后从本地日志复制escaped sender/target，立即停止、填入binding并关闭discovery。该模式仍拒绝业务消息，且
`aico-service doctor/install`必定FAIL，不能用于常驻服务。

`AICO_APPROVAL_MAX_AGE_SECONDS`默认86400秒，只允许300..604800秒。新approval创建时会冻结deadline；之后修改配置
只影响新请求，不能追溯延长旧审批。到期后approval变为`expired`、task变为`rejected`，owner需检查旧`/task`后重新
提交明确任务；系统不会自动批准、重提或复用旧票据。`aico-service doctor`会在install前拒绝无界或非整数值。

默认 `AICO_CLAUDE_COMMAND` 使用 `claude -p --output-format text --permission-mode bypassPermissions`。远程场景由 AICO 的 `/approve` 负责审批,避免 Claude Code 在本机再弹出无法通过 Telegram 处理的授权提示。

`AICO_CODEX_OUTPUT_IDLE_TIMEOUT_SECONDS` 默认 1800 秒。它是 no-output idle guard,不是任务总时长限制;Codex CLI 进程已 accepted 但一直没有 stdout 且超过该阈值时,AICO 会终止该进程并返回 `adapter output idle timeout after <Ns>`,避免任务长期占用并发槽位。设为 `0` 可禁用自动 idle timeout,适合老板不在时允许 agent 长时间工作;仍可用 `/interrupt <task_id>` 远程叫停。

长沉默任务不会再只停留在 `Task accepted`:AICO 会周期性编辑 IM 消息,提示 `Still running: no adapter output for <Ns>` 和 `/task` / `/interrupt` 路径。这个 quiet heartbeat 只是可观察信号,不会算作模型结果,也不会写进 lead decision memo 或 Goal Brief 输出。

如果同一岗位的 provider session 正被另一项任务占用,AICO 会显示 `Role is busy with another task`,而不是把底层 session id 发到聊天。先用 `/tasks` 找到运行中的任务,等待其完成或执行 `/interrupt <task_id>`,再重试原请求。需要排障时用 `/task <failed_task_id>` 查看保留的原始 provider 错误;AICO 不会自动新建 session,以免静默丢失岗位上下文连续性。

`AICO_AUDIT_LOG_PATH` 可省略;指定后,每条审计事件会追加写入 JSONL 文件,同时 `/audit` 仍展示进程内最近事件。
Round 62 起,启动时也会读取这个 JSONL 文件里的历史审计事件;`/metrics` 会用这些事件重建历史任务指标,因此重启后 24h / 7d 的 done / failed / interrupted 等统计不会直接清空。配置 `AICO_STATE_DB_PATH` 后,`/tasks` 也会恢复持久化 task snapshot。

`AICO_MEMORY_PATH` 可省略;指定后,Phase 7 shared memory 会写入 append-only JSONL,并在 project-scoped task prompt 中自动召回当前项目少量高置信记忆。`/remember` / `/recall` / `/forget` 是纠错、补充、排障和验收入口,不是要求老板日常手动维护记忆。

`AICO_STATE_DB_PATH` 可省略;指定后,task records、task snapshots、pending approval 和 `/overnight` 托管工单会写入本地 SQLite。它用于恢复 AICO 的业务状态,例如重启后继续查看 `/tasks`、`/task <id>`、`/overnight` 或处理仍在lease内的 `/approve`;它不等于恢复已经退出的底层 CLI 子进程。新 runtime 接管数据库时会把旧 `running` 任务改为 `interrupted`,因为 subprocess/output/interrupt ownership 已丢失;先核对文件、消息、发布等实际副作用,再显式提交新任务。AICO 不会自动 replay。尚未 dispatch且未到期的`waiting_approval`保持pending；到期项会原子变为`approval=expired`与`task=rejected`并留下audit intent。
Round 203 起,该 interrupted snapshot 与完整 recovery audit intent 在同一 SQLite transaction 提交。若 audit sink
暂时失败,intent 保持 pending 并在下次 startup 用同一 event id 重投;内置 JSONL sink 会去重。商用/常驻配置应同时
设置 `AICO_STATE_DB_PATH` 与 `AICO_AUDIT_LOG_PATH`,让恢复证据真正跨进程持久化。outbox 不是新的 `/audit` 真相源。
owner lock path 自动由 canonical state DB 派生为 `<state-db>.owner.lock`,所以不同 state DB 的开发/runtime 可独立运行;
共享同一 DB 的进程不能并存。
开发期可设置 `AICO_STATE_DB_PATH=true`,AICO 会使用 `.aico/state.db`;`false` / `0` / `off` 会视为关闭。使用 `aico-state --db <path>` 查看 schema version 和表行数;需要清空开发期业务状态时,使用 `aico-state --db <path> reset --yes`。

`AICO_RUNTIME_HEARTBEAT_PATH` 默认 `.aico/runtime-heartbeat.json`,每 30 秒原子刷新;设为空可关闭。
`AICO_RUNTIME_HEARTBEAT_INTERVAL_SECONDS` 可改刷新间隔。正常停止会写 `state=stopped`;崩溃会留下
stale running heartbeat,由 `aico-service doctor` 区分。
`AICO_RUNTIME_HEALTH_CHECK_TIMEOUT_SECONDS` 默认 5 秒,每个 Channel/Adapter/scheduler health check 并发且
单独受限;timeout 或插件异常只写 FAILED 状态,不会把 exception text 写入 heartbeat。
Heartbeat v5 还写入 secret-free `self_healing`、`alerting` 与 `liveness`:当前 owner 只会恢复自身 Telegram polling 和 enabled morning
scheduler task。连续 3 次未稳定会熔断 15 分钟,避免 tight loop;Channel API、provider 或可选 Adapter 故障
只影响 health,绝不会消耗恢复次数。看到 `recovery open` 时先查对应 task 的异常类型日志,不要直接删 lock。
可选 `AICO_RUNTIME_ALERT_WEBHOOK_URL` 把 open/resolved 通过独立 HTTPS sink 至少一次投递;事件和 active incident
先写同一 state DB transaction,HTTP 成功后才 ack。失败按持久化 1/5/15 分钟退避,队首未到期时不允许后续
resolved 越序。receiver 必须按 event id / `Idempotency-Key` 幂等;AICO 不宣称远端 exactly-once。
Round 239起，required Channel/default Adapter/scheduler即使task仍存活，只要连续三份时间递增heartbeat均为FAILED，也会生成
`health:<kind>:<name>` incident；单次失败、optional和DEGRADED不open，FAILED后的DEGRADED也不会过早resolved，只有OK或显式
改为optional才resolved。同名owned-task circuit只生成一个incident。该告警只通知，不授权restart、provider replay或restore。
`aico-state --db <path>` 会显示 `pending_runtime_alerts`和`runtime_health_alert_candidates`，reset会同时清理alert
incident/outbox/confirmation；unsafe plugin name在webhook中会被hash，异常、URL/token、target与业务正文不会持久化。
启用 `AICO_RUNTIME_LIVENESS_ENABLED` 后,heartbeat 会驱动低频 external dead-man pulse。首次发送立即发生,失败
保留同一个内存 pulse/idempotency key 重试；最近一次成功仍在 TTL 内时为 degraded,从未成功或超过 TTL 为 failed。
pulse v2还携带bounded `alert_delivery_status`：secondary alert为`pending/failed`时receiver只接受排序、不续租；若该状态
持续到既有TTL到期，会生成reason=`alert_delivery_unhealthy`的outage。后续`healthy/disabled`新pulse才续租并生成同reason
resolved。这样alert sink失败不能被fresh pulse掩盖；状态不含incident、异常、endpoint、target或正文，也不授权自动repair。
pulse 不落 AICO SQLite,并使用专用 `AICO_RUNTIME_LIVENESS_WEBHOOK_URL` / bearer；strict incident alert 与 pulse
endpoint 不能共用 URL；两侧都有bearer时也不能复用token。doctor/runtime会以`runtime endpoint isolation`固定错误拒绝，
且不回显URL/token。receiver 才是 stale open/resolved 的真相源,并须在永久卸载前由 owner 显式 disarm；普通
stop 绝不自动解除监控,Mac sleep/网络分区超过 TTL 按不可用处理。独立 receiver 的部署、arm/status/disarm 和
outage 验收见 [`deploy/dead-man-receiver/README.md`](../../deploy/dead-man-receiver/README.md)。
receiver 的 `/healthz` 只证明 HTTP process响应；容器必须探测 `/readyz`,它还要求 SQLite 可用且 expiry/delivery
worker 在三个 sweep interval内成功推进。连续第三次内部失败或进展过期会返回通用 503并交给 restart policy；
downstream notification 正在 durable backoff时仍保持 ready,避免外部抖动制造 restart loop。
Round 241起receiver可选different-origin fallback notification route。两路并发发送相同event和`Idempotency-Key`；
`AICO_DEAD_MAN_NOTIFICATION_MINIMUM_ACKNOWLEDGEMENTS=1`是availability-first的1-of-2，设2则任一路失败都会保持pending。
quorum miss继续走既有durable backoff，不能靠restart修复。notification token彼此不同且不得复用pulse/admin authority；
schema v3会冻结逐事件策略，pending期间修改route/quorum将fail closed；先按原策略drain再改。evidence的delivered只表示
该event冻结的local quorum，不是all-route送达或老板已读。
schema v4起，1-of-2部分成功不再显示全绿：失败slot转degraded，并通过尚存route发送独立健康边沿；后续真实outage event
ACK才转healthy并发送recovered。每日可用admin-only`/v1/notification-routes`核对slot与pending edge；不要把该event-driven状态
写成周期探测结果，也不要因degraded让`/readyz`触发restart。
schema v5可选silent probe会把exact intent先落盘，再用真实route的POST/credential低频探测。一个失败窗口显示suspect/PENDING，
达到持久阈值才degraded并发边沿；ACK后recovered。该合同默认disabled，只有两个bridge都保证ACK且不展示probe时才能启用。
每日核对admin `probe.last_completed_at`、ACK vector和手机无噪声；local ACK仍不是老板已读或物理HA证明。
真实 outage演练后用 admin-only `/v1/monitors/<runtime_id>/signed-evidence` 导出 bounded envelope,再在可信环境运行
`aico-dead-man-evidence <file> --trusted-public-key <receiver-public.pem> --runtime-id <id> --minimum-complete-outages 1 --require-all-delivered
--maximum-evidence-age-seconds 300 --require-fresh-notification-probe --require-all-routes-healthy`。最后三项是当前商用验收条件；
只做历史审计时才可省略。bundle只含
monitor/outage/event/delivery与notification policy事实；schema v5还包含slot health、逐event ACK、route-health edge与silent probe
checkpoint，event reason
区分`pulse_expired`和`alert_delivery_unhealthy`，并绑定创建时route/quorum，open/resolved reason必须一致。
SHA-256用于归档后字节比对；Ed25519证明owner-pinned key possession，但不能冒充第二故障域、TLS或fault-action证明。

`AICO_PREFER_NATIVE_CHANNEL_FORMAT` 默认关闭。设为 `true` 后,Telegram task 会要求 agent 优先输出 Telegram Bot API HTML 子集;AICO 会先白名单验证 HTML,验证失败自动回退到 rich text renderer。该开关用于 dogfood 模型是否能稳定输出 Channel-native 格式,不要把未经验证的模型 HTML 原样发送给 IM。

### 启用 Cursor / CodeFlicker / Trae / Gemini 可选 Adapter

这些 Adapter 默认不启用。需要让 `/agents` 展示更多可用成员时,在启动前打开对应开关:

```bash
export AICO_ENABLE_CURSOR_ADAPTER=true
export AICO_ENABLE_CODEFLICKER_ADAPTER=true
export AICO_ENABLE_TRAE_ADAPTER=true
export AICO_ENABLE_GEMINI_ADAPTER=true
export AICO_CURSOR_OUTPUT_IDLE_TIMEOUT_SECONDS=1800
export AICO_CODEFLICKER_OUTPUT_IDLE_TIMEOUT_SECONDS=1800
export AICO_TRAE_OUTPUT_IDLE_TIMEOUT_SECONDS=1800
export AICO_GEMINI_OUTPUT_IDLE_TIMEOUT_SECONDS=1800
```

默认命令:

```bash
export AICO_CURSOR_COMMAND="cursor-agent -p --force --output-format text"
export AICO_CODEFLICKER_COMMAND="flickcli -q --approval-mode yolo --output-format text"
export AICO_TRAE_COMMAND="trae-cli --print --yolo"
export AICO_GEMINI_COMMAND="gemini --approval-mode yolo --output-format text"
```

Cursor 需要本机安装并登录 `cursor-agent`;CodeFlicker 需要本机 `flickcli` 可用并完成 SSO 登录;Trae 需要 `trae-cli`;Gemini 需要 `gemini` CLI。Round 67 起这些 Adapter 声明完整 `code_edit` / `shell_exec` 能力,底层 CLI 使用非交互批准模式避免卡在本机确认。远程安全边界由 AICO 的风险识别、`/approve`、审计和 `/interrupt` 承担;不要绕过 AICO 直接在 IM 里长期使用裸 YOLO 命令。

写文件、shell 或 destructive 任务发给这些 Adapter 时,应先进入 `waiting_approval`。确认任务无误后再 `/approve <short_task_id>`;如果只是分析/总结,请在 prompt 里明确 `do not edit files`。

### Feishu Channel

Round 67 选择飞书作为第一个非 Telegram Channel,原因是官方 Server API 和事件订阅文档较完整,企业自建应用 + bot 的文本收发路径清晰。

当前已实现 `FeishuChannel` 插件和 webhook runtime,覆盖:
- `tenant_access_token` 获取。
- 通过 chat id 发送文本消息。
- 文本消息编辑 / 删除。
- URL verification challenge。
- `im.message.receive_v1` 文本事件转 `IncomingMessage`。
- `aico-feishu-webhook` FastAPI 入口,提供 `/healthz` 和默认 `/feishu/events` 事件回调。
- Feishu 事件幂等:2.0 事件按 `header.event_id` 去重,1.0 事件按 `uuid` 去重,默认本地保留 8 小时。

飞书启动示例:

```bash
export AICO_CHANNEL=feishu
export AICO_FEISHU_APP_ID="你的 Feishu App ID"
export AICO_FEISHU_APP_SECRET="你的 Feishu App Secret"
export AICO_FEISHU_VERIFICATION_TOKEN="你的 Verification Token"
export AICO_FEISHU_EVENT_PATH="/feishu/events"
export AICO_FEISHU_WEBHOOK_HOST="0.0.0.0"
export AICO_FEISHU_WEBHOOK_PORT=8080
export AICO_CLAUDE_WORKING_DIRECTORY="/Users/wangzq/VsCodeProjects/ai-company-os"
export AICO_PERSONA_CONFIG_PATH="config/personas.example.json"
export AICO_PROJECT_CONFIG_PATH="config/projects.example.json"
export AICO_AUDIT_LOG_PATH="/tmp/aico-audit.jsonl"
export AICO_MEMORY_PATH="/tmp/aico-memory.jsonl"
env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python /opt/homebrew/bin/python3.11 aico-feishu-webhook
```

Feishu 不是 long polling,需要把公网 HTTPS callback 转到本机或部署实例的 `http://<host>:8080/feishu/events`,然后在飞书开放平台事件订阅里配置这个 URL。URL verification 通过后,订阅 `im.message.receive_v1`,向机器人所在聊天发送文本,应能收到 AICO 的文本回复。Telegram 仍可继续用 `aico-phase1` 作为默认主控入口;飞书是独立 webhook 进程。

Mac App 登录只代表你能在飞书客户端里看到机器人消息;真正 smoke test 还需要开放平台侧配置:

1. 打开飞书开放平台,创建或进入企业自建应用。
2. 开启机器人能力,把机器人添加到一个测试群或单聊。
3. 记录 App ID、App Secret、Verification Token。
4. 本机启动 `aico-feishu-webhook`,并用 ngrok / Cloudflare Tunnel / 其它 HTTPS 入口把
   `https://<public-host>/feishu/events` 转到 `http://127.0.0.1:8080/feishu/events`。
5. 在事件订阅 Request URL 填入公网 HTTPS URL,等待 URL verification 通过。
6. 订阅 `im.message.receive_v1`,保存并发布应用配置。
7. 在飞书 Mac App 的机器人聊天里发 `/help`、`/status`、`/project aico`;
   预期收到 AICO 文本回复,本地日志不出现 verification token 错误或重复事件重复任务。

如果飞书事件日志显示重试,同一个 `header.event_id` 或 `uuid` 不应在 AICO 侧触发两次任务。该幂等缓存是进程内缓存,覆盖飞书常见重试窗口;进程重启后的极端重复投递仍可能重新进入 Orchestrator,后续如需要可升级为 audit / JSONL backed 去重。

### Morning Push

Round 164 起,`/morning` 可以保持手动命令,也可以配置为定时推送到指定 IM chat。该能力默认关闭,只发送同一份只读早报,不自动批准风险任务。

```bash
export AICO_MORNING_PUSH_ENABLED=true
export AICO_MORNING_PUSH_TARGET_ID="<Telegram chat_id 或 Feishu chat_id>"
export AICO_MORNING_PUSH_PROJECT="aico"
export AICO_MORNING_PUSH_TIME="09:00"
# 必填:scheduled delivery先写入主state DB，不能关闭
export AICO_STATE_DB_PATH=".aico/state.db"
# 可选:只限制IM平台ACK等待，不限制standing autonomy
export AICO_MORNING_PUSH_DELIVERY_TIMEOUT_SECONDS=60
# 可选:启动后立即推一次,便于 smoke test
export AICO_MORNING_PUSH_ON_START=true
# 可选:如果要复用某个 IM scope 的 /overnight 记录
export AICO_MORNING_PUSH_SCOPE_ID="<scope id, 默认等于 target id>"
```

默认仍只发早报。若 owner 明确希望让**一个 standing charter 的只读检查**在定时晨报后自动开始，可另行配置
owner-bound grant：

```bash
install -m 600 docs/examples/standing-autonomy.example.json \
  /absolute/private/aico-standing-autonomy.json
# 编辑外部文件：替换 identity/binding/expiry/run/duration/max_total_tokens/token threshold，保留 mode=read_only
export AICO_STANDING_AUTONOMY_GRANT_PATH="/absolute/private/aico-standing-autonomy.json"
uv run aico-service --repo . doctor
```

只有 doctor 输出 `standing autonomy: owner-bound runtime binding verified (...)` 才进入 install。它不仅检查grant文件，
还用真实Phase 1路由验证scheduled target、project/charter、appointment/persona、Codex启用状态和executable hard
boundary；检查过程不创建state/log/lock、不调用CLI或网络。`grant file verified`旧文案不代表当前版本的完整preflight。

该文件必须是当前用户所有的普通文件、`0600`、位于所有 managed project repo 之外；示例中的
`replace-with-*` 不能启动。grant 的 channel/target/thread/project 必须与上面的 scheduled morning 配置逐字段一致，
charter 必须任命给 executable 为 `codex` 的 Codex Adapter，并配置不超过8个bounded `evidence_sources`。运行时只向模型提供
不超过64 KiB的allowlisted path/line片段，固定使用 read-only、tool-free、no-network、no-resume、no-collaboration 命令，
并在 dispatch 前扣除持久化 `max_runs`。`/inbox`、手工 `/morning`、`/proposals` 和 runtime
startup 本身永远不会消费 grant。

先用 `max_runs=1`、短 `max_duration_seconds` 和保守`token_stop_threshold`验收；确认 task history 写入 preauthorized grant identity、输出只回
精确 target，并在重启后二次触发得到 `run budget exhausted`。这只授权观察/报告，不授权写文件、联网、发布、付款、
客户沟通或多 Agent 协作。`0600` 也不是 owner 密码学签名；同一 OS 用户恶意进程属于 B-014 的更强威胁模型。

下一次`/morning`或`/inbox`还应出现`Standing autonomy receipts`/`自治回执`：`done`表示本地TaskBus终态完成，
`interrupted`表示timeout/restart中断，`failed/rejected`需要`/task <id>`，`evidence_missing`表示预算已扣但没有匹配的
task/grant evidence或provider usage缺失。后者是保守的at-most-once crash window，必须人工核对，禁止自动换grant重跑。
terminal receipt的`tokens=N`来自Codex `turn.completed`，同grant累计值达到`token_stop_threshold`后下一次run才停授；
`budget=within_limit/N`或`budget=exceeded/N`则按grant的单次`max_total_tokens`与同一usage比较。超过时usage仍留存、结果不采信；
该token envelope仍不等于美元计费、provider内部quota、provider质量或远端IM业务验收。

Round 238起，实际dispatch还会生成独立`Scheduled autonomy outcome`：source status/outcome/criteria/source/evidence或failure
从authoritative proposal/task/result投影，exact content先写主state DB再发送。平台失败只按同一notification重试，不会重跑
provider或再次消费grant；`aico-state`中的`recent_autonomy_outcome_deliveries`必须最终为`delivered`。`retrying`表示待重发，
`duplicate_possible=true`表示ACK前崩溃可能造成相同内容重复，`exhausted`会使runtime health FAILED。该ACK仍不等于老板已读。
同一回执还必须区分task status与`outcome`。只有`outcome=complete`且`criteria=N/N`才通过本地结果合同；
`missing/invalid/blocked`均停授。`sources=N`表示引用的repository-relative file/line存在，不是业务事实认证；真实
owner sample仍要人工抽查引用内容。preauthorized raw JSON不会进入老板IM，只保留bounded outcome字段。
若compact result消息显示`result_too_large`或`result_schema_invalid`，不要索要raw正文或调大grant重跑；先核对schema/
charter数量和当前Codex版本。standing结果固定32K且字段/数组有上限，这只是本地接收与持久化保护，不是token cap。
complete回执还要检查`evidence=current`。系统不在IM暴露path/hash/source正文，但会从owner-local SQLite重算最多16个
source的full-file fingerprint；`drifted/missing`表示完成后文件变化、删除或旧receipt没有manifest，后续scheduled run
会停授。先由owner检查Git/本地变更与引用语义，再发起新的人工验收；禁止修改旧receipt、伪造hash或自动重跑。

验收方式:

1. 先手动在同一个项目里发 `/project aico`、`/overnight <小目标>`。
2. 确认 `/overnight` lead 完成后会自动排 challenger / reviewer checkpoint review。
3. 发 `/morning`,确认手动早报可读。
4. 未配置 grant 时,开启 `AICO_MORNING_PUSH_ON_START=true` 重启 runtime,确认目标 chat 只收到同口径早报。
5. 关闭 `AICO_MORNING_PUSH_ON_START`,保留 `AICO_MORNING_PUSH_TIME`,观察指定时间是否推送。

Round 232起，正式scheduled morning没有`AICO_STATE_DB_PATH`会拒绝启动。发送前会固定exact content和每日delivery id；
同一天重启或`push_on_start`复用同一投递。用以下命令核对最近回执：

```bash
uv run aico-state --db "$AICO_STATE_DB_PATH"
```

`status=delivered`只表示IM平台返回了发送确认，不表示老板已读；`duplicate_possible=true`表示平台可能在AICO确认前已接受，
重试可能形成带相同`Delivery:`引用的有界重复。`retrying`时runtime health为DEGRADED，五次耗尽为FAILED。输出只含delivery id、
尝试数、content SHA、standing receipt数量和时间，不含target、正文或raw platform message id。正文因exact retry需要保存在owner-only
state DB，备份与off-device副本必须继续加密保护。

Round 233起，同一命令还会显示`recent_scheduled_autonomy`。每个delivery在IM外发前已有稳定intent：`pending/retrying/running`
表示晨报与自治仍未共同收敛，health为DEGRADED；`settled`只表示本次调度已得到not-applicable/held/dispatch-recorded回执，
不是老板已读或结果complete；`exhausted`为FAILED。重启看到accepted proposal/task绑定时会直接结算且不重跑provider，无证据才
有界重试。`duplicate_notification_possible=true`表示hold通知可能带相同`Intent:`重复，不表示允许第二次provider dispatch。
operator输出只显示proposal/task ID的SHA，不显示原ID、project、target或消息正文。

本地排查同一份审计指标时可直接跑:

```bash
env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python /opt/homebrew/bin/python3.11 aico-metrics --audit-log "$AICO_AUDIT_LOG_PATH"
env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python /opt/homebrew/bin/python3.11 aico-metrics --audit-log "$AICO_AUDIT_LOG_PATH" --format json
env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python /opt/homebrew/bin/python3.11 aico-glance --audit-log "$AICO_AUDIT_LOG_PATH"
env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python /opt/homebrew/bin/python3.11 aico-glance --audit-log "$AICO_AUDIT_LOG_PATH" --format json
```

`aico-metrics` 不连接正在运行的 AICO 进程,只读取 audit JSONL,适合重启后排查历史指标和给后续本地 glance 原型消费 JSON。
`aico-glance` 同样只读取 audit JSONL,输出更紧凑的 Status Island 快照:active agents、open/running/waiting/failed、最近任务和可复制的 `/task` / `/approve` / `/reject` / `/interrupt` 命令。它适合先接 xbar/Swift 菜单栏原型,不替代 Telegram 主控台。

`AICO_LOG_PATH` 默认是 `logs/aico.log`;如果设置为空则只输出到控制台。`AICO_LOG_LEVEL` 默认 `INFO`。排查长任务没回包时先看:

```bash
tail -f logs/aico.log
```

复测 Claude session resume 时,连续发送同一 active session 的两条普通消息,日志中应先出现 `provider_session_mode=new`,之后出现 `provider_session_mode=resume`。日志只记录 session mode 和 session id 前缀,不会打印完整 prompt。

启动后在 Telegram Bot 会话中发送 `/status`,应看到 `claude-code` 和 `codex` 两个 Adapter。跑过任务后再次发送 `/status`,还会看到最近任务状态。

常用 Telegram 命令:

```text
/help
/status
/metrics
/inbox
/tasks
/task <short_task_id>
/audit
/projects
/project aico
/brief
/risks
/blockers
/next
/daily
/weekly
/overnight 梳理当前项目下一步,早上给我 done/blocked/risks/next actions
/roles
/roles all
/role implementer
/role propose 需要一个增长分析岗位
/role confirm
/team
/who implementer
/appoint claude as tester
/unappoint tester
/ask reviewer 检查这个方案
/lead implementer
/use project aico
/assignments aico
/assignment aico-implementer
/agents
/agent claude
/skills claude
/tools codex
/remember Phase 7 记忆默认由 agent 主动维护
/recall phase 7
/forget <memory_id>
/sessions
/new claude
/use <session_id>
/bind codex <provider_session_id>
/claude summarize this repo in one sentence
/codex summarize this repo in one sentence
@codex summarize this repo in one sentence
codex: summarize this repo in one sentence
/broadcast summarize this repo in one sentence
/approve
/approve <short_task_id>
/reject
/reject <short_task_id>
/interrupt <short_task_id>
```

写文件、shell 执行和破坏性任务会先进入审批状态。Telegram 返回 `Approval required: <short_task_id>` 后,如果当前只有一个待审批任务,任务发起人或配置的额外审批人可直接发送 `/approve` 继续,或发送 `/reject` 拒绝。若同时有多个待审批任务,使用提示里的短 ID,如 `/approve abcdef12`。未授权用户审批会返回 `approver not authorized`,任务不会派发。

不要把approval当长期授权。到期边界为`now >= expires_at`；`/inbox`、`/morning`、`/task`、startup以及
`/approve`/`/reject`都会先执行lazy sweep。过期文案为`approval lease expired; submit a new task for fresh review`，
此时只能核对旧task并重新下达当前意图，不能编辑SQLite、调大配置后复活旧审批或自动重跑。

授权时间另有rollback fence：SQLite high-water与进程monotonic elapsed允许最多5秒小幅校时；更大的回拨会让pending
approval全部失效，并暂停新risk approval、direct preauthorized task与scheduled standing run，直到wall time追平。
稳定文案以`authorization clock rollback detected`开头。先修复系统时间，再提交新的当前意图；不要改SQLite、延长
lease或重新加载grant来尝试复活旧授权。`aico-state reset/restore`会重建/恢复该安全状态，只能在owner明确的停机运维中用。

看本地运营指标时用 `/metrics`。当前会展示 `glance` 小节,快速说明 24h 内是否 `needs_approval` / `working` / `attention` / `quiet`,以及 open/running/waiting approval/failed 数;随后展示最近 24h / 7d 的任务总数、状态分布、agent/adaptor 接活数、open work、协作触发次数和平均终态耗时。若配置了 `AICO_AUDIT_LOG_PATH`,历史 done / failed / interrupted / rejected / waiting approval 指标会从 audit JSONL 恢复。token/cost 当前依赖底层 CLI 暴露能力,拿不到时会明确显示 unavailable。

Adapter 未来若能稳定提供 usage,应记录 `task_usage_recorded` 审计事件,`detail` 为 JSON:

```json
{"input_tokens":10,"output_tokens":20,"total_tokens":30,"cost_usd":0.03}
```

没有真实 usage 时不要估算或手填 token/cost;`/metrics` 和 `aico-metrics` 会继续显示 unavailable。

老板回来看当前项目时优先用 `/inbox`。它聚合当前 active project 的 pending approvals、running quiet tasks、failed/interrupted tasks、`/overnight` handoff、Goal Brief 和 lead decision follow-up,并给出 `/approve`、`/reject`、`/task`、`/interrupt`、`/morning`、`/audit` 等下一步入口。若项目配置了 standing charter、团队完整且没有运行中/待审批工作,该恢复动作还会生成至多一个**候选提案**;生成候选不会创建任务。

用 `/proposals` 查看当前项目提案历史。老板决定后发送 `/proposal accept <short_id>` 或 `/proposal reject <short_id> [reason]`。只有 accept 会按提案指定 role 创建任务,且继续经过原有风险识别、`/approve`、审计、持久化和 `/interrupt`;查看和 reject 都不会执行工作。默认早报也不执行；只有按 Morning Push 小节显式配置的 owner-bound、hard-read-only grant 可由**定时**早报消费一次，手工 `/morning` 仍不消费。standing charter 是提议范围,不是发布、付款、真实客户数据或其它外部动作授权。

需要看更完整的可视化留痕时,在启动前设置 `AICO_VIEW_ENABLED=true`,然后在 IM 里发送 `/view`。AICO 会把当前 active project 渲染成自包含 HTML 文件并通过支持附件的 Channel(当前 Telegram)发送。打开后先看 First action、Approval needed、Blockers 和 Overnight results;需要核对证据时再向下看 recent tasks / Timeline / Trace / Memory。按钮只会回到 IM 预填 `/approve`、`/reject`、`/task` 等命令,HTML 本身不执行写操作。这不会启动本机 HTTP 服务,也不会要求手机访问 `127.0.0.1`。附件内容严格按目标 project 投影,但仍会进入 Telegram 聊天记录,只发到可信私聊或可信小群。

长任务卡住或 Adapter 长时间 busy 时,可先用 `/inbox` 或 `/tasks` 找到最近任务,再用 `/task <short_task_id>` 查看状态和可用动作。running 任务会提示 `/interrupt <short_task_id>`,待审批任务会提示 `/approve <short_task_id>` / `/reject <short_task_id>`。协作任务还会在 `/task` 详情里展示 parent / child trace,可从 implementer 父任务跳到 reviewer 子任务,也可从子任务回看是谁发起。中断示例:`/interrupt 31e559c3`。中断会调用底层 Adapter 的 interrupt 能力,任务状态变为 `interrupted`,并记录审计事件。

Codex 默认是 read-only reviewer,不承接写文件 / shell / destructive 任务。这类任务请用 `/claude`;如果误发给 `/codex`,系统会在核心层直接拒绝,不会再进入无效审批。

Session 命令用于 IM 侧会话管理 MVP:
- `/sessions` 查看当前 AICO 进程内的 session 引用。
- `/new <agent>` 创建一个 AICO session 引用,例如 `/new claude`。
- `/use <session_id>` 将当前聊天 + 当前发送者的普通消息路由到该 session 的 agent。
- `/bind <session_id|agent> <provider_session_id>` 将已有 provider session 绑定到 AICO session;如果 `<agent>` 能匹配 agent card,会创建并激活一个新 session。
- `/bind <provider_session_id>` 会把 provider session id 绑定到当前 active session。

Agent 能力展示命令:
- `/agents` 查看当前 agent、adapter、实时状态。
- `/agent <agent>` 查看角色、adapter、provider、capabilities、tools/skills 来源和 session 特性。输出末尾会给出简短 `Next` 指导命令,例如任命到 role 或创建 session。
- `/skills <agent>` 会把“列出你当前可用 skills”的只读问题路由给底层 provider 自己回答;AICO 不维护 skills registry。
- `/tools <agent>` 同理,由底层 provider 自己列出当前可调用工具。

当前 session 仍是 AICO 的薄门面,只保存 IM 侧 active session 和 provider session 引用位置;provider 的真实上下文仍由 Claude/Codex 自己保存,AICO 不复制对话历史。

Shared Memory 命令用于 Phase 7 记忆纠错和排障:
- `/remember <fact>` 把事实写入当前 active project scope;没有 active project 时会提示先 `/project <project>`。
- `/recall [query]` 查看当前项目未归档记忆,包含 memory id、scope、confidence、source 和 evidence 摘要。
- `/forget <memory_id>` 归档一条记忆,不物理删除 JSONL 历史;归档后普通项目任务不会再自动注入这条记忆。
- 老板自然消息里的明确偏好也会被自动抽取:带当前项目上下文时写入 project memory,无项目或全局表达时写入 boss global memory;语气不确定时先进入 `candidate`,不会注入后续 prompt。
- 日常主路径仍是 agent 在项目任务、交接、报告和后续抽取流程中主动维护记忆,老板只在需要纠偏、补充或验收时使用这些命令。
- 企业/团队管理验收重点:同一 project/team 能共享合同、法务、交付检查点等共识;其它 project 的敏感事实不会串入;lead agent 可把重要共识 broadcast 成 team memory,并在 `/audit` / `AICO_AUDIT_LOG_PATH` 中留下 `memory_broadcasted` receipt;A2A `memory_refs + delta` 只是省 token 优化,必要时回退完整消息。
- `/recall` 和 Prompt Stack 召回使用可插拔语义 scorer。默认本地实现支持中文长句和常见中英项目术语,例如“法务检查”可召回 `legal review`;后续可替换为 embedding / LLM rerank。

Project Team / Appointment 命令用于项目办公室语义:
- `/projects` 查看配置中的项目列表;当前 active project 会以 `*` 标记。
- `/project [project]` 进入或查看项目办公室;已进入项目后发送 `/project` 会重新展示当前项目的 repo、阶段、默认接活角色和团队任命。
- `/brief [project]` 查看项目简报,包括 repo、阶段、团队、牵头 role、最近任务、最近审计事件,以及 north star / status / journal 文档短片段。顶部会尝试生成 `Boss summary`,下方 `Facts` 保留原始事实并渲染小节标题 / slash command 样式。
- `/risks [project]` 查看真正的项目交付风险,例如失败/中断任务、破坏性任务和 blockers / pitfalls 文档短片段;普通写文件审批和路由噪音不在这里展示。顶部会尝试生成 `Boss summary`,下方 `Facts` 保留原始事实并渲染小节标题 / slash command 样式。
- `/blockers [project]` 查看当前卡住的工作和待决策项,包括等待审批、失败/拒绝/中断任务、未知 persona 这类系统噪音,以及 blockers 文档短片段。顶部会尝试生成 `Boss summary`;如果 summary 不可用,原始 Facts 也会保留基础格式。
- `/next [project]` 查看下一步建议动作,优先提示待审批、失败任务、路由/配置问题;没有卡点时建议把任务交给当前 lead role。顶部会尝试生成 `Boss summary`,下方 `Facts` 保留原始事实并渲染小节标题 / slash command 样式。
- `/daily [project]` 查看日报式项目报告,聚合最近 24 小时本地 AICO 状态里的团队、完成项、未完成项、风险和项目文档短片段。顶部会尝试生成 `Boss summary`,下方 `Facts` 保留原始事实并渲染小节标题 / slash command 样式。
- `/weekly [project]` 查看周报式项目报告,聚合最近 7 天本地 AICO 状态里的团队、完成项、未完成项、风险和项目文档短片段。顶部会尝试生成 `Boss summary`,下方 `Facts` 保留原始事实并渲染小节标题 / slash command 样式。
- `/overnight <goal>` 创建 Phase 8 离线托管工单,把目标派给当前项目 lead/default role。它不是自动越权执行器;写文件、执行命令或破坏性动作仍会进入 `/approve`。早上先用 `/morning` 接手,再用 `/task <id>` 追溯单任务原文。
- `/overnight` 不带目标时,展示当前 active project 最近的托管工单和早报入口;配置 `AICO_STATE_DB_PATH` 后,这些工单可跨重启恢复。
- `/project`、`/team`、`/roles`、`/role <id>` 这类查看命令末尾会给出简短 `Next` 指导命令,帮助顺手进入 brief/team/next/daily/weekly、appoint、ask、lead 等下一步。
- `/roles [project]` 查看紧凑项目岗位板,默认只展示核心/专家岗位;`/roles all` 展示支持岗位和全部 role。
- `/role <id>` 查看单个岗位详情,包括 owner、scope、approval 和 risk ladder;若该 role 已任命,可按 Next 提示用 `/appoint <agent> as <role> <scope>` 覆盖 scope。
- `/role propose <诉求>` 让当前项目 lead role 起草一个新岗位草案;系统会展示 role id、title、summary、默认权限、审批权限和 prompt。
- `/role confirm` 将上一条岗位草案加入当前项目的进程内 roles;不会直接写配置文件,重启后仍以配置文件为准。Telegram 中也可以点击岗位草案下方的 `Confirm` 按钮。
- `/role discard` 丢弃当前聊天里的待确认岗位草案。Telegram 中也可以点击岗位草案下方的 `Discard` 按钮。
- `/team [project]` 查看当前或指定项目的团队任命;输出会显示当前 lead,并在对应成员行标记 `[lead]`。
- `/who <role>` 查看当前项目某岗位由谁负责,以及权限、工作目录和内部 seat。
- `/appoint <agent> as <role> [scope]` 在当前项目里任命员工到岗位;不传 scope 时继承 role 默认 scope。同一项目的同一 role 只保留一个负责人,重复任命会覆盖而不是追加。当前实现是进程内 appointment,重启后仍以配置文件为准。
- `/unappoint <role>` 撤销当前项目某岗位的进程内任命;重启后仍以配置文件为准。
- `/ask <role> <task>` 把单次任务交给当前项目某岗位,不改变默认接活角色。
- `/ask --exact <role> <task>` 用于格式验收、短结论等一次性任务:只执行目标岗位本条请求,
  不进入 lead decision / Goal Brief 自动扩展,也不会把模型输出中的 `@role` 解析成协作子任务。
  prompt 已明确“只输出本条”“不要请求协作”“do not delegate”等同义约束时,也会自动启用该模式。
- `/ask lead ...` 中的 `lead` 是当前 lead role 的别名;如果实际岗位是 reviewer 等角色,IM 会先显示
  `Routing: lead -> reviewer (<agent>)`,避免静默换岗。
- `/lead <role>` 设置当前项目默认牵头角色;之后普通消息会交给这个 role。

走 Project Team / Appointment 的任务会自动渲染 prompt stack,包含 Agent、RoleTemplate、Project、Appointment Contract 和 Current task。显式 `/claude`、`/codex`、`@reviewer` 这类非项目任命路由仍走原 persona prompt。

兼容 / 排障命令:
- `/use project <project>` 仍可将当前聊天 + 当前发送者的普通消息路由到该项目默认 role。
- `/assignments [project]` 查看旧 assignment/seat 列表。
- `/assignment <seat>` 查看某个内部工位的 agent、provider、role、workspace、session policy 和 risk policy。
- `/default <role>` 是 `/lead <role>` 的兼容别名。

使用 `/project aico` 后,普通消息会走 `aico` 项目的默认 role,默认是 `implementer -> claude`。这个 appointment 会复用自己的 project-scoped provider session;第一次普通消息是 `new`,后续普通消息是 `resume`。显式 `/claude`、`/codex`、`@reviewer` 等路由仍优先于 active project。

Claude provider session 已接入最小恢复链路:默认配置下 `/new claude` 会用 AICO session UUID 作为 Claude session id;第一次普通消息使用 `claude ... --session-id <uuid> <prompt>`,之后同一 active session 的普通消息使用 `claude ... --resume <uuid> <prompt>`。如果自定义 `AICO_CLAUDE_COMMAND` 已经包含 `--session-id`、`--resume`、`--continue` 等 session 参数,AICO 不会再追加自己的 session 参数,避免重复。

Codex 已评估并实现 Adapter 侧 resume 命令构造:已有 Codex provider ref 时会走 `codex exec resume <session_id> <prompt>`。Codex `exec` 首轮仍没有稳定的“指定新 session id”入口,所以当前用显式绑定承接已有 Codex 会话:

```text
/bind codex <provider_session_id>
继续刚才那个 review 上下文
```

绑定后,当前聊天 + 发送者的普通消息会自动路由到该 Codex session,并使用 `resume` 模式。

AI 间协作使用显式行首指令:`@persona request` 或 `@persona: request`。例如 implementer 输出:

```text
@reviewer inspect this implementation for missing tests
```

推荐真实 smoke test 任务:

```text
/claude 请先用三条 bullet 简要说明当前 AICO Phase 5 项目办公室和协作链路的现状，然后在最后单独输出一行：
@reviewer review the current Phase 5 collaboration smoke test for risks, missing tests, and whether audit evidence is enough
```

系统会把它转成 reviewer 的普通任务,并在 Telegram 中提示 `Collaboration requested: implementer -> reviewer`。当前只支持单层协作,避免无限递归。
同时 `/audit` 和 JSONL 审计文件会出现 `collaboration_requested` 事件,其中 `task` 是 reviewer 子任务,`actor` 是源 persona,`detail` 中记录 parent task。
也可以用 `/tasks` 找到 parent / child task,再分别执行 `/task <parent_short_id>` 和 `/task <child_short_id>` 查看协作上下游。

长文本输出会自动按安全长度拆成多条 Telegram 消息。第一条仍用于流式编辑,超过单条消息上限后会继续发送下一条,避免 Telegram 4096 字符限制导致后续内容丢失。

默认 Persona:

| Persona | Adapter | Alias |
|---|---|---|
| `implementer` | `claude-code` | `/claude`, `/claude-code` |
| `reviewer` | `codex` | `/codex` |

---

## 本地验证

```bash
env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python /opt/homebrew/bin/python3.11 pytest
env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python /opt/homebrew/bin/python3.11 ruff check .
env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python /opt/homebrew/bin/python3.11 ruff format --check .
env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python /opt/homebrew/bin/python3.11 mypy src tests
```

Project Team 主流程可以先跑本地验收流,再做 Telegram 真实验收:

```bash
env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python /opt/homebrew/bin/python3.11 pytest tests/unit/test_orchestrator.py -k project_team_acceptance_flow
```

---

## 日志查看

```bash
tail -f logs/aico.log
rg "task_id=<task_id>" logs/aico.log
rg "Adapter busy|Adapter process exited|Stream message split|Telegram editMessageText" logs/aico.log
```

长文本任务如果 Telegram 没回结果,重点看:
- 是否有 `Adapter process starting`:没有说明没有派发到 Claude/Codex。
- 是否有 `Adapter busy`:说明该 Adapter 已有任务在跑,当前请求被拒绝。
- 是否有 `Adapter process exited`:没有说明 CLI 还没结束或卡住。
- 是否有 `Stream output`:没有说明还没有 stdout chunk 进入编排层。
- 是否有 `Stream message split`:说明长文本分片已触发。
- 是否有 `Telegram sendMessage` / `Telegram editMessageText` 后的异常:说明 IM 出口失败。

---

## 任务管理

```text
/status
/audit
```

当前 `/status` 会展示 Adapter 状态和最近任务状态。任务状态包括:`running`、`waiting_approval`、`done`、`failed`、`interrupted`、`rejected`。危险任务会在状态行展示风险等级,如 `write_files` / `shell_exec` / `destructive`。

当前 `/audit` 会以多行块展示最近 10 条内存审计事件,包括事件类型、task id、actor、target、adapter、risk 和事件详情。重启进程后内存审计记录会清空;如已配置 `AICO_AUDIT_LOG_PATH`,完整历史可从 JSONL 文件追溯。
未授权审批会记录为 `approval_denied`。
AI 间协作会记录为 `collaboration_requested`,用于追踪 `implementer -> reviewer` 等子任务关系。

Round 223起，durable JSONL每行保留event顶层字段并增加`_audit`链；同目录
`<audit>.checkpoint.json`锚定event count、byte size和chain head。日常检查用：

```bash
uv run aico-audit --audit-log "$AICO_AUDIT_LOG_PATH" verify
```

若是升级前已有的普通JSONL，先停runtime并由owner核对历史baseline，再**一次性**执行`seal`。seal不重写event行，
只收紧文件权限并锚定当时字节；它不证明seal前历史真实，也不是损坏修复命令。新ledger会自动初始化，不要对不存在的
路径运行seal。

查看 JSONL 审计文件:

```bash
tail -n 20 /tmp/aico-audit.jsonl
```

```bash
# 中断某个任务
# 重试失败任务
```

---

## Lead 内务命令(老板平时不碰)

`/timeline` 和 `/rollback` 是 lead 的精细工具。老板继续用 `/undo`(撤最近一步)
和 `/why <short_id>`(看一条 trace)。

```text
# 过滤时间线(过去 24h,默认)
/timeline

# 过滤源、限制条数、按 trace 前缀
/timeline --since 6h --source memory --limit 20
/timeline --trace task-abc

# 精细回滚(只撤 AICO 内部状态,**不撤** git / shell / file)
/rollback memory <id>         # fact memory -> archived
/rollback experience <id>     # active experience -> candidate; archived 不变
/rollback task <id>           # 写一条 ROLLBACK_PERFORMED audit 标记;不级联撤 memory
```

边界说明:每次 `/rollback` 都会写一条 `rollback_performed` audit。`/rollback task`
本 sprint 只写 audit 标记,**不级联撤** memory/experience 副作用——如果要清理,需要
显式 `/rollback memory <id>` 或 `/rollback experience <id>`。永远不撤已写文件、已跑
shell、已发 IM 消息。详见 ADR-0034。

---

## Adapter 管理

```bash
# 列出所有已注册 Adapter
# 启用 / 禁用某个 Adapter
# 查看某 Adapter 状态
```

---

## Channel 管理

```bash
# 列出所有 IM 通道状态
# 重连 Telegram Webhook
```

---

## 配置变更

```bash
# 查看当前生效配置
# reload 配置(无需重启)
```

---

## 数据备份与恢复

`AICO_STATE_DB_PATH` 是 task、approval、overnight、recovery/alert outbox 等 AICO 业务状态的
SQLite 真相源。备份使用 SQLite online backup API,所以 runtime 正在运行时也可以生成一致的单文件
artifact；不要直接 `cp` live `state.db` 或只复制 `-wal`。

```bash
# 在线备份；output 必须是不存在的新文件
uv run aico-state --db .aico/state.db backup \
  --output /path/outside-repo/aico-state-20260721.db

# 离线、只读校验；记录输出中的 sha256
uv run aico-state --db .aico/state.db verify \
  --backup /path/outside-repo/aico-state-20260721.db

# 不触碰 live DB，实际走一次 disposable restore；report必须是新文件
mkdir -p /path/private-drill-workspace
chmod 700 /path/private-drill-workspace
uv run aico-state --db .aico/state.db drill \
  --backup /path/outside-repo/aico-state-20260721.db \
  --expected-sha256 <verify 输出的 64 位 sha256> \
  --workspace /path/private-drill-workspace \
  --report /path/outside-repo/aico-state-20260721-drill.json

# 恢复前先停止 runtime，并确认 doctor 不再报告 active owner
uv run aico-service --repo . status
uv run aico-state --db .aico/state.db restore \
  --from /path/outside-repo/aico-state-20260721.db \
  --expected-sha256 <verify 输出的 64 位 sha256> \
  --yes
```

`drill`会在private temp目录调用同一个production restore primitive，重新打开materialized DB并比较
schema/table counts，随后无论成功失败都清理临时DB、owner lock和sidecar。它不会打开或创建`--db`，所以live
runtime可以继续运行。报告是`0600`、原子new-path JSON；不要复用固定文件名覆盖历史证据。

restore 会先再次校验选定 artifact 和 SHA，拒绝 active runtime，再为当前 DB 创建
`state.db.pre-restore-<UTC>.db` 安全副本，最后原子替换主 DB。若 safety backup 无法完成，目标不会被替换。
`reset --yes` 同样拒绝 active runtime。不要删除 pre-restore 文件，直到恢复后的 `/tasks`、`/inbox`、
`/audit` 和代表性 IM 路径都已验收。

当前命令**只覆盖 AICO 主 SQLite 业务状态**，不覆盖 audit/memory JSONL、Persona/Project Git 配置、`.env`、
日志或 dead-man receiver DB。local drill报告仍不算灾难恢复；商用运行还需要加密的off-device存储、保留策略，
并从off-device artifact在隔离checkout完成`/tasks`、`/inbox`、outbox和代表性IM业务恢复，见B-013。

audit恢复资产至少同时包含`audit.jsonl`与`audit.jsonl.checkpoint.json`；不要备份/恢复运行时`.lock`，也不能只恢复
JSONL后重新seal来掩盖缺失checkpoint。恢复后在启动runtime前运行`aico-audit verify`。本地链只能发现不一致，不替代
off-device retention、数字签名或WORM存储。

不要直接分别复制live ledger/checkpoint。创建一个writer-locked point-in-time artifact，并把输出SHA记录到不同故障域：

```bash
uv run aico-audit --audit-log "$AICO_AUDIT_LOG_PATH" backup \
  --output /path/outside-repo/aico-audit-20260722.zip

# 可在没有live ledger的隔离机器运行；off-device复制后建议强制比对之前记录的SHA
chmod 600 /path/outside-repo/aico-audit-20260722.zip
uv run aico-audit verify-backup \
  --backup /path/outside-repo/aico-audit-20260722.zip \
  --expected-sha256 <backup输出sha256>

# 不触碰live audit，实际走production materializer并留下new-path报告
mkdir -p /path/private-audit-drill
chmod 700 /path/private-audit-drill
uv run aico-audit drill-backup \
  --backup /path/outside-repo/aico-audit-20260722.zip \
  --expected-sha256 <backup输出sha256> \
  --workspace /path/private-audit-drill \
  --report /path/outside-repo/aico-audit-20260722-drill.json

# 破坏性恢复：先停止runtime；preservation必须是不存在的新路径
uv run aico-service --repo . status
uv run aico-audit --audit-log "$AICO_AUDIT_LOG_PATH" restore \
  --backup /path/outside-repo/aico-audit-20260722.zip \
  --expected-sha256 <backup输出sha256> \
  --state-db "$AICO_STATE_DB_PATH" \
  --preservation-output /path/outside-repo/aico-audit-pre-restore-20260722.zip \
  --yes
uv run aico-audit --audit-log "$AICO_AUDIT_LOG_PATH" verify
```

artifact是固定三member的未压缩ZIP，内含完整审计正文，不是加密容器。命令在全量复制期间持有audit writer lock；
大ledger会短时阻塞新audit写入，未有rotation/增量策略前应放在维护窗口，不要直接配置高频无人scheduler。
`drill-backup`在private temp中走同一production materializer并清理，不取得live owner lock；runtime运行期间也可演练。
restore会校验state DB确实是受支持的AICO数据库并取得其owner lock；active runtime、缺`--yes`、错误SHA或已有
preservation输出都在覆盖前拒绝。当前live有效时preservation是标准verified safety backup；损坏/unsealed时则是
保留原始字节和hash的`unverified_quarantine`，只能取证，不能送入普通restore。

ledger与checkpoint无法用一次可移植rename同时替换。若第二次replace前异常，严格verify会fail closed；保留已生成的
preservation，核对原artifact SHA后用**新的preservation路径**重跑同一备份可收敛。绝不能删除checkpoint或用`seal`
掩盖半恢复现场。restore仍是owner显式事故动作，不能进入scheduler；本机component restore也不等于off-device全资产
业务恢复通过。

Memory JSONL从Round 227起也是owner-only hash-chain ledger。升级前legacy文件必须先停止runtime、核对内容并显式执行
`uv run aico-memory --memory-log "$AICO_MEMORY_PATH" seal`；日常可用`verify`检查。独立恢复点与演练/恢复命令分别是
`backup --output`、`verify-backup --backup [--expected-sha256]`、`drill-backup --backup --expected-sha256`和要求
`--state-db --preservation-output --yes`的`restore`。其writer lock、outer SHA、safety/quarantine及禁止自动restore边界与
audit一致，但artifact包含完整memory正文，必须外层加密。

Dead-man receiver是第二故障域，必须使用独立恢复节奏，不能塞入或跟随AICO core set一起回滚。receiver在线时可生成
consistent standalone backup；off-device副本在无credential环境做deep verify和disposable drill：

```bash
aico-dead-man-recovery backup \
  --db /data/dead-man.db \
  --output /data/dead-man-20260722.db
aico-dead-man-recovery verify \
  --backup /secure/off-device/dead-man-20260722.db
aico-dead-man-recovery drill \
  --backup /secure/off-device/dead-man-20260722.db \
  --expected-sha256 <独立保存的backup sha256> \
  --workspace /secure/private-receiver-drill \
  --report /secure/evidence/dead-man-drill-20260722.json
```

backup允许active receiver；restore必须先停止receiver并取得同一个kernel owner lock，再提供独立SHA与`--yes`。有效live
先生成verified pre-restore backup，无法验证的DB/WAL/SHM原字节进入owner-only quarantine。恢复后重启receiver，核对
`/readyz`、monitor状态、pending delivery和admin evidence export。不得删lock文件绕过worker fence，不得由scheduler、
“latest artifact”或AICO主机恢复自动触发。Compose精确命令见
[`deploy/dead-man-receiver/README.md`](../../deploy/dead-man-receiver/README.md#independent-receiver-backup-and-recovery)。

为避免从不同时间各取一个state/audit/memory artifact后口头拼成“一次备份”，可以生成一个有界窗口core recovery set：

```bash
# capture允许runtime继续运行；输出必须是不存在的新路径
uv run aico-recovery capture \
  --state-db "$AICO_STATE_DB_PATH" \
  --audit-log "$AICO_AUDIT_LOG_PATH" \
  --memory-log "$AICO_MEMORY_PATH" \
  --checkout "$PWD" \
  --project-config "$AICO_PROJECT_CONFIG_PATH" \
  --persona-config "$AICO_PERSONA_CONFIG_PATH" \
  --expected-config-revision "$AICO_REVIEWED_CONFIG_REVISION" \
  --output /path/outside-repo/aico-core-recovery-20260722.zip

# 把capture输出的outer SHA保存在独立authority；off-device复制后强制核对
uv run aico-recovery verify \
  --recovery-set /path/outside-repo/aico-core-recovery-20260722.zip \
  --expected-sha256 <capture输出sha256>

# 在隔离checkout中取回manifest记录的精确commit后，证明代码、tree与active config完全一致
uv run aico-recovery verify-checkout \
  --recovery-set /path/outside-repo/aico-core-recovery-20260722.zip \
  --expected-sha256 <capture输出sha256> \
  --checkout /path/to/clean-restored-checkout

# component restore后，由owner重新注入.env/轮换secret并重新签发standing grant；runtime继续保持停止
uv run aico-recovery reinjection-receipt \
  --recovery-set /path/outside-repo/aico-core-recovery-20260722.zip \
  --expected-sha256 <capture输出sha256> \
  --checkout /path/to/clean-restored-checkout \
  --owner-decision-ref incident-2026-07-22-001 \
  --output /path/outside-repo/aico-reinjection-20260722.json

# 把上一步receipt_sha256保存到独立authority，并在启动runtime前重验当前material
uv run aico-recovery verify-reinjection \
  --recovery-set /path/outside-repo/aico-core-recovery-20260722.zip \
  --expected-sha256 <capture输出sha256> \
  --checkout /path/to/clean-restored-checkout \
  --receipt /path/outside-repo/aico-reinjection-20260722.json \
  --expected-receipt-sha256 <reinjection-receipt输出receipt_sha256>

# 真实联系manifest要求的每个provider；把新receipt SHA保存到独立authority
uv run aico-recovery provider-auth-receipt \
  --recovery-set /path/outside-repo/aico-core-recovery-20260722.zip \
  --expected-sha256 <capture输出sha256> \
  --checkout /path/to/clean-restored-checkout \
  --reinjection-receipt /path/outside-repo/aico-reinjection-20260722.json \
  --expected-reinjection-receipt-sha256 <reinjection-receipt输出receipt_sha256> \
  --output /path/outside-repo/aico-provider-auth-20260722.json

# 30分钟内复核binding/freshness；此命令不会再次调用或收费
uv run aico-recovery verify-provider-auth \
  --recovery-set /path/outside-repo/aico-core-recovery-20260722.zip \
  --expected-sha256 <capture输出sha256> \
  --checkout /path/to/clean-restored-checkout \
  --reinjection-receipt /path/outside-repo/aico-reinjection-20260722.json \
  --expected-reinjection-receipt-sha256 <reinjection-receipt输出receipt_sha256> \
  --receipt /path/outside-repo/aico-provider-auth-20260722.json \
  --expected-receipt-sha256 <provider-auth-receipt输出receipt_sha256>

mkdir -p /path/private-core-drill
chmod 700 /path/private-core-drill
uv run aico-recovery drill \
  --recovery-set /path/outside-repo/aico-core-recovery-20260722.zip \
  --expected-sha256 <capture输出sha256> \
  --workspace /path/private-core-drill \
  --report /path/outside-repo/aico-core-recovery-20260722-drill.json
```

set固定包含`recovery-set.json`、standalone state DB、portable audit ZIP和portable memory ZIP；配置、`.env`、secret和grant
正文均不进入artifact。
capture必须由flag或`AICO_REVIEWED_CONFIG_REVISION`提供owner/CI在另一信任面选定的完整commit，并要求Git root全工作树clean、
active project/persona config位于checkout内且与commit blob一致。输出必须在checkout外。manifest绑定commit/tree/object
format、relative path、blob OID、size/hash；未配置persona文件时来源固定为`built_in_at_revision`。checkout根目录`.env`必须
owner-only、non-symlink、Git未跟踪、无duplicate key，并通过与`aico-service install`相同的control-plane/standing-grant preflight。

数据capture按configuration→runtime reinjection requirements→state→audit→memory顺序执行并记录整体start/end及component
completion，所以只能声称三个数据point落在同一bounded window；
runtime期间发生的写入可能造成skew，manifest永久声明`global_transaction=false`。`verify`会深入运行三套component
verifier；`drill`再实际走state restore、audit与memory materializer，而不是只解析outer ZIP。

manifest将project/persona config标为`included=false`但`recovery_contract_ready=true`，因为它们必须从已验证revision恢复；
control-plane secret与standing grant同样`included=false`，但可通过灾后slot/mode合同和owner-only receipt验证；receipt允许
credential轮换，却不保存值、hash、identity或grant正文。receiver state保持`included=false`，但以
`external_component_recovery`标记独立合同就绪；这不表示receiver artifact已capture或与core set同一时间点。
schema v6将AI provider标为`post_restore_live_probe`并记录required provider集合；Claude/Codex probe要求exact随机challenge、
terminal success与usage。回执只保存challenge/probe executable hash，30分钟后或executable/provider/reinjection漂移时必须重跑。
Cursor/CodeFlicker/Trae/Gemini在没有批准的安全结构化probe前fail closed。`unresolved_assets=()`只表示恢复方法齐备；
`post_restore_evidence_assets`仍必须逐项交付，且`business_restore_ready=false`保持。
runtime lock/heartbeat被明确排除。artifact包含完整业务state、audit与memory正文，仍需
off-device加密。当前没有combined restore：事故恢复时持续保持runtime停止，分别按state/audit/memory owner-fenced合同执行，
receiver只在自身故障时独立恢复；再补齐外部认证与业务RPO/RTO验收。

若owner已选择并挂载真实备份目标，可让Phase1按日自动执行同一capture + immediate verify合同：

```bash
mkdir -p /absolute/private/recovery-destination
chmod 700 /absolute/private/recovery-destination
export AICO_RECOVERY_BACKUP_ENABLED=true
export AICO_RECOVERY_BACKUP_CHECKOUT_PATH="$PWD"
export AICO_RECOVERY_BACKUP_OUTPUT_DIR=/absolute/private/recovery-destination
export AICO_RECOVERY_BACKUP_INTERVAL_SECONDS=86400
export AICO_RECOVERY_BACKUP_MAX_AGE_SECONDS=172800
export AICO_RECOVERY_CUSTODY_CHECK_INTERVAL_SECONDS=3600
export AICO_RECOVERY_CUSTODY_MAX_AGE_SECONDS=7200
# Destructive opt-in: review age/generation/capacity policy before enabling.
export AICO_RECOVERY_RETENTION_ENABLED=false
export AICO_RECOVERY_RETENTION_AFTER_SECONDS=2592000
export AICO_RECOVERY_RETENTION_MIN_GENERATIONS=7
export AICO_RECOVERY_RETENTION_CHECK_INTERVAL_SECONDS=21600
export AICO_RECOVERY_RETENTION_MAX_PRUNES_PER_RUN=2
# Non-destructive opt-in: actually exercise disposable production materializers every week.
export AICO_RECOVERY_DRILL_ENABLED=false
export AICO_RECOVERY_DRILL_INTERVAL_SECONDS=604800
export AICO_RECOVERY_DRILL_MAX_AGE_SECONDS=1209600
# export AICO_RECOVERY_DRILL_WORKSPACE=/absolute/private/recovery-drill-workspace

uv run aico-service --repo . doctor
uv run aico-state --db "$AICO_STATE_DB_PATH"
```

scheduler默认关闭。每个窗口先写stable SQLite intent，再生成唯一artifact、立即deep verify并写owner-only receipt；失败按
1/5/15/15分钟最多五次。`recent_recovery_backups`中的`verified`和两份SHA是本机capture证据；无verified receipt为
DEGRADED，超过max age或`exhausted`会使heartbeat required health FAILED。Round 235起receipt还绑定不展示raw值的destination
fingerprint，独立custody cadence会重新打开最新artifact/sidecar，复核权限、两份SHA和完整recovery-set；CLI显示
`custody=verified|failed`、checked time和failure count。artifact缺失/漂移、目录identity变化、权限放宽或custody age超限都使
required health FAILED，而大文件deep verify不会阻塞heartbeat。Round 236增加独立且默认关闭的retention授权：只有同一binding下
超过age、位于最新保留代际之外且custody VERIFIED的scheduled pair才可按最老优先、单轮有界清理。scheduler先持久化`PRUNING`
与policy SHA，再deep verify并按artifact/sidecar顺序删除；`PRUNED`仍在SQLite保留receipt/artifact/policy SHA tombstone。
任何删前漂移或不可解释的artifact-only状态都保留现场并使health FAILED。关闭开关只阻止新intent，不能取消已落盘的`PRUNING`。
Round 237再增加独立、默认关闭的scheduled disposable drill：到期时选择latest VERIFIED + custody VERIFIED artifact，先写稳定
intent，再在worker thread和private临时目录实际运行state/audit/memory production materializer。失败按1/5/15/15分钟最多五次；
due/open为DEGRADED，EXHAUSTED或success receipt超过max age为FAILED。open/latest exhausted drill的目标不会被retention删除；
关闭drill但继续retention时仍加载durable drill历史。可选workspace必须预先存在、absolute、owner-only且不与checkout/output重叠。
state capture发生在本次成功receipt写回之前，
所以artifact不会包含自己的最终VERIFIED行；这不构成global transaction。

目标目录必须提前存在、absolute、非symlink、owner-only并位于checkout外。AICO故意不创建缺失目录，避免off-device mount
掉线后静默回落到本机同名路径。doctor的`storage class not attested`表示它没有证明加密、第二故障域、retention或访问审计；
这些仍由owner和存储系统提供。retention开关只授权上述旧scheduled pair，不扫描未知文件、不删除custody失败记录、也不会restore；
scheduled drill同样不会restore live state，其receipt只证明captured components能本地materialize。事故恢复继续使用上面的显式
owner-fenced流程，并补齐checkout/reinjection/provider/receiver与代表性IM证据。
合法storage迁移若改变identity，也会保守失败；使用新的明确output path重新跑doctor与外部存储验收，不要改SQLite或复制
旧sidecar伪造连续性。kernel fingerprint不是volume UUID/provider签名，仍不能证明第二故障域或云端durability。

---

## 健康检查

```bash
# 自检命令
# 验证所有 Adapter 可达
# 验证所有 Channel 可达
```

---

## 开源主 Demo:Release Room

主 demo 位于 `examples/release-room`,用于展示在 IM 中远程管理 AI team 完成小型
开源 CLI 的 v0.2 release。

```bash
export AICO_PROJECT_CONFIG_PATH="examples/release-room/aico-project.json"
export AICO_MEMORY_PATH="/tmp/aico-release-room-memory.jsonl"
export AICO_AUDIT_LOG_PATH="/tmp/aico-release-room-audit.jsonl"
```

按 [`docs/playbooks/release-room-demo.md`](../playbooks/release-room-demo.md) 执行。核心验收路径:

```text
/use project release-room
/team
/remember v0.2 不接受没有测试的功能。
/ask pm 阅读 STATUS.md 和 issues/003-v02-release.md，把 v0.2 拆成角色任务、验收标准和风险清单。
/ask implementer 实现 v0.2 的 tags/search/export JSON，修复 unknown id done 的退出码问题，并补测试。
/ask tester 根据 tests/test_v02_contract.py 设计回归验证，运行必要测试并报告失败项。
/ask reviewer review v0.2 release 风险，重点检查行为回归、测试缺口和 README/CHANGELOG 一致性。
/overnight 推进 v0.2 release room，早上给我 done/blocked/risks/next actions。
/morning
/audit
```

## 持续项目场景:SME Agent

`projects/sme-agent` 是由 AICO Team / AI Lead 持续管理的独立业务项目,不是 AICO core 模块。

```bash
export AICO_ENABLE_CODEX_ADAPTER=true
export AICO_CLAUDE_WORKING_DIRECTORY="/Users/wangzq/VsCodeProjects/ai-company-os"
export AICO_PROJECT_CONFIG_PATH="projects/sme-agent/aico-project.json"
export AICO_MEMORY_PATH=".aico/sme-agent-memory.jsonl"
export AICO_AUDIT_LOG_PATH=".aico/sme-agent-audit.jsonl"
export AICO_STATE_DB_PATH=".aico/sme-agent-state.db"
```

进入项目后先执行 `/use project sme-agent`、`/team`、`/brief`;跨天恢复从 `/morning`、
`/inbox`、`projects/sme-agent/STATUS.md` 和 `projects/sme-agent/docs/handoffs/current.md` 开始。
完整流程见 [`projects/sme-agent/docs/operating-model/aico-runbook.md`](../../projects/sme-agent/docs/operating-model/aico-runbook.md)。

---

## Dogfooding 推荐流程(Phase 1 完成后)

每天早晚两次 5 分钟:

**早上**(检查夜间任务):
1. 打开 Telegram"晨会群"
2. 看夜间各 AI 跑的任务汇总
3. 决定今天派什么新任务

**晚上**(下达夜间任务):
1. 整理白天没做完的事
2. 在 Telegram 群里发任务"今晚把 issue #X-#Y 看一遍"
3. 关电脑(Adapter 仍在跑)

---

## 月度运维

- [ ] 检查 token 消耗,看哪个 Adapter 性价比低
- [ ] 检查 PITFALLS 是否有可以转化为 ADR 的模式
- [ ] 检查 BLOCKERS 是否有长期未解决项,提升优先级
- [ ] 清理 Round 50+ 之前的归档(如有需要)
