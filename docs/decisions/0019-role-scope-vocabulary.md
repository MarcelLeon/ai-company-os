# ADR-0019: Role Scope Vocabulary and Compact Team Views

**状态**:Accepted
**日期**:2026-05-13
**决策者**:Codex
**相关 Round**:Round 68

---

## 背景与问题

Round 67 扩充了 Adapter 和 AI Company roles 后,`/agents` 与 `/roles` 暴露出两个产品语义问题:

1. `/agents` 同时使用 `implementer` / `reviewer` 这类岗位名和 `cursor` / `codeflicker` 这类工具名,用户难以判断它展示的是员工、岗位还是底层工具。
2. `/roles` 默认输出包含大量 summary 和 permission token,在 IM 里像配置 dump,不像老板查看项目团队。

同时,权限语义需要分层,但不能发展成难记的大型 RBAC。北极星要求“像管理真实团队一样”,所以默认视图必须符合团队管理直觉:少量岗位、清晰任命、危险动作走审批。

## 候选方案

### 方案 A — 直接实现完整 RBAC

- 优点:权限语义最强,可以严格控制每个 role 的每类操作。
- 缺点:当前执行门禁已经由 risk + approval + adapter capability 承担,此时上 RBAC 会扩大范围,还会让个人 dogfooding 配置成本过高。

### 方案 B — 只做 UI 压缩,不定义权限词表

- 优点:改动小。
- 缺点:权限 token 仍然不成体系,下一轮 Agent 可能继续新增 `read_xxx` / `write_xxx` 细粒度词,回到难管理状态。

### 方案 C — 三层小词表 + 紧凑默认视图

- 优点:保留现有审批安全边界,同时让用户只记少量词:
  - Adapter capabilities:工具物理能力。
  - Role scopes:岗位工作范围。
  - Risk levels:单次任务风险与审批。
- 缺点:Role scopes 暂时仍是 prompt / appointment contract,不是强运行时 ACL。

## 决策

选择 **方案 C — 三层小词表 + 紧凑默认视图**。

三层词表如下:

| 层级 | 用途 | 枚举 |
|---|---|---|
| Adapter capability | 工具物理上能不能做 | `code_review`, `code_edit`, `shell_exec`, `long_running`, `stream_output`, `interruptible` |
| Role scope | 这个岗位默认该做什么 | `docs`, `code`, `tests`, `ops`, `audit` |
| Risk level | 这次任务危险到什么程度 | `read_only`, `write_files`, `shell_exec`, `destructive` |

默认 `/roles` 只展示核心岗位和专家岗位;支持岗位与长说明放到 `/roles all` 和 `/role <id>`。`/appoint <agent> as <role>` 不传 scope 时,继承 role 默认 scope。

## 决策理由

- 一个普通项目经理不应该记住十几个 `read_repo` / `write_docs` 风格 token;5 个 role scope 更接近团队管理里的职责域。
- “一个讨论大于 3 人就变重、一个人管理约 10 人是上限”这类团队管理经验可以映射到默认 UX:默认板只展示少数关键岗位,其余按需展开。
- Adapter capability 和 risk level 已经有代码语义,保留它们比重命名为另一个权限系统更安全。
- Role scope 当前只表达岗位契约;危险任务仍由 risk assessor、adapter capability 和 `/approve` 共同控制。

## 后果

### 正面后果

- `/agents` 更像员工池,优先展示 `claude` / `codex` 等工具入口名。
- `/roles` 更像项目岗位板,默认输出短、可扫读。
- role 权限词表收敛到 5 个可记忆 scope。
- 任命命令默认继承岗位 scope,减少 IM 中的配置负担。

### 负面后果

- Role scope 不是强 ACL,需要在 UI 和文档中避免暗示它已经是底层执行授权。
- 旧配置中的细粒度 permission token 仍可存在;本轮不做迁移器。

### 后续演化

- 如果后续要让 role scope 参与真实门禁,应新增明确的 RoleAuthorizationPolicy,并写新 ADR。
- 如果默认 role 超过 10 个,应优先分组或隐藏,不要继续拉长 `/roles` 默认输出。

## 相关链接

- ADR-0007:远程审批与 Adapter 能力边界
- ADR-0011:Project Assignment Layer
- ADR-0012:Boss-Facing Team Commands and Role System
