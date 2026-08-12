"""Simulated annealing (Metropolis) com resfriamento geométrico.

options: initial_temp (relativo à escala do score; auto se None),
cooling (0.95), step_scale (0.2 -> reduz junto com a temperatura).
"""

from __future__ import annotations

import math

import numpy as np

from .base import Optimizer, register
from .space import Design


@register("annealing")
class SimulatedAnnealing(Optimizer):
    def __init__(self, space, cfg) -> None:
        super().__init__(space, cfg)
        self.temp: float | None = self.option("initial_temp", None)
        self.cooling = float(self.option("cooling", 0.95))
        self.step_scale = float(self.option("step_scale", 0.2))
        self.current: Design | None = None
        self.current_score = -np.inf
        self._pending: Design | None = None
        self._scores: list[float] = []

    def ask(self) -> Design | None:
        if self.current is None:
            self._pending = self.space.sample(self.rng)
        else:
            frac = self.temp / self._t0 if (self.temp and getattr(self, "_t0", 0)) else 1.0
            self._pending = self.space.neighbor(
                self.current, self.rng, self.step_scale * max(frac, 0.05)
            )
        return self._pending

    def _on_tell(self, design: Design, score: float, feasible: bool) -> None:
        self._scores.append(score)
        if self.temp is None and len(self._scores) >= 5:
            spread = float(np.std(self._scores)) or 1.0
            self.temp = spread
            self._t0 = spread
        if self.current is None:
            if feasible:
                self.current, self.current_score = dict(design), score
            return
        delta = score - self.current_score
        t = self.temp or 1.0
        if delta >= 0 or self.rng.random() < math.exp(delta / max(t, 1e-12)):
            self.current, self.current_score = dict(design), score
        if self.temp is not None:
            self.temp *= self.cooling
