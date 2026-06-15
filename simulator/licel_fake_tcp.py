#!/usr/bin/env python3
"""Minimal Licel Ethernet Controller simulator used by licelcontroller.py."""

import argparse
import glob
import json
import math
import os
import random
import socketserver
import struct
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 2055
DEFAULT_SHOT_RATE = 30.0
MAX_BINS = 16384
DEFAULT_DATA_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "data"
)


@dataclass
class TransientRecorder:
    input_range: int = 0
    threshold_mode: int = 0
    discriminator: int = 0
    shots: int = 2
    armed: bool = False
    acquiring: bool = False
    memory: str = "A"
    started_at: Optional[float] = None
    recorded_signal_mv: Optional[List[float]] = None

    def clear(self):
        self.shots = 2
        self.memory = "A"

    def start(self):
        self.clear()
        self.armed = True
        self.acquiring = True
        self.started_at = time.monotonic()

    def update_shots(self, shot_rate):
        if self.acquiring and self.started_at is not None:
            elapsed = max(0.0, time.monotonic() - self.started_at)
            self.shots = min(4094, 2 + int(elapsed * shot_rate))

    def stop(self, shot_rate):
        self.update_shots(shot_rate)
        self.acquiring = False
        self.started_at = None


@dataclass
class LicelState:
    device_ids: Tuple[int, ...]
    shot_rate: float = DEFAULT_SHOT_RATE
    recording_paths: Tuple[str, ...] = ()
    selected: List[int] = field(default_factory=list)
    recorders: Dict[int, TransientRecorder] = field(init=False)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def __post_init__(self):
        self.recorders = {
            device_id: TransientRecorder() for device_id in self.device_ids
        }

    def selected_recorders(self):
        return [self.recorders[device_id] for device_id in self.selected]

    def load_next_recording(self):
        if not self.recording_paths:
            return {}

        path = random.choice(self.recording_paths)
        with open(path, "r", encoding="utf-8") as recording_file:
            recording = json.load(recording_file)
        print(f"Using recorded acquisition: {os.path.basename(path)}")
        return recording

    def assign_next_recording(self, device_ids):
        recording = self.load_next_recording()
        for device_id in device_ids:
            channel = recording.get(str(device_id))
            signal = channel.get("data_mv") if channel else None
            self.recorders[device_id].recorded_signal_mv = signal


