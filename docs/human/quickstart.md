# Quickstart - 5 分钟跑起来

> 给人类看的快速上手文档。当前最小公开路径是 Telegram -> AICO 编排核心 -> Claude Code / Codex。

---

## 当前阶段说明

项目当前处于 Phase 8:离线托管 + 开源主 Demo。Telegram 主控、Claude Code / Codex
Adapter、项目办公室、审批审计、共享记忆、任务观测和 Release Room Demo 都已经落地。
Cursor / CodeFlicker / Trae / Gemini Adapter 已完成真实 smoke test,可作为已登录本机
CLI 后的可选成员启用。Feishu Channel 已有实现切片,但仍需要真实生产 smoke test 后再作为
稳定公开路径推荐。

---

## 5 分钟快速上手

公开用户只需要在自己的电脑运行一个AICO Runtime。独立Dead-Man Receiver不是入门依赖；它只用于检测
整台电脑离线、LaunchAgent持续启动失败等高级故障，且必须运行在另一台主机或云服务上才有意义。

### 不配置 token 先看效果

第一次看项目时,可以先跑本地 deterministic Release Room demo。它使用 fake adapters,
不需要 Telegram Bot Token,也不会调用 Claude / Codex / 任何付费 provider:

```bash
git clone https://github.com/MarcelLeon/ai-company-os.git
cd ai-company-os

env UV_CACHE_DIR=/tmp/aico-uv-cache uv sync --python 3.11
env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python 3.11 aico demo
```

如果这条链路能看懂,再配置真实 Telegram runtime。

### 前置依赖

