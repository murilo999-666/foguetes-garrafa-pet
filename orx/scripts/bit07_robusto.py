"""bit07 — projeto de foguete ROBUSTO A PRESSÃO, com nota multicritério.

Contexto (2026-08-04)
--------------------
bit04 e bit05 foram lançados de verdade. A bancada só chegou a 140–150 psi
(projeto assumia 170), os dois saíram rasos e bateram numa cerca à frente.
Otimizar "alcance numa pressão só" acabou aqui.

O que este script faz
---------------------
ETAPA 1 (ampla, paralela): busca adaptativa sobre config/bit07_robusto.yaml,
simulando no PIOR cenário realista (140 psi) e já com as restrições duras que
faltavam no bit04/bit05 (estabilidade nunca < 1 calibre, saída de trilho
>= 15 m/s, raiz de aleta colável). A etapa 1 otimiza a MESMA nota da etapa 2
(menos o termo de consistência, que exige várias pressões) — a primeira tentativa
usou "alcance − peso" como atalho e devolveu 40 finalistas colados em 1,00 cal,
repetindo o vício do bit04; ver `versoes_teste/RELATORIO_bit07_v1.md`.

ETAPA 2 (fina, multicritério): os finalistas são re-simulados em TODAS as
pressões da bancada (130→200 psi) × 3 ventos, e recebem uma NOTA de 0 a 100:

    ALCANCE ROBUSTO ......... 40 pts   média do alcance nas 8 pressões
    CONSISTÊNCIA ............ 25 pts   pior pressão / média (não pode desabar)
    LEVEZA .................. 20 pts   massa seca (estrutura + lastro, sem vinagre)
    MARGEM DE SEGURANÇA ..... 15 pts   estabilidade (10) + saída do trilho (5)
                              -----
                              100 pts

Por que esses pesos
-------------------
- Alcance continua sendo o que a OBAFOG pontua, então é a maior fatia — mas
  sozinho ele é justamente o que produziu dois foguetes que não voaram.
- Consistência vale quase tanto quanto alcance porque o problema REAL do
  Murilo é a bancada variar: um projeto de 380 m que só anda a 180 psi vale
  menos que um de 330 m que anda igual a 130 e a 180 psi.
- Leveza tem peso próprio (20) porque o otimizador antigo, livre, sempre
  escolhia o caminho "pesado + coeficiente balístico alto" — que funciona no
  papel e some quando falta empuxo. Peso não é só massa: é o que transforma
  falta de pressão em voo rasante.
- Margem de segurança é o menor peso mas tem restrição DURA junto: quem não
  passar de 1 calibre em todo o voo nem entra na lista.

Uso:
    .venv\\Scripts\\python scripts\\bit07_robusto.py            # etapa 1 + 2
    .venv\\Scripts\\python scripts\\bit07_robusto.py --so-etapa2  # só re-pontua o banco
"""

from __future__ import annotations

import dataclasses
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from orx.config import load_config
from orx.config.loader import BatchConfig, OptimizerConfig
from orx.results.db import ResultsDB
from orx.simulation.runner import Runner
from orx.utils.logging import setup_logging

CONFIG = r"C:\Users\muril\openrocket-optimizer\config\bit07_robusto.yaml"
PASTA = Path(r"D:\OBAFOG\bit07 robusto 2L")
MOTORES = PASTA / "motores"
MANIFESTO = json.loads((MOTORES / "manifesto.json").read_text(encoding="utf-8"))

# ---------------- cenários ----------------
# Faixa COMPLETA da bancada: do pior dia real (130) ao melhor caso (200 psi).
# 140-150 é o que ele mediu nos lançamentos que falharam; 170 era o "nominal"
# antigo; 190-200 é o teto se a reação render tudo. O projeto tem de ir bem
# nas oito — é isso que "robusto a pressão" significa.
PRESSOES = [130, 140, 150, 160, 170, 180, 190, 200]
SEEDS_VENTO = [42, 101, 202]                # 3 realizações de vento (2 m/s médio)
PASSO_FINO = 0.005                          # time step da simulação de validação

