# ADR-0069: Live Provider Authentication Receipts

**状态**:Accepted
**日期**:2026-07-22
**决策者**:Codex / Round 231
**Supersedes**:ADR-0068的recovery-set v5 coverage范围；独立receiver恢复决策继续有效

## 背景

Round 229的runtime reinjection只能证明secret槽位、channel和standing grant binding已恢复，不能证明Claude/Codex远端接受
当前credential。简单`which`、CLI `--version`、环境变量非空或adapter health都会产生灾后假绿色；把真实response写入回执又会
扩大业务内容、credential提示和故障详情的泄露面。

## 候选方案

- 继续把provider认证留给人工口头确认：否决；不可重复、不可绑定recovery set，也不适合boss-absent操作。
- 运行CLI `--version`或现有adapter health：否决；只证明本地二进制存在。
- 使用普通业务prompt作为probe并保存输出：否决；结果不可判定，可能运行工具并泄露上下文。
- 固定随机challenge、受限provider命令、短时secret-free receipt：采用。

## 决策

1. runtime reinjection schema v2记录`claude-code`及所有enabled optional adapter的canonical provider集合；启停漂移必须重新capture。
2. provider probe是可插拔接口，但内建只批准Claude和Codex。它只从配置命令提取official executable，重新构造tool-free、
   non-persistent、read-only/no-network命令，不继承运行时危险参数。
3. probe在private empty cwd启动独立process group，移除所有`AICO_*` child env，限制90秒与每路256 KiB；timeout/overflow杀死
   整个process group。只接受exact随机challenge、terminal success和usage齐备的结构化结果。
4. provider receipt必须先验证set与reinjection receipt，随后绑定两份SHA、revision、owner decision、provider集合与实际probe
   executable SHA。回执30分钟过期，new-path/owner-only发布；不保存challenge明文、prompt、stdout/stderr或credential value/hash/identity。
5. `verify-provider-auth`只复核artifact SHA、current checkout/reinjection/provider scope、executable hash和freshness；它固定报告
   `live_probe_executed=false`、`live_probe_replayed=false`，不能被解释为再次联系provider或连续健康。
6. recovery-set schema v6把provider asset标为`post_restore_live_probe`合同就绪，并新增`requires_post_restore_evidence`维度。
   `unresolved_assets=()`只表示所有资产已有恢复方法，不表示post-restore evidence已提供；`business_restore_ready=false`保持。

## 取舍与后果

- 每次新receipt会产生极小的真实provider成本；freshness换取更接近恢复时点的事实，不能无限复用历史绿色结果。
- executable hash能检测probe入口路径漂移，但不证明PATH解析后的binary内容、签名或供应链；高威胁环境仍需签名/managed install。
- Claude/Codex CLI输出协议升级可能让probe fail closed，需要显式更新parser与测试，不能降级为文本包含匹配。
- 其他provider在有安全、结构化、可限权协议前保持unsupported；可插拔不等于默认信任任意wrapper或yolo command。
