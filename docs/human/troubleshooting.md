# Troubleshooting — 故障排查

> 常见问题速查。问题按"症状 → 原因 → 处理"组织。
> Phase 0 占位,实际问题在使用过程中逐步累积。

---

## 排查总原则

遇到问题,**按以下顺序处理**:

1. **看日志**:`tail -f logs/aico.log`,搜 `ERROR`、`WARN`、`Adapter busy`、`Adapter process exited`
2. **看状态**:运行健康检查命令
3. **查 PITFALLS**:[`docs/journal/PITFALLS.md`](../journal/PITFALLS.md) grep 关键词
4. **查 BLOCKERS**:[`docs/journal/BLOCKERS.md`](../journal/BLOCKERS.md) 看是不是已知问题
5. **以上都没有 → 写到 BLOCKERS,留给下一轮**

---

## 启动相关

### 启动失败:端口被占用
```bash
# 查找占用端口
lsof -i :8080
# 杀掉占用进程
```

### 启动失败:配置缺失
- 检查 `.env` 文件存在
- 检查必填配置(Bot Token、Adapter 路径)

### 关闭终端后 Bot 消失 / 定时早报没有发送

1. 运行 `uv run aico-service --repo . doctor`。
2. `env file` 失败:从 `.env.example` 创建 `.env`,替换 placeholder,执行 `chmod 600 .env`。
3. `plist current` 失败:仓库/venv/PATH 已变化,重新执行 `aico-service install`。
4. `launchctl` 未 loaded:执行 `aico-service restart`;仍失败时看 `.aico/service/stderr.log`。
5. `heartbeat` stale/invalid:先看 `logs/aico.log` 和 stderr,确认进程是否崩溃或 event loop 卡住。
6. `components failed: channel:<name>`:检查 active polling/webhook 服务和 Channel API;Telegram polling task
   意外退出即使 `getMe` 可达也会失败。
7. `components failed: adapter:<default>`:确认默认 CLI 在 LaunchAgent PATH 中可见;再跑真实最小任务验证登录态。
8. `components degraded: adapter:<optional>`:primary path 仍可用,修复对应可选 Adapter 后重新 doctor。
9. `owned task recovering:<name>`:runtime 已原地拉起自有后台 task;至少等待 60 秒稳定期后再查。
10. `owned task recovery open:<name>`:连续 3 次恢复未稳定,已熔断 15 分钟;检查日志中的异常类型和代码,
    不要用 restart 循环掩盖问题。冷却后会再进行一轮有界尝试。
11. `out-of-band alerting disabled`:primary path 可继续运行,但完全无人值守故障没有第二通知出口;由 owner 配置
    durable HTTPS receiver,不要复用同一个 primary Channel。
12. `out-of-band alerts pending:<N>`:事件仍在 SQLite,按 1/5/15 分钟退避;检查 receiver 可达性和按
    `Idempotency-Key` 去重能力。不要手工删除 outbox 或反复 restart。
13. `out-of-band alerting failed`:alert store/probe 内部失败;先看异常类型日志和 `aico-state` 表计数,URL/token
    不会出现在诊断输出。
14. components FAILED但owned task仍healthy时，required组件会在第三份时间递增snapshot生成`health:*` secondary incident。
    `runtime_health_alert_candidates`表示仍在确认窗口；不要删除表、反复restart或把它当成自动修复计数。恢复到DEGRADED不会
    resolved，必须恢复到OK；optional组件永远不进入该incident源。
15. `component health unavailable`:旧 heartbeat;当前 runtime 启动会先完成首轮 probe 再进入服务。
16. components healthy 但没有 IM:继续检查 token、网络、provider 登录和 send/getUpdates 日志;synthetic
    health 不能替代真实 IM 回包。

### install被 absence admission 拒绝

`AICO_ABSENCE_ADMISSION_MODE=strict`表示owner要求“老板离开前”的机器合同门禁，不是普通开发安装。doctor会在固定合同名后
列出尚未OK的项目；它不会显示URL、token、target、grant或path。

1. `runtime alerts`：配置独立durable incident receiver，不要复用primary IM。
2. `runtime liveness`：先在第二故障域arm strict pulse receiver，再配置专用URL/token/monitor id/TTL。
3. `recovery backup`或`recovery drill`：使用预先存在的owner-only外部目标，启用scheduled capture和disposable drill；不要让
   AICO创建缺失mount，也不要为了过门禁开启未审阅的retention删除授权。
4. `standing autonomy`：配置morning push、Codex read-only charter和external owner-only grant，并让真实binding preflight通过。
5. `runtime commissioning`：先从receiver导出signed evidence，在最终`.env`写入evidence、owner-pinned receiver公钥、receipt
   三个checkout-external绝对路径，再运行`aico-commission create`并传`--trusted-receiver-public-key`。必须是clean
   owner-reviewed revision，evidence/receipt为owner-only，公钥不可被group/world写入。
