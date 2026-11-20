"""Verifica adaptador real contra uma API machine simulada."""
import importlib
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'/'firmware'))


class Pin:
    IN=0; OUT=1; PULL_UP=2
    def __init__(self,n,mode,pull=None,value=None):
        self.n=n; self.state=1 if value is None else value
    def value(self,v=None):
        if v is not None: self.state=v
        return self.state
    def init(self,mode,value=0): self.state=value


class PWM:
    events=[]
    def __init__(self,pin,freq,duty_u16):
        self.pin=pin; self.duty=duty_u16
    def duty_u16(self,v):
        self.duty=v; self.events.append((self.pin.n,v))
    def deinit(self): self.duty=0


class Encoder:
    def __init__(self,i,a,b,**kwargs): self.v=0; self.kwargs=kwargs
    def value(self): return self.v
    def deinit(self): pass


class Clock:
    def __init__(self): self.t=0
    def ticks_ms(self): return self.t
    def ticks_diff(self,a,b): return a-b
    def sleep_ms(self,n): self.t+=n
    def sleep_us(self,n): pass


class HardwareTests(unittest.TestCase):
    def setUp(self):
        self.pulse=1000
        fake=SimpleNamespace(Pin=Pin,PWM=PWM,Encoder=Encoder,time_pulse_us=lambda *a:self.pulse)
        self.patch=patch.dict(sys.modules,{'machine':fake}); self.patch.start()
        sys.modules.pop('robot.hardware',None)
        self.mod=importlib.import_module('robot.hardware')
        self.clock=Clock(); self.mod.time=self.clock
        PWM.events=[]
        self.h=self.mod.Hardware()

    def tearDown(self):
        self.h.close(); self.patch.stop(); sys.modules.pop('robot.hardware',None)

    def test_pinout_and_encoder_phase(self):
        self.assertEqual([(a.n,b.n) for a,b in self.h.outputs],[(16,17),(18,8)])
        self.assertEqual((self.h.sensors['front'][0].n,self.h.sensors['front'][1].n),(35,36))
        self.assertTrue(all(e.kwargs['phases']==4 for e in self.h.encoders))

    def test_reverse_zeros_other_pin_first_and_caps(self):
        self.h.power(1,1)
        self.assertLessEqual(self.h.pwms[0][0].duty,32768)
        PWM.events=[]
        self.h.power(-.4,.4)
        self.assertEqual(PWM.events[0],(16,0))
        self.assertEqual(PWM.events[1][0],17)

    def test_invalid_pulse_and_range(self):
        for pulse in (-2,-1,0,1,30000):
            self.pulse=pulse
            self.assertIsNone(self.h.distance('front'))

    def test_ping_spacing_across_sensors(self):
        self.h.distance('front'); self.h.distance('right')
        self.assertGreaterEqual(self.clock.t,65)

    def test_scan_median_and_invalid(self):
        self.assertEqual(self.h.scan()['front'],172)
        self.pulse=-1
        self.assertIsNone(self.h.scan()['front'])

    def test_scan_stops_motors(self):
        self.h.power(.4,.4); self.h.scan()
        self.assertTrue(all(p.duty==0 for pair in self.h.pwms for p in pair))


if __name__=='__main__': unittest.main()
