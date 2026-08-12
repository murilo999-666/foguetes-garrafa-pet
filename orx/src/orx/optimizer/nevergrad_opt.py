"""Adaptador Nevergrad (opcional: pip install nevergrad).

options: method (NGOpt, CMA, PSO, DE, ...).
"""

from __future__ import annotations

import nevergrad as ng

from .base import Optimizer, register
from .space import Design


@register("nevergrad")
class NevergradOptimizer(Optimizer):
    supports_batch = True

    def __init__(self, space, cfg) -> None:
        super().__init__(space, cfg)
        kwargs = {}
        for p in space.params:
            if p.is_categorical:
                kwargs[p.name] = ng.p.Choice(list(p.choices))
            elif p.integer:
                kwargs[p.name] = ng.p.Scalar(lower=int(p.low), upper=int(p.high)).set_integer_casting()
            else:
                kwargs[p.name] = ng.p.Scalar(lower=float(p.low), upper=float(p.high))
        parametrization = ng.p.Instrumentation(**kwargs)
        if cfg.seed is not None:
            parametrization.random_state.seed(cfg.seed)
        method = str(self.option("method", "NGOpt"))
        self._opt = ng.optimizers.registry[method](
            parametrization=parametrization, budget=cfg.max_evaluations
        )
        self._candidates: dict[tuple, list] = {}

    def ask(self) -> Design | None:
        cand = self._opt.ask()
        design = dict(cand.kwargs)
        self._candidates.setdefault(self.space.canonical_key(design), []).append(cand)
        return design

    def _on_tell(self, design: Design, score: float, feasible: bool) -> None:
        key = self.space.canonical_key(design)
        cands = self._candidates.get(key)
        if cands:
            self._opt.tell(cands.pop(0), -score)  # nevergrad minimiza
