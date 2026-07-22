# Data-Agent V1 Baseline Goal Brief

## Boss Prompt

```text
/goal lead 研发企业级 data-agent v1。验收: 本地可运行; 有语义层; 能回答20个golden业务问题; 回答必须给出SQL或确定性计算依据; 遇到歧义必须追问; 有测试、README、quickstart、handoff和AICO证据。停止: 需要真实外部账号、付费、上传第三方、或无法确定企业语义口径。
```

## Acceptance Evidence

- Local CLI quickstart works.
- 20 golden evals pass.
- AICO project config loads with a complete team.
- `/morning`, `/inbox`, `/task`, and `/view` evidence is captured after real runtime.
- Human scorecard is filled.

## Stop Conditions

- Real external account, payment, upload, publication, or sensitive data action.
- Benchmark criteria need to change before scoring v1.
- Data-agent cannot answer with deterministic evidence.
