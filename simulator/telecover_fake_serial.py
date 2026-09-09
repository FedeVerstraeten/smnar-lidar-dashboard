#!/usr/bin/env python3
"""Serial simulator for the TelecoverFinal4 firmware.

The simulator creates a Unix pseudo-terminal and exposes a stable link at
``/tmp/telecover-sim``. Configure that path as the Telecover serial port in the
dashboard to exercise Telecover Mode without hardware.
"""

import argparse
import os
import select
import time
from dataclasses import dataclass


DEFAULT_LINK = "/tmp/telecover-sim"

POSITIONS = {"N", "E", "S", "W", "UNKNOWN"}
LIFT_STATES = {"UP", "DOWN", "UNKNOWN"}
POSITION_NAMES = {
    "N": "NORTE",
    "E": "ESTE",
    "S": "SUR",
    "W": "OESTE",
    "UNKNOWN": "DESCONOCIDO",
}
VALID_CLOCKWISE_MOVES = {
    ("N", "E"),
    ("E", "S"),
    ("S", "W"),
    ("W", "N"),
}


@dataclass
class TelecoverState:
    homed_lift: bool = False
    homed_disk: bool = False
    lift: str = "UNKNOWN"
    disk_position: str = "UNKNOWN"
    darkcover: str = "OPEN"
    motion: str = "PARADO"
    encoder_count: int = 0
    sensor_arriba: bool = False

    def __post_init__(self):
        self.lift = normalize_choice(self.lift, LIFT_STATES, "UNKNOWN")
        self.disk_position = normalize_choice(self.disk_position, POSITIONS, "UNKNOWN")
        if self.lift != "UNKNOWN":
            self.homed_lift = True
        if self.disk_position != "UNKNOWN":
            self.homed_disk = True
        self.sensor_arriba = self.lift == "UP"

    def handle_command(self, command):
        command = command.strip()
        if not command:
            return []

        handlers = {
            "TCVHomeE": self.home_lift,
            "TCVArriba": self.lift_up,
            "TCVAbajo": self.lift_down,
            "TCVDetener": self.stop_lift,
            "TCVEstado": self.status_lift,
            "TCVNorte": lambda: self.move_north_or_home(),
            "TCVHomeP": self.home_disk,
            "TCVEste": lambda: self.move_disk("E"),
            "TCVSur": lambda: self.move_disk("S"),
            "TCVOeste": lambda: self.move_disk("W"),
            "TCVCOI": self.dark_close,
            "TCVCOO": self.dark_open,
            "TCVEstadoPlato": self.status_disk,
        }

        if command in handlers:
            return handlers[command]()
        if command.startswith("TCV"):
            return ["TCV: COMANDO DESCONOCIDO"]
        return ["ok"]

    def home_lift(self):
        self.motion = "HOMING"
        self.encoder_count = 0
        self.homed_lift = True
        self.lift = "UP"
        self.sensor_arriba = True
        self.motion = "PARADO"
        return [
            "TCV: HOME INICIADO (EJE VERTICAL)",
            "TCV: HOME COMPLETADO",
        ]

    def lift_up(self):
        if not self.homed_lift:
            return ["TCV: REALICE HOME PRIMERO (TCVHomeE)"]
        if self.lift == "UP":
            return ["TCV: YA ESTA ARRIBA"]

        self.motion = "SUBIENDO"
        self.encoder_count += 50
        self.lift = "UP"
        self.sensor_arriba = True
        self.motion = "PARADO"
        return [
            "TCV: SUBIENDO",
            "TCV: ARRIBA COMPLETADO",
        ]

    def lift_down(self):
        if not self.homed_lift:
            return ["TCV: REALICE HOME PRIMERO (TCVHomeE)"]
        if self.lift == "DOWN":
            return ["TCV: YA ESTA ABAJO"]

        self.motion = "BAJANDO"
        self.encoder_count += 50
        self.lift = "DOWN"
        self.sensor_arriba = False
        self.motion = "PARADO"
        return [
            "TCV: BAJANDO",
            "TCV: ABAJO COMPLETADO",
        ]

    def stop_lift(self):
        self.motion = "PARADO"
        return ["TCV: DETENIDO"]

    def status_lift(self):
        return [
            "===== TCV =====",
            "Home: {}".format("SI" if self.homed_lift else "NO"),
            "Sensor Arriba: {}".format(1 if self.sensor_arriba else 0),
            "Encoder Count: {}".format(self.encoder_count),
            "Posicion: {}".format(lift_name(self.lift)),
            "Movimiento: {}".format(self.motion),
            "================",
        ]

    def move_north_or_home(self):
        if self.homed_disk and self.disk_position == "N":
            self.darkcover = "OPEN"
            return ["PLATO: YA ESTA EN NORTE"]

        if self.homed_disk and self.disk_position == "W":
            return self.move_disk("N")

        self.motion = "HOMING HORARIO"
        self.homed_disk = True
        self.disk_position = "N"
        self.darkcover = "OPEN"
        self.motion = "PARADO"
        return [
            "PLATO: HOME INICIADO",
            "PLATO: HOME COMPLETADO",
        ]

    def home_disk(self):
        if self.disk_position != "N":
            return ["PLATO: ERROR -> TCVHomeP solo puede ejecutarse estando en NORTE."]

        self.motion = "TCVHOME ANTIHORARIO"
        self.homed_disk = True
        self.disk_position = "N"
        self.darkcover = "OPEN"
        self.motion = "PARADO"
        return [
            "PLATO: TCVHomeP INICIADO",
            "PLATO: TCVHomeP COMPLETADO (Vuelta de 360° exitosa)",
        ]

    def move_disk(self, target):
        target = normalize_choice(target, {"N", "E", "S", "W"}, "UNKNOWN")
        if not self.homed_disk:
            return ["PLATO: ERROR -> Primero ejecute TCVNorte o TCVHomeP."]
        if self.disk_position == target:
            return ["PLATO: YA ESTA EN DESTINO"]
        if (self.disk_position, target) not in VALID_CLOCKWISE_MOVES:
            return [
                "PLATO: ERROR -> No se puede ir directo de {} a {}".format(
                    POSITION_NAMES.get(self.disk_position, "DESCONOCIDO"),
                    POSITION_NAMES.get(target, "DESCONOCIDO"),
                )
            ]

        self.motion = "MOVIENDO"
        self.disk_position = target
        self.darkcover = "OPEN"
        self.motion = "PARADO"
        return [
            "PLATO: GIRANDO HORARIO",
            "PLATO: DESTINO ALCANZADO",
        ]

    def dark_close(self):
        if not self.homed_disk:
            return ["PLATO: ERROR -> Primero ejecute TCVNorte o TCVHomeP."]
        if self.disk_position != "N":
            return [
                "PLATO: ERROR -> TCVCOI (ir a SUR) solo puede ejecutarse desde NORTE. "
                "Posicion actual: {}".format(POSITION_NAMES.get(self.disk_position, "DESCONOCIDO"))
            ]

        self.motion = "MOVIENDO ANTIHORARIO"
        self.disk_position = "S"
        self.darkcover = "CLOSED"
        self.motion = "PARADO"
        return [
            "PLATO ANTIHORARIO: Iniciando viaje inverso -> Buscando SUR",
            "PLATO: DESTINO ALCANZADO",
        ]

    def dark_open(self):
        if self.darkcover != "CLOSED":
            return ["PLATO: YA ESTA EN DESTINO"]

        self.motion = "MOVIENDO ANTIHORARIO"
        self.disk_position = "N"
        self.darkcover = "OPEN"
        self.homed_disk = True
        self.motion = "PARADO"
        return [
            "PLATO ANTIHORARIO: Iniciando viaje inverso -> Buscando NORTE",
            "PLATO: DESTINO ALCANZADO",
        ]

    def status_disk(self):
        io12, io13 = disk_sensors(self.disk_position)
        return [
            "===== PLATO =====",
            "Home: {}".format("SI" if self.homed_disk else "NO"),
            "IO12: {}".format(1 if io12 else 0),
            "IO13: {}".format(1 if io13 else 0),
            "Posicion: {}".format(POSITION_NAMES.get(self.disk_position, "DESCONOCIDO")),
            "Estado: {}".format(self.motion),
            "=================",
        ]


