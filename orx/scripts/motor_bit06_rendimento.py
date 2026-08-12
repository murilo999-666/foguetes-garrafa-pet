"""Família de motores do bit06 (garrafa PET retornável REDUZIDA ~1,8 L),
parametrizada pelo RENDIMENTO DE CO2 da reação — não por psi absoluto.

Por que rendimento e não psi (correção sobre o grid do bit07)
------------------------------------------------------------
O bicarbonato entra em EXCESSO, então quem limita o CO2 é o ácido acético do
vinagre (4% m/v). Para uma carga V de vinagre existe um teto físico de CO2 e,
portanto, uma pressão NOMINAL P_nom(V) que só é atingida se a reação render
tudo e nada vazar. Pedir mais psi que P_nom(V) é impossível.

O grid do bit07 cruzava "carga x psi" livremente, o que gerava combinações
fisicamente inatingíveis (ex.: 0,90 L a 200 psi => precisaria de 1,8x mais CO2
do que o ácido daquela carga fornece). Aqui o eixo de incerteza é o rendimento:

    eta = CO2 que ficou no sistema / CO2 que o ácido poderia dar
    P(V, eta) = pressão de equilíbrio com eta * n_acido(V)

Como p é linear em n_total, P(V, eta) ~ eta * P_nom(V). Toda combinação do grid
é fisicamente possível por construção, e eta<1 representa exatamente o que
derrubou bit04/bit05: bicarbonato velho, vinagre fraco, reação incompleta ao
fechar, vazamento na rosca/bocal.

Ancoragem no dado real do Murilo
--------------------------------
bit04/bit05: esperava 170 psi (nominal), a bancada entregou 140-150 psi.
=> eta_real ~ 0,82-0,88. Por isso a busca ampla (etapa 1) roda em eta=0,80
(dia ruim, levemente pessimista) e a nota final varre eta de 0,70 a 1,00.

O modelo bit06 ANTIGO foi projetado em eta=1,00 (1,35 L -> "170 psi",
1,5 L -> "189 psi" — exatamente as pressões nominais). É a mesma premissa
otimista que já falhou duas vezes no campo.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import motor_vinagre as mv

# ---- corpo: garrafa retornável REDUZIDA ----
mv.V_BOTTLE = 1.82e-3          # m3 internos até a boca (~1,8 L úteis + gargalo)
DIAM_MM = 96                   # Ø 9,585 cm -> casa de motor 96 mm
K_FLIGHT = 2.172               # fator de escoamento calibrado nos 275 m reais

OUT = Path(r"D:\OBAFOG\bit06 1,8L\motores")

# cargas de vinagre (L). A reduzida comporta menos líquido; acima de ~1,5 L o
# headspace fica pequeno demais para a expulsão render.
LOADS_L = [0.50, 0.70, 0.90, 1.05, 1.20, 1.35, 1.50]

# cenários de rendimento da reação/vedação (o eixo de robustez)
ETAS = [0.70, 0.80, 0.90, 1.00]
ETA_BUSCA = 0.80               # cenário da etapa 1 (dia ruim realista)

_acid_nominal = mv.acid_mol    # guarda a original antes de qualquer patch


def set_yield(eta: float) -> None:
    mv.acid_mol = lambda v, _e=eta: _acid_nominal(v) * _e


def nominal_pressure_psi(v_L: float) -> float:
    set_yield(1.0)
    return mv.equilibrium_pressure(v_L * 1e-3) / 6894.76


def motor_name(v_L: float, eta: float) -> str:
    return f"Bit06-L{v_L:.2f}-E{int(round(eta * 100)):03d}".replace(".", "_")


def write_eng(result: mv.MotorResult, k: float, path: Path, v_L: float,
              eta: float, p_psi: float, p_nom: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"; bit06 garrafa reduzida ~1,8L | {v_L:.2f} L vinagre 4%",
        f"; rendimento de CO2 eta={eta:.2f} => P0={p_psi:.0f} psi man. "
        f"(teto fisico desta carga: {p_nom:.0f} psi)",
        f"; pico={result.peak_thrust_N * k:.0f} N | "
        f"impulso efetivo={result.total_impulse_Ns * k:.1f} Ns",
        f"; quimica kH_eff calibrada em 170 psi/1,55 L (garrafa 2L); "
        f"fator de voo k={k} (275 m reais)",
        f"{result.name} {DIAM_MM} 230 0 {result.propellant_kg:.4f} "
        f"{result.propellant_kg + 0.002:.4f} ORX-bit06",
    ]
    for tt, ff in mv.resample(result.curve):
        lines.append(f"   {max(tt, 1e-3):.4f} {max(ff * k, 0.0):.2f}")
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    manifesto: dict[str, dict] = {}
    print(f"garrafa reduzida V={mv.V_BOTTLE * 1e3:.2f} L | kH_eff={mv.KH_EFF:.4f} | "
          f"k={K_FLIGHT}\n")
    print(f"{'carga':>6s} {'P teto':>7s} | " +
          "  ".join(f"eta={e:.2f}" for e in ETAS))
    print("-" * 74)

    for v_L in LOADS_L:
        p_nom = nominal_pressure_psi(v_L)
        celulas = []
        for eta in ETAS:
            set_yield(eta)
            name = motor_name(v_L, eta)
            r = mv.simulate(v_L * 1e-3, name)
            p_psi = mv.equilibrium_pressure(v_L * 1e-3) / 6894.76
            write_eng(r, K_FLIGHT, OUT / f"{name}.eng", v_L, eta, p_psi, p_nom)
            manifesto[name] = {
                "arquivo": str(OUT / f"{name}.eng"),
                "carga_L": v_L,
                "eta": eta,
                "pressao_psi": round(p_psi, 1),
                "pressao_teto_psi": round(p_nom, 1),
                "impulso_Ns": round(r.total_impulse_Ns * K_FLIGHT, 2),
                "pico_N": round(r.peak_thrust_N * K_FLIGHT, 1),
                "queima_s": round(r.burn_time_s, 3),
                "propelente_kg": round(r.propellant_kg, 4),
            }
            celulas.append(f"{p_psi:4.0f}psi/{r.total_impulse_Ns * K_FLIGHT:4.0f}Ns")
        print(f"{v_L:5.2f}L {p_nom:6.0f}p | " + "  ".join(celulas))

    set_yield(1.0)
    (OUT / "manifesto.json").write_text(
        json.dumps(manifesto, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\n{len(manifesto)} motores + manifesto.json em {OUT}")
    print("Cada LINHA e uma carga de vinagre; cada COLUNA e o rendimento da reacao.")
    print(f"Etapa 1 da busca roda em eta={ETA_BUSCA:.2f} (o dia ruim medido no bit04/05).")


if __name__ == "__main__":
    main()
