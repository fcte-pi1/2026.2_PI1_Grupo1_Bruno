"""Adaptador ESP32-S3/MicroPython. Nenhum movimento no construtor."""
import time
import machine
from . import config as cfg


class Hardware:
    def __init__(self):
        self.outputs = []
        self.pwms = []
        self.encoders = []
        self.sensors = {}
        self.last_ping = None
        try:
            for pair in cfg.MOTOR_PINS:
                self.outputs.append([machine.Pin(n, machine.Pin.OUT, value=0) for n in pair])
            for pair in self.outputs:
                self.pwms.append([machine.PWM(p, freq=cfg.PWM_HZ, duty_u16=0) for p in pair])
            self.button = machine.Pin(cfg.BUTTON_PIN, machine.Pin.IN, machine.Pin.PULL_UP)
            if not hasattr(machine, 'Encoder'):
                raise RuntimeError('Build sem machine.Encoder: nao habilitar navegacao; verificar firmware.')
            for i, (a, b) in enumerate(cfg.ENCODER_PINS):
                self.encoders.append(machine.Encoder(i, machine.Pin(a, machine.Pin.IN),
                    machine.Pin(b, machine.Pin.IN), phases=4, filter_ns=cfg.ENCODER_FILTER_NS))
            for name, (trig, echo) in cfg.SENSOR_PINS.items():
                self.sensors[name] = (machine.Pin(trig, machine.Pin.OUT, value=0),
                                      machine.Pin(echo, machine.Pin.IN))
        except BaseException:
            self.close()
            raise

    def now(self):
        return time.ticks_ms()

    def diff(self, a, b):
        return time.ticks_diff(a, b)

    def sleep(self, ms):
        time.sleep_ms(ms)

    def stop(self):
        for pair in self.pwms:
            for pwm in pair:
                pwm.duty_u16(0)

    def power(self, left, right):
        # Sempre zera o sentido oposto antes de ligar outro transistor.
        for i, requested in enumerate((left, right)):
            value = max(-cfg.MAX_PWM, min(cfg.MAX_PWM, requested)) * cfg.MOTOR_SIGNS[i]
            forward, reverse = self.pwms[i]
            if value >= 0:
                reverse.duty_u16(0)
                forward.duty_u16(round(value * 65535))
            else:
                forward.duty_u16(0)
                reverse.duty_u16(round(-value * 65535))

    def counts(self):
        return tuple(enc.value() * cfg.ENCODER_SIGNS[i] for i, enc in enumerate(self.encoders))

    def pressed(self):
        return self.button.value() == 0

    def distance(self, name):
        trig, echo = self.sensors[name]
        if self.last_ping is not None:
            wait = cfg.PING_GAP_MS - self.diff(self.now(), self.last_ping)
            if wait > 0:
                self.sleep(wait)
        self.last_ping = self.now()
        trig.value(0)
        time.sleep_us(5)
        trig.value(1)
        time.sleep_us(10)
        trig.value(0)
        try:
            pulse = machine.time_pulse_us(echo, 1, cfg.PING_TIMEOUT_US)
        except OSError:
            return None
        if pulse <= 0:
            return None
        mm = pulse * 0.343 / 2
        return round(mm) if cfg.SENSOR_MIN_MM <= mm <= cfg.SENSOR_MAX_MM else None

    def scan(self, service=lambda: None):
        # Parado: tres amostras por direcao, sem converter falha em 'infinito'.
        self.stop()
        buckets = {k: [] for k in cfg.SENSOR_PINS}
        for _ in range(3):
            for name in ('front', 'right', 'back', 'left'):
                service()
                buckets[name].append(self.distance(name))
        result = {}
        for name, samples in buckets.items():
            if any(v is None for v in samples) or max(samples) - min(samples) > cfg.SCAN_SPREAD_MM:
                result[name] = None
            else:
                result[name] = sorted(samples)[1]
        return result

    def close(self):
        for pair in self.pwms:
            for pwm in pair:
                try:
                    pwm.duty_u16(0)
                    pwm.deinit()
                except Exception:
                    pass
        self.pwms = []
        for pair in self.outputs:
            for pin in pair:
                pin.init(machine.Pin.OUT, value=0)
        for enc in self.encoders:
            enc.deinit()
        self.encoders = []
