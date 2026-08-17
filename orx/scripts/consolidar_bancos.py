"""Consolida TODOS os bancos SQLite da OBAFOG num resumo único e num Excel
mestre, para o Murilo acessar tudo de um lugar só.

Gera em D:\\1-Competicoes\\OBAFOG\\:
  - _TODOS_OS_TESTES.xlsx  (aba 'runs' = todos os experimentos; aba 'melhores'
    = melhor design de cada run)
  - imprime a tabela resumo no terminal
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from orx.results.db import ResultsDB

OBAFOG = Path(r"D:\1-Competicoes\OBAFOG")
# (rótulo do foguete, caminho do banco)
BANCOS = [
    ("bit03 2L real (corpo original)", OBAFOG / "bit03 2L real/otimizacao/orx.sqlite"),
    ("bit03 2L real (arquitetura livre)", OBAFOG / "bit03 2L real/otimizacao_pet/orx.sqlite"),
    ("bit04 2L script (versão antiga)", OBAFOG / "bit04 2L script/otimizacao/orx.sqlite"),
    ("bit04 2L script (estudo garrafa 2L)", OBAFOG / "bit04 2L script/foguete_real/otimizacao/orx.sqlite"),
    ("bit06 1,8L script (garrafa reduzida)", OBAFOG / "bit06 1,8L script/simulacoes/orx.sqlite"),
]


def main() -> None:
    runs_rows, best_rows = [], []
    for rotulo, caminho in BANCOS:
        if not caminho.exists():
            continue
        db = ResultsDB(str(caminho))
        runs = db.runs_df()
        for _, r in runs.iterrows():
            rid = int(r["id"])
            n = db.count_evaluations(rid)
            best = db.best_evaluation(rid, r["direction"] or "maximize")
            runs_rows.append({
                "foguete": rotulo, "banco": str(caminho), "run_id": rid,
                "nome": r["name"], "algoritmo": r["algorithm"], "status": r["status"],
                "objetivo": r["objective"], "n_testes": n,
                "melhor_alcance_m": round(best["score"], 1) if best else None,
            })
            if best:
                row = {"foguete": rotulo, "run_id": rid, "nome": r["name"],
                       "melhor_alcance_m": round(best["score"], 1)}
                row.update({f"p_{k}": v for k, v in best["params"].items()})
                best_rows.append(row)
        db.close()

    runs_df = pd.DataFrame(runs_rows)
    best_df = pd.DataFrame(best_rows)

    out = OBAFOG / "_TODOS_OS_TESTES.xlsx"
    with pd.ExcelWriter(out, engine="openpyxl") as w:
        runs_df.to_excel(w, sheet_name="runs", index=False)
        best_df.to_excel(w, sheet_name="melhores", index=False)
    total = int(runs_df["n_testes"].sum())

    print(f"{'foguete':32s} {'run':>3s} {'algoritmo':16s} {'testes':>7s} {'melhor(m)':>9s}  nome")
    print("-" * 100)
    for _, r in runs_df.iterrows():
        best = f"{r['melhor_alcance_m']:.1f}" if pd.notna(r["melhor_alcance_m"]) else "-"
        print(f"{r['foguete']:32s} {r['run_id']:>3d} {str(r['algoritmo']):16s} "
              f"{r['n_testes']:>7d} {best:>9s}  {r['nome']}")
    print("-" * 100)
    print(f"TOTAL: {len(runs_df)} runs, {total:,} testes/simulações em {len(BANCOS)} bancos")
    print(f"\nExcel mestre gerado: {out}")


if __name__ == "__main__":
    main()
