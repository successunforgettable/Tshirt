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


class TestPendingIsNotPass(unittest.TestCase):
    """The core anti-invention guarantee."""

    def test_unknown_stroke_threshold_yields_pending_not_pass(self):
        report = validate.validate(make_asset(), make_profile())
        f = next(x for x in report.findings if x.check == "minimum_feature")
        self.assertEqual(f.verdict, validate.PENDING)
        self.assertNotEqual(f.verdict, validate.PASS)
        # The measurement is still reported so calibration can turn it into a threshold.
        self.assertIn("p1_stroke_mm", f.detail)

    def test_unknown_alpha_tolerance_yields_pending(self):
        report = validate.validate(make_asset(), make_profile())
        f = next(x for x in report.findings if x.check == "alpha_quality")
        self.assertEqual(f.verdict, validate.PENDING)
        self.assertIn("soft_ratio", f.detail)

    def test_unknown_max_dimensions_yield_pending(self):
        report = validate.validate(make_asset(), make_profile())
        verdicts = {f.check: f.verdict for f in report.findings}
        self.assertEqual(verdicts["max_width"], validate.PENDING)
        self.assertEqual(verdicts["max_height"], validate.PENDING)

    def test_known_threshold_produces_a_real_verdict(self):
        profile = make_profile(
            min_reliable_stroke_mm=Field("min_reliable_stroke_mm", 0.5, CONFIRMED))
        report = validate.validate(make_asset(), profile)
        f = next(x for x in report.findings if x.check == "minimum_feature")
        self.assertIn(f.verdict, (validate.PASS, validate.FAIL))


class TestReadinessModel(unittest.TestCase):
    """Three states. A boolean would have to lie about one of them."""

    def test_pending_withholds_print_ready(self):
        report = validate.validate(make_asset(), make_profile())
        self.assertTrue(report.pending)
        self.assertEqual(report.readiness, validate.READY_FOR_CALIBRATION)
        self.assertFalse(report.is_print_ready,
                         "an asset with unresolved checks must never be print_ready")

    def test_ready_for_calibration_is_still_sendable(self):
        report = validate.validate(make_asset(), make_profile())
        self.assertTrue(report.can_send_for_calibration)

    def test_failure_yields_not_ready(self):
        report = validate.validate(make_asset(image_format="TIFF"), make_profile())
        self.assertEqual(report.readiness, validate.NOT_READY)
        self.assertFalse(report.can_send_for_calibration)
        self.assertFalse(report.is_print_ready)

    def test_failure_dominates_pending(self):
        """A FAIL alongside PENDING is NOT_READY, not READY_FOR_CALIBRATION."""
        report = validate.validate(make_asset(image_format="TIFF"), make_profile())
        self.assertTrue(report.pending)
        self.assertEqual(report.readiness, validate.NOT_READY)

    def test_print_ready_only_when_nothing_is_unresolved(self):
        report = validate.validate(make_asset(), fully_resolved_profile())
        self.assertEqual(report.pending, [])
        self.assertEqual(report.readiness, validate.PRINT_READY)
        self.assertTrue(report.is_print_ready)

    def test_a_single_pending_is_enough_to_withhold_print_ready(self):
        profile = fully_resolved_profile()
        profile.fields["min_reliable_stroke_mm"] = Field(
            "min_reliable_stroke_mm", None, UNKNOWN)
        report = validate.validate(make_asset(), profile)
        self.assertEqual(len(report.pending), 1)
        self.assertEqual(report.readiness, validate.READY_FOR_CALIBRATION)
        self.assertFalse(report.is_print_ready)

    def test_warnings_do_not_withhold_print_ready(self):
        arr = make_rgba()
        arr[0, 0, :3] = 255
        arr[0, 0, 3] = 0
        report = validate.validate(make_asset(rgba=arr), fully_resolved_profile())
        self.assertTrue(report.warnings)
        self.assertEqual(report.readiness, validate.PRINT_READY)


class TestResolutionPaths(unittest.TestCase):
    """Unresolved checks are separated by who resolves them."""

    def setUp(self):
        self.report = validate.validate(make_asset(), make_profile())

    def test_tolerances_are_resolved_by_calibration(self):
        checks = {f.check for f in self.report.awaiting_calibration}
        self.assertEqual(checks, {"minimum_feature", "alpha_quality"})

    def test_printer_limits_are_resolved_by_asking(self):
        checks = {f.check for f in self.report.awaiting_printer_answer}
        self.assertEqual(checks, {"max_width", "max_height"})

    def test_every_pending_declares_a_resolution_path(self):
        for f in self.report.pending:
            self.assertIn(f.resolution,
                          (validate.BY_CALIBRATION, validate.BY_PRINTER_ANSWER),
                          f"{f.check} has no resolution path")

    def test_summary_exposes_readiness_and_unresolved(self):
        s = self.report.summary()
        self.assertEqual(s["readiness"], validate.READY_FOR_CALIBRATION)
        self.assertFalse(s["print_ready"])
        self.assertTrue(s["can_send_for_calibration"])
        self.assertEqual(sorted(s["unresolved"]["awaiting_calibration"]),
                         ["alpha_quality", "minimum_feature"])


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
