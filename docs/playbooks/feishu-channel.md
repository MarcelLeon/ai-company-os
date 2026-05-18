# Playbook: Feishu Channel Smoke Test

## 适用场景

当 `FeishuChannel` 新增、改事件解析、改发送消息 payload 或准备把飞书接入部署层时,用本 Playbook 验证最小文本收发链路。

## 前置条件

- 已在飞书开放平台创建企业自建应用。
- 已开通机器人能力,并记录 App ID、App Secret。
- 已在事件订阅中配置接收消息事件 `im.message.receive_v1`。
- 已配置 Verification Token。
- 本轮代码只提供 Channel 插件和 payload handler;真实公网 callback server 需要后续部署层接入 FastAPI route 后再做端到端验收。

## 步骤

1. 本地跑 mock 单测。

   ```bash
   env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python /opt/homebrew/bin/python3.11 pytest tests/unit/test_feishu_channel.py
   ```

2. 在飞书开放平台完成 URL verification。

   - 事件回调 payload 中 `type=url_verification` 时,部署层应调用 `FeishuChannel.handle_event(payload)`。
   - 返回值应是 `{"challenge": "<原 challenge>"}`。
   - 如果 token 不匹配,应返回错误而不是静默接受。

3. 验证文本入站解析。

   - 飞书事件类型应为 `im.message.receive_v1`。
   - `event.message.message_type` 应为 `text`。
   - `event.message.content` 中的 JSON `text` 会映射到 `IncomingMessage.content.text`。
   - `event.message.chat_id` 会映射到 `ChannelTarget.target_id`。

4. 验证文本发送。

   - `FeishuChannel.send_message()` 会先用 App ID / App Secret 获取 `tenant_access_token`。
   - 发送接口使用 `/open-apis/im/v1/messages?receive_id_type=chat_id`。
   - `MessageContent.actions` 暂时降级为文本提示,不在第一切片做飞书 interactive card。

## 验证

- URL verification 返回 challenge。
- 文本消息能转换为 `IncomingMessage` 并进入现有 Orchestrator handler。
- `send_message()` 能用 chat id 发出文本。
- `edit_message()` 和 `delete_message()` 调用 Feishu message API,失败时抛出 `FeishuAPIError`。

## 失败回滚

- 不启用飞书部署层即可回到 Telegram 单入口。
- 如果飞书事件字段变化,优先只修 `src/aico/channel/feishu.py`,不要改 `IMChannel` 协议。
- 如果飞书 action/card 映射复杂度超出第一切片,继续保持文本降级,核心不感知差异。

## 相关

- ADR-0018
- `src/aico/channel/feishu.py`
- `tests/unit/test_feishu_channel.py`
- Feishu send message: https://open.feishu.cn/document/server-docs/im-v1/message/create
- Feishu event subscription: https://open.feishu.cn/document/server-docs/event-subscription-guide/event-subscription-configure-/request-url-configuration-case
