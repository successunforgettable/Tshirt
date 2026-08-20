"""Parameterised merch styles.

A style takes any segmented phrase and lays it out. Nothing here is written for
one particular slogan, which is the whole point: the operator types a
description, and the generator runs every style over it.

Each style encodes one set of conventions read from the reference merchandise -
how it treats the big lines, what it does with the connectors, which graphic
device carries the rhythm, and where a handwritten accent lands.
"""

from __future__ import annotations

from dataclasses import dataclass

from .brief import Brief, Line
from .elements import (BLACK, Box, DashedFrame, Element, FitText, Gap,
                       JustifyText, Rule, Stack, Text, Underline)


@dataclass(frozen=True)
class Palette:
    """Placeholder colours. The authoritative brand red is unknown and unguessed."""

    name: str
    ink: tuple
    accent: tuple
    second: tuple
    muted: tuple


WHITE = (255, 255, 255, 255)

PALETTES = {
    "mono": Palette("mono", WHITE, WHITE, WHITE, (165, 165, 165, 255)),
    "ice": Palette("ice", WHITE, (86, 180, 233, 255), (255, 255, 255, 255),
                   (150, 150, 150, 255)),
    "sunset": Palette("sunset", WHITE, (240, 140, 60, 255), (86, 180, 233, 255),
                      (165, 165, 165, 255)),
    "acid": Palette("acid", WHITE, (198, 233, 78, 255), (255, 255, 255, 255),
                    (150, 150, 150, 255)),
}


def _major_width(line: Line, w: float) -> float:
    """How wide a big line should be set.

    Short words set to the full measure become absurd, so width grows with word
    length and tops out at the measure. This is what gives a stack its natural
    ragged rhythm instead of a uniform block.
    """
    return w * min(1.0, 0.44 + 0.085 * len(line.text))


def highlight_stack(brief: Brief, pal: Palette) -> Element:
    """Alternate big lines reversed out of solid blocks."""
    w = brief.width_mm
    kids: list[Element] = []
    flip = False
    for ln in brief.lines:
        if ln.major:
            width = _major_width(ln, w * 0.94)
            if flip:
                kids.append(Box(FitText(ln.text, "display-black",
                                        width_mm=width, colour=BLACK),
                                pad_mm=(3, 4.5), fill=pal.ink))
            else:
                kids.append(FitText(ln.text, "display-black",
                                    width_mm=width, colour=pal.ink))
            flip = not flip
        else:
            kids.append(Text(ln.text.upper(), "sans-bold", cap_mm=6,
                             tracking_em=0.35, colour=pal.muted))
    return Stack(kids, gap_mm=2.5, align="centre")


def condensed_shout(brief: Brief, pal: Palette) -> Element:
    """Tall condensed caps, connectors small and tracked, accent on the longest line."""
    w = brief.width_mm
    hero = brief.longest_major
    kids: list[Element] = []
    for ln in brief.lines:
        if ln.major:
            colour = pal.accent if (hero and ln is hero) else pal.ink
            kids.append(FitText(ln.text, "display", _major_width(ln, w),
                                colour=colour))
        else:
            kids.append(Gap(2))
            kids.append(JustifyText(ln.text.upper(), "display-condensed",
                                    cap_mm=7, width_mm=w * 0.30, colour=pal.muted))
            kids.append(Gap(2))
    return Stack(kids, gap_mm=1.5, align="centre")


def script_finish(brief: Brief, pal: Palette) -> Element:
    """Caps throughout, with the final line handwritten and underlined."""
    w = brief.width_mm
    majors = brief.majors
    last = majors[-1] if majors else None
    kids: list[Element] = []
    for ln in brief.lines:
        if ln.major and ln is last:
            kids.append(Gap(3))
            kids.append(Underline(
                Text(ln.text.title(), "script",
                     cap_mm=min(34.0, 150.0 / max(3, len(ln.text))),
                     colour=pal.ink),
                thickness_mm=2.2, gap_mm=1, inset_frac=0.10, colour=pal.ink))
        elif ln.major:
            kids.append(FitText(ln.text, "display-black",
                                _major_width(ln, w * 0.95), colour=pal.accent))
        else:
            kids.append(Text(ln.text.lower(), "brush", cap_mm=9, colour=pal.muted))
    return Stack(kids, gap_mm=2, align="centre")


def brush_sticker(brief: Brief, pal: Palette) -> Element:
    """Hand-lettered throughout, alternating colours, inside a dashed cut-line."""
    w = brief.width_mm
    pad_v, pad_h = 8.0, 10.0
    inner = w - pad_h * 2
    kids: list[Element] = []
    tone = 0
    for ln in brief.lines:
        if ln.major:
            colour = (pal.accent, pal.second)[tone % 2]
            tone += 1
            kids.append(FitText(ln.text, "brush", _major_width(ln, inner),
                                colour=colour))
        else:
            kids.append(Text(ln.text.lower(), "script", cap_mm=11,
                             colour=pal.muted))
    return DashedFrame(Stack(kids, gap_mm=1, align="centre"),
                       pad_mm=(pad_v, pad_h), dash_mm=5, gap_mm=3.5,
                       thickness_mm=1.1, colour=pal.muted)


def ruled_editorial(brief: Brief, pal: Palette) -> Element:
    """Left-aligned and asymmetric, with hairlines separating the lines."""
    w = brief.width_mm
    kids: list[Element] = []
    for idx, ln in enumerate(brief.lines):
        if ln.major:
            kids.append(FitText(ln.text, "serif-bold", _major_width(ln, w * 0.98),
                                colour=pal.ink))
        else:
            kids.append(Text(ln.text.lower(), "serif-italic", cap_mm=9,
                             colour=pal.accent))
        if idx < len(brief.lines) - 1:
            kids.append(Gap(2))
            kids.append(Rule(width_mm=w * 0.34, thickness_mm=0.8, colour=pal.muted))
            kids.append(Gap(2))
    return Stack(kids, gap_mm=1.5, align="left")


def boxed_badge(brief: Brief, pal: Palette) -> Element:
    """Everything contained in an outlined frame, centred and formal."""
    w = brief.width_mm
    pad_v, pad_h = 10.0, 12.0
    inner = w - pad_h * 2
    kids: list[Element] = []
    for ln in brief.lines:
        if ln.major:
            kids.append(FitText(ln.text, "display-condensed",
                                _major_width(ln, inner), colour=pal.ink))
        else:
            kids.append(Text(ln.text.upper(), "mono-bold", cap_mm=4.5,
                             tracking_em=0.7, colour=pal.accent))
    body = Stack(kids, gap_mm=3, align="centre")
    return Box(Stack([Rule(inner * 0.85, 0.9, colour=pal.muted), Gap(5),
                      body, Gap(5),
                      Rule(inner * 0.85, 0.9, colour=pal.muted)],
                     gap_mm=0, align="centre"),
               pad_mm=(pad_v, pad_h), outline_mm=1.5)


STYLES = {
    "highlight-stack": highlight_stack,
    "condensed-shout": condensed_shout,
    "script-finish": script_finish,
    "brush-sticker": brush_sticker,
    "ruled-editorial": ruled_editorial,
    "boxed-badge": boxed_badge,
}
