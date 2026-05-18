# ADR-0017: Optional Agent Adapters

**状态**:Accepted
**日期**:2026-05-07
**决策者**:Codex
**相关 Round**:Round 66

---

## 背景与问题

人类明确近期要高优新增 CodeFlicker Adapter 和 Cursor Adapter,最终让 Telegram `/agents` 中有更多可用 agents。北极星第二句要求 AI 适配器化和能力可插拔,因此新 AI 工具必须通过既有 `AIAdapter` / `AdapterRegistry` 接入,不能污染核心编排。

问题是:第一切片是否直接把这些工具做成默认启用的写能力 Agent,以及如何处理 CLI 能力尚未完全 dogfood 的风险。

## 候选方案

### 方案 A — 直接默认启用并授予写能力
- 优点:`/agents` 立即更丰富,看起来更像完整 AI 公司。
- 缺点:Cursor / CodeFlicker CLI 都有文件修改和命令执行能力,远程 IM 默认放开会绕过现有审批纪律或导致非交互卡住。
- 复杂度:中。

### 方案 B — 先做可选只读 Adapter 第一切片
- 优点:不影响现有 Claude/Codex 链路;通过环境变量启用;默认能力只声明 `code_review` / `stream_output` / `interruptible`,写文件和 shell 任务仍由核心风险门禁拒绝。
- 缺点:第一切片更偏分析/规划,还不能替代 Claude 的写代码路径。
- 复杂度:低。

### 方案 C — 先只写调研文档,不写代码
- 优点:最稳。
- 缺点:不能让 `/agents` 真实增加成员,不符合“开始开发”的要求。
- 复杂度:低。

## 决策

选择 **方案 B:先做可选只读 Adapter 第一切片**。

具体包括:
- `CursorAdapter` 默认命令为 `cursor-agent -p --output-format text`。
- `CodeFlickerAdapter` 默认命令为 `flickcli -q --output-format text --tools '{"bash":false,"write":false}'`。
- 两者默认 `output_idle_timeout_seconds=90`,避免 CLI accepted 后长期无 stdout 占用 Adapter。
- `aico-phase1` 增加 `AICO_ENABLE_CURSOR_ADAPTER` 和 `AICO_ENABLE_CODEFLICKER_ADAPTER` 开关。
- 启用后内置 personas 增加 `cursor` 和 `codeflicker`,让 `/agents` 能展示新成员。

## 决策理由

- 符合北极星第一句:让远程 IM 里的“虚拟公司”有更多真实 AI 成员。
- 符合北极星第二句:新增工具只通过 Adapter / Registry / Persona 接入,核心不写工具专属分支。
- 符合北极星第三句:默认不授予写能力或 shell 能力,危险任务仍走既有审批和能力门禁。
- Cursor 官方 CLI 已有非交互 print mode;本机 CodeFlicker `flickcli --help` 已确认 quiet mode、`--cwd`、`--tools` 和 output format。

## 后果

### 正面后果
- 用户可通过环境变量快速让 `/agents` 出现 Cursor / CodeFlicker。
- 新 Adapter 复用 ClaudeCodeAdapter 的进程、流式输出、中断和 health check 逻辑,代码改动小。
- 后续 Trae / OpenClaw 可以复制同样模式,等第三个相似实现后再考虑抽象 CLI Adapter 配置。

### 负面后果
- Cursor 写能力、CodeFlicker yolo/autoEdit 模式暂不默认暴露。
- Cursor 本机未安装时 health check 会失败,需要用户自行安装并登录。
- CodeFlicker 需要内网/SSO 登录,真实 smoke test 依赖本机账号状态。

### 我们接受这些代价是因为

第一目标是安全地扩充 agents 名录和可路由能力,不是一次性把每个 CLI 的全部能力暴露到远程 IM。

## 不再做的事

- 不在核心编排中新增 `if cursor` / `if codeflicker`。
- 不默认启用 `cursor-agent --force`。
- 不默认启用 CodeFlicker `approval-mode yolo` 或打开 bash/write tools。
- 不在第一切片实现 provider session resume;等真实 dogfood 后再判断是否需要。

## 相关链接

- ADR-0002
- ADR-0007
- ADR-0010
- ROUNDS Round 65
- ROUNDS Round 66
- `src/aico/adapter/cursor.py`
- `src/aico/adapter/codeflicker.py`
