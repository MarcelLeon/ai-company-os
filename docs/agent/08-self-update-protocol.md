# 08 — Agent 自我更新协议

> Agent 完成一轮工作后,**必须**按本协议更新文档体系。
> 这是项目能被任意 AI 接手而不退化的机制保障。

---

## 为什么这件事极其重要

如果你写了代码却没更新文档,下一轮 AI:
- 不知道你做了什么 → 可能重复劳动
- 不知道你为什么这么做 → 可能误改
- 不知道你踩了什么坑 → 可能再踩
- 不知道你卡在哪 → 可能瞎尝试

**写代码 30 分钟,更新文档 5 分钟。这 5 分钟决定了项目能不能活过 10 轮**。

---

## 必更新文档清单

### 强制(每轮必更)

#### 1. `STATUS.md`
更新内容:
- [ ] 顶部"最后更新"日期
- [ ] "当前轮次"+1
- [ ] "Phase X 进度"打勾相关项
- [ ] "上一轮做了什么"重写
- [ ] "下一轮建议做什么"按最新优先级重排

模板填写:
```markdown
## 上一轮做了什么

**Round N**(YYYY-MM-DD,角色):
- 做了 A
- 做了 B
- 决策:选了 X 而不是 Y
```

#### 2. `docs/journal/ROUNDS.md`
追加一段记录,使用文件中的模板。**重点写否决方案的理由**。

模板:
```markdown
## Round N — YYYY-MM-DD — [角色]

### 输入
### 思考与讨论
### 产出
### 关键决策
### 留给下一轮
### 状态变化
```

### 视情况更新

#### 3. `docs/journal/PITFALLS.md`
**踩了新坑就加**。即使是"小坑",写下来。

判定标准:
- 我花了 > 10 分钟才搞明白的问题 → 一定要写
- 文档没说但实际遇到的差异 → 一定要写
- 调试出错信息 / stacktrace 中暴露的非显然问题 → 一定要写

#### 4. `docs/journal/BLOCKERS.md`
- **遇到无法本轮解决的问题就加**(状态 BLOCKING / DEFERRED)
- **解决了已有 BLOCKER 就更新状态为 RESOLVED**

#### 5. `docs/decisions/`(ADR)
**做了重要架构决策就写 ADR**。

判定标准 — 满足任一即写:
- 选了 A 而否决了 B(技术方案 / 库 / 模式)
- 影响多个模块的接口
- 规模较大,改起来代价高

ADR 文件名:`NNNN-short-title.md`(如 `0001-tech-stack-selection.md`)

#### 6. `CHANGELOG.md`
- 用户可见的功能变更必更新
- 内部重构、文档修改不需要

#### 7. `docs/human/daily-ops.md`
- 新增了运维命令必更新
- 改了启动方式必更新

#### 8. `docs/human/troubleshooting.md`
- 修复了之前列在这里的问题 → 标记已解决
- 引入了新的常见错误 → 加入

---

## 更新顺序(建议)

```
1. 写代码 + 写测试
   ↓
2. 跑 CI / 本地验证
   ↓
3. 更新 PITFALLS.md(如有新坑)
   ↓
4. 更新 BLOCKERS.md(如有新卡点 / 解决旧卡点)
   ↓
5. 更新 docs/decisions/(如有架构决策)
   ↓
6. 更新 ROUNDS.md(本轮记录)
   ↓
7. 更新 STATUS.md(顶层状态)
   ↓
8. 更新 CHANGELOG.md(如有用户可见变更)
   ↓
9. 更新 daily-ops.md / troubleshooting.md(如有运维变更)
   ↓
10. commit & push
```

`ROUNDS.md` 和 `STATUS.md` 放最后,因为它们要总结所有变更。

---

## 自检:文档质量

更新完文档后,问自己:

- [ ] 一个完全没接触过本项目的 AI,只读 `AGENTS.md` 指定的 7 篇文档,能否独立完成下一轮任务?
- [ ] 6 个月后的我,看 `ROUNDS.md` Round N 这一段,能不能想起来当时的思考过程?
- [ ] `PITFALLS.md` 新加的条目,有没有"症状 / 根因 / 解决方案 / 如何避免"四件套?
- [ ] `STATUS.md` 的"下一轮建议"是否具体到可以直接派任务?

任何一项"不确定",回去补。

---

## 反模式

❌ **更新文档时只写"做了什么",不写"为什么"和"否决了什么"**
→ 下一轮 AI 没有否决记录,会重新发明被否决的方案。

❌ **更新 STATUS 把所有 Phase 都标"进行中"**
→ 状态失真。任何时刻应只有 1-2 个 Phase 在"进行中"。

❌ **PITFALLS 只写"遇到 X 报错"不写解决方案**
→ 没价值。下一轮看到这条还是不知道怎么办。

❌ **写文档时加大量营销语言**
→ "革命性的设计"、"前所未有的架构"。文档要事实,不要修饰。

❌ **代码里的 `// TODO` 不同步到 BLOCKERS**
→ TODO 散在代码里没人看,卡点要有显式登记处。

---

## 一个好的文档更新示例

```
本轮我:
- 实现了 TelegramChannel(代码)
- 写了 8 个单测和 1 个集成测试

我更新了:
✓ STATUS.md:Phase 1 进度 +"Telegram Channel 完成",下一轮建议改为"实现 Claude Code Adapter"
✓ ROUNDS.md:追加 Round 2,记录我考虑过 long polling vs webhook,选了 long polling 因为 Phase 1 不引入域名/反向代理
✓ PITFALLS.md:加 P-00X — Telegram bot 长连接被 Cloudflare 误判限流的处理方案
✓ docs/decisions/0002-telegram-long-polling.md:正式 ADR 记录长连接选择
✓ CHANGELOG.md:[Unreleased] / Added — Telegram Channel adapter

我没更新(故意):
- daily-ops.md(运维命令没变)
- troubleshooting.md(没新错误)
```

这就是合格的一轮交接。
