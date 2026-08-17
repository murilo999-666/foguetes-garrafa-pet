"""Varre o angulo de lancamento em varios modelos e acha o otimo de cada um."""
import sys, math
sys.path.insert(0, "src")
from orx.bridge.orjava import OrBridge
from orx.simulation.metrics import extract_metrics

B = r"D:\1-Competicoes\OBAFOG"
MODELOS = [
    ("bit03 (PET otim.)",      B+r"\bit03\resultados_digitais\foguete_novo_PET_otimizado.ork"),
    ("bit04 MODELO_FINAL",     B+r"\bit04 2L script\bit04_MODELO_FINAL.ork"),
    ("bit04 real SEGURO 1_55L",B+r"\bit04 2L script\foguete_real\foguete_real_otimizado_SEGURO_1_55L.ork"),
    ("bit05 MODELO_FINAL",     B+r"\bit05 2L humano\bit05_MODELO_FINAL.ork"),
    ("bit06 MODELO_FINAL",     B+r"\bit06 1,8L\bit06_MODELO_FINAL.ork"),
    ("bit06 OTIMIZADO",        B+r"\bit06 1,8L\foguete_bit06_OTIMIZADO.ork"),
    ("bit07 MODELO_FINAL",     B+r"\bit07 robusto 2L\bit07_MODELO_FINAL.ork"),
    ("bit07_B (1_55L/170psi)", B+r"\bit07 robusto 2L\bit07_B_maior_alcance.ork"),
    ("foguete2 1_2L MELHOR",   B+r"\_foguete2_garantia\foguete2_1_2L_MELHOR.ork"),
    ("lab construivel MELHOR", B+r"\_laboratorio construivel\LAB_CONSTRUIVEL_MELHOR_656m.ork"),
]
ANGLES = list(range(38, 65, 2))  # 38..64
PREF_MOTOR = "1_55"  # p/ o bit07_B, escolher a config do motor 170 psi

b = OrBridge()

def sim_com_motor(doc, pref=None):
    sims = doc.getSimulations()
    cand = []
    for i in range(sims.size()):
        sim = sims.get(i)
        fcid = sim.getFlightConfigurationId()
        mot = None
        for c in b.iter_components(doc):
            try:
                mc = c.getMotorConfig(fcid)
                if mc is not None and mc.getMotor() is not None:
                    mot = str(mc.getMotor().getDesignation()); break
            except Exception:
                pass
        if mot:
            cand.append((sim, mot))
    if not cand:
        return None, None
    if pref:
        for sim, mot in cand:
            if pref in mot:
                return sim, mot
    return cand[0]

print(f"{'modelo':26s} {'motor':20s} {'ang_arq':>7s} {'d@arq':>7s} {'d@45':>7s} {'OTIMO':>6s} {'d_otim':>7s} {'ganho_vs45':>10s}")
for label, path in MODELOS:
    try:
        doc = b.load_document(path)
    except Exception as e:
        print(f"{label:26s} ERRO load: {e}"); continue
    pref = PREF_MOTOR if "bit07_B" in label else None
    sim, mot = sim_com_motor(doc, pref)
    if sim is None:
        print(f"{label:26s} (sem motor)"); continue
    ang_arq = math.degrees(sim.getOptions().getLaunchRodAngle())
    curve = {}
    for a in sorted(set(ANGLES + [round(ang_arq)])):
        b.apply_sim_overrides(sim, {"launch_rod_angle_deg": float(a)})
        b.run_simulation(sim)
        m = extract_metrics(sim, doc)
        curve[a] = m.horizontal_distance or 0.0
    best_a = max(curve, key=curve.get)
    d45 = curve.get(44) or curve.get(46) or 0.0
    # d@45 exato
    b.apply_sim_overrides(sim, {"launch_rod_angle_deg": 45.0})
    b.run_simulation(sim); d45 = extract_metrics(sim, doc).horizontal_distance or 0.0
    b.apply_sim_overrides(sim, {"launch_rod_angle_deg": ang_arq})
    b.run_simulation(sim); darq = extract_metrics(sim, doc).horizontal_distance or 0.0
    print(f"{label:26s} {mot:20s} {ang_arq:7.1f} {darq:7.1f} {d45:7.1f} {best_a:6d} {curve[best_a]:7.1f} {curve[best_a]-d45:+10.1f}")
    print("     curva:", " ".join(f"{a}:{curve[a]:.0f}" for a in sorted(curve)))
