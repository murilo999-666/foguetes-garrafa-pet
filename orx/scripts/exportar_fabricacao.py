"""Gera arquivos de FABRICAÇÃO a partir de um .ork: STL da ogiva + molde das aletas.

Lê a geometria do próprio .ork (fonte da verdade — é o que foi simulado), então
serve para qualquer projeto do OBAFOG, não só o bit06.

Saídas:
  <nome>_coifa.stl                 peça única
  <nome>_coifa_parte1_base.stl     metade de baixo + colar de encaixe
  <nome>_coifa_parte2_ponta.stl    metade de cima
  <nome>_aleta_molde.svg / .pdf    molde 1:1 (A4) para recortar a chapa
  <nome>_aleta_molde.dxf           contorno para laser/plotter
  <nome>_aletas_Nx.dxf             N aletas aninhadas

Uso:
  python scripts/exportar_fabricacao.py "D:\\...\\bit06_B_CONSTRUTIVEL.ork" \
      --saida "D:\\1-Competicoes\\OBAFOG\\foguetes\\bit06 1,8L\\impressao" --nome bit06
"""

from __future__ import annotations

import math
import re
import struct
import sys
import zipfile
from pathlib import Path

# ----------------------------------------------------------------- geometria

def _pontos_com_raiz(caminho: Path) -> list[tuple[float, float]] | None:
    """Contorno REAL da aleta (com a raiz seguindo a superfície do corpo).

    Usa `FreeformFinSet.getFinPointsWithRoot()` do OpenRocket. Devolve None se a
    ponte com a JVM não estiver disponível — aí o chamador usa os pontos do XML.
    """
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
        from orx.bridge.jvm import ensure_jvm
        from orx.bridge.orjava import OrBridge

        ensure_jvm()
        br = OrBridge()
        doc = br.load_document(str(caminho))
        fins = br.find_component(doc, "*formato livre*")

        # getFinPointsWithRoot() traz os pontos certos mas com um fora de ordem e
        # um duplicado; remontamos o contorno de forma determinística:
        #   bordo de ataque + ponta  (dos finPoints)  +  raiz em x decrescente
        base = [(float(p.x) * 1000, float(p.y) * 1000) for p in fins.getFinPoints()]
        raiz = [(float(p.x) * 1000, float(p.y) * 1000) for p in fins.getRootPoints()]
        if len(base) < 3 or len(raiz) < 2:
            return None
        raiz = sorted(set(raiz), key=lambda p: -p[0])       # do bordo de fuga ao de ataque

        contorno = base[:-1] + raiz                          # tira o último (é o início da raiz)
        limpo: list[tuple[float, float]] = []
        for p in contorno:
            if not limpo or abs(p[0] - limpo[-1][0]) > 1e-6 or abs(p[1] - limpo[-1][1]) > 1e-6:
                limpo.append(p)
        while (len(limpo) > 2 and abs(limpo[-1][0] - limpo[0][0]) < 1e-6
               and abs(limpo[-1][1] - limpo[0][1]) < 1e-6):
            limpo.pop()
        return limpo if len(limpo) >= 3 else None
    except Exception as e:  # pragma: no cover — sem JVM, cai no XML
        print(f"  (aviso: não foi possível ler a raiz real via OpenRocket: {e})")
        print("  (o molde sairá com a raiz RETA — confira antes de cortar)")
        return None


