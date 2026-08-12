"""Gera gabarito DXF de aletas pronto para corte a laser.

Formato: DXF AC1014 (R14), unidades em MILÍMETROS (INSUNITS=4) — o mesmo do
gabarito_aletas.dxf que a equipe já usa, então a cortadora aceita direto.

Cada aleta é uma LWPOLYLINE fechada (contorno de corte). As peças são dispostas
lado a lado com folga, e a chapa é desenhada como retângulo de referência.

Uso: python scripts/gabarito_dxf.py <arquivo.ork> <saida.dxf> [n_aletas]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from orx.bridge.orjava import OrBridge

FOLGA = 8.0        # mm entre peças
MARGEM = 10.0      # mm de borda da chapa


def _cab(minx, miny, maxx, maxy) -> list[str]:
    return [
        "999", "gabarito de aletas gerado pelo orx",
        "0", "SECTION", "2", "HEADER",
        "9", "$ACADVER", "1", "AC1014",
        "9", "$INSUNITS", "70", "4",          # 4 = milimetros
        "9", "$EXTMIN", "10", f"{minx:.3f}", "20", f"{miny:.3f}", "30", "0.0",
        "9", "$EXTMAX", "10", f"{maxx:.3f}", "20", f"{maxy:.3f}", "30", "0.0",
        "0", "ENDSEC",
        "0", "SECTION", "2", "TABLES",
        "0", "TABLE", "2", "LAYER", "70", "2",
        "0", "LAYER", "2", "CORTE", "70", "0", "62", "1", "6", "CONTINUOUS",
        "0", "LAYER", "2", "REFERENCIA", "70", "0", "62", "8", "6", "CONTINUOUS",
        "0", "ENDTAB", "0", "ENDSEC",
        "0", "SECTION", "2", "ENTITIES",
    ]


def _polilinha(pontos, camada="CORTE") -> list[str]:
    saida = ["0", "LWPOLYLINE", "8", camada, "100", "AcDbEntity",
             "100", "AcDbPolyline", "90", str(len(pontos)), "70", "1"]
    for x, y in pontos:
        saida += ["10", f"{x:.4f}", "20", f"{y:.4f}"]
    return saida


def _texto(x, y, altura, texto, camada="REFERENCIA") -> list[str]:
    return ["0", "TEXT", "8", camada, "10", f"{x:.3f}", "20", f"{y:.3f}",
            "30", "0.0", "40", f"{altura:.2f}", "1", texto]


def gerar(ork: str, saida: Path, n_aletas: int = 3) -> None:
    b = OrBridge()
    doc = b.load_document(ork)
    fins = b.find_component(doc, "Conjunto de aletas de formato livre")
    pts = [(float(p.x) * 1000, float(p.y) * 1000) for p in fins.getFinPoints()]
    esp = float(fins.getThickness()) * 1000

    # normaliza para o primeiro quadrante
    mx, my = min(x for x, _ in pts), min(y for _, y in pts)
    base = [(x - mx, y - my) for x, y in pts]
    larg = max(x for x, _ in base)
    alt = max(y for _, y in base)

    linhas = []
    for i in range(n_aletas):
        dx = MARGEM + i * (larg + FOLGA)
        linhas += _polilinha([(x + dx, y + MARGEM) for x, y in base])
        linhas += _texto(dx + 3, MARGEM + 3, 5.0, f"{i+1}")

    chapa_l = MARGEM * 2 + n_aletas * larg + (n_aletas - 1) * FOLGA
    chapa_a = MARGEM * 2 + alt
    linhas += _polilinha([(0, 0), (chapa_l, 0), (chapa_l, chapa_a), (0, chapa_a)],
                         camada="REFERENCIA")
    linhas += _texto(MARGEM, chapa_a - 7, 4.0,
                     f"{n_aletas} aletas - chapa {esp:.1f}mm - "
                     f"peca {larg:.1f}x{alt:.1f}mm - ESCALA 1:1 - unidades mm")

    conteudo = _cab(0, 0, chapa_l, chapa_a) + linhas + ["0", "ENDSEC", "0", "EOF"]
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text("\n".join(conteudo) + "\n", encoding="ascii")
    print(f"  {saida.name}: {n_aletas} aletas de {larg:.1f} x {alt:.1f} mm "
          f"| chapa {esp:.1f} mm | area minima {chapa_l:.0f} x {chapa_a:.0f} mm")


if __name__ == "__main__":
    gerar(sys.argv[1], Path(sys.argv[2]), int(sys.argv[3]) if len(sys.argv) > 3 else 3)
