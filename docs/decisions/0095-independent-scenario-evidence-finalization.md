# ADR-0095: Independent Scenario Evidence Finalization

**状态**:Accepted
**日期**:2026-07-23
**决策者**:Wang / Codex(协作)
**相关 Round**:Round 262

---

## 背景与问题

ADR-0094的AICO runner可以证明不同Agent按frozen role顺序、共享预算、跨runtime消费checkpoint，但`role_chain_complete`只说明
模型角色完成了各自turn。它不能自行证明外部fixture没有漂移、审批前没有写入、进程真的重启、IM接管成本或无关大源未被消费。

若直接由被测AICO把自己的state映射为`BossAbsentTaskResult`，系统会同时扮演执行者和裁判；五项指标中的证据完整度与接手成本尤其容易
被自报数据污染。

## 候选方案

### 方案 A — role chain完成后自动标记task complete

- 优点：结果生成简单。
- 缺点：没有外部scenario、terminal、test、source、approval或IM证据，属于自证。

### 方案 B — 人工阅读日志后手写result

- 优点：无需新增机器合同。
- 缺点：不可重复、易漏样本，raw日志还可能泄露prompt、路径和身份。

### 方案 C — independent harness生成有界scenario receipt，再由纯finalizer绑定state与result

- 优点：执行者、观察者、scorer分离；所有事实可按SHA复核，且不保存raw prompt/log。
- 缺点：正式run仍需实现真正独立的harness collector，而不能用unit-test fixture冒充。

## 决策

选择 **方案 C**：

1. scenario receipt必须绑定contract SHA、task id、完整role-state SHA、observer build和event transcript SHA，observer kind固定为
   `independent_harness`。
2. terminal必须消费最后一个role artifact；role order、distinct agent、checkpoint chain和总provider usage再次由finalizer复核。
3. budget receipt必须present，否则usage不可作为正式result；超contract usage拒绝封口。
4. restart task要求独立restart SHA、exact一次runtime generation变化、不同runtime instance且`replayed_dispatches=0`。
5. approval task要求exact一次request/grant、审批前零mutation、一个human intervention和approval SHA。
6. evidence-drift task要求injected/detected且未发布stale result；budget-pressure要求irrelevant source已暴露但未消费、引用全在allowlist。
7. IM takeover task要求action/seconds/evidence三元组完整；不要求takeover的task禁止夹带takeover claim。
8. `aico-benchmark finalize-aico`只做bounded JSON读取、identity/scenario校验和fresh output写入；它不调用模型，也不修改原state。

## 当前证据

- 五类frozen scenario都能用同一finalizer生成schema-valid AICO result，role checkpoints链接到下一role或terminal。
- negative tests覆盖restart replay/同runtime、stale drift、approval前mutation/额外人工介入、irrelevant source consumption、
  budget receipt缺失和terminal未消费final checkpoint。
- CLI把task set SHA、state task identity和scenario receipt绑定到一个fresh result文件，重复输出路径拒绝覆盖。

## 残余边界

- 当前scenario receipt来自unit-test independent fake，尚未连接真实fault injector、filesystem observer、approval fence、Telegram observer。
- `observer_kind`是schema边界，不是远程证明；正式collector build和event transcript必须在isolated run中由harness实际生成。
- finalizer生成结果不代表AICO获胜；仍须两侧全部task结果进入同一scorer。

## 相关链接

- `src/aico/app/boss_absent_aico_evidence.py`
- `src/aico/app/boss_absent_benchmark_cli.py`
- `tests/unit/test_boss_absent_aico_evidence.py`
- ADR-0091
- ADR-0094