class LicelProtocol:
    def __init__(self, state):
        self.state = state

    def handle(self, command):
        command = command.strip()
        if not command:
            return b""

        print(f">> {command}")
        parts = command.split()
        name = parts[0].upper()

        with self.state.lock:
            if name in {"SELECT", "SEL"}:
                response = self._select(command[len(parts[0]) :].strip())
            elif name in {"RANGE", "RANG"}:
                response = self._range(parts)
            elif name in {"THRESHOLD", "THR", "TRESHOLD"}:
                response = self._threshold(parts)
            elif name in {"DISCRIMINATOR", "DISC"}:
                response = self._discriminator(parts)
            elif name in {"CLEAR", "CLE"}:
                response = self._clear(multiple=False)
            elif name in {"MCLEAR", "MCL"}:
                response = self._clear(multiple=True)
            elif name in {"START", "STAR"}:
                response = self._start(multiple=False)
            elif name in {"MSTART", "MSTA"}:
                response = self._start(multiple=True)
            elif name == "STOP":
                response = self._stop(multiple=False)
            elif name in {"MSTOP", "MSTO"}:
                response = self._stop(multiple=True)
            elif name in {"STAT?", "STATUS?"}:
                response = self._status()
            elif name == "DATA?":
                response = self._data(parts)
            else:
                response = self._text(f"{parts[0]} unknown command")

        if name == "DATA?" and not response.endswith(b"\r\n"):
            print(f"<< {len(response)} binary bytes")
        else:
            print(f"<< {response.decode(errors='replace').strip()}")
        return response

    @staticmethod
    def _text(message):
        return (message + "\r\n").encode("ascii")

    def _select(self, argument):
        if argument == "-1":
            self.state.selected = []
            return self._text("SELECT executed")

        try:
            selected = [int(value.strip()) for value in argument.split(",")]
        except ValueError:
            return self._text("SELECT unknown command")

        for device_id in selected:
            if device_id not in self.state.recorders:
                return self._text(
                    f"Device ID {device_id} is currently not supported"
                )

        self.state.selected = selected
        selected_text = ", ".join(str(value) for value in selected)
        return self._text(f"SELECT {selected_text} executed")

    def _first_selected(self):
        if not self.state.selected:
            return None
        return self.state.recorders[min(self.state.selected)]

    def _range(self, parts):
        recorder = self._first_selected()
        try:
            value = int(parts[1])
        except (IndexError, ValueError):
            return self._text("Illegal Range Value")
        if value not in (0, 1, 2):
            return self._text("Illegal Range Value")
        if recorder is None:
            return self._text("RANGE failed for TR -1, Can't write")

        recorder.input_range = value
        millivolts = {0: 500, 1: 100, 2: 20}[value]
        return self._text(f"RANGE set to -{millivolts}mV")

    def _threshold(self, parts):
        recorder = self._first_selected()
        try:
            value = int(parts[1])
        except (IndexError, ValueError):
            value = -1
        if recorder is None or value not in (0, 1):
            return self._text("THRESHOLD failed for TR -1, Can't write")

        recorder.threshold_mode = value
        damping = "on" if value else "off"
        return self._text(f"THRESHOLD executed : Damping {damping}")

    def _discriminator(self, parts):
        recorder = self._first_selected()
        try:
            value = int(parts[1])
        except (IndexError, ValueError):
            value = -1
        if not 0 <= value <= 63:
            return self._text("DISCRIMINATOR value is out of range")
        if recorder is None:
            return self._text(
                "DISCRIMINATOR failed for TR -1, Can't write"
            )

        recorder.discriminator = value
        return self._text(f"DISCRIMINATOR set to {value}")

    def _clear(self, multiple):
        recorders = self.state.selected_recorders()
        if not recorders:
            command = "MCLEAR" if multiple else "CLEAR"
            return self._text(f"{command} failed for TR -1, Can't write")
        targets = recorders if multiple else recorders[:1]
        for recorder in targets:
            recorder.clear()
        return self._text("MCLEAR executed" if multiple else "CLEAR executed")

    def _start(self, multiple):
        recorders = self.state.selected_recorders()
        if not recorders:
            command = "MSTART" if multiple else "START"
            return self._text(f"{command} failed for TR -1, Can't write")
        targets = recorders if multiple else recorders[:1]
        target_ids = self.state.selected if multiple else self.state.selected[:1]
        self.state.assign_next_recording(target_ids)
        for recorder in targets:
            recorder.start()
        return self._text("MSTART executed" if multiple else "START executed")

    def _stop(self, multiple):
        recorders = self.state.selected_recorders()
        if not recorders:
            command = "MSTOP" if multiple else "STOP"
            return self._text(f"{command} failed for TR -1, Can't write")
        targets = recorders if multiple else recorders[:1]
        for recorder in targets:
            recorder.stop(self.state.shot_rate)
        return self._text("MSTOP executed" if multiple else "STOP executed")

    def _status(self):
        recorder = self._first_selected()
        if recorder is None:
            return self._text("STAT? failed for TR -1, Can't write")

        recorder.update_shots(self.state.shot_rate)
        fields = ["Shots", str(recorder.shots)]
        if recorder.armed:
            fields.append("Armed")
        if recorder.acquiring:
            fields.append("Acquiring")
        if recorder.memory == "B":
            fields.append("MemB")
        return self._text(" ".join(fields))

    def _data(self, parts):
        try:
            device_id = int(parts[1])
            bins = int(parts[2])
            dataset = parts[3].upper()
            memory = parts[4].upper()
        except (IndexError, ValueError):
            return self._text("DATA? unknown command")

        if device_id not in self.state.recorders:
            return self._text(
                f"Device ID {device_id} is currently not supported"
            )
        if bins < 1 or bins > MAX_BINS or dataset not in {"PC", "LSW", "MSW"}:
            return self._text("DATA? unknown command")
        if memory not in {"A", "B"}:
            return self._text("DATA? unknown command")

        recorder = self.state.recorders[device_id]
        recorder.update_shots(self.state.shot_rate)
        values = self._dataset_values(device_id, recorder, dataset, bins)
        return struct.pack(f"<{bins}H", *values)

    @staticmethod
    def _dataset_values(device_id, recorder, dataset, bins):
        # The first word is intentionally discarded by combineAnalogDatasets.
        values = [0]
        cycles = max(1, recorder.shots - 2)
        range_mv = {0: 500.0, 1: 100.0, 2: 20.0}[recorder.input_range]

        for index in range(1, bins):
            x = index - 1
            accumulated = None
            if (
                recorder.recorded_signal_mv is not None
                and x < len(recorder.recorded_signal_mv)
            ):
                signal_mv = float(recorder.recorded_signal_mv[x])
                # Recorded values are already normalized by shot count. Encode
                # the accumulated ADC value so sub-count precision is retained.
                accumulated = round(
                    signal_mv * 4096.0 * cycles / range_mv
                )
            else:
                background = 120.0 + 8.0 * math.sin(x / 37.0 + device_id)
                peak = 2200.0 * math.exp(-((x - 650.0) / 170.0) ** 2)
                tail = 700.0 * math.exp(-x / 1800.0)
                adc_counts = int(background + peak + tail)
                adc_counts = max(0, min(4095, adc_counts))
                accumulated = adc_counts * cycles

            if dataset == "PC":
                value = int(20 + 180 * math.exp(-x / 900.0))
            else:
                clipped = accumulated > 0xFFFFFF
                accumulated = max(0, min(0xFFFFFF, accumulated))
                if dataset == "LSW":
                    value = accumulated & 0xFFFF
                else:
                    value = (accumulated >> 16) & 0x00FF
                    if clipped:
                        value |= 0x0100
            values.append(value)

        return values


