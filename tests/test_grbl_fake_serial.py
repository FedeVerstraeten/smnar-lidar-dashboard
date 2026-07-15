import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from lidarcontroller.motorcontroller import MotorController
from simulator import grbl_fake_serial as grbl


class SimulatorSerial:
    def __init__(self):
        self.command_buffer = b""
        self.responses = []
        self.writes = []

    def write(self, data):
        self.writes.append(data)
        self.command_buffer, events = grbl.process_serial_data(
            data, self.command_buffer
        )
        for _, response_lines in events:
            self.responses.extend(
                (line + "\r\n").encode() for line in response_lines
            )

    def readline(self):
        return self.responses.pop(0) if self.responses else b""

    def reset_input_buffer(self):
        self.responses.clear()

    def flush(self):
        pass


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

    def test_status_waits_for_line_ending(self):
        buffer, events = grbl.process_serial_data(b"?")

        self.assertEqual(buffer, b"?")
        self.assertEqual(events, [])

    def test_status_with_crlf_emits_one_response(self):
        buffer, events = grbl.process_serial_data(b"?\r\n")

        self.assertEqual(buffer, b"")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0][0], "?")
        self.assertEqual(
            events[0][1],
            ["<Idle|MPos:0.000,0.000,0.000|WPos:0.000,0.000,0.000|FS:500,0>"],
        )

    def test_motor_controller_sends_line_terminated_status(self):
        serial_connection = SimulatorSerial()
        motor = MotorController(ser=serial_connection)

        status = motor.status(timeout_s=0.1)

        self.assertIn("<Idle|", status)
        self.assertEqual(serial_connection.writes, [b"?\r\n"])

    @patch("simulator.grbl_fake_serial.time.sleep", return_value=None)
    def test_motor_controller_completes_grid_and_returns_home(self, _sleep):
        visited = []

        with TemporaryDirectory() as temp_dir, patch.object(
            MotorController, "STATE_FILE", Path(temp_dir) / "state.json"
        ), patch.object(
            MotorController, "HISTORY_FILE", Path(temp_dir) / "history.jsonl"
        ):
            motor = MotorController(ser=SimulatorSerial())
            motor.initialize(feed=50)
            motor.disable_limits()
            motor.scan_grid(
                rows=3,
                cols=3,
                step_x=1.0,
                step_y=1.0,
                centered=True,
                on_point=lambda index, x, y: visited.append((index, x, y)),
            )
            motor.go_home(feed=50)

        self.assertEqual(len(visited), 9)
        self.assertEqual(motor.position, {"x": 0.0, "y": 0.0, "z": 0.0})

    @patch("simulator.grbl_fake_serial.time.sleep", return_value=None)
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

    @patch("simulator.grbl_fake_serial.time.sleep", return_value=None)
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
