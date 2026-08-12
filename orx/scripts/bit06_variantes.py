"""bit06 — variantes de entrega + confronto com o modelo antigo.

Lição do bit07 que se repetiu aqui: a busca LIVRE escolhe o material mais leve
e a espessura mínima (leveza vale 20 pts), e devolve um foguete que ninguém
constrói. O campeão desta campanha veio com poliestireno 0,8 mm na ogiva e nas
aletas. Então entregamos três coisas, não uma:

  A) CAMPEÃO       — o que a busca achou (referência de teto)
  B) CONSTRUTÍVEL  — ogiva PLA 1,2 mm impressa + aletas de POLIETILENO 1,0 mm
                     (a chapa que o Murilo passou a usar no bit07_B), medidas
                     arredondadas para régua e trena
  C) MARGEM EXTRA  — mais lastro/aleta, troca alcance por estabilidade

E ainda: o MODELO ANTIGO medido com a MESMA régua (mesmos rendimentos, mesmos
ventos, mesma nota), que é o único jeito honesto de dizer se o reprojeto ganhou.
"""

from __future__ import annotations

import copy
import dataclasses
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from orx.config import load_config
from orx.config.loader import BatchConfig
from orx.simulation.runner import Runner

import bit06_robusto as B

PASTA = Path(r"D:\OBAFOG\bit06 1,8L")
ANTIGO = PASTA / "_MODELO_ANTIGO_falhou" / "bit06_MODELO_FINAL.ork"


def arredonda_construtivel(design: dict) -> dict:
    """Medidas de régua/trena + materiais que o Murilo realmente tem."""
    d = copy.deepcopy(design)
    d["nose_material"] = "pla"           # impressa em 3D
    d["nose_thickness"] = 1.2            # parede padrão das impressões dele
    d["fin_material"] = "polietileno"    # chapa de PE 1 mm (bit07_B)
    d["fin_thickness"] = 1.0
    # geometria em passos de 0,5 cm / 1 grau
    for k in ("nose_length", "fin_root", "fin_tip", "fin_sweep", "fin_height"):
        d[k] = round(float(d[k]) * 2) / 2
    d["ballast_fill"] = round(float(d["ballast_fill"]) * 2) / 2
    d["launch_angle"] = float(round(float(d["launch_angle"])))
    d["nose_shape_param"] = round(float(d["nose_shape_param"]), 2)
    d["fin_cant"] = 0.0                  # aleta reta: mais fácil de colar certo
    return d


def variante_margem(design: dict) -> dict:
    """Mais margem de estabilidade: lastro maior e aleta um pouco maior."""
    d = arredonda_construtivel(design)
    d["ballast_fill"] = round(min(26.0, float(d["ballast_fill"]) + 4.0) * 2) / 2
    d["fin_height"] = round(min(15.0, float(d["fin_height"]) + 1.0) * 2) / 2
    d["fin_root"] = round(min(14.0, float(d["fin_root"]) + 1.0) * 2) / 2
    return d


# ---------- avaliação do .ork ANTIGO com a régua nova ----------

