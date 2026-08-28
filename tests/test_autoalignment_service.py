import json
import time
import unittest

from lidarcontroller.autoalignment import (
    AutoalignmentAlreadyRunning,
    AutoalignmentService,
)


SCAN_CONFIG = {
    "motor_port": "fake",
    "scan_rows": 2,
    "scan_cols": 2,
    "scan_step_x": 1.0,
    "scan_step_y": 1.0,
    "scan_feed": 50,
    "scan_pattern": "raster",
    "scan_reverse": False,
    "scan_delay": 0.0,
    "scan_on_fail": "abort",
}


class FakeSerial:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


class FakeMotor:
    points = [(-0.5, -0.5), (0.5, -0.5), (-0.5, 0.5), (0.5, 0.5)]

    def __init__(self, serial_connection):
        self.serial_connection = serial_connection
        self.home_calls = 0

    def initialize(self, feed):
        self.feed = feed

    def disable_limits(self):
        pass

    def scan_grid(self, on_point, **_kwargs):
        for index, (x, y) in enumerate(self.points):
            response = on_point(index, x, y)
            if not response.get("ok", True) and response.get("action") == "abort":
                break

    def go_home(self, feed):
        self.home_calls += 1


def wait_for(predicate, timeout=1.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(0.005)
    raise AssertionError("Timed out waiting for autoalignment state")


class AutoalignmentServiceTest(unittest.TestCase):
    def make_service(self, acquire_point=None):
        serial_connections = []
        motors = []
        saved = []
        values = iter([0.1, 0.8, 0.3, 0.2])

        def serial_factory(_config):
            connection = FakeSerial()
            serial_connections.append(connection)
            return connection

        def motor_factory(connection):
            motor = FakeMotor(connection)
            motors.append(motor)
            return motor

        def default_acquire():
            time.sleep(0.02)
            pearson = next(values)
            return {
                "pearson": pearson,
                "plots": {
                    "plot_lidar_signal": json.dumps({"pearson": pearson}),
                    "plot_lidar_range_correction": json.dumps({"pearson": pearson}),
                },
            }

        def plots_builder(results):
            return {
                "plot_pearson": json.dumps([item["pearson"] for item in results]),
                "plot_measurement_grid": json.dumps(len(results)),
            }

        def results_saver(config, results, best):
            saved.append((config, results, best))
            return "result.json"

        service = AutoalignmentService(
            serial_factory=serial_factory,
            motor_factory=motor_factory,
            acquire_point=acquire_point or default_acquire,
            plots_builder=plots_builder,
            results_saver=results_saver,
        )
        return service, serial_connections, motors, saved

    def test_start_returns_before_scan_finishes_and_exposes_partial_progress(self):
        service, serial_connections, motors, saved = self.make_service()

        initial = service.start(SCAN_CONFIG)

        self.assertTrue(initial["running"])
        self.assertIn(initial["status"], {"Starting", "Running"})
        partial = wait_for(
            lambda: (
                state
                if (state := service.snapshot())["measured_points"] >= 1
                and state["running"]
                else None
            )
        )
        self.assertGreater(partial["progress"], 0)
        self.assertLess(partial["progress"], 100)
        self.assertIn("plot_lidar_signal", partial)
        self.assertIn("plot_pearson", partial)
        self.assertIsNotNone(partial["current"])

        final = service.wait(2.0)

        self.assertEqual(final["status"], "Complete")
        self.assertEqual(final["progress"], 100)
        self.assertEqual(final["measured_points"], 4)
        self.assertEqual(final["best"]["pearson"], 0.8)
        self.assertEqual(final["filename"], "result.json")
        self.assertTrue(serial_connections[0].closed)
        self.assertEqual(motors[0].home_calls, 1)
        self.assertEqual(len(saved), 1)

    def test_second_start_is_rejected_while_running(self):
        service, *_ = self.make_service()
        service.start(SCAN_CONFIG)

        with self.assertRaises(AutoalignmentAlreadyRunning):
            service.start(SCAN_CONFIG)

        service.stop()
        service.wait(2.0)

    def test_stop_finishes_scan_between_points(self):
        service, *_ = self.make_service()
        service.start(SCAN_CONFIG)
        wait_for(lambda: service.snapshot()["measured_points"] >= 1)

        stopping = service.stop()
        final = service.wait(2.0)

        self.assertTrue(stopping["stop_requested"])
        self.assertEqual(final["status"], "Stopped")
        self.assertLess(final["measured_points"], final["total_points"])
        self.assertFalse(final["running"])

    def test_worker_error_is_reported_in_status(self):
        def failing_acquisition():
            raise RuntimeError("Licel acquisition failed")

        service, *_ = self.make_service(acquire_point=failing_acquisition)
        config = dict(SCAN_CONFIG, scan_on_fail="abort")
        service.start(config)
        final = service.wait(2.0)

        self.assertEqual(final["status"], "Error")
        self.assertEqual(final["measured_points"], 0)
        self.assertIn("Licel acquisition failed", final["message"])


if __name__ == "__main__":
    unittest.main()
