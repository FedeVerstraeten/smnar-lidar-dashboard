#!/usr/bin/env python3
import os
import re
import select
import time


SYMLINK = "/tmp/grbl-sim"

pos = {"X": 0.0, "Y": 0.0, "Z": 0.0}
feed = 500.0
absolute_mode = True
state = "Idle"

LIMITS = {
    "X": (-5.0, 5.0),
    "Y": (-5.0, 5.0),
    "Z": (-5.0, 5.0),
}


def clamp_axis(axis, value):
    lo, hi = LIMITS[axis]
    return max(lo, min(hi, value))


def write_line(fd, text):
    os.write(fd, (text + "\r\n").encode())


def grbl_status():
    return (
        f"<{state}|"
        f"MPos:{pos['X']:.3f},{pos['Y']:.3f},{pos['Z']:.3f}|"
        f"WPos:{pos['X']:.3f},{pos['Y']:.3f},{pos['Z']:.3f}|"
        f"FS:{feed:.0f},0>"
    )


def handle_command(cmd):
    global absolute_mode, feed, state, pos

    cmd = cmd.strip()
    if not cmd:
        return ["ok"]

    if cmd == "?":
        return [grbl_status()]

    if "\x18" in cmd:
        pos = {"X": 0.0, "Y": 0.0, "Z": 0.0}
        state = "Idle"
        return ["Grbl 1.1h ['$' for help]"]

    if cmd == "$X":
        state = "Idle"
        return ["[MSG:Caution: Unlocked]", "ok"]

    if cmd == "$H":
        pos = {"X": 0.0, "Y": 0.0, "Z": 0.0}
        state = "Idle"
        return ["ok"]

    if cmd == "$$":
        return [
            "$0=10",
            "$1=25",
            "$2=0",
            "$3=0",
            "$10=1",
            "$100=250.000",
            "$101=250.000",
            "$102=250.000",
            "$110=1000.000",
            "$111=1000.000",
            "$112=1000.000",
            "$120=100.000",
            "$121=100.000",
            "$122=100.000",
            "ok",
        ]

    if re.match(r"^\$\d+=", cmd):
        return ["ok"]

    if "G90" in cmd:
        absolute_mode = True

    if "G91" in cmd:
        absolute_mode = False

    feed_match = re.search(r"F(-?\d+(\.\d+)?)", cmd)
    if feed_match:
        feed = float(feed_match.group(1))

    if "G0" in cmd or "G00" in cmd or "G1" in cmd or "G01" in cmd:
        target = pos.copy()

        for axis in ["X", "Y", "Z"]:
            axis_match = re.search(axis + r"(-?\d+(\.\d+)?)", cmd)
            if axis_match:
                value = float(axis_match.group(1))
                if absolute_mode:
                    target[axis] = value
                else:
                    target[axis] = pos[axis] + value

                target[axis] = clamp_axis(axis, target[axis])

        state = "Run"
        time.sleep(0.05)
        pos.update(target)
        state = "Idle"
        return ["ok"]

    if cmd.startswith(("G21", "G20", "G17", "G94", "M3", "M5", "M2")):
        return ["ok"]

    return ["ok"]


def process_serial_data(data, buffer=b""):
    """Process raw serial bytes received from the dashboard."""
    events = []

    for byte in data:
        if byte == 0x18:
            events.append(("\x18", handle_command("\x18")))
            buffer = b""
            continue

        if byte in (10, 13):
            command = buffer.decode(errors="ignore").strip()
            buffer = b""
            if command:
                events.append((command, handle_command(command)))
            continue

        buffer += bytes([byte])

    return buffer, events


def main():
    try:
        import pty
        import tty
    except ImportError as exc:
        raise SystemExit(
            "El simulador GRBL requiere Linux, macOS o WSL para crear un PTY."
        ) from exc

    master_fd, slave_fd = pty.openpty()
    slave_name = os.ttyname(slave_fd)

    try:
        if os.path.islink(SYMLINK) or os.path.exists(SYMLINK):
            os.remove(SYMLINK)
        os.symlink(slave_name, SYMLINK)
    except PermissionError:
        print(f"No pude crear {SYMLINK}. Usa directamente: {slave_name}")

    tty.setraw(master_fd)

    print("Simulador GRBL iniciado.")
    print(f"Puerto virtual real: {slave_name}")
    print(f"Puerto recomendado para el dashboard: {SYMLINK}")
    print("Ctrl+C para salir.")

    write_line(master_fd, "Grbl 1.1h ['$' for help]")
    buffer = b""

    try:
        while True:
            read_fds, _, _ = select.select([master_fd], [], [], 0.1)
            if master_fd not in read_fds:
                continue

            data = os.read(master_fd, 1024)
            buffer, events = process_serial_data(data, buffer)
            for command, response_lines in events:
                print(f">> {command}")
                for line in response_lines:
                    print(f"<< {line}")
                    write_line(master_fd, line)
    except KeyboardInterrupt:
        print("\nCerrando simulador.")
    finally:
        try:
            if os.path.islink(SYMLINK):
                os.remove(SYMLINK)
        except OSError:
            pass


if __name__ == "__main__":
    main()
