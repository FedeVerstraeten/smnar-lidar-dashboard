import unittest

from lidarcontroller.telecovercontroller import (
    TelecoverController,
    parse_telecover_response,
    telecover_default_state,
)


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


class TelecoverParserTest(unittest.TestCase):
    def test_lift_home_updates_incrementally(self):
        state = telecover_default_state()

        state = parse_telecover_response(
            "TCV: HOME INICIADO (EJE VERTICAL)",
            state,
            "TCVHomeE",
        )
        self.assertEqual(state["event"], "movement_started")
        self.assertEqual(state["lift"], "MOVING")
        self.assertEqual(state["motion"], "MOVING")

        state = parse_telecover_response("TCV: HOME COMPLETADO", state, "TCVHomeE")
        self.assertEqual(state["event"], "movement_completed")
        self.assertEqual(state["lift"], "UP")
        self.assertTrue(state["homed_lift"])
        self.assertEqual(state["motion"], "IDLE")

    def test_lift_down_and_up(self):
        state = telecover_default_state()
        state = parse_telecover_response("TCV: BAJANDO", state, "TCVAbajo")
        self.assertEqual(state["lift"], "MOVING")
        state = parse_telecover_response("TCV: ABAJO COMPLETADO", state, "TCVAbajo")
        self.assertEqual(state["lift"], "DOWN")

        state = parse_telecover_response("TCV: SUBIENDO", state, "TCVArriba")
        self.assertEqual(state["lift"], "MOVING")
        state = parse_telecover_response("TCV: ARRIBA COMPLETADO", state, "TCVArriba")
        self.assertEqual(state["lift"], "UP")

    def test_disk_move_uses_last_command_target(self):
        state = telecover_default_state()
        state = parse_telecover_response("PLATO: GIRANDO HORARIO", state, "TCVEste")
        self.assertEqual(state["motion"], "MOVING")

        state = parse_telecover_response("PLATO: DESTINO ALCANZADO", state, "TCVEste")
        self.assertEqual(state["disk_position"], "E")
        self.assertEqual(state["target_position"], "E")
        self.assertEqual(state["darkcover"], "OPEN")
        self.assertEqual(state["motion"], "IDLE")

    def test_darkcover_close_and_open(self):
        state = telecover_default_state()
        state = parse_telecover_response(
            "PLATO ANTIHORARIO: Iniciando viaje inverso -> Buscando SUR",
            state,
            "TCVCOI",
        )
        self.assertEqual(state["subsystem"], "darkcover")
        self.assertEqual(state["target_position"], "S")
        self.assertEqual(state["darkcover"], "MOVING")

        state = parse_telecover_response("PLATO: DESTINO ALCANZADO", state, "TCVCOI")
        self.assertEqual(state["disk_position"], "S")
        self.assertEqual(state["darkcover"], "CLOSED")

        state = parse_telecover_response(
            "PLATO ANTIHORARIO: Iniciando viaje inverso -> Buscando NORTE",
            state,
            "TCVCOO",
        )
        self.assertEqual(state["target_position"], "N")
        state = parse_telecover_response("PLATO: DESTINO ALCANZADO", state, "TCVCOO")
        self.assertEqual(state["disk_position"], "N")
        self.assertEqual(state["darkcover"], "OPEN")

    def test_status_reports_parse_sensors(self):
        state = telecover_default_state()
        state = parse_telecover_response("Home: SI", state, "TCVEstado")
        state = parse_telecover_response("Sensor Arriba: 1", state, "TCVEstado")
        state = parse_telecover_response("Encoder Count: 42", state, "TCVEstado")
        state = parse_telecover_response("Posicion: ARRIBA", state, "TCVEstado")
        self.assertTrue(state["homed_lift"])
        self.assertTrue(state["sensors"]["lift_top"])
        self.assertEqual(state["sensors"]["encoder_count"], 42)
        self.assertEqual(state["lift"], "UP")

        state = parse_telecover_response("Home: SI", state, "TCVEstadoPlato")
        state = parse_telecover_response("IO12: 1", state, "TCVEstadoPlato")
        state = parse_telecover_response("Posicion: OESTE", state, "TCVEstadoPlato")
        self.assertTrue(state["homed_disk"])
        self.assertTrue(state["sensors"]["disk_io12"])
        self.assertEqual(state["disk_position"], "W")

    def test_json_response_is_normalized(self):
        state = parse_telecover_response(
            '{"status": "ok", "disk_position": "S", "motion": "idle"}',
            telecover_default_state(),
            "TCVEstadoPlato",
        )

        self.assertEqual(state["device"], "telecover")
        self.assertEqual(state["status"], "OK")
        self.assertEqual(state["disk_position"], "S")
        self.assertEqual(state["motion"], "IDLE")

    def test_unknown_response_preserves_previous_state(self):
        previous = telecover_default_state()
        previous["disk_position"] = "N"

        state = parse_telecover_response("texto inesperado", previous, "TCVNorte")

        self.assertEqual(state["status"], "UNKNOWN")
        self.assertEqual(state["event"], "unknown_response")
        self.assertEqual(state["disk_position"], "N")
        self.assertEqual(state["message"], "texto inesperado")


class TelecoverControllerTest(unittest.TestCase):
    def test_move_to_sends_real_firmware_command_and_waits(self):
        serial = FakeSerial(["PLATO: GIRANDO HORARIO", "PLATO: DESTINO ALCANZADO"])
        controller = TelecoverController(serial)

        state = controller.move_to("e")

        self.assertEqual(serial.commands, ["TCVEste"])
        self.assertEqual(state["disk_position"], "E")

    def test_full_home_uses_lift_home_then_north(self):
        serial = FakeSerial([
            "TCV: HOME INICIADO (EJE VERTICAL)",
            "TCV: HOME COMPLETADO",
            "PLATO: HOME INICIADO",
            "PLATO: DESTINO ALCANZADO",
        ])
        controller = TelecoverController(serial)

        state = controller.full_home()

        self.assertEqual(serial.commands, ["TCVHomeE", "TCVNorte"])
        self.assertEqual(state["lift"], "UP")
        self.assertEqual(state["disk_position"], "N")
        self.assertEqual(state["darkcover"], "OPEN")
        self.assertTrue(state["homed_lift"])
        self.assertTrue(state["homed_disk"])

    def test_move_to_rejects_darkcurrent_as_disk_position(self):
        controller = TelecoverController(FakeSerial())

        with self.assertRaises(ValueError):
            controller.move_to("DC")


if __name__ == "__main__":
    unittest.main()
