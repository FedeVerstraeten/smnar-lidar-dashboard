import unittest
from unittest.mock import patch

import grbl_fake_serial as grbl


class GrblFakeSerialTest(unittest.TestCase):
    def setUp(self):
        grbl.pos = {"X": 0.0, "Y": 0.0, "Z": 0.0}
        grbl.feed = 500.0
        grbl.absolute_mode = True
        grbl.state = "Idle"

    def test_status_reports_position_and_feed(self):
        grbl.pos.update({"X": 1.25, "Y": -2.5, "Z": 3.0})
        grbl.feed = 750.0

        status = grbl.handle_command("?")

        self.assertEqual(
            status,
            [
                "<Idle|MPos:1.250,-2.500,3.000|"
                "WPos:1.250,-2.500,3.000|FS:750,0>"
            ],
        )

    @patch("grbl_fake_serial.time.sleep", return_value=None)
    def test_absolute_and_relative_movements(self, _sleep):
        self.assertEqual(
            grbl.handle_command("G90 G1 X2.5 Y-1.5 F800"),
            ["ok"],
        )
        self.assertEqual(grbl.pos, {"X": 2.5, "Y": -1.5, "Z": 0.0})
        self.assertEqual(grbl.feed, 800.0)

        self.assertEqual(grbl.handle_command("G91 G0 X1 Y2 Z-3"), ["ok"])
        self.assertEqual(grbl.pos, {"X": 3.5, "Y": 0.5, "Z": -3.0})
        self.assertFalse(grbl.absolute_mode)

    @patch("grbl_fake_serial.time.sleep", return_value=None)
    def test_movements_are_clamped_to_axis_limits(self, _sleep):
        grbl.handle_command("G90 G1 X99 Y-99 Z8")

        self.assertEqual(grbl.pos, {"X": 5.0, "Y": -5.0, "Z": 5.0})

    def test_homing_and_soft_reset_restore_origin(self):
        grbl.pos = {"X": 1.0, "Y": 2.0, "Z": 3.0}
        self.assertEqual(grbl.handle_command("$H"), ["ok"])
        self.assertEqual(grbl.pos, {"X": 0.0, "Y": 0.0, "Z": 0.0})

        grbl.pos = {"X": -1.0, "Y": -2.0, "Z": -3.0}
        self.assertEqual(
            grbl.handle_command("\x18"),
            ["Grbl 1.1h ['$' for help]"],
        )
        self.assertEqual(grbl.pos, {"X": 0.0, "Y": 0.0, "Z": 0.0})
        self.assertEqual(grbl.state, "Idle")

    def test_unlock_settings_and_supported_commands(self):
        self.assertEqual(
            grbl.handle_command("$X"),
            ["[MSG:Caution: Unlocked]", "ok"],
        )
        settings = grbl.handle_command("$$")
        self.assertIn("$100=250.000", settings)
        self.assertEqual(settings[-1], "ok")
        self.assertEqual(grbl.handle_command("$110=900"), ["ok"])
        self.assertEqual(grbl.handle_command("G21"), ["ok"])
        self.assertEqual(grbl.handle_command("M5"), ["ok"])


if __name__ == "__main__":
    unittest.main()