def ler_ork(caminho: Path) -> dict:
    """Extrai ogiva e aletas do XML de dentro do .ork."""
    with zipfile.ZipFile(caminho) as z:
        nome = next(n for n in z.namelist() if n.endswith(".ork"))
        xml = z.read(nome).decode("utf-8", errors="replace")

    nose = re.search(r"<nosecone>(.*?)</nosecone>", xml, re.S)
    if not nose:
        raise SystemExit("nenhuma ogiva encontrada no .ork")
    nose = nose.group(1)

    def tag(t: str, s: str) -> str | None:
        m = re.search(rf"<{t}>([^<]+)</{t}>", s)
        return m.group(1) if m else None

    fin = re.search(r"<freeformfinset>(.*?)</freeformfinset>", xml, re.S)
    if not fin:
        raise SystemExit("nenhum conjunto de aletas de formato livre no .ork")
    fin = fin.group(1)
    pts = [(float(x) * 1000, float(y) * 1000)
           for x, y in re.findall(r'<point x="([^"]+)" y="([^"]+)"', fin)]

    mat_nose = re.search(r'<material[^>]*>([^<]+)<', nose)
    mat_fin = re.search(r'<material[^>]*>([^<]+)<', fin)

    # Os 4 pontos do XML descrevem a aleta com a raiz RETA. Quando a aleta fica
    # sobre o ombro da garrafa (ou a cavalo entre cilindro e cone), a raiz real
    # NÃO é reta: ela é plana no trecho cilíndrico e curva no cone. Cortar pelo
    # contorno reto deixa a aleta sem encostar no corpo (chega a 8 mm de vão no
    # bit07). Quem sabe a raiz de verdade é o OpenRocket — perguntamos a ele.
    pts_reais = _pontos_com_raiz(caminho)
    if pts_reais:
        pts = pts_reais

    return {
        "nose_L": float(tag("length", nose)) * 1000,
        "nose_R": float(tag("aftradius", nose)) * 1000,
        "nose_wall": float(tag("thickness", nose)) * 1000,
        "nose_shape": (tag("shape", nose) or "parabolic").lower(),
        "nose_K": float(tag("shapeparameter", nose) or 0.0),
        "nose_mat": (mat_nose.group(1) if mat_nose else "?"),
        "fin_pts": pts,
        "fin_n": int(tag("fincount", fin) or 3),
        "fin_wall": float(tag("thickness", fin)) * 1000,
        "fin_mat": (mat_fin.group(1) if mat_fin else "?"),
    }


def raio_ogiva(x: float, L: float, R: float, forma: str, K: float) -> float:
    """Raio a x da PONTA, conforme a fórmula do OpenRocket para cada forma."""
    if x <= 0:
        return 0.0
    t = min(x / L, 1.0)
    if forma == "conical":
        return R * t
    if forma == "parabolic":                      # série parabólica
        return R * (2 * t - K * t * t) / (2 - K)
    if forma == "ellipsoid":
        return R * math.sqrt(max(0.0, 1 - (1 - t) ** 2))
    if forma == "power":
        return R * (t ** max(K, 1e-6))
    if forma == "haack":
        th = math.acos(max(-1.0, min(1.0, 1 - 2 * t)))
        v = th - math.sin(2 * th) / 2 + K * math.sin(th) ** 3
        return R * math.sqrt(max(0.0, v / math.pi))
    if forma == "ogive":
        # ogiva tangente: rho = (R^2 + L^2) / (2R)
        rho = (R * R + L * L) / (2 * R)
        return math.sqrt(max(0.0, rho * rho - (L - x) ** 2)) - (rho - R)
    raise SystemExit(f"forma de ogiva não suportada: {forma}")


# ----------------------------------------------------------------- malha STL

