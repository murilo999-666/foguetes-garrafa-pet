"""Função objetivo e restrições sobre as métricas de voo.

O objetivo pode ser o nome de uma métrica (``horizontal_distance``) ou uma
expressão aritmética sobre métricas (``apogee - 2*ground_hit_velocity``),
avaliada num namespace restrito (sem builtins; apenas métricas + math).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from ..config.loader import ConstraintConfig, ObjectiveConfig

_SAFE_FUNCS = {
    name: getattr(math, name)
    for name in ("sqrt", "log", "log10", "exp", "fabs", "hypot", "sin", "cos", "tan")
}
_SAFE_FUNCS.update({"abs": abs, "min": min, "max": max})


@dataclass(frozen=True)
class Objective:
    cfg: ObjectiveConfig

    @property
    def maximize(self) -> bool:
        return self.cfg.direction == "maximize"

    def value(self, metrics: dict[str, Any]) -> float | None:
        """Valor bruto do objetivo (None se métricas insuficientes)."""
        expr = self.cfg.metric
        if expr in metrics:
            raw = metrics[expr]
            return float(raw) if raw is not None else None
        namespace = {k: v for k, v in metrics.items() if isinstance(v, (int, float))}
        namespace.update(_SAFE_FUNCS)
        try:
            result = eval(expr, {"__builtins__": {}}, namespace)  # noqa: S307 — namespace restrito
            return float(result)
        except Exception:
            return None

    def signed(self, value: float | None) -> float | None:
        """Score interno sempre-maximizado pelos otimizadores."""
        if value is None:
            return None
        return value if self.maximize else -value


@dataclass(frozen=True)
class Constraints:
    items: tuple[ConstraintConfig, ...]

    def violations(self, metrics: dict[str, Any]) -> list[str]:
        """Lista de violações (vazia = design viável)."""
        out: list[str] = []
        for c in self.items:
            value = metrics.get(c.metric)
            if value is None:
                out.append(f"{c.metric}: métrica ausente/NaN")
                continue
            value = float(value)
            if c.min is not None and value < c.min:
                out.append(f"{c.metric}={value:.4g} < min {c.min}")
            if c.max is not None and value > c.max:
                out.append(f"{c.metric}={value:.4g} > max {c.max}")
        return out
