import copy
import datetime
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

import numpy as np

import run as dashboard
from lidarcontroller.lidarsignal import lidarSignal


class AutoalignmentRecordingTest(unittest.TestCase):
    def setUp(self):
        self.original_config = copy.deepcopy(dashboard.globalconfig)
        self.addCleanup(lambda: dashboard.globalconfig.update(self.original_config))
        self.config = dict(self.original_config, channel=2, acq_time=1,
                           max_bins=60, bin_offset=3, bias_init=375,
                           fit_init=75, fit_final=225, smooth_level=3,
                           temperature=20, pressure=1010, wavelength=355,
                           raw_limits_final=450, rc_limits_final=450, scan_feed=75)
        self.raw = np.linspace(10, 1, 63) + np.sin(np.arange(63)) * 0.1
        self.controller = Mock(shots_number=102)
        self.controller.getAnalogSignalmV.return_value = self.raw
        controller_patch = patch.object(dashboard, "lc", self.controller)
        controller_patch.start()
        self.addCleanup(controller_patch.stop)
        sounding_patch = patch.object(dashboard.lidar, "sounding_data", {
            "height": [], "temperature": [], "pressure": []
        })
        sounding_patch.start()
        self.addCleanup(sounding_patch.stop)

    def test_capture_preserves_original_mv_and_uses_frozen_settings(self):
        # Simulate edits to the interface while hardware acquisition is waiting.
        self.controller.msDelay.side_effect = lambda delay: dashboard.globalconfig.update(
            channel=9, temperature=40, pressure=900, wavelength=1064, bin_offset=10
        )
        point = dashboard.acquire_autoalignment_point(self.config)
        self.controller.selectTR.assert_called_once_with(2)
        self.controller.msDelay.assert_called_once_with(1000)
        self.controller.getAnalogSignalmV.assert_called_once_with(2, 63, "A", 0)
        self.assertEqual(point["channel"], 2)
        self.assertEqual(point["data_mv"], self.raw.tolist())
        self.assertEqual(point["bins"], 63)
        self.assertEqual(point["bin_size_m"], 7.5)
        self.assertEqual(point["signal_units"], "mV")
        self.assertEqual(point["shots"], 102)
        self.assertEqual(point["atmospheric_model"], "us_standard")
        start = datetime.datetime.fromisoformat(point["timestamp"])
        end = datetime.datetime.fromisoformat(point["timestamp_end"])
        self.assertIsNotNone(start.tzinfo)
        self.assertGreaterEqual(end, start)
        figure = json.loads(point["plots"]["plot_lidar_signal"])
        # The saved trace is prior to insertion of the processing zero and offset.
        self.assertEqual(len(figure["data"][0]["y"]), 61)
        np.testing.assert_allclose(figure["data"][0]["y"], self.raw[2:])

    def test_json_saves_only_requested_configuration_keys_and_actual_values(self):
        config = dict(self.config, future_ui_setting="not measurement metadata")
        expected_fields = {
            "channel", "acq_time", "bin_offset", "max_bins", "bias_init", "bias_final",
            "temperature", "pressure", "masl", "wavelength", "fit_init", "fit_final",
            "motor_resolution", "motor_feed_rate", "corr_range_init", "corr_range_final",
            "grid_min_resolution", "scan_rows", "scan_cols", "scan_step_x", "scan_step_y",
            "scan_feed", "scan_pattern", "scan_centered", "scan_reverse",
        }
        record = {"index": 0, "data_mv": [1.25, 2.5], "pearson": 0.8}
        best = {"index": 0, "pearson": 0.8}
        original = copy.deepcopy(config)
        with TemporaryDirectory() as directory, patch.object(dashboard, "APP_ROOT", directory):
            filename = dashboard.save_autoalignment_results(config, [record], best)
            path = Path(directory) / "acquisdata" / filename
            document = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(set(document["globalconfig"]), expected_fields)
        self.assertEqual(document["globalconfig"], {key: config[key] for key in expected_fields})
        self.assertEqual(document["results"], [record])
        self.assertEqual(document["best"], best)
        self.assertEqual(config, original)

    def assert_json_can_reconstruct_capture(self):
        point = dashboard.acquire_autoalignment_point(self.config)
        record = {key: value for key, value in point.items() if key != "plots"}
        record.update(index=0, x=1.0, y=-1.0)
        with TemporaryDirectory() as directory, patch.object(dashboard, "APP_ROOT", directory):
            filename = dashboard.save_autoalignment_results(
                self.config, [record], {"index": 0, "pearson": point["pearson"]}
            )
            path = Path(directory) / "acquisdata" / filename
            document = json.loads(path.read_text(encoding="utf-8"))
        saved = document["results"][0]
        self.assertEqual(saved["data_mv"], self.raw.tolist())
        for key in ["acq_time", "temperature", "pressure", "wavelength", "fit_init",
                    "fit_final", "scan_feed", "bin_offset"]:
            self.assertEqual(document["globalconfig"][key], self.config[key])
        self.assertEqual(document["best"]["index"], saved["index"])
        replayed = lidarSignal()
        replayed.sounding_data = saved["sounding_data"]
        # Display smoothing may be chosen independently when replaying raw data.
        self.assertNotIn("smooth_level", document["globalconfig"])
        replay_config = dict(document["globalconfig"], smooth_level=1)
        dashboard.process_lidar_trace(np.array(saved["data_mv"]),
                                      config=replay_config, signal=replayed)
        self.assertAlmostEqual(replayed.alignment_factor, saved["pearson"], places=12)
        self.assertAlmostEqual(replayed.bias, saved["bias_mv"], places=12)
        figure = json.loads(point["plots"]["plot_lidar_signal"])
        np.testing.assert_allclose(replayed.raw_signal, figure["data"][0]["y"])
        return saved

    def test_json_reconstructs_raw_and_pearson_with_different_display_smoothing(self):
        self.assert_json_can_reconstruct_capture()

    def test_display_smoothing_changes_corrected_plot_but_not_raw_or_pearson(self):
        first = dashboard.acquire_autoalignment_point(dict(self.config, smooth_level=1))
        second = dashboard.acquire_autoalignment_point(dict(self.config, smooth_level=9))
        self.assertEqual(first["data_mv"], second["data_mv"])
        self.assertAlmostEqual(first["pearson"], second["pearson"], places=12)
        first_raw = json.loads(first["plots"]["plot_lidar_signal"])["data"][0]["y"]
        second_raw = json.loads(second["plots"]["plot_lidar_signal"])["data"][0]["y"]
        self.assertEqual(first_raw, second_raw)
        first_rc = json.loads(first["plots"]["plot_lidar_range_correction"])["data"][0]["y"]
        second_rc = json.loads(second["plots"]["plot_lidar_range_correction"])["data"][0]["y"]
        self.assertFalse(np.allclose(first_rc, second_rc))

    def test_json_includes_sounding_needed_to_reconstruct_custom_atmosphere(self):
        profile = {
            "height": [0, 1000, 2000, 3000],
            "temperature": [300, 290, 280, 270],
            "pressure": [1010, 900, 800, 700],
        }
        dashboard.lidar.sounding_data = profile
        saved = self.assert_json_can_reconstruct_capture()
        self.assertEqual(saved["atmospheric_model"], "sounding")
        self.assertEqual(saved["sounding_data"], profile)
        profile["temperature"][0] = 500
        self.assertEqual(saved["sounding_data"]["temperature"][0], 300)


if __name__ == "__main__":
    unittest.main()
