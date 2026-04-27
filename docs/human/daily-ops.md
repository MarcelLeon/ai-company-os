# Daily Ops — 日常运维速查

> 高频运维操作速查。按场景组织,不按命令组织。
> Phase 0 占位,实际命令在 Phase 1+ 填充。

---

## 启动 / 停止

```bash
# 启动(Phase 1 完成后填充)
# stop / restart 同上
```

---

## 日志查看

```bash
# 实时日志
# 按 traceId 过滤
# 按 taskId 过滤
```

---

## 任务管理

```bash
# 查看当前 OPEN 任务
# 中断某个任务
# 重试失败任务
```

---

## Adapter 管理

```bash
# 列出所有已注册 Adapter
# 启用 / 禁用某个 Adapter
# 查看某 Adapter 状态
```

---

## Channel 管理

```bash
# 列出所有 IM 通道状态
# 重连 Telegram Webhook
```

---

## 配置变更

```bash
# 查看当前生效配置
# reload 配置(无需重启)
```

---

## 数据备份与恢复

```bash
# 备份当前任务历史
# 备份当前 Persona 配置
# 恢复到某个备份点
```

---

## 健康检查

```bash
# 自检命令
# 验证所有 Adapter 可达
# 验证所有 Channel 可达
```

---

## Dogfooding 推荐流程(Phase 1 完成后)

每天早晚两次 5 分钟:

**早上**(检查夜间任务):
1. 打开 Telegram"晨会群"
2. 看夜间各 AI 跑的任务汇总
3. 决定今天派什么新任务

**晚上**(下达夜间任务):
1. 整理白天没做完的事
2. 在 Telegram 群里发任务"今晚把 issue #X-#Y 看一遍"
3. 关电脑(Adapter 仍在跑)

---

## 月度运维

- [ ] 检查 token 消耗,看哪个 Adapter 性价比低
- [ ] 检查 PITFALLS 是否有可以转化为 ADR 的模式
- [ ] 检查 BLOCKERS 是否有长期未解决项,提升优先级
- [ ] 清理 Round 50+ 之前的归档(如有需要)
