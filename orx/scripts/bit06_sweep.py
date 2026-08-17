import sys, math
sys.path.insert(0, "src")
from orx.bridge.orjava import OrBridge
from orx.simulation.metrics import extract_metrics
b = OrBridge()
path = r"D:\1-Competicoes\OBAFOG\foguetes\bit06 1,8L\foguete_bit06_OTIMIZADO.ork"
eng = r"D:\1-Competicoes\OBAFOG\foguetes\bit06 1,8L\motores\VinagreBit06-1_5L.eng"
doc = b.load_document(path)
mount = None
for c in b.iter_components(doc):
    try:
        if c.isMotorMount():
            mount = str(c.getName()); break
    except Exception:
        pass
print("mount:", mount)
sim = b.get_simulation(doc, None)
b.set_motor(doc, sim, mount, f"file:{eng}")
curve = {}
for a in list(range(38, 65, 2)):
    b.apply_sim_overrides(sim, {"launch_rod_angle_deg": float(a), "wind_speed_average": 2.0, "launch_rod_length": 1.0})
    b.run_simulation(sim)
    curve[a] = extract_metrics(sim, doc).horizontal_distance or 0.0
best = max(curve, key=curve.get)
d45 = curve[44]
print(f"bit06 OTIMIZADO (VinagreBit06-1_5L)  OTIMO={best}deg d={curve[best]:.1f}  d@45={d45:.1f}  ganho={curve[best]-d45:+.1f}")
print("curva:", " ".join(f"{a}:{curve[a]:.0f}" for a in sorted(curve)))
