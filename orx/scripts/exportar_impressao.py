"""Exporta coifa (ogiva) e aletas de um .ork em arquivos prontos para impressão 3D.

- A ogiva é exportada SEM os componentes filhos (os discos de lastro de Durepoxi
  são filhos dela e apareceriam no modelo 3D).
- Gera .obj (do OpenRocket) e .stl binário (padrão para fatiadores).
- A coifa sai EM PÉ: o eixo longo vira Z, a ponta para cima e a base apoiada
  em Z=0, pronta para fatiar sem precisar girar.
- As aletas saem deitadas no plano da mesa (Z=0), que é como se imprime chapa.

Uso: python scripts/exportar_impressao.py <arquivo.ork> <pasta_saida> [prefixo]
"""

import struct
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from orx.bridge.orjava import J, OrBridge


# ---------------------------------------------------------------- OBJ / STL

def ler_obj(caminho: Path) -> tuple[np.ndarray, list[tuple[int, int, int]]]:
    """Lê vértices e faces trianguladas de um .obj."""
    verts, faces = [], []
    for linha in caminho.read_text(encoding="utf-8", errors="ignore").splitlines():
        if linha.startswith("v "):
            _, x, y, z = linha.split()[:4]
            verts.append((float(x), float(y), float(z)))
        elif linha.startswith("f "):
            idx = [int(p.split("/")[0]) for p in linha.split()[1:]]
            idx = [i - 1 if i > 0 else len(verts) + i for i in idx]
            for k in range(1, len(idx) - 1):        # fan-triangulation
                faces.append((idx[0], idx[k], idx[k + 1]))
    return np.array(verts, dtype=float), faces


def escrever_stl(caminho: Path, verts: np.ndarray, faces: list, nome: str) -> None:
    """STL binário."""
    with open(caminho, "wb") as f:
        f.write(nome.encode("ascii", "ignore")[:80].ljust(80, b"\0"))
        f.write(struct.pack("<I", len(faces)))
        for a, b_, c in faces:
            p0, p1, p2 = verts[a], verts[b_], verts[c]
            n = np.cross(p1 - p0, p2 - p0)
            ln = np.linalg.norm(n)
            n = n / ln if ln > 1e-12 else np.zeros(3)
            f.write(struct.pack("<3f", *n))
            for p in (p0, p1, p2):
                f.write(struct.pack("<3f", *p))
            f.write(struct.pack("<H", 0))


def por_em_pe(verts: np.ndarray, comprimento_mm: float | None = None) -> np.ndarray:
    """Gira para o eixo do foguete virar Z, com a PONTA para cima e base em Z=0.

    O eixo do foguete é identificado pela extensão que casa com o comprimento
    REAL da peça (uma coifa pode ser mais larga que alta — o eixo não é
    necessariamente a maior dimensão). A ponta é o extremo de menor raio.
    """
    v = verts - verts.mean(axis=0)
    extensoes = v.max(axis=0) - v.min(axis=0)
    if comprimento_mm:
        eixo = int(np.argmin(np.abs(extensoes - comprimento_mm)))
    else:
        eixo = int(np.argmax(extensoes))
    ordem = [i for i in range(3) if i != eixo] + [eixo]       # eixo do foguete -> Z
    v = v[:, ordem]

    # qual extremo é a ponta? o de menor raio no plano XY
    z = v[:, 2]
    lim = (z.max() - z.min()) * 0.12
    raio_topo = np.linalg.norm(v[z > z.max() - lim, :2], axis=1).mean()
    raio_base = np.linalg.norm(v[z < z.min() + lim, :2], axis=1).mean()
    if raio_topo > raio_base:            # ponta está embaixo -> inverte
        v[:, 2] = -v[:, 2]
    v[:, 2] -= v[:, 2].min()             # base apoiada em Z=0
    v[:, 0] -= v[:, 0].mean()
    v[:, 1] -= v[:, 1].mean()
    return v


def deitar(verts: np.ndarray) -> np.ndarray:
    """Deita a peça no plano da mesa: menor dimensão vira a espessura (Z)."""
    v = verts - verts.mean(axis=0)
    esp = int(np.argmin(v.max(axis=0) - v.min(axis=0)))
    ordem = [i for i in range(3) if i != esp] + [esp]
    v = v[:, ordem]
    v[:, 2] -= v[:, 2].min()
    return v


# ---------------------------------------------------------------- exportação

