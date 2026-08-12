"""Simula um .ork COMO ELE ESTÁ (materiais/dimensões do arquivo), anexando um
motor .eng, com validação de robustez em 20 ventos.

Uso: python scripts/simular_ork.py <arquivo.ork> <motor.eng> [angulo_graus]
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from orx.bridge.orjava import OrBridge
from orx.simulation.metrics import extract_metrics

SEEDS = list(range(101, 121))


def simular(ork: str, motor_eng: str, angulo: float | None = None) -> None:
    b = OrBridge()
    dists, met = [], None
    for seed in SEEDS:
        doc = b.load_document(ork)
        sim = b.get_simulation(doc)
        # o mount é o cilindro da garrafa (2L ou reduzida)
        mount = None
        for c in b.iter_components(doc):
            if "cilindro" in str(c.getName()):
                mount = str(c.getName())
                break
        b.set_motor(doc, sim, mount, f"file:{motor_eng}")
        ov = {"random_seed": seed}
        if angulo is not None:
            ov["launch_rod_angle_deg"] = angulo
        b.apply_sim_overrides(sim, ov)
        b.run_simulation(sim)
        m = extract_metrics(sim, doc)
        if m.horizontal_distance:
            dists.append(m.horizontal_distance)
            met = met or m
    a = np.array(dists)
    nome = Path(ork).name
    print(f"\n{nome}  (motor {Path(motor_eng).stem}"
          + (f", {angulo:.0f}°" if angulo else "") + ")")
    if not a.size:
        print("  nenhum voo válido")
        return
    print(f"  alcance médio (20 ventos): {a.mean():.1f} m  (±{a.std():.1f}, pior {a.min():.1f})")
    print(f"  apogeu {met.apogee:.0f} m | vel.máx {met.max_velocity:.0f} m/s | "
          f"massa decolagem {met.liftoff_mass:.2f} kg")
    print(f"  estabilidade: inicial {met.stability_static:.2f} cal | "
          f"pós-queima {met.stability_max:.2f} cal"
          + ("   [ABAIXO de 1,0 — instável]" if met.stability_max < 1.0 else "   [ok, >=1,0]"))
    print(f"  lastro Durepoxi: {met.ballast_mass*1000:.0f} g")


if __name__ == "__main__":
    ang = float(sys.argv[3]) if len(sys.argv) > 3 else None
    simular(sys.argv[1], sys.argv[2], ang)
