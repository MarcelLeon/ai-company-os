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
- (待填充)

### Adapter 层
- (待填充)

### IM 通道
- P-006:审批命令依赖完整 task id 导致 Telegram 真实交互失败
- P-007:远程审批通过后仍触发底层 CLI 权限或沙箱失败
- P-008:Telegram polling await 长任务 handler 导致 `/status` / `/audit` 卡住
- P-010:Telegram 单条消息长度上限导致长输出像被吞掉
- P-011:后台缺少关键链路日志导致长任务卡点不可定位
- P-012:Telegram no-op edit 400 导致流式 handler 中断

### AI 间协作
- P-009:协作指令只支持冒号导致真实自然语言未触发 reviewer
- P-014:Reviewer 子任务已 accepted 但 Codex CLI 长时间无 stdout 且 IM 无中断入口

### 人格化与状态
- P-013:Project Team 同一 role 可出现多个 appointment 导致 `/team` 重复成员
- P-016:Appointment prompt 脚手架导致普通项目咨询误触发审批

### 部署与运维
- P-017:真实 Stage 3 录屏被底层 CLI 噪音污染
- P-018:httpx INFO 日志会把 Telegram Bot token 打进日志

### Java / Spring AI 相关
- (待填充)

### Python 相关
- P-003:本机默认 Python / uv 缓存与项目基线不一致
- P-004:`uv run` 本地 console script 触发构建依赖下载

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
**最后更新**:2026-05-20
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
- Codex Adapter 默认启用输出空闲超时。Round 57 首版阈值为 90 秒;Round 98 已放宽到 300 秒,
  返回 `adapter output idle timeout after 300s`,并释放并发槽位。
- 可通过 `AICO_CODEX_OUTPUT_IDLE_TIMEOUT_SECONDS` 调整 Codex 空闲超时阈值。

**如何避免再次踩中**
- 真实 smoke test 如果停在 `Task accepted` 后无输出,先查 `/status`,再用 `/interrupt <short_task_id>`。
- 重启到 Round 98 之后,如果忘记手动 interrupt,Codex 也应在 300 秒空闲超时后自动失败并释放并发槽位。
- 新增任何长任务入口时,必须确认 IM 侧有中断路径,不能只在 Adapter 接口里有 interrupt。
- 排查 Codex 卡住时,优先 grep task id,看是否有 `Stream output` 或 `Adapter process exited`。

**相关链接**
- ROUNDS Round 53
- ROUNDS Round 98
- ROUNDS Round 57

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
**最后更新**:2026-05-20
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
- Codex / optional CLI adapter 默认 output idle timeout 从 90 秒放宽到 300 秒,减少长思考任务被误杀。

**如何避免再次踩中**
- 不要把 `AdapterStatus.BUSY` 理解成“有任何任务在跑”;用户关心的是还能不能接新任务。
- 任命同一 agent 到多个高频 role 时,先看 `/agent <agent>` 的最大并发;超过上限应新增 agent 或降低并行派工。
- 如果真实 provider 长时间不吐 stdout,先用环境变量调大 timeout 或设计 heartbeat,不要回退到无限 busy。

**相关链接**
- ROUNDS Round 98
