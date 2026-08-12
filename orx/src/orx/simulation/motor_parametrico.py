"""Motor vinagre+bicarbonato PARAMÉTRICO: gera a curva de empuxo para
QUALQUER geometria de vaso de pressão, não só a garrafa PET de catálogo.

Física (a mesma calibrada nos dados reais do Murilo):
  - química: vinagre 4% + bicarbonato em excesso; o CO₂ se reparte entre o
    headspace e o líquido (Henry), com kH_eff calibrado em 170 psi @ 1,55 L
    numa garrafa de 2,10 L;
  - lançamento: expulsão do líquido (Bernoulli) + desgaseificação sustentando
    a pressão + descarga do gás residual;
  - fator de escoamento de voo k=2,172, calibrado no voo real de 275 m
    (embute tubo-guia do lançador, espuma e reação continuada).

O que passa a ser livre: volume interno, carga de vinagre e diâmetro do bocal.

LIMITE FÍSICO: um vaso de pressão obedece à tensão de aro sigma = P·r/t. Um
corpo mais largo aguenta MENOS pressão para a mesma parede. Se a pressão de
equilíbrio passar do limite do material, o motor é rejeitado (estouraria).
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from pathlib import Path

R_GAS = 8.314
PA = 101_325.0
T0 = 298.15
ATM = 101_325.0

VINEGAR_ACID_MOL_L = 40.0 / 60.052   # vinagre 4% m/v
RHO_LIQ = 1030.0
KH_EFF = 0.0431                      # mol/(L·atm) — calibrado em 170 psi @1,55 L
K_FLIGHT = 2.172                     # calibrado no voo real de 275 m
CD = 0.95
GAMMA_POLY = 1.15
GAMMA_GAS = 1.30
M_CO2, M_AIR = 0.044, 0.029
TAU_OUTGAS = 0.10

# Tensão de aro admissível (Pa) — CALIBRADA no dado real do Murilo:
# a garrafa 2L retornável (raio 52 mm, parede 0,62 mm) opera a 170 psi, o que
# dá sigma = P*r/t = 98 MPa. PET soprado é biaxialmente orientado (cristaliza
# sob deformação) e chega a 150-220 MPa; adotamos 110 MPa, que reproduz ruptura
# em ~190 psi — coerente com os 150-190 psi medidos na literatura.
SIGMA_ADM = {
    "pet_garrafa": 110e6,   # ancorado no comportamento real da garrafa
    "pla": 25e6,            # impresso: a adesão entre camadas é o ponto fraco
    "poliestireno": 18e6,   # chapa colada: as emendas limitam
    "papel_cartao": 5e6,
    "balsa": 8e6,
}


class PressaoExcessiva(ValueError):
    """A pressão de equilíbrio passa do que o vaso aguenta (estouraria)."""


@dataclass
class MotorGerado:
    caminho: Path
    p0_psi: float
    p_max_psi: float
    impulso_Ns: float
    pico_N: float
    queima_s: float
    massa_prop_kg: float


def pressao_maxima(raio_m: float, parede_m: float, material: str = "pet_garrafa") -> float:
    """Pressão manométrica de ruptura pela tensão de aro (Pa)."""
    sigma = SIGMA_ADM.get(material, 15e6)
    return sigma * parede_m / max(raio_m, 1e-4)


def pressao_equilibrio(v_total_m3: float, v_liq_m3: float) -> float:
    """Pressão parcial de CO₂ no equilíbrio antes do lançamento (Pa)."""
    n_total = VINEGAR_ACID_MOL_L * v_liq_m3 * 1000.0
    v_gas = max(v_total_m3 - v_liq_m3, 1e-9)
    denom = v_gas / (R_GAS * T0) + KH_EFF * (v_liq_m3 * 1000.0) / ATM
    return n_total / denom


def _simular(v_total: float, v_liq0: float, area_bocal: float, dt: float = 1e-4):
    p_co2 = pressao_equilibrio(v_total, v_liq0)
    v_gas = v_total - v_liq0
    n_air = PA * v_gas / (R_GAS * T0)
    n_gas = p_co2 * v_gas / (R_GAS * T0)
    n_dis = VINEGAR_ACID_MOL_L * v_liq0 * 1000.0 - n_gas
    v_liq, temp, t = v_liq0, T0, 0.0
    curva, impulso, pico = [], 0.0, 0.0
    massa_prop = RHO_LIQ * v_liq0 + M_CO2 * VINEGAR_ACID_MOL_L * v_liq0 * 1000.0 + M_AIR * n_air

    # fase 1: expulsão do líquido
    while v_liq > 1e-9 and t < 5.0:
        p = (n_gas + n_air) * R_GAS * temp / v_gas
        if p <= PA * 1.001:
            break
        u = CD * math.sqrt(2.0 * (p - PA) / RHO_LIQ)
        dv = min(area_bocal * u * dt, v_liq)
        empuxo = RHO_LIQ * area_bocal * u * u
        if v_liq > 0:
            n_dis -= n_dis * (dv / v_liq)
        v_novo = v_gas + dv
        temp *= (v_gas / v_novo) ** (GAMMA_POLY - 1.0)
        v_gas, v_liq = v_novo, v_liq - dv
        p_par = n_gas * R_GAS * temp / v_gas
        n_eq = KH_EFF * (p_par / ATM) * (v_liq * 1000.0)
        if n_dis > n_eq:
            dn = (n_dis - n_eq) * dt / TAU_OUTGAS
            n_dis -= dn
            n_gas += dn
        impulso += empuxo * dt
        pico = max(pico, empuxo)
        t += dt
        if not curva or t - curva[-1][0] >= 2e-3:
            curva.append((t, empuxo))

    # fase 2: descarga do gás
    crit = ((GAMMA_GAS + 1.0) / 2.0) ** (GAMMA_GAS / (GAMMA_GAS - 1.0))
    while t < 5.0:
        n_tot = n_gas + n_air
        if n_tot <= 1e-9:
            break
        p = n_tot * R_GAS * temp / v_gas
        if p <= PA * 1.02:
            break
        m_mix = (n_gas * M_CO2 + n_air * M_AIR) / n_tot
        rs, g = R_GAS / m_mix, GAMMA_GAS
        if p / PA >= crit:
            mdot = CD * area_bocal * p * math.sqrt(g / (rs * temp)) * \
                (2.0 / (g + 1.0)) ** ((g + 1.0) / (2.0 * (g - 1.0)))
            v_e = math.sqrt(g * rs * temp * 2.0 / (g + 1.0))
            p_g = p * (2.0 / (g + 1.0)) ** (g / (g - 1.0))
            empuxo = mdot * v_e + (p_g - PA) * area_bocal
        else:
            t_e = temp * (PA / p) ** ((g - 1.0) / g)
            v_e = math.sqrt(max(2.0 * g / (g - 1.0) * rs * temp *
                                (1.0 - (PA / p) ** ((g - 1.0) / g)), 0.0))
            mdot = CD * (PA / (rs * t_e)) * area_bocal * v_e
            empuxo = mdot * v_e
        dn = min(mdot / m_mix * dt, n_tot * 0.5)
        frac = n_gas / n_tot
        n_gas -= dn * frac
        n_air -= dn * (1.0 - frac)
        temp *= max(1.0 - (g - 1.0) * dn / n_tot, 0.5)
        impulso += empuxo * dt
        pico = max(pico, empuxo)
        t += dt
        if t - curva[-1][0] >= 2e-3:
            curva.append((t, empuxo))
    curva.append((t + 2e-3, 0.0))
    return curva, impulso, pico, t, massa_prop


def _reamostrar(curva, n: int = 26):
    if len(curva) <= n:
        return curva
    i_pico = max(range(len(curva)), key=lambda i: curva[i][1])
    idx = sorted({0, i_pico, len(curva) - 1} |
                 {round(i * (len(curva) - 1) / (n - 1)) for i in range(n)})
    return [curva[i] for i in idx]


def gerar_motor(v_total_m3: float, fracao_vinagre: float, bocal_m: float,
                raio_vaso_m: float, parede_m: float, material: str,
                pasta_cache: Path, diametro_mm: float = 104.0,
                comprimento_mm: float = 230.0) -> MotorGerado:
    """Gera (ou reaproveita do cache) o .eng para esta geometria.

    Levanta PressaoExcessiva se o vaso não aguentaria a pressão resultante.
    """
    v_liq = max(min(fracao_vinagre, 0.92), 0.0) * v_total_m3
    if v_liq <= 1e-6:
        raise PressaoExcessiva("sem vinagre suficiente")

    p0 = pressao_equilibrio(v_total_m3, v_liq)
    p_max = pressao_maxima(raio_vaso_m, parede_m, material)
    if p0 > p_max:
        raise PressaoExcessiva(
            f"P0={p0/6894.76:.0f} psi > limite {p_max/6894.76:.0f} psi "
            f"(raio {raio_vaso_m*1000:.0f} mm, parede {parede_m*1000:.2f} mm, {material})")

    chave = hashlib.md5(
        f"{v_total_m3:.6f}|{v_liq:.6f}|{bocal_m:.5f}".encode()).hexdigest()[:12]
    pasta_cache.mkdir(parents=True, exist_ok=True)
    caminho = pasta_cache / f"param_{chave}.eng"

    area = math.pi * (bocal_m / 2) ** 2
    curva, impulso, pico, queima, massa_prop = _simular(v_total_m3, v_liq, area)
    if not caminho.exists():
        linhas = [
            f"; motor parametrico | vaso {v_total_m3*1000:.2f} L | vinagre {v_liq*1000:.2f} L",
            f"; P0={p0/6894.76:.0f} psi (limite {p_max/6894.76:.0f}) | bocal {bocal_m*1000:.1f} mm",
            f"; impulso efetivo {impulso*K_FLIGHT:.1f} Ns | pico {pico*K_FLIGHT:.0f} N",
            f"P{chave} {diametro_mm:.0f} {comprimento_mm:.0f} 0 "
            f"{massa_prop:.4f} {massa_prop + 0.002:.4f} ORX-param",
        ]
        for tt, ff in _reamostrar(curva):
            linhas.append(f"   {max(tt, 1e-3):.4f} {max(ff * K_FLIGHT, 0.0):.2f}")
        caminho.write_text("\n".join(linhas) + "\n", encoding="ascii")

    return MotorGerado(caminho, p0 / 6894.76, p_max / 6894.76,
                       impulso * K_FLIGHT, pico * K_FLIGHT, queima, massa_prop)
