"""bit06 v2 — coifa de garrafa PET moldada + NOTA COM AERODINÂMICA.

O que muda em relação a scripts/bit06_robusto.py
------------------------------------------------
1) A coifa virou DADO: o Murilo moldou uma coifa esquentando uma garrafa PET
   sobre um molde — ogival, 17–18 cm, parede de garrafa. Forma, material e
   comprimento saem do espaço de busca.

2) A nota deixou de olhar só o RESULTADO do voo e passou a olhar COMO ele voa:

     ALCANCE ROBUSTO ............ 30   média nos 4 rendimentos de reação
     CONSISTÊNCIA ............... 15   pior rendimento / média
     LEVEZA ..................... 10   massa seca
     ESTABILIDADE MÍNIMA ........ 10   o menor valor durante o voo
     SAÍDA DO TRILHO ............. 5
     ---- aerodinâmica (30 pts) ----
     ARRASTO (Cd médio) ......... 12   quanto o ar cobra por metro subido
     AMORTECIMENTO EM ARFAGEM .... 8   o que faz a oscilação MORRER
     ÂNGULO DE ATAQUE ............ 5   voar de través = cata-vento
     RIGIDEZ AEROELÁSTICA ........ 5   aleta que não balança
                                 ----
                                  100

Por que cada termo aerodinâmico
-------------------------------
- ARRASTO: o alcance já embute o arrasto, mas só nas condições simuladas.
  Pontuar o Cd separadamente premia o foguete limpo, que continua limpo quando
  a realidade sai do script (acabamento, rajada, ângulo fora do nominal).
- AMORTECIMENTO: estabilidade estática diz que o foguete VOLTA ao rumo;
  amortecimento diz se ele volta rápido ou fica oscilando o voo inteiro. Dois
  foguetes com 1,3 cal podem se comportar de forma completamente diferente.
- ÂNGULO DE ATAQUE: cada grau de través é energia gasta empurrando ar de lado
  e é o mecanismo do cata-vento (virar contra o vento e encurtar o alcance).
- RIGIDEZ AEROELÁSTICA: o OpenRocket trata a aleta como rígida. Sem este termo
  nada impede a busca de escolher a chapa mais fina e esbelta possível — que é
  exatamente o que "leveza" premia. Ver src/orx/rocket/aeroelastica.py: o valor
  ABSOLUTO da fórmula não é confiável nesta faixa (t/c ~0,015, muito fora de
  onde ela foi validada, e a aleta é colada numa superfície curva que enrijece);
  ele é usado como ÍNDICE RELATIVO, que acerta a direção.

Âncoras: medidas em 140 amostras VIÁVEIS do próprio espaço
(scripts/calibrar_ancoras_aero.py). As do bit06 v1 não serviam aqui — alcance
com nota cheia em 340 m (ninguém passa de 255 com a coifa curta) e trilho com
nota cheia em 25 m/s (o p05 já é 27,8), dois critérios que não separavam nada.

Uso:
    .venv\\Scripts\\python scripts\\bit06_pet_aero.py --bloco 1 --blocos 8 --por-bloco 12400
    .venv\\Scripts\\python scripts\\bit06_pet_aero.py --so-etapa2 --finalistas 60
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

CONFIG = r"C:\Users\muril\openrocket-optimizer\config\bit06_pet_aero.yaml"
PASTA = Path(r"D:\1-Competicoes\OBAFOG\foguetes\bit06 1,8L")
MOTORES = PASTA / "motores"
MANIFESTO = json.loads((MOTORES / "manifesto.json").read_text(encoding="utf-8"))
LOG = PASTA / "log_busca_bit06_pet.txt"
STATUS = PASTA / "simulacoes" / "status_pet.json"

ETAS = [0.70, 0.80, 0.90, 1.00]
ETA_BUSCA = 0.80
SEEDS_VENTO = [42, 101, 202]
PASSO_FINO = 0.005

BLOCOS = 8
AVALIACOES_POR_BLOCO = 12400
FINALISTAS = 60
WORKERS = 6

# ---------------- pesos (somam 100) ----------------
PESO_ALCANCE = 28.0
PESO_LEVEZA = 20.0          # 2o maior: massa seca pesa de novo como na v1 do bit06
PESO_ARRASTO = 12.0
PESO_CONSISTENCIA = 12.0
PESO_ESTABILIDADE = 10.0
PESO_AMORTECIMENTO = 6.0
PESO_RIGIDEZ = 6.0
PESO_AOA = 4.0
PESO_SAIDA_TRILHO = 2.0

# ---------------- âncoras (p05..p95 da população viável) ----------------
ALCANCE_ZERO, ALCANCE_CHEIO = 100.0, 280.0     # m
RAZAO_ZERO, RAZAO_CHEIA = 0.70, 0.95           # pior/média
MASSA_ZERO, MASSA_CHEIA = 1.000, 0.300         # kg (menor é melhor)
ESTAB_ZERO, ESTAB_CHEIA = 1.0, 2.0             # cal
TRILHO_ZERO, TRILHO_CHEIO = 25.0, 40.0         # m/s
CD_ZERO, CD_CHEIO = 0.55, 0.33                 # menor é melhor
AMORT_ZERO, AMORT_CHEIO = 0.0002, 0.0028       # maior é melhor
AOA_ZERO, AOA_CHEIO = 6.5, 3.5                 # graus, menor é melhor
RIGIDEZ_ZERO, RIGIDEZ_CHEIA = 30.0, 300.0      # m/s (índice relativo)

# ---------------- restrições duras ----------------
ESTAB_MIN = 1.0
ESTAB_MAX = 3.5
TRILHO_MIN = 15.0
APOGEU_MIN = 30.0


def log(msg: str = "") -> None:
    print(msg, flush=True)
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write((f"{time.strftime('%H:%M:%S')} {msg}" if msg else "") + "\n")


def escreve_status(**campos) -> None:
    STATUS.parent.mkdir(parents=True, exist_ok=True)
    base = {"atualizado": time.strftime("%Y-%m-%d %H:%M:%S")}
    base.update(campos)
    STATUS.write_text(json.dumps(base, indent=1, ensure_ascii=False), encoding="utf-8")


def fmt_dur(seg: float) -> str:
    h, r = divmod(int(seg), 3600)
    m, s = divmod(r, 60)
    return f"{h}h{m:02d}m" if h else f"{m}m{s:02d}s"


def nota_linear(valor: float | None, zero: float, cheio: float, peso: float) -> float:
    """Nota linear entre `zero` (0 pt) e `cheio` (peso). Funciona nos dois
    sentidos: se cheio < zero, é porque menor é melhor (arrasto, AoA)."""
    if valor is None or cheio == zero:
        return 0.0
    t = (valor - zero) / (cheio - zero)
    return peso * float(np.clip(t, 0.0, 1.0))


def troca_rendimento(motor_file: str, eta: float) -> str:
    nome = Path(motor_file[5:]).stem
    carga = nome.split("-E")[0]
    return f"file:{MOTORES / f'{carga}-E{int(round(eta * 100)):03d}.eng'}"


def dados_motor(motor_file: str) -> dict:
    return MANIFESTO[Path(motor_file[5:]).stem]


def normaliza_motor(motor_file: str) -> str:
    """Reaponta o caminho do motor para a pasta ATUAL, preservando o arquivo.

    O banco SQLite guarda o design com o caminho absoluto do .eng como texto.
    Se a pasta do projeto mudar de lugar (reorganização do disco), os designs
    antigos continuam apontando para o caminho velho e o salvamento do .ork
    quebra com FileNotFoundError — mesmo que a simulação funcione, porque ela
    reconstrói o caminho a cada rendimento. Aqui só o nome do arquivo importa.
    """
    if not isinstance(motor_file, str) or not motor_file.startswith("file:"):
        return motor_file
    return f"file:{MOTORES / Path(motor_file[5:]).name}"


@dataclasses.dataclass
class Avaliacao:
    design: dict
    nota: float
    alcance_medio: float
    alcance_pior: float
    alcance_por_eta: dict
    psi_por_eta: dict
    massa_seca: float
    estab_min: float
    estab_max: float
    trilho_min: float
    apogeu_medio: float
    cd_medio: float
    cd_atrito: float
    cd_pressao: float
    cd_base: float
    aoa_max: float
    amortecimento: float
    rigidez: float
    razao_finura: float
    partes: dict
    motivo_descarte: str | None = None


def avalia_completo(runner: Runner, design: dict) -> Avaliacao:
    por_eta: dict = {}
    psi_por_eta: dict = {}
    estab_min, estab_max, trilho_min = 9e9, 0.0, 9e9
    apogeus: list[float] = []
    massa_seca = 0.0
    aero: dict[str, list[float]] = {k: [] for k in
                                    ("cd_medio", "cd_atrito", "cd_pressao", "cd_base",
                                     "aoa_max", "amortecimento_pitch", "razao_finura")}
    rigidez = 0.0
    descarte: str | None = None
    vazio = dict(alcance_medio=0, alcance_pior=0, alcance_por_eta={}, psi_por_eta={},
                 massa_seca=0, estab_min=0, estab_max=0, trilho_min=0, apogeu_medio=0,
                 cd_medio=0, cd_atrito=0, cd_pressao=0, cd_base=0, aoa_max=0,
                 amortecimento=0, rigidez=0, razao_finura=0, partes={})

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
            falta = [k for k in ("horizontal_distance", "stability_min", "stability_max",
                                 "launch_rod_velocity", "apogee", "dry_mass", "cd_medio")
                     if m.get(k) is None]
            if falta:
                return Avaliacao(design, -1, **vazio,
                                 motivo_descarte=f"métrica ausente em eta={eta}: {falta}")
            alcances.append(m["horizontal_distance"])
            estab_min = min(estab_min, m["stability_min"])
            estab_max = max(estab_max, m["stability_max"])
            trilho_min = min(trilho_min, m["launch_rod_velocity"])
            apogeus.append(m["apogee"])
            massa_seca = max(massa_seca, m["dry_mass"])
            rigidez = max(rigidez, m.get("fin_flutter_velocity") or 0.0)
            for k in aero:
                v = m.get(k)
                if v is not None:
                    aero[k].append(float(v))
            if m["stability_min"] < ESTAB_MIN:
                descarte = f"estabilidade {m['stability_min']:.2f} cal < {ESTAB_MIN} em eta={eta}"
            elif m["stability_max"] > ESTAB_MAX:
                descarte = f"estabilidade {m['stability_max']:.2f} cal > {ESTAB_MAX} em eta={eta}"
            elif m["launch_rod_velocity"] < TRILHO_MIN:
                descarte = f"saída do trilho {m['launch_rod_velocity']:.1f} m/s em eta={eta}"
            elif m["apogee"] < APOGEU_MIN:
                descarte = f"apogeu {m['apogee']:.0f} m em eta={eta}"
        por_eta[eta] = float(np.mean(alcances))

    med = lambda k: float(np.mean(aero[k])) if aero[k] else 0.0   # noqa: E731
    d_med = float(np.mean(list(por_eta.values())))
    d_pior = float(min(por_eta.values()))
    razao = d_pior / d_med if d_med > 0 else 0.0
    cd = med("cd_medio")
    aoa = float(np.max(aero["aoa_max"])) if aero["aoa_max"] else 0.0
    amort = med("amortecimento_pitch")

    partes = {
        "alcance": nota_linear(d_med, ALCANCE_ZERO, ALCANCE_CHEIO, PESO_ALCANCE),
        "consistencia": nota_linear(razao, RAZAO_ZERO, RAZAO_CHEIA, PESO_CONSISTENCIA),
        "leveza": nota_linear(massa_seca, MASSA_ZERO, MASSA_CHEIA, PESO_LEVEZA),
        "estabilidade": nota_linear(estab_min, ESTAB_ZERO, ESTAB_CHEIA, PESO_ESTABILIDADE),
        "saida_trilho": nota_linear(trilho_min, TRILHO_ZERO, TRILHO_CHEIO, PESO_SAIDA_TRILHO),
        "arrasto": nota_linear(cd, CD_ZERO, CD_CHEIO, PESO_ARRASTO),
        "amortecimento": nota_linear(amort, AMORT_ZERO, AMORT_CHEIO, PESO_AMORTECIMENTO),
        "angulo_ataque": nota_linear(aoa, AOA_ZERO, AOA_CHEIO, PESO_AOA),
        "rigidez_aleta": nota_linear(rigidez, RIGIDEZ_ZERO, RIGIDEZ_CHEIA, PESO_RIGIDEZ),
    }
    nota = sum(partes.values()) if descarte is None else -1.0
    return Avaliacao(design, nota, d_med, d_pior, por_eta, psi_por_eta, massa_seca,
                     estab_min, estab_max, trilho_min, float(np.mean(apogeus)),
                     cd, med("cd_atrito"), med("cd_pressao"), med("cd_base"),
                     aoa, amort, rigidez, med("razao_finura"), partes, descarte)


# ============================== etapa 1 ==============================

def progresso(bloco: int, blocos: int, feitas_antes: int, t0: float, total: int):
    def p(i, tot, valor, melhor):
        if i % max(1, tot // 20) and i != tot:
            return
        feitas = feitas_antes + i
        frac = feitas / total if total else 0
        dec = time.time() - t0
        taxa = feitas / dec if dec > 0 else 0
        resta = (total - feitas) / taxa if taxa > 0 else 0
        mm = f"{melhor:.2f}" if melhor is not None and melhor > -1e8 else "n/a"
        barra = "#" * int(frac * 30) + "." * (30 - int(frac * 30))
        log(f"  [bloco {bloco}/{blocos}] [{barra}] {feitas:6d}/{total} "
            f"({frac*100:4.1f}%) melhor={mm} | {taxa:.1f} sims/s | resta ~{fmt_dur(resta)}")
        escreve_status(etapa=1, bloco=bloco, blocos=blocos, simulacoes_feitas=feitas,
                       simulacoes_total=total, percentual=round(frac * 100, 1),
                       melhor_nota_etapa1=mm, sims_por_segundo=round(taxa, 2),
                       restante_estimado=fmt_dur(resta))
    return p


def roda_bloco(cfg, bloco: int, blocos: int, por_bloco: int, t0: float) -> None:
    from orx.optimizer.engine import run_optimization
    log(f"\n-- bloco {bloco}/{blocos} ({por_bloco} simulações, semente {200+bloco}) --")
    cfg_b = dataclasses.replace(
        cfg,
        optimizer=OptimizerConfig(algorithm="adaptive", max_evaluations=por_bloco,
                                  seed=200 + bloco, profile="balanced",
                                  options={"chunk_size": 1500}),
        batch=BatchConfig(workers=WORKERS))
    run_optimization(cfg_b, run_name=f"bit06-pet-aero-b{bloco}",
                     progress=progresso(bloco, blocos, (bloco - 1) * por_bloco, t0,
                                        blocos * por_bloco))


def finalistas_do_banco(cfg, quantos: int) -> list[dict]:
    db = ResultsDB(cfg.db_path)
    df = db.evaluations_df()
    db.close()
    nomes = [p.name for p in cfg.parameters]
    inteiros = {p.name for p in cfg.parameters if getattr(p, "integer", False)}
    ok = df[(df["feasible"] == 1) & df["score"].notna()].sort_values("score", ascending=False)
    designs, vistos = [], set()
    for _, row in ok.iterrows():
        d = {}
        for n in nomes:
            v = row[f"p_{n}"]
            d[n] = v if isinstance(v, str) else (int(round(float(v))) if n in inteiros else float(v))
        d["motor"] = normaliza_motor(d.get("motor", ""))
        chave = tuple(round(v) if isinstance(v, float) else v for v in d.values())
        if chave in vistos:
            continue
        vistos.add(chave)
        designs.append(d)
        if len(designs) >= quantos:
            break
    return designs


# ============================== relatório ==============================

def relatorio(rank: list[Avaliacao], runner: Runner, total_sims: int, dur: float) -> None:
    L: list[str] = []
    add = L.append
    add("# bit06 v2 — coifa de garrafa PET + nota aerodinâmica\n")
    add(f"Gerado em {time.strftime('%Y-%m-%d %H:%M')} | garrafa reduzida ~1,8 L "
        f"(Ø9,585 cm) | **coifa de garrafa PET moldada a quente, ogival, 17–18 cm**\n")
    add(f"**{total_sims:,} simulações** ({fmt_dur(dur)}) — {len(rank)} finalistas "
        f"pontuados em {len(ETAS)} rendimentos × {len(SEEDS_VENTO)} ventos.\n"
        .replace(",", "."))

    add("## A nota, critério por critério\n")
    add("| critério | peso | 0 ponto em | nota cheia em | por que está aqui |")
    add("|---|---|---|---|---|")
    add(f"| Alcance robusto | {PESO_ALCANCE:.0f} | {ALCANCE_ZERO:.0f} m | {ALCANCE_CHEIO:.0f} m | é o que a OBAFOG pontua |")
    add(f"| Consistência | {PESO_CONSISTENCIA:.0f} | {RAZAO_ZERO:.2f} | {RAZAO_CHEIA:.2f} | a bancada varia de um dia p/ outro |")
    add(f"| Leveza | {PESO_LEVEZA:.0f} | {MASSA_ZERO*1000:.0f} g | {MASSA_CHEIA*1000:.0f} g | peso vira voo rasante quando falta empuxo |")
    add(f"| Estabilidade mínima | {PESO_ESTABILIDADE:.0f} | {ESTAB_ZERO:.1f} cal | {ESTAB_CHEIA:.1f} cal | o que faltou no bit04/05 |")
    add(f"| Saída do trilho | {PESO_SAIDA_TRILHO:.0f} | {TRILHO_ZERO:.0f} m/s | {TRILHO_CHEIO:.0f} m/s | tolera tip-off e vento |")
    add(f"| **Arrasto (Cd médio)** | {PESO_ARRASTO:.0f} | {CD_ZERO:.2f} | {CD_CHEIO:.2f} | foguete limpo continua limpo fora do script |")
    add(f"| **Amortecimento em arfagem** | {PESO_AMORTECIMENTO:.0f} | {AMORT_ZERO:.4f} | {AMORT_CHEIO:.4f} | faz a oscilação morrer, não só voltar |")
    add(f"| **Ângulo de ataque** | {PESO_AOA:.0f} | {AOA_ZERO:.1f}° | {AOA_CHEIO:.1f}° | voar de través = cata-vento |")
    add(f"| **Rigidez aeroelástica** | {PESO_RIGIDEZ:.0f} | {RIGIDEZ_ZERO:.0f} | {RIGIDEZ_CHEIA:.0f} | aleta fina demais balança; o OpenRocket não vê |")
    add("\nRestrições duras (reprovam): estabilidade sempre entre "
        f"{ESTAB_MIN} e {ESTAB_MAX} cal, saída do trilho ≥ {TRILHO_MIN} m/s, "
        f"apogeu ≥ {APOGEU_MIN:.0f} m — em TODOS os rendimentos.\n")
    add("> As âncoras vêm de 140 amostras viáveis do próprio espaço de busca. As do\n"
        "> bit06 v1 não serviriam: alcance com nota cheia em 340 m (ninguém passa de\n"
        "> 255 com a coifa curta) e trilho com nota cheia em 25 m/s (o p05 já é 27,8).\n")

    add("## Ranking\n")
    add("| # | nota | alcance | pior η | massa | estab | Cd | AoA | amort. | rigidez |")
    add("|---|---|---|---|---|---|---|---|---|---|")
    for i, a in enumerate(rank[:15], 1):
        add(f"| {i} | **{a.nota:.1f}** | {a.alcance_medio:.0f} m | {a.alcance_pior:.0f} m | "
            f"{a.massa_seca*1000:.0f} g | {a.estab_min:.2f} | {a.cd_medio:.3f} | "
            f"{a.aoa_max:.1f}° | {a.amortecimento:.4f} | {a.rigidez:.0f} |")

    c = rank[0]
    add("\n## Campeão — parâmetros de construção\n")
    add("| parâmetro | valor |")
    add("|---|---|")
    for k, v in c.design.items():
        if k == "motor":
            info = dados_motor(str(v))
            v = f"{info['carga_L']:.2f} L de vinagre (teto {info['pressao_teto_psi']:.0f} psi)"
        add(f"| {k} | {v if not isinstance(v, float) else f'{v:.3f}'} |")

    add("\n### Nota do campeão\n")
    add("| critério | pontos | de |")
    add("|---|---|---|")
    for nome, peso in (("alcance", PESO_ALCANCE), ("consistencia", PESO_CONSISTENCIA),
                       ("leveza", PESO_LEVEZA), ("estabilidade", PESO_ESTABILIDADE),
                       ("saida_trilho", PESO_SAIDA_TRILHO), ("arrasto", PESO_ARRASTO),
                       ("amortecimento", PESO_AMORTECIMENTO), ("angulo_ataque", PESO_AOA),
                       ("rigidez_aleta", PESO_RIGIDEZ)):
        add(f"| {nome} | {c.partes[nome]:.1f} | {peso:.0f} |")
    add(f"| **TOTAL** | **{c.nota:.1f}** | **100** |")

    add("\n### Composição do arrasto do campeão\n")
    add("| parcela | Cd | o que é |")
    add("|---|---|---|")
    add(f"| atrito (pele) | {c.cd_atrito:.4f} | superfície molhada pelo ar |")
    add(f"| pressão (forma) | {c.cd_pressao:.4f} | nariz e ombro empurrando ar |")
    add(f"| base (esteira) | {c.cd_base:.4f} | vácuo atrás da traseira |")
    add(f"| **total** | **{c.cd_medio:.4f}** | razão de finura {c.razao_finura:.2f} |")

    add("\n### Alcance por rendimento\n")
    add("| η | pressão | alcance |")
    add("|---|---|---|")
    for e in ETAS:
        add(f"| {e:.2f} | {c.psi_por_eta[e]:.0f} psi | {c.alcance_por_eta[e]:.0f} m |")

    (PASTA / "RELATORIO_bit06_PET_AERO.md").write_text("\n".join(L) + "\n", encoding="utf-8")

    import csv
    with (PASTA / "ranking_bit06_pet_aero.csv").open("w", newline="", encoding="utf-8") as fh:
        campos = ["nota", "alcance_medio", "alcance_pior", "massa_seca_g", "estab_min",
                  "trilho_min", "cd_medio", "cd_atrito", "cd_pressao", "cd_base",
                  "aoa_max", "amortecimento", "rigidez", "razao_finura"] + \
                 [f"alcance_eta{int(e*100)}" for e in ETAS] + \
                 [f"pts_{k}" for k in rank[0].partes] + list(rank[0].design.keys())
        w = csv.DictWriter(fh, fieldnames=campos)
        w.writeheader()
        for a in rank:
            linha = {"nota": round(a.nota, 2), "alcance_medio": round(a.alcance_medio, 1),
                     "alcance_pior": round(a.alcance_pior, 1),
                     "massa_seca_g": round(a.massa_seca * 1000, 1),
                     "estab_min": round(a.estab_min, 3), "trilho_min": round(a.trilho_min, 2),
                     "cd_medio": round(a.cd_medio, 4), "cd_atrito": round(a.cd_atrito, 4),
                     "cd_pressao": round(a.cd_pressao, 4), "cd_base": round(a.cd_base, 4),
                     "aoa_max": round(a.aoa_max, 2), "amortecimento": round(a.amortecimento, 5),
                     "rigidez": round(a.rigidez, 1), "razao_finura": round(a.razao_finura, 2)}
            linha.update({f"alcance_eta{int(e*100)}": round(a.alcance_por_eta[e], 1) for e in ETAS})
            linha.update({f"pts_{k}": round(v, 2) for k, v in a.partes.items()})
            linha.update(a.design)
            w.writerow(linha)

    ork = PASTA / "bit06_PET_AERO_FINAL.ork"
    runner.save_design(c.design, str(ork))
    json.dump([dataclasses.asdict(a) for a in rank],
              (PASTA / "simulacoes" / "rank_bit06_pet_aero.json").open("w", encoding="utf-8"),
              indent=1, ensure_ascii=False, default=str)
    log(f"\n>> campeão: {ork}")
    log(f">> relatório: {PASTA / 'RELATORIO_bit06_PET_AERO.md'}")


def main() -> None:
    setup_logging()
    t0 = time.time()
    cfg = load_config(CONFIG)
    so_etapa2 = "--so-etapa2" in sys.argv

    def arg(nome, padrao):
        return int(sys.argv[sys.argv.index(nome) + 1]) if nome in sys.argv else padrao

    blocos = arg("--blocos", BLOCOS)
    por_bloco = arg("--por-bloco", AVALIACOES_POR_BLOCO)
    finalistas = arg("--finalistas", FINALISTAS)
    so_bloco = arg("--bloco", None)

    if so_bloco is not None:
        roda_bloco(cfg, so_bloco, blocos, por_bloco,
                   time.time() - (so_bloco - 1) * por_bloco * 0.20)
        return

    if not so_etapa2:
        LOG.write_text("", encoding="utf-8")
        for b in range(1, blocos + 1):
            roda_bloco(cfg, b, blocos, por_bloco, t0)

    n1 = blocos * por_bloco
    log(f"\n===== ETAPA 2 — nota aerodinâmica dos {finalistas} finalistas =====")
    designs = finalistas_do_banco(cfg, finalistas)
    if not designs:
        raise SystemExit("nenhum design viável no banco — rode a etapa 1 primeiro")

    runner = Runner(dataclasses.replace(cfg, batch=BatchConfig(workers=1)))
    rank: list[Avaliacao] = []
    for i, d in enumerate(designs, 1):
        a = avalia_completo(runner, d)
        escreve_status(etapa=2, finalista=i, finalistas=len(designs), aprovados=len(rank),
                       simulacoes_feitas=n1 + i * len(ETAS) * len(SEEDS_VENTO))
        if a.motivo_descarte:
            log(f"  [{i}/{len(designs)}] descartado: {a.motivo_descarte}")
            continue
        rank.append(a)
        log(f"  [{i}/{len(designs)}] nota {a.nota:5.1f} | {a.alcance_medio:5.0f} m | "
            f"seca {a.massa_seca*1000:4.0f} g | estab {a.estab_min:.2f} | "
            f"Cd {a.cd_medio:.3f} | AoA {a.aoa_max:4.1f}° | rig {a.rigidez:5.0f}")

    if not rank:
        raise SystemExit("nenhum finalista sobreviveu")
    rank.sort(key=lambda a: -a.nota)
    total = n1 + len(designs) * len(ETAS) * len(SEEDS_VENTO)
    relatorio(rank, runner, total, time.time() - t0)
    escreve_status(etapa="concluido", simulacoes_feitas=total,
                   melhor_nota=round(rank[0].nota, 2), duracao=fmt_dur(time.time() - t0))
    log(f"\ntempo total: {fmt_dur(time.time() - t0)} | {total} simulações")


if __name__ == "__main__":
    main()
