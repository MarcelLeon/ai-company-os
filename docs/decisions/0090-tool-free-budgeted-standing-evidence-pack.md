# ADR-0090: Tool-Free Budgeted Standing Evidence Pack

**状态**:Accepted
**日期**:2026-07-22
**决策者**:Wang / Codex(协作)
**相关 Round**:Round 257

---

## 背景与问题

Round 256 的真实 standing autonomy 单次运行消耗 227,252 tokens，远超 grant 中 50,000 的累计停止阈值；模型又引用
324 KiB 的 `STATUS.md`，结果被 256 KiB source validator 拒绝。控制面完成了 owner binding、定时派发、Telegram ACK、
durable usage/outcome 和 `max_runs=1`，但当前 run 的上下文和结果证据没有共同边界。

Codex 的 rollout budget 在每次 provider response 后记账并停止后续 rollout；它不能单独证明当前 response 绝不越界。
因此系统需要同时约束可见上下文、工具能力、Codex rollout 和结果采信，而不能继续把 post-run 累计阈值称为硬预算。

## 候选方案

### 方案 A — 只保留 `token_stop_threshold`

- 优点：无需改协议。
- 缺点：只能阻止下一次运行；真实样本已经证明单次成本可大幅越界。

### 方案 B — 让 Agent 在只读沙箱内自行浏览仓库

- 优点：上下文灵活。
- 缺点：无法在派发前确定输入边界，且 charter 可能把 Agent 引向 validator 不接受的大文件。

### 方案 C — 系统生成 evidence pack，执行时禁用工具并施加多层 token 门禁

- 优点：派发前即可确定模型唯一可见的证据、原始 path/line、完整文件 SHA 和总字符数；结果只能引用 pack 中的行。
- 缺点：需要维护 allowlist/section marker；Codex/provider 的计费语义仍不是 AICO 能控制的美元 hard quota。

## 决策

选择 **方案 C**：

1. standing charter 必须显式配置最多 8 个 repo-relative evidence source，可选 exact start/end heading；系统读取最多
   1 MiB/文件、384 行/片段、2,000 字符/行，生成不超过 64 KiB 的 fingerprinted pack。
2. pack 保存完整源文件的 size/SHA，但 prompt 只包含 allowlisted 原始 `path:line:text`；绝对路径、越界、软链、非 UTF-8、
   marker 歧义、超限或运行中漂移全部 fail closed。
3. Codex 预授权命令忽略 user config/rules，使用 read-only sandbox、never approval、ephemeral session、strict schema，显式禁用
   shell、unified exec、multi-agent、apps、browser、computer use、image generation 和 web search。
4. grant schema 升级 v2，新增 `max_total_tokens`。Codex 命令把它同时写入 rollout budget 和 model context window；Adapter 必须声明
   支持该范围，Phase 1 preflight 才允许启动。
5. terminal provider usage 是采信权威：若 `total_tokens > max_total_tokens`，usage 仍持久化，但结果不进入业务验收，IM/晨报显示
   `budget=exceeded`。within-limit 同样进入 restart-safe receipt。
6. `token_stop_threshold`继续只表示跨 run 累计熔断；不得与 `max_total_tokens`混称。

## 安全与口径边界

- 这是 owner token envelope 与结果采信的硬门禁，不是美元账单、provider 内部计费或网络层 quota 保证。
- Codex rollout budget按 response 后记账；AICO 通过 tool-free 单次 response、context window 和 post-run usage gate组合收口，仍必须用
  真实样本验证当前 CLI/provider 是否在 owner limit 内结束。
- pack 的 SHA 证明 owner-local exact bytes 未漂移，不证明业务语义、远端来源、Telegram human read或同一 OS 用户下的密码学 owner 身份。
- provider usage 缺失、pack 漂移、结果越界或未引用 allowlisted 行都停授，不自动换 grant 重跑。

## 后果

### 正面后果

- 大型状态文件可以提供小型精确片段，而不放宽全文件 source cap。
- prompt 注入式工具指令没有可用工具，pack 正文也不参与写操作风险分类。
- 预算 breach 成为 durable、可比较、可在 IM 接手的显式事实。

### 负面后果

- heading 重命名会让 preflight/dispatch fail closed，需要 owner 更新 charter。
- 任务只能基于预先选定证据回答；需要探索的新任务应走有人审批的普通 task，而不是 standing autonomy。
- 旧 v1 grant 不兼容，必须由 owner 重新签发 v2 external `0600` grant。

## 相关链接

- `src/aico/core/standing_evidence_pack.py`
- `src/aico/core/standing_autonomy.py`
- `src/aico/adapter/codex.py`
- `docs/journal/BLOCKERS.md` B-014
- `docs/journal/PITFALLS.md` P-113
- [Codex rollout budget session implementation](https://github.com/openai/codex/blob/main/codex-rs/core/src/session/rollout_budget.rs)
