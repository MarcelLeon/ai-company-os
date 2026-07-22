# PITFALLS.md — 踩坑录

> 本项目踩过的所有坑。**踩同一个坑两次是不可接受的**。
>
> 每个坑必须有:简短标题、症状、根因、解决方案、状态、相关文件。
>
> Agent 接手任何任务前,先 grep 这里看相关关键词。

---

## 状态图例

- 🔴 **OPEN** — 已知问题,尚未解决
- 🟡 **MITIGATED** — 已绕过/缓解,根因未除
- 🟢 **RESOLVED** — 已彻底解决
- ⚫ **WONT_FIX** — 决定不修(留作记录)

---

## 索引(按主题分类)

### 文档与流程
- (待填充)

### 技术栈
- P-040:本机 dogfood `AICO_*` 环境变量污染单测

### Adapter 层
- (待填充)
- P-026:非交互 CLI 子进程继承 stdin 导致 Codex 长期等待额外输入
- P-027:CLI 子进程 stderr 不读取导致 Codex stdout 被 pipe 反压卡住

### IM 通道
- P-006:审批命令依赖完整 task id 导致 Telegram 真实交互失败
- P-007:远程审批通过后仍触发底层 CLI 权限或沙箱失败
- P-008:Telegram polling await 长任务 handler 导致 `/status` / `/audit` 卡住
- P-010:Telegram 单条消息长度上限导致长输出像被吞掉
- P-011:后台缺少关键链路日志导致长任务卡点不可定位
- P-012:Telegram no-op edit 400 导致流式 handler 中断
- P-030:Renderer 只逐行加 spans 无法处理真实 agent Markdown
- P-031:无限扩 Markdown 兼容 case 会让 IM 输出层失控
- P-032:quiet heartbeat 进入结果缓冲导致 native HTML 回退裸露
- P-036:Agent native heading / bullet 被流式拼接后糊成 Telegram 一整段
- P-037:Telegram API 上限不是老板手机阅读上限
- P-042:真实 Telegram 链路跑通但老板可读性仍失败
- P-047:native `<pre>` 包 Markdown 表格会绕过紧凑表格 renderer
- P-049:紧凑表格的连续 code 行必须合并成单个 Telegram `<pre>`

### AI 间协作
- P-009:协作指令只支持冒号导致真实自然语言未触发 reviewer
- P-014:Reviewer 子任务已 accepted 但 Codex CLI 长时间无 stdout 且 IM 无中断入口
- P-025:长沉默 Adapter 任务被误判为 IM 挂死
- P-024:协作短指令引用父输出编号但 child task 丢失上下文
- P-034:协作 parent context 被风险识别扫描导致只读 reviewer 子任务误判为 shell_exec

### 人格化与状态
- P-013:Project Team 同一 role 可出现多个 appointment 导致 `/team` 重复成员
- P-016:Appointment prompt 脚手架导致普通项目咨询误触发审批
- P-035:CLI exit 0 的短输出被 `/overnight` 误当作可交接成功

### 部署与运维
- P-017:真实 Stage 3 录屏被底层 CLI 噪音污染
- P-018:httpx INFO 日志会把 Telegram Bot token 打进日志
- P-061:Generic health failure 不能直接驱动无人值守重启
- P-062:Heartbeat 直发 webhook 不是可靠的缺席告警
- P-095:Process alive 与 dead-man pulse fresh 不能证明 required 业务组件仍可用

### Java / Spring AI 相关
- (待填充)

### Python 相关
- P-003:本机默认 Python / uv 缓存与项目基线不一致
- P-004:`uv run` 本地 console script 触发构建依赖下载

### 持久化与 schema 兼容
- P-033:Memory/Audit JSONL 升级是单向门(`FrozenModel.extra="forbid"`)
- P-045:Dream 候选经验不能被当成普通 shared memory 或 `/remember` 流程

### Adapter 层
- P-005:Codex CLI 全局参数必须放在子命令前
- P-015:Trae CLI help 先尝试 keyring token store 导致误判为不可用

---

## 详细坑位记录

> 模板:
>
> ```markdown
> ### [P-XXX] 简短标题
>
> **状态**:🔴 OPEN / 🟡 MITIGATED / 🟢 RESOLVED / ⚫ WONT_FIX
> **首次踩中**:Round N
> **最后更新**:YYYY-MM-DD
> **影响范围**:`path/to/affected/files`
>
> **症状**
> 具体出现了什么现象、报错。
>
> **根因**
> 为什么会发生这个问题。
>
> **解决方案 / 缓解措施**
> 具体怎么处理的。代码示例放这里。
>
> **如何避免再次踩中**
> 给后人的具体可执行建议。
>
> **相关链接**
> - ROUNDS Round N
> - ADR-XXX
> - PR #YY
> ```

---

### P-001(示例) 抽象过早,Adapter 接口频繁返工

**状态**:🟢 RESOLVED(示例,演示用)
**首次踩中**:Round 0(示例)
**最后更新**:2026-04-26
**影响范围**:`docs/agent/03-design-patterns.md`(预防性记录)

**症状**
(示例)在没接入第二个 AI 之前就过早设计了大而全的 `AIAdapter` 抽象接口,接入第二个 AI 时发现 1/3 的接口方法用不上,1/3 需要改签名。

**根因**
(示例)违反 Rule of Three,在仅 1 个实现样本时就抽象。

**解决方案 / 缓解措施**
(示例)在 [`docs/agent/03-design-patterns.md`](../agent/03-design-patterns.md) 写明"抽象时机判定"硬规则:第 3 次出现相似代码时再抽象,第 1、2 次直接复制粘贴。

**如何避免再次踩中**
- PR 中抽象层超过 3 个接口方法的,review 时必须问"现在有几个实现样本"
- 接 Adapter 时按"先复制 Claude Code Adapter,改成 Codex Adapter"的方式做,不要一开始就大重构

**相关链接**
- (本条为示例条目,实际触发后填充真实链接)

---

<!-- 真实坑位从下方追加。每个新坑单独一条。 -->

### [P-002] 文档文件被扁平化导致 AGENTS 路径失效

**状态**:🟢 RESOLVED
**首次踩中**:Round 2
**最后更新**:2026-04-27
**影响范围**:`AGENTS.md`, `README.md`, `STATUS.md`, `docs/`

**症状**
`AGENTS.md` 要求读取 `docs/journal/ROUNDS.md`、`docs/agent/01-development-workflow.md` 等路径,但实际文件曾经全部堆在仓库根目录。Agent 按强制阅读路径执行时会找不到文档,只能靠猜测同名根目录文件。

**根因**
Round 1 设计的是 `docs/agent` / `docs/journal` / `docs/architecture` / `docs/human` 分层目录,但落盘或拷贝过程中只保留了扁平文件结构,导致文档契约和文件系统不一致。

**解决方案 / 缓解措施**
Round 2 已将文档归位:
- Agent 指南移动到 `docs/agent/`
- journal 三件套移动到 `docs/journal/`
- 架构文档移动到 `docs/architecture/`
- 人类操作文档移动到 `docs/human/`
- 补回 `docs/decisions/README.md` 和 `docs/playbooks/README.md`

**如何避免再次踩中**
- 新增文档时先确认它属于哪个目录,不要直接丢到根目录。
- 修改 `AGENTS.md` 或 `README.md` 的路径后,用 Markdown 链接检查脚本验证断链。
- 根目录只保留入口级文档:`README.md`、`AGENTS.md`、`NORTH_STAR.md`、`STATUS.md`、`CONTRIBUTING.md`、`CHANGELOG.md`。

**相关链接**
- ROUNDS Round 2

### [P-003] 本机默认 Python / uv 缓存与项目基线不一致

**状态**:🟡 MITIGATED
**首次踩中**:Round 3
**最后更新**:2026-04-27
**影响范围**:`pyproject.toml`, `uv.lock`, 本地验证命令

**症状**
本机默认 `python3` 是 3.9.6,不满足 ADR-0001 的 Python 3.11+ 基线。第一次在沙箱里跑 `uv run` 时还会尝试初始化 `/Users/wangzq/.cache/uv`,可能因为沙箱权限报 `Operation not permitted`。首次安装依赖还需要访问 PyPI,网络受限时会出现 DNS 失败。

**根因**
macOS 系统 Python 版本低于项目基线,而 `uv` 默认缓存目录位于用户 home 下,不一定在当前沙箱可写范围内。新项目第一次解析依赖也不可避免需要拉包。

**解决方案 / 缓解措施**
本轮实际验证使用:

```bash
uv run --python /opt/homebrew/bin/python3.11 pytest
uv run --python /opt/homebrew/bin/python3.11 ruff check .
uv run --python /opt/homebrew/bin/python3.11 ruff format --check .
uv run --python /opt/homebrew/bin/python3.11 mypy src tests
```

如果沙箱拒绝访问默认 uv cache,先临时指定可写缓存:

```bash
env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python /opt/homebrew/bin/python3.11 pytest
```

如果依赖尚未缓存且网络受限,需要请求允许 `uv run` 联网下载依赖。

**如何避免再次踩中**
- 不要用裸 `python3` 运行项目检查,显式使用 `/opt/homebrew/bin/python3.11` 或让 `uv` 管理 3.11 环境。
- 新机器第一次跑检查时预期会生成 `.venv` 和 `uv.lock`; `.venv` 已被 `.gitignore` 忽略,`uv.lock` 应提交。
- 沙箱环境优先使用 `/tmp/aico-uv-cache` 作为临时 cache。

**相关链接**
- ROUNDS Round 3
- ADR-0001

### [P-004] `uv run` 本地 console script 触发构建依赖下载

**状态**:🟡 MITIGATED
**首次踩中**:Round 6
**最后更新**:2026-04-27
**影响范围**:`pyproject.toml`, `uv.lock`, `.venv`, 本地验证命令

**症状**
新增 `[project.scripts]` 后运行 `uv run --python /opt/homebrew/bin/python3.11 pytest` 会先尝试构建本地包 `aico`。沙箱网络受限且 `hatchling` 不在缓存中时,命令报错:

```text
Failed to resolve requirements from build-system.requires
Failed to fetch: https://pypi.org/simple/hatchling/
```

**根因**
`aico-phase1` console script 需要将当前项目作为包安装到 `.venv`;安装项目时 `uv` 会按 `build-system.requires` 拉取 `hatchling`。这不是测试失败,而是构建后端依赖首次下载失败。

**解决方案 / 缓解措施**
本轮通过允许 `uv run` 联网下载缺失构建依赖后恢复。依赖进入 `/tmp/aico-uv-cache` 和 `.venv` 后,后续 `pytest` / `ruff` / `mypy` 均可正常运行。

**如何避免再次踩中**
- 新增或修改 `[project.scripts]` 后,预期第一次 `uv run` 可能需要构建本地包。
- 如果看到 `hatchling` 下载失败,不要误判为代码问题;按权限流程允许 `uv run` 联网一次。
- 继续显式使用 `UV_CACHE_DIR=/tmp/aico-uv-cache`,避免默认 home cache 权限问题和重复下载。

**相关链接**
- ROUNDS Round 6
- P-003

### [P-005] Codex CLI 全局参数必须放在子命令前

**状态**:🟢 RESOLVED
**首次踩中**:Round 9
**最后更新**:2026-04-28
**影响范围**:`src/aico/adapter/codex.py`, `src/aico/app/phase1.py`

**症状**
用户在 Telegram 中发送 `@codex summarize this repo in one sentence` 后,Codex Adapter 返回:

```text
error unexpected argument '--ask-for-approval' found
```

**根因**
`--ask-for-approval` 是 Codex CLI 顶层参数,不是 `codex exec` 子命令参数。错误命令形态是:

```bash
codex exec --sandbox read-only --ask-for-approval never --color never "hello"
```

Codex CLI 会把 `--ask-for-approval` 当成 `exec` 子命令参数解析,因此报 unexpected argument。

**解决方案 / 缓解措施**
将默认命令改为把全局参数放在子命令前:

```bash
codex --ask-for-approval never exec --sandbox read-only --color never "hello"
```

本轮用 `codex --ask-for-approval never exec --help` 验证新形态可被 CLI 接受。

**如何避免再次踩中**
- 修改 Codex Adapter 默认命令时,先跑 `codex <global-options> exec --help`。
- 区分 Codex 顶层参数和 `exec` 子命令参数:`--ask-for-approval` 是顶层参数,`--sandbox` / `--color` 是 `exec` 参数。
- 在文档中给出的 smoke test 命令必须使用正确顺序。

**相关链接**
- ROUNDS Round 9

### [P-015] Trae CLI help 先尝试 keyring token store 导致误判为不可用

**状态**:🟡 MITIGATED
**首次踩中**:Round 67
**最后更新**:2026-05-12
**影响范围**:`src/aico/adapter/trae.py`, `docs/playbooks/optional-agent-adapters.md`

**症状**
本机执行 `trae-cli --help` 时先输出:

```text
ERROR failed to create token store error="keyring is not supported on this system"
```

随后仍继续输出完整 help,包含 `--print`、`--yolo`、`--session-id`、`--resume` 等参数。

**根因**
Trae CLI 启动时会初始化 token store / keyring。当前运行环境不支持该 keyring 后端,但 help 命令仍可继续执行并返回 CLI 形态信息。

**解决方案 / 缓解措施**
Round 67 没把这个错误当作 CLI 不存在或参数不可用;仍以 help 后续输出作为命令形态依据。真实 smoke test 前需要单独解决 Trae 登录/token 配置问题。

**如何避免再次踩中**
- 看到该 keyring 错误时,先确认命令是否继续输出 help 和退出码,不要直接判定 `trae-cli` 不可用。
- Trae 真实验收前先处理登录/token store,再启用 `AICO_ENABLE_TRAE_ADAPTER=true`。
- 如果真实任务仍因 keyring 失败退出,只修 Trae Adapter 命令或运行环境,不要改核心 `AIAdapter` 协议。

**相关链接**
- ROUNDS Round 67
- ADR-0018

### [P-006] 审批命令依赖完整 task id 导致 Telegram 真实交互失败

**状态**:🟢 RESOLVED
**首次踩中**:Round 15
**最后更新**:2026-04-28
**影响范围**:`src/aico/core/task_bus.py`, `src/aico/core/orchestrator.py`

**症状**
人类在 Telegram 中批准 Claude 写文件任务时收到:

```text
Task rejected: unknown pending approval
```

同时真实 Telegram 对话中完整 task id 不易查看和复制,导致 `/approve <task_id>` 的交互很脆。

**根因**
Round 13 的审批命令完全依赖完整 task id。真实 IM 场景里用户更自然地发送 `/approve`,或只能看到/输入短 ID。一旦 task id 缺失、复制不完整或输错,`TaskBus` 就找不到 pending approval。

**解决方案 / 缓解措施**
- `TaskBus.approve()` / `reject_approval()` 支持 `None` task id:当只有一个待审批任务时直接处理它。
- 支持 task id 前缀匹配,Telegram 提示只展示短 ID。
- 如果存在多个待审批任务且用户未指定 ID,返回短 ID 列表。

**如何避免再次踩中**
- 面向 IM 的命令不要要求用户复制长 UUID。
- 需要引用任务时优先支持“唯一待处理对象”快捷操作和短 ID。
- Playbook 必须按真实聊天体验写,不要只按 CLI 思维写命令。

**相关链接**
- ROUNDS Round 15

### [P-007] 远程审批通过后仍触发底层 CLI 权限或沙箱失败

**状态**:🟢 RESOLVED
**首次踩中**:Round 17
**最后更新**:2026-04-28
**影响范围**:`src/aico/adapter/claude_code.py`, `src/aico/core/task_bus.py`, `src/aico/core/risk_capability.py`

**症状**
真实 Telegram smoke test 中出现两类问题:

```text
当前环境是 read-only 沙箱，且不允许申请写权限
```

以及 `/claude` 写文件任务在 Telegram `/approve` 后,Claude Code 仍提示需要本机授权写权限,用户不知道该在电脑哪里授权。

**根因**
AICO 的 `/approve` 只表达“远程人类批准这个危险任务”,但 Round 16 之前没有处理两个额外边界:
- read-only Adapter(如 Codex reviewer)没有写入能力,即使批准也无法执行写任务。
- Claude Code CLI 自己还有权限系统;非交互 `-p` 模式下的本机授权提示不会自然转发到 Telegram。

**解决方案 / 缓解措施**
- 新增 Adapter 能力门禁:危险任务在进入审批前先确认 Adapter 是否具备对应能力。Codex 这类 read-only Adapter 遇到写文件 / shell / destructive 任务会直接拒绝并提示使用 `/claude`。
- Claude Code 默认命令改为:

```bash
claude -p --output-format text --permission-mode bypassPermissions
```

远程场景由 AICO `/approve` 作为唯一审批门,避免底层 CLI 再要求本机授权。

**如何避免再次踩中**
- 不要把“人批准了”当作“Adapter 一定能做”;派发前必须校验 Adapter capability。
- 远程 IM 入口不能依赖 TTY / 本机弹窗 / CLI 原生交互审批。
- read-only Adapter 的危险任务应在核心层返回清晰拒绝,不要等 CLI 报底层沙箱错误。

**相关链接**
- ROUNDS Round 17
- ADR-0007

### [P-008] Telegram polling await 长任务 handler 导致 `/status` / `/audit` 卡住

**状态**:🟢 RESOLVED
**首次踩中**:Round 20
**最后更新**:2026-04-28
**影响范围**:`src/aico/channel/telegram.py`

**症状**
人类在 Telegram 中让 Claude 执行长任务时,再输入 `/status` 或 `/audit` 会卡住,直到 Claude 当前任务结束才响应。

**根因**
`TelegramChannel.poll_once()` 在处理每条 update 时直接 `await self._handler(message)`。而 `Orchestrator.handle_incoming()` 对普通任务会一直 await Adapter 输出流,导致 long polling 循环无法继续处理后续 Telegram update。

**解决方案 / 缓解措施**
`TelegramChannel` 改为为每条 incoming message 创建后台 handler task,并在 `stop()` 时取消仍在运行的 handler。这样 polling 可以继续接收 `/status` / `/audit` 等轻量命令。

**如何避免再次踩中**
- Channel 层不要直接 await 可能长时间运行的业务 handler。
- 长任务流式处理应在后台 task 中运行,Channel polling/webhook 入口只负责快速接收和分发。
- 新增 Channel 时必须测试“长 handler 运行时仍可处理下一条 update”。

**相关链接**
- ROUNDS Round 20

### [P-009] 协作指令只支持冒号导致真实自然语言未触发 reviewer

**状态**:🟢 RESOLVED
**首次踩中**:Round 20
**最后更新**:2026-04-28
**影响范围**:`src/aico/core/collaboration.py`

**症状**
人类在 Telegram 中发送:

```text
@claude 请简要分一下当前仓库phase 5的协作方案，然后输出一行 @reviewer review一下phase 5有什么风险和问题
```

Claude 返回了“Phase 5 协作方案简析”,但没有触发 Codex/reviewer 子任务。

**根因**
Round 19 的协作解析只识别行首 `@reviewer: ...`,真实自然语言里更容易写成 `@reviewer review一下...`。没有冒号时,协作指令被当成普通文本。

**解决方案 / 缓解措施**
`parse_collaboration_directive()` 同时支持:
- `@reviewer: inspect this`
- `@reviewer inspect this`

仍要求指令出现在非空行行首,避免普通正文中的 `@reviewer` 误触发。

**如何避免再次踩中**
- 面向 IM 的触发语法要兼容真实聊天习惯,不能只按程序员 DSL 设计。
- Playbook 示例要覆盖冒号和空格两种写法。

**相关链接**
- ROUNDS Round 20

### [P-010] Telegram 单条消息长度上限导致长输出像被吞掉

**状态**:🟢 RESOLVED
**首次踩中**:Round 21
**最后更新**:2026-04-28
**影响范围**:`src/aico/core/orchestrator.py`, `src/aico/core/streaming.py`

**症状**
人类在 Telegram 中让 AI 返回较长文本时,只能收到前半段或部分信息,看起来像 Codex / Claude 把消息吞掉。

**根因**
`Orchestrator` 原本把所有流式 chunk 拼成一条字符串,并持续调用 `editMessageText` 刷新同一条 Telegram 消息。Telegram Bot API 文本消息有 4096 字符限制;内容超过限制后,编辑请求会失败,handler 可能被打断,后续输出无法继续推送。

**解决方案 / 缓解措施**
新增 `StreamedMessageWriter`,使用 3900 字符的保守上限。当前消息装满后,继续用 `sendMessage` 发送下一段,并在新消息上继续流式追加,保证每次发送 / 编辑都低于安全长度。

**如何避免再次踩中**
- 所有 IM 输出都不能假设“无限长文本可以编辑在同一条消息里”。
- 新增 Channel 或富文本格式时,先确认平台单条消息上限,再决定分片策略。
- 长输出测试必须覆盖超过单条消息上限的场景。

**相关链接**
- ROUNDS Round 21

### [P-011] 后台缺少关键链路日志导致长任务卡点不可定位

**状态**:🟢 RESOLVED
**首次踩中**:Round 23
**最后更新**:2026-04-29
**影响范围**:`src/aico/app/phase1.py`, `src/aico/channel/telegram.py`, `src/aico/core/orchestrator.py`, `src/aico/adapter/claude_code.py`, `src/aico/core/streaming.py`

**症状**
人类发送长文本任务后 Telegram 没收到结果,只能猜是 Claude 卡住、Adapter busy、Telegram 发送失败,还是长文本分片仍有问题。

**根因**
此前只有少量异常日志,缺少“入站消息 → 路由 → Adapter ack → CLI 进程 → stdout chunk → Telegram send/edit → 分片”这条主链路的后台日志。

**解决方案 / 缓解措施**
- `aico-phase1` 默认写 `logs/aico.log`,可用 `AICO_LOG_PATH` 覆盖或置空关闭文件日志。
- 新增 `AICO_LOG_LEVEL`,默认 `INFO`。
- 在 Telegram Channel、Orchestrator、Claude/Codex Adapter 和流式分片器记录关键节点,只记录 task id、长度、状态、退出码等元信息,不打印完整 prompt。

**如何避免再次踩中**
- 新增远程长任务链路时,必须同时记录开始、ack、输出、结束和错误。
- 日志不要打印完整用户 prompt,只打印长度和可追踪 id。
- 排查“没收到结果”时先 `tail -f logs/aico.log`,再看 `/status` 和 `/audit`。

**相关链接**
- ROUNDS Round 23

### [P-012] Telegram no-op edit 400 导致流式 handler 中断

**状态**:🟢 RESOLVED
**首次踩中**:Round 27
**最后更新**:2026-04-29
**影响范围**:`src/aico/channel/telegram.py`, `src/aico/core/streaming.py`

**症状**
人类在 Telegram 中询问 Claude 有什么技能时,只收到开头一句“作为 implementer 角色...”后后续消失;执行 `/codex inspect this` 后也表现为长时间卡住,后续 Codex 请求返回 `Adapter busy`。

**根因**
流式输出会频繁调用 Telegram `editMessageText`。当某个 chunk 只带来 Telegram 视觉上无变化的内容,例如尾部空白或换行归一化后内容相同,Telegram 会返回 HTTP 400 `Bad Request: message is not modified`。旧实现先 `raise_for_status()`,没有解析 Telegram JSON `description`;异常冒泡后 handler 中断,后续 stdout 虽然还在产生,但不再推送到 Telegram。Codex 任务则因为底层进程仍在运行,表现为 Adapter 单槽位被占用。

**解决方案 / 缓解措施**
- Telegram `_post()` 先解析 Bot API JSON body,保留 `description`,再按 `ok` 判断业务错误。
- `edit_message()` 对 `message is not modified` 做 no-op 处理并记录日志,不再中断流式 handler。
- 非 no-op Telegram 错误仍继续抛出,避免真正的权限、chat id、网络问题被吞掉。

**如何避免再次踩中**
- Telegram HTTP 400 不等于一定是传输层错误,必须优先看 Bot API 的 JSON `description`。
- 流式编辑同一条消息时,要把平台的幂等/no-op 错误视为可恢复。
- 排查“只收到开头一句”时,优先 grep `editMessageText`、`message is not modified` 和 `Telegram incoming message handler failed`。

**相关链接**
- ROUNDS Round 27

### [P-013] Project Team 同一 role 可出现多个 appointment 导致 `/team` 重复成员

**状态**:🟢 RESOLVED
**首次踩中**:Round 46
**最后更新**:2026-05-05
**影响范围**:`src/aico/core/project_assignment.py`, `src/aico/core/project_messages.py`

**症状**
人类在 Telegram 中多次执行 `/appoint claude as tester read_repo run_tests` 后,`/team`
输出可能出现多个 `tester -> claude` 行。老板视角下一个项目里的一个 role 只需要一个负责人,
重复显示会让“谁负责测试”变得不可信。

**根因**
Project appointment 的底层存储按 `seat` 唯一,但产品语义真正需要按 `project + role`
唯一。只按 `seat` 存储时,历史配置或进程内状态一旦出现同 role 多个 seat,`/team`
会把它们全部渲染出来。

**解决方案 / 缓解措施**
`ProjectAssignmentDirectory` 新增唯一存储路径,写入 appointment 时会先移除同一
`project + role` 的旧 appointment,再保留新的负责人。初始化配置时如果遇到重复 role,
也按最后一个 appointment 生效。`/team` 同时展示当前 lead,避免老板还要从别的命令推断。

**如何避免再次踩中**
- Project Team 的任命语义以 `project + role` 为唯一键,不要把内部 `seat` 当成用户可感知的唯一负责人。
- 新增任何任命写入入口时,必须复用 `ProjectAssignmentDirectory` 的 upsert / remove 方法。
- Telegram 验收里重复执行同一条 `/appoint ... as <role>` 后,必须复查 `/team` 只出现一个 role 行。

**相关链接**
- ROUNDS Round 46

### [P-014] Reviewer 子任务已 accepted 但 Codex CLI 长时间无 stdout 且 IM 无中断入口

**状态**:🟢 RESOLVED
**首次踩中**:Round 53
**最后更新**:2026-05-25
**影响范围**:`src/aico/core/commands.py`, `src/aico/core/orchestrator.py`, `src/aico/core/task_bus.py`, `src/aico/adapter/claude_code.py`, `src/aico/adapter/codex.py`, `src/aico/app/phase1.py`

**症状**
Phase 5 真实协作 smoke test 中,Telegram 能收到:

```text
Collaboration requested: claude -> reviewer
Task accepted: 31e559c3-bd7c-4e1b-9385-024431f8635a [reviewer]
```

但之后长时间没有 reviewer 输出。日志显示 reviewer 子任务已派发到 `codex`,并停在 `Stream start`;
进程表能看到 Codex CLI 子进程仍在运行,但没有 stdout chunk。

**根因**
协作链路已成功创建 reviewer 子任务,真正卡点是底层 Codex CLI 长时间运行且未产出 stdout。
AICO 的 Adapter 和 TaskBus 其实已经支持 interrupt,但 IM 命令层没有暴露 `/interrupt`,
导致远程用户只能等待或回到机器上手动杀进程。这个体验违反北极星第三句的“可中断”。

Round 57 真实复测再次卡在 `Task accepted ... [reviewer]`,此时 `/interrupt` 已可用,
进一步确认还缺 Adapter 侧自动释放 busy 的输出空闲超时。

**解决方案 / 缓解措施**
- 新增 `/interrupt <task_id>` 命令。
- `TaskBus.interrupt()` 支持 task id 前缀匹配,和 `/approve <short_id>` 一样适配 IM 输入。
- 中断 running 任务后任务状态更新为 `interrupted`,并记录 `task_interrupted` 审计事件。
- Phase 5 collaboration playbook 增加卡在 `Task accepted ... [reviewer]` 时的排查和中断步骤。
- Codex Adapter 默认启用输出空闲超时。Round 57 首版阈值为 90 秒;Round 98 放宽到 300 秒;
  Round 114 进一步放宽到 1800 秒,避免把正常长 review / dogfooding 误杀。
- 可通过 `AICO_CODEX_OUTPUT_IDLE_TIMEOUT_SECONDS` 调整 Codex 空闲超时阈值;设为 `0` 可禁用自动 idle timeout。

