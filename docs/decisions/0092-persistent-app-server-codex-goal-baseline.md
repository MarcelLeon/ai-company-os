# ADR-0092: Persistent App-Server Codex Goal Baseline

**状态**:Accepted
**日期**:2026-07-23
**决策者**:Wang / Codex(协作)
**相关 Round**:Round 259

---

## 背景与问题

Boss-absent benchmark要求比较AICO与“当前Codex Goal”，而不是普通一次性Codex任务。本机`codex-cli 0.144.5`的`codex exec`
没有Goal子命令；若用它作为baseline，只能测一次turn，无法覆盖Goal的持久状态、自动continuation、token/time usage与状态转换。

本机app-server experimental protocol公开`thread/goal/set|get|clear`以及`thread/start`、`turn/start`。live no-model探测进一步证明：
Goal拒绝ephemeral thread，必须绑定persistent thread。直接复用桌面Codex的`CODEX_HOME`又可能与正在运行的桌面state runtime竞争，
出现SQLite初始化失败，不能作为稳定benchmark入口。

## 候选方案

### 方案 A — 用`codex exec`模拟Goal

- 优点：命令简单，已有JSONL usage解析。
- 缺点：没有Goal状态与continuation，不是被比较对象，结论无效。

### 方案 B — 在当前Codex桌面home直接启动独立app-server

- 优点：复用现有登录和state。
- 缺点：与桌面进程共享SQLite/runtime，live probe已出现间歇初始化失败；探测线程也可能污染用户日常任务。

### 方案 C — 每个benchmark run使用隔离Codex home，通过persistent app-server线程测真实Goal

- 优点：准确覆盖Goal API，state/线程/cleanup可按run隔离；不会与日常Codex状态库竞争。
- 缺点：正式模型run仍需owner-authorized credential injection；persistent thread创建与cleanup存在外部原子性边界。

## 决策

选择 **方案 C**：

1. Codex Goal baseline必须使用app-server`thread/start`创建persistent thread，再调用`thread/goal/set|get`；禁止用`codex exec`结果
   代替Goal baseline。
2. admission probe从frozen contract读取exact CLI version、model和token budget；线程固定`approvalPolicy=never`、read-only sandbox、
   network disabled。probe不调用`turn/start`，因此必须看到`tokensUsed=0`、`timeUsedSeconds=0`。
3. 每次probe/run使用owner-only隔离`CODEX_HOME`，不读取或修改桌面Codex state DB。local admission已证明现有owner-only
   `auth.json`可用symlink挂载并由`codex login status`识别，不复制secret；正式模型turn仍需owner预算授权和runner内全生命周期清理。
4. Goal不支持ephemeral thread。probe成功后必须按`goal/clear`→`thread/delete`清理，并删除隔离home。
5. thread创建后立即落owner-only cleanup intent；连接失败时保留intent与isolated home，下次probe先重连删除旧thread，再开始新探测。
   external thread create与local intent write无法原子提交，这一极小crash window继续作为残余风险公开。
6. 正式runner必须同时采集Goal`tokensUsed/timeUsedSeconds/status`与turn/provider usage；任一缺失或口径不一致按missing/budget loss，
   不允许只信被测Agent自报。

## 当前证据

- 生成的0.144.5 app-server schema包含`thread/goal/set|get|clear`、`thread/start`和`turn/start`。
- ephemeral live probe明确返回“不支持goals”。
- persistent no-model live probe完成start/set/get/clear/delete，读到50,000 budget、0 tokens、0 seconds。
- 共享home出现过SQLite state runtime初始化失败；隔离home live CLI probe稳定通过且正常删除home/cleanup intent。
- isolated auth symlink的local status为ChatGPT logged in；未调用模型，临时helper和home已删除。

## 安全与口径边界

- no-model protocol receipt只证明当前CLI的Goal控制面可用，不证明continuation、模型质量或正式benchmark结果。
- `thread/delete`成功不证明app-server外部所有telemetry消失；receipt不保存thread id、prompt、home path或用户身份。
- turn supervision已由offline contract覆盖；ADR-0093进一步确认app-server不拥有automatic continuation，正式run仍缺native Codex host
  adapter/build receipt、credential注入和scenario injection，因此仍禁止“强于Codex Goal”声明。

## 相关链接

- `src/aico/app/boss_absent_codex_goal_probe.py`
- `src/aico/app/boss_absent_benchmark_cli.py`
- `docs/benchmarks/boss-absent-vs-codex-goal.md`
- ADR-0091
- ADR-0093
