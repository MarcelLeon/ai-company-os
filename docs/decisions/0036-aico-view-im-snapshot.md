# ADR-0036: aico-view IM-delivered HTML snapshot

**状态**:Accepted
**日期**:2026-06-02
**决策者**:Wang / Codex
**相关 Round**:Round 137
**相关文档**:ADR-0033;ADR-0035;`docs/human/aico-view-deploy.md`

---

## 背景与问题

ADR-0033/0035 把 `aico-view` 设计为独立 read-only FastAPI 进程,并为隧道访问增加
`AICO_VIEW_TOKEN`。这对本机排障和可选手机隧道是成立的,但老板在 Telegram 里进入
项目后,默认不应该被引导去访问 Mac 本机服务或公网 tunnel。

人类明确指出:不要让 Telegram/手机访问本机;更自然的老板路径是把只读 HTML 文件直接
发到 Telegram。

## 决策

新增 **IM-delivered HTML snapshot** 模式:

- `AICO_VIEW_ENABLED=true` 只启用 IM 里的 `/view [project]` 命令。
- `/view` 生成一份自包含 HTML 文件,内联 CSS,不包含 `127.0.0.1` / localhost URL,
  不要求启动 `aico-view` HTTP 进程。
- Telegram Channel 通过 Bot API `sendDocument` 发送 `.html` 文件。
- 不支持附件的 Channel 暂时降级为写本地 snapshot 文件并回 IM 提示路径。
- 既有 `uv run aico-view` FastAPI 服务保留,但它是显式本机排障/可选隧道模式,
  不由 `AICO_VIEW_ENABLED` 自动启动。

## 安全边界

- ✅ 避免入站端口、ngrok、Cloudflare tunnel 成为默认路径。
- ✅ HTML snapshot 是只读文件;所有写操作继续回 IM。
- ✅ snapshot 不包含外部 CSS 或本机服务链接。
- ⚠️ snapshot 内容会进入 Telegram 聊天记录/云端存储。它可能包含 memory、experience
  和 audit 摘要,因此只能发到可信私聊或可信小群。

## 该决策不做的事

- ❌ 不把 `aico-phase1` 变成 Web server supervisor。
- ❌ 不自动在 `/project` 后发送 snapshot,避免在群里刷屏或误发敏感 memory。
- ❌ 不废弃 FastAPI `aico-view`;它仍用于本机调试和显式隧道 dogfood。
- ❌ 不给 snapshot 加写按钮。按钮最多是回 Telegram 的命令 deep link 或复制提示。

## 结果

- `src/aico/view/snapshot.py`:生成自包含 Boss Brief / Timeline / Trace / Memory HTML。
- `src/aico/view/commands.py`:新增 `/view [project]` handler。
- `src/aico/channel/base.py`:新增可选 `DocumentChannel` 协议。
- `src/aico/channel/telegram.py`:新增 `send_document()` → Telegram `sendDocument`。
- `src/aico/app/phase1.py`:新增 `AICO_VIEW_ENABLED` / `AICO_VIEW_OUTPUT_DIR` 配置。

## 后续

- 根据真实 dogfood 决定是否增加 `AICO_VIEW_AUTO_SEND_ON_PROJECT=true`。
- 如果 Feishu 要支持同等体验,新增 Feishu 文件上传能力,不要在 core 写平台分支。
