# 05 — Python 开发最佳实践

> 本文针对本项目中可能采用 Python 的部分(可能用于 AI Adapter 层、脚本工具、或核心)。

---

## 版本与基线

- **Python**:3.11+
- **包管理**:`uv`(优先)或 `poetry`
- **格式化**:`ruff format` + `ruff check`
- **类型检查**:`mypy --strict`(对核心模块)

---

## 项目结构

```
src/aico/
├── core/              # 编排核心
│   ├── orchestrator.py
│   ├── task.py
│   ├── persona.py
│   └── events.py
├── adapter/           # AI 适配器
│   ├── base.py        # AIAdapter Protocol
│   ├── claudecode.py
│   ├── codex.py
│   └── openclaw.py
├── channel/           # IM 通道
│   ├── base.py
│   ├── telegram.py
│   └── feishu.py
├── persistence/
├── policy/
└── infra/
tests/
├── unit/
├── integration/
└── e2e/
```

---

## 类型注解(强制)

### 全部代码必须有类型注解
- 所有函数签名
- 所有类属性
- 所有公共变量

```python
# ✅ 对
def receive_task(self, task: Task) -> TaskAck:
    ...

# ❌ 错(没有类型)
def receive_task(self, task):
    ...
```

### 用 Protocol 定义接口
Python 不是 Java,**优先用 `typing.Protocol` 而不是抽象基类**:

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class AIAdapter(Protocol):
    name: str

    async def receive_task(self, task: Task) -> TaskAck: ...
    async def stream_output(self, task_id: TaskId) -> AsyncIterator[TaskOutput]: ...
    def status(self) -> AdapterStatus: ...
```

### 不可变数据用 Pydantic / frozen dataclass

```python
from pydantic import BaseModel, ConfigDict

class Task(BaseModel):
    model_config = ConfigDict(frozen=True)

    task_id: TaskId
    payload: str
    persona: PersonaId
```

---

## 异步优先

本项目大量场景是 IO 密集(IM 长轮询、AI 流式输出),**默认用 asyncio**。

### 何时用 async
- IM Bot 接收消息
- AI Adapter 流式输出
- HTTP 调用、数据库访问

### 何时用同步
- CPU 密集计算
- 启动配置加载
- 测试工具

### asyncio 反模式
- ❌ 在 async 函数里调用阻塞库(`requests.get`)→ 用 `httpx` / `aiohttp`
- ❌ 用 `time.sleep` → 用 `asyncio.sleep`
- ❌ 在协程里 `loop.run_until_complete` → 用 `await`
- ❌ 全局共享可变状态不加锁

---

## 依赖注入

Python 没有 Spring,但仍要做依赖注入。两种推荐做法:

### A. 构造器注入(简单场景)
```python
class Orchestrator:
    def __init__(
        self,
        adapters: list[AIAdapter],
        event_bus: EventBus,
    ) -> None:
        self._adapters = adapters
        self._event_bus = event_bus
```

### B. 容器注入(复杂场景)
用 `dependency-injector` 或 `punq` 做容器,不要全局变量。

**反模式**:全局 `orchestrator = Orchestrator(...)` 模块级单例 → 测试痛苦。

---

## 配置管理

### 用 pydantic-settings

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class TelegramSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AICO_TELEGRAM_",
        env_file=".env",
    )
    bot_token: str
    webhook_url: str
    poll_interval_seconds: int = 30
```

### 不要做
- ❌ `os.getenv(...)` 散落各处
- ❌ 配置写在代码字符串里
- ❌ 把 secret commit 进 git

---

## 错误处理

### 异常体系
```python
class AICompanyError(Exception): ...
class AdapterError(AICompanyError): ...
class ChannelError(AICompanyError): ...
class TaskError(AICompanyError): ...
```

### 不要做的事
- ❌ `except: pass` 静默吞异常
- ❌ `except Exception as e: print(e)` → 用 logger
- ❌ 用异常代替返回值(状态判断不该靠抛异常)

### 重试用现成库
用 `tenacity` 做重试装饰器,不要手撸:

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential())
async def call_telegram_api(...): ...
```

---

## 日志

```python
import logging
log = logging.getLogger(__name__)

log.info("Task received: task_id=%s adapter=%s", task_id, adapter_name)
```

- 用 `logging.getLogger(__name__)` 不要全局 `logging.info`
- 用占位符 `%s` 不要 f-string(因为 f-string 会先求值,即使日志级别没开)
- 配置走 `logging.config.dictConfig` 集中管理

---

## 测试(pytest + pytest-asyncio)

详见 [`06-testing-guide.md`](06-testing-guide.md)。

Python 特有:
- 用 `pytest` 不用 `unittest`
- 异步测试用 `pytest-asyncio`(标记 `@pytest.mark.asyncio`)
- Mock 用 `unittest.mock` 的 `AsyncMock`(异步函数必须用这个,不能用普通 `Mock`)
- 用 `pytest-cov` 算覆盖率
- 用 fixture 而不是 setUp/tearDown

---

## 包管理与构建

### pyproject.toml(用 uv 时)
```toml
[project]
name = "aico"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "pydantic>=2.0",
    "httpx>=0.27",
    "fastapi>=0.110",
]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.mypy]
strict = true
```

### 必跑的检查
```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src/
uv run pytest --cov=src
```

CI 任何一项不过,PR 不准合。

---

## 常见 Python 踩坑(预防性记录)

- 默认参数是可变对象 → `def f(x=[])` ❌ → `def f(x=None): x = x or []` ✅
- 闭包捕获变量是引用不是值 → 循环里建 lambda 要用默认参数固化
- `asyncio.gather` 异常处理:一个 task 失败其他不会取消,要用 `return_exceptions=True` 或 `TaskGroup`
- Pydantic v1 vs v2 行为差异巨大,本项目用 v2
- `dataclass(frozen=True)` 哈希要 `eq=True` 配合
- Python 3.11+ 才有 `tomllib`,旧版要 `tomli`

---

## 何时选 Python

如果技术栈选型最终走向 Python,理由通常是:
- AI 生态成熟(LLM SDK、向量库、Agent 框架)
- 各 AI CLI 大多 Python 实现,Adapter 直接走库内调用而非 subprocess

如果选 Python,主要痛点:
- Wang 的 Java 经验复用低
- 多核并发能力弱(GIL),本项目 IO 密集影响小
- 类型系统比 Java 弱,需要纪律保证(`mypy --strict`)

具体取舍由 ADR-001 决定。
