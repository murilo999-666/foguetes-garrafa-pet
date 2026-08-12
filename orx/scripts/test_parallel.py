"""Gate M4: avaliação paralela com N workers (1 JVM por processo).

Precisa ser um arquivo (não stdin) por causa do multiprocessing spawn no
Windows, e do guard __main__ obrigatório.
"""

import dataclasses
import time

from orx.config import load_config
from orx.config.loader import BatchConfig, OptimizerConfig
from orx.optimizer.engine import run_optimization
from orx.results.db import ResultsDB
from orx.utils.logging import setup_logging

CONFIG = r"C:\Users\muril\openrocket-optimizer\config\default.yaml"


def main() -> None:
    setup_logging()
    cfg = load_config(CONFIG)
    cfg = dataclasses.replace(
        cfg,
        optimizer=OptimizerConfig(algorithm="random", max_evaluations=8, seed=2),
        batch=BatchConfig(workers=2),
    )
    t0 = time.perf_counter()
    run_id = run_optimization(cfg, run_name="teste-paralelo")
    dt = time.perf_counter() - t0
    with ResultsDB(cfg.db_path) as db:
        n = db.count_evaluations(run_id)
    print(f"PARALLEL OK: {n} sims em {dt:.1f}s com 2 workers")


if __name__ == "__main__":
    main()
