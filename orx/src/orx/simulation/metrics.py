"""Extração de métricas de voo de uma simulação executada.

Nomes de métodos/constantes verificados por reflexão (scripts/api_dump*.txt).
Unidades: SI (m, m/s, s, kg); estabilidade em calibres.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np

from ..bridge.orjava import J


@dataclass
class FlightMetrics:
    apogee: float | None = None
    max_velocity: float | None = None
    max_acceleration: float | None = None
    max_mach: float | None = None
    time_to_apogee: float | None = None
    flight_time: float | None = None
    ground_hit_velocity: float | None = None
    deployment_velocity: float | None = None
    launch_rod_velocity: float | None = None
    horizontal_distance: float | None = None
    landing_east: float | None = None
    landing_north: float | None = None
    ejection_time: float | None = None
    stability_static: float | None = None
    stability_min: float | None = None
    stability_max: float | None = None
    cp_location: float | None = None
    cg_location: float | None = None
    liftoff_mass: float | None = None
    dry_mass: float | None = None      # massa após queimar todo o propelente (kg)
    ballast_mass: float | None = None  # soma dos componentes de massa (kg)
    rocket_length: float | None = None
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _clean(value: Any) -> float | None:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(v) or math.isinf(v) else v


def _series(branch: Any, type_name: str) -> np.ndarray:
    FlightDataType = J("info.openrocket.core.simulation.FlightDataType")
    dtype = getattr(FlightDataType, type_name)
    values = branch.get(dtype)
    if values is None:
        return np.array([])
    return np.array([float(v) for v in values], dtype=float)


def extract_metrics(sim: Any, doc: Any) -> FlightMetrics:
    """Extrai métricas do FlightData de uma simulação já executada."""
    m = FlightMetrics()
    data = sim.getSimulatedData()
    if data is None or data.getBranchCount() == 0:
        m.warnings.append("simulação sem dados")
        return m

    m.apogee = _clean(data.getMaxAltitude())
    m.max_velocity = _clean(data.getMaxVelocity())
    m.max_acceleration = _clean(data.getMaxAcceleration())
    m.time_to_apogee = _clean(data.getTimeToApogee())
    m.flight_time = _clean(data.getFlightTime())
    m.ground_hit_velocity = _clean(data.getGroundHitVelocity())
    m.deployment_velocity = _clean(data.getDeploymentVelocity())
    m.launch_rod_velocity = _clean(data.getLaunchRodVelocity())

    branch = data.getBranch(0)

    # Distância horizontal do lançamento ao pouso (TYPE_POSITION_XY = distância
    # lateral ao ponto de lançamento; último valor = pouso).
    xy = _series(branch, "TYPE_POSITION_XY")
    if xy.size:
        m.horizontal_distance = _clean(xy[-1])
    east = _series(branch, "TYPE_POSITION_X")
    north = _series(branch, "TYPE_POSITION_Y")
    if east.size:
        m.landing_east = _clean(east[-1])
    if north.size:
        m.landing_north = _clean(north[-1])

    mach = _series(branch, "TYPE_MACH_NUMBER")
    if mach.size:
        m.max_mach = _clean(np.nanmax(mach))

    mass = _series(branch, "TYPE_MASS")
    if mass.size:
        m.liftoff_mass = _clean(mass[0])
        # após a queima a massa para de cair: o mínimo da série É a massa seca
        # (estrutura + lastro, sem propelente) — a métrica de "leveza" honesta,
        # que não depende de qual motor/carga o design escolheu.
        m.dry_mass = _clean(np.nanmin(mass))

    ref_len = _series(branch, "TYPE_REFERENCE_LENGTH")
    time = _series(branch, "TYPE_TIME")

    # Estabilidade (calibres): série contém NaN fora do voo propulsado/estável.
    stab = _series(branch, "TYPE_STABILITY")
    if stab.size and time.size == stab.size:
        finite = np.isfinite(stab)
        # janela até o apogeu (fase que importa para estabilidade)
        if m.time_to_apogee is not None:
            finite &= time <= m.time_to_apogee
        vals = stab[finite]
        if vals.size:
            m.stability_static = _clean(vals[0])
            m.stability_min = _clean(vals.min())
            m.stability_max = _clean(vals.max())

    cp = _series(branch, "TYPE_CP_LOCATION")
    cg = _series(branch, "TYPE_CG_LOCATION")
    for series, attr in ((cp, "cp_location"), (cg, "cg_location")):
        finite = series[np.isfinite(series)] if series.size else np.array([])
        if finite.size:
            setattr(m, attr, _clean(finite[0]))

    try:
        m.rocket_length = _clean(doc.getRocket().getLength())
    except Exception:
        pass

    try:
        import jpype

        MassComponent = J("info.openrocket.core.rocketcomponent.MassComponent")

        def _walk(c: Any) -> float:
            total = float(c.getMass()) if isinstance(c, MassComponent) else 0.0
            for child in c.getChildren():
                total += _walk(child)
            return total

        m.ballast_mass = _clean(_walk(doc.getRocket()))
    except Exception:
        pass

    try:
        warning_set = sim.getSimulatedWarnings()
        if warning_set is not None:
            m.warnings.extend(str(w) for w in warning_set)
    except Exception:
        pass

    # tempo da carga de ejeção
    try:
        EventType = J("info.openrocket.core.simulation.FlightEvent$Type")
        event = branch.getFirstEvent(EventType.EJECTION_CHARGE)
        if event is not None:
            m.ejection_time = _clean(event.getTime())
    except Exception:
        pass

    return m
