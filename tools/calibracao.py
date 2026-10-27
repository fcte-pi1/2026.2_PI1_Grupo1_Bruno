"""INT05: análise offline de medições; não controla nem configura o robô."""

import argparse
import csv
import json
import math
import statistics
from collections import defaultdict


def numero(valor, campo, minimo=None):
    try:
        resultado = float(valor)
    except (TypeError, ValueError) as erro:
        raise ValueError(f"{campo}: esperado numero") from erro
    if not math.isfinite(resultado) or (minimo is not None and resultado < minimo):
        raise ValueError(f"{campo}: valor fora da faixa")
    return resultado


def contador(valor, campo):
    resultado = numero(valor, campo, 0)
    if not resultado.is_integer():
        raise ValueError(f"{campo}: esperado inteiro nao negativo")
    return int(resultado)


def opcional(valor, campo, minimo=0):
    return None if valor is None or str(valor).strip() == "" else numero(valor, campo, minimo)


def ler_csv(caminho, campos):
    with open(caminho, encoding="utf-8-sig", newline="") as arquivo:
        leitor = csv.DictReader(arquivo)
        if leitor.fieldnames is None or set(leitor.fieldnames) != set(campos):
            raise ValueError("cabecalho esperado: " + ",".join(campos))
        if len(leitor.fieldnames) != len(campos):
            raise ValueError("colunas duplicadas")
        linhas = list(leitor)
        if any(None in linha or any(v is None for v in linha.values()) for linha in linhas):
            raise ValueError("linha com quantidade incorreta de colunas")
        return linhas


def diametro_por_volta(distancia_mm, contagens, contagens_por_volta):
    """Distância medida externamente e pulsos de UMA roda; resultado em mm."""
    distancia = numero(distancia_mm, "distancia_mm", 0)
    pulsos = abs(numero(contagens, "contagens"))
    escala = numero(contagens_por_volta, "contagens_por_volta", 0)
    if distancia == 0 or pulsos == 0 or escala == 0:
        raise ValueError("calibracao exige distancia, contagens e escala nao nulas")
    return distancia * escala / (math.pi * pulsos)


def distancia_rodas_corrigida(atual_mm, angulo_odometria_graus, angulo_referencia_graus):
    atual = numero(atual_mm, "distancia atual", 0)
    odometria = numero(angulo_odometria_graus, "angulo odometria")
    referencia = numero(angulo_referencia_graus, "angulo referencia")
    if atual == 0 or odometria * referencia <= 0:
        raise ValueError("exige distancia positiva e angulos nao nulos com mesmo sinal")
    return atual * odometria / referencia


CAMPOS_MOVIMENTO = ("origem", "tipo", "controle", "alvo", "medido",
                    "desvio_mm", "colisoes", "resultado")
CAMPOS_AUTONOMIA = ("t_s", "origem", "estado", "tensao_v", "corrente_a",
                   "temperatura_c", "resets", "quedas_link")


def analisar_movimentos(linhas, tolerancia_reta_mm, tolerancia_giro_graus, desvio_max_mm):
    tolerancias = {"reta": numero(tolerancia_reta_mm, "tolerancia reta", 0),
                   "giro": numero(tolerancia_giro_graus, "tolerancia giro", 0)}
    desvio_max = numero(desvio_max_mm, "desvio maximo", 0)
    grupos = defaultdict(list)
    for indice, linha in enumerate(linhas, start=2):
        try:
            origem, tipo, controle = linha["origem"], linha["tipo"], linha["controle"]
            if origem not in ("measured", "simulated") or tipo not in tolerancias:
                raise ValueError("origem/tipo invalido")
            if controle not in ("com_correcao", "sem_correcao"):
                raise ValueError("controle invalido")
            if linha["resultado"] not in ("concluido", "interrompido", "falha"):
                raise ValueError("resultado invalido")
            alvo = numero(linha["alvo"], "alvo")
            if alvo == 0:
                raise ValueError("alvo deve ser nao nulo")
            medido = numero(linha["medido"], "medido")
            desvio = numero(linha["desvio_mm"], "desvio_mm", 0)
            colisoes = contador(linha["colisoes"], "colisoes")
            erro = medido - alvo
            aprovado = (abs(erro) <= tolerancias[tipo] and desvio <= desvio_max
                        and colisoes == 0 and linha["resultado"] == "concluido")
            grupos[(origem, tipo, controle, alvo)].append((erro, colisoes, aprovado, desvio))
        except (KeyError, ValueError) as erro:
            raise ValueError(f"linha {indice}: {erro}") from erro
    if not grupos:
        raise ValueError("sem ensaios; formulario vazio nao e evidencia")
    saida = []
    for (origem, tipo, controle, alvo), valores in sorted(grupos.items()):
        erros = [v[0] for v in valores]
        saida.append(dict(origem=origem, tipo=tipo, controle=controle, alvo=alvo,
                          unidade="mm" if tipo == "reta" else "graus",
                          repeticoes=len(valores), erro_medio=statistics.mean(erros),
                          erro_absoluto_medio=statistics.mean(abs(e) for e in erros),
                          desvio_padrao=statistics.stdev(erros) if len(erros) > 1 else None,
                          desvio_lateral_max_mm=max(v[3] for v in valores),
                          colisoes=sum(v[1] for v in valores),
                          sucessos=sum(v[2] for v in valores),
                          taxa_sucesso=sum(v[2] for v in valores) / len(valores)))
    return {"tolerancia_reta_mm": tolerancias["reta"],
            "tolerancia_giro_graus": tolerancias["giro"],
            "desvio_max_mm": desvio_max, "grupos": saida}


