"""bit07 — variantes da fronteira + a versão CONSTRUÍVEL de verdade.

A busca principal (scripts/bit07_robusto.py) devolveu 40 finalistas praticamente
empatados (nota 69,9–72,3). Empate técnico não se resolve no grito: quem escolhe
é quem vai construir e lançar. Este script separa as opções que importam:

  A) MAIOR NOTA        — o campeão puro do modelo de pontuação
  B) MAIOR ALCANCE     — o mais longe entre os aprovados (todas as restrições)
  C) MAIS LEVE         — o menor massa seca aprovado
  D) MATERIAIS REAIS   — o melhor usando ogiva em PLA + aletas de poliestireno,
                         que é como TODOS os bits do Murilo são construídos.
                         A busca livre escolhe papelão porque a leveza paga
                         ponto; papelão de 0,6 mm não sobrevive a 45 m/s de
                         saída, então esta é a variante para levar a campo.

Cada uma vira um .ork e uma seção no relatório.
"""

from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from orx.config import load_config
from orx.config.loader import BatchConfig
from orx.results.db import ResultsDB
from orx.simulation.runner import Runner
from orx.utils.logging import setup_logging

import bit07_robusto as B

CANDIDATOS_POR_GRUPO = 18


def designs_do_banco(cfg, filtro=None, quantos: int = CANDIDATOS_POR_GRUPO) -> list[dict]:
    db = ResultsDB(cfg.db_path)
    df = db.evaluations_df()
    db.close()
    nomes = [p.name for p in cfg.parameters]
    inteiros = {p.name for p in cfg.parameters if getattr(p, "integer", False)}
    ok = df[(df["feasible"] == 1) & df["score"].notna()].sort_values("score", ascending=False)
    out: list[dict] = []
    vistos: set = set()
    for _, row in ok.iterrows():
        d = {}
        for n in nomes:
            v = row[f"p_{n}"]
            d[n] = v if isinstance(v, str) else (int(round(float(v))) if n in inteiros else float(v))
        if filtro and not filtro(d):
            continue
        chave = tuple(round(v) if isinstance(v, float) else v for v in d.values())
        if chave in vistos:
            continue
        vistos.add(chave)
        out.append(d)
        if len(out) >= quantos:
            break
    return out


def avalia_todos(runner, designs) -> list[B.Avaliacao]:
    """Avalia cada design UMA vez (18 simulações cada) e devolve os aprovados.

    Os grupos A/B/C saem todos da mesma lista — avaliar por grupo repetiria o
    mesmo trabalho pesado três vezes.
    """
    avaliados = []
    for i, d in enumerate(designs, 1):
        a = B.avalia_completo(runner, d)
        if a.motivo_descarte:
            print(f"  [{i}/{len(designs)}] reprovado: {a.motivo_descarte}", flush=True)
            continue
        avaliados.append(a)
        print(f"  [{i}/{len(designs)}] nota {a.nota:5.1f} | {a.alcance_medio:5.0f} m | "
              f"{a.massa_seca*1000:4.0f} g | {a.estab_min:.2f} cal", flush=True)
    return avaliados


