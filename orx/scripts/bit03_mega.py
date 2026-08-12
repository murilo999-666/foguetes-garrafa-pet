"""Mega-otimização do bit03: ~100.000 simulações em duas estratégias +
validação de robustez multi-vento + entrega completa.

Etapas:
  A. adaptive 65.000 avaliações (exploração 15% / TPE em blocos 60% / refino 25%)
  B. genetic  35.000 avaliações (população 64)
  C. top-30 global re-simulado com 20 ventos (seeds) -> campeão ROBUSTO
  D. planilha, .ork das versões, gráficos, resumo
"""

import dataclasses
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from orx.analysis.compare import compare_runs, summarize_run
from orx.config import load_config
from orx.config.loader import BatchConfig, OptimizerConfig
from orx.optimizer.engine import run_optimization
from orx.plots.charts import generate_all_plots, plot_runs_comparison
from orx.results.db import ResultsDB
from orx.simulation.runner import Runner
from orx.utils.logging import setup_logging

CONFIG = r"C:\Users\muril\openrocket-optimizer\config\bit03.yaml"
TEST_MODE = "--test" in sys.argv  # ensaio rápido do pipeline completo


def _arg(name: str, default: int) -> int:
    if name in sys.argv:
        return int(sys.argv[sys.argv.index(name) + 1])
    return default


ROBUST_SEEDS = list(range(101, 121 if not TEST_MODE else 104))
TOP_GLOBAL = 30 if not TEST_MODE else 5
BUDGET_A = _arg("--budget-a", 65_000 if not TEST_MODE else 300)
BUDGET_B = _arg("--budget-b", 35_000 if not TEST_MODE else 200)
SEED_A = _arg("--seed-a", 7)


