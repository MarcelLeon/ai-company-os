# ADR-0082: Strict Absence Install Admission

**状态**:Accepted
**日期**:2026-07-22
**决策者**:Codex
**相关 Round**:Round 244

## 背景

`aico-service install`原先只拒绝readiness中的`FAIL`。runtime alerts、external liveness、scheduled recovery和standing
autonomy在关闭时都只产生`WARN`，因此一个适合本地开发的配置也能被安装为常驻服务。进程在线不等于无人公司在线；若operator
误把安装成功当成absence-ready，老板离开后才会发现告警、死信号、恢复演练或主动工作合同从未建立。

## 候选方案

- 所有安装默认要求全部absence合同：否决；会破坏最小开发与交互式dogfood入口，也把外部基础设施强加给每次本地启动。
- 把四个disabled状态直接改成`FAIL`：否决；丢失“功能可选”和“生产准入”的层级差异。
- 新建一套独立production检查器：否决；容易与真实`readiness_checks`漂移，重演P-070的looser shadow policy。
- 在同一readiness图上增加显式strict admission聚合门禁：采用。

## 决策

1. 新增`AICO_ABSENCE_ADMISSION_MODE=optional|strict`，默认`optional`。默认模式保持开发兼容，同时明确WARN“关键absence合同不是
   install gate”。非法值fail closed且不回显原值。
2. `strict`复用同一次`readiness_checks`中`runtime alerts`、`runtime liveness`、`recovery backup`和`standing autonomy`的真实结果；
   任一非OK都使`absence admission`为FAIL，`install`不得调用launchctl。
3. strict另要求`AICO_RECOVERY_DRILL_ENABLED=true`。仅配置capture/custody仍不能证明production materializer曾被周期性锻炼；
   retention保持独立破坏性授权，不作为准入条件。
4. 输出只列固定合同名，不显示URL、token、target、path、grant identity或非法配置值。
5. strict成功只声明`machine contracts configured; external evidence not attested`。它不证明receiver/provider独立、外部endpoint ACK、
   off-device存储、真实IM投递、human read、业务RPO/RTO或commercial readiness。

## 后果

- owner可把“准备安装本地进程”和“准备让老板离开”设为两个清晰门槛，避免WARN堆叠被忽略。
- 现有开发者无需部署外部receiver即可继续安装；商用dogfood必须显式opt-in strict并补齐机器合同。
- 外部真实性仍由B-010/B-011/B-012/B-013/B-014的真实样本关闭，不能由本门禁自动解决。

## 相关链接

- ROUNDS Round 244
- PITFALLS P-100
- Goal Brief `docs/superpowers/specs/2026-07-22-strict-absence-install-admission.md`
- 相关代码:`src/aico/app/service_cli.py`,`tests/unit/test_service_cli.py`