6. 若当前只是本地开发，可由owner明确改回`optional`；这会恢复WARN安装，不代表上述能力存在。
7. strict OK后仍必须保存真实receiver ACK、provider/IM、存储和手机样本；不要把machine admission当成commercial认证。
8. install曾经OK但LaunchAgent反复重启时，重新运行doctor；runtime会持续执行strict，不会因supervisor restart降级到optional。
   `AICO configuration validation failed`是故意脱敏的入口错误，具体固定合同从doctor查看，不要在stderr寻找token/URL。
9. `runtime endpoint isolation`失败表示incident alert和dead-man pulse复用了exact URL或bearer；为两种strict protocol配置不同path，
   双方都有token时轮换为不同credential。不要通过打印原值比较，也不要把same-origin误当成该错误。
10. `configuration:dotenv-generation`失败表示当前进程加载后`.env`发生变化；旧进程不会热加载。核对新配置并完成外部验收后显式
   restart/install，不要反复touch文件或删除heartbeat消音。
11. `configuration:commissioning-receipt`失败表示receipt/evidence/config/dotenv binding漂移或已到最早TTL。保留旧artifact审计，
    使用新路径重新export/create/doctor并显式restart；不要覆盖JSON、手改expiry或扩大age掩盖失败。

### dead-man evidence strict验收失败

1. `evidence freshness requirement is not met`：bundle已超过operator声明窗口；从receiver重新导出并立即验证，不要放大TTL掩盖流程延迟。
2. `evidence generation time is in the future`：先修复可信验收机时钟或来源；不要用未来时间延长证据寿命。
3. `notification probe freshness requirement is not met`：probe可能disabled、pending、从未完成或按当前时刻已过期；检查provider bridge
   对silent v1的真实ACK与无展示合同，不能手工改JSON。
4. `notification route health requirement is not met`：至少一个slot仍unknown/degraded；恢复真实route并等待持久状态转healthy后重新导出。
5. 不带`--maximum-evidence-age-seconds --require-fresh-notification-probe --require-all-routes-healthy`的成功只表示历史artifact结构可验，
   不能作为commission/recommission当前健康结论。
6. `signed evidence verification failed`：拒绝把unsigned历史bundle用于strict commissioning；核对owner固定的SPKI Ed25519公钥、
   receiver私钥路径/`0600`权限和rotation记录。不要信任envelope自带key、不要把公钥替换成新key来消音。

### 启动报 runtime owner already active

另一个进程正在拥有同一 state DB。竞争者会在 reconciliation、scheduler 和 Channel start 前退出,这是防止
live task 被误标 interrupted 和重复消费 IM 的安全门禁。

1. 运行 `uv run aico-service --repo . doctor`,查看 owner PID 是否与 launchd PID 一致。
2. 一致:服务已在运行,不要再启动第二个 terminal runtime。
3. 不一致:通常是手动 runtime 占锁而 LaunchAgent loaded;先确认 PID/日志并正常停止原 runtime。
4. 不要仅因 lock 文件存在就删除它;kernel lock 才是 owner 事实,crash 后会自动释放。
5. 原 owner 停止后重试。系统不会自动 kill 竞争 owner。

Round 200 修复了旧 runtime 在 Channel 非阻塞启动后立刻停止 morning scheduler 的生命周期问题。若使用
更早代码,即使进程仍在,定时早报也可能从未真正保持运行。

### 重启后任务显示 interrupted

如果 reason 包含 `runtime restarted before task completion`,说明旧 runtime 退出时任务仍是 `running`,但新
runtime 已失去该 Adapter 进程的输出和中断所有权。这是保守恢复,不代表底层外部动作一定没有发生。

1. 用 `/task <id>` 和 `/audit` 核对原任务、Adapter、风险与恢复原因。
2. 检查目标文件、消息、发布、付款或数据修改是否已产生部分/完整副作用。
3. 只有确认重做安全后才提交新任务;当前不会自动 retry/replay。
4. 若原任务是 `waiting_approval`且仍在冻结的approval lease内,它不会因restart被取消；已到期则会在startup变为
   `rejected`，必须重新提交任务，不能批准旧票据。

### 审批显示 approval lease expired

这不是Adapter失败，而是风险任务在老板确认前超过了冻结deadline。系统已经将approval与task原子收口为
`expired/rejected`，并通过reconciliation audit outbox保留`approval_expired`事件。

1. 用`/task <id>`核对旧目标、风险和可能已经变化的仓库/外部上下文。
2. 仍需执行时，重新发送一条范围明确的新任务，让它重新经过风险识别和审批；不要尝试复活旧approval。
3. 若业务确实需要更长窗口，只能在300..604800秒内调整`AICO_APPROVAL_MAX_AGE_SECONDS`并重启；修改只影响新审批。
4. 若startup报告audit sink失败，先修复`AICO_AUDIT_LOG_PATH`；不要删除pending outbox或直接改SQLite状态。

### 出现 authorization clock rollback detected

系统观察到wall clock比SQLite high-water或进程monotonic应到时间落后超过5秒。为避免延长旧授权，pending approval已经
失效，新的risk/preauthorized任务和scheduled standing run会fail closed；普通只读查询仍可用。