class LicelTCPHandler(socketserver.BaseRequestHandler):
    def handle(self):
        peer = f"{self.client_address[0]}:{self.client_address[1]}"
        print(f"Client connected: {peer}")
        protocol = LicelProtocol(self.server.licel_state)
        buffer = b""

        try:
            while True:
                data = self.request.recv(4096)
                if not data:
                    break
                buffer += data

                while b"\r\n" in buffer:
                    raw_command, buffer = buffer.split(b"\r\n", 1)
                    response = protocol.handle(
                        raw_command.decode("ascii", errors="ignore")
                    )
                    if response:
                        self.request.sendall(response)
        finally:
            print(f"Client disconnected: {peer}")


class LicelTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, address, state):
        self.licel_state = state
        super().__init__(address, LicelTCPHandler)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Minimal TCP simulator for lidarcontroller/licelcontroller.py"
    )
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument(
        "--devices",
        default="0-15",
        help="Available TR IDs, for example 0-15 or 0,2,5",
    )
    parser.add_argument(
        "--shot-rate",
        type=float,
        default=DEFAULT_SHOT_RATE,
        help="Simulated trigger rate in Hz",
    )
    parser.add_argument(
        "--data-dir",
        default=DEFAULT_DATA_DIR,
        help=(
            "Directory containing lidar_simul_*.json recordings. "
            "Use an empty directory for synthetic signals only."
        ),
    )
    return parser.parse_args()


def parse_devices(value):
    device_ids = set()
    for item in value.split(","):
        item = item.strip()
        if "-" in item:
            start_text, end_text = item.split("-", 1)
            start, end = int(start_text), int(end_text)
            device_ids.update(range(start, end + 1))
        else:
            device_ids.add(int(item))
    if not device_ids:
        raise ValueError("at least one device ID is required")
    return tuple(sorted(device_ids))


def main():
    args = parse_args()
    recording_pattern = os.path.join(args.data_dir, "lidar_simul_*.json")
    recording_paths = tuple(sorted(glob.glob(recording_pattern)))
    state = LicelState(
        parse_devices(args.devices),
        args.shot_rate,
        recording_paths,
    )

    with LicelTCPServer((args.host, args.port), state) as server:
        print("Licel TCP simulator started.")
        print(f"Listening on {args.host}:{args.port}")
        print(f"Available TRs: {', '.join(map(str, state.device_ids))}")
        print(f"Recorded acquisitions: {len(recording_paths)}")
        print("Ctrl+C to stop.")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nStopping simulator.")


if __name__ == "__main__":
    main()
