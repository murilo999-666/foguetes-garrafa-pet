"""Execução de simulações: aplica um design no .ork base e simula.

O documento base é recarregado do disco a cada avaliação — mais lento (~0,2 s)
porém garante independência total entre avaliações (sem estado residual).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..bridge.orjava import OrBridge
from ..config.loader import AppConfig, ParameterConfig
from ..rocket.architecture import apply_architecture
from ..rocket.parameters import apply_design
from ..rocket.vaso_pressao import eh_parametrico, preparar_motor, remodelar_corpo
from ..utils.logging import get_logger
from .metrics import FlightMetrics, extract_metrics

log = get_logger("simulation.runner")


def _fin_geometry(design: dict[str, Any]) -> dict[str, float]:
    """Métricas geométricas da aleta (em cm) derivadas do design, para as
    restrições construtivas checarem — ex.: garantir raiz mínima colável.

    fin_root_cm      = comprimento da raiz (linha de cola contra o corpo)
    fin_total_chord  = extensão axial total da aleta (raiz vs. ponta enflechada)
    fin_root_ratio   = raiz / corda total (0..1); baixo = aleta grande colada por
                       uma raiz pequena, que descola no lançamento
    """
    if "fin_root" not in design:
        return {}
    root = float(design.get("fin_root", 0.0))
    total = max(root, float(design.get("fin_sweep", 0.0)) + float(design.get("fin_tip", 0.0)))
    out = {
        "fin_root_cm": root,
        "fin_total_chord": total,
        "fin_root_ratio": (root / total) if total > 1e-9 else 1.0,
    }

    # Rigidez aeroelástica da aleta (índice RELATIVO — ver aeroelastica.py).
    # O OpenRocket trata a aleta como rígida; nada na simulação penaliza uma
    # chapa fina e esbelta que balança. Sem isto, "leveza" empurra a busca para
    # a aleta mais mole possível.
    from ..rocket.aeroelastica import flutter_trapezio

    tip = float(design.get("fin_tip", 0.0))
    span = float(design.get("fin_height", 0.0))
    esp = float(design.get("fin_thickness", 0.0))
    mat = str(design.get("fin_material", ""))
    if root > 0 and span > 0 and esp > 0 and mat:
        d = flutter_trapezio(root / 100.0, tip / 100.0, span / 100.0, esp / 1000.0, mat)
        if d:
            out["fin_flutter_velocity"] = d["flutter_velocity"]
            out["fin_aspect_ratio"] = d["fin_aspect_ratio"]
            out["fin_taper_ratio"] = d["fin_taper_ratio"]
            out["fin_thickness_ratio"] = d["fin_thickness_ratio"]
    return out


@dataclass
class EvalResult:
    design: dict[str, Any]
    metrics: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    error: str | None = None
    duration_s: float = 0.0

    @property
    def ok(self) -> bool:
        return self.error is None


class Runner:
    """Executa avaliações (design -> métricas) num único processo/JVM."""

    def __init__(self, cfg: AppConfig) -> None:
        self.cfg = cfg
        self.bridge = OrBridge()  # inicia a JVM se necessário
        self.specs: dict[str, ParameterConfig] = {p.name: p for p in cfg.parameters}
        self._cache_motores = Path(cfg.output_dir) / "_motores_gerados"

    # ---------- API principal ----------

    def evaluate(
        self, design: dict[str, Any], sim_overrides: dict[str, float] | None = None
    ) -> EvalResult:
        """Aplica o design, roda a simulação e devolve as métricas.

        sim_overrides: overrides extras de simulação só desta avaliação
        (ex.: random_seed diferente para teste de robustez ao vento)."""
        start = time.perf_counter()
        try:
            doc, sim = self._prepare(design, sim_overrides)
            self.bridge.run_simulation(sim)
            metrics: FlightMetrics = extract_metrics(sim, doc)
            m = metrics.to_dict()
            m.update(_fin_geometry(design))   # métricas de geometria da aleta
            return EvalResult(
                design=dict(design),
                metrics=m,
                warnings=metrics.warnings,
                duration_s=time.perf_counter() - start,
            )
        except Exception as exc:  # falha de sim individual não derruba o lote
            log.warning("Avaliação falhou para %s: %s", design, exc)
            return EvalResult(
                design=dict(design),
                error=f"{type(exc).__name__}: {exc}",
                duration_s=time.perf_counter() - start,
            )

    def save_design(self, design: dict[str, Any], out_path: str) -> str:
        """Aplica o design e salva um novo .ork."""
        doc, _sim = self._prepare(design)
        self.bridge.save_document(doc, out_path)
        return out_path

    def baseline_design(self) -> dict[str, Any]:
        from ..rocket.parameters import read_current_values

        doc = self.bridge.load_document(self.cfg.base_ork)
        return read_current_values(self.bridge, doc, self.specs)

    def component_tree(self) -> list[dict[str, str]]:
        doc = self.bridge.load_document(self.cfg.base_ork)
        return self.bridge.component_tree(doc)

    # ---------- interno ----------

    def _prepare(
        self, design: dict[str, Any], sim_overrides: dict[str, float] | None = None
    ) -> tuple[Any, Any]:
        doc = self.bridge.load_document(self.cfg.base_ork)
        apply_architecture(self.bridge, doc, design, self.specs)
        # corpo paramétrico: o vaso de pressão vira geometria livre e o motor
        # é gerado proporcionalmente a ele
        motor_param = None
        if eh_parametrico(design):
            geo = remodelar_corpo(self.bridge, doc, design, self.specs)
            motor_param = preparar_motor(design, self.specs, geo, self._cache_motores)
        pending_motor = apply_design(self.bridge, doc, design, self.specs)
        sim = self.bridge.get_simulation(doc, self.cfg.simulation.simulation_name)
        # parâmetros de design com attribute sim_<opcao> viram overrides de
        # simulação (ex.: sim_launch_rod_angle_deg -> ângulo do lançamento)
        design_sim: dict[str, float] = {}
        for name, value in design.items():
            spec = self.specs.get(name)
            if spec is not None and spec.attribute.startswith("sim_"):
                design_sim[spec.attribute[4:]] = float(value)
        overrides = {**self.cfg.simulation.overrides, **design_sim, **(sim_overrides or {})}
        self.bridge.apply_sim_overrides(sim, overrides)
        if motor_param is not None:
            mount = None
            for c in self.bridge.iter_components(doc):
                if "cilindro" in str(c.getName()).lower():
                    mount = str(c.getName()); break
            self.bridge.set_motor(doc, sim, mount, f"file:{motor_param.caminho}")
        for _name, (spec, value) in pending_motor.items():
            if spec.attribute == "motor":
                designation, _, manufacturer = str(value).partition("@")
                self.bridge.set_motor(
                    doc, sim, spec.component, designation, manufacturer or None
                )
            elif spec.attribute == "ejection_delay":
                mount = self.bridge.find_component(doc, spec.component)
                fcid = sim.getFlightConfigurationId()
                mount.getMotorConfig(fcid).setEjectionDelay(float(value))
        return doc, sim