# ---------------- etapa 1 ----------------
BLOCOS = 3
AVALIACOES_POR_BLOCO = 6000
FINALISTAS = 40

# ---------------- pesos da nota (somam 100) ----------------
PESO_ALCANCE = 40.0
PESO_CONSISTENCIA = 25.0
PESO_LEVEZA = 20.0
PESO_ESTABILIDADE = 10.0
PESO_SAIDA_TRILHO = 5.0

# âncoras de normalização (0 pt -> nota cheia)
ALCANCE_ZERO, ALCANCE_CHEIO = 150.0, 400.0        # m (média nas 8 pressões)
RAZAO_ZERO, RAZAO_CHEIA = 0.70, 0.95              # pior/média
MASSA_ZERO, MASSA_CHEIA = 0.700, 0.250            # kg de massa seca
ESTAB_ZERO, ESTAB_CHEIA = 1.0, 2.0                # calibres (mínimo do voo)
TRILHO_ZERO, TRILHO_CHEIO = 15.0, 25.0            # m/s na saída do tubo-guia

# ---------------- restrições duras (valem em TODOS os cenários) ----------------
ESTAB_MIN = 1.0
ESTAB_MAX = 3.5
TRILHO_MIN = 15.0
APOGEU_MIN = 40.0


def nota_linear(valor: float, zero: float, cheio: float, peso: float) -> float:
    if cheio == zero:
        return 0.0
    t = (valor - zero) / (cheio - zero)
    return peso * float(np.clip(t, 0.0, 1.0))


def troca_pressao(motor_file: str, psi: int) -> str:
    """Mesmo motor (mesma carga de vinagre), outra pressão atingida."""
    nome = Path(motor_file[5:]).stem            # Bit07-L1_55-P140
    carga = nome.split("-P")[0]
    return f"file:{MOTORES / f'{carga}-P{psi:03d}.eng'}"


def propelente_kg(motor_file: str) -> float:
    nome = Path(motor_file[5:]).stem
    return float(MANIFESTO[nome]["propelente_kg"])


# ============================== ETAPA 2 ==============================

@dataclasses.dataclass
class Avaliacao:
    design: dict
    nota: float
    alcance_medio: float
    alcance_pior: float
    alcance_por_psi: dict[int, float]
    massa_seca: float
    estab_min: float
    estab_max: float
    trilho_min: float
    apogeu_medio: float
    partes: dict[str, float]
    motivo_descarte: str | None = None