1. 用系统设置或受管时间服务核对本机日期、时区和同步状态；AICO不会自行改系统时间或联网取时。
2. 让wall time自然追平或修正到正确时间，再重新发送范围明确的新risk task；旧approval不会复活。
3. 用`/task <id>`和`/audit`核对被失效任务；standing消息只应显示hold，不应有provider dispatch/usage receipt。
4. 不要直接删除`authorization_clock_state`、改approval payload或用state reset绕过。确需restore/reset时按owner-fenced
   停机流程执行，并把该动作视为安全边界重建。

### Bot 收到消息但完全不回复

先检查日志是否出现`Unauthorized IM ingress dropped`。Round 221起正式runtime会在任何command、memory、task、audit或
provider动作前同时校验channel、owner sender和trusted target；静默拒绝是安全行为，不是Adapter故障。

1. 运行`uv run aico-service --repo . doctor`，确认`IM ingress`为OK；不要把Bot Token当sender授权。
2. 核对`AICO_OWNER_SENDER_IDS`和`AICO_TRUSTED_TARGET_IDS`，以及消息实际所在的Telegram chat/Feishu chat。
3. 不知道ID时停止常驻服务，仅在前台用空binding和`AICO_INGRESS_DISCOVERY_LOG_IDENTITIES=true`发送一条消息；复制
   本地escaped sender/target后立刻关闭discovery并填回`.env`。
4. `AICO_MORNING_PUSH_TARGET_ID`必须属于trusted target；额外approval reviewer必须属于owner sender。
5. 不要为排障改成allow all或开放unauthenticated `/whoami`；如果owner IM账号被接管，应先在平台侧撤销session/token。

### Morning scheduler存活但早报、后置自治或终态通知没有收敛

Round 232/233/238起scheduler health同时读取durable morning delivery、scheduled autonomy intent和terminal outcome outbox，
不再只看background task。先运行
`uv run aico-state --db "$AICO_STATE_DB_PATH"`：`pending/retrying/sending`为DEGRADED，`exhausted`为FAILED，
`delivered`只证明平台ACK。

1. 确认morning push启用时`AICO_STATE_DB_PATH`存在且owner可写；不要为恢复发送而删除outbox或改delivery id。
2. `retrying`按1/5/15/15分钟退避，最多五次；修复channel credential/network后等待同一exact envelope收敛。
3. `duplicate_possible=true`表示accept-before-ack或发送中崩溃，检查聊天里相同`Delivery:`引用；不要把重复当成两次业务运行。
4. `delivered`后standing autonomy异常不会重发晨报；分别从proposal/task/result/usage receipt排查自治事实。
5. `aico-state`不会展示target、正文和raw message id；不要通过数据库截图向外分享owner-only晨报正文。
6. `recent_scheduled_autonomy`为`retrying`时，先看是否只有hold通知重复；系统沿用相同intent id。不要删除intent、
   proposal或task来强制重跑。`settled + dispatch_recorded`表示已有accepted proposal/task，继续从`/task`和result/usage查结果。
7. intent `exhausted`表示五次都未形成可结算证据，runtime health为FAILED；停止自动恢复并保留state/audit后人工核对。
   `settled`不等于outcome complete，proposal/task ID SHA也不证明业务语义。
8. `recent_autonomy_outcome_deliveries`为`retrying`时先修复同一channel，不要重跑task或换grant；系统只重发冻结的content SHA。
   `duplicate_possible`表示平台可能已接受但本机未记录ACK，`exhausted`为required health FAILED。
9. `settled + dispatch_recorded`却没有outcome行应在scheduler下一次工作前自动补建；若持续缺失，保留DB并检查projection错误。
   `source_status=evidence_missing`是accepted后缺task/usage证据的主动告警，不授权自动provider replay。
10. outcome `delivered`只证明exact trusted target返回平台ACK；正文、target和raw message id不会出现在`aico-state`，也不能据此
    声称human read或业务验收完成。
11. `bounded evidence pack unavailable`表示charter未配置source、heading marker漂移、路径/软链/UTF-8或size/line/总字符上限失败；
    修正owner-reviewed project config后重新doctor，不要放宽cap或让Agent浏览全仓库。
12. `budget=exceeded`表示provider已报告本run超过grant的`max_total_tokens`；系统保留usage但拒绝结果。它仍算预算失控样本，
    不得通过换grant重跑洗掉；先保留state/audit并复核CLI/provider budget行为。

### 启动日志显示 recovery audit sink unavailable

恢复 outbox 会先保留 interrupted 状态与完整 audit intent,再投递 configured sink。若 JSONL 路径不可写或内容损坏,
startup 会失败而不会错误确认 delivered;LaunchAgent 可能按异常退出策略重试。

1. 停止runtime，同时只读复制JSONL与`.checkpoint.json`；不要编辑原文件、删除checkpoint或先重跑seal。
2. 运行`uv run aico-audit --audit-log "$AICO_AUDIT_LOG_PATH" verify`。hash chain、checkpoint、truncated、incomplete、
   duplicate id、symlink或owner-only错误都必须当作证据事件处理，不能自动跳过坏行。
