import socket
import struct
import threading
import time
import unittest
import json
import os
import tempfile
from pathlib import Path
from unittest import mock

import numpy as np

from simulator.licel_fake_tcp import (
    LicelProtocol,
    LicelState,
    LicelTCPServer,
)
from lidarcontroller.licelcontroller import licelController


class LicelFakeTCPTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        state = LicelState((0, 1, 2), shot_rate=1000.0)
        cls.server = LicelTCPServer(("127.0.0.1", 0), state)
        cls.thread = threading.Thread(
            target=cls.server.serve_forever, daemon=True
        )
        cls.thread.start()
        cls.host, cls.port = cls.server.server_address

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def setUp(self):
        self.controller = licelController()
        self.controller.openConnection(self.host, self.port)

    def tearDown(self):
        if self.controller.sock is not None:
            self.controller.closeConnection()

    def test_controller_reports_connection_lifecycle(self):
        self.assertTrue(self.controller.isConnected())

        self.controller.closeConnection()

        self.assertFalse(self.controller.isConnected())

    def test_failed_connection_can_be_retried(self):
        controller = licelController()
        fake_socket = mock.Mock()
        fake_socket.connect.side_effect = OSError("connection refused")

        with mock.patch(
            "lidarcontroller.licelcontroller.socket.socket",
            return_value=fake_socket,
        ):
            with self.assertRaisesRegex(
                ValueError, "Connection to server failed"
            ):
                controller.openConnection("127.0.0.1", 1)

        self.assertFalse(controller.isConnected())
        fake_socket.close.assert_called_once()

    def test_single_recorder_command_flow(self):
        self.assertEqual(self.controller.selectTR(0), 0)
        self.assertEqual(self.controller.setInputRange(0), 0)
        self.assertEqual(self.controller.setThresholdMode(1), 0)
        self.assertEqual(self.controller.setDiscriminatorLevel(16), 0)
        self.assertEqual(self.controller.clearMemory(), 0)
        self.assertEqual(self.controller.startAcquisition(), 0)
        time.sleep(0.05)
        self.assertEqual(self.controller.stopAcquisition(), 0)
        self.assertEqual(self.controller.getStatus(), 0)
        self.assertGreater(self.controller.shots_number, 2)

    def test_data_response_is_exactly_two_bytes_per_bin(self):
        self.assertEqual(self.controller.selectTR(0), 0)
        self.controller.startAcquisition()
        time.sleep(0.01)
        self.controller.stopAcquisition()

        data = self.controller.getDatasets(0, "LSW", 64, "A")

        self.assertEqual(data.dtype, np.dtype(np.uint16))
        self.assertEqual(len(data), 64)
        self.assertEqual(data[0], 0)
        self.assertTrue(np.any(data[1:] > 0))

    def test_controller_accumulates_fragmented_tcp_dataset(self):
        expected = (0, 10, 20, 30)
        payload = struct.pack("<4H", *expected)

        class FragmentedSocket:
            def __init__(self):
                self.fragments = [
                    payload[:3],
                    payload[3:5],
                    payload[5:],
                ]

            def sendall(self, _command):
                pass

            def settimeout(self, _timeout):
                pass

            def recv(self, size):
                fragment = self.fragments.pop(0)
                return fragment[:size]

        controller = licelController()
        controller.sock = FragmentedSocket()

        data = controller.getDatasets(0, "LSW", 4, "A")

        self.assertEqual(data.tolist(), list(expected))

    def test_analog_signal_end_to_end(self):
        bins = 128
        self.assertEqual(self.controller.selectTR(1), 0)
        self.controller.startAcquisition()
        time.sleep(0.01)
        self.controller.stopAcquisition()

        signal_mv = self.controller.getAnalogSignalmV(1, bins, "A", 0)

        self.assertEqual(len(signal_mv), bins)
        self.assertTrue(np.all(np.isfinite(signal_mv)))
        self.assertGreater(float(np.max(signal_mv)), 0.0)

    def test_recorded_signal_is_encoded_as_licel_lsw_msw(self):
        expected_mv = np.array([1.0, 2.5, 4.0, 8.0])
        with tempfile.TemporaryDirectory() as data_dir:
            recording_path = os.path.join(data_dir, "lidar_simul_0.json")
            with open(recording_path, "w", encoding="utf-8") as output:
                json.dump(
                    {
                        "0": {
                            "bins": str(len(expected_mv)),
                            "data_mv": expected_mv.tolist(),
                        }
                    },
                    output,
                )

            state = LicelState((0,), 1000.0, (recording_path,))
            server = LicelTCPServer(("127.0.0.1", 0), state)
            thread = threading.Thread(
                target=server.serve_forever, daemon=True
            )
            thread.start()
            controller = licelController()
            try:
                controller.openConnection(*server.server_address)
                controller.selectTR(0)
                controller.startAcquisition()
                time.sleep(0.01)
                controller.stopAcquisition()
                actual_mv = controller.getAnalogSignalmV(
                    0, len(expected_mv), "A", 0
                )
            finally:
                controller.closeConnection()
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

        np.testing.assert_allclose(actual_mv, expected_mv, atol=0.01)

    def test_recorded_signal_retains_sub_adc_count_precision(self):
        expected_mv = np.array([4.6691, 4.6711, 4.6726, 4.6745])
        recorder = type(
            "Recorder",
            (),
            {
                "shots": 66,
                "input_range": 0,
                "recorded_signal_mv": expected_mv.tolist(),
            },
        )()

        lsw = LicelProtocol._dataset_values(
            0, recorder, "LSW", len(expected_mv) + 1
        )
        msw = LicelProtocol._dataset_values(
            0, recorder, "MSW", len(expected_mv) + 1
        )
        accumulated = (
            (np.asarray(msw[1:], dtype=np.uint32) & 0x00FF) << 16
        ) + np.asarray(lsw[1:], dtype=np.uint32)
        actual_mv = accumulated / 64 * (500.0 / 4096.0)

        np.testing.assert_allclose(actual_mv, expected_mv, atol=0.001)

    def test_multiple_recorder_flow(self):
        self.assertEqual(self.controller.selectTR("0,1,2"), 0)
        self.assertEqual(self.controller.multipleClearMemory(), 0)
        self.assertEqual(self.controller.multipleStartAcquisition(), 0)
        time.sleep(0.01)
        self.assertEqual(self.controller.multipleStopAcquisition(), 0)

        for device_id in (0, 1, 2):
            data = self.controller.getDatasets(
                device_id, "MSW", 32, "A"
            )
            self.assertEqual(len(data), 32)

    def test_unknown_command_uses_manual_error_format(self):
        with socket.create_connection((self.host, self.port), timeout=2) as sock:
            sock.sendall(b"BOGUS\r\n")
            self.assertEqual(sock.recv(1024), b"BOGUS unknown command\r\n")

    def test_recording_files_have_all_channels_and_bins(self):
        recording_paths = sorted(
            Path("simulator/data").glob("lidar_simul_*.json")
        )

        self.assertEqual(len(recording_paths), 33)
        for recording_path in recording_paths:
            with recording_path.open(encoding="utf-8") as input_file:
                recording = json.load(input_file)

            self.assertEqual(set(recording), {"0", "1", "2", "3"})
            for channel in recording.values():
                self.assertEqual(int(channel["bins"]), 4092)
                self.assertEqual(len(channel["data_mv"]), 4092)
                self.assertTrue(
                    np.all(np.isfinite(channel["data_mv"]))
                )


if __name__ == "__main__":
    unittest.main()
