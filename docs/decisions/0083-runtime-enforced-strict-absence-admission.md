# ADR-0083: Runtime-Enforced Strict Absence Admission

**状态**:Accepted
**日期**:2026-07-22
**决策者**:Codex
**相关 Round**:Round 245
**Extends**:ADR-0082

## 背景

ADR-0082让`aico-service install`在strict机器合同缺失时拒绝launchctl，但LaunchAgent之后的异常重启直接执行`aico-phase1`或
`aico-feishu-webhook`。`Phase1Settings(extra="ignore")`没有声明admission字段，因此dotenv里的strict在runtime入口被静默丢弃。
安装后配置漂移或灾后恢复可关闭alert/liveness/recovery/standing合同，进程仍会自动启动，形成“安装时strict、运行时optional”的绕过。

## 候选方案

- 只要求每次改配置后重跑install：否决；LaunchAgent自动重启和老板缺席场景不能依赖人工纪律。
- 把admission写进plist参数：否决；会产生双配置源，dotenv漂移仍无法约束真实runtime。
- runtime启动后只报health FAILED：否决；缺失第二通知/死信号时可能无人观察，且业务入口已开始接活。
- runtime显式加载同一mode，在构造Channel/state前fail closed：采用。

## 决策

1. 抽出纯函数`strict_absence_contract_gaps`和固定合同名，service/install与Phase1 settings共同使用；不复制两套名称/聚合顺序。
2. `Phase1Settings`显式声明`absence_admission_mode: optional|strict`。strict要求alert URL、liveness enabled、recovery backup + drill和
   standing grant path存在；既有validators继续验证HTTPS、durable state、TTL、recovery完整性等细节。
3. `build_phase1_runtime`在构造Channel、audit/state store或owner lock前调用`preflight_absence_admission`，复用真实standing routing和
   recovery destination preflight。外部binding漂移时不启动Channel、不调用provider、不创建state/audit。
4. Telegram与Feishu生产入口统一经`load_phase1_settings`加载。Pydantic原始ValidationError可能包含dotenv input，入口只抛通用
   `AICO configuration validation failed; run aico-service doctor`，不把token/URL/target写入stderr。
5. optional仍保持当前开发语义；runtime fail-closed不证明外部endpoint、provider、storage或human read。

## 后果

- strict成为跨install、异常重启和Channel入口持续生效的部署意图，不能被BaseSettings extra-ignore静默绕过。
- 配置漂移会让LaunchAgent保持失败/重试而非以宽松模式接活；operator通过secret-safe doctor修复配置。
- 真实外部dogfood与freshness attestation仍由B-010至B-014跟踪，本决策不把startup成功写成commercial readiness。

## 相关链接

- ROUNDS Round 245
- PITFALLS P-101
- Goal Brief `docs/superpowers/specs/2026-07-22-runtime-enforced-strict-absence-admission.md`
- 相关代码:`src/aico/app/absence_admission.py`,`src/aico/app/phase1.py`,`src/aico/app/service_cli.py`
