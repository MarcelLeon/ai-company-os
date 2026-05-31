# ADR-0033: aico-view read-only mobile web surface (V1)

**状态**:Accepted
**日期**:2026-05-31
**决策者**:Wang / Claude
**相关 Round**:Round 133
**相关文档**:[`docs/architecture/boss-first-grounding.md`](../architecture/boss-first-grounding.md) §3.3

---

## 背景与问题

`boss-first-grounding.md` §3.3 论证:trace / timeline / memory tree 在 IM 文本框里**注定糊**;堆 ID 是治标。一次老板 dogfood 已经明确这一点。

但纯 IM 又是 NORTH_STAR 第一句"无论身处何地"的硬约束:不能让老板必须坐到 Mac 前才能看 trace。

解法是 §3.3 提出的"写在 IM、看在 Web"分工:write surface 是 Telegram/Feishu;view surface 是手机浏览器打开的 aico-view。

## 候选方案

### 方案 A — Desktop GUI(Electron / 原生)
- 优点:体验顺滑。
- 缺点:**完全破坏** absence-first(老板不在 Mac 就用不了);维护成本巨大。
- 复杂度:极高。
- ❌ 否决。

### 方案 B — Web GUI 走 SPA(React / Vue)
- 优点:UI 灵活。
- 缺点:本机构件 + 前端构建 + bundler 全部上场,违反 "no early abstraction";老板手机网络环境下 SPA 首屏不友好。
- 复杂度:高。
- ❌ 否决(本 sprint)。

### 方案 C — 一个 FastAPI 进程 + 服务端渲染 HTML + 一份 CSS
- 优点:**无前端构建**,无 JS framework,mobile-first,首屏快;一个进程 + 一组 GET 路由 + 一个 CSS;easy to dogfood on the phone today。
- 缺点:UI 简陋;无 SPA 的交互。
- 复杂度:低。
- ✅ 选定。

## 决策

选择 **方案 C:FastAPI + 服务端 HTML + 一份 CSS**。

### 关键边界

1. **Read-only**。所有路由都是 GET;FastAPI 自动 405 任何 POST/PUT/PATCH/DELETE(测试覆盖)。写操作回 IM。
2. **不启动 Phase 1 runtime**。aico-view 是独立进程,只**打开**与 orchestrator 共用的 JSONL/SQLite,**不挂 channel / adapter / EventBus**。即使 view 进程 crash,orchestrator 不受影响。
3. **直接使用 UnifiedEventIndex**(ADR-0030)。Timeline / Task Trace 视图都从 InMemoryUnifiedEventIndex 取数据;不重新发明索引。
4. **三个视图,不更多**:Timeline、Task Trace、Memory Tree。其他视图(`/agents`、`/projects`)留作未来评估,本 sprint 不做以避免范围蔓延。
5. **无 JS framework,无 Jinja2**。f-string + html.escape 直接生成 HTML;视图代码留在 `src/aico/view/app.py` 一文件 < 300 行。新增依赖为 0(FastAPI/uvicorn 项目已有)。
6. **每次请求重建 index**。性能可接受(JSONL 解析非常快),实现简单;避免缓存失效问题。如未来数据规模大可加 mtime cache。
7. **本 sprint 无鉴权**。绑定 `127.0.0.1`,默认只在本机访问。任何对外暴露(ngrok / Cloudflare tunnel)留 V3 加 token 鉴权。

### 该 sprint 不做的事(明确范围边界)

- ❌ IM deep link 跳回 Telegram 预填命令(留 V2)
- ❌ Token 鉴权 / 隧道部署文档(留 V3)
- ❌ `/agents` `/projects` `/inbox` 视图复刻
- ❌ JS framework / 客户端路由 / 实时 push

## 结果

- 新增 `src/aico/view/__init__.py` + `src/aico/view/app.py`(< 300 行)。
- 新增 `src/aico/app/view_cli.py` 启动入口(uvicorn + env-based settings)。
- 新增 `pyproject.toml` `[project.scripts]` 中的 `aico-view = "aico.app.view_cli:main"`。
- 启动方式:
  ```bash
  AICO_AUDIT_LOG_PATH=/tmp/aico-audit.jsonl \
  AICO_MEMORY_PATH=/tmp/aico-memory.jsonl \
  AICO_STATE_DB_PATH=/tmp/aico-state.db \
  AICO_VIEW_PROJECT_IDS=aico \
  uv run aico-view
  # 默认 http://127.0.0.1:8765
  ```
- 视图清单:
  - `GET /healthz` — JSON health probe
  - `GET /` — Timeline(最近 100 条事件,倒序;每条事件的 short_id 是 trace 链接)
  - `GET /trace/{trace_id}` — Task Trace(单 trace 全部事件,oldest first)
  - `GET /memory` — Memory Tree(experience 在前 / fact 在后;archived 灰显)
  - `GET /static/style.css` — 内嵌单 CSS(暗色 mobile-first)
- 测试覆盖 `tests/unit/test_aico_view_routes.py`(12 用例):healthz / timeline 渲染 / trace 渲染 / 404 / memory 渲染 / **所有路由 405 拒绝写方法** / CSS 服务 / GET-only 参数化。

## 后续相关 ADR / Sprint

- V2 sprint:Telegram `tg://resolve?...&text=` deep link 跳回 IM 预填命令;Feishu 暂用文本提示降级。
- V3 sprint:`AICO_VIEW_TOKEN` 强制鉴权 + 部署文档(localhost / ngrok / Cloudflare tunnel)+ 安全模型说明。
- 远期:`/agents`、`/projects`、`/inbox` 等额外视图按 dogfood 反馈再加。
