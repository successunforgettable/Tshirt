"""Gate 1a export-check artefact.

Every assertion here maps to something the physical check will confirm with a
ruler. If the generator's own geometry is wrong, the physical measurement proves
nothing.
"""

import unittest
from pathlib import Path

import numpy as np

from tshirt.calibration import export_check
from tshirt.core import analysis, size, validate
from tshirt.core.profile import load_profile

ROOT = Path(__file__).resolve().parent.parent
FONT = ROOT / "assets" / "fonts" / "LiberationSans-Bold.ttf"
DPI = 300.0


class TestExportCheckGeometry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = export_check.build_export_check(FONT, DPI, width_mm=160.0)
        cls.alpha = cls.r.rgba[:, :, 3]

    def test_declared_width_is_derived_from_actual_pixels(self):
        """Declared size must be what the pixels really are, not what was asked for.

        160 mm at 300 DPI rounds to 1890 px, which is 160.02 mm. Reporting the
        request would put a small lie in the manifest.
        """
        self.assertEqual(self.r.image.width, 1890)
        self.assertAlmostEqual(self.r.width_mm, size.px_to_mm(1890, DPI), places=9)
        self.assertAlmostEqual(self.r.width_mm, 160.0, delta=0.05)

    def test_stays_compact(self):
        """Small and cheap: this is a one-off correctness check, not a chart."""
        self.assertLess(self.r.height_mm, 170.0)
        self.assertGreater(self.r.height_mm, 100.0)

    def test_horizontal_reference_is_exactly_100mm(self):
        ref = self.r.regions["horizontal_reference"]
        self.assertAlmostEqual(size.px_to_mm(ref["length_px"], DPI), 100.0, delta=0.05)

    def test_vertical_reference_is_exactly_100mm(self):
        ref = self.r.regions["vertical_reference"]
        self.assertAlmostEqual(size.px_to_mm(ref["length_px"], DPI), 100.0, delta=0.05)

    def test_both_references_are_the_same_length(self):
        """Equal in the file, so any physical difference is printer distortion."""
        self.assertEqual(self.r.regions["horizontal_reference"]["length_px"],
                         self.r.regions["vertical_reference"]["length_px"])

    def test_effective_dpi_is_exactly_300_on_both_axes(self):
        self.assertAlmostEqual(size.effective_dpi(self.r.image.width, self.r.width_mm),
                               300.0, places=4)
        self.assertAlmostEqual(size.effective_dpi(self.r.image.height, self.r.height_mm),
                               300.0, places=4)

    def test_ink_reaches_every_edge(self):
        """Registration marks define the extent, so cropping is detectable."""
        box = analysis.inked_bbox(self.r.rgba)
        self.assertEqual((box.left, box.top), (0, 0))
        self.assertEqual(box.right, self.r.image.width - 1)
        self.assertEqual(box.bottom, self.r.image.height - 1)

    def test_registration_marks_span_the_full_artefact(self):
        reg = self.r.regions["registration_marks"]
        self.assertGreater(reg["horizontal_separation_px"], self.r.image.width * 0.9)
        self.assertGreater(reg["vertical_separation_px"], self.r.image.height * 0.9)

    def test_deterministic_across_runs(self):
        again = export_check.build_export_check(FONT, DPI, width_mm=160.0)
        self.assertTrue(np.array_equal(self.r.rgba, again.rgba))


class TestExportCheckContent(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = export_check.build_export_check(FONT, DPI, width_mm=160.0)

    def test_carries_every_required_element(self):
        required = {"horizontal_reference_100mm", "vertical_reference_100mm",
                    "orientation_marker", "registration_marks",
                    "printed_dimensions", "deterministic_text", "solid_geometry"}
        self.assertTrue(required.issubset(set(self.r.elements)),
                        f"missing: {required - set(self.r.elements)}")

    def test_renders_the_brand_string_and_ip_probe(self):
        joined = " ".join(self.r.rendered_strings)
        self.assertIn("THE INCREDIBLE YOU", joined)
        self.assertIn("N-Codes", joined)

    def test_declares_its_own_intended_size(self):
        """So the physical measurement needs no separate document in hand."""
        self.assertTrue(any("160" in s and "DPI" in s for s in self.r.rendered_strings))

    def test_no_missing_glyphs(self):
        self.assertEqual(self.r.missing_glyph_chars, [])

    def test_has_real_transparency(self):
        self.assertGreater(int(np.count_nonzero(self.r.rgba[:, :, 3] == 0)), 0)

    def test_soft_alpha_is_negligible(self):
        stats = analysis.alpha_stats(self.r.rgba)
        self.assertLess(stats.soft_ratio, 0.001)

    def test_carries_no_printer_characterisation_elements(self):
        """Gate 1a does not assess the trusted printer."""
        banned = {"red_family_sweep", "greyscale_wedge", "alpha_step_wedge",
                  "white_density", "stroke_ladder", "negative_space_test",
                  "hard_edge_vs_fade", "ip_text_ladder", "sustained_coverage"}
        self.assertEqual(banned & set(self.r.elements), set())


class TestExportCheckValidates(unittest.TestCase):
    def test_reaches_print_ready(self):
        r = export_check.build_export_check(FONT, DPI, width_mm=160.0)
        report = validate.validate(
            validate.AssetUnderTest(
                name="export-check-v1.png", rgba=r.rgba, image_format="PNG",
                mode="RGBA", declared_width_mm=r.width_mm,
                declared_height_mm=r.height_mm,
                rendered_strings=r.rendered_strings,
                authoritative_strings=["THE INCREDIBLE YOU", "N-Codes"],
                missing_glyph_chars=r.missing_glyph_chars,
            ),
            load_profile(ROOT / "profiles" / "dtf-printer-a.json"),
        )
        self.assertEqual(report.readiness, validate.PRINT_READY, report.summary())
        self.assertEqual(report.failures, [])


class TestDiagnosticSheetIsNotInTheDefaultPath(unittest.TestCase):
    """The full calibration sheet is retained, but must never run by default."""

    def test_default_build_does_not_import_the_calibration_sheet(self):
        import inspect
        from tshirt.cli import main
        src = inspect.getsource(main.build)
        before = src.split("if diagnostic:")[0]
        self.assertNotIn("build_calibration_sheet", before)

    def test_calibration_sheet_is_still_available_as_a_diagnostic(self):
        from tshirt.calibration.sheet import build_calibration_sheet
        self.assertTrue(callable(build_calibration_sheet))


if __name__ == "__main__":
    unittest.main()
