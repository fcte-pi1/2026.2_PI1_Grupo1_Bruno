
import time
from machine import Pin, disable_irq, enable_irq


class Button:
    def __init__(self, pin_no, debounce_ms=50, active_low=True):
        pull = Pin.PULL_UP if active_low else Pin.PULL_DOWN
        self._pin = Pin(pin_no, Pin.IN, pull)
        self._debounce_ms = debounce_ms
        self._last = time.ticks_add(time.ticks_ms(), -debounce_ms)
        self.pressed = False
        trigger = Pin.IRQ_FALLING if active_low else Pin.IRQ_RISING
        self._pin.irq(trigger=trigger, handler=self._isr)

    def _isr(self, pin):
        now = time.ticks_ms()
        if time.ticks_diff(now, self._last) >= self._debounce_ms:
            self._last = now
            self.pressed = True

    def consume(self):
        state = disable_irq()
        was_pressed = self.pressed
        self.pressed = False
        enable_irq(state)
        return was_pressed