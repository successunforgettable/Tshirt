"""Deterministic print validation. Pure functions — no file I/O.

Five verdicts:

  PASS      the check ran and the asset satisfies it
  WARNING   worth a human look; does not block
  FAIL      our software emitted something wrong; blocks
  PENDING   a BLOCKING check could not run for want of an input; blocks
  ADVISORY  a measurement reported with no threshold to judge it against, because
            the threshold is the printer's to own; never blocks

No threshold is ever invented (D-11). PENDING and ADVISORY are the two honest
ways of saying "unknown", and they differ in who the unknown belongs to: PENDING
is a gap in what we need to verify ourselves, ADVISORY is a number we can measure
but have no standing to judge.
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
ADVISORY = "ADVISORY"

# --- what this validator is responsible for ----------------------------------
#
# It answers one question: did OUR SOFTWARE emit a correct, DTF-ready file at the
# intended physical size? It does not assess the printer, who is experienced and
# trusted.
#
# That splits the checks in two:
#
#   BLOCKING   our own correctness - transparency, dimensions, effective DPI,
#              bounds, canonical strings, format. A failure here is our bug and
#              must stop the file being sent.
#
#   ADVISORY   printer-owned tolerances such as minimum reliable stroke width and
#              partial-alpha behaviour. We can measure the artwork and report the
#              number, but the threshold belongs to the printer's process. With no
#              supplied threshold there is nothing to judge against, so these are
#              reported and never block.
#
# Two states, not three:
#
#   NOT_READY    a FAIL, or a BLOCKING check that could not run. Do not send.
#   PRINT_READY  every blocking check ran and passed. Advisories may be present.
#
# An earlier revision had a middle state for assets awaiting printer
# characterisation. That state now has no members: the checks that populated it
# are advisory, because characterising the printer is not this project's job.
# Removing it is a scope correction, not a relaxation - no threshold is invented,
# and a blocking check that cannot run still reports PENDING and still blocks.

NOT_READY = "NOT_READY"
PRINT_READY = "PRINT_READY"

# Who owns an unresolved item.
BY_PRINTER_EXPERTISE = "printer_expertise"  # trusted printer's process, not ours
BY_PRINTER_ANSWER = "printer_answer"        # a question we could ask if it mattered


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
    def advisories(self) -> list[Finding]:
        """Measurements reported without a threshold. Never affect readiness."""
        return [f for f in self.findings if f.verdict == ADVISORY]

    @property
    def readiness(self) -> str:
        """NOT_READY or PRINT_READY.

        A FAIL blocks. A blocking check that could not run (PENDING) also blocks —
        we never call a file correct on the strength of a check we skipped.
        ADVISORY findings never block, because the threshold they would be judged
        against belongs to the printer, not to us.
        """
        if self.failures or self.pending:
            return NOT_READY
        return PRINT_READY

    @property
    def is_print_ready(self) -> bool:
        return self.readiness == PRINT_READY

    def summary(self) -> dict:
        counts: dict[str, int] = {}
        for f in self.findings:
            counts[f.verdict] = counts.get(f.verdict, 0) + 1
        return {
            "asset": self.asset,
            "readiness": self.readiness,
            "print_ready": self.is_print_ready,
            "counts": counts,
            "blocking_failures": [f.check for f in self.failures],
            "blocking_unrunnable": [f.check for f in self.pending],
            "advisory": [f.check for f in self.advisories],
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
    The tolerance belongs to the printer's process, so with none supplied this
    reports the measurement as ADVISORY rather than guessing a threshold or
    blocking on someone else's unknown.
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
            "alpha_quality", ADVISORY,
            f"Soft (non-edge) partial alpha measured at {stats.soft_ratio:.4%} of inked pixels. "
            "No printer tolerance supplied; reported for information only.",
            detail, resolution=BY_PRINTER_EXPERTISE,
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
            out.append(Finding(f"max_{label}", ADVISORY,
                               f"Declared {label} {declared:.1f} mm. No printer maximum "
                               "supplied; reported for information only.",
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
            "minimum_feature", ADVISORY,
            f"Thinnest stroke (1st percentile) measured at {p1_mm:.3f} mm. "
            "No printer minimum supplied; reported for information only.",
            detail, resolution=BY_PRINTER_EXPERTISE,
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
