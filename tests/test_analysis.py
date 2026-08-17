"""Image analysis primitives — the measurements the validator reasons about."""

import unittest

import numpy as np

from tshirt.core import analysis


def canvas(h=200, w=200) -> np.ndarray:
    return np.zeros((h, w, 4), dtype=np.uint8)


class TestAlphaStats(unittest.TestCase):
    def test_hard_edged_shape_has_no_soft_alpha(self):
        arr = canvas()
        arr[50:150, 50:150, :] = 255
        stats = analysis.alpha_stats(arr)
        self.assertEqual(stats.soft_px, 0)
        self.assertEqual(stats.partial_px, 0)
        self.assertEqual(stats.inked_px, 100 * 100)

    def test_antialiased_edge_is_not_counted_as_soft(self):
        arr = canvas()
        arr[50:150, 50:150, :3] = 255
        arr[50:150, 50:150, 3] = 255
        arr[49, 50:150, :3] = 255
        arr[49, 50:150, 3] = 128          # one-pixel partial edge
        stats = analysis.alpha_stats(arr, edge_band_px=3)
        self.assertGreater(stats.partial_px, 0)
        self.assertEqual(stats.soft_px, 0)

    def test_large_soft_region_is_detected(self):
        """A glow: partial alpha far from any opaque/transparent boundary."""
        arr = canvas()
        arr[20:180, 20:180, :3] = 255
        arr[20:180, 20:180, 3] = 128      # a big translucent block
        stats = analysis.alpha_stats(arr, edge_band_px=3)
        self.assertGreater(stats.soft_px, 0)
        self.assertGreater(stats.soft_ratio, 0.5)

    def test_stray_colour_detected(self):
        arr = canvas()
        arr[10, 10, :3] = 255             # colour with alpha 0
        stats = analysis.alpha_stats(arr)
        self.assertEqual(stats.stray_colour_px, 1)

    def test_ratios_safe_on_empty_image(self):
        stats = analysis.alpha_stats(canvas())
        self.assertEqual(stats.partial_ratio, 0.0)
        self.assertEqual(stats.soft_ratio, 0.0)

    def test_rejects_non_rgba(self):
        with self.assertRaises(ValueError):
            analysis.alpha_stats(np.zeros((10, 10, 3), dtype=np.uint8))


class TestBBox(unittest.TestCase):
    def test_locates_ink(self):
        arr = canvas()
        arr[30:70, 40:90, 3] = 255
        box = analysis.inked_bbox(arr)
        self.assertEqual((box.left, box.top, box.right, box.bottom), (40, 30, 89, 69))
        self.assertEqual((box.width, box.height), (50, 40))

    def test_none_when_empty(self):
        self.assertIsNone(analysis.inked_bbox(canvas()))


class TestStrokeStats(unittest.TestCase):
    def test_measures_known_bar_width(self):
        arr = canvas()
        arr[:, 90:102, 3] = 255           # a 12 px vertical bar
        stats = analysis.stroke_stats(arr)
        self.assertEqual(stats.horizontal.min_px, 12)

    def test_finds_the_thinnest_of_several(self):
        arr = canvas(200, 300)
        arr[10:20, 10:22, 3] = 255        # 12 px
        arr[40:50, 10:13, 3] = 255        # 3 px  <- thinnest
        stats = analysis.stroke_stats(arr)
        self.assertEqual(stats.horizontal.min_px, 3)

    def test_reports_method_limitation(self):
        arr = canvas()
        arr[:, 90:102, 3] = 255
        stats = analysis.stroke_stats(arr)
        self.assertTrue(any("overestimates diagonals" in n for n in stats.notes))

    def test_empty_image_yields_none(self):
        self.assertIsNone(analysis.stroke_stats(canvas()).min_px)


class TestDilate(unittest.TestCase):
    def test_grows_by_one_ring_per_iteration(self):
        m = np.zeros((21, 21), dtype=bool)
        m[10, 10] = True
        self.assertEqual(np.count_nonzero(analysis.dilate(m, 1)), 9)
        self.assertEqual(np.count_nonzero(analysis.dilate(m, 2)), 25)

    def test_zero_iterations_is_identity(self):
        m = np.zeros((5, 5), dtype=bool)
        m[2, 2] = True
        self.assertTrue(np.array_equal(analysis.dilate(m, 0), m))


if __name__ == "__main__":
    unittest.main()