def avalia_completo(runner: Runner, design: dict) -> Avaliacao:
    """Simula o design em todas as pressões × ventos e devolve a nota 0–100."""
    por_psi: dict[int, float] = {}
    estab_min = 9e9
    estab_max = 0.0
    trilho_min = 9e9
    apogeus: list[float] = []
    massa_seca = 0.0
    descarte: str | None = None

    for psi in PRESSOES:
        d = dict(design)
        d["motor"] = troca_pressao(design["motor"], psi)
        alcances = []
        for seed in SEEDS_VENTO:
            r = runner.evaluate(d, sim_overrides={
                "random_seed": seed, "time_step": PASSO_FINO,
                "wind_speed_average": 2.0, "launch_rod_length": 1.0,
                "launch_rod_angle_deg": float(design["launch_angle"]),
            })
            if not r.ok:
                return Avaliacao(design, -1, 0, 0, {}, 0, 0, 0, 0, 0, {},
                                 motivo_descarte=f"sim falhou em {psi} psi: {r.error}")
            m = r.metrics
            faltando = [k for k in ("horizontal_distance", "stability_min",
                                    "stability_max", "launch_rod_velocity", "apogee",
                                    "dry_mass")
                        if m.get(k) is None]
            if faltando:
                return Avaliacao(design, -1, 0, 0, {}, 0, 0, 0, 0, 0, {},
                                 motivo_descarte=f"métrica ausente em {psi} psi: {faltando}")
            alcances.append(m["horizontal_distance"])
            estab_min = min(estab_min, m["stability_min"])
            estab_max = max(estab_max, m["stability_max"])
            trilho_min = min(trilho_min, m["launch_rod_velocity"])
            apogeus.append(m["apogee"])
            massa_seca = max(massa_seca, m["dry_mass"])
            if m["stability_min"] < ESTAB_MIN:
                descarte = f"estabilidade {m['stability_min']:.2f} cal < {ESTAB_MIN} em {psi} psi"
            elif m["stability_max"] > ESTAB_MAX:
                descarte = f"estabilidade {m['stability_max']:.2f} cal > {ESTAB_MAX} em {psi} psi"
            elif m["launch_rod_velocity"] < TRILHO_MIN:
                descarte = f"saída do trilho {m['launch_rod_velocity']:.1f} m/s em {psi} psi"
            elif m["apogee"] < APOGEU_MIN:
                descarte = f"apogeu {m['apogee']:.0f} m em {psi} psi"
        por_psi[psi] = float(np.mean(alcances))

    d_med = float(np.mean(list(por_psi.values())))
    d_pior = float(min(por_psi.values()))
    razao = d_pior / d_med if d_med > 0 else 0.0

    partes = {
        "alcance": nota_linear(d_med, ALCANCE_ZERO, ALCANCE_CHEIO, PESO_ALCANCE),
        "consistencia": nota_linear(razao, RAZAO_ZERO, RAZAO_CHEIA, PESO_CONSISTENCIA),
        "leveza": nota_linear(massa_seca, MASSA_ZERO, MASSA_CHEIA, PESO_LEVEZA),
        "estabilidade": nota_linear(estab_min, ESTAB_ZERO, ESTAB_CHEIA, PESO_ESTABILIDADE),
        "saida_trilho": nota_linear(trilho_min, TRILHO_ZERO, TRILHO_CHEIO, PESO_SAIDA_TRILHO),
    }
    nota = sum(partes.values()) if descarte is None else -1.0
    return Avaliacao(design, nota, d_med, d_pior, por_psi, massa_seca,
                     estab_min, estab_max, trilho_min, float(np.mean(apogeus)),
                     partes, descarte)


# ============================== ETAPA 1 ==============================

