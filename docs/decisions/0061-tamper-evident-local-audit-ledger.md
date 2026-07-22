# ADR-0061: Tamper-Evident Local Audit Ledger

**状态**:Accepted
**日期**:2026-07-22
**决策者**:Codex / Round 223

## 背景

ADR-0008选择JSONL持久化审计，但“append API”不等于历史不可修改。老板长期缺席时，AICO会从该文件重建metrics和
审计视图；有效JSON修改、删除或重排若静默通过，会让恢复证据比无证据更危险。

## 候选方案

- 继续普通JSONL并依赖文件权限：简单，但误编辑、损坏或非恶意本地修改仍无法发现。
- 把审计迁入SQLite：可事务化，但扩大状态迁移，且单库本身仍不能证明历史未被重写。
- 每条记录做独立checksum：能发现字段损坏，不能发现整行删除、插入或重排。
- JSONL SHA-256链 + 独立checkpoint + writer lock：保留运维可读性，并有界检测历史和tail变化。
- 远端签名/WORM：信任更强，但引入外部服务、密钥轮换与离线可用性，不适合作为当前本地基线。

## 决策

扩展ADR-0008：新event写入canonical JSONL并带previous/head SHA-256 link；owner-only sidecar checkpoint锚定事件数、字节数
与链头，OS advisory lock串行化writer。event先fsync，checkpoint后原子fsync，使crash window可验证恢复。

旧日志必须由owner显式seal；seal不重写历史event，只对核对后的现有字节建立baseline。所有read/replay和production
preflight遇到不一致都fail closed。

## 取舍与后果

- 保留原event字段在顶层，现有`tail`/`jq`仍可用；消费者必须容忍新增`_audit`字段。
- checkpoint让tail deletion可见，但ledger和checkpoint被同一主机攻击者一起重写仍不可证明；更强威胁模型需要外部签名
  或WORM anchor。
- checkpoint短暂落后于已fsync的完整链是唯一自动修复窗口；反向落后、断链、非canonical record和duplicate event id拒绝。
- ledger、checkpoint与lock均要求owner-only regular file；audit和checkpoint必须一起备份、恢复和校验。
- `aico-audit seal`是信任声明，不是修复命令；owner不确认baseline时不得运行。
