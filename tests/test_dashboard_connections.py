import copy
import threading
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

import serial

import run as dashboard
from lidarcontroller.autoalignment import AutoalignmentService
from lidarcontroller.motionconnection import (
    MotionConnection, MotionConnectionBusy, MotionOperationStopped,
)
from lidarcontroller.motorcontroller import MotorController
from simulator import grbl_fake_serial as grbl
from simulator.telecover_fake_serial import TelecoverState


class BridgeSerial:
    """One transport accepting both existing simulator command sets."""

    def __init__(self, **settings):
        self.settings = settings
        self.is_open = True
        self.writes = []
        self.responses = []
        self.telecover = TelecoverState()
        self.fail_writes = False

    def write(self, data):
        if self.fail_writes:
            raise serial.SerialException("USB connection lost")
        self.writes.append(data)
        command = data.decode(errors="ignore").strip()
        if command.startswith("TCV"):
            lines = self.telecover.handle_command(command)
        elif data == b"\x85":
            lines = []
        else:
            lines = grbl.handle_command(command)
        self.responses.extend((line + "\r\n").encode() for line in lines)
        return len(data)

    def readline(self):
        return self.responses.pop(0) if self.responses else b""

    def flush(self):
        pass

    def reset_input_buffer(self):
        self.responses.clear()

    def close(self):
        self.is_open = False


class SharedMotionConnectionTest(unittest.TestCase):
    def setUp(self):
        self.serial = BridgeSerial()
        self.factory = Mock(return_value=self.serial)
        self.link = MotionConnection(serial_factory=self.factory, startup_delay=0)

    def test_operations_share_one_open_port_until_explicit_disconnect(self):
        self.link.connect("COM8")
        self.link.connect("COM8")
        with self.link.operation("alignment") as connection:
            connection.write(b"G21\n")
        with self.link.operation("telecover") as connection:
            connection.write(b"TCVEstado\n")
        self.assertTrue(self.serial.is_open)
        self.assertEqual(self.factory.call_count, 1)
        self.assertEqual(self.link.snapshot()["state"], "connected")
        self.link.disconnect()
        self.assertFalse(self.serial.is_open)

    def test_busy_operations_reject_other_commands_and_disconnect_without_waiting(self):
        self.link.connect("COM8")
        with self.link.operation("autoalignment"):
            self.assertEqual(self.link.snapshot()["state"], "busy")
            with self.assertRaises(MotionConnectionBusy):
                self.link.disconnect()
            with self.assertRaises(MotionConnectionBusy):
                self.link.configure("COM9")
            with self.assertRaises(MotionConnectionBusy):
                with self.link.operation("telecover"):
                    self.fail("Concurrent operation acquired the port")
        self.assertFalse(self.link.snapshot()["busy"])

    def test_stop_does_not_consume_responses_or_allow_following_movement(self):
        self.link.connect("COM8")
        with self.link.operation("telecover") as connection:
            connection.write(b"TCVHomeE\n")
            self.assertTrue(self.link.interrupt("telecover", b"TCVDetener\n"))
            self.assertTrue(connection.readline())
            with self.assertRaises(MotionOperationStopped):
                connection.write(b"TCVEste\n")
        self.assertNotIn(b"TCVEste\n", self.serial.writes)
        with self.link.operation("alignment") as connection:
            connection.write(b"G21\n")

    def test_serial_failure_closes_connection_and_releases_busy_state(self):
        self.link.connect("COM8")
        self.serial.fail_writes = True
        with self.assertRaises(serial.SerialException):
            with self.link.operation("alignment") as connection:
                connection.write(b"G21\n")
        self.assertFalse(self.link.is_connected())
        self.assertFalse(self.link.snapshot()["busy"])

    def test_invalid_port_and_failed_open_remain_disconnected(self):
        for port in ["", "  ", "COM4\nCOM5"]:
            with self.assertRaises(ValueError):
                self.link.connect(port)
        self.factory.assert_not_called()
        self.factory.side_effect = serial.SerialException("Port unavailable")
        with self.assertRaises(serial.SerialException):
            self.link.connect("COM8")
        self.assertEqual(self.link.snapshot()["state"], "disconnected")

    def test_unresponsive_grbl_times_out_instead_of_waiting_forever(self):
        motor = MotorController(ser=Mock(readline=Mock(return_value=b"")))
        with self.assertRaises(TimeoutError):
            motor.send("G21", timeout_s=0.005)


