# Playbooks — 操作剧本

> 复杂操作的逐步剧本。和文档不同,Playbook 是"按步骤执行就能完成"的可操作清单。
>
> 当前 Phase 0 占位。Phase 1+ 会逐步累积真实剧本。

---

## 什么是 Playbook

Playbook = "可执行的步骤清单",特点:
- 给定输入,按步骤执行,得到确定输出
- 不需要思考(思考已经在 ADR / 设计文档里)
- 可以被人类或 Agent 直接复用

举例:
- 「如何接入一个新 IM 通道」
- 「如何接入一个新 AI 工具」
- 「如何创建一个新 Persona」
- 「如何处理审批流的异常」
- 「如何回滚一个错误的发布」

---

## Playbook 模板

```markdown
# Playbook: 标题

## 适用场景
什么时候用这个 Playbook?(具体到可判断"是不是我现在的情况")

## 前置条件
- 需要的权限 / 工具 / 知识

## 步骤
1. 步骤 1(具体到可执行命令)
2. 步骤 2
3. ...

## 验证
完成后如何验证成功?

## 失败回滚
某步失败怎么办?

## 相关
- 相关 ADR
- 相关 PITFALLS
```

---

## Playbook 列表

(Phase 0 占位,以下都将在对应 Phase 实现时填充)

### 接入类
- [ ] `add-new-adapter.md` — 接入一个新 AI 工具(预计 Phase 2 编写)
- [ ] `add-new-channel.md` — 接入一个新 IM 通道(预计 Phase 2 编写)
- [ ] `add-new-persona.md` — 创建一个新人格(预计 Phase 3 编写)

### 运维类
- [ ] `daily-startup.md` — 日常启动检查清单
- [ ] `incident-response.md` — 故障响应流程
- [ ] `release-rollback.md` — 发布回滚

### 开发类
- [ ] `bisect-failure.md` — 二分查找哪次提交引入了 bug
- [ ] `add-new-capability.md` — 给 Adapter 添加新能力

### 测试类
- [ ] `test-new-telegram-bot.md` — 验证新 Telegram Bot 配置
- [ ] `test-claude-code-adapter.md` — 验证 Claude Code Adapter

---

## Playbook 编写时机

- **第 2 次执行某个复杂流程**:开始写
- **第 3 次执行**:完善
- **看到自己或别人在某流程犯错**:立刻补丁

不要为还没做过的事写 Playbook——那是设计文档,不是 Playbook。

---

## Playbook vs ADR vs PITFALLS

| 文档类型 | 回答的问题 | 时态 |
|---|---|---|
| ADR | 为什么这么做? | 过去式 |
| Playbook | 怎么做? | 现在/将来式 |
| PITFALLS | 这里有坑,小心 | 过去式 |

三者互补,不要混用。
