# 04 — Java 开发最佳实践

> 本文针对本项目(可能采用 Java + Spring AI / Spring Boot / Spring WebFlux)的 Java 实践规范。
> 如果技术栈选型最终未选 Java,本文保留作为可选模块的指南。

---

## 版本与基线

- **JDK**:Java 21+(LTS)
- **Spring Boot**:3.x
- **Spring AI**:最新稳定版
- **构建工具**:Maven 或 Gradle(按 ADR 决定后统一)

---

## 项目结构(模块化)

```
src/main/java/com/aico/
├── core/              # 编排核心,不依赖任何具体 Adapter / Channel
│   ├── orchestrator/
│   ├── task/
│   ├── persona/       # 接口
│   └── event/
├── adapter/           # AI 适配器(每个 AI 一个子模块)
│   ├── api/           # AIAdapter 接口、Capability 枚举
│   ├── claudecode/
│   ├── codex/
│   └── openclaw/
├── channel/           # IM 通道(每个 IM 一个子模块)
│   ├── api/           # IMChannel 接口
│   ├── telegram/
│   └── feishu/
├── persistence/       # 仓储实现
│   ├── memory/
│   └── jdbc/
├── policy/            # 审批/人格策略实现
└── infra/             # 基础设施(配置、日志、监控)
```

**核心原则**:`core/` 不依赖 `adapter/` `channel/` `persistence/` 任何具体实现,只依赖它们的 `api/` 子包接口。

---

## Spring 使用规范

### 依赖注入
- ✅ 构造器注入(必填依赖)
- ✅ `@Autowired` 仅用于可选依赖且加 `(required = false)`
- ❌ 字段注入

```java
// ✅ 对
@Service
public class Orchestrator {
    private final List<AIAdapter> adapters;
    private final EventBus eventBus;

    public Orchestrator(List<AIAdapter> adapters, EventBus eventBus) {
        this.adapters = List.copyOf(adapters);
        this.eventBus = eventBus;
    }
}
```

### Bean 配置
- 优先用 `@Component` / `@Service` / `@Repository` 标注
- 第三方对象用 `@Bean` 在 `@Configuration` 类中
- 不要在业务代码里手动 `new` 然后 `register`

### 配置类
所有配置走 `@ConfigurationProperties`,不要散落 `@Value`:

```java
@ConfigurationProperties("aico.telegram")
public record TelegramProperties(
    String botToken,
    String webhookUrl,
    Duration pollInterval
) {}
```

---

## 响应式 vs 同步

本项目大量场景适合响应式(长连接、流式输出、IM 长轮询)。

### 何时用响应式(WebFlux / Reactor)
- AI 输出流式回传(`Flux<TaskOutput>`)
- IM 消息接收(背压敏感)
- 多 Adapter 并发调用

### 何时用同步
- 一次性查询(`TaskRepository.findById`)
- 简单 CRUD
- 测试 / 工具脚本

**关键纪律**:**不要混用**。同一个调用链要么全响应式,要么全同步。混用会出现 `block()` 死锁。

### Reactor 反模式
- ❌ 在响应式链里调用 `.block()`(死锁源)
- ❌ 在 `subscribe` 里再 `subscribe`
- ❌ 用 `Mono.fromCallable` 包阻塞代码却不指定 `subscribeOn`

---

## 不可变与并发

- 优先 `record` 表示数据(任务、消息、事件)
- 集合用 `List.copyOf` / `Map.copyOf` 防止外部篡改
- 共享可变状态用 `ConcurrentHashMap` / `Atomic*`
- 任务状态机用 `compareAndSet` 实现状态迁移,避免锁

---

## 异常处理

### 异常体系
```java
public class AICompanyException extends RuntimeException { ... }

public class AdapterException extends AICompanyException { ... }
public class ChannelException extends AICompanyException { ... }
public class TaskException extends AICompanyException { ... }
```

### 全局错误处理(WebFlux)
```java
@RestControllerAdvice
public class GlobalExceptionHandler {
    @ExceptionHandler(AdapterException.class)
    public ResponseEntity<ErrorResponse> handleAdapter(...) { ... }
}
```

---

## 日志(SLF4J + Logback)

```java
private static final Logger log = LoggerFactory.getLogger(Orchestrator.class);

log.info("Task received: taskId={}, adapter={}", taskId, adapterName);
```

- 必须用占位符 `{}`,不要字符串拼接
- 必须带 traceId / taskId
- 用 MDC 在请求范围内携带 traceId

---

## 测试(JUnit 5 + Mockito + Testcontainers)

详见 [`06-testing-guide.md`](06-testing-guide.md)。

Java 特有:
- 单测用 JUnit 5 + Mockito
- 响应式测试用 `StepVerifier`
- 集成测试用 Testcontainers(避免依赖外部 DB)
- WebFlux 测试用 `WebTestClient`

---

## 构建与依赖

### Maven 推荐
- 多模块项目用父 POM 锁版本
- 用 `dependencyManagement` 管理传递依赖
- 用 `enforcer-plugin` 防止循环依赖

### 必装的检查插件
- `spotless`:格式化
- `checkstyle`:风格检查
- `spotbugs`:静态分析
- `jacoco`:覆盖率

---

## Spring AI 使用注意

### 模型抽象
用 Spring AI 的 `ChatModel` / `EmbeddingModel` 接口,不要直接调用 SDK,这样切换模型只改配置。

### Tool Calling
本项目可能把"任务派发到 Adapter"也封装成 Spring AI 的 Tool。设计时:
- Tool 必须粒度合适(参考 [`03-design-patterns.md`](03-design-patterns.md) 关于工具粒度)
- Tool 有副作用必须经过审批策略

### Sandbox
执行 AI 生成的代码必须有 Sandbox 隔离。**不可以直接 `Runtime.exec`**。

---

## 常见 Java 踩坑(预防性记录,实际踩到加 PITFALL 编号)

- `Optional` 不要做字段、不要序列化
- `Stream` 不要在 try-with-resources 外消费
- `LocalDateTime` 没时区,跨时区场景用 `Instant` 或 `ZonedDateTime`
- Jackson 默认序列化 `record` 没问题,但反序列化可能要 `@JsonCreator`
- `@Async` 必须开在 `@Configuration` 类(`@EnableAsync`),否则不生效
- WebFlux 不能直接用 `ThreadLocal`,要用 Reactor Context

---

## 参考 Wang 已有项目

`claw-code-java` 是 Wang 已经做过的 Spring AI + Claude Code runtime 复刻。本项目可以**复用其中的 Sandbox / Tool 路由 / Skill Registry 模式**,但要注意:
- 那个项目是单 AI 视角,本项目是多 AI 编排
- 需要在其基础上加一层 Adapter 抽象
