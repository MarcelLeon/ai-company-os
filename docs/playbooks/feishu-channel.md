# Playbook: Feishu Channel Smoke Test

## 适用场景

当 `FeishuChannel`、`aico-feishu-webhook`、事件解析、发送消息 payload 或飞书部署配置变化时,用本 Playbook 验证最小文本收发链路。

## 前置条件

- 已在飞书开放平台创建企业自建应用。
- 已开通机器人能力,并记录 App ID、App Secret。
- 已在事件订阅中配置接收消息事件 `im.message.receive_v1`。
- 已配置 Verification Token。
- 有一个公网 HTTPS callback URL 能转发到 `aico-feishu-webhook`。

## 步骤

1. 本地跑 mock 单测和 webhook 单测。

   ```bash
   env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python /opt/homebrew/bin/python3.11 pytest tests/unit/test_feishu_channel.py tests/unit/test_feishu_webhook.py
   ```

2. 启动 webhook runtime。

   ```bash
   export AICO_CHANNEL=feishu
   export AICO_FEISHU_APP_ID="你的 Feishu App ID"
   export AICO_FEISHU_APP_SECRET="你的 Feishu App Secret"
   export AICO_FEISHU_VERIFICATION_TOKEN="你的 Verification Token"
   export AICO_FEISHU_EVENT_PATH="/feishu/events"
   export AICO_FEISHU_WEBHOOK_HOST="0.0.0.0"
   export AICO_FEISHU_WEBHOOK_PORT=8080
   export AICO_CLAUDE_WORKING_DIRECTORY="/Users/wangzq/VsCodeProjects/ai-company-os"
   export AICO_PROJECT_CONFIG_PATH="config/projects.example.json"
   export AICO_MEMORY_PATH="/tmp/aico-memory.jsonl"
   env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python /opt/homebrew/bin/python3.11 aico-feishu-webhook
   ```

3. 验证本地健康检查。

   ```bash
   curl -fsS http://127.0.0.1:8080/healthz
   ```

   预期返回 `{"status":"ok"}`。

4. 配置公网 HTTPS callback。

   - 把公网 `https://<public-host>/feishu/events` 转发到 webhook runtime。
   - 在飞书开放平台事件订阅中填写该 URL。
   - 飞书发送 `type=url_verification` 时,webhook 应返回 `{"challenge":"<原 challenge>"}`。
   - 如果 Verification Token 不匹配,webhook 应返回错误而不是静默接受。

5. 验证文本入站解析和 AICO 回复。

   - 飞书事件类型应为 `im.message.receive_v1`。
   - `event.message.message_type` 应为 `text`。
   - `event.message.content` 中的 JSON `text` 会映射到 `IncomingMessage.content.text`。
   - `event.message.chat_id` 会映射到 `ChannelTarget.target_id`。
   - 向机器人所在聊天发送 `/help` 或 `/status`,应收到 AICO 文本回复。

6. 验证事件幂等。

   - 同一个 v2 事件的 `header.event_id` 重复投递时,只应触发一次 AICO 任务。
   - 旧 v1 事件如果带 `uuid`,同一个 `uuid` 重复投递时也只应触发一次。
   - 本地单测 `test_feishu_deduplicates_retried_v2_events_by_event_id` 和 `test_feishu_deduplicates_legacy_v1_events_by_uuid` 覆盖这个契约。

7. 验证文本发送。

   - `FeishuChannel.send_message()` 会先用 App ID / App Secret 获取 `tenant_access_token`。
   - 发送接口使用 `/open-apis/im/v1/messages?receive_id_type=chat_id`。
   - `MessageContent.actions` 暂时降级为文本提示,不在第一切片做飞书 interactive card。

## 验证

- URL verification 返回 challenge。
- 文本消息能转换为 `IncomingMessage` 并进入现有 Orchestrator handler。
- `send_message()` 能用 chat id 发出文本。
- `edit_message()` 和 `delete_message()` 调用 Feishu message API,失败时抛出 `FeishuAPIError`。
- `/help`、`/status` 这类 Telegram 已有基础命令在飞书文本入口也可用。
- 飞书重试同一个 event id / uuid 时不会重复创建任务。

## 失败回滚

- 不启用飞书部署层即可回到 Telegram 单入口。
- 如果飞书事件字段变化,优先只修 `src/aico/channel/feishu.py`,不要改 `IMChannel` 协议。
- 如果飞书 action/card 映射复杂度超出第一切片,继续保持文本降级,核心不感知差异。

## 相关

- ADR-0018
- `src/aico/channel/feishu.py`
- `src/aico/app/feishu_webhook.py`
- `tests/unit/test_feishu_channel.py`
- `tests/unit/test_feishu_webhook.py`
- Feishu send message: https://open.feishu.cn/document/server-docs/im-v1/message/create
- Feishu event subscription: https://open.feishu.cn/document/server-docs/event-subscription-guide/event-subscription-configure-/request-url-configuration-case
