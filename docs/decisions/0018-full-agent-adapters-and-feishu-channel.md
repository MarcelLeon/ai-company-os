# ADR-0018: Full Agent Adapters and Feishu First Channel

**状态**:Accepted
**日期**:2026-05-12
**决策者**:Codex
**相关 Round**:Round 67

---

## 背景与问题

人类明确要求 Cursor / CodeFlicker 从只读 MVP 升级为完整支持,并新增 Trae CLI、Gemini CLI Adapter。同时要求扩充 AI Company 的有效岗位,并从飞书、钉钉、QQ、微信中选择一个官方接口文档最好、接入成本可控的 Channel。

这会同时影响 Adapter 能力边界、默认 role 体系和 Channel 插件路线,需要单独决策,不能继续沿用 ADR-0017 的“可选只读第一切片”结论。

## 候选方案

### 方案 A — 继续保持 Cursor / CodeFlicker 只读,先只新增 Trae/Gemini 只读
- 优点:最安全,实现小。
- 缺点:不满足“完整支持”,也不能让这些 CLI 真正承担开发任务。
- 复杂度:低。

### 方案 B — 在 AICO 审批门禁保护下开放完整 CLI 能力
- 优点:Cursor / CodeFlicker / Trae / Gemini 都能承担写代码、跑命令、review、长任务和中断;远程危险任务仍先经过 AICO 风险识别和 `/approve`。
- 缺点:底层 CLI 使用 `--force` / `yolo` / 等价非交互批准模式后,如果风险识别漏判,CLI 侧不会再次询问。
- 复杂度:中。

### 方案 C — 每次按任务风险动态切换 CLI approval mode
- 优点:理论上最安全。
- 缺点:当前 `AIAdapter.receive_task()` 只收到 Task,风险评估在 TaskBus 内部,需要扩展公开协议;这会扩大核心改动面。
- 复杂度:高。

## Channel 选择

选择 **飞书 / Lark** 作为第一个非 Telegram Channel。

理由:
- 飞书开放平台有较完整的官方 Server API 文档,覆盖 `im/v1/messages` 发送消息和事件订阅。
- 文本收发路径标准化:事件回调 `im.message.receive_v1` + REST 发送消息。
- 官方文档和开发者后台能力比 QQ/微信更适合先做企业 IM dogfooding;QQ/微信在审核、白名单、合规和非标准机器人能力上摩擦更高。
- 钉钉也可行,但飞书 / Lark 的国际化文档、事件订阅和自建应用模型更贴近未来多团队协作入口。

参考:
- Feishu send message: https://open.feishu.cn/document/server-docs/im-v1/message/create
- Feishu event subscription: https://open.feishu.cn/document/server-docs/event-subscription-guide/event-subscription-configure-/request-url-configuration-case
- Cursor CLI: https://docs.cursor.com/en/cli/overview
- Gemini CLI: https://google-gemini.github.io/gemini-cli/docs/cli/
- Trae CLI: https://docs.trae.cn/cli

## 决策

选择 **方案 B:在 AICO 审批门禁保护下开放完整 CLI 能力**,并把飞书作为第一个新增 Channel。

本轮范围:
- Cursor / CodeFlicker capabilities 包含 `code_edit` 和 `shell_exec`。
- Cursor 默认命令改为 `cursor-agent -p --force --output-format text`。
- CodeFlicker 默认命令改为 `flickcli -q --approval-mode yolo --output-format text`。
- 新增 Trae Adapter,默认命令 `trae-cli --print --yolo`。
- 新增 Gemini Adapter,默认命令 `gemini --approval-mode yolo --output-format text`。
- 新增 FeishuChannel,覆盖文本发送、消息编辑/删除、URL verification、`im.message.receive_v1` 文本事件解析。
- 默认 role 模板补充 PM、Senior Architect、Golden Tester、Market Risk、Legal Compliance 等确实服务 AI 公司生产流的岗位。

## 决策理由

- 符合北极星第一句:让远程 IM 里的虚拟公司拥有更多真实可派工成员和更像公司的职责分工。
- 符合北极星第二句:新增 AI 工具仍只通过 `AIAdapter` / `AdapterRegistry` / Persona 接入;新增 IM 仍只通过 `IMChannel` 接入。
- 符合北极星第三句:危险任务仍走 AICO 风险识别、审批、审计和中断;底层 CLI 非交互批准模式只是避免远程任务卡在本机提示。

## 后果

### 正面后果
- `/agents` 可以展示更多真实 CLI 成员:Cursor、CodeFlicker、Trae、Gemini。
- 这些成员能承担真实实现任务,而不是只做只读分析。
- 飞书 Channel 有了可测试插件边界,后续可接 FastAPI webhook 部署层。
- Role 体系更有 company 感,且岗位都围绕交付、架构、测试、市场风险、合规审查等真实产出。

### 负面后果
- CLI 完整能力依赖 AICO 风险识别准确性;底层 CLI 不再作为第二道交互审批。
- Feishu 本轮只完成 Channel 插件和 webhook payload 解析,还未把 FastAPI 公网 callback server 纳入 `aico-phase1` 生命周期。
- Cursor 本机仍需单独安装登录;CodeFlicker / Trae / Gemini 也依赖本机 CLI 登录状态。

### 我们接受这些代价是因为

当前目标是让虚拟公司成员池和 IM 入口真实扩展。相比在核心协议中新增 per-risk adapter execution mode,先复用现有审批/审计/中断闭环更小、更符合当前阶段。

## 不再做的事

- 不新增核心里的 `if cursor` / `if trae` / `if gemini` 路由分支。
- 不为“前台、仓库管理员、财务、客户经理”等短期无明确 AI 公司产出的角色扩充模板。
- 不先接 QQ/微信这类审核、白名单、合规摩擦更高的 Channel。
- 不在本轮引入完整 Web dashboard 或独立 Channel server 进程。

## 相关链接

- ADR-0002
- ADR-0007
- ADR-0013
- ADR-0017
- ROUNDS Round 67
- `src/aico/adapter/cursor.py`
- `src/aico/adapter/codeflicker.py`
- `src/aico/adapter/trae.py`
- `src/aico/adapter/gemini.py`
- `src/aico/channel/feishu.py`
