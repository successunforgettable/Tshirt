"""Printer package export: deterministic tree, checksums, human-readable spec.

The package must make it impossible to confuse a preview with production
artwork, and must state every physical dimension explicitly so the printer never
has to infer one (spec 16).
"""

from __future__ import annotations

import hashlib
import json
import textwrap
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


# The print spec is read by a human on unknown software — a phone, a mail client,
# a print shop's terminal, a plain-text previewer. It is therefore written as
# deliberately boring 7-bit ASCII, wrapped under 80 columns, with no long runs of
# "=" or "-". Those runs are what Markdown treats as setext headings and rules, so
# a previewer that guesses at Markdown reformats the whole document.
SPEC_WIDTH = 78

_ASCII_MAP = {
    "—": "-", "–": "-", "−": "-",     # em/en dash, minus
    "‘": "'", "’": "'",                     # curly single quotes
    "“": '"', "”": '"',                     # curly double quotes
    "…": "...", " ": " ", "×": "x",    # ellipsis, nbsp, times
}


def to_ascii(text: str) -> str:
    """Flatten typographic punctuation to 7-bit ASCII.

    Rich messages stay intact in manifest.json and validation.json; only the
    human-facing spec is flattened, so nothing is lost.
    """
    for src, dst in _ASCII_MAP.items():
        text = text.replace(src, dst)
    return text.encode("ascii", "replace").decode("ascii")


def wrap_lines(text: str, indent: str = "", width: int = SPEC_WIDTH) -> list[str]:
    """Wrap to `width`, preserving an indent. Long unbreakable tokens are kept whole."""
    wrapped = textwrap.wrap(
        to_ascii(text), width=width, initial_indent=indent, subsequent_indent=indent,
        break_long_words=False, break_on_hyphens=False,
    )
    return wrapped or [indent.rstrip()]


def _profile_lines(profile: PrinterProfile) -> list[str]:
    out = []
    for status, heading in ((CONFIRMED, "Confirmed by printer"),
                            (ASSUMED, "Working assumptions (NOT confirmed)"),
                            (UNKNOWN, "Unknown (awaiting measurement)")):
        fields = [f for f in profile.fields.values() if f.status == status]
        if not fields:
            continue
        out.append(f"  {heading}:")
        for f in sorted(fields, key=lambda x: x.name):
            val = "not supplied" if f.value is None else f.value
            out.extend(wrap_lines(f"- {f.name}: {val}", indent="    "))
        out.append("")
    return out


def write_print_spec(path: str | Path, design: PackagedAsset, calibration: PackagedAsset,
                     profile: PrinterProfile, garment: dict, reports: list[ValidationReport]) -> Path:
    path = Path(path)
    lines: list[str] = []
    a = lines.append

    a("PRINT SPECIFICATION")
    a("THE INCREDIBLE YOU 001")
    a("")
    a("Process: DTF transfer (confirmed by printer)")
    a("")
    a("IMPORTANT")
    a("  1. DO NOT RESIZE. Both files are built at exact final print size.")
    a("  2. DO NOT MIRROR. Artwork is supplied UNMIRRORED; we understand your")
    a("     RIP handles transfer mirroring. If that is wrong, please tell us")
    a("     BEFORE printing rather than mirroring the file yourself.")
    a("  3. Please place both files on the same gang sheet / batch.")
    a("")

    def asset_block(title: str, asset: PackagedAsset) -> None:
        a(title)
        a(f"  Filename    : PRINT/{asset.filename}")
        a(f"  Print size  : {asset.width_mm:.1f} mm wide x {asset.height_mm:.1f} mm high")
        a(f"  Pixels      : {asset.width_px} x {asset.height_px}")
        a(f"  Resolution  : {asset.dpi:.0f} DPI at the size above")
        a(f"  Colour      : RGB / sRGB, 8-bit, with alpha")
        a(f"  Background  : fully transparent")
        a(f"  SHA-256     :")
        a(f"    {asset.checksum}")
        a("")

    asset_block("[1] PRODUCTION ARTWORK", design)
    a(f"  Garment     : {garment.get('colour','')} {garment.get('type','')}, "
      f"size {garment.get('size','TBC')}")
    a(f"  Placement   : {garment.get('placement','')}")
    a("")

    asset_block("[2] CALIBRATION SHEET", calibration)
    a("  This sheet is a measurement instrument, not a design. It lets us")
    a("  characterise your process so future files arrive correct first time.")
    a("  Please print it at exactly the stated size alongside file 1.")
    a("")

    a("[3] PRINTER PROFILE STATE")
    lines.extend(_profile_lines(profile))

    a("[4] VALIDATION SUMMARY")
    for r in reports:
        s = r.summary()
        a(f"  {r.asset}: {s['readiness']}")
        for f in r.findings:
            if f.verdict in ("FAIL", "WARNING", "PENDING"):
                lines.extend(wrap_lines(f"[{f.verdict}] {f.check}: {f.message}",
                                        indent="    "))
    a("")
    a("  READY_FOR_CALIBRATION means: no failures, and safe to print as part of")
    a("  this calibration run, but NOT yet proven print-ready, because some")
    a("  checks could not run against a real tolerance. PENDING is not a pass.")
    a("  Establishing those tolerances is exactly what this transfer is for.")
    a("")
    a("End of specification.")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(to_ascii("\n".join(lines)) + "\n", encoding="ascii")
    return path


def write_manifest(path: str | Path, payload: dict) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    return path
