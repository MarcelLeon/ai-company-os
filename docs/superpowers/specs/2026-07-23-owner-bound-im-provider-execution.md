# Goal Brief: Owner-bound IM与provider execution evidence

## Objective

关闭formal AICO benchmark中两个可伪造边界：手写owner grant/takeover ACK，以及只靠`agent_id`标签声明跨Agent协作。

## Acceptance

- IM发送前有durable intent；平台ACK落盘，ACK歧义重启不盲重发。
- 只有exact owner、target、thread、request token和有效期内的inbound action可产生decision。
- approval grant和takeover ACK逐SHA绑定IM decision；raw身份与token不进入score artifact。
- contract冻结project assignment；role receipt绑定exact appointment和provider-issued execution fingerprint。
- 不同Agent名但相同provider execution不能获得协作checkpoint。
- no-network fake Channel、restart ambiguity、wrong owner、invalid action、assignment drift和shared execution均有单测。

## Non-goals

- 本轮不实际发送Telegram、不调用模型、不生成benchmark胜负。
- 不为Telegram `sendMessage`虚构平台幂等能力。
- 不把AICO内存session ID当作provider-issued execution ID。

## Verification

- `collect-aico-approval-im`与`collect-aico-takeover-im`可安装解析，token只从环境读取。
- Codex JSON `thread.started`产生execution fingerprint；缺失时formal role拒绝。
- targeted、full root、SME、Ruff、mypy、format、class/method尺寸和`git diff --check`全部通过。
