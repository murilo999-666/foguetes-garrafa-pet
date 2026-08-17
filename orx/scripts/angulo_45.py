"""Compara alcance a 45 graus vs. angulo atual do .ork, por motor."""
import sys, math
sys.path.insert(0, "src")
from orx.bridge.orjava import OrBridge
from orx.simulation.metrics import extract_metrics

ORK = r"D:\1-Competicoes\OBAFOG\foguetes\bit07 robusto 2L\bit07_B_maior_alcance.ork"

b = OrBridge()
doc = b.load_document(ORK)
sims = doc.getSimulations()

rows = []
for i in range(sims.size()):
    sim = sims.get(i)
    name = str(sim.getName())
    opts = sim.getOptions()
    ang0 = math.degrees(opts.getLaunchRodAngle())
    # motor da config
    fcid = sim.getFlightConfigurationId()
    mot = "-"
    for c in b.iter_components(doc):
        try:
            mc = c.getMotorConfig(fcid)
            if mc is not None and mc.getMotor() is not None:
                mot = str(mc.getMotor().getDesignation()); break
        except Exception:
            pass
    if mot == "-":
        continue  # config sem motor (Simulation 1)

    res = {}
    for tag, ang in (("atual", ang0), ("45", 45.0)):
        b.apply_sim_overrides(sim, {"launch_rod_angle_deg": ang})
        b.run_simulation(sim)
        m = extract_metrics(sim, doc)
        res[tag] = (m.horizontal_distance, m.apogee)
    rows.append((name, mot, ang0, res))
    d_at, a_at = res["atual"]; d_45, a_45 = res["45"]
    print(f"{mot:20s} ang_atual={ang0:5.1f}  atual={d_at:7.1f} m (apo {a_at:5.1f})  "
          f"45deg={d_45:7.1f} m (apo {a_45:5.1f})  delta={d_45-d_at:+6.1f} m")

print("\nOK", len(rows), "motores")
