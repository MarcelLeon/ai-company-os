"""Generate Xiaohongshu cover SVGs from the week-one post plan."""

from __future__ import annotations

from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "docs/commercialization/assets/xiaohongshu"

COVERS = [
    ("data-translation", "小老板不是不会经营", "是没人把数据讲成人话", "订单 / 库存 / 广告 / 退款"),
    ("revenue-drop", "收入下降", "别先怪流量", "先查新客、复购、退款、客单价"),
    ("inventory", "库存积压", "不是仓库一个人的问题", "动销 / 毛利 / 季节 / 广告一起看"),
    ("ad-roi", "广告 ROI 变差", "别只问投手行不行", "渠道、商品、退款、复购要一起拆"),
    ("ai-diagnosis", "请不起数据分析师", "先做一次 AI 经营诊断", "从一个具体问题开始"),
    ("report-sample", "AI 诊断报告", "应该长什么样？", "问题 / 口径 / 证据 / 动作"),
    ("seed-users", "招 3 个种子用户", "体验价做一次真实诊断", "换反馈和匿名案例"),
]


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for index, (slug, title, subtitle, footer) in enumerate(COVERS, start=1):
        (OUTPUT_DIR / f"{index:02d}-{slug}.svg").write_text(
            svg(title=title, subtitle=subtitle, footer=footer, index=index),
            encoding="utf-8",
        )


def svg(*, title: str, subtitle: str, footer: str, index: int) -> str:
    accent = "#1e3a8a" if index % 2 else "#0f172a"
    return f"""<svg
  xmlns="http://www.w3.org/2000/svg"
  width="1080"
  height="1440"
  viewBox="0 0 1080 1440"
>
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#f8fafc"/>
      <stop offset="100%" stop-color="#e8eef7"/>
    </linearGradient>
    <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="18" stdDeviation="22" flood-color="#1f2a44" flood-opacity="0.15"/>
    </filter>
  </defs>
  <rect width="1080" height="1440" rx="64" fill="url(#bg)"/>
  <circle cx="910" cy="170" r="190" fill="#dbeafe" opacity="0.72"/>
  <circle cx="150" cy="1260" r="240" fill="#e0e7ff" opacity="0.55"/>

  <text x="92" y="128" font-family="Arial, 'PingFang SC', 'Microsoft YaHei', sans-serif"
        font-size="36" fill="#64748b" letter-spacing="3">AI 经营诊断</text>
  <text x="92" y="272" font-family="Arial, 'PingFang SC', 'Microsoft YaHei', sans-serif"
        font-size="82" font-weight="900" fill="#0f172a">{title}</text>
  <text x="92" y="382" font-family="Arial, 'PingFang SC', 'Microsoft YaHei', sans-serif"
        font-size="70" font-weight="900" fill="{accent}">{subtitle}</text>

  <g filter="url(#shadow)">
    <rect x="92" y="520" width="896" height="460" rx="44" fill="#ffffff"/>
    <rect x="142" y="590" width="350" height="22" rx="11" fill="{accent}"/>
    <rect x="142" y="656" width="680" height="18" rx="9" fill="#cbd5e1"/>
    <rect x="142" y="706" width="560" height="18" rx="9" fill="#e2e8f0"/>
    <rect x="142" y="820" width="210" height="110" rx="28" fill="#eff6ff"/>
    <rect x="404" y="820" width="210" height="110" rx="28" fill="#eef2ff"/>
    <rect x="666" y="820" width="210" height="110" rx="28" fill="#f8fafc"/>
    <text x="178" y="890" font-family="Arial, 'PingFang SC', 'Microsoft YaHei', sans-serif"
          font-size="32" font-weight="800" fill="#1e3a8a">证据</text>
    <text x="440" y="890" font-family="Arial, 'PingFang SC', 'Microsoft YaHei', sans-serif"
          font-size="32" font-weight="800" fill="#4338ca">口径</text>
    <text x="702" y="890" font-family="Arial, 'PingFang SC', 'Microsoft YaHei', sans-serif"
          font-size="32" font-weight="800" fill="#475569">动作</text>
  </g>

  <rect x="92" y="1110" width="896" height="116" rx="58" fill="#0f172a"/>
  <text x="146" y="1184" font-family="Arial, 'PingFang SC', 'Microsoft YaHei', sans-serif"
        font-size="36" font-weight="800" fill="#ffffff">{footer}</text>

  <text x="92" y="1320" font-family="Arial, 'PingFang SC', 'Microsoft YaHei', sans-serif"
        font-size="30" fill="#64748b">不卖玄学增长，只讲数据、证据和可执行动作</text>
</svg>
"""


if __name__ == "__main__":
    main()
