# 06 — 测试指南

> 本项目的测试纪律和分层。**没有测试的功能不予合并**。

---

## 测试金字塔

```
    /\        E2E 测试 (~5%)
   /  \       集成测试 (~25%)
  /────\      单元测试 (~70%)
```

**单测要多,集成要稳,E2E 要精**。

---

## 三层测试

### 单元测试(unit)
- **覆盖**:核心业务逻辑、工具函数、领域模型
- **隔离**:外部依赖全部 mock
- **速度**:整套跑完 < 30 秒
- **覆盖率目标**:核心模块 ≥ 80%

### 集成测试(integration)
- **覆盖**:Adapter 与真实 AI CLI 的对接、Channel 与真实 IM API 的对接
- **隔离**:用 Testcontainers / 本地容器化依赖
- **速度**:整套跑完 < 5 分钟
- **要求**:每个 Adapter / Channel 至少 1 个集成测试

### 端到端测试(e2e)
- **覆盖**:完整链路 "IM 输入 → 编排 → AI → IM 输出"
- **环境**:模拟环境或 staging
- **速度**:不限制,但每条不超过 2 分钟
- **要求**:每个 Phase 验收时至少 1 条新增 e2e

---

## 测试命名

### Java(JUnit 5)
```java
@Test
void receiveTask_shouldRouteToCorrectAdapter_whenPersonaMatches() { ... }
```

格式:`方法名_期望行为_前置条件`

### Python(pytest)
```python
def test_receive_task_routes_to_correct_adapter_when_persona_matches(): ...
```

格式:`test_方法_期望行为_前置条件`

---

## Mock 与 Stub

### 何时 mock
- 外部 AI CLI(每次调真的太慢、太贵、不稳定)
- 外部 IM API(同上)
- 数据库(用内存替身或 Testcontainers)
- 时间(用 fake clock,不要真等)

### 不要 mock 的对象
- ❌ 自己代码里的值对象、工具函数
- ❌ 标准库
- ❌ 简单 collections

### 测试替身的层次
1. **Stub**:返回固定值
2. **Mock**:验证调用
3. **Fake**:轻量功能实现(如内存版 Repository)

**优先用 Fake 而不是 Mock**——Fake 让测试更稳健,Mock 太多会和实现绑死。

---

## Adapter / Channel 的测试要求

### Adapter 必须有
- ✅ 接收任务 → 派发 → 返回 ack 的单测(mock CLI)
- ✅ 流式输出读取的单测(用 fake stream)
- ✅ 异常路径单测(CLI crash / 超时 / 空输出)
- ✅ 一个集成测试(用真实 CLI 跑一个 hello world)

### Channel 必须有
- ✅ 接收消息 → 解析 → 转 Task 的单测(mock IM SDK)
- ✅ 推送结果 → 调 IM API 的单测
- ✅ 流式更新(消息编辑)的单测
- ✅ 一个集成测试(用 Bot Token 跑通发收)

### 反模式
- ❌ 测试只跑 happy path,没异常分支
- ❌ 测试 Adapter 时把整个 Spring Context 起起来(用切片测试或纯 POJO 测试)
- ❌ 测试间共享可变状态导致顺序依赖

---

## 流式输出测试

### Java(StepVerifier)
```java
StepVerifier.create(adapter.streamOutput(taskId))
    .expectNext(new TaskOutput("Hello"))
    .expectNext(new TaskOutput(" World"))
    .verifyComplete();
```

### Python(async generator)
```python
async def test_stream():
    outputs = []
    async for o in adapter.stream_output(task_id):
        outputs.append(o)
    assert outputs == [...]
```

---

## 测试数据管理

### Builder 模式
```java
Task task = aTask()
    .withPersona(PersonaId.of("oldZhang"))
    .withPayload("Refactor this")
    .build();
```

### Fixture
- Java:`@BeforeEach` 但避免共享可变状态
- Python:`@pytest.fixture` 用 `scope="function"` 默认

### 黄金文件(golden file)
对于复杂输出验证,可以用快照测试:
```python
def test_render_persona_prompt(snapshot):
    output = persona.render_prompt(task)
    snapshot.assert_match(output, "old_zhang_prompt.txt")
```

---

## 覆盖率与质量

### 覆盖率不是目标,只是指标
- 不要为了凑覆盖率写测无意义代码
- 关注**变更点的覆盖率**,不是全局百分比
- 关注**分支覆盖**而不只是行覆盖

### 测试质量自检
- 改动一行业务代码,有测试会挂吗?
- 删掉一行业务代码,有测试会挂吗?
- 测试名字本身能描述功能吗?

如果三问都能答"是",这是好测试。

---

## CI 中的测试

```yaml
# 伪 CI 流程
- 单元测试: 必跑,失败阻断
- 集成测试: 必跑,失败阻断
- E2E 测试: PR 跑可选,合并到主干必跑
- 覆盖率: 低于阈值阻断
- 静态分析(spotbugs / mypy): 失败阻断
```

详见 [`07-deployment-guide.md`](07-deployment-guide.md)。

---

## 项目特有测试场景

### 测试 Persona 行为差异
不同 Persona 对同一任务应有可预测的行为差异。
**做法**:Snapshot 测试 prompt 渲染结果。

### 测试审批流
危险操作必须触发审批策略。
**做法**:用 `ApprovalPolicy` 的 fake 实现验证调用次数和参数。

### 测试可中断性
长任务必须能在 N 秒内响应中断信号。
**做法**:启动任务 → 发送中断 → 验证 5 秒内 task status 变 `INTERRUPTED`。

### 测试可观测性
关键事件必须发到 EventBus。
**做法**:订阅 EventBus,验证事件类型和顺序。
