"""The generator: a typed description in, a set of design ideas out.

This is the piece the product is actually about. Everything below it - the
vocabulary, the styles, the print pipeline - exists so that this call can work:

    generate("trust the process")

and come back with several genuinely different ideas to choose from.
"""

from __future__ import annotations

from dataclasses import dataclass

from PIL import Image

from .brief import Brief, segment
from .elements import Ctx, render
from .styles import PALETTES, STYLES, Palette


@dataclass
class Idea:
    """One generated design, with everything needed to identify and reprint it."""

    style: str
    palette: str
    image: Image.Image
    brief: Brief

    @property
    def name(self) -> str:
        return f"{self.style}--{self.palette}"

    @property
    def width_mm(self) -> float:
        return self.image.width / self.dpi * 25.4 if hasattr(self, "dpi") else 0.0


MAX_HEIGHT_MM = 380.0     # roughly the printable height of an adult tee front


def _fit_to_height(style_fn, brief: Brief, pal: Palette, ctx_dpi: float,
                   max_height_mm: float, width_mm: float) -> Image.Image:
    """Render, and if the stack is too tall for a shirt, narrow it until it fits.

    Every style sets its big lines to near the full measure, so height grows with
    the number of lines. A long phrase in a tall style can easily exceed the
    printable area - a seven-word phrase reached 442mm against a 380mm limit.

    Height is very close to linear in width, so one corrective pass lands it.
    Narrowing rather than truncating keeps the whole phrase legible, which is the
    right trade for merch: a slightly smaller design still works, a cropped one
    does not.
    """
    from .brief import Brief as _B  # local import keeps the module import-light

    def draw(w: float) -> Image.Image:
        b = _B(phrase=brief.phrase, lines=brief.lines, width_mm=w,
               attribution=brief.attribution)
        return render(_with_attribution(style_fn(b, pal), b, pal),
                      Ctx(dpi=ctx_dpi, ink=pal.ink))

    img = draw(width_mm)
    for _ in range(3):
        h_mm = img.height / ctx_dpi * 25.4
        if h_mm <= max_height_mm:
            break
        width_mm = width_mm * (max_height_mm / h_mm) * 0.98
        img = draw(width_mm)
    return img


def _with_attribution(body, brief: Brief, pal: Palette) -> "Element":
    """Sign the design off with the brand or seminar name.

    Applied around every style rather than inside each one, so the convention
    stays consistent and a new style gets it for free. Kept small and quiet: in
    the reference work the programme name supports the slogan, it never competes
    with it.
    """
    from .elements import Gap, RuledLabel, Stack

    if not brief.attribution:
        return body
    return Stack([
        body,
        Gap(6),
        RuledLabel(brief.attribution.upper(), face="sans-bold", cap_mm=4.0,
                   tracking_em=0.55, width_mm=brief.width_mm * 0.62,
                   thickness_mm=0.7, gap_mm=4),
    ], gap_mm=0, align="centre")


def generate(description: str, width_mm: float = 260.0, dpi: float = 300.0,
             styles: list[str] | None = None,
             palettes: list[str] | None = None,
             attribution: str | None = None,
             max_height_mm: float = MAX_HEIGHT_MM) -> list[Idea]:
    """Lay `description` out in every requested style and palette.

    Deterministic: the same description always produces the same set, so an idea
    can be regenerated from its name alone rather than stored as a blob.

    Whatever is typed, every returned idea fits a printable shirt front.
    """
    brief = segment(description, width_mm=width_mm, attribution=attribution)
    if not brief.lines:
        raise ValueError("Nothing to lay out - the description was empty.")

    style_names = styles or list(STYLES)
    palette_names = palettes or ["mono"]

    ideas: list[Idea] = []
    for sname in style_names:
        if sname not in STYLES:
            raise KeyError(f"Unknown style {sname!r}. Available: {sorted(STYLES)}")
        for pname in palette_names:
            if pname not in PALETTES:
                raise KeyError(f"Unknown palette {pname!r}. "
                               f"Available: {sorted(PALETTES)}")
            pal: Palette = PALETTES[pname]
            img = _fit_to_height(STYLES[sname], brief, pal, dpi,
                                 max_height_mm, width_mm)
            ideas.append(Idea(style=sname, palette=pname, image=img, brief=brief))
    return ideas
