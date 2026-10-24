"""Bounded JSON Lines telemetry core for CPython and MicroPython.

No hardware, wall clock, logging, thread or transport dependency is imported.
Call from the main loop, after control, never from an interrupt handler.
"""

import json

MAX_PAYLOAD_BYTES = 4096  # LF is additional to this limit.
MAX_SAFE_INTEGER = 2**53 - 1
CRITICAL_EVENTS = ("start", "finish", "fault")
EVENTS = ("start", "sample", "map_update", "finish", "fault")
STAT_KEYS = (
    "control_cycles",
    "control_late_cycles",
    "samples_dropped",
    "events_dropped",
    "queue_high_water",
)


def _text(value, name, maximum, nullable=False):
    if value is None and nullable:
        return
    if not isinstance(value, str) or not 1 <= len(value) <= maximum:
        raise ValueError("invalid " + name)


def reading(value, unit, source="measured", valid=True):
    """Construct a contract reading; simulated measurements must say so."""
    result = {"value": value, "unit": unit, "source": source, "valid": valid}
    _reading(result)
    return result


def _reading(value, unit=None):
    if not isinstance(value, dict) or set(value) != {"value", "unit", "source", "valid"}:
        raise ValueError("reading requires value, unit, source and valid")
    _text(value["unit"], "unit", 16)
    if unit is not None and value["unit"] != unit:
        raise ValueError("reading requires unit " + unit)
    if value["source"] not in ("simulated", "measured", "estimated"):
        raise ValueError("invalid reading source")
    if type(value["valid"]) is not bool:
        raise ValueError("invalid reading validity")
    number = value["value"]
    if number is not None:
        if type(number) not in (int, float):
            raise ValueError("invalid reading value")
        try:
            finite = -float("inf") < float(number) < float("inf")
        except OverflowError:
            finite = False
        if not finite:
            raise ValueError("reading must be finite")


def _validate_payload(event, payload):
    allowed = {"wheel_left", "wheel_right", "control_error", "sensors", "battery_voltage", "fault", "map"}
    if set(payload) - allowed:
        raise ValueError("unknown payload field")
    if event != "fault" and payload.get("fault") is not None:
        raise ValueError("fault is only allowed in a fault event")
    if event != "map_update" and payload.get("map") is not None:
        raise ValueError("map is only allowed in a map_update event")
    for key, unit in (("control_error", "mm/s"), ("battery_voltage", "V")):
        if payload.get(key) is not None:
            _reading(payload[key], unit)
    for key in ("wheel_left", "wheel_right"):
        if payload.get(key) is not None:
            wheel = payload[key]
            if not isinstance(wheel, dict) or set(wheel) != {"speed", "target"}:
                raise ValueError("wheel requires speed and target")
            _reading(wheel["speed"], "mm/s")
            _reading(wheel["target"], "mm/s")
    sensors = payload.get("sensors", {})
    if not isinstance(sensors, dict) or len(sensors) > 8:
        raise ValueError("sensors must be an object with at most 8 entries")
    for key, value in sensors.items():
        _text(key, "sensor name", 24)
        _reading(value, "cm")
    fault = payload.get("fault")
    if event == "fault" or fault is not None:
        if not isinstance(fault, dict) or set(fault) != {"code", "message"}:
            raise ValueError("fault requires code and message")
        _text(fault["code"], "fault code", 40)
        if not isinstance(fault["message"], str) or len(fault["message"]) > 200:
            raise ValueError("invalid fault message")
    if event == "map_update" or payload.get("map") is not None:
        _validate_map(payload.get("map"))


