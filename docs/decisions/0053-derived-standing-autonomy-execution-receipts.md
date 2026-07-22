# ADR-0053: Derived Standing Autonomy Execution Receipts

**状态**:Accepted
**日期**:2026-07-21
**决策者**:Codex / Round 215

## 背景

owner-bound standing run 会持久化accepted proposal与TaskBus task/snapshot，但`/inbox`、`/morning`只显示generic task。
owner无法直接判断它属于哪次预授权；在“先扣run budget、后submit TaskBus”的故意at-most-once窗口中崩溃时，还会留下
accepted proposal但没有task evidence，现有视图完全隐藏。另一次E2E补测发现preauthorized runner错误复用了overnight
handoff grader，普通只读输出会被二次标成FAILED。

## 决策

1. receipt是既有`StandingProposal + TaskSnapshot`的只读projection，不新增table/schema或第二份outcome状态。
2. 只投影`decision_mode=preauthorized`且accepted的proposal；必须同时匹配task id、proposal metadata和grant metadata。
3. 无task id、无snapshot或metadata不一致统一显示`evidence_missing`，保留at-most-once语义，不自动重试/退款。
4. terminal status与elapsed只来自TaskBus snapshot；不从provider自然语言推断成功。running/missing不显示完成耗时。
5. inbox/morning只显示short proposal/task/auth ref、charter、status和bounded elapsed；不显示payload、output、reason、
   owner/target/path/secret。
6. failed/interrupted/rejected/missing成为恢复动作，running成为monitor动作，done只保留证据不制造待办。
7. preauthorized runner直接走普通TaskBus stream与自身timeout，不再调用overnight handoff completeness grader。

## 否决方案

- **新增execution_receipts表**：会与authoritative task snapshot形成双写/恢复一致性问题。
- **把provider正文存进proposal**：扩大敏感数据retention，并把自然语言误当终态事实。
- **accepted无task时自动retry/refund**：crash前是否已产生provider成本未知，可能重复执行。
- **继续依赖generic Done/Blocked**：不能证明grant/proposal/task linkage，也隐藏dispatch crash window。
- **复用overnight runner**：standing inspection没有overnight handoff contract，跨意图grader会制造假失败。

## 后果

### 正面

- owner回归视图直接看到每次自治结果与可执行下一步，重启后投影一致。
- metadata mismatch和accepted-without-task变成显式证据缺口，不会沉默。
- 没有新持久化表、migration或outcome双写窗口。

### 代价与剩余风险

- receipt只证明本地durable orchestration truth，不证明provider输出质量、成本、远端IM receipt或业务验收。
- elapsed以proposal decision到terminal snapshot近似，不是provider精确计费时长。
- B-014真实owner grant/provider/scheduler/IM样本仍未完成。

## 验证

- 六种Task状态、missing/mismatched metadata、manual exclusion、SQLite restart parity、inbox/morning优先级和脱敏回归。
- scheduled success第二个morning tick显示done且不重跑；timeout显示interrupted且不重跑。
- ordinary inspection output不再被overnight grader改成FAILED。