**如何避免再次踩中**
- 真实 smoke test 如果停在 `Task accepted` 后无输出,先查 `/status`,再用 `/interrupt <short_task_id>`。
- 重启到 Round 114 之后,如果忘记手动 interrupt,Codex 默认会在 1800 秒空闲超时后自动失败并释放并发槽位;若启动时把 timeout 设为 `0`,需要靠 `/interrupt` 或进程重启收口。
- 新增任何长任务入口时,必须确认 IM 侧有中断路径,不能只在 Adapter 接口里有 interrupt。
- 排查 Codex 卡住时,优先 grep task id,看是否有 `Stream output` 或 `Adapter process exited`。

**相关链接**
- ROUNDS Round 53
- ROUNDS Round 98
- ROUNDS Round 57

### [P-025] 长沉默 Adapter 任务被误判为 IM 挂死

**状态**:🟡 MITIGATED
**首次踩中**:Round 115
**最后更新**:2026-05-26
**影响范围**:`src/aico/adapter/claude_code.py`, `src/aico/core/orchestrator.py`, `src/aico/core/task_bus.py`, `src/aico/core/inbox.py`

**症状**
真实 IM 中提交 reviewer 长任务后,Telegram 只看到任务 accepted / running。日志显示 task `01ddaa36` 已被 Codex 接收、进程已启动并进入 `Stream start`,但 14 分钟以上没有 stdout chunk,也没有退出事件。用户视角无法区分“任务真的在跑”“IM handler 挂住”还是“路由没提交出去”。

**根因**
Adapter 流式读取只在 stdout 产生一行时才向上游 yield。Round 114 把 no-output idle timeout 放宽到 1800 秒后,避免了 5 分钟误杀,但也暴露出一个新缺口:长时间静默 provider 会让 IM 没有中间状态。Absence-first 场景下,老板离开电脑后不能靠猜测判断任务是否还活着。

**解决方案 / 缓解措施**
- `ClaudeCodeAdapter` 家族新增 quiet heartbeat:进程仍存活但长时间没有 stdout 时,周期性产出 `OutputType.STATUS`。
- `TaskBus` 收到 `OutputType.STATUS` 后保持 task `running`,并把 status 写入 running reason。
- `Orchestrator` 会把 status 推到 IM,但不会把它写入普通任务结果、lead decision memo 或 Goal Brief captured output。
- 新增 `/inbox` 当前项目入口,集中展示 running 静默任务、待审批、失败/中断、离线托管和决策/目标 follow-up。

**如何避免再次踩中**
- 看到 `Task accepted` 后长时间无输出,先查 `/inbox` 或 `/task <id>`;如果出现 `Still running...`,说明是 provider 静默而不是 IM 提交失败。
- 不要靠缩短 no-output timeout 来解决可见性问题;长任务应该可观察、可中断,而不是被过早误杀。
- 新增任何长任务 Adapter 时,必须确认静默状态不会污染最终任务结果,也不会绕过 `/interrupt` 和 idle timeout。

**相关链接**
- ROUNDS Round 115

### [P-026] 非交互 CLI 子进程继承 stdin 导致 Codex 长期等待额外输入

**状态**:🟢 RESOLVED
**首次踩中**:Round 116
**最后更新**:2026-05-26
**影响范围**:`src/aico/adapter/claude_code.py`, `tests/unit/test_claude_code_adapter.py`

**症状**
Round 115 quiet heartbeat 生效后,真实 IM 中 reviewer/Codex 任务持续显示:

```text
Still running: no adapter output for 120s...
...
Still running: no adapter output for 1680s...
```

日志显示 task `0e72ac63` 已被 Codex adapter 接收并进入 `Stream start`,但没有任何 `type=text` 输出。状态库中任务 payload 约 1996 字符,不是异常巨大的 prompt。

**根因**
`create_subprocess_exec()` 启动 CLI adapter 时没有显式设置 `stdin`,导致子进程继承 AICO 进程的 stdin。Codex 0.125 在 `exec` 模式会尝试读取 stdin 作为 additional input;如果继承到一个不会立刻 EOF 的 stdin,就会一直等待额外输入,从而没有 stdout。最小 Codex smoke 在相同用户权限下可正常返回,说明不是账号、网络或 Codex CLI 整体不可用。

**解决方案 / 缓解措施**
- `_create_process()` 改为 `stdin=DEVNULL`,让 Claude/Codex/optional CLI adapter 都以真正非交互模式启动。
- 新增单测确认 adapter 子进程创建时关闭 stdin,同时保留 stdout/stderr pipe。
- 当前已 running 的旧任务不会自动继承修复,需要 `/interrupt <task_id>` 后重启 AICO 再提交。

**如何避免再次踩中**
- 所有非交互 CLI adapter 都必须显式处理 stdin;不要依赖父进程当前 stdin 状态。
- 看到连续 heartbeat 且没有 stdout 时,先做最小 CLI smoke;若 smoke 正常,再查子进程启动契约、stdin/stderr 和 prompt 注入。
- 不要把这种问题误判为“任务太难”或“需要继续加长 idle timeout”。

**相关链接**
- ROUNDS Round 116

### [P-027] CLI 子进程 stderr 不读取导致 Codex stdout 被 pipe 反压卡住

**状态**:🟢 RESOLVED
**首次踩中**:Round 117
**最后更新**:2026-05-26
**影响范围**:`src/aico/adapter/claude_code.py`, `tests/unit/test_claude_code_adapter.py`

**症状**
Round 116 修复 stdin 后,真实 IM 再次提交 reviewer/Codex 任务 `3be492f3`,任务已 accepted 并进入 `Stream start`,但 120 / 240 / 360 秒仍只有 heartbeat,没有任何 `type=text` 输出。`ps` 可见 Codex 子进程仍在运行,命令参数中包含完整 reviewer prompt,说明不是 `/ask` 没交给 Codex。

**根因**
AICO 过去只读取子进程 stdout,stderr 要等进程退出后才读。Codex CLI 会把运行头、hook、工具日志、警告等大量信息写到 stderr;当 stderr pipe 写满后,子进程会被 OS 反压阻塞,导致最终 stdout 也无法产出。这个现象会被误看成“模型思考很久”。

**解决方案 / 缓解措施**
- 启动 CLI 子进程后立即创建后台任务持续 drain stderr,只保留 tail 用于失败时生成错误信息。
- 成功任务不会把 stderr 诊断日志推给 IM;失败任务仍使用 stderr tail 作为错误内容。
- 新增单测构造“stderr 不被读取则 process.wait 不返回”的场景,确认 adapter 会并发 drain stderr。
- 人类真实 IM 复验确认改动有效,该问题已关闭。

**如何避免再次踩中**
- 所有 subprocess adapter 都必须同时处理 stdout 和 stderr;不能只在进程结束后读 stderr。
- 看到连续 heartbeat 且 `ps` 里子进程仍在,不要只判断“模型太慢”;要检查 stderr pipe 是否被 drain。
- 如果未来要展示 provider 诊断,应单独做 debug/audit 入口,不要把 stderr 噪音混进用户任务结果。

**相关链接**
- ROUNDS Round 117

### [P-028] 内置命令绕过 rich text renderer 导致真实 IM 不解析标题和列表

**状态**:🟢 RESOLVED
**首次踩中**:Round 120
**最后更新**:2026-05-27(Round 124)
**影响范围**:`src/aico/core/goal_brief.py`, `src/aico/core/outcome_grader.py`, `src/aico/core/dream.py`, `src/aico/core/memory_commands.py`, `src/aico/core/message_rendering.py`

**症状**
真实 dogfood 中,`/goal` 和 `/recall` 的返回内容在 IM 里没有正确 Markdown/富文本效果:
标题、无序列表和命令提示看起来只是普通文本。`/dream` 虽然返回了 candidate memory,
但逐条列出旧 task id 和失败原因,人类难以判断“这是正确反思”还是“系统乱记旧错误”。

**根因**
流式 adapter 输出已经通过 `StreamedMessageWriter` 调用 `rich_text_message()`,
但部分内置命令消息直接构造 `MessageContent(text=...)`,没有生成 `MessageTextSpan`。
同时 Dream 第一版把每个异常 task 直接变成 memory candidate,缺少面向老板的 Meaning / Effect 解释,
也没有按相同失败原因聚合成可复用 lesson。

**解决方案 / 缓解措施**
- Goal Brief、Outcome Grader、Dream review 和 memory recall/remember/forget 输出统一走 `rich_text_message()`。
- `message_rendering` 增补 Phase 8 常见 label keys,包括 `owner`、`tracking`、`goal`、`grader`、`graded_task`、`query`、`purpose`、`evidence`。
- Dream review 改为按 waiting/running/idle-timeout/interrupted/rejected/generic failed 聚合 candidate lesson。
- Dream 输出新增 Meaning / Effect / Next,明确 candidate memory 不会自动注入 prompt,只有人类认可后才用 `/remember <accepted lesson>` 晋升。

**如何避免再次踩中**
- 新增任何 IM-facing 内置命令时,默认使用 `rich_text_message()` 或专门的 render helper,不要直接返回裸 `MessageContent(text=...)`。
- 单测不要只看 `.text`,还要在关键命令上断言 `.spans` 非空或命令被 code span 标记。
- Dream / self-improving 输出必须解释“为什么这是候选经验”和“会不会影响后续 prompt”,不能只暴露内部 task/memory id。

**相关链接**
- ROUNDS Round 120

### [P-029] Prompt 注入提示词包含风险关键词会让普通任务误触发审批

**状态**:🟢 RESOLVED
**首次踩中**:Round 121
**最后更新**:2026-05-27
**影响范围**:`src/aico/core/language.py`, `src/aico/core/risk.py`

**症状**
实现 `/language zh` 后,普通只读任务 `please inspect` 没有被 adapter 接收。排查发现任务在 submit 前被语言提示词包装,
而提示词里包含 `shell commands`,命中了 `TextRiskAssessor` 的 `command` / `shell` 风险关键词,
导致普通任务进入 approval gate。

**根因**
AICO 的风险识别是对最终 task payload 做文本扫描。任何系统级 prompt wrapper 如果包含 `run`、`write`、`shell`、
`command` 等词,都会被当成用户任务风险的一部分。语言偏好本来只想限制回复语言,不应改变任务风险等级。

**解决方案 / 缓解措施**
- 语言提示词改用 `CLI snippets`,避免包含风险规则关键词。
- 保留“代码块、路径、日志、标识符、协议关键字、严格 JSON/schema 不翻译”的约束。
- 新增端到端单测,确认 `/language zh` 后普通任务能直接进入 adapter,不会误触发审批。

**如何避免再次踩中**
- 新增任何 task payload wrapper 前,先检查文案是否包含 `TextRiskAssessor.RISK_RULES` 里的关键词。
- 风险识别应继续基于最终 payload,但系统 wrapper 文案必须保持风险中性。
- 不要为了一个 wrapper 把整类 metadata 标成 read-only,否则会掩盖真实用户任务风险。

**相关链接**
- ROUNDS Round 121

### [P-030] Renderer 只逐行加 spans 无法处理真实 agent Markdown

**状态**:🟢 RESOLVED
**首次踩中**:Round 122
**最后更新**:2026-05-27
**影响范围**:`src/aico/core/message_rendering.py`, `src/aico/channel/telegram.py`, `src/aico/core/orchestrator.py`

**症状**
真实 Telegram dogfood 中,agent / memory 输出里出现粘连 Markdown:

```text
Decision Memo — Phase 8 Operator Inbox Kickoff## DecisionYes ...## Why1. ...
```

Telegram 侧没有把标题、列表、表格等结构渲染清楚;`Collaboration requested: implementer -> reviewer`
也只是普通文本。用户看到的是一大段难读内容,无法快速判断记忆和 agent 输出。

**根因**
项目的正确架构是 core 产生平台无关 `MessageTextSpan`,Telegram Channel 再映射为 HTML parse mode。
但 `rich_text_message()` 过去只对“已经分好行”的轻量 Markdown 做逐行处理;真实 agent 输出经常会出现 heading
与正文粘连、Markdown table、fenced code block、大小写 label 等更复杂结构。逐命令补 `MessageContent`
无法覆盖这些情况。

**解决方案 / 缓解措施**
- 在 `rich_text_message()` 前增加 IM Markdown normalization:
  - 拆分粘连 `## Heading`。
  - 对已知 heading 做标题 / 正文拆分。
  - Markdown table 转等宽 IM table,用 code span 保持对齐。
  - fenced code block 转 code span。
  - label span 大小写无关。
- `Collaboration requested` 改为结构化 rich text message。
- Telegram 仍只负责把 spans 映射为 HTML,不把 Telegram Markdown 方言泄漏到 core。

**如何避免再次踩中**
- 新增输出格式能力时先改 `message_rendering.py`,不要在单个 command handler 里手搓 HTML 或 Markdown。
- 真实 IM 验收应包含 agent markdown 样例:heading、list、table、code block、粘连 heading。
- Telegram 没有真实 table;表格应降级为等宽 text table + code span。

**相关链接**
- ROUNDS Round 122

### [P-031] 无限扩 Markdown 兼容 case 会让 IM 输出层失控

**状态**:🟢 RESOLVED
**首次踩中**:Round 123
**最后更新**:2026-05-27
**影响范围**:`src/aico/core/native_output.py`, `src/aico/core/streaming.py`, `src/aico/channel/telegram.py`

**症状**
真实 Telegram dogfood 中,即使 Round 122 已经把 agent Markdown 走 rich text normalization,
模型仍可能返回非标准但常见的格式,例如单行 fenced code:

````text
```uv run pytest```
````

如果继续把所有情况都塞进 `rich_text_message()`,renderer 会变成无限 case 集合,每接入一个 IM
Channel 都要重新补一批规则。

**根因**
`rich_text_message()` 适合作为保底归一化层,但不应该承担“理解所有模型 Markdown 方言”的全部责任。
更合理的链路是:按目标 Channel 给 agent 明确输出契约,让模型直接输出该 Channel 支持的 native format;
系统只做白名单 sanitize / validate,失败再回退到 rich text fallback。

**解决方案 / 缓解措施**
- 新增 opt-in native output contract:`AICO_PREFER_NATIVE_CHANNEL_FORMAT=true` 时,Telegram 任务 prompt
  会要求 agent 输出 Telegram Bot API HTML 子集。
- 新增 Telegram HTML 白名单 sanitizer;只允许 `<b>`、`<i>`、`<u>`、`<s>`、`<code>`、`<pre>`、
  `<blockquote>` 等安全标签,不允许属性和 unsupported tag。
- `StreamedMessageWriter` 优先尝试 native Telegram HTML;验证失败时自动回退到 `rich_text_message()`。
- 同时补齐单行 fenced code fallback,避免 native 失败后内容被吞。
- Round 124 修正:在 `<pre>` / `<code>` literal block 内,`<id>` / `<task_id>` 这类占位符应安全转义为文本,
  不能让整条 native HTML 被打回 fallback;literal block 外的 unsupported HTML 仍保持失败回退。

**如何避免再次踩中**
- 新 Channel 优先定义自己的 output contract 和 validator,不要复制 Telegram Markdown 规则。
- native format 永远不能直接信任模型原样输出;必须 sanitize / validate 后才允许带 parse mode 发送。
- rich text renderer 是 fallback,不是无限制兼容所有模型输出格式的主战场。
- Telegram HTML validator 要区分“真正 unsupported tag”和“`<pre>` / `<code>` 里的文本占位符”。

**相关链接**
- ROUNDS Round 123
- ROUNDS Round 124

### [P-032] quiet heartbeat 进入结果缓冲导致 native HTML 回退裸露

**状态**:🟢 RESOLVED
**首次踩中**:Round 125
**最后更新**:2026-05-27
**影响范围**:`src/aico/core/streaming.py`, `src/aico/core/orchestrator.py`

**症状**
真实 Telegram dogfood 中,先出现 quiet heartbeat:

```text
Still running: no adapter output for 120s. Use /task <id> for details or /interrupt <id> to stop.
```

随后 agent 的 native Telegram HTML 结果被拼在后面,并以裸标签形式显示:

```text
... to stop.<b>1. verdict:</b> pass- list actionable items...
```

**根因**
`OutputType.STATUS` 是状态提示,但过去通过 `StreamedMessageWriter.append()` 写入同一个
`_current_text` 缓冲。后续 agent 输出到达时,状态行和 native HTML 混在一起;状态行中的
`/task <id>` 会让 native HTML validator 看到 literal block 外的 unknown tag,最终回退到
`rich_text_message()`,于是 `<b>` / `<code>` 等标签作为普通文本裸露。

**解决方案 / 缓解措施**
- 新增 `StreamedMessageWriter.show_status()`:只临时编辑 IM 消息展示 heartbeat,不写入结果缓冲。
- `Orchestrator` 对 `OutputType.STATUS` 调用 `show_status()` 后直接 `continue`,不进入 captured output、
  native HTML validator 或最终 IM 内容。
- 如果已经有真实输出,late status 不覆盖结果;老板仍可通过 `/task <id>` / `/inbox` 看 running reason。
- Telegram native output prompt 增补:标题、段落、列表项要分行,bullet 用 `•`,不要用 Markdown `- `。

**如何避免再次踩中**
- `OutputType.STATUS` 永远是 transient UI hint,不是 agent result。
- 所有 writer / renderer 新增状态类输出时,先问“它是否会进入最终结果缓冲”;答案应为否。
- native HTML validator 不应承担清理 AICO 自己的 status 行;status 行应在进入 validator 之前被隔离。

**相关链接**
- ROUNDS Round 125

### [P-016] Appointment prompt 脚手架导致普通项目咨询误触发审批

**状态**:🟢 RESOLVED
**首次踩中**:Round 69
**最后更新**:2026-05-13
**影响范围**:`src/aico/core/risk.py`, `src/aico/core/task_bus.py`, `src/aico/core/prompt_stack.py`

**症状**
用户在 active project 中 `lead` 某个 agent 后,只是询问团队或项目问题,也可能收到
`Approval required`。如果用户没有及时 `/approve` 或 `/reject`,继续操作会积累多个
`waiting_approval` 任务;随后裸 `/approve` 会提示多个 pending approvals,而
`/interrupt <task_id>` 又会返回 `task is waiting_approval, not running`。

**根因**
project-scoped task 会通过 Appointment Prompt Stack 拼入 Agent、Role、Project、
Appointment Contract 和 `Current task`。旧风险识别扫描整段 prompt,因此 role summary /
inline prompt 里的 `write`、`run tests`、`command` 等词会污染真实用户请求的风险级别。

同时,`/interrupt` 只支持 running 任务,无法用来清理还没 approve/reject 的 waiting approval。

**解决方案 / 缓解措施**
- `TextRiskAssessor` 在检测到 appointment prompt 的 `Current task:` 段时,只对其后的真实用户请求做风险识别。
- 如果真实 `Current task` 要求写文件、执行命令或 destructive 操作,仍按原规则触发审批。
- `TaskBus.interrupt()` 对 `waiting_approval` 任务执行取消:更新任务为 `interrupted`,把 approval 从 pending 中移除,并记录 `approval_rejected` / `task_interrupted` 审计事件。

**如何避免再次踩中**
- 风险识别应检查用户真实意图,不要把 system/role/project prompt scaffolding 当作用户请求。
- 新增 prompt stack 字段时,不要让这些字段直接影响 approval gate;如需影响,应通过显式 metadata 或新 ADR 设计。
- 多个 pending approvals 时,可以用 `/interrupt <short_task_id>` 清理不想执行的待审批任务。

**相关链接**
- ROUNDS Round 69

### [P-017] 真实 Stage 3 录屏被底层 CLI 噪音污染

**状态**:🟡 MITIGATED
**首次踩中**:Round 91
**最后更新**:2026-05-18(Round 92)
**影响范围**:`examples/release-room/shot-rhythm.md`, `src/aico/adapter/codex.py`, `src/aico/adapter/claude_code.py`, Telegram 录屏

**症状**
Release Room Stage 3 真实 Telegram dogfooding 时,Claude CLI 在无 Pro / 输出不稳定环境下长时间不回包;改用 Codex 做 PM 拆工后,Telegram 被 Codex CLI warning、HTML 片段和 thread resume 错误刷屏。这些输出能证明真实链路跑过,但不适合作为 README public GIF。Round 92 修复后,Codex PM 短输出已经可用作 public GIF 镜头。

**根因**
Stage 3 直接拍真实底层 AI CLI 输出,把 AICO 的管理面展示绑定到底层 CLI 当前状态、登录/额度、插件噪音和 session resume 状态。AICO 的价值点是 project/team/memory/approval/audit 编排,而不是把 provider 原始 stdout 原样公开展示。

**解决方案 / 缓解措施**
- public GIF 先使用 Stage 2 transcript-driven 稳定链路或更短的真实 IM 管理命令,避免长 provider 输出入镜。
- 真实 Claude/Codex dogfooding 继续保留为验收记录,但需要先清理 Adapter stdout、session resume 和 warning 过滤后再拍 public 素材。
- Stage 3 录屏脚本中保留 approval gate、interrupt、daily/audit 等 AICO 管理面,底层 AI 输出只截取短摘要。
- Round 92 已增加 Codex 输出过滤,并避免跨 provider session resume;Codex PM/test/review 短任务可作为真实 GIF 镜头。

**如何避免再次踩中**
- 不要直接把 provider stdout 当 README 素材。
- 真实录屏前先跑 1 条 `/ask pm ...` dry run,确认输出首屏没有 CLI warning / HTML / token / path 噪音。
- 如果 provider 输出不可控,先用 transcript-driven GIF 完成 showcase,把真实 dogfooding 问题写到 BLOCKERS。

**相关链接**
- ROUNDS Round 91

### [P-018] httpx INFO 日志会把 Telegram Bot token 打进日志

**状态**:🟢 RESOLVED
**首次踩中**:Round 91
**最后更新**:2026-05-18
**影响范围**:`src/aico/app/phase1.py`, `logs/aico.log`

**症状**
Stage 3 启动真实 Telegram polling 且日志级别为 INFO 时,httpx 会记录完整请求 URL,形如 `https://api.telegram.org/bot<token>/getUpdates`。这会把 Telegram Bot token 写入 `logs/aico.log`。

**根因**
`configure_logging()` 对 root logger 设置 INFO 后,httpx/httpcore 的 INFO 请求日志也进入 AICO 文件日志;Telegram Bot API 把 token 放在 URL path 中,不是 header,因此 URL 日志本身就是敏感信息。

**解决方案 / 缓解措施**
Round 91 已在 `configure_logging()` 中将 `httpx` 和 `httpcore` logger 降到 WARNING,避免正常 INFO 运行时记录完整 Bot API URL。

**如何避免再次踩中**
- 新增外部 HTTP 客户端时,检查其 INFO/DEBUG 日志是否包含 URL、header、query 或 body 中的 token。
- 真实 smoke test 前不要把 `AICO_LOG_LEVEL=DEBUG` 用在带真实 token 的 IM Channel 上。
- 如果需要调试 HTTP,使用脱敏 logger 或 mock token。

**相关链接**
- ROUNDS Round 91

### [P-017] Project Next 命令被富文本化后 Telegram 不再识别为可触碰命令

**状态**:🟢 RESOLVED
**首次踩中**:Round 71
**最后更新**:2026-05-14
**影响范围**:`src/aico/core/project_messages.py`, `src/aico/channel/telegram.py`

**症状**
`/roles`、`/role`、`/project`、`/team` 等项目消息末尾的 `Next:` 引导命令在 Telegram
里显示为普通白字,不能像 `/agents` 输出里的 `- /agent <agent>` 一样变成蓝色可触碰命令。

**根因**
Project message renderer 会把 `- ` / `* ` 统一规范成 `• `,并给所有裸 `/command`
追加 `MessageTextStyle.CODE` span。Telegram Bot API 发送 HTML rich text 后,code 样式和
项目侧 bullet 规范化会压掉 Telegram 对 bot command 的自动识别。

**解决方案 / 缓解措施**
- 对形如 `- /command` 或 `* /command` 的 Next 引导命令行保留原始 hyphen list 文本。
- Next 命令行不再添加 slash command code span,交给 Telegram 自动识别为可触碰命令。
- 正文、blocker、Facts 等非 Next 命令仍保留原有 Markdown 清洗和 code span 行为。

**如何避免再次踩中**
- IM 里希望用户直接触碰发送的 bot command,优先使用裸文本 `- /command`,不要包成 code。
- 新增项目侧 `Next:` guidance 时,用单测确认输出是 `- /command` 且 Next 区块没有 command code span。
- 平台无关 render contract 不应假设所有富文本样式都比 IM 原生识别更友好。

**相关链接**
- ROUNDS Round 71

### [P-018] Smoke prompt 里的否定危险词也会触发 approval gate

**状态**:🟢 RESOLVED
**首次踩中**:Round 73
**最后更新**:2026-05-15
**影响范围**:`src/aico/core/risk.py`, `tests/golden/test_phase6_metrics_token_golden.py`

**症状**
真实 provider token golden 起初没有发给模型,而是停在 approval 前。原因不是 Adapter
或 CLI 失败,而是 smoke prompt 写了 `Do not run tools`,其中的 `run` 被风险识别判定为
shell 风险。

**根因**
当前 `TextRiskAssessor` 是保守词法规则,不会理解“不要 run”这种否定语义。只要用户请求文本中
出现 shell/write/destructive 触发词,就可能进入审批门禁。这符合安全优先,但会让验收 prompt
本身污染测试目标。

**解决方案 / 缓解措施**
- token golden prompt 改为纯短答:`Return exactly this text: AICO_METRICS_TOKEN_SMOKE_OK`。
- Phase 6 playbook 记录:smoke prompt 不要写 `run`、`modify`、`edit` 等风险词,即便是否定句也避免。

**如何避免再次踩中**
- 验证“只读模型调用”时,不要在 prompt 里描述不做哪些危险事;直接要求返回固定短文本。
- 如果要测试 approval gate,单独写 approval case,不要和 provider token smoke 混在同一个 golden。

**相关链接**
- ROUNDS Round 73

### [P-019] Phase 7 第一版中文记忆检索不是语义搜索

**状态**:🟢 RESOLVED
**首次踩中**:Round 82
**最后更新**:2026-05-18
**影响范围**:`src/aico/core/memory.py`, Phase 7 acceptance / IM 体感验收

**症状**
验收 boss global 偏好时,记忆 claim 是“我更喜欢汇报进度时告诉我还有几阶段”,但任务 query 写成
“汇报当前项目进度,并告诉我还有几阶段”时没有召回该记忆。

**根因**
Phase 7 第一版 search 故意只做 scope + 子串/标签匹配,不引入向量库或分词器。
英文长句能靠空格 token 部分命中,中文长句没有空格时会被当成一个完整 token,导致近义长句无法命中。

**解决方案 / 缓解措施**
- Round 84 新增 `MemorySemanticScorer` 和默认 `LocalSemanticMemoryScorer`。
- `MemoryRetriever` 改为先按 scope 收集候选,再按 semantic score 排序;`MemoryGovernor` 继续做 active / sensitivity / confidence 投影。
- `/recall` 和 Prompt Stack 可召回中文长句复述,也支持少量常见中英项目术语别名,例如“法务检查”匹配 `legal review`。
- 后续如果要接真实 embedding / LLM rerank,应替换 scorer 实现,不要绕过 scope、candidate、sensitivity 和 citation。

**如何避免再次踩中**
- 新增语义 scorer 时,先写跨 project / candidate / restricted 回归测试,避免召回能力提升导致越权披露。
- 真实模型 rerank 必须有结构化输出、失败回退和成本/延迟边界。

**相关链接**
- ROUNDS Round 82
- ROUNDS Round 84

### [P-020] Codex read-only sandbox 里直接跑 pytest 可能没有可写临时目录

**状态**:🟡 ACTIVE
**首次踩中**:Round 93
**最后更新**:2026-05-18
**影响范围**:`CodexAdapter`, Release Room Stage 3 真实 Telegram dogfooding

**症状**
Release Room GIF 实录中,`/ask tester Give 2 regression checks for v0.2. No code.`
触发 Codex 以 read-only sandbox 执行 tester 分析。Codex 尝试运行
`PYTHONDONTWRITEBYTECODE=1 python -m pytest -p no:cacheprovider ...`,但在只读沙箱下
测试收集前失败:`FileNotFoundError: No usable temporary directory found`。