def _validate_map(value):
    if not isinstance(value, dict) or set(value) != {"width", "height", "source", "cells"}:
        raise ValueError("map requires width, height, source and cells")
    for key in ("width", "height"):
        if type(value[key]) is not int or not 1 <= value[key] <= 32:
            raise ValueError("invalid map dimensions")
    if value["source"] not in ("simulated", "measured", "estimated"):
        raise ValueError("invalid map source")
    cells = value["cells"]
    if not isinstance(cells, list) or not 1 <= len(cells) <= 32:
        raise ValueError("map must contain 1 to 32 cells")
    seen = set()
    for cell in cells:
        if not isinstance(cell, dict) or set(cell) != {"x", "y", "walls", "known"}:
            raise ValueError("invalid map cell")
        for key, limit in (
            ("x", value["width"] - 1),
            ("y", value["height"] - 1),
            ("walls", 15),
            ("known", 15),
        ):
            if type(cell[key]) is not int or not 0 <= cell[key] <= limit:
                raise ValueError("invalid map cell " + key)
        coordinate = (cell["x"], cell["y"])
        if coordinate in seen or cell["walls"] & ~cell["known"]:
            raise ValueError("duplicate cell or walls outside known mask")
        seen.add(coordinate)


class TicksClock:
    """Extend wrapping ticks using the port's documented ticks_diff function.

    Poll at least once per half ticks period, including while disconnected.
    Example: TicksClock(time.ticks_ms, time.ticks_diff).
    """

    def __init__(self, ticks_ms, ticks_diff):
        self._ticks = ticks_ms
        self._diff = ticks_diff
        self._last = ticks_ms()
        self._elapsed = 0

    def __call__(self):
        now = self._ticks()
        delta = self._diff(now, self._last)
        if delta < 0:
            raise ValueError("ticks clock was not polled within its half period")
        self._last = now
        self._elapsed += delta
        return self._elapsed


class BoundedWriter:
    """Adapter around ONE nonblocking stream, replaced on reconnection.

    write(buffer) must return a count or None, with a timeout of zero.
    This adapter cannot make a blocking driver nonblocking. EAGAIN/EWOULDBLOCK
    means no progress; other OSError values disconnect this stream.
    """

    def __init__(self, write, close=None):
        self._write = write
        self._close = close
        self.connected = True

    def disconnect(self):
        if self.connected:
            self.connected = False
            if self._close is not None:
                self._close()

    def write(self, data):
        if not self.connected:
            return 0
        try:
            written = self._write(data)
        except OSError as error:
            code = error.args[0] if error.args else None
            if code in (11, 35):  # EAGAIN / EWOULDBLOCK across supported ports.
                return 0
            self.disconnect()
            return 0
        if written is None:
            return 0
        if type(written) is not int or not 0 <= written <= len(data):
            self.disconnect()
            raise ValueError("writer returned an invalid byte count")
        return written