def revolve(perfil: list[tuple[float, float]], n_ang: int = 180) -> list:
    """Revoluciona um perfil (r,z) FECHADO. Perfil limpo => malha estanque."""
    limpo: list[tuple[float, float]] = []
    for p in perfil:
        if not limpo or abs(p[0] - limpo[-1][0]) > 1e-7 or abs(p[1] - limpo[-1][1]) > 1e-7:
            limpo.append(p)
    while (len(limpo) > 1 and abs(limpo[-1][0] - limpo[0][0]) < 1e-7
           and abs(limpo[-1][1] - limpo[0][1]) < 1e-7):
        limpo.pop()

    tris = []
    m = len(limpo)
    for k in range(m):
        r1, z1 = limpo[k]
        r2, z2 = limpo[(k + 1) % m]
        for j in range(n_ang):
            a1 = 2 * math.pi * j / n_ang
            a2 = 2 * math.pi * (j + 1) / n_ang
            p1 = (r1 * math.cos(a1), r1 * math.sin(a1), z1)
            p2 = (r1 * math.cos(a2), r1 * math.sin(a2), z1)
            p3 = (r2 * math.cos(a2), r2 * math.sin(a2), z2)
            p4 = (r2 * math.cos(a1), r2 * math.sin(a1), z2)
            if r1 < 1e-9 and r2 < 1e-9:
                continue
            if r1 < 1e-9:
                tris.append((p1, p3, p4))
            elif r2 < 1e-9:
                tris.append((p1, p2, p3))
            else:
                tris.append((p1, p2, p3))
                tris.append((p1, p3, p4))
    return tris


def _vol(tris) -> float:
    v = 0.0
    for a, b, c in tris:
        v += (a[0] * (b[1] * c[2] - b[2] * c[1])
              - a[1] * (b[0] * c[2] - b[2] * c[0])
              + a[2] * (b[0] * c[1] - b[1] * c[0])) / 6.0
    return v


def grava_stl(caminho: Path, tris) -> None:
    if _vol(tris) < 0:
        tris = [(a, c, b) for a, b, c in tris]

    def normal(v1, v2, v3):
        ux, uy, uz = v2[0]-v1[0], v2[1]-v1[1], v2[2]-v1[2]
        vx, vy, vz = v3[0]-v1[0], v3[1]-v1[1], v3[2]-v1[2]
        nx, ny, nz = uy*vz-uz*vy, uz*vx-ux*vz, ux*vy-uy*vx
        mg = math.sqrt(nx*nx + ny*ny + nz*nz) or 1.0
        return nx/mg, ny/mg, nz/mg

    with caminho.open("wb") as f:
        f.write(b"\0" * 80)
        f.write(struct.pack("<I", len(tris)))
        for v1, v2, v3 in tris:
            f.write(struct.pack("<3f", *normal(v1, v2, v3)))
            for v in (v1, v2, v3):
                f.write(struct.pack("<3f", *v))
            f.write(struct.pack("<H", 0))


def checa_estanque(tris) -> tuple[bool, int]:
    from collections import defaultdict
    idx: dict[tuple, int] = {}
    arestas: dict[tuple[int, int], int] = defaultdict(int)
    degen = 0
    for tri in tris:
        ids = []
        for v in tri:
            ch = (round(v[0], 4), round(v[1], 4), round(v[2], 4))
            ids.append(idx.setdefault(ch, len(idx)))
        if len(set(ids)) < 3:
            degen += 1
            continue
        for a, b in ((ids[0], ids[1]), (ids[1], ids[2]), (ids[2], ids[0])):
            arestas[(min(a, b), max(a, b))] += 1
    return (set(arestas.values()) == {2}, degen)


