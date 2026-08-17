"""Tabela de lançamento do bit06: o MESMO foguete com cada carga de vinagre.

O projeto foi afinado para 1,50 L, mas no dia pode faltar vinagre. Aqui o
foguete final é simulado com todas as cargas disponíveis x todos os rendimentos,
para o manual dizer o que esperar (alcance E estabilidade) em cada caso.
"""
from __future__ import annotations

import copy
import dataclasses
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from orx.config import load_config
from orx.config.loader import BatchConfig
from orx.simulation.runner import Runner

import bit06_robusto as B

PASTA = Path(r"D:\1-Competicoes\OBAFOG\foguetes\bit06 1,8L")
CARGAS = [0.50, 0.70, 0.90, 1.05, 1.20, 1.35, 1.50]
NaHCO3 = 84.007
ACIDO_MOL_L = 40.0 / 60.052      # vinagre 4% m/v
BICARB_PRATICA_G_L = 130.0       # o que o Murilo usa (~200 g em 1,55 L)


def main() -> None:
    cfg = load_config(B.CONFIG)
    runner = Runner(dataclasses.replace(cfg, batch=BatchConfig(workers=1)))
    v = json.loads((PASTA / "simulacoes" / "variantes_bit06.json").read_text(encoding="utf-8"))
    base = [x for x in v["variantes"] if x["tag"] == "B_CONSTRUTIVEL"][0]["design"]

    print(f"{'carga':>6s} {'bicarb':>7s} {'teto':>6s} | " +
          "  ".join(f"eta={e:.2f}" for e in B.ETAS) + " | estab.min")
    print("-" * 86)
    linhas = []
    for carga in CARGAS:
        nome = f"Bit06-L{carga:.2f}-E080".replace(".", "_")
        if nome not in B.MANIFESTO:
            continue
        d = copy.deepcopy(base)
        d["motor"] = f"file:{B.MOTORES / (nome + '.eng')}"
        a = B.avalia_completo(runner, d)
        teto = B.MANIFESTO[nome]["pressao_teto_psi"]
        bic_estq = carga * ACIDO_MOL_L * NaHCO3
        bic_uso = carga * BICARB_PRATICA_G_L
        if a.motivo_descarte and a.nota < 0:
            estab = a.estab_min if a.estab_min else 0
        cels = []
        for e in B.ETAS:
            psi = B.MANIFESTO[f"Bit06-L{carga:.2f}-E{int(round(e*100)):03d}".replace(".", "_")]["pressao_psi"]
            alc = a.alcance_por_eta.get(e)
            cels.append(f"{psi:3.0f}psi/{alc:3.0f}m" if alc else "    --    ")
        marca = ""
        if a.motivo_descarte:
            marca = "  << " + a.motivo_descarte[:40]
        print(f"{carga:5.2f}L {bic_uso:6.0f}g {teto:5.0f}p | " + "  ".join(cels) +
              f" | {a.estab_min:.2f}{marca}")
        linhas.append({
            "carga_L": carga,
            "bicarb_estequiometrico_g": round(bic_estq, 1),
            "bicarb_uso_g": round(bic_uso, 0),
            "pressao_teto_psi": teto,
            "psi_por_eta": {str(k): val for k, val in a.psi_por_eta.items()},
            "alcance_por_eta": {str(k): round(val, 1) for k, val in a.alcance_por_eta.items()},
            "estab_min": round(a.estab_min, 3),
            "trilho_min": round(a.trilho_min, 2),
            "apogeu_medio": round(a.apogeu_medio, 1),
            "nota": round(a.nota, 2),
            "descarte": a.motivo_descarte,
        })
    (PASTA / "simulacoes" / "cargas_bit06.json").write_text(
        json.dumps(linhas, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\n>> {PASTA / 'simulacoes' / 'cargas_bit06.json'}")


if __name__ == "__main__":
    main()
