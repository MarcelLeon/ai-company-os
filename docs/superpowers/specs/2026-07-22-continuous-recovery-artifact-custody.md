# Continuous Recovery Artifact Custody — Goal Brief

**Round**:235
**Status**:Implemented
**Goal**:让boss-absent runtime持续证明最近verified recovery artifact仍存在、未漂移且目标身份连续，而不是只相信创建时receipt。

## Problem

创建时deep verify通过后，外部盘仍可能掉线、目录被替换、artifact/sidecar被删除或修改、权限被放宽。旧health只看SQLite
VERIFIED和年龄，会在下一次capture前错误显示OK；对个人公司而言，这会把不可恢复状态隐藏到真正事故发生时。

## Contract

- receipt绑定不泄露raw storage信息的destination fingerprint SHA；同一output binding后续capture必须保持identity连续。
- 独立custody interval在后台thread复验latest artifact/sidecar权限、receipt SHA、artifact SHA和完整recovery-set内容。
- 每次成功/失败持久化custody status、checked time和bounded failure count；state schema v9，CLI不输出destination fingerprint。
- heartbeat即时拒绝missing/unsafe/identity drift，并在custody FAILED或age超过max时保持FAILED；deep verify不阻塞heartbeat。
- backup cadence与custody cadence独立；改变cadence不重置binding。异常不触发restore、delete、mkdir或自动storage rebind。

## Acceptance Evidence

- 正常周期复验会推进custody checked time并保持failure=0。
- 删除artifact、修改字节、替换目录、放宽权限和custody stale分别使durable custody/required health失败。
- 目录替换后到达下一backup窗口也不能capture新artifact建立假基线；原capture count不增加。
- state CLI只显示custody状态、时间、次数和既有SHA，不显示目录指纹、路径、config/project/provider。
- Phase1/service config支持独立custody cadence/max age；doctor仍明确storage class未被attest。

## Stop Conditions

- kernel-visible directory identity不是volume UUID、provider签名、encryption或off-device证明。
- 本轮不配置真实目标、不生成真实artifact、不安装服务、不调用IM/provider；不能声称真实RPO/RTO或commercial DR。
- custody失败只告警和阻断健康声明；自动restore/delete/rebind继续禁止。