**根因**
Codex read-only sandbox 适合静态分析和文件读取,但不保证 Python / pytest 可写临时目录。
即使关闭 bytecode 和 pytest cache,部分运行时仍需要临时目录,因此“只读测试执行”不是稳定假设。

**解决方案 / 缓解措施**
- README GIF 中保留这一段作为真实 dogfooding 证据,但后续精剪时应避免把它当作成功测试 verdict。
- 需要 tester 真跑 pytest 时,给 Codex 明确可写临时目录或走审批保护的非 read-only 执行路径。
- 只想拍 public demo 时,让 tester 做静态 regression checklist,不要要求 runtime verdict。

**如何避免再次踩中**
- Codex read-only prompt 不要暗示可以运行测试;把“检查测试策略”和“执行测试”拆成两条不同风险级别任务。
- 后续若要支持 read-only smoke,Adapter 层应显式配置 `TMPDIR` 指向允许写入的位置,并用单测覆盖命令环境。

**相关链接**
- ROUNDS Round 93

### [P-021] Project agent alias 与 provider 名漂移导致 `/appoint` 被拒

**状态**:🟢 RESOLVED
**首次踩中**:Round 98
**最后更新**:2026-05-25
**影响范围**:`src/aico/app/phase1.py`, `src/aico/core/project_assignment.py`

**症状**
真实 IM 中执行 `/appoint codeflicker as tester` 返回
`Cannot appoint codeflicker as tester`。`/agents` 能看到 CodeFlicker,但项目办公室不能任命。

**根因**
默认 project config 过去对所有 persona 都优先取第一个 alias 作为 agent id。
CodeFlicker 的第一个 alias 是 `flicker`,而用户自然输入的是 provider / persona 名 `codeflicker`。
命令层 `AgentDirectory.resolve()` 能识别 `codeflicker`,但 `ProjectAssignmentDirectory`
只按配置 agent id 精确匹配,因此任命失败。

**解决方案 / 缓解措施**
- 默认 project config 只对 `implementer` / `reviewer` 保留历史别名 `claude` / `codex`;
  Cursor / CodeFlicker / Trae / Gemini 使用 persona 名作为 agent id。
- `ProjectAssignmentDirectory.resolve_agent_id()` 支持先按 agent id 匹配,再在唯一匹配时按
  `CompanyAgentProfile.provider` 匹配。
- 新增单测覆盖 `codeflicker` provider 名任命路径。

**如何避免再次踩中**
- 新 adapter 进入 `/agents` 后,必须用 `/appoint <agent> as <role>` 的展示名做一次 project-office 验收。
- agent id、persona name、adapter/provider name、alias 可以不同,但 project appointment 解析必须支持用户看到的名字。

**相关链接**
- ROUNDS Round 98

### [P-022] 单 adapter 单槽位不适合一个 agent 担任多个 role

**状态**:🟢 RESOLVED
**首次踩中**:Round 98
**最后更新**:2026-05-20
**影响范围**:`src/aico/adapter/claude_code.py`, `src/aico/core/command_messages.py`

**症状**
同一个 Codex 被任命为 reviewer 和 tester 后,连续 `/ask reviewer ...` 与
`/ask tester ...` 时第二个任务返回 `Task busy: adapter is busy`。

**根因**
`ClaudeCodeAdapter` 家族原来只要有任意运行中 task 就把 adapter 标成 busy 并拒绝新任务。
这在单 persona smoke test 中可用,但不符合“一个真实 agent 可同时承担多个岗位”的 project-office 语义。

**解决方案 / 缓解措施**
- CLI adapter 新增 `max_concurrent_tasks`,默认 5;只有运行中任务达到上限才返回 busy。
- `AdapterSnapshot` 记录 `running_tasks` / `max_concurrent_tasks`。
- `/agents` / `/agent` 展示当前运行数、最大并发和建议任命上限;`/appoint` 成功回执也展示同样约束。
- Codex / optional CLI adapter 默认 output idle timeout 从 90 秒逐步放宽到 1800 秒,减少长思考任务被误杀;启动配置可设为 `0` 禁用自动 idle timeout。

**如何避免再次踩中**
- 不要把 `AdapterStatus.BUSY` 理解成“有任何任务在跑”;用户关心的是还能不能接新任务。
- 任命同一 agent 到多个高频 role 时,先看 `/agent <agent>` 的最大并发;超过上限应新增 agent 或降低并行派工。
- 如果真实 provider 长时间不吐 stdout,先用环境变量调大 timeout 或设计 heartbeat,不要回退到无限 busy。

**相关链接**
- ROUNDS Round 98

### [P-023] 验收 prompt 把 lead 概念和 role id 混用

**状态**:🟢 RESOLVED
**首次踩中**:Round 111
**最后更新**:2026-05-24
**影响范围**:`src/aico/core/project_assignment.py`, `src/aico/core/collaboration.py`, `src/aico/core/orchestrator.py`

**症状**
真实 IM 中执行:

```text
/ask lead decide whether we should start Phase 8 operator inbox now...
/ask lead propose a tiny Phase 8 inbox implementation plan, then ask @reviewer: ...
```

Telegram 只显示任务仍在运行,例如:

```text
4697ce83-d7bc-4e7a-8863-09f43998d009 [codex]: running
4c31d567-f9cf-48de-a232-8dfe74af5cef [codex]: running
```

日志显示两条任务被 Codex 接收后 300 秒没有 stdout,最后触发 idle timeout。

**根因**
`lead` 是老板视角的项目概念,但 `/ask <role> <task>` 过去只按真实 role id 查 appointment。
验收 prompt 使用 `/ask lead ...` 时容易落不到预期的 lead/default role 语义。
同时,协作解析只看 Adapter 输出的第一条非空行;如果模型先输出计划,再在后续行写
`@reviewer: ...`,不会触发 reviewer child task。即使识别到后续行,旧流式处理也会把同一段输出的
非指令正文吞掉。

**解决方案 / 缓解措施**
- `ProjectAssignmentDirectory.appointment_for_role()` 支持 `lead` / `default` 作为当前项目 default assignment 别名。
- 协作解析改为扫描任意一行以 `@persona` 开头的指令。
- 流式输出处理会保留非协作指令正文,同时触发 child task。
- 新增单测覆盖 `/ask lead ...` 触发 lead decision workflow,以及“计划正文 + 后续 `@reviewer:` 行”的协作触发。

**如何避免再次踩中**
- 面向老板的真实 IM 验收问题可以使用 `lead`,但代码必须把它解析为项目 default assignment。
- 验证 Phase 5 协作时,不要假设模型第一行一定就是 `@reviewer:`;应支持模型先给计划再发协作指令。
- 如果 Telegram 只看到 `running`,先查 `logs/aico.log` 里的 task id;区分命令路由问题和 provider 无 stdout timeout。

**相关链接**
- ROUNDS Round 111

### [P-024] 协作短指令引用父输出编号但 child task 丢失上下文

**状态**:🟢 RESOLVED
**首次踩中**:Round 113
**最后更新**:2026-05-25
**影响范围**:`src/aico/core/collaboration.py`, `src/aico/core/orchestrator.py`, `src/aico/core/task_bus.py`

**症状**
真实 IM dogfood 中,人类让 reviewer 检查 Phase 8 inbox plan。reviewer 成功输出 findings 后,
又发出 `@implementer: please reflect (a)-(d) in the inbox PR plan and the new ADR before coding starts.`
系统显示 `Collaboration requested: implementer -> implementer`,随后 implementer 回答自己不知道
`(a)-(d)` 是什么、PR plan 在哪里、ADR 是哪一篇。

**根因**
Round 111 修复了“后续行 `@reviewer` 能触发 child task,且保留父输出展示”,但 child task payload
仍只包含协作指令后的短句。真实 reviewer 常用 `(a)-(d)`、`above`、`these findings` 这类引用父输出的短指令;
如果不把父输出上下文一并交给 child,二次协作会出现上下文断层。另一个体感问题是 project appointment
任务底层 target persona 可能仍是 `implementer` / `claude`,导致 reviewer 发起协作时 IM 显示为
`implementer -> implementer`。

**解决方案 / 缓解措施**
- `collaboration_payload()` 支持可选 `source_context`,会把父任务截至协作指令前的可见输出注入 child payload。
- `Orchestrator._stream_outputs_for_task()` 在触发协作时传入已捕获父输出和当前 chunk 的非指令正文。
- 协作来源优先使用 task metadata 中的 `aico.assignment_role`,IM 提示和 audit actor 会显示 reviewer 等项目岗位,
  不再只显示底层 persona。

**如何避免再次踩中**
- 真实协作 smoke 不能只看 child task 是否创建;还要看 child task 是否有足够上下文理解短引用。
- 后续新增协作协议字段时,保留“短指令 + 父输出上下文”的交接契约,不要只传 directive payload。
- 排查 project appointment 协作时,优先看 metadata 中的 assignment role,不要把底层 agent persona 当作老板视角 role。

**相关链接**
- ROUNDS Round 113

---

### [P-033] Memory/Audit JSONL 升级是单向门

**状态**:🟡 ACTIVE
**首次踩中**:Round 129(Sprint A1)
**最后更新**:2026-05-31

**症状**
Sprint A1 给 `MemoryAtom` / `AuditEvent` / `Task` 都加了 `trace_id: str | None = None`,M1 还给 `MemoryAtom` 加了 `kind` / `experience`。新代码读老 JSONL 安全(老记录缺少新字段时,Pydantic 会用 default 填补);**反向不安全**——老代码读新 JSONL 时,因为 `FrozenModel` 配置是 `extra="forbid"`,会因为遇到陌生字段 `kind` / `trace_id` 直接报 `ValidationError` 拒绝整个 JSONL 行。

**根因**
`FrozenModel` 默认 `extra="forbid"` 是为了核心域强约束:任何未声明字段都视为协议错误。代价是:**JSONL 升级是单向门**——一旦运行过新代码并写过新记录,该 JSONL 文件就不能再被回滚后的老代码加载。

**解决方案 / 缓解措施**
- 接受单向语义。AICO 不支持降级运行。
- 升级前如有顾虑,先备份 `AICO_MEMORY_PATH` 和 `AICO_AUDIT_LOG_PATH` 指向的 JSONL 文件。
- 后续如果需要做 schema 大改(改字段名/删字段),先开新 ADR,设计迁移工具,不要靠 `extra="ignore"` 偷偷绕过。

**如何避免再次踩中**
- 给已存在的 JSONL 新增字段时,**字段必须带 default 值**(否则连前向兼容都做不到)。
- 不要把 `FrozenModel` 默认改为 `extra="ignore"` 来"兼容老代码读新数据"——那会让协议层失去强约束,得不偿失。
- 在 STATUS / CHANGELOG 里明确标注引入新 schema 字段的 round,提醒用户升级前备份。

**相关链接**
- ADR-0030 §"关键边界 #3"
- ROUNDS Round 128 / Round 129
- `src/aico/core/memory.py` MemoryAtom

### [P-034] 协作 parent context 被风险识别扫描导致只读 reviewer 子任务误判为 shell_exec

**状态**:🟢 RESOLVED
**首次踩中**:Round 138
**最后更新**:2026-06-15(Round 164)
**影响范围**:`src/aico/core/collaboration.py`, `src/aico/core/risk.py`, `src/aico/core/orchestrator.py`, `src/aico/core/offline_delegation.py`

**症状**
真实 IM 验收 `/overnight 为我准备好上线github的全部工作...` 时,lead/implementer 输出触发协作:

```text
Collaboration requested
source: implementer
target: reviewer
Task rejected: adapter codex cannot handle shell_exec tasks; use /claude
```

reviewer 的职责是只读审阅风险和缺口,但系统把它当成 `shell_exec` 任务拒绝,导致 `/overnight`
托管链路中断。

**根因**
Round 113 为解决协作短指令上下文丢失,把 parent output context 注入 child task payload。
但带 context 的协作 payload 旧格式使用 `Request:` 标记真实委托内容,而 `TextRiskAssessor`
只会在存在 `Current task:` 时截取真实任务段。结果风险识别扫描了完整 parent context;
只要 context 中出现 `run pytest`、`git push`、`命令` 等词,只读 reviewer/Codex 子任务就会被误判为
`shell_exec`。

**解决方案 / 缓解措施**
- `collaboration_payload()` 在带 source context 时改用 `Current task:` 标记真实委托内容。
- 保持 Codex read-only capability 不变;如果 `Current task:` 本身要求执行命令或写文件,仍会被拒绝或进入审批。
- 新增 TaskBus + Orchestrator 回归测试,覆盖 parent context 含 `run pytest` / `git push` 但 reviewer 只做风险审阅的场景。
- Round 164 将 `/overnight` wrapper 同样改为把规则放在上文、真实老板目标放在最后的 `Current task:` 下;否则系统提示词里的 `execution` / `shell` / `write` 等词也会让托管任务误入 approval。

**如何避免再次踩中**
- 给 agent 子任务注入上下文时,必须用风险识别已识别的任务边界标记,不要发明新的 `Request:` / `Delta:` 标签。
- 给 `/overnight`、goal、review 等系统 wrapper 增加操作规则时,不要把规则放在 `Current task:` 之后;真实用户目标必须是最后一个 `Current task:` 后的内容。
- 排查 `adapter codex cannot handle shell_exec tasks` 时,先看 child payload 的 `Current task:` 边界是否存在;不要直接把 reviewer 改任命给可执行 shell 的 adapter。
- 不要为修这种误判放宽 Codex capability;正确边界是“只扫描真实委托内容”,不是让只读 reviewer 能执行命令。

**相关链接**
- ROUNDS Round 138
- P-024

### [P-035] CLI exit 0 的短输出被 `/overnight` 误当作可交接成功

**状态**:🟢 RESOLVED
**首次踩中**:Round 139
**最后更新**:2026-06-04
**影响范围**:`src/aico/core/offline_delegation.py`, `src/aico/core/orchestrator.py`, `src/aico/core/task_bus.py`

**症状**
真实 IM 验收 `/overnight 为我准备好上线github的全部工作...` 后,`/task 3f7d57c2`
只看到半句输出:

```text
Community 文件：写一个简短 Code of Conduct（基于 Contributor Covenant 2.1）：
```

日志显示 Claude CLI 运行约 8 分钟后 `return_code=0`,但 `stdout_chunks=1`,最终 IM 只有 64 字符。
SQLite snapshot 却显示任务 `done`,容易让老板误以为 overnight handoff 成功。

**根因**
`TaskBus` 的通用语义是:Adapter 产出 `OutputType.DONE` 就标记 `TaskStatus.DONE`。这对普通短问答合理,
但 `/overnight` 的产品合同不是“有输出即可”,而是必须留下 morning handoff:done、blocked、risks 和 next actions。
AICO 缺少 `/overnight` 专属的交接完整性验收,导致 CLI exit 0 + 任意短 stdout 被误判为成功。

**解决方案 / 缓解措施**
- 新增 `offline_delegation_completion_issue(output)`:只检查 `/overnight` handoff,输出过短或缺少 done / blocked / risks / next actions 时返回问题。
- `Orchestrator._run_delegated_task()` 只在 task snapshot 已是 `DONE` 时调用该检查;等待审批、rejected、failed 不受影响。
- 不完整 handoff 会调用 `TaskBus.mark_failed(...)`,记录 `TASK_FAILED` audit,并通过 IM 发送 `Overnight delegation output incomplete`。
- `/goal` 改走独立 `_run_goal_task`,继续用 Outcome Grader,不套 overnight handoff 合同。

**如何避免再次踩中**
- Absence-first 工作流不能只看 provider exit code;必须看老板早上能不能接手。
- 后续新增 `/morning` 自动生成、lead 自驱、多 agent 夜间编排时,都要定义“可交接成功”的产品合同。
- 不要把这个规则下沉为所有任务的全局最小输出长度;普通 `/ask` 短问答仍然可以短输出成功。

**相关链接**
- ROUNDS Round 139
- NORTH_STAR.md 第三句 Dogfooding / 可审计交接

### [P-036] Agent native heading / bullet 被流式拼接后糊成 Telegram 一整段

**状态**:🟢 RESOLVED
**首次踩中**:Round 141
**最后更新**:2026-06-04
**影响范围**:`src/aico/core/native_output.py`, `src/aico/core/streaming.py`

**症状**
真实 IM 复验 `/overnight 为我准备好上线github的全部工作...` 时,implementer handoff 在 Telegram
里显示为一整段:

```text
... handoff:<b>Overnight delegation handoff ...</b><b>Goal received</b>"..."
<b>Decision</b>本轮不写新功能...
```

reviewer 子任务也把多条 finding 粘在同一行:

```text
• High — ...。• Medium — ...。• Medium — ...
```

任务本身已完成,但老板在 IM 里很难快速扫描 severity、done、risk 和 next action。

**根因**
`StreamedMessageWriter` 会把 adapter stdout chunks 忠实累加到 `_current_text`,再每次调用
`agent_output_message()` 重新渲染。模型虽然收到 Telegram HTML 输出契约,但真实输出可能没有在
`<b>Heading</b>`、section label 和 `•` bullet 前后留换行。AICO 过去只做 Markdown fallback
normalization,没有在 native HTML / agent output 总入口处理这种流式粘连。

**解决方案 / 缓解措施**
- `agent_output_message()` 在进入 Telegram HTML sanitizer 或 `rich_text_message()` fallback 前,
  先执行保守 IM normalization。
- normalization 只拆明显 case:相邻 `<b>/<strong>` heading、正文后接已知 section heading、
  `<b>Why</b>:` 这类 label 和行内 `• High/Medium/...` bullet。
- 不把规则写进 Telegram Channel;core 仍保持平台无关 `MessageContent`,Channel 只映射 native HTML / spans。
- 新增单测覆盖 implementer 粘连 heading 和 reviewer `。• High` 列表粘连。

**如何避免再次踩中**
- 真实 IM 验收 delegate / collaboration 时,不要只看 task 是否 done;还要看 severity list 和 handoff
  headings 是否能在手机屏幕上快速扫读。
- 新增 agent 输出格式兜底时优先改 `agent_output_message()` 或 `message_rendering.py`,不要在单个
  command handler 或 Telegram Channel 中手搓局部规则。
- 不要只靠 prompt 要求“put headings on separate lines”;provider 输出不稳定时,core 需要保守兜底。

**相关链接**
- ROUNDS Round 141
- P-030
- P-031
- P-032

### [P-037] Telegram API 上限不是老板手机阅读上限

**状态**:🟢 RESOLVED
**首次踩中**:Round 142
**最后更新**:2026-06-05
**影响范围**:`src/aico/core/streaming.py`, `src/aico/core/offline_delegation.py`, `src/aico/core/commands.py`

**症状**
Round 141 后再次真实复验 `/overnight` 和 implementer -> reviewer 协作,`Collaboration requested`
之后 reviewer 审阅仍然像一整面长墙。截图里的消息约 1800 字,没有触发旧的 3900 字分片上限,
但在 Telegram 手机端已经明显不可读。

同时老板不清楚 overnight 结束后该看哪里:猜 `/aico-view`、`/brief`,结果 `/aico-view` 不是命令,
`/brief` 又只是项目背景,不是 overnight 执行日志。

**根因**
旧 `STREAM_MESSAGE_TEXT_LIMIT=3900` 是 Telegram Bot API 安全上限附近的工程限制,不是移动端阅读体验限制。
对老板缺席场景来说,验收标准不是“消息发送成功”,而是“老板在手机上一眼知道现在要做什么”。

命令动线也偏工程化:`/overnight` 回执只给 `/daily` / `/tasks`,没有秘书式解释 `/inbox`、`/morning`、
`/task`、`/view`、`/brief` 分别解决什么问题。

**解决方案 / 缓解措施**
- `StreamedMessageWriter` 默认分片上限从 3900 改为 1400 字,面向手机阅读而不是 API 极限。
- 分片前先复用 `normalize_agent_output_for_im()`,并优先在空行、换行、句号、空格处切分。
- severity bullet 前插入空行,让 `• High` / `• Medium` 成为可扫描的审阅卡片。
- `/overnight` queued / listing / incomplete 回执改成老板秘书动线:
  `/inbox` 看当前第一动作,`/morning` 看早上交接,`/task` 看精确原文,`/view` 看 HTML 快照,
  `/brief` 只看项目背景。
- `/aico-view` 作为 `/view` 别名,避免老板按产品名输入时进入普通 agent 路由。

**如何避免再次踩中**
- IM 输出验收必须看手机截图,不能只看 Bot API 是否成功、消息是否低于 4096 字符。
- 长 agent 输出应优先拆成多条老板可扫读的卡片;如果要完整原文,让老板进 `/task <id>` 或 `/view`。
- 新增老板入口命令时,回执要写“现在看什么 / 早上看什么 / 深挖看什么”,不要只列内部命令名。

**相关链接**
- ROUNDS Round 142
- P-036

### [P-038] 公开 demo 在产品动线变化后仍教旧命令

**状态**:🟢 RESOLVED
**首次踩中**:Round 146
**最后更新**:2026-06-09
**影响范围**:`src/aico/app/release_room_demo.py`, `examples/release-room/*`, `docs/examples/release-room.md`, `docs/playbooks/release-room-demo.md`

**症状**
Round 142 已把 `/overnight` 后的老板秘书动线固定为现在看 `/inbox`,早上接手看 `/morning`,
深挖看 `/task`,HTML 看 `/view`。但发布前运行 `uv run aico-release-room-demo` 时,no-token
demo 仍然演示:

```text
Boss:
/daily release-room
```

README 和 release notes 已经准备对外公开,如果这个 drift 留到发布日,陌生开发者会在最重要的
30 秒 demo 里学到旧入口,削弱 absence-first 的产品叙事。

**根因**
产品动线修复主要落在 runtime、STATUS 和 Phase 8 playbook,但 public demo 脚本、transcript、
shot rhythm 和 contributor quickstart 没有和 runtime gate 一起进入验证清单。pytest 能证明
`/morning` 存在,但不能证明公开 demo 正在讲同一个产品故事。

**解决方案 / 缓解措施**
- `aico-release-room-demo` 的早上接手命令改为 `/morning`。
- Release Room transcript、demo script、shot rhythm、recording storyboard、docs examples 和
  release-room playbook 全部改为 `/morning`。
- 发布前显式运行 `uv run aico-release-room-demo`,把 no-token demo 纳入 RC 验收,不只跑单测。

**如何避免再次踩中**
- 每次修改老板入口命令或 handoff 动线后,同时搜索 README、release notes、demo script、
  transcript、shot rhythm 和 contributor quickstart。
- 发布前必须实际运行 no-token demo;不要只相信文档里写着"30 秒可跑"。
- 历史 ADR / ROUNDS 可以保留旧命令作为历史事实,但 public-facing quickstart / demo 必须对齐当前产品动线。

**相关链接**
- ROUNDS Round 146
- P-037

### [P-039] README GIF 首帧和最新能力比文件是否存在更重要

**状态**:🟢 RESOLVED
**首次踩中**:Round 147
**最后更新**:2026-06-10
**影响范围**:`README.md`, `README.zh-CN.md`, `docs/assets/release-room-demo.gif`,
`examples/release-room/shot-rhythm.md`, `docs/launch/playbook.md`

**症状**
Round 147 发布复核时,README 已经嵌入 `docs/assets/release-room-demo.gif`,因此很容易把
"GIF 文件存在"误判成"公开首屏视觉已完成"。

实际检查发现当前 GIF 约 95 秒、`360 x 730`,首帧不是 Telegram 产品画面,而是旧分镜/表格
画面;抽样帧也没有把当前最重要的 `/morning` 接手和 `/view` IM HTML snapshot 前置展示。
如果直接公开并强传播,陌生开发者第一眼会先看到旧素材,而不是 AICO 的 absence-first 工作流。

**根因**
Stage 3 把"真实 Telegram dogfooding GIF 已生成并嵌入 README"视为完成项,但没有单独建立
D0 首印象验收:第一帧、时长、是否展示最新命令、是否适合 GitHub 首屏和 social preview。
发布材料的正确性不只取决于文件是否存在,还取决于它是否讲当前产品故事。

**解决方案 / 缓解措施**
- 不用文案粉饰旧 GIF,也不伪造一段看似真实的 Telegram 录屏。
- 在 README roadmap、GitHub publication checklist、launch playbook 和 shot rhythm 中标出:
  D0 前需要复剪 README GIF。
- 复剪要求:首帧是当前 IM 产品画面;控制在 30-60 秒;保留 `/team`、`/remember`、`/ask`、
  `/approve`、`/overnight`、`/morning`、`/view`、`/audit` 的最短闭环。
- GitHub social preview 另做静态 `1280 x 640` PNG,不要直接上传 README 动图。
- Round 148 新增 `examples/release-room/generate-public-gif.py`,生成稳定 transcript-driven
  README GIF 和 social preview;Round 149 根据人类反馈把首帧和 social preview 主文案改为明确
  boss-absent 假设:
  - `docs/assets/release-room-demo.gif`:约 36 秒、`960 x 540`,首帧明确 boss-absent 假设。
  - `docs/assets/social-preview.png`:`1280 x 640`,小于 1 MB,用于 GitHub Social preview。

**如何避免再次踩中**
- 发布前把 README GIF 当作 release gate,像 no-token demo 一样实际打开检查。
- 检查动图时至少看:第一帧、前 5 秒、最后 10 秒、总时长、是否有旧命令、是否露出旧聊天记录。
- 每次新增老板入口命令或改变接手动线后,同步搜索 README、release notes、demo script、
  transcript、shot rhythm 和 GIF 说明。
- 不要在 `STATUS.md` 里只写"GIF 已嵌入";要写它是否适合当前 D0 传播。
- 如果后续用真实 IM 精剪版替换 transcript-driven GIF,必须保持首帧、时长、`/morning`
  和 `/view` 展示质量不倒退。

**相关链接**
- ROUNDS Round 148
- ROUNDS Round 149
- ROUNDS Round 147
- P-038

### [P-040] 本机 dogfood `AICO_*` 环境变量污染单测

**状态**:🟢 RESOLVED
**首次踩中**:Round 157
**最后更新**:2026-06-14
**影响范围**:`tests/unit/conftest.py`, `tests/unit/test_aico_view_routes.py`, `tests/unit/test_aico_view_deep_link.py`, `tests/unit/test_phase1_app.py`

**症状**
在本机真实 dogfood shell 中运行 `uv run pytest -q` 时,完整测试出现 9 个失败:

- aico-view 路由测试期望本地 loopback 无 token 可访问,实际因 `AICO_VIEW_TOKEN` 存在返回 401。
- `Phase1Settings(...)` 单测期望 view snapshot handler 默认关闭,实际因 `AICO_VIEW_ENABLED=true`
  从环境注入而被开启。

Phase 8 contract gate 因显式 `env -u AICO_VIEW_TOKEN -u AICO_VIEW_ENABLED` 可以通过,但完整测试不应该依赖
调用者手动清理本机运行环境。

**根因**
项目本身鼓励真实 dogfooding,因此开发 shell 里经常保留 `AICO_TELEGRAM_BOT_TOKEN`、`AICO_VIEW_TOKEN`、
`AICO_VIEW_ENABLED`、`AICO_MEMORY_PATH` 等真实运行配置。单测里直接构造 `build_view_app()` 或
`Phase1Settings(...)` 时会读取当前进程环境,导致测试语义被本机状态污染。

**解决方案 / 缓解措施**
新增 `tests/unit/conftest.py` 的 autouse fixture,在每个 unit test 前清理当前进程中的 `AICO_*`
环境变量。需要测试环境读取行为的用例必须在测试函数里用 `monkeypatch.setenv(...)` 显式设置。

**如何避免再次踩中**
- 不要假设开发者 shell 是干净的;AICO 的本机 dogfood 配置很可能长期存在。
- 新增读取 `AICO_*` 环境变量的单测时,用 `monkeypatch.setenv` 声明输入,不要依赖外部环境。
- 如果新增非 unit 的 golden / smoke 测试确实需要真实环境变量,不要放进 `tests/unit/`。

**相关链接**
- ROUNDS Round 157
- NORTH_STAR.md Dogfooding 的验收分层

### [P-041] Telegram Desktop 实例与启动状态必须实测

