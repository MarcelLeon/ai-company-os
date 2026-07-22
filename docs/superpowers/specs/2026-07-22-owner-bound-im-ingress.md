# Goal Brief: Owner-Bound IM Ingress

## Goal

让 Telegram/Feishu 控制面只接受显式 owner 从显式可信聊天发来的消息，阻止陌生 sender 读取公司状态、消耗 provider
或自行提交并批准风险任务。

## In scope

- channel + owner sender + trusted target 三重精确绑定。
- 在命令解析、memory/task/audit mutation和provider dispatch之前fail closed。
- scheduled morning target与trusted target交叉校验。
- bounded identity-safe denial log和显式foreground discovery bootstrap。
- `aico-service doctor/install`配置门禁。

## Out of scope

- IM平台账号被接管后的密码学二次签名、passkey或多人quorum。
- IM平台自身webhook/polling transport authentication替代。
- 细粒度owner角色RBAC或跨Channel统一身份映射。

## Acceptance

1. 只有configured channel、owner sender和trusted target同时匹配时，消息才进入Orchestrator业务路径。
2. 未授权普通消息和`/approve`都不发送回复、不创建task、不修改approval/audit/memory、不调用Adapter。
3. owner在非trusted target发消息同样被拒绝，防止结果回到公共群或错误会话。
4. approval reviewer必须是owner sender；enabled morning target必须是trusted target。
5. 默认denial log不含sender/target/content，且只在累计1/2/4/8...次记录，避免日志放大。
6. discovery仅在owner显式开启时输出本地sender/target；业务仍拒绝，doctor/install必须FAIL直到关闭。
7. 最多接受16个sender和16个target，每个ID最多256字符；placeholder、unknown和控制字符fail closed。

## Stop conditions

- 不把Bot Token或“没人知道Bot地址”当授权边界。
- 不只校验sender而忽略回复target。
- 不为bootstrap开放一个可执行的unauthenticated `/whoami`业务命令。
- 不把IM sender ID描述为密码学owner签名或账号接管防护。
