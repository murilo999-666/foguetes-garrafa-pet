"""Orquestrador da campanha bit06: roda cada bloco num PROCESSO SEPARADO.

Por que separar em processos
----------------------------
A máquina do Murilo está SEM arquivo de paginação (page file desativado), então
o limite de commit do Windows é a RAM física. Cada worker do pool é uma JVM;
mesmo com a JVM enxuta, rodar ~100 mil simulações num único processo acumula
fragmentação e qualquer pico derruba tudo com
"WinError 1455 - arquivo de paginação muito pequeno".

Terminar o processo ao fim de cada bloco devolve 100% da memória ao SO. O banco
SQLite acumula os resultados de TODOS os blocos, então a etapa 2 (que pontua os
finalistas) enxerga a campanha inteira mesmo que um bloco tenha falhado.

Uso:
    .venv\\Scripts\\python scripts\\bit06_orquestrador.py
    .venv\\Scripts\\python scripts\\bit06_orquestrador.py --blocos 8 --por-bloco 12400
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).parent.parent
PY = RAIZ / ".venv" / "Scripts" / "python.exe"
SCRIPT = RAIZ / "scripts" / "bit06_robusto.py"
PASTA = Path(r"D:\1-Competicoes\OBAFOG\foguetes\bit06 1,8L")
LOG = PASTA / "log_busca_bit06.txt"


def arg(nome: str, padrao: int) -> int:
    return int(sys.argv[sys.argv.index(nome) + 1]) if nome in sys.argv else padrao


def fmt(seg: float) -> str:
    h, r = divmod(int(seg), 3600)
    m, s = divmod(r, 60)
    return f"{h}h{m:02d}m" if h else f"{m}m{s:02d}s"


def main() -> None:
    blocos = arg("--blocos", 8)
    por_bloco = arg("--por-bloco", 12400)
    finalistas = arg("--finalistas", 60)
    total = blocos * por_bloco

    LOG.write_text("", encoding="utf-8")
    cab = (f"{'='*70}\n"
           f"bit06 — campanha de {total:,} simulações em {blocos} blocos\n".replace(",", ".") +
           f"cada bloco roda num processo próprio (máquina sem page file)\n"
           f"início: {time.strftime('%Y-%m-%d %H:%M:%S')}\n{'='*70}\n")
    LOG.write_text(cab, encoding="utf-8")
    print(cab, flush=True)

    t0 = time.time()
    falhas = []
    for b in range(1, blocos + 1):
        print(f"\n>>> bloco {b}/{blocos} (processo próprio)", flush=True)
        cmd = [str(PY), str(SCRIPT), "--bloco", str(b), "--blocos", str(blocos),
               "--por-bloco", str(por_bloco)]
        r = subprocess.run(cmd, cwd=str(RAIZ))
        if r.returncode != 0:
            falhas.append(b)
            msg = f"!! bloco {b} terminou com código {r.returncode} — seguindo para o próximo"
            print(msg, flush=True)
            with LOG.open("a", encoding="utf-8") as fh:
                fh.write(msg + "\n")

    dur = time.time() - t0
    print(f"\n>>> etapa 1 concluída em {fmt(dur)} "
          f"({len(falhas)} bloco(s) com falha: {falhas or 'nenhum'})", flush=True)

    print("\n>>> ETAPA 2 (processo próprio)", flush=True)
    r = subprocess.run([str(PY), str(SCRIPT), "--so-etapa2",
                        "--blocos", str(blocos), "--por-bloco", str(por_bloco),
                        "--finalistas", str(finalistas)], cwd=str(RAIZ))
    print(f"\n>>> campanha encerrada em {fmt(time.time() - t0)} "
          f"(etapa 2 saiu com código {r.returncode})", flush=True)


if __name__ == "__main__":
    main()
