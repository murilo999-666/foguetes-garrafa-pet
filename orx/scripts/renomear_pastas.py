"""Renomeia as pastas dos foguetes com descritores e atualiza TODAS as
referências (configs .yaml, scripts .py e o índice).

Convenção: "bitNN <garrafa> <origem>"
  script = projeto saído do otimizador | humano = projeto por pesquisa humana
  real   = foguete que efetivamente voou
"""

import re
import sys
from pathlib import Path

OBAFOG = Path(r"D:\OBAFOG")
PROJ = Path(__file__).parent.parent

# antigo -> novo
RENOMES = {
    "bit01": "bit01 ogivas",
    "bit02": "bit02 ogivas",
    "bit03": "bit03 2L real",
    "bit04": "bit04 2L script",
    "bit05": "bit05 2L humano",
    "bit06": "bit06 1,8L script",
    "bit07": "bit07 reservado",
    "bit08": "bit08 reservado",
}


def renomear_pastas() -> None:
    for antigo, novo in RENOMES.items():
        origem, destino = OBAFOG / antigo, OBAFOG / novo
        if destino.exists():
            print(f"  = {novo} (já existe)")
            continue
        if not origem.exists():
            print(f"  ! {antigo} não encontrado")
            continue
        origem.rename(destino)
        print(f"  {antigo}  ->  {novo}")


def atualizar_referencias() -> int:
    """Troca OBAFOG\\bitNN por OBAFOG\\<novo nome> em configs e scripts."""
    alvos = list((PROJ / "config").glob("*.yaml")) + list((PROJ / "scripts").glob("*.py"))
    alvos += [OBAFOG / "_INDICE.md"]
    n_arquivos = 0
    for arq in alvos:
        if not arq.exists() or arq.name == Path(__file__).name:
            continue
        texto = original = arq.read_text(encoding="utf-8")
        for antigo, novo in RENOMES.items():
            # caminhos com 1 barra (escalares YAML, strings python raw)
            texto = texto.replace(f"OBAFOG\\{antigo}", f"OBAFOG\\{novo}")
            # caminhos com 2 barras (strings YAML entre aspas)
            texto = texto.replace(f"OBAFOG\\\\{antigo}", f"OBAFOG\\\\{novo}")
            # caminhos em markdown / barras normais
            texto = texto.replace(f"OBAFOG/{antigo}", f"OBAFOG/{novo}")
            texto = re.sub(rf"`{antigo}/`", f"`{novo}/`", texto)
        if texto != original:
            arq.write_text(texto, encoding="utf-8")
            print(f"  atualizado: {arq.relative_to(PROJ) if PROJ in arq.parents else arq.name}")
            n_arquivos += 1
    return n_arquivos


def main() -> int:
    print("Renomeando pastas:")
    renomear_pastas()
    print("\nAtualizando referências:")
    n = atualizar_referencias()
    print(f"\n{n} arquivos atualizados")
    return 0


if __name__ == "__main__":
    sys.exit(main())
