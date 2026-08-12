"""LABORATÓRIO — 500.000 simulações de exploração livre.

Roda em fases com estratégias diferentes e, ao FIM DE CADA FASE, grava os
resultados na pasta (planilha, CSV, gráficos e relatório). Assim o material
vai aparecendo mesmo que o processo seja interrompido no meio.

Fases (500 mil no total):
  1. random   150k — mapa imparcial do espaço (é o que mais gera informação)
  2. adaptive 175k — busca adaptativa com estreitamento
  3. genetic  125k — evolução populacional
  4. optuna    50k — modelagem bayesiana (TPE)

Ao final: análise de sensibilidade, comparação entre estratégias e validação
de robustez multi-vento dos melhores.
"""

import dataclasses
import sys
import time
import traceback
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from orx.analysis.compare import compare_runs, summarize_run
from orx.analysis.sensitivity import parameter_importance
from orx.config import load_config
from orx.config.loader import BatchConfig, OptimizerConfig
from orx.objectives.objective import Constraints
from orx.optimizer.engine import run_optimization
from orx.plots.charts import generate_all_plots, plot_runs_comparison
from orx.results.db import ResultsDB
from orx.simulation.runner import Runner
from orx.utils.logging import setup_logging

CONFIG = r"C:\Users\muril\openrocket-optimizer\config\laboratorio.yaml"
TEST = "--test" in sys.argv

# (algoritmo, avaliações, seed, opções)
FASES = [
    ("random",   150_000, 11, {}),
    ("adaptive", 175_000, 22, {"fractions": [0.25, 0.55], "chunk_size": 4000}),
    ("genetic",  125_000, 33, {"population": 120, "elite": 6, "mutation_rate": 0.35}),
    ("optuna",    50_000, 44, {"sampler": "tpe", "n_startup_trials": 500}),
]
if TEST:
    FASES = [(a, 200, s, o) for a, _, s, o in FASES]


