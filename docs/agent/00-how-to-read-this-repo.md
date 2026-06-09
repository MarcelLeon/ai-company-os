# 00 — Agent 阅读路径

> 本文是 [`AGENTS.md`](../../AGENTS.md) 的扩展版,详细说明 Agent 接手项目的阅读策略。
> 如果你只是要快速接手,看 `AGENTS.md` 就够了。

---

## 三种接手场景

### 场景 A:首次接触本项目
完整执行 `AGENTS.md` 的 7 步阅读路径,不要跳。预计耗时 15-20 分钟。

### 场景 B:已经熟悉,接手新一轮任务
最小阅读集:
1. `STATUS.md`(看现状和下一轮建议)
2. `docs/journal/ROUNDS.md` 最近 3 轮
3. `docs/journal/BLOCKERS.md`
4. 与你任务相关的具体文档

预计耗时 5 分钟。

### 场景 C:接到一个具体小任务(如修一个 bug、加一个 Adapter)
最小阅读集:
1. `docs/journal/PITFALLS.md` grep 相关关键词
2. 任务直接相关的代码文件和测试
3. 相关的 ADR(如有)

预计耗时 3 分钟。

### 场景 D:接到 GitHub 发布 / public / tag / Release 任务
最小阅读集:
1. `STATUS.md` 的当前轮次和"下一轮建议"
2. `docs/agent/09-github-release-ops.md`
3. `docs/human/github-publication.md`
4. `docs/launch/playbook.md`
5. `docs/launch/v0.1.0-release-notes.md`

预计耗时 5-8 分钟。public、tag、GitHub Release、D0 宣发都属于外部信号动作,不要只按普通
commit 流程处理。

---

## 阅读时的注意事项

### 文档之间的优先级冲突

如果你发现两份文档有冲突,优先级:

```
NORTH_STAR.md
  > STATUS.md
    > docs/decisions/(ADR)
      > docs/journal/(实际历史)
        > docs/agent/(规范)
          > docs/architecture/(设计)
            > 代码注释
```

发现冲突时,**不要自行决定遵循哪一份**——记录到 `BLOCKERS.md` 并请求人类裁决。

### 时效性判断

每个文件顶部应该有 `最后更新` 字段。如果某文档超过 30 天没更新但代码已大幅变更,**默认怀疑文档过时**,以代码和 `ROUNDS.md` 为准,并把过时的文档标到 `BLOCKERS.md`。

### "我不知道"的合法表达

读完文档后,如果你对某个问题仍然不清楚,**明确说"我不知道,需要人类确认 X"**比硬猜好。把不确定性藏起来是制造下一轮 PITFALLS 的最快方式。

---

## 反模式(请避免)

❌ **不读 ROUNDS 直接动手**:你会重新发明被否决过的方案。
❌ **不读 PITFALLS 直接动手**:你会踩一个明确记录过的坑。
❌ **跳过 NORTH_STAR**:你做的功能可能根本不该存在。
❌ **只读代码不读文档**:代码能告诉你"做了什么",但不能告诉你"为什么这么做"和"否决了什么"。
❌ **读完了不更新文档**:你的工作就白做了一半,下一轮 AI 会重复你的思考过程。
