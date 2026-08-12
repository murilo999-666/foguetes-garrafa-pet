"""Otimização final do foguete realista (garrafa 2L + motor físico):
10.000 avaliações adaptativas (validação/ajuste fino) + robustez multi-vento
+ bracket de incerteza (motor físico vs. motor -calib antigo do Murilo).
"""

import dataclasses
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from orx.analysis.compare import summarize_run
from orx.config import load_config
from orx.config.loader import BatchConfig, OptimizerConfig
from orx.objectives.objective import Constraints
from orx.optimizer.engine import run_optimization
from orx.plots.charts import generate_all_plots
from orx.results.db import ResultsDB
from orx.simulation.runner import Runner
from orx.utils.logging import setup_logging

CONFIG = r"C:\Users\muril\openrocket-optimizer\config\foguete_real_materiais.yaml"
TEST_MODE = "--test" in sys.argv
ROBUST_SEEDS = list(range(101, 121 if not TEST_MODE else 104))
TOP_GLOBAL = 20 if not TEST_MODE else 5
BUDGET = 10_000 if not TEST_MODE else 300


def progress(i: int, total: int, value, best) -> None:
    if i % max(1, total // 100) == 0 or i == total:
        best_s = f"{best:.1f}" if best is not None and best > -1e8 else "n/a"
        print(f"[{i}/{total}] melhor={best_s}", flush=True)


def main() -> None:
    setup_logging()
    cfg = load_config(CONFIG)
    cfg = dataclasses.replace(cfg, batch=BatchConfig(workers=4), optimizer=OptimizerConfig(
        algorithm="adaptive", max_evaluations=BUDGET, seed=42, profile="balanced",
        options={"chunk_size": 2000},
    ))
    rocket_dir = Path(cfg.base_ork).parent
    t0 = time.time()

    run_id = run_optimization(cfg, run_name=f"MATERIAIS-REAIS-{BUDGET}", progress=progress)
    print(f"\nrun {run_id} concluída em {(time.time() - t0) / 60:.1f} min", flush=True)

    db = ResultsDB(cfg.db_path)
    param_names = [p.name for p in cfg.parameters]
    df = db.evaluations_df(run_id)
    ok = df[(df["feasible"] == 1) & df["score"].notna()].sort_values("score", ascending=False)
    print(f"avaliações viáveis: {len(ok)}", flush=True)

    def row_params(row) -> dict:
        return {n: (float(row[f"p_{n}"]) if isinstance(row[f"p_{n}"], (int, float, np.floating))
                    else row[f"p_{n}"]) for n in param_names}

    # ---------- robustez multi-vento ----------
    seen, top_rows = set(), []
    for _, row in ok.iterrows():
        p = row_params(row)
        key = tuple(round(v, 3) if isinstance(v, float) else v for v in p.values())
        if key in seen:
            continue
        seen.add(key)
        top_rows.append(row)
        if len(top_rows) >= TOP_GLOBAL:
            break

    print(f"robustez: top-{len(top_rows)} × {len(ROBUST_SEEDS)} ventos", flush=True)
    runner = Runner(cfg)
    cons = Constraints(cfg.constraints)
    robust = []
    for row in top_rows:
        params = row_params(row)
        dists = []
        for seed in ROBUST_SEEDS:
            res = runner.evaluate(params, sim_overrides={"random_seed": seed})
            if res.ok and res.metrics.get("horizontal_distance") is not None:
                viol = cons.violations(res.metrics)
                dists.append(res.metrics["horizontal_distance"] if not viol else np.nan)
            else:
                dists.append(np.nan)
        arr = np.array(dists, dtype=float)
        valid = arr[np.isfinite(arr)]
        robust.append({
            **params,
            "alcance_seed42": float(row["score"]),
            "alcance_medio": float(valid.mean()) if valid.size else np.nan,
            "alcance_desvio": float(valid.std()) if valid.size else np.nan,
            "alcance_pior": float(valid.min()) if valid.size else np.nan,
            "ventos_validos": int(valid.size),
            "teste": int(row["iteration"]),
        })
    rdf = pd.DataFrame(robust)
    if rdf.empty or "alcance_medio" not in rdf:
        print("ERRO: nenhuma avaliacao viavel"); db.close(); return
    rdf = rdf.sort_values("alcance_medio", ascending=False)
    champion = rdf.iloc[0]
    champion_params = {n: (float(champion[n]) if isinstance(champion[n], (int, float, np.floating))
                           else champion[n]) for n in param_names}

    # ---------- entrega ----------
    versions = rocket_dir / "versoes_teste"
    versions.mkdir(exist_ok=True)
    for rank, (_, r) in enumerate(rdf.head(15).iterrows(), start=1):
        p = {n: (float(r[n]) if isinstance(r[n], (int, float, np.floating)) else r[n])
             for n in param_names}
        runner.save_design(p, str(versions / f"matreal{rank:02d}_media{r['alcance_medio']:.0f}m.ork"))
    runner.save_design(champion_params, str(rocket_dir / "foguete_real_MATERIAIS_REAIS.ork"))

    xlsx = rocket_dir / "foguete_real_MATERIAIS_otimizacao.xlsx"
    cols = ["iteration", "score"] + [f"p_{n}" for n in param_names]
    with pd.ExcelWriter(xlsx, engine="openpyxl") as writer:
        rdf.to_excel(writer, sheet_name="robustez_top20", index=False)
        ok.head(1000)[cols].rename(columns={f"p_{n}": n for n in param_names}).to_excel(
            writer, sheet_name="top1000_seed42", index=False)
    pd.concat([db.evaluations_df(int(r)) for r in db.runs_df()["id"]], ignore_index=True).to_csv(
        rocket_dir / "foguete_real_MATERIAIS_completa.csv", index=False, encoding="utf-8")
    generate_all_plots(db, run_id, cfg.output_dir, "alcance (m)", "maximize")

    print("\n" + summarize_run(db, run_id))
    print("\n=== CAMPEÃO ROBUSTO (motor FÍSICO, média em 20 ventos) ===")
    for k, v in champion_params.items():
        print(f"  {k} = {v:.4g}" if isinstance(v, float) else f"  {k} = {v}")
    print(f"  alcance médio: {champion['alcance_medio']:.1f} m (± {champion['alcance_desvio']:.1f}) "
          f"| pior vento: {champion['alcance_pior']:.1f} m")

    # ---------- bracket: mesmo foguete com o motor -calib antigo ----------
    calib_params = dict(champion_params)
    calib_params["motor"] = "VinagreCO2-1_5L-calib"
    vals = []
    for seed in ROBUST_SEEDS:
        res = runner.evaluate(calib_params, sim_overrides={"random_seed": seed})
        if res.ok and res.metrics.get("horizontal_distance") is not None:
            vals.append(res.metrics["horizontal_distance"])
    if vals:
        arr = np.array(vals)
        print(f"\n=== BRACKET otimista: mesmo foguete com o motor 'VinagreCO2-1_5L-calib' antigo ===")
        print(f"  alcance médio: {arr.mean():.1f} m (± {arr.std():.1f})")
    print(f"\ntempo total: {(time.time() - t0) / 60:.1f} min")
    db.close()


if __name__ == "__main__":
    main()
