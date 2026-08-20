"""Directions matching the product owner's reference merchandise.

Read from four supplied reference tees, the shared DNA is:

  * a MULTI-LINE stacked phrase, not a single word
  * violent scale contrast between lines - one or two words dominate
  * colour used to separate lines from one another
  * a graphic device sitting behind or around the type (highlight blocks, a
    dashed sticker cut-line, an underline swash)
  * two or three typefaces in ONE composition, almost always including a
    handwritten or brush accent
  * dense and tight, with very little air

The earlier directions were the opposite of that on nearly every count, which is
why they read as branding rather than as merch.

All compositions are original, under usage_tier `brand_inspired`. Nothing
reconstructs or approximates the official mark, and no reference artwork is
reproduced, traced or derived from - only the compositional conventions of the
category are used (spec 18.0).
"""

from __future__ import annotations

from .elements import (BLACK, Box, Ctx, DashedFrame, Element, FitText, Gap,
                       JustifyText, Row, Rule, Stack, Text, Underline, render)

WIDTH_MM = 260.0

# Placeholder palette, chosen to read on a black garment. The authoritative
# brand red is still unknown and is NOT guessed here (D-11).
INK = (255, 255, 255, 255)
ACCENT = (86, 180, 233, 255)      # placeholder accent
WARM = (240, 140, 60, 255)        # placeholder secondary
MUTED = (170, 170, 170, 255)


def highlight_stack(w: float = WIDTH_MM) -> Element:
    """R1 - Highlight stack.

    Alternate lines reversed out of solid blocks. The device carries the rhythm,
    so the type can stay in one family and still feel designed.
    """
    def block(text: str, width: float) -> Element:
        return Box(FitText(text, "display-black", width_mm=width, colour=BLACK),
                   pad_mm=(3.5, 5), fill=INK)

    return Stack(gap_mm=3, align="centre", children=[
        FitText("THE", "display-black", width_mm=w * 0.36, colour=INK),
        block("INCREDIBLE", w * 0.90),
        FitText("YOU", "display-black", width_mm=w * 0.46, colour=INK),
    ])


def scale_stack_script(w: float = WIDTH_MM) -> Element:
    """R2 - Scale stack with a script finish.

    Small caps set the setup line, a condensed display face shouts the middle,
    and a script signs off under a swash. Three faces, one composition.
    """
    return Stack(gap_mm=0, align="centre", children=[
        JustifyText("THE", "display-condensed", cap_mm=13, width_mm=w * 0.42,
                    colour=INK),
        Gap(3),
        FitText("INCREDIBLE", "display", width_mm=w, colour=ACCENT),
        Gap(5),
        Underline(Text("You", "script", cap_mm=30, colour=INK),
                  thickness_mm=2.4, gap_mm=1, inset_frac=0.10, colour=INK),
    ])


def sticker_brush(w: float = WIDTH_MM) -> Element:
    """R3 - Brush sticker.

    Brush lettering in two colours with a small script connector, wrapped in a
    dashed cut-line. The loosest of the three and the closest to hand-lettered
    reference work.
    """
    return DashedFrame(
        Stack(gap_mm=1, align="centre", children=[
            FitText("THE", "brush", width_mm=w * 0.34, colour=MUTED),
            FitText("INCREDIBLE", "brush", width_mm=w * 0.92, colour=ACCENT),
            FitText("YOU", "brush", width_mm=w * 0.52, colour=WARM),
        ]),
        pad_mm=(9, 11), dash_mm=5, gap_mm=3.5, thickness_mm=1.1, colour=MUTED)


def slogan_highlight(w: float = WIDTH_MM) -> Element:
    """R4 - A SLOGAN in the reference style, to make a point about content.

    Every reference tee carries a full motivational phrase. THE INCREDIBLE YOU is
    a three-word brand name, and the category's conventions were built around
    longer copy - which is why the style only half fits it. This shows the same
    vocabulary given something to work with.

    The wording is placeholder, not approved brand copy.
    """
    def block(text: str, width: float) -> Element:
        return Box(FitText(text, "display-black", width_mm=width, colour=BLACK),
                   pad_mm=(3, 4.5), fill=INK)

    return Stack(gap_mm=2.5, align="centre", children=[
        FitText("BECOME", "display-black", width_mm=w * 0.62, colour=INK),
        block("THE INCREDIBLE", w * 0.94),
        FitText("VERSION OF", "display-black", width_mm=w * 0.66, colour=INK),
        block("YOURSELF", w * 0.76),
    ])


DIRECTIONS = {
    "R1-highlight-stack": highlight_stack,
    "R2-scale-script": scale_stack_script,
    "R3-sticker-brush": sticker_brush,
    "R4-slogan-highlight": slogan_highlight,
}


def build(name: str, width_mm: float = WIDTH_MM, dpi: float = 300.0):
    if name not in DIRECTIONS:
        raise KeyError(f"Unknown direction {name!r}. Available: {sorted(DIRECTIONS)}")
    return render(DIRECTIONS[name](width_mm), Ctx(dpi=dpi, ink=INK))