def analisar_autonomia(linhas, intervalo_max_s, tensao_min_v, temperatura_max_c):
    intervalo_max = numero(intervalo_max_s, "intervalo maximo", 0)
    tensao_min = numero(tensao_min_v, "tensao minima", 0)
    temperatura_max = numero(temperatura_max_c, "temperatura maxima")
    if intervalo_max == 0 or tensao_min == 0:
        raise ValueError("intervalo e tensao minima devem ser positivos")
    amostras = []
    for indice, linha in enumerate(linhas, start=2):
        try:
            if linha["origem"] not in ("measured", "simulated"):
                raise ValueError("origem invalida")
            if linha["estado"] not in ("executando", "parado", "falha"):
                raise ValueError("estado invalido")
            a = dict(t=numero(linha["t_s"], "t_s", 0), origem=linha["origem"],
                     estado=linha["estado"], v=opcional(linha["tensao_v"], "tensao_v"),
                     i=opcional(linha["corrente_a"], "corrente_a"),
                     temp=opcional(linha["temperatura_c"], "temperatura_c", -273.15),
                     resets=contador(linha["resets"], "resets"),
                     quedas=contador(linha["quedas_link"], "quedas_link"))
            if amostras:
                anterior = amostras[-1]
                if a["t"] <= anterior["t"]:
                    raise ValueError("tempo deve crescer estritamente")
                if a["origem"] != anterior["origem"]:
                    raise ValueError("nao misturar origens no mesmo ensaio")
                if a["resets"] < anterior["resets"] or a["quedas"] < anterior["quedas"]:
                    raise ValueError("contadores cumulativos nao podem diminuir")
            amostras.append(a)
        except (KeyError, ValueError) as erro:
            raise ValueError(f"linha {indice}: {erro}") from erro
    if len(amostras) < 2:
        raise ValueError("exige ao menos duas amostras")
    duracao = amostras[-1]["t"] - amostras[0]["t"]
    intervalos = [b["t"] - a["t"] for a, b in zip(amostras, amostras[1:])]
    tensoes = [a["v"] for a in amostras if a["v"] is not None]
    temperaturas = [a["temp"] for a in amostras if a["temp"] is not None]
    motivos = []
    if duracao < 1800:
        motivos.append("duracao inferior a 30 minutos")
    if max(intervalos) > intervalo_max:
        motivos.append("lacuna de coleta acima do limite")
    if any(a["estado"] != "executando" for a in amostras):
        motivos.append("operacao interrompida ou falha")
    if len(tensoes) != len(amostras) or min(tensoes, default=0) < tensao_min:
        motivos.append("tensao ausente ou abaixo do limite")
    if len(temperaturas) != len(amostras) or max(temperaturas, default=float('inf')) > temperatura_max:
        motivos.append("temperatura ausente ou acima do limite")
    if amostras[-1]["resets"]:
        motivos.append("reset registrado")
    if amostras[-1]["quedas"]:
        motivos.append("queda de comunicacao registrada")
    energia_wh = None
    if all(a["v"] is not None and a["i"] is not None for a in amostras):
        energia_wh = sum((a["v"] * a["i"] + b["v"] * b["i"]) / 2
                         * (b["t"] - a["t"]) / 3600
                         for a, b in zip(amostras, amostras[1:]))
    return dict(origem=amostras[0]["origem"], duracao_s=duracao,
                intervalo_max_observado_s=max(intervalos),
                tensao_min_observada_v=min(tensoes, default=None),
                temperatura_max_observada_c=max(temperaturas, default=None),
                resets=amostras[-1]["resets"], quedas_link=amostras[-1]["quedas"],
                energia_wh=energia_wh, criterios_observaveis_atendidos=not motivos,
                pendencias=motivos,
                limites=dict(intervalo_max_s=intervalo_max, tensao_min_v=tensao_min,
                             temperatura_max_c=temperatura_max))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    comandos = parser.add_subparsers(dest="comando", required=True)
    mov = comandos.add_parser("movimentos")
    mov.add_argument("csv")
    mov.add_argument("--tolerancia-reta-mm", type=float, required=True)
    mov.add_argument("--tolerancia-giro-graus", type=float, required=True)
    mov.add_argument("--desvio-max-mm", type=float, required=True)
    auto = comandos.add_parser("autonomia")
    auto.add_argument("csv")
    auto.add_argument("--intervalo-max-s", type=float, required=True)
    auto.add_argument("--tensao-min-v", type=float, required=True)
    auto.add_argument("--temperatura-max-c", type=float, required=True)
    args = parser.parse_args(argv)
    try:
        if args.comando == "movimentos":
            resultado = analisar_movimentos(ler_csv(args.csv, CAMPOS_MOVIMENTO),
                                            args.tolerancia_reta_mm,
                                            args.tolerancia_giro_graus, args.desvio_max_mm)
        else:
            resultado = analisar_autonomia(ler_csv(args.csv, CAMPOS_AUTONOMIA),
                                           args.intervalo_max_s, args.tensao_min_v,
                                           args.temperatura_max_c)
    except (OSError, ValueError) as erro:
        parser.error(str(erro))
    print(json.dumps(resultado, indent=2, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
