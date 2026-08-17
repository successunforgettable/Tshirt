"""Image analysis primitives. Pure functions over numpy arrays — no file I/O.

These produce the measurements the validator reasons about. They deliberately
report numbers and never verdicts; deciding what a number means belongs to
`validate`, which needs the printer profile to do it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

# Alpha classification. 8-bit alpha rarely lands exactly on 0 or 255 after
# compositing, so the ends are treated as bands rather than exact values.
OPAQUE_MIN = 250
TRANSPARENT_MAX = 5


@dataclass(frozen=True)
class AlphaStats:
    total_px: int
    inked_px: int
    opaque_px: int
    partial_px: int
    transparent_px: int
    soft_px: int
    edge_band_px: int
    stray_colour_px: int

    @property
    def partial_ratio(self) -> float:
        """Partial-alpha pixels as a fraction of inked pixels."""
        return self.partial_px / self.inked_px if self.inked_px else 0.0

    @property
    def soft_ratio(self) -> float:
        """Partial-alpha pixels lying OUTSIDE the edge band, as a fraction of inked.

        This is the number that matters for DTF. Anti-aliasing puts partial alpha
        at edges, which is normal and unavoidable. Partial alpha *away* from an
        edge means a glow, soft shadow or gradient-to-transparent, which prints as
        haze over the white underbase.
        """
        return self.soft_px / self.inked_px if self.inked_px else 0.0


@dataclass(frozen=True)
class RunStats:
    min_px: int
    p1_px: float
    p5_px: float
    median_px: float
    count: int
    axis: str


@dataclass(frozen=True)
class BBox:
    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return self.right - self.left + 1

    @property
    def height(self) -> int:
        return self.bottom - self.top + 1

    def as_dict(self) -> dict:
        return {
            "left": self.left,
            "top": self.top,
            "right": self.right,
            "bottom": self.bottom,
            "width": self.width,
            "height": self.height,
        }


@dataclass
class StrokeStats:
    horizontal: RunStats | None = None
    vertical: RunStats | None = None
    notes: list[str] = field(default_factory=list)

    @property
    def min_px(self) -> int | None:
        vals = [r.min_px for r in (self.horizontal, self.vertical) if r is not None]
        return min(vals) if vals else None

    @property
    def p1_px(self) -> float | None:
        vals = [r.p1_px for r in (self.horizontal, self.vertical) if r is not None]
        return min(vals) if vals else None


def dilate(mask: np.ndarray, iterations: int) -> np.ndarray:
    """Binary dilation with an 8-connected 3x3 element, without scipy."""
    if iterations <= 0:
        return mask.copy()
    out = mask.copy()
    for _ in range(iterations):
        acc = out.copy()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dy == 0 and dx == 0:
                    continue
                acc |= np.roll(np.roll(out, dy, axis=0), dx, axis=1)
        out = acc
    return out


def alpha_stats(rgba: np.ndarray, edge_band_px: int = 3) -> AlphaStats:
    """Measure alpha composition and locate partial alpha relative to edges.

    `edge_band_px` is how far from the opaque/transparent boundary partial alpha
    is considered normal anti-aliasing. Partial alpha beyond that band is "soft".
    """
    if rgba.ndim != 3 or rgba.shape[2] != 4:
        raise ValueError(f"expected an RGBA array, got shape {rgba.shape}")

    alpha = rgba[:, :, 3]
    opaque = alpha >= OPAQUE_MIN
    transparent = alpha <= TRANSPARENT_MAX
    partial = ~opaque & ~transparent
    inked = alpha > TRANSPARENT_MAX

    # The band straddling the boundary: near something opaque AND near something
    # transparent. Anti-aliased edges live here; glows and shadows do not.
    band = dilate(opaque, edge_band_px) & dilate(transparent, edge_band_px)
    soft = partial & ~band

    # Fully transparent pixels carrying colour data confuse some RIPs and signal
    # a flattening or export mistake upstream.
    fully_transparent = alpha == 0
    stray = int(np.count_nonzero(fully_transparent & (rgba[:, :, :3].max(axis=2) > 0)))

    return AlphaStats(
        total_px=int(alpha.size),
        inked_px=int(np.count_nonzero(inked)),
        opaque_px=int(np.count_nonzero(opaque)),
        partial_px=int(np.count_nonzero(partial)),
        transparent_px=int(np.count_nonzero(transparent)),
        soft_px=int(np.count_nonzero(soft)),
        edge_band_px=edge_band_px,
        stray_colour_px=stray,
    )


def inked_bbox(rgba: np.ndarray) -> BBox | None:
    """Bounding box of every pixel carrying any ink. None if the image is empty."""
    alpha = rgba[:, :, 3]
    rows = np.flatnonzero(alpha.max(axis=1) > TRANSPARENT_MAX)
    cols = np.flatnonzero(alpha.max(axis=0) > TRANSPARENT_MAX)
    if rows.size == 0 or cols.size == 0:
        return None
    return BBox(left=int(cols[0]), top=int(rows[0]), right=int(cols[-1]), bottom=int(rows[-1]))


def _runs_along_rows(mask: np.ndarray) -> np.ndarray:
    """Lengths of every contiguous True run, scanning left to right."""
    padded = np.pad(mask, ((0, 0), (1, 1)), constant_values=False).astype(np.int8)
    d = np.diff(padded, axis=1)
    starts = np.argwhere(d == 1)
    ends = np.argwhere(d == -1)
    if starts.shape[0] == 0:
        return np.empty(0, dtype=np.int64)
    # argwhere sorts by row then column, so starts and ends pair positionally.
    return (ends[:, 1] - starts[:, 1]).astype(np.int64)


def stroke_stats(rgba: np.ndarray, opaque_min: int = OPAQUE_MIN) -> StrokeStats:
    """Estimate stroke widths from opaque-run lengths along both axes.

    Method and its limits, stated plainly because the number feeds a print
    decision: a run length measures the horizontal or vertical extent of solid
    ink, which equals the true perpendicular stroke width only for axis-aligned
    strokes. A diagonal stroke of width w yields runs up to w*sqrt(2), so this
    OVERESTIMATES diagonal strokes by up to ~41%. It never underestimates, so it
    is safe as a lower-bound check but must not be read as exact.

    Percentiles rather than the raw minimum are reported because a single stray
    anti-aliased pixel would otherwise dominate the result.
    """
    opaque = rgba[:, :, 3] >= opaque_min
    stats = StrokeStats()
    stats.notes.append(
        "Run-length method: exact for axis-aligned strokes, overestimates diagonals "
        "by up to sqrt(2). Lower-bound safe; not exact."
    )

    for axis_name, mask in (("horizontal", opaque), ("vertical", opaque.T)):
        runs = _runs_along_rows(mask)
        if runs.size == 0:
            continue
        rs = RunStats(
            min_px=int(runs.min()),
            p1_px=float(np.percentile(runs, 1)),
            p5_px=float(np.percentile(runs, 5)),
            median_px=float(np.median(runs)),
            count=int(runs.size),
            axis=axis_name,
        )
        if axis_name == "horizontal":
            stats.horizontal = rs
        else:
            stats.vertical = rs

    return stats
