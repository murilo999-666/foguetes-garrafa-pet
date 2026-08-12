"""Adaptador Optuna (TPE, CMA-ES, random) via API ask/tell.

options: sampler (tpe|cmaes|random), n_startup_trials (10).
"""

from __future__ import annotations

import logging
from typing import Any

import optuna

from .base import Optimizer, register
from .space import Design

optuna.logging.set_verbosity(optuna.logging.WARNING)
logging.getLogger("optuna").setLevel(logging.WARNING)


@register("optuna")
class OptunaOptimizer(Optimizer):
    supports_batch = True

    def __init__(self, space, cfg) -> None:
        super().__init__(space, cfg)
        sampler_name = str(self.option("sampler", "tpe")).lower()
        seed = cfg.seed
        n_startup = int(self.option("n_startup_trials", 10))
        if sampler_name == "cmaes":
            if space.categorical:
                # CMA-ES é contínuo; categóricos caem no sampler independente
                sampler: Any = optuna.samplers.CmaEsSampler(
                    seed=seed, n_startup_trials=n_startup,
                    independent_sampler=optuna.samplers.TPESampler(seed=seed),
                )
            else:
                sampler = optuna.samplers.CmaEsSampler(seed=seed, n_startup_trials=n_startup)
        elif sampler_name == "random":
            sampler = optuna.samplers.RandomSampler(seed=seed)
        else:
            sampler = optuna.samplers.TPESampler(seed=seed, n_startup_trials=n_startup)
        self.study = optuna.create_study(direction="maximize", sampler=sampler)
        self._trials: dict[tuple, list[optuna.trial.Trial]] = {}

    def ask(self) -> Design | None:
        trial = self.study.ask()
        design: Design = {}
        for p in self.space.params:
            if p.is_categorical:
                design[p.name] = trial.suggest_categorical(p.name, list(p.choices))
            elif p.integer:
                design[p.name] = trial.suggest_int(p.name, int(p.low), int(p.high))
            else:
                design[p.name] = trial.suggest_float(p.name, float(p.low), float(p.high))
        self._trials.setdefault(self.space.canonical_key(design), []).append(trial)
        return design

    def _on_tell(self, design: Design, score: float, feasible: bool) -> None:
        key = self.space.canonical_key(design)
        trials = self._trials.get(key)
        if trials:
            self.study.tell(trials.pop(0), score)
