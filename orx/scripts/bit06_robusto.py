"""bit06 — reprojeto da garrafa REDUZIDA (~1,8 L) pelo método do bit07.

Contexto
--------
O bit06 antigo (arquivado em `_MODELO_ANTIGO_falhou/`) foi otimizado por ALCANCE
PURO: 376 m no papel com estabilidade ~1,03 cal. É a mesma assinatura de bit04 e
bit05, que foram lançados de verdade, saíram rasos e bateram numa cerca.
E as pressões que ele assumia (1,35 L -> "170 psi"; 1,5 L -> "189 psi") são
exatamente as pressões NOMINAIS dessas cargas — isto é, o projeto contava com
rendimento PERFEITO da reação. A bancada real entregou eta ~0,82-0,88.

O que este script faz
---------------------
ETAPA 1 (ampla, paralela): busca adaptativa sobre config/bit06_robusto.yaml no
cenário RUIM (rendimento de CO2 eta=0,80), já com as restrições duras que
faltavam (estabilidade nunca < 1,08 cal, saída de trilho >= 15 m/s, raiz de
aleta colável). Roda em BLOCOS com sementes diferentes: cada bloco é uma busca
adaptativa completa (explora -> modela -> refina), então vários blocos dão
DIVERSIDADE de bacias em vez de um único ótimo local aprofundado.

ETAPA 2 (fina, multicritério): os finalistas são re-simulados em TODOS os
rendimentos (0,70 / 0,80 / 0,90 / 1,00) x 3 ventos e recebem NOTA de 0 a 100:

    ALCANCE ROBUSTO ......... 40 pts   média do alcance nos 4 rendimentos
    CONSISTÊNCIA ............ 25 pts   pior rendimento / média (não pode desabar)
    LEVEZA .................. 20 pts   massa seca (estrutura + lastro, sem vinagre)
    MARGEM DE SEGURANÇA ..... 15 pts   estabilidade (10) + saída do trilho (5)
                              -----
                              100 pts

Por que esses pesos (idem bit07, re-ancorados para a garrafa reduzida)
----------------------------------------------------------------------
- Alcance é o que a OBAFOG pontua, então é a maior fatia — mas sozinho é
  exatamente o que produziu três projetos que não voaram como prometido.
- Consistência vale quase tanto porque o problema REAL é a bancada variar:
  um projeto de 340 m que só anda com reação perfeita vale menos que um de
  300 m que anda igual com reação ruim.
- Leveza tem peso próprio porque a busca livre sempre tende ao "pesado +
  coeficiente balístico alto", que funciona no papel e some quando falta empuxo.
- Margem de segurança é o menor peso mas tem restrição DURA junto: quem não
  passar de 1 calibre em todo o voo nem entra na lista.

Uso:
    .venv\\Scripts\\python scripts\\bit06_robusto.py                 # etapa 1 + 2
    .venv\\Scripts\\python scripts\\bit06_robusto.py --so-etapa2      # só re-pontua
    .venv\\Scripts\\python scripts\\bit06_robusto.py --blocos 4       # menos blocos
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

CONFIG = r"C:\Users\muril\openrocket-optimizer\config\bit06_robusto.yaml"
PASTA = Path(r"D:\OBAFOG\bit06 1,8L")
MOTORES = PASTA / "motores"
MANIFESTO = json.loads((MOTORES / "manifesto.json").read_text(encoding="utf-8"))
LOG = PASTA / "log_busca_bit06.txt"
STATUS = PASTA / "simulacoes" / "status.json"

# ---------------- cenários de robustez ----------------
# O eixo de incerteza é o RENDIMENTO da reação (quanto do CO2 do ácido ficou
# no sistema), não psi absoluto: assim nenhuma combinação pede mais CO2 do que
# a carga de vinagre pode dar. eta=0,80 é o dia ruim medido no bit04/05.
ETAS = [0.70, 0.80, 0.90, 1.00]
ETA_BUSCA = 0.80
SEEDS_VENTO = [42, 101, 202]
PASSO_FINO = 0.005

# ---------------- etapa 1 ----------------
BLOCOS = 8
AVALIACOES_POR_BLOCO = 12400        # 8 x 12.400 = 99.200 simulações
FINALISTAS = 60
WORKERS = 6                          # 6 JVMs: medido melhor que 10 nesta máquina

# ---------------- pesos da nota (somam 100) ----------------
PESO_ALCANCE = 40.0
PESO_CONSISTENCIA = 25.0
PESO_LEVEZA = 20.0
PESO_ESTABILIDADE = 10.0
PESO_SAIDA_TRILHO = 5.0

# âncoras de normalização (0 pt -> nota cheia)
ALCANCE_ZERO, ALCANCE_CHEIO = 120.0, 340.0        # m (média nos rendimentos)
RAZAO_ZERO, RAZAO_CHEIA = 0.70, 0.95              # pior/média
MASSA_ZERO, MASSA_CHEIA = 0.600, 0.200            # kg de massa seca
ESTAB_ZERO, ESTAB_CHEIA = 1.0, 2.0                # calibres (mínimo do voo)
TRILHO_ZERO, TRILHO_CHEIO = 15.0, 25.0            # m/s na saída do tubo-guia

# ---------------- restrições duras (valem em TODOS os cenários) ----------------
ESTAB_MIN = 1.0
ESTAB_MAX = 3.5
TRILHO_MIN = 15.0
APOGEU_MIN = 30.0


# ============================== utilidades ==============================

def log(msg: str = "", tela: bool = True) -> None:
    linha = f"{time.strftime('%H:%M:%S')} {msg}" if msg else ""
    if tela:
        print(msg, flush=True)
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(linha + "\n")


def escreve_status(**campos) -> None:
    STATUS.parent.mkdir(parents=True, exist_ok=True)
    base = {"atualizado": time.strftime("%Y-%m-%d %H:%M:%S")}
    base.update(campos)
    STATUS.write_text(json.dumps(base, indent=1, ensure_ascii=False), encoding="utf-8")


def fmt_dur(seg: float) -> str:
    h, resto = divmod(int(seg), 3600)
    m, s = divmod(resto, 60)
    return f"{h}h{m:02d}m" if h else f"{m}m{s:02d}s"


def nota_linear(valor: float, zero: float, cheio: float, peso: float) -> float:
    if cheio == zero:
        return 0.0
    t = (valor - zero) / (cheio - zero)
    return peso * float(np.clip(t, 0.0, 1.0))


def troca_rendimento(motor_file: str, eta: float) -> str:
    """Mesmo motor (mesma carga de vinagre), outro rendimento de reação."""
    nome = Path(motor_file[5:]).stem            # Bit06-L1_20-E080
    carga = nome.split("-E")[0]
    return f"file:{MOTORES / f'{carga}-E{int(round(eta * 100)):03d}.eng'}"


def dados_motor(motor_file: str) -> dict:
    return MANIFESTO[Path(motor_file[5:]).stem]


# ============================== ETAPA 2 ==============================

@dataclasses.dataclass
class Avaliacao:
    design: dict
    nota: float
    alcance_medio: float
    alcance_pior: float
    alcance_por_eta: dict[float, float]
    psi_por_eta: dict[float, float]
    massa_seca: float
    estab_min: float
    estab_max: float
    trilho_min: float
    apogeu_medio: float
    partes: dict[str, float]
    motivo_descarte: str | None = None


def avalia_completo(runner: Runner, design: dict) -> Avaliacao:
    """Simula o design em todos os rendimentos × ventos e devolve a nota 0–100."""
    por_eta: dict[float, float] = {}
    psi_por_eta: dict[float, float] = {}
    estab_min, estab_max = 9e9, 0.0
    trilho_min = 9e9
    apogeus: list[float] = []
    massa_seca = 0.0
    descarte: str | None = None
    vazio = dict(alcance_medio=0, alcance_pior=0, alcance_por_eta={}, psi_por_eta={},
                 massa_seca=0, estab_min=0, estab_max=0, trilho_min=0,
                 apogeu_medio=0, partes={})

    for eta in ETAS:
        d = dict(design)
        d["motor"] = troca_rendimento(design["motor"], eta)
        psi_por_eta[eta] = dados_motor(d["motor"])["pressao_psi"]
        alcances = []
        for seed in SEEDS_VENTO:
            r = runner.evaluate(d, sim_overrides={
                "random_seed": seed, "time_step": PASSO_FINO,
                "wind_speed_average": 2.0, "launch_rod_length": 1.0,
                "launch_rod_angle_deg": float(design["launch_angle"]),
            })
            if not r.ok:
                return Avaliacao(design, -1, **vazio,
                                 motivo_descarte=f"sim falhou em eta={eta}: {r.error}")
            m = r.metrics
            faltando = [k for k in ("horizontal_distance", "stability_min", "stability_max",
                                    "launch_rod_velocity", "apogee", "dry_mass")
                        if m.get(k) is None]
            if faltando:
                return Avaliacao(design, -1, **vazio,
                                 motivo_descarte=f"métrica ausente em eta={eta}: {faltando}")
            alcances.append(m["horizontal_distance"])
            estab_min = min(estab_min, m["stability_min"])
            estab_max = max(estab_max, m["stability_max"])
            trilho_min = min(trilho_min, m["launch_rod_velocity"])
            apogeus.append(m["apogee"])
            massa_seca = max(massa_seca, m["dry_mass"])
            if m["stability_min"] < ESTAB_MIN:
                descarte = f"estabilidade {m['stability_min']:.2f} cal < {ESTAB_MIN} em eta={eta}"
            elif m["stability_max"] > ESTAB_MAX:
                descarte = f"estabilidade {m['stability_max']:.2f} cal > {ESTAB_MAX} em eta={eta}"
            elif m["launch_rod_velocity"] < TRILHO_MIN:
                descarte = f"saída do trilho {m['launch_rod_velocity']:.1f} m/s em eta={eta}"
            elif m["apogee"] < APOGEU_MIN:
                descarte = f"apogeu {m['apogee']:.0f} m em eta={eta}"
        por_eta[eta] = float(np.mean(alcances))

    d_med = float(np.mean(list(por_eta.values())))
    d_pior = float(min(por_eta.values()))
    razao = d_pior / d_med if d_med > 0 else 0.0

    partes = {
        "alcance": nota_linear(d_med, ALCANCE_ZERO, ALCANCE_CHEIO, PESO_ALCANCE),
        "consistencia": nota_linear(razao, RAZAO_ZERO, RAZAO_CHEIA, PESO_CONSISTENCIA),
        "leveza": nota_linear(massa_seca, MASSA_ZERO, MASSA_CHEIA, PESO_LEVEZA),
        "estabilidade": nota_linear(estab_min, ESTAB_ZERO, ESTAB_CHEIA, PESO_ESTABILIDADE),
        "saida_trilho": nota_linear(trilho_min, TRILHO_ZERO, TRILHO_CHEIO, PESO_SAIDA_TRILHO),
    }
    nota = sum(partes.values()) if descarte is None else -1.0
    return Avaliacao(design, nota, d_med, d_pior, por_eta, psi_por_eta, massa_seca,
                     estab_min, estab_max, trilho_min, float(np.mean(apogeus)),
                     partes, descarte)


# ============================== ETAPA 1 ==============================

def progresso(bloco: int, total_blocos: int, feitas_antes: int, t_inicio: float,
              orcamento_total: int):
    """Callback de progresso: imprime, loga e atualiza status.json."""
    ultimo = {"i": 0}

    def p(i, total, valor, melhor):
        ultimo["i"] = i
        if i % max(1, total // 20) and i != total:
            return
        feitas = feitas_antes + i
        frac = feitas / orcamento_total if orcamento_total else 0
        decorrido = time.time() - t_inicio
        taxa = feitas / decorrido if decorrido > 0 else 0
        restante = (orcamento_total - feitas) / taxa if taxa > 0 else 0
        m = f"{melhor:.2f}" if melhor is not None and melhor > -1e8 else "n/a"
        barra = "#" * int(frac * 30) + "." * (30 - int(frac * 30))
        log(f"  [bloco {bloco}/{total_blocos}] [{barra}] {feitas:6d}/{orcamento_total} "
            f"({frac*100:4.1f}%) melhor={m} | {taxa:.1f} sims/s | "
            f"resta ~{fmt_dur(restante)}")
        escreve_status(etapa=1, bloco=bloco, blocos=total_blocos,
                       simulacoes_feitas=feitas, simulacoes_total=orcamento_total,
                       percentual=round(frac * 100, 1), melhor_nota_etapa1=m,
                       sims_por_segundo=round(taxa, 2),
                       restante_estimado=fmt_dur(restante))
    return p


def roda_bloco(cfg, bloco: int, blocos: int, por_bloco: int, t0: float) -> None:
    """Um bloco = uma busca adaptativa completa (explora -> modela -> refina)."""
    from orx.optimizer.engine import run_optimization
    log(f"\n-- bloco {bloco}/{blocos} ({por_bloco} simulações, semente {100+bloco}) --")
    cfg_b = dataclasses.replace(
        cfg,
        optimizer=OptimizerConfig(algorithm="adaptive", max_evaluations=por_bloco,
                                  seed=100 + bloco, profile="balanced",
                                  options={"chunk_size": 1500}),
        batch=BatchConfig(workers=WORKERS))
    run_optimization(cfg_b, run_name=f"bit06-robusto-b{bloco}",
                     progress=progresso(bloco, blocos, (bloco - 1) * por_bloco,
                                        t0, blocos * por_bloco))


def etapa1(cfg, blocos: int, por_bloco: int, so_bloco: int | None = None) -> None:
    t0 = time.time()
    if so_bloco is None:
        log(f"\n===== ETAPA 1 — {blocos * por_bloco} simulações em {blocos} blocos "
            f"(rendimento eta={ETA_BUSCA:.2f}, o dia ruim medido no bit04/05) =====")
        for bloco in range(1, blocos + 1):
            roda_bloco(cfg, bloco, blocos, por_bloco, t0)
        log(f"\n>> etapa 1 concluída em {fmt_dur(time.time() - t0)}")
    else:
        # modo "um bloco por processo": o orquestrador chama este script uma vez
        # por bloco. Numa máquina SEM arquivo de paginação, terminar o processo
        # a cada bloco devolve toda a memória ao SO — é o que mantém de pé uma
        # rodada de várias horas. O banco SQLite acumula os resultados de todos.
        roda_bloco(cfg, so_bloco, blocos, por_bloco,
                   time.time() - (so_bloco - 1) * por_bloco * 0.33)


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
        # deduplica: arredondar para o inteiro (cm, mm, grau) colapsa a nuvem de
        # vizinhos do adaptativo, e a lista vira variedade de verdade.
        chave = tuple(round(v) if isinstance(v, float) else v for v in d.values())
        if chave in vistos:
            continue
        vistos.add(chave)
        designs.append(d)
        if len(designs) >= quantos:
            break
    return designs


# ============================== relatório ==============================

def linha_tabela(a: Avaliacao, i: int) -> str:
    return (f"| {i} | **{a.nota:.1f}** | {a.alcance_medio:.0f} m | {a.alcance_pior:.0f} m | "
            f"{a.massa_seca*1000:.0f} g | {a.estab_min:.2f} cal | {a.trilho_min:.1f} m/s | "
            + " | ".join(f"{a.alcance_por_eta[e]:.0f}" for e in ETAS) + " |")


def relatorio(rank: list[Avaliacao], runner: Runner, total_sims: int,
              duracao_s: float) -> None:
    PASTA.mkdir(parents=True, exist_ok=True)
    L: list[str] = []
    add = L.append
    add("# bit06 — reprojeto por NOTA multicritério (0–100)\n")
    add(f"Gerado em {time.strftime('%Y-%m-%d %H:%M')} | garrafa PET retornável "
        f"REDUZIDA ~1,8 L (Ø9,585 cm)\n")
    add(f"**{total_sims:,} simulações** ({fmt_dur(duracao_s)}) — {len(rank)} finalistas "
        f"re-simulados em {len(ETAS)} rendimentos de reação × {len(SEEDS_VENTO)} ventos.\n"
        .replace(",", "."))

    add("## Por que o modelo antigo foi aposentado\n")
    add("O `bit06` anterior (em `_MODELO_ANTIGO_falhou/`) foi otimizado por **alcance "
        "puro**: 376 m no papel, estabilidade ~1,03 cal. É a mesma assinatura de bit04 "
        "e bit05, que foram lançados de verdade, saíram rasos e bateram numa cerca.\n")
    add("Além disso, as pressões que ele assumia (1,35 L → \"170 psi\"; 1,5 L → "
        "\"189 psi\") são exatamente as pressões **nominais** dessas cargas — ou seja, "
        "o projeto contava com **rendimento perfeito da reação**. A bancada real do "
        "Murilo entregou η ≈ 0,82–0,88.\n")

    add("## O eixo de robustez: rendimento, não psi\n")
    add("O bicarbonato entra em excesso, então quem limita o CO₂ é o **ácido do vinagre**. "
        "Cada carga tem um teto físico de pressão. Por isso a robustez aqui é varrida em "
        "**rendimento de reação (η)** — toda combinação é fisicamente possível, e η<1 é "
        "exatamente o que derrubou bit04/bit05.\n")
    add("| η | significado | 1,20 L | 1,35 L | 1,50 L |")
    add("|---|---|---|---|---|")
    for eta in ETAS:
        psis = []
        for carga in ("1_20", "1_35", "1_50"):
            k = f"Bit06-L{carga}-E{int(round(eta*100)):03d}"
            psis.append(f"{MANIFESTO[k]['pressao_psi']:.0f} psi" if k in MANIFESTO else "—")
        sig = {0.70: "dia ruim", 0.80: "o que a bancada deu no bit04/05",
               0.90: "bom dia", 1.00: "reação perfeita (teto físico)"}.get(eta, "")
        add(f"| {eta:.2f} | {sig} | " + " | ".join(psis) + " |")

    add("\n## Como a nota é montada\n")
    add("| critério | peso | 0 ponto em | nota cheia em |")
    add("|---|---|---|---|")
    add(f"| Alcance robusto (média dos rendimentos) | {PESO_ALCANCE:.0f} | "
        f"{ALCANCE_ZERO:.0f} m | {ALCANCE_CHEIO:.0f} m |")
    add(f"| Consistência (pior η / média) | {PESO_CONSISTENCIA:.0f} | "
        f"{RAZAO_ZERO:.2f} | {RAZAO_CHEIA:.2f} |")
    add(f"| Leveza (massa seca) | {PESO_LEVEZA:.0f} | {MASSA_ZERO*1000:.0f} g | "
        f"{MASSA_CHEIA*1000:.0f} g |")
    add(f"| Estabilidade mínima do voo | {PESO_ESTABILIDADE:.0f} | "
        f"{ESTAB_ZERO:.1f} cal | {ESTAB_CHEIA:.1f} cal |")
    add(f"| Saída do tubo-guia | {PESO_SAIDA_TRILHO:.0f} | {TRILHO_ZERO:.0f} m/s | "
        f"{TRILHO_CHEIO:.0f} m/s |")
    add("\nRestrições duras (reprovam o design): estabilidade sempre entre "
        f"{ESTAB_MIN} e {ESTAB_MAX} cal, saída do trilho ≥ {TRILHO_MIN} m/s, "
        f"apogeu ≥ {APOGEU_MIN:.0f} m — em TODOS os rendimentos.\n")

    add("## Ranking\n")
    add("| # | nota | alcance médio | pior η | massa seca | estab mín | trilho | "
        + " | ".join(f"η={e:.2f}" for e in ETAS) + " |")
    add("|" + "---|" * (7 + len(ETAS)))
    for i, a in enumerate(rank[:15], 1):
        add(linha_tabela(a, i))

    campeao = rank[0]
    add("\n## Campeão — parâmetros de construção\n")
    add("| parâmetro | valor |")
    add("|---|---|")
    for k, v in campeao.design.items():
        if k == "motor":
            info = dados_motor(str(v))
            v = f"{info['carga_L']:.2f} L de vinagre (teto {info['pressao_teto_psi']:.0f} psi)"
        add(f"| {k} | {v if not isinstance(v, float) else f'{v:.3f}'} |")
    add("\n### Nota do campeão, critério por critério\n")
    add("| critério | pontos | de |")
    add("|---|---|---|")
    for nome, peso in (("alcance", PESO_ALCANCE), ("consistencia", PESO_CONSISTENCIA),
                       ("leveza", PESO_LEVEZA), ("estabilidade", PESO_ESTABILIDADE),
                       ("saida_trilho", PESO_SAIDA_TRILHO)):
        add(f"| {nome} | {campeao.partes[nome]:.1f} | {peso:.0f} |")
    add(f"| **TOTAL** | **{campeao.nota:.1f}** | **100** |")
    add("\n### Alcance esperado por rendimento\n")
    add("| η | pressão | alcance |")
    add("|---|---|---|")
    for e in ETAS:
        add(f"| {e:.2f} | {campeao.psi_por_eta[e]:.0f} psi | "
            f"{campeao.alcance_por_eta[e]:.0f} m |")

    (PASTA / "RELATORIO_bit06.md").write_text("\n".join(L) + "\n", encoding="utf-8")

    import csv
    with (PASTA / "ranking_bit06.csv").open("w", newline="", encoding="utf-8") as fh:
        campos = ["nota", "alcance_medio", "alcance_pior", "massa_seca_g", "estab_min",
                  "estab_max", "trilho_min"] + [f"alcance_eta{int(e*100)}" for e in ETAS] + \
                 list(rank[0].design.keys())
        w = csv.DictWriter(fh, fieldnames=campos)
        w.writeheader()
        for a in rank:
            linha = {"nota": round(a.nota, 2), "alcance_medio": round(a.alcance_medio, 1),
                     "alcance_pior": round(a.alcance_pior, 1),
                     "massa_seca_g": round(a.massa_seca * 1000, 1),
                     "estab_min": round(a.estab_min, 3), "estab_max": round(a.estab_max, 3),
                     "trilho_min": round(a.trilho_min, 2)}
            linha.update({f"alcance_eta{int(e*100)}": round(a.alcance_por_eta[e], 1)
                          for e in ETAS})
            linha.update(a.design)
            w.writerow(linha)

    ork = PASTA / "bit06_MODELO_FINAL.ork"
    runner.save_design(campeao.design, str(ork))
    json.dump([dataclasses.asdict(a) for a in rank],
              (PASTA / "simulacoes" / "rank_bit06.json").open("w", encoding="utf-8"),
              indent=1, ensure_ascii=False, default=str)
    log(f"\n>> campeão salvo em {ork}")
    log(f">> relatório: {PASTA / 'RELATORIO_bit06.md'}")
    log(f">> ranking:   {PASTA / 'ranking_bit06.csv'}")


def main() -> None:
    setup_logging()
    t0 = time.time()
    cfg = load_config(CONFIG)
    so_etapa2 = "--so-etapa2" in sys.argv

    def arg(nome: str, padrao):
        return int(sys.argv[sys.argv.index(nome) + 1]) if nome in sys.argv else padrao

    blocos = arg("--blocos", BLOCOS)
    por_bloco = arg("--por-bloco", AVALIACOES_POR_BLOCO)
    finalistas = arg("--finalistas", FINALISTAS)
    so_bloco = arg("--bloco", None)

    # só zera o log quando é a rodada inteira; no modo "um bloco por processo"
    # cada chamada acrescenta ao mesmo log para o acompanhamento ficar contínuo
    if so_bloco is None and not so_etapa2:
        LOG.write_text("", encoding="utf-8")
        log("=" * 70)
        log("bit06 — reprojeto robusto da garrafa reduzida (~1,8 L)")
        log("=" * 70)

    if so_bloco is not None:
        etapa1(cfg, blocos, por_bloco, so_bloco=so_bloco)
        return

    if not so_etapa2:
        etapa1(cfg, blocos, por_bloco)

    n_etapa1 = blocos * por_bloco
    log(f"\n===== ETAPA 2 — nota multicritério dos {finalistas} finalistas "
        f"({len(ETAS)} rendimentos × {len(SEEDS_VENTO)} ventos) =====")
    designs = finalistas_do_banco(cfg, finalistas)
    if not designs:
        raise SystemExit("nenhum design viável no banco — rode a etapa 1 primeiro")

    cfg_serial = dataclasses.replace(cfg, batch=BatchConfig(workers=1))
    runner = Runner(cfg_serial)
    rank: list[Avaliacao] = []
    for i, d in enumerate(designs, 1):
        a = avalia_completo(runner, d)
        escreve_status(etapa=2, finalista=i, finalistas=len(designs),
                       aprovados=len(rank),
                       simulacoes_feitas=n_etapa1 + i * len(ETAS) * len(SEEDS_VENTO))
        if a.motivo_descarte:
            log(f"  [{i}/{len(designs)}] descartado: {a.motivo_descarte}")
            continue
        rank.append(a)
        log(f"  [{i}/{len(designs)}] nota {a.nota:5.1f} | médio {a.alcance_medio:5.0f} m | "
            f"pior {a.alcance_pior:5.0f} m | seca {a.massa_seca*1000:4.0f} g | "
            f"estab {a.estab_min:.2f} cal")

    if not rank:
        raise SystemExit("nenhum finalista sobreviveu à validação multi-rendimento")
    rank.sort(key=lambda a: -a.nota)
    total_sims = n_etapa1 + len(designs) * len(ETAS) * len(SEEDS_VENTO)
    relatorio(rank, runner, total_sims, time.time() - t0)
    escreve_status(etapa="concluido", simulacoes_feitas=total_sims,
                   melhor_nota=round(rank[0].nota, 2),
                   duracao=fmt_dur(time.time() - t0))
    log(f"\ntempo total: {fmt_dur(time.time() - t0)} | {total_sims} simulações")


if __name__ == "__main__":
    main()
