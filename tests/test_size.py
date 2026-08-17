"""Physical sizing. These are the calculations that decide real print dimensions."""

import unittest

from tshirt.core import size


class TestConversions(unittest.TestCase):
    def test_inch_is_25_4_mm(self):
        self.assertAlmostEqual(size.inches_to_mm(1), 25.4)
        self.assertAlmostEqual(size.mm_to_inches(25.4), 1.0)

    def test_round_trip(self):
        for mm in (1.0, 25.4, 100.0, 280.0, 560.0):
            self.assertAlmostEqual(size.inches_to_mm(size.mm_to_inches(mm)), mm, places=9)


class TestRequiredPx(unittest.TestCase):
    def test_one_inch_at_300(self):
        self.assertEqual(size.required_px(25.4, 300), 300)

    def test_gate_1a_target(self):
        """280 mm at 300 DPI. Rounds UP: 3307.09 -> 3308, never 3307."""
        self.assertEqual(size.required_px(280.0, 300), 3308)

    def test_spec_worked_example_12_inches(self):
        self.assertEqual(size.required_px(size.inches_to_mm(12), 300), 3600)

    def test_always_rounds_up(self):
        # A fractional pixel short of the requirement is still short.
        self.assertEqual(size.required_px(25.5, 300), 302)
        self.assertEqual(size.required_px(0.1, 300), 2)

    def test_rejects_non_positive(self):
        for bad in (0, -1, -280.0):
            with self.assertRaises(ValueError):
                size.required_px(bad, 300)
            with self.assertRaises(ValueError):
                size.required_px(280, bad)


class TestEffectiveDpi(unittest.TestCase):
    def test_exact(self):
        self.assertAlmostEqual(size.effective_dpi(3600, size.inches_to_mm(12)), 300.0)

    def test_undersized_artwork_reports_low_dpi(self):
        self.assertLess(size.effective_dpi(1800, size.inches_to_mm(12)), 300.0)

    def test_gate_1a_asset_meets_300(self):
        self.assertGreaterEqual(size.effective_dpi(3308, 280.08), 299.5)

    def test_rejects_non_positive(self):
        with self.assertRaises(ValueError):
            size.effective_dpi(0, 280)
        with self.assertRaises(ValueError):
            size.effective_dpi(3308, 0)


class TestPhysicalSpec(unittest.TestCase):
    def test_derives_mm_from_px(self):
        spec = size.PhysicalSpec(3308, 1202, 300.0)
        self.assertAlmostEqual(spec.width_mm, 280.08, places=2)
        self.assertAlmostEqual(spec.effective_dpi_width, 300.0, places=6)

    def test_describe_is_serialisable(self):
        d = size.PhysicalSpec(3308, 1202, 300.0).describe()
        self.assertEqual(d["width_px"], 3308)
        self.assertEqual(d["dpi"], 300.0)


class TestAspect(unittest.TestCase):
    def test_preserves_ratio(self):
        w, h = size.scale_preserving_aspect(1000, 500, 3308)
        self.assertEqual(w, 3308)
        self.assertEqual(h, 1654)

    def test_never_collapses_to_zero(self):
        _, h = size.scale_preserving_aspect(10000, 1, 100)
        self.assertGreaterEqual(h, 1)


class TestLengthHelpers(unittest.TestCase):
    def test_stroke_conversion_round_trip(self):
        for mm in (0.25, 0.5, 1.0, 2.0):
            px = size.mm_to_px_length(mm, 300)
            self.assertAlmostEqual(size.px_to_mm_length(px, 300), mm, places=9)

    def test_known_stroke(self):
        self.assertAlmostEqual(size.mm_to_px_length(1.0, 300), 11.811, places=3)


if __name__ == "__main__":
    unittest.main()
