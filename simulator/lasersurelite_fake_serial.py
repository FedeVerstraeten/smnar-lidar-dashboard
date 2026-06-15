#!/usr/bin/env python3
"""Simulador serie del laser Continuum Surelite II.

Crea un pseudo-terminal en Linux, macOS o WSL y publica el enlace estable
``/tmp/laser-surelite-sim``. La comunicacion usa 9600 baud, 8 bits, sin
paridad, 1 stop bit (8N1) y comandos ASCII terminados en Carriage Return.

Comandos implementados:
    SS      Disparo unico cuando ST esta activo y PD vale 000.
    SE      Devuelve un codigo de interlock de 2 digitos y CR.
    SH 0/1  Cierra o abre el shutter.
    ST 0/1  Detiene o inicia el laser.
    QS XXX  Configura el retardo Q-switch con 3 digitos.
    RR XX.X Configura la tasa de repeticion.
    VA X.XX Configura el voltaje de la fuente.
    PD XXX  Configura la division de pulsos.
    SC      Devuelve el contador de 9 digitos y CR.

Solo ``SE`` y ``SC`` generan respuesta. Los comandos de escritura actualizan
el estado interno sin responder, igual que el controlador real.

Uso:
    python simulator/lasersurelite_fake_serial.py

Configurar ``/tmp/laser-surelite-sim`` como puerto del laser en el dashboard.
"""

import argparse
import os
import re
import select
import time
from dataclasses import dataclass, field
from typing import Callable, Optional


DEFAULT_SYMLINK = "/tmp/laser-surelite-sim"


@dataclass
class SureliteState:
    security_code: str = "00"
    shot_counter: int = 0
    shutter_open: bool = False
    started: bool = False
    q_switch_delay: int = 195
    repetition_rate: float = 10.0
    voltage: float = 0.90
    pulse_division: int = 0
    clock: Callable[[], float] = field(
        default=time.monotonic,
        repr=False,
    )
    _last_update: Optional[float] = field(default=None, init=False)
    _fractional_shots: float = field(default=0.0, init=False)

    def update_shot_counter(self):
        # Acumula disparos segun el tiempo y la tasa de repeticion.
        now = self.clock()
        if self._last_update is None:
            self._last_update = now
            return

        elapsed = max(0.0, now - self._last_update)
        self._last_update = now
        if not self.started:
            return

        shots = self._fractional_shots + elapsed * self.repetition_rate
        whole_shots = int(shots)
        self._fractional_shots = shots - whole_shots
        self.shot_counter = (self.shot_counter + whole_shots) % 1_000_000_000

    def handle_command(self, command):
        # Valida comandos exactos, sensibles a mayusculas y sin el CR final.
        if command == "SE":
            return self.security_code

        if command == "SC":
            self.update_shot_counter()
            return f"{self.shot_counter:09d}"

        if command == "SS":
            self.update_shot_counter()
            if self.started and self.pulse_division == 0:
                self.shot_counter = (self.shot_counter + 1) % 1_000_000_000
            return None

        match = re.fullmatch(r"SH ([01])", command)
        if match:
            self.shutter_open = match.group(1) == "1"
            return None

        match = re.fullmatch(r"ST ([01])", command)
        if match:
            self.update_shot_counter()
            self.started = match.group(1) == "1"
            self._last_update = self.clock()
            return None

        match = re.fullmatch(r"QS (\d{3})", command)
        if match:
            self.q_switch_delay = int(match.group(1))
            return None

        match = re.fullmatch(r"RR (\d{2}\.\d)", command)
        if match:
            self.update_shot_counter()
            self.repetition_rate = float(match.group(1))
            return None

        match = re.fullmatch(r"VA (\d\.\d{2})", command)
        if match:
            self.voltage = float(match.group(1))
            return None

        match = re.fullmatch(r"PD (\d{3})", command)
        if match:
            self.pulse_division = int(match.group(1))
            return None

        return None


def write_response(fd, response):
    # Las respuestas del equipo terminan solamente en Carriage Return.
    os.write(fd, (response + "\r").encode("ascii"))


def parse_args():
    parser = argparse.ArgumentParser(
        description="Continuum Surelite II serial simulator (9600 8N1)"
    )
    parser.add_argument(
        "--symlink",
        default=DEFAULT_SYMLINK,
        help=f"stable serial port link (default: {DEFAULT_SYMLINK})",
    )
    parser.add_argument(
        "--security-code",
        choices=[f"{value:02d}" for value in range(10)],
        default="00",
        help="SE interlock response (default: 00)",
    )
    parser.add_argument(
        "--shot-count",
        type=int,
        default=0,
        help="initial shot counter (default: 0)",
    )
    return parser.parse_args()


def create_pty(symlink):
    # Los pseudo-terminales solo estan disponibles en sistemas tipo Unix.
    try:
        import pty
        import tty
    except ImportError as exc:
        raise SystemExit(
            "El simulador Surelite requiere Linux, macOS o WSL."
        ) from exc

    master_fd, slave_fd = pty.openpty()
    slave_name = os.ttyname(slave_fd)
    tty.setraw(master_fd)

    # Publica un nombre estable para configurar el dashboard.
    try:
        if os.path.islink(symlink) or os.path.exists(symlink):
            os.remove(symlink)
        os.symlink(slave_name, symlink)
    except PermissionError:
        print(f"No pude crear {symlink}. Usa directamente: {slave_name}")

    return master_fd, slave_fd, slave_name


def run_simulator(state, symlink=DEFAULT_SYMLINK):
    master_fd, slave_fd, slave_name = create_pty(symlink)

    print("Simulador Continuum Surelite II iniciado.")
    print(f"Puerto virtual real: {slave_name}")
    print(f"Puerto recomendado para el dashboard: {symlink}")
    print("Configuracion serie: 9600 baud, 8N1")
    print("Ctrl+C para salir.")

    buffer = bytearray()
    try:
        while True:
            # Mantiene actualizado el contador aunque no lleguen comandos.
            read_fds, _, _ = select.select([master_fd], [], [], 0.1)
            if master_fd not in read_fds:
                state.update_shot_counter()
                continue

            for byte in os.read(master_fd, 1024):
                # El CR delimita cada comando enviado por el controlador.
                if byte == 13:
                    command = buffer.decode("ascii", errors="ignore")
                    buffer.clear()
                    print(f">> {command}")
                    response = state.handle_command(command)
                    if response is not None:
                        print(f"<< {response}")
                        write_response(master_fd, response)
                elif byte != 10:
                    buffer.append(byte)
    except KeyboardInterrupt:
        print("\nCerrando simulador Surelite.")
    finally:
        # Elimina el enlace y cierra ambos extremos del pseudo-terminal.
        if os.path.islink(symlink):
            os.remove(symlink)
        os.close(master_fd)
        os.close(slave_fd)


def main():
    args = parse_args()
    # El contador SC debe poder representarse siempre con 9 digitos.
    if not 0 <= args.shot_count <= 999_999_999:
        raise SystemExit("--shot-count debe estar entre 0 y 999999999")

    state = SureliteState(
        security_code=args.security_code,
        shot_counter=args.shot_count,
    )
    run_simulator(state, args.symlink)


if __name__ == "__main__":
    main()
