"""Calcula parametros a partir de MEDICOES, sem conectar ou gravar na ESP."""
import argparse
import math


def counts_per_mm(counts, turns, diameter_mm):
    if not counts or turns <= 0 or diameter_mm <= 0:
        raise ValueError('Contagens nao nulas, voltas e diametro positivos obrigatorios.')
    return abs(counts) / (turns * math.pi * diameter_mm)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--left-counts',type=int,required=True)
    p.add_argument('--right-counts',type=int,required=True)
    p.add_argument('--turns',type=float,required=True,help='voltas completas de CADA roda, ambas no sentido de avancar')
    p.add_argument('--diameter-mm',type=float,required=True)
    a=p.parse_args()
    values=tuple(counts_per_mm(n,a.turns,a.diameter_mm) for n in (a.left_counts,a.right_counts))
    print('COUNTS_PER_MM =',values)
    print('Sinais observados:',tuple(1 if n>0 else -1 for n in (a.left_counts,a.right_counts)))
    print('Se ENCODER_SIGNS ja foi aplicado, nao inverter novamente. Validar no chao.')
    print('Nao define CALIBRATED, curva, frenagem nem estabilidade automaticamente.')


if __name__=='__main__': main()
