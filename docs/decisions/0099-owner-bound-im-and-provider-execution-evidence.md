# ADR-0099: Owner-bound IM decision与provider execution证据

- **状态**: Accepted
- **日期**: 2026-07-23
- **范围**: Boss-Absent benchmark formal AICO runtime

## 背景

ADR-0097/0098已经让external observer读取真实文件代际，并让approval runner在exact grant前停止；但grant仍可手写，
`AicoTakeoverAckReceipt`也只验证本地JSON结构。另一方面，role target中的`agent_id`来自CLI配置，一个provider execution
可以换两个名字冒充跨Agent协作。这两类证据都不足以支撑正式benchmark。

Telegram Bot API的`sendMessage`没有调用方幂等键。若平台已接收消息、进程却在ACK落盘前崩溃，重启盲目重发会增加owner
操作和重复审批风险。

## 决策

1. formal IM exchange由one-shot collector独占Channel polling。collector在外发前保存0600 immutable intent；正常路径保存
   Telegram `sendMessage` ACK。intent存在但ACK缺失时禁止重发，只允许绑定owner、target、request token和有效期的inbound
   callback完成delivery reconciliation。
2. inbound相关操作写入0600 hash-chain ledger；错误owner和无关消息忽略，匹配request但无效的操作计入接手成本。terminal
   decision只能闭合一次，并绑定request、delivery ACK、inbound ACK、owner identity fingerprint、actions与elapsed seconds。
3. approval grant必须由`approved` IM decision生成并携带其exact receipt SHA；mutation executor和observer都复核该receipt。
   takeover receipt同样必须逐字段绑定`acknowledged` IM decision与final checkpoint。
4. benchmark contract冻结`project.json`及project ID。runtime按role解析exact appointment，Task metadata携带project/seat/role。
   Codex Adapter从`thread.started`采集provider-issued execution ID，role receipt只保存其SHA。协作任务要求不同Agent且不同
   provider execution；两者任一复用都fail closed。

## 结果

- Round 267已在owner显式授权下完成真实Telegram approval与takeover：collector独占bot polling，Bot API返回platform ACK，
  当前owner在Telegram Web各执行1次操作，exact inbound callback闭合decision。所有exchange、grant与takeover receipt均为0600。
- 本次使用显式synthetic/no-model state，只证明真实transport、owner-bound decision与receipt链；不证明provider执行、
  approval mutation或formal benchmark成绩。
- Telegram缺少发送幂等键时，ambiguous delivery可能等待到期而不是冒险重发；这是安全优先的显式失败。
- raw bot token、chat/sender ID和provider thread ID不进入score artifact；只有owner-only exchange state或不可逆fingerprint。
- formal run新增project config、IM exchange目录和decision receipt依赖，但协作率与接手成本获得可独立复核的事实来源。
