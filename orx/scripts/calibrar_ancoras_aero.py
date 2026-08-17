"""Calibra as âncoras das notas aerodinâmicas amostrando o PRÓPRIO espaço de busca.

Sem isto o critério vira ruído: se a faixa for larga demais todo mundo tira nota
cheia; estreita demais, todo mundo tira zero. Aqui a faixa sai dos percentis
observados numa amostra aleatória do espaço definido no YAML.
"""
from __future__ import annotations

import dataclasses
import json
import random
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from orx.config import load_config
from orx.config.loader import BatchConfig
from orx.simulation.runner import Runner

CONFIG = r"C:\Users\muril\openrocket-optimizer\config\bit06_pet_aero.yaml"
SAIDA = Path(r"D:\1-Competicoes\OBAFOG\foguetes\bit06 1,8L\simulacoes\ancoras_aero.json")
N = 120

CAMPOS = ["cd_medio", "cd_atrito", "cd_pressao", "cd_base", "aoa_max", "aoa_medio",
          "amortecimento_pitch", "razao_finura", "fin_flutter_velocity",
          "horizontal_distance", "dry_mass", "stability_min", "launch_rod_velocity",
          "apogee", "max_velocity"]


def amostra(spec, rng: random.Random):
    if getattr(spec, "choices", None):
        return rng.choice(list(spec.choices))
    lo, hi = float(spec.low), float(spec.high)
    v = rng.uniform(lo, hi)
    return int(round(v)) if getattr(spec, "integer", False) else v


def main() -> None:
    n = int(sys.argv[sys.argv.index("-n") + 1]) if "-n" in sys.argv else N
    cfg = load_config(CONFIG)
    runner = Runner(dataclasses.replace(cfg, batch=BatchConfig(workers=1)))
    rng = random.Random(20260816)

    # Só a população VIÁVEL importa. Numa amostra aleatória a maioria dos
    # designs é instável (mediana de estabilidade ~0,4 cal) e seria descartada
    # pelas restrições; ancorar as notas nela descreveria foguetes que não
    # entram na disputa.
    colhido: dict[str, list[float]] = {c: [] for c in CAMPOS}
    viaveis = 0
    for i in range(1, n + 1):
        d = {p.name: amostra(p, rng) for p in cfg.parameters}
        r = runner.evaluate(d, sim_overrides={
            "random_seed": 42, "wind_speed_average": 2.0, "launch_rod_length": 1.0,
            "launch_rod_angle_deg": float(d["launch_angle"]),
        })
        if not r.ok:
            continue
        m = r.metrics
        if m.get("horizontal_distance") is None or m.get("cd_medio") is None:
            continue
        est = m.get("stability_min")
        if est is None or est < 1.08 or (m.get("stability_max") or 9) > 3.5:
            continue
        if (m.get("launch_rod_velocity") or 0) < 15 or (m.get("apogee") or 0) < 30:
            continue
        viaveis += 1
        for c in CAMPOS:
            v = m.get(c)
            if v is not None:
                colhido[c].append(float(v))
        if i % 50 == 0:
            print(f"  [{i}/{n}] {viaveis} viáveis", flush=True)

    print(f"\n{viaveis} amostras VIÁVEIS (passam nas restrições) de {n}\n")
    print(f"{'métrica':22s} {'p05':>10s} {'p25':>10s} {'mediana':>10s} "
          f"{'p75':>10s} {'p95':>10s}")
    print("-" * 78)
    resumo = {}
    for c in CAMPOS:
        v = np.array(colhido[c], dtype=float)
        if v.size < 5:
            continue
        q = {k: float(np.percentile(v, p))
             for k, p in (("p05", 5), ("p25", 25), ("p50", 50), ("p75", 75), ("p95", 95))}
        resumo[c] = q | {"n": int(v.size), "min": float(v.min()), "max": float(v.max())}
        print(f"{c:22s} {q['p05']:10.4f} {q['p25']:10.4f} {q['p50']:10.4f} "
              f"{q['p75']:10.4f} {q['p95']:10.4f}")

    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(json.dumps(resumo, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\n>> {SAIDA}")
    print("\nSugestão de âncoras (0 pt no p05 ruim, nota cheia no p95 bom):")
    for c, sentido in (("cd_medio", "menor"), ("aoa_max", "menor"),
                       ("amortecimento_pitch", "maior"), ("fin_flutter_velocity", "maior")):
        if c in resumo:
            r = resumo[c]
            if sentido == "menor":
                print(f"  {c:22s} 0 pt em {r['p95']:.4f} -> cheia em {r['p05']:.4f}")
            else:
                print(f"  {c:22s} 0 pt em {r['p05']:.4f} -> cheia em {r['p95']:.4f}")


if __name__ == "__main__":
    main()
