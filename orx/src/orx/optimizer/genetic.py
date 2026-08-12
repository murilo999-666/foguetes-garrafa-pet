"""Algoritmo genético: torneio + crossover uniforme/blend + mutação gaussiana.

options: population (16), elite (2), tournament (3), crossover_rate (0.9),
mutation_rate (0.25), mutation_scale (0.15).
"""

from __future__ import annotations

import numpy as np

from .base import Optimizer, register
from .space import Design


@register("genetic")
class GeneticAlgorithm(Optimizer):
    supports_batch = True

    def __init__(self, space, cfg) -> None:
        super().__init__(space, cfg)
        self.pop_size = int(self.option("population", 16))
        self.elite = int(self.option("elite", 2))
        self.tournament = int(self.option("tournament", 3))
        self.cx_rate = float(self.option("crossover_rate", 0.9))
        self.mut_rate = float(self.option("mutation_rate", 0.25))
        self.mut_scale = float(self.option("mutation_scale", 0.15))
        self._pending: list[Design] = [space.sample(self.rng) for _ in range(self.pop_size)]
        self._generation: list[tuple[Design, float]] = []

    def ask(self) -> Design | None:
        if not self._pending:
            self._evolve()
        return self._pending.pop(0)

    def _on_tell(self, design: Design, score: float, feasible: bool) -> None:
        self._generation.append((dict(design), score))

    def _select(self) -> Design:
        idx = self.rng.integers(len(self._generation), size=self.tournament)
        best = max((self._generation[int(i)] for i in idx), key=lambda t: t[1])
        return best[0]

    def _crossover(self, a: Design, b: Design) -> Design:
        child: Design = {}
        for p in self.space.params:
            va, vb = a[p.name], b[p.name]
            if p.is_categorical or p.integer:
                child[p.name] = va if self.rng.random() < 0.5 else vb
            else:  # blend (BLX-alpha simplificado)
                w = float(self.rng.uniform(-0.25, 1.25))
                child[p.name] = float(va) * w + float(vb) * (1 - w)
        return self.space.clip(child)

    def _evolve(self) -> None:
        if not self._generation:  # sem tells ainda: nova geração aleatória
            self._pending = [self.space.sample(self.rng) for _ in range(self.pop_size)]
            return
        ranked = sorted(self._generation, key=lambda t: t[1], reverse=True)
        next_pop: list[Design] = [dict(d) for d, _ in ranked[: self.elite]]
        while len(next_pop) < self.pop_size:
            if self.rng.random() < self.cx_rate and len(self._generation) >= 2:
                child = self._crossover(self._select(), self._select())
            else:
                child = dict(self._select())
            if self.rng.random() < self.mut_rate:
                child = self.space.neighbor(child, self.rng, self.mut_scale)
            next_pop.append(child)
        self._generation = []
        self._pending = next_pop
