# 03 — 设计模式与抽象时机

> **过早抽象比晚抽象糟糕得多**。本文给出抽象时机判定和模式选择指导。

---

## 抽象时机硬规则(Rule of Three)

| 出现次数 | 应对策略 |
|---|---|
| 第 1 次 | **直接写**,不抽象 |
| 第 2 次 | **复制粘贴**,标记 `// TODO(P-XXX): 第 3 次出现时抽象` |
| 第 3 次 | **这时才抽象** |

### 为什么是 3 次

- 1 个样本无法识别"什么是变化点,什么是不变点"
- 2 个样本可能是巧合,且抽象方向容易偏
- 3 个样本足以暴露真实变化维度,抽象方向收敛

### 例外
真正例外的情况(可以提前抽象):
1. 跨语言协议(如 Adapter 接口要被 Java 和 Python 各实现一份)
2. 公开 API(对外 SDK,改起来代价大)
3. 已有大量同类模式的成熟领域(如 Repository 模式之于 CRUD)

非例外情况下,**违反 Rule of Three 的抽象会被 PR 打回**。

---

## 本项目最常用的几个模式

### 1. Adapter 模式(必用)

**用于**:统一各 AI 工具(Claude Code / Codex / OpenClaw / 内部 CLI)的接口差异。

**接口设计原则**:
- 只放共性方法
- 每个 Adapter 内部封装易变性
- Adapter 不知道彼此存在

**最小接口示例**(Java):
```java
public interface AIAdapter {
    String name();
    Set<Capability> capabilities();
    Mono<TaskAck> receiveTask(Task task);
    Flux<TaskOutput> streamOutput(TaskId taskId);
    AdapterStatus status();
    Mono<Void> interrupt(TaskId taskId);
}
```

### 2. 策略模式(用于人格化、审批)

**用于**:同一个动作,不同策略产生不同行为。

**典型场景**:
- 人格化:"老张严谨"vs"小李激进" → 两个 `PersonaStrategy`
- 审批:"自动通过"vs"必须人工"vs"金额阈值" → 多个 `ApprovalPolicy`

**避免**:用 `if/switch` 做 N 个分支处理不同策略。

### 3. 责任链(用于消息处理管道)

**用于**:用户消息进来 → 解析 → 路由 → 鉴权 → 派发 → 出口。

**好处**:每一段可以独立加减。

### 4. 观察者 / 事件总线(用于状态变化广播)

**用于**:Adapter 状态变化 → 通知 IM Channel 推送 → 通知审计日志 → 通知看板更新。

**注意**:用现成的事件总线(Spring Events / Python blinker / Node EventEmitter),**不要自己撸**。

### 5. 仓储模式(用于持久化)

**用于**:任务、Round、Persona 配置等的持久化。

**抽象**:`TaskRepository` 接口 → 多实现(In-Memory / SQLite / Postgres)。

### 6. 工厂 + 注册表(用于插件加载)

**用于**:启动时根据配置加载 Adapter 和 Channel 实例。

```java
// 注册表
@Component
public class AdapterRegistry {
    private Map<String, AIAdapter> adapters;
    public AIAdapter get(String name) { ... }
}
```

---

## 反模式(本项目里出现就打回)

### ❌ 上帝类
单个类有 5+ 不同职责,每次需求来都要改它。
**判定**:看 import 数量 + 行数 + 公开方法数。

### ❌ 贫血模型 + 胖 Service
所有逻辑塞在 Service 里,模型只是 getter/setter。
**应对**:让领域模型有行为,Service 只协调。

### ❌ 过度抽象
- 接口里只有一个实现类还永远只会有一个
- 抽象的接口比具体实现还多
- "为了未来可能的扩展"提前抽象

### ❌ 配置驱动一切
所有逻辑都做成配置可调,导致行为不可预测。
**原则**:可插拔 ≠ 行为完全配置化。

### ❌ Sidecar 滥用
一个简单功能拆成多个进程通信,徒增运维复杂度。
**原则**:进程边界要有充分理由(独立部署 / 独立扩缩容 / 隔离故障)。

---

## 引入新模式的流程

如果你要在本项目首次引入某个新模式(本文未列出的):

1. 先查 `docs/journal/PITFALLS.md` 是否有否决过类似方案
2. 在 `docs/decisions/` 写一个 ADR,说明:
   - 为什么需要这个模式
   - 否决了哪些替代方案
   - 引入后影响哪些模块
3. 写一个最小示范实现
4. 提 PR 时 link ADR

**禁止"我先写一下试试"式引入**。模式一旦扩散,移除成本极高。

---

## 抽象重构的时机

### 何时该把"复制粘贴"重构成抽象
- 第 3 次出现相似代码
- 维护其中一份发现"哦还有另外两份要同步改"
- 三份代码出现 bug 修一份忘了另两份

### 何时该把"过度抽象"拍扁
- 抽象层只有 1 个实现且 6 个月没变
- 阅读代码必须跳 3 个文件才能理解一个功能
- 加新功能要改 5+ 个文件且都在改抽象层

**两种方向都是合法的演化**。重要的是**做完写到 ROUNDS.md**,让下一轮 AI 知道。
