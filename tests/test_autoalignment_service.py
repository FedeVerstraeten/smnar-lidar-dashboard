import json
import time
import unittest

from lidarcontroller.autoalignment import (
    AutoalignmentAlreadyRunning,
    AutoalignmentMoveUnavailable,
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
    "scan_centered": True,
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
        self.position = {"x": 0.0, "y": 0.0, "z": 0.0}
        self.grid = None
        self.moved_to = None

    def initialize(self, feed):
        self.feed = feed

    def disable_limits(self):
        pass

    def define_grid(self, rows, cols, step_x, step_y, centered, **_kwargs):
        x0 = -((cols - 1) * step_x) / 2.0 if centered else 0.0
        y0 = -((rows - 1) * step_y) / 2.0 if centered else 0.0
        self.grid = {
            (row, col): (x0 + col * step_x, y0 + row * step_y)
            for row in range(rows)
            for col in range(cols)
        }

    def move_to_grid_point(self, row, col, feed):
        self.moved_to = (row, col, feed)
        x, y = self.grid[(row, col)]
        self.position.update({"x": x, "y": y})

    def scan_grid(self, on_point, **kwargs):
        rows = kwargs["rows"]
        cols = kwargs["cols"]
        step_x = kwargs["step_x"]
        step_y = kwargs["step_y"]
        centered = kwargs["centered"]
        x0 = -((cols - 1) * step_x) / 2.0 if centered else 0.0
        y0 = -((rows - 1) * step_y) / 2.0 if centered else 0.0
        points = [
            (x0 + col * step_x, y0 + row * step_y)
            for row in range(rows)
            for col in range(cols)
        ]
        for index, (x, y) in enumerate(points):
            response = on_point(index, x, y)
            if not response.get("ok", True) and response.get("action") == "abort":
                break

    def go_home(self, feed):
        self.home_calls += 1
        self.position.update({"x": 0.0, "y": 0.0, "z": 0.0})


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
        self.assertEqual(final["current"]["x"], 0.0)
        self.assertEqual(final["current"]["y"], 0.0)
        self.assertEqual(final["current"]["col"], 1.5)
        self.assertEqual(final["current"]["row"], 1.5)
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

    def test_move_to_best_reloads_grid_and_updates_current_position(self):
        service, serial_connections, motors, _ = self.make_service()
        service.start(SCAN_CONFIG)
        service.wait(2.0)

        moved = service.move_to_best()

        self.assertEqual(motors[1].moved_to, (0, 1, SCAN_CONFIG["scan_feed"]))
        self.assertEqual(moved["current"]["x"], 0.5)
        self.assertEqual(moved["current"]["y"], -0.5)
        self.assertEqual(moved["current"]["col"], 2)
        self.assertEqual(moved["current"]["row"], 1)
        self.assertEqual(moved["best"]["pearson"], 0.8)
        self.assertFalse(moved["moving"])
        self.assertTrue(serial_connections[1].closed)

    def test_move_to_best_requires_a_completed_scan(self):
        service, *_ = self.make_service()

        with self.assertRaises(AutoalignmentMoveUnavailable):
            service.move_to_best()

    def test_non_centered_scan_uses_zero_based_grid_coordinates(self):
        service, _, motors, _ = self.make_service()
        config = dict(SCAN_CONFIG, scan_centered=False)
        service.start(config)
        final = service.wait(2.0)

        self.assertEqual(final["current"]["col"], 0)
        self.assertEqual(final["current"]["row"], 0)
        self.assertEqual(final["best"]["col"], 1)
        self.assertEqual(final["best"]["row"], 0)
        self.assertEqual(final["best"]["x"], 1.0)
        self.assertEqual(final["best"]["y"], 0.0)

        moved = service.move_to_best()

        self.assertEqual(motors[1].moved_to, (0, 1, SCAN_CONFIG["scan_feed"]))
        self.assertEqual(moved["current"]["col"], 1)
        self.assertEqual(moved["current"]["row"], 0)


if __name__ == "__main__":
    unittest.main()
