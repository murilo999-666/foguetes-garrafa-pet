"""Modelo físico do motor vinagre + bicarbonato (CO2) em garrafa PET 2L.

Química (bicarbonato em EXCESSO, como o Murilo faz — ~200 g):
    NaHCO3 + CH3COOH -> CH3COONa + H2O + CO2
    Vinagre comercial 4% m/v -> 0,666 mol de ácido (= mol de CO2) por litro.
    O CO2 divide-se entre o headspace (gás) e o líquido (dissolvido, lei de
    Henry). kH_eff é CALIBRADO no dado real do Murilo: ~1,55 L de vinagre na
    garrafa de 2 L (headspace ~0,55 L) atingiu 170 psi manométricos.

Lançamento (garrafa invertida, bico = bocal PCO 28 mm, furo 21,7 mm):
    Fase 1 — expulsão do líquido: jato incompressível (Bernoulli, Cd=0,95),
       F = 2·Cd²·(P−Pa)·A. O gás expande politropicamente (γp=1,15) e o CO2
       dissolvido DESGASEIFICA (relaxação com constante τ) sustentando a
       pressão — é o que diferencia este motor de um foguete de água a ar
       comprimido. O líquido expelido leva consigo o CO2 nele dissolvido.
    Fase 2 — descarga do gás residual: bocal compressível (blocado/subsônico),
       mistura CO2+ar, resfriamento adiabático de blowdown.

Saída: arquivos .eng (RASP) por carga de vinagre + tabela comparativa.

Incertezas honestas (não elimináveis sem ensaio): τ de desgaseificação
(0,10 s baseline; a mistura espuma violentamente), Cd do gargalo, fração de
espuma no jato. O ponto de 170 psi ancora a QUÍMICA; os impulsos dos motores
antigos do Murilo (62–93 Ns p/ 1,5 L) servem de faixa de sanidade do ESCOAMENTO.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

# ---------------- constantes físicas ----------------
R = 8.314               # J/(mol K)
PA = 101_325.0          # Pa
T0 = 298.15             # K
ATM = 101_325.0

# ---------------- parâmetros do sistema ----------------
VINEGAR_ACID_MOL_L = 40.0 / 60.052   # 4% m/v ácido acético
RHO_LIQ = 1030.0        # kg/m3 (vinagre + acetato de sódio)
V_BOTTLE = 2.10e-3      # m3 — volume interno até a boca da garrafa "2 L"
NECK_BORE_D = 0.0217    # m — furo interno do bocal PCO 28 mm
A_NOZZLE = math.pi * (NECK_BORE_D / 2) ** 2
CD = 0.95               # coeficiente de descarga do gargalo liso
GAMMA_POLY = 1.15       # expansão do gás na fase líquida (entre isoterma e adiabática)
GAMMA_GAS = 1.30        # CO2(+ar) na descarga
M_CO2 = 0.044           # kg/mol
M_AIR = 0.029
TAU_OUTGAS = 0.10       # s — relaxação da desgaseificação (espuma violenta)

# ---------------- ponto de calibração (dado real do Murilo) ----------------
CAL_V_L = 1.55e-3       # m3 de vinagre ("pouco mais de 1,5 L")
CAL_P_GAUGE = 170.0 * 6894.76  # Pa (170 psi manométricos)


def acid_mol(v_liq_m3: float) -> float:
    return VINEGAR_ACID_MOL_L * v_liq_m3 * 1000.0


def calibrate_kh() -> float:
    """kH_eff [mol/(L·atm)] tal que o equilíbrio bata 170 psi em 1,55 L."""
    n_total = acid_mol(CAL_V_L)
    v_gas = V_BOTTLE - CAL_V_L
    p_co2 = CAL_P_GAUGE  # parcial de CO2 = manométrica (ar fica ~1 atm parcial)
    n_gas = p_co2 * v_gas / (R * T0)
    n_dis = n_total - n_gas
    if n_dis <= 0:
        raise ValueError("calibração inconsistente: todo CO2 caberia no headspace")
    return n_dis / ((p_co2 / ATM) * (CAL_V_L * 1000.0))


KH_EFF = calibrate_kh()


def equilibrium_pressure(v_liq_m3: float) -> float:
    """Pressão parcial de CO2 no equilíbrio pré-lançamento [Pa]."""
    n_total = acid_mol(v_liq_m3)
    v_gas = V_BOTTLE - v_liq_m3
    denom = v_gas / (R * T0) + KH_EFF * (v_liq_m3 * 1000.0) / ATM
    return n_total / denom


@dataclass
class MotorResult:
    name: str
    v_vinegar_L: float
    p0_gauge_psi: float
    peak_thrust_N: float
    burn_time_s: float
    total_impulse_Ns: float
    propellant_kg: float
    curve: list[tuple[float, float]]  # (t, F)


def simulate(v_liq0: float, name: str, dt: float = 1e-4) -> MotorResult:
    p_co2 = equilibrium_pressure(v_liq0)
    v_gas = V_BOTTLE - v_liq0
    n_air = PA * v_gas / (R * T0)
    n_gas_co2 = p_co2 * v_gas / (R * T0)
    n_dis = acid_mol(v_liq0) - n_gas_co2
    v_liq = v_liq0
    temp = T0
    t = 0.0
    curve: list[tuple[float, float]] = []
    impulse = 0.0
    peak = 0.0
    m_expelled = 0.0
    m_total_prop = RHO_LIQ * v_liq0 + M_CO2 * acid_mol(v_liq0) + M_AIR * n_air

    def pressure() -> float:
        return (n_gas_co2 + n_air) * R * temp / v_gas

    # ---------------- fase 1: expulsão do líquido ----------------
    while v_liq > 1e-9:
        p = pressure()
        if p <= PA * 1.001:
            break
        u = CD * math.sqrt(2.0 * (p - PA) / RHO_LIQ)
        q = A_NOZZLE * u
        dv = min(q * dt, v_liq)
        thrust = RHO_LIQ * (A_NOZZLE * u) * u  # = 2 Cd^2 (P-Pa) A
        # líquido expelido leva o CO2 dissolvido proporcional
        if v_liq > 0:
            n_dis -= n_dis * (dv / v_liq)
        v_gas_new = v_gas + dv
        temp *= (v_gas / v_gas_new) ** (GAMMA_POLY - 1.0)
        v_gas = v_gas_new
        v_liq -= dv
        m_expelled += RHO_LIQ * dv
        # desgaseificação (relaxação para o equilíbrio de Henry na P atual)
        p_partial_co2 = n_gas_co2 * R * temp / v_gas
        n_eq = KH_EFF * (p_partial_co2 / ATM) * (v_liq * 1000.0)
        if n_dis > n_eq:
            dn = (n_dis - n_eq) * dt / TAU_OUTGAS
            n_dis -= dn
            n_gas_co2 += dn
        impulse += thrust * dt
        peak = max(peak, thrust)
        t += dt
        if len(curve) == 0 or t - curve[-1][0] >= 2e-3:
            curve.append((t, thrust))

    # ---------------- fase 2: descarga do gás ----------------
    crit = ((GAMMA_GAS + 1.0) / 2.0) ** (GAMMA_GAS / (GAMMA_GAS - 1.0))
    while t < 5.0:
        n_tot = n_gas_co2 + n_air
        if n_tot <= 1e-9:
            break
        p = pressure()
        if p <= PA * 1.02:
            break
        m_mix = (n_gas_co2 * M_CO2 + n_air * M_AIR) / n_tot
        rs = R / m_mix
        g = GAMMA_GAS
        if p / PA >= crit:  # blocado
            mdot = CD * A_NOZZLE * p * math.sqrt(g / (rs * temp)) * (2.0 / (g + 1.0)) ** (
                (g + 1.0) / (2.0 * (g - 1.0))
            )
            t_throat = temp * 2.0 / (g + 1.0)
            v_e = math.sqrt(g * rs * t_throat)
            p_throat = p * (2.0 / (g + 1.0)) ** (g / (g - 1.0))
            thrust = mdot * v_e + (p_throat - PA) * A_NOZZLE
        else:  # subsônico expandido a Pa
            t_e = temp * (PA / p) ** ((g - 1.0) / g)
            v_e = math.sqrt(max(2.0 * g / (g - 1.0) * rs * temp * (1.0 - (PA / p) ** ((g - 1.0) / g)), 0.0))
            rho_e = PA / (rs * t_e)
            mdot = CD * rho_e * A_NOZZLE * v_e
            thrust = mdot * v_e
        dn = mdot / m_mix * dt
        dn = min(dn, n_tot * 0.5)
        frac_co2 = n_gas_co2 / n_tot
        n_gas_co2 -= dn * frac_co2
        n_air -= dn * (1.0 - frac_co2)
        temp *= max(1.0 - (g - 1.0) * dn / n_tot, 0.5)  # blowdown adiabático
        m_expelled += dn * m_mix
        impulse += thrust * dt
        peak = max(peak, thrust)
        t += dt
        if t - curve[-1][0] >= 2e-3:
            curve.append((t, thrust))

    curve.append((t + 2e-3, 0.0))
    return MotorResult(
        name=name,
        v_vinegar_L=v_liq0 * 1000.0,
        p0_gauge_psi=(equilibrium_pressure(v_liq0)) / 6894.76,
        peak_thrust_N=peak,
        burn_time_s=t,
        total_impulse_Ns=impulse,
        propellant_kg=m_total_prop,
        curve=curve,
    )


def resample(curve: list[tuple[float, float]], n: int = 28) -> list[tuple[float, float]]:
    """Reduz a curva a ~n pontos preservando pico e forma (RASP)."""
    if len(curve) <= n:
        return curve
    peak_i = max(range(len(curve)), key=lambda i: curve[i][1])
    idx = sorted({0, peak_i, len(curve) - 1}
                 | {round(i * (len(curve) - 1) / (n - 1)) for i in range(n)})
    return [curve[i] for i in idx]


def write_eng(result: MotorResult, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{result.name}.eng"
    lines = [
        f"; Motor vinagre+bicarbonato fisico - {result.v_vinegar_L:.2f} L de vinagre 4%",
        f"; P0={result.p0_gauge_psi:.0f} psi man., pico={result.peak_thrust_N:.0f} N, "
        f"queima={result.burn_time_s:.2f} s, impulso={result.total_impulse_Ns:.1f} Ns",
        f"; quimica calibrada no dado real: 1,55 L -> 170 psi (kH_eff={KH_EFF:.4f} mol/L/atm)",
        f"{result.name} 104 230 0 {result.propellant_kg:.4f} {result.propellant_kg + 0.002:.4f} ORX-fisico",
    ]
    for tt, ff in resample(result.curve):
        if tt <= 0:
            tt = 1e-3
        lines.append(f"   {tt:.4f} {max(ff, 0.0):.2f}")
    path.write_text("\n".join(lines) + "\n", encoding="ascii")
    return path


def main() -> None:
    out_dir = Path(r"D:\1-Competicoes\OBAFOG\foguete_real\motores")
    loads_L = [0.6, 0.8, 1.0, 1.2, 1.4, 1.55, 1.7, 1.8]
    print(f"kH_eff calibrado = {KH_EFF:.4f} mol/(L·atm)  "
          f"[literatura agua pura ~0.034 — coerente]\n")
    print(f"{'motor':22s} {'vinagre':>8s} {'P0 psi':>7s} {'pico N':>7s} "
          f"{'queima s':>8s} {'impulso Ns':>10s} {'prop kg':>8s}")
    for v in loads_L:
        name = f"VinagreFisico-{str(v).replace('.', '_')}L"
        r = simulate(v * 1e-3, name)
        write_eng(r, out_dir)
        warn = "  << ACIMA de 170 psi ja validados!" if r.p0_gauge_psi > 175 else ""
        print(f"{r.name:22s} {r.v_vinegar_L:7.2f}L {r.p0_gauge_psi:7.0f} "
              f"{r.peak_thrust_N:7.0f} {r.burn_time_s:8.2f} {r.total_impulse_Ns:10.1f} "
              f"{r.propellant_kg:8.3f}{warn}")
    print(f"\n.eng gerados em {out_dir}")


if __name__ == "__main__":
    main()
