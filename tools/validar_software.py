"""Executa suites existentes e salva logs/cobertura sem acessar hardware.

Na raiz: python tools/validar_software.py
Requer requirements-dev.txt da telemetria e coverage==7.17.0.
"""

import json
import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
DESTINO = ROOT / 'docs/evidencias/software'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--isolar-telemetria', action='store_true',
                        help='executa cada arquivo da telemetria em processo separado')
    opcoes = parser.parse_args()
    DESTINO.mkdir(parents=True, exist_ok=True)
    ambiente = os.environ.copy()
    ambiente['PYTHONUTF8'] = '1'
    ambiente['PYTHONIOENCODING'] = 'utf-8'
    ambiente['PYTHONPATH'] = os.pathsep.join(
        str(ROOT / p) for p in ('src/firmware', 'src/telemetria', 'tools')
    )
    suites = [
        ('firmware', ROOT, 'src/firmware', ['src/firmware', '-q', '-ra']),
        ('telemetria', ROOT / 'src/telemetria', 'telemetria', ['tests', '-q', '-ra']),
        ('calibracao', ROOT, 'tools', ['tools/test_calibracao.py', '-q', '-ra']),
    ]
    resultados = {}
    with tempfile.TemporaryDirectory(prefix='validacao-software-') as pasta:
        for nome, cwd, fonte, args in suites:
            dados = str(Path(pasta) / (nome + '.coverage'))
            base = [sys.executable, '-m', 'coverage']
            omitir = '*/test_*.py,*/tests/*,*/.venv/*,*/wifi_config.example.py,*/validar_software.py'
            grupos = [args]
            if nome == 'telemetria' and opcoes.isolar_telemetria:
                grupos = [[str(p.relative_to(cwd)), '-q', '-ra']
                          for p in sorted((cwd / 'tests').glob('test_*.py'))]
            log = ''
            codigo = 0
            for indice, grupo in enumerate(grupos):
                limite_s = 30 if len(grupos) > 1 else 180
                cmd = [*base, 'run', '--branch', '--data-file', dados,
                       '--source', fonte, '--omit', omitir]
                if indice:
                    cmd.append('--append')
                cmd.extend(['-m', 'pytest', *grupo])
                try:
                    proc = subprocess.run(cmd, cwd=cwd, env=ambiente, capture_output=True,
                                          encoding='utf-8', timeout=limite_s)
                    saida = proc.stdout + proc.stderr
                    codigo = codigo or proc.returncode
                except subprocess.TimeoutExpired as exc:
                    saida = (exc.stdout or b'').decode('utf-8', errors='replace') if isinstance(exc.stdout, bytes) else (exc.stdout or '')
                    saida += '\nINTERROMPIDO: excedeu %s s; grupo nao aprovado.\n' % limite_s
                    codigo = codigo or 124
                log += '$ ' + subprocess.list2cmdline(cmd) + '\n\n' + saida + '\n'
                print(nome + ' ' + grupo[0] + ':\n' + saida[-1200:], flush=True)
            # Mantem os logs portateis e sem caminhos pessoais/temporarios.
            log = log.replace(str(ROOT), '<REPOSITORIO>').replace(pasta, '<TEMP>')
            (DESTINO / (nome + '-testes.txt')).write_text(log, encoding='utf-8')
            report = subprocess.run([*base, 'report', '--data-file', dados, '-m', '--precision=2'],
                                    cwd=cwd, env=ambiente, capture_output=True, encoding='utf-8')
            (DESTINO / (nome + '-cobertura.txt')).write_text(report.stdout + report.stderr, encoding='utf-8')
            resumo = Path(pasta) / (nome + '.json')
            gerar = subprocess.run([*base, 'json', '--data-file', dados, '-o', str(resumo)],
                                   cwd=cwd, env=ambiente, capture_output=True)
            resultados[nome] = {'exit_code_testes': codigo,
                               'grupos_em_processos_separados': len(grupos),
                               'exit_code_cobertura': report.returncode}
            if gerar.returncode == 0:
                resultados[nome]['totais'] = json.loads(resumo.read_text(encoding='utf-8'))['totals']
    (DESTINO / 'resumo.json').write_text(json.dumps(resultados, indent=2), encoding='utf-8')
    return int(any(r['exit_code_testes'] or r['exit_code_cobertura'] for r in resultados.values()))


if __name__ == '__main__':
    raise SystemExit(main())
