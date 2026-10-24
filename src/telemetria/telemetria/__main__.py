import argparse

from nicegui import app, background_tasks, ui

from telemetria.coleta import coletar
from telemetria.estado import EstadoPainel
from telemetria.fonte_simulada import FonteSimulada
from telemetria.painel import criar_pagina


def argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Painel de telemetria do Micromouse")
    parser.add_argument("--porta", type=int, default=8080)
    parser.add_argument("--taxa", type=float, default=20.0, help="mensagens por segundo da fonte")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--intervalo-queda", type=float, default=25.0)
    parser.add_argument("--duracao-queda", type=float, default=4.0)
    parser.add_argument("--sem-navegador", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = argumentos()
    estado = EstadoPainel()
    fonte = FonteSimulada(
        seed=args.seed,
        taxa_hz=args.taxa,
        intervalo_queda_s=args.intervalo_queda,
        duracao_queda_s=args.duracao_queda,
    )
    criar_pagina(estado, fonte_simulada=fonte.simulada)
    app.on_startup(lambda: background_tasks.create(coletar(fonte, estado), name="coleta"))
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
