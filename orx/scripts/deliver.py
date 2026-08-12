"""Entrega genérica de uma otimização:
    python scripts/deliver.py <config.yaml> [--top 25] [--run ID]

1. planilha xlsx na pasta do .ork base;
2. versões .ork dos melhores em <pasta_do_ork>/versoes_teste/;
3. <nome>_otimizado.ork na pasta do .ork;
4. gráficos em output_dir/plots/;
5. resumo textual + validação re-simulada do melhor.
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from orx.analysis.compare import summarize_run
from orx.config import load_config
from orx.plots.charts import generate_all_plots
from orx.results.db import ResultsDB
from orx.simulation.runner import Runner
from orx.utils.logging import setup_logging

METRIC_LABELS = {
    "m_horizontal_distance": "alcance_m",
    "m_apogee": "apogeu_m",
    "m_max_velocity": "vel_max_ms",
    "m_stability_static": "estab_inicial_cal",
    "m_stability_max": "estab_pos_queima_cal",
    "m_ballast_mass": "durepox_massa_kg",
    "m_liftoff_mass": "massa_decolagem_kg",
    "m_flight_time": "tempo_voo_s",
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("config")
    ap.add_argument("--top", type=int, default=25)
    ap.add_argument("--run", type=int, default=None)
    args = ap.parse_args()

    setup_logging()
    cfg = load_config(args.config)
    rocket_path = Path(cfg.base_ork)
    rocket_dir = rocket_path.parent
    stem = rocket_path.stem

    db = ResultsDB(cfg.db_path)
    run_id = args.run or db.latest_run_id()
    if run_id is None:
        print("Nenhuma run no banco.")
        return
    df = db.evaluations_df(run_id)
    print(f"run {run_id}: {len(df)} avaliações\n")

    # 1. planilha
    param_names = [p.name for p in cfg.parameters]
    cols = (["iteration"] + [f"p_{n}" for n in param_names if f"p_{n}" in df.columns]
            + [c for c in METRIC_LABELS if c in df.columns]
            + ["feasible", "violations", "error"])
    labels = {"iteration": "teste", "feasible": "viavel", "violations": "violacoes",
              "error": "erro", **METRIC_LABELS,
              **{f"p_{n}": n for n in param_names}}
    sheet = df[cols].rename(columns=labels)
    for c in sheet.columns:
        if sheet[c].dtype == float:
            sheet[c] = sheet[c].round(3)
    sheet = sheet.sort_values("alcance_m", ascending=False, na_position="last")
    xlsx = rocket_dir / f"{stem}_otimizacao.xlsx"
    with pd.ExcelWriter(xlsx, engine="openpyxl") as writer:
        sheet.to_excel(writer, sheet_name="testes", index=False)
        sheet[sheet["viavel"] == 1].head(50).to_excel(writer, sheet_name="top50_viaveis", index=False)
    print(f"[1] planilha: {xlsx} ({len(sheet)} linhas)")

    # 2. versões .ork
    versions_dir = rocket_dir / "versoes_teste"
    versions_dir.mkdir(exist_ok=True)
    okdf = df[(df["feasible"] == 1) & df["score"].notna()].sort_values("score", ascending=False)
    if okdf.empty:
        print("Nenhuma avaliação viável!")
        return
    runner = Runner(cfg)

    def row_params(row: pd.Series) -> dict:
        out = {}
        for n in param_names:
            v = row[f"p_{n}"]
            out[n] = float(v) if isinstance(v, (int, float)) else v
        return out

    for rank, (_, row) in enumerate(okdf.head(args.top).iterrows(), start=1):
        name = f"rank{rank:02d}_alcance{row['score']:.0f}m_teste{int(row['iteration'])}.ork"
        runner.save_design(row_params(row), str(versions_dir / name))
    best_params = row_params(okdf.iloc[0])
    runner.save_design(best_params, str(rocket_dir / f"{stem}_otimizado.ork"))
    print(f"[2] top-{args.top} em {versions_dir} + {stem}_otimizado.ork")

    # 3. gráficos
    paths = generate_all_plots(db, run_id, cfg.output_dir, "alcance (m)", "maximize")
    print(f"[3] {len(paths)} gráficos em {Path(cfg.output_dir) / 'plots'}")

    # 4. resumo + validação
    print()
    print(summarize_run(db, run_id))
    print("\n=== MELHOR DESIGN ===")
    for k, v in best_params.items():
        print(f"  {k} = {v:.4g}" if isinstance(v, float) else f"  {k} = {v}")
    check = runner.evaluate(best_params)
    m = check.metrics
    print("=== VALIDAÇÃO (re-simulado) ===")
    for key in ("horizontal_distance", "apogee", "max_velocity", "stability_static",
                "stability_max", "ballast_mass", "liftoff_mass", "flight_time"):
        v = m.get(key)
        print(f"  {key}: {v:.3f}" if v is not None else f"  {key}: n/a")
    db.close()


if __name__ == "__main__":
    main()
