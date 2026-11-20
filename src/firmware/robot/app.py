"""Aplicacao: sempre partida explicita, sem acesso a rede no controle."""
from . import config
from .control import Motion, Halt
from .planner import Explorer, patrol_choice, classify


class Robot:
    def __init__(self, hw, cfg=config, log=print, feed=lambda: None):
        self.hw, self.cfg, self.log, self.feed = hw, cfg, log, feed
        self.state = 'IDLE'
        self.reason = None
        self.started = None
        self.motion = Motion(hw, cfg, self.service)
        self.explorer = None
        self.hw.stop()

    def service(self):
        if self.hw.pressed():
            raise Halt('BUTTON_STOP')
        if self.started is not None and self.hw.diff(self.hw.now(), self.started) >= self.cfg.RUN_TIMEOUT_MS:
            raise Halt('RUN_TIMEOUT')
        self.feed()

    def sensors(self):
        self.hw.stop()
        return self.hw.scan(self.service)

    def run(self, mode=None):
        self.hw.stop()
        self.started = None
        self.reason = None
        self.state = 'IDLE'
        mode = self.cfg.MODE if mode is None else mode
        try:
            self.cfg.validate_motion()
            if mode not in ('patrol', 'explore'):
                raise ValueError('Modo deve ser patrol ou explore.')
            if mode == 'explore':
                self.cfg.validate_grid()
            self.started = self.hw.now()
            self.service()
            scan = self.hw.scan(self.service)
            if any(v is None for v in scan.values()):
                raise Halt('SENSOR_INVALID')
            self.explorer = Explorer(self.cfg.MAX_CELLS, self.cfg.GOAL_CELL) if mode == 'explore' else None
            self.state = 'RUNNING'
            for action_no in range(self.cfg.MAX_ACTIONS):
                self.service()
                self.log('SCAN', action_no, scan)
                if mode == 'patrol':
                    choice = patrol_choice(scan, self.cfg.START_CLEARANCE_MM,
                                           self.cfg.TURN_CLEARANCE_MM)
                    if choice in ('FAULT', 'BLOCKED'):
                        raise Halt(choice)
                    if choice == 'FORWARD':
                        self.motion.forward(self.cfg.STEP_MM)
                    else:
                        self.motion.turn({'RIGHT': 1, 'BACK': 2, 'LEFT': 3}[choice])
                else:
                    openings = classify(scan, self.cfg.WALL_MM, self.cfg.WALL_HYST_MM)
                    status, relative = self.explorer.choose(openings)
                    if status in ('GOAL', 'EXPLORED'):
                        self.state, self.reason = 'FINISHED', status
                        return status
                    if status != 'MOVE':
                        raise Halt(status)
                    self.motion.turn(relative)
                    self.motion.forward(self.cfg.CELL_MM)
                    self.explorer.commit()
                    self.log('POSE', self.explorer.pos, self.explorer.heading)
                self.hw.stop()
                self.hw.sleep(self.cfg.SETTLE_MS)
                scan = self.hw.scan(self.service)
                if any(v is None for v in scan.values()):
                    raise Halt('SENSOR_INVALID')
            raise Halt('ACTION_LIMIT')
        except Halt as exc:
            self.reason = str(exc)
            self.state = 'STOPPED' if self.reason in ('BUTTON_STOP', 'RUN_TIMEOUT', 'ACTION_LIMIT') else 'FAULT'
            return self.reason
        except Exception as exc:
            self.state, self.reason = 'FAULT', str(exc)
            return self.reason
        except BaseException:
            self.state, self.reason = 'STOPPED', 'INTERRUPTED'
            raise
        finally:
            self.hw.stop()
            self.started = None
            if self.explorer is not None:
                self.explorer.abort()
            self.log('STATE', self.state, self.reason)

    def pulse(self, left=0, right=0, duration_ms=200, wheels_lifted=False):
        """Somente bancada: observacao de sentido e calibracao, nao navegacao."""
        self.hw.stop()
        if not wheels_lifted:
            raise ValueError('Pulso de bancada exige rodas suspensas.')
        if not 0 < duration_ms <= 300 or max(abs(left), abs(right)) > self.cfg.MAX_PWM:
            raise ValueError('Limite de bancada: 300ms e MAX_PWM.')
        start = self.hw.now()
        before = self.hw.counts()
        try:
            self.service()
            self.hw.power(left, right)
            while self.hw.diff(self.hw.now(), start) < duration_ms:
                self.service()
                self.hw.sleep(min(10, duration_ms-self.hw.diff(self.hw.now(),start)))
        finally:
            self.hw.stop()
        after = self.hw.counts()
        return tuple(after[i] - before[i] for i in (0, 1))

    def jog(self, direction='forward', duration_ms=150):
        """Pulso supervisionado de calibracao NO CHAO, chassi ja estavel.

        Nao exige contagens/mm ainda desconhecidas. Limite rigido de 300ms,
        pre-leitura, monitoramento de distancia e comando manual por pulso.
        """
        h,c=self.hw,self.cfg
        h.stop()
        if not c.STABLE_CHASSIS:
            raise ValueError('Corrigir estabilidade antes de calibrar no chao.')
        if direction not in ('forward','right','left') or not 0<duration_ms<=300:
            raise ValueError('Direcao ou duracao invalida.')
        guard='front' if direction=='forward' else 'turn'
        try:
            scan=h.scan(self.service)
            if any(v is None for v in scan.values()):
                raise Halt('SENSOR_INVALID')
            if guard=='front' and scan['front']<=c.START_CLEARANCE_MM:
                raise Halt('FRONT_OBSTACLE')
            if guard=='turn' and (c.TURN_CLEARANCE_MM is None or min(scan.values())<=c.TURN_CLEARANCE_MM):
                raise Halt('TURN_CLEARANCE')
            signs={'forward':(1,1),'right':(1,-1),'left':(-1,1)}[direction]
            power=min(c.MAX_PWM,c.DRIVE_PWM if guard=='front' else c.TURN_PWM)
            before=h.counts()
            start=h.now()
            last_ping=start
            self.service()
            h.power(signs[0]*power,signs[1]*power)
            while h.diff(h.now(),start)<duration_ms:
                self.service()
                remaining=duration_ms-h.diff(h.now(),start)
                # Nao iniciar leitura bloqueante perto do fim do pulso.
                if remaining<=c.PING_GAP_MS+25:
                    h.sleep(min(10,remaining))
                    continue
                if h.diff(h.now(),last_ping)>=c.PING_GAP_MS:
                    self.motion._guard(guard)
                    last_ping=h.now()
                h.sleep(10)
        finally:
            h.stop()
        h.sleep(c.SETTLE_MS)
        after=h.counts()
        return tuple(after[i]-before[i] for i in (0,1))


def connect():
    from .hardware import Hardware
    return Robot(Hardware())


def standalone():
    """BOOT pressionado por 2s e solto inicia. Qualquer pressao durante run para.

    Exige nova pressao completa depois de qualquer parada/reset. Nao existe
    retomada automatica. Um watchdog reinicia para estado parado.
    """
    import machine
    robot = connect()
    wdt = machine.WDT(timeout=config.WATCHDOG_MS)
    robot.feed = wdt.feed
    h = robot.hw
    print('PARADO. Calibrar antes. BOOT por 2s e soltar inicia; BOOT para.')
    # Ignora botao que ja estava pressionado no inicio.
    while h.pressed():
        h.stop(); wdt.feed(); h.sleep(20)
    held = None
    try:
        while True:
            h.stop()
            wdt.feed()
            if h.pressed():
                if held is None:
                    held = h.now()
            elif held is not None:
                duration = h.diff(h.now(), held)
                held = None
                if duration >= 2000:
                    robot.run()
                    # O botao usado para parar nao pode iniciar outra corrida.
                    while h.pressed():
                        wdt.feed(); h.sleep(20)
            h.sleep(20)
    finally:
        h.close()
