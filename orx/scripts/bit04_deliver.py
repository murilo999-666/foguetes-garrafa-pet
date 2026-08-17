"""Entrega da otimização do bit04:
1. planilha xlsx com todos os testes em D:\\1-Competicoes\\OBAFOG\\foguetes\\bit04 2L script\\
2. versões .ork dos melhores designs em D:\\1-Competicoes\\OBAFOG\\foguetes\\bit04 2L script\\versoes_teste\\
3. gráficos em D:\\1-Competicoes\\OBAFOG\\foguetes\\bit04 2L script\\otimizacao\\plots\\
4. resumo textual da run
"""

import json
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

CONFIG = r"C:\Users\muril\openrocket-optimizer\config\bit04.yaml"
ROCKET_DIR = Path(r"D:\1-Competicoes\OBAFOG\foguetes\bit04 2L script")
VERSIONS_DIR = ROCKET_DIR / "versoes_teste"
TOP_N = 25

COLUMN_LABELS = {
    "iteration": "teste",
    "p_nose_length": "ogiva_cm",
    "p_ballast_mass": "lastro_g",
    "p_ballast_fill": "durepox_profundidade_cm",
    "m_ballast_mass": "durepox_massa_kg",
    "p_fin_root": "aleta_raiz_cm",
    "p_fin_tip": "aleta_ponta_cm",
    "p_fin_sweep": "aleta_enflech_cm",
    "p_fin_height": "aleta_altura_cm",
    "m_horizontal_distance": "alcance_m",
    "m_apogee": "apogeu_m",
    "m_max_velocity": "vel_max_ms",
    "m_stability_static": "estab_inicial_cal",
    "m_stability_max": "estab_pos_queima_cal",
    "m_liftoff_mass": "massa_decolagem_kg",
    "m_flight_time": "tempo_voo_s",
    "feasible": "viavel",
    "violations": "violacoes",
    "error": "erro",
}


def main() -> None:
    setup_logging()
    cfg = load_config(CONFIG)
    db = ResultsDB(cfg.db_path)
    run_id = db.latest_run_id()
    if run_id is None:
        print("Nenhuma run no banco.")
        return

    df = db.evaluations_df(run_id)
    print(f"run {run_id}: {len(df)} avaliações\n")

    # 1. planilha
    cols = [c for c in COLUMN_LABELS if c in df.columns]
    sheet = df[cols].rename(columns=COLUMN_LABELS)
    for c in sheet.columns:
        if sheet[c].dtype == float:
            sheet[c] = sheet[c].round(3)
    sheet = sheet.sort_values("alcance_m", ascending=False, na_position="last")
    xlsx = ROCKET_DIR / "bit04_otimizacao.xlsx"
    with pd.ExcelWriter(xlsx, engine="openpyxl") as writer:
        sheet.to_excel(writer, sheet_name="testes", index=False)
        ok = sheet[sheet["viavel"] == 1].head(50)
        ok.to_excel(writer, sheet_name="top50_viaveis", index=False)
    print(f"[1] planilha: {xlsx} ({len(sheet)} linhas)")

    # 2. versões .ork dos melhores
    VERSIONS_DIR.mkdir(exist_ok=True)
    okdf = df[(df["feasible"] == 1) & df["score"].notna()].sort_values("score", ascending=False)
    runner = Runner(cfg)
    param_names = [p.name for p in cfg.parameters]

    def row_params(row: pd.Series) -> dict:
        return {n: float(row[f"p_{n}"]) for n in param_names}

    saved = []
    for rank, (_, row) in enumerate(okdf.head(TOP_N).iterrows(), start=1):
        name = f"rank{rank:02d}_alcance{row['score']:.0f}m_teste{int(row['iteration'])}.ork"
        runner.save_design(row_params(row), str(VERSIONS_DIR / name))
        saved.append(name)
    best_params = row_params(okdf.iloc[0])
    runner.save_design(best_params, str(ROCKET_DIR / "bit04_otimizado.ork"))
    print(f"[2] {len(saved)} versões em {VERSIONS_DIR} + bit04_otimizado.ork")

    # 3. gráficos
    paths = generate_all_plots(db, run_id, cfg.output_dir, "alcance (m)", "maximize")
    print(f"[3] {len(paths)} gráficos em {Path(cfg.output_dir) / 'plots'}")

    # 4. resumo + validação do melhor design re-simulado
    print()
    print(summarize_run(db, run_id))
    print()
    check = runner.evaluate(best_params)
    m = check.metrics
    print("=== VALIDAÇÃO do melhor design (re-simulado) ===")
    for key in ("horizontal_distance", "apogee", "max_velocity", "stability_static",
                "stability_max", "liftoff_mass", "flight_time"):
        print(f"  {key}: {m[key]:.3f}" if m.get(key) is not None else f"  {key}: n/a")
    db.close()


if __name__ == "__main__":
    main()
