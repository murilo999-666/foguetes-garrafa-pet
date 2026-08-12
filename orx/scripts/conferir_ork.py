"""Confere um .ork componente a componente: dimensões, material, densidade e massa.

Uso: python scripts/conferir_ork.py <arquivo.ork> [...]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from orx.bridge.orjava import OrBridge

# densidades de referência (kg/m3) para checagem
ESPERADO = {
    "pla": 1250.0, "orx_pla": 1250.0,
    "poliestireno": 1050.0, "orx_poliestireno": 1050.0,
    "pet_garrafa": 1380.0, "orx_pet_garrafa": 1380.0,
    "papel_cartao": 680.0, "orx_papel_cartao": 680.0,
}


def conferir(caminho: str) -> None:
    b = OrBridge()
    doc = b.load_document(caminho)
    print(f"\n{'='*96}\n{Path(caminho).name}  —  {doc.getRocket().getName()}\n{'='*96}")
    print(f"{'componente':34s} {'tipo':22s} {'dim':>10s} {'material':20s} {'ρ':>6s} {'massa':>8s}")
    print("-" * 96)
    total = 0.0
    for c in b.iter_components(doc):
        nome = str(c.getName())
        tipo = str(c.getComponentName())
        massa = float(c.getMass())
        total += massa
        try:
            mat = str(c.getMaterial().getName())
            rho = float(c.getMaterial().getDensity())
            rho_s = f"{rho:.0f}"
            aviso = ""
            chave = mat.lower().replace("orx_", "")
            if chave in ESPERADO and abs(rho - ESPERADO[chave]) > 1:
                aviso = f"  <-- esperado {ESPERADO[chave]:.0f}"
        except Exception:
            mat, rho_s, aviso = "-", "-", ""
        try:
            dim = f"{float(c.getLength())*100:.1f}cm"
        except Exception:
            dim = "-"
        extra = ""
        try:
            extra = f" esp={float(c.getThickness())*1000:.2f}mm"
        except Exception:
            pass
        print(f"{nome:34s} {tipo:22s} {dim:>10s} {mat:20s} {rho_s:>6s} {massa*1000:7.1f}g{extra}{aviso}")
    print("-" * 96)
    print(f"{'MASSA VAZIA TOTAL':34s} {'':22s} {'':>10s} {'':20s} {'':>6s} {total*1000:7.1f}g")
    print(f"comprimento total: {float(doc.getRocket().getLength())*100:.1f} cm")


if __name__ == "__main__":
    for arq in sys.argv[1:]:
        conferir(arq)