def normalize_choice(value, choices, default):
    value = str(value or default).upper()
    return value if value in choices else default


def lift_name(lift):
    return {
        "UP": "ARRIBA",
        "DOWN": "ABAJO",
    }.get(lift, "DESCONOCIDA")


def disk_sensors(position):
    return {
        "N": (True, True),
        "E": (False, True),
        "S": (False, False),
        "W": (True, False),
    }.get(position, (False, False))


def write_line(fd, text):
    os.write(fd, (text + "\r\n").encode("utf-8"))


def create_pty(link):
    try:
        import pty
        import tty
    except ImportError as exc:
        raise SystemExit(
            "El simulador Telecover requiere Linux, macOS o WSL para crear un PTY."
        ) from exc

    master_fd, slave_fd = pty.openpty()
    slave_name = os.ttyname(slave_fd)
    tty.setraw(master_fd)

    try:
        if os.path.islink(link) or os.path.exists(link):
            os.remove(link)
        os.symlink(slave_name, link)
    except PermissionError:
        print(f"No pude crear {link}. Usa directamente: {slave_name}")

    return master_fd, slave_fd, slave_name


def parse_args():
    parser = argparse.ArgumentParser(
        description="TelecoverFinal4 serial simulator"
    )
    parser.add_argument(
        "--link",
        default=DEFAULT_LINK,
        help=f"stable serial port link (default: {DEFAULT_LINK})",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.2,
        help="delay between movement start and completion lines (default: 0.2)",
    )
    parser.add_argument(
        "--initial-lift",
        choices=["UP", "DOWN", "UNKNOWN"],
        default="UNKNOWN",
        help="initial lift state (default: UNKNOWN)",
    )
    parser.add_argument(
        "--initial-disk",
        choices=["N", "E", "S", "W", "UNKNOWN"],
        default="UNKNOWN",
        help="initial disk state (default: UNKNOWN)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="print received commands and sent responses",
    )
    return parser.parse_args()


