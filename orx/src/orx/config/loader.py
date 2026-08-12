"""Carregamento e validação da configuração (YAML) da plataforma.

Todos os valores numéricos de parâmetros são expressos na unidade declarada em
``unit`` (mm, cm, m, g, kg, deg, rad, ...) e convertidos para SI apenas na hora
de aplicar no OpenRocket. O banco de resultados guarda os valores na unidade
declarada (legível para humanos).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# Fator de conversão -> unidade SI usada pelo OpenRocket (m, kg, rad).
UNIT_TO_SI: dict[str, float] = {
    "m": 1.0,
    "cm": 0.01,
    "mm": 0.001,
    "kg": 1.0,
    "g": 0.001,
    "rad": 1.0,
    "deg": 0.017453292519943295,
    "": 1.0,  # adimensional (contagem, coeficiente, categoria)
}


class ConfigError(Exception):
    """Configuração inválida."""


@dataclass(frozen=True)
class PathsConfig:
    openrocket_dir: str = r"C:\Program Files\OpenRocket"
    jar: str | None = None      # se None: auto-descoberta em openrocket_dir/jar
    jvm_dll: str | None = None  # se None: auto-descoberta em openrocket_dir/jre

    def resolve_jar(self) -> str:
        if self.jar:
            return self.jar
        jar_dir = Path(self.openrocket_dir) / "jar"
        jars = sorted(jar_dir.glob("OpenRocket-*.jar")) if jar_dir.exists() else []
        if not jars:
            raise ConfigError(
                f"Nenhum OpenRocket-*.jar encontrado em {jar_dir}. "
                "Defina paths.jar no YAML."
            )
        return str(jars[-1])

    def resolve_jvm(self) -> str:
        if self.jvm_dll:
            return self.jvm_dll
        dll = Path(self.openrocket_dir) / "jre" / "bin" / "server" / "jvm.dll"
        if not dll.exists():
            raise ConfigError(
                f"jvm.dll não encontrada em {dll}. Defina paths.jvm_dll no YAML."
            )
        return str(dll)


@dataclass(frozen=True)
class ParameterConfig:
    """Um parâmetro otimizável do foguete."""

    name: str                      # identificador único (ex.: fin_root_chord)
    component: str                 # nome do componente no projeto (ex.: "Trapezoidal fin set")
    attribute: str                 # atributo mapeado (ex.: root_chord, shape, motor)
    unit: str = ""                 # mm, cm, m, g, kg, deg, rad, ""
    low: float | None = None       # limite inferior (contínuo/inteiro)
    high: float | None = None      # limite superior
    step: float | None = None      # passo p/ grid search (opcional)
    choices: list[Any] | None = None  # categórico (ex.: formatos de cone, motores)
    integer: bool = False          # inteiro (ex.: número de aletas)
    options: dict[str, Any] = field(default_factory=dict)  # extras do atributo (ex.: densidade)

    def __post_init__(self) -> None:
        if self.unit not in UNIT_TO_SI:
            raise ConfigError(f"Parâmetro {self.name}: unidade desconhecida '{self.unit}'")
        if self.choices is None and (self.low is None or self.high is None):
            raise ConfigError(
                f"Parâmetro {self.name}: defina low/high (numérico) ou choices (categórico)"
            )

    @property
    def is_categorical(self) -> bool:
        return self.choices is not None

    def to_si(self, value: Any) -> Any:
        if self.is_categorical:
            return value
        return float(value) * UNIT_TO_SI[self.unit]


@dataclass(frozen=True)
class ObjectiveConfig:
    """Função objetivo: nome de métrica ou expressão sobre métricas."""

    metric: str = "horizontal_distance"
    direction: str = "maximize"  # maximize | minimize

    def __post_init__(self) -> None:
        if self.direction not in ("maximize", "minimize"):
            raise ConfigError(f"objective.direction inválido: {self.direction}")


@dataclass(frozen=True)
class ConstraintConfig:
    metric: str
    min: float | None = None
    max: float | None = None


@dataclass(frozen=True)
class OptimizerConfig:
    algorithm: str = "random"          # grid|random|hill_climbing|annealing|genetic|optuna|nevergrad|adaptive
    max_evaluations: int = 100
    seed: int | None = None
    profile: str = "balanced"          # wide | balanced | local (modo adaptativo)
    infeasible_penalty: float | None = None  # score atribuído a designs inviáveis (None = pior observado)
    options: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SimulationConfig:
    """Overrides das opções de simulação (unidades SI; ângulos em graus)."""

    overrides: dict[str, float] = field(default_factory=dict)
    # chaves aceitas: wind_speed_average (m/s), wind_speed_deviation (m/s),
    # wind_turbulence_intensity (0-1), wind_direction_deg, launch_rod_length (m),
    # launch_rod_angle_deg, launch_rod_direction_deg, launch_altitude (m),
    # launch_latitude, launch_longitude, launch_temperature (K),
    # launch_pressure (Pa), time_step (s), max_simulation_time (s), random_seed
    simulation_name: str | None = None  # usar simulação nomeada do .ork (None = primeira)


@dataclass(frozen=True)
class BatchConfig:
    workers: int = 1               # processos paralelos (1 JVM cada)
    save_timeseries: bool = False  # salvar CSV da série temporal de cada sim


@dataclass(frozen=True)
class AppConfig:
    base_ork: str
    paths: PathsConfig = field(default_factory=PathsConfig)
    simulation: SimulationConfig = field(default_factory=SimulationConfig)
    parameters: tuple[ParameterConfig, ...] = ()
    objective: ObjectiveConfig = field(default_factory=ObjectiveConfig)
    constraints: tuple[ConstraintConfig, ...] = ()
    optimizer: OptimizerConfig = field(default_factory=OptimizerConfig)
    batch: BatchConfig = field(default_factory=BatchConfig)
    db_path: str = "results/orx.sqlite"
    output_dir: str = "results"

    def parameter(self, name: str) -> ParameterConfig:
        for p in self.parameters:
            if p.name == name:
                return p
        raise ConfigError(f"Parâmetro desconhecido: {name}")


def _build_parameters(raw: list[dict[str, Any]]) -> tuple[ParameterConfig, ...]:
    params = tuple(ParameterConfig(**item) for item in raw)
    names = [p.name for p in params]
    if len(names) != len(set(names)):
        raise ConfigError(f"Nomes de parâmetros duplicados: {names}")
    return params


def load_config(path: str | os.PathLike[str]) -> AppConfig:
    """Carrega o YAML de configuração e devolve um AppConfig validado."""
    path = Path(path)
    if not path.exists():
        raise ConfigError(f"Arquivo de configuração não encontrado: {path}")
    with open(path, encoding="utf-8") as f:
        raw: dict[str, Any] = yaml.safe_load(f) or {}

    if "base_ork" not in raw:
        raise ConfigError("Configuração precisa de 'base_ork' (caminho do .ork)")

    base_dir = path.parent
    base_ork = str((base_dir / raw["base_ork"]).resolve()) if not os.path.isabs(raw["base_ork"]) else raw["base_ork"]
    if not Path(base_ork).exists():
        raise ConfigError(f"Arquivo .ork não encontrado: {base_ork}")

    def _resolve(p: str) -> str:
        return p if os.path.isabs(p) else str((base_dir / p).resolve())

    return AppConfig(
        base_ork=base_ork,
        paths=PathsConfig(**raw.get("paths", {})),
        simulation=SimulationConfig(**raw.get("simulation", {})),
        parameters=_build_parameters(raw.get("parameters", [])),
        objective=ObjectiveConfig(**raw.get("objective", {})),
        constraints=tuple(ConstraintConfig(**c) for c in raw.get("constraints", [])),
        optimizer=OptimizerConfig(**raw.get("optimizer", {})),
        batch=BatchConfig(**raw.get("batch", {})),
        db_path=_resolve(raw.get("db_path", "results/orx.sqlite")),
        output_dir=_resolve(raw.get("output_dir", "results")),
    )
