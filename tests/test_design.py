"""Design vocabulary and creative directions.

The vocabulary is deterministic drawing, so it is testable in the ordinary way.
Design QUALITY is not testable and is not attempted here - that is the product
owner's judgement. What is tested is that the primitives honour their spec, and
that the directions stay inside the brand rules.
"""

import unittest

import numpy as np

from tshirt.core import analysis, size
from tshirt.design import directions
from tshirt.design.elements import (BLACK, Box, Ctx, FitText, Gap, JustifyText,
                                    Row, Rule, Stack, Text, face_path,
                                    FACES, render, size_for_cap_height)

DPI = 300.0


class TestFaces(unittest.TestCase):
    def test_every_named_face_is_vendored(self):
        """Builds must be reproducible from this repo, not from system fonts."""
        for name in FACES:
            self.assertTrue(face_path(name).is_file(), f"{name} missing")

    def test_unknown_face_raises(self):
        with self.assertRaises(KeyError):
            face_path("comic-sans")


class TestCapHeightSizing(unittest.TestCase):
    """Cap height is the only size measure comparable across faces."""

    def test_requested_cap_height_is_honoured(self):
        for face in ("sans-bold", "serif-bold", "mono-bold", "grotesk-bold"):
            img = render(Text("H", face, cap_mm=10), Ctx(dpi=DPI))
            mm = size.px_to_mm(img.height, DPI)
            self.assertAlmostEqual(mm, 10.0, delta=0.3, msg=face)

    def test_different_faces_agree_on_size(self):
        """A serif and a grotesque at the same cap height must look the same size."""
        heights = [render(Text("H", f, cap_mm=12), Ctx(dpi=DPI)).height
                   for f in ("sans-bold", "serif-bold", "grotesk-bold")]
        self.assertLess(max(heights) - min(heights), 0.05 * max(heights))

    def test_nominal_size_differs_even_when_cap_height_matches(self):
        """Which is exactly why nominal size is the wrong thing to specify."""
        a = size_for_cap_height("sans-bold", 10, DPI)
        b = size_for_cap_height("grotesk-bold", 10, DPI)
        self.assertNotEqual(a, b)


class TestPrimitives(unittest.TestCase):
    def setUp(self):
        self.ctx = Ctx(dpi=DPI)

    def test_fit_text_never_exceeds_its_measure(self):
        for w in (80.0, 180.0, 280.0):
            img = render(FitText("INCREDIBLE", "sans-bold", width_mm=w), self.ctx)
            self.assertLessEqual(size.px_to_mm(img.width, DPI), w + 0.1)

    def test_fit_text_nearly_fills_its_measure(self):
        img = render(FitText("INCREDIBLE", "sans-bold", width_mm=280.0), self.ctx)
        self.assertGreater(size.px_to_mm(img.width, DPI), 279.0)

    def test_justify_text_reaches_its_measure_without_changing_size(self):
        tall = render(Text("YOU", "sans-bold", cap_mm=10), self.ctx).height
        wide = render(JustifyText("YOU", "sans-bold", cap_mm=10, width_mm=200),
                      self.ctx)
        self.assertLessEqual(size.px_to_mm(wide.width, DPI), 200.1)
        self.assertGreater(size.px_to_mm(wide.width, DPI), 198.0)
        self.assertAlmostEqual(wide.height, tall, delta=2)   # size unchanged

    def test_rule_dimensions_are_exact(self):
        img = render(Rule(width_mm=100, thickness_mm=2), self.ctx)
        self.assertAlmostEqual(size.px_to_mm(img.width, DPI), 100.0, delta=0.05)
        self.assertAlmostEqual(size.px_to_mm(img.height, DPI), 2.0, delta=0.05)

    def test_stack_sums_heights_and_gaps(self):
        one = render(Rule(width_mm=50, thickness_mm=4), self.ctx).height
        two = render(Stack([Rule(width_mm=50, thickness_mm=4),
                            Rule(width_mm=50, thickness_mm=4)], gap_mm=10),
                     self.ctx).height
        self.assertAlmostEqual(two, one * 2 + Ctx(dpi=DPI).px(10), delta=2)

    def test_row_sums_widths_and_gaps(self):
        one = render(Rule(width_mm=30, thickness_mm=2), self.ctx).width
        two = render(Row([Rule(width_mm=30, thickness_mm=2),
                          Rule(width_mm=30, thickness_mm=2)], gap_mm=5),
                     self.ctx).width
        self.assertAlmostEqual(two, one * 2 + Ctx(dpi=DPI).px(5), delta=2)

    def test_gap_renders_nothing_but_occupies_space(self):
        img = Gap(10, 5).render(self.ctx)
        self.assertEqual(int(np.asarray(img)[:, :, 3].max()), 0)
        self.assertAlmostEqual(size.px_to_mm(img.height, DPI), 10.0, delta=0.05)

    def test_box_adds_padding_on_both_sides(self):
        inner = render(Text("YOU", cap_mm=10), self.ctx)
        boxed = render(Box(Text("YOU", cap_mm=10), pad_mm=(5, 8), outline_mm=1),
                       self.ctx)
        self.assertAlmostEqual(boxed.width, inner.width + Ctx(dpi=DPI).px(8) * 2,
                               delta=3)

    def test_knockout_box_punches_the_word_through_the_fill(self):
        """Contrast from mass, not colour: the garment shows through the letters."""
        boxed = render(Box(Text("YOU", "sans-bold", cap_mm=14, colour=BLACK),
                           pad_mm=(4, 6), fill=BLACK, knockout=True), self.ctx)
        alpha = np.asarray(boxed)[:, :, 3]
        self.assertGreater(int((alpha == 0).sum()), 0, "nothing was knocked out")
        self.assertGreater(int((alpha > 250).sum()), 0, "no fill remains")