3. `unsealed`只用于升级前legacy：owner核对baseline无误后运行`seal`。如果已经报告hash/checkpoint损坏，seal不是repair。
4. 检查父目录、磁盘空间和owner权限；audit JSONL、checkpoint必须来自同一恢复点。不要手工删除state DB中的pending
   outbox，修复可信资产后再启动。
5. 启动后`aico-state --db <path>`应显示`pending_recovery_audits: 0`。event已fsync但checkpoint未落盘的单一crash
   window会自动推进checkpoint，同event重投不会重复；其它不一致仍fail closed。

### Audit backup / verify-backup 被拒绝

1. `does not exist`或`unsealed`：核对live audit路径；legacy先由owner确认baseline再seal，不能用backup隐式迁移。
2. `output already exists`：换一个新artifact名。命令不会覆盖已有恢复点，也不要先删除旧证据来复用固定文件名。
3. `owner-only`/`non-symlink`：artifact含审计正文，确认来源后`chmod 600`；不要从symlink或公共目录直接verify。
4. member/manifest/hash/ledger integrity失败：隔离artifact，不要改ZIP或重写manifest。用独立记录的outer SHA判断传输变化，
   再从可信live source生成新的new-path恢复点。
5. outer SHA一致只证明选中了同一artifact；没有独立保存SHA、off-device加密/retention和隔离恢复时，不能声明DR完成。
6. backup期间audit写入短暂停顿是point-in-time锁的代价；ledger过大时安排维护窗口，不要通过跳过lock或分别复制规避。

### Audit drill-backup / restore 被拒绝

1. drill的`workspace/report`错误：workspace若显式提供必须已存在；report必须是新路径。失败后workspace应为空，报告不会
   覆盖旧证据。drill不接触live audit，也不需要停止runtime。
2. `state database identity verification failed`：`--state-db`必须指向生产runtime同一份AICO SQLite，不能用空文件、
   任意SQLite或拼错路径代替owner fence。不要为了通过检查初始化另一份DB。
3. `runtime owner is active`：先正常停止LaunchAgent/前台runtime并用doctor/status确认；不要删除`.owner.lock`文件，
   kernel lock而不是文件是否存在决定owner状态。
4. `explicit restore confirmation`、SHA或preservation output错误都发生在覆盖前；补`--yes`、核对独立记录的SHA、换
   new-path输出。不要删除旧preservation来复用文件名。
5. summary中的`verified_safety`可再跑`verify-backup`；`unverified_quarantine`说明原live已损坏/unsealed，只保留原始
   取证字节，不能当可信backup恢复或重新seal。
6. restore异常后先跑live `verify`。若双文件替换中断，verify必须失败；保留所有preservation，使用同一可信backup和
   **新的**preservation路径重跑可收敛。不要手工拼接ledger/checkpoint。
7. restore成功只证明local audit component恢复；仍需核对state、memory/config、pending outbox和代表性IM。没有
   off-device来源、加密、retention与隔离checkout证据时，B-013仍未关闭。

### Core recovery set capture / verify / drill 被拒绝

1. capture提示path/revision缺失：显式传`--state-db`/`--audit-log`/`--memory-log`/`--project-config`及
   `--expected-config-revision`，或确认对应环境变量已配置。persona使用外部文件时也传`--persona-config`。命令不会自动
   初始化空DB、seal legacy ledger或把当前HEAD当作reviewed revision。
2. `output already exists`：换new-path名称，不要删除旧set复用。state DB的WAL/SHM/owner lock和audit checkpoint/lock
   也不能作为output，避免覆盖live sidecar。
3. SHA、member、manifest或component integrity失败：隔离整个set。即使outer manifest/hash同步改写，内部SQLite schema/
   integrity、audit和memory chain/checkpoint仍必须通过；不要只解出看似正常的那个组件继续恢复。
4. `business_restore_ready=false`、`unresolved_assets=[]`与非空`post_restore_evidence_assets`可以同时出现：前者表示尚未完成
   商业恢复验收，中间只表示每个required asset已有恢复方法，后者才列出本次恢复仍要提供的checkout/reinjection/provider/
   receiver证据。不能手改manifest或把contract-ready写成evidence supplied/artifact captured。
5. capture window较长表示三个component可能有更大skew；它不是global transaction。大state/audit/memory应安排低写入窗口，但
   不要通过伪造时间或删除coverage项改善指标。
6. drill workspace/report遵守new-path规则，失败后workspace应清空。drill只证明内嵌state/audit/memory能走production primitive，
   不触碰live、不恢复missing assets，也不授权combined restore。
7. artifact同时含业务SQLite与完整audit正文，必须owner-only并进入加密off-device storage；outer SHA存到独立authority。
8. `owner-reviewed revision`/`clean checkout`拒绝：必须使用Git root、完整40/64位reviewed commit，并提交或移除所有非ignored
   tracked/untracked变化；active config必须在checkout内、已被该commit跟踪且字节一致。不要用`git reset --hard`绕过取证。