**状态**:🟡 MITIGATED
**首次踩中**:Round 178
**最后更新**:2026-07-15(Round 191)
**影响范围**:真实 Telegram dogfood、Computer Use 验收、AICO IM baseline

**症状**
Round 178 尝试用 Computer Use 操作 Telegram 时,系统中同时存在:

- `/Applications/Telegram.app`:已登录,能看到 `ai_co` bot 对话。
- `/Applications/Telegram 2.app`:未登录,打开后是 QR code 登录页。

如果只按 bundle id `ru.keepcoder.Telegram` 操作,Computer Use 会认为 app identifier ambiguous。即使指定
已登录的 `/Applications/Telegram.app`,读屏可用,但 click 动作本轮返回 tool activation error。
Round 179 继续复验后,Computer Use 仍可渲染 Telegram 截图,但 click / key 均不可用;`open`、直接 executable
和 System Events 也不能稳定控制 Telegram 进程。

Round 191 复验时只剩 `/Applications/Telegram.app` 12.8(build 282010)。它启动后约 0.1 秒主动
以 exit 0 退出,macOS 没有生成 crash report;Telegram 自身日志显示加密数据库打开且网络握手已开始,
但没有明确 fatal。`codesign --verify` 报 `CSSMERR_TP_NOT_TRUSTED`,但该信号不足以证明它是主动退出的根因。

**根因**
同一 bundle id 下有两个 Telegram 安装实例,其中一个未登录。桌面自动化如果不指定准确 app path,容易进入错误实例或登录页。

**解决方案 / 缓解措施**
- 做真实 Telegram dogfood 前先用 Computer Use `list_apps` / `get_app_state` 确认 app path 和是否已登录。
- 不要使用 `/Applications/Telegram 2.app` 跑 AICO baseline,除非人类明确在该实例完成登录。
- 如果 Computer Use click 不稳定,把 exact IM commands 写入 evidence,由人类手动粘贴发送,agent 继续做可判定证据整理。
- 如果需要非人工证据,只能标注为 local injected IM baseline,不能写成真实 Telegram baseline。
- Round 191 起桌面 app 不可用时,优先复用已登录 Telegram Web;不在无根因证据时删除 group container
  或重置账号数据。

**如何避免再次踩中**
- 所有 Telegram dogfood runbook 写清楚目标 app path 和目标 bot/chat。
- 不要把“Telegram app 能打开”误判为“已登录且可发送到正确 bot”。
- 不要把未发送的 IM 命令登记为已完成 transcript。
- 不要把 Computer Use 截图能力误判为 Computer Use 操作能力。

**相关链接**
- ROUNDS Round 178
- ROUNDS Round 179
- B-007

### [P-042] 真实 Telegram 链路跑通但老板可读性仍失败

**状态**:🟢 RESOLVED
**首次踩中**:Round 181
**最后更新**:2026-07-06
**影响范围**:`src/aico/core/native_output.py`, `src/aico/core/streaming.py`,
`src/aico/core/inbox.py`, `src/aico/view/commands.py`

**症状**
data-agent-v1 真实 Telegram Web 聊天记录显示 `/ask lead`、`/inbox`、`/view` 已经真实送达,
后台 `logs/aico.log` 也能对上 task / adapter / sendMessage / editMessageText 链路。但老板端仍然很难读:

- agent 输出出现 `Findings1.`、`Missing Tests未...`、Markdown 表格和本地绝对路径原样露出。
- 流式分片虽然低于 1400 字,但会发出 3 字符或几十字符的尾片。
- `/inbox` 空状态仍展示多个 `none` 小节、audit event kind 和固定 Next 命令,像后台状态 dump。
- `/view` 只发 HTML 附件,没有告诉老板为什么要打开、打不开时该看什么。

**根因**
上一轮修复解决了“能发”和“不要超长墙”,但还把“Bot API 成功发送”和“老板能在手机上接手”混在一起。
当前流式 writer 按长度切分,没有按语义卡片切分;`/inbox` 直接暴露内部状态集合;`/view` 把附件当成完整交接。

**解决方案 / 缓解措施**
- `normalize_agent_output_for_im()` 增加普通标题粘连归一化,覆盖 `Findings1.`、编号项连续、`Missing Tests未...` 和 `Verdict:`。
- `StreamedMessageWriter` 对接近阅读上限的小尾片不再单独发消息,避免 Telegram 出现微型碎片。
- `StreamedMessageWriter` 进一步按 Summary / Findings / Decision / Risks / Next Actions 等老板语义卡片切分,卡片内部超长才回退长度切分。
- `normalize_agent_output_for_im()` 将本地 Markdown 文件链接简化为 `path:line`,避免 Telegram 暴露 `/Users/...` 绝对路径。
- `/inbox` 改为老板摘要:无动作时只说“当前无待处理事项”;有动作时优先显示一个下一步,再显示少量需要关注、运行中、交接和深挖入口。
- `/view` 在发送附件前先发中文说明,告诉老板用途和替代命令 `/inbox`、`/task <id>`。
- 新增/更新单测覆盖真实坏样本和新的老板摘要 contract,并新增 `test_telegram_ux_regression.py` 集中回归 `Findings1.`、本地路径链接和 Markdown 表格分隔符。

**如何避免再次踩中**
- 真实 IM 验收不能只看链路是否跑通;必须看第一屏是否能回答“现在要我做什么”。
- 长输出不要只按字符数切;先问是否能按 Findings / Decision / Risks / Next Actions 切成老板卡片。
- `/inbox`、`/morning`、`/view` 这类老板入口默认应隐藏内部 event kind,把原始审计留给 `/task`、`/why`、`/audit`。
- 每次修 Telegram 输出,都把真实坏样本固化成 unit test 或模拟 E2E,不要只依赖下一次人工截图。

**相关链接**
- ROUNDS Round 181
- P-036
- P-037

### [P-043] 表格渲染不能只看语法,要按移动端可读性分流

**状态**:🟢 RESOLVED
**首次踩中**:Round 183
**最后更新**:2026-07-09(Round 189)
**影响范围**:`src/aico/core/message_rendering.py`, `tests/unit/test_telegram_ux_regression.py`

**症状**
Round 182 后,回归测试已经覆盖 `|---|---|` 不应直接出现在 Telegram 输出里,但真实 Telegram Web
抽样仍然看到角色分工表格以 `| 角色 | seat | 状态 | 交付 |` 形式挤在一条气泡里。Round 184/186 又尝试让少行少列小表保留
为 Markdown 表格,但人类用真实 `/ask reviewer ... 小表、宽表、HTML list ...` 验收后反馈“表格是错乱的”。
Round 187 改成纯字段列表后,人类再次反馈“这是人能看懂的???”。结论是:Telegram 需要保留表格感,但不能裸发 pipe table;
需要紧凑等宽表格、压缩字符,并用 `/view` / `/task` 懒加载详情。

**根因**
测试把“Markdown 表格语法没有裸露”或“小表在桌面看起来还行”误当成“Telegram 气泡可读”。Telegram 气泡不是数据表容器,
pipe table 在手机和 Web 气泡里都会受到字体、换行、缩放和内容宽度影响。但把表格完全降级成字段列表也会丢失横向比较能力。
另一个真实坏样本是 provider 会把标题和表格粘在同一行,或把新表头行混在旧表格 body 中,
导致常规 Markdown table detector 根本识别不到表格结构。

**解决方案 / 缓解措施**
- Round 183 先把 Markdown 表格统一降级为 key-value 列表,快速解决宽表手机不可读。
- Round 184/186 的“小表保留”策略被真实 Telegram 验收推翻。
- Round 187 最终改为无裸表格策略:
  - 所有 Markdown 表格都降级为 key-value 字段列表;
  - 表头作为字段 label,在 Telegram HTML payload 中加粗;
  - 缺失表头的额外列不再显示 `col 4`,改为 `补充`,避免把实现细节暴露给老板;
  - native Telegram prompt 明确要求不要输出 Markdown table,也不要用 `<pre>` 包表格。
- Round 188 根据人类反馈修正最终策略:
  - 不裸发 pipe Markdown table,但尽量保留表格形态;
  - 表格渲染为紧凑等宽 Telegram 表格,长单元格截断;
  - 截断或列数较多时追加 `详情: /view 查看完整表格`;
  - 缺失表头的额外列使用 `补充1/补充2`,避免多个 `补充` 混在一起;
  - 当表格 body 中出现更宽的行,且后续行同宽,把该行识别为嵌入的新表头,避免把真实列名渲染成一串补充字段。
- Round 189 补齐 native Telegram HTML 缺口:
  - 如果模型把 Markdown pipe table 放进 `<pre>`,native validator 先把允许的 HTML tag 去掉再检测 Markdown table;
  - 命中后不允许 native HTML 直通,而是回退到平台中立 renderer 生成紧凑表格;
  - `<pre>` 中的 Markdown table 回退时不再继续作为 fenced code block,避免 `详情: /view 查看完整表格` 被整行 code span 吃掉。
- `_split_glued_markdown_tables()` 在渲染前识别 `||---|...` 一类 glued table,先拆回多行再转紧凑表格。
- `tests/unit/test_telegram_ux_regression.py` 同时覆盖小表紧凑表格、宽表截断、glued table、malformed table extra cell、
  嵌入式宽表表头和“小表 + 宽表 + HTML list”展示样例。

**如何避免再次踩中**
- Telegram / Feishu / Kim 等 IM 输出不要裸发 pipe table,也不要一律字段列表;默认紧凑表格,详情交给 `/view` / `/task`。
- 表格类回归测试必须断言最终阅读形态,不只断言分隔符消失。
- 遇到真实 IM 反馈“好不好看”时,要把审美/可扫读规则转成可测试阈值,不要只靠下一次截图。

**相关链接**
- ROUNDS Round 183
- ROUNDS Round 184
- ROUNDS Round 187
- ROUNDS Round 188
- ROUNDS Round 189
- P-030
- P-042

### [P-044] 短格式验收 prompt 被协作链放大

**状态**:🟢 RESOLVED
**首次踩中**:Round 184
**最后更新**:2026-07-21(Round 194)
**影响范围**:`src/aico/core/orchestrator.py`, `src/aico/core/lead_decision.py`,
`src/aico/core/project_assignment.py`, `src/aico/adapter/claude_code.py`, Telegram E2E

**症状**
data-agent-v1 真实 Telegram E2E 中,人类只要求验证表格渲染和 active project 恢复,并明确“不要改文件”。
但 `/ask lead ...` 仍自动触发 reviewer / challenger / implementer 多任务链:

- 第 1 条格式验收 prompt 产出了可用表格,随后又触发 `Collaboration requested source: lead target: reviewer`。
- reviewer/codex 超过 120 秒无输出,Telegram 出现 `Still running: no adapter output for 120s`。
- 第 2 条请求撞上 Claude provider session 并发,直接回 `Session ID ... is already in use`。
- 第 4 条虽然指定 `/ask lead`,日志显示任务先路由到 reviewer/codex,随后又派生 implementer/claude。
- 输出还出现 `FindingsHigh:`、`Risks / approval need-`、`今日验收 3 条要点1.` 这类粘连。

**根因**
当前 `/ask <role>` 缺少“短验收 / exact-output / no-collab”模式。role prompt 和 provider 输出里的
consult/reviewer/challenger 语义容易触发协作解析,导致本应一次性返回的格式样本被编排成多 agent 链。
同时 provider session 并发没有老板可读的排队/新 session 策略,所以第二个请求会把底层 session 占用错误原样暴露到 Telegram。

**解决方案 / 缓解措施**
- Round 193 已完成:
  - 新增 `/ask --exact <role> <task>`,并自动识别“不要请求协作/不要 @/只输出本条/do not delegate”等明确约束。
  - exact-output task 写入 `aico.collaboration_mode=disabled`,跳过 lead decision / Goal Brief 自动扩展;
    stream parser 即使看到 `@role` 也不会创建 child task 或 `collaboration_requested` audit。
  - `/ask lead|default` 解析到实际 role 时,IM 先显示 `Routing: <alias> -> <role> (<agent>)`。
  - 标题粘连由 Round 186-192 的 native output / renderer golden loop 覆盖。
- Round 194 已完成:
  - presentation 层识别 provider session busy 签名,即时 IM 返回 role busy、`/tasks`、等待或 `/interrupt`、重试路径。
  - `/tasks`、`/audit`、`/inbox`、`/morning`、project 摘要与 aico-view 使用老板可读摘要,不暴露 session id。
  - 原始错误仍保留在 TaskBus snapshot/audit 和显式 `/task`;未知 provider 错误不被分类器吞掉。
  - 不自动新建 session,避免在老板不知情时切断岗位的 provider 会话连续性。

**如何避免再次踩中**
- 修真实 IM UX 时,不要只看目标功能是否生效;同时检查是否引入额外协作、额外任务和 provider session 争用。
- E2E prompt 如果用于格式验收,应有明确的 no-collab 合同并用单测覆盖。
- 任何底层 provider session 错误都必须翻译成老板可执行语言,原始错误只进 `/task` / logs。

**相关链接**
- ROUNDS Round 184
- ROUNDS Round 193
- ROUNDS Round 194
- P-042

### [P-045] Dream 候选经验不能被当成普通 shared memory 或 `/remember` 流程

**状态**:🟢 RESOLVED
**首次踩中**:Round 185
**最后更新**:2026-07-07
**影响范围**:`src/aico/core/dream.py`, `src/aico/core/memory.py`, `tests/unit/test_pop_culture_memory_dream_showcase.py`

**症状**
在设计“芙莉莲式长记忆旅队”和“无限城作战会议”两个热点叙事化验证 case 时,发现两处产品表达不一致:

- `/dream` 已经把近期 task 信号写成 `kind=experience` + `status=candidate`,但下一步仍提示
  `/remember <accepted lesson>`,把用户带回事实记忆入口。
- `MemoryGovernor` 没有区分 `kind=fact` 和 `kind=experience`,导致 promoted experience 可能同时出现在
  `Shared memory` 和 `Reusable experience` 两个 prompt section。

同时 case 设计还暴露了一个客观规律:shared memory retrieval 不是读心。如果任务 query 和记忆 claim 没有可解释关联,
就不应该强行声称系统“记住并召回”。

**根因**
M1/M2 后 experience 已从普通 memory 演化出独立生命周期,但 `/dream` 文案和 Shared memory governor 仍沿用早期
“memory atom 都是事实”的心智模型。热点宣传 case 容易为了生动而把产品能力讲过头,从而掩盖真实边界。

**解决方案 / 缓解措施**
- `MemoryGovernor.allows()` 明确只允许 `MemoryKind.FACT` 进入 Shared memory packet。
- `dream_review_message()` 的 Next 改为:
  - `/experience review`
  - `/experience promote <candidate-id> as <role>`
- 新增 `tests/unit/test_pop_culture_memory_dream_showcase.py`,用两个可传播 case 验证 shared memory、dream candidate、
  experience promote、collaboration audit 的真实链路。
- showcase 文档显式写明 objective-reality review:任务文本必须和记忆有可解释关联;candidate experience 不会自动注入。

**如何避免再次踩中**
- 凡是输出 `kind=experience` 的入口,下一步必须指向 `/experience` 生命周期,不要回到 `/remember`。
- Shared memory 文案只承诺事实记忆,experience 单独放在 Experience layer。
- 宣传 case 要先写“客观边界”,再写“宣传话术”;不要为了借热点 IP 把检索、推理和自动学习讲成魔法。

**相关链接**
- ROUNDS Round 185
- ADR-0031
- `docs/showcase/frieren-memory-dream-case.md`
- `docs/showcase/infinity-castle-memory-dream-case.md`

### [P-046] Telegram Web 不是稳定的自动化发送 harness

**状态**:🟡 MITIGATED
**首次踩中**:Round 186
**最后更新**:2026-07-15(Round 191)
**影响范围**:Telegram E2E, Computer Use, `src/aico/channel/telegram.py`, `tests/unit/test_telegram_channel.py`

**症状**
Round 186 重启本机 `aico-phase1` 并打开已登录的 Telegram Web 后,输入框里能看到待发送的 `/inbox`,
但自动化点击发送按钮、Space、Return 都没有让消息进入聊天。Accessibility tree 显示焦点在发送按钮,
输入框内容仍保留 `/inbox`,因此不能把这次操作记为真实 Telegram 新消息验证。

**根因**
Telegram Web 的 contenteditable 输入框、图标按钮和浏览器 accessibility bridge 对自动化不稳定。
Computer Use 能读到聊天历史和控件树,但“点击按钮 == 提交消息”这个假设不可靠。继续依赖 UI 点击会带来
两类风险:把未发送消息误判成已发送,或把旧聊天记录误判成新代码的实端证据。

**解决方案 / 缓解措施**
- 本轮用 mock Bot API payload golden 覆盖可编程出口:
  - 宽表最终进入 `sendMessage` payload 时必须是字段列表;
  - HTML list fallback 不能包含 unsupported `<ul>/<li>`。
- 真实 Telegram Web 只能作为肉眼观察补充,不能作为自动发送 harness。
- 后续若要 agent 自闭环真实 E2E,优先新增受控的 Telegram dogfood harness:
  - 通过测试 Bot token + test chat id 明确配置;
  - 不从日志或进程环境泄漏 token;
  - 每次测试记录 message id、输入命令、最终 payload / 可见文本和截图或 transcript。
- Round 191 确认 Chrome Telegram Web 可以做受控 E2E,但不能把页面中唯一的 Playwright `textbox`
  当成消息输入框:它实际是左侧搜索框。消息 composer 是 `div[contenteditable=true]`,需在当前可见 DOM
  中定位后发送,再以当日时间、runtime 入站日志和最新气泡三方确认。
- 同轮使用真实 Bot API 发送确定性样例,Telegram Web DOM 确认最终表格为 `PRE > CODE`,
  因此 Web 当前可作为“可编程发送 + 真实客户端视觉”验收表面,但仍要保留 payload golden 作为稳定 Gate。

**如何避免再次踩中**
- “实端验证”必须区分三层证据:本地 renderer golden、Bot API payload golden、真实客户端视觉样本。
- 不要把旧 Telegram 聊天历史、未提交输入框内容或单纯按钮焦点变化当作新代码证据。
- UI 自动化失败时及时转向可编程 harness,不要靠反复点按钮碰运气。

**相关链接**
- ROUNDS Round 186
- P-043
- P-044

### [P-049] 紧凑表格的连续 code 行必须合并成单个 Telegram `<pre>`

**状态**:🟢 RESOLVED
**首次踩中**:Round 191
**最后更新**:2026-07-15
**影响范围**:`src/aico/channel/telegram.py`,`tests/unit/test_telegram_channel.py`,Telegram Web 表格体感

**症状**
Core renderer 已经把 Markdown table 压缩成对齐的等宽文本,但每行各自带一个 `MessageTextStyle.CODE`
span。Telegram Channel 按 span 逐个转 HTML,导致一张表变成多个 `<code>...</code>` 行。真实客户端无法把它
当作同一个可复制、列对齐的表格块,看起来仍像拼接文本。

**根因**
Core 的 code span 是平台中立 IR,`CODE` 同时表示行内命令和整行等宽内容。Telegram Channel 之前只做一对一
tag 映射,没有识别“连续整行 code spans”这个平台级块结构。

**解决方案 / 缓解措施**
- Telegram Channel 仅在至少两个 code span 都占据完整行、彼此只差一个换行时,合并为单个 `<pre>`。
- 单个整行 code 和普通行内 code 仍映射为 `<code>`,避免把 `/view` 等命令误放大。
- payload 测试断言每张表恰好一个 `<pre>`,不含 `<code>Option...`,且 `/view` 位于块外。
- 真实 Telegram Web DOM 确认为一个 `PRE > CODE`,并显示客户端复制控件。

**如何避免再次踩中**
- 不要把“HTML 中有 code tag”当成“Telegram 中是表格块”;payload 必须区分 `<pre>` 和多个 `<code>`。
- 平台中立 renderer 负责生成对齐内容,Channel 负责生成平台原生块,不为此向 core 引入 Telegram 专用模型。

**相关链接**
- ROUNDS Round 191
- P-043
- P-047

### [P-047] native `<pre>` 包 Markdown 表格会绕过紧凑表格 renderer

**状态**:🟢 RESOLVED
**首次踩中**:Round 189
**最后更新**:2026-07-09
**影响范围**:`src/aico/core/native_output.py`, `src/aico/channel/telegram.py`,
`tests/unit/test_native_output.py`, `tests/unit/test_telegram_channel.py`

**症状**
Round 188 已经让普通 Markdown table 渲染为紧凑 Telegram 表格,但 Round 189 端到端 mock Bot API 检查发现:
如果 agent 在 native Telegram HTML 模式下输出:

```html
<pre>| Option | Decision | Owner | Evidence |
|---|---|---|---|
| Start v2 | Reject | lead | needs another full benchmark cycle |</pre>
```

`telegram_html_message()` 会把整段当作合法 native HTML 直通,最终 `sendMessage` payload 中仍包含 raw
`|---|---|---|---|`。这会绕过紧凑表格截断和 `/view` 懒加载提示。

**根因**
native HTML validator 只检查标签白名单和原始文本中的 Markdown table 结构。`<pre>` 是允许标签,
而第一行实际变成 `<pre>| Option ...`,不再匹配“行首是 `|` 的 Markdown table”正则。
第一次修复只让这类内容回退,但因为 `<pre>` fallback 会转成 fenced code block,
`详情: /view 查看完整表格` 也会被当作 code block 的一部分,Telegram 中不可点击也不可突出。

**解决方案 / 缓解措施**
- `_contains_markdown_structure()` 改为先生成去除允许 HTML tag 的检测文本,再判断 Markdown table。
- `_telegram_html_to_light_markdown()` 对 `<pre>` 内容分流:
  - 普通代码 / 日志仍转 fenced code block;
  - Markdown table 内容直接交还给 rich text renderer,生成紧凑等宽表格和独立的 `详情: /view 查看完整表格`。
- 新增 native output 回归和 Telegram Channel payload golden:
  - `telegram_html_message()` 拒绝 `<pre>` 包 Markdown table;
  - `agent_output_message(..., preferred_format=TELEGRAM_HTML)` 会回退到紧凑表格;
  - mock Bot API `sendMessage` payload 不含 raw `|---|`,且 `/view` 单独作为 code slash command。

**如何避免再次踩中**
- native format 不是可信终态;即使 tag 合法,也要检查里面是否藏了当前 Channel 不适合直通的结构。
- `<pre>` 只适合真正的代码 / 日志 / 已压缩表格;如果内容仍是 Markdown table,必须回到 renderer 统一处理。
- Bot API payload golden 要覆盖 native HTML fallback 路径,不能只测普通 Markdown 输入。

**相关链接**
- ROUNDS Round 189
- P-031
- P-043

### [P-048] Dream candidate experience 不能只藏在 `/experience review`

**状态**:🟢 RESOLVED
**首次踩中**:Round 190
**最后更新**:2026-07-09
**影响范围**:`src/aico/core/dream.py`, `src/aico/core/inbox.py`, `src/aico/core/morning.py`,
`src/aico/core/experience_commands.py`, `tests/unit/test_pop_culture_memory_dream_showcase.py`

**症状**
Round 185 已经修正 `/dream` 输出,让它产生 `kind=experience,status=candidate` 的候选经验,
并提示 `/experience review` / `/experience promote`。但人类进一步指出:如果老板或 lead 不知道系统 dream 出了哪些候选,
就无法决定是否把它赋给 role agent。候选经验虽然存在于 memory store,却没有进入老板恢复入口,动线仍不省心。

**根因**
`/experience review` 是显式管理命令,不是 boss-absent 的主动恢复入口。之前的实现把“候选经验已生成”和“老板知道需要确认”
混为一谈,导致 `/dream` 后的状态只有主动查询才可见。对 absence-first 产品来说,隐藏在后台的 candidate 不能算闭环。

**解决方案 / 缓解措施**
- `/inbox` 新增“经验候选”区,显示候选 id、claim、`/experience promote <id> as <role>` 和 `/experience archive <id>`。
- `/morning` 新增 `Experience candidates` 区,并把 `/experience review` 放进 Next actions。
- Orchestrator 在当前项目 `/inbox`、`/morning` 和自动 morning push 时,查询 memory store 中 `status=candidate` 的 experience。
- 端到端测试覆盖:
  - 同意路径:候选出现在 `/inbox` / `/morning`,promote 后变 active,后续注入 role prompt;
  - 不同意路径:候选出现在 `/inbox` / `/morning`,archive 后从待审队列消失,后续不注入 role prompt。

**如何避免再次踩中**
- 凡是系统/lead 产生需要老板确认的对象,都必须进入 `/inbox` 或 `/morning`,不能只提供后台查询命令。
- candidate 状态可以不可自动注入,但必须可发现、可确认、可消失。
- 新增候选类生命周期时,测试至少覆盖 accept 和 reject/archive 两条路。

**相关链接**
- ROUNDS Round 190
- ADR-0031

### [P-050] 已闭合 Markdown 表格后的粘连正文不能算额外列

**状态**:🟢 RESOLVED
**首次踩中**:Round 192
**最后更新**:2026-07-17
**影响范围**:`src/aico/core/message_rendering.py`,`tests/unit/test_message_rendering.py`,Telegram 表格体感

**症状**
真实 reviewer 按要求输出四列表格和 `详情命令: /view`,但流式拼接后的末行形如
`| 宽表 | 受控 | lead | ... |详情命令: /view`。旧 parser 按所有 pipe 切分,将详情文案当成第 5 列,
最终 Telegram 显示虚假的 `补充1` 和被截断的 `详情命…`。

**根因**
`_table_cells()` 不区分表头声明的列数和完整表格闭合 pipe 后的普通正文。
之前为了兼容真实行列不齐表格,renderer 会扩展缺失表头为 `补充1/补充2`,因此粘连正文被合理但错误地纳入该兼容路径。

**解决方案 / 缓解措施**
- 收集 body row 时以表头列数定位闭合 pipe;其后若是可识别的 `详情: /view` 或 `详情命令: /view` 提示,
  将其拆回表格外。
- 其他后续 cell 按真正额外业务列处理,即使省略末尾 pipe 也继续保留 `补充N` 兼容行为。
- 拆出的正文与自动 `详情: /view 查看完整表格` 等价时去重。
- 用真实四列表格坏签名做 red-green 回归,断言无 `补充1`、无 `详情命…` 且只出现一次 `/view`。

**如何避免再次踩中**
- 表格修复不能只看最大 cell 数;必须同时考虑表头契约和表格闭合边界。
- 不要为消除 `补充1` 全局丢弃额外 cell,否则会破坏 P-043 的 malformed table 兼容。
- 每次真实 provider 输出暴露新坏签名,先保留原始形态写回归,再调整 renderer。

**相关链接**
- ROUNDS Round 192
- P-043
- P-049

### [P-051] Telegram TLS 建连超时会让已完成的 agent 结果丢在回执阶段

**状态**:🟢 RESOLVED
**首次踩中**:Round 192
**最后更新**:2026-07-17
**影响范围**:`src/aico/channel/telegram.py`,`tests/unit/test_telegram_channel.py`,真实 `/ask` 链路

**症状**
真实 `/ask reviewer` 中,Codex Adapter 已 accepted 并最终 return code 0,但 Telegram 发送 accepted 回执时
`httpx.ConnectTimeout` 从 `_post()` 直接向上抛出,handler 提前失败,最终 agent 正文没有进入 Telegram。

**根因**
Channel 对 long polling 有外层失败恢复,但单次出站 `sendMessage/editMessageText/sendDocument` 没有连接阶段重试。
TLS 握手抖动因此会中断整个 orchestrator handler,即使 provider 任务本身已经完成。

**解决方案 / 缓解措施**
- JSON 和 multipart 出站请求共用 `_request_with_connect_retry()`。
- 仅捕获 `httpx.ConnectTimeout`,最多重试一次;第二次失败继续向上抛出并保留日志。
- 不重试 read/write timeout 或 Telegram API 业务错误,避免请求已送达时产生重复消息。
- MockTransport 回归先让第一次连接失败、第二次成功,断言最终 message id 和两次尝试。

**如何避免再次踩中**
- 对 IM 出站重试要按故障阶段分类,不能笼统捕获 `HTTPError`。
- 可靠性修复必须同时评估“结果丢失”和“重复消息”两侧风险。
- 真实 E2E 要检查 `handler finished`,只看到 adapter return code 0 不能算闭环。