def gera_coifas(g: dict, saida: Path, nome: str, corte_mm: float | None,
                colar_h: float = 20.0, folga: float = 0.35, aba: float = 2.0) -> list[Path]:
    L, R, W = g["nose_L"], g["nose_R"], g["nose_wall"]
    forma, K = g["nose_shape"], g["nose_K"]

    def r_o(z):   # z medido da BASE (0) até a ponta (L)
        return raio_ogiva(L - z, L, R, forma, K)

    def r_i(z):
        return max(r_o(z) - W, 0.0)

    def amostra(fn, z0, z1, passo=1.0):
        n = max(2, int(abs(z1 - z0) / passo) + 1)
        return [(fn(z0 + (z1 - z0) * i / (n - 1)), z0 + (z1 - z0) * i / (n - 1))
                for i in range(1, n)]

    feitos: list[Path] = []

    # ---- peça inteira ----
    def z_ponta_interna(z_ini=0.0):
        lo, hi = z_ini, L
        for _ in range(80):
            mid = 0.5 * (lo + hi)
            if r_i(mid) > 0:
                lo = mid
            else:
                hi = mid
        return 0.5 * (lo + hi)

    zit = z_ponta_interna()
    perfil = [(r_i(0.0), 0.0), (r_o(0.0), 0.0)]
    perfil += amostra(r_o, 0.0, L)
    perfil.append((0.0, zit))
    perfil += amostra(r_i, zit, 0.0)
    tris = revolve(perfil)
    p = saida / f"{nome}_coifa.stl"
    grava_stl(p, tris)
    ok, dg = checa_estanque(tris)
    print(f"  {p.name}: {len(tris)} tris | estanque={ok} degenerados={dg} | altura {L:.0f} mm")
    feitos.append(p)

    if not corte_mm:
        return feitos

    # ---- duas peças com encaixe ----
    zc = corte_mm
    zt = zc + colar_h

    def col_o(z):
        return r_i(z) - folga

    def col_i(z):
        return r_i(z) - folga - W

    pb = [(r_i(0.0), 0.0), (r_o(0.0), 0.0)]
    pb += amostra(r_o, 0.0, zc)
    pb.append((col_o(zc), zc))
    pb += amostra(col_o, zc, zt)
    pb.append((col_i(zt), zt))
    pb += amostra(col_i, zt, zc)
    pb.append((col_i(zc), zc - aba))
    pb.append((r_i(zc - aba), zc - aba))
    pb += amostra(r_i, zc - aba, 0.0)
    tb = revolve(pb)
    p1 = saida / f"{nome}_coifa_parte1_base.stl"
    grava_stl(p1, tb)
    ok1, d1 = checa_estanque(tb)
    print(f"  {p1.name}: {len(tb)} tris | estanque={ok1} degen={d1} | altura {zt:.0f} mm")

    zit2 = z_ponta_interna(zc)
    pt = [(r_i(zc), zc), (r_o(zc), zc)]
    pt += amostra(r_o, zc, L)
    pt.append((0.0, zit2))
    pt += amostra(r_i, zit2, zc)
    tt = revolve(pt)
    p2 = saida / f"{nome}_coifa_parte2_ponta.stl"
    grava_stl(p2, tt)
    ok2, d2 = checa_estanque(tt)
    print(f"  {p2.name}: {len(tt)} tris | estanque={ok2} degen={d2} | altura {L-zc:.0f} mm")
    print(f"  encaixe: colar de {colar_h:.0f} mm, folga {folga} mm em toda a volta")
    feitos += [p1, p2]
    return feitos


# ----------------------------------------------------------------- moldes 2D

