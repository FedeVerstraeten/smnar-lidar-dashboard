import warnings
import unittest

import numpy as np

from lidarcontroller.lidarsignal import lidarSignal


class LidarSignalFittingTest(unittest.TestCase):
    def make_signal(self, raw_signal, molecular_signal):
        lidar = lidarSignal()
        lidar.raw_signal = np.asarray(raw_signal, dtype=np.float64)
        lidar.pr_mol = np.asarray(molecular_signal, dtype=np.float64)
        lidar.fit_init = 0
        lidar.fit_final = (len(lidar.raw_signal) - 1) * 7.5
        lidar.bias = 0.0
        return lidar

    def test_overlap_fitting_returns_zero_for_constant_signal(self):
        lidar = self.make_signal(
            np.ones(20),
            np.linspace(1.0, 2.0, 20),
        )

        with warnings.catch_warnings():
            warnings.simplefilter("error", RuntimeWarning)
            lidar.overlapFitting()

        self.assertEqual(lidar.alignment_factor, 0.0)
        self.assertEqual(lidar.rms_err, 0.0)

    def test_overlap_fitting_ignores_non_finite_samples(self):
        molecular = np.linspace(1.0, 3.0, 20)
        raw = molecular * 4.0
        raw[3] = np.nan
        raw[8] = np.inf
        lidar = self.make_signal(raw, molecular)

        with warnings.catch_warnings():
            warnings.simplefilter("error", RuntimeWarning)
            lidar.overlapFitting()

        self.assertAlmostEqual(lidar.alignment_factor, 1.0)
        self.assertAlmostEqual(lidar.rms_err, 1.0)

    def test_rayleigh_fit_handles_zero_molecular_profile(self):
        lidar = lidarSignal()
        lidar.rc_signal = np.ones(20)
        lidar.pr2_mol = np.zeros(20)

        lidar.rayleighFit(0, 19 * 7.5)

        self.assertEqual(lidar.adj_factor, 0.0)

    def test_offset_keeps_complete_0_to_30000_meter_range(self):
        lidar = lidarSignal()
        requested_bins = 4000 + 10
        lidar.loadSignal(np.ones(requested_bins))
        lidar.offsetCorrection(10)
        lidar.rangeCorrection(22500)

        self.assertEqual(lidar.bin_long_trace, 4001)
        self.assertEqual(len(lidar.range), 4001)
        self.assertEqual(lidar.range[0], 0.0)
        self.assertEqual(lidar.range[-1], 30000.0)

    def test_range_correction_uses_configured_bias_start(self):
        lidar = lidarSignal()
        lidar.raw_signal = np.concatenate(
            (np.full(3000, 10.0), np.full(1001, 2.0))
        )
        lidar.bin_long_trace = len(lidar.raw_signal)

        lidar.rangeCorrection(22500)

        self.assertEqual(lidar.bin_threshold, 3000)
        self.assertEqual(lidar.bias, 2.0)


if __name__ == "__main__":
    unittest.main()
