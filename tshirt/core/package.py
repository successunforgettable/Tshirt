"""Printer package export: deterministic tree, checksums, human-readable spec.

The package must make it impossible to confuse a preview with production
artwork, and must state every physical dimension explicitly so the printer never
has to infer one (spec 16).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from .profile import ASSUMED, CONFIRMED, UNKNOWN, PrinterProfile
from .validate import ValidationReport


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass
class PackagedAsset:
    filename: str
    role: str                # "production" | "calibration"
    width_px: int
    height_px: int
    width_mm: float
    height_mm: float
    dpi: float
    checksum: str
    bytes: int


def save_png(image: Image.Image, path: str | Path, dpi: float) -> Path:
    """Write RGBA PNG. The dpi tag is metadata only — never trusted on read."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGBA").save(path, format="PNG", dpi=(dpi, dpi), optimize=True)
    return path


def describe_asset(path: str | Path, role: str, width_mm: float,
                   height_mm: float, dpi: float) -> PackagedAsset:
    path = Path(path)
    with Image.open(path) as im:
        w, h = im.size
    return PackagedAsset(
        filename=path.name,
        role=role,
        width_px=w,
        height_px=h,
        width_mm=round(width_mm, 3),
        height_mm=round(height_mm, 3),
        dpi=dpi,
        checksum=sha256_file(path),
        bytes=path.stat().st_size,
    )


def _profile_lines(profile: PrinterProfile) -> list[str]:
    out = []
    for status, heading in ((CONFIRMED, "CONFIRMED BY PRINTER"),
                            (ASSUMED, "WORKING ASSUMPTIONS - NOT CONFIRMED"),
                            (UNKNOWN, "UNKNOWN - AWAITING MEASUREMENT")):
        fields = [f for f in profile.fields.values() if f.status == status]
        if not fields:
            continue
        out.append(f"  {heading}:")
        for f in sorted(fields, key=lambda x: x.name):
            val = "not supplied" if f.value is None else f.value
            out.append(f"    - {f.name}: {val}")
        out.append("")
    return out


def write_print_spec(path: str | Path, design: PackagedAsset, calibration: PackagedAsset,
                     profile: PrinterProfile, garment: dict, reports: list[ValidationReport]) -> Path:
    path = Path(path)
    lines: list[str] = []
    a = lines.append

    a("=" * 78)
    a("PRINT SPECIFICATION - THE INCREDIBLE YOU 001")
    a("=" * 78)
    a("")
    a("PROCESS: DTF transfer (confirmed by printer)")
    a("")
    a("*** DO NOT RESIZE. Both files are built at exact final print size. ***")
    a("*** DO NOT MIRROR. Artwork is supplied UNMIRRORED; we understand your")
    a("    RIP handles transfer mirroring. If that is wrong, please tell us")
    a("    BEFORE printing rather than mirroring the file yourself. ***")
    a("")
    a("PLEASE PLACE BOTH FILES ON THE SAME GANG SHEET / BATCH.")
    a("")
    a("-" * 78)
    a("FILE 1 - PRODUCTION ARTWORK")
    a("-" * 78)
    a(f"  Filename          : PRINT/{design.filename}")
    a(f"  Print size        : {design.width_mm:.1f} mm wide x {design.height_mm:.1f} mm high")
    a(f"  Pixel dimensions  : {design.width_px} x {design.height_px} px")
    a(f"  Resolution        : {design.dpi:.0f} DPI at the size above")
    a(f"  Colour            : RGB / sRGB, 8-bit, with alpha")
    a(f"  Background        : fully transparent")
    a(f"  SHA-256           : {design.checksum}")
    a("")
    a("  Garment           : "
      f"{garment.get('colour','')} {garment.get('type','')}, size {garment.get('size','TBC')}")
    a(f"  Placement         : {garment.get('placement','')}")
    a("")
    a("-" * 78)
    a("FILE 2 - CALIBRATION SHEET")
    a("-" * 78)
    a(f"  Filename          : PRINT/{calibration.filename}")
    a(f"  Print size        : {calibration.width_mm:.1f} mm wide x "
      f"{calibration.height_mm:.1f} mm high")
    a(f"  Pixel dimensions  : {calibration.width_px} x {calibration.height_px} px")
    a(f"  Resolution        : {calibration.dpi:.0f} DPI at the size above")
    a(f"  SHA-256           : {calibration.checksum}")
    a("")
    a("  This sheet is a measurement instrument, not a design. It lets us")
    a("  characterise your process so future files arrive correct first time.")
    a("  Please print it at exactly the stated size alongside File 1.")
    a("")
    a("-" * 78)
    a("PRINTER PROFILE STATE")
    a("-" * 78)
    lines.extend(_profile_lines(profile))
    a("-" * 78)
    a("VALIDATION SUMMARY")
    a("-" * 78)
    for r in reports:
        s = r.summary()
        a(f"  {r.asset}: {s['readiness']}  {s['counts']}")
        for f in r.findings:
            if f.verdict in ("FAIL", "WARNING", "PENDING"):
                a(f"    [{f.verdict}] {f.check}: {f.message}")
    a("")
    a("  READY_FOR_CALIBRATION means: no failures, and safe to print as part of")
    a("  this calibration run - but NOT yet proven print-ready, because some")
    a("  checks could not run against a real tolerance. PENDING is not a pass.")
    a("  Establishing those tolerances is exactly what this transfer is for.")
    a("")
    a("=" * 78)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_manifest(path: str | Path, payload: dict) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    return path