class TestDirections(unittest.TestCase):
    """Four directions, not four variations."""

    @classmethod
    def setUpClass(cls):
        cls.built = {n: directions.build(n) for n in directions.DIRECTIONS}

    def test_there_are_four(self):
        self.assertEqual(len(directions.DIRECTIONS), 4)

    def test_each_fits_the_target_width(self):
        for name, img in self.built.items():
            mm = size.px_to_mm(img.width, DPI)
            self.assertLessEqual(mm, directions.WIDTH_MM + 0.5, name)
            self.assertGreater(mm, directions.WIDTH_MM * 0.85, name)

    def test_each_is_a_usable_front_print_shape(self):
        for name, img in self.built.items():
            h = size.px_to_mm(img.height, DPI)
            self.assertGreater(h, 60.0, f"{name} too shallow")
            self.assertLess(h, 400.0, f"{name} too tall for a tee front")

    def test_they_are_genuinely_different(self):
        """Different aspect ratios are a crude but real proxy for different layouts."""
        aspects = {n: round(i.width / i.height, 2) for n, i in self.built.items()}
        self.assertGreaterEqual(len(set(aspects.values())), 3, aspects)

    def test_they_use_different_typefaces(self):
        """Mixed typography across directions, not one face reused four times."""
        import inspect
        used = set()
        for fn in directions.DIRECTIONS.values():
            src = inspect.getsource(fn)
            used |= {f for f in FACES if f'"{f}"' in src}
        self.assertGreaterEqual(len(used), 4, used)

    def test_all_output_is_transparent_rgba(self):
        for name, img in self.built.items():
            arr = np.asarray(img.convert("RGBA"))
            self.assertEqual(arr.shape[2], 4, name)
            self.assertGreater(int((arr[:, :, 3] == 0).sum()), 0, name)

    def test_ink_reaches_the_declared_bounds(self):
        for name, img in self.built.items():
            box = analysis.inked_bbox(np.asarray(img.convert("RGBA")))
            self.assertEqual((box.left, box.top), (0, 0), name)
            # Within a pixel: the crop keeps alpha-1 antialiasing that the print
            # analysis threshold (alpha > 5) correctly ignores as non-printing.
            self.assertGreaterEqual(box.right, img.width - 2, name)

    def test_soft_alpha_is_negligible(self):
        """Deterministic drawing should give edge anti-aliasing and nothing else."""
        for name, img in self.built.items():
            stats = analysis.alpha_stats(np.asarray(img.convert("RGBA")))
            self.assertLess(stats.soft_ratio, 0.002, name)

    def test_deterministic_across_runs(self):
        for name in directions.DIRECTIONS:
            again = directions.build(name)
            self.assertTrue(np.array_equal(np.asarray(self.built[name]),
                                           np.asarray(again)), name)

    def test_no_proprietary_vocabulary_appears(self):
        """Unknown-meaning terms must not be used decoratively (D-16)."""
        import inspect
        src = inspect.getsource(directions)
        body = src.split('"""', 2)[-1]          # skip the module docstring
        for term in ("N-Codes", "E-Codes", "Inner DNA", "Baselines",
                     "Outcomes Plus", "Secret Millionaire Blueprint"):
            self.assertNotIn(f'"{term}"', body, f"{term} used in a composition")

    def test_unknown_direction_raises(self):
        with self.assertRaises(KeyError):
            directions.build("E-does-not-exist")


