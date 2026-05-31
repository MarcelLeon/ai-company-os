# aico-view 部署

`aico-view` 是一个独立的 read-only FastAPI 进程,把 orchestrator 写出的
JSONL/SQLite 渲染成手机友好的 Timeline / Task Trace / Memory Tree 三视图。
**所有写操作都回 IM**;view 自身永远是只读的(任何 POST/PUT/DELETE 都 405)。

本文给三种典型部署形态,以及为什么 V3 要求 token 鉴权。

---

## 安全模型(必读)

`aico-view` 不是公共服务。它要解决的是"老板在地铁/床上想看一眼项目状态"的场景。
能力边界:

- ✅ 适合:本机 dev、个人手机隧道、单人 dogfood。
- ❌ 不适合:团队共享、公网部署、多用户鉴权、长期生产暴露。

强制规则:

1. **若 `AICO_VIEW_HOST` 是 loopback**(127.* / localhost / ::1 / 空 / 0.0.0.0)
   且 `AICO_VIEW_TOKEN` 未设 → 允许无 token 访问(本机便利)。
2. **若 `AICO_VIEW_HOST` 是非 loopback** 且 `AICO_VIEW_TOKEN` 未设 → **所有请求都
   返回 401**。这是有意的:绑公网必须先设 token。
3. `AICO_VIEW_TOKEN` 设置后,请求必须带 `X-AICO-Token` header 或 `?token=` query。

这条规则在 `src/aico/view/auth.py:TokenGuard.from_env` 中强制执行。详见 ADR-0035。

---

## 形态 1:本机访问(最简)

适合:开发期、本机调试、不需要手机访问。

```bash
export AICO_AUDIT_LOG_PATH="/tmp/aico-audit.jsonl"
export AICO_MEMORY_PATH="/tmp/aico-memory.jsonl"
export AICO_STATE_DB_PATH="/tmp/aico-state.db"

uv run aico-view
# 浏览 http://127.0.0.1:8765
```

无 token,无隧道。仅本机 loopback 访问。

---

## 形态 2:手机访问(ngrok 隧道 + token)

适合:个人 dogfood,老板手机访问。

```bash
# 1. 生成一个随机 token(40 字符以上,只你自己知道)
export AICO_VIEW_TOKEN="$(openssl rand -hex 32)"
echo "Your view token: $AICO_VIEW_TOKEN"

# 2. 启动 view(仍然绑 127.0.0.1)
export AICO_AUDIT_LOG_PATH="/tmp/aico-audit.jsonl"
export AICO_MEMORY_PATH="/tmp/aico-memory.jsonl"
export AICO_STATE_DB_PATH="/tmp/aico-state.db"
export AICO_VIEW_TELEGRAM_BOT_USERNAME="aico_dogfood_bot"  # 启用 deep link
uv run aico-view &

# 3. 起 ngrok 隧道
ngrok http 8765
# 假设拿到 https://abc123.ngrok-free.app

# 4. 手机访问(注意 ?token=...)
# https://abc123.ngrok-free.app/?token=<AICO_VIEW_TOKEN>
```

建议:

- token 写进手机浏览器书签,不要发到群里。
- ngrok 每次重启 URL 变,建议升级 ngrok 账号锁定 subdomain。
- 用完关掉(`kill` aico-view 进程 + Ctrl+C ngrok)。

---

## 形态 3:Cloudflare Tunnel(更稳定但需要域名)

适合:长期个人使用,你已经有 Cloudflare 域名。

```bash
# 1. 设 token 和 env(同形态 2)
export AICO_VIEW_TOKEN="$(openssl rand -hex 32)"
export AICO_AUDIT_LOG_PATH="/tmp/aico-audit.jsonl"
export AICO_MEMORY_PATH="/tmp/aico-memory.jsonl"
uv run aico-view &

# 2. cloudflared 隧道(假设已 `cloudflared tunnel login`)
cloudflared tunnel --url http://127.0.0.1:8765

# 或绑定固定子域名:
cloudflared tunnel route dns <tunnel-id> aico-view.example.com
cloudflared tunnel run <tunnel-id>
```

仍然只通过 `?token=` 鉴权。Cloudflare Access 可以再加一层认证,但**那是奢侈品,
单人 dogfood 不需要**。

---

## 不要做的事

- ❌ 不要直接把 `AICO_VIEW_HOST=0.0.0.0` 设了又不设 token。`TokenGuard.from_env`
  会写一行 WARN 日志说"every request will be rejected",然后真的全拒。这是设计意图。
- ❌ 不要把 token 写进 git 仓库或公开 channel。token 等于查看权限。
- ❌ 不要让 aico-view 进程跑在比 orchestrator 更敏感的环境里。view 永远是只读的,
  但**它能读到所有 memory 内容**——包括老板的 boss-scope memory。
- ❌ 不要给 view 加任何写路由。任何 POST/PUT/DELETE 都被 FastAPI 自动 405。
  如果想要新功能,先回到 boss-first-grounding,问"这件事能不能在 IM 做"。

---

## Env 速查

| 变量 | 必需 | 说明 |
|---|---|---|
| `AICO_AUDIT_LOG_PATH` | 否 | audit JSONL 路径(与 phase1 一致) |
| `AICO_MEMORY_PATH` | 否 | memory JSONL 路径(与 phase1 一致) |
| `AICO_STATE_DB_PATH` | 否 | SQLite task state 路径;`true` 映射到 `.aico/state.db` |
| `AICO_VIEW_PROJECT_IDS` | 否 | 逗号分隔的项目 ID;不设则从 memory 推断 |
| `AICO_VIEW_HOST` | 否 | 监听 host,默认 `127.0.0.1` |
| `AICO_VIEW_PORT` | 否 | 监听端口,默认 `8765` |
| `AICO_VIEW_TOKEN` | 视情况 | 非 loopback 部署**必需** |
| `AICO_VIEW_TELEGRAM_BOT_USERNAME` | 否 | 设了之后,view 内的命令按钮会生成 `https://t.me/<bot>?text=` deep link;不设则降级为复制提示 |

---

## 相关

- ADR-0033 — aico-view read-only mobile web surface
- ADR-0035 — aico-view token auth posture(本文)
- `docs/architecture/boss-first-grounding.md` §3.3
- `docs/human/quickstart.md` 启动指引
