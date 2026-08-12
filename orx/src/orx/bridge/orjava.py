"""Wrappers finos e verificados sobre a API Java do OpenRocket 24.12.

Todos os nomes de classes/métodos usados aqui foram confirmados por reflexão
contra o jar instalado (scripts/dump_api.py -> scripts/api_dump*.txt).
"""

from __future__ import annotations

from typing import Any, Iterator

import jpype

from .jvm import ensure_jvm, motor_database
from ..utils.logging import get_logger

log = get_logger("bridge.orjava")


def J(name: str) -> Any:
    """Atalho para jpype.JClass com nome totalmente qualificado."""
    return jpype.JClass(name)


class OrBridge:
    """Operações de alto nível: carregar/salvar .ork, componentes, simulação."""

    def __init__(self) -> None:
        ensure_jvm()

    # ---------- documento ----------

    def load_document(self, ork_path: str) -> Any:
        File = J("java.io.File")
        loader = J("info.openrocket.core.file.GeneralRocketLoader")(File(ork_path))
        return loader.load()

    def save_document(self, doc: Any, out_path: str) -> None:
        File = J("java.io.File")
        J("info.openrocket.core.file.GeneralRocketSaver")().save(File(out_path), doc)

    # ---------- componentes ----------

    def iter_components(self, doc: Any) -> Iterator[Any]:
        """Percorre a árvore de componentes em profundidade."""

        def _walk(comp: Any) -> Iterator[Any]:
            yield comp
            for child in comp.getChildren():
                yield from _walk(child)

        yield from _walk(doc.getRocket())

    def find_components(self, doc: Any, pattern: str) -> list[Any]:
        """Componentes cujo nome casa com o padrão (glob: '*', '?'), case-insensitive."""
        import fnmatch

        wanted = pattern.strip().lower()
        matches = [
            c
            for c in self.iter_components(doc)
            if fnmatch.fnmatch(str(c.getName()).strip().lower(), wanted)
        ]
        if not matches:
            available = [str(c.getName()) for c in self.iter_components(doc)]
            raise KeyError(f"Componente '{pattern}' não encontrado. Disponíveis: {available}")
        return matches

    def find_component(self, doc: Any, name: str) -> Any:
        """Busca componente por nome exato ou glob (primeiro match)."""
        return self.find_components(doc, name)[0]

    def component_tree(self, doc: Any) -> list[dict[str, str]]:
        return [
            {"name": str(c.getName()), "type": str(c.getComponentName())}
            for c in self.iter_components(doc)
        ]

    # ---------- simulação ----------

    def get_simulation(self, doc: Any, name: str | None = None) -> Any:
        """Simulação do documento (por nome ou a primeira); cria se não houver."""
        sims = doc.getSimulations()
        if name:
            for i in range(sims.size()):
                if str(sims.get(i).getName()) == name:
                    return sims.get(i)
            raise KeyError(f"Simulação '{name}' não existe no .ork")
        if sims.size() > 0:
            return sims.get(0)
        Simulation = J("info.openrocket.core.document.Simulation")
        sim = Simulation(doc, doc.getRocket())
        doc.addSimulation(sim)
        return sim

    def apply_sim_overrides(self, sim: Any, overrides: dict[str, float]) -> None:
        """Aplica overrides do YAML nas SimulationOptions (nomes verificados)."""
        import math

        opts = sim.getOptions()
        setters = {
            "wind_speed_average": opts.setWindSpeedAverage,
            "wind_speed_deviation": opts.setWindSpeedDeviation,
            "wind_turbulence_intensity": opts.setWindTurbulenceIntensity,
            "wind_direction_deg": lambda v: opts.setWindDirection(math.radians(v)),
            "launch_rod_length": opts.setLaunchRodLength,
            "launch_rod_angle_deg": lambda v: opts.setLaunchRodAngle(math.radians(v)),
            "launch_rod_direction_deg": lambda v: opts.setLaunchRodDirection(math.radians(v)),
            "launch_altitude": opts.setLaunchAltitude,
            "launch_latitude": opts.setLaunchLatitude,
            "launch_longitude": opts.setLaunchLongitude,
            "launch_temperature": opts.setLaunchTemperature,
            "launch_pressure": opts.setLaunchPressure,
            "time_step": opts.setTimeStep,
            "max_simulation_time": opts.setMaxSimulationTime,
            "random_seed": lambda v: opts.setRandomSeed(int(v)),
        }
        for key, value in overrides.items():
            if key not in setters:
                raise KeyError(
                    f"Override de simulação desconhecido: {key}. Válidos: {sorted(setters)}"
                )
            setters[key](value)

    def run_simulation(self, sim: Any) -> Any:
        """Executa a simulação e devolve FlightData."""
        SimulationListener = J("info.openrocket.core.simulation.listeners.SimulationListener")
        sim.simulate(jpype.JArray(SimulationListener)([]))
        return sim.getSimulatedData()

    # ---------- motores ----------

    def find_motor(self, designation: str, manufacturer: str | None = None) -> Any:
        """Busca um ThrustCurveMotor por designação (ex.: 'C6') e fabricante."""
        wanted = designation.strip().lower()
        wanted_manu = manufacturer.strip().lower() if manufacturer else None
        candidates = []
        for mset in motor_database().getMotorSets():
            for motor in mset.getMotors():
                if str(motor.getDesignation()).strip().lower() != wanted:
                    continue
                manu = str(motor.getManufacturer().getDisplayName()).strip().lower()
                if wanted_manu and wanted_manu not in manu:
                    continue
                candidates.append(motor)
        if not candidates:
            raise KeyError(f"Motor '{designation}' (fabricante={manufacturer}) não encontrado")
        return candidates[0]

    def search_motors(self, text: str, limit: int = 25) -> list[dict[str, Any]]:
        text = text.strip().lower()
        out: list[dict[str, Any]] = []
        for mset in motor_database().getMotorSets():
            for motor in mset.getMotors():
                desig = str(motor.getDesignation())
                manu = str(motor.getManufacturer().getDisplayName())
                if text in desig.lower() or text in manu.lower():
                    out.append(
                        {
                            "designation": desig,
                            "manufacturer": manu,
                            "diameter_mm": float(motor.getDiameter()) * 1000,
                            "length_mm": float(motor.getLength()) * 1000,
                            "total_impulse_Ns": float(motor.getTotalImpulseEstimate()),
                        }
                    )
                    if len(out) >= limit:
                        return out
        return out

    _file_motor_cache: dict[str, Any] = {}

    def load_motor_file(self, path: str) -> Any:
        """Carrega um ThrustCurveMotor de um arquivo .eng/.rse local."""
        if path in self._file_motor_cache:
            return self._file_motor_cache[path]
        import os

        FileInputStream = J("java.io.FileInputStream")
        loader = J("info.openrocket.core.file.motor.GeneralMotorLoader")()
        builders = loader.load(FileInputStream(path), os.path.basename(path))
        if builders is None or builders.size() == 0:
            raise ValueError(f"Nenhum motor carregado de {path}")
        motor = builders.get(0).build()
        self._file_motor_cache[path] = motor
        return motor

    def set_motor(
        self,
        doc: Any,
        sim: Any,
        mount_name: str,
        designation: str,
        manufacturer: str | None = None,
        ejection_delay: float | None = None,
    ) -> None:
        """Troca o motor do mount para a configuração de voo da simulação.

        designation aceita 'file:<caminho>.eng' para motores gerados
        localmente (fora do banco do OpenRocket)."""
        mount = self.find_component(doc, mount_name)
        if not mount.isMotorMount():
            mount.setMotorMount(True)
        fcid = sim.getFlightConfigurationId()
        rocket = doc.getRocket()
        # .ork sem configuração de voo registrada: o fcid da simulação é o
        # placeholder default, no qual setMotorConfig não registra — cria uma
        # configuração real e aponta a simulação para ela (como a GUI faz)
        if not any(str(i) == str(fcid) for i in rocket.getIds()):
            FlightConfigurationId = J(
                "info.openrocket.core.rocketcomponent.FlightConfigurationId"
            )
            fcid = FlightConfigurationId()
            rocket.createFlightConfiguration(fcid)
            sim.setFlightConfigurationId(fcid)
        # registra uma MotorConfiguration nova para o fcid (como a GUI faz);
        # mutar o retorno de getMotorConfig() não registra e a simulação aborta
        # com "No motors defined"
        MotorConfiguration = J("info.openrocket.core.motor.MotorConfiguration")
        motor_config = MotorConfiguration(mount, fcid)
        if designation.startswith("file:"):
            motor = self.load_motor_file(designation[5:])
        else:
            motor = self.find_motor(designation, manufacturer)
        motor_config.setMotor(motor)
        if ejection_delay is not None:
            motor_config.setEjectionDelay(float(ejection_delay))
        mount.setMotorConfig(motor_config, fcid)
