# ADR-0051: Owner-Bound Read-Only Standing Autonomy

**状态**:Accepted
**日期**:2026-07-21
**决策者**:Codex / Round 213

## 背景

standing charter 已能在项目空闲时生成持久化 proposal，但老板缺席时仍必须手工 accept。直接按 chat target、
charter 文案或 `read_only` prompt 自动接受并不成立：它们既不能证明 owner 授权，也不能约束 broad-permission
Adapter，更不能限制总运行次数与单次时长。

## 决策

1. 自执行是显式 opt-in：只读取项目仓库外、当前用户所有、`0600`、非 symlink 的 versioned grant file。
2. grant 精确绑定 owner IM identity、channel/target/thread、project/charter、aware expiry、`max_runs`、
   `max_duration_seconds` 与唯一 `grant_id`；占位符、重复绑定和晨报目标不匹配在启动时失败。
3. 只有 scheduler 的 morning handoff 可消费 grant；交互 `/inbox`、`/morning`、`/proposals` 仍只生成/展示候选。
4. 消费记录在 dispatch 前持久化为 `PREAUTHORIZED + grant_id`，因此 crash/restart、失败与 timeout 都不会恢复预算。
5. TaskBus 只接受 read-only risk、collaboration disabled、无 provider resume，且 Adapter 自身实现 hard boundary 的
   preauthorized task。当前只有 executable basename 为 `codex` 的 Codex Adapter 支持。
6. 预授权 Codex 忽略可配置参数，固定使用 approval never、read-only sandbox、ignore user config/rules、ephemeral、
   strict config 和显式 network disabled。OpenAI 对 Codex sandbox 的 write/network policy 定义见
   [Running Codex safely](https://openai.com/index/running-codex-safely/)。
7. AICO 用 wall-clock timeout 中断 TaskBus 并取消本地 waiter；输出仍只回精确授权 target。

## 否决方案

- **target/chat id 等同 owner**：destination 不是 requester authority。
- **charter 或 prompt 写 `read_only`**：意图文本不是操作系统/工具权限。
- **复用 Claude bypass/Cursor 等 broad Adapter**：核心层无法从外部证明其工具调用只读。
- **把 grant 放项目仓库**：有写权限的工作 Agent 可把自身工作范围改成授权。
- **允许 collaboration 或 provider resume**：子任务和旧可写 session 会逃逸本次边界。
- **dispatch 成功后才扣预算**：crash/accept-before-record 会重复执行。
- **无限 grant 或自动续期**：无法给缺席期建立可审计损失上限。

## 后果

### 正面

- owner 可预先批准一个有界、只读、不可扩散的 standing inspection，scheduler 无需下一次 IM tap。
- grant、proposal、task 与 budget 可在 SQLite 历史中关联，重启不重置 run count。
- 配置错误、expired/exhausted、风险升级或 Adapter 能力漂移均 fail closed，候选仍可人工处理。

### 代价与剩余风险

- 当前只支持 Codex read-only inspection；任何写入、网络、发布、付款、客户沟通仍需人工审批链。
- `0600 + current uid` 是本机进程信任边界，不是 owner 的密码学签名；同一 OS 用户下的恶意进程仍可能改写
  grant。更强商用威胁模型需要 detached signature、Keychain/managed policy 或独立 OS identity。
- 本轮没有创建真实 grant、安装 LaunchAgent、调用付费 provider 或取得真实定时 IM 样本。

## 验证

- loader、exact target、placeholder、expiry、budget/restart、interactive no-run、timeout/interrupt、forged metadata、
  broad Adapter refusal 与固定 Codex command 均有回归。
- SME `commercial-evidence-loop` 已校准为 Codex reviewer 的 read-only inspection charter。
- 真实 CLI 只用固定参数执行 `--help` 解析验证，不消耗模型调用。
