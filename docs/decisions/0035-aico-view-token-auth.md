# ADR-0035: aico-view token auth posture (V3)

**状态**:Accepted
**日期**:2026-05-31
**决策者**:Wang / Claude
**相关 Round**:Round 136
**相关文档**:[`docs/architecture/boss-first-grounding.md`](../architecture/boss-first-grounding.md) §3.3;ADR-0033

---

## 背景与问题

ADR-0033 把 aico-view 定为 read-only mobile web,V1/V2 默认绑 `127.0.0.1`,
本机 dev 无需鉴权。但 boss-first-grounding §3.3 的真实用例是"老板手机访问",
意味着必须能通过 ngrok / Cloudflare tunnel 暴露,这时无鉴权 = 任何拿到 URL 的人
都能看老板的全部 memory(包括 boss-scope)。

需要给 V3 一个简单但强制的鉴权:
- 本机 dev 仍然零摩擦
- 公网暴露时必须有 token
- 实现复杂度不能高于"加一个 dependency"

## 候选方案

### 方案 A — OAuth / OIDC(Cloudflare Access / Authentik)
- 优点:真正的"用户系统"。
- 缺点:重型;违反"单人 dogfood"产品边界;增加运维负担。
- 复杂度:高。
- ❌ 否决。

### 方案 B — HTTP Basic Auth
- 优点:浏览器内置 UI。
- 缺点:每次新设备都要输用户名密码;手机不友好;凭据进浏览器密码管理器后难撤销。
- 复杂度:低。
- ❌ 不选。

### 方案 C — 单 token via env(query or header)
- 优点:一个 env + 一个 query 参数,书签存好就行;撤销 = 改 env;实现 < 100 行。
- 缺点:URL 里带 token 会被浏览器历史记下,但这是单人 dogfood 工具,不是生产 SaaS。
- 复杂度:低。
- ✅ 选定。

## 决策

选择 **方案 C:`AICO_VIEW_TOKEN` env + `X-AICO-Token` header / `?token=` query**。

### 行为矩阵(写死,测试覆盖)

| `AICO_VIEW_TOKEN` | `AICO_VIEW_HOST` is loopback | 行为 |
|---|---|---|
| 已设 | 任意 | 所有受保护路由要求 token 匹配;不匹配 → 401 |
| 未设 | 是(127.* / localhost / ::1 / 空 / 0.0.0.0) | 所有受保护路由 **放行**(本机 dev) |
| 未设 | 否(非 loopback) | 所有受保护路由 **全部返回 401**(refuse to expose unauth'd view) |

非 loopback 无 token 时启动会写一行 WARN 日志,提醒用户设 token。

### 路由保护范围

✅ 受保护:`/`、`/trace/{id}`、`/memory`
❌ 不保护:`/healthz`(liveness probe);`/static/style.css`(无敏感数据)

理由:health 探针应该可以无鉴权(给 tunnel 上游用);CSS 是公开样式,无信息泄露。

### 实现选型

- 使用 `secrets.compare_digest` 做 token 比较,避免 timing attack。
- 没有 session、没有 cookie、没有 CSRF——纯 token,API 风格。
- 不挂 FastAPI Depends,而是在每个受保护路由内显式调 `guard.check(request)`。理由:
  健康检查和静态文件不要走 dependency 树,降低误配风险。

### 该 sprint 不做的事

- ❌ 多 token 多用户
- ❌ token 轮换 API(轮换 = 改 env + 重启,**这就够了**)
- ❌ Cloudflare Access 集成
- ❌ rate limit / brute force 检测(单人 dogfood 不需要)

## 结果

- 新增 `src/aico/view/auth.py`(< 90 行):`TokenGuard` + `is_loopback_host` + `TokenGuard.from_env`。
- `src/aico/view/app.py`:`build_view_app(..., token_guard=None)`;三个受保护路由调
  `guard.check(request)`;healthz 和 static 不调。
- 新增 `docs/human/aico-view-deploy.md`:三种部署形态(localhost / ngrok / Cloudflare)
  + 安全模型 + env 速查 + "不要做的事" 清单。
- 新增测试 `tests/unit/test_aico_view_auth.py`(17 用例):loopback 判定参数化、
  loopback 无 token 放行、非 loopback 无 token 全拒、header / query / 错 token、
  healthz 和 static 不被 token 保护、trace / memory 都被保护。

## 后续

- V3 完成后:Phase 8 dogfood 复盘(boss-first §3.5),决定 Phase 8 后续。
- 独立 sprint:Orchestrator 类拆分(B-005)。
- 未来:如果出现"多人共看"需求,再开 ADR 评估 Cloudflare Access / OIDC。当前不做。
