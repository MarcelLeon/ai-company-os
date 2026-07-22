# ADR-0057: Standing Evidence Fingerprint and Drift Gate

**状态**:Accepted
**日期**:2026-07-22
**决策者**:Codex / Round 219

## 背景

ADR-0055只在结果完成时验证repository-relative file/line存在。文件之后可能被修改、删除或替换，SQLite中的
`outcome=complete`却仍会被早报和下一次scheduled run使用。这证明了“当时位置存在”，没有证明“接手时证据仍是
同一份”。对老板缺席系统而言，过期证据继续驱动自治比直接停授更危险。

同时，证据复核本身必须有IO预算；按无限历史、无限文件大小重新hash会把安全检查变成新的event-loop阻塞源。

## 决策

1. 每个成功standing result持久化bounded source manifest：canonical repo-relative path、1-based line、file size和
   full-file SHA-256；不保存source正文。
2. manifest最多16个distinct source，单文件最多256KiB；同一文件多行只读取/hash一次。超过限制结果invalid并停授。
3. proposal receipt保存manifest aggregate SHA-256，SQLite restart后可重算；hash是内容漂移锚点，不是签名或语义证明。
4. 下一次scheduled dispatch只复核同grant最近一次成功结果，限制每次最多4MiB source IO；旧结果的invalid/blocked/
   missing contract仍按既有规则全历史停授。
5. `/inbox`、`/morning`只复核并展示最近5份receipt，最坏约20MiB source IO；更早receipt保留历史状态但不每次重hash。
6. 内容或size变化显示`evidence=drifted`、`outcome=drifted`；root/file/legacy manifest缺失显示`evidence/outcome=missing`。
7. drift/missing均阻止后续自治，要求owner核对；老板IM不显示path、hash或source正文。

## 否决方案

- **只在result time验证一次**：无法覆盖结果完成到老板接手之间的仓库变化。
- **只保存aggregate hash，不保存source ref**：无法从SQLite独立重算，hash成为不可操作装饰。
- **保存引用行正文**：扩大敏感内容与durable state体积；path/line/file hash足以做漂移检查。
- **hash全部历史receipt**：grant最多可有大量run，复核成本会随历史线性增长。
- **只hash cited line**：短行hash可能更容易被低熵猜测；full-file hash更保守，任何文件变化都要求重新验收。
- **drift后自动重跑**：新provider调用不能替代owner对证据变化的判断，还会继续消耗授权成本。

## 后果

### 正面

- complete outcome首次绑定到一个可跨重启重算的内容快照，而不只是可变路径。
- 老板早报和下一次自治能识别证据陈旧，不会在静默变化上继续推进。
- IO、manifest size和IM disclosure都有固定上限。

### 代价与剩余风险

- 文件任意位置变化都会保守标记drift，即使cited line没变；owner需要重新验收。
- repo-relative path和file hash进入owner-local SQLite；不进入IM。若本地state本身失守，hash仍可能提供猜测确认信号。
- 文件读取不是filesystem snapshot；并发写入可能得到中间内容，但后续复核会保守检测变化。
- SHA-256不是来源签名、业务语义、远端provider或真实IM证据；B-014保持。

## 验证

- 单测覆盖current/drifted/missing、oversized file、source总数、manifest aggregate与最近5份复核窗口。
- SQLite round-trip后manifest仍可重算；老板消息不泄漏private path。
- scheduled E2E覆盖drift和missing均不dispatch，并返回bounded hold reason。