def descreve(a: B.Avaliacao) -> list[str]:
    L = ["| parâmetro | valor |", "|---|---|"]
    for k, v in a.design.items():
        if k == "motor":
            v = Path(str(v)[5:]).stem
        L.append(f"| {k} | {v if not isinstance(v, float) else f'{v:.2f}'} |")
    L += ["", f"nota **{a.nota:.1f}** · alcance médio **{a.alcance_medio:.0f} m** "
              f"(pior pressão {a.alcance_pior:.0f} m) · massa seca **{a.massa_seca*1000:.0f} g** "
              f"· estabilidade mínima **{a.estab_min:.2f} cal** · saída do trilho "
              f"{a.trilho_min:.1f} m/s", "",
          "| pressão | " + " | ".join(f"{p} psi" for p in B.PRESSOES) + " |",
          "|---|" + "---|" * len(B.PRESSOES),
          "| alcance | " + " | ".join(f"{a.alcance_por_psi[p]:.0f} m" for p in B.PRESSOES) + " |",
          "", "| critério | pontos | de |", "|---|---|---|"]
    for nome, peso in (("alcance", B.PESO_ALCANCE), ("consistencia", B.PESO_CONSISTENCIA),
                       ("leveza", B.PESO_LEVEZA), ("estabilidade", B.PESO_ESTABILIDADE),
                       ("saida_trilho", B.PESO_SAIDA_TRILHO)):
        L.append(f"| {nome} | {a.partes[nome]:.1f} | {peso:.0f} |")
    L.append(f"| **TOTAL** | **{a.nota:.1f}** | **100** |")
    return L


def main() -> None:
    setup_logging()
    cfg = load_config(B.CONFIG)
    runner = Runner(dataclasses.replace(cfg, batch=BatchConfig(workers=1)))

    reais = lambda d: d["nose_material"] == "pla" and d["fin_material"] == "poliestireno"

    livres = designs_do_banco(cfg, quantos=30)
    print(f"\n=== busca livre: {len(livres)} candidatos ===", flush=True)
    aval_livres = avalia_todos(runner, livres)

    construiveis = designs_do_banco(cfg, filtro=reais, quantos=22)
    print(f"\n=== materiais reais (PLA + poliestireno): {len(construiveis)} candidatos ===",
          flush=True)
    aval_reais = avalia_todos(runner, construiveis)

    grupos = [
        ("A", "Maior nota (busca livre)", aval_livres, lambda a: a.nota,
         "bit07_A_maior_nota.ork"),
        ("B", "Maior alcance entre os aprovados", aval_livres,
         lambda a: a.alcance_medio, "bit07_B_maior_alcance.ork"),
        ("C", "Mais leve entre os aprovados", aval_livres,
         lambda a: -a.massa_seca, "bit07_C_mais_leve.ork"),
        ("D", "MATERIAIS REAIS (PLA + poliestireno) — o de construir", aval_reais,
         lambda a: a.nota, "bit07_D_materiais_reais.ork"),
    ]

    secoes: list[str] = ["", "---", "", "# Opções — a fronteira, não um vencedor só", "",
                         "Os 40 finalistas ficaram entre 69,9 e 72,3 pontos: empate técnico.",
                         "Abaixo, as opções que realmente diferem entre si.", ""]
    resultados = {}
    for tag, titulo, avaliados, chave, arquivo in grupos:
        if not avaliados:
            secoes += [f"## {tag}) {titulo}", "", "*nenhum design aprovado com esse filtro*", ""]
            continue
        a = max(avaliados, key=chave)
        resultados[tag] = a
        destino = B.PASTA / arquivo
        runner.save_design(a.design, str(destino))
        print(f"\n{tag}) {titulo} -> {destino}")
        secoes += [f"## {tag}) {titulo}", "", f"Arquivo: `{arquivo}`", ""] + descreve(a) + [""]

    if "D" in resultados:
        alvo = B.PASTA / "bit07_MODELO_FINAL.ork"
        runner.save_design(resultados["D"].design, str(alvo))
        secoes += ["", "> **`bit07_MODELO_FINAL.ork` é a opção D** (materiais reais). "
                   "A opção A pontua mais, mas usa ogiva e aletas de papelão — leve no "
                   "modelo, frágil a 45 m/s de saída. Se você for imprimir a ogiva em PLA "
                   "e cortar as aletas em poliestireno, como sempre fez, construa a D.", ""]

    rel = B.PASTA / "RELATORIO_bit07.md"
    rel.write_text(rel.read_text(encoding="utf-8") + "\n".join(secoes) + "\n", encoding="utf-8")
    print(f"\nrelatório atualizado: {rel}")


if __name__ == "__main__":
    main()