9. `verify-checkout`失败但offline `verify`成功，说明artifact本身可信而恢复代码环境不匹配；保持runtime停止，取回精确commit、
   清理意外文件并重新核对。该命令不会自动checkout/pull/reset。
10. capture或`reinjection-receipt`报告runtime material失败：`.env`必须位于checkout根、owner-only、非symlink、Git未跟踪且无duplicate key；
    channel required secret、alert/liveness配对、IM binding、approval lease和standing grant必须通过production preflight。
    错误不会显示值/path。不要把secret/grant正文复制进set来绕过。
11. `verify-reinjection`拒绝：先核对独立receipt SHA，再检查slot集合、grant enabled mode与当前binding。有效secret允许轮换，
    但新增/删除slot或启停grant需要新的reviewed recovery set；grant内容变化需要新的owner decision receipt。receipt中的
    `external_authentication_live_verified=false`不是故障，表示下一步仍需provider receipt。
12. `provider-auth-receipt`拒绝：它会真实调用manifest中的全部provider。Claude/Codex必须能在private empty cwd用受限命令返回
    exact challenge、terminal success和usage；timeout、每路输出超过256 KiB、wrapper executable、缺usage或非exact response均
    fail closed且不生成receipt。其他provider尚无批准probe时必须保持失败，不能改用yolo参数绕过。
13. `verify-provider-auth`拒绝：核对两份独立SHA、当前reinjection receipt、provider启停与probe executable是否漂移，并确认未超过30分钟。
    verify固定不重放live probe；过期后要生成新provider receipt，不能改时间或复制旧JSON。

### Scheduled recovery backup没有收敛或RPO health失败

1. 运行`uv run aico-service --repo . doctor`和`uv run aico-state --db "$AICO_STATE_DB_PATH"`。`pending/retrying`表示
   capture尚未结算，`exhausted`或最后verified超过`AICO_RECOVERY_BACKUP_MAX_AGE_SECONDS`会使required health FAILED；
   `custody=failed`或checked time超过`AICO_RECOVERY_CUSTODY_MAX_AGE_SECONDS`表示最近恢复点现在已无法持续证明。
2. doctor报告destination invalid时，确认目标目录仍是已挂载、absolute、owner-only、非symlink且位于checkout外。不要让AICO
   自动mkdir；mount消失时创建本地替代目录会制造“off-device备份成功”的假象。
3. `artifact only`会在同一ID上deep verify并补receipt；artifact+receipt会同时复验。`receipt only`、SHA不匹配、宽权限或已有
   不一致文件都fail closed。不要删除文件或改SQLite状态来强制重建，先隔离并保存证据。
   周期custody同样会重新打开pair并运行完整verifier，不只检查文件名。
4. 重试按1/5/15/15分钟最多五次。修复source ledger/config cleanliness/目标容量后等待同一intent；EXHAUSTED后保留现场，
   由owner确认原因并以新的scheduled窗口恢复，不要自动restore。
5. doctor的`storage class not attested`不是故障：它提醒本机无法证明目标已加密、off-device、retained或被独立监控。
   只有外部存储证据和隔离restore drill才能关闭B-013。
6. `destination identity changed`可能是mount掉线、目录被重建，也可能是合法remount/迁移。保持health FAILED并核对真实volume；
   有意迁移时使用新的明确output path重新建立外部验收，不要自动rebind。fingerprint是本机连续性证据，不是volume UUID。
7. `pruning`表示破坏性intent已经先落SQLite。不要改状态或手工补文件：pair都在会重新deep verify后删除，artifact已删但sidecar
   仍在会复核receipt后收口，两者都无会写`pruned` tombstone；仅artifact仍在表示receipt异常丢失，必须保留现场并调查。
   即使把`AICO_RECOVERY_RETENTION_ENABLED`改回false，既有intent仍会恢复；该开关只阻止新清理。
8. retention到期但未推进会使health DEGRADED；PRUNING卡住使health FAILED。先核对`aico-state`中的policy SHA/time和目标容量，
   再检查artifact/sidecar权限与digest。不要用mtime手工轮转，也不要把本机`pruned` tombstone写成provider lifecycle/WORM证明。
9. `recent_recovery_drills`为`pending/retrying`表示disposable materialization尚未收敛，`exhausted`或最后verified超过
   `AICO_RECOVERY_DRILL_MAX_AGE_SECONDS`会使required health FAILED。先保留目标artifact，检查临时容量和production
   state/audit/memory drill错误；不要改SQLite为verified，也不要为了转绿执行live restore。
10. restart中的RUNNING drill会回到同一intent立即重试且不消费一次失败预算，因为它没有live副作用。关闭
    `AICO_RECOVERY_DRILL_ENABLED`可停止新/后续演练，但若retention仍开，durable open/latest exhausted目标仍受保护。
    success只证明本地captured components materialize，不能替代off-device来源、checkout/reinjection/provider/receiver和业务RTO。

### Dead-man receiver backup / drill / restore 被拒绝

1. `schema`、`executable objects`或`semantic verification`失败：隔离artifact。工具要求exact version/DDL，并拒绝trigger、
   view、user index、partial monitor checkpoint、payload-column mismatch、outage顺序或delivery overtake；不要修改DB凑通过。
