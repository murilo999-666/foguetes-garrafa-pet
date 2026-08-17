"""Descobre a posicao axial da aleta em relacao ao BOCAL da garrafa."""
import sys
sys.path.insert(0, "src")
from orx.bridge.orjava import OrBridge

ORK = r"D:\1-Competicoes\OBAFOG\foguetes\bit07 robusto 2L\bit07_MODELO_FINAL.ork"
b = OrBridge()
doc = b.load_document(ORK)

alvo = {}
for c in b.iter_components(doc):
    alvo[str(c.getName())] = c

fin = alvo["Conjunto de aletas de formato livre"]
omb = alvo["Garrafa 2L - ombro"]

L_omb = float(omb.getLength()) * 1000
print(f"ombro: L={L_omb:.2f} mm  fore(r)={omb.getForeRadius()*1000:.2f}  aft(r)={omb.getAftRadius()*1000:.2f}")

off = float(fin.getAxialOffset()) * 1000
print(f"aleta: axialOffset={off:.2f} mm   metodo={fin.getAxialMethod()}")
print(f"aleta: comprimento(planform)={float(fin.getLength())*1000:.2f} mm")

pts = fin.getFinPoints()
print("\npontos da aleta (x ao longo da raiz, y altura) em mm:")
xs = []
for i in range(len(pts)):
    p = pts[i]
    print(f"   ({p.x*1000:8.2f}, {p.y*1000:8.2f})")
    xs.append(p.x * 1000)

# posicao do inicio da raiz medida a partir do TOPO do ombro (lado do cilindro)
try:
    front = float(fin.getAxialFront()) * 1000
    print(f"\naxialFront (do topo do ombro) = {front:.2f} mm")
except Exception as e:
    front = None
    print("\nsem getAxialFront:", e)

# converte para z medido do BOCAL:
#   bocal 0 | rosca 12 | anel 14.5 | pescoco 18.5 | ombro 18.5..73.5 | cilindro >73.5
# no ombro, x=0 fica no TOPO (r=52, z=73.5) e cresce para baixo -> z = 73.5 - x
if front is not None:
    z_ini = 73.5 - front            # inicio da raiz (x menor)
    z_fim = 73.5 - (front + max(xs))
    print(f"\nRAIZ DA ALETA em z medido do BOCAL:")
    print(f"   de z={min(z_ini, z_fim):.1f} mm  ate  z={max(z_ini, z_fim):.1f} mm")
