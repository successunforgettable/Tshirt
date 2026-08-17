"""Brand DNA guards.

These tests encode product rules, not implementation detail. If one fails, the
data has drifted somewhere it must not go: an invented meaning, a reconstructed
logo, or a guessed brand colour.
"""

import json
import unittest
from pathlib import Path

from tshirt.branddna import DEFAULT_PATH, load_brand_dna

OPAQUE_TERM_IDS = ["inner-dna", "baselines", "n-codes", "e-codes",
                   "outcomes-plus", "secret-millionaire-blueprint"]


class TestNoInventedInformation(unittest.TestCase):
    """The hardest rule in the project: unknown stays unknown (D-16)."""

    @classmethod
    def setUpClass(cls):
        cls.brand = load_brand_dna()
        cls.raw = json.loads(Path(DEFAULT_PATH).read_text(encoding="utf-8"))

    def test_all_six_terms_present(self):
        self.assertEqual(sorted(self.brand.vocabulary), sorted(OPAQUE_TERM_IDS))

    def test_no_meaning_is_ever_populated(self):
        for entry in self.brand.vocabulary.values():
            self.assertIsNone(entry.meaning, f"{entry.canonical_name} has an invented meaning")

    def test_no_programme_relationship_or_usage_invented(self):
        for e in self.raw["vocabulary"]:
            for field in ("meaning", "meaning_source", "programme", "approved_usage",
                          "restricted_usage", "merch_relevance", "creative_notes"):
                self.assertIsNone(e[field], f"{e['canonical_name']}.{field} was invented")
            self.assertEqual(e["related_terms"], [],
                             f"{e['canonical_name']} has invented relationships")

    def test_every_term_is_opaque(self):
        self.assertEqual(len(self.brand.opaque_terms), 6)
        for e in self.brand.opaque_terms:
            self.assertTrue(e.is_opaque)

    def test_approval_covers_spelling_not_meaning(self):
        for e in self.brand.vocabulary.values():
            self.assertTrue(e.is_approved)
            self.assertTrue(e.is_opaque)


class TestExactSpelling(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.brand = load_brand_dna()

    def test_spellings_are_byte_exact(self):
        expected = {
            "inner-dna": "Inner DNA",
            "baselines": "Baselines",
            "n-codes": "N-Codes",
            "e-codes": "E-Codes",
            "outcomes-plus": "Outcomes Plus",
            "secret-millionaire-blueprint": "Secret Millionaire Blueprint",
        }
        for tid, spelling in expected.items():
            self.assertEqual(self.brand.exact_spelling(tid), spelling)

    def test_hyphens_preserved(self):
        self.assertIn("-", self.brand.exact_spelling("n-codes"))
        self.assertIn("-", self.brand.exact_spelling("e-codes"))

    def test_unknown_term_raises(self):
        with self.assertRaises(KeyError):
            self.brand.term("does-not-exist")


class TestNameIsNotMark(unittest.TestCase):
    """The canonical NAME is a usable string; the MARK is a file (D-17)."""

    @classmethod
    def setUpClass(cls):
        cls.brand = load_brand_dna()

    def test_canonical_name_available_as_text(self):
        self.assertEqual(self.brand.canonical_brand_name, "THE INCREDIBLE YOU")

    def test_no_logo_assets_supplied(self):
        self.assertEqual(self.brand.brand_mark_assets, [])

    def test_official_logo_tier_is_unavailable(self):
        self.assertFalse(self.brand.official_logo_available)
        self.assertFalse(self.brand.usage_tiers["official_logo"]["currently_available"])

    def test_other_tiers_are_available(self):
        for tier in ("brand_inspired", "campaign", "universe_original"):
            self.assertTrue(self.brand.usage_tiers[tier]["currently_available"])


class TestBrandColour(unittest.TestCase):
    def test_brand_red_hex_remains_unknown(self):
        """Never sampled or estimated from screenshots."""
        self.assertIsNone(load_brand_dna().colour_hex("brand red"))


class TestAuthoritativeStrings(unittest.TestCase):
    def test_resolves_term_ids_to_exact_spellings(self):
        brand = load_brand_dna()
        out = brand.authoritative_strings(["n-codes", "inner-dna"], include_brand_name=True)
        self.assertEqual(out, ["THE INCREDIBLE YOU", "N-Codes", "Inner DNA"])


if __name__ == "__main__":
    unittest.main()
