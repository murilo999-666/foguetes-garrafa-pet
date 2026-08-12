"""Diagnóstico: por que bit04 e bit05 não subiram nos lançamentos reais.

Fato de campo (2026-08): a bancada só chegou a 140–150 psi (não os 170 psi de
projeto). Os dois foguetes saíram rasos e bateram numa cerca à frente.

Este script simula os DOIS modelos finais na mesma faixa de pressão (130→190
psi), com o motor da carga que cada um usa, e imprime o que muda: velocidade de
saída do trilho, aceleração, apogeu, alcance e estabilidade. É a evidência
numérica que separa "faltou pressão" de "o projeto era frágil".
"""

from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from orx.config import load_config
from orx.config.loader import AppConfig, BatchConfig, SimulationConfig
from orx.simulation.runner import Runner
from orx.utils.logging import setup_logging

MOTORES = Path(r"D:\OBAFOG\bit07 robusto 2L\motores")
PRESSOES = [130, 140, 150, 160, 170, 180, 190]

FOGUETES = [
    # (rótulo, .ork, carga de vinagre usada, ângulo de projeto, lastro conhecido)
    ("bit04 (otimizado, 416 g de lastro)",
     r"D:\OBAFOG\bit04 2L script\bit04_MODELO_FINAL.ork", "1_80", 52.0),
    ("bit05 (humano, 115 g de lastro)",
     r"D:\OBAFOG\bit05 2L humano\bit05_MODELO_FINAL.ork", "1_55", 46.0),
]


def motor_file(carga: str, psi: int) -> str:
    return f"file:{MOTORES / f'Bit07-L{carga}-P{psi:03d}.eng'}"


def cfg_para(ork: str) -> AppConfig:
    """Config mínima: um único parâmetro (o motor) sobre o .ork existente."""
    base = load_config(r"C:\Users\muril\openrocket-optimizer\config\bit04.yaml")
    from orx.config.loader import ParameterConfig

    p = ParameterConfig(
        name="motor", component="Garrafa 2L - cilindro", attribute="motor",
        choices=[motor_file("1_80", 170)],
    )
    return dataclasses.replace(
        base, base_ork=ork, parameters=(p,), batch=BatchConfig(workers=1),
        simulation=SimulationConfig(overrides={"random_seed": 42, "time_step": 0.005}),
    )


def mount_de(runner: Runner) -> str:
    for c in runner.component_tree():
        if "cilindro" in c["name"].lower():
            return c["name"]
    raise SystemExit("nenhum corpo 'cilindro' para montar o motor")


def main() -> None:
    setup_logging()
    for rotulo, ork, carga, angulo in FOGUETES:
        cfg = cfg_para(ork)
        runner = Runner(cfg)
        mount = mount_de(runner)
        runner.specs["motor"] = dataclasses.replace(runner.specs["motor"], component=mount)
        print(f"\n{'=' * 92}\n{rotulo}\n  {ork}\n  motor: {carga.replace('_', ',')} L "
              f"de vinagre | lançamento a {angulo:.0f}°\n{'=' * 92}")
        print(f"{'psi':>5s} {'saída trilho':>13s} {'acel máx':>10s} {'apogeu':>8s} "
              f"{'alcance':>9s} {'estab min':>10s} {'estab máx':>10s} {'massa':>8s}")
        base = None
        for psi in PRESSOES:
            r = runner.evaluate(
                {"motor": motor_file(carga, psi)},
                sim_overrides={"random_seed": 42, "time_step": 0.005,
                               "launch_rod_angle_deg": angulo},
            )
            if not r.ok:
                print(f"{psi:5d}  ERRO: {r.error}")
                continue
            m = r.metrics
            if base is None:
                base = m.get("horizontal_distance") or 1.0
            def f(k, d=0.0):
                v = m.get(k)
                return d if v is None else v
            print(f"{psi:5d} {f('launch_rod_velocity'):11.1f}m/s {f('max_acceleration'):8.0f}m/s² "
                  f"{f('apogee'):7.1f}m {f('horizontal_distance'):8.1f}m "
                  f"{f('stability_min'):9.2f}c {f('stability_max'):9.2f}c "
                  f"{f('liftoff_mass') * 1000:6.0f}g")
        # segundo teste: a 140 psi (o que a bancada deu), quanto o vento entorta
        print(f"\n  -- a 140 psi, sensibilidade ao vento (weathercocking) --")
        print(f"  {'vento':>6s} {'alcance':>9s} {'apogeu':>8s} {'estab min':>10s}")
        for vento in (0.0, 2.0, 4.0, 6.0, 8.0):
            r = runner.evaluate(
                {"motor": motor_file(carga, 140)},
                sim_overrides={"random_seed": 42, "time_step": 0.005,
                               "launch_rod_angle_deg": angulo,
                               "wind_speed_average": vento},
            )
            if not r.ok:
                print(f"  {vento:5.1f}  ERRO")
                continue
            m = r.metrics
            g = lambda k: (m.get(k) if m.get(k) is not None else 0.0)
            print(f"  {vento:4.1f}m/s {g('horizontal_distance'):8.1f}m "
                  f"{g('apogee'):7.1f}m {g('stability_min'):9.2f}c")


if __name__ == "__main__":
    main()
