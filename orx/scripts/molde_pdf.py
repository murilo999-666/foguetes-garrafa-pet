"""Converte o molde SVG da aleta num PDF 1:1 em A4, pronto para imprimir.

Por que PDF: o navegador reescala SVG na impressão quase sempre. Um PDF com a
página declarada em A4 e o desenho em pontos PostScript (1 pt = 1/72") imprime
no tamanho certo com "escala 100% / tamanho real".

Se a peça não couber em A4 retrato, a página vira paisagem; se ainda não couber,
o desenho é dividido em várias páginas com marcas de colagem (a aleta é maior
que A4 em alguns projetos).

Uso: python scripts/molde_pdf.py <molde.svg> <saida.pdf> ["rótulo"]
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

MM = 72.0 / 25.4          # mm -> pontos PostScript
A4 = (210.0, 297.0)       # mm
MARGEM = 8.0              # mm de margem de impressão
SOBREPOSICAO = 10.0       # mm de aba de colagem entre páginas


def ler_svg(caminho: Path) -> tuple[list[tuple[float, float]], float, float, str]:
    txt = caminho.read_text(encoding="utf-8")
    pts_str = re.search(r'points="([^"]+)"', txt).group(1)
    pontos = [tuple(float(v) for v in par.split(",")) for par in pts_str.split()]
    w = float(re.search(r'width="([\d.]+)mm"', txt).group(1))
    h = float(re.search(r'height="([\d.]+)mm"', txt).group(1))
    rotulo = ""
    m = re.search(r"<text[^>]*>\s*(.*?)\s*</text>", txt, re.S)
    if m:
        rotulo = re.sub(r"\s+", " ", m.group(1)).strip()
    return pontos, w, h, rotulo


def _texto_pdf(s: str) -> str:
    return s.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def paginas_necessarias(w: float, h: float) -> tuple[float, float, int, int]:
    """Escolhe orientação e quantas páginas em x/y."""
    for pw, ph in (A4, (A4[1], A4[0])):
        util_w, util_h = pw - 2 * MARGEM, ph - 2 * MARGEM
        if w <= util_w and h <= util_h:
            return pw, ph, 1, 1
    pw, ph = A4
    util_w, util_h = pw - 2 * MARGEM - SOBREPOSICAO, ph - 2 * MARGEM - SOBREPOSICAO
    import math
    return pw, ph, math.ceil(w / util_w), math.ceil(h / util_h)


def gerar(svg: Path, pdf: Path, rotulo_extra: str = "") -> None:
    pontos, w, h, rotulo = ler_svg(svg)
    if rotulo_extra:
        rotulo = f"{rotulo_extra} — {rotulo}" if rotulo else rotulo_extra
    pw, ph, nx, ny = paginas_necessarias(w, h)
    util_w = pw - 2 * MARGEM - (SOBREPOSICAO if nx > 1 else 0)
    util_h = ph - 2 * MARGEM - (SOBREPOSICAO if ny > 1 else 0)

    conteudos: list[str] = []
    for iy in range(ny):
        for ix in range(nx):
            # deslocamento do recorte desta página, em mm (SVG tem y para baixo;
            # o PDF tem y para cima -> espelha em h)
            dx, dy = ix * util_w, iy * util_h
            ops = ["0.6 w", "0 G"]
            for i, (x, y) in enumerate(pontos):
                px = (x - dx + MARGEM) * MM
                py = ((h - y) - dy + MARGEM) * MM
                ops.append(f"{px:.2f} {py:.2f} {'m' if i == 0 else 'l'}")
            ops.append("h S")
            legenda = rotulo + (f"  [página {ix + 1},{iy + 1} de {nx}x{ny}]" if nx * ny > 1 else "")
            ops += ["BT /F1 8 Tf",
                    f"{MARGEM * MM:.2f} {(ph - MARGEM - 3) * MM:.2f} Td",
                    f"({_texto_pdf(legenda)}) Tj", "ET"]
            # régua de conferência de 100 mm: se não medir 100 mm, a escala saiu errada
            y0 = (MARGEM - 3) * MM
            ops += ["0.4 w",
                    f"{MARGEM * MM:.2f} {y0:.2f} m {(MARGEM + 100) * MM:.2f} {y0:.2f} l S",
                    f"{MARGEM * MM:.2f} {y0 - 4:.2f} m {MARGEM * MM:.2f} {y0 + 4:.2f} l S",
                    f"{(MARGEM + 100) * MM:.2f} {y0 - 4:.2f} m {(MARGEM + 100) * MM:.2f} {y0 + 4:.2f} l S",
                    "BT /F1 7 Tf",
                    f"{(MARGEM + 102) * MM:.2f} {y0 - 2:.2f} Td",
                    "(100 mm - confira com a regua) Tj", "ET"]
            conteudos.append("\n".join(ops))

    # ---- monta o PDF ----
    objs: list[str] = []
    n_pag = len(conteudos)
    fonte_id = 3 + 2 * n_pag
    kids = " ".join(f"{3 + 2 * i} 0 R" for i in range(n_pag))
    objs.append("<< /Type /Catalog /Pages 2 0 R >>")
    objs.append(f"<< /Type /Pages /Kids [{kids}] /Count {n_pag} >>")
    for i, c in enumerate(conteudos):
        objs.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {pw * MM:.2f} {ph * MM:.2f}] "
                    f"/Resources << /Font << /F1 {fonte_id} 0 R >> >> /Contents {4 + 2 * i} 0 R >>")
        objs.append(f"<< /Length {len(c.encode('latin-1', 'replace'))} >>\nstream\n{c}\nendstream")
    objs.append("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    saida = "%PDF-1.4\n"
    offsets = []
    for i, o in enumerate(objs, 1):
        offsets.append(len(saida.encode("latin-1", "replace")))
        saida += f"{i} 0 obj\n{o}\nendobj\n"
    inicio_xref = len(saida.encode("latin-1", "replace"))
    saida += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n"
    saida += "".join(f"{off:010d} 00000 n \n" for off in offsets)
    saida += (f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n"
              f"{inicio_xref}\n%%EOF\n")
    pdf.write_bytes(saida.encode("latin-1", "replace"))
    print(f"  {pdf.name}: {w:.1f} x {h:.1f} mm em {nx}x{ny} pagina(s) "
          f"{'A4 retrato' if pw < ph else 'A4 paisagem'}, escala 1:1")


if __name__ == "__main__":
    gerar(Path(sys.argv[1]), Path(sys.argv[2]),
          sys.argv[3] if len(sys.argv) > 3 else "")
