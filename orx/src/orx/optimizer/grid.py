"""Busca em grade: produto cartesiano dos steps/choices."""

from __future__ import annotations

from .base import Optimizer, register
from .space import Design


@register("grid")
class GridSearch(Optimizer):
    supports_batch = True

    def __init__(self, space, cfg) -> None:
        super().__init__(space, cfg)
        self._iter = space.grid(default_points=int(self.option("default_points", 4)))

    def ask(self) -> Design | None:
        return next(self._iter, None)