2. `receiver worker is active`：正常停止receiver并确认`/readyz`不可达/进程退出。不要删除`.owner.lock`；kernel lock而不是
   文件存在决定ownership。online `backup`和offline `drill`不需要停worker，只有live restore需要。
3. SHA错误或缺`--yes`发生在替换前：从独立authority核对exact artifact digest，再显式确认。不要自动选择目录中最新文件。
4. `verified_safety_backup`表示原live已被一致备份；`unverified_quarantine`只保留DB/WAL/SHM原字节，不证明它们一致或可恢复。
   两者都保留到`/readyz`、monitor、pending delivery与admin evidence export验收完成。
5. interrupted restore后保持receiver停止，核对选定artifact SHA和live `verify`。使用同一可信artifact重跑；不要手工拼接DB/WAL/SHM。
6. receiver只在自身故障时恢复。AICO Mac故障或core recovery不是receiver restore理由；回滚外部observer会删除正在需要的事故证据。

### Memory ledger / backup / restore 被拒绝

1. `unsealed`只允许用于owner核对过的升级前JSONL；先停止runtime、`chmod 600`并运行`aico-memory seal`。hash/checkpoint
   损坏不能通过seal修复。
2. `verify`报告hash、truncated、incomplete、permission或symlink错误时，隔离ledger与matching checkpoint，不要跳坏行。
3. backup/verify-backup/drill-backup遵守new-path、owner-only和expected SHA；ZIP内含完整记忆正文，不是加密容器。
4. restore必须指向真实AICO state DB并等待runtime owner释放，提供新的preservation路径和`--yes`。有效live先做verified
   safety；损坏live只进入unverified quarantine。异常后用同一可信artifact和新的preservation路径重跑。

### State backup / restore 被拒绝

1. `backup source database is missing`：核对 `AICO_STATE_DB_PATH`；不要让命令通过初始化空 DB 来伪造备份。
2. `backup output already exists`：换一个新 artifact 路径。命令不会覆盖已有备份。
3. integrity/schema/SHA 失败：不要继续 restore，也不要手改 artifact；重新从可信 source 备份，或核对 owner
   记录的 SHA。verify 是只读的，不会自动迁移旧 schema。
4. `runtime owner is active`：restore/reset 必须先正常停止 LaunchAgent 或前台 runtime，再用
   `aico-service doctor` 确认 owner free；不要删 lock file或 kill 未确认 PID。
5. restore 成功后保留 `state.db.pre-restore-<UTC>.db`，检查 `/tasks`、`/inbox`、pending approval/outbox和一条
   代表性 IM。恢复的是 AICO 业务状态，不会复活旧 Adapter subprocess，也不会自动 replay interrupted task。
6. 不要把同机 artifact/local drill当容灾证明；off-device copy、retention、encryption和隔离checkout业务恢复仍需按
   B-013 完成。
7. `drill workspace is missing`：先创建owner-only workspace或省略`--workspace`使用系统temp。drill不会创建
   operator指定workspace，避免拼写错误把证据写到意外位置。
8. `drill report already exists`：换一个新report名，不要删除/覆盖旧证据。失败后workspace应为空；若机器异常
   中断留下`aico-state-drill-*`，先确认没有drill进程再按owner运维流程处理。
9. drill通过只证明artifact能走本机production restore。off-device来源、credential、JSONL/config和真实IM仍按
   B-013单独验收。

---

## Telegram 相关

### Bot 收不到消息
1. 检查 Bot Token 正确
2. 检查 Bot 已被加到群 / 已被私聊唤醒
3. 如使用 Webhook,检查域名可达
4. 切换到 long polling 模式排查

### Bot 发不出消息
1. 检查群是否开启了"禁止 Bot 发言"
2. 检查是否使用的是最新版本;当前长输出会自动拆成多条消息,旧版本可能因超过 4096 字符限制发送失败

### External dead-man receiver 报 runtime stale

1. 按 [`deploy/dead-man-receiver/README.md`](../../deploy/dead-man-receiver/README.md) 从独立 receiver 查询
   monitor,确认仍 armed、TTL 与 `AICO_RUNTIME_LIVENESS_TTL_SECONDS` 一致；不要先 disarm 消音。
2. 在 Mac 上运行 `uv run aico-service --repo . doctor`:若 launchctl/owner/heartbeat 已失败,按本机 service 故障处理。
3. 若 runtime 仍在但 `external liveness pulse degraded/failed`,只查脱敏异常类型并检查 HTTPS receiver/network；
   URL、token 和 runtime identity 不会出现在 heartbeat/doctor。
4. 重启成功会用新 `boot_id` 立即发送 sequence 1,receiver 应生成一次 resolved。若未恢复,核对 receiver 的
   idempotency、TTL 和 replacement-boot 排序实现。
