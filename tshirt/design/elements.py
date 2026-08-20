"""Deterministic design vocabulary.

Gate 1a proved the print pipeline is correct. It also showed what the pipeline
could not do: a bare typography engine produces layout, not design. This module
is the missing vocabulary — the primitives a Creative Director composes with.

Two principles carried over from the rest of the core:

  * Everything is specified in MILLIMETRES, the unit a designer actually thinks
    in, and pixels are derived. Cap height in mm is the size that matters, not
    an arbitrary font-size number that means something different in every face.
  * Composition is declarative. An element tree renders the same way whatever
    builds it — a hand-written direction today, an LLM-emitted spec later, a
    browser editor after that. One rendering path (D-07).

Nothing here generates anything with a model. It is all deterministic drawing,
so wording stays exact (D-06) and output is reproducible.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

TRANSPARENT = (0, 0, 0, 0)
BLACK = (0, 0, 0, 255)
WHITE = (255, 255, 255, 255)

FONT_DIR = Path(__file__).resolve().parent.parent.parent / "assets" / "fonts"

# Named faces, so a design spec never carries a file path.
FACES = {
    # Workhorse faces
    "sans-bold": "LiberationSans-Bold.ttf",
    "sans": "LiberationSans-Regular.ttf",
    "serif-bold": "LiberationSerif-Bold.ttf",
    "serif-italic": "LiberationSerif-Italic.ttf",
    "mono-bold": "LiberationMono-Bold.ttf",
    "grotesk-bold": "DejaVuSans-Bold.ttf",
    # Display faces for merch headlines - heavy and condensed, which is what
    # lets a stacked slogan hold the chest without going thin.
    "display": "Anton-Regular.ttf",
    "display-condensed": "BebasNeue-Regular.ttf",
    "display-black": "ArchivoBlack-Regular.ttf",
    # Script and brush. The reference merch uses a handwritten accent on almost
    # every design - the small connecting word, or the final line. Without one
    # of these a composition reads as corporate rather than as apparel.
    "script": "Pacifico-Regular.ttf",
    "brush": "CaveatBrush-Regular.ttf",
}


def face_path(name: str) -> Path:
    if name not in FACES:
        raise KeyError(f"Unknown face {name!r}. Available: {sorted(FACES)}")
    return FONT_DIR / FACES[name]


def mm_to_px(mm: float, dpi: float) -> int:
    return max(1, round(mm / 25.4 * dpi))


@lru_cache(maxsize=256)
def _cap_ratio(face: str) -> float:
    """Cap height as a fraction of nominal font size, measured from the face itself.

    Sizing by cap height rather than nominal size is what lets a serif and a
    grotesque sit together and actually look the same size. Nominal font size is
    not comparable across faces; cap height is.
    """
    probe = 400
    font = ImageFont.truetype(str(face_path(face)), probe)
    img = Image.new("L", (probe * 2, probe * 2), 0)
    ImageDraw.Draw(img).text((probe // 4, probe // 4), "H", font=font, fill=255)
    bbox = img.getbbox()
    return (bbox[3] - bbox[1]) / probe


def size_for_cap_height(face: str, cap_mm: float, dpi: float) -> int:
    return max(4, round(mm_to_px(cap_mm, dpi) / _cap_ratio(face)))


@dataclass
class Ctx:
    """Rendering context. Everything an element needs that is not its own spec."""

    dpi: float = 300.0
    ink: tuple = BLACK

    def px(self, mm: float) -> int:
        return mm_to_px(mm, self.dpi)


class Element:
    """Anything that can render itself to a cropped RGBA image."""

    def render(self, ctx: Ctx) -> Image.Image:  # pragma: no cover - interface
        raise NotImplementedError


def _crop(img: Image.Image) -> Image.Image:
    bbox = img.getbbox()
    return img.crop(bbox) if bbox else img


@lru_cache(maxsize=1024)
def _tracked_mask(text: str, face: str, size_px: int,
                  tracking_q: int) -> Image.Image:
    """Greyscale ink mask for one tracked line, cropped to its ink.

    Geometry is cached separately from colour for two reasons. Fitting text to a
    measure binary-searches over size, so the same line gets laid out a dozen
    times per call; and the same design rendered in four palettes has identical
    geometry each time. Caching the mask makes both nearly free.

    Tracking is quantised to 1/16 px for the cache key - far finer than anything
    visible, and it keeps near-identical searches hitting the same entry.
    """
    tracking_px = tracking_q / 16.0
    font = ImageFont.truetype(str(face_path(face)), size_px)
    advances = [font.getlength(c) for c in text]
    total = sum(advances) + tracking_px * max(0, len(text) - 1)
    pad = size_px
    canvas = Image.new("L", (int(total) + pad * 2, size_px * 3), 0)
    draw = ImageDraw.Draw(canvas)
    x, y = float(pad), size_px // 2
    for ch, adv in zip(text, advances):
        draw.text((x, y), ch, font=font, fill=255)
        x += adv + tracking_px
    bbox = canvas.getbbox()
    return canvas.crop(bbox) if bbox else canvas


def _tracked_width(text: str, face: str, size_px: int, tracking_px: float) -> int:
    return _tracked_mask(text, face, size_px, round(tracking_px * 16)).width


def _draw_tracked(text: str, face: str, size_px: int, tracking_px: float,
                  colour) -> Image.Image:
    """Render one line with explicit letter-spacing, cropped to its ink.

    Characters are placed individually because PIL has no tracking control, and
    tracking is what lets a short word be set to a chosen measure without
    distorting the letterforms.
    """
    mask = _tracked_mask(text, face, size_px, round(tracking_px * 16))
    img = Image.new("RGBA", mask.size, colour)
    img.putalpha(mask)
    return img


@dataclass
class Text(Element):
    """A line of type, sized by CAP HEIGHT in mm."""

    text: str
    face: str = "sans-bold"
    cap_mm: float = 10.0
    tracking_em: float = 0.0     # letter-spacing as a fraction of cap height
    colour: tuple | None = None

    def render(self, ctx: Ctx) -> Image.Image:
        size = size_for_cap_height(self.face, self.cap_mm, ctx.dpi)
        tracking = self.tracking_em * ctx.px(self.cap_mm)
        return _draw_tracked(self.text, self.face, size, tracking,
                             self.colour or ctx.ink)


@dataclass
class FitText(Element):
    """A line scaled so its ink is exactly `width_mm` wide.

    The workhorse of headline-led merch: the word sets the measure, and its
    height falls out rather than being chosen.
    """

    text: str
    face: str = "sans-bold"
    width_mm: float = 200.0
    tracking_em: float = 0.0
    colour: tuple | None = None

    def render(self, ctx: Ctx) -> Image.Image:
        target = ctx.px(self.width_mm)
        colour = self.colour or ctx.ink

        # Width is very close to linear in font size, so one probe brackets the
        # search tightly. Blind bisection over 4..4000 wastes most of its steps.
        probe = 100
        probe_w = _tracked_width(self.text, self.face, probe,
                                 self.tracking_em * probe)
        est = max(4, int(probe * target / max(1, probe_w)))
        lo, hi = max(4, int(est * 0.85)), int(est * 1.18) + 2

        best = 4
        while lo <= hi:
            mid = (lo + hi) // 2
            if _tracked_width(self.text, self.face, mid,
                              self.tracking_em * mid) <= target:
                best, lo = mid, mid + 1
            else:
                hi = mid - 1
        return _draw_tracked(self.text, self.face, best,
                             self.tracking_em * best, colour)


@dataclass
class JustifyText(Element):
    """A line held at a fixed cap height and letter-spaced out to a measure.

    How a short word is made to align with a long one without inflating it.
    """

    text: str
    face: str = "sans-bold"
    cap_mm: float = 6.0
    width_mm: float = 200.0
    colour: tuple | None = None

    def render(self, ctx: Ctx) -> Image.Image:
        size = size_for_cap_height(self.face, self.cap_mm, ctx.dpi)
        colour = self.colour or ctx.ink
        target = ctx.px(self.width_mm)
        if len(self.text) < 2:
            return _draw_tracked(self.text, self.face, size, 0, colour)
        # Upper bound comes from the TARGET, not the font size. Deriving it from
        # font size silently under-fills whenever a short word is set small
        # across a wide measure - the search simply cannot reach far enough, and
        # returns its best near-miss without complaint.
        lo, hi, best = -size * 0.3, float(target), 0.0
        for _ in range(28):
            mid = (lo + hi) / 2
            if _tracked_width(self.text, self.face, size, mid) <= target:
                best, lo = mid, mid
            else:
                hi = mid
        return _draw_tracked(self.text, self.face, size, best, colour)


@dataclass
class Rule(Element):
    """A horizontal line. The cheapest graphic device there is, and often enough."""

    width_mm: float = 100.0
    thickness_mm: float = 2.0
    colour: tuple | None = None

    def render(self, ctx: Ctx) -> Image.Image:
        w, h = ctx.px(self.width_mm), ctx.px(self.thickness_mm)
        img = Image.new("RGBA", (w, h), TRANSPARENT)
        ImageDraw.Draw(img).rectangle([0, 0, w - 1, h - 1],
                                      fill=self.colour or ctx.ink)
        return img


@dataclass
class Gap(Element):
    """Deliberate empty space. Negative space is a design decision, not a leftover."""

    height_mm: float = 5.0
    width_mm: float = 1.0

    def render(self, ctx: Ctx) -> Image.Image:
        return Image.new("RGBA", (ctx.px(self.width_mm), ctx.px(self.height_mm)),
                         TRANSPARENT)


@dataclass
class Box(Element):
    """A child inside a rectangle: filled (knockout) or outlined.

    Filled boxes are how merch typography gets contrast without colour — the word
    reverses out of the block.
    """

    child: Element
    pad_mm: tuple = (4.0, 6.0)       # (vertical, horizontal)
    fill: tuple | None = None        # None = outlined instead
    outline_mm: float = 0.0
    knockout: bool = False           # punch the child through the fill

    def render(self, ctx: Ctx) -> Image.Image:
        inner = self.child.render(ctx)
        pv, ph = ctx.px(self.pad_mm[0]), ctx.px(self.pad_mm[1])
        w, h = inner.width + ph * 2, inner.height + pv * 2
        img = Image.new("RGBA", (w, h), TRANSPARENT)
        draw = ImageDraw.Draw(img)

        if self.fill is not None:
            draw.rectangle([0, 0, w - 1, h - 1], fill=self.fill)
        if self.outline_mm > 0:
            t = ctx.px(self.outline_mm)
            draw.rectangle([0, 0, w - 1, h - 1], outline=ctx.ink, width=t)

        if self.knockout and self.fill is not None:
            # Erase the child's shape out of the block, leaving garment showing.
            mask = Image.new("L", (w, h), 0)
            mask.paste(inner.split()[3], (ph, pv))
            img.putalpha(Image.composite(Image.new("L", (w, h), 0),
                                         img.split()[3], mask))
        else:
            img.alpha_composite(inner, (ph, pv))
        return img


@dataclass
class Stack(Element):
    """Vertical arrangement. `align` is left / centre / right."""

    children: list = field(default_factory=list)
    gap_mm: float = 4.0
    align: str = "centre"

    def render(self, ctx: Ctx) -> Image.Image:
        imgs = [c.render(ctx) for c in self.children]
        imgs = [i for i in imgs if i.width and i.height]
        if not imgs:
            return Image.new("RGBA", (1, 1), TRANSPARENT)
        gap = ctx.px(self.gap_mm) if self.gap_mm else 0
        w = max(i.width for i in imgs)
        h = sum(i.height for i in imgs) + gap * (len(imgs) - 1)
        out = Image.new("RGBA", (w, h), TRANSPARENT)
        y = 0
        for i in imgs:
            x = {"left": 0, "right": w - i.width}.get(self.align, (w - i.width) // 2)
            out.alpha_composite(i, (x, y))
            y += i.height + gap
        return out


@dataclass
class Row(Element):
    """Horizontal arrangement. `align` is top / middle / bottom."""

    children: list = field(default_factory=list)
    gap_mm: float = 4.0
    align: str = "middle"

    def render(self, ctx: Ctx) -> Image.Image:
        imgs = [c.render(ctx) for c in self.children]
        imgs = [i for i in imgs if i.width and i.height]
        if not imgs:
            return Image.new("RGBA", (1, 1), TRANSPARENT)
        gap = ctx.px(self.gap_mm) if self.gap_mm else 0
        h = max(i.height for i in imgs)
        w = sum(i.width for i in imgs) + gap * (len(imgs) - 1)
        out = Image.new("RGBA", (w, h), TRANSPARENT)
        x = 0
        for i in imgs:
            y = {"top": 0, "bottom": h - i.height}.get(self.align, (h - i.height) // 2)
            out.alpha_composite(i, (x, y))
            x += i.width + gap
        return out


@dataclass
class RuledLabel(Element):
    """A short line flanked by rules to a full measure — a classic eyebrow device."""

    text: str
    face: str = "sans-bold"
    cap_mm: float = 4.0
    tracking_em: float = 0.5
    width_mm: float = 200.0
    thickness_mm: float = 1.0
    gap_mm: float = 5.0

    def render(self, ctx: Ctx) -> Image.Image:
        label = Text(self.text, self.face, self.cap_mm, self.tracking_em).render(ctx)
        total, gap = ctx.px(self.width_mm), ctx.px(self.gap_mm)
        arm = max(1, (total - label.width - gap * 2) // 2)
        rule = Rule(width_mm=arm / ctx.dpi * 25.4,
                    thickness_mm=self.thickness_mm).render(ctx)
        h = max(label.height, rule.height)
        out = Image.new("RGBA", (total, h), TRANSPARENT)
        out.alpha_composite(rule, (0, (h - rule.height) // 2))
        out.alpha_composite(label, (arm + gap, (h - label.height) // 2))
        out.alpha_composite(rule, (total - arm, (h - rule.height) // 2))
        return out


@dataclass
class Shadow(Element):
    """A child with an offset copy of itself behind it.

    The most common device in the reference merchandise and the cheapest way to
    lift type off a garment. On a dark shirt the shadow is usually the accent
    colour rather than black, so the design reads as two-tone rather than dirty.
    """

    child: Element
    offset_mm: tuple = (1.6, 1.6)
    colour: tuple | None = None

    def render(self, ctx: Ctx) -> Image.Image:
        inner = self.child.render(ctx)
        dx, dy = ctx.px(abs(self.offset_mm[0])), ctx.px(abs(self.offset_mm[1]))
        sx = dx if self.offset_mm[0] >= 0 else 0
        sy = dy if self.offset_mm[1] >= 0 else 0
        img = Image.new("RGBA", (inner.width + dx, inner.height + dy), TRANSPARENT)

        shadow = Image.new("RGBA", inner.size, self.colour or ctx.ink)
        shadow.putalpha(inner.split()[3])
        img.alpha_composite(shadow, (sx, sy))
        img.alpha_composite(inner, (dx - sx, dy - sy))
        return img


@dataclass
class Outline(Element):
    """A child with a stroke around it, optionally hollow.

    `hollow` keeps only the stroke, which is how the reference work gets a line
    of type to recede behind a louder one without losing it.
    """

    child: Element
    width_mm: float = 1.2
    colour: tuple | None = None
    hollow: bool = False

    def render(self, ctx: Ctx) -> Image.Image:
        inner = self.child.render(ctx)
        t = max(1, ctx.px(self.width_mm))
        pad = t + 2
        base = Image.new("RGBA", (inner.width + pad * 2, inner.height + pad * 2),
                         TRANSPARENT)
        base.alpha_composite(inner, (pad, pad))
        alpha = base.split()[3]

        grown = alpha.filter(ImageFilter.MaxFilter(t * 2 + 1))
        stroke = Image.new("RGBA", base.size, self.colour or ctx.ink)
        stroke.putalpha(grown)

        if self.hollow:
            # Punch the original shape out, leaving only the ring.
            ring = Image.composite(Image.new("L", base.size, 0), grown, alpha)
            stroke.putalpha(ring)
            return stroke

        stroke.alpha_composite(base)
        return stroke


@dataclass
class Burst(Element):
    """Short radiating strokes flanking a child - the "pop" device."""

    child: Element
    rays: int = 5
    length_mm: float = 12.0
    thickness_mm: float = 1.4
    gap_mm: float = 5.0
    spread_deg: float = 46.0
    colour: tuple | None = None

    def render(self, ctx: Ctx) -> Image.Image:
        import math
        inner = self.child.render(ctx)
        L, t, g = ctx.px(self.length_mm), max(1, ctx.px(self.thickness_mm)), ctx.px(self.gap_mm)
        pad = L + g + t
        img = Image.new("RGBA", (inner.width + pad * 2, inner.height + pad * 2),
                        TRANSPARENT)
        img.alpha_composite(inner, (pad, pad))
        draw = ImageDraw.Draw(img)
        colour = self.colour or ctx.ink
        cy = pad + inner.height // 2
        for side, x0 in ((-1, pad - g), (1, pad + inner.width + g)):
            for i in range(self.rays):
                frac = (i / max(1, self.rays - 1)) - 0.5
                ang = math.radians(frac * self.spread_deg)
                dx = side * L * math.cos(ang)
                dy = L * math.sin(ang)
                draw.line([(x0, cy), (x0 + dx, cy + dy)], fill=colour, width=t)
        return img


@dataclass
class Banner(Element):
    """A child on a ribbon with notched ends - the awards-badge device."""

    child: Element
    pad_mm: tuple = (3.0, 9.0)
    notch_mm: float = 6.0
    fill: tuple | None = None
    text_colour: tuple = BLACK

    def render(self, ctx: Ctx) -> Image.Image:
        inner = self.child.render(ctx)
        pv, ph = ctx.px(self.pad_mm[0]), ctx.px(self.pad_mm[1])
        n = ctx.px(self.notch_mm)
        w, h = inner.width + ph * 2, inner.height + pv * 2
        img = Image.new("RGBA", (w, h), TRANSPARENT)
        ImageDraw.Draw(img).polygon(
            [(0, 0), (w - 1, 0), (w - 1 - n, h // 2), (w - 1, h - 1),
             (0, h - 1), (n, h // 2)],
            fill=self.fill or ctx.ink)
        img.alpha_composite(inner, (ph, pv))
        return img


@dataclass
class Star(Element):
    """A small filled star, for punctuating a stack."""

    size_mm: float = 5.0
    points: int = 5
    colour: tuple | None = None

    def render(self, ctx: Ctx) -> Image.Image:
        import math
        r = ctx.px(self.size_mm) / 2
        d = int(r * 2) + 2
        img = Image.new("RGBA", (d, d), TRANSPARENT)
        pts = []
        for i in range(self.points * 2):
            rad = r if i % 2 == 0 else r * 0.42
            a = math.pi / 2 * 3 + i * math.pi / self.points
            pts.append((d / 2 + rad * math.cos(a), d / 2 + rad * math.sin(a)))
        ImageDraw.Draw(img).polygon(pts, fill=self.colour or ctx.ink)
        return img


@dataclass
class Overlap(Element):
    """Two elements sharing space, the second riding over the first.

    Script crossing a line of caps is everywhere in the reference work and is the
    single strongest signal that a design was lettered rather than typeset.
    `shift` is a fraction of the base element's size.
    """

    base: Element
    over: Element
    shift: tuple = (0.0, 0.34)     # (x, y) as fractions of the base
    align: str = "centre"

    def render(self, ctx: Ctx) -> Image.Image:
        b = self.base.render(ctx)
        o = self.over.render(ctx)
        ox = int(b.width * self.shift[0])
        oy = int(b.height * self.shift[1])

        x = {"left": 0, "right": b.width - o.width}.get(
            self.align, (b.width - o.width) // 2) + ox
        y = b.height - o.height // 2 + oy - o.height // 2

        left, top = min(0, x), min(0, y)
        w = max(b.width, x + o.width) - left
        h = max(b.height, y + o.height) - top
        img = Image.new("RGBA", (w, h), TRANSPARENT)
        img.alpha_composite(b, (-left, -top))
        img.alpha_composite(o, (x - left, y - top))
        return img


@dataclass
class DashedFrame(Element):
    """A dashed outline around a child - the "sticker" device.

    Common on motivational merch: it reads as a cut-line and gives an otherwise
    floating lockup a defined edge.
    """

    child: Element
    pad_mm: tuple = (8.0, 10.0)
    dash_mm: float = 4.0
    gap_mm: float = 3.0
    thickness_mm: float = 1.0
    colour: tuple | None = None

    def render(self, ctx: Ctx) -> Image.Image:
        inner = self.child.render(ctx)
        pv, ph = ctx.px(self.pad_mm[0]), ctx.px(self.pad_mm[1])
        w, h = inner.width + ph * 2, inner.height + pv * 2
        img = Image.new("RGBA", (w, h), TRANSPARENT)
        draw = ImageDraw.Draw(img)
        colour = self.colour or ctx.ink
        d, g, t = ctx.px(self.dash_mm), ctx.px(self.gap_mm), ctx.px(self.thickness_mm)

        step = d + g
        for x in range(0, w, step):                       # top and bottom
            draw.rectangle([x, 0, min(x + d, w) - 1, t - 1], fill=colour)
            draw.rectangle([x, h - t, min(x + d, w) - 1, h - 1], fill=colour)
        for y in range(0, h, step):                       # left and right
            draw.rectangle([0, y, t - 1, min(y + d, h) - 1], fill=colour)
            draw.rectangle([w - t, y, w - 1, min(y + d, h) - 1], fill=colour)

        img.alpha_composite(inner, (ph, pv))
        return img


@dataclass
class Underline(Element):
    """A child with a rule beneath it, inset from each end.

    The swash under a script word. Ties a handwritten line back to the grid.
    """

    child: Element
    thickness_mm: float = 2.0
    gap_mm: float = 2.0
    inset_frac: float = 0.06
    colour: tuple | None = None

    def render(self, ctx: Ctx) -> Image.Image:
        inner = self.child.render(ctx)
        t, g = ctx.px(self.thickness_mm), ctx.px(self.gap_mm)
        w = inner.width
        img = Image.new("RGBA", (w, inner.height + g + t), TRANSPARENT)
        img.alpha_composite(inner, (0, 0))
        inset = int(w * self.inset_frac)
        ImageDraw.Draw(img).rectangle(
            [inset, inner.height + g, w - inset - 1, inner.height + g + t - 1],
            fill=self.colour or ctx.ink)
        return img


def render(element: Element, ctx: Ctx | None = None) -> Image.Image:
    """Render a design to a cropped RGBA image, ready for the print pipeline."""
    return _crop(element.render(ctx or Ctx()))
