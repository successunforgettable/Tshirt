"""FileProvider escape hatch, printer-profile status handling, and packaging."""

import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from tshirt.core import package
from tshirt.core.profile import ASSUMED, CONFIRMED, UNKNOWN, load_profile
from tshirt.providers.base import ImageProvider, ProviderUnavailable
from tshirt.providers.file import FileProvider

ROOT = Path(__file__).resolve().parent.parent


class TestFileProvider(unittest.TestCase):
    """The non-AI path must work with no key, no network, no account (D-05)."""

    def test_satisfies_the_provider_protocol(self):
        self.assertIsInstance(FileProvider(), ImageProvider)

    def test_loads_artwork_from_a_brief(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "art.png"
            Image.new("RGBA", (10, 10), (255, 0, 0, 255)).save(p)
            img = FileProvider().generate({"source_image": str(p)})
            self.assertEqual(img.size, (10, 10))
            self.assertEqual(img.mode, "RGBA")

    def test_converts_to_rgba(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "art.jpg"
            Image.new("RGB", (8, 8), (0, 128, 255)).save(p)
            self.assertEqual(FileProvider().generate({"source_image": str(p)}).mode, "RGBA")

    def test_missing_source_raises_clearly(self):
        with self.assertRaises(ProviderUnavailable):
            FileProvider().generate({})

    def test_missing_file_raises_clearly(self):
        with self.assertRaises(ProviderUnavailable):
            FileProvider().generate({"source_image": "/nonexistent/x.png"})

    def test_edit_is_honestly_unsupported(self):
        with self.assertRaises(ProviderUnavailable):
            FileProvider().edit(Image.new("RGBA", (4, 4)), "make it bolder")


class TestPrinterProfile(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profile = load_profile(ROOT / "profiles" / "dtf-printer-a.json")

    def test_physical_measurement_promoted_size_fields_to_confirmed(self):
        """Gate 1a measured 100 mm on both axes: the printer does not rescale."""
        self.assertEqual(self.profile.get("printer_resizes_files").value, False)
        self.assertEqual(self.profile.get("printer_resizes_files").status, CONFIRMED)
        self.assertEqual(self.profile.get("required_dpi").status, CONFIRMED)

    def test_a_size_measurement_does_not_confirm_colour_or_mirroring(self):
        """Measuring 100 mm says nothing about colour or which way round it presses."""
        self.assertEqual(self.profile.get("colour_space").status, ASSUMED)
        self.assertEqual(self.profile.get("rip_handles_mirroring").status, ASSUMED)

    def test_dtf_and_png_are_confirmed(self):
        self.assertEqual(self.profile.get("process").value, "DTF")
        self.assertEqual(self.profile.get("process").status, CONFIRMED)
        self.assertEqual(self.profile.get("accepted_formats").status, CONFIRMED)
        self.assertTrue(self.profile.get("requires_transparency").value)

    def test_working_baseline_is_marked_assumed_not_confirmed(self):
        # required_dpi moved to confirmed once the Gate 1a transfer was measured.
        for name in ("colour_space", "rip_handles_mirroring"):
            f = self.profile.get(name)
            self.assertEqual(f.status, ASSUMED, f"{name} must not be presented as confirmed")
            self.assertIsNotNone(f.confirm_via, f"{name} must say how it gets confirmed")

    def test_tolerances_remain_unknown(self):
        for name in ("min_reliable_stroke_mm", "max_partial_alpha_ratio",
                     "max_width_mm", "min_negative_space_mm"):
            f = self.profile.get(name)
            self.assertEqual(f.status, UNKNOWN)
            self.assertIsNone(f.value, f"{name} must not be invented")

    def test_unknown_fields_are_not_treated_as_known(self):
        self.assertFalse(self.profile.get("min_reliable_stroke_mm").is_known)
        self.assertTrue(self.profile.get("required_dpi").is_known)

    def test_absent_field_defaults_to_unknown(self):
        self.assertEqual(self.profile.get("never_defined").status, UNKNOWN)

    def test_assumptions_are_enumerable_for_reporting(self):
        names = {f.name for f in self.profile.assumptions()}
        self.assertEqual(names, {"colour_space", "rip_handles_mirroring"})


class TestPackaging(unittest.TestCase):
    def test_checksum_is_stable_and_content_sensitive(self):
        with tempfile.TemporaryDirectory() as td:
            a, b = Path(td) / "a.png", Path(td) / "b.png"
            Image.new("RGBA", (10, 10), (255, 255, 255, 255)).save(a)
            Image.new("RGBA", (10, 10), (255, 255, 255, 255)).save(b)
            self.assertEqual(package.sha256_file(a), package.sha256_file(b))
            Image.new("RGBA", (10, 10), (0, 0, 0, 255)).save(b)
            self.assertNotEqual(package.sha256_file(a), package.sha256_file(b))

    def test_saved_png_keeps_alpha(self):
        with tempfile.TemporaryDirectory() as td:
            p = package.save_png(Image.new("RGBA", (10, 10), (255, 255, 255, 0)),
                                 Path(td) / "out.png", 300)
            with Image.open(p) as im:
                self.assertEqual(im.mode, "RGBA")
                self.assertEqual(im.format, "PNG")

    def test_describe_asset_reports_physical_and_pixel_dimensions(self):
        with tempfile.TemporaryDirectory() as td:
            p = package.save_png(Image.new("RGBA", (3308, 1202)), Path(td) / "d.png", 300)
            a = package.describe_asset(p, "production", 280.08, 101.77, 300)
            self.assertEqual((a.width_px, a.height_px), (3308, 1202))
            self.assertAlmostEqual(a.width_mm, 280.08, places=2)
            self.assertEqual(len(a.checksum), 64)
            self.assertGreater(a.bytes, 0)

    def test_manifest_round_trips(self):
        with tempfile.TemporaryDirectory() as td:
            p = package.write_manifest(Path(td) / "m.json", {"design_id": "X", "n": 1})
            self.assertEqual(json.loads(p.read_text())["design_id"], "X")


class TestPrintSpecPortability(unittest.TestCase):
    """The spec is opened on unknown software, so it stays deliberately boring.

    A print shop may read it on a phone, in a mail client, or in a terminal.
    Anything that invites a previewer to reinterpret the document is removed.
    """

    def test_ascii_flattens_typographic_punctuation(self):
        self.assertEqual(package.to_ascii("a — b – c"), "a - b - c")
        self.assertEqual(package.to_ascii("‘x’ “y”"), "'x' \"y\"")
        self.assertEqual(package.to_ascii("wait…"), "wait...")

    def test_ascii_output_is_encodable(self):
        package.to_ascii("emoji \U0001F600 and é").encode("ascii")

    def test_wrap_respects_width_and_indent(self):
        out = package.wrap_lines("word " * 60, indent="    ")
        for line in out:
            self.assertLessEqual(len(line), package.SPEC_WIDTH)
            self.assertTrue(line.startswith("    "))

    def test_wrap_keeps_long_tokens_whole(self):
        """A SHA-256 must never be broken across lines - it would be unusable."""
        digest = "a" * 64
        out = package.wrap_lines(digest, indent="  ")
        self.assertIn(digest, "".join(out))

    def test_wrap_never_returns_empty(self):
        self.assertEqual(package.wrap_lines(""), [""])

    def test_generated_spec_is_plain_ascii_and_narrow(self):
        from tshirt.core.profile import load_profile
        from tshirt.core.validate import ValidationReport
        with tempfile.TemporaryDirectory() as td:
            p = package.save_png(Image.new("RGBA", (100, 100)), Path(td) / "a.png", 300)
            asset = package.describe_asset(p, "production", 8.47, 8.47, 300)
            spec = package.write_print_spec(
                Path(td) / "print-spec.txt", [asset],
                load_profile(ROOT / "profiles" / "dtf-printer-a.json"),
                [ValidationReport(asset="a.png")],
            )
            raw = spec.read_bytes()
            raw.decode("ascii")                       # no non-ASCII bytes at all
            self.assertNotIn(b"\r", raw)              # no CRLF
            text = raw.decode("ascii")
            for i, line in enumerate(text.splitlines(), 1):
                self.assertLessEqual(len(line), package.SPEC_WIDTH,
                                     f"line {i} is {len(line)} chars")

    def test_generated_spec_has_no_setext_separator_runs(self):
        """Runs of === or --- make a Markdown previewer reformat the document."""
        import re
        from tshirt.core.profile import load_profile
        from tshirt.core.validate import ValidationReport
        with tempfile.TemporaryDirectory() as td:
            p = package.save_png(Image.new("RGBA", (100, 100)), Path(td) / "a.png", 300)
            asset = package.describe_asset(p, "production", 8.47, 8.47, 300)
            spec = package.write_print_spec(
                Path(td) / "print-spec.txt", [asset],
                load_profile(ROOT / "profiles" / "dtf-printer-a.json"),
                [ValidationReport(asset="a.png")],
            )
            for i, line in enumerate(spec.read_text().splitlines(), 1):
                self.assertIsNone(re.fullmatch(r"\s*[=\-*_]{3,}\s*", line),
                                  f"line {i} is a separator run: {line!r}")


if __name__ == "__main__":
    unittest.main()


class TestSendSetIsExplicit(unittest.TestCase):
    """Only files actually being printed may appear in the printer's instructions."""

    def _assets(self, td):
        from tshirt.core.profile import load_profile
        p = package.save_png(Image.new("RGBA", (10, 10)), Path(td) / "export-check-v1.png", 300)
        q = package.save_png(Image.new("RGBA", (10, 10)), Path(td) / "pipeline-test-design.png", 300)
        return (package.describe_asset(p, "export_check", 160.0, 135.2, 300),
                package.describe_asset(q, "pipeline_test_artefact", 280.1, 270.0, 300),
                load_profile(ROOT / "profiles" / "dtf-printer-a.json"))

    def test_only_listed_assets_appear(self):
        from tshirt.core.validate import ValidationReport
        with tempfile.TemporaryDirectory() as td:
            send, not_sent, profile = self._assets(td)
            text = package.write_print_spec(
                Path(td) / "spec.txt", [send], profile,
                [ValidationReport(asset="export-check-v1.png")]).read_text()
            self.assertIn("export-check-v1.png", text)
            self.assertNotIn("pipeline-test-design.png", text)

    def test_spec_states_size_and_the_two_instructions(self):
        from tshirt.core.validate import ValidationReport
        with tempfile.TemporaryDirectory() as td:
            send, _, profile = self._assets(td)
            text = package.write_print_spec(
                Path(td) / "spec.txt", [send], profile,
                [ValidationReport(asset="export-check-v1.png")]).read_text()
            self.assertIn("160.0 mm wide", text)
            self.assertIn("DO NOT RESIZE", text)
            self.assertIn("normal reading orientation", text)
            self.assertIn("transparent", text.lower())

    def test_spec_stays_short(self):
        """The printer is trusted and busy; they do not need our internal state."""
        from tshirt.core.validate import ValidationReport
        with tempfile.TemporaryDirectory() as td:
            send, _, profile = self._assets(td)
            text = package.write_print_spec(
                Path(td) / "spec.txt", [send], profile,
                [ValidationReport(asset="export-check-v1.png")]).read_text()
            self.assertLess(len(text.splitlines()), 40)
            self.assertNotIn("ADVISORY", text)
            self.assertNotIn("PRINT_READY", text)
