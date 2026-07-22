# Goal Brief: Runtime-Enforced Strict Absence Admission

## Goal

让owner选择的strict absence意图在install之后的每次Telegram/Feishu runtime启动中继续fail closed，不能被dotenv解析或LaunchAgent
自动重启绕过。

## Contract

- service CLI与runtime共享固定的critical contract names和gap aggregation。
- Phase1Settings必须显式读取`AICO_ABSENCE_ADMISSION_MODE`；unknown value拒绝解析，strict缺项拒绝构造settings。
- strict runtime要求alerts、liveness、recovery backup + drill、standing grant均启用，并继续经过既有细节validators。
- build runtime第一步复用standing routing和recovery destination的production preflight；失败前不构造Channel/state/audit。
- Telegram与Feishu真实entrypoint不得原样输出Pydantic validation input；只给secret-safe doctor指引。
- optional保持兼容；任何OK仍不认证external ACK、off-device、provider delivery或human read。

## Acceptance

1. 只在`.env`写strict且缺合同时，production loader必须失败，证明字段未被extra-ignore。
2. 每个critical enable flag/path单独漂移都被固定合同名拒绝。
3. standing外部文件漂移在runtime construction前失败，state/audit文件未创建。
4. raw dotenv token不出现在production loader错误中。
5. service/Phase/Feishu targeted、full root/SME、Ruff/mypy/format/structure、JSON/Compose/wheel/diff全部通过。

## Non-goals

- 不让runtime启动时联网探测外部endpoint，不自动修复配置或安装服务。
- 不改变retention、restore、provider replay、grant签发或业务执行authority。
- 不把runtime startup gate称为商业认证或真实无人公司上线。
