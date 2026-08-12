"""Espaço de busca construído a partir dos ParameterConfig."""

from __future__ import annotations

import itertools
from typing import Any, Iterator, Sequence

import numpy as np

from ..config.loader import ParameterConfig

Design = dict[str, Any]


class SearchSpace:
    def __init__(self, params: Sequence[ParameterConfig]) -> None:
        if not params:
            raise ValueError("Espaço de busca vazio: defina 'parameters' no YAML")
        self.params: tuple[ParameterConfig, ...] = tuple(params)

    @property
    def names(self) -> list[str]:
        return [p.name for p in self.params]

    @property
    def numeric(self) -> list[ParameterConfig]:
        return [p for p in self.params if not p.is_categorical]

    @property
    def categorical(self) -> list[ParameterConfig]:
        return [p for p in self.params if p.is_categorical]

    # ---------- geração ----------

    def sample(self, rng: np.random.Generator) -> Design:
        design: Design = {}
        for p in self.params:
            if p.is_categorical:
                design[p.name] = p.choices[int(rng.integers(len(p.choices)))]
            elif p.integer:
                design[p.name] = int(rng.integers(int(p.low), int(p.high) + 1))
            else:
                design[p.name] = float(rng.uniform(p.low, p.high))
        return design

    def grid(self, default_points: int = 4) -> Iterator[Design]:
        """Produto cartesiano usando `step` de cada parâmetro (ou
        default_points divisões quando step ausente)."""
        axes: list[list[Any]] = []
        for p in self.params:
            if p.is_categorical:
                axes.append(list(p.choices))
            elif p.integer:
                step = int(p.step or 1)
                axes.append(list(range(int(p.low), int(p.high) + 1, step)))
            else:
                if p.step:
                    values = np.arange(p.low, p.high + p.step * 0.5, p.step)
                else:
                    values = np.linspace(p.low, p.high, default_points)
                axes.append([float(v) for v in values])
        for combo in itertools.product(*axes):
            yield dict(zip(self.names, combo))

    def neighbor(self, design: Design, rng: np.random.Generator, scale: float = 0.15) -> Design:
        """Perturba um design: gaussiana proporcional à faixa (numérico) ou
        troca de categoria (com prob. ~scale)."""
        out = dict(design)
        for p in self.params:
            if p.is_categorical:
                if len(p.choices) > 1 and rng.random() < max(scale, 0.05):
                    others = [c for c in p.choices if c != design.get(p.name)]
                    out[p.name] = others[int(rng.integers(len(others)))]
            else:
                span = float(p.high) - float(p.low)
                value = float(design.get(p.name, (p.low + p.high) / 2))
                value += float(rng.normal(0.0, scale * span))
                out[p.name] = value
        return self.clip(out)

    # ---------- utilidades ----------

    def clip(self, design: Design) -> Design:
        out = dict(design)
        for p in self.params:
            if p.name not in out:
                continue
            if p.is_categorical:
                if out[p.name] not in p.choices:
                    raise ValueError(f"{p.name}: '{out[p.name]}' fora de {p.choices}")
            else:
                v = min(max(float(out[p.name]), float(p.low)), float(p.high))
                out[p.name] = int(round(v)) if p.integer else v
        return out

    def canonical_key(self, design: Design) -> tuple:
        """Chave de deduplicação com tolerância (~0,5% da faixa)."""
        key: list[Any] = []
        for p in self.params:
            v = design.get(p.name)
            if p.is_categorical or v is None:
                key.append(v)
            else:
                span = float(p.high) - float(p.low) or 1.0
                key.append(round(float(v) / (span * 0.005)))
        return tuple(key)

    def narrowed(
        self,
        top_designs: Sequence[Design],
        margin: float = 0.10,
        keep_choices: dict[str, list[Any]] | None = None,
    ) -> "SearchSpace":
        """Espaço reduzido à região dos melhores designs (modo adaptativo)."""
        new_params: list[ParameterConfig] = []
        for p in self.params:
            if p.is_categorical:
                choices = (keep_choices or {}).get(p.name) or list(p.choices)
                new_params.append(
                    ParameterConfig(name=p.name, component=p.component, attribute=p.attribute,
                                    unit=p.unit, choices=choices, integer=p.integer,
                                    options=p.options)
                )
                continue
            values = [float(d[p.name]) for d in top_designs if p.name in d]
            if not values:
                new_params.append(p)
                continue
            span = float(p.high) - float(p.low)
            lo = max(float(p.low), min(values) - margin * span)
            hi = min(float(p.high), max(values) + margin * span)
            if hi - lo < 1e-12:  # região degenerada: mantém uma folga mínima
                lo, hi = max(float(p.low), lo - 0.05 * span), min(float(p.high), hi + 0.05 * span)
            new_params.append(
                ParameterConfig(name=p.name, component=p.component, attribute=p.attribute,
                                unit=p.unit, low=lo, high=hi, step=p.step, integer=p.integer,
                                options=p.options)
            )
        return SearchSpace(new_params)
