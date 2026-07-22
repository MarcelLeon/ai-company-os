# ADR-0085: Runtime Dotenv Generation Drift Health

**状态**:Accepted
**日期**:2026-07-22
**决策者**:Codex
**相关 Round**:Round 247

## 背景

strict install/startup会验证磁盘上的当前`.env`，但已运行进程继续持有启动时settings。文件被编辑、替换或删除后，doctor可能按新文件
显示OK，而旧进程仍使用旧endpoint、grant和recovery binding，形成“磁盘配置已验收=进程已加载”的false-green。

## 决策

1. production settings loader在读取`.env`前后捕获文件元数据代际：device、inode、size、mtime、mode、uid；两次不一致拒绝启动，且不读取、哈希或持久化内容。
2. strict heartbeat把该代际作为required `configuration:dotenv-generation` component；每轮只重新stat并比较。
3. 删除、替换或普通编辑使health FAILED，并复用既有三次确认runtime alert；heartbeat只暴露固定component name/status。
4. 漂移不自动reload/restart：旧进程维持已加载known-good配置并主动告警，由owner修复后显式restart/reinstall。
5. optional/manual settings不强制该探针；文件元数据不是防恶意篡改证明，也不替代external recommission evidence。

## 相关链接

- ROUNDS Round 247
- PITFALLS P-103
- Goal Brief `docs/superpowers/specs/2026-07-22-runtime-dotenv-generation-drift-health.md`
