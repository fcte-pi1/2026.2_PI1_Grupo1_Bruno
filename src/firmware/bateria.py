"""FW14: tensão por divisor/ADC e decisão local para alimentação do robô.

O adaptador fornece microvolts no pino do ADC. Não mede corrente nem carga.
Nenhuma dependência de machine ou do aplicativo de telemetria é necessária.
"""

from math import isfinite


def _numero(valor):
    return (not isinstance(valor, bool)
            and isinstance(valor, (int, float)) and isfinite(valor))


def _positivo(valor, nome):
    if not _numero(valor) or valor <= 0:
        raise ValueError(nome + " deve ser positivo e finito")
    return valor


class ConfiguracaoBateria:
    """Parâmetros físicos obrigatórios, a confirmar com Energia.

    r_superior fica entre bateria e ADC; r_inferior entre ADC e GND.
    Limites são do pacote inteiro, não de uma célula isolada.
    """

    def __init__(self, r_superior_ohm, r_inferior_ohm, adc_max_uv,
                 tensao_max_v, tensao_baixa_v, tensao_retomada_v,
                 ganho=1.0, offset_v=0.0):
        superior = _positivo(r_superior_ohm, "resistor superior")
        inferior = _positivo(r_inferior_ohm, "resistor inferior")
        self.fator_divisor = 1 + superior / inferior
        self.adc_max_uv = _positivo(adc_max_uv, "limite ADC")
        self.tensao_max_v = _positivo(tensao_max_v, "tensao maxima")
        self.tensao_baixa_v = _positivo(tensao_baixa_v, "limiar de baixa")
        self.tensao_retomada_v = _positivo(tensao_retomada_v, "limiar de retomada")
        self.ganho = _positivo(ganho, "ganho")
        if not _numero(offset_v):
            raise ValueError("offset deve ser finito")
        self.offset_v = offset_v
        if not self.tensao_baixa_v < self.tensao_retomada_v <= self.tensao_max_v:
            raise ValueError("exige baixa < retomada <= maxima")
        if not isfinite(self.fator_divisor):
            raise ValueError("fator do divisor fora da faixa numerica")
        # A faixa calibrada precisa cobrir o máximo esperado sem saturar.
        capacidade = (self.adc_max_uv / 1_000_000
                      * self.fator_divisor * self.ganho + self.offset_v)
        if not isfinite(capacidade) or capacidade <= self.tensao_max_v:
            raise ValueError("divisor/ADC sem margem para a tensao maxima")


class LeituraBateria:
    def __init__(self, tensao_v, origem, estado):
        self.tensao_v = tensao_v
        self.origem = origem
        self.estado = estado
        self.valida = tensao_v is not None
        self.solicitar_parada = estado != "normal"

    def telemetria(self):
        """Valor do campo battery_voltage do contrato atual da telemetria."""
        return {"value": self.tensao_v, "unit": "V",
                "source": self.origem, "valid": self.valida}


class MonitorBateria:
    """Lê uma fonte síncrona que retorna microvolts ou None quando ausente.

    Sem fonte ou sem configuração: indisponível e parada solicitada. OSError
    indica falha de aquisição; erros de programação do adaptador propagam.
    A máquina de estados deve aplicar solicitar_parada; não há GPIOs aqui.
    """

    def __init__(self, configuracao=None, ler_uv=None, origem="measured"):
        if origem not in ("measured", "simulated"):
            raise ValueError("origem deve ser measured ou simulated")
        if configuracao is not None and not isinstance(configuracao, ConfiguracaoBateria):
            raise ValueError("configuracao deve ser ConfiguracaoBateria ou None")
        if ler_uv is not None and not callable(ler_uv):
            raise ValueError("ler_uv deve ser uma funcao ou None")
        self.configuracao = configuracao
        self.ler_uv = ler_uv
        self.origem = origem
        self._baixa = False

    def _invalida(self, estado):
        # Mantém o bloqueio de baixa tensão após uma perda de leitura.
        return LeituraBateria(None, self.origem, estado)

    def ler(self):
        config = self.configuracao
        if config is None or self.ler_uv is None:
            return self._invalida("indisponivel")
        try:
            uv = self.ler_uv()
        except OSError:
            return self._invalida("erro_sensor")
        if uv is None:
            return self._invalida("indisponivel")
        if not _numero(uv) or uv <= 0 or uv >= config.adc_max_uv:
            return self._invalida("incoerente")
        tensao = (uv * config.fator_divisor
                  * config.ganho / 1_000_000 + config.offset_v)
        if not isfinite(tensao) or tensao <= 0 or tensao > config.tensao_max_v:
            return self._invalida("incoerente")
        if tensao <= config.tensao_baixa_v:
            self._baixa = True
        elif tensao >= config.tensao_retomada_v:
            self._baixa = False
        return LeituraBateria(tensao, self.origem, "baixa" if self._baixa else "normal")
