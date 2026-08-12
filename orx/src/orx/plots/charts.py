"""Geração automática de gráficos (PNG, matplotlib Agg).

Estilo: paleta categórica validada (ordem fixa, CVD-safe), rampa sequencial de
um único matiz (azul claro→escuro) para magnitude, grid recessivo, um eixo por
gráfico, marcas finas. (Ver skill dataviz — paleta de referência.)
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap

from ..results.db import ResultsDB
from ..utils.logging import get_logger

log = get_logger("plots")

# paleta de referência (ordem fixa; nunca ciclar além dela)
SERIES = ["#2a78d6", "#1baf7a", "#eda100", "#008300", "#4a3aa7", "#e34948", "#e87ba4", "#eb6834"]
SEQ_RAMP = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
SURFACE, GRID, MUTED, INK = "#fcfcfb", "#e1e0d9", "#898781", "#0b0b0b"
SEQ_CMAP = LinearSegmentedColormap.from_list("orx_blue", SEQ_RAMP)

plt.rcParams.update(
    {
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "axes.edgecolor": "#c3c2b7",
        "axes.labelcolor": "#52514e",
        "axes.grid": True,
        "grid.color": GRID,
        "grid.linewidth": 0.8,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "text.color": INK,
        "font.family": "sans-serif",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.dpi": 120,
    }
)


def _feasible(df: pd.DataFrame) -> pd.DataFrame:
    return df[(df["feasible"] == 1) & df["score"].notna()]


def _save(fig: plt.Figure, path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return str(path)


def plot_convergence(df: pd.DataFrame, path: Path, maximize: bool, objective: str) -> str:
    ok = _feasible(df)
    fig, ax = plt.subplots(figsize=(7, 4))
    if not ok.empty:
        it = ok["iteration"].to_numpy()
        sc = ok["score"].to_numpy(dtype=float)
        best = np.maximum.accumulate(sc) if maximize else np.minimum.accumulate(sc)
        ax.scatter(it, sc, s=14, color=SERIES[0], alpha=0.35, linewidths=0, label="avaliações")
        ax.plot(it, best, color=SERIES[0], linewidth=2, label="melhor até aqui")
        ax.legend(frameon=False)
    bad = df[df["feasible"] == 0]
    if not bad.empty:
        ax.scatter(bad["iteration"], np.full(len(bad), ax.get_ylim()[0]),
                   marker="x", s=18, color=MUTED, alpha=0.5, label="inviável")
    ax.set_xlabel("avaliação")
    ax.set_ylabel(objective)
    ax.set_title("Convergência")
    return _save(fig, path)


def plot_metric_histograms(df: pd.DataFrame, path: Path, metrics: list[str]) -> str:
    ok = _feasible(df)
    cols = [f"m_{m}" for m in metrics if f"m_{m}" in ok.columns]
    if ok.empty or not cols:
        return ""
    n = len(cols)
    fig, axes = plt.subplots(1, n, figsize=(3.2 * n, 3.2))
    axes = np.atleast_1d(axes)
    for ax, col in zip(axes, cols):
        values = ok[col].dropna().astype(float)
        ax.hist(values, bins=20, color=SERIES[0], edgecolor=SURFACE, linewidth=1)
        ax.set_title(col[2:], fontsize=10)
        ax.grid(axis="x", visible=False)
    fig.suptitle("Distribuição das métricas (viáveis)")
    return _save(fig, path)


def plot_param_effects(df: pd.DataFrame, path: Path, objective: str) -> str:
    """Dispersão score × cada parâmetro numérico + médias por categoria."""
    ok = _feasible(df)
    pcols = [c for c in ok.columns if c.startswith("p_")]
    if ok.empty or not pcols:
        return ""
    n = len(pcols)
    ncols = min(3, n)
    nrows = int(np.ceil(n / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(3.6 * ncols, 3.0 * nrows))
    axes = np.atleast_1d(axes).ravel()
    for ax in axes[n:]:
        ax.axis("off")
    for ax, col in zip(axes, pcols):
        series = ok[col]
        if pd.api.types.is_numeric_dtype(series):
            ax.scatter(series, ok["score"], s=12, color=SERIES[0], alpha=0.45, linewidths=0)
        else:
            means = ok.groupby(col)["score"].mean().sort_values()
            ax.barh(means.index.astype(str), means.values, color=SERIES[0],
                    edgecolor=SURFACE, linewidth=2, height=0.6)
            ax.grid(axis="y", visible=False)
        ax.set_title(col[2:], fontsize=10)
    fig.suptitle(f"Efeito dos parâmetros em {objective}")
    fig.tight_layout()
    return _save(fig, path)


def plot_heatmap(df: pd.DataFrame, path: Path, px: str, py: str, bins: int = 12) -> str:
    """Mapa de calor (média do score) para um par de parâmetros numéricos."""
    ok = _feasible(df)
    cx, cy = f"p_{px}", f"p_{py}"
    if ok.empty or cx not in ok or cy not in ok:
        return ""
    x, y, s = ok[cx].astype(float), ok[cy].astype(float), ok["score"].astype(float)
    xb = np.linspace(x.min(), x.max(), bins + 1)
    yb = np.linspace(y.min(), y.max(), bins + 1)
    sums, _, _ = np.histogram2d(x, y, bins=[xb, yb], weights=s)
    counts, _, _ = np.histogram2d(x, y, bins=[xb, yb])
    with np.errstate(invalid="ignore"):
        mean = np.where(counts > 0, sums / counts, np.nan)
    fig, ax = plt.subplots(figsize=(5.4, 4.4))
    im = ax.pcolormesh(xb, yb, mean.T, cmap=SEQ_CMAP, shading="flat")
    fig.colorbar(im, ax=ax, label="score médio")
    ax.set_xlabel(px)
    ax.set_ylabel(py)
    ax.set_title(f"Score médio: {px} × {py}")
    ax.grid(visible=False)
    return _save(fig, path)


def plot_pareto(df: pd.DataFrame, path: Path, mx: str, my: str,
                maximize_x: bool = True, maximize_y: bool = True) -> str:
    """Fronteira de Pareto para duas métricas."""
    ok = _feasible(df)
    cx, cy = f"m_{mx}", f"m_{my}"
    if ok.empty or cx not in ok or cy not in ok:
        return ""
    pts = ok[[cx, cy]].dropna().astype(float).to_numpy()
    if not len(pts):
        return ""
    sx = pts[:, 0] * (1 if maximize_x else -1)
    sy = pts[:, 1] * (1 if maximize_y else -1)
    is_front = np.array([
        not any((sx >= sx[i]) & (sy >= sy[i]) & ((sx > sx[i]) | (sy > sy[i])))
        for i in range(len(pts))
    ])
    fig, ax = plt.subplots(figsize=(5.6, 4.4))
    ax.scatter(pts[~is_front, 0], pts[~is_front, 1], s=14, color=MUTED, alpha=0.4,
               linewidths=0, label="dominados")
    front = pts[is_front][np.argsort(pts[is_front][:, 0])]
    ax.plot(front[:, 0], front[:, 1], color=SERIES[0], linewidth=2,
            marker="o", markersize=5, label="fronteira de Pareto")
    ax.set_xlabel(mx)
    ax.set_ylabel(my)
    ax.set_title(f"Pareto: {mx} × {my}")
    ax.legend(frameon=False)
    return _save(fig, path)


def plot_3d(df: pd.DataFrame, path: Path, px: str, py: str) -> str:
    ok = _feasible(df)
    cx, cy = f"p_{px}", f"p_{py}"
    if ok.empty or cx not in ok or cy not in ok:
        return ""
    fig = plt.figure(figsize=(6, 4.8))
    ax = fig.add_subplot(projection="3d")
    sc = ax.scatter(ok[cx], ok[cy], ok["score"], c=ok["score"], cmap=SEQ_CMAP, s=18)
    fig.colorbar(sc, ax=ax, shrink=0.6, label="score")
    ax.set_xlabel(px)
    ax.set_ylabel(py)
    ax.set_zlabel("score")
    ax.set_title(f"Superfície amostrada: {px} × {py}")
    return _save(fig, path)


def plot_runs_comparison(db: ResultsDB, run_ids: list[int], path: Path) -> str:
    """Convergência de várias runs no mesmo eixo (cores em ordem fixa)."""
    fig, ax = plt.subplots(figsize=(7, 4))
    plotted = 0
    for i, rid in enumerate(run_ids[: len(SERIES)]):
        df = _feasible(db.evaluations_df(rid))
        if df.empty:
            continue
        runs = db.runs_df()
        run = runs[runs["id"] == rid].iloc[0]
        maximize = run["direction"] == "maximize"
        sc = df["score"].to_numpy(dtype=float)
        best = np.maximum.accumulate(sc) if maximize else np.minimum.accumulate(sc)
        ax.plot(df["iteration"], best, color=SERIES[i], linewidth=2,
                label=f"run {rid} ({run['algorithm']})")
        plotted += 1
    if plotted == 0:
        plt.close(fig)
        return ""
    ax.set_xlabel("avaliação")
    ax.set_ylabel("melhor score")
    ax.set_title("Comparação de convergência entre runs")
    ax.legend(frameon=False)
    return _save(fig, path)


def generate_all_plots(db: ResultsDB, run_id: int, output_dir: str,
                       objective: str = "score", direction: str = "maximize") -> list[str]:
    """Gera o conjunto padrão de gráficos de uma run. Devolve os caminhos."""
    df = db.evaluations_df(run_id)
    if df.empty:
        log.warning("run %d sem avaliações; nada a plotar", run_id)
        return []
    out = Path(output_dir) / "plots" / f"run_{run_id}"
    maximize = direction == "maximize"
    paths = [
        plot_convergence(df, out / "convergence.png", maximize, objective),
        plot_metric_histograms(
            df, out / "histograms.png",
            ["apogee", "max_velocity", "horizontal_distance", "stability_static"],
        ),
        plot_param_effects(df, out / "param_effects.png", objective),
        plot_pareto(df, out / "pareto_apogee_distance.png", "horizontal_distance", "apogee"),
    ]
    # heatmap + 3D para os dois parâmetros numéricos mais influentes
    ok = _feasible(df)
    numeric = [c[2:] for c in ok.columns
               if c.startswith("p_") and pd.api.types.is_numeric_dtype(ok[c])]
    if len(numeric) >= 2 and not ok.empty:
        from ..analysis.sensitivity import parameter_importance

        imp = parameter_importance(ok)
        ranked = [n for n in sorted(numeric, key=lambda n: -imp.get(n, 0.0))]
        px, py = ranked[0], ranked[1]
        paths.append(plot_heatmap(df, out / f"heatmap_{px}_{py}.png", px, py))
        paths.append(plot_3d(df, out / f"surface_{px}_{py}.png", px, py))
    paths = [p for p in paths if p]
    log.info("%d gráficos gerados em %s", len(paths), out)
    return paths