**相关链接**
- ROUNDS Round 192
- P-037
- P-046

### [P-052] 项目标题不能代替 attachment 数据隔离

**状态**:🟢 RESOLVED
**首次踩中**:Round 197
**最后更新**:2026-07-21
**影响范围**:`src/aico/view/snapshot.py`,`src/aico/core/offline_delegation.py`, `/view <project>`

**症状**
旧 `/view` HTML 标题显示当前项目,但 snapshot builder 全量读取 SQLite task snapshots 和 audit JSONL。
当同一 runtime 管理多个项目时,另一个项目的任务描述、失败原因或 audit detail 可能出现在当前项目附件里。

**根因**
`ViewSettings.project_ids` 只约束 memory loader;task/audit 没有 project filter。渲染层把 project id 当作
展示参数,没有把它当作所有 truth source 的强制查询边界。

**解决方案 / 缓解措施**
- task record/snapshot 先用 `aico.project_id` 严格筛选。
- audit 只接收当前项目 task id 对应事件;memory 再校验 scope project;offline delegation 增加跨 IM scope 的 project loader。
- 统一索引只从上述 project-scoped 数据重建,再渲染 Boss Brief、Timeline、Trace 和 Memory。
- 回归同时种入另一个项目的 task reason、audit detail 和 overnight goal,断言附件完全不含这些 canary。

**如何避免再次踩中**
- 多源 read model 的 scope 必须在聚合前执行,不能靠标题、路由或最终模板暗示隔离。
- 新增 truth source 时,project isolation canary 必须和正常展示测试一起补。

**相关链接**
- ROUNDS Round 197
- B-009
- ADR-0036

### [P-053] 隐私提示文案不能代替商业输出硬门禁

**状态**:🟢 RESOLVED
**首次踩中**:Round 198
**最后更新**:2026-07-21
**影响范围**:`projects/sme-agent/src/sme_agent/commercialization/workbench.py`,`live_commerce_delivery.py`

**症状**
SME Agent workbench 会提示先脱敏,但带 `手机号` 的 CSV 仍可能展示并复制诊断;同一证据进入 governed delivery runner 时却会正确阻断。

**根因**
UI 把隐私要求当说明文案,没有复用交付层的 readiness/redaction 状态,导致浏览面和持久化交付面产生安全漂移。

**解决方案 / 缓解措施**
- 抽出无副作用 delivery preview,与 runner 共用 intake assessment、redaction scanner 和状态判定。
- `blocked_redaction` 统一隐藏指标、finding、报告、复制动作和付费验收控件,同时显示具体风险字段和下一动作。
- 用 `手机号` 回归同时断言报告为空、copy disabled、diagnosis artifact 不生成。

**如何避免再次踩中**
- 合规/隐私文案只负责解释,不能作为 gate 的证据。
- 同一输入经过 preview、UI 和 runner 必须得到相同 delivery status;新产品面必须用 blocked canary 做契约测试。

**相关链接**
- ROUNDS Round 198
- SME Agent P-005
- ADR-0003

### [P-054] Standing charter 是提议范围,不是 lead 的隐式执行授权

**状态**:🟢 RESOLVED
**首次踩中**:Round 199
**最后更新**:2026-07-21
**影响范围**:`src/aico/core/standing_proposal.py`,项目配置,`/inbox`,`/morning`

**症状**
如果把“老板不在时 lead 要主动”直接实现为定时创建任务,岗位职责会被误当成执行授权。即使 TaskBus 仍能拦截部分风险,只读或未识别动作也会在老板没有看到目标、验收和停止条件时启动。

**根因**
把 initiative、authorization 和 execution 合并成一个状态转换,没有给老板留下可审核的中间事实。

**解决方案 / 缓解措施**
- standing charter 只能生成 `candidate`,不能生成 task。
- candidate 持久化并进入 inbox/morning;只有唯一候选被 `/proposal accept` 后才创建正常项目任务。
- accept 不授予新权限,继续经过 risk/approval/audit/interrupt;reject 只写决定和 cooldown。
- charter 必须显式写验收证据与停止条件,不得从 Markdown 或 LLM 即兴推断。

**如何避免再次踩中**
- 新主动触发器必须复用 candidate → human decision → governed task 三段式。
- 任何外部发布、付款、客户数据和法律动作都需要独立授权,不得写进 charter 后视为已批准。

**相关链接**
- ROUNDS Round 199
- ADR-0037

### [P-055] Non-blocking Channel start 不能用局部 finally 管 scheduler 生命周期

**状态**:🟢 RESOLVED
**首次踩中**:Round 200
**最后更新**:2026-07-21
**影响范围**:`src/aico/app/phase1.py`,morning push,boss-absent local runtime

**症状**
`Phase1Runtime.start()` 先启动 morning scheduler,再 `await channel.start()`;Telegram/Feishu Channel 的
`start()` 负责创建后台任务后即可返回。旧实现用同一方法的 `finally` stop scheduler,因此 runtime 看似成功启动,
但定时早报实际上会立刻被取消。

**根因**
把“启动调用结束”误当成“runtime 生命周期结束”。对 non-blocking component,start/stop 生命周期必须由
外层 runtime owner 配对,不能用 start 方法内部的 unconditional cleanup。

**解决方案 / 缓解措施**
- `Phase1Runtime.start()` 只在 channel start 抛错时回滚 scheduler。
- `Phase1Runtime.stop()` 才停止 scheduler 和 channel;`run_phase1()` 负责持有进程直到 shutdown。
- 新增 fake non-blocking Channel 回归,断言 start 返回后 scheduler 仍在运行,stop 后恰好清理;启动失败也会回滚。
- 同轮加入 launchd service + heartbeat,把“进程活着”和“IM/provider 健康”分开诊断。

**如何避免再次踩中**
- 所有后台组件必须明确谁拥有 lifetime;non-blocking `start()` 不能用 finally 做正常 stop。
- 定时能力验收至少包含 start returned → still alive → explicit stop 三阶段,不能只断言 start 被调用。
- heartbeat 只证明本地进程存活,真实 Channel/provider 仍需独立 E2E 样本。

**相关链接**
- ROUNDS Round 200
- ADR-0038
- B-010

### [P-056] Fresh process heartbeat 不能代表后台组件仍可工作

**状态**:🟢 RESOLVED
**首次踩中**:Round 201
**最后更新**:2026-07-21
**影响范围**:`src/aico/app/runtime_health.py`,`runtime_heartbeat.py`,`telegram.py`,`morning_scheduler.py`,`aico-service doctor`

**症状**
Round 200 的 heartbeat task 可以每 30 秒持续写 fresh,但它与 Telegram polling task、默认 Adapter 和
morning scheduler 没有因果关系。polling task 因未预期异常退出后,Python event loop 仍活着,launchd 不会重启,
doctor 仍可能显示 healthy,形成老板缺席时最危险的静默失联。

**根因**
只建立了 process liveness,没有建立 owned background component 与 primary business path 的健康模型;
同时把所有 plugin 视为同等重要会走向另一个错误:一个可选 Adapter 离线就宣告整家公司不可用。

**解决方案 / 缓解措施**
- heartbeat schema v2 每轮并发检查 Channel、default/optional Adapter 和 enabled scheduler,每个检查受 timeout 限制。
- active Channel、default Adapter、enabled scheduler 标 required;其失败聚合 FAILED,optional Adapter 失败聚合 DEGRADED。
- Telegram `health_check()` 同时验证 owned polling task;polling/scheduler task 异常退出后 stop 安全消费异常。
- 插件 exception 只转成 status,不持久化 exception text;doctor 分开报告 stale、failed、degraded 和 legacy unknown。

**如何避免再次踩中**
- 每个长期后台 task 必须回答谁拥有、如何判断已死、谁消费异常、怎样进入 operator health。
- liveness、readiness、synthetic dependency health 和真实 E2E 是四层证据,文档/doctor 不得混写。
- required/optional 必须由业务主路径决定;不要用“任一失败全红”制造告警疲劳。
- 外部网络失败不要直接触发 crash loop;自动恢复必须另有阈值、退避和证据。

**相关链接**
- ROUNDS Round 201
- ADR-0039
- B-010

### [P-057] Service supervisor 必须启动 Channel 的真实入站入口

**状态**:🟢 RESOLVED
**首次踩中**:Round 201
**最后更新**:2026-07-21
**影响范围**:`src/aico/app/service_cli.py`,`phase1.py`,`feishu_webhook.py`

**症状**
Round 200 的 LaunchAgent 固定运行 `.venv/bin/aico-phase1`。Telegram 的入站是该进程内 long polling,
但 Feishu 的入站必须由 `aico-feishu-webhook` 暴露 FastAPI callback。配置 `AICO_CHANNEL=feishu` 时服务可以
进程存活、甚至拿到 tenant token,却没有任何 webhook listener 接收消息。

**根因**
把“Channel plugin”误当成“所有 Channel 共享同一个进程 entrypoint”。核心协议统一不代表部署入口相同;
同时 heartbeat lifecycle 只写在 Telegram CLI 的 `run_phase1`,Feishu webhook lifespan 没有复用。

**解决方案 / 缓解措施**
- `ServiceContext` 从 `.env` 只读取非敏感 Channel selector,Telegram 选择 `aico-phase1`,Feishu 选择 `aico-feishu-webhook`。
- 提取共享 `phase1_runtime_lifespan`,统一 runtime start → heartbeat start → runtime stop → heartbeat stop。
- plist golden 覆盖 Feishu executable,FastAPI lifespan 回归覆盖 heartbeat running/stopped;plist 仍不包含 secret。

**如何避免再次踩中**
- 每个 Channel 上线时必须分别验证 plugin contract、入站 transport entrypoint 和 supervisor command,三者缺一不可。
- 多入口 runtime 的 lifecycle/health 必须共享一个 owner,不要复制两套 start/stop。
- “进程已启动”必须与“入站 socket/polling 已存在”分别取证。

**相关链接**
- ROUNDS Round 201
- ADR-0039
- B-010

### [P-058] 持久化 RUNNING 不代表重启后仍有执行所有权

**状态**:🟢 RESOLVED
**首次踩中**:Round 202
**最后更新**:2026-07-21
**影响范围**:`src/aico/core/task_state.py`,`src/aico/core/task_bus.py`,SQLite task state,老板恢复视图

**症状**
LaunchAgent crash/restart 后,新 TaskBus 从 SQLite 原样载入旧 `RUNNING`。但旧进程持有的 Adapter subprocess、
stdout stream 和 interrupt handle 都无法恢复,所以 `/tasks`、`/inbox`、`/morning` 会永久显示一个无人拥有的
ghost running task。

**根因**
把“最后一次持久化的业务状态”误当成“当前进程仍拥有执行控制权”。状态可恢复不等于进程、流和外部副作用可恢复;
自动重新 dispatch 还可能重复写文件、发消息、发布或付款。

**解决方案 / 缓解措施**
- 新 runtime 加载持久化 snapshot 后,先把所有旧 `RUNNING` 写回 `INTERRUPTED`,再暴露 read model。
- reason 明确 runtime restarted、execution ownership lost,并要求 retry 前核对外部副作用。
- 每个本轮对账任务记录一次 `TASK_INTERRUPTED`;状态写回后再次 restart 不重复处理。
- `WAITING_APPROVAL` 保持 pending,终态保持不变;task/Adapter/risk/metadata/created time 均保留。

**如何避免再次踩中**
- 每个持久化“运行中”状态都必须说明 lease/owner 是否也可恢复;没有 owner 就不能继续显示 active。
- 没有 idempotency key 和 side-effect contract 时禁止 startup auto replay。
- restart 测试必须覆盖 running、waiting approval、terminal、第二次 restart 和老板 read model,不能只测 SQLite round-trip。
- 当前 SQLite 明确单 runtime owner;支持多 runtime 前必须先有 lease/leader election,不能复用本对账逻辑硬撑。

**相关链接**
- ROUNDS Round 202
- ADR-0040
- Goal Brief `docs/superpowers/specs/2026-07-21-restart-task-reconciliation.md`
- B-010

### [P-059] 状态恢复与审计顺序双写会在 crash 中永久分裂

**状态**:🟢 RESOLVED
**首次踩中**:Round 203
**最后更新**:2026-07-21
**影响范围**:`task_store.py`,`audit.py`,`task_state.py`,`task_bus.py`,SQLite schema,JSONL audit

**症状**
Round 202 先把 `RUNNING` snapshot 提交为 `INTERRUPTED`,再追加 `TASK_INTERRUPTED` JSONL。若进程或 sink 在两步
之间失败,业务状态已收口,但恢复审计永久缺失;后续 startup 看不到 `RUNNING`,也就不知道还应补写事件。

**根因**
把两个独立 truth source 的顺序调用误当成一个恢复动作。交换顺序只会把问题变成“有 audit、状态仍 running”或
重复 audit;普通 try/retry 也无法判断 append 是否已成功后才抛错。

**解决方案 / 缓解措施**
- SQLite schema v3 增加专用 recovery audit outbox,在同一 `BEGIN IMMEDIATE` transaction 写 snapshot 与完整事件。
- TaskBus startup 加载所有 pending event,投递成功后才标 delivered;sink 失败保留 intent。
- outbox 保存完整 `AuditEvent` 和稳定 event id,重试不重建 timestamp/trace/actor。
- `InMemoryAuditLog` 与内置 `JsonlAuditSink` 按 event id 幂等,同 id 不同内容报错;JSONL 启动建索引,后续 O(1)。
- `aico-state` 显示 `pending_recovery_audits`,reset 同时清理 outbox。

**如何避免再次踩中**
- 任何“状态改变 + 外部证据”都要逐点画出 crash window,不能只测 happy-path 顺序。
- outbox 必须保存完整、不可变的 delivery payload;只存 task id 会让 retry 内容漂移。
- ack 必须发生在 sink 返回成功后;失败路径测试要证明 intent 仍 pending。
- 幂等只对稳定 id 有意义;碰撞必须 fail loud,不能覆盖或吞掉不同内容。
- 本方案只保证当前 single-runtime + built-in JSONL 路径,不得宣传为分布式 exactly-once。

**相关链接**
- ROUNDS Round 203
- ADR-0041
- Goal Brief `docs/superpowers/specs/2026-07-21-recovery-audit-outbox.md`
- P-058
- B-010

### [P-060] 文档声明 single runtime 不能阻止第二进程破坏 live state

**状态**:🟢 RESOLVED
**首次踩中**:Round 204
**最后更新**:2026-07-21
**影响范围**:`runtime_owner.py`,`phase1.py`,`task_bus.py`,`service_cli.py`,Telegram/Feishu runtime lifecycle

**症状**
Round 202/203 只在 ADR 中声明 SQLite 是 single-runtime owner。若 runtime A 仍在执行任务,runtime B 构造 TaskBus
时会立即把 A 的 `RUNNING` 当 orphan 改为 `INTERRUPTED`;随后还可能启动第二个 Telegram poller、Feishu webhook 或
morning scheduler。

**根因**
把部署假设当成了执行契约,并让 destructive startup reconciliation 发生在 ownership 证明之前。普通 PID file
又会在 crash 后 stale,不能作为可靠 owner 事实。

**解决方案 / 缓解措施**
- 同 canonical state DB 派生同一 `.owner.lock`,以 kernel `flock(LOCK_EX|LOCK_NB)` 持有完整 runtime lifetime。
- `TaskBus.__init__` 只加载状态,正式 Phase1 runtime acquire 成功后才显式 recovery。
- competing owner 在任何 SQLite mutation/scheduler/Channel start 前 fail closed,不等待、不 kill。
- normal stop/start failure 显式 release;process kill 由 kernel 自动 release,metadata file 可保留但不代表 active。
- shutdown 顺序改为 heartbeat → Channel/scheduler → owner,避免旧 heartbeat 在 lock 释放后覆盖新 owner。
- doctor 同时验证 kernel owner active、owner PID 与 launchd PID一致;manual owner/launchd mismatch 为 FAIL。

**如何避免再次踩中**
- 任何 startup recovery 都必须先回答“谁有权宣布旧 owner 已死”,不能把 process construction 当 authority。
- 文件存在、PID 文本、fresh heartbeat、launchctl loaded 都不是单独充分证据;本机 owner 以 kernel lock 为准。
- duplicate-start 测试必须断言 live state 没变化且 Channel 未启动,不能只断言第二进程报错。
- shutdown 要按 start 的严格逆序释放 shared evidence 与 ownership。
- 本实现只覆盖 local single-host;多主机必须使用 lease+TTL+fencing token,不能复用 `flock` 宣称分布式安全。

**相关链接**
- ROUNDS Round 204
- ADR-0042
- Goal Brief `docs/superpowers/specs/2026-07-21-single-runtime-ownership.md`
- P-058
- P-059
- B-010

### [P-061] Generic health failure 不能直接驱动无人值守重启

**状态**:🟢 RESOLVED
**首次踩中**:Round 205
**最后更新**:2026-07-21
**影响范围**:`runtime_self_healing.py`,`runtime_heartbeat.py`,`telegram.py`,`morning_scheduler.py`,`aico-service doctor`

**症状**
Round 201 的 component health 能发现 Telegram polling/scheduler task 已死,但同一个 `FAILED` 也可能只是
Telegram API、网络或 provider 暂时不可达。如果按 required failure 直接退出或重启,外部抖动会变成 crash-loop;
如果完全不动作,本地 task 死亡又会在老板缺席时永久失联。

**根因**
把 synthetic dependency health 和本进程直接拥有的 background-task liveness 混成一个控制信号。前者只能用于
诊断,后者才具备明确 owner、可安全 restart 的生命周期边界;同时没有稳定期、上限和冷却的“自动恢复”本身也是故障源。

**解决方案 / 缓解措施**
- app runtime 单独列举 Telegram polling 与 enabled morning scheduler 两个 owned task,不扩展 generic plugin protocol。
- heartbeat 在 health probe 前运行 bounded supervisor;task 死亡时原地 restart,不重启进程、不重放业务 Task。
- 单次 restart 最长 5 秒,存活 60 秒才清零;连续 3 次未稳定后熔断 15 分钟,冷却后低频重试。
- heartbeat v3 只写稳定组件名、healthy/recovering/open、attempts 和时间;doctor 将 recovering/open 映射为 WARN/FAIL。
- generic Channel/Adapter health 即使 FAILED 也不会进入 supervisor,shutdown 后 restart 方法不会复活 task。

**如何避免再次踩中**
- 自动恢复前必须证明 failure source、resource owner 和 repair action 一一对应;generic status 不是控制信号。
- 每个 background-task restart 必须同时有 timeout、稳定期、尝试上限和 cooldown。
- 恢复成功不能按“create_task 返回”判断,必须跨过稳定窗口;恢复失败也不能用 tight retry 掩盖。
- 业务 Task 与 runtime task 必须分开:恢复 polling/scheduler 不代表可安全 replay 外部副作用。
- 熔断是可诊断失败,不是最终告警闭环;完全无人值守仍需要后续 second-channel/out-of-band notification。

**相关链接**
- ROUNDS Round 205
- ADR-0043
- Goal Brief `docs/superpowers/specs/2026-07-21-bounded-owned-task-self-healing.md`
- P-056
- B-010

### [P-062] Heartbeat 直发 webhook 不是可靠的缺席告警

**状态**:🟢 RESOLVED
**首次踩中**:Round 206
**最后更新**:2026-07-21
**影响范围**:`runtime_alerts.py`,`runtime_heartbeat.py`,`sqlite_state.py`,`phase1.py`,`aico-service doctor`

**症状**
owned-task circuit open 已可被 heartbeat 发现,但若每次 refresh 直接 POST,同一 incident 会每 30 秒制造告警风暴;
进程在远端 accepted 后、本地 ack 前 crash 会重发且没有幂等 identity,而 open 未送达时 resolved 还可能先到。
若仍通过 primary Telegram/Feishu 通知,Channel 本身失败时告警也一起失效。

**根因**
把“故障事实”“事件身份”“可靠交付”和“外部 endpoint”混成一个 callback。heartbeat snapshot 是周期状态,
不是 edge-triggered incident log；HTTP success 也不是跨两个系统的 exactly-once transaction。

**解决方案 / 缓解措施**
- 只把 owned component 的 first `open` 和 active incident 后的 `healthy` 转成 immutable open/resolved event;
  recovering 保持 incident,重复 snapshot 和 runtime rebuild 均不重复建单。
- active incident 与 outbox event 在同一 SQLite transaction 写入,与 Task recovery audit outbox 保持独立 truth boundary。
- sink 按 row order 投递,未到期/失败队首阻止后续越序;失败状态持久化 1/5/15 分钟封顶退避。
- HTTP event 使用稳定 event id 和 `Idempotency-Key`;accept-before-ack 可安全重投同一 identity,receiver 负责幂等。
- `RuntimeAlertSink` 隔离外部系统,generic HTTPS 实现不把 URL/token/异常内容写入 SQLite、heartbeat、doctor 或日志。
- heartbeat v4 / doctor 显式区分 disabled、healthy、pending、failed;启用 webhook 必须有 state DB 和 heartbeat loop。

**如何避免再次踩中**
- periodic state 变告警前必须先定义 incident edge、dedupe key 和 resolved 条件。
- 两系统交付默认只能 at-least-once;没有 receiver 幂等证明时不得宣传 exactly-once。
- retry 必须持久化 backoff,且队首顺序优先于吞吐,避免 resolved 越过 open。
- primary notification path 不能充当自己的唯一 failure notification path。
- runtime alert 与 business Task audit 必须分库表/模型,不能污染 `/audit`、metrics 或 Task recovery。

**相关链接**
- ROUNDS Round 206
- ADR-0044
- Goal Brief `docs/superpowers/specs/2026-07-21-durable-out-of-band-runtime-alerts.md`
- P-061
- B-011

### [P-096] Fresh dead-man pulse不能证明secondary alert出口仍能送达

**状态**:🟢 RESOLVED(machine contract;external receiver sample pending)
**首次踩中**:Round 240
**最后更新**:2026-07-22
**影响范围**:`runtime_liveness.py`,`runtime_heartbeat.py`,`dead_man_receiver_*`,B-011/B-012

**症状**
runtime、heartbeat和liveness publisher全部正常，required component failure也已形成durable alert event；但secondary alert sink
持续失败时，旧dead-man receiver仍因每分钟收到pulse而续租。老板缺席时primary路径已坏、secondary告警发不出，独立receiver却保持绿色。

**根因**
dead-man pulse只表达process/network reachability，续租条件没有包含系统已承诺的absence notification path健康。尝试让失败sink
自报失败会形成循环依赖；完全停发pulse又丢失最新boot/sequence和故障类型。

**解决方案 / 缓解措施**
- pulse v2只增加bounded `alert_delivery_status`，不携带incident、异常、endpoint、target或正文。
- disabled/healthy pulse排序并续租；pending/failed pulse只排序，保持最后成功续租anchor不变。
- TTL到期按最近信号生成`alert_delivery_unhealthy`或`pulse_expired`，healthy/disabled新pulse同reason resolved。
- receiver/evidence/recovery schema统一v2；v1迁移补保守默认，exact verifier拒绝partial checkpoint、非法enum和reason drift。
- pending pulse在ACK前冻结exact payload；接受状态变化最迟到其ACK后下一interval传播的有界延迟。

**如何避免再次踩中**
- 每条“老板缺席仍能被通知”的链路都要审计出口自身失败时由谁观察；发送者不能作为唯一observer。
- heartbeat顺序正确不等于通知闭环正确；必须把upstream detection、secondary delivery、dead-man renewal分别建模。
- liveness协议升级必须同步publisher、HTTP request、persistent store migration、evidence和offline recovery verifier，不能只改payload。
- `alert_delivery_unhealthy`只证明receiver观察到本地报告并停止续租，不证明真实老板已读、endpoint身份或业务损失。

**相关链接**
- ROUNDS Round 240
- ADR-0078
- Goal Brief `docs/superpowers/specs/2026-07-22-alert-delivery-aware-dead-man-renewal.md`
- P-095
- B-011
- B-012

### [P-098] Aggregate quorum成功会吞掉已失效fallback，形成通知冗余false green

**状态**:🟢 RESOLVED(event-driven route edge;continuous canary由P-099收口)
**首次踩中**:Round 242
**最后更新**:2026-07-22
**影响范围**:`dead_man_receiver.py`,`dead_man_receiver_store.py`,evidence/recovery,B-012

**症状**
双route配置为1-of-2时，primary ACK、fallback失败仍会把main event标为delivered。旧SQLite只保存aggregate结果，老板收到outage
但不知道备用通知通道已失效；若primary之后也失效，系统才第一次暴露冗余早已丢失。

**根因**
把“本次达到minimum ACK”错误扩张成“通知系统健康”。availability quorum、逐route健康和human read是三类事实；只保存第一类
会让成功路径抹掉重要失败。仅加被动admin字段也不符合absence-first，因为老板不会持续查询observer。

**解决方案 / 缓解措施**
- schema v4在main event保存最后一次ACK bitmask/time，并以slot 1/2维护unknown/healthy/degraded状态，不保存provider/URL/token。
- main settle/defer、route状态和新edge同一事务提交；first failure开stable degraded，degraded后的真实ACK开stable recovered。
- route-health edge使用独立outbox并按any-route ACK结算，通过尚存route主动触达老板；失败有界退避、restart不丢。
- meta-alert本身不反向更新route健康，避免用observer自己的通知递归证明自己；单route全断不制造不可送达的自我告警。
- evidence/recovery v4验证ACK mask、route checkpoint、edge trigger和pending policy fence；v3历史保持unknown。

**如何避免再次踩中**
- 每个quorum都分别回答aggregate success、member health、最终人类触点三份证据，不用一个boolean覆盖三层。
- 冗余降级必须主动通知且durable；只放在dashboard、log或readiness都不满足老板缺席。
- meta-monitor必须标清观察来源，不能把自身送达当成原route恢复证据，避免递归false green。
- event-driven route observation不等于continuous health。若需要“无事故时也持续证明fallback可用”，必须新增silent canary或
  provider-native probe合同，并单独控制噪声、identity与重试。

**相关链接**
- ROUNDS Round 242
- ADR-0080
- Goal Brief `docs/superpowers/specs/2026-07-22-durable-notification-route-health-edges.md`
- P-097
- B-012

### [P-099] 普通webhook canary会在“证明通知健康”时制造老板噪声或测试错链路

**状态**:🟢 RESOLVED(machine contract;real bridge silence sample pending)
**首次踩中**:Round 243
**最后更新**:2026-07-22
**影响范围**:`dead_man_receiver_*`,receiver deployment,evidence/recovery,B-012

**症状**
Round 242已有逐route健康边沿，但长期无outage时坏fallback仍可能保持旧healthy。直接定时POST普通outage会把探测展示给老板或触发
incident自动化；改做HEAD、另一probe URL或另一credential虽然安静，却没有验证真正事故通知的POST/auth/bridge链路。

**根因**
把“endpoint可连接”“探测旁路可ACK”和“真实owner notification wire contract可用”混成同一事实，也没有在协议层定义silent处理、
幂等identity、confirmation threshold和跨restart intent。

**解决方案 / 缓解措施**
- schema v5增加默认disabled的字面合同`silent-route-probe-v1`；只在双route且两个bridge均承诺ACK但不展示/不触发incident时启用。
- probe复用真实URL、token、POST与`Idempotency-Key`，payload使用独立event type；intent先落盘，ACK歧义重放exact event。
- 一个失败窗口只保留suspect/PENDING，连续达到2-10的持久阈值才degraded并复用既有edge；ACK清零并按需recovered。
- 不catch up历史窗口；全断时edge durable保留。meta-alert不反向证明route恢复，probe不获得restart/repair/restore权限。
- evidence/recovery v5验证probe policy/pending/ACK mask、route probe checkpoint、source-tagged edge与canonical v4迁移。

**如何避免再次踩中**
- continuous canary必须验证与生产事件相同的transport和credential；旁路健康不能冒充主链路健康。
- silent不是发送者单方面的字段，而是downstream bridge必须dogfood证明的协议承诺；不能证明就保持disabled。
- confirmation window必须显式显示suspect/PENDING，不能在阈值前false green，也不能一次抖动就刷老板。
- local probe ACK仍不证明provider故障域独立、手机展示或human read；B-012只能由真实双provider样本继续收口。

