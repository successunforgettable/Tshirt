"""Gate 1a export-check artefact.

Proves that OUR SOFTWARE emits a correct DTF-ready file at the intended physical
size. It does not characterise the printer, who is experienced and trusted.

Every element earns its place by testing something that can only be confirmed
physically:

  100 mm horizontal reference   scale on the X axis
  100 mm vertical reference     scale on the Y axis, and non-uniform distortion
                                that a single axis cannot reveal
  orientation marker            unexpected mirroring
  corner registration marks     cropping or lost extent
  printed overall dimensions    the artefact states its own intended size, so the
                                measurement needs no external reference
  deterministic text            the typography path end to end, including a
                                hyphenated proprietary term
  solid block and clean rules   transparency and edge integrity by eye

Anything measurable in software is checked in software instead, and is not here.
The full diagnostic calibration sheet lives in `sheet.py` and is deliberately NOT
part of the default build.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from ..core.compose import TRANSPARENT, missing_glyphs, render_line

# The export check is drawn in BLACK, not white.
#
# It is a measuring sheet, not artwork: its ink colour has no bearing on what it
# measures. White-on-transparent looked blank in every ordinary viewer, which
# made the file impossible to sanity-check by eye and led the print shop to ask
# whether half of it was meant to be there. Black is visible everywhere and
# removes that whole class of confusion. Production artwork chooses its own
# colours; this file only has to be legible.
INK = (0, 0, 0, 255)

REFERENCE_MM = 100.0
IP_PROBE = "N-Codes"
BRAND_STRING = "THE INCREDIBLE YOU"


@dataclass
class ExportCheckResult:
    image: Image.Image
    width_mm: float
    height_mm: float
    dpi: float
    elements: list[str] = field(default_factory=list)
    rendered_strings: list[str] = field(default_factory=list)
    missing_glyph_chars: list[str] = field(default_factory=list)
    regions: dict = field(default_factory=dict)

    @property
    def rgba(self) -> np.ndarray:
        return np.asarray(self.image.convert("RGBA"))


def _mm(value: float, dpi: float) -> int:
    return round(value / 25.4 * dpi)


def _pt(value: float, dpi: float) -> int:
    return max(1, round(value / 72.0 * dpi))


def build_export_check(font_path: str | Path, dpi: float = 300.0,
                       width_mm: float = 160.0) -> ExportCheckResult:
    font_path = str(font_path)
    W = _mm(width_mm, dpi)
    margin = _mm(9, dpi)
    bar = max(1, _mm(0.8, dpi))
    canvas = Image.new("RGBA", (W, _mm(260, dpi)), TRANSPARENT)
    draw = ImageDraw.Draw(canvas)

    label_px = _pt(9, dpi)
    elements: list[str] = []
    rendered: list[str] = []
    regions: dict = {}

    def label(text: str, x: int, y: int, size_px: int = label_px) -> int:
        img = render_line(font_path, text, size_px, 0, colour=INK)
        canvas.alpha_composite(img, (x, y))
        rendered.append(text)
        return img.height

    y = margin

    # --- title, orientation marker -------------------------------------------
    title_h = label("EXPORT CHECK v1", margin, y, _pt(15, dpi))
    ori_px = _pt(26, dpi)
    ori = render_line(font_path, "R", ori_px, 0, colour=INK)
    canvas.alpha_composite(ori, (W - margin - ori.width, y))
    label("ORIENT", W - margin - ori.width - _mm(17, dpi), y + _mm(2, dpi))
    regions["orientation_marker"] = {"glyph": "R", "x": W - margin - ori.width,
                                     "y": y, "w": ori.width, "h": ori.height}
    elements.append("orientation_marker")
    y += max(title_h, ori.height) + _mm(4, dpi)

    # --- vertical 100 mm reference, with everything else beside it -----------
    # Running the vertical reference alongside the content rather than below it
    # is what keeps the artefact compact: the 100 mm it needs is height the
    # content was going to occupy anyway.
    ref = _mm(REFERENCE_MM, dpi)
    end_stop = _mm(4, dpi)
    vx, vy = margin, y
    draw.rectangle([vx + end_stop // 2, vy, vx + end_stop // 2 + bar - 1, vy + ref], fill=INK)
    for i in range(11):
        gy = vy + round(ref * i / 10)
        tick = end_stop if i % 5 == 0 else _mm(2.5, dpi)
        draw.rectangle([vx + end_stop // 2, gy, vx + end_stop // 2 + tick, gy + bar - 1],
                       fill=INK)
    for gy in (vy, vy + ref):      # unambiguous end stops at exactly 0 and 100 mm
        draw.rectangle([vx, gy, vx + end_stop, gy + bar - 1], fill=INK)
    label("100", vx + end_stop + _mm(1.5, dpi), vy + ref // 2 - _mm(2, dpi))
    regions["vertical_reference"] = {"x": vx, "y": vy, "length_px": ref,
                                     "length_mm": REFERENCE_MM}
    elements.append("vertical_reference_100mm")

    # --- content column ------------------------------------------------------
    cx = vx + _mm(15, dpi)
    cy = vy

    # The artefact declares its own intended size, so the physical measurement
    # needs no separate reference document in hand.
    cy += label(f"INTENDED SIZE: {width_mm:.0f} mm WIDE  -  300 DPI  -  PNG RGBA",
                cx, cy) + _mm(1.5, dpi)
    cy += label("TRANSPARENT BACKGROUND  -  DO NOT RESIZE", cx, cy) + _mm(5, dpi)
    elements.append("printed_dimensions")

    # Horizontal 100 mm reference
    hx = cx
    draw.rectangle([hx, cy + end_stop // 2, hx + ref, cy + end_stop // 2 + bar - 1], fill=INK)
    for i in range(11):
        gx = hx + round(ref * i / 10)
        tick = end_stop if i % 5 == 0 else _mm(2.5, dpi)
        draw.rectangle([gx, cy + end_stop // 2, gx + bar - 1,
                        cy + end_stop // 2 + tick], fill=INK)
    for gx in (hx, hx + ref):
        draw.rectangle([gx, cy, gx + bar - 1, cy + end_stop], fill=INK)
    regions["horizontal_reference"] = {"x": hx, "y": cy, "length_px": ref,
                                       "length_mm": REFERENCE_MM}
    elements.append("horizontal_reference_100mm")
    cy += end_stop + _mm(2, dpi)
    label("0", hx, cy)
    label("50", hx + ref // 2 - _mm(3, dpi), cy)
    cy += label("100 mm", hx + ref - _mm(9, dpi), cy) + _mm(6, dpi)

    tiy = render_line(font_path, BRAND_STRING, _pt(19, dpi), 0, colour=INK)
    canvas.alpha_composite(tiy, (cx, cy))
    rendered.append(BRAND_STRING)
    cy += tiy.height + _mm(3.5, dpi)

    ip = render_line(font_path, IP_PROBE, _pt(15, dpi), 0, colour=INK)
    canvas.alpha_composite(ip, (cx, cy))
    rendered.append(IP_PROBE)
    cy += ip.height + _mm(5, dpi)
    elements.append("deterministic_text")

    # Solid block plus clean rules: transparency and edge integrity by eye.
    block_w, block_h = _mm(62, dpi), _mm(20, dpi)
    draw.rectangle([cx, cy, cx + block_w - 1, cy + block_h - 1], fill=INK)
    regions["solid_block"] = {"x": cx, "y": cy, "w": block_w, "h": block_h}
    cy += block_h + _mm(4, dpi)
    for t_mm in (2.0, 3.0):
        t = max(1, _mm(t_mm, dpi))
        draw.rectangle([cx, cy, cx + block_w - 1, cy + t - 1], fill=INK)
        cy += t + _mm(3.5, dpi)
    elements.append("solid_geometry")

    y = max(vy + ref, cy) + _mm(7, dpi)

    # --- finalise, then corner registration marks ----------------------------
    final_h = y + margin
    canvas = canvas.crop((0, 0, W, final_h))
    draw = ImageDraw.Draw(canvas)

    inset, arm = _mm(3, dpi), _mm(9, dpi)
    corners = [(inset, inset), (W - inset, inset),
               (inset, final_h - inset), (W - inset, final_h - inset)]
    for cxx, cyy in corners:
        draw.rectangle([cxx - arm // 2, cyy - bar // 2, cxx + arm // 2, cyy + bar // 2],
                       fill=INK)
        draw.rectangle([cxx - bar // 2, cyy - arm // 2, cxx + bar // 2, cyy + arm // 2],
                       fill=INK)
    regions["registration_marks"] = {
        "inset_mm": 3.0,
        "horizontal_separation_px": corners[1][0] - corners[0][0],
        "vertical_separation_px": corners[2][1] - corners[0][1],
    }
    elements.append("registration_marks")

    all_chars = "".join(set("".join(rendered)))
    # Report the width the pixels ACTUALLY represent, not the width requested.
    # `_mm()` rounds to whole pixels, so 160.0 mm at 300 DPI becomes 1890 px, which
    # is 160.02 mm. Declaring the request rather than the truth would put a 0.02 mm
    # lie in the manifest - small, but precisely the kind of drift this pipeline
    # exists to prevent. The printed label still says the round intended number.
    return ExportCheckResult(
        image=canvas,
        width_mm=W / dpi * 25.4,
        height_mm=final_h / dpi * 25.4,
        dpi=dpi,
        elements=elements,
        rendered_strings=sorted(set(rendered)),
        missing_glyph_chars=missing_glyphs(font_path, all_chars),
        regions=regions,
    )
