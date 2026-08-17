"""Validation rules, with emphasis on the two that protect physical output:

  * PENDING is never silently treated as PASS (no invented tolerances, D-11)
  * proprietary terminology must match byte-exactly (D-06 as an IP control)
"""

import unittest

import numpy as np

from tshirt.core import validate
from tshirt.core.profile import ASSUMED, CONFIRMED, UNKNOWN, Field, PrinterProfile


def make_profile(**overrides) -> PrinterProfile:
    base = {
        "accepted_formats": Field("accepted_formats", ["PNG"], CONFIRMED),
        "requires_transparency": Field("requires_transparency", True, CONFIRMED),
        "colour_space": Field("colour_space", "sRGB", ASSUMED),
        "required_dpi": Field("required_dpi", 300, ASSUMED),
        "max_width_mm": Field("max_width_mm", None, UNKNOWN),
        "max_height_mm": Field("max_height_mm", None, UNKNOWN),
        "min_reliable_stroke_mm": Field("min_reliable_stroke_mm", None, UNKNOWN),
        "max_partial_alpha_ratio": Field("max_partial_alpha_ratio", None, UNKNOWN),
    }
    base.update({k: v for k, v in overrides.items()})
    return PrinterProfile(name="test", fields=base)


def make_rgba(w=3308, h=1202, ink_w=None, alpha=255) -> np.ndarray:
    """Transparent canvas with a solid opaque bar spanning the full width."""
    arr = np.zeros((h, w, 4), dtype=np.uint8)
    ink_w = ink_w or w
    arr[h // 4:3 * h // 4, :ink_w, :3] = 255
    arr[h // 4:3 * h // 4, :ink_w, 3] = alpha
    return arr


def make_asset(**kw) -> validate.AssetUnderTest:
    defaults = dict(
        name="test.png", rgba=make_rgba(), image_format="PNG", mode="RGBA",
        declared_width_mm=280.08, declared_height_mm=101.77,
        rendered_strings=[], authoritative_strings=[], missing_glyph_chars=[],
    )
    defaults.update(kw)
    return validate.AssetUnderTest(**defaults)


def fully_resolved_profile() -> PrinterProfile:
    """A profile where every tolerance is known — the only route to PRINT_READY."""
    return make_profile(
        max_width_mm=Field("max_width_mm", 560.0, CONFIRMED),
        max_height_mm=Field("max_height_mm", 1000.0, CONFIRMED),
        min_reliable_stroke_mm=Field("min_reliable_stroke_mm", 0.5, CONFIRMED),
        max_partial_alpha_ratio=Field("max_partial_alpha_ratio", 0.05, CONFIRMED),
    )


class TestNoInventedThresholds(unittest.TestCase):
    """The anti-invention guarantee survives the advisory reclassification."""

    def test_unknown_stroke_threshold_is_never_a_pass(self):
        report = validate.validate(make_asset(), make_profile())
        f = next(x for x in report.findings if x.check == "minimum_feature")
        self.assertEqual(f.verdict, validate.ADVISORY)
        self.assertNotEqual(f.verdict, validate.PASS)
        self.assertIn("p1_stroke_mm", f.detail)

    def test_unknown_alpha_tolerance_is_never_a_pass(self):
        report = validate.validate(make_asset(), make_profile())
        f = next(x for x in report.findings if x.check == "alpha_quality")
        self.assertEqual(f.verdict, validate.ADVISORY)
        self.assertNotEqual(f.verdict, validate.PASS)
        self.assertIn("soft_ratio", f.detail)

    def test_known_threshold_produces_a_real_verdict(self):
        profile = make_profile(
            min_reliable_stroke_mm=Field("min_reliable_stroke_mm", 0.5, CONFIRMED))
        report = validate.validate(make_asset(), profile)
        f = next(x for x in report.findings if x.check == "minimum_feature")
        self.assertIn(f.verdict, (validate.PASS, validate.FAIL))


class TestReadinessModel(unittest.TestCase):
    """Two states. Blocking checks are OUR correctness; advisories are the printer's."""

    def test_advisories_do_not_block_print_ready(self):
        """The central correction: printer-owned unknowns must not gate our export."""
        report = validate.validate(make_asset(), make_profile())
        self.assertTrue(report.advisories)
        self.assertEqual(report.readiness, validate.PRINT_READY)
        self.assertTrue(report.is_print_ready)

    def test_failure_yields_not_ready(self):
        report = validate.validate(make_asset(image_format="TIFF"), make_profile())
        self.assertEqual(report.readiness, validate.NOT_READY)
        self.assertFalse(report.is_print_ready)

    def test_blocking_check_that_cannot_run_still_blocks(self):
        """A gap in what WE must verify is not the same as a printer-owned unknown."""
        profile = make_profile(
            accepted_formats=Field("accepted_formats", None, UNKNOWN))
        report = validate.validate(make_asset(), profile)
        f = next(x for x in report.findings if x.check == "format")
        self.assertEqual(f.verdict, validate.PENDING)
        self.assertEqual(report.readiness, validate.NOT_READY)

    def test_failure_dominates_advisories(self):
        report = validate.validate(make_asset(image_format="TIFF"), make_profile())
        self.assertTrue(report.advisories)
        self.assertEqual(report.readiness, validate.NOT_READY)

    def test_warnings_do_not_block(self):
        arr = make_rgba()
        arr[0, 0, :3] = 255
        arr[0, 0, 3] = 0
        report = validate.validate(make_asset(rgba=arr), make_profile())
        self.assertTrue(report.warnings)
        self.assertEqual(report.readiness, validate.PRINT_READY)

    def test_middle_state_is_gone(self):
        """READY_FOR_CALIBRATION existed to hold printer-characterisation work."""
        self.assertFalse(hasattr(validate, "READY_FOR_CALIBRATION"))


class TestAdvisoryClassification(unittest.TestCase):
    """Which checks block, and which merely report. This must not regress."""

    BLOCKING = {"format", "colour_space", "alpha_channel", "transparency_present",
                "effective_dpi", "rendered_bounds", "authoritative_string",
                "glyph_coverage"}
    ADVISORY = {"alpha_quality", "minimum_feature", "max_width", "max_height"}

    def setUp(self):
        self.report = validate.validate(
            make_asset(rendered_strings=["N-Codes"], authoritative_strings=["N-Codes"]),
            make_profile())

    def test_printer_owned_checks_are_advisory(self):
        got = {f.check for f in self.report.advisories}
        self.assertEqual(got, self.ADVISORY)

    def test_no_blocking_check_is_advisory(self):
        for f in self.report.findings:
            if f.check in self.BLOCKING:
                self.assertNotEqual(f.verdict, validate.ADVISORY,
                                    f"{f.check} must remain a blocking check")

    def test_advisories_still_report_their_measurement(self):
        """Not blocking is not the same as not measuring."""
        by_check = {f.check: f for f in self.report.advisories}
        self.assertIn("p1_stroke_mm", by_check["minimum_feature"].detail)
        self.assertIn("soft_ratio", by_check["alpha_quality"].detail)

    def test_advisories_name_their_owner(self):
        for f in self.report.advisories:
            self.assertIn(f.resolution,
                          (validate.BY_PRINTER_EXPERTISE, validate.BY_PRINTER_ANSWER))

    def test_no_threshold_is_invented(self):
        """Advisory means 'no threshold supplied', never 'threshold assumed'."""
        for f in self.report.advisories:
            self.assertNotIn("tolerance", f.detail)
            self.assertNotIn("min_reliable_stroke_mm", f.detail)

    def test_supplied_threshold_converts_advisory_to_a_real_verdict(self):
        profile = make_profile(
            min_reliable_stroke_mm=Field("min_reliable_stroke_mm", 0.5, CONFIRMED))
        report = validate.validate(make_asset(), profile)
        f = next(x for x in report.findings if x.check == "minimum_feature")
        self.assertIn(f.verdict, (validate.PASS, validate.FAIL))
        self.assertNotEqual(f.verdict, validate.ADVISORY)

    def test_summary_separates_blocking_from_advisory(self):
        s = self.report.summary()
        self.assertEqual(s["readiness"], validate.PRINT_READY)
        self.assertEqual(sorted(s["advisory"]), sorted(self.ADVISORY))
        self.assertEqual(s["blocking_failures"], [])
        self.assertEqual(s["blocking_unrunnable"], [])


class TestAuthoritativeStrings(unittest.TestCase):
    """Corruption of proprietary terminology must fail, not warn."""

    def _verdicts(self, rendered, authoritative):
        asset = make_asset(rendered_strings=rendered, authoritative_strings=authoritative)
        return [f for f in validate.check_authoritative_strings(asset)
                if f.check == "authoritative_string"]

    def test_exact_whole_string_passes(self):
        f = self._verdicts(["N-Codes"], ["N-Codes"])[0]
        self.assertEqual(f.verdict, validate.PASS)
        self.assertEqual(f.detail["match"], "whole_string")

    def test_exact_token_inside_longer_line_passes(self):
        f = self._verdicts(["N-Codes  E-Codes  Inner DNA"], ["N-Codes"])[0]
        self.assertEqual(f.verdict, validate.PASS)
        self.assertEqual(f.detail["match"], "token")

    def test_missing_hyphen_fails(self):
        f = self._verdicts(["N Codes"], ["N-Codes"])[0]
        self.assertEqual(f.verdict, validate.FAIL)

    def test_removed_hyphen_fails(self):
        self.assertEqual(self._verdicts(["NCodes"], ["N-Codes"])[0].verdict, validate.FAIL)

    def test_wrong_case_fails(self):
        for wrong in ("N-codes", "n-codes", "N-CODES"):
            self.assertEqual(self._verdicts([wrong], ["N-Codes"])[0].verdict,
                             validate.FAIL, msg=wrong)

    def test_singular_fails(self):
        self.assertEqual(self._verdicts(["N-Code"], ["N-Codes"])[0].verdict, validate.FAIL)

    def test_glued_to_adjacent_characters_fails(self):
        """Substring matching alone would wrongly accept these."""
        for glued in ("XN-Codes", "N-Codesy", "N-Codes-X", "AN-CodesB"):
            self.assertEqual(self._verdicts([glued], ["N-Codes"])[0].verdict,
                             validate.FAIL, msg=glued)

    def test_punctuation_boundaries_are_acceptable(self):
        for ok in ("THE N-Codes.", "(N-Codes)", "N-Codes,", "'N-Codes'"):
            self.assertEqual(self._verdicts([ok], ["N-Codes"])[0].verdict,
                             validate.PASS, msg=ok)

    def test_inner_dna_spacing_matters(self):
        self.assertEqual(self._verdicts(["InnerDNA"], ["Inner DNA"])[0].verdict,
                         validate.FAIL)
        self.assertEqual(self._verdicts(["Inner  DNA"], ["Inner DNA"])[0].verdict,
                         validate.FAIL)

    def test_brand_name_case_matters(self):
        self.assertEqual(
            self._verdicts(["The Incredible You"], ["THE INCREDIBLE YOU"])[0].verdict,
            validate.FAIL)

    def test_near_miss_is_reported_to_help_diagnosis(self):
        f = self._verdicts(["N Codes"], ["N-Codes"])[0]
        self.assertTrue(f.detail["near_misses"])

    def test_missing_glyphs_fail(self):
        asset = make_asset(rendered_strings=["N-Codes"], authoritative_strings=["N-Codes"],
                           missing_glyph_chars=["—"])
        f = next(x for x in validate.check_authoritative_strings(asset)
                 if x.check == "glyph_coverage")
        self.assertEqual(f.verdict, validate.FAIL)


class TestTokenBoundary(unittest.TestCase):
    def test_hyphen_is_not_a_boundary(self):
        self.assertFalse(validate.contains_exact_token("N-Codes-Plus", "N-Codes"))

    def test_space_is_a_boundary(self):
        self.assertTrue(validate.contains_exact_token("A N-Codes B", "N-Codes"))

    def test_string_edges_are_boundaries(self):
        self.assertTrue(validate.contains_exact_token("N-Codes", "N-Codes"))

    def test_digit_is_not_a_boundary(self):
        self.assertFalse(validate.contains_exact_token("N-Codes2", "N-Codes"))


class TestTransparency(unittest.TestCase):
    def test_fully_opaque_asset_fails(self):
        arr = np.full((100, 100, 4), 255, dtype=np.uint8)
        report = validate.validate(make_asset(rgba=arr, declared_width_mm=8.47,
                                              declared_height_mm=8.47), make_profile())
        f = next(x for x in report.findings if x.check == "transparency_present")
        self.assertEqual(f.verdict, validate.FAIL)
        self.assertEqual(report.readiness, validate.NOT_READY)

    def test_non_rgba_mode_fails(self):
        report = validate.validate(make_asset(mode="RGB"), make_profile())
        self.assertEqual(
            next(x for x in report.findings if x.check == "alpha_channel").verdict,
            validate.FAIL)

    def test_stray_colour_in_transparent_pixels_warns(self):
        arr = make_rgba()
        arr[0, 0, :3] = 255   # colour data where alpha is 0
        arr[0, 0, 3] = 0
        report = validate.validate(make_asset(rgba=arr), make_profile())
        f = next(x for x in report.findings if x.check == "stray_colour_in_transparent")
        self.assertEqual(f.verdict, validate.WARNING)


class TestFormatAndDpi(unittest.TestCase):
    def test_rejected_format_fails(self):
        report = validate.validate(make_asset(image_format="TIFF"), make_profile())
        self.assertEqual(next(x for x in report.findings if x.check == "format").verdict,
                         validate.FAIL)

    def test_insufficient_dpi_fails(self):
        asset = make_asset(rgba=make_rgba(w=1000, h=400), declared_width_mm=280.0,
                           declared_height_mm=112.0)
        report = validate.validate(asset, make_profile())
        self.assertEqual(
            next(x for x in report.findings if x.check == "effective_dpi").verdict,
            validate.FAIL)

    def test_oversized_artwork_fails_max_width(self):
        profile = make_profile(max_width_mm=Field("max_width_mm", 200.0, CONFIRMED))
        report = validate.validate(make_asset(), profile)
        self.assertEqual(next(x for x in report.findings if x.check == "max_width").verdict,
                         validate.FAIL)


class TestRenderedBounds(unittest.TestCase):
    def test_ink_to_every_edge_passes(self):
        arr = np.zeros((100, 100, 4), dtype=np.uint8)
        arr[:, :, :] = 255
        report = validate.validate(make_asset(rgba=arr, declared_width_mm=8.47,
                                              declared_height_mm=8.47), make_profile())
        self.assertEqual(
            next(x for x in report.findings if x.check == "rendered_bounds").verdict,
            validate.PASS)

    def test_large_transparent_margin_warns(self):
        arr = np.zeros((1200, 3308, 4), dtype=np.uint8)
        arr[400:800, 800:2400, :] = 255
        report = validate.validate(make_asset(rgba=arr), make_profile())
        f = next(x for x in report.findings if x.check == "rendered_bounds")
        self.assertEqual(f.verdict, validate.WARNING)

    def test_empty_asset_fails(self):
        arr = np.zeros((100, 100, 4), dtype=np.uint8)
        report = validate.validate(make_asset(rgba=arr, declared_width_mm=8.47,
                                              declared_height_mm=8.47), make_profile())
        self.assertEqual(
            next(x for x in report.findings if x.check == "rendered_bounds").verdict,
            validate.FAIL)


class TestReport(unittest.TestCase):
    def test_failures_block_everything(self):
        report = validate.validate(make_asset(image_format="TIFF"), make_profile())
        self.assertFalse(report.is_print_ready)
        self.assertEqual(report.readiness, validate.NOT_READY)

    def test_summary_is_json_serialisable(self):
        import json
        report = validate.validate(make_asset(), make_profile())
        json.dumps(report.summary())


if __name__ == "__main__":
    unittest.main()
