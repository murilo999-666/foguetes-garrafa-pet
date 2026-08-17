"""Amostra o perfil real (raio x posicao) da garrafa do .ork, do bocal pra cima."""
import sys
sys.path.insert(0, "src")
from orx.bridge.orjava import OrBridge

ORK = r"D:\1-Competicoes\OBAFOG\foguetes\bit07 robusto 2L\bit07_MODELO_FINAL.ork"
b = OrBridge()
doc = b.load_document(ORK)

comps = []
for c in b.iter_components(doc):
    nome = str(c.getName())
    try:
        L = float(c.getLength())
    except Exception:
        continue
    comps.append((nome, L, c))

print("componentes (ordem do arquivo):")
for nome, L, c in comps:
    print(f"  {nome:34s} L={L*1000:7.2f} mm  {type(c).__name__}")

print()
alvo = None
for nome, L, c in comps:
    if "ombro" in nome.lower():
        alvo = (nome, L, c)
if alvo is None:
    raise SystemExit("ombro nao encontrado")

nome, L, c = alvo
print(f"PERFIL DO OMBRO '{nome}'  (L={L*1000:.2f} mm)")
print(f"  fore={c.getForeRadius()*1000:.2f} mm  aft={c.getAftRadius()*1000:.2f} mm")
print("  x_do_topo_do_ombro[mm]   raio[mm]   diametro[mm]")
N = 28
for i in range(N + 1):
    x = L * i / N
    r = float(c.getRadius(x))
    print(f"    {x*1000:8.2f}            {r*1000:7.2f}     {2*r*1000:7.2f}")
