"""Consulta o histórico salvo pelo painel (TEL03). Abre o banco só para leitura."""

import argparse
import sqlite3
from pathlib import Path

from telemetria.armazenamento import LIMITE_CONSULTA, Armazenamento, ResumoExecucao
from telemetria.formatacao import ROTULO_ORIGEM, texto_tempo

ROTULO_STATUS = {
    "em_andamento": "em andamento",
    "concluida": "concluída",
    "incompleta": "incompleta",
}


def texto_status(resumo: ResumoExecucao) -> str:
    texto = ROTULO_STATUS[resumo.status]
    if resumo.estado_final:
        texto += f" ({resumo.estado_final})"
    return texto


def texto_origens(resumo: ResumoExecucao) -> str:
    return ", ".join(ROTULO_ORIGEM[origem] for origem in resumo.origens) or "—"


def observacoes(resumo: ResumoExecucao) -> str:
    notas = []
    if resumo.app_interrompido:
        notas.append("app interrompido: pode haver lacuna")
    if not resumo.start_recebido:
        notas.append("start não recebido")
    if resumo.amostras_descartadas:
        notas.append(f"{resumo.amostras_descartadas} amostras acima do limite")
    return "; ".join(notas)


def linhas_tabela(resumos: list[ResumoExecucao]) -> list[list[str]]:
    return [
        [
            resumo.recebido_em.replace("T", " ")[:19],
            resumo.run_id,
            resumo.maze_id or "—",
            texto_status(resumo),
            texto_tempo(resumo.duracao_ms),
            texto_origens(resumo),
            str(resumo.amostras),
            str(resumo.falhas),
            observacoes(resumo),
        ]
        for resumo in resumos
    ]


CABECALHO = [
    "Recebido (UTC)",
    "Execução",
    "Labirinto",
    "Estado",
    "Duração",
    "Origem",
    "Amostras",
    "Falhas",
    "Obs.",
]


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--banco", required=True, help="arquivo SQLite gerado com python -m telemetria --banco"
    )
    parser.add_argument("--labirinto", help="filtra por maze_id, por exemplo 4x4")
    parser.add_argument("--estado", choices=sorted(ROTULO_STATUS), help="filtra pelo estado da execução")
    parser.add_argument("--origem", choices=sorted(ROTULO_ORIGEM), help="filtra pela origem dos dados")
    parser.add_argument("--limite", type=int, default=20, help=f"máximo de linhas (1..{LIMITE_CONSULTA})")
    parser.add_argument("--pagina", type=int, default=1, help="página de resultados, a partir de 1")
    args = parser.parse_args(argv)
    if not 1 <= args.limite <= LIMITE_CONSULTA or args.pagina < 1:
        parser.error(f"--limite deve estar entre 1 e {LIMITE_CONSULTA}; --pagina a partir de 1")
    if not Path(args.banco).is_file():
        parser.exit(1, f"historico: banco não encontrado: {args.banco}\n")

    try:
        with Armazenamento(args.banco, somente_leitura=True) as banco:
            resumos = banco.execucoes(
                maze_id=args.labirinto,
                status=args.estado,
                origem=args.origem,
                limite=args.limite,
                deslocamento=(args.pagina - 1) * args.limite,
            )
    except sqlite3.Error as erro:
        parser.exit(1, f"historico: {erro}\n")

    if not resumos:
        print("Nenhuma execução encontrada.")
        return
    linhas = [CABECALHO, *linhas_tabela(resumos)]
    larguras = [max(len(linha[i]) for linha in linhas) for i in range(len(CABECALHO))]
    for linha in linhas:
        print(
            "  ".join(celula.ljust(largura) for celula, largura in zip(linha, larguras, strict=True)).rstrip()
        )


if __name__ == "__main__":
    main()
