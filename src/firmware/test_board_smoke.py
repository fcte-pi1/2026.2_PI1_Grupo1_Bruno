import json
import sys
import types
import unittest
from unittest.mock import patch

import board_smoke
from telemetry import BoundedWriter


class BoardSmokeTests(unittest.TestCase):
    def exercise(self, transport):
        now = [0]
        data = bytearray()
        closed = []
        uart_config = []

        def uart(*args, **kwargs):
            uart_config.append((args, kwargs))
            return types.SimpleNamespace(write=write, deinit=lambda: closed.append("serial"))

        def write(chunk):
            count = min(41, len(chunk))
            data.extend(chunk[:count])
            return count

        class FakeWifi:
            def __init__(self, *_args):
                self.writer = BoundedWriter(write)

            def service(self, publisher, _now_ms, byte_budget):
                publisher.service(self.writer, byte_budget)

            def close(self):
                closed.append("wifi")

        class FakeWlan:
            IF_STA = 0

            def __init__(self, _mode):
                pass

        def sleep_ms(delay):
            now[0] += delay

        modules = {
            "machine": types.SimpleNamespace(unique_id=lambda: b"board", UART=uart),
            "network": types.SimpleNamespace(WLAN=FakeWlan),
            "wifi_config": types.SimpleNamespace(SSID="fake", PASSWORD="fake", HOST="127.0.0.1", PORT=8765),
            "wifi_telemetry": types.SimpleNamespace(WifiTelemetry=FakeWifi),
        }
        with (
            patch.dict(sys.modules, modules),
            patch("time.ticks_ms", lambda: now[0], create=True),
            patch("time.ticks_diff", lambda a, b: a - b, create=True),
            patch("time.sleep_ms", sleep_ms, create=True),
        ):
            board_smoke.run(transport, duration_s=1)
        frames = [json.loads(line) for line in data.splitlines()]
        self.assertEqual(len(frames), 10)
        self.assertEqual([f["seq"] for f in frames], list(range(10)))
        self.assertTrue(all(f["run_id"] is None and f["state"] == "pronto" for f in frames))
        self.assertTrue(all(f["event"] == "sample" and "sensors" not in f for f in frames))
        self.assertEqual(closed, [transport])
        return uart_config

    def test_serial_heartbeat_partial_writes_and_cleanup(self):
        config = self.exercise("serial")
        self.assertEqual(config[0][0], (1,))
        self.assertEqual((config[0][1]["tx"], config[0][1]["rx"]), (17, 18))

    def test_wifi_heartbeat_and_cleanup_without_uart(self):
        self.assertEqual(self.exercise("wifi"), [])


if __name__ == "__main__":
    unittest.main()
