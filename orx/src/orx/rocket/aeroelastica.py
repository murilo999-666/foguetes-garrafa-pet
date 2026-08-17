"""Flutter de aleta — o modo de falha que o OpenRocket não calcula.

Aleta é uma placa em balanço dentro de um escoamento. Acima de uma velocidade
crítica, a torção e a flexão da placa acoplam e a oscilação diverge: a aleta
vibra, deforma e arranca. Não existe aviso no OpenRocket — a simulação continua
alegremente com a aleta "rígida".

Isso importa MUITO aqui porque a busca livre premia leveza, e leveza empurra a
espessura para o mínimo e a envergadura para o máximo — exatamente a receita de
uma aleta que balança. Uma chapa de polietileno de 1 mm com 13 cm de
envergadura é visivelmente mole na mão.

Fórmula clássica (NACA TN 4197, na forma divulgada pela Apogee):

    Vf = a * sqrt( G / ( 1.337 * AR^3 * P * (lambda+1)
                         / ( 2*(AR+2) * (t/c)^3 ) ) )

    a      velocidade do som (m/s)
    G      módulo de cisalhamento do material da aleta (Pa)
    AR     alongamento do painel = envergadura^2 / area
    lambda afilamento = corda da ponta / corda da raiz
    P      pressão atmosférica (Pa)
    t/c    espessura / corda da raiz

A fórmula é para painel trapezoidal em balanço; para aleta de formato livre
usamos o trapézio equivalente (mesma área, mesma envergadura, mesmas cordas de
raiz e ponta). É uma estimativa de engenharia, não um resultado de CFD — serve
para separar "seguro" de "temerário", que é o que falta hoje.
"""

from __future__ import annotations

import math

# Módulo de cisalhamento G = E / (2(1+v)), em Pa.
# Valores de referência para chapa/impressão; PET e PE variam com a orientação
# das cadeias (a parede de garrafa é biaxialmente orientada, fica mais rígida
# que o PET amorfo) — por isso são valores conservadores.
SHEAR_MODULUS: dict[str, float] = {
    "pla": 1.29e9,           # E 3,5 GPa, v 0,36
    "petg": 0.75e9,          # E 2,1 GPa, v 0,40
    "poliestireno": 1.19e9,  # E 3,2 GPa, v 0,34
    "polietileno": 0.35e9,   # HDPE: E 1,0 GPa, v 0,42  <- o mais mole da lista
    "pet_garrafa": 1.00e9,   # E 2,8 GPa, v 0,40 (parede orientada)
    "papel_cartao": 0.58e9,  # muito variável; estimativa conservadora
    "balsa": 0.12e9,
}


def flutter_velocity(
    area_m2: float,
    span_m: float,
    root_chord_m: float,
    tip_chord_m: float,
    thickness_m: float,
    shear_modulus_pa: float,
    pressure_pa: float = 101325.0,
    speed_of_sound: float = 340.3,
) -> float | None:
    """Velocidade crítica de flutter (m/s). None se a geometria for degenerada."""
    if min(area_m2, span_m, root_chord_m, thickness_m, shear_modulus_pa) <= 0:
        return None
    ar = span_m * span_m / area_m2                 # alongamento do painel
    lam = max(tip_chord_m, 0.0) / root_chord_m     # afilamento
    tc = thickness_m / root_chord_m                # espessura relativa
    if ar <= 0 or tc <= 0:
        return None
    denom = (1.337 * ar ** 3 * pressure_pa * (lam + 1.0)) / (2.0 * (ar + 2.0) * tc ** 3)
    if denom <= 0:
        return None
    return speed_of_sound * math.sqrt(shear_modulus_pa / denom)


def flutter_trapezio(root_m: float, tip_m: float, span_m: float,
                     thickness_m: float, material: str,
                     pressure_pa: float = 101325.0,
                     speed_of_sound: float = 340.3) -> dict[str, float] | None:
    """Flutter do painel trapezoidal — a forma que a fórmula pressupõe.

    ATENÇÃO à corda da raiz: é a corda NA BASE da aleta, não a extensão axial
    total do contorno. Numa aleta enflechada a ponta avança muito além da raiz
    (aqui: raiz 71 mm, extensão total 140 mm) e usar a extensão total dobra o
    t/c, o que derruba a velocidade de flutter por um fator ~2,8.
    """
    g = SHEAR_MODULUS.get(material.replace("orx_", "").lower())
    if g is None or root_m <= 0 or span_m <= 0 or thickness_m <= 0:
        return None
    area = (root_m + max(tip_m, 0.0)) / 2.0 * span_m
    if area <= 0:
        return None
    vf = flutter_velocity(area, span_m, root_m, tip_m, thickness_m, g,
                          pressure_pa, speed_of_sound)
    if vf is None:
        return None
    return {
        "flutter_velocity": vf,
        "fin_area_cm2": area * 1e4,
        "fin_aspect_ratio": span_m * span_m / area,
        "fin_taper_ratio": max(tip_m, 0.0) / root_m,
        "fin_thickness_ratio": thickness_m / root_m,
        "fin_shear_modulus_gpa": g / 1e9,
    }


def flutter_from_finset(fin_points_m: list[tuple[float, float]],
                        thickness_m: float,
                        material: str,
                        pressure_pa: float = 101325.0,
                        speed_of_sound: float = 340.3) -> dict[str, float] | None:
    """Extrai o trapézio equivalente dos pontos da aleta e devolve o flutter.

    Convenção dos pontos do OpenRocket: y=0 é a superfície do corpo no bordo de
    ataque da raiz; y cresce para fora. A raiz é a parte com y baixo (encostada
    no corpo) e a ponta é a parte em y máximo.
    """
    if len(fin_points_m) < 3:
        return None
    ys = [y for _, y in fin_points_m]
    y_max = max(ys)
    if y_max <= 0:
        return None
    # ponta: extensão em x dos pontos no topo
    xs_topo = [x for x, y in fin_points_m if abs(y - y_max) < 1e-9]
    tip = (max(xs_topo) - min(xs_topo)) if len(xs_topo) > 1 else 0.0
    # raiz: extensão em x dos pontos colados no corpo (metade inferior baixa)
    lim = y_max * 0.10
    xs_raiz = [x for x, y in fin_points_m if y <= lim]
    root = (max(xs_raiz) - min(xs_raiz)) if len(xs_raiz) > 1 else 0.0
    if root <= 0:
        return None
    return flutter_trapezio(root, tip, y_max, thickness_m, material,
                            pressure_pa, speed_of_sound)
