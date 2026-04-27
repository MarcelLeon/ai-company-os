# Troubleshooting — 故障排查

> 常见问题速查。问题按"症状 → 原因 → 处理"组织。
> Phase 0 占位,实际问题在使用过程中逐步累积。

---

## 排查总原则

遇到问题,**按以下顺序处理**:

1. **看日志**:`tail -f logs/aico.log`,搜 `ERROR` 和 `WARN`
2. **看状态**:运行健康检查命令
3. **查 PITFALLS**:[`docs/journal/PITFALLS.md`](../journal/PITFALLS.md) grep 关键词
4. **查 BLOCKERS**:[`docs/journal/BLOCKERS.md`](../journal/BLOCKERS.md) 看是不是已知问题
5. **以上都没有 → 写到 BLOCKERS,留给下一轮**

---

## 启动相关

### 启动失败:端口被占用
```bash
# 查找占用端口
lsof -i :8080
# 杀掉占用进程
```

### 启动失败:配置缺失
- 检查 `.env` 文件存在
- 检查必填配置(Bot Token、Adapter 路径)

---

## Telegram 相关

### Bot 收不到消息
1. 检查 Bot Token 正确
2. 检查 Bot 已被加到群 / 已被私聊唤醒
3. 如使用 Webhook,检查域名可达
4. 切换到 long polling 模式排查

### Bot 发不出消息
1. 检查群是否开启了"禁止 Bot 发言"
2. 检查消息长度是否超过 4096 字符限制

---

## Adapter 相关

### Claude Code Adapter 无响应
1. 检查 `claude` 命令在终端能跑
2. 检查 Adapter 配置的路径正确
3. 检查 Adapter 进程未卡死(`ps aux | grep claude`)

### Adapter 输出乱码
- 检查环境变量 `LANG=zh_CN.UTF-8` 或 `LC_ALL=en_US.UTF-8`
- 检查 stdin/stdout 编码

---

## 性能相关

### 任务响应慢
1. 看是哪一步慢:接收 → 派发 → AI 处理 → 输出 → 推送
2. 查 P99 延迟指标
3. 大概率是 AI 本身慢,不是编排层

### 内存占用高
1. 看是不是 token 历史没清理
2. 看是不是 stream 没正确关闭
3. 看是不是事件总线消费不及时堆积

---

## 数据相关

### 任务历史丢失
- 检查持久化后端是否正常
- 检查数据库文件路径
- Phase 1-2 用 SQLite 时:`.db` 文件别误删

### Persona 配置丢失
- 备份策略见 [`daily-ops.md`](daily-ops.md)
- Persona 配置应在 git 中(YAML),不要只存数据库

---

## 已修复历史问题(归档)

(本节随时间累积,记录已修复但有教学价值的问题)

---

## 还没修复的已知问题

参见 [`docs/journal/BLOCKERS.md`](../journal/BLOCKERS.md)。

---

## 我遇到了一个新问题

1. 先在本文 grep 关键词
2. 再到 [`PITFALLS.md`](../journal/PITFALLS.md) grep
3. 都没有 → 这是新问题:
   - 解决了:把它加到本文 + PITFALLS
   - 没解决:写到 BLOCKERS,等下一轮
