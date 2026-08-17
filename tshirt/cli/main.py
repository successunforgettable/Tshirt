"""Gate 1a build. A thin adapter over `core` — it holds no logic of its own.

Everything below is orchestration: load data, call the core, write files, report.
Adding an HTTP layer or a browser UI later replaces this file and nothing else
(D-01).

Gate 1a proves that OUR SOFTWARE emits a correct DTF-ready file at the intended
physical size. It does not characterise the printer, who is experienced and
trusted. The default build therefore produces exactly one thing to send: the
export-check artefact. The full diagnostic calibration sheet and the
deterministic pipeline-test design sit behind `--diagnostic` and never run in the
default path.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from ..branddna import load_brand_dna
from ..calibration.export_check import build_export_check
from ..core import compose, package, size, validate
from ..core.profile import load_profile

ROOT = Path(__file__).resolve().parent.parent.parent
FONT = ROOT / "assets" / "fonts" / "LiberationSans-Bold.ttf"
PROFILE = ROOT / "profiles" / "dtf-printer-a.json"

PACKAGE_ID = "GATE-1A-EXPORT-CHECK"
EXPORT_CHECK_WIDTH_MM = 160.0
DPI = 300.0
PIPELINE_VERSION = "gate-1a.2"

# Diagnostic-only. Not part of Gate 1a.
DESIGN_TARGET_WIDTH_MM = 280.0


def _report(r: validate.ValidationReport) -> None:
    print(f"--- {r.asset} ---")
    for f in r.findings:
        print(f"  [{f.verdict:8}] {f.check}: {f.message}")
    print(f"  => {r.readiness}")
    if r.advisories:
        print("     advisory (printer-owned, non-blocking): "
              f"{[f.check for f in r.advisories]}")
    print()


def build(outdir: Path, diagnostic: bool = False) -> dict:
    brand = load_brand_dna()
    profile = load_profile(PROFILE)

    print(f"Brand      : {brand.brand}")
    print("Opaque terms (D-16, text-only): "
          f"{[e.canonical_name for e in brand.opaque_terms]}")
    print(f"Brand red  : {brand.colour_hex('brand red')}  <- unknown by design")
    print()

    pkg = outdir / PACKAGE_ID
    print_dir = pkg / "PRINT"

    # --- export-check artefact: the ONLY thing Gate 1a sends ------------------
    check = build_export_check(FONT, DPI, width_mm=EXPORT_CHECK_WIDTH_MM)
    spec = size.PhysicalSpec(check.image.width, check.image.height, DPI)
    print(f"Export check: {spec.width_px} x {spec.height_px} px "
          f"= {spec.width_mm:.2f} x {spec.height_mm:.2f} mm @ {DPI:.0f} DPI")
    print()

    check_path = package.save_png(check.image, print_dir / "export-check-v1.png", DPI)

    authoritative = [brand.canonical_brand_name, brand.exact_spelling("n-codes")]
    check_report = validate.validate(
        validate.AssetUnderTest(
            name="export-check-v1.png", rgba=check.rgba, image_format="PNG",
            mode="RGBA", declared_width_mm=spec.width_mm,
            declared_height_mm=spec.height_mm,
            rendered_strings=check.rendered_strings,
            authoritative_strings=authoritative,
            missing_glyph_chars=check.missing_glyph_chars,
        ),
        profile,
    )
    _report(check_report)

    check_pkg = package.describe_asset(check_path, "export_check",
                                       spec.width_mm, spec.height_mm, DPI)
    reports = [check_report]
    assets = [check_pkg]

    # --- diagnostics: never in the default Gate 1a path -----------------------
    diagnostics: dict = {}
    if diagnostic:
        from ..calibration.sheet import build_calibration_sheet
        diag_dir = pkg / "DIAGNOSTIC"

        cal = build_calibration_sheet(FONT, DPI, width_mm=200.0)
        cal_spec = size.PhysicalSpec(cal.image.width, cal.image.height, DPI)
        cal_path = package.save_png(cal.image, diag_dir / "calibration-v1.png", DPI)
        print(f"[diagnostic] calibration sheet: {cal_spec.width_mm:.1f} x "
              f"{cal_spec.height_mm:.1f} mm")

        target_px = size.required_px(DESIGN_TARGET_WIDTH_MM, DPI)
        design = compose.compose_incredible_you(FONT, target_px, DPI)
        d_spec = size.PhysicalSpec(design.image.width, design.image.height, DPI)
        design_path = package.save_png(design.image,
                                       diag_dir / "pipeline-test-design.png", DPI)
        print(f"[diagnostic] pipeline test design: {d_spec.width_mm:.1f} x "
              f"{d_spec.height_mm:.1f} mm  (NOT wearable; Gate 1b owns that)")
        print()

        diagnostics = {
            "calibration-v1.png": {
                "role": "diagnostic_calibration_sheet",
                "width_mm": round(cal_spec.width_mm, 3),
                "height_mm": round(cal_spec.height_mm, 3),
                "checksum": package.sha256_file(cal_path),
                "note": "Full printer-characterisation sheet. Not part of Gate 1a; "
                        "kept in case a specific problem ever needs isolating.",
            },
            "pipeline-test-design.png": {
                "role": "pipeline_test_artefact",
                "width_mm": round(d_spec.width_mm, 3),
                "height_mm": round(d_spec.height_mm, 3),
                "checksum": package.sha256_file(design_path),
                "note": "Exercises the deterministic engine end to end. Reviewed and "
                        "rejected as a wearable design; Gate 1b owns the first "
                        "wearable design.",
            },
        }

    package.write_print_spec(pkg / "print-spec.txt", assets, profile, reports)

    manifest = {
        "package_id": PACKAGE_ID,
        "generated": date.today().isoformat(),
        "gate": "1a",
        "gate_purpose": "Prove our software emits a correct DTF-ready file at the "
                        "intended physical size. Does not characterise the printer.",
        "pipeline_version": PIPELINE_VERSION,
        "ai_generation_used": False,
        "provider": None,
        "typography": {
            "font_file": str(FONT.relative_to(ROOT)),
            "font_licence": "SIL OFL 1.1",
            "deterministic": True,
            "rendered_strings": check.rendered_strings,
            "missing_glyphs": check.missing_glyph_chars,
            "authoritative_strings": authoritative,
        },
        "send_to_printer": [check_pkg.filename],
        "assets": [vars(a) for a in assets],
        "export_check_elements": check.elements,
        "export_check_regions": check.regions,
        "diagnostics_not_sent": diagnostics,
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
    print(f"SEND TO PRINTER: PRINT/{check_pkg.filename} + print-spec.txt")
    return manifest


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="tshirt", description="Gate 1a deterministic build")
    ap.add_argument("command", choices=["build"])
    ap.add_argument("--outdir", default=str(ROOT / "output"))
    ap.add_argument("--diagnostic", action="store_true",
                    help="also emit the full calibration sheet and the pipeline test "
                         "design into DIAGNOSTIC/. Not part of Gate 1a.")
    args = ap.parse_args(argv)

    manifest = build(Path(args.outdir), diagnostic=args.diagnostic)
    states = [r["readiness"] for r in manifest["validation"]]
    if validate.NOT_READY in states:
        print("NOT_READY - do not send", file=sys.stderr)
        return 1
    print("PRINT_READY - correct by every check we own.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