def exportar_componente(bridge: OrBridge, doc, componente, destino: Path,
                        exportar_filhos: bool) -> None:
    ArrayList = J("java.util.ArrayList")
    File = J("java.io.File")
    OBJExportOptions = J("info.openrocket.core.file.wavefrontobj.export.OBJExportOptions")
    OBJExporterFactory = J("info.openrocket.core.file.wavefrontobj.export.OBJExporterFactory")
    WarningSet = J("info.openrocket.core.logging.WarningSet")
    LOD = J("info.openrocket.core.file.wavefrontobj.ObjUtils$LevelOfDetail")
    TriMethod = J("info.openrocket.core.file.wavefrontobj.ObjUtils$TriangulationMethod")

    rocket = doc.getRocket()
    opts = OBJExportOptions(rocket)
    opts.setExportChildren(exportar_filhos)   # <- tira os discos de lastro da ogiva
    opts.setExportAppearance(False)
    opts.setExportMotors(False)
    opts.setExportAsSeparateFiles(False)
    opts.setRemoveOffset(True)
    opts.setTriangulate(True)
    opts.setTriangulationMethod(TriMethod.DELAUNAY)   # obrigatório junto com setTriangulate
    opts.setExportAllInstances(False)   # UMA aleta, plana — imprima 3 cópias
    opts.setLOD(LOD.HIGH_QUALITY)
    opts.setScalingDouble(1000.0)             # metros -> milímetros

    lista = ArrayList()
    lista.add(componente)
    config = rocket.getSelectedConfiguration()
    for metodo in (TriMethod.DELAUNAY, TriMethod.SIMPLE):
        opts.setTriangulationMethod(metodo)
        try:
            OBJExporterFactory(lista, config, File(str(destino)), opts, WarningSet()).doExport()
            return
        except Exception:
            continue          # geometria difícil: tenta o método mais simples
    raise RuntimeError(f"falha ao exportar {componente.getName()}")


def main() -> None:
    ork = Path(sys.argv[1])
    saida = Path(sys.argv[2])
    prefixo = sys.argv[3] if len(sys.argv) > 3 else ork.stem
    saida.mkdir(parents=True, exist_ok=True)

    b = OrBridge()
    doc = b.load_document(str(ork))

    alvos = []
    for c in b.iter_components(doc):
        tipo = str(c.getComponentName()).lower()
        if "ogiva" in tipo or "nose" in tipo:
                alvos.append(("coifa", c, False, por_em_pe))  # sem filhos (lastro!)
        elif "aleta" in tipo or "fin" in tipo:
            alvos.append(("aletas", c, True, deitar))

    for rotulo, comp, filhos, orientar in alvos:
        comp_mm = float(comp.getLength()) * 1000.0
        obj_bruto = saida / f"{prefixo}_{rotulo}_bruto.obj"
        exportar_componente(b, doc, comp, obj_bruto, filhos)
        verts, faces = ler_obj(obj_bruto)
        if not len(verts):
            print(f"  ! {rotulo}: exportação vazia")
            continue
        verts = orientar(verts, comp_mm) if rotulo == "coifa" else orientar(verts)
        stl = saida / f"{prefixo}_{rotulo}.stl"
        escrever_stl(stl, verts, faces, f"{prefixo} {rotulo}")
        obj_bruto.unlink()          # mantém só o STL final
        dims = verts.max(axis=0) - verts.min(axis=0)
        print(f"  {stl.name:44s} {len(faces):6d} triangulos  "
              f"{dims[0]:.1f} x {dims[1]:.1f} x {dims[2]:.1f} mm")
        if rotulo == "aletas":
            exportar_molde_aleta(b, comp, saida / f"{prefixo}_aleta_molde.svg",
                                 f"{prefixo} aleta")




def exportar_molde_aleta(bridge: OrBridge, componente, destino: Path, rotulo: str) -> None:
    """Gera o molde 2D da aleta em SVG, escala 1:1 (mm), para cortar a chapa
    de poliestireno. Usa os pontos reais do planform do OpenRocket."""
    pts = [(float(p.x) * 1000, float(p.y) * 1000) for p in componente.getFinPoints()]
    if len(pts) < 3:
        return
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    larg, alt = max(xs) - min(xs), max(ys) - min(ys)
    m = 10  # margem mm
    # y invertido: SVG cresce para baixo
    caminho = " ".join(f"{x - min(xs) + m:.2f},{max(ys) - y + m:.2f}" for x, y in pts)
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{larg + 2*m}mm" height="{alt + 2*m}mm"
     viewBox="0 0 {larg + 2*m:.2f} {alt + 2*m:.2f}">
  <polygon points="{caminho}" fill="none" stroke="#000" stroke-width="0.3"/>
  <text x="{m}" y="{alt + 2*m - 2:.2f}" font-family="sans-serif" font-size="4">
    {rotulo} — {larg:.1f} x {alt:.1f} mm — escala 1:1, imprima SEM ajuste de página
  </text>
</svg>'''
    destino.write_text(svg, encoding="utf-8")
    print(f"  {destino.name:44s} molde 2D  {larg:.1f} x {alt:.1f} mm")

if __name__ == "__main__":
    main()