def progresso(tag: str):
    def p(i, total, valor, melhor):
        if i % max(1, total // 40) == 0:
            m = f"{melhor:.1f}" if melhor and melhor > -1e8 else "n/a"
            print(f"  [{tag} {i}/{total}] melhor={m}", flush=True)
    return p


def etapa1(cfg) -> None:
    from orx.optimizer.engine import run_optimization
    for bloco in range(1, BLOCOS + 1):
        print(f"\n===== ETAPA 1 — bloco {bloco}/{BLOCOS} "
              f"({AVALIACOES_POR_BLOCO} simulações a 140 psi) =====", flush=True)
        cfg_b = dataclasses.replace(cfg, optimizer=OptimizerConfig(
            algorithm="adaptive", max_evaluations=AVALIACOES_POR_BLOCO,
            seed=100 + bloco, profile="balanced", options={"chunk_size": 1500}))
        run_optimization(cfg_b, run_name=f"bit07-robusto-b{bloco}",
                         progress=progresso(f"b{bloco}"))


def finalistas_do_banco(cfg, quantos: int) -> list[dict]:
    db = ResultsDB(cfg.db_path)
    df = db.evaluations_df()
    db.close()
    nomes = [p.name for p in cfg.parameters]
    inteiros = {p.name for p in cfg.parameters if getattr(p, "integer", False)}
    ok = df[(df["feasible"] == 1) & df["score"].notna()].sort_values("score", ascending=False)
    designs: list[dict] = []
    vistos: set[tuple] = set()
    for _, row in ok.iterrows():
        d = {}
        for n in nomes:
            v = row[f"p_{n}"]
            if isinstance(v, str):
                d[n] = v
            elif n in inteiros:
                d[n] = int(round(float(v)))
            else:
                d[n] = float(v)
        # deduplica designs quase iguais: arredondar para o inteiro (cm, mm, grau)
        # colapsa a nuvem de vizinhos que o adaptativo produz em torno de um ótimo,
        # e a lista de finalistas vira variedade de verdade em vez de 40 clones.
        chave = tuple(round(v) if isinstance(v, float) else v for v in d.values())
        if chave in vistos:
            continue
        vistos.add(chave)
        designs.append(d)
        if len(designs) >= quantos:
            break
    return designs


# ============================== relatório ==============================

def relatorio(rank: list[Avaliacao], cfg, runner: Runner) -> None:
    PASTA.mkdir(parents=True, exist_ok=True)
    linhas: list[str] = []
    add = linhas.append
    add("# bit07 — campeões por NOTA multicritério (0–100)\n")
    add(f"Gerado em {time.strftime('%Y-%m-%d %H:%M')} | "
        f"{len(rank)} finalistas re-simulados em {len(PRESSOES)} pressões "
        f"({PRESSOES[0]}–{PRESSOES[-1]} psi) x {len(SEEDS_VENTO)} ventos.\n")
    add("## Como a nota é montada\n")
    add(f"| critério | peso | 0 ponto em | nota cheia em |")
    add("|---|---|---|---|")
    add(f"| Alcance robusto (média das pressões) | {PESO_ALCANCE:.0f} | "
        f"{ALCANCE_ZERO:.0f} m | {ALCANCE_CHEIO:.0f} m |")
    add(f"| Consistência (pior pressão / média) | {PESO_CONSISTENCIA:.0f} | "
        f"{RAZAO_ZERO:.2f} | {RAZAO_CHEIA:.2f} |")
    add(f"| Leveza (massa seca) | {PESO_LEVEZA:.0f} | {MASSA_ZERO*1000:.0f} g | "
        f"{MASSA_CHEIA*1000:.0f} g |")
    add(f"| Estabilidade mínima do voo | {PESO_ESTABILIDADE:.0f} | "
        f"{ESTAB_ZERO:.1f} cal | {ESTAB_CHEIA:.1f} cal |")
    add(f"| Saída do tubo-guia | {PESO_SAIDA_TRILHO:.0f} | {TRILHO_ZERO:.0f} m/s | "
        f"{TRILHO_CHEIO:.0f} m/s |")
    add("\nRestrições duras (reprovam o design): estabilidade sempre entre "
        f"{ESTAB_MIN} e {ESTAB_MAX} cal, saída do trilho >= {TRILHO_MIN} m/s, "
        f"apogeu >= {APOGEU_MIN:.0f} m — em TODAS as pressões.\n")

    add("## Ranking\n")
    cab = "| # | nota | alcance médio | pior pressão | massa seca | estab mín | trilho | " + \
          " | ".join(f"{p} psi" for p in PRESSOES) + " |"
    add(cab)
    add("|" + "---|" * (7 + len(PRESSOES)))
    for i, a in enumerate(rank[:15], 1):
        add(f"| {i} | **{a.nota:.1f}** | {a.alcance_medio:.0f} m | {a.alcance_pior:.0f} m | "
            f"{a.massa_seca*1000:.0f} g | {a.estab_min:.2f} cal | {a.trilho_min:.1f} m/s | "
            + " | ".join(f"{a.alcance_por_psi[p]:.0f}" for p in PRESSOES) + " |")

    campeao = rank[0]
    add("\n## Campeão — parâmetros de construção\n")
    add("| parâmetro | valor |")
    add("|---|---|")
    for k, v in campeao.design.items():
        if k == "motor":
            v = Path(str(v)[5:]).stem
        add(f"| {k} | {v if not isinstance(v, float) else f'{v:.3f}'} |")
    add("\n### Nota do campeão, critério por critério\n")
    add("| critério | pontos | de |")
    add("|---|---|---|")
    for nome, peso in (("alcance", PESO_ALCANCE), ("consistencia", PESO_CONSISTENCIA),
                       ("leveza", PESO_LEVEZA), ("estabilidade", PESO_ESTABILIDADE),
                       ("saida_trilho", PESO_SAIDA_TRILHO)):
        add(f"| {nome} | {campeao.partes[nome]:.1f} | {peso:.0f} |")
    add(f"| **TOTAL** | **{campeao.nota:.1f}** | **100** |")

    (PASTA / "RELATORIO_bit07.md").write_text("\n".join(linhas) + "\n", encoding="utf-8")

    # CSV com o ranking inteiro
    import csv
    with (PASTA / "ranking_bit07.csv").open("w", newline="", encoding="utf-8") as fh:
        campos = ["nota", "alcance_medio", "alcance_pior", "massa_seca_g", "estab_min",
                  "estab_max", "trilho_min"] + [f"alcance_{p}psi" for p in PRESSOES] + \
                 list(rank[0].design.keys())
        w = csv.DictWriter(fh, fieldnames=campos)
        w.writeheader()
        for a in rank:
            linha = {"nota": round(a.nota, 2), "alcance_medio": round(a.alcance_medio, 1),
                     "alcance_pior": round(a.alcance_pior, 1),
                     "massa_seca_g": round(a.massa_seca * 1000, 1),
                     "estab_min": round(a.estab_min, 3), "estab_max": round(a.estab_max, 3),
                     "trilho_min": round(a.trilho_min, 2)}
            linha.update({f"alcance_{p}psi": round(a.alcance_por_psi[p], 1) for p in PRESSOES})
            linha.update(a.design)
            w.writerow(linha)

    ork = PASTA / "bit07_MODELO_FINAL.ork"
    runner.save_design(campeao.design, str(ork))
    print(f"\n>> campeão salvo em {ork}")
    print(f">> relatório: {PASTA / 'RELATORIO_bit07.md'}")
    print(f">> ranking:   {PASTA / 'ranking_bit07.csv'}")


def main() -> None:
    setup_logging()
    t0 = time.time()
    cfg = load_config(CONFIG)
    so_etapa2 = "--so-etapa2" in sys.argv

    if not so_etapa2:
        etapa1(cfg)

    print(f"\n===== ETAPA 2 — nota multicritério dos {FINALISTAS} finalistas =====",
          flush=True)
    designs = finalistas_do_banco(cfg, FINALISTAS)
    if not designs:
        raise SystemExit("nenhum design viável no banco — rode a etapa 1 primeiro")

    cfg_serial = dataclasses.replace(cfg, batch=BatchConfig(workers=1))
    runner = Runner(cfg_serial)
    rank: list[Avaliacao] = []
    for i, d in enumerate(designs, 1):
        a = avalia_completo(runner, d)
        if a.motivo_descarte:
            print(f"  [{i}/{len(designs)}] descartado: {a.motivo_descarte}", flush=True)
            continue
        rank.append(a)
        print(f"  [{i}/{len(designs)}] nota {a.nota:5.1f} | médio {a.alcance_medio:5.0f} m | "
              f"pior {a.alcance_pior:5.0f} m | seca {a.massa_seca*1000:4.0f} g | "
              f"estab {a.estab_min:.2f} cal", flush=True)

    if not rank:
        raise SystemExit("nenhum finalista sobreviveu à validação multipressão")
    rank.sort(key=lambda a: -a.nota)
    relatorio(rank, cfg, runner)
    print(f"\ntempo total: {(time.time() - t0) / 60:.1f} min")


if __name__ == "__main__":
    main()
