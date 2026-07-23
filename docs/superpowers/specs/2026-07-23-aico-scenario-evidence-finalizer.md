# Goal Brief: AICO Scenario Evidence Finalizer

## Goal

把AICO managed role state与独立harness观察到的五类scenario事实绑定成唯一、可评分、owner-safe的task result，禁止执行系统自证完成。

## Acceptance

- receipt绑定contract/task/state/observer/event transcript SHA，不含raw prompt、path、identity或log。
- finalizer再次验证role order、distinct agents、checkpoint consumption、terminal consumption与shared provider usage。
- restart、approval、evidence drift、budget pressure和IM takeover分别有严格机器条件。
- 缺budget receipt、发生provider replay、审批前mutation、发布stale result或消费无关源都fail closed。
- CLI只接受frozen task set里的state task，并以fresh-file语义输出schema-valid AICO result。
- 单测覆盖五类正例和关键负例；不调用模型或IM。

## Stop Conditions

- 不把role-chain completion当terminal task completion。
- 不接受被测系统自报的scenario事实替代independent harness。
- 不把unit-test fake receipt写成正式成绩。
- 没有两侧完整result前不宣称胜出。

## Evidence

- ADR-0095记录执行者、观察者、scorer三层分离。
- `finalize-aico`提供可执行的no-model artifact入口。
- 37条AICO evidence/runner/benchmark定向测试通过。