class TelemetryPublisher:
    """Finite FIFO, critical-event retention and bounded incremental writes.

    Capacity includes the partially transmitted frame. Overload replaces the
    oldest waiting noncritical frame. A sample never evicts map_update; critical
    events may evict either. When all slots are critical (or pinned), reject the
    incoming frame and count the loss. Accepted frames retain sequence order.
    """

    def __init__(
        self, robot_id, boot_id, run_id, maze_id, clock_ms, sample_hz=10, queue_capacity=8, include_stats=True
    ):
        _text(robot_id, "robot_id", 40)
        _text(boot_id, "boot_id", 40)
        _text(run_id, "run_id", 40, True)
        _text(maze_id, "maze_id", 20, True)
        if type(queue_capacity) is not int or queue_capacity < 1:
            raise ValueError("queue_capacity must be a positive integer")
        if type(sample_hz) is not int or not 1 <= sample_hz <= 1000:
            raise ValueError("sample_hz must be an integer from 1 to 1000")
        self.robot_id, self.boot_id = robot_id, boot_id
        self.run_id, self.maze_id = run_id, maze_id
        self._clock = clock_ms
        self._last_time = 0
        self._period = max(1, (1000 + sample_hz - 1) // sample_hz)
        self._last_sample = None
        self._capacity = queue_capacity
        self._queue = []  # [event, encoded frame, write offset]
        self._writer = None
        self._seq = 0
        self._include_stats = include_stats
        self._stats = {key: 0 for key in STAT_KEYS}

    @property
    def pending_count(self):
        return len(self._queue)

    def stats(self):
        return dict(self._stats)

    def record_control_cycle(self, late=False):
        self._increment("control_cycles")
        if late:
            self._increment("control_late_cycles")

    def _increment(self, key):
        self._stats[key] = min(MAX_SAFE_INTEGER, self._stats[key] + 1)

    def _now(self):
        now = self._clock()
        if type(now) is not int or now < self._last_time or now > MAX_SAFE_INTEGER:
            raise ValueError("clock_ms must return monotonic integers in 0..2**53-1")
        self._last_time = now
        return now

    def _lost(self, event):
        key = "samples_dropped" if event == "sample" else "events_dropped"
        self._increment(key)

    def emit(self, event, state, **payload):
        return self._enqueue(event, state, self._now(), payload)

    def sample(self, state, **payload):
        """At most one sample per period; no catch-up bursts after delays."""
        now = self._now()
        if self._last_sample is not None and now - self._last_sample < self._period:
            return False
        self._last_sample = now
        return self._enqueue("sample", state, now, payload)

    def _enqueue(self, event, state, now, payload):
        if event not in EVENTS:
            raise ValueError("invalid event")
        _text(state, "state", 30)
        # The application may change run/maze between runs; validate each time.
        _text(self.run_id, "run_id", 40, True)
        _text(self.maze_id, "maze_id", 20, True)
        if event in ("start", "finish") and self.run_id is None:
            raise ValueError("start and finish require an application run_id")
        if event == "map_update" and self.maze_id is None:
            raise ValueError("map_update requires maze_id")
        if self._seq > MAX_SAFE_INTEGER:
            raise ValueError("sequence exhausted for this boot")
        _validate_payload(event, payload)
        frame = {
            "schema_version": 1,
            "robot_id": self.robot_id,
            "boot_id": self.boot_id,
            "run_id": self.run_id,
            "maze_id": self.maze_id,
            "seq": self._seq,
            "t_ms": now,
            "event": event,
            "state": state,
        }
        self._seq += 1
        frame.update(payload)
        if self._include_stats:
            frame["telemetry_stats"] = self.stats()
        try:
            encoded = json.dumps(frame, separators=(",", ":")).encode("utf-8")
        except (TypeError, ValueError):
            self._lost(event)
            raise ValueError("payload must be JSON serializable")
        if len(encoded) > MAX_PAYLOAD_BYTES:
            self._lost(event)
            return False
        if len(self._queue) == self._capacity:
            victim = None
            for index, item in enumerate(self._queue):
                if item[2] or item[0] in CRITICAL_EVENTS:
                    continue
                if event == "sample" and item[0] != "sample":
                    continue
                victim = index
                break
            if victim is None:
                self._lost(event)
                return False
            self._lost(self._queue[victim][0])
            del self._queue[victim]
        self._queue.append([event, encoded + b"\n", 0])
        self._stats["queue_high_water"] = max(self._stats["queue_high_water"], len(self._queue))
        return True

    def service(self, writer, byte_budget=256):
        """Make at most one write, offering at most byte_budget bytes.

        After disconnect or writer replacement, retry the entire current frame
        on the new stream. Bytes from two frames are never interleaved. Receiver
        must reset its line buffer for every new connection.
        """
        if type(byte_budget) is not int or byte_budget < 0:
            raise ValueError("byte_budget must be a nonnegative integer")
        if writer is not self._writer:
            if self._queue:
                self._queue[0][2] = 0
            self._writer = writer
        if not self._queue:
            return 0
        item = self._queue[0]
        if writer is None or not writer.connected:
            item[2] = 0
            return 0
        if byte_budget == 0:
            return 0
        offset = item[2]
        chunk = memoryview(item[1])[offset : offset + byte_budget]
        written = writer.write(chunk)
        if not writer.connected:
            item[2] = 0
            return 0
        item[2] += written
        if item[2] == len(item[1]):
            del self._queue[0]
        return written
