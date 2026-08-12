"""Ferramentas de alto nível para o Claude Code (e futura ponte MCP).

Uso típico (uma sessão = um YAML):

    from orx.mcp.tools import Session
    s = Session("config/default.yaml")
    s.simulate()                                  # baseline
    s.simulate({"fin_root_chord": 9.0})           # design modificado
    s.change_fin(root_chord=9, tip_chord=3)       # atalho incremental
    s.run_batch([{...}, {...}])
    s.optimize(algorithm="optuna", max_evaluations=200)
    s.best_design()
    s.compare()
    s.export_results()

Os atalhos change_* acumulam alterações em ``s.design`` (o design de trabalho);
``simulate()`` sem argumento usa esse design acumulado.
"""

from __future__ import annotations

import dataclasses
from typing import Any

from ..analysis.compare import compare_runs, summarize_run
from ..config import load_config
from ..config.loader import AppConfig, OptimizerConfig
from ..objectives.objective import Constraints, Objective
from ..results.db import ResultsDB
from ..results.export import export_run
from ..simulation.runner import Runner
from ..utils.logging import setup_logging


class Session:
    def __init__(self, config_path: str) -> None:
        setup_logging()
        self.cfg: AppConfig = load_config(config_path)
        self.runner = Runner(self.cfg)
        self.objective = Objective(self.cfg.objective)
        self.constraints = Constraints(self.cfg.constraints)
        self.design: dict[str, Any] = {}  # design de trabalho (change_* acumula aqui)

    # ---------- inspeção ----------

    def components(self) -> list[dict[str, str]]:
        """Árvore de componentes do foguete base."""
        return self.runner.component_tree()

    def parameters(self) -> list[dict[str, Any]]:
        """Parâmetros otimizáveis definidos no YAML."""
        return [dataclasses.asdict(p) for p in self.cfg.parameters]

    def baseline(self) -> dict[str, Any]:
        """Valores atuais dos parâmetros no .ork base."""
        return self.runner.baseline_design()

    def search_motors(self, text: str) -> list[dict[str, Any]]:
        """Busca motores no banco do OpenRocket por designação/fabricante."""
        return self.runner.bridge.search_motors(text)

    # ---------- design de trabalho ----------

    def set_params(self, **params: Any) -> dict[str, Any]:
        """Define valores no design de trabalho (nomes de parâmetros do YAML)."""
        for name in params:
            self.cfg.parameter(name)  # valida
        self.design.update(params)
        return dict(self.design)

    def _change(self, prefix: str, **kwargs: Any) -> dict[str, Any]:
        return self.set_params(**{f"{prefix}_{k}": v for k, v in kwargs.items()})

    def change_fin(self, **kwargs: Any) -> dict[str, Any]:
        """Atalho: change_fin(root_chord=9, height=5) -> fin_root_chord etc."""
        return self._change("fin", **kwargs)

    def change_nose(self, **kwargs: Any) -> dict[str, Any]:
        """Atalho: change_nose(length=12, shape='OGIVE')."""
        return self._change("nose", **kwargs)

    def change_ballast(self, mass: float) -> dict[str, Any]:
        """Atalho: massa de lastro (parâmetro ballast_mass)."""
        return self.set_params(ballast_mass=mass)

    def change_motor(self, designation: str) -> dict[str, Any]:
        """Atalho: troca de motor (parâmetro motor; 'C6' ou 'C6@Estes')."""
        return self.set_params(motor=designation)

    def reset_design(self) -> None:
        self.design = {}

    # ---------- simulação ----------

    def simulate(self, design: dict[str, Any] | None = None) -> dict[str, Any]:
        """Simula um design (default: o design de trabalho acumulado)."""
        d = self.design if design is None else design
        result = self.runner.evaluate(d)
        violations = self.constraints.violations(result.metrics) if result.ok else []
        return {
            "design": d,
            "ok": result.ok,
            "error": result.error,
            "objective": self.objective.value(result.metrics) if result.ok else None,
            "feasible": result.ok and not violations,
            "violations": violations,
            "metrics": result.metrics,
        }

    def run_batch(self, designs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Simula uma lista de designs em sequência."""
        return [self.simulate(d) for d in designs]

    def save_design(self, out_path: str, design: dict[str, Any] | None = None) -> str:
        """Salva um .ork com o design aplicado."""
        return self.runner.save_design(self.design if design is None else design, out_path)

    # ---------- otimização e resultados ----------

    def optimize(
        self,
        algorithm: str | None = None,
        max_evaluations: int | None = None,
        run_name: str | None = None,
        **options: Any,
    ) -> dict[str, Any]:
        """Roda uma otimização completa (bloqueante). Devolve run_id e o melhor."""
        from ..optimizer.engine import run_optimization

        opt = self.cfg.optimizer
        opt = OptimizerConfig(
            algorithm=algorithm or opt.algorithm,
            max_evaluations=max_evaluations or opt.max_evaluations,
            seed=opt.seed,
            profile=options.pop("profile", opt.profile),
            infeasible_penalty=opt.infeasible_penalty,
            options={**opt.options, **options},
        )
        cfg = dataclasses.replace(self.cfg, optimizer=opt)
        run_id = run_optimization(cfg, run_name=run_name)
        return {"run_id": run_id, "best": self.best_design(run_id)}

    def search(self, **kwargs: Any) -> dict[str, Any]:
        """Alias de optimize()."""
        return self.optimize(**kwargs)

    def best_design(self, run_id: int | None = None) -> dict[str, Any] | None:
        """Melhor avaliação viável de uma run (default: a mais recente)."""
        with ResultsDB(self.cfg.db_path) as db:
            rid = run_id or db.latest_run_id()
            if rid is None:
                return None
            return db.best_evaluation(rid, self.cfg.objective.direction)

    def compare(self, run_id: int | None = None) -> str:
        """Resumo automático em texto de uma run (default: a mais recente)."""
        with ResultsDB(self.cfg.db_path) as db:
            rid = run_id or db.latest_run_id()
            if rid is None:
                return "Nenhuma run no banco."
            return summarize_run(db, rid)

    def compare_algorithms(self, run_ids: list[int]) -> str:
        with ResultsDB(self.cfg.db_path) as db:
            return compare_runs(db, run_ids)

    def export_results(self, run_id: int | None = None, fmt: str = "csv") -> str | None:
        with ResultsDB(self.cfg.db_path) as db:
            rid = run_id or db.latest_run_id()
            if rid is None:
                return None
            return export_run(db, rid, self.cfg.output_dir, fmt)

    def plot(self, run_id: int | None = None) -> list[str]:
        """Gera os gráficos padrão de uma run."""
        from ..plots.charts import generate_all_plots

        with ResultsDB(self.cfg.db_path) as db:
            rid = run_id or db.latest_run_id()
            if rid is None:
                return []
            return generate_all_plots(
                db, rid, self.cfg.output_dir,
                self.cfg.objective.metric, self.cfg.objective.direction,
            )
