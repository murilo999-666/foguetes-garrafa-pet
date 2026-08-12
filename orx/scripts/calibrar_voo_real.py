"""Calibração inversa v2 do motor no voo real do Murilo, sobre a garrafa FIEL.

Dado real: foguete ~bit03 (ogiva 26 cm PLA, ~113 g de lastro, aletas
similares), 1,55 L a 170 psi, 45° -> 275 m COM A COIFA LEVEMENTE TORTA
(trajetória arqueou para cima). Logo 275 m é PISO do potencial limpo.

Calibra k (tubo-guia + espuma + reação contínua) para três alvos:
  275 m (piso) | 285 m (central adotado) | 300 m (teto)
e gera a família VinagreReal-*.eng com o k central.
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import jpype
import motor_vinagre as mv
from orx.bridge.orjava import J, OrBridge
from orx.rocket.parameters import _set_bulk_material
from orx.simulation.metrics import extract_metrics
from orx.utils.logging import setup_logging

BASE = r"D:\OBAFOG\foguete_real\garrafa2L_base.ork"
SEEDS = [42, 101, 102, 103, 104, 105, 106, 107]
TMP_DIR = Path(r"D:\OBAFOG\foguete_real\motores\_cal")
TARGETS = [275.0, 285.0, 300.0]
K_CENTRAL_TARGET = 285.0


def write_scaled_eng(result: mv.MotorResult, scale: float, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"{result.name} 104 230 0 {result.propellant_kg:.4f} {result.propellant_kg + 0.002:.4f} ORX-real",
    ]
    for tt, ff in mv.resample(result.curve):
        lines.append(f"   {max(tt, 1e-3):.4f} {max(ff * scale, 0.0):.2f}")
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


def make_replica(bridge: OrBridge):
    """Garrafa fiel configurada como o foguete do voo real."""
    doc = bridge.load_document(BASE)
    Shape = J("info.openrocket.core.rocketcomponent.Transition$Shape")
    nose = bridge.find_component(doc, "Ogiva")
    nose.setLength(0.26)
    nose.setShapeType(Shape.OGIVE)
    nose.setThickness(0.001)
    _set_bulk_material(nose, "pla")
    ballast = bridge.find_component(doc, "Componente de massa")
    ballast.setComponentMass(0.113)
    fins = bridge.find_component(doc, "Conjunto de aletas de formato livre")
    Coordinate = J("info.openrocket.core.util.Coordinate")
    slope = -0.037 / 0.08  # inclinação do ombro (aprox. do bit03 real)
    pts = [
        Coordinate(0.0, 0.0, 0.0),
        Coordinate(0.06, 0.05, 0.0),
        Coordinate(0.09, 0.05, 0.0),
        Coordinate(0.08, 0.08 * slope, 0.0),
    ]
    fins.setPoints(jpype.JArray(Coordinate)(pts))
    return doc


def mean_range(bridge: OrBridge, base_result: mv.MotorResult, k: float) -> float:
    eng = TMP_DIR / f"cal_{k:.4f}.eng"
    write_scaled_eng(base_result, k, eng)
    dists = []
    for seed in SEEDS:
        doc = make_replica(bridge)
        sim = bridge.get_simulation(doc)
        bridge.set_motor(doc, sim, "Garrafa 2L - cilindro", f"file:{eng}")
        bridge.apply_sim_overrides(sim, {"random_seed": seed})
        bridge.run_simulation(sim)
        m = extract_metrics(sim, doc)
        if m.horizontal_distance:
            dists.append(m.horizontal_distance)
    return float(np.mean(dists)) if dists else 0.0


def solve_k(bridge: OrBridge, base_result: mv.MotorResult, target: float) -> float:
    lo, hi = 1.0, 3.5
    for _ in range(20):
        mid = (lo + hi) / 2
        r = mean_range(bridge, base_result, mid)
        if abs(r - target) < 0.5:
            return mid
        if r < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def main() -> None:
    setup_logging()
    bridge = OrBridge()
    base = mv.simulate(1.55e-3, "cal155")
    print(f"motor físico puro 1,55L: {base.total_impulse_Ns:.1f} Ns")

    ks = {}
    for target in TARGETS:
        k = solve_k(bridge, base, target)
        ks[target] = k
        print(f"alvo {target:.0f} m -> k={k:.3f} -> impulso efetivo "
              f"{base.total_impulse_Ns * k:.1f} Ns")

    k = ks[K_CENTRAL_TARGET]
    print(f"\n>>> adotado k={k:.3f} (alvo central {K_CENTRAL_TARGET:.0f} m, "
          f"coifa torta corrigida); banda k={ks[TARGETS[0]]:.3f}..{ks[TARGETS[-1]]:.3f}")

    out = Path(r"D:\OBAFOG\foguete_real\motores")
    print(f"\n{'motor':20s} {'P0 psi':>7s} {'impulso ef. Ns':>14s}")
    for v in [0.6, 0.8, 1.0, 1.2, 1.4, 1.55, 1.7, 1.8]:
        name = f"VinagreReal-{str(v).replace('.', '_')}L"
        r = mv.simulate(v * 1e-3, name)
        write_scaled_eng(r, k, out / f"{name}.eng")
        print(f"{name:20s} {r.p0_gauge_psi:7.0f} {r.total_impulse_Ns * k:14.1f}")
    (out / "fator_calibracao.txt").write_text(
        f"k central = {k:.4f} (alvo 285 m: voo real 275 m + correcao da coifa torta)\n"
        f"banda: k(275m)={ks[275.0]:.4f}  k(300m)={ks[300.0]:.4f}\n"
        f"replica: garrafa fiel + ogiva 26cm PLA + 113g lastro + aletas ~bit03, 45 graus\n",
        encoding="utf-8",
    )
    print(f"\nfamília VinagreReal-*.eng regravada em {out}")


if __name__ == "__main__":
    main()
