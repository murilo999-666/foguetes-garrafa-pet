"""Busca aleatória uniforme."""

from __future__ import annotations

from .base import Optimizer, register
from .space import Design


@register("random")
class RandomSearch(Optimizer):
    supports_batch = True

    def ask(self) -> Design | None:
        return self.space.sample(self.rng)
