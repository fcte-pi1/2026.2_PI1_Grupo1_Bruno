from telemetria.modelos import Leitura

ROTULO_ORIGEM = {
    "simulated": "simulado",
    "measured": "medido",
    "estimated": "estimado",
}

COR_ORIGEM = {
    "simulated": "orange",
    "measured": "green",
    "estimated": "blue",
}

INDISPONIVEL = "indisponível"
SEM_LEITURA = "sem leitura"
INVALIDA = "inválida"


def valor_numerico(leitura: Leitura | None) -> float | None:
    if leitura is None or not leitura.valid:
        return None
    return leitura.value


def texto_leitura(leitura: Leitura | None, casas: int = 1) -> str:
    if leitura is None:
        return INDISPONIVEL
    if not leitura.valid:
        return INVALIDA
    if leitura.value is None:
        return SEM_LEITURA
    return f"{leitura.value:.{casas}f} {leitura.unit}"


def texto_origem(leitura: Leitura | None) -> str:
    if leitura is None:
        return ""
    return ROTULO_ORIGEM[leitura.source]


def cor_origem(leitura: Leitura | None) -> str:
    if leitura is None:
        return "grey"
    return COR_ORIGEM[leitura.source]


def texto_tempo(t_ms: int) -> str:
    minutos, resto = divmod(t_ms // 1000, 60)
    return f"{minutos:02d}:{resto:02d}.{(t_ms % 1000) // 100}"
