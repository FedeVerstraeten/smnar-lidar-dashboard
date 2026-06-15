import json
import time


class TelecoverController:
    VALID_POSITIONS = {"N", "E", "S", "W", "DC"}
    VALID_LIFT_STATES = {"UP", "DOWN", "MOVING"}
    VALID_MOTION_STATES = {"IDLE", "MOVING", "ERROR"}

    def __init__(self, ser):
        self.ser = ser
        self.state = {
            "homed": False,
            "position": "UNKNOWN",
            "lift": "UNKNOWN",
            "motion": "IDLE",
            "sensors": {},
            "last_error": "",
        }

    def send(self, cmd, timeout_s=2.0):
        self.ser.write((cmd.strip() + "\n").encode())
        self.ser.flush()
        deadline = time.monotonic() + timeout_s

        while time.monotonic() < deadline:
            response = self.ser.readline().decode(errors="ignore").strip()
            if response:
                return response

        raise TimeoutError("No response from telecover controller.")

    def status(self):
        try:
            response = self.send("STATUS")
            status = json.loads(response)
            if not isinstance(status, dict):
                raise ValueError("Telecover STATUS response must be a JSON object.")

            position = str(status.get("position", "UNKNOWN")).upper()
            lift = str(status.get("lift", "UNKNOWN")).upper()
            motion = str(status.get("motion", "IDLE")).upper()
            self.state.update({
                "homed": self._as_boolean(status.get("homed", self.state["homed"])),
                "position": position if position in self.VALID_POSITIONS else "UNKNOWN",
                "lift": lift if lift in self.VALID_LIFT_STATES else "UNKNOWN",
                "motion": motion if motion in self.VALID_MOTION_STATES else "ERROR",
                "sensors": status.get("sensors", {}),
                "last_error": status.get("last_error", ""),
            })
            if motion not in self.VALID_MOTION_STATES:
                self.state["last_error"] = "Invalid telecover motion state: {}".format(motion)
        except Exception as exc:
            self.state["motion"] = "ERROR"
            self.state["last_error"] = str(exc)

        return dict(self.state)

    @staticmethod
    def _as_boolean(value):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "1", "yes", "on"}:
                return True
            if normalized in {"false", "0", "no", "off"}:
                return False
        return bool(value)

    def home(self):
        self.send("HOME")
        return self.wait_until_idle()

    def lift_up(self):
        self.send("LIFT UP")
        return self.wait_until_idle()

    def lift_down(self):
        self.send("LIFT DOWN")
        return self.wait_until_idle()

    def move_to(self, position):
        position = str(position).upper()
        if position not in self.VALID_POSITIONS:
            raise ValueError("Invalid telecover position: {}".format(position))

        self.send("MOVE {}".format(position))
        return self.wait_until_idle()

    def stop(self):
        self.send("STOP")
        return self.status()

    def wait_until_idle(self, timeout_s=60.0, poll_s=0.1):
        deadline = time.monotonic() + timeout_s

        while time.monotonic() < deadline:
            state = self.status()
            if state["motion"] == "IDLE":
                return state
            if state["motion"] == "ERROR":
                raise RuntimeError(state["last_error"] or "Telecover controller error.")
            time.sleep(poll_s)

        raise TimeoutError("Timeout waiting for telecover controller to become idle.")
