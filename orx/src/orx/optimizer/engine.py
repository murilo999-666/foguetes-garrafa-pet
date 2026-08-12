"""Laço de otimização: liga otimizador ↔ simulador ↔ banco de resultados.

- Score interno é sempre maximizado (objetivos de minimização são negados).
- Designs inviáveis (restrição violada) ou com erro recebem penalidade
  (pior score observado - 3·desvio, ou optimizer.infeasible_penalty do YAML)
  e ficam marcados feasible=0 no banco — descartados nas consultas de melhor.
- Deduplicação: designs equivalentes (tolerância 0,5% da faixa) não são
  re-simulados; o score conhecido é reaproveitado.
- workers>1: avaliações em paralelo via multiprocessing (1 JVM por processo)
  para algoritmos que suportam lote.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any, Callable

import numpy as np

from ..config.loader import AppConfig
from ..objectives.objective import Constraints, Objective
from ..results.db import ResultsDB
from ..simulation.runner import EvalResult, Runner
from ..utils.logging import get_logger
from .base import create_optimizer
from .space import Design, SearchSpace

log = get_logger("optimizer.engine")

ProgressFn = Callable[[int, int, float | None, float | None], None]

# Se um lote não voltar nesse tempo, algum worker morreu (ex.: JVM sem memória
# nativa) e o multiprocessing.Pool.map ficaria esperando pra sempre em
# silêncio (visto na prática: travou 20+ min sem nenhum erro visível). Em vez
# de esperar pra sempre, detecta, recria o pool e tenta o lote de novo uma vez.
BATCH_TIMEOUT_S = 180
# recicla cada worker após N tarefas: mitiga crescimento de memória nativa da
# JVM (G1GC) ao longo de dezenas de milhares de avaliações no mesmo processo.
MAX_TASKS_PER_WORKER = 500


class _Evaluator:
    """Executa avaliações em série (1 JVM neste processo) ou em paralelo."""

    def __init__(self, cfg: AppConfig) -> None:
        self.cfg = cfg
        self.workers = max(1, cfg.batch.workers)
        self._runner: Runner | None = None
        self._pool = None
        self._ctx = None
        if self.workers > 1:
            import multiprocessing as mp

            self._ctx = mp.get_context("spawn")
            self._pool = self._make_pool()
            log.info("pool paralelo: %d workers (1 JVM cada)", self.workers)
        else:
            self._runner = Runner(cfg)

    def _make_pool(self):
        return self._ctx.Pool(
            self.workers,
            initializer=_init_worker,
            initargs=(asdict_config(self.cfg),),
            maxtasksperchild=MAX_TASKS_PER_WORKER,
        )

    def evaluate_many(self, designs: list[Design]) -> list[EvalResult]:
        if self._pool is None:
            assert self._runner is not None
            return [self._runner.evaluate(d) for d in designs]

        import multiprocessing as mp

        try:
            return self._pool.map_async(_worker_evaluate, designs).get(timeout=BATCH_TIMEOUT_S)
        except mp.TimeoutError:
            log.error(
                "lote de %d designs travado por >%ds — provável worker morto "
                "(JVM sem memória nativa). Reiniciando o pool e tentando de novo.",
                len(designs), BATCH_TIMEOUT_S,
            )
            self._pool.terminate()
            self._pool.join()
            self._pool = self._make_pool()
            return self._pool.map_async(_worker_evaluate, designs).get(timeout=BATCH_TIMEOUT_S)

    def close(self) -> None:
        if self._pool is not None:
            # terminate (não close/join): a JVM dos workers tem threads
            # não-daemon e o processo filho não sairia sozinho; os resultados
            # já foram coletados de forma síncrona pelo map().
            self._pool.terminate()
            self._pool.join()


# ---------- workers (multiprocessing spawn) ----------

_worker_runner: Runner | None = None


def asdict_config(cfg: AppConfig) -> dict[str, Any]:
    return asdict(cfg)


def _rebuild_config(raw: dict[str, Any]) -> AppConfig:
    from ..config.loader import (
        BatchConfig, ConstraintConfig, ObjectiveConfig, OptimizerConfig,
        ParameterConfig, PathsConfig, SimulationConfig,
    )

    return AppConfig(
        base_ork=raw["base_ork"],
        paths=PathsConfig(**raw["paths"]),
        simulation=SimulationConfig(**raw["simulation"]),
        parameters=tuple(ParameterConfig(**p) for p in raw["parameters"]),
        objective=ObjectiveConfig(**raw["objective"]),
        constraints=tuple(ConstraintConfig(**c) for c in raw["constraints"]),
        optimizer=OptimizerConfig(**raw["optimizer"]),
        batch=BatchConfig(**raw["batch"]),
        db_path=raw["db_path"],
        output_dir=raw["output_dir"],
    )


def _init_worker(raw_cfg: dict[str, Any]) -> None:
    global _worker_runner
    from ..utils.logging import setup_logging

    setup_logging()
    _worker_runner = Runner(_rebuild_config(raw_cfg))


def _worker_evaluate(design: Design) -> EvalResult:
    assert _worker_runner is not None
    return _worker_runner.evaluate(design)


# ---------- laço principal ----------

def run_optimization(
    cfg: AppConfig,
    run_name: str | None = None,
    progress: ProgressFn | None = None,
) -> int:
    """Executa a otimização configurada. Devolve o run_id no banco."""
    space = SearchSpace(cfg.parameters)
    objective = Objective(cfg.objective)
    constraints = Constraints(cfg.constraints)
    optimizer = create_optimizer(space, cfg.optimizer)
    db = ResultsDB(cfg.db_path)
    evaluator = _Evaluator(cfg)

    run_id = db.create_run(
        name=run_name or f"{cfg.optimizer.algorithm}",
        algorithm=cfg.optimizer.algorithm,
        objective=cfg.objective.metric,
        direction=cfg.objective.direction,
        base_ork=cfg.base_ork,
        config=asdict_config(cfg),
    )
    log.info(
        "run %d: %s, objetivo %s (%s), %d avaliações",
        run_id, cfg.optimizer.algorithm, cfg.objective.metric,
        cfg.objective.direction, cfg.optimizer.max_evaluations,
    )

    seen: dict[tuple, float] = {}
    feasible_scores: list[float] = []
    budget = cfg.optimizer.max_evaluations
    iteration = 0
    batch_size = evaluator.workers if optimizer.supports_batch else 1
    fruitless_rounds = 0  # rodadas seguidas sem nenhum design inédito

    def penalty() -> float:
        if cfg.optimizer.infeasible_penalty is not None:
            base = cfg.optimizer.infeasible_penalty
            return base if objective.maximize else -base
        if feasible_scores:
            arr = np.array(feasible_scores)
            return float(arr.min() - 3 * (arr.std() or abs(arr.min()) or 1.0))
        return -1e9

    try:
        while iteration < budget:
            # coleta um lote de designs inéditos
            batch: list[Design] = []
            duplicates: list[tuple[Design, float]] = []
            attempts = 0
            while len(batch) < min(batch_size, budget - iteration) and attempts < 20 * batch_size:
                attempts += 1
                design = optimizer.ask()
                if design is None:
                    break
                design = space.clip(design)
                key = space.canonical_key(design)
                if key in seen:
                    duplicates.append((design, seen[key]))
                    continue
                seen[key] = np.nan  # reservado
                batch.append(design)
            # duplicatas: devolve o score conhecido sem gastar simulação
            for design, known in duplicates:
                if np.isfinite(known):
                    optimizer.tell(design, known, True)
            if not batch:
                if duplicates:
                    fruitless_rounds += 1
                    if fruitless_rounds >= 25:
                        log.info("otimizador estagnado em designs repetidos; encerrando")
                        break
                    continue  # otimizador insistindo em região conhecida
                log.info("otimizador esgotou o espaço após %d avaliações", iteration)
                break
            fruitless_rounds = 0

            results = evaluator.evaluate_many(batch)
            for design, result in zip(batch, results):
                iteration += 1
                key = space.canonical_key(design)
                if not result.ok:
                    score = penalty()
                    db.add_evaluation(
                        run_id, iteration, design, None, None, False,
                        error=result.error, duration_s=result.duration_s,
                    )
                    optimizer.tell(design, score, False)
                    seen[key] = np.nan
                    if progress:
                        progress(iteration, budget, None, optimizer.best_score)
                    continue

                violations = constraints.violations(result.metrics)
                raw_value = objective.value(result.metrics)
                signed = objective.signed(raw_value)
                feasible = not violations and signed is not None
                if feasible:
                    feasible_scores.append(signed)  # type: ignore[arg-type]
                    score = float(signed)  # type: ignore[arg-type]
                else:
                    score = penalty()
                db.add_evaluation(
                    run_id, iteration, design, result.metrics,
                    raw_value, feasible, violations,
                    duration_s=result.duration_s,
                )
                optimizer.tell(design, score, feasible)
                seen[key] = score if feasible else np.nan
                if progress:
                    progress(iteration, budget, raw_value, optimizer.best_score)

        best = db.best_evaluation(run_id, cfg.objective.direction)
        notes = None
        if best:
            notes = (
                f"melhor {cfg.objective.metric}={best['score']:.4g} "
                f"em {json.dumps(best['params'], default=str)}"
            )
            log.info("run %d concluída: %s", run_id, notes)
        else:
            log.warning("run %d: nenhuma avaliação viável", run_id)
        db.finish_run(run_id, "done", notes)
        return run_id
    except BaseException:
        db.finish_run(run_id, "aborted")
        raise
    finally:
        evaluator.close()
        db.close()
