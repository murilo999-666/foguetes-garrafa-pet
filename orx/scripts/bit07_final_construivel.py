"""bit07 — escolhe o modelo FINAL entre os construíveis, já com as espessuras reais.

A busca livre trabalha com parede contínua (0,6–3,0 mm) e material livre; a
oficina do Murilo tem PLA impresso e chapa de poliestireno de 1,0 mm. Este
script pega os candidatos de materiais reais, **arredonda a espessura para o
construível** (ogiva 1,2 mm, aletas 1,0 mm), re-mede cada um nas 8 pressões
(130→200 psi) e entrega dois:

  FINAL         — maior nota entre os construíveis  -> bit07_MODELO_FINAL.ork
  MARGEM EXTRA  — maior nota entre os que têm estabilidade mínima >= 1,5 cal
                  -> bit07_E_margem_extra.ork

Por que os dois: a nota trata estabilidade como 10 dos 100 pontos, mas quem
acabou de ver dois foguetes baterem numa cerca pode preferir pagar alguns metros
por mais margem. A escolha é de quem lança.
"""

from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from orx.config import load_config
from orx.config.loader import BatchConfig
from orx.simulation.runner import Runner
from orx.utils.logging import setup_logging

import bit07_robusto as B
import bit07_variantes as V

ESPESSURA_OGIVA_MM = 1.2      # parede confiável em impressão 3D
ESPESSURA_ALETA_MM = 1.0      # chapa de poliestireno que a equipe usa
MARGEM_EXTRA_CAL = 1.5        # o que conta como "margem extra"


def construivel(d: dict) -> dict:
    return {**d, "nose_thickness": ESPESSURA_OGIVA_MM, "fin_thickness": ESPESSURA_ALETA_MM}


def main() -> None:
    setup_logging()
    cfg = load_config(B.CONFIG)
    runner = Runner(dataclasses.replace(cfg, batch=BatchConfig(workers=1)))

    reais = lambda d: d["nose_material"] == "pla" and d["fin_material"] == "poliestireno"
    candidatos = [construivel(d) for d in V.designs_do_banco(cfg, filtro=reais, quantos=22)]
    print(f"{len(candidatos)} candidatos de materiais reais, espessuras arredondadas "
          f"({ESPESSURA_OGIVA_MM} mm / {ESPESSURA_ALETA_MM} mm)\n")

    aprovados = V.avalia_todos(runner, candidatos)
    if not aprovados:
        raise SystemExit("nenhum candidato construível sobreviveu às 8 pressões")

    final = max(aprovados, key=lambda a: a.nota)
    com_margem = [a for a in aprovados if a.estab_min >= MARGEM_EXTRA_CAL]
    margem = max(com_margem, key=lambda a: a.nota) if com_margem else None

    runner.save_design(final.design, str(B.PASTA / "bit07_MODELO_FINAL.ork"))
    print(f"\nFINAL -> bit07_MODELO_FINAL.ork | nota {final.nota:.1f} | "
          f"{final.alcance_medio:.0f} m | {final.massa_seca*1000:.0f} g | "
          f"{final.estab_min:.2f} cal")

    secoes = ["", "---", "", "# Modelo entregue (espessuras construíveis)", "",
              f"Ogiva **{ESPESSURA_OGIVA_MM} mm** em PLA impresso, aletas "
              f"**{ESPESSURA_ALETA_MM} mm** em poliestireno — o material que a equipe tem. "
              "Todos os candidatos de materiais reais foram re-medidos já arredondados, "
              "nas 8 pressões.", "",
              "## FINAL — `bit07_MODELO_FINAL.ork`", ""] + V.descreve(final) + [""]

    if margem is not None and margem.design != final.design:
        runner.save_design(margem.design, str(B.PASTA / "bit07_E_margem_extra.ork"))
        print(f"MARGEM EXTRA -> bit07_E_margem_extra.ork | nota {margem.nota:.1f} | "
              f"{margem.alcance_medio:.0f} m | {margem.massa_seca*1000:.0f} g | "
              f"{margem.estab_min:.2f} cal")
        secoes += [f"## MARGEM EXTRA (>= {MARGEM_EXTRA_CAL} cal) — `bit07_E_margem_extra.ork`", "",
                   f"Custa **{final.alcance_medio - margem.alcance_medio:.0f} m** e "
                   f"**{(margem.massa_seca - final.massa_seca)*1000:.0f} g** a mais que o FINAL, "
                   f"e devolve **+{margem.estab_min - final.estab_min:.2f} cal** de margem "
                   "de estabilidade. Para quem acabou de perder dois foguetes numa cerca, "
                   "pode ser a troca certa.", ""] + V.descreve(margem) + [""]

    rel = B.PASTA / "RELATORIO_bit07.md"
    rel.write_text(rel.read_text(encoding="utf-8") + "\n".join(secoes) + "\n", encoding="utf-8")
    print(f"\nrelatório atualizado: {rel}")


if __name__ == "__main__":
    main()