def avalia_ork_antigo(caminho: Path, carga_L: float = 1.35) -> dict | None:
    """Roda o .ork antigo nos mesmos rendimentos/ventos e aplica a mesma nota.

    O modelo antigo não vive no espaço de parâmetros da busca (é um .ork
    pronto), então é avaliado direto pelo bridge: troca-se só o motor.
    """
    from orx.bridge.jvm import ensure_jvm
    from orx.bridge.orjava import OrBridge
    from orx.simulation.metrics import extract_metrics

    ensure_jvm()
    br = OrBridge()
    por_eta, psi_por_eta = {}, {}
    estab_min, estab_max, trilho_min = 9e9, 0.0, 9e9
    massa_seca, apogeus = 0.0, []
    carga = f"L{carga_L:.2f}".replace(".", "_")

    for eta in B.ETAS:
        nome = f"Bit06-{carga}-E{int(round(eta*100)):03d}"
        eng = B.MOTORES / f"{nome}.eng"
        if not eng.exists():
            print(f"  (sem motor {nome}, pulando)")
            return None
        psi_por_eta[eta] = B.MANIFESTO[nome]["pressao_psi"]
        alcances = []
        for seed in B.SEEDS_VENTO:
            doc = br.load_document(str(caminho))
            sim = br.get_simulation(doc, None)
            try:
                br.set_motor(doc, sim, "Garrafa reduzida - cilindro", f"file:{eng}")
            except KeyError:
                br.set_motor(doc, sim, "*cilindro*", f"file:{eng}")
            br.apply_sim_overrides(sim, {
                "random_seed": seed, "time_step": B.PASSO_FINO,
                "wind_speed_average": 2.0, "launch_rod_length": 1.0,
                "launch_rod_angle_deg": 54.0,
            })
            br.run_simulation(sim)
            m = extract_metrics(sim, doc)
            if m.horizontal_distance is None or m.stability_min is None:
                print("  (métrica ausente no modelo antigo)")
                return None
            alcances.append(m.horizontal_distance)
            estab_min = min(estab_min, m.stability_min)
            estab_max = max(estab_max, m.stability_max or 0)
            trilho_min = min(trilho_min, m.launch_rod_velocity or 0)
            apogeus.append(m.apogee or 0)
            massa_seca = max(massa_seca, m.dry_mass or 0)
        por_eta[eta] = float(np.mean(alcances))

    d_med = float(np.mean(list(por_eta.values())))
    d_pior = float(min(por_eta.values()))
    razao = d_pior / d_med if d_med > 0 else 0.0
    partes = {
        "alcance": B.nota_linear(d_med, B.ALCANCE_ZERO, B.ALCANCE_CHEIO, B.PESO_ALCANCE),
        "consistencia": B.nota_linear(razao, B.RAZAO_ZERO, B.RAZAO_CHEIA, B.PESO_CONSISTENCIA),
        "leveza": B.nota_linear(massa_seca, B.MASSA_ZERO, B.MASSA_CHEIA, B.PESO_LEVEZA),
        "estabilidade": B.nota_linear(estab_min, B.ESTAB_ZERO, B.ESTAB_CHEIA, B.PESO_ESTABILIDADE),
        "saida_trilho": B.nota_linear(trilho_min, B.TRILHO_ZERO, B.TRILHO_CHEIO, B.PESO_SAIDA_TRILHO),
    }
    reprova = []
    if estab_min < B.ESTAB_MIN:
        reprova.append(f"estabilidade mínima {estab_min:.2f} cal < {B.ESTAB_MIN}")
    if trilho_min < B.TRILHO_MIN:
        reprova.append(f"saída do trilho {trilho_min:.1f} m/s < {B.TRILHO_MIN}")
    return {
        "nota": sum(partes.values()), "partes": partes,
        "alcance_medio": d_med, "alcance_pior": d_pior,
        "alcance_por_eta": por_eta, "psi_por_eta": psi_por_eta,
        "massa_seca": massa_seca, "estab_min": estab_min, "estab_max": estab_max,
        "trilho_min": trilho_min, "apogeu_medio": float(np.mean(apogeus)),
        "reprova": reprova,
    }


def main() -> None:
    cfg = load_config(B.CONFIG)
    runner = Runner(dataclasses.replace(cfg, batch=BatchConfig(workers=1)))
    rank = json.loads((PASTA / "simulacoes" / "rank_bit06.json").read_text(encoding="utf-8"))
    campeao = rank[0]["design"]

    variantes = [
        ("A_CAMPEAO", "Campeão da busca (referência de teto)", campeao),
        ("B_CONSTRUTIVEL", "PLA 1,2 mm + polietileno 1,0 mm, medidas de régua",
         arredonda_construtivel(campeao)),
        ("C_MARGEM_EXTRA", "Construtível com mais lastro e aleta maior",
         variante_margem(campeao)),
    ]

    print(f"{'variante':18s} {'nota':>6s} {'médio':>7s} {'pior':>6s} {'seca':>7s} "
          f"{'estab':>7s} {'trilho':>7s}")
    print("-" * 68)
    resultados = []
    for tag, desc, d in variantes:
        a = B.avalia_completo(runner, d)
        if a.motivo_descarte:
            print(f"{tag:18s} REPROVADO: {a.motivo_descarte}")
            resultados.append((tag, desc, d, a, None))
            continue
        ork = PASTA / f"bit06_{tag}.ork"
        runner.save_design(d, str(ork))
        print(f"{tag:18s} {a.nota:6.1f} {a.alcance_medio:6.0f}m {a.alcance_pior:5.0f}m "
              f"{a.massa_seca*1000:6.0f}g {a.estab_min:6.2f} {a.trilho_min:6.1f}")
        resultados.append((tag, desc, d, a, str(ork)))

    print("\n== modelo ANTIGO sob a mesma régua ==")
    antigo = avalia_ork_antigo(ANTIGO) if ANTIGO.exists() else None
    if antigo:
        print(f"{'ANTIGO':18s} {antigo['nota']:6.1f} {antigo['alcance_medio']:6.0f}m "
              f"{antigo['alcance_pior']:5.0f}m {antigo['massa_seca']*1000:6.0f}g "
              f"{antigo['estab_min']:6.2f} {antigo['trilho_min']:6.1f}")
        if antigo["reprova"]:
            print("   REPROVA nas restrições duras: " + "; ".join(antigo["reprova"]))
    else:
        print("   (não foi possível avaliar o .ork antigo)")

    saida = {
        "gerado": time.strftime("%Y-%m-%d %H:%M"),
        "variantes": [
            {"tag": t, "descricao": desc, "design": d,
             "avaliacao": (dataclasses.asdict(a) if a and not a.motivo_descarte else None),
             "descarte": (a.motivo_descarte if a else None), "ork": ork}
            for (t, desc, d, a, ork) in resultados
        ],
        "modelo_antigo": antigo,
    }
    (PASTA / "simulacoes" / "variantes_bit06.json").write_text(
        json.dumps(saida, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"\n>> {PASTA / 'simulacoes' / 'variantes_bit06.json'}")


if __name__ == "__main__":
    main()
