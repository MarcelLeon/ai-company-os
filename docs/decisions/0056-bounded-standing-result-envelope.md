# ADR-0056: Bounded Standing Result Envelope

**状态**:Accepted
**日期**:2026-07-22
**决策者**:Codex / Round 218

## 背景

ADR-0055让standing结果具备结构和本地证据合同，但JSON Schema原先只有`minLength/minItems`。一个schema-compliant
结果仍可包含超长summary、海量source/list；schema被忽略时，raw final message还会完整进入Adapter output、
Orchestrator capture和validator。老板缺席时，这会把单个provider结果变成内存/SQLite膨胀入口。

结果总长也不能等同provider token cap：本地只能限制接收、解析和持久化，不可能追回已经生成的token成本。

## 决策

1. standing result总长固定最多32,768字符；Adapter与Orchestrator最多保留32,769字符，额外一位只用于让validator
   确定识别`result_too_large`。
2. 最多16个acceptance criteria、16个stop conditions、每个criterion最多8个source；gaps/risks/next actions各16项。
3. summary/evidence/list item最多2,000字符，repository-relative path最多512字符，identifier最多8字符。
4. source-controlled JSON Schema与Pydantic模型使用相同字段上限，并由测试逐字段核对，防止双份合同漂移。
5. `StandingCharterItem`在配置加载时同步限制criterion/stop数量和文本长度，拒绝永远无法满足的charter。
6. JSON语法错误记`invalid_json`；重复key或字段/数量越界记`result_schema_invalid`；总长越界记
   `result_too_large`。所有失败都只持久化bounded receipt并停止后续run。
7. raw preauthorized正文继续不进入老板IM或proposal；普通交互任务保持原输出行为。

## 否决方案

- **只相信provider output schema**：CLI/schema漂移或其他测试Adapter仍可能输出无界正文，总长也无法由字段schema精确限制。
- **超限后直接截成普通结果继续解析**：可能把不完整JSON或证据误判为业务结果；必须显式invalid并停授。
- **把限制做成owner grant可调参数**：这是runtime安全不变量，不应由单个授权放宽到不可控。
- **保存raw结果供人工排查**：会把资源放大和敏感正文带入durable state；现有task/audit恢复入口足够定位。
- **称为token/cost hard cap**：限制发生在provider生成后，只保护本地资源，不保护本次账单。

## 后果

### 正面

- schema被遵守或忽略时，本地result capture和proposal state都有确定上限。
- 配置、schema、runtime validation三层共享同一商业安全边界，错误原因仍可在老板面恢复。
- 普通任务与人工accepted proposal不被standing专属资源策略污染。

### 代价与剩余风险

- Codex JSONL整行在CLI/StreamReader解析阶段仍短暂存在；本轮限制从Adapter返回值开始，无法改变provider进程内部内存。
- 32K是固定产品合同，未来若真实charter需要更大结果，应提升证据附件协议，而不是无限放大正文。
- 本地bounded envelope仍不是真实provider/IM dogfood或单次成本证明；B-014保持。

## 验证

- 单测覆盖总长、字段长度、数组数量、重复JSON key、charter输入和schema/model常量一致性。
- Codex Adapter与Orchestrator E2E证明只保留上限+1、raw marker不进入IM、proposal序列化保持bounded。
- full root、SME、Ruff、mypy、结构、JSON、Compose、wheel与diff gate必须通过。
