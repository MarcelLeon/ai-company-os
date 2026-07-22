# ADR-0062: Portable Audit Recovery Point

**状态**:Accepted
**日期**:2026-07-22
**决策者**:Codex / Round 224

## 背景

ADR-0061定义ledger与checkpoint是一组证据，但两个live文件分别复制没有一致性边界。checkpoint可能在复制间隙推进，
导致所谓“备份”无法重放。B-013还需要一个能离开原Mac后独立验证的审计恢复资产。

## 候选方案

- 运维脚本依次`cp`两文件：简单，但没有writer lock，无法证明同一point-in-time。
- 只备份JSONL并在恢复时重新seal：否决；会抹掉tail checkpoint证据并把缺失历史重新包装成可信baseline。
- 目录artifact：可读，但跨设备传输容易漏文件，且目录发布没有可移植的atomic no-replace语义。
- 压缩ZIP：体积小，但增加压缩炸弹、资源上限与解压策略攻击面。
- 固定成员的ZIP_STORED + manifest + outer SHA：单文件可移交、流式验证、成员集合可严格约束。
- 直接构建完整state/audit/memory/config bundle：暂缓；跨truth-source一致性与secret/receiver边界尚未定义，不能用一个
  看似完整的包掩盖不同RPO。

## 决策

1. 在audit writer lock内验证并复制ledger与checkpoint；合法checkpoint lag先收敛，snapshot不带lag。
2. 生成owner-only、new-path、固定三member的uncompressed ZIP；manifest不保存源路径或payload摘要之外的正文。
3. 离线verify必须流式核对member hash，并materialize后调用同一production chain/checkpoint verifier。
4. artifact SHA作为外部记录锚点；verify可选要求expected SHA，未来restore必须强制要求。
5. publication使用同目录temporary、hard-link no-overwrite和fsync；失败清理自身输出，不删除并发创建的目标。

## 取舍与后果

- 复制期间writer被锁住，换取严格point-in-time；大ledger会带来短时写入停顿，需要后续rotation/增量策略。
- ZIP_STORED牺牲空间换取可预测流式IO和更小解码攻击面；它仍是敏感明文artifact，off-device层必须加密。
- manifest/member hash证明artifact内部一致，不能防能同时重写artifact的攻击者；expected SHA要保存在独立authority。
- 本决策只定义backup/verify，不授权自动restore。恢复必须有runtime owner fence、pre-restore safety/quarantine和crash-safe
  双文件替换合同后另立ADR。
