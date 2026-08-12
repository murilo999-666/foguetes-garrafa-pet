"""Modelo por conhecimento humano (pesquisa + física), no mesmo corpo/motor
que o campeão dos 100 mil testes, gravado no MESMO banco para virar um teste
comparável (com run_id e test id próprios).

Design fixo por princípio (ver MODELO_HUMANO_pesquisa.md). A ÚNICA quantidade
ajustada numericamente é o lastro — e mesmo assim pelo CRITÉRIO DE ESTABILIDADE
clássico (1,5–1,7 cal pós-queima), não por otimização de alcance.
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from orx.config import load_config
from orx.objectives.objective import Constraints, Objective
from orx.results.db import ResultsDB
from orx.simulation.runner import Runner
from orx.utils.logging import setup_logging

CONFIG = r"C:\Users\muril\openrocket-optimizer\config\foguete_real.yaml"
MOTOR = r"file:D:\OBAFOG\foguete_real\motores\VinagreReal-1_55L.eng"
ROBUST_SEEDS = list(range(101, 121))
LASTRO_REAL_G = 113.0  # lastro de nariz que a equipe usa na prática (bit03 real)

# Design por conhecimento humano (tudo fixo por princípio; ballast_fill ajustado
# para reproduzir a massa de lastro REAL da equipe, ~113 g — não otimizado).
BASE_DESIGN = {
    "nose_length": 22.0,        # ogiva alongada (~2 cal): concentra lastro na ponta
    "nose_shape": "OGIVE",      # OBAFOG recomenda ogiva; arrasto subsônico ~igual
    "nose_shape_param": 1.0,
    "nose_thickness": 1.2,      # parede imprimível
    "nose_material": "pla",     # impressão 3D padrão
    "fin_count": 3,             # -25% arrasto de interferência (Apogee 442)
    "fin_root": 14.0,           # aletas GRANDES: estabilidade vem daqui (leve),
    "fin_tip": 3.0,             #   não de quilos de lastro (Nakka/Apogee)
    "fin_sweep": 9.0,           # enflechamento p/ estabilidade + baixo form drag
    "fin_height": 11.0,         # span generoso p/ empurrar o CP p/ trás
    "fin_thickness": 1.0,       # poliestireno robusto (não fio de navalha)
    "fin_material": "poliestireno",
    "fin_cant": 0.0,            # sem cant: simplicidade construtiva
    "fin_position": -0.5,
    "motor": MOTOR,
    "launch_angle": 46.0,       # ótimo teórico com arrasto (~46-47°)
    "ballast_fill": 5.0,        # provisório; ajustado p/ ~113 g reais abaixo
}


def main() -> None:
    setup_logging()
    cfg = load_config(CONFIG)
    runner = Runner(cfg)
    obj = Objective(cfg.objective)
    cons = Constraints(cfg.constraints)

    # --- ajusta ballast_fill para a massa de lastro REAL da equipe (~113 g) ---
    print(f"Ajustando lastro para ~{LASTRO_REAL_G:.0f} g (prática real da equipe):")
    lo, hi = 0.0, 8.0
    design = dict(BASE_DESIGN)
    stab = None
    for _ in range(18):
        mid = (lo + hi) / 2
        design["ballast_fill"] = mid
        res = runner.evaluate(design, sim_overrides={"random_seed": 42})
        dur = res.metrics.get("ballast_mass", 0) * 1000 if res.ok else 0
        stab = res.metrics.get("stability_max") if res.ok else None
        if abs(dur - LASTRO_REAL_G) < 2:
            break
        if dur < LASTRO_REAL_G:
            lo = mid
        else:
            hi = mid
    print(f"  fill={design['ballast_fill']:.2f}cm -> durepox={dur:.0f}g | "
          f"estabilidade pós-queima resultante={stab if stab is None else round(stab,2)} cal")
    print(f"  (estabilidade vem das aletas grandes; alvo minimo 1,0 cal = voavel)")

    # --- validação de robustez em 20 ventos ---
    print("\nValidação de robustez (20 ventos):")
    dists, met = [], None
    for seed in ROBUST_SEEDS:
        res = runner.evaluate(design, sim_overrides={"random_seed": seed})
        if res.ok and res.metrics.get("horizontal_distance") is not None:
            viol = cons.violations(res.metrics)
            if not viol:
                dists.append(res.metrics["horizontal_distance"])
            if seed == 42 or met is None:
                met = res.metrics
    arr = np.array(dists)
    if arr.size:
        print(f"  alcance médio={arr.mean():.1f} m (±{arr.std():.1f}) | pior={arr.min():.1f} m | válidos={len(arr)}/20")
    else:
        print("  nenhum voo viável — revisar estabilidade")

    # --- grava no MESMO banco como run próprio (test id comparável) ---
    db = ResultsDB(cfg.db_path)
    run_id = db.create_run(
        name="MODELO-HUMANO-pesquisa",
        algorithm="conhecimento_humano",
        objective=cfg.objective.metric,
        direction=cfg.objective.direction,
        base_ork=cfg.base_ork,
        config={"fonte": "pesquisa+fisica, sem otimizador", "ver": "MODELO_HUMANO_pesquisa.md"},
    )
    final = runner.evaluate(design, sim_overrides={"random_seed": 42})
    score = obj.value(final.metrics)
    viol = cons.violations(final.metrics)
    eval_id = db.add_evaluation(
        run_id, 1, design, final.metrics, score,
        feasible=not viol, violations=viol, duration_s=final.duration_s,
    )
    db.finish_run(run_id, "done",
                  f"modelo humano: {score:.1f} m seed42, {arr.mean():.1f} m média 20 ventos")
    print(f"\n>>> gravado no banco: run_id={run_id}, evaluation_id={eval_id}")

    # --- salva o .ork ---
    out = r"D:\OBAFOG\foguete_real\foguete_MODELO_HUMANO.ork"
    runner.save_design(design, out)
    print(f">>> .ork salvo: {out}")

    m = final.metrics
    print("\n=== MODELO HUMANO (final) ===")
    for k in ("horizontal_distance", "apogee", "max_velocity", "stability_static",
              "stability_max", "ballast_mass", "liftoff_mass", "flight_time"):
        v = m.get(k)
        print(f"  {k}: {v:.3f}" if v is not None else f"  {k}: n/a")
    print(f"  ballast_fill final: {design['ballast_fill']:.2f} cm")
    db.close()


if __name__ == "__main__":
    main()
