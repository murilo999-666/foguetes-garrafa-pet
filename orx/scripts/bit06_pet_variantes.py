"""Variantes de entrega do bit06 v2 (coifa de PET).

O campeão da busca livre veio com ALETA DE PAPEL-CARTÃO de 0,84 mm e nota 0,0/5
em rigidez aeroelástica — a aleta mais mole que o espaço permite. É o mesmo
vício de sempre: "leveza" paga ponto e nada segura a espessura para baixo, então
a busca entrega um foguete que ninguém constrói (e que, em papel-cartão, murcha
na primeira garoa).

Então entregamos:
  A) CAMPEÃO      — o que a busca achou (referência de teto)
  B) CONSTRUTÍVEL — polietileno 1,0 mm, medidas de régua, aleta reta
  C) RÍGIDA       — polietileno 2,0 mm: paga o preço da rigidez
  D) MARGEM       — construtível com mais lastro, para estabilidade de verdade
"""

from __future__ import annotations

import copy
import dataclasses
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from orx.config import load_config
from orx.config.loader import BatchConfig
from orx.simulation.runner import Runner
from orx.bridge.orjava import OrBridge, J

import bit06_pet_aero as B

PASTA = Path(r"D:\1-Competicoes\OBAFOG\foguetes\bit06 1,8L")


def arredonda(design: dict) -> dict:
    d = copy.deepcopy(design)
    for k in ("nose_length", "fin_root", "fin_tip", "fin_sweep", "fin_height"):
        d[k] = round(float(d[k]) * 2) / 2          # passo de 0,5 cm
    d["ballast_fill"] = round(float(d["ballast_fill"]) * 2) / 2
    d["launch_angle"] = float(round(float(d["launch_angle"])))
    d["nose_shape_param"] = round(float(d["nose_shape_param"]), 2)
    d["fin_cant"] = 0.0                            # aleta reta: dá para colar certo
    return d


def construtivel(design: dict, espessura: float) -> dict:
    d = arredonda(design)
    d["fin_material"] = "polietileno"
    d["fin_thickness"] = espessura
    return d


def main() -> None:
    cfg = load_config(B.CONFIG)
    runner = Runner(dataclasses.replace(cfg, batch=BatchConfig(workers=1)))
    rank = json.loads((PASTA / "simulacoes" / "rank_bit06_pet_aero.json").read_text(encoding="utf-8"))
    campeao = rank[0]["design"]

    d_margem = construtivel(campeao, 1.0)
    d_margem["ballast_fill"] = round(min(16.0, float(d_margem["ballast_fill"]) + 3.0) * 2) / 2

    variantes = [
        ("A_CAMPEAO", "Campeão da busca (papel-cartão 0,84 mm)", campeao),
        ("B_CONSTRUTIVEL", "Polietileno 1,0 mm, medidas de régua", construtivel(campeao, 1.0)),
        ("C_RIGIDA", "Polietileno 2,0 mm — paga rigidez", construtivel(campeao, 2.0)),
        ("D_MARGEM", "Construtível com +3 cm de lastro", d_margem),
    ]

    br = OrBridge()
    MassComponent = J("info.openrocket.core.rocketcomponent.MassComponent")

    print(f"{'variante':16s} {'nota':>6s} {'alcance':>8s} {'seca':>7s} {'estab':>6s} "
          f"{'Cd':>6s} {'rigidez':>8s} {'lastro':>7s}")
    print("-" * 76)
    saida = []
    for tag, desc, d in variantes:
        a = B.avalia_completo(runner, d)
        if a.motivo_descarte:
            print(f"{tag:16s} REPROVOU: {a.motivo_descarte}")
            saida.append({"tag": tag, "descricao": desc, "design": d,
                          "descarte": a.motivo_descarte, "avaliacao": None})
            continue
        ork = PASTA / f"bit06_PET_{tag}.ork"
        runner.save_design(d, str(ork))
        doc = br.load_document(str(ork))
        lastro = sum(float(c.getMass()) for c in br.iter_components(doc)
                     if isinstance(c, MassComponent))
        print(f"{tag:16s} {a.nota:6.1f} {a.alcance_medio:7.0f}m {a.massa_seca*1000:6.0f}g "
              f"{a.estab_min:6.2f} {a.cd_medio:6.3f} {a.rigidez:8.0f} {lastro*1000:6.0f}g")
        saida.append({"tag": tag, "descricao": desc, "design": d, "ork": str(ork),
                      "lastro_g": round(lastro * 1000, 1),
                      "avaliacao": dataclasses.asdict(a)})

    (PASTA / "simulacoes" / "variantes_pet.json").write_text(
        json.dumps(saida, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"\n>> {PASTA / 'simulacoes' / 'variantes_pet.json'}")


if __name__ == "__main__":
    main()
