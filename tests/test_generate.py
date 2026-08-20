"""Type a description, get ideas back.

This is the product's central promise, so what is tested is that ANY phrase works
- not that one hand-tuned phrase works.
"""

import unittest

import numpy as np

from tshirt.core import analysis, size
from tshirt.design.brief import CONNECTORS, segment
from tshirt.design.generate import generate
from tshirt.design.styles import PALETTES, STYLES

DPI = 300.0

PHRASES = [
    "trust the process",
    "the incredible you",
    "success is a state of mind",
    "stay strong believe in yourself",
    "you will never win if you never begin",
    "discipline",
    "become the best version of yourself today",
]


class TestSegmentation(unittest.TestCase):
    def test_matches_the_reference_phrasing(self):
        """The references break exactly where the connector rule says they should."""
        got = [(l.text, l.major) for l in segment("trust the process").lines]
        self.assertEqual(got, [("TRUST", True), ("the", False), ("PROCESS", True)])

    def test_connectors_become_minor_lines(self):
        lines = segment("success is a state of mind").lines
        minors = [l.text for l in lines if not l.major]
        self.assertIn("is a", minors)
        self.assertIn("of", minors)

    def test_a_final_connector_stays_major(self):
        """A phrase ending on YOU ends on its point, not on a preposition."""
        lines = segment("the incredible you").lines
        self.assertTrue(lines[-1].major)
        self.assertEqual(lines[-1].text, "YOU")

    def test_long_runs_are_split_so_lines_can_be_set_large(self):
        for line in segment("become the best version of yourself today").lines:
            if line.major:
                self.assertLessEqual(len(line.text), 12, line.text)

    def test_slashes_force_explicit_breaks(self):
        got = [l.text for l in segment("TRUST / the / PROCESS").lines]
        self.assertEqual(got, ["TRUST", "the", "PROCESS"])

    def test_single_word_still_works(self):
        lines = segment("discipline").lines
        self.assertEqual(len(lines), 1)
        self.assertTrue(lines[0].major)

    def test_empty_phrase_yields_no_lines(self):
        self.assertEqual(segment("   ").lines, [])

    def test_connector_list_is_lowercase(self):
        for w in CONNECTORS:
            self.assertEqual(w, w.lower())


class TestGenerate(unittest.TestCase):
    def test_returns_one_idea_per_style(self):
        ideas = generate("trust the process")
        self.assertEqual(len(ideas), len(STYLES))
        self.assertEqual({i.style for i in ideas}, set(STYLES))

    def test_every_style_handles_every_phrase(self):
        """The generator must not have favourite inputs."""
        for phrase in PHRASES:
            for idea in generate(phrase):
                self.assertGreater(idea.image.width, 0, f"{phrase}/{idea.style}")
                self.assertGreater(idea.image.height, 0, f"{phrase}/{idea.style}")

    def test_output_respects_the_measure(self):
        for phrase in PHRASES:
            for idea in generate(phrase, width_mm=260.0):
                mm = size.px_to_mm(idea.image.width, DPI)
                self.assertLessEqual(mm, 260.5, f"{phrase}/{idea.style}")

    def test_output_fits_a_shirt_front(self):
        for phrase in PHRASES:
            for idea in generate(phrase, width_mm=260.0):
                mm = size.px_to_mm(idea.image.height, DPI)
                self.assertLess(mm, 400.0, f"{phrase}/{idea.style}")

    def test_ideas_are_visually_different(self):
        """Different styles, not one layout recoloured."""
        ideas = generate("trust the process")
        shapes = {(i.image.width, i.image.height) for i in ideas}
        self.assertGreaterEqual(len(shapes), 4, shapes)

    def test_palettes_multiply_the_options(self):
        ideas = generate("trust the process", palettes=["mono", "ice"])
        self.assertEqual(len(ideas), len(STYLES) * 2)

    def test_every_palette_renders(self):
        for name in PALETTES:
            ideas = generate("trust the process", styles=["highlight-stack"],
                             palettes=[name])
            self.assertEqual(len(ideas), 1, name)

    def test_output_is_print_ready_shaped(self):
        """Transparent RGBA with ink to the edges - ready for the export pipeline."""
        for idea in generate("trust the process"):
            arr = np.asarray(idea.image.convert("RGBA"))
            self.assertEqual(arr.shape[2], 4, idea.name)
            self.assertGreater(int((arr[:, :, 3] == 0).sum()), 0, idea.name)
            box = analysis.inked_bbox(arr)
            self.assertEqual((box.left, box.top), (0, 0), idea.name)

    def test_soft_alpha_is_negligible(self):
        for idea in generate("trust the process"):
            stats = analysis.alpha_stats(np.asarray(idea.image.convert("RGBA")))
            self.assertLess(stats.soft_ratio, 0.002, idea.name)

    def test_deterministic(self):
        """Same description, same ideas - so one can be regenerated from its name."""
        a = generate("trust the process")
        b = generate("trust the process")
        for x, y in zip(a, b):
            self.assertTrue(np.array_equal(np.asarray(x.image),
                                           np.asarray(y.image)), x.name)

    def test_empty_description_is_rejected_clearly(self):
        with self.assertRaises(ValueError):
            generate("   ")

    def test_unknown_style_and_palette_raise(self):
        with self.assertRaises(KeyError):
            generate("hello", styles=["does-not-exist"])
        with self.assertRaises(KeyError):
            generate("hello", palettes=["puce"])

    def test_names_are_stable_identifiers(self):
        for idea in generate("trust the process", palettes=["ice"]):
            self.assertEqual(idea.name, f"{idea.style}--{idea.palette}")


class TestBrandRules(unittest.TestCase):
    def test_wording_is_rendered_verbatim(self):
        """Deterministic typography: what is typed is what is set (D-06)."""
        brief = segment("trust the process")
        joined = " ".join(l.text.lower() for l in brief.lines)
        for word in ("trust", "the", "process"):
            self.assertIn(word, joined)

    def test_brand_red_is_not_among_the_palettes(self):
        """Placeholder palettes must not masquerade as the brand colour."""
        from tshirt.branddna import load_brand_dna
        self.assertIsNone(load_brand_dna().colour_hex("brand red"))


if __name__ == "__main__":
    unittest.main()