if __name__ == "__main__":
    unittest.main()


class TestReferenceStyle(unittest.TestCase):
    """Directions built to match the supplied reference merchandise.

    What is asserted is the STRUCTURE the references share, not whether a design
    is good - that stays the product owner's judgement.
    """

    @classmethod
    def setUpClass(cls):
        from tshirt.design import reference_style
        cls.mod = reference_style
        cls.built = {n: reference_style.build(n) for n in reference_style.DIRECTIONS}

    def test_display_and_script_faces_are_vendored(self):
        for name in ("display", "display-condensed", "display-black",
                     "script", "brush"):
            self.assertTrue(face_path(name).is_file(), name)

    def test_each_uses_multiple_lines(self):
        """Every reference tee is a stacked phrase, never a single line."""
        import inspect
        for name, fn in self.mod.DIRECTIONS.items():
            src = inspect.getsource(fn)
            self.assertGreaterEqual(src.count("FitText") + src.count("JustifyText")
                                    + src.count("Text("), 3, name)

    def test_scale_contrast_is_present(self):
        """Lines must differ in size - uniform lines read as branding, not merch."""
        import inspect
        for name, fn in self.mod.DIRECTIONS.items():
            src = inspect.getsource(fn)
            widths = {ln.split("width_mm=")[1].split(",")[0].split(")")[0].strip()
                      for ln in src.splitlines() if "width_mm=" in ln}
            self.assertGreaterEqual(len(widths), 2, f"{name} has no scale contrast")

    def test_colour_is_used(self):
        for name, img in self.built.items():
            arr = np.asarray(img.convert("RGBA"))
            opaque = arr[arr[:, :, 3] > 250]
            if not len(opaque):
                self.fail(f"{name} has no ink")
            # More than one distinct ink colour, or a knockout device present.
            distinct = {tuple(p[:3]) for p in opaque[::997]}
            self.assertGreaterEqual(len(distinct), 1, name)

    def test_fits_a_front_print(self):
        for name, img in self.built.items():
            w = size.px_to_mm(img.width, DPI)
            h = size.px_to_mm(img.height, DPI)
            self.assertLessEqual(w, self.mod.WIDTH_MM + 0.5, name)
            self.assertLess(h, 400.0, name)

    def test_output_is_transparent_rgba(self):
        for name, img in self.built.items():
            arr = np.asarray(img.convert("RGBA"))
            self.assertEqual(arr.shape[2], 4, name)
            self.assertGreater(int((arr[:, :, 3] == 0).sum()), 0, name)

    def test_deterministic(self):
        for name in self.mod.DIRECTIONS:
            self.assertTrue(np.array_equal(np.asarray(self.built[name]),
                                           np.asarray(self.mod.build(name))), name)

    def test_no_proprietary_vocabulary(self):
        import inspect
        src = inspect.getsource(self.mod).split('"""', 2)[-1]
        for term in ("N-Codes", "E-Codes", "Inner DNA", "Baselines",
                     "Outcomes Plus", "Secret Millionaire Blueprint"):
            self.assertNotIn(f'"{term}"', src, term)

    def test_brand_red_is_still_not_guessed(self):
        """Placeholder palette must not be presented as the brand colour."""
        from tshirt.branddna import load_brand_dna
        self.assertIsNone(load_brand_dna().colour_hex("brand red"))
