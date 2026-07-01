import unittest

from simulator.telecover_fake_serial import TelecoverState


class TelecoverFakeSerialTest(unittest.TestCase):
    def test_home_lift_leaves_lift_up(self):
        state = TelecoverState()

        response = state.handle_command("TCVHomeE")

        self.assertEqual(
            response,
            [
                "TCV: HOME INICIADO (EJE VERTICAL)",
                "TCV: HOME COMPLETADO",
            ],
        )
        self.assertTrue(state.homed_lift)
        self.assertEqual(state.lift, "UP")
        self.assertTrue(state.sensor_arriba)

    def test_lift_down_fails_without_home(self):
        state = TelecoverState()

        response = state.handle_command("TCVAbajo")

        self.assertEqual(response, ["TCV: REALICE HOME PRIMERO (TCVHomeE)"])
        self.assertEqual(state.lift, "UNKNOWN")

    def test_lift_down_after_home_leaves_lift_down(self):
        state = TelecoverState()

        state.handle_command("TCVHomeE")
        response = state.handle_command("TCVAbajo")

        self.assertEqual(response, ["TCV: BAJANDO", "TCV: ABAJO COMPLETADO"])
        self.assertEqual(state.lift, "DOWN")
        self.assertFalse(state.sensor_arriba)

    def test_lift_up_leaves_lift_up(self):
        state = TelecoverState()

        state.handle_command("TCVHomeE")
        state.handle_command("TCVAbajo")
        response = state.handle_command("TCVArriba")

        self.assertEqual(response, ["TCV: SUBIENDO", "TCV: ARRIBA COMPLETADO"])
        self.assertEqual(state.lift, "UP")

    def test_tcv_north_initializes_disk_at_north(self):
        state = TelecoverState()

        response = state.handle_command("TCVNorte")

        self.assertEqual(response, ["PLATO: HOME INICIADO", "PLATO: HOME COMPLETADO"])
        self.assertTrue(state.homed_disk)
        self.assertEqual(state.disk_position, "N")

    def test_valid_sequence_n_e_s_w_n(self):
        state = TelecoverState()
        state.handle_command("TCVNorte")

        commands = ["TCVEste", "TCVSur", "TCVOeste", "TCVNorte"]
        for command in commands:
            response = state.handle_command(command)
            self.assertEqual(response, ["PLATO: GIRANDO HORARIO", "PLATO: DESTINO ALCANZADO"])

        self.assertEqual(state.disk_position, "N")
        self.assertEqual(state.darkcover, "OPEN")

    def test_invalid_disk_move_generates_error(self):
        state = TelecoverState()
        state.handle_command("TCVNorte")

        response = state.handle_command("TCVSur")

        self.assertEqual(
            response,
            ["PLATO: ERROR -> No se puede ir directo de NORTE a SUR"],
        )
        self.assertEqual(state.disk_position, "N")

    def test_dark_close_from_north_closes_darkcover(self):
        state = TelecoverState()
        state.handle_command("TCVNorte")

        response = state.handle_command("TCVCOI")

        self.assertEqual(
            response,
            [
                "PLATO ANTIHORARIO: Iniciando viaje inverso -> Buscando SUR",
                "PLATO: DESTINO ALCANZADO",
            ],
        )
        self.assertEqual(state.disk_position, "S")
        self.assertEqual(state.darkcover, "CLOSED")

    def test_dark_open_opens_darkcover_and_returns_north(self):
        state = TelecoverState()
        state.handle_command("TCVNorte")
        state.handle_command("TCVCOI")

        response = state.handle_command("TCVCOO")

        self.assertEqual(
            response,
            [
                "PLATO ANTIHORARIO: Iniciando viaje inverso -> Buscando NORTE",
                "PLATO: DESTINO ALCANZADO",
            ],
        )
        self.assertEqual(state.disk_position, "N")
        self.assertEqual(state.darkcover, "OPEN")

    def test_lift_status_returns_text_block(self):
        state = TelecoverState()
        state.handle_command("TCVHomeE")

        response = state.handle_command("TCVEstado")

        self.assertIn("===== TCV =====", response)
        self.assertIn("Home: SI", response)
        self.assertIn("Sensor Arriba: 1", response)
        self.assertIn("Posicion: ARRIBA", response)
        self.assertIn("Movimiento: PARADO", response)

    def test_disk_status_returns_text_block(self):
        state = TelecoverState()
        state.handle_command("TCVNorte")
        state.handle_command("TCVEste")

        response = state.handle_command("TCVEstadoPlato")

        self.assertIn("===== PLATO =====", response)
        self.assertIn("Home: SI", response)
        self.assertIn("IO12: 0", response)
        self.assertIn("IO13: 1", response)
        self.assertIn("Posicion: ESTE", response)
        self.assertIn("Estado: PARADO", response)

    def test_unknown_tcv_and_grbl_bridge_responses(self):
        state = TelecoverState()

        self.assertEqual(state.handle_command("TCVFoo"), ["TCV: COMANDO DESCONOCIDO"])
        self.assertEqual(state.handle_command("G21"), ["ok"])


if __name__ == "__main__":
    unittest.main()
