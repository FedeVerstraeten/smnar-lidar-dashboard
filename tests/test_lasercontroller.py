import unittest
from unittest.mock import Mock, patch

from lidarcontroller.lasercontroller import laserController


class LaserCommandTimingTest(unittest.TestCase):
    def test_commands_are_drained_and_spaced_in_both_directions(self):
        events = []
        connection = Mock()
        connection.isOpen.return_value = True
        connection.write.side_effect = lambda data: events.append(data)
        connection.flush.side_effect = lambda: events.append("flush")
        with patch("lidarcontroller.lasercontroller.serial.Serial", return_value=connection), patch(
            "lidarcontroller.lasercontroller.time.sleep", side_effect=lambda delay: events.append(delay)
        ):
            laser = laserController()
            laser.startLaser()
            laser.stopLaser()
        self.assertEqual(events, [
            b"ST 1\r", "flush", 2.0, b"SH 1\r", "flush",
            b"SH 0\r", "flush", 2.0, b"ST 0\r", "flush",
        ])

    def test_disconnected_laser_sends_no_commands(self):
        connection = Mock()
        connection.isOpen.return_value = False
        with patch("lidarcontroller.lasercontroller.serial.Serial", return_value=connection):
            laser = laserController()
            with self.assertRaises(ValueError):
                laser.startLaser()
            with self.assertRaises(ValueError):
                laser.stopLaser()
        connection.write.assert_not_called()



if __name__ == "__main__":
    unittest.main()
