# Launch Article Pack — AI Company OS

> 中文发布素材索引。这里放可直接发布的长文、短文、图源和发布前口径检查,避免 D0 分发时临时翻散落文件。

## 当前可发布素材

| 素材 | 推荐平台 | 主诉求 | 使用方式 |
|---|---|---|---|
| [`2026-06-10-worker-resonance-cnblogs.md`](2026-06-10-worker-resonance-cnblogs.md) | 博客园 / 知乎 / 掘金 / 少数派 | 打工人共鸣:多 agent 反而增加调度成本、风险动作不敢放飞、离开电脑后项目停住 | 作为中文首发长文;建议插入两张架构图 PNG |
| [`2026-06-10-tech-lead-cnblogs.md`](2026-06-10-tech-lead-cnblogs.md) | 博客园 / 知乎 / 掘金 / 技术公众号 | 技术 Lead 视角:agent operations、领域模型、权限、task flow | 适合发给技术读者;标题可偏硬核 |
| [`2026-06-10-worker-resonance-xiaohongshu.md`](2026-06-10-worker-resonance-xiaohongshu.md) | 小红书 / 即刻 / 朋友圈 | 生活化钩子:吃饭、路上被问 release、睡前托管 | 配痛点首图;正文保持短,不要塞架构细节 |
| [`2026-06-10-tech-lead-xiaohongshu.md`](2026-06-10-tech-lead-xiaohongshu.md) | 小红书 / 即刻 / 朋友圈 | 多项目管理:需要 AI Lead 压缩局面 | 配项目组织关系图;重点讲“可靠项目负责人” |
| [`promotion-research-notes.md`](promotion-research-notes.md) | 内部参考 | 开源传播模式和后续素材建议 | 不直接发布;用于后续改稿和平台排期 |

## 图源

| 图源 | 内容 | 发布建议 |
|---|---|---|
| [`diagrams/aico-domain-model.drawio`](diagrams/aico-domain-model.drawio) | Boss / Project / Team / Role / Agent / Appointment / Memory / Task / View 领域关系 | 导出 PNG 后放在技术长文“领域模型”小节 |
| [`diagrams/aico-task-flow.drawio`](diagrams/aico-task-flow.drawio) | IM -> Router -> TaskFactory -> PromptStack -> TaskBus -> Risk/Approval/Adapter -> Audit/View | 导出 PNG 后放在“Task 架构”或“Lead 如何指挥 Roles”小节 |
| [`diagrams/social-pain-cover.drawio`](diagrams/social-pain-cover.drawio) | 痛点首图:吃饭、路上、睡前都在担心“AI 项目还能不能继续” | 导出 PNG 后配共鸣版小红书 / 即刻首图 |
| [`diagrams/boss-absent-loop.drawio`](diagrams/boss-absent-loop.drawio) | Boss-absent loop:`/overnight -> /inbox -> /morning -> /task -> /audit -> /view` | 导出 PNG 后配共鸣长文或评论区解释图 |
| [`diagrams/project-lead-org.drawio`](diagrams/project-lead-org.drawio) | 项目组织图:Boss -> Lead -> Implementer / Tester / Reviewer | 导出 PNG 后配技术 Lead 小红书 / 长文“Lead 如何指挥 Roles”小节 |

## 发布顺序

1. **GitHub public + v0.1.0 Release 之后**再发长文,避免读者点进仓库发现 private 或 release 不存在。
2. **先发共鸣长文**:它最容易让非框架作者理解为什么 AICO 不是另一个聊天 UI。
3. **再发技术 Lead 长文**:给技术读者解释领域模型、task flow、权限和和业界框架的边界。
4. **小红书 / 即刻短文**不要同时贴两篇。先发共鸣版,观察评论问题;第二篇用评论里的高频问题做二次分发。
5. **英文 D0** 仍按 [`../playbook.md`](../playbook.md) 执行,中文文章不要替代 Show HN / Reddit / X 的节奏。

## 发布前口径检查

发任何平台前先逐条确认:

- 当前稳定入口写 **Telegram**;飞书只能写 first slice / 待生产 smoke。
- 不把 OpenClaw 或公司内部 CLI 写成已实现 Adapter。
- 不写“无需 Mac”或“完全云端运行”;AICO 是本机 AI CLI 前面的控制层。
- 不写“安全沙箱”;AICO 是 approval + audit + capability gate,不是 sandbox。
- `/overnight` 当前是离线托管第一阶段,不要写成完整多 step 自动调度器。
- `/view` 是 IM 发送只读 HTML snapshot,不是默认 Web 控制台。
- 小红书正文保持 1000 字以内;长文可以硬核,但开头必须先给日常痛点。

## 推荐标题

### 共鸣长文

- `人不在电脑前,项目还得往前走:我为什么做 AI Company OS`
- `我离开电脑后,AI 项目还能继续吗?`
- `AI coding 工具很强,但我缺的是一个项目办公室`

### 技术长文

- `给每个项目任命一个 AI Lead:Agent 应用的新视角`
- `从 Agent Demo 到 Agent Operations:我为什么给本机 AI CLI 建了项目办公室`
- `AI Company OS 的领域模型:Agent、Role、Appointment、Task 和 Approval`

### 小红书

- `我做了一个“老板不在也能运转”的 AI 项目办公室`
- `多项目打工人,可能真正需要一个 AI Lead`
- `我不在电脑前,AI 项目还能继续吗?`

## 评论区应对

| 质疑 | 回法 |
|---|---|
| 这不就是 CrewAI / AutoGen / LangGraph 吗? | 它们更偏 agent 构建 / runtime;AICO 的 wedge 是本机 AI CLI 的 IM-first operations:项目、岗位、审批、审计、早报和接手。 |
| 为什么是 Telegram? | 当前先解决“人离开电脑后怎么管理本机 agents”的最短路径;Channel 是接口,飞书已有 first slice,但还待生产 smoke。 |
| 这安全吗? | AICO 不是沙箱。它做的是 risk classification、approval gate、adapter capability gate、audit 和 interrupt;高风险本机环境仍要谨慎。 |
| 我只用一个 agent,是不是太重? | 是的,如果只坐在电脑前跑一次任务,AICO 可能太重;它面向多项目、长任务、离线接手和多 agent 分工。 |
| 能不能不用 Codex? | 可以。AICO 的价值是 orchestration / memory / approval / handoff;Codex 是可接入的本机执行现场之一,不是唯一核心。 |

## 当前验证状态

- 小红书两篇已做字数检查:均低于 1000 字。
- draw.io XML 已可被 XML parser 解析,包括两张长文架构图和三张社交平台图。
- 发布前整体证据以 [`../readiness-audit.md`](../readiness-audit.md) 为准;本目录链接和图源已纳入审计。
- 本目录当前只包含发布素材,不改变运行代码。
