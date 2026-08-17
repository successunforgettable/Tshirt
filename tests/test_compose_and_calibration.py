"""Composition and calibration output verified against what they claim to produce.

The calibration sheet is a measurement instrument. If its own geometry is wrong,
every tolerance derived from the physical sample is wrong too — so its elements
are checked to the pixel against the coordinates the generator reports.
"""

import unittest
from pathlib import Path

import numpy as np

from tshirt.calibration import sheet
from tshirt.core import analysis, compose, size

ROOT = Path(__file__).resolve().parent.parent
FONT = ROOT / "assets" / "fonts" / "LiberationSans-Bold.ttf"
DPI = 300.0


class TestFontAvailable(unittest.TestCase):
    def test_font_is_vendored(self):
        """Vendored, not a system font: builds must be reproducible off this repo."""
        self.assertTrue(FONT.is_file())

    def test_licence_ships_with_font(self):
        self.assertTrue((FONT.parent / "LiberationSans-LICENSE.txt").is_file())

    def test_covers_every_character_we_print(self):
        chars = "THE INCREDIBLE YOU N-Codes E-Codes Inner DNA 0123456789.%#()/-"
        self.assertEqual(compose.missing_glyphs(FONT, chars), [])


class TestComposition(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.target_px = size.required_px(280.0, DPI)
        cls.result = compose.compose_incredible_you(FONT, cls.target_px, DPI)

    def test_hits_target_width_exactly(self):
        self.assertEqual(self.result.image.width, self.target_px)

    def test_physical_width_is_about_280mm(self):
        mm = size.px_to_mm(self.result.image.width, DPI)
        self.assertAlmostEqual(mm, 280.0, delta=0.5)

    def test_aspect_ratio_is_preserved_not_forced(self):
        """Height falls out of the composition; it is never fixed in advance."""
        self.assertNotEqual(self.result.image.height, self.result.image.width)
        self.assertGreater(self.result.image.height, 0)

    def test_is_a_large_centre_front_block_not_a_shallow_banner(self):
        """A wide chest banner is not representative of the intended product."""
        aspect = self.result.image.width / self.result.image.height
        self.assertLess(aspect, 1.4, f"too shallow for a centre-front print: {aspect:.2f}:1")
        self.assertGreater(aspect, 0.7, f"unexpectedly tall: {aspect:.2f}:1")

    def test_height_is_substantial_on_a_garment(self):
        mm = size.px_to_mm(self.result.image.height, DPI)
        self.assertGreater(mm, 200.0, "centre-front design should have real vertical presence")
        self.assertLess(mm, 400.0, "must fit a normal adult tee print area")

    def test_the_and_you_are_treated_identically(self):
        """Equal treatment keeps the hierarchy clearly distinct from the identity (D-17).

        Inked heights are compared with tolerance rather than for equality: THE is
        entirely flat-topped, while the round O in YOU carries the usual optical
        overshoot above cap height and below the baseline. Both lines are set at
        the same font size, which is what "identical treatment" actually means.
        """
        lines = self.result.layout["lines"]
        the_h, you_h = lines["THE"]["height"], lines["YOU"]["height"]
        drift = abs(the_h - you_h) / max(the_h, you_h)
        self.assertLess(drift, 0.05,
                        f"THE and YOU differ by {drift:.1%} — more than round-letter overshoot")
        self.assertGreater(self.result.layout["sub_font_size_px"],
                           self.result.layout["main_font_size_px"])

    def test_all_lines_justified_to_the_same_measure(self):
        lines = self.result.layout["lines"]
        widths = [lines[k]["width"] for k in ("THE", "INCREDIBLE", "YOU")]
        for w in widths:
            self.assertGreater(w / self.target_px, 0.97, "line not justified to the measure")

    def test_renders_the_authoritative_string(self):
        self.assertIn("THE INCREDIBLE YOU", self.result.rendered_strings)

    def test_no_missing_glyphs(self):
        self.assertEqual(self.result.missing_glyph_chars, [])

    def test_output_is_rgba_with_real_transparency(self):
        arr = self.result.rgba
        self.assertEqual(arr.shape[2], 4)
        self.assertGreater(int(np.count_nonzero(arr[:, :, 3] == 0)), 0)

    def test_ink_reaches_every_edge(self):
        """Declared size must be the artwork size — no wasted film."""
        box = analysis.inked_bbox(self.result.rgba)
        self.assertEqual(box.left, 0)
        self.assertEqual(box.top, 0)
        self.assertEqual(box.right, self.result.image.width - 1)
        self.assertEqual(box.bottom, self.result.image.height - 1)

    def test_soft_alpha_is_negligible(self):
        """Deterministic composition should produce edge anti-aliasing only."""
        stats = analysis.alpha_stats(self.result.rgba)
        self.assertLess(stats.soft_ratio, 0.001)

    def test_rules_are_at_least_the_requested_thickness(self):
        expected = round(2.0 / 25.4 * DPI)
        self.assertEqual(self.result.layout["rule_thickness_px"], expected)

    def test_deterministic_across_runs(self):
        again = compose.compose_incredible_you(FONT, self.target_px, DPI)
        self.assertTrue(np.array_equal(self.result.rgba, again.rgba))


class TestTypographyPrimitives(unittest.TestCase):
    def test_tracking_widens_a_line(self):
        tight = compose.render_line(FONT, "YOU", 200, 0)
        loose = compose.render_line(FONT, "YOU", 200, 60)
        self.assertGreater(loose.width, tight.width)

    def test_fit_font_size_never_exceeds_target(self):
        target = 2000
        s = compose.fit_font_size_for_width(FONT, "INCREDIBLE", target)
        self.assertLessEqual(compose.render_line(FONT, "INCREDIBLE", s, 0).width, target)

    def test_fit_tracking_never_exceeds_target(self):
        target = 1200
        t = compose.fit_tracking_for_width(FONT, "THE", 200, target)
        self.assertLessEqual(compose.render_line(FONT, "THE", 200, t).width, target)

    def test_single_character_needs_no_tracking(self):
        self.assertEqual(compose.fit_tracking_for_width(FONT, "R", 100, 500), 0.0)


class TestCalibrationSheet(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cal = sheet.build_calibration_sheet(FONT, DPI, width_mm=200.0)
        cls.alpha = cls.cal.rgba[:, :, 3]

    def test_width_is_exactly_200mm(self):
        self.assertAlmostEqual(self.cal.width_mm, 200.0, delta=0.05)

    def test_all_required_elements_present(self):
        required = {
            "red_family_sweep", "greyscale_wedge", "alpha_step_wedge", "white_density",
            "stroke_ladder", "negative_space_test", "hard_edge_vs_fade",
            "ip_text_ladder", "ruler_100mm", "registration_marks",
            "orientation_marker_R",
        }
        self.assertTrue(required.issubset(set(self.cal.elements)),
                        f"missing: {required - set(self.cal.elements)}")

    def test_stroke_ladder_thicknesses_are_exact(self):
        for r in self.cal.regions["stroke_ladder"]:
            col = self.alpha[r["y"]:r["y"] + r["thickness_px"] + 4, r["x"] + r["w"] // 2]
            measured = int(np.count_nonzero(col >= 250))
            self.assertEqual(measured, r["thickness_px"],
                             f"{r['mm']} mm stroke rendered at {measured} px")

    def test_stroke_ladder_covers_the_expected_range(self):
        self.assertEqual([r["mm"] for r in self.cal.regions["stroke_ladder"]],
                         [0.25, 0.5, 1.0, 2.0, 3.0, 4.0])

    def test_negative_space_gaps_are_exact(self):
        for r in self.cal.regions["negative_space_test"]:
            col = self.alpha[r["y"]:r["y"] + r["box"], r["probe_x"]]
            measured = int(np.count_nonzero(col == 0))
            self.assertEqual(measured, r["gap_px"],
                             f"{r['mm']} mm gap rendered at {measured} px")

    def test_alpha_step_wedge_values_are_exact(self):
        for r in self.cal.regions["alpha_step_wedge"]:
            v = int(self.alpha[r["y"] + r["h"] // 2, r["x"] + r["w"] // 2])
            self.assertEqual(v, r["alpha"], f"a{r['pct']}% rendered at alpha {v}")

    def test_red_sweep_colours_are_exact(self):
        rgba = self.cal.rgba
        for r in self.cal.regions["red_family_sweep"]:
            px = rgba[r["y"] + r["h"] // 2, r["x"] + r["w"] // 2]
            self.assertEqual(list(int(c) for c in px[:3]), r["rgb"], r["hex"])
            self.assertEqual(int(px[3]), 255)

    def test_ruler_is_exactly_100mm(self):
        ru = self.cal.regions["ruler_100mm"]
        self.assertAlmostEqual(size.px_to_mm(ru["length_px"], DPI), 100.0, delta=0.05)

    def test_ip_strings_rendered_verbatim(self):
        joined = " ".join(self.cal.rendered_strings)
        for term in ("N-Codes", "E-Codes", "Inner DNA"):
            self.assertIn(term, joined)

    def test_ip_strings_carry_no_interpretation(self):
        """Probes only: the terms appear as bare strings, never described (D-16)."""
        banned = ("means", "represents", "stands for", "symbol", "refers to")
        for s in self.cal.rendered_strings:
            low = s.lower()
            for term in ("n-codes", "e-codes", "inner dna"):
                if term in low:
                    for word in banned:
                        self.assertNotIn(word, low, f"{s!r} interprets {term}")

    def test_no_missing_glyphs(self):
        self.assertEqual(self.cal.missing_glyph_chars, [])

    def test_has_real_transparency(self):
        self.assertGreater(int(np.count_nonzero(self.alpha == 0)), 0)

    def test_fade_block_produces_soft_alpha_by_design(self):
        """The fade is deliberately soft — it exists to measure haze."""
        stats = analysis.alpha_stats(self.cal.rgba)
        self.assertGreater(stats.soft_px, 0)


if __name__ == "__main__":
    unittest.main()
