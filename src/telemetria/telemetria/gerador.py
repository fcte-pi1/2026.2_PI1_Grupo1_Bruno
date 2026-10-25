"""Robô falso determinístico para testar o mesmo caminho JSONL do hardware."""

import argparse
import asyncio
import math
import sys
from collections.abc import Iterator
from contextlib import nullcontext

from telemetria.fonte_simulada import SimuladorRobo
from telemetria.modelos import Frame


def positivo(valor: str) -> float:
    numero = float(valor)
    if not math.isfinite(numero) or numero <= 0:
        raise argparse.ArgumentTypeError("informe um número positivo e finito")
    return numero


def endereco_tcp(valor: str) -> tuple[str, int]:
    host, separador, porta = valor.rpartition(":")
    try:
        numero = int(porta)
    except ValueError as erro:
        raise argparse.ArgumentTypeError("use HOST:PORT, por exemplo 127.0.0.1:8765") from erro
    if not separador or not host or not 1 <= numero <= 65535:
        raise argparse.ArgumentTypeError("use HOST:PORT com porta entre 1 e 65535")
    return host.removeprefix("[").removesuffix("]"), numero


def gerar_frames(seed: int = 7, taxa_hz: float = 10.0, duracao_s: float = 10.0) -> Iterator[Frame]:
    if not math.isfinite(taxa_hz) or not math.isfinite(duracao_s) or taxa_hz <= 0 or duracao_s <= 0:
        raise ValueError("taxa e duração devem ser positivas e finitas")
    robo = SimuladorRobo(seed)
    yield robo.iniciar(0.0)
    for passo in range(1, math.floor(duracao_s * taxa_hz) + 1):
        yield robo.amostra(passo / taxa_hz, 1 / taxa_hz)
    yield robo.finalizar(duracao_s)


async def executar(args: argparse.Namespace) -> None:
    escritor = None
    try:
        if args.tcp:
            _, escritor = await asyncio.wait_for(asyncio.open_connection(*args.tcp), timeout=5.0)
        with open(args.output, "xb") if args.output else nullcontext(sys.stdout.buffer) as arquivo:
            for frame in gerar_frames(args.seed, args.taxa, args.duracao):
                linha = (frame.model_dump_json() + "\n").encode()
                if escritor:
                    escritor.write(linha)
                    await escritor.drain()
                else:
                    arquivo.write(linha)
                    arquivo.flush()
                await asyncio.sleep(0 if args.rapido else 1 / args.taxa)
    finally:
        if escritor:
            escritor.close()
            await escritor.wait_closed()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--taxa", type=positivo, default=10.0)
    parser.add_argument("--duracao", type=positivo, default=10.0)
    parser.add_argument("--rapido", action="store_true", help="gera sem espera; testa sobrecarga")
    destino = parser.add_mutually_exclusive_group()
    destino.add_argument("--output", help="arquivo JSONL novo (não sobrescreve)")
    destino.add_argument("--tcp", type=endereco_tcp, help="conecta ao receptor HOST:PORT")
    args = parser.parse_args()
    try:
        asyncio.run(executar(args))
    except (OSError, TimeoutError) as erro:
        parser.exit(1, f"gerador: {erro}\n")
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