**相关链接**
- ROUNDS Round 243
- ADR-0081
- Goal Brief `docs/superpowers/specs/2026-07-22-durable-silent-notification-route-probes.md`
- P-098
- B-012

### [P-100] 只阻止FAIL的服务安装会把absence关键WARN吞成配置级false green

**状态**:🟢 RESOLVED(explicit strict machine admission;external dogfood pending)
**首次踩中**:Round 244
**最后更新**:2026-07-22
**影响范围**:`aico-service doctor/install`,`.env.example`,B-010至B-014

**症状**
`runtime alerts`、`runtime liveness`、`recovery backup`和`standing autonomy`默认关闭时只显示WARN，而install只拒绝FAIL。
operator可以成功安装一个会自启动的进程，却没有任何第二告警、死信号、恢复演练或主动工作合同，并把“plist installed”误读为
“老板可以离开”。

**根因**
把开发配置合法性和absence部署准入压在同一severity阈值上。WARN对可选开发能力是正确语义，但没有显式deployment profile时，
它也会成为production gate的隐式放行。反过来把所有WARN升级FAIL又会破坏最小dogfood，并把外部基础设施强加给每个开发者。

**解决方案 / 缓解措施**
- 新增默认`optional`、owner显式选择的`strict` absence admission；optional继续WARN，strict成为install前FAIL门禁。
- strict复用同一轮真实readiness结果，不另写looser production checker；要求alert、liveness、backup、standing均OK。
- strict额外要求disposable recovery drill启用；retention因具有删除权限继续保持独立opt-in。
- 失败只列固定合同名，非法mode不回显；launchctl runner保持零调用。
- 成功文案固定声明external evidence未认证，不能把URL、path、配置preflight或unit test写成commercial readiness。

**如何避免再次踩中**
- 每个“安装成功”都要区分process deploy、machine absence contract、external E2E和human read四层事实。
- 可选能力若会决定无人值守是否成立，应提供显式聚合admission，而不是期待operator人工理解一串WARN。
- 聚合门禁必须复用production preflight结果，不能复制一套更松的shadow validation。
- strict配置也只能关闭机器侧false green；真实receiver/provider/storage/owner样本仍要由BLOCKERS跟踪。

**相关链接**
- ROUNDS Round 244
- ADR-0082
- Goal Brief `docs/superpowers/specs/2026-07-22-strict-absence-install-admission.md`
- B-010/B-011/B-012/B-013/B-014

### [P-101] 只在install执行strict门禁会被LaunchAgent自动重启绕过

**状态**:🟢 RESOLVED(runtime startup contract;external evidence pending)
**首次踩中**:Round 245
**最后更新**:2026-07-22
**影响范围**:`Phase1Settings`,`aico-phase1`,`aico-feishu-webhook`,`aico-service`,B-010至B-014

**症状**
Round 244的strict门禁只存在于`aico-service install`。LaunchAgent后续异常重启直接运行runtime entrypoint，而
`Phase1Settings(extra="ignore")`没有admission字段，dotenv中的strict被静默忽略。配置漂移关闭关键合同时，进程仍按optional语义启动。

**根因**
把部署前检查误当成持续运行policy，且没有沿真实entrypoint验证新配置字段是否被settings模型消费。另一个审计发现是Pydantic
model-level ValidationError会携带raw input；若直接让生产入口打印，fail-closed反而可能把dotenv token写进LaunchAgent stderr。

**解决方案 / 缓解措施**
- service与runtime共享固定合同名/gap聚合；Phase1Settings显式建模`optional|strict`，不再extra-ignore。
- strict缺enable项在settings构造时失败；完整配置在build runtime第一步复用standing/recovery production preflight。
- preflight在Channel、state/audit和owner lock构造前运行，失败不接IM、不调用provider、不创建本地业务状态。
- Telegram/Feishu entrypoint统一使用secret-safe settings loader，原始ValidationError不进入process stderr。
- optional开发路径不变；runtime gate仍不冒充外部ACK、storage class或human read。

**如何避免再次踩中**
- 新deployment policy必须沿所有真实entrypoint、supervisor restart与灾后启动路径验证，不能只测installer。
- BaseSettings使用`extra=ignore`时，每个新增env key都要有dotenv回归，证明不是“doctor认识、runtime忽略”。
- fail-closed错误也要审计secret exposure；validation framework的默认repr不能直接进入长期日志。
- startup gate要尽早、无网络、无业务副作用；外部freshness另建receipt合同，不能在构造期随意发探针。

**相关链接**
- ROUNDS Round 245
- ADR-0083
- Goal Brief `docs/superpowers/specs/2026-07-22-runtime-enforced-strict-absence-admission.md`
- P-100
- B-010/B-011/B-012/B-013/B-014

### [P-102] 文档声明webhook分离但机器准入不做跨字段校验仍会false green

**状态**:🟢 RESOLVED(machine isolation;external independence pending)
**首次踩中**:Round 246
**最后更新**:2026-07-22
**影响范围**:`runtime alerts`,`runtime liveness`,`aico-service`,`Phase1Settings`,P-064,B-011/B-012

**症状**
文档和P-064早已说明incident alert与pulse strict endpoint不能共用，但service/runtime只分别验证两个URL都是HTTPS。把同一个URL、
甚至同一个bearer填给两侧仍会通过strict admission；strict receiver随后会因schema/route不匹配拒绝其中一路。

**根因**
把单字段合法性误当成跨协议兼容性，并以文档纪律代替machine admission。两个publisher各自健康不等于它们拥有分离的endpoint和
authority；跨字段invariant没有进入共享policy，install/runtime都无法阻止错误组合。

**解决方案 / 缓解措施**
- 共享pure validator要求两URL exact-distinct，双方bearer均存在时也exact-distinct；不回显任何原值。
- service新增`runtime endpoint isolation`并纳入strict aggregate；冲突在launchctl前FAIL。
- Phase1Settings复用同一helper，Telegram/Feishu每次启动都在Channel/state前FAIL。
- 允许same origin/different strict path；不同origin、provider和网络独立继续是外部证据，不由字符串规则伪造。

**如何避免再次踩中**
- 当两个独立组件分别校验通过时，继续审计它们之间的identity、endpoint、credential和protocol不变量。
- “文档写了不能共用”不是机器合同；高影响配置隔离必须有cross-field test与runtime/install双入口验证。
- distinct URL只证明路由字符串不同，distinct token只证明配置值不同；不能扩张为第二故障域或human read。
- validator错误只能返回固定policy原因，不能为了排障打印endpoint/token。

**相关链接**
- ROUNDS Round 246
- ADR-0084
- Goal Brief `docs/superpowers/specs/2026-07-22-runtime-webhook-authority-isolation.md`
- P-064
- B-011/B-012

### [P-103] 磁盘新配置通过doctor不能证明运行进程已经加载

**状态**:🟢 RESOLVED(metadata generation health;external recommission pending)
**首次踩中**:Round 247
**最后更新**:2026-07-22
**影响范围**:`Phase1Settings`,`RuntimeHealthProbe`,heartbeat,runtime alerts

**症状**
运行中编辑`.env`后，doctor按新文件验证，但进程仍持有旧settings；磁盘OK会掩盖旧endpoint/grant/recovery binding仍在生效。

**解决方案 / 缓解措施**
- production loader只捕获文件stat代际，不读取/哈希内容；strict heartbeat每轮比较。
- 漂移投影为required `configuration:dotenv-generation` FAILED，进入既有confirmed alert且不暴露path/metadata。
- 不自动reload/restart，保留known-good进程并要求显式recommission/restart。

**如何避免再次踩中**
- 配置文件readiness、进程loaded config与external E2E是三份事实。
- secret-safe drift可以先比较文件代际；不要为方便持久化secret/content hash。
- drift告警不等于新配置已验收，不能自动切换业务authority。

**相关链接**
- ROUNDS Round 247
- ADR-0085
- Goal Brief `docs/superpowers/specs/2026-07-22-runtime-dotenv-generation-drift-health.md`
- P-101/P-102

### [P-104] 历史bundle结构合法不能证明当前外部路径仍健康

**状态**:🟢 RESOLVED(machine acceptance contract;external signed sample pending)
**首次踩中**:Round 248
**最后更新**:2026-07-22
**影响范围**:`dead_man_evidence_cli.py`,receiver commissioning,B-012

**症状**
一个数小时前或数月前导出的bundle只要schema、runtime、outage和delivery仍合法，就能反复通过离线verifier；生成时fresh的probe也可能
在operator验收时已经过期，unknown/degraded route不会影响旧的基础结论。

**解决方案 / 缓解措施**
- 保留默认历史审计语义，增加显式正有限最大年龄并拒绝future-generated artifact。
- strict probe按verification time重算，要求enabled、无pending且至少完成一次；不能只信bundle生成时的fresh布尔值。
- strict route gate要求所有slot healthy；commissioning命令必须组合三项，不修改schema、不联网。

**如何避免再次踩中**
- artifact validity、artifact freshness和external current health是三种结论；CLI成功必须标明启用了哪些验收条件。
- producer生成时计算的freshness不能替代consumer验收时钟；TTL必须在使用边界再次判断。
- exact-byte hash不是来源签名，local route状态也不是provider ACK、human read或物理故障动作证明。

**相关链接**
- ROUNDS Round 248
- ADR-0086
- Goal Brief `docs/superpowers/specs/2026-07-22-bounded-current-dead-man-evidence-acceptance.md`
- B-012

### [P-105] 独立绿灯不能证明当前runtime配置与当前外部证据属于同一代

**状态**:🟢 RESOLVED(expiring commissioning binding;external signed sample pending)
**首次踩中**:Round 249
**最后更新**:2026-07-22
**影响范围**:strict admission,runtime health,reviewed config,dotenv generation,dead-man evidence

**症状**
reviewed config、loaded dotenv和strict dead-man bundle可分别通过，但没有共同identity/expiry。A配置生成的历史证据可能被B配置用于安装，
已运行进程也可能在bundle/probe过期后继续显示全绿。

**解决方案 / 缓解措施**
- owner先固定最终`.env`中的checkout-external evidence/receipt路径，再生成owner-only immutable receipt，避免SHA写回形成循环。
- receipt绑定safe runtime id、canonical reviewed config evidence SHA、dotenv stat代际fingerprint和dead-man exact-byte SHA。
- expiry取bundle maximum age与completed probe TTL较早值；strict doctor/startup复核，heartbeat持续required health。
- 不记录dotenv path/metadata/content/content hash；漂移只告警，不自动reload/restart/replay。

**如何避免再次踩中**
- 多份preflight OK只有在同一receipt内绑定generation、identity和expiry后，才能形成一个组合准入事实。
- expected receipt SHA不能写回它所绑定的同一`.env`；否则创建后修改配置会让receipt立即自我失效。
- local receipt/hash不是detached owner signature，更不是receiver origin、provider ACK、fault action或human read证明。
- 持续有效性必须进入runtime health；只在install时验证会被长时间运行和supervisor restart绕过。

**相关链接**
- ROUNDS Round 249
- ADR-0087
- Goal Brief `docs/superpowers/specs/2026-07-22-expiring-runtime-commissioning-receipt.md`
- P-103/P-104
- B-010/B-012

### [P-106] 把独立故障域写进默认Quickstart会把高级可靠性误成基础使用门槛

**状态**:🟢 RESOLVED(tiered onboarding;external outage evidence remains optional)
**首次踩中**:Round 251
**最后更新**:2026-07-22
**影响范围**:公开Quickstart、LaunchAgent安装、Dead-Man Receiver部署、产品分发形态

**症状**
普通用户只是想从Telegram调用本机AI CLI，却被引导先准备第二台电脑或云服务器、部署receiver并完成严格
commissioning。机器合同虽然更完整，但首次使用路径被高级可靠性验收吞没，也让人误以为本机Runtime不能独立工作。

**解决方案 / 缓解措施**
- 公开默认路径固定为checkout + `aico init` + 前台runtime；macOS需要常驻时再安装用户级LaunchAgent。
- Dead-Man Receiver明确标为可选高级能力，只有整机失联检测目标才需要，且仅异机部署能形成独立故障域。
- `optional`是普通开发/dogfood默认；`strict`只用于owner主动选择的absence可靠性验收。
- Docker Compose继续服务独立receiver；本机核心保留原生进程，以复用本地仓库、CLI凭据和macOS服务管理。

**如何避免再次踩中**
- 文档先回答“最少需要运行什么”，再分层介绍可靠性增强，不把所有可用能力堆进第一条路径。
- 部署组件是否必需由产品承诺决定；某能力需要第二故障域，不代表整个产品需要第二故障域。
- Quickstart只调用单一公开CLI；shell脚本和内部entrypoint不能发展成并行策略源。

**相关链接**
- ROUNDS Round 251
- ADR-0089
- B-010/B-012

### [P-107] Active long polling时旁路getUpdates为空不能证明Telegram消息未送达

**状态**:🟢 RESOLVED(live UI + consumed-update log correlation)
**首次踩中**:Round 251
**最后更新**:2026-07-22
**影响范围**:Telegram dogfood、LaunchAgent运行态诊断、Bot API验收、B-010

**症状**
LaunchAgent已经运行Telegram long polling时，旁路调用同一Bot Token的`getUpdates`返回空数组。若把“此刻没有待消费update”误写成
“测试消息从未进入Bot API”，会在Web Telegram已有新鲜回包、runtime也已消费update的情况下错误判定E2E失败；页面中其他位置的
账号状态文本还可能进一步放大误诊。

**解决方案 / 缓解措施**
- 真实入站验收以同一Bot私聊中的新鲜用户命令和可见Bot回包为客户端证据。
- runtime侧按时间与raw ref核对`incoming -> command -> sendMessage -> handler finished`完整链路。
- active poller存在时不启动竞争性`getUpdates`消费者；空pending queue只说明update可能已经被主runtime消费。
- 页面状态结论必须限定到当前账号与当前私聊，不用无关DOM文本替代消息链证据。

**如何避免再次踩中**
- 先画清Bot API消费模型：`getUpdates`是消费队列，不是不可变消息历史查询。
- 通道E2E至少组合客户端可见结果与服务端消费日志；只看其中一层不能定位链路断点。
- 若需要旁路检查，使用不会争抢update的健康信息与既有日志，不让诊断动作改变被测系统。

**相关链接**
- ROUNDS Round 251/252
- B-010
- P-056

### [P-063] 进程内告警无法证明发送者自身仍存活

**状态**:🟢 RESOLVED(machine contract;external deployment pending)
**首次踩中**:Round 207
**最后更新**:2026-07-21
**影响范围**:`runtime_liveness.py`,`runtime_heartbeat.py`,`phase1.py`,`aico-service doctor`

**症状**
durable incident outbox 能覆盖“event loop 仍活着但 owned task 熔断”,却无法在 event loop 卡死、LaunchAgent
持续启动失败或 Mac 断电时创建告警。若在 clean shutdown 自动发送 stopped/disarm,一次 stop 后未成功重启还会被
错误静音。若把每个 heartbeat pulse 写进 durable outbox,则会制造无限历史和无意义重放。

**根因**
把 sender delivery health 当成 service availability,并让被监控对象决定何时解除监控。缺席监控必须在独立失效域
根据“预期信号未按期到达”形成事实；intentional permanent stop 也只能由 receiver owner 明确声明。

**解决方案 / 缓解措施**
- AICO 只发送低频 ephemeral pulse:stable runtime id、fresh per-process boot id、sequence、interval 和 TTL。
- failed send 在内存保留同一 pulse/`Idempotency-Key` 有界重试,成功后才推进 sequence；不写 SQLite/outbox。
- receiver 必须先显式 arm,按 acceptance time + TTL 判 stale；首次超时 open,新有效 pulse 后 resolved。
- arm 后从未收到首个 pulse 也会在 TTL 后 open；duplicate/out-of-order pulse 不延期。
- 普通 stop/restart 不自动 disarm；永久卸载前由 owner 在 receiver 显式 disarm。Mac sleep/网络分区超过 TTL
  默认就是 unavailable。
- heartbeat v5 / doctor 只显示 publisher disabled/healthy/degraded/failed,不能作为外部 receiver 存活证明。

**如何避免再次踩中**
- “故障发送者主动报告自己已死”是逻辑悖论；整进程/整机故障必须有独立 observer。
- periodic liveness 默认是覆盖型状态,不要当永久审计事件持久化；只保留 bounded retry identity。
- 自动 disarm 必须 fail closed:除非 owner 在独立 receiver 明确永久停用,任何本机 stop 都继续等待 TTL。
- receiver expiry 使用本地 acceptance time,避免 sender clock skew 决定 outage；sender timestamp 只用于保守拒绝旧 boot。
- 本机单测只能验证协议和 state machine,不能替代独立部署后的 kill/launch-failure/network sample。

**相关链接**
- ROUNDS Round 207
- ADR-0045
- Goal Brief `docs/superpowers/specs/2026-07-21-external-runtime-dead-man-liveness.md`
- P-062
- B-012

### [P-064] 不同 strict webhook 协议不能因共用 HTTPS 而复用 endpoint

**状态**:🟢 RESOLVED
**首次踩中**:Round 208
**最后更新**:2026-07-21
**影响范围**:`phase1.py`,`service_cli.py`,`dead_man_receiver_app.py`,receiver deployment

**症状**
Round 207 把 liveness pulse 配置复用了 `AICO_RUNTIME_ALERT_WEBHOOK_URL`。两者虽都通过 HTTPS POST,但 alert
endpoint 接收 `incident_opened/resolved`,pulse endpoint 接收 schema v1 liveness envelope；strict receiver 会正确
以 422 拒绝另一协议。结果可能是 pulse 可达但 incident outbox 永远 pending,或反之。同期的 in-memory tracker
即使 state machine 正确,receiver restart 后仍会忘记 armed monitor,不能作为可部署 dead-man service。

**根因**
把 transport similarity 当成 wire compatibility,又把 reference algorithm 当成 independent service。URL/token 的
存在只能证明配置非空,不能证明 endpoint 接受 caller 的 schema、authority 和 retry contract。

**解决方案 / 缓解措施**
- AICO 增加专用 `AICO_RUNTIME_LIVENESS_WEBHOOK_URL` / bearer / timeout；incident alert transport 保持独立。
- strict ASGI integration 证明 AICO publisher 可以进入 pulse route,同时证明 incident payload 会被该 route 拒绝。
- standalone receiver 用专用 SQLite 持久化 arm/current/outage/outbox；restart immediate reconcile,admin 与 pulse
  credential 分离,且启动时拒绝长度足够但仍是示例值的 placeholder token。
- 部署文档明确两个 strict endpoint 不能共用 URL,并把第二故障域/TLS/真实 outage sample 留作外部证据。

**如何避免再次踩中**
- provider/receiver 替换必须验证 endpoint、wire schema、auth scope、idempotency 和 caller contract；同为 webhook
  或存在 nonempty secret 不是兼容证据。
- reference state machine 升级为运维能力前,必须补 persistence、restart reconciliation、delivery outbox、auth、
  packaging 和 deployment boundary。
- strict protocols 应 fail closed；不要为了掩盖错误复用而放宽 extra/event validation。

**相关链接**
- ROUNDS Round 208
- ADR-0046
- Goal Brief `docs/superpowers/specs/2026-07-21-deployable-dead-man-receiver.md`
- B-012

### [P-065] HTTP process 存活和核心 worker 正在推进不是同一个健康事实

**状态**:🟢 RESOLVED
**首次踩中**:Round 209
**最后更新**:2026-07-21
**影响范围**:`dead_man_receiver_app.py`,`/healthz`,`/readyz`,receiver Compose healthcheck

**症状**
receiver 的 `/readyz` 只执行 SQLite ping。expiry/delivery worker即使连续异常或永久不再调度,HTTP server仍返回
200；Compose healthcheck因此不会 restart。负责发现 AICO 静默失联的 observer会自己静默失效,形成二阶假健康。

**根因**
把 request-path liveness、storage readiness和 owned background-loop progress合成一个“服务能响应”事实；同时
没有区分 worker内部失败与 downstream notification已进入持久 backoff的受控降级。

**解决方案 / 缓解措施**
- `/healthz` 只表达 process/event-loop可响应；`/readyz` 同时要求 SQLite ping和 worker progress。
- startup 先完成 immediate coordinator pass；每次 pass用 monotonic clock记录 success/failure,不依赖 wall clock。
- 允许两个连续内部失败；第三次或三个 sweep interval无成功进展时返回无细节 503。后续成功立即恢复。
- notification rejection已被 coordinator持久化为 pending/backoff时仍算 pass成功,避免 receiver restart storm。
- progress只保存在当前进程；restart后旧健康不继承,新进程必须重新建立证据。

**如何避免再次踩中**
- 每个 owned background loop都必须回答“外部 supervisor如何知道它还在推进”,不能只探测端口/DB。
- liveness、readiness、dependency degradation和业务 E2E必须分层,不能用一个 HTTP 200代表全部。
- progress elapsed time使用 monotonic clock；wall-clock校时不能延长健康窗口或制造假 stale。
- public health endpoint只返回稳定状态,异常详情留在脱敏日志,不得泄露路径、identity、event或secret。

**相关链接**
- ROUNDS Round 209
- ADR-0047
- Goal Brief `docs/superpowers/specs/2026-07-21-dead-man-receiver-worker-readiness.md`
- B-012

### [P-066] 通知截图和直接查库都不是可移植、可机器复核的 outage 验收证据

**状态**:🟢 RESOLVED(machine evidence contract;external exercise pending)
**首次踩中**:Round 210
**最后更新**:2026-07-21
**影响范围**:dead-man receiver evidence endpoint、offline verifier、B-012 outage exercise

**症状**
receiver已经持久化open/resolved与delivery retry,但真实演练只能靠owner看下游通知截图或登录主机查询SQLite。
截图不能严格验证event identity/order/retry,直查DB会暴露路径/内部schema并让验收脚本与存储实现耦合。反过来,
只给JSON加一个hash又容易被误写成来源签名或独立部署证明。

**根因**
运行事实已有,但缺少稳定、bounded、authority-separated的evidence projection和离线invariant verifier；同时没有
明确区分artifact完整性、receiver来源认证、物理故障动作与第二故障域部署四种证据。

**解决方案 / 缓解措施**
- admin-only endpoint按最近完整outage group导出versioned JSON；pulse/public authority无读取权限。
- bundle只含safe runtime、optional monitor、open/resolved identity/time和local delivered/attempt/next-retry,
  不含URL/token/path/exception/request/operator note。
- 按outage数量截断,不把resolved与opened切开；disarm后immutable event仍可导出。
- offline CLI严格验证schema、runtime、unique identity、chronology、open-before-resolved、delivery order、minimum
  complete outages和all-delivered；不联网、不接credential、不改变receiver。
- CLI输出exact artifact byte SHA-256供与已记录digest比对；文档明确它不是origin signature。

**如何避免再次踩中**
- 外部验收先拆证据层：机器事实、artifact完整性、来源/TLS、物理操作、最终业务效果分别证明,不能相互替代。
- 可导出证据必须有strict schema、bounded response、authority boundary和offline verifier,不能只“提供一个JSON”。
- hash只有在先前digest由可信通道记录时才能检测后续改动；没有签名key就不得宣称不可否认来源。
- valid bundle只能收窄B-012,不能关闭B-012；独立host与真实kill/network sample仍需当前外部证据。

**相关链接**
- ROUNDS Round 210
- ADR-0048
- Goal Brief `docs/superpowers/specs/2026-07-21-dead-man-evidence-bundle.md`
- B-012

### [P-067] SQLite 持久化和直接复制主文件都不等于可恢复

**状态**:🟢 RESOLVED(local recovery primitive;off-device drill pending)
**首次踩中**:Round 211
**最后更新**:2026-07-21
**影响范围**:`AICO_STATE_DB_PATH`、WAL、`aico-state` backup/verify/restore、reset、B-013

**症状**
AICO 已把核心业务状态持久化到 SQLite，但 daily ops 的“数据备份与恢复”只有空注释。operator若直接复制
`state.db`，可能遗漏 WAL 中已提交事务；若在 runtime active时 restore/reset，旧连接和sidecar仍可能继续写入，
造成“文件替换成功但运行事实不可解释”。

**根因**
把“进程重启后能重新读状态”误当成“有备份、可校验、可恢复”。恢复还需要一致快照、artifact identity、
schema/integrity gate、独占 mutation fence、安全回退点和真实 drill，这些都不是 SQLite 持久化自动提供的。

**解决方案 / 缓解措施**
- backup使用SQLite online backup API，live source也生成transaction-consistent standalone artifact；不复制raw DB/WAL。
- artifact必须new path、`0600`、current schema、integrity ok，并输出exact-byte SHA-256。
- verify用read-only immutable connection，不调用会bootstrap/migrate schema的业务DB helper。
- restore先验证artifact/hash，再取得canonical runtime owner lock；active owner fail closed。
- target存在时先生成verified pre-restore safety backup，再通过same-directory temp + fsync + atomic replace恢复；sidecar
  仅在owner fence内清理。reset也复用同一fence。

**如何避免再次踩中**
- 对任何持久化truth source都分别回答：如何一致备份、如何只读校验、如何选择准确artifact、谁拥有restore权限、
  如何回退、多久做一次真实drill。
- WAL数据库禁止把raw `cp main.db`写进runbook；优先使用数据库原生online backup/export contract。
- destructive maintenance必须复用runtime ownership边界，不能另造“服务大概停了”的检查。
- 本机round trip只能证明local primitive；没有off-device artifact、加密/retention和disposable restore sample时，
  不得写成disaster recovery complete。

**相关链接**
- ROUNDS Round 211
- ADR-0049
- Goal Brief `docs/superpowers/specs/2026-07-21-aico-state-backup-restore.md`
- B-013

### [P-068] 备份 integrity/哈希校验不等于生产恢复路径已演练

**状态**:🟢 RESOLVED(local disposable drill;off-device exercise pending)
**首次踩中**:Round 212
**最后更新**:2026-07-21
**影响范围**:`aico-state verify/drill/restore`、DR evidence、B-013

**症状**
Round 211能证明artifact字节、SQLite integrity、schema和table counts，但这些检查没有执行production restore的
临时物化、owner lock、atomic replace和sidecar cleanup。把verify输出直接写成“恢复演练通过”，会让商用DR证据
比实际验证范围更宽。

**根因**
混淆了三层事实：artifact可读、restore implementation可运行、off-device全资产业务恢复成功。前一层是后一层的
必要条件，不是替代品。

**解决方案 / 缓解措施**
- `aico-state drill`先verify exact SHA，再在私有临时目录调用同一`restore_state_backup()`。
- materialized DB重新read-only verify并比较schema/known-table counts；不是复制一套假的restore逻辑。
- CLI全局`--db`在drill路径完全不打开/创建/lock，live runtime可以保持active。
- success/failure都由`TemporaryDirectory`清除DB、lock和sidecar；optional report为`0600`、new-path、atomic
  no-overwrite JSON，只包含bounded machine facts。
- report明确只证明local artifact + restore code，不证明off-device origin、credentials、JSONL/config或IM E2E。

**如何避免再次踩中**
- 每个“备份已验证”claim要写清是verify、materialization drill还是business restore exercise。
- recovery test必须调用production restore primitive，不能维护第二份测试专用实现。
- drill默认使用disposable target且自动清理；live state只在owner明确恢复窗口中操作。
- verifier/report都不能提升自身证据等级；独立故障域和业务可用性必须由对应范围的真实样本证明。

**相关链接**
- ROUNDS Round 212
- ADR-0050
- Goal Brief `docs/superpowers/specs/2026-07-21-aico-state-disposable-restore-drill.md`
- B-013

### [P-069] Standing charter、chat target 和只读文案都不等于 owner 预授权

**状态**:🟢 RESOLVED(local hard-read-only contract;external owner sample pending)
**首次踩中**:Round 213
**最后更新**:2026-07-21
**影响范围**:standing proposal、scheduled morning、TaskBus、Adapter sandbox、B-014

