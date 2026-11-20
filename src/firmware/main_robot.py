"""Copiar como main.py SOMENTE na instalacao final. Nunca inicia movimento no boot."""
from machine import Pin

# Zera saidas antes de importar/configurar os demais modulos.
_motor_pins = [Pin(n, Pin.OUT, value=0) for n in (16, 17, 18, 8)]
try:
    from robot.app import standalone
    standalone()
finally:
    for _pin in _motor_pins:
        _pin.init(Pin.OUT, value=0)
