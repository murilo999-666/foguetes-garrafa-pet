"""Gabarito de ALINHAMENTO de aletas — placas que vestem na garrafa.

Reproduz o padrão do gabarito_aletas.dxf que a equipe já usa (placas de
260 × 260 mm, cantos arredondados r10, furos de fixação Ø9 nos cantos, furo
central que encaixa no ombro da garrafa e fendas radiais de 1 mm), mas com
**3 fendas a 120°** em vez de 4 a 90°.

São 3 placas com furos de Ø90, Ø77 e Ø64 — os mesmos três diâmetros do
gabarito original, que correspondem a três alturas do ombro cônico da garrafa
(que afunila de Ø104 para Ø24,9 em 55 mm). Usando as três empilhadas, a aleta
fica guiada em três pontos e cola reta.

Saída: DXF R14 em milímetros, pronto para corte a laser.
"""

import math
import sys
from pathlib import Path

# ---- parâmetros (todos em mm) ----
PLACA = 260.0          # lado da placa quadrada
RAIO_CANTO = 10.0      # arredondamento dos cantos
FURO_FIX = 9.0         # diâmetro dos furos de fixação nos cantos
INSET_FURO = 10.0      # distância do furo à borda
FENDA_LARG = 1.0       # largura da fenda = espessura da aleta (o kerf do laser
                       # abre ~0,1-0,2 mm, dando o encaixe justo)
FENDA_ATE = 115.0      # raio até onde a fenda vai (deixa 15 mm de borda)
ALIVIO = 4.0           # raio do alívio de cola no encontro fenda x furo central
                       # (semicírculo: a metade interna já está dentro do furo)
DIAMETROS = [90.0, 77.0, 64.0]   # furos centrais (3 alturas do ombro)
N_ALETAS = 3
FOLGA_PLACAS = 20.0    # espaço entre placas na chapa


def _cab(maxx, maxy):
    return ["999", "gabarito de alinhamento de 3 aletas - gerado pelo orx",
            "0", "SECTION", "2", "HEADER",
            "9", "$ACADVER", "1", "AC1014",
            "9", "$INSUNITS", "70", "4",
            "9", "$EXTMIN", "10", "0.0", "20", "0.0", "30", "0.0",
            "9", "$EXTMAX", "10", f"{maxx:.3f}", "20", f"{maxy:.3f}", "30", "0.0",
            "0", "ENDSEC",
            "0", "SECTION", "2", "TABLES",
            "0", "TABLE", "2", "LAYER", "70", "1",
            "0", "LAYER", "2", "CORTE", "70", "0", "62", "1", "6", "CONTINUOUS",
            "0", "ENDTAB", "0", "ENDSEC",
            "0", "SECTION", "2", "ENTITIES"]


def _linha(x1, y1, x2, y2, cam="CORTE"):
    return ["0", "LINE", "8", cam, "10", f"{x1:.4f}", "20", f"{y1:.4f}", "30", "0.0",
            "11", f"{x2:.4f}", "21", f"{y2:.4f}", "31", "0.0"]


def _circulo(cx, cy, d, cam="CORTE"):
    return ["0", "CIRCLE", "8", cam, "10", f"{cx:.4f}", "20", f"{cy:.4f}", "30", "0.0",
            "40", f"{d/2:.4f}"]


def _arco(cx, cy, r, a1, a2, cam="CORTE"):
    return ["0", "ARC", "8", cam, "10", f"{cx:.4f}", "20", f"{cy:.4f}", "30", "0.0",
            "40", f"{r:.4f}", "50", f"{a1:.3f}", "51", f"{a2:.3f}"]


def _texto(x, y, h, txt, cam="TEXTO"):
    return ["0", "TEXT", "8", cam, "10", f"{x:.3f}", "20", f"{y:.3f}", "30", "0.0",
            "40", f"{h:.2f}", "1", txt]


def _placa(ox, oy, diam_furo):
    """Uma placa completa com origem no canto inferior esquerdo."""
    e = []
    L, r = PLACA, RAIO_CANTO
    # contorno com cantos arredondados
    e += _linha(ox + r, oy, ox + L - r, oy)
    e += _linha(ox + L, oy + r, ox + L, oy + L - r)
    e += _linha(ox + L - r, oy + L, ox + r, oy + L)
    e += _linha(ox, oy + L - r, ox, oy + r)
    e += _arco(ox + r, oy + r, r, 180, 270)
    e += _arco(ox + L - r, oy + r, r, 270, 360)
    e += _arco(ox + L - r, oy + L - r, r, 0, 90)
    e += _arco(ox + r, oy + L - r, r, 90, 180)
    # furos de fixação nos cantos
    for fx, fy in [(INSET_FURO, INSET_FURO), (L - INSET_FURO, INSET_FURO),
                   (L - INSET_FURO, L - INSET_FURO), (INSET_FURO, L - INSET_FURO)]:
        e += _circulo(ox + fx, oy + fy, FURO_FIX)
    # furo central (encaixa na garrafa)
    cx, cy = ox + L / 2, oy + L / 2
    e += _circulo(cx, cy, diam_furo)
    # 3 fendas radiais a 120 graus, cada uma com alívio de cola na raiz
    r_furo = diam_furo / 2
    r_int = r_furo - 2.0                 # entra 2 mm no furo p/ unir bem
    meia = FENDA_LARG / 2
    for k in range(N_ALETAS):
        graus = 90 + k * 360.0 / N_ALETAS
        ang = math.radians(graus)
        ux, uy = math.cos(ang), math.sin(ang)        # direção radial (p/ fora)
        px, py = -uy, ux                              # perpendicular
        ax, ay = cx + ux * r_int, cy + uy * r_int     # início (dentro do furo)
        bx, by = cx + ux * FENDA_ATE, cy + uy * FENDA_ATE   # fim
        e += _linha(ax + px * meia, ay + py * meia, bx + px * meia, by + py * meia)
        e += _linha(ax - px * meia, ay - py * meia, bx - px * meia, by - py * meia)
        e += _linha(bx + px * meia, by + py * meia, bx - px * meia, by - py * meia)
        # alívio: semicírculo com centro no encontro fenda x furo central,
        # voltado para FORA (a metade interna já é o próprio furo)
        jx, jy = cx + ux * r_furo, cy + uy * r_furo
        e += _arco(jx, jy, ALIVIO, graus - 90, graus + 90)
    return e


def gerar(saida: Path):
    # layout 2x2 usando 3 quadrantes (mesmo tamanho de chapa do gabarito antigo)
    passo = PLACA + FOLGA_PLACAS
    posicoes = [(0, passo), (passo, passo), (0, 0)]
    ents = []
    for (ox, oy), d in zip(posicoes, DIAMETROS):
        ents += _placa(ox, oy, d)
    maxx, maxy = passo + PLACA, passo + PLACA
    conteudo = _cab(maxx, maxy) + ents + ["0", "ENDSEC", "0", "EOF"]
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text("\n".join(conteudo) + "\n", encoding="ascii")
    print(f"  {saida.name}: 3 placas de {PLACA:.0f}x{PLACA:.0f}mm "
          f"(furos D{'/D'.join(f'{d:.0f}' for d in DIAMETROS)}), "
          f"3 fendas de {FENDA_LARG}mm a 120 graus")
    print(f"  chapa necessaria: {maxx:.0f} x {maxy:.0f} mm")


if __name__ == "__main__":
    gerar(Path(sys.argv[1] if len(sys.argv) > 1 else "gabarito_3aletas.dxf"))
