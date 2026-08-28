import copy
import datetime
import threading
from contextlib import nullcontext


class AutoalignmentAlreadyRunning(RuntimeError):
    pass


class AutoalignmentService:
    """Run an autoalignment scan outside the HTTP request lifecycle."""

    def __init__(
        self,
        serial_factory,
        motor_factory,
        acquire_point,
        plots_builder,
        results_saver,
        run_context=None,
    ):
        self._serial_factory = serial_factory
        self._motor_factory = motor_factory
        self._acquire_point = acquire_point
        self._plots_builder = plots_builder
        self._results_saver = results_saver
        self._run_context = run_context or nullcontext
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._thread = None
        self._state = self._initial_state()

    @staticmethod
    def _initial_state():
        return {
            "ok": True,
            "running": False,
            "stop_requested": False,
            "status": "Idle",
            "message": "Autoalignment is idle.",
            "progress": 0,
            "total_points": 0,
            "measured_points": 0,
            "current": None,
            "best": None,
            "results": [],
            "filename": None,
            "revision": 0,
        }

    def _update(self, **changes):
        with self._lock:
            self._state.update(changes)
            self._state["revision"] += 1

    def snapshot(self):
        with self._lock:
            return copy.deepcopy(self._state)

    def start(self, config):
        scan_config = copy.deepcopy(config)
        total_points = scan_config["scan_rows"] * scan_config["scan_cols"]

        with self._lock:
            if self._state["running"]:
                raise AutoalignmentAlreadyRunning(
                    "Autoalignment is already running."
                )

            revision = self._state["revision"] + 1
            self._state = self._initial_state()
            self._state.update({
                "running": True,
                "status": "Starting",
                "message": "Autoalignment is starting.",
                "total_points": total_points,
                "revision": revision,
            })
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._run,
                args=(scan_config,),
                name="autoalignment-worker",
                daemon=True,
            )
            self._thread.start()

        return self.snapshot()

    def stop(self):
        with self._lock:
            if not self._state["running"]:
                state = copy.deepcopy(self._state)
                state["message"] = "No autoalignment scan is running."
                return state

            self._stop_event.set()
            self._state.update({
                "stop_requested": True,
                "status": "Stopping",
                "message": "Autoalignment stop requested.",
            })
            self._state["revision"] += 1
            return copy.deepcopy(self._state)

    def wait(self, timeout=None):
        thread = self._thread
        if thread is not None:
            thread.join(timeout)
        return self.snapshot()

    def _run(self, config):
        serial_motor = None
        motor = None
        returned_home = False
        results = []
        fatal_acquisition_error = [None]
        rows = config["scan_rows"]
        cols = config["scan_cols"]
        total_points = rows * cols
        step_x = config["scan_step_x"]
        step_y = config["scan_step_y"]
        x0 = -((cols - 1) * step_x) / 2.0
        y0 = -((rows - 1) * step_y) / 2.0

        try:
            with self._run_context():
                serial_motor = self._serial_factory(config)
                motor = self._motor_factory(serial_motor)
                motor.initialize(feed=config["scan_feed"])
                motor.disable_limits()
                self._update(
                    status="Running",
                    message="Autoalignment scan is running.",
                )

                def measure_point(scan_index, x, y):
                    if self._stop_event.is_set():
                        return {"ok": False, "action": "abort"}

                    try:
                        measurement = self._acquire_point()
                    except Exception as ex:
                        if config["scan_on_fail"] == "abort":
                            fatal_acquisition_error[0] = ex
                        self._update(
                            message="Acquisition failed at point {}: {}".format(
                                scan_index + 1, ex
                            )
                        )
                        return {
                            "ok": False,
                            "action": config["scan_on_fail"],
                        }

                    col = int(round((x - x0) / step_x)) + 1
                    row = int(round((y - y0) / step_y)) + 1
                    result = {
                        "index": len(results),
                        "scan_index": scan_index,
                        "row": row,
                        "col": col,
                        "x": x,
                        "y": y,
                        "pearson": float(measurement["pearson"]),
                        "timestamp": datetime.datetime.now().isoformat(),
                    }
                    results.append(result)
                    best = max(results, key=lambda item: item["pearson"])
                    progress = int(round((len(results) / total_points) * 100))
                    plots = dict(measurement.get("plots", {}))
                    plots.update(self._plots_builder(results))
                    self._update(
                        results=copy.deepcopy(results),
                        measured_points=len(results),
                        progress=progress,
                        current=copy.deepcopy(result),
                        best=copy.deepcopy(best),
                        message="Measured point {} of {}.".format(
                            len(results), total_points
                        ),
                        **plots
                    )
                    return {"ok": True}

                motor.scan_grid(
                    rows=rows,
                    cols=cols,
                    step_x=step_x,
                    step_y=step_y,
                    feed=config["scan_feed"],
                    pattern=config["scan_pattern"],
                    centered=True,
                    reverse=config["scan_reverse"],
                    wait_mode="delay",
                    delay_s=config["scan_delay"],
                    on_point=measure_point,
                    on_fail=config["scan_on_fail"],
                    return_home=False,
                )
                motor.go_home(feed=config["scan_feed"])
                returned_home = True

                if fatal_acquisition_error[0] is not None:
                    raise RuntimeError(
                        "Autoalignment acquisition failed: {}".format(
                            fatal_acquisition_error[0]
                        )
                    )

            stopped = self._stop_event.is_set()
            filename = self._results_saver(
                config, results, self.snapshot()["best"]
            )
            self._update(
                status="Stopped" if stopped else "Complete",
                message=(
                    "Autoalignment stopped."
                    if stopped
                    else "Autoalignment scan completed."
                ),
                filename=filename,
            )
        except Exception as ex:
            self._update(
                ok=False,
                status="Error",
                message=str(ex),
            )
        finally:
            if motor is not None and not returned_home:
                try:
                    motor.go_home(feed=config["scan_feed"])
                except Exception as ex:
                    self._update(
                        message="{} Return home failed: {}".format(
                            self.snapshot()["message"], ex
                        )
                    )

            if serial_motor is not None:
                try:
                    serial_motor.close()
                except Exception:
                    pass

            self._update(running=False)
