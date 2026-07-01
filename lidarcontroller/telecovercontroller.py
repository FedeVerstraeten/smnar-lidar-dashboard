import json
import time


DEFAULT_TELECOVER_STATE = {
    "device": "telecover",
    "status": "UNKNOWN",
    "command": None,
    "event": "unknown_response",
    "subsystem": "unknown",
    "disk_position": "UNKNOWN",
    "target_position": "NONE",
    "lift": "UNKNOWN",
    "darkcover": "UNKNOWN",
    "motion": "IDLE",
    "homed_lift": False,
    "homed_disk": False,
    "sensors": {},
    "message": "",
    "error": None,
    "last_response": "",
}


POSITION_BY_COMMAND = {
    "TCVNorte": "N",
    "TCVEste": "E",
    "TCVSur": "S",
    "TCVOeste": "W",
    "TCVHomeP": "N",
    "TCVCOI": "S",
    "TCVCOO": "N",
}


POSITION_TEXT = {
    "NORTE": "N",
    "ESTE": "E",
    "SUR": "S",
    "OESTE": "W",
}


TERMINAL_EVENTS = {
    "movement_completed",
    "already_in_position",
    "movement_stopped",
    "busy",
    "timeout",
    "error",
}


def telecover_default_state():
    state = dict(DEFAULT_TELECOVER_STATE)
    state["sensors"] = {}
    return state


def normalize_telecover_state(data, current_state=None, last_command=None, line=""):
    state = telecover_default_state()
    if current_state:
        state.update(current_state)
        state["sensors"] = dict(current_state.get("sensors", {}))

    if isinstance(data, dict):
        state.update(data)

    state["device"] = "telecover"
    state["command"] = state.get("command") or last_command
    state["message"] = state.get("message") or line
    state["last_response"] = state.get("last_response") or line
    state["sensors"] = dict(state.get("sensors") or {})
    state["status"] = str(state.get("status") or "UNKNOWN").upper()
    state["event"] = state.get("event") or "unknown_response"
    state["subsystem"] = state.get("subsystem") or "unknown"
    state["disk_position"] = _normalize_disk_position(state.get("disk_position"))
    state["target_position"] = _normalize_target_position(state.get("target_position"))
    state["lift"] = _normalize_lift(state.get("lift"))
    state["darkcover"] = _normalize_darkcover(state.get("darkcover"))
    state["motion"] = _normalize_motion(state.get("motion"))
    state["homed_lift"] = _as_boolean(state.get("homed_lift", False))
    state["homed_disk"] = _as_boolean(state.get("homed_disk", False))
    state["error"] = state.get("error")
    return state


def parse_telecover_response(line, current_state, last_command=None):
    text = (line or "").strip()
    state = normalize_telecover_state({}, current_state, last_command, text)
    state.update({
        "command": last_command,
        "message": text,
        "last_response": text,
    })

    if not text:
        return state

    try:
        parsed = json.loads(text)
    except (TypeError, ValueError):
        parsed = None

    if isinstance(parsed, dict):
        return normalize_telecover_state(parsed, state, last_command, text)

    upper = text.upper()

    if "TIMEOUT" in upper:
        state.update({
            "status": "TIMEOUT",
            "event": "timeout",
            "motion": "ERROR",
            "error": text,
        })
        if upper.startswith("PLATO:"):
            state["subsystem"] = "disk"
            if text == "PLATO: TIMEOUT":
                state["error"] = "PLATO TIMEOUT"
        return state

    if "ERROR" in upper:
        state.update({
            "status": "ERROR",
            "event": "error",
            "motion": "ERROR",
            "error": _known_error_message(text),
            "subsystem": _subsystem_from_text(text, last_command),
        })
        return state

    if "OCUPADO" in upper or "MOVIMIENTO EN CURSO" in upper:
        state.update({
            "status": "BUSY",
            "event": "busy",
            "motion": "MOVING",
            "subsystem": _subsystem_from_text(text, last_command),
        })
        return state

    handlers = (
        _parse_lift_response,
        _parse_darkcover_response,
        _parse_disk_response,
        _parse_status_report,
    )
    for handler in handlers:
        updated = handler(text, upper, state, last_command)
        if updated is not None:
            return normalize_telecover_state(updated, state, last_command, text)

    state.update({
        "status": "UNKNOWN",
        "event": "unknown_response",
    })
    return state


