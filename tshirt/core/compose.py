"""Deterministic typography and composition.

Every production string is rendered here from a pinned font file. No image model
ever contributes wording to a production asset (D-06). Composition is driven by a
declarative layout so that a future browser editor can manipulate the same object
and call the same function — one rendering path, not two (D-07).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

WHITE = (255, 255, 255, 255)
TRANSPARENT = (0, 0, 0, 0)

# A Private Use codepoint no real font maps. Rendering it yields the font's
# substitution glyph, which lets us detect missing glyphs by comparison.
_PROBE_CHAR = ""


@dataclass
class LineSpec:
    """One typographic line in a declarative layout."""

    text: str
    target_width_px: int | None = None   # fit font size to this inked width
    font_size_px: int | None = None      # or pin the size directly
    tracking_ratio: float = 0.0          # letter-spacing as a fraction of font size
    colour: tuple[int, int, int, int] = WHITE


@dataclass
class ComposeResult:
    image: Image.Image
    rendered_strings: list[str]
    missing_glyph_chars: list[str]
    font_path: str
    font_name: str
    layout: dict = field(default_factory=dict)

    @property
    def rgba(self) -> np.ndarray:
        return np.asarray(self.image.convert("RGBA"))


def load_font(font_path: str | Path, size_px: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(font_path), size_px)


def _glyph_signature(font: ImageFont.FreeTypeFont, ch: str) -> bytes:
    img = Image.new("L", (font.size * 2 or 32, font.size * 2 or 32), 0)
    ImageDraw.Draw(img).text((0, 0), ch, font=font, fill=255)
    return img.tobytes()


def missing_glyphs(font_path: str | Path, chars: str, probe_size: int = 64) -> list[str]:
    """Characters the font cannot render, detected via the substitution glyph.

    Guards the pixels that the string comparison in `validate` cannot see: a
    missing glyph renders as a substitution box, which is a wrong shirt even
    though the source string was perfectly correct.
    """
    font = load_font(font_path, probe_size)
    notdef = _glyph_signature(font, _PROBE_CHAR)
    blank = Image.new("L", (probe_size * 2, probe_size * 2), 0).tobytes()
    missing = []
    for ch in sorted(set(chars)):
        if ch.isspace():
            continue
        sig = _glyph_signature(font, ch)
        if sig == notdef or sig == blank:
            missing.append(ch)
    return missing


def render_line(font_path: str | Path, text: str, font_size_px: int,
                tracking_px: float, colour=WHITE) -> Image.Image:
    """Render one line with explicit letter-spacing, cropped to its ink.

    Characters are placed individually because PIL has no tracking control, and
    tracking is what lets a short word be set to a chosen width without distorting
    the letterforms.
    """
    font = load_font(font_path, font_size_px)
    advances = [font.getlength(ch) for ch in text]
    total = sum(advances) + tracking_px * max(0, len(text) - 1)

    pad = font_size_px
    canvas = Image.new("RGBA", (int(total) + pad * 2, font_size_px * 3), TRANSPARENT)
    draw = ImageDraw.Draw(canvas)

    x = float(pad)
    y = font_size_px // 2
    for ch, adv in zip(text, advances):
        draw.text((x, y), ch, font=font, fill=colour)
        x += adv + tracking_px

    bbox = canvas.getbbox()
    return canvas.crop(bbox) if bbox else canvas


def fit_font_size_for_width(font_path: str | Path, text: str, target_width_px: int,
                            tracking_ratio: float = 0.0,
                            lo: int = 8, hi: int = 4000) -> int:
    """Largest font size whose rendered ink does not exceed `target_width_px`.

    Binary search over actual rendered ink, not advance-width estimates, because
    the file's physical size contract is defined by ink and side bearings differ
    from advances.
    """
    best = lo
    while lo <= hi:
        mid = (lo + hi) // 2
        img = render_line(font_path, text, mid, tracking_ratio * mid)
        if img.width <= target_width_px:
            best = mid
            lo = mid + 1
        else:
            hi = mid - 1
    return best


def fit_tracking_for_width(font_path: str | Path, text: str, font_size_px: int,
                           target_width_px: int) -> float:
    """Letter-spacing that brings a fixed-size line to a target inked width."""
    if len(text) < 2:
        return 0.0
    lo, hi = -font_size_px * 0.3, font_size_px * 3.0
    best = 0.0
    for _ in range(60):
        mid = (lo + hi) / 2
        img = render_line(font_path, text, font_size_px, mid)
        if img.width <= target_width_px:
            best = mid
            lo = mid
        else:
            hi = mid
    return best


def compose_incredible_you(font_path: str | Path, target_width_px: int,
                           dpi: float, rule_thickness_mm: float = 2.0) -> ComposeResult:
    """The Gate 1a production composition.

    An ORIGINAL typographic merchandise lockup — a centred three-line stack with
    the longest word dominant and thin flanking rules. It is deliberately NOT a
    reconstruction of the official brand mark (D-17): no human figure, no attempt
    to mirror the identity's own hierarchy, and INCREDIBLE rather than YOU carries
    the dominant weight. Only generic typographic conventions are used.

    The flanking rules are set at a safely printable 2 mm. Probing the printer's
    actual limits is the calibration sheet's job, not the production piece's.
    """
    font_path = str(font_path)
    words = ("THE", "INCREDIBLE", "YOU")
    full_string = "THE INCREDIBLE YOU"

    # INCREDIBLE is the width-setting element.
    main_size = fit_font_size_for_width(font_path, "INCREDIBLE", target_width_px,
                                        tracking_ratio=-0.01)
    main_img = render_line(font_path, "INCREDIBLE", main_size, -0.01 * main_size)

    # THE and YOU are supporting elements at EQUAL weight. Keeping them equal is
    # deliberate: giving YOU dominant emphasis would echo the identity's own
    # hierarchy, and this composition must remain clearly original (D-17).
    sub_size = max(8, int(main_size * 0.46))
    sub_target = int(target_width_px * 0.38)
    the_track = fit_tracking_for_width(font_path, "THE", sub_size, sub_target)
    you_track = fit_tracking_for_width(font_path, "YOU", sub_size, sub_target)
    the_img = render_line(font_path, "THE", sub_size, the_track)
    you_img = render_line(font_path, "YOU", sub_size, you_track)

    rule_px = max(1, round(rule_thickness_mm / 25.4 * dpi))
    gap_px = round(sub_size * 0.60)          # gap between a rule and its word
    line_gap = round(main_size * 0.40)       # vertical gap between lines

    width = max(target_width_px, main_img.width)
    height = the_img.height + line_gap + main_img.height + line_gap + you_img.height
    canvas = Image.new("RGBA", (width, height), TRANSPARENT)
    draw = ImageDraw.Draw(canvas)

    def place_with_rules(img: Image.Image, top: int) -> dict:
        x = (width - img.width) // 2
        canvas.alpha_composite(img, (x, top))
        cy = top + img.height // 2 - rule_px // 2
        left_end = x - gap_px
        right_start = x + img.width + gap_px
        if left_end > 0:
            draw.rectangle([0, cy, left_end, cy + rule_px - 1], fill=WHITE)
        if right_start < width:
            draw.rectangle([right_start, cy, width - 1, cy + rule_px - 1], fill=WHITE)
        return {"x": x, "top": top, "width": img.width, "height": img.height}

    y = 0
    layout_the = place_with_rules(the_img, y)
    y += the_img.height + line_gap
    x_main = (width - main_img.width) // 2
    canvas.alpha_composite(main_img, (x_main, y))
    layout_main = {"x": x_main, "top": y, "width": main_img.width, "height": main_img.height}
    y += main_img.height + line_gap
    layout_you = place_with_rules(you_img, y)

    bbox = canvas.getbbox()
    cropped = canvas.crop(bbox)

    return ComposeResult(
        image=cropped,
        rendered_strings=[full_string, *words],
        missing_glyph_chars=missing_glyphs(font_path, full_string),
        font_path=font_path,
        font_name=Path(font_path).stem,
        layout={
            "target_width_px": target_width_px,
            "achieved_width_px": cropped.width,
            "achieved_height_px": cropped.height,
            "main_font_size_px": main_size,
            "sub_font_size_px": sub_size,
            "rule_thickness_px": rule_px,
            "rule_thickness_mm": rule_thickness_mm,
            "lines": {"THE": layout_the, "INCREDIBLE": layout_main, "YOU": layout_you},
            "composition": "original centred three-line lockup with flanking rules",
        },
    )
