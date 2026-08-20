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
from .elements import (BLACK, Banner, Box, Burst, DashedFrame, Element, FitText,
                       Gap, JustifyText, Outline, Overlap, Rule, Shadow, Stack,
                       Star, Text, Underline)


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
    # Drawn from the reference merchandise: a warm accent against white is the
    # commonest scheme on a black garment by a wide margin.
    "amber": Palette("amber", WHITE, (247, 197, 45, 255), (255, 255, 255, 255),
                     (160, 160, 160, 255)),
    "orange": Palette("orange", WHITE, (240, 130, 30, 255), (255, 255, 255, 255),
                      (155, 155, 155, 255)),
    "teal": Palette("teal", WHITE, (36, 190, 180, 255), (255, 255, 255, 255),
                    (150, 150, 150, 255)),
    "candy": Palette("candy", WHITE, (232, 62, 140, 255), (247, 197, 45, 255),
                     (120, 200, 230, 255)),
}


def _cycle(pal: Palette) -> list:
    """Colours to rotate through when a style gives each line its own."""
    return [pal.ink, pal.accent, pal.second, pal.muted]


def _accent_indices(brief: Brief) -> set[int]:
    """Which lines get the script / accent treatment.

    Connectors take it when the phrase has any - "GREAT / things / TAKE / TIME"
    reads exactly that way in the reference work. A phrase with no connectors
    still needs the alternation, so every second line takes it instead. Without
    this fallback, a phrase like "great things take time" would render as four
    identical shouted lines.
    """
    minors = {i for i, ln in enumerate(brief.lines) if not ln.major}
    if minors:
        return minors
    return {i for i in range(len(brief.lines)) if i % 2 == 1}


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


def shadow_pop(brief: Brief, pal: Palette) -> Element:
    """Heavy caps with an offset accent shadow, colour rotating down the stack."""
    w = brief.width_mm
    cyc = [pal.ink, pal.accent]
    accents = _accent_indices(brief)
    kids: list[Element] = []
    n = 0
    for idx, ln in enumerate(brief.lines):
        if ln.major and idx not in accents:
            colour = cyc[n % len(cyc)]
            shade = cyc[(n + 1) % len(cyc)]
            n += 1
            kids.append(Shadow(
                FitText(ln.text, "display-black", _major_width(ln, w * 0.96),
                        colour=colour),
                offset_mm=(1.8, 1.8), colour=shade))
        else:
            kids.append(FitText(ln.text.title(), "script",
                                _major_width(ln, w * 0.62), colour=pal.second))
    return Stack(kids, gap_mm=2, align="centre")


def script_overlap(brief: Brief, pal: Palette) -> Element:
    """Caps with the connecting words riding over them in script.

    The strongest signal in the reference work that a design was lettered rather
    than typeset.
    """
    w = brief.width_mm
    accents = _accent_indices(brief)
    kids: list[Element] = []
    pending: Line | None = None
    for idx, ln in enumerate(brief.lines):
        if ln.major and idx not in accents:
            base = FitText(ln.text, "display-black", _major_width(ln, w * 0.96),
                           colour=pal.accent)
            if pending is not None:
                kids.append(Overlap(
                    base,
                    FitText(pending.text.title(), "script",
                            _major_width(pending, w * 0.55), colour=pal.ink),
                    shift=(0.0, -0.30)))
                pending = None
            else:
                kids.append(base)
        else:
            pending = ln
    if pending is not None:
        kids.append(FitText(pending.text.title(), "script",
                            _major_width(pending, w * 0.55), colour=pal.ink))
    return Stack(kids, gap_mm=1, align="centre")


def banner_badge(brief: Brief, pal: Palette) -> Element:
    """Ribbon banners behind the connectors, one big line boxed in contrast."""
    w = brief.width_mm
    majors = brief.majors
    hero = max(majors, key=lambda l: len(l.text), default=None)
    kids: list[Element] = []
    for ln in brief.lines:
        if ln.major and ln is hero:
            kids.append(Box(FitText(ln.text, "display-black",
                                    _major_width(ln, w * 0.80), colour=pal.ink),
                            pad_mm=(3, 5), outline_mm=1.4))
        elif ln.major:
            kids.append(FitText(ln.text, "display-condensed",
                                _major_width(ln, w * 0.92), colour=pal.ink))
        else:
            kids.append(Banner(Text(ln.text.upper(), "sans-bold", cap_mm=5,
                                    tracking_em=0.4, colour=BLACK),
                               pad_mm=(2.5, 8), notch_mm=5, fill=pal.accent))
    kids = [Star(size_mm=5, colour=pal.accent)] + kids + [
        Star(size_mm=5, colour=pal.accent)]
    return Stack(kids, gap_mm=3, align="centre")


def burst_script(brief: Brief, pal: Palette) -> Element:
    """A burst around the first line, script for the connectors, hollow accents."""
    w = brief.width_mm
    accents = _accent_indices(brief)
    kids: list[Element] = []
    first = True
    for idx, ln in enumerate(brief.lines):
        if ln.major and idx not in accents:
            el: Element = FitText(ln.text, "display-black",
                                  _major_width(ln, w * 0.80), colour=pal.ink)
            if first:
                el = Burst(el, rays=4, length_mm=10, thickness_mm=1.3,
                           gap_mm=5, colour=pal.accent)
                first = False
            kids.append(el)
        else:
            kids.append(FitText(ln.text.title(), "script",
                                _major_width(ln, w * 0.58), colour=pal.accent))
    return Stack(kids, gap_mm=2, align="centre")


STYLES = {
    "highlight-stack": highlight_stack,
    "shadow-pop": shadow_pop,
    "script-overlap": script_overlap,
    "banner-badge": banner_badge,
    "burst-script": burst_script,
    "condensed-shout": condensed_shout,
    "script-finish": script_finish,
    "brush-sticker": brush_sticker,
    "ruled-editorial": ruled_editorial,
    "boxed-badge": boxed_badge,
}
