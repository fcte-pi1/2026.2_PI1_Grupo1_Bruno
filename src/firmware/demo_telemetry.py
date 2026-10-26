"""simulação com controle a 100 hz e telemetria a 10 hz."""

from telemetry import BoundedWriter, TelemetryPublisher, reading


def run_simulation(writer, cycles=100, byte_budget=256, boot_id="sim-boot-1"):
    now = [0]
    publisher = TelemetryPublisher("sim-robot", boot_id, "sim-run-1", "sim-maze", lambda: now[0])
    publisher.emit("start", "running")
    for cycle in range(cycles):
        now[0] = cycle * 10
        publisher.record_control_cycle(late=False)
        speed = reading(120 + cycle % 5, "mm/s", "simulated")
        target = reading(120, "mm/s", "simulated")
        publisher.sample(
            "running",
            wheel_left={"speed": speed, "target": target},
            wheel_right={"speed": speed, "target": target},
            control_error=reading(cycle % 5, "mm/s", "simulated"),
            sensors={"front": reading(18, "cm", "simulated")},
            battery_voltage=reading(7.5, "V", "simulated"),
        )
        publisher.service(writer, byte_budget)
    now[0] = cycles * 10
    publisher.emit("finish", "stopped")
    # escoa a fila com limite de tentativas ao encerrar a simulação
    for _ in range((publisher.pending_count + 1) * 4097):
        if not publisher.pending_count or not writer.connected:
            break
        if not publisher.service(writer, byte_budget):
            break
    return publisher


def uart_writer(uart_id, tx, rx, baudrate=115200):
    from machine import UART

    uart = UART(uart_id, baudrate=baudrate, tx=tx, rx=rx, timeout=0, timeout_char=0, txbuf=512)
    return BoundedWriter(uart.write, uart.deinit)


def main():
    import argparse
    import json
    import sys
    import uuid

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cycles", type=int, default=100)
    args = parser.parse_args()
    if args.cycles < 1:
        parser.error("--cycles must be positive")
    publisher = run_simulation(
        BoundedWriter(sys.stdout.buffer.write), args.cycles, boot_id="sim-" + uuid.uuid4().hex
    )
    sys.stdout.buffer.flush()
    print(json.dumps(publisher.stats()), file=sys.stderr)


if __name__ == "__main__":
    main()
