import argparse
import asyncio
import logging
from contextlib import aclosing

from telemetria.captura import CapturaJSONL, FonteArquivo
from telemetria.coleta import aplicar, coletar
from telemetria.estado import EstadoPainel
from telemetria.fonte_simulada import FonteSimulada
from telemetria.gerador import endereco_tcp, positivo
from telemetria.modelos import Frame
from telemetria.receptor import FonteSerial, FonteTCPListen


def inteiro_positivo(valor: str) -> int:
    numero = int(valor)
    if numero <= 0:
        raise argparse.ArgumentTypeError("informe um inteiro positivo")
    return numero


def argumentos(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Painel de telemetria do Micromouse")
    parser.add_argument("--porta", type=int, default=8080)
    parser.add_argument("--taxa", type=positivo, default=10.0, help="taxa do simulador/playback (Hz)")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--intervalo-queda", type=positivo, default=25.0)
    parser.add_argument("--duracao-queda", type=positivo, default=4.0)
    parser.add_argument("--sem-navegador", action="store_true")
    fontes = parser.add_mutually_exclusive_group()
    fontes.add_argument("--serial", metavar="PORT", help="porta serial ou URL pySerial (ex.: loop://)")
    fontes.add_argument(
        "--tcp-listen", type=endereco_tcp, metavar="HOST:PORT", help="PC escuta o ESP32 cliente STA"
    )
    fontes.add_argument("--arquivo", help="reproduz frames JSONL")
    parser.add_argument("--baud", type=inteiro_positivo, default=115200)
    parser.add_argument("--fila-max", type=inteiro_positivo, default=256)
    parser.add_argument("--captura", help="arquivo novo para salvar frames validados em JSONL")
    parser.add_argument("--captura-max-bytes", type=inteiro_positivo, default=10 * 1024 * 1024)
    parser.add_argument(
        "--headless", action="store_true", help="sem UI; Frames válidos em stdout, diagnóstico em stderr"
    )
    parser.add_argument("--rapido", action="store_true", help="playback sem espera")
    parser.add_argument("--limite", type=inteiro_positivo, help="encerra headless após N Frames")
    parser.add_argument("--duracao", type=positivo, help="encerra headless após N segundos")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)
    if args.captura and not (args.serial or args.tcp_listen):
        parser.error("--captura requer --serial ou --tcp-listen")
    if (args.limite or args.duracao) and not args.headless:
        parser.error("--limite e --duracao requerem --headless")
    if args.rapido and not args.arquivo:
        parser.error("--rapido requer --arquivo")
    return args


def criar_fonte(args: argparse.Namespace, captura: CapturaJSONL | None = None):
    if args.serial:
        return FonteSerial(args.serial, args.baud, fila_max=args.fila_max, captura=captura)
    if args.tcp_listen:
        return FonteTCPListen(*args.tcp_listen, fila_max=args.fila_max, captura=captura)
    if args.arquivo:
        return FonteArquivo(args.arquivo, args.taxa, args.rapido)
    return FonteSimulada(
        seed=args.seed,
        taxa_hz=args.taxa,
        intervalo_queda_s=args.intervalo_queda,
        duracao_queda_s=args.duracao_queda,
    )


async def headless(fonte, limite: int | None = None, duracao: float | None = None) -> None:
    quantidade = 0
    estado = EstadoPainel()
    try:
        async with asyncio.timeout(duracao), aclosing(fonte.eventos()) as eventos:
            async for evento in eventos:
                if isinstance(evento, Frame):
                    if not estado.registrar(evento):
                        continue
                    print(evento.model_dump_json(), flush=True)
                    quantidade += 1
                    if limite is not None and quantidade >= limite:
                        break
                else:
                    aplicar(evento, estado)
                    logging.getLogger(__name__).info("%s", evento)
    except TimeoutError:
        pass


def main() -> None:
    args = argumentos()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)
    captura = CapturaJSONL(args.captura, args.captura_max_bytes) if args.captura else None
    fonte = criar_fonte(args, captura)
    if args.headless:

        async def executar() -> None:
            try:
                if captura:
                    await captura.abrir()
                await headless(fonte, args.limite, args.duracao)
            finally:
                if captura:
                    await captura.fechar()
                if hasattr(fonte, "estatisticas"):
                    logging.getLogger(__name__).info("recepção: %s", fonte.estatisticas)

        try:
            asyncio.run(executar())
        except KeyboardInterrupt:
            pass
        except (OSError, ValueError) as erro:
            raise SystemExit(f"telemetria: {erro}") from erro
        return

    from nicegui import app, background_tasks, ui

    from telemetria.painel import criar_pagina

    estado = EstadoPainel()
    tarefa = None

    async def iniciar() -> None:
        nonlocal tarefa
        if captura:
            await captura.abrir()
        tarefa = background_tasks.create(coletar(fonte, estado), name="coleta")

    async def encerrar() -> None:
        if tarefa:
            tarefa.cancel()
            await asyncio.gather(tarefa, return_exceptions=True)
        if captura:
            await captura.fechar()

    criar_pagina(estado, fonte_simulada=fonte.simulada)
    app.on_startup(iniciar)
    app.on_shutdown(encerrar)
    ui.run(
        port=args.porta,
        title="Telemetria Micromouse",
        reload=False,
        show=not args.sem_navegador,
        language="pt-BR",
        show_welcome_message=False,
    )


if __name__ in {"__main__", "__mp_main__"}:
    main()
