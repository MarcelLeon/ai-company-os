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

### AI 间协作
- P-009:协作指令只支持冒号导致真实自然语言未触发 reviewer
- P-014:Reviewer 子任务已 accepted 但 Codex CLI 长时间无 stdout 且 IM 无中断入口
- P-025:长沉默 Adapter 任务被误判为 IM 挂死
- P-024:协作短指令引用父输出编号但 child task 丢失上下文

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
