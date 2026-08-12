"""Hill climbing estocástico com reinício aleatório.

options: step_scale (0.1), restart_after (12 avaliações sem melhora),
start (design inicial opcional).
"""

from __future__ import annotations

from .base import Optimizer, register
from .space import Design


@register("hill_climbing")
class HillClimbing(Optimizer):
    def __init__(self, space, cfg) -> None:
        super().__init__(space, cfg)
        self.step_scale = float(self.option("step_scale", 0.1))
        self.restart_after = int(self.option("restart_after", 12))
        self.current: Design | None = self.option("start", None)
        self.stall = 0
        self._pending: Design | None = None

    def ask(self) -> Design | None:
        if self.current is None:
            self._pending = self.space.sample(self.rng)
        else:
            self._pending = self.space.neighbor(self.current, self.rng, self.step_scale)
        return self._pending

    def _on_tell(self, design: Design, score: float, feasible: bool) -> None:
        if feasible and (self.best_design is None or design == self.best_design):
            # design virou o melhor: sobe a colina a partir dele
            self.current = dict(design)
            self.stall = 0
            return
        self.stall += 1
        if self.current is None and feasible:
            self.current = dict(design)
        if self.stall >= self.restart_after:
            self.current = None  # reinício aleatório
            self.stall = 0
