"""Gate 1a build. A thin adapter over `core` — it holds no logic of its own.

Everything below is orchestration: load data, call the core, write files, report.
Adding an HTTP layer or a browser UI later replaces this file and nothing else
(D-01).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

import numpy as np

from ..branddna import load_brand_dna
from ..calibration.sheet import build_calibration_sheet
from ..core import compose, package, size, validate
from ..core.profile import load_profile

ROOT = Path(__file__).resolve().parent.parent.parent
FONT = ROOT / "assets" / "fonts" / "LiberationSans-Bold.ttf"
PROFILE = ROOT / "profiles" / "dtf-printer-a.json"

DESIGN_ID = "INCREDIBLE-YOU-001"
TARGET_WIDTH_MM = 280.0
DPI = 300.0
PIPELINE_VERSION = "gate-1a.1"

GARMENT = {
    "type": "T-shirt",
    "colour": "black",
    "size": "TBC",
    "placement": "large centred front",
}


def build_brief(brand) -> dict:
    """Structured brief for the Gate 1a production piece (spec 6.2)."""
    return {
        "design_id": DESIGN_ID,
        "concept": "The Incredible You - original typographic lockup",
        "message": brand.canonical_brand_name,
        "message_is_authoritative": True,
        "garment": GARMENT,
        "placement": GARMENT["placement"],
        "aesthetic": ["motivational", "headline-led", "restrained premium"],
        "palette": ["white"],
        "typography_role": "dominant",
        "graphic_complexity": "low",
        "creative_directions": 1,
        "brand": {
            "usage_tier": "brand_inspired",
            "vocabulary_used": [],
            "authoritative_strings": [brand.canonical_brand_name],
            "logo_asset": None,
        },
        "target_width_mm": TARGET_WIDTH_MM,
        "dpi": DPI,
    }


def build(outdir: Path) -> dict:
    brand = load_brand_dna()
    profile = load_profile(PROFILE)
    brief = build_brief(brand)

    tier = brief["brand"]["usage_tier"]
    if tier == "official_logo" and not brand.official_logo_available:
        raise SystemExit("official_logo requires a supplied brand mark asset (D-17).")

    print(f"Brand      : {brand.brand}")
    print(f"Usage tier : {tier}  (official_logo available: {brand.official_logo_available})")
    print(f"Opaque terms (D-16, text-only): "
          f"{[e.canonical_name for e in brand.opaque_terms]}")
    print(f"Brand red  : {brand.colour_hex('brand red')}  <- unknown by design")
    print()

    target_px = size.required_px(TARGET_WIDTH_MM, DPI)
    print(f"Target width: {TARGET_WIDTH_MM} mm @ {DPI:.0f} DPI -> {target_px} px")

    # --- production artwork ---------------------------------------------------
    result = compose.compose_incredible_you(FONT, target_px, DPI)
    design_spec = size.PhysicalSpec(result.image.width, result.image.height, DPI)
    print(f"Design      : {design_spec.width_px} x {design_spec.height_px} px "
          f"= {design_spec.width_mm:.2f} x {design_spec.height_mm:.2f} mm")

    # --- calibration sheet ----------------------------------------------------
    cal = build_calibration_sheet(FONT, DPI, width_mm=200.0)
    cal_spec = size.PhysicalSpec(cal.image.width, cal.image.height, DPI)
    print(f"Calibration : {cal_spec.width_px} x {cal_spec.height_px} px "
          f"= {cal_spec.width_mm:.2f} x {cal_spec.height_mm:.2f} mm")
    print()

    # --- write assets ---------------------------------------------------------
    pkg = outdir / DESIGN_ID
    print_dir = pkg / "PRINT"
    design_path = package.save_png(result.image, print_dir / "incredible-you-001.png", DPI)
    cal_path = package.save_png(cal.image, print_dir / "calibration-v1.png", DPI)

    # --- validate -------------------------------------------------------------
    design_asset = validate.AssetUnderTest(
        name="incredible-you-001.png",
        rgba=np.asarray(result.image.convert("RGBA")),
        image_format="PNG",
        mode="RGBA",
        declared_width_mm=design_spec.width_mm,
        declared_height_mm=design_spec.height_mm,
        rendered_strings=result.rendered_strings,
        authoritative_strings=brief["brand"]["authoritative_strings"],
        missing_glyph_chars=result.missing_glyph_chars,
    )
    cal_asset = validate.AssetUnderTest(
        name="calibration-v1.png",
        rgba=cal.rgba,
        image_format="PNG",
        mode="RGBA",
        declared_width_mm=cal_spec.width_mm,
        declared_height_mm=cal_spec.height_mm,
        rendered_strings=cal.rendered_strings,
        authoritative_strings=[brand.exact_spelling(t) for t in
                               ("n-codes", "e-codes", "inner-dna")],
        missing_glyph_chars=cal.missing_glyph_chars,
    )

    reports = [validate.validate(design_asset, profile), validate.validate(cal_asset, profile)]
    for r in reports:
        print(f"--- {r.asset} ---")
        for f in r.findings:
            print(f"  [{f.verdict:7}] {f.check}: {f.message}")
        print(f"  => readiness={r.readiness}")
        if r.awaiting_calibration:
            print(f"     awaiting calibration    : {[f.check for f in r.awaiting_calibration]}")
        if r.awaiting_printer_answer:
            print(f"     awaiting printer answer : {[f.check for f in r.awaiting_printer_answer]}")
        print()

    # --- package --------------------------------------------------------------
    design_pkg = package.describe_asset(design_path, "production",
                                        design_spec.width_mm, design_spec.height_mm, DPI)
    cal_pkg = package.describe_asset(cal_path, "calibration",
                                     cal_spec.width_mm, cal_spec.height_mm, DPI)

    package.write_print_spec(pkg / "print-spec.txt", design_pkg, cal_pkg,
                             profile, GARMENT, reports)

    manifest = {
        "design_id": DESIGN_ID,
        "generated": date.today().isoformat(),
        "gate": "1a",
        "pipeline_version": PIPELINE_VERSION,
        "ai_generation_used": False,
        "provider": None,
        "brief": brief,
        "typography": {
            "font_file": str(FONT.relative_to(ROOT)),
            "font_licence": "SIL OFL 1.1",
            "deterministic": True,
            "rendered_strings": result.rendered_strings,
            "missing_glyphs": result.missing_glyph_chars,
            "layout": result.layout,
        },
        "assets": [vars(design_pkg), vars(cal_pkg)],
        "calibration_elements": cal.elements,
        "printer_profile": {
            "name": profile.name,
            "confirmed": {f.name: f.value for f in profile.confirmed()},
            "assumed": {f.name: {"value": f.value, "confirm_via": f.confirm_via}
                        for f in profile.assumptions()},
            "unknown": [f.name for f in profile.unknowns()],
        },
        "validation": [r.summary() for r in reports],
    }
    package.write_manifest(pkg / "manifest.json", manifest)
    package.write_manifest(pkg / "validation.json",
                           {"reports": [r.summary() for r in reports]})

    print(f"Package written to {pkg.relative_to(ROOT)}")
    return manifest


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="tshirt", description="Gate 1a deterministic build")
    ap.add_argument("command", choices=["build"])
    ap.add_argument("--outdir", default=str(ROOT / "output"))
    args = ap.parse_args(argv)

    manifest = build(Path(args.outdir))
    states = [r["readiness"] for r in manifest["validation"]]
    if validate.NOT_READY in states:
        print("VALIDATION FAILED - do not send", file=sys.stderr)
        return 1
    if all(s == validate.PRINT_READY for s in states):
        print("All assets PRINT_READY.")
    else:
        print("All assets READY_FOR_CALIBRATION - NOT print-ready.")
        print("Unresolved checks become resolvable once the calibration transfer is "
              "measured and the printer answers the outstanding questions.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
