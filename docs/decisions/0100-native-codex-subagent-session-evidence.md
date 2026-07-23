# ADR-0100: Native Codex Subagent Session Evidence

**状态**:Accepted
**日期**:2026-07-23
**决策者**:Wang / Codex(协作)
**相关 Round**:Round 271

---

## 背景与问题

ADR-0093证明native host拥有Goal continuation，ADR-0099要求协作角色来自不同Agent与不同provider execution。但
`CodexGoalRoleEvidence`若由外部脚本直接填写，仍可能把一个main thread换几个role label包装成multi-agent；host run也没有把角色
执行绑定到真实runtime instance。正式baseline需要从Codex Desktop自身持久session派生这些事实，而不是相信被测系统的角色摘要。

## 候选方案

### 方案 A — 信任Goal最终文本中的角色清单

- 优点：实现最简单。
- 缺点：Agent ID、execution、消费链和重启边界均可自报，不能用于正式评分。

### 方案 B — benchmark runner直接创建subagent并记录ID

- 优点：证据易采集。
- 缺点：测到的是AICO runner编排能力，不是Codex Goal原生multi-agent能力，污染baseline。

### 方案 C — 只读解析Codex Desktop parent/child session JSONL

- 优点：provider-issued thread/turn、parent spawn、模型/权限、完成产物和来源turn均有第一方持久事件。
- 缺点：必须冻结session schema和角色assignment envelope；产品升级后可能需要适配parser。

## 决策

选择 **方案 C**：

1. runner只提交canonical frozen task，不调用`spawn_agent`。是否拆角色以及何时续跑由native Goal host决定。
2. 每个required role必须在child user input中收到exact
   `<aico_boss_absent_role_assignment>` envelope，绑定contract/task/sequence/role与前序artifact SHA。
3. observer从parent `spawn_agent → sub_agent_activity`与child
   `session_meta → task_started → turn_context → task_complete`交叉派生Agent identity、provider execution、source host turn和最终
   artifact；raw thread/turn ID不进入score artifact。
4. parent出现未声明或缺失subagent、child再次委派、模型/effort/只读无网络边界漂移、终态文本不一致或session权限/JSON异常时
   fail closed。host turn新增runtime instance SHA，role runtime必须与source turn一致。
5. scenario facts进入owner-only hash-chain ledger；`finalize-codex-goal-observations`只能从完整ledger派生receipt。restart、drift、
   approval、source pressure、IM takeover、external checks、budget和terminal缺一项均不能得到对应task成绩。

## 后果

- Codex Goal baseline可以使用真实原生subagent能力，但不能用角色标签冒充协作。
- hidden/extra Agent同样会被计为证据漂移，避免把额外provider成本藏在required roles之外。
- formal harness增加parent/child session路径和observer ledger；这些owner-private原始文件不提交仓库。
- session schema变化会显式打断formal run，而不是静默降低证据等级。

## 相关链接

- ADR-0093
- ADR-0099
- B-015
- P-130
- `src/aico/app/boss_absent_codex_goal_role_observer.py`
- `src/aico/app/boss_absent_codex_goal_scenario_observer.py`
