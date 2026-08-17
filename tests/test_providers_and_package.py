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

    def test_dtf_and_png_are_confirmed(self):
        self.assertEqual(self.profile.get("process").value, "DTF")
        self.assertEqual(self.profile.get("process").status, CONFIRMED)
        self.assertEqual(self.profile.get("accepted_formats").status, CONFIRMED)
        self.assertTrue(self.profile.get("requires_transparency").value)

    def test_working_baseline_is_marked_assumed_not_confirmed(self):
        for name in ("required_dpi", "colour_space", "rip_handles_mirroring"):
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
        self.assertEqual(names, {"required_dpi", "colour_space", "rip_handles_mirroring"})


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


if __name__ == "__main__":
    unittest.main()