def run_simulator(state, link=DEFAULT_LINK, delay=0.2, verbose=False):
    master_fd, slave_fd, slave_name = create_pty(link)

    print("Simulador TelecoverFinal4 iniciado.")
    print(f"Puerto virtual real: {slave_name}")
    print(f"Puerto recomendado para el dashboard: {link}")
    print("Ctrl+C para salir.")

    buffer = bytearray()
    try:
        while True:
            read_fds, _, _ = select.select([master_fd], [], [], 0.1)
            if master_fd not in read_fds:
                continue

            data = os.read(master_fd, 1024)
            for byte in data:
                if byte in (10, 13):
                    command = buffer.decode("utf-8", errors="ignore").strip()
                    buffer.clear()
                    if command or verbose:
                        print(f">> {command}")
                    responses = state.handle_command(command)
                    for index, response in enumerate(responses):
                        if index > 0 and is_movement_response_pair(responses):
                            time.sleep(max(0.0, delay))
                        print(f"<< {response}")
                        write_line(master_fd, response)
                else:
                    buffer.append(byte)
    except KeyboardInterrupt:
        print("\nCerrando simulador Telecover.")
    finally:
        if os.path.islink(link):
            os.remove(link)
        os.close(master_fd)
        os.close(slave_fd)


def is_movement_response_pair(responses):
    if len(responses) < 2:
        return False
    start_markers = (
        "INICIADO",
        "SUBIENDO",
        "BAJANDO",
        "GIRANDO",
        "Iniciando viaje inverso",
    )
    return any(marker in responses[0] for marker in start_markers)


def main():
    args = parse_args()
    state = TelecoverState(
        lift=args.initial_lift,
        disk_position=args.initial_disk,
    )
    run_simulator(
        state,
        link=args.link,
        delay=args.delay,
        verbose=args.verbose,
    )


if __name__ == "__main__":
    main()