def gera_moldes(g: dict, saida: Path, nome: str, titulo: str) -> list[Path]:
    PTS = g["fin_pts"]
    N = g["fin_n"]
    mat = f"{g['fin_mat'].replace('orx_', '')} {g['fin_wall']:.1f} mm".replace(".", ",")
    xs = [p[0] for p in PTS]
    ys = [p[1] for p in PTS]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    Wd, Hd = maxx - minx, maxy - miny
    arestas = [(PTS[i], PTS[(i + 1) % len(PTS)],
                math.dist(PTS[i], PTS[(i + 1) % len(PTS)])) for i in range(len(PTS))]
    # Contorno: [bordo de ataque, ponta...] + raiz. A raiz começa no índice 3 e
    # fecha no ponto 0 — vale tanto para o contorno real (muitos pontos) quanto
    # para o simplificado de 4 pontos.
    i_raiz = 3 if len(PTS) > 3 else len(PTS) - 1
    raiz_pts = PTS[i_raiz:] + [PTS[0]]
    comp_raiz = sum(math.dist(raiz_pts[i], raiz_pts[i + 1]) for i in range(len(raiz_pts) - 1))
    # rotula só as arestas que valem medida (as curtas da raiz poluiriam o desenho)
    rotular = [(a, b, d) for (a, b, d) in arestas[:i_raiz] if d >= 15.0]
    print(f"  aleta {Wd:.0f} x {Hd:.0f} mm | {N} unidades | {mat}")
    print(f"  contorno com {len(PTS)} pontos "
          f"({'raiz real seguindo o corpo' if len(PTS) > 4 else 'raiz reta'})")
    for i, (_, _, d) in enumerate(rotular):
        print(f"    aresta {i}: {d:.1f} mm")
    print(f"    raiz (desenvolvida): {comp_raiz:.1f} mm")

    M = 18.0
    A4W, A4H = 210.0, 297.0
    paisagem = Wd + 2 * M > A4W or Hd + 2 * M > A4H - 40
    PW, PH = (A4H, A4W) if paisagem else (A4W, A4H)
    feitos = []

    def X(x):
        return M + (x - minx)

    def Y(y):
        return M + (maxy - y)

    poly = " ".join(f"{X(x):.3f},{Y(y):.3f}" for x, y in PTS)
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{PW}mm" height="{PH}mm" '
         f'viewBox="0 0 {PW} {PH}">',
         f'<rect width="{PW}" height="{PH}" fill="white"/>',
         f'<polygon points="{poly}" fill="none" stroke="#000" stroke-width="0.3"/>']
    for x, y in PTS[:i_raiz + 1]:
        s.append(f'<circle cx="{X(x):.2f}" cy="{Y(y):.2f}" r="0.8" fill="#c00"/>')
    for a, b, d in rotular:
        s.append(f'<text x="{X((a[0]+b[0])/2):.2f}" y="{Y((a[1]+b[1])/2):.2f}" '
                 f'font-size="4" fill="#06c" text-anchor="middle">{d:.0f}</text>')
    # raiz destacada: a curva inteira (é ela que encosta no corpo)
    traj = " ".join(f"{X(x):.2f},{Y(y):.2f}" for x, y in raiz_pts)
    s.append(f'<polyline points="{traj}" fill="none" stroke="#0a0" '
             f'stroke-width="0.7" stroke-dasharray="3,2"/>')
    mx, my = raiz_pts[len(raiz_pts) // 2]
    s.append(f'<text x="{X(mx):.2f}" y="{Y(my)+6:.2f}" '
             f'font-size="4" fill="#0a0" text-anchor="middle">raiz - colar no corpo</text>')
    s.append(f'<text x="{M}" y="{PH-24:.1f}" font-size="6">{titulo}</text>')
    s.append(f'<text x="{M}" y="{PH-16:.1f}" font-size="4.5">{mat} - cortar {N} unidades</text>')
    sx, sy = M, PH - 9
    s.append(f'<line x1="{sx}" y1="{sy}" x2="{sx+100}" y2="{sy}" stroke="#000" stroke-width="0.4"/>')
    for t in range(0, 101, 10):
        s.append(f'<line x1="{sx+t}" y1="{sy-1.5}" x2="{sx+t}" y2="{sy+1.5}" stroke="#000" stroke-width="0.4"/>')
    s.append(f'<text x="{sx+50}" y="{sy+5}" font-size="4" text-anchor="middle">'
             f'100 mm - imprima a 100% (sem "ajustar a pagina")</text>')
    s.append('</svg>')
    p = saida / f"{nome}_aleta_molde.svg"
    p.write_text("\n".join(s), encoding="utf-8")
    feitos.append(p)

    try:
        from reportlab.lib.units import mm as MM
        from reportlab.pdfgen import canvas
        p = saida / f"{nome}_aleta_molde.pdf"
        c = canvas.Canvas(str(p), pagesize=(PW * MM, PH * MM))

        def PX(x):
            return (M + (x - minx)) * MM

        def PY(y):
            return (M + (y - miny)) * MM

        path = c.beginPath()
        path.moveTo(PX(PTS[0][0]), PY(PTS[0][1]))
        for x, y in PTS[1:]:
            path.lineTo(PX(x), PY(y))
        path.close()
        c.setLineWidth(0.85)
        c.drawPath(path, stroke=1, fill=0)
        c.setDash(3, 2); c.setStrokeColorRGB(0, 0.6, 0); c.setLineWidth(1.5)
        for i in range(len(raiz_pts) - 1):
            c.line(PX(raiz_pts[i][0]), PY(raiz_pts[i][1]),
                   PX(raiz_pts[i + 1][0]), PY(raiz_pts[i + 1][1]))
        c.setDash(); c.setStrokeColorRGB(0, 0, 0)
        c.setFont("Helvetica", 9); c.setFillColorRGB(0, 0.4, 0.8)
        for a, b, d in rotular:
            c.drawCentredString((PX(a[0]) + PX(b[0])) / 2, (PY(a[1]) + PY(b[1])) / 2, f"{d:.0f}")
        c.setFillColorRGB(0, 0, 0)
        c.setFont("Helvetica-Bold", 12); c.drawString(M * MM, 26 * MM, titulo)
        c.setFont("Helvetica", 10)
        c.drawString(M * MM, 20 * MM, f"{mat} - cortar {N} unidades identicas")
        c.setLineWidth(1); c.line(M * MM, 12 * MM, (M + 100) * MM, 12 * MM)
        for t in range(0, 101, 10):
            c.line((M + t) * MM, 10.5 * MM, (M + t) * MM, 13.5 * MM)
        c.setFont("Helvetica", 8)
        c.drawString(M * MM, 7 * MM, '100 mm - imprima a 100% (sem "ajustar a pagina")')
        c.showPage(); c.save()
        feitos.append(p)
    except Exception as e:
        print("  (PDF nao gerado:", e, ")")

    try:
        import ezdxf
        d1 = ezdxf.new("R2010"); d1.units = ezdxf.units.MM
        d1.modelspace().add_lwpolyline(PTS, close=True, dxfattribs={"layer": "CORTE"})
        p = saida / f"{nome}_aleta_molde.dxf"; d1.saveas(p); feitos.append(p)

        d2 = ezdxf.new("R2010"); d2.units = ezdxf.units.MM
        for k in range(N):
            dx = k * (Wd + 8.0)
            d2.modelspace().add_lwpolyline([(x + dx, y) for x, y in PTS], close=True,
                                           dxfattribs={"layer": "CORTE"})
        p = saida / f"{nome}_aletas_{N}x.dxf"; d2.saveas(p); feitos.append(p)
    except Exception as e:
        print("  (DXF nao gerado:", e, ")")

    return feitos


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    ork = Path(sys.argv[1])

    def opt(nome, padrao=None):
        return sys.argv[sys.argv.index(nome) + 1] if nome in sys.argv else padrao

    saida = Path(opt("--saida", str(ork.parent / "impressao")))
    nome = opt("--nome", ork.stem)
    corte = opt("--corte", None)
    saida.mkdir(parents=True, exist_ok=True)

    g = ler_ork(ork)
    print(f"lido {ork.name}")
    print(f"  ogiva: {g['nose_shape']} K={g['nose_K']:.3f} | L={g['nose_L']:.1f} mm | "
          f"Ø base {2*g['nose_R']:.1f} mm | parede {g['nose_wall']:.2f} mm | {g['nose_mat']}")

    # corta em duas se não couber numa mesa comum (Z ~ 220 mm)
    z_corte = float(corte) if corte else (g["nose_L"] / 2 if g["nose_L"] > 215 else None)
    print("\nSTL da coifa:")
    gera_coifas(g, saida, nome, z_corte)
    print("\nMolde das aletas:")
    gera_moldes(g, saida, nome, f"{nome} - molde de aleta (1:1)")
    print(f"\n>> tudo em {saida}")


if __name__ == "__main__":
    main()
