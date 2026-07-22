# ADR-0078: Alert-Delivery-Aware Dead-Man Renewal

**状态**:Superseded by ADR-0079(receiver/evidence/recovery schema only)
**日期**:2026-07-22
**决策者**:Codex
**相关 Round**:Round 240
**Supersedes**:ADR-0045/0046的pulse续租与wire schema、ADR-0048的evidence schema、ADR-0068的receiver schema验证部分；独立失效域、显式arm/disarm和独立恢复原则继续有效

## 背景

Round 239能在required component稳定FAILED后写入secondary alert outbox；但若该alert sink本身持续失败，runtime仍会正常发送dead-man pulse。旧receiver只判断pulse是否到达，因此会持续续租并保持绿色，缺席老板既收不到primary alert，也收不到dead-man告警。

## 候选方案

- 让AICO本机为alert delivery failure再发一条同通道告警：否决；故障出口不能自证自身失败。
- alert delivery failure立即停止所有pulse：否决；receiver无法区分runtime死亡与告警出口失败，也失去最新boot/sequence排序证据。
- 新增第三个observer：暂不采用；增加部署与credential成本，仍需定义第二通道健康如何传递。
- 在既有secret-free pulse携带bounded alert-delivery状态，由独立receiver决定是否续租：采用。

## 决策

1. pulse schema升级v2，增加`alert_delivery_status=disabled|healthy|pending|failed`；不携带事件、endpoint、target、异常或业务正文。
2. `disabled/healthy` pulse既排序又续租；`pending/failed` pulse只更新boot/sequence与最近pulse接收时间，不更新最后成功续租时间。
3. 续租窗口到期时，若最近已排序pulse为`pending/failed`，receiver创建reason=`alert_delivery_unhealthy`的outage；否则为`pulse_expired`。
4. 后续`disabled/healthy`新pulse原子写入同outage的resolved，再恢复续租。duplicate/older pulse不能延期。
5. pending pulse在成功ACK前保持exact payload；状态变化最迟在该pulse ACK后的下一interval传播，接受这一有界延迟以保持幂等。
6. receiver与evidence schema升级v2；v1 DB迁移将历史续租复制为最近pulse、状态置`disabled`，历史open outage标为`pulse_expired`。recovery verifier要求新列、合法枚举与open/resolved reason一致。

## 后果

- secondary alert出口持续失败不再被fresh process pulse掩盖，可复用receiver独立notification outbox通知老板。
- receiver status能区分runtime/pulse失联与alert-delivery unhealthy，但仍不证明老板已读或primary业务恢复。
- 老部署必须先升级receiver到schema v2，再启用v2 publisher；协议不提供v1/v2双写或静默降级。
- alert sink未配置时`disabled`仍可续租，因为此时没有“已承诺但失败”的secondary delivery。

## 不再做的事

- 不用同一个失败alert sink报告自己的delivery failure。
- 不把pulse arrival直接等同于absence notification path健康。
- 不让alert-delivery状态授权restart、restore、provider replay或grant消费。
- 不把本机测试、receiver local ACK或valid evidence bundle写成真实第二故障域/老板已读。
