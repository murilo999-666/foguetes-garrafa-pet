"""Otimização livre GRANDE do bit05 (garrafa reduzida ~1,8L):
adaptive 25k + genetic 15k = 40.000 avaliações + robustez multi-vento.
Toda a liberdade: ogiva, lastro, aletas, materiais, motor (família bit05),
ângulo de lançamento. Grava no MESMO banco do modelo humano (run 1) para
comparação por test id.
"""

import dataclasses
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from orx.analysis.compare import compare_runs, summarize_run
from orx.config import load_config
from orx.config.loader import BatchConfig, OptimizerConfig
from orx.objectives.objective import Constraints
from orx.optimizer.engine import run_optimization
from orx.plots.charts import generate_all_plots, plot_runs_comparison
from orx.results.db import ResultsDB
from orx.simulation.runner import Runner
from orx.utils.logging import setup_logging

CONFIG = r"C:\Users\muril\openrocket-optimizer\config\bit05.yaml"
TEST_MODE = "--test" in sys.argv
ROBUST_SEEDS = list(range(101, 121 if not TEST_MODE else 104))
TOP_GLOBAL = 25 if not TEST_MODE else 5
BUDGET_A = 25_000 if not TEST_MODE else 250
BUDGET_B = 15_000 if not TEST_MODE else 150


def progress_factory(tag: str):
    def p(i, total, value, best):
        if i % max(1, total // 100) == 0 or i == total:
            bs = f"{best:.1f}" if best is not None and best > -1e8 else "n/a"
            print(f"[{tag} {i}/{total}] melhor={bs}", flush=True)
    return p


def main() -> None:
    setup_logging()
    cfg = load_config(CONFIG)
    cfg = dataclasses.replace(cfg, batch=BatchConfig(workers=4))
    rocket_dir = Path(cfg.base_ork).parent
    t0 = time.time()

    cfg_a = dataclasses.replace(cfg, optimizer=OptimizerConfig(
        algorithm="adaptive", max_evaluations=BUDGET_A, seed=7, profile="balanced",
        options={"fractions": [0.15, 0.60], "chunk_size": 3000 if not TEST_MODE else 80}))
    run_a = run_optimization(cfg_a, run_name=f"bit05-adaptive-{BUDGET_A}", progress=progress_factory("A"))

    cfg_b = dataclasses.replace(cfg, optimizer=OptimizerConfig(
        algorithm="genetic", max_evaluations=BUDGET_B, seed=21,
        options={"population": 80 if not TEST_MODE else 16, "elite": 5, "mutation_rate": 0.3}))
    run_b = run_optimization(cfg_b, run_name=f"bit05-genetic-{BUDGET_B}", progress=progress_factory("B"))

    print(f"\notimizacao concluida em {(time.time()-t0)/3600:.2f} h", flush=True)

    db = ResultsDB(cfg.db_path)
    pn = [p.name for p in cfg.parameters]
    frames = []
    for rid in db.runs_df()["id"]:
        d = db.evaluations_df(int(rid))
        if not d.empty and "score" in d:
            d = d[(d["feasible"] == 1) & d["score"].notna()]
            if not d.empty:
                d = d.copy(); d["run_id"] = rid; frames.append(d)
    all_ok = pd.concat(frames, ignore_index=True).sort_values("score", ascending=False)

    def rowp(row):
        return {n: (float(row[f"p_{n}"]) if not isinstance(row[f"p_{n}"], str) else row[f"p_{n}"]) for n in pn}

    seen, top = set(), []
    for _, row in all_ok.iterrows():
        p = rowp(row); key = tuple(round(v, 3) if isinstance(v, float) else v for v in p.values())
        if key in seen: continue
        seen.add(key); top.append(row)
        if len(top) >= TOP_GLOBAL: break

    print(f"robustez: top-{len(top)} x {len(ROBUST_SEEDS)} ventos", flush=True)
    runner = Runner(cfg); cons = Constraints(cfg.constraints)
    robust = []
    for row in top:
        params = rowp(row); dists = []
        for seed in ROBUST_SEEDS:
            res = runner.evaluate(params, sim_overrides={"random_seed": seed})
            if res.ok and res.metrics.get("horizontal_distance") is not None and not cons.violations(res.metrics):
                dists.append(res.metrics["horizontal_distance"])
        arr = np.array(dists)
        robust.append({**params, "alcance_medio": float(arr.mean()) if arr.size else np.nan,
                       "alcance_desvio": float(arr.std()) if arr.size else np.nan,
                       "alcance_pior": float(arr.min()) if arr.size else np.nan,
                       "ventos_validos": int(arr.size), "run_id": int(row["run_id"]), "teste": int(row["iteration"])})
    rdf = pd.DataFrame(robust).sort_values("alcance_medio", ascending=False)
    champ = rdf.iloc[0]
    cp = {n: (float(champ[n]) if not isinstance(champ[n], str) else champ[n]) for n in pn}

    versions = rocket_dir / "versoes_teste"; versions.mkdir(exist_ok=True)
    for rank, (_, r) in enumerate(rdf.head(15).iterrows(), 1):
        p = {n: (float(r[n]) if not isinstance(r[n], str) else r[n]) for n in pn}
        runner.save_design(p, str(versions / f"robusto{rank:02d}_media{r['alcance_medio']:.0f}m.ork"))
    runner.save_design(cp, str(rocket_dir / "foguete_bit05_OTIMIZADO.ork"))

    with pd.ExcelWriter(rocket_dir / "bit05_otimizacao.xlsx", engine="openpyxl") as w:
        rdf.to_excel(w, sheet_name="robustez_top25", index=False)
        all_ok.head(1000)[["run_id","iteration","score"]+[f"p_{n}" for n in pn]].rename(
            columns={f"p_{n}": n for n in pn}).to_excel(w, sheet_name="top1000", index=False)
        db.runs_df()[["id","name","algorithm","status","notes"]].to_excel(w, sheet_name="runs", index=False)
    pd.concat([db.evaluations_df(int(r)) for r in db.runs_df()["id"]], ignore_index=True).to_csv(
        rocket_dir / "bit05_otimizacao_completa.csv", index=False, encoding="utf-8")

    for rid in (run_a, run_b):
        generate_all_plots(db, rid, cfg.output_dir, "alcance (m)", "maximize")
    plot_runs_comparison(db, [int(r) for r in db.runs_df()["id"]], Path(cfg.output_dir) / "plots" / "comparacao_runs.png")

    for rid in (run_a, run_b):
        print("\n" + summarize_run(db, rid))
    print("\n=== CAMPEAO OTIMIZADO bit05 (media 20 ventos) ===")
    for k, v in cp.items():
        print(f"  {k} = {v:.4g}" if isinstance(v, float) else f"  {k} = {v}")
    print(f"  alcance medio={champ['alcance_medio']:.1f} m (+-{champ['alcance_desvio']:.1f}) pior={champ['alcance_pior']:.1f} m")
    print(f"\ntempo total: {(time.time()-t0)/3600:.2f} h")
    db.close()


if __name__ == "__main__":
    main()
