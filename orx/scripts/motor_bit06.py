"""Família de motores vinagre+bicarbonato para a garrafa REDUZIDA do bit05.

Mesma química calibrada nos dados reais do Murilo (kH_eff do CO2, calibrado em
170 psi/1,55 L na garrafa 2L) e mesmo fator de escoamento de voo k=2,17
(calibrado nos 275 m reais — depende do bocal PCO-28 e da química, não do corpo).

O QUE MUDA: o volume interno da garrafa (2,10 L -> ~1,82 L). Com menos espaço
morto (headspace), a MESMA quantidade de vinagre gera MAIS pressão. E como o
raio é menor (4,79 vs 5,2 cm), a garrafa aguenta mais pressão (tensão de aro
sigma = P*r/t), então dá pra ir a cargas que atingem ~200-215 psi com segurança
relativa maior que a 2L nos mesmos psi.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import motor_vinagre as mv

# kH_eff já foi calibrado no import (garrafa 2L, 170 psi/1,55 L). Mantemos.
KH_EFF = mv.KH_EFF
K_FLIGHT = 2.172  # fator de escoamento calibrado nos 275 m reais (2L)

# agora troca o volume da garrafa para a reduzida (kH_eff permanece o de 2L)
mv.V_BOTTLE = 1.82e-3   # m3 internos até a boca (~1,8 L úteis + gargalo)

OUT = Path(r"D:\OBAFOG\bit06 1,8L script\motores")
# cargas de vinagre; a reduzida comporta menos líquido — máx ~1,5 L deixando
# headspace mínimo. As pressões sobem em relação à 2L para a mesma carga.
LOADS_L = [0.5, 0.7, 0.9, 1.05, 1.2, 1.35, 1.45, 1.5]


def write_scaled(result: mv.MotorResult, k: float, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"; bit05 garrafa reduzida ~1,8L | {result.v_vinegar_L:.2f} L vinagre 4%",
        f"; P0={result.p0_gauge_psi:.0f} psi man. | pico={result.peak_thrust_N:.0f} N | "
        f"impulso efetivo={result.total_impulse_Ns*k:.1f} Ns (k={k})",
        f"{result.name} 96 230 0 {result.propellant_kg:.4f} {result.propellant_kg + 0.002:.4f} ORX-bit05",
    ]
    for tt, ff in mv.resample(result.curve):
        lines.append(f"   {max(tt,1e-3):.4f} {max(ff*k, 0.0):.2f}")
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


def main() -> None:
    print(f"kH_eff (calibrado 2L) = {KH_EFF:.4f} mol/L/atm | V_garrafa reduzida = {mv.V_BOTTLE*1e3:.2f} L")
    print(f"fator de voo k = {K_FLIGHT}\n")
    print(f"{'motor':22s} {'vinagre':>8s} {'P0 psi':>7s} {'pico N':>7s} {'impulso ef. Ns':>14s}")
    for v in LOADS_L:
        name = f"VinagreBit05-{str(v).replace('.', '_')}L"
        r = mv.simulate(v * 1e-3, name)
        write_scaled(r, K_FLIGHT, OUT / f"{name}.eng")
        flag = "  << alta pressao" if r.p0_gauge_psi > 200 else ""
        print(f"{name:22s} {r.v_vinegar_L:7.2f}L {r.p0_gauge_psi:7.0f} {r.peak_thrust_N:7.0f} "
              f"{r.total_impulse_Ns*K_FLIGHT:14.1f}{flag}")
    (OUT / "info_motores.txt").write_text(
        f"Motores da garrafa reduzida bit05 (~1,8 L internos).\n"
        f"Quimica calibrada em 170 psi/1,55 L (2L); fator de voo k={K_FLIGHT} (275 m reais).\n"
        f"Volume menor -> mesma carga gera mais pressao que na 2L.\n"
        f"Raio menor (4,79 cm) -> aguenta mais pressao para a mesma parede.\n",
        encoding="utf-8")
    print(f"\nfamilia VinagreBit05-*.eng em {OUT}")


if __name__ == "__main__":
    main()
