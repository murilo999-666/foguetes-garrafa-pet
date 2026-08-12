"""Interface ask/tell dos otimizadores + registry por nome.

Contrato:
- ``ask()`` devolve o próximo design a avaliar (ou None quando esgotado);
- ``tell(design, score, feasible)`` informa o resultado — score é SEMPRE
  maximizado (o engine converte objetivos de minimização);
- designs inviáveis chegam com score de penalidade (pior que qualquer viável).

Novos algoritmos: subclasse + decorador ``@register("nome")`` — nada mais
precisa mudar no projeto.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import numpy as np

from ..config.loader import OptimizerConfig
from .space import Design, SearchSpace

_REGISTRY: dict[str, type["Optimizer"]] = {}


def register(name: str):
    def deco(cls: type["Optimizer"]) -> type["Optimizer"]:
        cls.name = name
        _REGISTRY[name] = cls
        return cls

    return deco


def registered_algorithms() -> list[str]:
    return sorted(_REGISTRY)


def create_optimizer(space: SearchSpace, cfg: OptimizerConfig) -> "Optimizer":
    # import tardio para registrar as implementações
    from . import adaptive, annealing, genetic, grid, hill_climbing, optuna_opt, random_search  # noqa: F401

    try:
        from . import nevergrad_opt  # noqa: F401
    except ImportError:
        pass
    if cfg.algorithm not in _REGISTRY:
        raise KeyError(
            f"Algoritmo '{cfg.algorithm}' desconhecido. Disponíveis: {registered_algorithms()}"
        )
    return _REGISTRY[cfg.algorithm](space, cfg)


class Optimizer(ABC):
    name = "base"
    supports_batch = False  # True: engine pode pedir vários asks antes dos tells

    def __init__(self, space: SearchSpace, cfg: OptimizerConfig) -> None:
        self.space = space
        self.cfg = cfg
        self.rng = np.random.default_rng(cfg.seed)
        self.best_design: Design | None = None
        self.best_score: float = -np.inf
        self.n_told = 0

    @abstractmethod
    def ask(self) -> Design | None: ...

    def tell(self, design: Design, score: float, feasible: bool) -> None:
        self.n_told += 1
        if feasible and score > self.best_score:
            self.best_score = score
            self.best_design = dict(design)
        self._on_tell(design, score, feasible)

    def _on_tell(self, design: Design, score: float, feasible: bool) -> None:
        """Hook para subclasses."""

    def option(self, key: str, default: Any) -> Any:
        return self.cfg.options.get(key, default)