def progress_factory(tag: str):
    def progress(i: int, total: int, value, best) -> None:
        if i % max(1, total // 100) == 0 or i == total:
            best_s = f"{best:.1f}" if best is not None and best > -1e8 else "n/a"
            print(f"[{tag} {i}/{total}] melhor={best_s}", flush=True)

    return progress


def main() -> None:
    setup_logging()
    cfg = load_config(CONFIG)
    cfg = dataclasses.replace(cfg, batch=BatchConfig(workers=6))
    rocket_dir = Path(cfg.base_ork).parent
    stem = Path(cfg.base_ork).stem
    t0 = time.time()

    # ---------- A. adaptativo gigante ----------
    run_a = None
    if BUDGET_A > 0:
        cfg_a = dataclasses.replace(cfg, optimizer=OptimizerConfig(
            algorithm="adaptive", max_evaluations=BUDGET_A, seed=SEED_A, profile="balanced",
            options={"fractions": [0.15, 0.60], "chunk_size": 3000 if not TEST_MODE else 80},
        ))
        run_a = run_optimization(cfg_a, run_name=f"mega-adaptive-{BUDGET_A}",
                                 progress=progress_factory("A"))

    # ---------- B. genético ----------
    run_b = None
    if BUDGET_B > 0:
        cfg_b = dataclasses.replace(cfg, optimizer=OptimizerConfig(
            algorithm="genetic", max_evaluations=BUDGET_B, seed=21,
            options={"population": 64 if not TEST_MODE else 16, "elite": 4, "mutation_rate": 0.3},
        ))
        run_b = run_optimization(cfg_b, run_name=f"mega-genetic-{BUDGET_B}",
                                 progress=progress_factory("B"))

    print(f"\nruns concluídas em {(time.time() - t0) / 3600:.2f} h", flush=True)

    # ---------- C. robustez multi-vento ----------
    db = ResultsDB(cfg.db_path)
    param_names = [p.name for p in cfg.parameters]
    frames = []
    for rid in db.runs_df()["id"]:
        d = db.evaluations_df(int(rid))
        if not d.empty:
            d["run_id"] = rid
            frames.append(d[(d["feasible"] == 1) & d["score"].notna()])
    all_ok = pd.concat(frames, ignore_index=True).sort_values("score", ascending=False)

    seen, top_rows = set(), []
    for _, row in all_ok.iterrows():
        key = tuple(round(float(row[f"p_{n}"]), 3) if isinstance(row[f"p_{n}"], float)
                    else row[f"p_{n}"] for n in param_names)
        if key in seen:
            continue
        seen.add(key)
        top_rows.append(row)
        if len(top_rows) >= TOP_GLOBAL:
            break

    print(f"\nrobustez: top-{len(top_rows)} global × {len(ROBUST_SEEDS)} ventos", flush=True)
    runner = Runner(cfg)

    def row_params(row) -> dict:
        return {n: (float(row[f"p_{n}"]) if isinstance(row[f"p_{n}"], (int, float, np.floating))
                    else row[f"p_{n}"]) for n in param_names}

    robust = []
    for row in top_rows:
        params = row_params(row)
        dists = []
        for seed in ROBUST_SEEDS:
            res = runner.evaluate(params, sim_overrides={"random_seed": seed})
            if res.ok and res.metrics.get("horizontal_distance") is not None:
                v = res.metrics["horizontal_distance"]
                viol = []
                from orx.objectives.objective import Constraints
                viol = Constraints(cfg.constraints).violations(res.metrics)
                dists.append(v if not viol else np.nan)
            else:
                dists.append(np.nan)
        arr = np.array(dists, dtype=float)
        valid = arr[np.isfinite(arr)]
        robust.append({
            **{n: params[n] for n in param_names},
            "alcance_seed42": float(row["score"]),
            "alcance_medio": float(valid.mean()) if valid.size else np.nan,
            "alcance_desvio": float(valid.std()) if valid.size else np.nan,
            "alcance_pior": float(valid.min()) if valid.size else np.nan,
            "ventos_validos": int(valid.size),
            "run_id": int(row["run_id"]),
            "teste": int(row["iteration"]),
        })
    rdf = pd.DataFrame(robust).sort_values("alcance_medio", ascending=False)
    champion = rdf.iloc[0]
    champion_params = {n: champion[n] for n in param_names}
    champion_params = {k: (float(v) if isinstance(v, (int, float, np.floating)) else v)
                       for k, v in champion_params.items()}

    # ---------- D. entrega ----------
    versions = rocket_dir / "versoes_teste"
    versions.mkdir(exist_ok=True)
    for rank, (_, r) in enumerate(rdf.head(25).iterrows(), start=1):
        p = {n: (float(r[n]) if isinstance(r[n], (int, float, np.floating)) else r[n])
             for n in param_names}
        name = f"robusto{rank:02d}_media{r['alcance_medio']:.0f}m_desvio{r['alcance_desvio']:.0f}.ork"
        runner.save_design(p, str(versions / name))
    runner.save_design(champion_params, str(rocket_dir / f"{stem}_otimizado.ork"))

    xlsx = rocket_dir / f"{stem}_otimizacao.xlsx"
    top1000 = all_ok.head(1000)
    cols = ["run_id", "iteration", "score"] + [f"p_{n}" for n in param_names]
    with pd.ExcelWriter(xlsx, engine="openpyxl") as writer:
        rdf.to_excel(writer, sheet_name="robustez_top30", index=False)
        top1000[cols].rename(columns={f"p_{n}": n for n in param_names}).to_excel(
            writer, sheet_name="top1000_seed42", index=False)
        db.runs_df()[["id", "name", "algorithm", "status", "notes"]].to_excel(
            writer, sheet_name="resumo_runs", index=False)
    full_csv = rocket_dir / f"{stem}_otimizacao_completa.csv"
    pd.concat([db.evaluations_df(int(r)) for r in db.runs_df()["id"]],
              ignore_index=True).to_csv(full_csv, index=False, encoding="utf-8")

    for rid in (run_a, run_b):
        if rid is not None:
            generate_all_plots(db, rid, cfg.output_dir, "alcance (m)", "maximize")
    plot_runs_comparison(db, [int(r) for r in db.runs_df()["id"]],
                         Path(cfg.output_dir) / "plots" / "comparacao_runs.png")

    for rid in (run_a, run_b):
        if rid is not None:
            print("\n" + summarize_run(db, rid))
    print("\n" + compare_runs(db, [int(r) for r in db.runs_df()["id"]]))
    print("\n=== CAMPEÃO ROBUSTO (média em 20 ventos) ===")
    for k, v in champion_params.items():
        print(f"  {k} = {v:.4g}" if isinstance(v, float) else f"  {k} = {v}")
    print(f"  alcance médio: {champion['alcance_medio']:.1f} m "
          f"(± {champion['alcance_desvio']:.1f}) | pior vento: {champion['alcance_pior']:.1f} m "
          f"| seed42: {champion['alcance_seed42']:.1f} m")
    print(f"\ntempo total: {(time.time() - t0) / 3600:.2f} h")
    db.close()


if __name__ == "__main__":
    main()
