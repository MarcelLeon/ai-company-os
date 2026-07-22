# Goal Brief: Runtime Dotenv Generation Drift Health

## Goal

让strict runtime主动暴露“磁盘`.env`已变化但当前进程仍运行旧settings”，且不读取、哈希或持久化secret内容。

## Acceptance

- production loader冻结启动代际，strict heartbeat将其作为required configuration component。
- ordinary edit/replacement/deletion导致FAILED；unchanged generation保持OK。
- payload、日志和operator输出不含path、metadata、content或hash。
- drift进入既有confirmed alert，不触发auto reload/restart/provider replay。
- full tests、Ruff/mypy/format/structure/Compose/wheel/diff通过。

## Non-goals

- 不抵抗能伪造inode/mtime的本机恶意管理员，不做content/secret hash。
- 不证明新配置已完成external recommission，不自动应用磁盘变化。
