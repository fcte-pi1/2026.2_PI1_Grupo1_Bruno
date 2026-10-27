
IDLE = "IDLE"
READY = "READY"
RUNNING = "RUNNING"
STOPPED = "STOPPED"
FINISHED = "FINISHED"
FAULT = "FAULT"

EV_START = "START"
EV_STOP = "STOP"
EV_GOAL = "GOAL"
EV_REARM = "REARM"
EV_ACK_FAULT = "ACK_FAULT"

#Causas de falha
F_BOOT = "BOOT"
F_WDT_RESET = "WDT_RESET"
F_EXCEPTION = "EXCEPTION"
F_FRONT_CRITICAL = "FRONT_CRITICAL"
F_SENSOR_INVALID = "SENSOR_INVALID"
F_STALL = "STALL"
F_RUN_TIMEOUT = "RUN_TIMEOUT"

#Causas de parada
S_BUTTON = "BUTTON"
S_REMOTE = "REMOTE"
S_CMD_TIMEOUT = "CMD_TIMEOUT"

MODE_LOCAL = "LOCAL"
MODE_REMOTE = "REMOTE"

TRANSITIONS = {
    (IDLE, "ARM"): READY,
    (READY, EV_START): RUNNING,
    (RUNNING, EV_STOP): STOPPED,
    (RUNNING, EV_GOAL): FINISHED,
    (STOPPED, EV_REARM): READY,
    (FINISHED, EV_REARM): READY,
    (FAULT, EV_ACK_FAULT): IDLE,
}

_TICKS_PERIOD = 1 << 30
_TICKS_HALF = _TICKS_PERIOD >> 1


def ticks_diff(a, b):
    d = (a - b) & (_TICKS_PERIOD - 1)
    if d >= _TICKS_HALF:
        d -= _TICKS_PERIOD
    return d


class Config:
    #Limiares provisorios -> Calibrados no robô montado
    def __init__(self, front_critical_mm=40, sensor_timeout_ms=200,
                 stall_ms=400, run_timeout_ms=120000, cmd_timeout_ms=500,
                 loop_max_ms=100):
        self.front_critical_mm = front_critical_mm
        self.sensor_timeout_ms = sensor_timeout_ms
        self.stall_ms = stall_ms
        self.run_timeout_ms = run_timeout_ms
        self.cmd_timeout_ms = cmd_timeout_ms
        self.loop_max_ms = loop_max_ms


class MouseFSM:
    def __init__(self, motors, clock_ms, clock_us=None, self_check=None,
                 cfg=None, reset_was_wdt=False, on_transition=None):
        self._motors = motors
        self._ms = clock_ms
        self._us = clock_us
        self._self_check = self_check
        self._on_transition = on_transition
        self.cfg = cfg if cfg is not None else Config()

        self.state = IDLE
        self.mode = MODE_LOCAL
        self.fault_cause = None
        self.fault_detail = None
        self.stop_cause = None
        self.last_stop_latency_us = None

        now = self._ms()
        self._last_update = None
        self._loop_ok = True
        self._run_start = now
        self._last_front_ok = now
        self._last_motion = now
        self._last_cmd = now

        if not self._halt():
            self._enter_fault(F_BOOT, "motors.stop() falhou no boot")
        elif reset_was_wdt:
            self._enter_fault(F_WDT_RESET, None)

    @property
    def allows_motion(self):
        return self.state == RUNNING

    def health_ok(self):
        return self._loop_ok

    def _halt(self):
        try:
            self._motors.stop()
            return True
        except Exception:
            return False

    def _elapsed_us(self, t0):
        if self._us is None:
            return None
        return ticks_diff(self._us(), t0)

    def _t0(self):
        return self._us() if self._us is not None else None

    def _set_state(self, new, cause=None):
        old = self.state
        self.state = new
        if self._on_transition is not None:
            try:
                self._on_transition(old, new, cause)
            except Exception:
                pass

    def _enter_fault(self, cause, detail):
        self.fault_cause = cause
        self.fault_detail = detail
        self._set_state(FAULT, cause)

    def fault(self, cause, detail=None):
        if self.state == FAULT:
            return
        t0 = self._t0()
        self._halt()
        self.last_stop_latency_us = self._elapsed_us(t0) if t0 is not None else None
        self._enter_fault(cause, detail)

    def guarded(self, fn, *args):
        try:
            return fn(*args)
        except Exception as e:
            self.fault(F_EXCEPTION, repr(e))
            return None

    def handle(self, event, cause=None):
        new = TRANSITIONS.get((self.state, event))
        if new is None:
            return False
        if new == RUNNING:
            now = self._ms()
            self._run_start = now
            self._last_front_ok = now
            self._last_motion = now
            self._last_cmd = now
            self.stop_cause = None
            self._set_state(RUNNING, cause)
            return True
        t0 = self._t0()
        self._halt()
        if self.state == RUNNING:
            self.last_stop_latency_us = (
                self._elapsed_us(t0) if t0 is not None else None)
        if new == IDLE:
            self.fault_cause = None
            self.fault_detail = None
        if new == STOPPED:
            self.stop_cause = cause
        self._set_state(new, cause)
        return True

    def on_button(self):
        s = self.state
        if s == READY:
            return self.handle(EV_START, S_BUTTON)
        if s == RUNNING:
            return self.handle(EV_STOP, S_BUTTON)
        if s in (STOPPED, FINISHED):
            return self.handle(EV_REARM, S_BUTTON)
        if s == FAULT:
            return self.handle(EV_ACK_FAULT, S_BUTTON)
        return False

    def goal_reached(self):
        return self.handle(EV_GOAL)

    def set_mode(self, mode):
        self.mode = mode
        self._last_cmd = self._ms()

    def command_heartbeat(self):
        self._last_cmd = self._ms()

    def remote_command(self, event):
        if self.mode != MODE_REMOTE:
            return False
        self.command_heartbeat()
        return self.handle(event, S_REMOTE)

    def _try_arm(self):
        ok = True
        if self._self_check is not None:
            try:
                ok = bool(self._self_check())
            except Exception as e:
                self.fault(F_EXCEPTION, repr(e))
                return
        if ok:
            self.handle("ARM")

    def update(self, front_mm=None, motion_commanded=False, enc_moved=False):
        now = self._ms()
        if self._last_update is None:
            period = 0
        else:
            period = ticks_diff(now, self._last_update)
        self._last_update = now
        self._loop_ok = period <= self.cfg.loop_max_ms

        s = self.state
        if s == IDLE:
            self._try_arm()
            return
        if s != RUNNING:
            return

        cfg = self.cfg
        if front_mm is None:
            if ticks_diff(now, self._last_front_ok) > cfg.sensor_timeout_ms:
                self.fault(F_SENSOR_INVALID)
                return
        else:
            self._last_front_ok = now
            if front_mm < cfg.front_critical_mm:
                self.fault(F_FRONT_CRITICAL, str(front_mm))
                return

        if enc_moved or not motion_commanded:
            self._last_motion = now
        elif ticks_diff(now, self._last_motion) > cfg.stall_ms:
            self.fault(F_STALL)
            return

        if ticks_diff(now, self._run_start) > cfg.run_timeout_ms:
            self.fault(F_RUN_TIMEOUT)
            return

        if self.mode == MODE_REMOTE:
            if ticks_diff(now, self._last_cmd) > cfg.cmd_timeout_ms:
                self.handle(EV_STOP, S_CMD_TIMEOUT)