- macOS / Linux
- Python 3.11+
- `uv`
- Telegram Bot Token([如何创建](https://core.telegram.org/bots/tutorial))
- Claude Code 已安装并能在命令行使用
- Codex CLI 已安装并能在命令行使用(启用 Codex Adapter 时需要)

```bash
# 1. clone并安装依赖
git clone https://github.com/MarcelLeon/ai-company-os.git
cd ai-company-os
env UV_CACHE_DIR=/tmp/aico-uv-cache uv sync --python 3.11

# 2. 交互式生成owner-only .env；token使用隐藏输入
uv run aico init

# 3. 先检查配置
uv run aico doctor

# 4. 前台启动Telegram runtime
uv run aico run

# 5. 在Telegram找到自己的Bot并发送
# /help
```

`aico init`会给出一条带随机码的`/help AICO-setup-...`命令；在自己的Bot私聊发送后按回车，
它只接受exact private update并自动绑定sender/chat ID。若另一个poller正在消费同一Bot或Telegram账号不能发消息，
配对会fail closed；已知ID时可使用`--owner-id`与`--chat-id`一起显式提供。
它只写最小Telegram配置，创建的`.env`固定为`0600`；高级选项仍以`.env.example`为准，且不会部署
Dead-Man、创建云资源或自动安装后台服务。

### 常用命令

```text
/help
/status
/project aico
/team
/roles
/ask pm summarize the next release plan in 3 bullets
/remember This project prefers small, reviewable changes.
/recall project preferences
/tasks
/metrics
/audit
/overnight 梳理当前项目下一步,早上给我 done/blocked/risks/next actions
```

预期效果:

- Bot 把请求派发给对应 persona / Adapter,执行结果回到 Telegram。
- 只有configured owner sender在configured trusted target中的消息才进入编排；其它消息无回复、无task、无provider调用。
- `/status` 展示 Adapter 状态和最近任务状态。
- `/project` / `/team` 展示当前项目办公室和团队任命。
- 写文件、shell 或 destructive 任务会先进入 `/approve` / `/reject` 审批流。
- 新审批默认只在24小时内有效；可用`AICO_APPROVAL_MAX_AGE_SECONDS`配置300..604800秒。deadline在创建时冻结，
  到期后task会变为rejected且必须重新提交，不会因重启或放大配置继续有效。
- 指定 `AICO_MEMORY_PATH` 后,`/remember` / `/recall` / `/forget` 使用本地 JSONL
  共享记忆;如果启动时没带这个环境变量,运行中的 Bot 需要重启后才会启用记忆。
- 指定 `AICO_STATE_DB_PATH` 后,task records、task snapshots、pending approval
  和 `/overnight` 托管工单会写入 SQLite;重启后 `/tasks`、`/task <id>`、`/approve`
  和 `/overnight` 能恢复 AICO 业务状态；已经到期的approval会在startup事务性回收，不会恢复为可执行。
- 同一SQLite还保存authorization clock high-water。系统时间明显回拨时，pending approval会失效，新的risk task和
  standing autonomy会暂停到wall time追平；不要通过reset/改库复活旧授权。
- 指定`AICO_AUDIT_LOG_PATH`后，runtime会维护JSONL SHA-256链和同目录checkpoint；修改、重排、截断或半写都会使
  replay/startup fail closed。升级已有普通JSONL时，先人工核对baseline，再执行：

  ```bash
  uv run aico-audit --audit-log "$AICO_AUDIT_LOG_PATH" seal
  uv run aico-audit --audit-log "$AICO_AUDIT_LOG_PATH" verify
  ```

  新路径由runtime首次启动自动初始化，无需seal。不要删除或单独恢复`.checkpoint.json`sidecar。

  需要移交/备份审计时，不要分别`cp`两个live文件；创建并离线复核一个恢复点：

  ```bash
  uv run aico-audit --audit-log "$AICO_AUDIT_LOG_PATH" backup \
    --output /path/outside-repo/aico-audit-20260722.zip
  uv run aico-audit verify-backup \
    --backup /path/outside-repo/aico-audit-20260722.zip \
    --expected-sha256 <backup输出sha256>
  ```

  artifact含完整审计正文且未加密；复制到off-device前使用owner批准的加密存储，并把SHA记录在独立位置。
  用`aico-audit drill-backup --expected-sha256 ...`可在disposable目录走一次真实materialization。live restore必须先
  停runtime，再显式提供同一`AICO_STATE_DB_PATH`、new-path preservation artifact和`--yes`；完整命令及损坏现场
  quarantine语义见 [`daily-ops.md`](daily-ops.md#数据备份与恢复)。restore永远不应由scheduler自动触发。
- 同一 canonical state DB 同时只允许一个 active runtime。owner lock 由 state path 自动派生;
  重复 terminal/LaunchAgent 会在 task recovery 和 Channel start 前失败,不会误中断 live task。
- 开发期如果只想快速启用本地状态库,也可以设置 `AICO_STATE_DB_PATH=true`;
  AICO 会映射到 `.aico/state.db`,避免在仓库根目录生成名为 `true` 的数据库文件。
  用 `aico-state --db .aico/state.db` 可以查看 schema version 和各状态表行数。
- 生产性使用前至少执行一次在线备份和只读校验：

  ```bash
  uv run aico-state --db .aico/state.db backup --output /path/outside-repo/aico-state.db
  uv run aico-state --db .aico/state.db verify --backup /path/outside-repo/aico-state.db
  uv run aico-state --db .aico/state.db drill \
    --backup /path/outside-repo/aico-state.db \
    --expected-sha256 <verify输出sha256> \
    --report /path/outside-repo/aico-state-drill.json
  ```

  restore/reset 是 owner-fenced 破坏性操作，必须先停止 runtime并显式传 `--yes`。完整恢复命令、
  drill不会打开live `--db`，只在private temp中演练production restore并清理；它仍不等于off-device业务恢复。
  safety backup和未覆盖资产边界见 [`daily-ops.md`](daily-ops.md#数据备份与恢复)。

  需要把同一操作窗口的state/audit/memory恢复点绑定后移交时，使用`aico-recovery capture`，再从off-device副本运行
  `verify --expected-sha256`和`drill`。manifest会明确显示`global_transaction=false`、
  `business_restore_ready=false`及必须补齐的`post_restore_evidence_assets`。capture还要求owner/CI独立选定的full Git commit、clean
  checkout、commit内active Project/Persona config和owner-only `.env`；恢复checkout、轮换control-plane secret并重新签发grant后，
  必须依次跑`verify-checkout`、`reinjection-receipt`、`verify-reinjection`、`provider-auth-receipt`和
  `verify-provider-auth`。后者会产生真实Claude/Codex请求，30分钟过期，但不保存prompt/output/credential。
  receiver DB保持set外独立恢复，使用`aico-dead-man-recovery backup|verify|drill|restore`，绝不能在AICO故障恢复时一起回滚。
  memory legacy文件要先owner核对并运行`aico-memory seal`。不要把core set称为全资产容灾。完整命令见
  [`daily-ops.md`](daily-ops.md#数据备份与恢复)。

### 让 AICO 在关闭终端后继续运行(macOS)

先完成一次前台启动,确认 Telegram、项目配置和 Adapter 都正常。`aico init`生成的`.env`就是
LaunchAgent读取的durable配置；不要把token直接写进plist:

如果还不知道sender/target ID，可先把两项留空并仅在当前terminal设置
`AICO_INGRESS_DISCOVERY_LOG_IDENTITIES=true`后运行`aico-phase1`。发送一条消息，本地日志会显示escaped
`sender`/`target`，但消息仍在业务入口前被拒绝。复制ID后停止进程，填入`.env`并把discovery设回`false`。
`aico-service doctor/install`会拒绝开启discovery的配置，避免身份日志长期暴露。

```bash
uv run aico-audit --audit-log .aico/audit.jsonl verify
uv run aico doctor
uv run aico-service --repo . render | plutil -lint -  # operator diagnostics
uv run aico service install
```

上面的默认`AICO_ABSENCE_ADMISSION_MODE=optional`适合开发和前台dogfood：关键absence能力关闭会WARN，但不会阻止安装。
准备让老板长期离开前，把`.env`改为`AICO_ABSENCE_ADMISSION_MODE=strict`。此时install只有在runtime alerts、external
liveness、scheduled recovery + disposable drill和owner-bound standing autonomy全部通过同一套preflight后才会执行launchctl。
strict OK只证明本机机器合同已配置；仍需分别验收receiver/provider独立、真实平台ACK、off-device存储、手机收件与human read，
不能把它称为commercial readiness认证。strict不是一次性installer flag：Telegram/Feishu runtime每次由LaunchAgent重启都会重新读取并
执行同一门禁；配置或external grant/backup binding漂移时会在Channel/state构造前失败，stderr只给出运行doctor的通用提示。

`install` 会创建用户级 `~/Library/LaunchAgents/com.aico.phase1.plist`,登录时启动,异常退出后重启。
Telegram 配置启动 polling runtime,Feishu 配置启动 webhook runtime;切换 Channel 后要重新 install。
日志写入 `.aico/service/`,进程 heartbeat 写入 `.aico/runtime-heartbeat.json`。plist 只包含可执行文件、
工作目录、PATH 和日志路径,不包含 `.env` 的 token/key value。

```bash
uv run aico service status
uv run aico doctor
uv run aico service restart
uv run aico service uninstall
```

`doctor` 的 `runtime owner` 必须显示 active PID 且与 launchd PID 一致。若提示 owner mismatch,
通常是另一个手动 `aico-phase1` / webhook 仍在运行;先停止原进程,不要删除 lock file或直接 kill 未确认 PID。

`uninstall` 会先 bootout,再把 plist 移到 `~/.Trash`,便于恢复。Heartbeat v5 同时记录 process freshness
以及 Channel、默认/可选 Adapter、morning scheduler 的脱敏 component status:required failure 会让 doctor
FAIL,optional Adapter failure 会 WARN。Telegram polling 或 morning scheduler 这类 owned task 死亡时,当前
runtime 会在进程内有界拉起:最多连续 3 次、每次最长 5 秒,存活 60 秒才清零;反复失败熔断 15 分钟。
`owned task recovering` 为 WARN,`owned task recovery open` 为 FAIL。外部 API/provider 失败不会触发恢复。
它仍是 synthetic health,不能证明 provider 已登录或真实 IM 已回包;
最终健康必须检查日志并发一条代表性 IM。

若要在primary Telegram/Feishu失效时把owned-task熔断或持续required component failure通知到独立系统,由owner在`.env`配置
vendor-neutral HTTPS webhook；receiver 必须按 `Idempotency-Key` 去重:

```bash
AICO_RUNTIME_ALERT_WEBHOOK_URL=https://your-alert-receiver.example/aico-runtime
AICO_RUNTIME_ALERT_WEBHOOK_BEARER_TOKEN=replace-with-owner-managed-token  # 可选
AICO_RUNTIME_ALERT_WEBHOOK_TIMEOUT_SECONDS=5
```

启用时必须同时保留 `AICO_STATE_DB_PATH` 和 heartbeat。AICO 会 durable 投递一条 `incident_opened`,恢复
稳定后投递同incident的`incident_resolved`;required component需要连续三份时间递增FAILED才open，OK才resolved；optional、
DEGRADED和瞬时失败不open，也不会触发自动restart/provider replay。失败按1/5/15分钟退避。URL/token不进入plist、SQLite、
heartbeat、doctor 或 event JSON。未配置时 doctor 明确 WARN `runtime alerts: disabled`,不会假装有第二通道。

若还要覆盖 Python event loop 卡死、LaunchAgent 持续启动失败或整台 Mac 离线,必须先在独立失效域部署并
显式 arm 一个 dead-man receiver,再配置独立于 incident alert 的 liveness HTTPS endpoint:

```bash
AICO_RUNTIME_LIVENESS_ENABLED=true
AICO_RUNTIME_LIVENESS_WEBHOOK_URL=https://receiver.example/v1/runtime-liveness/pulses
AICO_RUNTIME_LIVENESS_WEBHOOK_BEARER_TOKEN=replace-with-receiver-pulse-token
AICO_RUNTIME_MONITOR_ID=owner-runtime       # 仅小写字母/数字/._-,不要填主机名或路径
AICO_RUNTIME_LIVENESS_INTERVAL_SECONDS=60
AICO_RUNTIME_LIVENESS_TTL_SECONDS=300       # 至少为 interval 的 3 倍
```

runtime 取得 owner 后会立即发送一个新 `boot_id` 的 sequence 1,之后只在内存保留至多一个待重试 pulse；
不会把周期 pulse 写进 SQLite/outbox。receiver 必须按接收时间 + TTL 判 stale,并用 `Idempotency-Key` 去重。
当前pulse schema为v2：`disabled/healthy`会续租，`pending/failed`只排序、不续租；secondary alert交付持续异常超过TTL时，
receiver应产生reason=`alert_delivery_unhealthy`的open/resolved。升级时先升级并迁移receiver DB到schema v2，再启动v2 publisher，
不要把新publisher指向只接受v1的旧receiver。
Mac sleep/断网超过 TTL 默认就是 unavailable。正常 stop/restart 不会自动 disarm；永久卸载前必须先在 receiver
显式 disarm,否则远端应当按设计告警。heartbeat/doctor 只报告本机最近发送状态,不能证明远端仍在工作。
`AICO_RUNTIME_ALERT_WEBHOOK_URL` 继续只接收 `incident_opened/resolved`;它和 strict pulse endpoint 不能共用 URL。
若两侧都配置bearer，token也必须不同；doctor的`runtime endpoint isolation`会在install前fail closed，Phase1每次重启同样校验。
receiver 的 Docker/Compose、secret 生成、arm/status/disarm 与 outage 验收命令见
[`deploy/dead-man-receiver/README.md`](../../deploy/dead-man-receiver/README.md)。
商用absence路径应再配置different-origin fallback notification URL/token；两路并发接收同一event id，默认
`AICO_DEAD_MAN_NOTIFICATION_MINIMUM_ACKNOWLEDGEMENTS=1`提供1-of-2 failover，只有owner确实要求双平台ACK时才设2。
fallback token不得复用primary、pulse或admin token。不同origin只是机器下限，仍需真实provider/账号/网络隔离证据。
receiver会把当前策略和逐事件策略写入schema v3；pending期间改route/quorum会拒绝启动。应先恢复原配置并清空pending，
再切换策略，不能用1-of-2配置重启去降级原2-of-2事件。v1/v2升级前先备份receiver。
Round 242的schema v4再保存逐event ACK和slot健康：partial quorum会通过尚存route主动发送
`notification_route_degraded`，后续真实event恢复时发送`notification_route_recovered`。可用admin token查询
`GET /v1/notification-routes`；该状态不含URL/token，也不是无event期间的continuous canary。v3升级前先备份。
若两个真实webhook bridge都已承诺识别并吞掉`notification_route_probe`，可在升级receiver到schema v5并备份v4后显式设置
`AICO_DEAD_MAN_NOTIFICATION_PROBE_CONTRACT=silent-route-probe-v1`。probe复用真实URL/token/POST，首次失败只标suspect，连续达到阈值
才主动发degraded；默认disabled。任何probe出现在老板终端或触发事故自动化，都应立即关闭，不能用HEAD/旁路token替代该验收。

真实演练必须从receiver的`/signed-evidence`导出envelope；owner从receiver私钥导出的SPKI公钥应单独复制并固定在
AICO checkout之外。commission/recommission在owner选择的短窗口内组合运行：

```bash
uv run aico-dead-man-evidence signed-dead-man-evidence-owner-runtime.json \
  --trusted-public-key /absolute/private/receiver-evidence-public.pem \
  --runtime-id owner-runtime \
  --minimum-complete-outages 1 \
  --require-all-delivered \
  --maximum-evidence-age-seconds 300 \
  --require-fresh-notification-probe \
  --require-all-routes-healthy
```

省略最后三项只适合历史审计；生成时fresh不代表验收时仍fresh。签名通过只证明owner-pinned私钥签过exact payload，
不证明私钥确实位于独立host、provider ACK或老板已读。

strict runtime不能只保留上面的命令输出。先在最终`.env`写入两个新的绝对、checkout-external路径，确保evidence为owner-only，
checkout为owner审阅的clean revision，然后生成不可覆盖的commission receipt：

```bash
chmod 600 /absolute/private/signed-dead-man-evidence-owner-runtime.json
uv run aico-commission create \
  --checkout . \
  --project-config config/projects.example.json \
  --persona-config config/personas.example.json \
  --expected-config-revision <full-owner-reviewed-commit> \
  --runtime-id owner-runtime \
  --dotenv .env \
  --dead-man-evidence /absolute/private/signed-dead-man-evidence-owner-runtime.json \
  --trusted-receiver-public-key /absolute/private/receiver-evidence-public.pem \
  --maximum-evidence-age-seconds 300 \
  --output /absolute/private/runtime-commissioning-<generation>.json
```

把输出中的receipt SHA保存到owner操作记录，可在有效期内离线复核：

```bash
uv run aico-commission verify \
  --checkout . \
  --project-config config/projects.example.json \
  --persona-config config/personas.example.json \
  --expected-config-revision <full-owner-reviewed-commit> \
  --runtime-id owner-runtime \
  --dotenv .env \
  --dead-man-evidence /absolute/private/signed-dead-man-evidence-owner-runtime.json \
  --trusted-receiver-public-key /absolute/private/receiver-evidence-public.pem \
  --receipt /absolute/private/runtime-commissioning-<generation>.json \
  --expected-receipt-sha256 <sha-from-create>
```

`AICO_COMMISSIONING_DEAD_MAN_EVIDENCE_PATH`、`AICO_COMMISSIONING_RECEIVER_PUBLIC_KEY_PATH`与
`AICO_COMMISSIONING_RECEIPT_PATH`必须已在receipt创建前写入最终`.env`；否则后写会改变
代际并使receipt立即失效。每次config/evidence更新使用新文件名并重新commission，不覆盖旧artifact。之后再运行doctor/install。
receipt会在dead-man age或silent-probe TTL较早者到期；运行中到期显示required
`configuration:commissioning-receipt` FAILED并告警，不自动重启或联网刷新。

---

## 可选：授权一次定时只读 standing work

只有在 morning push 已精确配置、Codex Adapter 已启用、项目 charter 任命给 Codex reviewer 后，才考虑启用：

```bash
install -m 600 docs/examples/standing-autonomy.example.json \
  /absolute/private/aico-standing-autonomy.json
# 替换外部文件中的所有 replace-with-*、expiry、run/duration 与 token_stop_threshold
export AICO_STANDING_AUTONOMY_GRANT_PATH="/absolute/private/aico-standing-autonomy.json"
uv run aico-service --repo . doctor
```

不要把 grant 留在 repo，也不要给 group/world 权限。系统只在 scheduler 的 morning tick 消费，固定 Codex
read-only/no-network/no-resume/no-collaboration boundary；手工 `/morning` 和 `/inbox` 不会自执行。首次真实验收使用
`max_runs=1`。install前必须看到doctor的`owner-bound runtime binding verified`；该non-mutating preflight会沿真实
project/charter/persona/Adapter路径验证，而不创建state或调用provider。步骤与停止条件见
[`daily-ops.md`](daily-ops.md)；没有真实owner grant时保持禁用。

真实运行后再次查看`/morning`：必须有短ID的standing autonomy receipt。`evidence_missing`不是“尚未刷新”，而是
accepted与task证据不完整；先查`/proposals`/`/tasks`/`/audit`，不要自动retry或refund run budget。
terminal receipt还应显示provider实际`tokens=N`。`token_stop_threshold`只会在下一次run前按累计实测量停授，不能
阻止当前run越过阈值；usage缺失同样显示`evidence_missing`并停止后续自治。不要从该值自行推算美元账单。
Round 217起还要看`outcome=complete criteria=N/N sources=N`：task `[done]`只表示transport结束，不能代替结果合同。
`outcome=missing/invalid/blocked`都会停止下一次scheduled run；先查`/task`和`/proposals`，人工核对引用的仓库相对
file/line是否真的支持charter，禁止换grant自动重试。`sources=N`只证明本地位置存在，不证明业务语义正确。
standing result还固定限制为32K总字符及bounded criteria/source/list/text/path；`result_too_large`或
`result_schema_invalid`表示provider结果未进入业务验收，只保存了短失败回执。该上限保护本地内存/state，不限制本次
provider token账单。
成功回执还应显示`evidence=current`。系统会用最多16个source、单文件256KiB的本地fingerprint，在老板接手和下一次
scheduled run前检测变化；`evidence=drifted/missing`都会停授。老板IM不会显示path/hash/source正文。full-file hash是
保守的字节漂移锚点，不是签名或业务语义证明；owner检查变更后应重新人工验收，不要自动重跑。

同时运行`uv run aico-state --db "$AICO_STATE_DB_PATH"`：morning delivery应为`delivered`，对应
`recent_scheduled_autonomy`应为`settled`。`dispatch_recorded`只证明accepted proposal/task已在provider派发前持久化；
proposal/task只显示SHA。`retrying`会只重试自治而不重发已ACK晨报，`exhausted`会让runtime health失败。

---

## 启用 aico-view(只读视图)

老板在 IM 里的默认入口不是访问 Mac 本机服务,而是让 AICO 发送一份 HTML 快照:

```bash
export AICO_VIEW_ENABLED=true
export AICO_VIEW_OUTPUT_DIR=".aico/view-snapshots"  # 可选,非附件 Channel 的本地降级目录
export AICO_VIEW_TELEGRAM_BOT_USERNAME="your_bot_username"  # 可选,启用 HTML 内回 IM deep link
```

重启 `aico-phase1` 后,在 Telegram 里:

```text
/project aico
/view
```

`/view` 会把当前项目的 Boss Brief / Timeline / Trace / Memory 生成一份自包含
`.html` 文件发到 Telegram。它不启动本机 HTTP 服务,也不要求手机访问
`127.0.0.1`。注意:HTML 内容会进入 Telegram 聊天记录,只发到可信私聊或可信小群。

### 可选:启动 aico-view HTTP 服务(本机排障 / 隧道 dogfood)

`aico-view` 是一个独立的 FastAPI 进程,它**不挂 channel/adapter**,只打开
orchestrator 写出的 JSONL/SQLite,提供 Timeline / Task Trace / Memory Tree
三个手机友好视图。所有写操作仍走 IM(/undo、/why、/experience 等),aico-view 自身
是只读的(任何 POST/PUT/DELETE 都会返回 405)。

```bash
export AICO_AUDIT_LOG_PATH="/tmp/aico-audit.jsonl"
export AICO_MEMORY_PATH="/tmp/aico-memory.jsonl"
export AICO_STATE_DB_PATH="/tmp/aico-state.db"
export AICO_VIEW_PROJECT_IDS="aico"     # 可选,逗号分隔
export AICO_VIEW_HOST="127.0.0.1"        # 默认 127.0.0.1,只允许本机访问
export AICO_VIEW_PORT="8765"

uv run aico-view
# 浏览 http://127.0.0.1:8765
```

要让手机访问需要隧道(ngrok / Cloudflare tunnel)和 **`AICO_VIEW_TOKEN`**。
绑非 loopback host 时没设 token 会全请求 401(有意防误暴露)。完整部署形态、
安全模型和 env 速查见 [`aico-view-deploy.md`](aico-view-deploy.md)。

---

## 启用更多 Adapter

这些 Adapter 默认关闭,适合在本机 CLI 已安装并登录后再开启:

```bash
export AICO_ENABLE_CURSOR_ADAPTER=true
export AICO_ENABLE_CODEFLICKER_ADAPTER=true
export AICO_ENABLE_TRAE_ADAPTER=true
export AICO_ENABLE_GEMINI_ADAPTER=true
```

公开 README 当前仍把 Claude Code / Codex 作为最低门槛快速路径。Cursor / CodeFlicker /
Trae / Gemini 已完成真实 smoke test,但使用前仍需要确认本机 CLI 已安装并登录;详见
[`STATUS.md`](../../STATUS.md)。

---

## 跑不起来怎么办

参见 [`troubleshooting.md`](troubleshooting.md) 和 [`daily-ops.md`](daily-ops.md)。