**症状**
为了让 boss-absent loop 真正前进，最短路径看似是让定时晨报自动 accept 当前 standing proposal。但项目 charter
可能被工作 Agent 修改，chat target 只是结果目的地，prompt 中的 `read_only` 也不能阻止 broad-permission CLI 写盘、
联网、续接旧 session 或发起协作。这样得到的是无人看守的执行，不是 owner 授权的自治。

**根因**
把 intent、routing、identity、authorization 和 enforcement 五层事实混成一个字段。缺席执行还需要 expiry、总次数、
单次时长和 crash-consistent consumption；否则即使单次看似安全，也没有商业可接受的损失上限。

**解决方案 / 缓解措施**
- 独立 owner-only external grant 精确绑定 owner、target/thread、project/charter、expiry、max runs/duration。
- runtime 启动时拒绝 repo 内文件、symlink、宽权限、占位符、未知 charter、晨报目标漂移和非 hard-safe Adapter。
- 只有 scheduled morning 可消费；交互 read surfaces 不触发执行。
- TaskBus 再次检查 read-only risk、无 collaboration、无 provider resume 和 Adapter-owned boundary。
- Codex 预授权任务丢弃用户配置命令，固定 read-only/no-network/ephemeral command；预算先持久化再 dispatch。

**如何避免再次踩中**
- 对每个“自动执行”分别回答：谁授权、授权放在哪、如何防工作 Agent 自改、工具层如何强制、预算如何跨重启扣除。
- prompt/role/charter 只能缩小意图，不能作为 sandbox 或 requester identity 的证据。
- fail closed 后应保留 manual decision path，不能为了无人值守而静默放宽边界。
- `0600` 仍不是密码学 owner signature；更强同用户威胁模型必须单独设计，不得在产品口径中省略。

**相关链接**
- ROUNDS Round 213
- ADR-0051
- Goal Brief `docs/superpowers/specs/2026-07-21-owner-bound-readonly-standing-autonomy.md`
- B-014

### [P-093] 持续验证备份字节不等于持续验证恢复路径

**状态**:🟢 RESOLVED(durable scheduled disposable production drill)
**首次踩中**:Round 237
**最后更新**:2026-07-22
**影响范围**:`RecoveryBackupScheduler`、`drill_recovery_set`、runtime health、retention、B-013

**症状**
Round 234-236已经自动capture、deep verify、custody和retention。所有SHA都可能长期绿色，但state/audit/memory production
materializer若因代码回归或内部语义变化无法工作，只有operator手工运行drill时才会发现；无人值守期间恢复信心仍会腐化。

**根因**
把“artifact现在还能完整读取”误当成“事故时能实际materialize”。verify检查格式/完整性，drill还必须执行replace、sidecar、
checkpoint和production restore helper；两者是不同证据。手工命令存在也不等于cadence受控。

**解决方案 / 缓解措施**
- 默认关闭的scheduled drill为每次到期先写durable intent，再对最新VERIFIED + custody VERIFIED artifact运行既有production drill。
- drill只在private disposable workspace进行；可选workspace与checkout/output隔离，不触碰live state或自动restore。
- success receipt绑定artifact/backup receipt/policy SHA和component evidence，保留post-restore缺项与business readiness=false。
- 失败有界重试、crash同ID恢复；due/open/exhausted/stale进入health，失败目标受retention保护。

**如何避免再次踩中**
- 备份运营必须分别报告capture、verify、custody、materialization drill和live business recovery，不能用任一层覆盖其他层。
- 自动drill只能获得non-destructive disposable权限；不能顺手扩成live restore或自动业务切换。
- feature toggle与retention组合必须检查durable历史，不能因为当前drill关闭就遗忘旧失败intent并删除现场。
- local drill不证明artifact来自off-device，也不覆盖checkout、credential、provider、receiver或代表性IM业务恢复。

**相关链接**
- ROUNDS Round 237
- ADR-0075
- Goal Brief `docs/superpowers/specs/2026-07-22-durable-scheduled-recovery-drill.md`
- B-013

### [P-092] 永不自动删除不等于长期无人值守更安全

**状态**:🟢 RESOLVED(explicit bounded retention + durable prune reconciliation)
**首次踩中**:Round 236
**最后更新**:2026-07-22
**影响范围**:`RecoveryBackupScheduler`、SQLite recovery state、runtime health、B-013

**症状**
Round 234/235为了避免误删，scheduler只capture和custody、永不清理。短期安全，但长期boss-absent会无界堆积daily artifact；目标盘
耗尽后新恢复点无法生成，最终把“禁止删除”变成更高RPO和隐藏的运营依赖。

**根因**
把“没有设计安全删除合同”简化成“永远不给机器删除权限”，没有区分默认授权、候选资格、删前验真、单轮损失上限、崩溃恢复和
可审计tombstone。直接依赖operator定期清盘又与human-absent目标冲突。

**解决方案 / 缓解措施**
- retention独立默认关闭；owner同时选择age、至少两个最新代际、check cadence与单轮最大删除数。
- 候选必须是同一binding的VERIFIED + custody VERIFIED；SQLite先落PRUNING/policy SHA，随后再次deep verify。
- artifact和sidecar按固定顺序删除并fsync；PRUNED保留receipt/artifact/policy SHA与时间，不删除审计事实。
- restart按pair存在矩阵收敛；artifact-only或验真漂移保留现场并使health FAILED，关闭开关也不取消既有intent。

**如何避免再次踩中**
- “不做破坏性动作”必须同时回答资源是否会无界增长；若会，要设计窄授权和可恢复状态机，而不是把工作留给缺席的人。
- retention不能扫描目录或按mtime猜候选；durable state、custody与策略证据缺一不可。
- feature flag只控制新授权，不能撤销已开始的破坏性事务或让半删除状态恢复绿色。
- 本地PRUNED tombstone不是storage provider lifecycle/WORM、off-device或商业DR证据。

**相关链接**
- ROUNDS Round 236
- ADR-0074
- Goal Brief `docs/superpowers/specs/2026-07-22-bounded-recovery-retention.md`
- B-013

### [P-091] 创建时deep verify不等于无人值守期间artifact仍受保管

**状态**:🟢 RESOLVED(periodic custody attestation + destination continuity)
**首次踩中**:Round 235
**最后更新**:2026-07-22
**影响范围**:`RecoveryBackupScheduler`、runtime health、`aico-state`、B-013

**症状**
Round 234在capture后立即deep verify并持久VERIFIED receipt，但后续若目标盘掉线、目录被替换、artifact/sidecar被删或篡改，
heartbeat直到下一次capture仍只看到旧receipt和RPO age，可能错误保持OK。

**根因**
把point-in-time verification当成持续custody；没有独立回答“现在还能重新打开同一字节吗”“目标目录还是同一identity吗”“最近
一次复验是什么时候”。

**解决方案 / 缓解措施**
- receipt绑定secret-free destination fingerprint；后续capture和health必须保持目录device/filesystem/inode identity连续。
- 独立custody cadence在worker thread重新校验文件类型/权限、sidecar receipt SHA、artifact SHA与完整production verifier。
- custody status/time/failure count持久化；FAILED、stale、missing、drift、unsafe permission和identity change进入required health FAILED。
- heartbeat只做cheap stat/identity gate，避免每30秒hash大artifact；deep verify由scheduler独立节奏执行。

**如何避免再次踩中**
- 每个“verified backup”都要区分created-at verification与latest custody attestation；没有后者只能说明过去曾经可读。
- 备份cadence和custody cadence必须独立：低频RPO不能成为长时间不检查artifact是否仍在的理由。
- 目录指纹只证明本机连续性，不得写成volume UUID、云存储durability、off-device或encryption evidence。
- custody发现问题只能fail health并保留现场；不得顺势自动restore/delete/rebind。

**相关链接**
- ROUNDS Round 235
- ADR-0073
- Goal Brief `docs/superpowers/specs/2026-07-22-continuous-recovery-artifact-custody.md`
- B-013

### [P-090] 有可用的手动备份命令不等于boss-absent期间RPO受控

**状态**:🟢 RESOLVED(local scheduled capture + verify;external storage policy pending)
**首次踩中**:Round 234
**最后更新**:2026-07-22
**影响范围**:`aico-recovery`、Phase1 scheduler/heartbeat、SQLite state、B-013

**症状**
core recovery set已经能capture、verify和drill，但所有入口都要求operator主动运行。长期无人值守时，命令本身全绿也不能说明
最近恢复点有多新；普通cron还可能在artifact已发布而状态未提交后覆盖文件，或在外部mount缺失时悄悄写入本机目录。

**根因**
把“恢复primitive存在”误当成“备份运营闭环存在”，没有为scheduled intent、crash reconciliation、bounded retry、RPO age和
runtime health建立同一durable contract。

**解决方案 / 缓解措施**
- 默认关闭的scheduler先写SQLite intent，再以稳定ID生成new-path set，capture后立即运行production verifier并写receipt。
- artifact/sidecar四种存在组合逐一fail closed或复验收敛；open intent有界重试，exhausted/stale RPO进入required health failure。
- output必须是已存在的absolute owner-only真实目录且位于checkout外；缺失mount不创建，doctor不声称off-device/encrypted。
- restore保持独立owner动作；retention必须是独立显式owner授权。Round 236只在该开关下让scheduler处理已验真旧代际。

**如何避免再次踩中**
- 每个“已支持备份”声明都要同时回答：谁触发、失败如何重试、崩溃如何对账、最新verified age是多少、谁会收到失败信号。
- 路径在checkout外只是一项本机安全条件，不是第二故障域、加密、WORM、retention或restore rehearsal证据。
- capture自动化不得顺带获得restore/delete权限；恢复仍必须停机、owner fence、显式选择artifact和独立SHA。

**相关链接**
- ROUNDS Round 234
- ADR-0072
- Goal Brief `docs/superpowers/specs/2026-07-22-durable-scheduled-core-recovery-backup.md`
- B-013

### [P-094] 自治dispatch不盲重跑不等于老板一定收到终态

**状态**:🟢 RESOLVED(durable exact-outcome outbox + required health)
**首次踩中**:Round 238
**最后更新**:2026-07-22
**影响范围**:`MorningPushScheduler`、standing autonomy、SQLite state、runtime health、B-010/B-014

**症状**
scheduled autonomy已有intent和accepted evidence，能在崩溃后避免重复provider dispatch；但result/invalid/blocked通知仍是直接
`send_message`。平台失败或ACK前崩溃后intent会保守SETTLED，老板只能等下一次`/morning`/`/inbox`才看到结果或
`evidence_missing`。同时started提示在TaskBus submit前失败，会留下accepted proposal却根本没有开始provider任务。

**根因**
把“provider不能盲重跑”当成整个absence loop已经收口，遗漏了独立的terminal outcome transport状态；进度提示还错误地位于
业务dispatch的关键路径。dispatch decision、provider/task evidence、结果投影、平台ACK和human read是五种事实。

**解决方案 / 缓解措施**
- 从authoritative proposal/task/result投影bounded outcome envelope，绑定run receipt/content SHA且不保存provider正文。
- 发送前写独立outbox；同一notification按1/5/15/15分钟最多五次，重启立即恢复，wrong-target ACK拒绝落DELIVERED。
- 重试只发送exact content，不调用provider、不消费grant；open进入DEGRADED，EXHAUSTED进入FAILED。
- settled intent缺outbox时在新工作前补建；started提示普通发送异常只脱敏记录，不阻断TaskBus submit。
- RUNNING/WAITING不冻结为terminal通知；TaskBus dispatch后的IM异常要interrupt本地RUNNING task，否则保持DEGRADED轮询。
- `aico-state`只输出status/attempt/content SHA/source/outcome/ACK time，不显示target、正文或raw message id。

**如何避免再次踩中**
- 每个异步工作都要画清`intent -> dispatch evidence -> terminal evidence -> delivery ACK -> human read`，不能用其中一段代替全链。
- “不重跑下游”必须同时提供“主动交付不确定终态”的路径，否则保守安全会变成静默失败。
- progress hint不能成为business effect的前置依赖；只有安全授权/adapter ACK等真实门禁可以阻止dispatch。
- at-least-once notification允许有界重复，但必须冻结exact content、稳定ID并把歧义暴露给operator。

**相关链接**
- ROUNDS Round 238
- ADR-0076
- Goal Brief `docs/superpowers/specs/2026-07-22-durable-autonomy-outcome-delivery.md`
- B-010
- B-014

### [P-089] 晨报平台ACK不等于后置自治已被安全触发

**状态**:🟢 RESOLVED(durable intent + accepted-evidence reconciliation)
**首次踩中**:Round 233
**最后更新**:2026-07-22
**影响范围**:`MorningPushScheduler`、standing proposal/task、SQLite state、B-010/B-014

**症状**
Round 232把平台ACK先落DELIVERED再运行standing autonomy，避免自治失败重发晨报。但进程若在ACK后、自治调用前崩溃，
DELIVERED记录不会再进入发送路径，自治永久漏掉；若重启时无条件重跑，又可能重复消费已被provider接受的任务。

**根因**
正确拆开transport和business事实后，没有为两者之间的后置动作建立独立durable intent；同时缺少“provider dispatch前必须先落哪份
业务证据”的恢复判据。

**解决方案 / 缓解措施**
- 在任何晨报外发前创建稳定scheduled autonomy intent，独立记录状态、attempt、backoff和结算receipt。
- standing coordinator在provider dispatch前持久accepted proposal/task并绑定intent；恢复时有该证据就结算，不再调用provider。
- 没有accepted证据才允许最多五次重试；中断后标记notification可能重复，EXHAUSTED使health失败。
- `aico-state`把delivery与autonomy分栏，只输出secret-free状态和identity hash。

**如何避免再次踩中**
- 所有“ACK后再做X”都要单独回答：X的intent何时落盘、dispatch证据何时落盘、重启如何判断可否重试。
- 下游缺乏幂等事务时，不能用“函数已返回/可能已调用”猜测执行事实；只信可验证的durable evidence。
- notification重复与provider重复是不同风险；前者可有界暴露，后者必须由dispatch前证据阻断。

**相关链接**
- ROUNDS Round 233
- ADR-0071
- Goal Brief `docs/superpowers/specs/2026-07-22-durable-scheduled-autonomy-intent.md`
- B-010
- B-014

### [P-088] Scheduler task存活不等于scheduled message已送达

**状态**:🟢 RESOLVED(durable exact-envelope outbox + bounded ambiguity)
**首次踩中**:Round 232
**最后更新**:2026-07-22
**影响范围**:`MorningPushScheduler`、runtime health、SQLite state、standing autonomy、B-010/B-014

**症状**
原scheduler在`send_message`异常后只写日志并继续循环；后台task仍存活，所以heartbeat返回OK。进程也可能在平台已接受消息后、
AICO记录前崩溃。这样boss-absent runtime会静默漏报，或在重启后无法说明是否可能重复。

**根因**
把process liveness、transport acknowledgement、human read和business result混成一个“晨报成功”；同时重试前没有冻结exact content，
重新渲染会让同一逻辑投递随状态变化。

**解决方案 / 缓解措施**
- 发送前持久化稳定daily delivery id、exact content/content SHA和所含standing receipt SHA；重试只复用该envelope。
- 1/5/15/15分钟最多五次；发送中崩溃或未确认尝试标记`duplicate_possible`，耗尽使scheduler health FAILED。
- 平台ACK先落DELIVERED与raw message id SHA，再触发standing autonomy；自治失败不能让已确认晨报重发。
- `aico-state`只展示secret-free delivery摘要；target、正文与raw message id不进入operator输出。

**如何避免再次踩中**
- 所有scheduled outbound都必须分别报告task liveness、pending/retry/exhausted和platform ACK，不能用绿色进程替代delivery。
- 平台没有端到端幂等事务时只能声明bounded at-least-once；accept-before-ack窗口必须显式暴露，不能伪造exactly-once。
- platform ACK不等于人类已读或消息长期可见；content/result fingerprint也不证明业务语义正确。
- 需要重试的动态报告必须先冻结内容；同一logical id下重新渲染属于identity drift，应fail closed。

**相关链接**
- ROUNDS Round 232
- ADR-0070
- Goal Brief `docs/superpowers/specs/2026-07-22-durable-scheduled-morning-delivery.md`
- B-010
- B-014

### [P-070] Grant 文件安全不等于 runtime autonomy binding 已就绪

**状态**:🟢 RESOLVED(non-mutating deployment preflight)
**首次踩中**:Round 214
**最后更新**:2026-07-21
**影响范围**:`aico-service doctor`、Phase 1 config、standing autonomy、B-014

**症状**
一个external、owner-only、strict JSON grant可通过旧doctor，但它可能指向另一个morning target、不存在的charter、
未任命persona，或Codex Adapter根本没启用/已被wrapper替换。operator会在install前看到OK，runtime后台启动后才失败。

**根因**
readiness只检查credential/artifact形状，没有沿真实routing graph验证“grant -> scheduled target -> project -> charter
-> appointment -> persona -> Adapter hard boundary”。文件合法是输入证据，不是可执行部署证据。

**解决方案 / 缓解措施**
- Phase 1提供non-mutating preflight，复用真实Adapter/persona/project/grant binding validator。
- doctor只投影相关`.env`字段，相对config path按launchd repo WorkingDirectory解析。
- empty、mismatch、unknown、missing、disabled、wrapper与parser failure全部fail closed。
- preflight只构造内存control plane，不打开SQLite/JSONL/log/lock/heartbeat，不spawn CLI、不联网。
- 所有失败统一安全文案，禁止回显owner/target/grant/path/command/raw parser input。

**如何避免再次踩中**
- readiness必须覆盖下一步真实启动使用的同一validation path；不能只对某个配置文件做lint。
- doctor/preflight不得通过“试运行完整服务”获得证据，诊断本身应无状态、无网络、可重复。
- 每个OK claim写清证明层级：artifact、binding、runtime health、provider E2E、external receipt不能互相替代。
- 配置规则若影响authorization或sandbox，优先复用production implementation，不维护looser shadow policy。

**相关链接**
- ROUNDS Round 214
- ADR-0052
- Goal Brief `docs/superpowers/specs/2026-07-21-standing-autonomy-deployment-preflight.md`
- B-014

### [P-071] 复用执行runner时不能连同另一种业务意图的grader一起复用

**状态**:🟢 RESOLVED(intent-specific preauthorized runner + derived receipts)
**首次踩中**:Round 215
**最后更新**:2026-07-21
**影响范围**:standing autonomy、offline delegation、TaskBus terminal state、inbox/morning evidence

**症状**
Round 213的preauthorized standing task复用了`_run_delegated_task`。该runner在普通TaskBus stream结束后会执行
`/overnight`专属handoff completeness检查；一个正常的`inspection complete`因此先DONE、随后又被标成FAILED。
原测试只断言Adapter收到task和timeout可interrupt，没有断言成功终态，缺陷直到receipt E2E才暴露。

**根因**
把“提交/流式收集”的通用机制和“overnight输出必须包含handoff结构”的业务grader封装在同一runner中。调用方想复用
前者，却无意继承后者。没有结果receipt时，这类终态覆盖又很难在老板视图被识别。

**解决方案 / 缓解措施**
- preauthorized runner直接调用普通`_run_task`并保留自己的wall-clock timeout/interrupt，不经过overnight grader。
- 新增derived receipt，用proposal/task/grant metadata和authoritative snapshot投影done/failed/interrupted等状态。
- accepted但无task或metadata不一致显示`evidence_missing`，不自动retry/refund。
- scheduled success/timeout都在第二次morning tick验证receipt且Adapter不重复接活。

**如何避免再次踩中**
- 复用runner前拆分mechanism与intent-specific policy：streaming、timeout可复用，handoff grading不可跨意图复用。
- E2E不能只断言“任务已派发”；必须断言最终TaskStatus和下一次恢复视图。
- 任何终态后处理都要有测试证明不会把已完成状态改成另一业务合同的失败。
- 老板缺席链路必须显式投影accepted-without-evidence crash window，不能依赖人工跨表猜测。

**相关链接**
- ROUNDS Round 215
- ADR-0053
- Goal Brief `docs/superpowers/specs/2026-07-21-standing-autonomy-execution-receipts.md`
- B-014

### [P-072] Terminal usage receipt 不能冒充当前调用的硬 token / cost 上限

**状态**:🟢 RESOLVED(post-run cumulative circuit breaker;provider-native hard cap pending)
**首次踩中**:Round 216
**最后更新**:2026-07-21
**影响范围**:Codex Adapter、TaskBus audit、standing grant、commercial cost boundary、B-014

**症状**
standing grant已有run次数和wall-clock timeout，直觉上再加一个`max_tokens`字段就像获得了商用成本上限。但Codex
machine-readable usage只在terminal `turn.completed`出现；当前调用的token已经消耗，且事件不提供可证明的美元账单。
项目原有`TASK_USAGE_RECORDED`也只有fixture/解析器，没有Adapter真正写入。

**根因**
混淆了pre-run enforcement、in-flight telemetry和post-run accounting。完成后的实际usage能约束下一次授权，不能倒流
阻止本次越界；cached/reasoning字段还是output的细分，不能随意重复相加或套公开价表。

**解决方案 / 缓解措施**
- preauthorized Codex使用`--json`，只解析terminal usage并让TaskBus写结构化audit。
- accepted proposal持久化usage；grant用`token_stop_threshold`在下一次dispatch前按同grant累计实测量熔断。
- 任何已消费run缺usage都fail closed，receipt显示`evidence_missing`，不按0继续。
- 明确称post-run cumulative circuit breaker；不声称per-run hard cap，不自行填`cost_usd`。

**如何避免再次踩中**
- 每个预算字段都回答：数据在调用前、调用中还是调用后可得；谁真正执行中断。
- provider-native limit不存在时，字段名、UI和ADR必须写清overshoot窗口。
- usage schema漂移或崩溃导致缺证时保守停授，不能用估算值修补authorization truth。
- 美元成本必须绑定model、auth/billing tier和provider bill evidence；token receipt只是用量事实。

**相关链接**
- ROUNDS Round 216
- ADR-0054
- Goal Brief `docs/superpowers/specs/2026-07-21-post-run-provider-usage-circuit-breaker.md`
- B-014

### [P-073] Transport DONE 不能冒充 standing charter 结果通过

**状态**:🟢 RESOLVED(structured result contract + local source verification)
**首次踩中**:Round 217
**最后更新**:2026-07-21
**影响范围**:scheduled standing autonomy、proposal receipt、老板早报、无人继续执行

**症状**
TaskBus显示DONE且usage存在时，老板视图会把任务看成成功；但provider可能只返回空泛总结、blocked结果、自相矛盾的
complete，或引用不存在的仓库证据。若下一次调度只看transport与预算，它仍会继续消耗无人授权。

**根因**
混淆了transport completion、result contract acceptance与业务真值。JSON形状、charter覆盖、本地文件位置和语义正确性
是不同证据层；前两层缺失不应继续，后一层也不能由“路径存在”伪造。

**解决方案 / 缓解措施**
- Codex固定使用versioned output schema；prompt将charter条目编号为`A*`/`S*`。
- 本地验证精确覆盖、状态一致性、repo-relative path边界和file/line存在，形成complete/blocked/invalid receipt。
- raw JSON不进老板IM；inbox/morning分开展示task status与outcome coverage。
- prior result missing、invalid或blocked全部停授，不自动retry/refund。

**如何避免再次踩中**
- 所有无人链路都必须分别回答“进程结束了吗”“结果合同通过了吗”“业务事实是真的吗”。
- deterministic verifier只能声明它实际验证的shape/coverage/location，不扩大成语义或时效性证明。
- 结果不健康时先恢复/人工核对，不能让scheduled loop用下一次provider调用替代验收。
- schema enforcement与本地validation必须同时存在；任一层漂移都fail closed。

**相关链接**
- ROUNDS Round 217
- ADR-0055
- Goal Brief `docs/superpowers/specs/2026-07-21-standing-result-contract.md`
- B-014

### [P-074] JSON Schema 不能单独充当无人结果的资源预算

**状态**:🟢 RESOLVED(fixed result envelope across config/adapter/capture/validator)
**首次踩中**:Round 218
**最后更新**:2026-07-22
**影响范围**:standing charter、Codex Adapter、Orchestrator capture、result receipt、runtime memory/state

**症状**
standing result已经要求JSON Schema，但原schema没有`maxLength/maxItems`，Orchestrator也会把所有provider正文加入
`captured`。超长summary、海量source或忽略schema的final message可能在无人运行时放大内存，并把错误恢复变成大正文。

**根因**
把“结构合法”误当成“资源有界”。字段schema、总序列化长度、Adapter返回值、编排capture和durable receipt属于不同
边界；只限制其中一层无法对schema drift、测试Adapter或恶意输出fail closed。

**解决方案 / 缓解措施**
- 固定32K total result、criteria/stop/source/list/text/path上限，并同步到schema和Pydantic。
- charter配置入口拒绝超过结果合同的criteria/stop/text，避免生成不可满足任务。
- Codex Adapter与Orchestrator最多保留上限+1，validator将其稳定分类为`result_too_large`。
- 重复key/字段越界与语法错误分开分类；只持久化bounded receipt，不保存raw正文。

**如何避免再次踩中**
- 每个外部/AI payload都分别检查shape、field cardinality、total bytes/chars、stream capture与durable state。
- schema enforcement不能替代consumer-side limit；provider遵守只是第一层。
- 超限必须显式invalid并停授，不能静默截断后继续当业务结果。
- 本地接收上限不是provider token/cost cap，产品口径必须保留时间边界。

**相关链接**
- ROUNDS Round 218
- ADR-0056
- Goal Brief `docs/superpowers/specs/2026-07-22-bounded-standing-result-envelope.md`
- B-014

### [P-075] 完成时 file/line 存在不能证明老板接手时证据仍然有效

**状态**:🟢 RESOLVED(bounded source fingerprint + handoff revalidation)
**首次踩中**:Round 219
**最后更新**:2026-07-22
**影响范围**:standing result、SQLite restart、老板早报、下一次scheduled autonomy

**症状**
standing result在完成时已经验证repository-relative file/line存在，但文件之后可能被修改或删除。若老板面和下一次
调度继续沿用旧的`outcome=complete`，系统会把一个可变路径误当成仍然成立的证据。

**根因**
混淆了point-in-time location validation与handoff-time evidence integrity。只保存path/line无法判断内容是否变化；
反过来，无界重hash全部历史和任意大小文件又会让完整性检查成为新的IO风险。

**解决方案 / 缓解措施**
- complete receipt保存最多16个source的canonical path、line、size和full-file SHA-256，不保存正文。
- 单文件最多256KiB；同文件多行只hash一次。下一次dispatch只复核最近成功结果，老板面只复核最近5份。
- 内容变化投影`drifted`，文件/root/legacy manifest缺失投影`missing`；两者都停止后续scheduled dispatch。
- path/hash只留在owner-local SQLite，不进入老板IM；owner核对后通过新的人工运行生成新receipt，不自动重跑。

**如何避免再次踩中**
- 所有跨时间使用的AI证据都要回答“当时存在”和“现在仍是同一份”是否分别有证据。
- revalidation必须同时有历史窗口、文件数量和单文件大小上限，不能用安全名义引入无界IO。
- hash只证明字节漂移，不是来源签名、Git attestation或业务语义真值。
- drift后不能让下一次provider调用替代owner判断；先检查变更，再决定是否重新验收。

**相关链接**
- ROUNDS Round 219
- ADR-0057
- Goal Brief `docs/superpowers/specs/2026-07-22-standing-evidence-fingerprint-drift.md`
- B-014

### [P-076] Pending approval 不是可以永久保存的能力票据

**状态**:🟢 RESOLVED(frozen deadline + transactional expiry)
**首次踩中**:Round 220
**最后更新**:2026-07-22
**影响范围**:风险审批、SQLite restart、老板inbox/morning、audit recovery

**症状**
写文件、shell和destructive任务虽然会停在`waiting_approval`，但原实现没有deadline。老板数天后批准旧task时，
repository、外部条件和意图上下文可能已经变化，系统仍会直接dispatch。若只在内存加timer，restart又会重置边界。

**根因**
把“等待人工决定”误当成“永久授权尚未消费”。approval本质是针对一份具体上下文的短期能力票据；其deadline、
terminal task状态和audit intent还必须在同一crash-consistent边界内变化。

