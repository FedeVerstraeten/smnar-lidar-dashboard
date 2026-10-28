"""One persistent serial transport for alignment motors and Telecover."""

import threading
import time
from contextlib import contextmanager

import serial


class MotionConnectionError(RuntimeError):
    pass


class MotionConnectionBusy(MotionConnectionError):
    pass


class MotionOperationStopped(MotionConnectionError):
    pass


class _SerialOperation:
    """A serial view that prevents further commands after an operator stop."""

    def __init__(self, link, connection):
        self._link = link
        self._connection = connection

    def __getattr__(self, name):
        return getattr(self._connection, name)

    def write(self, data):
        with self._link._state_lock:
            if self._link.stop_requested.is_set():
                raise MotionOperationStopped("Motor/Telecover operation stopped by the operator.")
            return self._connection.write(data)


class MotionConnection:
    def __init__(self, port="COM4", serial_factory=None, startup_delay=2.0):
        self.port = port
        self._serial_factory = serial_factory or serial.Serial
        self._serial = None
        self._operation_lock = threading.Lock()
        self._state_lock = threading.RLock()
        self._owner = None
        self.startup_delay = startup_delay
        self.stop_requested = threading.Event()

    def is_connected(self):
        with self._state_lock:
            return self._serial is not None and self._serial.is_open

    def snapshot(self, ok=True, message=""):
        with self._state_lock:
            connected = self.is_connected()
            busy = self._owner is not None
            return {
                "ok": ok,
                "connected": connected,
                "port": self.port,
                "state": "busy" if busy else "connected" if connected else "disconnected",
                "busy": busy,
                "owner": self._owner,
                "message": message,
            }

    @staticmethod
    def validate_port(port):
        port = str(port).strip()
        if not port or any(ord(char) < 32 for char in port):
            raise ValueError("A valid serial port is required.")
        return port

    @contextmanager
    def _exclusive(self):
        if not self._operation_lock.acquire(blocking=False):
            raise MotionConnectionBusy("The shared motor/Telecover connection is busy.")
        try:
            yield
        finally:
            self._operation_lock.release()

    def configure(self, port):
        port = self.validate_port(port)
        with self._exclusive(), self._state_lock:
            if self.is_connected() and port != self.port:
                raise MotionConnectionBusy("Disconnect motors/Telecover before changing the serial port.")
            self.port = port

    def connect(self, port):
        port = self.validate_port(port)
        with self._exclusive():
            with self._state_lock:
                if self.is_connected():
                    if port != self.port:
                        raise MotionConnectionBusy("Disconnect motors/Telecover before changing the serial port.")
                    return self.snapshot()
                self.port = port
                self._owner = "connecting"
            connection = None
            try:
                connection = self._serial_factory(port=port, baudrate=115200, timeout=0.2, write_timeout=2.0)
                # Opening an Arduino serial port may reset it. Wait only once.
                time.sleep(self.startup_delay)
                connection.reset_input_buffer()
                with self._state_lock:
                    self._serial = connection
            except Exception:
                if connection is not None:
                    connection.close()
                raise
            finally:
                with self._state_lock:
                    self._owner = None
        return self.snapshot(message="Shared motor/Telecover serial connection established.")

    def disconnect(self):
        with self._exclusive(), self._state_lock:
            self._close()
        return self.snapshot(message="Shared motor/Telecover serial connection closed.")

    def _close(self):
        connection, self._serial = self._serial, None
        if connection is not None:
            connection.close()

    def interrupt(self, owner, command):
        """Send only a stop command without consuming the active operation's replies."""
        with self._state_lock:
            if not self.is_connected():
                raise MotionConnectionError("Connect motors/Telecover before sending commands.")
            if self._owner is None:
                return False
            if self._owner != owner:
                raise MotionConnectionBusy("The shared connection is being used by {}.".format(self._owner))
            self.stop_requested.set()
            try:
                self._serial.write(command)
                self._serial.flush()
            except (serial.SerialException, OSError):
                self._close()
                raise
            return True

    @contextmanager
    def operation(self, owner):
        with self._exclusive():
            with self._state_lock:
                if not self.is_connected():
                    raise MotionConnectionError("Connect motors/Telecover before sending commands.")
                self._owner = owner
                connection = self._serial
                self.stop_requested.clear()
            try:
                # Discard replies left by the previous operation, never mid-scan.
                connection.reset_input_buffer()
                yield _SerialOperation(self, connection)
            except (serial.SerialException, OSError):
                with self._state_lock:
                    self._close()
                raise
            finally:
                with self._state_lock:
                    self._owner = None
