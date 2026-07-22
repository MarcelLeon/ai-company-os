# ADR-0084: Runtime Webhook Authority Isolation

**状态**:Accepted
**日期**:2026-07-22
**决策者**:Codex
**相关 Round**:Round 246

## 背景

AICO有两条absence webhook：runtime alert发送`incident_opened/resolved`，dead-man liveness发送pulse v2。strict receiver为两种
协议使用不同route，正确拒绝错误event。旧service/Phase1只分别验证HTTPS、token形状和TTL；同一个URL甚至同一个bearer可以同时
通过strict admission，造成“两个publisher都配置了”但其中一路必然被协议/authority拒绝的false-green。

## 候选方案

- 只保留文档警告：否决；P-064已写明不能共用，但机器准入仍接受错误配置。
- 允许同URL，由receiver按event type分流：否决；当前strict routes有不同schema与authority，放宽会扩大攻击面并破坏独立演化。
- 要求不同origin：否决；两个协议可以由同一外部receiver的不同strict path承载，origin独立不是本合同能证明的故障域。
- 要求exact URL不同，双方配置token时token也不同：采用。

## 决策

1. 在共享absence policy中增加secret-free cross-field validator。alert/liveness URL去除首尾空白后不得完全相等。
2. 两侧bearer均非空时不得完全相等；单侧无token仍由各自transport policy决定，本决策不隐式强制认证模式。
3. `aico-service doctor/install`新增`runtime endpoint isolation`检查；冲突为FAIL，strict aggregate同时列出固定合同名。
4. `Phase1Settings`复用同一helper，每次Telegram/Feishu启动都fail closed；错误不包含URL、token或response。
5. 不声称不同path/token等于第二故障域、provider独立或真实ACK；这些继续由external dogfood证明。

## 后果

- 两种不兼容协议不能再因“都是HTTPS”而共享endpoint/credential并通过机器准入。
- 同一receiver origin仍可用两个strict route，但credential rotation必须保持authority separation。
- 现有未同时启用两条webhook的开发配置不受影响。

## 相关链接

- ROUNDS Round 246
- PITFALLS P-102
- Goal Brief `docs/superpowers/specs/2026-07-22-runtime-webhook-authority-isolation.md`
- P-064
- 相关代码:`src/aico/app/absence_admission.py`,`src/aico/app/service_cli.py`,`src/aico/app/phase1.py`
