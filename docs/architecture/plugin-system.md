# Plugin System — 插件化机制

> 本文说明本项目的可插拔机制。**核心思想:核心代码不应包含任何具体 AI / IM / 策略名字**。

---

## 可插拔的层

```
┌─────────────────────────────────────┐
│           核心代码(只依赖接口)        │
└─────────────────────────────────────┘
              ↑ 通过注册表加载 ↑
┌─────────────────────────────────────┐
│  插件层(实现接口)                    │
│                                      │
│  AI Adapter:  Claude Code / Codex /  │
│               OpenClaw / 内部 CLI /  │
│                                      │
│  IM Channel:  Telegram / 飞书 /      │
│               QQ / Slack /          │
│                                      │
│  Persona Strategy:  老张 / 小李 /     │
│                     默认人设 /       │
│                                      │
│  Approval Policy:  自动通过 /        │
│                    阈值审批 /        │
│                    人工必审 /        │
│                                      │
│  Memory Backend:  内存 / SQLite /    │
│                   Postgres /        │
└─────────────────────────────────────┘
```

---

## 插件加载机制

### 启动时
1. 读取配置文件 `application.yml` / `aico.yaml`
2. 配置文件声明启用的插件:
   ```yaml
   aico:
     adapters:
       - name: claude-code
         class: com.aico.adapter.claudecode.ClaudeCodeAdapter
         config:
           cli_path: /usr/local/bin/claude
       - name: codex
         class: com.aico.adapter.codex.CodexAdapter
         config: ...

     channels:
       - name: telegram
         class: com.aico.channel.telegram.TelegramChannel
         config:
           bot_token: ${TELEGRAM_BOT_TOKEN}
   ```
3. 注册表(`AdapterRegistry`、`ChannelRegistry`)按配置加载

### 运行时增删
- Phase 5+ 支持运行时增删插件(无需重启)
- 通过 IM 命令"/admin add adapter codex"等

### 加载顺序
1. 配置加载
2. 基础设施(EventBus、Persistence)
3. Memory Backend(Adapter 启动可能需要)
4. Adapter 注册
5. Persona / Approval 策略加载
6. Channel 启动(最后启动,确保后端就绪才接收消息)

---

## 插件契约

每个插件类型必须满足:

### 1. 实现对应接口
没什么好说的,这是基础。

### 2. 必须有 0 参构造或仅依赖配置对象的构造
插件加载机制不应该需要复杂的依赖注入。
- Java:用 `@Component` + `@ConfigurationProperties`
- Python:用 `__init__(self, config: Settings)`

### 3. 自描述
每个插件必须能够回答:
- 我是什么(name)
- 我能干什么(capabilities)
- 我现在状态如何(status / health)

### 4. 优雅关闭
每个插件必须实现:
- `start()`(初始化资源)
- `stop()`(释放资源,等待进行中的任务完成或中断)

### 5. 不能修改核心
插件不允许:
- 反射改核心的 final 字段
- 引入新的核心依赖
- 持有核心组件的强引用并跨生命周期使用

---

## 插件作者指南

### 新建一个 Adapter 插件
1. 在 `adapter/` 下新建一个子模块/包
2. 实现 `AIAdapter` 接口
3. 提供配置类
4. 写单测(必须)
5. 写一个集成测试(必须)
6. 在 `application.yml.example` 加示例配置
7. 在 README 加一段说明
8. 提 PR

### 新建一个 Channel 插件
同上,在 `channel/` 下。

### 新建一个 Persona 策略
同上,在 `policy/persona/` 下。
- 注意:Persona 大多数情况下**不需要写代码**,只需要 YAML 配置(prompt 模板 + 行为参数)。
- 仅当现有策略类型不够用时才写新策略类。

---

## 配置约定

### 命名规范
- 插件名用 kebab-case:`claude-code`、`telegram`
- 配置 key 用 snake_case:`bot_token`、`cli_path`
- 环境变量用大写下划线:`AICO_TELEGRAM_BOT_TOKEN`

### 配置层级
```
默认值(代码内)
    ↑
应用配置(application.yml)
    ↑
环境特定配置(application-{env}.yml)
    ↑
环境变量(优先级最高)
```

### Secret 处理
所有 secret 走环境变量,不进配置文件:
```yaml
bot_token: ${TELEGRAM_BOT_TOKEN}  # ✅ 引用环境变量
# bot_token: "12345:abc..."         # ❌ 硬编码
```

---

## 未来扩展点

这些是 Phase 6+ 才考虑的可插拔点,**Phase 1-5 不需要为它们设计**:

- **Memory Backend**:跨 AI 的共享记忆(向量库 / 关系库 / 文件)
- **Sandbox Strategy**:执行 AI 生成代码的沙箱(Docker / Firecracker / 仅本地)
- **Cost Tracker**:多模型/多 Provider 的成本归因
- **MCP Server Plugin**:把本系统也暴露成 MCP server,被其他 AI 调用

---

## 反插件化的反模式

❌ **核心硬编码 Adapter 名字**:
```java
if (adapter.name().equals("claude-code")) { ... special logic ... }
```

❌ **配置驱动行为分支爆炸**:
```yaml
behavior:
  if-claude-code-then: skip-approval
  if-codex-then: require-confirm
```
→ 这种分化逻辑应该用 Persona / Strategy 表达,不是塞配置。

❌ **插件之间互相直接依赖**:
- ClaudeCodeAdapter 直接 import TelegramChannel
- 应该通过 EventBus 或核心的接口间接交互

❌ **插件改核心代码**:
- 加新插件时改了 `core/` 包下的代码
- 这是"应该核心做但偷懒塞插件里"的反信号

如果你看到这些情况,**写到 PITFALLS,然后重构**。
