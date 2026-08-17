"""Physical sizing and resolution.

Pure functions: values in, values out. No I/O, no imaging library, no globals.
This module and `validate` carry the project's correctness burden (spec 4.3, D-14).

Canonical internal unit is the millimetre (spec 12). Pixels are always derived,
never assumed, and effective DPI is always computed, never read from metadata.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

MM_PER_INCH = 25.4


def inches_to_mm(inches: float) -> float:
    return inches * MM_PER_INCH


def mm_to_inches(mm: float) -> float:
    return mm / MM_PER_INCH


def required_px(physical_mm: float, dpi: float) -> int:
    """Pixels needed to render `physical_mm` at `dpi`.

    Rounds up: a fractional pixel short of the requirement is still short.
    """
    if physical_mm <= 0:
        raise ValueError(f"physical_mm must be positive, got {physical_mm}")
    if dpi <= 0:
        raise ValueError(f"dpi must be positive, got {dpi}")
    return math.ceil(mm_to_inches(physical_mm) * dpi)


def px_to_mm(px: int, dpi: float) -> float:
    """Physical size of `px` pixels rendered at `dpi`."""
    if dpi <= 0:
        raise ValueError(f"dpi must be positive, got {dpi}")
    return inches_to_mm(px / dpi)


def effective_dpi(px: int, physical_mm: float) -> float:
    """Actual resolution of `px` pixels printed across `physical_mm`.

    This is the only DPI the system trusts. Image metadata is never consulted
    (spec 12) because it describes intent, not the pixels present.
    """
    if physical_mm <= 0:
        raise ValueError(f"physical_mm must be positive, got {physical_mm}")
    if px <= 0:
        raise ValueError(f"px must be positive, got {px}")
    return px / mm_to_inches(physical_mm)


def scale_preserving_aspect(width_px: int, height_px: int, target_width_px: int) -> tuple[int, int]:
    """Target dimensions preserving aspect ratio, driven by width."""
    if width_px <= 0 or height_px <= 0:
        raise ValueError("source dimensions must be positive")
    if target_width_px <= 0:
        raise ValueError("target width must be positive")
    return target_width_px, max(1, round(height_px * target_width_px / width_px))


@dataclass(frozen=True)
class PhysicalSpec:
    """A production asset's physical intent, paired with the pixels realising it.

    Height is derived from the rendered composition rather than fixed in advance,
    so aspect ratio is preserved rather than invented (Gate 1a product direction).
    """

    width_px: int
    height_px: int
    dpi: float

    @property
    def width_mm(self) -> float:
        return px_to_mm(self.width_px, self.dpi)

    @property
    def height_mm(self) -> float:
        return px_to_mm(self.height_px, self.dpi)

    @property
    def effective_dpi_width(self) -> float:
        return effective_dpi(self.width_px, self.width_mm)

    def describe(self) -> dict:
        return {
            "width_px": self.width_px,
            "height_px": self.height_px,
            "width_mm": round(self.width_mm, 3),
            "height_mm": round(self.height_mm, 3),
            "dpi": self.dpi,
        }


def px_to_mm_length(px: float, dpi: float) -> float:
    """Millimetre length of a pixel measurement (e.g. a stroke width).

    Separate from `px_to_mm` because it accepts fractional pixel measurements
    produced by image analysis rather than whole-image dimensions.
    """
    if dpi <= 0:
        raise ValueError(f"dpi must be positive, got {dpi}")
    return inches_to_mm(px / dpi)


def mm_to_px_length(mm: float, dpi: float) -> float:
    """Fractional pixel length of a millimetre measurement."""
    if dpi <= 0:
        raise ValueError(f"dpi must be positive, got {dpi}")
    return mm_to_inches(mm) * dpi
