"""Generate public Release Room visual assets.

The output is transcript-driven and intentionally clean: it presents the current
IM-first product flow without exposing private chats or relying on provider tokens.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from textwrap import wrap

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError as exc:  # pragma: no cover - maintenance script guard.
    raise SystemExit(
        "Pillow is required for this maintenance script. Install it with "
        "`python3 -m pip install Pillow` and rerun the command."
    ) from exc


ROOT = Path(__file__).resolve().parents[2]
ASSET_DIR = ROOT / "docs" / "assets"
GIF_PATH = ASSET_DIR / "release-room-demo.gif"
SOCIAL_PATH = ASSET_DIR / "social-preview.png"

FONT_REGULAR = Path("/System/Library/Fonts/Supplemental/Arial.ttf")
FONT_BOLD = Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf")

WIDTH = 960
HEIGHT = 540
SOCIAL_WIDTH = 1280
SOCIAL_HEIGHT = 640


@dataclass(frozen=True)
class Scene:
    title: str
    subtitle: str
    boss: tuple[str, ...]
    aico: tuple[str, ...]
    focus: str
    duration_ms: int


SCENES = (
    Scene(
        title="Project Office",
        subtitle="Open a release room from IM.",
        boss=("/use project release-room", "/team"),
        aico=("release-room", "lead: pm -> claude", "pm / implementer / tester / reviewer"),
        focus="Team",
        duration_ms=4000,
    ),
    Scene(
        title="Shared Memory",
        subtitle="Team rules survive the next task.",
        boss=("/remember v0.2 requires tests", "/remember README is first-user friendly"),
        aico=("Memory saved", "Memory saved", "Prompt stack updated for project roles"),
        focus="Memory",
        duration_ms=4000,
    ),
    Scene(
        title="Role-Based Work",
        subtitle="A fuzzy goal becomes owned jobs.",
        boss=("/ask pm split v0.2 into role tasks",),
        aico=("implementer: code + docs", "tester: contract tests", "reviewer: release risk"),
        focus="Plan",
        duration_ms=4500,
    ),
    Scene(
        title="Approval Gate",
        subtitle="Risky work still waits for the boss.",
        boss=("/ask implementer update code and run pytest", "/approve"),
        aico=("Approval required", "reason: shell execution", "Task approved"),
        focus="Approval",
        duration_ms=5000,
    ),
    Scene(
        title="Independent Checks",
        subtitle="Testing and review are separate jobs.",
        boss=("/ask tester check v0.2 contracts", "/ask reviewer review release risk"),
        aico=("tester: missing contract is visible", "reviewer: no release until tests pass"),
        focus="Review",
        duration_ms=4500,
    ),
    Scene(
        title="Overnight Delegation",
        subtitle="Leave the lead with work while you are away.",
        boss=("/overnight push v0.2 and report done/blocked/risks/next",),
        aico=("Overnight delegation queued", "project: release-room", "lead: pm -> claude"),
        focus="Overnight",
        duration_ms=4000,
    ),
    Scene(
        title="Morning Handoff",
        subtitle="Wake up to a handoff, not terminal archaeology.",
        boss=("/morning",),
        aico=(
            "done: plan and checks staged",
            "blocked: real code change needs approval",
            "next: run tests and update notes",
        ),
        focus="Morning",
        duration_ms=5000,
    ),
    Scene(
        title="View And Audit",
        subtitle="Inspect the snapshot and trace every action.",
        boss=("/view", "/audit"),
        aico=("HTML snapshot attached", "audit: approval_requested", "audit: task_completed"),
        focus="View",
        duration_ms=5000,
    ),
)

FOCUS_ITEMS = (
    ("Team", "project roles"),
    ("Memory", "shared context"),
    ("Plan", "role handoff"),
    ("Approval", "write/run gate"),
    ("Review", "independent checks"),
    ("Overnight", "offline delegation"),
    ("Morning", "done / blocked / next"),
    ("View", "HTML snapshot + audit"),
)


def main() -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    gif_frames = [_render_gif_frame(scene, index) for index, scene in enumerate(SCENES)]
    gif_frames[0].save(
        GIF_PATH,
        save_all=True,
        append_images=gif_frames[1:],
        duration=[scene.duration_ms for scene in SCENES],
        loop=0,
        optimize=True,
        disposal=2,
    )
    _render_social_preview().save(SOCIAL_PATH, optimize=True)
    print(f"Wrote {GIF_PATH}")
    print(f"Wrote {SOCIAL_PATH}")


def _font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    path = FONT_BOLD if bold else FONT_REGULAR
    return ImageFont.truetype(str(path), size=size)


def _render_gif_frame(scene: Scene, index: int) -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), "#f3f6fb")
    draw = ImageDraw.Draw(image)
    _draw_header(draw, scene, index)
    _draw_phone(draw, scene)
    _draw_panel(draw, scene)
    _draw_footer(draw)
    return image


def _draw_header(draw: ImageDraw.ImageDraw, scene: Scene, index: int) -> None:
    draw.rounded_rectangle((28, 22, WIDTH - 28, 82), radius=18, fill="#ffffff")
    draw.ellipse((52, 46, 64, 58), fill="#18a058")
    draw.text((76, 35), "AI Company OS", fill="#111827", font=_font(24, bold=True))
    draw.text((284, 41), "Release Room demo", fill="#64748b", font=_font(17))
    draw.text(
        (WIDTH - 158, 39), f"{index + 1}/{len(SCENES)}", fill="#64748b", font=_font(18, bold=True)
    )
    progress_x = 52
    progress_y = 68
    progress_w = WIDTH - 104
    draw.rounded_rectangle(
        (progress_x, progress_y, progress_x + progress_w, progress_y + 5), radius=3, fill="#e2e8f0"
    )
    filled = int(progress_w * (index + 1) / len(SCENES))
    draw.rounded_rectangle(
        (progress_x, progress_y, progress_x + filled, progress_y + 5), radius=3, fill="#2563eb"
    )
    draw.text((44, 96), scene.title, fill="#111827", font=_font(26, bold=True))
    draw.text((44, 128), scene.subtitle, fill="#475569", font=_font(18))


def _draw_phone(draw: ImageDraw.ImageDraw, scene: Scene) -> None:
    x0, y0, x1, y1 = 40, 166, 462, 492
    draw.rounded_rectangle((x0, y0, x1, y1), radius=24, fill="#0f172a")
    draw.rounded_rectangle((x0 + 10, y0 + 10, x1 - 10, y1 - 10), radius=20, fill="#eef4fb")
    draw.rounded_rectangle((x0 + 10, y0 + 10, x1 - 10, y0 + 54), radius=18, fill="#ffffff")
    draw.text((x0 + 30, y0 + 22), "IM: release-room", fill="#0f172a", font=_font(18, bold=True))
    draw.text((x1 - 98, y0 + 24), "online", fill="#18a058", font=_font(14, bold=True))

    y = y0 + 76
    for line in scene.boss:
        y = _bubble(draw, x0 + 98, y, line, mine=True, max_width=318)
    for line in scene.aico:
        y = _bubble(draw, x0 + 28, y, line, mine=False, max_width=342)


def _bubble(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    text: str,
    *,
    mine: bool,
    max_width: int,
) -> int:
    font = _font(16, bold=text.startswith("/"))
    wrapped = _wrap_text(text, max_chars=34 if mine else 38)
    line_height = 20
    padding_x = 14
    padding_y = 10
    text_width = max(draw.textlength(line, font=font) for line in wrapped)
    width = min(max_width, int(text_width + padding_x * 2))
    height = len(wrapped) * line_height + padding_y * 2
    fill = "#2563eb" if mine else "#ffffff"
    text_fill = "#ffffff" if mine else "#0f172a"
    if mine:
        x = 426 - width
    draw.rounded_rectangle((x, y, x + width, y + height), radius=15, fill=fill)
    for i, line in enumerate(wrapped):
        draw.text((x + padding_x, y + padding_y + i * line_height), line, fill=text_fill, font=font)
    return y + height + 10


def _draw_panel(draw: ImageDraw.ImageDraw, scene: Scene) -> None:
    x0, y0, x1, y1 = 500, 166, 920, 492
    draw.rounded_rectangle((x0, y0, x1, y1), radius=20, fill="#ffffff")
    draw.text((x0 + 26, y0 + 24), "Operating surface", fill="#111827", font=_font(22, bold=True))
    draw.text((x0 + 26, y0 + 54), "What the boss sees from IM", fill="#64748b", font=_font(16))
    grid_y = y0 + 92
    col_w = 176
    row_h = 45
    for idx, (label, desc) in enumerate(FOCUS_ITEMS):
        col = idx % 2
        row = idx // 2
        x = x0 + 24 + col * (col_w + 20)
        y = grid_y + row * row_h
        active = label == scene.focus
        fill = "#eff6ff" if active else "#f8fafc"
        outline = "#2563eb" if active else "#e2e8f0"
        draw.rounded_rectangle(
            (x, y, x + col_w, y + 34),
            radius=10,
            fill=fill,
            outline=outline,
            width=2 if active else 1,
        )
        draw.text(
            (x + 16, y + 6),
            label,
            fill="#1d4ed8" if active else "#334155",
            font=_font(12, bold=True),
        )
        draw.text((x + 16, y + 20), desc, fill="#475569", font=_font(10))

    draw.rounded_rectangle((x0 + 24, y1 - 58, x1 - 24, y1 - 24), radius=12, fill="#0f172a")
    draw.text(
        (x0 + 42, y1 - 49),
        "Local agents stay local. Approval and audit stay visible.",
        fill="#ffffff",
        font=_font(13, bold=True),
    )


def _draw_footer(draw: ImageDraw.ImageDraw) -> None:
    footer = "No-token transcript - Telegram / Feishu - Claude Code / Codex / Cursor"
    draw.text(
        (44, HEIGHT - 34),
        footer,
        fill="#64748b",
        font=_font(14),
    )


def _wrap_text(text: str, *, max_chars: int) -> list[str]:
    return wrap(text, width=max_chars, break_long_words=False, break_on_hyphens=False) or [text]


def _render_social_preview() -> Image.Image:
    image = Image.new("RGB", (SOCIAL_WIDTH, SOCIAL_HEIGHT), "#f3f6fb")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        (54, 54, SOCIAL_WIDTH - 54, SOCIAL_HEIGHT - 54), radius=34, fill="#ffffff"
    )
    draw.text((110, 120), "AI Company OS", fill="#111827", font=_font(64, bold=True))
    draw.text(
        (112, 202),
        "Run local AI coding agents from Telegram or Feishu.",
        fill="#334155",
        font=_font(30, bold=True),
    )
    tags = ("Telegram / Feishu", "Claude Code / Codex", "Approval + Audit")
    x = 112
    for tag in tags:
        width = int(draw.textlength(tag, font=_font(22, bold=True))) + 42
        draw.rounded_rectangle(
            (x, 278, x + width, 328), radius=18, fill="#eff6ff", outline="#bfdbfe"
        )
        draw.text((x + 21, 291), tag, fill="#1d4ed8", font=_font(22, bold=True))
        x += width + 18

    phone = (890, 108, 1168, 526)
    draw.rounded_rectangle(phone, radius=36, fill="#0f172a")
    draw.rounded_rectangle((910, 132, 1148, 502), radius=28, fill="#eef4fb")
    draw.rounded_rectangle((910, 132, 1148, 186), radius=26, fill="#ffffff")
    draw.text((938, 150), "release-room", fill="#0f172a", font=_font(24, bold=True))
    _social_bubble(draw, 944, 214, "/morning", mine=True)
    _social_bubble(draw, 938, 282, "done / blocked / risks / next", mine=False)
    _social_bubble(draw, 960, 358, "/view", mine=True)
    _social_bubble(draw, 938, 426, "HTML snapshot attached", mine=False)
    draw.text(
        (112, 430),
        "Run a local AI team while you are away.",
        fill="#0f172a",
        font=_font(34, bold=True),
    )
    draw.text(
        (112, 480),
        "Roles, memory, approvals, audit, and morning handoff.",
        fill="#475569",
        font=_font(24),
    )
    return image


def _social_bubble(draw: ImageDraw.ImageDraw, x: int, y: int, text: str, *, mine: bool) -> None:
    font = _font(20, bold=text.startswith("/"))
    width = int(draw.textlength(text, font=font)) + 32
    fill = "#2563eb" if mine else "#ffffff"
    text_fill = "#ffffff" if mine else "#0f172a"
    if mine:
        x = 1118 - width
    draw.rounded_rectangle((x, y, x + width, y + 46), radius=17, fill=fill)
    draw.text((x + 16, y + 12), text, fill=text_fill, font=font)


if __name__ == "__main__":
    main()
