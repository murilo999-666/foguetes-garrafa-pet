import sys, math
sys.path.insert(0,"src")
from orx.bridge.orjava import OrBridge
from orx.simulation.metrics import extract_metrics
b=OrBridge()
for path in [r"D:\OBAFOG\bit03\resultados_digitais\foguete_novo_PET_otimizado.ork",
             r"D:\OBAFOG\bit07 robusto 2L\bit07_MODELO_FINAL.ork"]:
    doc=b.load_document(path); rocket=doc.getRocket()
    print("###",path.split("\\")[-1])
    ids=rocket.getIds()  # flight config ids
    print("  rocket configs:", ids.size() if hasattr(ids,'size') else len(list(ids)))
    sims=doc.getSimulations()
    for i in range(sims.size()):
        s=sims.get(i); fcid=s.getFlightConfigurationId()
        b.apply_sim_overrides(s,{"launch_rod_angle_deg":50.0})
        try:
            b.run_simulation(s); d=extract_metrics(s,doc).horizontal_distance
        except Exception as e:
            d=f"ERR {e}"
        print(f"  sim{i} '{s.getName()}' d50={d}")
