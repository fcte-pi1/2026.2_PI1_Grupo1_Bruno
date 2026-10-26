import importlib
import os
import sys
import types
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class FakeTime(types.ModuleType):

    def __init__(self):
        super().__init__("time")
        self.now = 100000

    def ticks_ms(self):
        return self.now

    def ticks_add(self, a, b):
        return a + b

    def ticks_diff(self, a, b):
        return a - b


class FakePin:
    IN = 0
    PULL_UP = 1
    PULL_DOWN = 2
    IRQ_FALLING = 4
    IRQ_RISING = 8
    last = None

    def __init__(self, no, mode=None, pull=None):
        self.no = no
        self.mode = mode
        self.pull = pull
        self.trigger = None
        self.handler = None
        FakePin.last = self

    def irq(self, trigger=None, handler=None):
        self.trigger = trigger
        self.handler = handler

    def fire(self):
        self.handler(self)


def fake_machine():
    m = types.ModuleType("machine")
    m.Pin = FakePin
    m.disable_irq = lambda: 0
    m.enable_irq = lambda state: None
    return m


class TestButton(unittest.TestCase):
    def setUp(self):
        self.clock = FakeTime()
        patcher = mock.patch.dict(
            sys.modules, {"time": self.clock, "machine": fake_machine()})
        patcher.start()
        self.addCleanup(patcher.stop)
        sys.modules.pop("button", None)
        self.button = importlib.import_module("button")
        self.addCleanup(sys.modules.pop, "button", None)

    def make(self, **kw):
        b = self.button.Button(7, **kw)
        return b, FakePin.last

    def test_configuracao_ativa_em_nivel_baixo(self):
        b, pin = self.make()
        self.assertEqual(pin.pull, FakePin.PULL_UP)
        self.assertEqual(pin.trigger, FakePin.IRQ_FALLING)

    def test_configuracao_ativa_em_nivel_alto(self):
        b, pin = self.make(active_low=False)
        self.assertEqual(pin.pull, FakePin.PULL_DOWN)
        self.assertEqual(pin.trigger, FakePin.IRQ_RISING)

    def test_um_acionamento_gera_um_evento(self):
        b, pin = self.make()
        pin.fire()
        self.assertTrue(b.consume())
        self.assertFalse(b.consume())

    def test_primeiro_acionamento_apos_criacao_nao_e_descartado(self):
        b, pin = self.make()
        pin.fire()
        self.assertTrue(b.pressed)

    def test_repique_dentro_da_janela_conta_uma_vez(self):
        b, pin = self.make(debounce_ms=50)
        pin.fire()
        for dt in (2, 3, 5, 10):
            self.clock.now += dt
            pin.fire()
        self.assertTrue(b.consume())
        self.assertFalse(b.consume())

    def test_dois_acionamentos_separados_geram_dois_eventos(self):
        b, pin = self.make(debounce_ms=50)
        pin.fire()
        self.assertTrue(b.consume())
        self.clock.now += 200
        pin.fire()
        self.assertTrue(b.consume())

    def test_repique_apos_consumir_ainda_e_ignorado(self):
        b, pin = self.make(debounce_ms=50)
        pin.fire()
        self.assertTrue(b.consume())
        self.clock.now += 20
        pin.fire()
        self.assertFalse(b.consume())

    def test_rotina_de_interrupcao_so_marca_flag(self):
        b, pin = self.make()
        pin.fire()
        self.assertIs(b.pressed, True)


if __name__ == "__main__":
    unittest.main()