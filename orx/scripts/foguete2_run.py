"""FOGUETE 2 — "garantia" com motor fixo de 1,2 L (o vinagre que sobra).

Busca o melhor FORMATO (coifa, lastro, aletas, ângulo) para a pressão menor
do motor de 1,2 L, na mesma garrafa 2 L. Duas fases (explora + refina), depois
valida os melhores em 20 ventos no passo ultrafino e salva o campeão.
"""

import dataclasses
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from orx.config import load_config
from orx.config.loader import BatchConfig, OptimizerConfig
from orx.objectives.objective import Constraints
from orx.optimizer.engine import run_optimization
from orx.results.db import ResultsDB
from orx.simulation.runner import Runner
from orx.utils.logging import setup_logging

CONFIG = r"C:\Users\muril\openrocket-optimizer\config\foguete2_garantia.yaml"
OUT = r"D:\OBAFOG\_foguete2_garantia\foguete2_1_2L_MELHOR.ork"
FASES = [("random", 8_000, 7), ("adaptive", 16_000, 21)]
SEEDS = list(range(101, 121))   # 20 ventos p/ validação


def progresso(tag):
    def p(i, total, valor, melhor):
        if i % max(1, total // 80) == 0 or i == total:
            m = f"{melhor:.1f}" if melhor and melhor > -1e8 else "n/a"
            print(f"[{tag} {i}/{total}] melhor={m}", flush=True)
    return p


def valida(runner, cons, params_list, ts=0.005):
    out = []
    for p in params_list:
        ds, est = [], []
        for s in SEEDS:
            r = runner.evaluate(p, sim_overrides={"random_seed": s, "time_step": ts})
            if r.ok and r.metrics.get("horizontal_distance") is not None \
                    and not cons.violations(r.metrics):
                ds.append(r.metrics["horizontal_distance"])
                est.append(r.metrics.get("stability_max") or 0)
        a = np.array(ds)
        out.append({"params": p,
                    "media": float(a.mean()) if a.size else -1,
                    "pior": float(a.min()) if a.size else -1,
                    "desvio": float(a.std()) if a.size else -1,
                    "estab": float(np.mean(est)) if est else 0,
                    "ventos_ok": int(a.size)})
    return sorted(out, key=lambda d: -d["media"])


def main():
    setup_logging()
    cfg = load_config(CONFIG)
    cfg = dataclasses.replace(cfg, batch=BatchConfig(workers=4))
    runner = Runner(cfg)
    cons = Constraints(cfg.constraints)
    pn = [p.name for p in cfg.parameters]
    t0 = time.time()

    run_ids = []
    for algo, orc, seed in FASES:
        print(f"\n===== FASE {algo} ({orc} avaliações) =====", flush=True)
        cfg_f = dataclasses.replace(cfg, optimizer=OptimizerConfig(
            algorithm=algo, max_evaluations=orc, seed=seed, profile="balanced",
            options={"chunk_size": 2500} if algo == "adaptive" else {}))
        rid = run_optimization(cfg_f, run_name=f"fog2-{algo}", progress=progresso(algo))
        run_ids.append(rid)

    # junta as fases, pega os melhores viáveis únicos
    db = ResultsDB(cfg.db_path)
    import pandas as pd
    frames = [db.evaluations_df(r) for r in run_ids]
    db.close()
    todos = pd.concat([f for f in frames if not f.empty], ignore_index=True)
    ok = todos[(todos["feasible"] == 1) & todos["score"].notna()].sort_values(
        "score", ascending=False)
    vistos, tops = set(), []
    for _, row in ok.iterrows():
        p = {n: (float(row[f"p_{n}"]) if not isinstance(row[f"p_{n}"], str)
                 else row[f"p_{n}"]) for n in pn}
        chave = tuple(round(v, 2) if isinstance(v, float) else v for v in p.values())
        if chave in vistos:
            continue
        vistos.add(chave)
        tops.append(p)
        if len(tops) >= 12:
            break

    print(f"\n== validando top {len(tops)} em 20 ventos (passo 0.005) ==", flush=True)
    val = valida(runner, cons, tops)
    best = val[0]
    runner.save_design(best["params"], OUT)

    print("\n" + "=" * 60)
    print(f"FOGUETE 2 (1,2 L) — MELHOR: {best['media']:.1f} m  "
          f"(pior {best['pior']:.1f} / desvio {best['desvio']:.1f} / "
          f"estab {best['estab']:.2f} cal / {best['ventos_ok']}/20 ventos)")
    for k, v in best["params"].items():
        print(f"  {k} = {v:.4g}" if isinstance(v, float) else f"  {k} = {v}")
    # métricas cheias do campeão
    m = runner.evaluate(best["params"],
                        sim_overrides={"random_seed": 42, "time_step": 0.005}).metrics
    print(f"  >> apogeu={m.get('apogee',0):.0f} m | massa={m.get('liftoff_mass',0)*1000:.0f} g "
          f"| lastro={m.get('ballast_mass',0)*1000:.0f} g | saída={m.get('launch_rod_velocity',0):.1f} m/s")
    print(f"  >> salvo: {OUT}")
    print("\n-- top 5 alternativas --")
    for i, d in enumerate(val[:5], 1):
        p = d["params"]
        print(f"  {i}. {d['media']:.1f} m | estab {d['estab']:.2f} | "
              f"{int(p['fin_count'])} aletas {p['nose_shape']} coifa {p['nose_length']:.1f}cm | "
              f"lastro~{p['ballast_fill']:.1f}cm | {p['launch_angle']:.0f}°")
    print(f"\ntempo total: {(time.time()-t0)/3600:.2f} h", flush=True)


if __name__ == "__main__":
    main()
