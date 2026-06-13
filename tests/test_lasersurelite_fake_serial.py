import unittest
from unittest.mock import patch

from simulator.lasersurelite_fake_serial import SureliteState, write_response


class FakeClock:
    def __init__(self):
        self.value = 0.0

    def __call__(self):
        return self.value

    def advance(self, seconds):
        self.value += seconds


class SureliteFakeSerialTest(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.state = SureliteState(clock=self.clock)

    def test_dashboard_start_and_stop_sequence(self):
        self.state.handle_command("ST 1")
        self.state.handle_command("SH 1")

        self.assertTrue(self.state.started)
        self.assertTrue(self.state.shutter_open)

        self.state.handle_command("SH 0")
        self.state.handle_command("ST 0")

        self.assertFalse(self.state.shutter_open)
        self.assertFalse(self.state.started)

    def test_security_and_shot_counter_responses(self):
        self.state.security_code = "06"
        self.state.shot_counter = 123456

        self.assertEqual(self.state.handle_command("SE"), "06")
        self.assertEqual(self.state.handle_command("SC"), "000123456")

    def test_running_laser_increments_counter_at_repetition_rate(self):
        self.state.handle_command("RR 20.0")
        self.state.handle_command("ST 1")
        self.clock.advance(1.5)

        self.assertEqual(self.state.handle_command("SC"), "000000030")

    def test_single_shot_requires_started_laser_and_pd_000(self):
        self.state.handle_command("ST 1")
        self.state.handle_command("PD 001")
        self.state.handle_command("SS")
        self.assertEqual(self.state.shot_counter, 0)

        self.state.handle_command("PD 000")
        self.state.handle_command("SS")
        self.assertEqual(self.state.shot_counter, 1)

    def test_parameter_commands_require_exact_format(self):
        self.state.handle_command("QS 195")
        self.state.handle_command("RR 05.0")
        self.state.handle_command("VA 0.90")
        self.state.handle_command("PD 007")

        self.assertEqual(self.state.q_switch_delay, 195)
        self.assertEqual(self.state.repetition_rate, 5.0)
        self.assertEqual(self.state.voltage, 0.90)
        self.assertEqual(self.state.pulse_division, 7)

        self.state.handle_command("qs 200")
        self.state.handle_command("RR 5.0")
        self.state.handle_command("VA .95")
        self.state.handle_command("PD 8")

        self.assertEqual(self.state.q_switch_delay, 195)
        self.assertEqual(self.state.repetition_rate, 5.0)
        self.assertEqual(self.state.voltage, 0.90)
        self.assertEqual(self.state.pulse_division, 7)

    def test_shutter_does_not_stop_internal_shot_counter(self):
        self.state.handle_command("RR 10.0")
        self.state.handle_command("ST 1")
        self.state.handle_command("SH 0")
        self.clock.advance(1.0)

        self.assertEqual(self.state.handle_command("SC"), "000000010")

    @patch("simulator.lasersurelite_fake_serial.os.write")
    def test_responses_are_ascii_terminated_by_carriage_return(self, os_write):
        write_response(12, "000123456")

        os_write.assert_called_once_with(12, b"000123456\r")


if __name__ == "__main__":
    unittest.main()