5. monitor显示`alert_delivery_status=pending/failed`且reason=`alert_delivery_unhealthy`时，runtime/pulse可能仍可达；
   应检查独立runtime-alert endpoint及其ACK，不要通过disarm或重复restart掩盖。恢复alert sink后，下一份已ACK的
   `healthy` pulse才会续租并resolved；pending pulse失败重试期间payload冻结，状态传播存在有界延迟。
6. Mac sleep 或断网超过 TTL 默认就是 outage。永久卸载前必须在 receiver 显式 disarm；AICO 正常 stop 不会代办。
7. receiver 重启后应先用持久 SQLite 自动补判已过期 monitor并续投 pending event；若状态消失,先检查 `/data`
   volume/文件权限。incident alert URL 与 `AICO_RUNTIME_LIVENESS_WEBHOOK_URL` 必须指向各自 strict endpoint。
8. `/healthz` 200但 `/readyz` 503表示 HTTP process仍活着、SQLite或 expiry/delivery worker未 ready。不要把
   downstream pending/backoff误判成 worker death；检查脱敏 failure type日志和 volume权限,由 Compose restart policy
   处理持续三次内部失败或三个 sweep interval无成功进展的进程。
9. evidence verifier报 `pending delivery` 时,先等待 receiver outbox退避到期并确认owner sink恢复,再重新导出；
   不要手改JSON把 `delivered` 改成true。报 runtime/completed/schema错误时核对导出的monitor、完整outage数量和
   artifact是否被改动；strict路径还必须用owner-pinned公钥验证signed envelope，unsigned历史bundle不能commission。
10. 配置fallback后，primary失败但1-of-2仍delivered是预期failover；两route都会被尝试，但不会单独持久化route-level receipt。
    若策略为2-of-2，任一路失败都会保持pending并按stable event id重投。检查两URL确属不同HTTPS origin且token不复用；
    不要把不同域名直接写成不同云/账号/网络已证明，也不要通过降低quorum掩盖owner原本要求的双ACK策略。
11. receiver启动报notification policy conflict时，说明schema v3中仍有按旧策略冻结的pending event。恢复旧route/quorum并让
    exact event按原策略settle，再停止worker并修改配置；不要删outbox、改SQLite或用较低quorum强行启动。已delivered历史
    evidence保留旧策略是正常的。
12. main event显示delivered但`/v1/notification-routes`有degraded slot时，这是1-of-2部分成功，不是矛盾。检查尚存route是否收到
    `notification_route_degraded`；恢复失败provider后必须由下一次真实outage event ACK触发recovered，meta-alert自身不会递归
    证明route恢复。pending edge也会阻止策略切换。没有真实event时状态可能保持旧值，不能手改SQLite或宣称continuous healthy。
13. schema v5启用silent probe后，`unknown`且`consecutive_probe_failures=1`是confirmation window，delivery应为PENDING；达到阈值才
    degraded。若probe出现在老板终端，说明bridge不支持`silent-route-probe-v1`，立即改回disabled并按原配置drain pending，不能靠
    降低threshold掩盖。pending probe会冻结配置；HEAD成功、另一个probe URL或另一个token都不能证明真实通知链路。

---

## Adapter 相关

### Standing autonomy 没有执行或 doctor 失败

1. 先确认这是 scheduler 的 morning tick；手工 `/morning`、`/inbox`、`/proposals` 按设计不消费 grant。
2. grant path 必须绝对、文件必须当前用户所有、`0600`、非 symlink，且位于所有 managed project repo 外。
3. 替换全部 `replace-with-*`；expiry 必须含时区且尚未到期，`max_runs`/duration/`max_total_tokens`/
   `token_stop_threshold`必须在允许范围；旧schema-v1 grant会fail closed。
4. channel/target/thread/project 必须与 `AICO_MORNING_PUSH_*` 精确一致，charter id 必须存在。
5. charter role 必须任命给真正的 `codex` executable，并配置可构建的bounded `evidence_sources`；Claude/Cursor/包装脚本即使
   声称只读也会 fail closed。
6. 查 `/proposals` 和 task/audit history：同 `grant_id` 的 preauthorized decision 数已达到 `max_runs` 时只会返回
   `run budget exhausted`，编辑同一 grant 不会重置预算。
7. timeout 会先扣预算再 interrupt；不要通过放大 duration 或换 grant id 隐藏失败，先查 bounded output/Adapter health。
8. 错误信息不会显示 owner id 或 grant path。需要确认具体文件时由 owner 在本机核对，不要把 grant 内容贴进 IM。
9. 文件权限/JSON通过但显示`runtime binding is invalid`时，依次核对repo-relative project/persona config、charter
   appointment、`AICO_ENABLE_CODEX_ADAPTER=true`和Codex command首个executable。不要用wrapper冒充`codex`。
10. 只有`owner-bound runtime binding verified`表示install前静态绑定已通过；它仍不证明Codex登录、定时触发或IM送达。
11. receipt为`evidence_missing`时，说明preauthorized proposal已accepted，但task id/snapshot或proposal/grant metadata
    不匹配。先用`/proposals`、`/tasks`、`/audit`核对crash window；由于provider成本未知，不自动返还预算或重跑。
