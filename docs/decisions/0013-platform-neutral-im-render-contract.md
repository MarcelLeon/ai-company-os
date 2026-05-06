# ADR-0013: Platform-Neutral IM Render Contract

**状态**:Accepted
**日期**:2026-05-05
**决策者**:Wang / Codex(协作)
**相关 Round**:Round 48

---

## 背景与问题

Project Team / Appointment 命令已经开始承担“项目办公室”的主界面职责。真实 Telegram 验收后,人类指出纯文本和 Markdown 风格文案不够适合长期使用;后续还需要更清晰的审批、确认、项目摘要和按钮式交互。

但北极星要求 IM 通道可插拔。核心层如果直接输出 Telegram HTML、MarkdownV2 或 Telegram button payload,未来接入 Feishu、Kim 或其他 IM 时会让平台细节污染 `Orchestrator`、command message 和项目消息渲染。

## 候选方案

### 方案 A — 核心直接输出 Telegram HTML / Markdown
- 优点:最快让 Telegram 看起来更好。
- 缺点:核心消息会绑定 Telegram parse mode;其他 IM 只能解析 Telegram 方言。
- 复杂度:低。

### 方案 B — `MessageContent` 增加平台无关 render hints
- 优点:核心只表达文本 span 和动作,Channel 自己决定如何渲染;Telegram 可以映射到 HTML 和 inline keyboard。
- 缺点:第一切片只能覆盖基础样式和按钮,复杂 layout 还需要后续扩展。
- 复杂度:中。

### 方案 C — 引入完整 block UI schema
- 优点:可以表达 section、fields、buttons、menus 等复杂界面。
- 缺点:当前只有 Telegram 一个强需求样本,容易过早抽象;会扩大 Channel 和消息生成代码。
- 复杂度:高。

## 决策

选择 **方案 B:`MessageContent` 增加平台无关 render hints**。

第一切片只引入:

```text
MessageTextSpan(offset, length, style)
MessageAction(label, value)
```

核心消息仍保留 `text` 作为唯一必填正文。没有 spans/actions 时,所有 Channel 继续按纯文本发送。Telegram Channel 负责把 spans 映射为 HTML `parse_mode`,把 actions 映射为 `inline_keyboard`。

## 决策理由

- 符合北极星第二句“协议优先、能力可插拔”:核心表达语义,Channel 负责平台适配。
- 能满足当前 Telegram 富文本和按钮式文案的第一步需求,但不会把 Telegram parse mode 写进项目消息函数。
- 保留纯文本 fallback,不会破坏已有测试、长文本分片和未来非富文本 Channel。
- 遵守 Rule of Three:暂不引入完整 block UI schema,等更多 IM 或更多复杂布局需求出现后再扩展。

## 后果

### 正面后果

- Telegram 可以逐步使用 HTML 和 inline keyboard 改善项目办公室体验。
- Feishu / Kim 可以独立把同一份 `MessageContent` 映射到各自的富文本或按钮协议。
- 现有 `MessageContent(text="...")` 调用保持兼容。

### 负面后果

- spans 基于 offset / length,消息生成方如果要加样式需要小心文本位置。
- 当前只支持基础文本样式和一行动作按钮,复杂卡片、表格和多区块布局还没表达。
- Telegram callback query 的入站处理尚未实现,actions 目前只是出口契约。

### 我们接受这些代价是因为

当前最重要的是避免平台细节进入核心,同时给 Telegram 体验改进开一条小而可测试的路。完整 UI schema 可以在更多真实用例出现后再抽象。

## 不再做的事

- 不在 `project_messages.py`、`command_messages.py` 或 `Orchestrator` 中直接写 Telegram HTML / MarkdownV2。
- 不把 Telegram `reply_markup` 作为核心模型字段。
- 不在当前阶段引入完整 block/card UI schema。

## 相关链接

- ROUNDS Round 48
- `src/aico/core/models.py`
- `src/aico/channel/telegram.py`
