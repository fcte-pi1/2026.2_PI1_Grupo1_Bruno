"""Teste manual de comunicação da ESP32-S3-DevKitC-1; não aciona motores.

No mpremote/REPL: import board_smoke; board_smoke.run("wifi")
Serial dedicada opcional: board_smoke.run("serial") em UART1, TX17/RX18.
"""

from telemetry import BoundedWriter, TelemetryPublisher, TicksClock


def run(transport="wifi", duration_s=30):
    if transport not in ("wifi", "serial"):
        raise ValueError("transport deve ser wifi ou serial")
    if type(duration_s) is not int or not 1 <= duration_s <= 300:
        raise ValueError("duration_s deve ser inteiro entre 1 e 300")

    import binascii
    import os
    import time

    import machine

    clock = TicksClock(time.ticks_ms, time.ticks_diff)
    publisher = TelemetryPublisher(
        robot_id="esp32s3-" + binascii.hexlify(machine.unique_id()).decode(),
        boot_id=binascii.hexlify(os.urandom(8)).decode(),
        run_id=None,
        maze_id=None,
        clock_ms=clock,
        include_stats=False,
    )
    if transport == "wifi":
        import network
        import wifi_config
        from wifi_telemetry import WifiTelemetry

        link = WifiTelemetry(
            network.WLAN(network.WLAN.IF_STA),
            wifi_config.SSID,
            wifi_config.PASSWORD,
            wifi_config.HOST,
            wifi_config.PORT,
        )
    else:
        # Só para bancada com GPIO17/18 livres e adaptador TTL 3,3 V separado.
        uart = machine.UART(1, baudrate=115200, tx=17, rx=18, timeout=0, timeout_char=0, txbuf=512)
        link = BoundedWriter(uart.write, uart.deinit)
    try:
        while clock() < duration_s * 1000:
            publisher.sample("pronto")  # Sem corrida e sem inventar leituras de sensores.
            if transport == "wifi":
                link.service(publisher, time.ticks_ms(), byte_budget=256)
            else:
                publisher.service(link, byte_budget=256)
            time.sleep_ms(10)
    finally:
        if transport == "wifi":
            link.close()
        else:
            link.disconnect()