class DashboardMotionTest(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.connection = BridgeSerial()
        self.factory = Mock(return_value=self.connection)
        self.link = MotionConnection(serial_factory=self.factory, startup_delay=0)
        self.config = copy.deepcopy(dashboard.globalconfig)
        self.addCleanup(lambda: dashboard.globalconfig.update(self.config))
        self.patches = [
            patch.object(dashboard, "motion_connection", self.link),
            patch.object(MotorController, "STATE_FILE", Path(self.temp.name) / "state.json"),
            patch.object(MotorController, "HISTORY_FILE", Path(self.temp.name) / "history.jsonl"),
        ]
        for item in self.patches:
            item.start()
            self.addCleanup(item.stop)
        self.client = dashboard.app.test_client()
        grbl.pos = {"X": 0.0, "Y": 0.0, "Z": 0.0}
        grbl.state = "Idle"

    def connect(self):
        result = self.client.post("/motor_connection", data={"selected": "motor_connect", "input": "COM8"})
        self.assertEqual(result.status_code, 200)

    def test_motion_and_scan_require_explicit_connection(self):
        for url, data in [
            ("/motor", {"selected": "motor_left"}),
            ("/telecover_control", {"action": "home"}),
            ("/telecover_status", {}),
            ("/telecover_run_sequence", {}),
        ]:
            self.assertEqual(self.client.get(url, query_string=data).status_code, 409)
        self.assertEqual(self.client.post("/autoalign/start").status_code, 409)
        self.factory.assert_not_called()

    def test_motor_and_telecover_use_same_transport_and_synchronized_port(self):
        self.connect()
        moved = self.client.post("/motor", data={"selected": "motor_left"})
        self.assertEqual(moved.status_code, 200)
        homed = self.client.get("/telecover_control?action=home_lift")
        self.assertEqual(homed.status_code, 200)
        self.assertEqual(homed.json["lift"], "UP")
        self.assertEqual(dashboard.globalconfig["motor_port"], "COM8")
        self.assertEqual(dashboard.globalconfig["telecover_port"], "COM8")
        self.assertEqual(self.factory.call_count, 1)
        self.assertTrue(self.connection.is_open)
        self.assertIn(b"TCVHomeE\n", self.connection.writes)
        self.assertTrue(any(command.startswith(b"$J=") for command in self.connection.writes))
        self.assertEqual(self.client.post("/motor_connection", data={"selected": "motor_disconnect"}).status_code, 200)
        self.assertFalse(self.connection.is_open)

    def test_port_change_is_rejected_while_connected_from_either_mode(self):
        self.connect()
        self.assertEqual(self.client.post("/motor", data={"selected": "motor_port", "input": "COM9"}).status_code, 409)
        self.assertEqual(self.client.get("/telecover_setup?selected=telecover_port&input=COM9").status_code, 409)
        self.assertEqual(dashboard.globalconfig["motor_port"], "COM8")
        self.assertEqual(dashboard.globalconfig["telecover_port"], "COM8")

    def test_status_does_not_send_commands_or_reopen_the_port(self):
        self.connect()
        before = list(self.connection.writes)
        with self.link.operation("telecover"):
            status = self.client.get("/motor_connection")
            self.assertEqual(status.status_code, 200)
            self.assertTrue(status.json["busy"])
            self.assertEqual(self.client.get("/telecover_control?action=home").status_code, 409)
            self.assertEqual(self.client.post("/motor_connection", data={"selected": "motor_disconnect"}).status_code, 409)
        self.assertEqual(self.connection.writes, before)
        self.assertEqual(self.factory.call_count, 1)

    def test_stop_reaches_busy_telecover_and_prevents_the_next_command(self):
        self.connect()
        with self.link.operation("telecover") as connection:
            response = self.client.get("/telecover_control?action=stop")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(self.connection.writes[-1], b"TCVDetener\n")
            with self.assertRaises(MotionOperationStopped):
                connection.write(b"TCVEste\n")
        self.assertTrue(self.connection.is_open)

    def test_autoalignment_serial_failure_closes_shared_port_and_clears_busy(self):
        self.connect()
        motor = Mock(position={"x": 0.0, "y": 0.0})
        motor.initialize.side_effect = serial.SerialException("USB lost during scan")
        service = AutoalignmentService(
            serial_factory=lambda config: self.fail("Scan reopened serial port"),
            motor_factory=lambda connection: motor,
            acquire_point=lambda: {},
            plots_builder=lambda results: {},
            results_saver=lambda *args: "result.json",
            connection_context=dashboard.autoalignment_motor_connection,
        )
        service.start(dashboard.globalconfig)
        state = service.wait(2)
        self.assertEqual(state["status"], "Error")
        self.assertFalse(state["running"])
        self.assertFalse(self.link.is_connected())
        self.assertFalse(self.link.snapshot()["busy"])

    def test_serial_error_is_visible_and_status_becomes_disconnected(self):
        self.connect()
        self.connection.fail_writes = True
        response = self.client.post("/motor", data={"selected": "motor_left"})
        self.assertEqual(response.status_code, 503)
        self.assertFalse(response.json["motor_connection"]["connected"])

    def test_controls_render_with_one_shared_port_and_indicator(self):
        for route in ["/alignment", "/autoalignment", "/telecover"]:
            response = self.client.get(route)
            self.assertEqual(response.status_code, 200)
            html = response.get_data(as_text=True)
            self.assertEqual(html.count('id="motor_port_input"'), 1)
            self.assertEqual(html.count('id="motor_connectbtn"'), 1)
            self.assertEqual(html.count('id="motor_nav_led"'), 1)
            self.assertNotIn('id="telecover-port"', html)

    def test_autoalignment_borrows_connection_and_keeps_it_open_for_move_best(self):
        self.connect()
        acquired = threading.Event()
        release = threading.Event()
        self.addCleanup(release.set)
        motor = Mock(position={"x": 0.0, "y": 0.0})

        def acquire():
            acquired.set()
            if not release.wait(2):
                raise RuntimeError("Test did not release acquisition")
            return {"pearson": 0.8, "plots": {}}

        motor.scan_grid.side_effect = lambda **kwargs: kwargs["on_point"](0, -3.5, -3.5)
        service = AutoalignmentService(
            serial_factory=lambda config: self.fail("Scan reopened serial port"),
            motor_factory=lambda connection: motor,
            acquire_point=acquire,
            plots_builder=lambda results: {},
            results_saver=lambda *args: "result.json",
            connection_context=dashboard.autoalignment_motor_connection,
        )
        with patch.object(dashboard, "autoalignment_service", service), patch.object(dashboard.lc, "isConnected", return_value=True):
            self.assertEqual(self.client.post("/autoalign/start").status_code, 202)
            self.assertTrue(acquired.wait(1))
            self.assertEqual(self.link.snapshot()["owner"], "autoalignment")
            self.assertEqual(self.client.get("/telecover_control?action=home").status_code, 409)
            self.assertEqual(self.client.post("/motor_connection", data={"selected": "motor_disconnect"}).status_code, 409)
            release.set()
            self.assertEqual(service.wait(2)["status"], "Complete")
            self.assertTrue(self.connection.is_open)
            self.assertFalse(self.link.snapshot()["busy"])
            self.assertEqual(self.client.post("/autoalign/move-best").status_code, 200)
        self.assertTrue(self.connection.is_open)
        self.assertEqual(self.factory.call_count, 1)


if __name__ == "__main__":
    unittest.main()