class TelecoverController:
    VALID_POSITIONS = {"N", "E", "S", "W"}
    COMMANDS = {
        "home_lift": "TCVHomeE",
        "lift_up": "TCVArriba",
        "lift_down": "TCVAbajo",
        "stop_lift": "TCVDetener",
        "home_disk": "TCVHomeP",
        "dark_close": "TCVCOI",
        "dark_open": "TCVCOO",
        "status_lift": "TCVEstado",
        "status_disk": "TCVEstadoPlato",
    }
    MOVE_COMMANDS = {
        "N": "TCVNorte",
        "E": "TCVEste",
        "S": "TCVSur",
        "W": "TCVOeste",
    }

    def __init__(self, ser):
        self.ser = ser
        self.state = telecover_default_state()
        self.last_command = None

    def send(self, cmd, timeout_s=2.0):
        self.last_command = cmd
        self.state["command"] = cmd
        self.ser.write((cmd.strip() + "\n").encode())
        self.ser.flush()

        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            response = self.ser.readline().decode(errors="ignore").strip()
            if response:
                self.state = parse_telecover_response(response, self.state, cmd)
                return dict(self.state)
            time.sleep(0.01)

        self.state.update({
            "status": "TIMEOUT",
            "event": "timeout",
            "motion": "ERROR",
            "error": "No response from telecover controller.",
            "message": "No response from telecover controller.",
            "last_response": "",
        })
        raise TimeoutError(self.state["error"])

    def read_lines_until_idle(self, timeout_s=60.0):
        deadline = time.monotonic() + timeout_s

        while time.monotonic() < deadline:
            response = self.ser.readline().decode(errors="ignore").strip()
            if not response:
                time.sleep(0.01)
                continue

            self.state = parse_telecover_response(response, self.state, self.last_command)
            if self.state["event"] in TERMINAL_EVENTS:
                if self.state["status"] in {"ERROR", "TIMEOUT"}:
                    raise RuntimeError(self.state["error"] or self.state["message"])
                return dict(self.state)

        timeout_line = "Timeout waiting for telecover controller to become idle."
        self.state = parse_telecover_response("TIMEOUT", self.state, self.last_command)
        self.state.update({
            "error": timeout_line,
            "message": timeout_line,
            "last_response": timeout_line,
        })
        raise TimeoutError(timeout_line)

    def parse_telecover_response(self, line, current_state=None, last_command=None):
        self.state = parse_telecover_response(
            line,
            current_state or self.state,
            last_command if last_command is not None else self.last_command,
        )
        return dict(self.state)

    def status(self):
        try:
            self.status_lift()
        except Exception:
            pass
        try:
            self.status_disk()
        except Exception:
            pass
        return dict(self.state)

    def status_lift(self):
        self.send(self.COMMANDS["status_lift"])
        return self._read_status_lines("lift")

    def status_disk(self):
        self.send(self.COMMANDS["status_disk"])
        return self._read_status_lines("disk")

    def home_lift(self):
        self.send(self.COMMANDS["home_lift"])
        return self.read_lines_until_idle()

    def home_disk(self):
        self.send(self.COMMANDS["home_disk"])
        return self.read_lines_until_idle()

    def full_home(self):
        self.home_lift()
        self.move_to("N")
        self.state.update({
            "status": "OK",
            "event": "movement_completed",
            "subsystem": "disk",
            "lift": "UP",
            "disk_position": "N",
            "target_position": "N",
            "darkcover": "OPEN",
            "motion": "IDLE",
            "homed_lift": True,
            "homed_disk": True,
            "error": None,
        })
        return dict(self.state)

    def lift_up(self):
        self.send(self.COMMANDS["lift_up"])
        return self.read_lines_until_idle()

    def lift_down(self):
        self.send(self.COMMANDS["lift_down"])
        return self.read_lines_until_idle()

    def move_to(self, position):
        position = str(position).upper()
        if position not in self.VALID_POSITIONS:
            raise ValueError("Invalid telecover position: {}".format(position))

        self.send(self.MOVE_COMMANDS[position])
        state = self.read_lines_until_idle()
        if state["event"] in {"movement_completed", "already_in_position"}:
            self.state.update({
                "disk_position": position,
                "target_position": position,
                "darkcover": "OPEN",
                "motion": "IDLE",
            })
        return dict(self.state)

    def dark_close(self):
        self.send(self.COMMANDS["dark_close"])
        return self.read_lines_until_idle()

    def dark_open(self):
        self.send(self.COMMANDS["dark_open"])
        return self.read_lines_until_idle()

    def stop_lift(self):
        self.send(self.COMMANDS["stop_lift"])
        return dict(self.state)

    # Compatibility with the first Telecover branch.
    def home(self):
        return self.full_home()

    def stop(self):
        return self.stop_lift()

    def _read_status_lines(self, subsystem, timeout_s=0.25):
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            response = self.ser.readline().decode(errors="ignore").strip()
            if response:
                self.state = parse_telecover_response(response, self.state, self.last_command)
            else:
                time.sleep(0.01)
        if self.state["subsystem"] == "unknown":
            self.state["subsystem"] = subsystem
        return dict(self.state)


