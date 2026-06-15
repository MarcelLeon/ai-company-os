# 我做了一个“老板不在也能运转”的 AI 项目办公室

![Release Room demo](../../assets/release-room-demo.gif)

最近用 AI coding agent,最强的反差不是 AI 不会写代码,而是我还是得一直盯着它们。

中午去吃饭,agent 还在跑测试;进电梯时群里问“今天能不能发”;睡前想把 release 交出去,又怕早上回来只看到一屏混杂输出。

真正卡住我的不是代码能力,而是这些事:

- 多个 agent 都来问我下一步,我变成调度器
- 写文件、跑 shell、git push 不能默认放飞
- 手机上想看局面,不是看一整屏日志
- 人离开 Mac 后,项目就容易停在半路
- 长任务做完后很难接手
- 测试命令、发布坑、老板偏好每次都要重讲

现实公司不是这样的。老板不在办公室,公司也会继续运转:负责人拆目标、盯风险、同步进度,关键动作再升级。

所以我做了 AI Company OS。它不是新的聊天 UI,而是把本机 Claude Code、Codex、Cursor、Trae、Gemini 等 CLI 组织成一个能通过 Telegram 远程管理的小团队。

你可以给项目任命 PM、implementer、tester、reviewer,然后在手机上:

```text
/team
/ask
/approve
/overnight
/morning
/task
/audit
```

睡前把任务交出去,风险动作等你审批;第二天先看早报和局面,需要细节再查任务和审计。

它不承诺 AI 永远正确,所以才把审批、审计、打断、早报放在第一层。

我想要的不是多一个聊天框,而是我不在电脑前时,项目也能被组织起来继续往前走。

项目: AI Company OS  
关键词: 本机 agents / Telegram / 审批 / 审计 / 离线托管

#AI工具 #程序员 #开源项目 #AI编程 #效率工具
