# ADR-0081: Durable Silent Notification Route Probes

**状态**:Accepted
**日期**:2026-07-22
**决策者**:Codex
**相关 Round**:Round 243
**Supersedes**:ADR-0080的receiver/evidence/recovery schema v4与“仅event-driven”边界；其route-health edge规则继续有效

## 背景

ADR-0080只能从真实outage event观察通知route。长期没有事故时，坏fallback可能保持unknown或旧healthy，直到下一次真正需要它。
普通webhook没有silent语义，直接定时发送事故消息会骚扰老板；探测另一URL、只做HEAD或使用另一credential又不能证明真实POST链路。

## 候选方案

- 定时HEAD通知URL：否决；不验证POST payload、credential、幂等处理或bridge路由。
- 使用独立probe URL/token：否决；只能证明另一条链路，不能证明事故通知credential仍有效。
- 定时发送普通outage event：否决；会制造老板噪声，并可能污染真实incident自动化。
- provider-native status API：保留为provider插件的未来补充；generic receiver不能从它证明owner实际通知bridge。
- 显式opt-in、复用真实route的strict silent event：采用。

## 决策

1. 只有配置字面量`silent-route-probe-v1`才启用；默认`disabled`。启用要求双route，且operator必须先确认两个downstream bridge会
   识别`notification_route_probe`、按`Idempotency-Key`幂等ACK并禁止展示给老板或触发事故工作流。
2. probe复用同一HTTPS URL、bearer credential、POST transport与schema envelope，不创建旁路authority。payload只含schema、stable
   `rp-*` event id、contract和scheduled time，不含monitor、业务正文、endpoint或secret。
3. 当前probe intent先写入schema v5 singleton，再发送；send-before-record崩溃后重放exact payload/key。每轮完成后从attempt time计算
   下一窗口，不追赶遗漏窗口，也不无限增长history。
4. 每个route独立记录last probe、ACK与连续probe failure。首次失败为suspect并让delivery显示pending；连续失败达到owner配置阈值后
   才转degraded并复用ADR-0080的durable edge，避免瞬时网络抖动刷屏。ACK重置计数，degraded后ACK生成recovered edge。
5. probe无main quorum结算语义：一次attempt无论结果都形成bounded observation；全断时edge保留，恢复route后先投递edge，再由后续probe
   证明route恢复。meta-alert仍不反向更新route健康。
6. probe contract、cadence、failure threshold、max age、pending exact event与last ACK mask持久化。pending probe或health edge期间配置变化
   fail closed；disable→缩route、扩route→enable采用安全启动顺序。
7. receiver/evidence/recovery升级schema v5。v4迁移默认disabled并重建canonical route/edge表；offline verifier校验exact DDL、probe
   checkpoint、ACK mask、source-tagged edge和pending policy，不把local ACK写成owner read。

## 后果

- 在没有真实outage的月份里，双route也能低频验证真实POST/credential/bridge transport，confirmed failure会主动通知缺席老板。
- generic webhook bridge必须实现silent contract；若不能保证不展示，保持disabled，继续诚实地只声称event-driven health。
- local probe ACK仍不证明provider账号/网络/物理故障域独立、终端展示或老板已读；真实双provider dogfood仍是B-012外部边界。
- schema v4部署升级前必须备份receiver；配置probe前必须先升级两端bridge，再显式opt-in。

## 不再做的事

- 不用HEAD、DNS、TCP connect或旁路credential冒充通知链路健康。
- 不把probe包装成outage，也不让它触发老板可见消息、repair、restart、restore或provider replay。
- 不因一次瞬时失败立即开降级边沿，不追赶历史窗口制造probe storm。