def _parse_lift_response(text, upper, state, last_command):
    exact = {
        "TCV: HOME INICIADO (EJE VERTICAL)": {
            "status": "OK", "event": "movement_started", "subsystem": "lift",
            "lift": "MOVING", "motion": "MOVING",
        },
        "TCV: HOME COMPLETADO": {
            "status": "OK", "event": "movement_completed", "subsystem": "lift",
            "lift": "UP", "motion": "IDLE", "homed_lift": True,
        },
        "TCV: SUBIENDO": {
            "status": "OK", "event": "movement_started", "subsystem": "lift",
            "lift": "MOVING", "motion": "MOVING",
        },
        "TCV: SENSOR SUPERIOR": {
            "status": "OK", "event": "movement_completed", "subsystem": "lift",
            "lift": "UP", "motion": "IDLE",
        },
        "TCV: ARRIBA COMPLETADO": {
            "status": "OK", "event": "movement_completed", "subsystem": "lift",
            "lift": "UP", "motion": "IDLE",
        },
        "TCV: BAJANDO": {
            "status": "OK", "event": "movement_started", "subsystem": "lift",
            "lift": "MOVING", "motion": "MOVING",
        },
        "TCV: ABAJO COMPLETADO": {
            "status": "OK", "event": "movement_completed", "subsystem": "lift",
            "lift": "DOWN", "motion": "IDLE",
        },
        "TCV: YA ESTA ARRIBA": {
            "status": "OK", "event": "already_in_position", "subsystem": "lift",
            "lift": "UP", "motion": "IDLE",
        },
        "TCV: YA ESTA ABAJO": {
            "status": "OK", "event": "already_in_position", "subsystem": "lift",
            "lift": "DOWN", "motion": "IDLE",
        },
        "TCV: REALICE HOME PRIMERO (TCVHomeE)": {
            "status": "ERROR", "event": "error", "subsystem": "lift",
            "motion": "ERROR", "error": "REALICE HOME PRIMERO (TCVHomeE)",
        },
        "TCV: DETENIDO": {
            "status": "OK", "event": "movement_stopped", "subsystem": "lift",
            "motion": "IDLE",
        },
    }
    return exact.get(text)


def _parse_darkcover_response(text, upper, state, last_command):
    if last_command == "TCVCOI" and text == "PLATO: DESTINO ALCANZADO":
        return {
            "status": "OK", "event": "movement_completed", "subsystem": "darkcover",
            "disk_position": "S", "darkcover": "CLOSED", "motion": "IDLE",
        }
    if last_command == "TCVCOO" and text == "PLATO: DESTINO ALCANZADO":
        return {
            "status": "OK", "event": "movement_completed", "subsystem": "darkcover",
            "disk_position": "N", "darkcover": "OPEN", "motion": "IDLE",
        }
    if (
        last_command == "TCVCOI"
        and text == "PLATO ANTIHORARIO: Iniciando viaje inverso -> Buscando SUR"
    ):
        return {
            "status": "OK", "event": "movement_started", "subsystem": "darkcover",
            "target_position": "S", "darkcover": "MOVING", "motion": "MOVING",
        }
    if (
        last_command == "TCVCOO"
        and text == "PLATO ANTIHORARIO: Iniciando viaje inverso -> Buscando NORTE"
    ):
        return {
            "status": "OK", "event": "movement_started", "subsystem": "darkcover",
            "target_position": "N", "darkcover": "MOVING", "motion": "MOVING",
        }
    return None


