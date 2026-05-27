# ADR-0026: Lead Decision Team Contract

**状态**:Accepted
**日期**:2026-05-21
**决策者**:Wang / Codex
**相关 Round**:Round 102

---

## 背景与问题

AICO 的项目办公室已经有 `/lead`、roles、shared memory、team broadcast 和 `/overnight`。但原来的 lead 更像“默认路由角色”,还没有承担真实公司里项目负责人的判断职责。

如果 AICO 要真正替个人开发者省力,不能只把更多任务转给 boss。Lead agent 应该吸收团队历史经验、调取其他 agent 的关键进展和反对意见,在授权范围内替 boss 做判断,只把高风险或不可逆决策升级给 boss。

## 候选方案

### 方案 A — 保持 lead 为默认路由

- 优点:实现简单,不改变现有命令。
- 缺点:boss 仍要自己汇总上下文和做大量中间判断,虚拟公司只像任务转发器。

### 方案 B — 让所有 agent 都能直接做最终决策

- 优点:自动化程度高。
- 缺点:责任边界混乱,容易让执行者自证正确,也绕开 reviewer / challenger 的独立批判。

### 方案 C — 强化 lead,并要求团队具备 challenger

- 优点:符合真实团队:lead 对交付负责,challenger 提供独立质疑,普通 agent 沉淀关键进展和经验。
- 缺点:项目 team setup 多一个必备角色,托管入口需要检查团队完整性。

## 决策

选择 **方案 C**。

Lead 是项目责任人,不是默认路由别名。AICO 的项目团队至少需要:

- 一个 appointed lead,由 `/lead <role>` 或项目默认 role 指定。
- 一个 `challenger` 角色,用于提出反对意见、质疑前提、审查机会成本和长期风险。

## 决策规则

- Lead 可以替 boss 做可逆、低风险、项目内的决策。
- 架构大改、公开发布、删除/迁移数据、凭证、付费、生产危险动作、法律/合规承诺必须升级给 boss。
- Lead 做重要判断前,应召回 shared memory,并咨询 challenger / reviewer / tester / architect 等相关角色。
- Challenger 不是普通 reviewer。Reviewer 偏代码质量和测试风险;challenger 偏前提、取舍、机会成本、长期副作用和反方论证。
- Agent 内部短期记忆不能默认等同于 lead 可用决策证据。后续 memory purpose 会区分 public broadcast、task key progress、task private 和 decision review。

## 第一阶段落地

- 默认角色库新增 `challenger` / `Critical Philosopher`。
- 默认项目配置自动任命 challenger:优先 Codex,否则复用已有 agent。
- Project office 和 `/team` 展示 team readiness。
- `/overnight` 要求 team 至少有 lead + challenger。
- project lead 的 prompt 增加决策责任、调取记忆、咨询 challenger 和升级 boss 的约束。

## 后续阶段

- Stage 2:给 `MemoryAtom` 增加用途标签,区分 public broadcast、task key progress、task private、decision review。
- Stage 3:实现 lead decision workflow,让 lead 在决策类任务中自动召回记忆、咨询 challenger/reviewer,输出 decision memo 并写审计。

## 相关链接

- ADR-0012 Boss-Facing Team Commands and Role System
- ADR-0022 A2A Memory Fabric
- ADR-0024 Phase 8 Offline Delegation Scope
- ADR-0025 Goal Mode Orchestration
- `src/aico/core/project_assignment.py`
- `src/aico/core/prompt_stack.py`
- `src/aico/core/offline_delegation.py`