**解决方案 / 缓解措施**
- 新approval创建时冻结aware `expires_at`，默认24小时，只允许owner配置5分钟到7天。
- startup、老板视图和approval action前lazy sweep；精确到期即`expired/rejected`且不dispatch。
- SQLite在一个事务里更新approval/task并写`approval_expired` outbox；sink失败保留pending重投。
- legacy无deadline记录按当前bounded policy推导，naive timestamp fail closed；配置变化不延长新格式旧票据。

**如何避免再次踩中**
- 所有可延后消费的authorization都要区分创建时间、冻结deadline和消费时间。
- deadline必须随票据持久化，不能在restart时按新配置重新生成。
- time-based状态若同时影响业务状态和audit，必须走事务/outbox，不能三次独立写。
- expiry只能要求重新确认，不得自动批准、重提或复用旧副作用上下文。

**相关链接**
- ROUNDS Round 220
- ADR-0058
- Goal Brief `docs/superpowers/specs/2026-07-22-bounded-approval-lease.md`
- B-010

### [P-077] Requester 自审批只有在 IM requester 先被认证时才安全

**状态**:🟢 RESOLVED(owner sender + trusted target ingress gate)
**首次踩中**:Round 221
**最后更新**:2026-07-22
**影响范围**:Telegram/Feishu ingress、普通任务、状态命令、风险审批、scheduled morning

**症状**
`RequesterOrListedApproverPolicy`允许task requester处理自己触发的approval，这符合单owner体验；但Phase 1此前把任何
Bot来信都直接交给Orchestrator。陌生sender因此可以读取状态、消耗provider，甚至提交风险任务后以同一sender批准。
只加sender allowlist后，合法owner在公共群发送`/inbox`仍会让AICO把公司状态回复到该群。

**根因**
把IM平台传来的`sender_id`当成已经授权的老板身份，却没有在业务入口建立显式authentication/authorization边界；
同时只考虑“谁发的”，没有考虑“结果将回到哪里”。approval policy不能替代控制面ingress policy。

**解决方案 / 缓解措施**
- 正式Phase 1在command解析前要求configured channel、owner sender和trusted target同时精确匹配；空配置deny all。
- 未授权消息不回复、不创建task、不读写业务audit/memory、不调用Adapter；陌生`/approve`不能改变既有approval。
- reviewer必须是owner，morning target必须trusted；identity list/cardinality/长度/placeholder均有界。
- 默认拒绝日志脱敏并按2的幂限流；显式foreground discovery仍deny业务，doctor禁止安装。
- Channel transport不得在guard之前记录raw sender；Telegram入口只保留update/raw ref/字符数。

**如何避免再次踩中**
- requester/actor字段是业务归属，不等于入口认证；所有外部Channel都必须在解析和副作用前统一授权。
- sender和reply target要同时绑定，避免合法owner把敏感结果带到错误会话。
- bootstrap不能靠永久开放命令；discovery必须显式、短时、local-only并被production preflight拒绝。
- IM sender ID依赖平台账号安全，不是密码学owner signature；账号接管必须在平台侧撤销。

**相关链接**
- ROUNDS Round 221
- ADR-0059
- Goal Brief `docs/superpowers/specs/2026-07-22-owner-bound-im-ingress.md`
- B-010

### [P-078] 有deadline不等于系统时间回拨时授权仍然有界

**状态**:🟢 RESOLVED(persisted high-water + monotonic rollback fence)
**首次踩中**:Round 222
**最后更新**:2026-07-22
**影响范围**:approval lease、standing autonomy、SQLite restart、scheduled morning

**症状**
Approval和standing grant都有aware expiry，但若系统wall clock向后调整，`now < expires_at`会更久成立。只检查
approval `created_at`无法保护standing grant，也无法发现创建后已经经过、但wall没有体现的进程内时间。

**根因**
把timezone-aware timestamp误当成monotonic/trusted time。aware只消除时区歧义，不保证时间不会倒退；单进程timer
又不能跨restart保存，联网NTP则会把授权安全边界耦合到外部服务。

**解决方案 / 缓解措施**
- SQLite保存单行authorization high-water；所有approval/preauthorization敏感入口先推进并检查该锚点。
- 同进程把monotonic elapsed叠加到最近安全wall baseline，覆盖长时间空闲后的回拨；重启后继续使用持久锚点。
- 允许5秒校时容差；超过后废止pending approval并停standing/new risk，high-water不回退，追平后只接受新授权。
- 复用approval事务/outbox留下稳定审计，不自动改系统时间、重提task或重新消费grant。

**如何避免再次踩中**
- 任何expiry/budget窗口都要分别回答wall clock是否可回拨、进程restart后时间锚点是否保留。
- timezone-aware、NTP enabled和monotonic分别解决不同问题，不能互相冒充。
- 时间异常时优先废止旧能力并要求新上下文，不要通过扩大TTL或降低high-water恢复执行。
- 本地锚点不是TPM、签名或外部可信时间；恶意主机和owner-fenced restore/reset仍是独立安全边界。

**相关链接**
- ROUNDS Round 222
- ADR-0060
- Goal Brief `docs/superpowers/specs/2026-07-22-authorization-clock-rollback-fence.md`
- B-010 / B-014

### [P-079] 追加写JSONL不等于审计历史防篡改

**状态**:🟢 RESOLVED(hash chain + sealed checkpoint + fail-closed replay)
**首次踩中**:Round 223
**最后更新**:2026-07-22
**影响范围**:`JsonlAuditSink`、runtime replay、metrics、recovery outbox、service doctor、B-013

**症状**
审计sink只通过`open("a")`追加，但磁盘文件仍能被有效JSON替换、整行删除或重排。旧reader只验证schema，因此修改后的
历史会被安静地重放到`/metrics`、`/audit`和runtime startup；“append-only”只是writer行为，不是证据属性。

**根因**
把API调用方式、Unix文件权限和历史完整性混为一谈。单条checksum也只能发现内容变化，不能证明顺序或tail没有被删除；
仅做hash chain又无法发现删除最后若干条。

**解决方案 / 缓解措施**
- 每个新event包含canonical payload的previous/head SHA-256 link；独立checkpoint锚定count、byte size与head。
- writer用process lock串行化，先append+fsync再原子更新checkpoint；只允许完整有效链的checkpoint lag自动收敛。
- replay、runtime和doctor统一拒绝mutation/reorder/insertion/truncation/torn tail/duplicate id/symlink/宽权限。
- legacy由owner核对后显式seal，不重写event bytes；ledger/checkpoint/lock收紧为owner-only。

**如何避免再次踩中**
- 写“append-only”前分别回答：谁阻止内容修改、谁检测顺序变化、谁检测tail删除、crash在哪一步恢复。
- migration seal只能锚定当前baseline，不能追溯证明旧历史；不得把seal称为repair或签名。
- 本地hash/checkpoint不抵抗能同时改ledger与checkpoint的同主机攻击者；更强声明必须有独立签名/WORM authority。
- 备份与恢复必须把audit JSONL和checkpoint作为一组，不能只复制其中一个。

**相关链接**
- ROUNDS Round 223
- ADR-0061
- Goal Brief `docs/superpowers/specs/2026-07-22-tamper-evident-audit-ledger.md`
- B-013

### [P-080] 两个完整文件不等于一个一致的审计恢复点

**状态**:🟢 RESOLVED(writer-locked snapshot + single-file verified artifact)
**首次踩中**:Round 224
**最后更新**:2026-07-22
**影响范围**:audit ledger/checkpoint、off-device export、B-013、operator backup

**症状**
Round 223要求audit JSONL与checkpoint成组备份，但人工先后复制仍有时间窗口：runtime可在中间追加event并推进checkpoint，
最终两个副本分别可读却不是同一point-in-time。把它们放进同一目录或事后压缩，不能追溯消除复制窗口。

**根因**
把“资产清单完整”误当成“快照一致”。多文件恢复点需要明确writer barrier；manifest如果只记录复制后的文件，也只能证明
artifact内部当前字节，不能证明复制时live source没有跨版本。

**解决方案 / 缓解措施**
- 复用audit process lock，在同一锁持有期内验证、收敛合法checkpoint lag并复制ledger/checkpoint。
- 固定三member的ZIP_STORED避免漏文件与解压攻击面；member size/hash、ledger chain/checkpoint和outer SHA分层校验。
- 输出采用owner-only new-path + fsync，不覆盖既有artifact；offline verify不依赖live path并实际materialize验证。
- manifest/summary不含source path或payload，但artifact本身含完整审计正文，必须由外部层加密。

**如何避免再次踩中**
- 每个多文件backup都要回答：一致性barrier在哪里、复制期间谁还能写、发布是否no-overwrite、失败是否有半成品。
- “ZIP/manifest/hash”只解决包装与检测，不自动提供source point-in-time或签名；必须先锁住/冻结source。
- outer SHA应存于独立信任位置；artifact与SHA同盘同权限不抵抗同主机重写。
- writer-locked全量copy的延迟随ledger增长；未有rotation/增量前不要把它静默放进高频scheduler。

**相关链接**
- ROUNDS Round 224
- ADR-0062
- Goal Brief `docs/superpowers/specs/2026-07-22-portable-audit-recovery-point.md`
- B-013

### [P-081] 可验证备份不等于可安全覆盖 live 审计

**状态**:🟢 RESOLVED(owner fence + mandatory preservation + fail-closed retry)
**首次踩中**:Round 225
**最后更新**:2026-07-22
**影响范围**:`aico-audit restore|drill-backup`、audit ledger/checkpoint、事故取证、B-013

**症状**
一个ZIP能离线verify后，最直觉的恢复做法是解压并依次覆盖live ledger/checkpoint。但active runtime可能同时写入；当前
live可能已损坏而无法生成普通backup；进程还可能在只替换一个文件后退出。直接删live或重新seal会进一步销毁现场证据。

**根因**
把artifact integrity、live mutation authorization和multi-file publication混为一件事。ZIP内部自洽只证明source可用，
不证明何时能覆盖、覆盖前保存了什么，也不提供跨两个文件的filesystem transaction。

**解决方案 / 缓解措施**
- restore强制expected SHA、真实AICO state DB identity、runtime owner fence、new preservation path和显式`--yes`。
- live有效时先创建标准verified safety backup；无效时原样复制到标记为`unverified_quarantine`的取证artifact。
- staged pair先完整验证，再按ledger/checkpoint顺序replace+directory fsync；中断后严格reader fail closed，同一备份可重跑。
- disposable drill调用同一production materializer，不触碰live并输出bounded owner-only evidence。

**如何避免再次踩中**
- 每个restore都要分别回答：谁批准覆盖、谁冻结writer、如何保留当前现场、第二个replace失败后系统读到什么。
- “原子恢复”不能用于描述两个独立文件的两次rename；准确口径是中断可检测、启动拒绝、重跑可收敛。
- 损坏现场只能quarantine，不能给它verified/backup标签；安全留存失败时宁可不恢复。
- 自动backup/verify可调度，destructive restore不可调度，也不能自动选择latest artifact。

**相关链接**
- ROUNDS Round 225
- ADR-0063
- Goal Brief `docs/superpowers/specs/2026-07-22-owner-fenced-audit-restore.md`
- B-013

### [P-082] 两个验证通过的 component artifact 不等于一次业务恢复集合

**状态**:🟢 RESOLVED(bounded capture window + fixed coverage ledger + combined drill)
**首次踩中**:Round 226
**最后更新**:2026-07-22
**影响范围**:`aico-recovery`、state/audit component RPO、off-device transfer、B-013

**症状**
State backup和audit backup都能独立verify后，operator很容易按相似文件名把它们当作“一次备份”。但两者可能来自不同日期，
也没有任何机器证据说明memory、配置、secret、standing grant或receiver state是否覆盖。两个绿色结果制造了全资产DR假阳性。

**根因**
把component integrity、capture-time relationship与asset coverage混为一谈。独立SHA只能绑定各自字节，不能绑定另一artifact、
采集窗口或未出现的资产；停止runtime也不会让SQLite/JSONL/独立receiver自动获得一个共享transaction。

**解决方案 / 缓解措施**
- 一次capture按state→audit生成两个既有格式artifact，并以outer recovery set绑定其hash/size/summary和时间窗口。
- schema强制`global_transaction=false`与`business_restore_ready=false`，不能通过正常manifest把局部集合升级成完整DR。
- 固定coverage ledger列出captured、snapshot missing、source-control restore、secret reinjection、external backup与ephemeral排除。
- verify深入调用两个production verifier；drill再实际调用两个production materializer，不以top manifest解析成功代替恢复演练。

**如何避免再次踩中**
- 每个多组件DR声明都要分别回答：字节如何绑定、时间关系是什么、哪些资产明确缺失、是否真的走过restore路径。
- “同一目录/同一日期/同一命令生成”不是global consistency；没有shared transaction就必须暴露capture window与skew。
- coverage清单必须包含缺项，不能只列“包里有什么”；readiness字段不能由operator凭感觉改true。
- 合并transport artifact不等于授权合并restore；破坏性恢复仍按component fence和隔离业务验收执行。

**相关链接**
- ROUNDS Round 226
- ADR-0064
- Goal Brief `docs/superpowers/specs/2026-07-22-bounded-window-core-recovery-set.md`
- B-013

### [P-083] Append-only memory JSONL 不等于可恢复的可信记忆

**状态**:🟢 RESOLVED(process lock + hash chain/checkpoint + portable recovery)
**首次踩中**:Round 227
**最后更新**:2026-07-22
**影响范围**:`JsonlMemoryStore`、prompt/experience continuity、`aico-memory`、`aico-recovery`、B-013

**症状**
旧memory store把“每次写一行JSONL”当作durable：两个runtime各自持有陈旧索引，写失败前内存状态已更新；历史字段修改、
记录重排、tail截断和只复制一半恢复资产都可能继续被加载，影响后续agent决策却没有证据告警。

**根因**
Append-only只描述预期写法，不提供writer serialization、durable commit顺序、历史完整性或恢复点边界。MemoryAtom允许同ID多版本，
也不能用“拒绝duplicate ID”代替版本语义和chain校验。

**解决方案 / 缓解措施**
- writer在process lock内刷新ledger，先append+fsync，再原子发布tail checkpoint；索引只在durable append返回后重建。
- 独立memory hash domain覆盖canonical envelope，checkpoint锚定record count/byte size/head；legacy必须owner显式seal。
- backup在writer lock内复制matching pair，offline verify还加载MemoryAtom/MemoryEdge domain model；restore保留或隔离旧现场。
- recovery-set v2只在上述component primitive完成后把memory标为captured，仍不提升full DR readiness。

**如何避免再次踩中**
- 任何会进入prompt或授权判断的append-only文件，都要分别回答并发writer、half-commit、tail truncation和portable recovery point。
- 写入顺序必须是durable truth先于进程视图；失败后不能留下只在内存可见的phantom状态。
- legacy migration不能自动seal未知字节；owner核对与显式命令是信任边界。
- 同ID新版本是业务语义，不得在完整性层误判为collision；完整性层只验证字节序列和checkpoint。

**相关链接**
- ROUNDS Round 227
- ADR-0065
- Goal Brief `docs/superpowers/specs/2026-07-22-tamper-evident-memory-recovery.md`
- B-013

### [P-084] Capture 时的当前 HEAD 不等于 reviewed recovery revision

**状态**:🟢 RESOLVED(independent expected revision + clean checkout/config parity)
**首次踩中**:Round 228
**最后更新**:2026-07-22
**影响范围**:`aico-recovery`、Project/Persona config、deployment review、B-013

**症状**
数据组件都能恢复后，最直接的配置合同是把capture时`git rev-parse HEAD`写进manifest。但这会把任意本地commit自动称为
“reviewed”；dirty tracked/untracked文件、active config指向checkout外文件或配置字节与commit blob不同也可能被忽略。

**根因**
把“可识别当前版本”与“由独立authority选择了允许恢复的版本”混为一谈。commit SHA只绑定Git对象，不绑定operator选择、
worktree cleanliness、实际读取的配置文件或恢复时checkout状态。

**解决方案 / 缓解措施**
- capture强制接收独立的完整expected commit，并与HEAD精确比较；manifest明确authority仅是operator-supplied revision。
- 同时绑定HEAD tree、Git object format和active config的relative path/blob OID/size/SHA，不复制正文。
- capture/verify-checkout都要求worktree root与clean tracked/untracked状态；config必须在checkout内、非symlink且等于commit blob。
- recovery set区分物理`included`与`recovery_contract_ready`，配置可从revision恢复但不能伪称已嵌入bundle。

**如何避免再次踩中**
- 任何“reviewed/approved revision”都必须说明谁在artifact之外选择了它；当前HEAD、自生成时间或文件名都不是authority。
- 恢复代码版本要验证worktree，不只验证commit：dirty文件和active config path同样会改变运行行为。
- 不把source-control restore偷换成复制当前配置；secret与源码正文应保持各自边界。
- commit/hash不是平台review签名或remote availability证明，外部clone和业务演练仍需单独取证。

**相关链接**
- ROUNDS Round 228
- ADR-0066
- Goal Brief `docs/superpowers/specs/2026-07-22-reviewed-config-revision-recovery.md`
- B-013

### [P-085] Secret hash不是安全的恢复回执，presence也不是远端认证

**状态**:🟢 RESOLVED(slot/mode contract + owner decision receipt + external-auth gap)
**首次踩中**:Round 229
**最后更新**:2026-07-22
**影响范围**:`aico-recovery`、`.env`、standing grant、AI provider auth、B-013/B-014

**症状**
为证明灾后secret与grant已恢复，最直接的做法是把`.env`/grant放进bundle，或只保存它们的SHA-256。但前者直接扩大泄露面；
后者会为低熵token/ID产生离线猜测和稳定关联，还会把合规轮换后的新secret误判为不一致。反过来，只检查环境变量非空又可能
被写成“Claude/Codex认证已恢复”，把本地presence偷换成远端事实。

**根因**
混淆了三类证据：需要恢复哪些槽位、当前本地material是否通过binding preflight、外部服务是否真实接受credential。它们的
authority、敏感性和验证时机不同，不能用一个hash或一个绿色doctor结论替代。

**解决方案 / 缓解措施**
- capture只读取owner-only且Git未跟踪的`.env`，记录control-plane secret slot名称、channel和standing grant enabled mode，不记录值、hash、owner/target或grant正文。
- 灾后允许secret轮换与grant重新签发，但必须提供safe owner decision reference；receipt绑定set SHA、revision、当前slot/count和时间。
- receipt复用production service/grant preflight，并以owner-only、atomic new-path发布；verify再次校验独立receipt SHA和当前material。
- AI provider认证单列为required unresolved asset，receipt固定`external_authentication_live_verified=false`，等待真实provider样本。

**如何避免再次踩中**
- 不要为“避免保存secret”就默认保存普通hash；先判断输入熵、轮换语义与谁持有独立authority。
- “configured/present/preflight passed”不能写成“远端认证成功”；需要实际外部请求的事实必须单独验收。
- owner decision reference是审计关联，不是数字签名；不要借它声称owner身份已被密码学证明。
- secret/grant恢复工具必须先验证exact checkout和runtime binding，不能只看文件存在或JSON可解析。

**相关链接**
- ROUNDS Round 229
- ADR-0067
- Goal Brief `docs/superpowers/specs/2026-07-22-secret-free-runtime-reinjection-receipts.md`
- B-013
- B-014

### [P-086] 第二故障域receiver不能随主系统恢复集同步回滚

**状态**:🟢 RESOLVED(independent receiver recovery contract + shared worker fence)
**首次踩中**:Round 230
**最后更新**:2026-07-22
**影响范围**:`aico-dead-man-receiver`、`aico-dead-man-recovery`、core recovery set、B-012/B-013

**症状**
主AICO的state/audit/memory恢复工具完成后，最直观的补缺方式是把receiver SQLite也加进同一个ZIP和combined restore。这样看似
“全资产”，实际会在AICO故障恢复时回滚仍正常工作的外部monitor、active outage和pending notification，抹掉事故证据。

**根因**
把“业务恢复需要知道该资产有合同”误解为“所有资产必须同一时刻snapshot并一起restore”。receiver有独立host、worker、RPO和
事故条件；两个主机没有共享事务。主机故障和receiver故障也不是同一个事件。

**解决方案 / 缓解措施**
- receiver使用独立online backup、exact schema/domain deep verify、disposable production restore drill与worker owner fence。
- 有效live恢复前生成verified safety；无法验证的DB/WAL/SHM原字节进入owner-only unverified quarantine。
- core schema v5只记录`external_component_recovery`合同就绪，保持`included=false`，不嵌入字节或声称同步时间点。
- restore只由receiver自身事故触发，要求独立SHA和显式确认；AICO恢复、scheduler或“latest”选择都不能触发。

**如何避免再次踩中**
- 每个外部observer/alert sink都先问：被观察者故障时它是否必须继续运行；若是，就不能绑定到被观察者的combined restore。
- coverage ledger的`recovery_contract_ready`不等于artifact captured、off-device存在或RPO通过，必须分别报告。
- 通用SQLite integrity/table count不能替代domain invariants；恢复后仍需验证monitor/outage/outbox与delivery语义。
- lock文件存在不是worker active；service与restore必须竞争同一kernel lock，不能靠删pid/lock文件绕过。

**相关链接**
- ROUNDS Round 230
- ADR-0068
- Goal Brief `docs/superpowers/specs/2026-07-22-independent-dead-man-receiver-recovery.md`
- B-012
- B-013

### [P-087] Provider CLI存在与credential已被远端接受不是同一事实

**状态**:🟢 RESOLVED(constrained live challenge + short-lived bound receipt)
**首次踩中**:Round 231
**最后更新**:2026-07-22
**影响范围**:`aico-recovery`、Claude/Codex adapter、runtime reinjection、B-013/B-014

**症状**
灾后最容易把`which claude/codex`、`--version`、环境变量非空或adapter health绿色写成“provider认证恢复”。这些检查都不联系
远端；反过来，直接跑一条普通业务任务又可能加载customization、调用工具、持久化session，并把prompt/output/error带入证据。

**根因**
混淆了本地binary readiness、远端authentication、业务执行质量和持续可用性四种事实；同时没有为恢复探测单独设计最小权限、
可判定response和privacy contract。

**解决方案 / 缓解措施**
- recovery contract记录required provider集合，恢复后逐一发送随机challenge；只接受exact response、terminal success和usage齐备。
- 内建Claude/Codex probe重新构造safe command，在private empty cwd运行，关闭tools/customization/session/user rules/network，限制
  process group时长与输出；不复用runtime中的bypass/yolo参数。
- 30分钟owner-only receipt绑定set/reinjection SHA、revision、owner decision、provider scope和probe executable hash；只存challenge SHA，
  不存challenge、prompt、output、stderr或credential。
- offline verify明确不replay live probe；receipt过期、command/scope/reinjection漂移都要求重新探测。

**如何避免再次踩中**
- 任何`authenticated/accepted by provider`声明都必须有真实远端请求，binary presence和local config不能替代。
- 恢复probe使用可判定随机challenge，不使用业务数据；provider没有安全结构化协议时fail closed，不猜文本。
- `recovery_contract_ready`与`post_restore evidence supplied`必须分字段报告；合同存在不等于本次恢复已经执行。
- receipt SHA是外部authority binding，不是数字签名；executable hash也不证明binary provenance或账号identity。

**相关链接**
- ROUNDS Round 231
- ADR-0069
- Goal Brief `docs/superpowers/specs/2026-07-22-live-provider-authentication-receipts.md`
- B-013
- B-014

### [P-095] Process alive 与 dead-man pulse fresh 不能证明 required 业务组件仍可用

**状态**:🟢 RESOLVED(machine contract;external endpoint sample pending)
**首次踩中**:Round 239
**最后更新**:2026-07-22
**影响范围**:`runtime_alerts.py`,`runtime_heartbeat.py`,scheduled outcome/recovery health,B-011

**症状**
morning outcome delivery耗尽、recovery artifact损坏或default adapter持续失败时，runtime component health已经FAILED；但后台task、
event loop和dead-man pulse仍可能正常。旧alert只观察owned-task recovery circuit，因此老板缺席时不会收到secondary incident，除非
以后主动运行doctor。

**根因**
把“进程/后台task仍活着”当成“商业主路径仍可用”，同时为了避免generic health驱动危险重启，把generic health也完全排除在
通知边界之外。repair signal和notification signal被错误绑定：前者需要精确owner/action，后者可以对稳定、required failure保守告警。

**解决方案 / 缓解措施**
- 仅required组件连续三份、时间递增的FAILED snapshot进入durable confirmation；optional、DEGRADED和瞬时失败不open。
- 第三次确认、incident和outbox同SQLite transaction提交；计数跨restart保留，重复/倒退snapshot不放大。
- OK才resolved，DEGRADED保持open；owned-task circuit与同名health incident去重。
- outbound component只含safe name或hash，不带异常、endpoint、secret、target或业务正文；该incident不授权任何自动repair。
- state schema v13把confirmation table纳入backup/reset，CLI只显示candidate count。

**如何避免再次踩中**
- liveness、owned-task recovery、dependency/component health和业务E2E必须分层取证；任一绿色不能替代其它层。
- “generic health不能驱动restart”不等于“generic health永远不能通知”；先定义required范围、稳定边沿和噪声预算。
- periodic snapshot变事件必须有durable confirmation、dedupe identity、同事务outbox与明确resolved条件。
- 对外alert只表达组件状态，不自动推导human read、业务损失、repair权限或provider replay安全性。

**相关链接**
- ROUNDS Round 239
- ADR-0077
- Goal Brief `docs/superpowers/specs/2026-07-22-confirmed-required-component-runtime-alerts.md`
- P-061
- P-062
- B-011

### [P-097] 独立receiver形成outage不等于缺席老板一定有可用通知出口

**状态**:🟢 RESOLVED(machine failover contract;external route sample pending)
**首次踩中**:Round 241
**最后更新**:2026-07-22
**影响范围**:`dead_man_receiver.py`,`dead_man_receiver_app.py`,receiver deployment,B-012

**症状**
receiver位于第二故障域、monitor/outage/outbox和worker都正常，甚至evidence能看到pending retry；但唯一owner notification webhook
长期失败时，老板不会主动查询admin endpoint，`/readyz`也按设计保持绿色以避免restart storm，事故因此仍可静默。

**根因**
把“独立发现故障”和“独立触达老板”合并为一个可用性结论。receiver与被监控Mac失效域独立，不代表receiver下游通知provider、
credential、账号或网络没有单点；让readiness失败只会重启sender，不能创造第二条送达路径。

**解决方案 / 缓解措施**
- 可选配置different-origin fallback，两路并发发送相同immutable event和stable idempotency key。
- 默认1-of-2 ACK结算以提高触达可用性；owner可显式要求2-of-2，quorum不得超过route count。
- quorum miss继续复用既有SQLite outbox、队首顺序和1/5/15分钟backoff；不因外部失败restart receiver。
- fallback token必须存在对应URL，route token彼此不同且不复用pulse/admin authority；错误保持通用、无URL/token/response正文。
- receiver schema v3持久化当前策略，并在event创建事务内冻结逐事件route count/quorum；pending期间配置变化fail closed，不能让
  原2-of-2事件在重启后按1-of-2结算。历史delivered event保留原策略，v1/v2保守迁移为1-of-1。
- evidence/recovery schema v3验证当前与逐事件策略；delivered只表示该事件冻结的local quorum，不保存或推断per-route/human-read事实。

**如何避免再次踩中**
- 对每个observer继续向下画到最终人类触点；“observer独立”与“notification path冗余”必须分开验收。
- 不用进程restart解决外部provider故障；重启不增加authority、网络路径或收件渠道。
- 1-of-2与2-of-2是不同产品策略：前者优化availability，后者优化双ACK证据，不得在故障时偷偷降级。
- 运行时settings不是durable authority；影响outbox结算的策略必须随event持久化，并用事务围栏拒绝pending期间漂移。
- different-origin只是静态最低门槛；真实商业声明仍要验证provider、账号、credential、网络与终端展示。
- 未出现稳定route-level成功/失败历史需求前，不提前引入per-route SQLite receipt；结算所需的逐事件策略不属于可省略的抽象。

**相关链接**
- ROUNDS Round 241
- ADR-0079
- Goal Brief `docs/superpowers/specs/2026-07-22-quorum-dead-man-notification-routes.md`
- P-096
- B-012