def _parse_disk_response(text, upper, state, last_command):
    exact = {
        "PLATO: GIRANDO HORARIO": {
            "status": "OK", "event": "movement_started", "subsystem": "disk",
            "motion": "MOVING", "darkcover": "OPEN",
        },
        "PLATO: GIRANDO ANTIHORARIO": {
            "status": "OK", "event": "movement_started", "subsystem": "disk",
            "motion": "MOVING",
        },
        "PLATO: YA ESTA EN NORTE": {
            "status": "OK", "event": "already_in_position", "subsystem": "disk",
            "disk_position": "N", "homed_disk": True, "motion": "IDLE",
            "darkcover": "OPEN",
        },
        "PLATO: HOME INICIADO": {
            "status": "OK", "event": "movement_started", "subsystem": "disk",
            "motion": "MOVING", "target_position": "N",
        },
        "PLATO: HOME COMPLETADO": {
            "status": "OK", "event": "movement_completed", "subsystem": "disk",
            "disk_position": "N", "target_position": "N", "homed_disk": True,
            "motion": "IDLE", "darkcover": "OPEN",
        },
        "PLATO: TCVHomeP INICIADO": {
            "status": "OK", "event": "movement_started", "subsystem": "disk",
            "motion": "MOVING", "target_position": "N",
        },
        "PLATO: EJECUTE TCVNorte o TCVHomeP": {
            "status": "ERROR", "event": "error", "subsystem": "disk",
            "motion": "ERROR", "error": "EJECUTE TCVNorte o TCVHomeP",
        },
        "PLATO: YA ESTA EN DESTINO": {
            "status": "OK", "event": "already_in_position", "subsystem": "disk",
            "motion": "IDLE",
        },
        "PLATO: DESTINO ALCANZADO": {
            "status": "OK", "event": "movement_completed", "subsystem": "disk",
            "motion": "IDLE",
        },
    }
    if text in exact:
        result = exact[text]
        target = POSITION_BY_COMMAND.get(last_command)
        if result["event"] in {"movement_completed", "already_in_position"} and target in {"N", "E", "S", "W"}:
            result = dict(result)
            result.setdefault("disk_position", target)
            result.setdefault("target_position", target)
            result.setdefault("darkcover", "OPEN")
        return result

    if text.startswith("PLATO: TCVHomeP COMPLETADO"):
        return {
            "status": "OK", "event": "movement_completed", "subsystem": "disk",
            "disk_position": "N", "target_position": "N", "homed_disk": True,
            "motion": "IDLE", "darkcover": "OPEN",
        }

    prefix = "PLATO: POSICION ACTUAL -> "
    if text.startswith(prefix):
        position_text = text[len(prefix):].strip().upper()
        return {
            "status": "OK",
            "event": "status_report",
            "subsystem": "disk",
            "disk_position": POSITION_TEXT.get(position_text, "UNKNOWN"),
        }

    if text.startswith("PLATO: ERROR -> No se puede ir directo de"):
        return {
            "status": "ERROR", "event": "error", "subsystem": "disk",
            "motion": "ERROR", "error": text,
        }
    return None


