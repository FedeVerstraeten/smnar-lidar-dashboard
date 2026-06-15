import json
import unittest

from lidarcontroller.telecovercontroller import TelecoverController


class FakeSerial:
    def __init__(self, responses=None):
        self.responses = [
            response.encode() for response in (responses or [])
        ]
        self.commands = []

    def write(self, value):
        self.commands.append(value.decode().strip())

    def flush(self):
        pass

    def readline(self):
        if self.responses:
            return self.responses.pop(0)
        return b""


def status_response(**overrides):
    payload = {
        "homed": True,
        "position": "N",
        "lift": "DOWN",
        "motion": "IDLE",
        "sensors": {},
        "last_error": "",
    }
    payload.update(overrides)
    return json.dumps(payload)


class TelecoverControllerTest(unittest.TestCase):
    def test_status_parses_firmware_json(self):
        serial = FakeSerial([status_response(homed="false")])
        controller = TelecoverController(serial)

        state = controller.status()

        self.assertEqual(serial.commands, ["STATUS"])
        self.assertFalse(state["homed"])
        self.assertEqual(state["position"], "N")
        self.assertEqual(state["motion"], "IDLE")

    def test_move_to_sends_command_and_waits_for_idle(self):
        serial = FakeSerial(["OK", status_response(position="W")])
        controller = TelecoverController(serial)

        state = controller.move_to("w")

        self.assertEqual(serial.commands, ["MOVE W", "STATUS"])
        self.assertEqual(state["position"], "W")

    def test_move_to_rejects_unknown_position(self):
        controller = TelecoverController(FakeSerial())

        with self.assertRaises(ValueError):
            controller.move_to("invalid")

    def test_invalid_status_response_returns_error_state(self):
        controller = TelecoverController(FakeSerial(["not-json"]))

        state = controller.status()

        self.assertEqual(state["motion"], "ERROR")
        self.assertTrue(state["last_error"])


if __name__ == "__main__":
    unittest.main()
