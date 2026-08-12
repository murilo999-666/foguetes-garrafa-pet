"""Tolerância do lastro do bit06: quanto de Durepoxi pesar e o que muda.

Varre a profundidade de preenchimento do bico da ogiva na variante construtível
e pontua cada valor com a MESMA régua da campanha (4 rendimentos x 3 ventos).
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

import bit06_robusto as B

PASTA = Path(r"D:\OBAFOG\bit06 1,8L")
FILLS_CM = [8.0, 10.0, 12.0, 14.0, 16.0, 18.0]


def main() -> None:
    cfg = load_config(B.CONFIG)
    runner = Runner(dataclasses.replace(cfg, batch=BatchConfig(workers=1)))
    v = json.loads((PASTA / "simulacoes" / "variantes_bit06.json").read_text(encoding="utf-8"))
    base = [x for x in v["variantes"] if x["tag"] == "B_CONSTRUTIVEL"][0]["design"]

    br = OrBridge()
    MassComponent = J("info.openrocket.core.rocketcomponent.MassComponent")

    print(f"{'bico':>6s} {'lastro':>8s} {'seca':>7s} {'estab':>7s} {'alcance':>8s} "
          f"{'pior':>6s} {'trilho':>7s} {'nota':>6s}")
    print("-" * 62)
    linhas = []
    for fill in FILLS_CM:
        d = copy.deepcopy(base)
        d["ballast_fill"] = fill
        a = B.avalia_completo(runner, d)
        if a.motivo_descarte:
            print(f"{fill:5.1f}cm  REPROVA: {a.motivo_descarte}")
            linhas.append({"fill_cm": fill, "reprova": a.motivo_descarte})
            continue
        tmp = PASTA / "simulacoes" / "_tmp_lastro.ork"
        runner.save_design(d, str(tmp))
        doc = br.load_document(str(tmp))
        lastro = sum(float(c.getMass()) for c in br.iter_components(doc)
                     if isinstance(c, MassComponent))
        print(f"{fill:5.1f}cm {lastro*1000:7.0f}g {a.massa_seca*1000:6.0f}g "
              f"{a.estab_min:6.2f} {a.alcance_medio:7.0f}m {a.alcance_pior:5.0f}m "
              f"{a.trilho_min:6.1f} {a.nota:6.1f}")
        linhas.append({
            "fill_cm": fill, "lastro_g": round(lastro * 1000, 1),
            "seca_g": round(a.massa_seca * 1000, 1),
            "estab_min": round(a.estab_min, 3),
            "alcance_medio": round(a.alcance_medio, 1),
            "alcance_pior": round(a.alcance_pior, 1),
            "trilho": round(a.trilho_min, 2), "nota": round(a.nota, 2),
            "alcance_por_eta": {str(k): round(val, 1) for k, val in a.alcance_por_eta.items()},
        })
    tmp = PASTA / "simulacoes" / "_tmp_lastro.ork"
    if tmp.exists():
        tmp.unlink()
    (PASTA / "simulacoes" / "lastro_bit06.json").write_text(
        json.dumps(linhas, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\n>> {PASTA / 'simulacoes' / 'lastro_bit06.json'}")


if __name__ == "__main__":
    main()
