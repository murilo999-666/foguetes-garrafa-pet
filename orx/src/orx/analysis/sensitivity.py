"""Influência de cada parâmetro no objetivo.

Usa |correlação de Spearman| (robusta a não-linearidade monotônica); com
dados suficientes e Optuna disponível, refina com fANOVA.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def parameter_importance(feasible_df: pd.DataFrame) -> dict[str, float]:
    """{parâmetro: influência 0..1} a partir do DataFrame de avaliações viáveis."""
    if feasible_df.empty or "score" not in feasible_df:
        return {}
    out: dict[str, float] = {}
    scores = feasible_df["score"].astype(float)
    if scores.std() < 1e-12:
        return {}
    for col in feasible_df.columns:
        if not col.startswith("p_"):
            continue
        series = feasible_df[col]
        name = col[2:]
        if pd.api.types.is_numeric_dtype(series):
            if series.std() < 1e-12:
                out[name] = 0.0
                continue
            corr = series.rank().corr(scores.rank())  # Spearman
            out[name] = float(abs(corr)) if np.isfinite(corr) else 0.0
        else:
            # categórico: eta (razão de variância entre grupos)
            groups = [g["score"].values for _, g in feasible_df.groupby(col) if len(g) > 0]
            if len(groups) < 2:
                out[name] = 0.0
                continue
            grand = scores.mean()
            ss_between = sum(len(g) * (np.mean(g) - grand) ** 2 for g in groups)
            ss_total = float(((scores - grand) ** 2).sum()) or 1.0
            out[name] = float(np.sqrt(max(ss_between / ss_total, 0.0)))
    return out