def progresso(tag: str):
    def p(i, total, valor, melhor):
        if i % max(1, total // 200) == 0 or i == total:
            m = f"{melhor:.1f}" if melhor is not None and melhor > -1e8 else "n/a"
            print(f"[{tag} {i}/{total}] melhor={m}", flush=True)
    return p


def checkpoint(cfg, db: ResultsDB, pasta: Path, param_nomes: list[str]) -> None:
    """Grava planilha, CSV, gráficos e relatório com TUDO que existe até agora."""
    frames = []
    for rid in db.runs_df()["id"]:
        d = db.evaluations_df(int(rid))
        if not d.empty and "score" in d:
            d = d.copy()
            d["run_id"] = rid
            frames.append(d)
    if not frames:
        return
    todos = pd.concat(frames, ignore_index=True)
    viaveis = todos[(todos["feasible"] == 1) & todos["score"].notna()].sort_values(
        "score", ascending=False)

    cols = ["run_id", "iteration", "score"] + [f"p_{n}" for n in param_nomes if f"p_{n}" in todos]
    ren = {f"p_{n}": n for n in param_nomes}

    with pd.ExcelWriter(pasta / "LABORATORIO_resultados.xlsx", engine="openpyxl") as w:
        viaveis.head(2000)[cols].rename(columns=ren).to_excel(w, sheet_name="top2000", index=False)
        db.runs_df()[["id", "name", "algorithm", "status", "notes"]].to_excel(
            w, sheet_name="estrategias", index=False)
        imp = parameter_importance(viaveis)
        if imp:
            (pd.DataFrame(sorted(imp.items(), key=lambda kv: -kv[1]),
                          columns=["parametro", "influencia"])
             .to_excel(w, sheet_name="influencia", index=False))
        # estatística por escolha categórica (que material/motor/forma rende mais)
        linhas = []
        for c in [c for c in viaveis.columns if c.startswith("p_")]:
            s = viaveis[c]
            if s.dtype == object and s.nunique() <= 12:
                g = viaveis.groupby(c)["score"].agg(["count", "mean", "max"])
                for idx, r in g.iterrows():
                    linhas.append({"parametro": c[2:], "valor": idx, "n": int(r["count"]),
                                   "media_m": round(r["mean"], 1), "melhor_m": round(r["max"], 1)})
        if linhas:
            pd.DataFrame(linhas).to_excel(w, sheet_name="categorias", index=False)

    viaveis[cols].rename(columns=ren).to_csv(
        pasta / "LABORATORIO_viaveis.csv", index=False, encoding="utf-8")

    relatorio = [f"LABORATÓRIO — {len(todos):,} simulações ({len(viaveis):,} viáveis)",
                 f"gerado em {time.strftime('%d/%m/%Y %H:%M')}", ""]
    for rid in db.runs_df()["id"]:
        try:
            relatorio.append(summarize_run(db, int(rid)))
            relatorio.append("")
        except Exception:
            pass
    try:
        relatorio.append(compare_runs(db, [int(r) for r in db.runs_df()["id"]]))
    except Exception:
        pass
    (pasta / "LABORATORIO_relatorio.txt").write_text("\n".join(relatorio), encoding="utf-8")

    for rid in db.runs_df()["id"]:
        try:
            generate_all_plots(db, int(rid), str(pasta / "simulacoes"),
                               "alcance (m)", "maximize")
        except Exception:
            pass
    try:
        plot_runs_comparison(db, [int(r) for r in db.runs_df()["id"]],
                             pasta / "simulacoes" / "plots" / "comparacao_estrategias.png")
    except Exception:
        pass
    print(f"  >> checkpoint gravado ({len(todos):,} sims)", flush=True)


def main() -> None:
    setup_logging()
    cfg_base = load_config(CONFIG)
    cfg_base = dataclasses.replace(cfg_base, batch=BatchConfig(workers=4))
    pasta = Path(cfg_base.base_ork).parent
    nomes = [p.name for p in cfg_base.parameters]
    t0 = time.time()

    for algo, orcamento, seed, opts in FASES:
        print(f"\n===== FASE {algo} ({orcamento:,} avaliações) =====", flush=True)
        try:
            cfg = dataclasses.replace(cfg_base, optimizer=OptimizerConfig(
                algorithm=algo, max_evaluations=orcamento, seed=seed,
                profile="balanced", options=opts))
            run_optimization(cfg, run_name=f"lab-{algo}-{orcamento}",
                             progress=progresso(algo))
        except Exception:
            print(f"!! fase {algo} falhou:", flush=True)
            traceback.print_exc()
        try:
            db = ResultsDB(cfg_base.db_path)
            checkpoint(cfg_base, db, pasta, nomes)
            db.close()
        except Exception:
            print("!! checkpoint falhou:", flush=True)
            traceback.print_exc()
        print(f"   tempo acumulado: {(time.time()-t0)/3600:.2f} h", flush=True)

    # ---------- validação final de robustez dos melhores ----------
    try:
        db = ResultsDB(cfg_base.db_path)
        frames = [db.evaluations_df(int(r)) for r in db.runs_df()["id"]]
        todos = pd.concat([f for f in frames if not f.empty], ignore_index=True)
        ok = todos[(todos["feasible"] == 1) & todos["score"].notna()].sort_values(
            "score", ascending=False)
        runner, cons = Runner(cfg_base), Constraints(cfg_base.constraints)
        vistos, top = set(), []
        for _, row in ok.iterrows():
            p = {n: (float(row[f"p_{n}"]) if not isinstance(row[f"p_{n}"], str)
                     else row[f"p_{n}"]) for n in nomes}
            chave = tuple(round(v, 2) if isinstance(v, float) else v for v in p.values())
            if chave in vistos:
                continue
            vistos.add(chave)
            top.append(p)
            if len(top) >= 20:
                break
        linhas = []
        for p in top:
            d = []
            for s in range(101, 121):
                r = runner.evaluate(p, sim_overrides={"random_seed": s})
                if r.ok and r.metrics.get("horizontal_distance") is not None \
                        and not cons.violations(r.metrics):
                    d.append(r.metrics["horizontal_distance"])
            a = np.array(d)
            linhas.append({**p, "alcance_medio": float(a.mean()) if a.size else np.nan,
                           "desvio": float(a.std()) if a.size else np.nan,
                           "pior": float(a.min()) if a.size else np.nan,
                           "ventos_ok": int(a.size)})
        rdf = pd.DataFrame(linhas).sort_values("alcance_medio", ascending=False)
        rdf.to_csv(pasta / "LABORATORIO_top20_robustez.csv", index=False, encoding="utf-8")
        for i, (_, r) in enumerate(rdf.head(10).iterrows(), 1):
            p = {n: (float(r[n]) if not isinstance(r[n], str) else r[n]) for n in nomes}
            runner.save_design(p, str(pasta / f"lab_top{i:02d}_{r['alcance_medio']:.0f}m.ork"))
        db.close()
        print("\n>> robustez final gravada", flush=True)
    except Exception:
        print("!! robustez final falhou:", flush=True)
        traceback.print_exc()

    print(f"\nLABORATÓRIO CONCLUÍDO em {(time.time()-t0)/3600:.2f} h", flush=True)


if __name__ == "__main__":
    main()
