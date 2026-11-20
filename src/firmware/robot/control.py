"""Movimento limitado, com interfaces injetaveis para teste no computador."""


class Halt(Exception):
    pass


class Motion:
    def __init__(self, hw, cfg, service=lambda: None):
        self.hw, self.cfg, self.service = hw, cfg, service

    def _check(self):
        self.service()  # botao, watchdog e prazo global, inclusive em scans

    def move(self, targets, signs, pwm, guard):
        """Contagens assinadas esperadas por roda; nunca usa tempo como odometria."""
        h, c = self.hw, self.cfg
        h.stop()
        start = h.now()
        initial = h.counts()
        last_counts = [0, 0]
        last_change = [start, start]
        last_guard = start
        active_pwm = 0.0
        previous_time = start
        try:
            self._check()
            self._guard(guard)
            while True:
                self._check()
                now = h.now()
                if h.diff(now, start) >= c.MOVE_TIMEOUT_MS:
                    raise Halt('MOVE_TIMEOUT')
                counts = h.counts()
                progress = [(counts[i] - initial[i]) * signs[i] for i in (0, 1)]
                if any(v < -4 for v in progress):
                    raise Halt('ENCODER_DIRECTION')
                done = [progress[i] >= targets[i] for i in (0, 1)]
                if all(done):
                    return progress
                if h.diff(now, last_guard) >= c.PING_GAP_MS:
                    self._guard(guard)
                    last_guard = h.now()
                    now = h.now()
                for i in (0, 1):
                    if progress[i] != last_counts[i]:
                        last_counts[i] = progress[i]
                        last_change[i] = now
                    # A rampa precisa atingir o PWM de trabalho antes de julgar
                    # uma roda que ainda nao venceu o atrito estatico.
                    grace = int(1000 * pwm / c.RAMP_PER_SECOND) if progress[i] == 0 else 0
                    if not done[i] and h.diff(now, last_change[i]) >= c.STALL_MS + grace:
                        raise Halt('STALL_' + str(i))
                dt = max(0, h.diff(now, previous_time)) / 1000
                previous_time = now
                active_pwm = min(pwm, active_pwm + c.RAMP_PER_SECOND * dt)
                # Progresso normalizado: permite rodas com contagens/mm diferentes.
                error = (progress[0] / targets[0] - progress[1] / targets[1])
                correction = max(-c.MAX_BALANCE, min(c.MAX_BALANCE,
                                 error * min(targets) * c.BALANCE_KP))
                powers = (active_pwm - correction, active_pwm + correction)
                h.power(*[0 if done[i] else signs[i] * max(0, min(pwm, powers[i]))
                          for i in (0, 1)])
                h.sleep(10)
        finally:
            h.stop()

    def _guard(self, mode):
        c = self.cfg
        if mode == 'front':
            d = self.hw.distance('front')
            self._check()
            if d is None:
                raise Halt('FRONT_INVALID')
            if d <= c.FRONT_STOP_MM:
                raise Halt('FRONT_OBSTACLE')
        elif mode == 'turn':
            # Durante giro, monitora frente/tras alternadamente; folga de varredura
            # exige scan dos QUATRO lados antes de ligar os motores.
            name = getattr(self, '_turn_sensor', 'front')
            self._turn_sensor = 'back' if name == 'front' else 'front'
            d = self.hw.distance(name)
            self._check()
            if d is None or d <= c.TURN_CLEARANCE_MM:
                raise Halt('TURN_CLEARANCE')
        else:
            raise ValueError('Modo de protecao invalido.')

    def forward(self, mm):
        c = self.cfg
        if mm <= 0:
            raise ValueError('Distancia deve ser positiva.')
        return self.move(tuple(max(1, round(mm * v)) for v in c.COUNTS_PER_MM),
                         (1, 1), c.DRIVE_PWM, 'front')

    def turn(self, relative):
        if relative not in (0, 1, 2, 3):
            raise ValueError('Giro invalido.')
        if relative == 0:
            return
        c = self.cfg
        scan = self.hw.scan(self._check)
        if any(d is None or d <= c.TURN_CLEARANCE_MM for d in scan.values()):
            raise Halt('TURN_CLEARANCE')
        factor = 2 if relative == 2 else 1
        signs = (-1, 1) if relative == 3 else (1, -1)
        return self.move(tuple(round(v * factor) for v in c.TURN_90_COUNTS),
                         signs, c.TURN_PWM, 'turn')
