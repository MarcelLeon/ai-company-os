# Goal Brief: Live Provider Authentication Receipts

## Goal

在灾后恢复中把“provider配置存在”升级为“当前Claude/Codex凭据已被真实外部请求接受”的短时证据，同时不把
credential、prompt、challenge明文、provider输出、stderr或绝对路径写入恢复artifact和回执。

## Acceptance

- recovery-set固定记录当前runtime必须验收的provider canonical集合；adapter启停漂移会让reinjection验证fail closed。
- `provider-auth-receipt`先深验recovery set、exact checkout和reinjection receipt，再逐个运行真实provider probe。
- Claude probe关闭customization、tools、Chrome与session persistence；Codex probe忽略user config/rules、ephemeral、
  read-only sandbox且关闭experimental network。两者都在private empty cwd运行，并限制时长和stdout/stderr字节。
- 每个probe必须返回随机challenge的exact response、terminal success和provider-reported usage；缺一项不发布receipt。
- owner-only、atomic、new-path receipt绑定set SHA、reinjection receipt SHA、config revision、owner decision、provider集合及
  executable hash，30分钟过期；只记录challenge SHA，不记录challenge/prompt/output/error/credential。
- `verify-provider-auth`重验全部本地binding、独立receipt SHA和freshness，但明确不重放付费live probe。
- 未批准安全probe的provider fail closed；不得复用Cursor/CodeFlicker/Trae/Gemini现有yolo runtime参数。

## Non-goals

- 不在当前无`.env`/owner授权的checkout消费付费provider或制造真实外部样本。
- 不证明provider连续可用、模型质量、账号余额、credential identity、CLI binary provenance或owner密码学身份。
- 不把短时provider receipt写成full-business restore ready；off-device、receiver、IM、RPO/RTO仍需独立证据。
