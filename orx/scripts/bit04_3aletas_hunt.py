"""Caça por um design de 3 aletas SEM cant que supere 380 m.

Roda buscas adaptativas em blocos e PARA assim que o melhor (validado no passo
ultrafino 0.005) superar o alvo. Se estagnar após o orçamento máximo, para e
reporta o teto real — sem rodar para sempre.
"""

import dataclasses
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from orx.config import load_config
from orx.config.loader import BatchConfig, OptimizerConfig
from orx.objectives.objective import Constraints
from orx.optimizer.engine import run_optimization
from orx.results.db import ResultsDB
from orx.simulation.runner import Runner
from orx.utils.logging import setup_logging

CONFIG = r"C:\Users\muril\openrocket-optimizer\config\bit04_aletas.yaml"
ALVO = 380.0
BLOCO = 12_000          # avaliações por bloco
MAX_BLOCOS = 5          # teto: 60 mil avaliações
SEEDS_ROBUSTEZ = list(range(101, 121))


def progresso(tag):
    def p(i, total, valor, melhor):
        if i % max(1, total // 60) == 0:
            m = f"{melhor:.1f}" if melhor and melhor > -1e8 else "n/a"
            print(f"[{tag} {i}/{total}] melhor={m}", flush=True)
    return p


def valida_finos(runner, cons, params_list, ts=0.005):
    """Média em 20 ventos no passo ultrafino."""
    out = []
    for p in params_list:
        ds = []
        for s in SEEDS_ROBUSTEZ:
            r = runner.evaluate(p, sim_overrides={"random_seed": s, "time_step": ts})
            if r.ok and r.metrics.get("horizontal_distance") is not None \
                    and not cons.violations(r.metrics):
                ds.append(r.metrics["horizontal_distance"])
        a = np.array(ds)
        out.append((float(a.mean()) if a.size else -1, p))
    return sorted(out, key=lambda t: -t[0])


def main() -> None:
    setup_logging()
    cfg = load_config(CONFIG)
    cfg = dataclasses.replace(cfg, batch=BatchConfig(workers=3))
    runner = Runner(cfg)
    cons = Constraints(cfg.constraints)
    pn = [p.name for p in cfg.parameters]
    t0 = time.time()
    melhor_global = -1
    melhor_params = None

    for bloco in range(1, MAX_BLOCOS + 1):
        print(f"\n===== BLOCO {bloco}/{MAX_BLOCOS} ({BLOCO} avaliações) =====", flush=True)
        cfg_b = dataclasses.replace(cfg, optimizer=OptimizerConfig(
            algorithm="adaptive", max_evaluations=BLOCO, seed=10 + bloco,
            profile="balanced", options={"chunk_size": 2500}))
        run_id = run_optimization(cfg_b, run_name=f"3aletas-b{bloco}",
                                  progress=progresso(f"b{bloco}"))

        db = ResultsDB(cfg.db_path)
        df = db.evaluations_df(run_id)
        db.close()
        ok = df[(df["feasible"] == 1) & df["score"].notna()].sort_values("score", ascending=False)
        if ok.empty:
            print("  bloco sem viáveis", flush=True)
            continue
        tops = []
        for _, row in ok.head(8).iterrows():
            tops.append({n: (float(row[f"p_{n}"]) if not isinstance(row[f"p_{n}"], str)
                             else row[f"p_{n}"]) for n in pn})
        validados = valida_finos(runner, cons, tops)
        alcance, params = validados[0]
        print(f"  melhor do bloco (ultrafino, 20 ventos): {alcance:.1f} m", flush=True)
        if alcance > melhor_global:
            melhor_global, melhor_params = alcance, params

        if melhor_global > ALVO:
            print(f"\n>>> ALVO SUPERADO: {melhor_global:.1f} m > {ALVO} m", flush=True)
            break
        print(f"  (teto ate agora: {melhor_global:.1f} m; alvo {ALVO} m)", flush=True)

    # resultado final
    if melhor_params is not None:
        out = r"D:\OBAFOG\bit04 2L script\foguete_real\bit04_3aletas_SEMCANT.ork"
        runner.save_design(melhor_params, out)
        m = runner.evaluate(melhor_params, sim_overrides={"random_seed": 42, "time_step": 0.005}).metrics
        print("\n" + "=" * 60)
        if melhor_global > ALVO:
            print(f"SUCESSO: 3 aletas sem cant = {melhor_global:.1f} m (superou {ALVO})")
        else:
            print(f"TETO ATINGIDO: melhor 3 aletas sem cant = {melhor_global:.1f} m")
            print(f"NAO alcancou {ALVO} m em {MAX_BLOCOS*BLOCO} avaliacoes.")
        for k, v in melhor_params.items():
            print(f"  {k} = {v:.4g}" if isinstance(v, float) else f"  {k} = {v}")
        print(f"  >> estab_pos_queima={m['stability_max']:.2f} cal | lastro={m['ballast_mass']*1000:.0f}g")
        print(f"  >> salvo: {out}")
    print(f"\ntempo total: {(time.time()-t0)/3600:.2f} h", flush=True)


if __name__ == "__main__":
    main()
