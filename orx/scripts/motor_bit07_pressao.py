"""Família de motores do bit07 parametrizada por PRESSÃO REALMENTE ATINGIDA.

Motivo (2026-08-04): nos lançamentos reais do bit04 e do bit05 o Murilo só
conseguiu **140–150 psi**, não os 170 psi que ancoravam toda a calibração.
Os dois foguetes não subiram e bateram numa cerca à frente. Portanto o projeto
novo não pode ser otimizado para UMA pressão: ele precisa ir bem em toda a
faixa que a bancada realmente entrega.

Como a pressão vira parâmetro
-----------------------------
A química de `motor_vinagre.py` (Henry + blowdown bifásico, kH_eff calibrado em
170 psi / 1,55 L na garrafa 2 L) diz qual pressão de equilíbrio uma carga de
vinagre DEVERIA dar. Se a bancada entrega menos, é porque menos CO2 ficou no
sistema — bicarbonato insuficiente/velho, vinagre mais fraco que 4%, reação
incompleta na hora de fechar, vazamento pela rosca ou pelo bocal. Todos esses
casos se resumem, para efeito de motor, a um **rendimento de CO2** η < 1.

Como a pressão de equilíbrio é linear em n_total (p = n_total / denom, com
denom independente de η), sai direto:

    η(V, P_alvo) = P_alvo / P_nominal(V)

Menos CO2 => menos pressão E menos impulso (o gás dissolvido que sustentaria a
expulsão também some). É exatamente o efeito que derrubou os dois foguetes.

Saída: grade `carga de vinagre × pressão atingida` em .eng (RASP), já com o
fator de voo k=2,172 (calibrado nos 275 m reais do bit03), mais um manifesto
JSON com massa de propelente e impulso de cada motor — o otimizador usa o
manifesto para calcular massa seca e para trocar de pressão sem re-simular a
química.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import motor_vinagre as mv

K_FLIGHT = 2.172          # fator de escoamento calibrado no voo real (275 m)
OUT = Path(r"D:\1-Competicoes\OBAFOG\foguetes\bit07 robusto 2L\motores")

# cargas de vinagre (L) na garrafa 2 L retornável — o corpo é o mesmo do bit04/05
LOADS_L = [0.9, 1.1, 1.3, 1.45, 1.55, 1.7, 1.8]
# pressões manométricas realmente possíveis na bancada do Murilo (psi).
# 140 e 150 = o que ele mediu de verdade; 170 = o antigo "nominal"; 180 = bom dia.
PRESSURES_PSI = [130, 140, 150, 160, 170, 180, 190, 200]

_acid_nominal = mv.acid_mol   # guarda a função original antes de qualquer patch


def set_yield(eta: float) -> None:
    """Escala o CO2 disponível (rendimento da reação/vedação)."""
    mv.acid_mol = lambda v, _e=eta: _acid_nominal(v) * _e


def nominal_pressure_psi(v_L: float) -> float:
    set_yield(1.0)
    return mv.equilibrium_pressure(v_L * 1e-3) / 6894.76


def write_eng(result: mv.MotorResult, k: float, path: Path, v_L: float,
              p_psi: float, eta: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"; bit07 garrafa 2L | {v_L:.2f} L vinagre 4% | rendimento de CO2 eta={eta:.2f}",
        f"; P0={p_psi:.0f} psi man. (MEDIDA na bancada, nao nominal) | "
        f"pico={result.peak_thrust_N * k:.0f} N | impulso efetivo={result.total_impulse_Ns * k:.1f} Ns",
        f"; quimica kH_eff calibrada em 170 psi/1,55 L; fator de voo k={k} (275 m reais)",
        f"{result.name} 104 230 0 {result.propellant_kg:.4f} "
        f"{result.propellant_kg + 0.002:.4f} ORX-bit07",
    ]
    for tt, ff in mv.resample(result.curve):
        lines.append(f"   {max(tt, 1e-3):.4f} {max(ff * k, 0.0):.2f}")
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


def motor_name(v_L: float, p_psi: int) -> str:
    return f"Bit07-L{v_L:.2f}-P{p_psi:03d}".replace(".", "_")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    manifesto: dict[str, dict] = {}
    print(f"garrafa 2L (V={mv.V_BOTTLE * 1e3:.2f} L) | kH_eff={mv.KH_EFF:.4f} | k={K_FLIGHT}\n")
    print(f"{'carga':>6s} {'P nominal':>10s} | " +
          " ".join(f"{p:>5d}psi" for p in PRESSURES_PSI))
    print("-" * 78)

    for v_L in LOADS_L:
        p_nom = nominal_pressure_psi(v_L)
        linha = []
        for p_psi in PRESSURES_PSI:
            eta = p_psi / p_nom
            set_yield(eta)
            name = motor_name(v_L, p_psi)
            r = mv.simulate(v_L * 1e-3, name)
            write_eng(r, K_FLIGHT, OUT / f"{name}.eng", v_L, p_psi, eta)
            manifesto[name] = {
                "arquivo": str(OUT / f"{name}.eng"),
                "carga_L": v_L,
                "pressao_psi": p_psi,
                "eta_CO2": round(eta, 4),
                "impulso_Ns": round(r.total_impulse_Ns * K_FLIGHT, 2),
                "pico_N": round(r.peak_thrust_N * K_FLIGHT, 1),
                "queima_s": round(r.burn_time_s, 3),
                "propelente_kg": round(r.propellant_kg, 4),
            }
            linha.append(f"{r.total_impulse_Ns * K_FLIGHT:6.0f}Ns")
        print(f"{v_L:5.2f}L {p_nom:9.0f}p | " + " ".join(linha))

    set_yield(1.0)
    (OUT / "manifesto.json").write_text(
        json.dumps(manifesto, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\n{len(manifesto)} motores + manifesto.json em {OUT}")
    print("Leitura: cada LINHA e uma carga de vinagre; cada COLUNA e a pressao que a")
    print("bancada realmente entregou. O impulso cai junto com a pressao — e por isso")
    print("que 140 psi nao levantou um foguete projetado para 170.")


if __name__ == "__main__":
    main()
