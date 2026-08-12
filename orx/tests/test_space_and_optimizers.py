"""Otimizadores em função sintética (sem JVM): todos devem se aproximar do
ótimo conhecido de uma quadrática com um categórico."""

import numpy as np
import pytest

from orx.config.loader import OptimizerConfig, ParameterConfig
from orx.optimizer.base import create_optimizer, registered_algorithms
from orx.optimizer.space import SearchSpace

PARAMS = [
    ParameterConfig(name="x", component="c", attribute="a", low=-5, high=5),
    ParameterConfig(name="y", component="c", attribute="a", low=-5, high=5),
    ParameterConfig(name="n", component="c", attribute="a", low=1, high=6, integer=True),
    ParameterConfig(name="cat", component="c", attribute="a", choices=["good", "bad"]),
]


def score_fn(d: dict) -> float:
    bonus = 2.0 if d["cat"] == "good" else 0.0
    return -((d["x"] - 1.5) ** 2) - (d["y"] + 2.0) ** 2 - 0.1 * (d["n"] - 3) ** 2 + bonus


OPTIMUM = score_fn({"x": 1.5, "y": -2.0, "n": 3, "cat": "good"})


@pytest.mark.parametrize(
    "algorithm", ["random", "hill_climbing", "annealing", "genetic", "optuna", "adaptive"]
)
def test_optimizer_converges(algorithm):
    space = SearchSpace(PARAMS)
    cfg = OptimizerConfig(algorithm=algorithm, max_evaluations=120, seed=3)
    opt = create_optimizer(space, cfg)
    for _ in range(cfg.max_evaluations):
        design = opt.ask()
        assert design is not None
        design = space.clip(design)
        opt.tell(design, score_fn(design), True)
    assert opt.best_design is not None
    # deve chegar razoavelmente perto do ótimo (2.0)
    assert opt.best_score > OPTIMUM - 2.0, f"{algorithm}: best={opt.best_score}"


def test_grid_exhausts():
    space = SearchSpace(
        [
            ParameterConfig(name="x", component="c", attribute="a", low=0, high=1, step=0.5),
            ParameterConfig(name="cat", component="c", attribute="a", choices=["a", "b"]),
        ]
    )
    opt = create_optimizer(space, OptimizerConfig(algorithm="grid", max_evaluations=100))
    designs = []
    while (d := opt.ask()) is not None:
        designs.append(d)
    assert len(designs) == 3 * 2  # x: 0, 0.5, 1.0 × 2 categorias


def test_space_helpers():
    space = SearchSpace(PARAMS)
    rng = np.random.default_rng(0)
    d = space.sample(rng)
    assert set(d) == {"x", "y", "n", "cat"}
    clipped = space.clip({"x": 99, "y": -99, "n": 2.6, "cat": "good"})
    assert clipped["x"] == 5 and clipped["y"] == -5 and clipped["n"] == 3
    k1 = space.canonical_key({"x": 1.0, "y": 0.0, "n": 2, "cat": "good"})
    k2 = space.canonical_key({"x": 1.001, "y": 0.0, "n": 2, "cat": "good"})
    assert k1 == k2  # tolerância de dedup
    n = space.neighbor(d, rng)
    assert -5 <= n["x"] <= 5


def test_registry_lists_algorithms():
    space = SearchSpace(PARAMS[:1])
    create_optimizer(space, OptimizerConfig(algorithm="random"))
    algos = registered_algorithms()
    for expected in ("grid", "random", "hill_climbing", "annealing", "genetic", "optuna", "adaptive"):
        assert expected in algos
