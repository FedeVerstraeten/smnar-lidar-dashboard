# Stepper motors control for LiDAR rotation using GRBL commands. 
# This module handles motor configuration and command generation 
# based on user input from the dashboard.

import time
import serial

GCODES = {
    "unlock": "$X",
    "mm": "G21",
    "abs": "G90",
    "inc": "G91",
    "feed": "F{f:.2f}",
    "move_lin": "G1 X{x:.4f} Y{y:.4f}",
    "move_x": "G1 X{x:.4f}",
    "move_y": "G1 Y{y:.4f}",
    "set_zero": "G92 X0 Y0",
}

class MotorController:
    def __init__(self, port: str, baud: int = 115200, timeout: float = 2.0):
        self.ser = serial.Serial(port, baudrate=baud, timeout=timeout)
        time.sleep(2.0)  # reset típico al abrir puerto en Arduino
        self._wake()

    def _wake(self):
        self.ser.write(b"\r\n\r\n")
        time.sleep(0.3)
        self.ser.reset_input_buffer()

    def _readline(self) -> str:
        return self.ser.readline().decode(errors="ignore").strip()

    def send(self, line: str) -> list[str]:
        """Envía una línea y espera ok/error. Devuelve el log recibido."""
        self.ser.write((line.strip() + "\n").encode())
        self.ser.flush()
        out = []
        while True:
            r = self._readline()
            if not r:
                continue
            out.append(r)
            rl = r.lower()
            if rl.startswith("ok") or rl.startswith("error"):
                break
        return out

    def status(self) -> str:
        self.ser.write(b"?")
        self.ser.flush()
        return self._readline()

    def init_incremental(self, feed_mm_min: float = 50.0):
        # Unlock + mm + incremental + feed
        self.send(GCODES["unlock"])
        self.send(GCODES["mm"])
        self.send(GCODES["inc"])
        self.send(GCODES["feed"].format(f=feed_mm_min))

    def jog(self, dx: float = 0.0, dy: float = 0.0):
        # Movimiento incremental (G91 ya seteado)
        cmd = GCODES["move_lin"].format(x=dx, y=dy)
        return self.send(cmd)

if __name__ == "__main__":
    # Windows: "COM5"
    # Linux/RPi: "/dev/ttyUSB0" o "/dev/ttyACM0"
    PORT = "COM5"

    grbl = MotorController(PORT)
    grbl.init_incremental(feed_mm_min=80.0)

    print("Estado:", grbl.status())

    # Prueba: mover en cruz (0.2 mm)
    grbl.jog(dx=+0.2); print("X+ 0.2")
    grbl.jog(dx=-0.2); print("X- 0.2")
    grbl.jog(dy=+0.2); print("Y+ 0.2")
    grbl.jog(dy=-0.2); print("Y- 0.2")

    print("Listo. Estado:", grbl.status())
