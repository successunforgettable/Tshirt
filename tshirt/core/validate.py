"""Deterministic print validation. Pure functions — no file I/O.

Four verdicts, and the fourth exists on purpose:

  PASS     the check ran and the asset satisfies it
  WARNING  worth a human look; does not block export
  FAIL     blocks print-ready status unless explicitly overridden
  PENDING  the check CANNOT run because the printer has not supplied the
           threshold it needs

PENDING is not a soft pass. It is the mechanism that stops the system inventing
tolerances it does not have (D-11). Before physical calibration, minimum stroke
width and partial-alpha tolerance are genuinely unknown, and reporting them as
PASS would be a lie that reaches the printer. The measurement is still reported
so the calibration transfer can turn it into a real threshold.

Findings roll up into one of three asset states — NOT_READY,
READY_FOR_CALIBRATION, PRINT_READY — rather than a boolean. A boolean forces an
asset with unmeasured print behaviour into either "not ready" (false: it is
perfectly sendable for calibration) or "print ready" (false: nothing about its
physical behaviour has been established). The middle state is the honest one for
a first transfer, and it is where Gate 1a assets sit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from . import analysis, size
from .profile import PrinterProfile

PASS = "PASS"
WARNING = "WARNING"
FAIL = "FAIL"
PENDING = "PENDING"

# --- asset readiness ---------------------------------------------------------
#
# Three states, because two are not enough. An asset can be structurally sound
# and still not be proven fit for production, and collapsing that into a boolean
# produces a green label on artwork whose print behaviour nobody has measured.
#
#   NOT_READY              a FAIL is present. Do not send.
#   READY_FOR_CALIBRATION  no FAIL, but checks remain unresolved. Safe to send as
#                          part of a calibration run; NOT proven print-ready.
#   PRINT_READY            no FAIL and nothing unresolved. Every required check
#                          ran against a real threshold and passed.
#
# PRINT_READY is deliberately hard to reach: any PENDING at all withholds it.
# Weakening PENDING to obtain a green status would defeat the reason PENDING
# exists.

NOT_READY = "NOT_READY"
READY_FOR_CALIBRATION = "READY_FOR_CALIBRATION"
PRINT_READY = "PRINT_READY"

# How an unresolved check gets resolved. These have different owners and
# different timescales, so they are reported separately.
BY_CALIBRATION = "calibration"        # measure it from the physical transfer
BY_PRINTER_ANSWER = "printer_answer"  # ask the printer


@dataclass(frozen=True)
class Finding:
    check: str
    verdict: str
    message: str
    detail: dict[str, Any] = field(default_factory=dict)
    resolution: str | None = None      # set on PENDING: how it becomes resolvable

    def as_dict(self) -> dict:
        out = {
            "check": self.check,
            "verdict": self.verdict,
            "message": self.message,
            "detail": self.detail,
        }
        if self.resolution:
            out["resolution"] = self.resolution
        return out


@dataclass
class ValidationReport:
    asset: str
    findings: list[Finding] = field(default_factory=list)

    def add(self, *findings: Finding) -> None:
        self.findings.extend(findings)

    @property
    def failures(self) -> list[Finding]:
        return [f for f in self.findings if f.verdict == FAIL]

    @property
    def warnings(self) -> list[Finding]:
        return [f for f in self.findings if f.verdict == WARNING]

    @property
    def pending(self) -> list[Finding]:
        return [f for f in self.findings if f.verdict == PENDING]

    @property
    def awaiting_calibration(self) -> list[Finding]:
        return [f for f in self.pending if f.resolution == BY_CALIBRATION]

    @property
    def awaiting_printer_answer(self) -> list[Finding]:
        return [f for f in self.pending if f.resolution == BY_PRINTER_ANSWER]

    @property
    def readiness(self) -> str:
        """NOT_READY / READY_FOR_CALIBRATION / PRINT_READY.

        Any PENDING withholds PRINT_READY, whatever its resolution path. An
        unmeasured tolerance is unmeasured regardless of who is going to supply it.
        """
        if self.failures:
            return NOT_READY
        if self.pending:
            return READY_FOR_CALIBRATION
        return PRINT_READY

    @property
    def is_print_ready(self) -> bool:
        """True only in the PRINT_READY state. Never true with anything pending."""
        return self.readiness == PRINT_READY

    @property
    def can_send_for_calibration(self) -> bool:
        return self.readiness in (READY_FOR_CALIBRATION, PRINT_READY)

    def summary(self) -> dict:
        counts: dict[str, int] = {}
        for f in self.findings:
            counts[f.verdict] = counts.get(f.verdict, 0) + 1
        return {
            "asset": self.asset,
            "readiness": self.readiness,
            "print_ready": self.is_print_ready,
            "can_send_for_calibration": self.can_send_for_calibration,
            "counts": counts,
            "unresolved": {
                "awaiting_calibration": [f.check for f in self.awaiting_calibration],
                "awaiting_printer_answer": [f.check for f in self.awaiting_printer_answer],
            },
            "findings": [f.as_dict() for f in self.findings],
        }


@dataclass
class AssetUnderTest:
    """Everything validation needs, already loaded. Keeps this module I/O-free."""

    name: str
    rgba: Any                      # numpy array, HxWx4 uint8
    image_format: str              # e.g. "PNG"
    mode: str                      # e.g. "RGBA"
    declared_width_mm: float
    declared_height_mm: float
    rendered_strings: list[str] = field(default_factory=list)
    authoritative_strings: list[str] = field(default_factory=list)
    missing_glyph_chars: list[str] = field(default_factory=list)


# --- individual checks -------------------------------------------------------


def check_format(asset: AssetUnderTest, profile: PrinterProfile) -> Finding:
    accepted = profile.get("accepted_formats")
    if not accepted.is_known:
        return Finding("format", PENDING, "Accepted formats not supplied by printer.",
                       resolution=BY_PRINTER_ANSWER)
    if asset.image_format.upper() in [a.upper() for a in accepted.value]:
        return Finding(
            "format", PASS,
            f"{asset.image_format} is accepted.",
            {"format": asset.image_format, "accepted": accepted.value, "status": accepted.status},
        )
    return Finding(
        "format", FAIL,
        f"{asset.image_format} is not in accepted formats {accepted.value}.",
        {"format": asset.image_format, "accepted": accepted.value},
    )


def check_colour_space(asset: AssetUnderTest, profile: PrinterProfile) -> Finding:
    fld = profile.get("colour_space")
    if not fld.is_known:
        return Finding("colour_space", PENDING, "Colour space not supplied by printer.",
                       resolution=BY_PRINTER_ANSWER)
    is_rgb = asset.mode in ("RGBA", "RGB")
    verdict = PASS if is_rgb else FAIL
    return Finding(
        "colour_space", verdict,
        f"Image mode {asset.mode} against profile {fld.value} ({fld.status}).",
        {"mode": asset.mode, "profile_value": fld.value, "profile_status": fld.status},
    )


def check_transparency(asset: AssetUnderTest, profile: PrinterProfile,
                       stats: analysis.AlphaStats) -> list[Finding]:
    out: list[Finding] = []
    requires = profile.get("requires_transparency")

    if asset.mode != "RGBA":
        out.append(Finding("alpha_channel", FAIL,
                           f"Image mode is {asset.mode}; a real alpha channel is required."))
        return out
    out.append(Finding("alpha_channel", PASS, "RGBA alpha channel present."))

    if requires.is_known and requires.value:
        if stats.transparent_px == 0:
            out.append(Finding(
                "transparency_present", FAIL,
                "No transparent pixels: artwork would print with a solid background.",
                {"transparent_px": 0},
            ))
        else:
            out.append(Finding(
                "transparency_present", PASS,
                f"{stats.transparent_px:,} transparent pixels "
                f"({stats.transparent_px / stats.total_px:.1%} of canvas).",
                {"transparent_px": stats.transparent_px, "total_px": stats.total_px},
            ))

    if stats.stray_colour_px:
        out.append(Finding(
            "stray_colour_in_transparent", WARNING,
            f"{stats.stray_colour_px:,} fully transparent pixels carry colour data.",
            {"stray_colour_px": stats.stray_colour_px},
        ))
    else:
        out.append(Finding("stray_colour_in_transparent", PASS,
                           "No colour data in fully transparent pixels."))
    return out


def check_alpha_quality(asset: AssetUnderTest, profile: PrinterProfile,
                        stats: analysis.AlphaStats) -> Finding:
    """Soft (non-edge) partial alpha is the dominant DTF failure mode.

    Over a white underbase, glows and gradients-to-transparent print as haze.
    The tolerance is printer-specific and currently unmeasured, so this reports
    PENDING with the measurement attached rather than guessing a threshold.
    """
    detail = {
        "inked_px": stats.inked_px,
        "partial_px": stats.partial_px,
        "partial_ratio": round(stats.partial_ratio, 6),
        "soft_px": stats.soft_px,
        "soft_ratio": round(stats.soft_ratio, 6),
        "edge_band_px": stats.edge_band_px,
    }
    tol = profile.get("max_partial_alpha_ratio")
    if not tol.is_known:
        return Finding(
            "alpha_quality", PENDING,
            f"Soft (non-edge) partial alpha measured at {stats.soft_ratio:.4%} of inked pixels. "
            "Printer tolerance unknown — to be established by the calibration alpha step wedge.",
            detail, resolution=BY_CALIBRATION,
        )
    verdict = PASS if stats.soft_ratio <= tol.value else FAIL
    return Finding(
        "alpha_quality", verdict,
        f"Soft partial alpha {stats.soft_ratio:.4%} against tolerance {tol.value:.4%}.",
        {**detail, "tolerance": tol.value, "tolerance_status": tol.status},
    )


def check_effective_dpi(asset: AssetUnderTest, profile: PrinterProfile) -> Finding:
    fld = profile.get("required_dpi")
    height_px, width_px = asset.rgba.shape[0], asset.rgba.shape[1]
    actual_w = size.effective_dpi(width_px, asset.declared_width_mm)
    actual_h = size.effective_dpi(height_px, asset.declared_height_mm)
    detail = {
        "effective_dpi_width": round(actual_w, 3),
        "effective_dpi_height": round(actual_h, 3),
        "width_px": width_px,
        "height_px": height_px,
        "declared_width_mm": round(asset.declared_width_mm, 3),
        "declared_height_mm": round(asset.declared_height_mm, 3),
    }
    if not fld.is_known:
        return Finding("effective_dpi", PENDING,
                       "Required DPI not supplied by printer.", detail,
                       resolution=BY_PRINTER_ANSWER)
    ok = actual_w >= fld.value - 0.5 and actual_h >= fld.value - 0.5
    return Finding(
        "effective_dpi", PASS if ok else FAIL,
        f"Computed {actual_w:.1f} x {actual_h:.1f} DPI against required "
        f"{fld.value} ({fld.status}).",
        {**detail, "required_dpi": fld.value, "required_dpi_status": fld.status},
    )


def check_max_dimensions(asset: AssetUnderTest, profile: PrinterProfile) -> list[Finding]:
    out = []
    for fname, declared, label in (
        ("max_width_mm", asset.declared_width_mm, "width"),
        ("max_height_mm", asset.declared_height_mm, "height"),
    ):
        fld = profile.get(fname)
        if not fld.is_known:
            out.append(Finding(f"max_{label}", PENDING,
                               f"Maximum {label} not supplied by printer.",
                               {f"declared_{label}_mm": round(declared, 2)},
                               resolution=BY_PRINTER_ANSWER))
        elif declared <= fld.value:
            out.append(Finding(f"max_{label}", PASS,
                               f"{declared:.1f} mm within maximum {fld.value} mm."))
        else:
            out.append(Finding(f"max_{label}", FAIL,
                               f"{declared:.1f} mm exceeds maximum {fld.value} mm."))
    return out


def check_minimum_feature(asset: AssetUnderTest, profile: PrinterProfile,
                          strokes: analysis.StrokeStats, dpi: float) -> Finding:
    fld = profile.get("min_reliable_stroke_mm")
    if strokes.p1_px is None:
        return Finding("minimum_feature", WARNING, "No opaque pixels to measure.")

    p1_mm = size.px_to_mm_length(strokes.p1_px, dpi)
    min_mm = size.px_to_mm_length(strokes.min_px, dpi)
    detail = {
        "p1_stroke_px": round(strokes.p1_px, 2),
        "p1_stroke_mm": round(p1_mm, 4),
        "min_stroke_px": strokes.min_px,
        "min_stroke_mm": round(min_mm, 4),
        "method_notes": strokes.notes,
    }
    if not fld.is_known:
        return Finding(
            "minimum_feature", PENDING,
            f"Thinnest stroke (1st percentile) measured at {p1_mm:.3f} mm. "
            "Printer minimum unknown — to be established by the calibration stroke ladder.",
            detail, resolution=BY_CALIBRATION,
        )
    verdict = PASS if p1_mm >= fld.value else FAIL
    return Finding(
        "minimum_feature", verdict,
        f"Thinnest stroke {p1_mm:.3f} mm against minimum {fld.value} mm ({fld.status}).",
        {**detail, "min_reliable_stroke_mm": fld.value},
    )


def check_rendered_bounds(asset: AssetUnderTest, dpi: float,
                          bbox: analysis.BBox | None) -> Finding:
    height_px, width_px = asset.rgba.shape[0], asset.rgba.shape[1]
    if bbox is None:
        return Finding("rendered_bounds", FAIL, "Asset contains no ink at all.")

    margin = {
        "left_px": bbox.left,
        "top_px": bbox.top,
        "right_px": width_px - 1 - bbox.right,
        "bottom_px": height_px - 1 - bbox.bottom,
    }
    detail = {
        "canvas_px": [width_px, height_px],
        "inked_bbox": bbox.as_dict(),
        "inked_width_mm": round(size.px_to_mm(bbox.width, dpi), 3),
        "inked_height_mm": round(size.px_to_mm(bbox.height, dpi), 3),
        "transparent_margin_px": margin,
    }
    worst = max(margin.values())
    if worst == 0:
        return Finding("rendered_bounds", PASS,
                       "Ink extends to every canvas edge: declared size is the artwork size.",
                       detail)
    worst_mm = size.px_to_mm_length(worst, dpi)
    verdict = WARNING if worst_mm > 1.0 else PASS
    return Finding(
        "rendered_bounds", verdict,
        f"Largest transparent margin {worst} px ({worst_mm:.2f} mm). "
        "Declared physical size includes empty film." if verdict == WARNING
        else f"Transparent margin within 1 mm ({worst_mm:.2f} mm).",
        detail,
    )


def _is_boundary(ch: str | None) -> bool:
    """True at a token edge. Alphanumerics and hyphens are NOT boundaries.

    Hyphens are excluded deliberately: without that, approved 'N-Codes' would
    match inside a corrupted 'N-Codes-X', and the check would pass on wrong
    artwork.
    """
    return ch is None or not (ch.isalnum() or ch == "-")


def contains_exact_token(haystack: str, needle: str) -> bool:
    """Byte-exact occurrence of `needle` in `haystack` at token boundaries.

    Whole-string equality is too strict — an approved term legitimately appears
    inside a longer rendered line. Naive substring matching is too loose, since
    it would accept the term glued to adjacent characters. Boundary-anchored
    exact matching is the correct middle: the characters must be identical, and
    the term must stand alone.
    """
    start = 0
    while (idx := haystack.find(needle, start)) != -1:
        before = haystack[idx - 1] if idx > 0 else None
        after_idx = idx + len(needle)
        after = haystack[after_idx] if after_idx < len(haystack) else None
        if _is_boundary(before) and _is_boundary(after):
            return True
        start = idx + 1
    return False


def check_authoritative_strings(asset: AssetUnderTest) -> list[Finding]:
    """Byte-exact comparison of rendered wording against approved strings.

    Scope, stated honestly: this compares the strings the compositor was given
    against the strings Brand DNA approved. It does not read pixels. Because
    typography is rendered deterministically from those strings, the chain holds
    — but it verifies the pipeline's input, not its output. The glyph-coverage
    check below is what protects the pixels.
    """
    out: list[Finding] = []
    if not asset.authoritative_strings:
        out.append(Finding("authoritative_strings", PASS,
                           "No authoritative strings declared for this asset."))
        return out

    rendered = list(asset.rendered_strings)
    for expected in asset.authoritative_strings:
        if expected in rendered:
            out.append(Finding(
                "authoritative_string", PASS,
                f"Exact match rendered as a complete string: {expected!r}",
                {"expected": expected, "match": "whole_string"},
            ))
            continue

        carriers = [r for r in rendered if contains_exact_token(r, expected)]
        if carriers:
            out.append(Finding(
                "authoritative_string", PASS,
                f"Exact match rendered within: {carriers[0]!r}",
                {"expected": expected, "match": "token", "carriers": carriers},
            ))
        else:
            near = [r for r in rendered if expected.lower().replace("-", "").replace(" ", "")
                    in r.lower().replace("-", "").replace(" ", "")]
            out.append(Finding(
                "authoritative_string", FAIL,
                f"Approved string {expected!r} was not rendered byte-exactly."
                + (f" Closest rendered: {near[:3]!r} — check hyphens, spacing and capitalisation."
                   if near else " No similar string was rendered at all."),
                {"expected": expected, "near_misses": near[:3],
                 "rendered_count": len(rendered)},
            ))

    if asset.missing_glyph_chars:
        out.append(Finding(
            "glyph_coverage", FAIL,
            f"Font lacks glyphs for: {asset.missing_glyph_chars!r}. "
            "These would render as substitution boxes.",
            {"missing": asset.missing_glyph_chars},
        ))
    else:
        out.append(Finding("glyph_coverage", PASS,
                           "Font provides a glyph for every character rendered."))
    return out


# --- orchestration -----------------------------------------------------------


def validate(asset: AssetUnderTest, profile: PrinterProfile) -> ValidationReport:
    report = ValidationReport(asset=asset.name)
    stats = analysis.alpha_stats(asset.rgba)
    bbox = analysis.inked_bbox(asset.rgba)
    strokes = analysis.stroke_stats(asset.rgba)

    dpi_field = profile.get("required_dpi")
    dpi = dpi_field.value if dpi_field.is_known else size.effective_dpi(
        asset.rgba.shape[1], asset.declared_width_mm
    )

    report.add(check_format(asset, profile))
    report.add(check_colour_space(asset, profile))
    report.add(*check_transparency(asset, profile, stats))
    report.add(check_alpha_quality(asset, profile, stats))
    report.add(check_effective_dpi(asset, profile))
    report.add(*check_max_dimensions(asset, profile))
    report.add(check_minimum_feature(asset, profile, strokes, dpi))
    report.add(check_rendered_bounds(asset, dpi, bbox))
    report.add(*check_authoritative_strings(asset))
    return report
