# ADR-0037: Lead Standing Charter Proposal Boundary

**状态**:Accepted
**日期**:2026-07-21
**决策者**:Codex
**相关 Round**:Round 199

## 背景

AICO 已经具备 IM 下达、异步任务、风险审批、持久化状态、早报、经验和审计恢复,但 lead 在老板
沉默时仍完全被动。`boss-first-grounding.md` 的 Future F-1 要求先有 proposal queue,避免把主动性
误做成无人监管的自动执行。

## 候选方案

### A. Lead 定时直接创建任务

拒绝。它会把“岗位职责”变成隐式授权,并可能在老板不在时触发文件、shell、发布或客户数据动作。

### B. 用 LLM 扫 STATUS/BLOCKERS 即兴决定下一步

拒绝。自由文本不是稳定机器契约,结果不可重复,也容易把旧文档或描述性内容当成授权。

### C. 显式 standing charter 生成持久化 candidate,老板接受后才建 task

采用。charter 是项目配置中的有界输入;proposal 是可审计状态;真正工作继续经过现有 role、TaskBus、
risk、approval、audit、memory、interrupt 和 handoff 链路。

## 决策

- `ProjectProfile` 增加显式 standing-charter items,每项声明 objective、role、acceptance evidence、
  stop conditions 和 cooldown。
- 恢复入口最多刷新一个 candidate。存在 running/waiting work、团队不完整或 cooldown 未到时不生成。
- proposal 使用独立 `StandingProposalStore` port;本地默认实现与其它 Phase 8 状态共用 SQLite。
- `/proposal accept` 是唯一执行入口;`/proposal reject` 只记录决定。读取 `/inbox`、`/morning`、
  `/proposals` 永不创建 task。
- accepted task 不获得额外权限;风险动作仍由既有 `/approve` 决定。

## 后果

### 正面

- 老板不必先提出每一个下一步,但仍保留最终决策权。
- proposal 跨重启可恢复,进入 inbox/morning,不会藏在后台。
- 主动机制使用显式配置和确定性 gate,不依赖模型猜项目状态。

### 代价

- 第一切片只在 inbox/morning refresh 点产生 proposal,不是通用后台 scheduler。
- charter 的质量由项目 owner 负责;错误 charter 仍可能产生低价值候选,但不会自动执行。
- runtime 进程守护、真实 Telegram credentials 和 real-client 体感仍需单独验证。

## 不再做的事

- 不把 standing charter 当成 blanket authorization。
- 不让 lead 自动 accept 自己的 proposal。
- 不把 proposal store 塞进 TaskBus 或 MemoryStore。
- 不在 core 中解析项目 Markdown 来推断职责。
