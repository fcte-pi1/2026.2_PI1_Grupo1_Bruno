"""Adaptador CONDICIONAL: duas entradas de sentido + PWM por roda e enable comum.

TODO(INT02/#22): confirmar se o driver real oferece esta interface. Se nao,
implementar outro adaptador write/enable/disable; nao adaptar ligacoes por palpite.
Tabela verdade, GPIOs, polaridade de enable e frequencia vem da configuracao.
"""

from robo.controle.motores import numero


def validar(config):
    if not isinstance(config, dict) or config.get('confirmado') is not True:
        raise ValueError('hardware nao confirmado: pendente INT02/#22')
    for campo in ('placa', 'driver', 'fonte_tabela', 'comportamento_desabilitado'):
        if not isinstance(config.get(campo), str) or not config[campo].strip():
            raise ValueError('documentar ' + campo)
    if config.get('interface') != '2in_pwm_enable':
        raise ValueError('interface nao suportada por este adaptador')
    pinos = [config['enable_gpio']]
    for lado in ('esquerda', 'direita'):
        pinos.extend(config[lado])
        if len(config[lado]) != 3:
            raise ValueError('cada roda exige (in1, in2, pwm)')
    if any(type(p) is not int or p < 0 for p in pinos) or len(set(pinos)) != 7:
        raise ValueError('GPIOs devem ser inteiros distintos')
    if any(p not in config['gpios_saida_aprovados'] for p in pinos):
        raise ValueError('GPIO nao aprovado para saida na placa exata')
    if type(config['enable_ativo']) is not int or config['enable_ativo'] not in (0, 1):
        raise ValueError('enable_ativo deve ser 0 ou 1')
    if type(config['pwm_hz']) is not int or config['pwm_hz'] <= 0:
        raise ValueError('pwm_hz deve ser inteiro positivo')
    tabela = config['tabela']
    for estado in ('frente', 're', 'zero'):
        par = tabela[estado]
        if len(par) != 2 or any(type(v) is not int or v not in (0, 1) for v in par):
            raise ValueError('tabela verdade invalida')
    if tuple(tabela['frente']) == tuple(tabela['re']):
        raise ValueError('frente e re devem ser diferentes')


class PontePWM:
    def __init__(self, config, machine_module=None):
        validar(config)  # Nenhum GPIO e tocado com configuracao incompleta.
        if machine_module is None:
            import machine as machine_module
        self._ativo = config['enable_ativo']
        self._tabela = {k: tuple(config['tabela'][k]) for k in ('frente', 're', 'zero')}
        self._rodas = []
        self.habilitado = False
        Pin, PWM = machine_module.Pin, machine_module.PWM
        self._enable = Pin(config['enable_gpio'], Pin.OUT, value=1 - self._ativo)
        try:
            for lado in ('esquerda', 'direita'):
                a, b, pwm = config[lado]
                in1 = Pin(a, Pin.OUT, value=self._tabela['zero'][0])
                in2 = Pin(b, Pin.OUT, value=self._tabela['zero'][1])
                saida = PWM(Pin(pwm, Pin.OUT, value=0), freq=config['pwm_hz'], duty_u16=0)
                self._rodas.append((in1, in2, saida))
        except BaseException:
            self.disable()
            for _, _, pwm in self._rodas:
                pwm.deinit()
            raise

    def enable(self):
        # Chamado pelo controlador somente apos write(0, 0).
        self._enable.value(self._ativo)
        self.habilitado = True

    def disable(self):
        self.habilitado = False
        erro = None
        # Tenta desabilitar enable e AMBOS os PWMs mesmo se um acesso falhar.
        operacoes = [(self._enable.value, 1 - self._ativo)]
        for _, _, pwm in self._rodas:
            operacoes.append((pwm.duty_u16, 0))
        for operacao, valor in operacoes:
            try:
                operacao(valor)
            except BaseException as exc:
                if erro is None:
                    erro = exc
        if erro is not None:
            raise erro

    def write(self, left, right):
        try:
            valores = (numero(left), numero(right))
            if any(abs(v) > 1 for v in valores):
                raise ValueError('duty fora de [-1, 1]')
            if not self.habilitado and any(valores):
                raise RuntimeError('ponte desabilitada')
            for (a, b, pwm), valor in zip(self._rodas, valores):
                estado = 'frente' if valor > 0 else 're' if valor < 0 else 'zero'
                # PWM zerado antes de qualquer mudanca de sentido.
                pwm.duty_u16(0)
                a.value(self._tabela[estado][0])
                b.value(self._tabela[estado][1])
                pwm.duty_u16(round(abs(valor) * 65535))
        except BaseException:
            self.disable()
            raise
