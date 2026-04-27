# 02 — 代码规范

> 本文是本项目代码层面的硬约束。**违反这些规则的代码不会被合并**。

---

## 硬约束(物理上限,不是建议)

### 单类 < 500 行
- 包括注释和空行
- 超过即拆。拆分思路:
  - 是否承担了多个职责?→ 按职责拆
  - 是否有可复用部分?→ 抽 utility
  - 是否有内部状态机?→ 状态对象拆出去

### 单方法 < 100 行
- 超过即拆。拆分思路:
  - 是否有多层嵌套循环?→ 提取私有方法
  - 是否有多种 case?→ 用策略模式或多态
  - 是否有连续多步?→ 提取流程方法

### 单文件外部依赖 < 10 个
- import / require 语句多于 10 个,**这个类大概率职责过重**
- 例外:配置类、入口类

---

## 设计原则

### 面向接口编程

**所有跨模块的协作必须通过接口**。具体规则:

1. AI 工具适配器 → 必须实现 `AIAdapter` 接口
2. IM 通道 → 必须实现 `IMChannel` 接口
3. 持久化后端 → 必须实现对应的 Repository 接口
4. 人格化策略 → 必须实现 `PersonaStrategy` 接口
5. 审批策略 → 必须实现 `ApprovalPolicy` 接口

**反模式**:
```java
// ❌ 错
public class Orchestrator {
    private ClaudeCodeAdapter claudeCode;  // 直接依赖具体实现
}

// ✅ 对
public class Orchestrator {
    private List<AIAdapter> adapters;  // 依赖接口
}
```

### 可插拔

**新增能力 = 新增插件,不是修改核心**。

判定一个组件是否真的可插拔:
- 删掉它,核心代码不报错(可能功能少,但能编译能运行)
- 加一个新的同类组件,核心代码不需要改

### 配置外置

不要把"哪些 AI、哪些 IM、哪些人格"硬编码在代码里。
- Java:用 `application.yml` + `@ConfigurationProperties`
- Python:用 `pydantic-settings` + `.env`
- 都用配置文件 + 环境变量覆盖模式

---

## 命名规范

### 通用
- 类名:大驼峰(`TelegramChannel`)
- 方法/变量:小驼峰(Java/JS) / 蛇形(Python)
- 常量:全大写下划线(`MAX_RETRY_COUNT`)
- 接口名:不带 `I` 前缀,直接用名词(`AIAdapter` 不是 `IAIAdapter`)
- 实现类:实现 + 接口名(`ClaudeCodeAdapter`、`TelegramChannel`)

### 项目特定术语(统一全项目)

| 术语 | 含义 | 不要用 |
|---|---|---|
| Adapter | AI 工具适配器 | Connector / Wrapper |
| Channel | IM 通道 | Messenger / Bridge |
| Persona | AI 人格 | Identity / Character |
| Orchestrator | 编排核心 | Hub / Manager |
| Task | 用户下发的工作单元 | Job / Request |
| Round | 一轮工作 | Iteration / Session |

---

## 错误处理

### 异常分层
- **可恢复异常**(网络抖动、API 限流):捕获 + 重试 + 记录日志
- **配置/编程错误**:fail-fast,不要试图自愈
- **业务异常**:转化为统一的 `OrchestrationException`,带语义错误码

### 不要做的事
- ❌ 空 catch:`try { ... } catch (Exception e) {}`
- ❌ 吞异常变 null:`return null;` 在 catch 里
- ❌ `printStackTrace()` 或 `print(e)`,必须用 logger
- ❌ 把异常消息当业务返回值返回给用户(暴露内部细节)

---

## 日志规范

### 日志级别使用
- `ERROR`:导致流程终止的问题
- `WARN`:可恢复但需要关注的(重试、降级)
- `INFO`:关键业务节点(任务接收、任务完成、Adapter 启动)
- `DEBUG`:详细执行流程(开发期开,生产期默认关闭)
- `TRACE`:几乎不用

### 日志内容
- 必须带 traceId / taskId,便于跨系统追踪
- 不要打印敏感信息(token、用户消息原文中的密码等)
- 不要在循环里打 INFO,会刷屏

---

## 注释规范

### 该写的注释
- 公共接口的 Javadoc / docstring(说**为什么**而不是**做了什么**)
- 复杂业务逻辑的"为什么这么做"
- 引用了某个 ADR / PITFALL 的代码处:`// 见 ADR-003 / PITFALL P-005`

### 不该写的注释
- 复述代码的注释:`i++;  // i 加 1`
- 过期注释(代码改了注释没改)
- TODO 不写到 BLOCKERS.md

### TODO 规则
项目内 `TODO` 必须是以下之一:
```java
// TODO(B-001): 等技术栈选型 ADR 出来后切换
// TODO(@username, 2026-05-01): 临时方案,需在 5/1 前重构
```

无追溯信息的 `// TODO` 一律视为代码异味,review 时打回。

---

## 不变性优先

- Java:多用 `record` / `final` / 不可变集合
- Python:多用 `frozen=True` 的 dataclass / `tuple`
- 所有事件、消息、状态对象**必须不可变**

---

## 依赖管理

### 添加新依赖必须自问
1. 这个依赖能用现有依赖替代吗?
2. 这个依赖最近 12 个月有维护吗?
3. 它的传递依赖会引入多少 MB?
4. 加进来需要写 ADR 吗?(如果是核心层依赖,**需要**)

### 不允许
- 引入孤儿库(GitHub stars < 100 且最近 1 年无 commit)
- 引入和已有依赖功能重复的库
