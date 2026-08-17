"""Compara o foguete CONSTRUÍDO com o que a campanha grande encontrou.

Pergunta que isto responde: a busca de 99 mil simulações achou algo melhor do que
o que o Murilo já montou? Se sim, quanto — e vale para o PRÓXIMO foguete, não
para o de hoje (o de hoje já está colado).

Tudo é medido com a MESMA régua (mesmos rendimentos, mesmos ventos, mesma nota),
que é a única forma de a comparação significar alguma coisa.
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
from orx.simulation.runner import Runner

import bit06_pet_aero as B
import bit06_pet_variantes as V

PASTA = Path(r"D:\1-Competicoes\OBAFOG\foguetes\bit06 1,8L")
ENTREGUE = PASTA / "_ENTREGUE_16ago_2245"


def main() -> None:
    cfg = load_config(B.CONFIG)
    runner = Runner(dataclasses.replace(cfg, batch=BatchConfig(workers=1)))

    # o que foi construído
    ent = json.loads((ENTREGUE / "variantes_pet.json").read_text(encoding="utf-8"))
    d_construido = [x for x in ent if x["tag"] == "B_CONSTRUTIVEL"][0]["design"]
    d_construido["motor"] = B.normaliza_motor(d_construido["motor"])

    # o que a campanha grande achou
    rank = json.loads((PASTA / "simulacoes" / "rank_bit06_pet_aero.json").read_text(encoding="utf-8"))
    d_novo = rank[0]["design"]
    d_novo["motor"] = B.normaliza_motor(d_novo["motor"])
    d_novo_c = V.construtivel(d_novo, 1.0)      # em polietileno 1 mm, como se constrói

    casos = [
        ("CONSTRUIDO (hoje)", d_construido),
        ("campanha 99k — campeão", d_novo),
        ("campanha 99k — construtível", d_novo_c),
    ]

    print(f"{'versão':30s} {'nota':>6s} {'alcance':>8s} {'seca':>7s} {'estab':>7s} "
          f"{'Cd':>6s} {'rig':>5s} {'AoA':>5s}")
    print("-" * 82)
    res = []
    for nome, d in casos:
        a = B.avalia_completo(runner, d)
        if a.motivo_descarte:
            print(f"{nome:30s} REPROVOU: {a.motivo_descarte}")
            res.append((nome, d, None))
            continue
        print(f"{nome:30s} {a.nota:6.1f} {a.alcance_medio:7.0f}m {a.massa_seca*1000:6.0f}g "
              f"{a.estab_min:7.2f} {a.cd_medio:6.3f} {a.rigidez:5.0f} {a.aoa_max:5.1f}")
        res.append((nome, d, a))

    base = res[0][2]
    print()
    if base is None:
        print("não foi possível avaliar o construído")
        return
    for nome, d, a in res[1:]:
        if a is None:
            continue
        dn, dm, de = a.nota - base.nota, a.alcance_medio - base.alcance_medio, \
            a.estab_min - base.estab_min
        print(f"{nome} vs construído: nota {dn:+.1f} | alcance {dm:+.0f} m | "
              f"estabilidade {de:+.2f} cal | massa {(a.massa_seca-base.massa_seca)*1000:+.0f} g")

    (PASTA / "simulacoes" / "comparacao_final.json").write_text(
        json.dumps([{"versao": n, "design": d,
                     "avaliacao": (dataclasses.asdict(a) if a else None)}
                    for n, d, a in res], indent=1, ensure_ascii=False, default=str),
        encoding="utf-8")
    print(f"\n>> {PASTA / 'simulacoes' / 'comparacao_final.json'}")


if __name__ == "__main__":
    main()
