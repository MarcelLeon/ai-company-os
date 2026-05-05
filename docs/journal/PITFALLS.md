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

### 人格化与状态
- P-013:Project Team 同一 role 可出现多个 appointment 导致 `/team` 重复成员

### 部署与运维
- (待填充)

### Java / Spring AI 相关
- (待填充)

### Python 相关
- P-003:本机默认 Python / uv 缓存与项目基线不一致
- P-004:`uv run` 本地 console script 触发构建依赖下载

### Adapter 层
- P-005:Codex CLI 全局参数必须放在子命令前

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
