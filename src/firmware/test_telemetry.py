"""Host-side fake-stream tests; no board, UART or network is required."""

import json
import unittest

from demo_telemetry import run_simulation
from telemetry import (
    MAX_PAYLOAD_BYTES,
    STAT_KEYS,
    BoundedWriter,
    TelemetryPublisher,
    TicksClock,
    reading,
)


class FakeStream:
    def __init__(self, limit=4097):
        self.limit = limit
        self.data = bytearray()
        self.calls = []
        self.result = "write"

    def write(self, data):
        self.calls.append(len(data))
        if isinstance(self.result, Exception):
            raise self.result
        if self.result != "write":
            return self.result
        count = min(self.limit, len(data))
        self.data.extend(data[:count])
        return count

    def frames(self):
        return [json.loads(line) for line in bytes(self.data).splitlines()]


class TelemetryTests(unittest.TestCase):
    def setUp(self):
        self.now = 0

    def publisher(self, **kwargs):
        return TelemetryPublisher("robot-1", "boot-1", "run-1", "maze-1", lambda: self.now, **kwargs)

    def drain(self, publisher, writer):
        for _ in range(10000):
            if not publisher.pending_count:
                return
            publisher.service(writer, 31)
        self.fail("bounded queue did not drain")

    def test_partial_writer_never_interleaves_lines_and_obeys_budget(self):
        publisher = self.publisher()
        publisher.emit("start", "running")
        publisher.emit("sample", "running", sensors={"front": reading(12, "cm")})
        publisher.emit("finish", "stopped")
        stream = FakeStream(7)
        self.drain(publisher, BoundedWriter(stream.write))
        self.assertLessEqual(max(stream.calls), 31)
        self.assertEqual([f["seq"] for f in stream.frames()], [0, 1, 2])
        self.assertEqual([f["event"] for f in stream.frames()], ["start", "sample", "finish"])

    def test_service_makes_one_write_only(self):
        publisher = self.publisher()
        publisher.emit("start", "running")
        stream = FakeStream(1)
        self.assertEqual(publisher.service(BoundedWriter(stream.write), 20), 1)
        self.assertEqual(stream.calls, [20])

    def test_absent_consumer_bounds_memory_and_retains_critical_events(self):
        publisher = self.publisher(queue_capacity=3)
        publisher.emit("start", "running")
        for _ in range(1000):
            publisher.emit("sample", "running")
        publisher.emit("finish", "stopped")
        self.assertEqual(publisher.pending_count, 3)
        self.assertEqual(publisher.stats()["queue_high_water"], 3)
        self.assertEqual(publisher.stats()["samples_dropped"], 999)
        stream = FakeStream()
        self.drain(publisher, BoundedWriter(stream.write))
        frames = stream.frames()
        self.assertEqual([f["event"] for f in frames], ["start", "sample", "finish"])
        self.assertEqual([f["seq"] for f in frames], [0, 1000, 1001])

    def test_all_critical_saturation_rejects_newest_and_counts_it(self):
        publisher = self.publisher(queue_capacity=2)
        publisher.emit("start", "running")
        publisher.emit("fault", "fault", fault={"code": "STOP", "message": "stopped"})
        self.assertFalse(publisher.emit("finish", "stopped"))
        self.assertFalse(publisher.emit("sample", "stopped"))
        self.assertEqual(publisher.stats()["events_dropped"], 1)
        self.assertEqual(publisher.stats()["samples_dropped"], 1)
        stream = FakeStream()
        self.drain(publisher, BoundedWriter(stream.write))
        publisher.emit("finish", "stopped")
        self.drain(publisher, BoundedWriter(stream.write))
        self.assertEqual([f["seq"] for f in stream.frames()], [0, 1, 4])

    def test_partial_noncritical_frame_is_pinned_even_for_critical(self):
        publisher = self.publisher(queue_capacity=1)
        publisher.emit("sample", "running")
        stream = FakeStream(3)
        writer = BoundedWriter(stream.write)
        publisher.service(writer)
        self.assertFalse(publisher.emit("finish", "stopped"))
        self.drain(publisher, writer)
        self.assertEqual(stream.frames()[0]["event"], "sample")
        self.assertEqual(publisher.stats()["events_dropped"], 1)

    def test_slow_consumer_keeps_controller_progressing(self):
        stream = FakeStream(1)
        publisher = run_simulation(BoundedWriter(stream.write), cycles=1000, byte_budget=7)
        self.assertEqual(publisher.stats()["control_cycles"], 1000)
        self.assertGreater(publisher.stats()["samples_dropped"], 0)
        self.assertLessEqual(publisher.stats()["queue_high_water"], 8)
        self.assertEqual(stream.frames()[0]["event"], "start")
        self.assertEqual(stream.frames()[-1]["event"], "finish")

    def test_none_and_eagain_make_no_progress_or_loss(self):
        publisher = self.publisher()
        publisher.emit("start", "running")
        stream = FakeStream()
        writer = BoundedWriter(stream.write)
        for result in (None, 0, OSError(11), OSError(35)):
            stream.result = result
            self.assertEqual(publisher.service(writer), 0)
            self.assertTrue(writer.connected)
            self.assertEqual(publisher.pending_count, 1)
        stream.result = "write"
        self.drain(publisher, writer)
        self.assertEqual(len(stream.frames()), 1)

    def test_disconnect_mid_frame_replays_whole_frame_on_new_stream(self):
        publisher = self.publisher()
        publisher.emit("start", "running")
        stream = FakeStream(17)
        old = BoundedWriter(stream.write)
        publisher.service(old)
        self.assertEqual(len(stream.data), 17)
        stream.result = OSError(104)
        self.assertEqual(publisher.service(old), 0)
        self.assertFalse(old.connected)
        replacement = FakeStream()
        self.drain(publisher, BoundedWriter(replacement.write))
        frame = replacement.frames()[0]
        self.assertTrue(bytes(replacement.data).startswith(b"{"))
        self.assertEqual((frame["run_id"], frame["boot_id"], frame["seq"]), ("run-1", "boot-1", 0))

    def test_writer_replacement_without_intermediate_service_restarts_frame(self):
        publisher = self.publisher()
        publisher.emit("sample", "ready")
        old_stream = FakeStream(13)
        old = BoundedWriter(old_stream.write)
        publisher.service(old)
        old.disconnect()
        stream = FakeStream()
        self.drain(publisher, BoundedWriter(stream.write))
        self.assertEqual(stream.frames()[0]["seq"], 0)

    def test_invalid_byte_count_disconnects_without_advancing(self):
        publisher = self.publisher()
        publisher.emit("start", "running")
        stream = FakeStream()
        stream.result = 5000
        writer = BoundedWriter(stream.write)
        with self.assertRaises(ValueError):
            publisher.service(writer, 10)
        self.assertFalse(writer.connected)
        self.assertEqual(publisher.pending_count, 1)

    def test_sample_10hz_and_no_catchup_bursts(self):
        publisher = self.publisher()
        for cycle in range(100):
            self.now = cycle * 10
            publisher.record_control_cycle(late=cycle == 5)
            publisher.sample("running")
        self.assertEqual(publisher.stats()["control_cycles"], 100)
        self.assertEqual(publisher.stats()["control_late_cycles"], 1)
        self.assertEqual(publisher.stats()["samples_dropped"], 2)
        self.now = 5000
        self.assertTrue(publisher.sample("running"))
        self.assertFalse(publisher.sample("running"))

    def test_time_and_seq_remain_monotonic_between_runs(self):
        publisher = self.publisher()
        publisher.emit("start", "running")
        self.now = 20
        publisher.emit("finish", "stopped")
        publisher.run_id = "run-2"  # Application alone starts another run.
        self.now = 100
        publisher.emit("start", "running")
        stream = FakeStream()
        self.drain(publisher, BoundedWriter(stream.write))
        self.assertEqual([f["seq"] for f in stream.frames()], [0, 1, 2])
        self.assertEqual([f["t_ms"] for f in stream.frames()], [0, 20, 100])
        self.assertEqual(stream.frames()[-1]["run_id"], "run-2")
        self.now = 99
        with self.assertRaises(ValueError):
            publisher.emit("sample", "running")

    def test_wrapping_ticks_are_extended(self):
        ticks = [250]
        clock = TicksClock(lambda: ticks[0], lambda a, b: (a - b + 128) % 256 - 128)
        ticks[0] = 4
        self.assertEqual(clock(), 10)
        ticks[0] = 24
        self.assertEqual(clock(), 30)

    def test_stats_exact_shape_and_snapshot(self):
        publisher = self.publisher()
        publisher.record_control_cycle(late=True)
        snapshot = publisher.stats()
        self.assertEqual(set(snapshot), set(STAT_KEYS))
        self.assertTrue(all(type(v) is int and v >= 0 for v in snapshot.values()))
        snapshot["control_cycles"] = -1
        self.assertEqual(publisher.stats()["control_cycles"], 1)

    def test_payload_bound_counts_encoded_utf8_and_excludes_lf(self):
        publisher = self.publisher(include_stats=False)
        stream = FakeStream()
        writer = BoundedWriter(stream.write)
        # Large but finite numeric readings allow hitting the precise byte limit
        # while retaining valid sensor names, counts and units.
        sensors = {"sensor" + str(i): reading(1, "cm") for i in range(8)}
        left = {"speed": reading(1, "mm/s"), "target": reading(1, "mm/s")}
        right = {"speed": reading(1, "mm/s"), "target": reading(1, "mm/s")}
        payload = {"sensors": sensors, "wheel_left": left, "wheel_right": right}
        publisher.emit("sample", "running", **payload)
        self.drain(publisher, writer)
        additional = MAX_PAYLOAD_BYTES - (len(stream.data) - 1)
        measurements = list(sensors.values()) + list(left.values()) + list(right.values())
        for measurement in measurements:
            extra_digits = min(299, additional)
            measurement["value"] = int("1" * (extra_digits + 1))
            additional -= extra_digits
        self.assertEqual(additional, 0)
        self.assertTrue(publisher.emit("sample", "running", **payload))
        self.drain(publisher, writer)
        self.assertEqual(len(bytes(stream.data).splitlines()[1]), MAX_PAYLOAD_BYTES)
        self.assertFalse(publisher.emit("sample", "runniné", **payload))
        self.assertEqual(publisher.stats()["samples_dropped"], 1)

    def test_invalid_and_nonfinite_measurements_are_rejected(self):
        for value in (float("nan"), float("inf"), -float("inf"), True, "12"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                reading(value, "cm")
        self.assertEqual(reading(None, "cm", valid=False)["value"], None)
        publisher = self.publisher()
        for payload in (
            {"debug": "not on telemetry UART"},
            {"fault": {"code": "X"}},
            {"sensors": {"a": {"value": 1}}},
        ):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                publisher.emit("sample", "running", **payload)
        with self.assertRaises(ValueError):
            publisher.emit("fault", "fault")
        for payload in (
            {"sensors": {"": reading(1, "cm")}},
            {"sensors": {"x" * 25: reading(1, "cm")}},
            {"sensors": {str(i): reading(1, "cm") for i in range(9)}},
            {"sensors": {"front": reading(1, "mm")}},
            {"battery_voltage": reading(1, "mV")},
            {"control_error": reading(1, "m/s")},
        ):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                publisher.emit("sample", "running", **payload)

    def test_timestamp_and_sequence_safe_integer_limits(self):
        publisher = self.publisher()
        self.now = 2**53
        with self.assertRaises(ValueError):
            publisher.emit("sample", "running")
        self.now = 0
        publisher._seq = 2**53
        with self.assertRaises(ValueError):
            publisher.emit("sample", "running")

    def test_map_update_and_run_requirements(self):
        publisher = self.publisher()
        map_data = {
            "width": 2,
            "height": 2,
            "source": "simulated",
            "cells": [{"x": 0, "y": 0, "walls": 9, "known": 15}],
        }
        self.assertTrue(publisher.emit("map_update", "mapping", map=map_data))
        with self.assertRaises(ValueError):
            publisher.emit("map_update", "mapping")
        with self.assertRaises(ValueError):
            publisher.emit("sample", "mapping", map=map_data)
        map_data["cells"][0]["known"] = 1
        with self.assertRaises(ValueError):
            publisher.emit("map_update", "mapping", map=map_data)
        publisher.run_id = None
        with self.assertRaises(ValueError):
            publisher.emit("start", "running")
        self.assertTrue(publisher.emit("sample", "ready"))

    def test_simulated_demo_labels_sources_and_rates(self):
        stream = FakeStream()
        publisher = run_simulation(BoundedWriter(stream.write), cycles=100)
        frames = stream.frames()
        self.assertEqual(len(frames), 12)  # start + 10 samples + finish.
        self.assertEqual(publisher.stats()["samples_dropped"], 0)
        self.assertEqual([f["seq"] for f in frames], list(range(12)))
        for frame in frames:
            self.assertEqual(frame["schema_version"], 1)
            self.assertEqual(frame["boot_id"], "sim-boot-1")
            self.assertLessEqual(len(json.dumps(frame, separators=(",", ":")).encode()), 4096)
            if frame["event"] == "sample":
                self.assertEqual(frame["wheel_left"]["speed"]["source"], "simulated")
                self.assertEqual(frame["sensors"]["front"]["source"], "simulated")

    def test_demo_matches_receiver_contract_when_host_dependency_available(self):
        try:
            from telemetria.modelos import Frame
        except ImportError:
            self.skipTest("optional host contract check: set PYTHONPATH=src/telemetria and install host deps")
        stream = FakeStream()
        run_simulation(BoundedWriter(stream.write))
        for frame in stream.frames():
            Frame.model_validate(frame)
        publisher = self.publisher()
        publisher.emit("fault", "fault", fault={"code": "STOP", "message": "stopped"})
        publisher.emit(
            "map_update",
            "mapping",
            map={
                "width": 2,
                "height": 2,
                "source": "simulated",
                "cells": [{"x": 0, "y": 0, "walls": 9, "known": 15}],
            },
        )
        stream = FakeStream()
        self.drain(publisher, BoundedWriter(stream.write))
        for frame in stream.frames():
            Frame.model_validate(frame)


if __name__ == "__main__":
    unittest.main()
