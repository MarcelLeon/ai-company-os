# ADR-0087: Expiring Runtime Commissioning Receipt

**状态**:Accepted
**日期**:2026-07-22
**决策者**:Codex
**相关 Round**:Round 249

## 背景

Round 247能发现运行中`.env`代际漂移，Round 248能严格验证当前dead-man bundle，但两份事实彼此独立。operator仍可能用A配置
生成的外部证据启动B配置，或在artifact过期后让已运行进程继续保持全绿；一个可选的离线报告也无法约束LaunchAgent restart。

## 备选方案

1. runtime每次启动联网探测receiver/provider：扩大启动副作用，credential和网络故障会进入构造路径。
2. 把`.env`内容或内容hash写进receipt：会持久化secret-derived material，且receipt SHA写回`.env`会形成循环绑定。
3. owner先在最终`.env`配置外部artifact/receipt路径，再离线生成owner-only receipt；receipt绑定reviewed Git config evidence、
   `.env` stat代际fingerprint、strict dead-man exact bytes和最早底层expiry。strict install/startup验证，heartbeat持续复核。

## 决策

采用方案3。`aico-commission create|verify`只接受checkout外、owner-only的evidence与receipt；创建要求clean checkout和owner supplied full
revision。receipt不记录dotenv path、metadata、content或content hash，expiry取bundle最大年龄与silent probe TTL的较早值。

`AICO_ABSENCE_ADMISSION_MODE=strict`新增`runtime commissioning`合同：doctor/install和Telegram/Feishu startup必须通过当前绑定，
否则在launchctl/Channel/state前fail closed。运行中每轮health把它作为required `configuration:commissioning-receipt`；过期、receipt/
evidence字节、runtime identity、Git/config或dotenv代际漂移会进入既有confirmed alert，但不触发reload/restart/provider replay。

receipt SHA可由owner另行归档复核，但runtime不把它写回同一`.env`，避免循环；该local artifact不是数字签名，也不证明receiver origin、
provider/platform ACK、fault action或human read，`business_absence_ready`固定为false。

## 相关链接

- ROUNDS Round 249
- PITFALLS P-105
- Goal Brief `docs/superpowers/specs/2026-07-22-expiring-runtime-commissioning-receipt.md`
- ADR-0085
- ADR-0086
