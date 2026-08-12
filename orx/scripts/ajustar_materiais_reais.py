"""Aplica os materiais REAIS de construção (ogiva PLA, aletas poliestireno 1 mm)
e reajusta o lastro de Durepoxi para restaurar a margem de estabilidade.

Motivo: os designs foram otimizados com aletas de papel-cartão 0,6 mm. Trocar
por poliestireno 1,0 mm (mais pesado, na traseira) puxa o CG para trás e derruba
a estabilidade pós-queima abaixo do mínimo de 1,0 cal. A correção correta é
compensar com um pouco mais de lastro na ponta.
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from orx.config import load_config
from orx.objectives.objective import Constraints
from orx.results.db import ResultsDB
from orx.simulation.runner import Runner
from orx.utils.logging import setup_logging

CONFIG = r"C:\Users\muril\openrocket-optimizer\config\foguete_real.yaml"
OLD = "OBAFOG" + chr(92) + "foguete_real"
NEW = "OBAFOG" + chr(92) + "bit04" + chr(92) + "foguete_real"
STAB_ALVO = 1.10          # margem confortável acima do mínimo de 1,0
SEEDS = list(range(101, 121))

MATERIAIS_REAIS = {
    "nose_material": "pla",           # ogiva impressa em 3D
    "fin_material": "poliestireno",   # aletas recortadas
    "fin_thickness": 1.0,             # mm
}


def robustez(runner, cons, design):
    v, met = [], None
    for s in SEEDS:
        r = runner.evaluate(design, sim_overrides={"random_seed": s})
        if r.ok and r.metrics.get("horizontal_distance") is not None:
            if not cons.violations(r.metrics):
                v.append(r.metrics["horizontal_distance"])
            met = met or r.metrics
    return np.array(v), met


def main() -> None:
    setup_logging()
    cfg = load_config(CONFIG)
    runner, cons = Runner(cfg), Constraints(cfg.constraints)
    db = ResultsDB(cfg.db_path)

    alvos = [
        (1, "OTIMIZADO", "foguete_real_otimizado_MATERIAIS_REAIS.ork", 51.0),
        (2, "HUMANO", "foguete_MODELO_HUMANO_MATERIAIS_REAIS.ork", 46.0),
    ]
    for run_id, tag, saida, _ang in alvos:
        best = db.best_evaluation(run_id, "maximize")
        d = dict(best["params"])
        d["motor"] = d["motor"].replace(OLD, NEW)
        antes_fill = d["ballast_fill"]
        d.update(MATERIAIS_REAIS)

        r0 = runner.evaluate(d, sim_overrides={"random_seed": 42})
        s0 = r0.metrics.get("stability_max")
        print(f"\n[{tag}] com materiais reais, lastro original ({antes_fill:.1f} cm): "
              f"estabilidade pós-queima = {s0:.3f} cal"
              + ("  <-- ABAIXO de 1,0" if s0 and s0 < 1.0 else ""))

        # sobe o lastro até a margem alvo
        lo, hi = antes_fill, min(antes_fill + 12.0, 27.0)
        for _ in range(20):
            mid = (lo + hi) / 2
            d["ballast_fill"] = mid
            r = runner.evaluate(d, sim_overrides={"random_seed": 42})
            s = r.metrics.get("stability_max") if r.ok else None
            if s is None:
                lo = mid
                continue
            if abs(s - STAB_ALVO) < 0.01:
                break
            if s < STAB_ALVO:
                lo = mid
            else:
                hi = mid

        a, m = robustez(runner, cons, d)
        print(f"       lastro ajustado: {antes_fill:.1f} -> {d['ballast_fill']:.1f} cm "
              f"({m['ballast_mass']*1000:.0f} g de Durepoxi)")
        print(f"       estabilidade pós-queima: {m['stability_max']:.2f} cal | "
              f"inicial {m['stability_static']:.2f} cal")
        print(f"       alcance médio (20 ventos): {a.mean():.1f} m (±{a.std():.1f}, pior {a.min():.1f})")
        print(f"       massa decolagem {m['liftoff_mass']:.2f} kg | apogeu {m['apogee']:.0f} m")

        destino = Path(cfg.base_ork).parent / saida
        runner.save_design(d, str(destino))
        print(f"       salvo: {destino.name}")
    db.close()


if __name__ == "__main__":
    main()
