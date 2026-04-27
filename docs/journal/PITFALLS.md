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
- (待填充)

### 人格化与状态
- (待填充)

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
