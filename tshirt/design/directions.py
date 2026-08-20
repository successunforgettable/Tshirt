"""Four creative directions for THE INCREDIBLE YOU.

These are DIRECTIONS, not variations: different hierarchies, different faces,
different graphic devices, different amounts of air. Four seeds of one layout
would tell the product owner nothing.

Every one is an ORIGINAL typographic composition under usage_tier
`brand_inspired`. None reconstructs, traces or approximates the official brand
mark, and none contains a human figure (D-17). Wording is rendered
deterministically from pinned fonts, so it is exact by construction (D-06).

Proprietary vocabulary is deliberately absent. Those terms have no supplied
meaning, and putting them into a composition would imply one (D-16).
"""

from __future__ import annotations

from .elements import (BLACK, Box, Ctx, Element, FitText, Gap, JustifyText, Row,
                       Rule, RuledLabel, Stack, Text, render)

WIDTH_MM = 280.0


def quiet_luxury(w: float = WIDTH_MM) -> Element:
    """A — Quiet luxury.

    Restraint as the statement. One dominant word, everything else small and
    widely letterspaced, and a great deal of deliberate air. The confidence is in
    what is left out.
    """
    return Stack(gap_mm=0, align="centre", children=[
        Text("THE", "sans", cap_mm=7, tracking_em=0.85),
        Gap(9),
        FitText("INCREDIBLE", "sans-bold", width_mm=w, tracking_em=-0.005),
        Gap(11),
        JustifyText("YOU", "sans", cap_mm=7, width_mm=w * 0.52),
        Gap(16),
        Rule(width_mm=w * 0.18, thickness_mm=0.9),
    ])


def streetwear_slab(w: float = WIDTH_MM) -> Element:
    """B — Streetwear slab.

    Loud and tight. A heavy grotesque at full measure, with YOU reversed out of a
    solid bar so the contrast comes from mass rather than colour. Almost no air.
    """
    return Stack(gap_mm=0, align="centre", children=[
        Row(gap_mm=4, align="middle", children=[
            Rule(width_mm=w * 0.30, thickness_mm=3.0),
            Text("THE", "grotesk-bold", cap_mm=11, tracking_em=0.30),
            Rule(width_mm=w * 0.30, thickness_mm=3.0),
        ]),
        Gap(5),
        FitText("INCREDIBLE", "grotesk-bold", width_mm=w, tracking_em=-0.02),
        Gap(4),
        Box(JustifyText("YOU", "grotesk-bold", cap_mm=26, width_mm=w * 0.74,
                        colour=BLACK),
            pad_mm=(7, 9), fill=BLACK, knockout=True),
    ])


def editorial_serif(w: float = WIDTH_MM) -> Element:
    """C — Editorial.

    Asymmetric and left-aligned, which almost nothing on a T-shirt is. A serif
    carries the weight and an italic supplies the turn, so the whole piece reads
    as a masthead rather than a slogan.
    """
    return Stack(gap_mm=0, align="left", children=[
        Text("THE", "sans", cap_mm=6, tracking_em=0.7),
        Gap(6),
        FitText("INCREDIBLE", "serif-bold", width_mm=w, tracking_em=-0.01),
        Gap(7),
        Row(gap_mm=10, align="middle", children=[
            Text("YOU", "serif-italic", cap_mm=30),
            Rule(width_mm=w * 0.44, thickness_mm=1.2),
        ]),
    ])


def stamp_badge(w: float = WIDTH_MM) -> Element:
    """D — Stamp.

    Contained and official-looking: an outlined frame, a monospaced eyebrow, and
    a centred stack. The frame does the work a logo would, without being one.
    """
    inner = w * 0.80
    return Box(
        Stack(gap_mm=0, align="centre", children=[
            Text("ORIGINAL", "mono-bold", cap_mm=4.5, tracking_em=0.75),
            Gap(7),
            Rule(width_mm=inner * 0.9, thickness_mm=0.9),
            Gap(9),
            Text("THE", "sans-bold", cap_mm=8, tracking_em=0.55),
            Gap(7),
            FitText("INCREDIBLE", "sans-bold", width_mm=inner, tracking_em=-0.01),
            Gap(8),
            JustifyText("YOU", "sans-bold", cap_mm=13, width_mm=inner * 0.5),
            Gap(11),
            Rule(width_mm=inner * 0.9, thickness_mm=0.9),
            Gap(7),
            RuledLabel("MINDSET", cap_mm=4.0, tracking_em=0.7,
                       width_mm=inner * 0.7, thickness_mm=0.7, gap_mm=4),
        ]),
        pad_mm=(11, 14), outline_mm=1.6)


DIRECTIONS = {
    "A-quiet-luxury": quiet_luxury,
    "B-streetwear-slab": streetwear_slab,
    "C-editorial-serif": editorial_serif,
    "D-stamp-badge": stamp_badge,
}


def build(name: str, width_mm: float = WIDTH_MM, dpi: float = 300.0):
    if name not in DIRECTIONS:
        raise KeyError(f"Unknown direction {name!r}. Available: {sorted(DIRECTIONS)}")
    return render(DIRECTIONS[name](width_mm), Ctx(dpi=dpi, ink=BLACK))
