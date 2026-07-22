# Goal Brief: Strict Absence Install Admission

## Goal

阻止operator在明确选择“老板即将离开”的部署模式后，仍把缺少关键无人值守合同的AICO安装成常驻服务。

## Problem

当前install只拒绝FAIL，而四个absence关键能力关闭时均为WARN。WARN对开发模式合理，但无法表达生产dogfood门槛，容易形成
“plist已安装、进程会重启，所以无人公司已上线”的配置级false-green。

## Contract

- 配置键为`AICO_ABSENCE_ADMISSION_MODE`，只接受`optional`与`strict`，默认`optional`。
- optional不改变既有安装行为，但doctor/install必须显示关键合同未成为门禁。
- strict复用同一轮真实readiness结果，要求runtime alerts、external liveness、scheduled recovery和standing autonomy均为OK。
- strict额外要求scheduled disposable recovery drill启用；不要求自动retention，因为删除是独立破坏性授权。
- strict失败必须在任何launchctl命令前停止，并只输出固定合同名。
- strict成功仍明确“不认证外部证据”，不得出现commercial-ready、HA-ready、human-read或full-DR声称。

## Non-goals

- 不自动修改`.env`、安装LaunchAgent、部署receiver、创建备份目录、签发grant或调用provider。
- 不探测外部URL、不发送IM/webhook、不验证storage class或第二故障域。
- 不把开发默认改成strict，也不新建一套可能漂移的production checker。

## Acceptance

1. 默认配置保持可安装且显示optional WARN。
2. strict + 四类disabled合同必须FAIL，runner零调用。
3. strict + 四类真实本地preflight OK + drill启用时admission为OK。
4. 非法mode FAIL且原值不出现在输出。
5. unit、Ruff、mypy、structure、full root/SME gate通过；文档明确外部证据边界。