12. receipt为`failed`且provider正文看似正常时，确认已包含Round 215修复；旧版可能把standing输出误套overnight
    handoff grader。升级后普通只读输出应保持`done`，timeout才显示`interrupted`。
13. terminal receipt没有`tokens=N`或显示`evidence_missing`时，说明Codex JSONL没有给出有效`turn.completed.usage`，
    或provider完成后在proposal持久化前崩溃。后续run会fail closed；不要把missing按0处理。
14. `observed token threshold reached`表示此前同grant累计实测量已达阈值。该阈值在run之间检查，当前run可能越界；
    如业务要求单次硬成本上限，必须改用provider原生pre-run/max-token/spend contract，不能放大本地文案。
15. complete receipt显示`evidence=drifted`时，说明至少一个bounded source文件的size或full-file SHA-256已变化；
    `evidence=missing`表示repo root、文件或legacy manifest缺失。先由owner检查仓库变更和引用语义，再进行新的人工验收。
    不要编辑旧proposal、从IM索要path/hash、自动重跑或把hash当签名。

### Claude Code Adapter 无响应
1. 检查 `claude` 命令在终端能跑
2. 检查 Adapter 配置的路径正确
3. 检查 Adapter 进程未卡死(`ps aux | grep claude`)

### Adapter 输出乱码
- 检查环境变量 `LANG=zh_CN.UTF-8` 或 `LC_ALL=en_US.UTF-8`
- 检查 stdin/stdout 编码

### 长任务没有 Telegram 结果
1. `/status` 看 Adapter 是否 `busy`。
2. `tail -f logs/aico.log` 看是否有 `Adapter process starting` 和 `Adapter process exited`。
3. 如果有 `Adapter busy`,说明当前 Claude/Codex Adapter 执行槽位已被占用,等待旧任务结束或重启进程。
4. 如果有 `Adapter process starting` 但长期没有 `Stream output`,说明 CLI 没有产生 stdout chunk 或还没结束。
5. 如果有 `Stream message split` 但 Telegram 没收到后续消息,检查 `Telegram sendMessage` / `editMessageText` 附近是否有异常。

### 只收到回复开头一句
1. 先确认服务已包含 Round 27 修复。
2. `grep -n "message is not modified\\|Telegram incoming message handler failed" logs/aico.log`。
3. 如果只看到 `Telegram editMessageText ignored no-op`,这是正常的可恢复 no-op。
4. 如果仍看到 `Telegram incoming message handler failed`,继续看同一段日志里的 Telegram `description`,区分 chat 权限、消息长度、网络等真实错误。

---

## 性能相关

### Standing task 显示 done，但 outcome 不是 complete

`done`只表示TaskBus transport结束。`outcome=missing`表示没有持久结果证据，`invalid`表示JSON/charter coverage/
source location或状态一致性失败，`blocked`表示provider明确留下未满足验收项。三者都会阻止下一次scheduled run。
先看`/task <id>`、`/proposals`与audit，核对当前Codex是否支持配置的output schema，并人工检查repository-relative
file/line内容；不要删除历史proposal、换grant或自动重跑。source存在不代表业务语义正确。

`result_too_large`表示最终结果超过32K；`result_schema_invalid`表示duplicate key、字段长度/数量或schema形状不符。
两者都只留下bounded receipt，不保存raw正文。先缩小charter或修provider/schema兼容；不要把result envelope调成
无限，也不要将它误认为provider生成阶段的token上限。

### 任务响应慢
1. 看是哪一步慢:接收 → 派发 → AI 处理 → 输出 → 推送
2. 查 P99 延迟指标
3. 大概率是 AI 本身慢,不是编排层

### 内存占用高
1. 看是不是 token 历史没清理
2. 看是不是 stream 没正确关闭
3. 看是不是事件总线消费不及时堆积

---

## 数据相关

### 任务历史丢失
- 检查持久化后端是否正常
- 检查数据库文件路径
- Phase 1-2 用 SQLite 时:`.db` 文件别误删

### Persona 配置丢失
- 备份策略见 [`daily-ops.md`](daily-ops.md)
- Persona 配置应在 git 中(YAML),不要只存数据库

---

## 已修复历史问题(归档)

### Telegram 长文本只收到一部分

原因通常是旧版本把所有流式输出编辑到同一条消息里,超过 Telegram 4096 字符限制后 Bot API 请求失败。当前版本已在核心流式输出层按安全长度拆分为多条消息。

### Telegram 回复停在第一句

原因可能是旧版本在流式编辑过程中遇到 Telegram `Bad Request: message is not modified`。这类 no-op edit 已在当前版本中忽略,不会再中断后续输出。

---

## 还没修复的已知问题

参见 [`docs/journal/BLOCKERS.md`](../journal/BLOCKERS.md)。

---

## 我遇到了一个新问题

1. 先在本文 grep 关键词
2. 再到 [`PITFALLS.md`](../journal/PITFALLS.md) grep
3. 都没有 → 这是新问题:
   - 解决了:把它加到本文 + PITFALLS
   - 没解决:写到 BLOCKERS,等下一轮