def _parse_status_report(text, upper, state, last_command):
    sensors = dict(state.get("sensors") or {})
    result = {
        "status": "OK",
        "event": "status_report",
        "subsystem": _status_subsystem(last_command, state),
    }

    if text == "Home: SI":
        if last_command == "TCVEstadoPlato":
            result["homed_disk"] = True
        else:
            result["homed_lift"] = True
        return result
    if text == "Home: NO":
        if last_command == "TCVEstadoPlato":
            result["homed_disk"] = False
        else:
            result["homed_lift"] = False
        return result
    if text.startswith("Sensor Arriba:"):
        sensors["lift_top"] = text.split(":", 1)[1].strip() == "1"
        result.update({"subsystem": "lift", "sensors": sensors})
        return result
    if text.startswith("Encoder Count:"):
        try:
            sensors["encoder_count"] = int(text.split(":", 1)[1].strip())
        except ValueError:
            sensors["encoder_count"] = text.split(":", 1)[1].strip()
        result.update({"subsystem": "lift", "sensors": sensors})
        return result
    if text.startswith("IO12:"):
        sensors["disk_io12"] = text.split(":", 1)[1].strip() == "1"
        result.update({"subsystem": "disk", "sensors": sensors})
        return result
    if text.startswith("IO13:"):
        sensors["disk_io13"] = text.split(":", 1)[1].strip() == "1"
        result.update({"subsystem": "disk", "sensors": sensors})
        return result

    if text.startswith("Posicion:"):
        value = text.split(":", 1)[1].strip().upper()
        if value in {"ARRIBA", "ABAJO", "DESCONOCIDA"}:
            result["subsystem"] = "lift"
            result["lift"] = {"ARRIBA": "UP", "ABAJO": "DOWN"}.get(value, "UNKNOWN")
            return result
        if value in {"NORTE", "ESTE", "SUR", "OESTE", "DESCONOCIDO"}:
            result["subsystem"] = "disk"
            result["disk_position"] = POSITION_TEXT.get(value, "UNKNOWN")
            return result

    if text.startswith("Movimiento:"):
        value = text.split(":", 1)[1].strip().upper()
        result["subsystem"] = "lift"
        if value == "PARADO":
            result["motion"] = "IDLE"
        elif value in {"SUBIENDO", "BAJANDO", "HOMING"}:
            result["lift"] = "MOVING"
            result["motion"] = "MOVING"
        else:
            return None
        return result

    if text.startswith("Estado:"):
        value = text.split(":", 1)[1].strip().upper()
        result["subsystem"] = "disk"
        if value == "PARADO":
            result["motion"] = "IDLE"
        elif value in {"HOMING HORARIO", "TCVHOME ANTIHORARIO", "MOVIENDO", "MOVIENDO ANTIHORARIO"}:
            result["motion"] = "MOVING"
        else:
            return None
        return result

    return None


def _known_error_message(text):
    known = {
        "TCV: REALICE HOME PRIMERO (TCVHomeE)": "REALICE HOME PRIMERO (TCVHomeE)",
        "PLATO: ERROR -> Primero ejecute TCVNorte o TCVHomeP.": "Primero ejecute TCVNorte o TCVHomeP.",
        "PLATO: ERROR -> TCVHomeP solo puede ejecutarse estando en NORTE.": "TCVHomeP solo puede ejecutarse estando en NORTE.",
    }
    return known.get(text, text)


def _subsystem_from_text(text, last_command):
    if text.startswith("TCV:") or last_command in {"TCVHomeE", "TCVArriba", "TCVAbajo", "TCVDetener", "TCVEstado"}:
        return "lift"
    if last_command in {"TCVCOI", "TCVCOO"}:
        return "darkcover"
    if text.startswith("PLATO:") or text.startswith("PLATO ANTIHORARIO:") or last_command in POSITION_BY_COMMAND:
        return "disk"
    return "unknown"


def _status_subsystem(last_command, state):
    if last_command == "TCVEstado":
        return "lift"
    if last_command == "TCVEstadoPlato":
        return "disk"
    return state.get("subsystem", "unknown")


def _normalize_disk_position(value):
    value = str(value or "UNKNOWN").upper()
    return value if value in {"N", "E", "S", "W", "UNKNOWN"} else "UNKNOWN"


def _normalize_target_position(value):
    value = str(value or "NONE").upper()
    return value if value in {"N", "E", "S", "W", "NONE", "UNKNOWN"} else "NONE"


def _normalize_lift(value):
    value = str(value or "UNKNOWN").upper()
    return value if value in {"UP", "DOWN", "MOVING", "UNKNOWN"} else "UNKNOWN"


def _normalize_darkcover(value):
    value = str(value or "UNKNOWN").upper()
    return value if value in {"OPEN", "CLOSED", "MOVING", "UNKNOWN"} else "UNKNOWN"


def _normalize_motion(value):
    value = str(value or "IDLE").upper()
    return value if value in {"IDLE", "MOVING", "ERROR"} else "ERROR"


def _as_boolean(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "on", "si"}:
            return True
        if normalized in {"false", "0", "no", "off"}:
            return False
    return bool(value)
