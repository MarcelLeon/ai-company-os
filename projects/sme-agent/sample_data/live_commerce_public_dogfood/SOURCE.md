# Public-web dogfood fixture

This fixture is designed for SME Agent dogfooding, not for benchmarking real
merchant performance.

## Public sources

- KuaiLive public dataset page: <https://imgkkk574.github.io/KuaiLive>
  - The page describes a real Kuaishou live-streaming dataset released on
    Zenodo.
  - Its public summary reports 11,613,708 live rooms, 5,357,998 interactions,
    4,909,515 clicks, and 72,646 gifts.
- KuaiLive Zenodo record: <https://zenodo.org/records/16565801>
  - The full archive is about 858 MB and is intentionally not vendored here.
- OnlineGMV / TRACE project: <https://github.com/alimama-tech/OnlineGMV>
  - The project frames post-click GMV prediction around exposure/click,
    payment, and refund-style downstream commerce signals.

## Transformation notes

- This local CSV package is a small scaled-down dogfood fixture. It is derived
  from public dataset shapes and aggregate public statistics, then normalized to
  the SME Agent live-commerce template.
- It is **not** a raw extract from any merchant backend.
- It is **not** a statistically representative sample of KuaiLive or TRACE.
- It should only be used to verify that SME Agent can:
  - map Chinese platform-style headers;
  - compute GMV, paid GMV, AOV, refund rate, GPM, and payment conversion;
  - render human-review findings with explicit assumptions.

## Expected diagnosis values

- field mapping coverage: 100%;
- GMV: 2850;
- paid GMV: 2249;
- paid order count: 5;
- paid buyer count: 5;
- AOV: 449.80;
- refund rate: 0.17;
- GPM: 398.97;
- payment conversion rate: 0.0009.

## Human-use warning

Do not present this as real customer data. For commercial validation, replace
this fixture with a real customer export after authorization and redaction.
