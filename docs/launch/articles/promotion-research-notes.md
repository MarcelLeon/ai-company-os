# Promotion Research Notes — 2026-06-10

本轮为四篇宣传稿做了一个轻量外部对照,目标不是模仿爆款项目的语气,而是提炼开源传播里可以复用的结构。

## 参考到的模式

### 1. 首屏一句话要足够窄

- Ollama 的 GitHub README 首屏用非常短的定位和安装入口开始:先告诉读者它让 open models 跑起来,再给下载、quickstart、API 和 community。
- Supabase 早期传播能打穿,很大程度来自一个清晰类比:"open-source Firebase alternative"。这个类比让用户不用先理解所有功能。

AICO 目前最强的一句话不是"multi-agent orchestration",而是:

```text
老板不在电脑前,本机 AI agents 仍然能被远程指挥、审批、交接和追溯。
```

建议后续所有中文传播都围绕这个句子变体展开。

### 2. README 和文章都要有可运行证据

- Dify README 很快进入 Quick start,并明确 Docker Compose 的启动路径。
- Ollama README 直接给安装命令、运行命令和 API 示例。
- AICO 已有 no-token demo,这是非常适合传播的证据。文章里应该反复给这个命令,不要只讲愿景:

```bash
env UV_CACHE_DIR=/tmp/aico-uv-cache uv run --python 3.11 aico-release-room-demo
```

### 3. 爆款项目通常有生态入口

- LangChain README 强调文档、论坛、贡献指南、学院和生态。
- Dify README 有文档、多语言 README、Discord、Reddit、X、LinkedIn、Docker Hub 等入口。
- Ollama README 的 Community Integrations 很长,让人感到项目不是单点工具,而是生态中心。

AICO 当前可以先做轻量版:

- 中文传播入口:博客园 / 小红书 / 知乎 / V2EX。
- 英文传播入口:Show HN / Reddit / X / LinkedIn / dev.to。
- GitHub 入口:good-first-issue、Contributor Quickstart、Release Room no-token demo。

### 4. 传播素材要先讲场景,再讲架构

技术读者也会被场景吸引。AICO 最容易传播的 3 个场景:

- 被追问进度时,手机上拿到可信、可转发、可追溯的简报。
- 睡前托管任务,早上用 `/morning` 接手。
- agent 要写文件或跑 shell 时,手机审批并留审计。

架构文章可以从这些场景反推 Adapter / Channel / audit / memory,不要直接从类图开头。

## 对项目本身的后续建议

1. 增加一页 `docs/launch/articles/README.md`,把四篇文章、Show HN 模板、Reddit 模板、release notes 串成一个发布素材索引。
2. 为中文平台补 3 张静态图:
   - "老板不在场 loop": `/overnight -> /inbox -> /morning -> /task -> /audit`
   - "项目 Lead 组织结构": Boss -> Lead -> Implementer / Tester / Reviewer
   - "AICO 不是什么":不是聊天 UI / 不是沙箱 / 不是单 agent wrapper
3. 小红书不要发长技术解释。第一张图一定要是痛点句,如"我离开电脑后,AI 项目还能继续吗?"
4. 博客园和知乎可以发长文,但标题要偏具体:
   - `人不在电脑前,项目还得往前走:我为什么做 AI Company OS`
   - `给每个项目任命一个 AI Lead:Agent 应用的新视角`
5. 后续如果飞书生产 smoke test 完成,中文文章可以补一版"企业 IM"叙事;当前不要把飞书写成稳定入口。

## Sources

- Ollama GitHub README: <https://github.com/ollama/ollama>
- Dify GitHub README: <https://github.com/langgenius/dify>
- LangChain GitHub README: <https://github.com/langchain-ai/langchain>
- Supabase launch / positioning background: <https://en.wikipedia.org/wiki/Supabase>

