"""Otimização adaptativa: meta-estratégia que analisa o histórico e decide
onde explorar em seguida.

Fases (frações do orçamento definidas pelo perfil):
1. exploração  — busca aleatória no espaço completo;
2. modelagem   — Optuna TPE num espaço ESTREITADO à região dos melhores
                 designs (categorias fracas são descartadas);
3. refinamento — hill climbing em volta do melhor design encontrado.

Perfis: wide (0.50/0.40/0.10), balanced (0.30/0.50/0.20), local (0.10/0.30/0.60).

A cada transição a estratégia registra no log o que aprendeu: bounds novos,
categorias descartadas e parâmetros de baixa influência (|correlação| baixa).
"""

from __future__ import annotations

import numpy as np

from ..config.loader import OptimizerConfig
from ..utils.logging import get_logger
from .base import Optimizer, register
from .space import Design, SearchSpace

log = get_logger("optimizer.adaptive")

PROFILES = {
    "wide": (0.50, 0.40, 0.10),
    "balanced": (0.30, 0.50, 0.20),
    "local": (0.10, 0.30, 0.60),
}


@register("adaptive")
class AdaptiveOptimizer(Optimizer):
    supports_batch = True

    def __init__(self, space: SearchSpace, cfg: OptimizerConfig) -> None:
        super().__init__(space, cfg)
        fractions = PROFILES.get(cfg.profile, PROFILES["balanced"])
        custom = self.option("fractions", None)  # ex.: [0.15, 0.60]
        if custom:
            fractions = (float(custom[0]), float(custom[1]),
                         1.0 - float(custom[0]) - float(custom[1]))
        budget = cfg.max_evaluations
        self._phase_ends = [
            int(budget * fractions[0]),
            int(budget * (fractions[0] + fractions[1])),
            budget,
        ]
        # orçamentos grandes: TPE fica lento com dezenas de milhares de trials;
        # a fase 2 é dividida em blocos, re-estreitando o espaço a cada bloco
        self._chunk = int(self.option("chunk_size", 3000))
        self._phase2_told = 0
        self.history: list[tuple[Design, float, bool]] = []
        self._phase = 0
        self._sub = self._make_sub(0, space)

    # ---------- fases ----------

    def _make_sub(self, phase: int, space: SearchSpace) -> Optimizer:
        from .hill_climbing import HillClimbing
        from .optuna_opt import OptunaOptimizer
        from .random_search import RandomSearch

        sub_cfg = OptimizerConfig(
            algorithm="_sub", max_evaluations=self.cfg.max_evaluations,
            seed=self.cfg.seed, options=dict(self.cfg.options),
        )
        if phase == 0:
            log.info("fase 1/3: exploração ampla (random) — espaço completo")
            return RandomSearch(space, sub_cfg)
        if phase == 1:
            log.info("fase 2/3: modelagem (Optuna TPE) — espaço estreitado")
            return OptunaOptimizer(space, sub_cfg)
        log.info("fase 3/3: refinamento local (hill climbing) em volta do melhor")
        opts = dict(sub_cfg.options)
        opts.update({"step_scale": 0.05, "start": self.best_design})
        return HillClimbing(
            space,
            OptimizerConfig(algorithm="_sub", max_evaluations=self.cfg.max_evaluations,
                            seed=self.cfg.seed, options=opts),
        )

    def _feasible_sorted(self) -> list[tuple[Design, float]]:
        rows = [(d, s) for d, s, ok in self.history if ok and np.isfinite(s)]
        return sorted(rows, key=lambda t: t[1], reverse=True)

    def _analyze_and_narrow(self) -> SearchSpace:
        """Estreita o espaço com base no top-25% e descarta categorias ruins."""
        ranked = self._feasible_sorted()
        if len(ranked) < 4:
            log.info("histórico insuficiente para estreitar; mantendo espaço completo")
            return self.space
        top = [d for d, _ in ranked[: max(3, len(ranked) // 4)]]

        # categorias: mantém as com média >= mediana global das médias
        keep_choices: dict[str, list] = {}
        for p in self.space.categorical:
            means = {}
            for choice in p.choices:
                scores = [s for d, s in ranked if d.get(p.name) == choice]
                if scores:
                    means[choice] = float(np.mean(scores))
            if len(means) >= 2:
                cutoff = float(np.median(list(means.values())))
                kept = [c for c, m in means.items() if m >= cutoff]
                dropped = [c for c in p.choices if c not in kept and c in means]
                if dropped and kept:
                    log.info("descartando categorias fracas de %s: %s", p.name, dropped)
                    keep_choices[p.name] = kept

        influence = self.influence_report()
        weak = [n for n, corr in influence.items() if corr < 0.1]
        if weak:
            log.info("parâmetros de baixa influência (|corr|<0.1): %s", weak)

        narrowed = self.space.narrowed(top, margin=0.10, keep_choices=keep_choices)
        for old, new in zip(self.space.numeric, narrowed.numeric):
            if (new.low, new.high) != (old.low, old.high):
                log.info(
                    "estreitando %s: [%.4g, %.4g] -> [%.4g, %.4g]",
                    old.name, old.low, old.high, new.low, new.high,
                )
        return narrowed

    # ---------- ask/tell ----------

    def ask(self) -> Design | None:
        if self._phase < 2 and self.n_told >= self._phase_ends[self._phase]:
            self._phase += 1
            space = self._analyze_and_narrow() if self._phase == 1 else self.space
            self._sub = self._make_sub(self._phase, space)
        elif self._phase == 1 and self._phase2_told >= self._chunk:
            # novo bloco TPE: modelo zerado num espaço re-estreitado
            self._phase2_told = 0
            log.info("novo bloco TPE (%d tells acumulados)", self.n_told)
            self._sub = self._make_sub(1, self._analyze_and_narrow())
        return self._sub.ask()

    def _on_tell(self, design: Design, score: float, feasible: bool) -> None:
        self.history.append((dict(design), score, feasible))
        if self._phase == 1:
            self._phase2_told += 1
        self._sub.tell(design, score, feasible)

    def influence_report(self) -> dict[str, float]:
        """|correlação| score×parâmetro (0 = pouca influência)."""
        ranked = self._feasible_sorted()
        if len(ranked) < 5:
            return {}
        scores = np.array([s for _, s in ranked])
        out: dict[str, float] = {}
        for p in self.space.numeric:
            values = np.array([float(d[p.name]) for d, _ in ranked])
            if np.std(values) < 1e-12 or np.std(scores) < 1e-12:
                out[p.name] = 0.0
            else:
                out[p.name] = float(abs(np.corrcoef(values, scores)[0, 1]))
        return out
