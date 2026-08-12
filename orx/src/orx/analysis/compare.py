"""Comparações automáticas em linguagem natural sobre os resultados.

Gera conclusões do tipo:
- "nose_shape=OGIVE teve média 21.3 m, 18% acima de CONICAL (18.1 m)."
- "O ideal de ballast_mass ficou entre 42 e 48 g (faixa do top-10%)."
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..results.db import ResultsDB
from .sensitivity import parameter_importance


def _feasible(df: pd.DataFrame) -> pd.DataFrame:
    return df[(df["feasible"] == 1) & df["score"].notna()]


def _param_cols(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if c.startswith("p_")]


def summarize_run(db: ResultsDB, run_id: int, top_fraction: float = 0.10) -> str:
    """Resumo textual automático de uma run."""
    runs = db.runs_df()
    run = runs[runs["id"] == run_id]
    if run.empty:
        return f"Run {run_id} não existe."
    run = run.iloc[0]
    maximize = run["direction"] == "maximize"

    df = db.evaluations_df(run_id)
    lines = [
        f"=== Run {run_id} ({run['algorithm']}) — objetivo: "
        f"{'maximizar' if maximize else 'minimizar'} {run['objective']} ===",
        f"Avaliações: {len(df)} | viáveis: {int(df['feasible'].sum()) if not df.empty else 0} "
        f"| erros: {int(df['error'].notna().sum()) if not df.empty else 0}",
    ]
    ok = _feasible(df)
    if ok.empty:
        lines.append("Nenhuma avaliação viável — revise restrições/espaço de busca.")
        return "\n".join(lines)

    best = ok.loc[ok["score"].idxmax() if maximize else ok["score"].idxmin()]
    lines.append(f"Melhor {run['objective']}: {best['score']:.4g} (iteração {int(best['iteration'])})")
    lines.append("Melhor design:")
    for col in _param_cols(ok):
        lines.append(f"  {col[2:]} = {best[col]:.4g}" if isinstance(best[col], float)
                     else f"  {col[2:]} = {best[col]}")

    scores = ok["score"] if maximize else -ok["score"]
    cutoff = scores.quantile(1 - top_fraction)
    top = ok[scores >= cutoff]
    if len(top) >= 2:
        lines.append(f"\nFaixas ideais (top-{int(top_fraction * 100)}%, n={len(top)}):")
        for col in _param_cols(ok):
            series = top[col]
            if pd.api.types.is_numeric_dtype(series):
                lines.append(f"  {col[2:]}: entre {series.min():.4g} e {series.max():.4g}")

    # comparação de categorias
    for col in _param_cols(ok):
        series = ok[col]
        if pd.api.types.is_numeric_dtype(series) or series.nunique() < 2:
            continue
        means = ok.groupby(col)["score"].agg(["mean", "count"])
        means = means.sort_values("mean", ascending=not maximize)
        best_cat, runner_up = means.iloc[0], means.iloc[1]
        base = abs(runner_up["mean"]) or 1.0
        pct = 100 * (best_cat["mean"] - runner_up["mean"]) / base
        lines.append(
            f"\n{col[2:]}: '{means.index[0]}' foi o melhor "
            f"(média {best_cat['mean']:.4g}, n={int(best_cat['count'])}), "
            f"{abs(pct):.0f}% {'acima' if pct > 0 else 'abaixo'} de "
            f"'{means.index[1]}' ({runner_up['mean']:.4g})."
        )

    importance = parameter_importance(ok)
    if importance:
        lines.append("\nInfluência dos parâmetros (|correlação| com o objetivo):")
        for name, corr in sorted(importance.items(), key=lambda kv: -kv[1]):
            marker = "###" if corr > 0.5 else ("## " if corr > 0.25 else ("#  " if corr > 0.1 else "   "))
            lines.append(f"  {marker} {name}: {corr:.2f}")
        weak = [n for n, c in importance.items() if c < 0.1]
        if weak:
            lines.append(f"  (pouca influência detectada: {', '.join(weak)})")
    return "\n".join(lines)


def compare_runs(db: ResultsDB, run_ids: list[int]) -> str:
    """Compara o desempenho final e a convergência de várias runs."""
    lines = ["=== Comparação de runs ==="]
    rows = []
    for rid in run_ids:
        runs = db.runs_df()
        run = runs[runs["id"] == rid]
        if run.empty:
            continue
        run = run.iloc[0]
        ok = _feasible(db.evaluations_df(rid))
        if ok.empty:
            rows.append((rid, run["algorithm"], None, 0, len(db.evaluations_df(rid))))
            continue
        maximize = run["direction"] == "maximize"
        best = ok["score"].max() if maximize else ok["score"].min()
        # avaliações até chegar a 95% do melhor
        target = best * (0.95 if maximize else 1.05)
        hit = ok[ok["score"] >= target] if maximize else ok[ok["score"] <= target]
        first_hit = int(hit["iteration"].min()) if not hit.empty else None
        rows.append((rid, run["algorithm"], best, first_hit, len(ok)))
    for rid, algo, best, first_hit, n in rows:
        if best is None:
            lines.append(f"run {rid} ({algo}): sem avaliações viáveis")
        else:
            lines.append(
                f"run {rid} ({algo}): melhor={best:.4g} | avaliações viáveis={n} "
                f"| atingiu 95% do melhor na iteração {first_hit}"
            )
    ranked = [r for r in rows if r[2] is not None]
    if len(ranked) >= 2:
        ranked.sort(key=lambda r: r[2], reverse=True)
        a, b = ranked[0], ranked[1]
        base = abs(b[2]) or 1.0
        lines.append(
            f"\n'{a[1]}' (run {a[0]}) superou '{b[1]}' (run {b[0]}) "
            f"em {100 * (a[2] - b[2]) / base:.1f}%."
        )
    return "\n".join(lines)
