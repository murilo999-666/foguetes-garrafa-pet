"""Playbook de lançamento do bit04 — o que fazer no campo, com números.

Gera (em texto/CSV na pasta do bit04):
  1. SENSIBILIDADE AO LASTRO — quanto o alcance/estabilidade mudam se o Durepoxi
     ficar +-10/20/30 g dos 416 g alvo (o que o Murilo vai pesar agora).
  2. MELHOR CONFIG POR VENTO — para cada vento (0..6 m/s), qual carga de vinagre
     e qual ângulo dão o maior alcance, mantendo estabilidade >=1,0.
  3. ALCANCE ESPERADO (Monte Carlo) — sorteia vento + erros de construção reais
     e devolve a distribuição honesta (média, faixa, pior caso).

Tudo no passo fino (0.005) para números confiáveis.
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from orx.bridge.orjava import OrBridge
from orx.simulation.metrics import extract_metrics

ORK = r"D:\OBAFOG\bit04 2L script\bit04_MODELO_FINAL.ork"
MOTORES = r"D:\OBAFOG\bit04 2L script\foguete_real\motores"
SAIDA = Path(r"D:\OBAFOG\bit04 2L script")
TS = 0.005

b = OrBridge()


def simula(mods: dict, seed: int, wind: float | None = None,
           wind_dir: float | None = None, angle: float | None = None,
           ballast_g: float | None = None):
    """Carrega o .ork, aplica overrides de voo e (opcional) troca o lastro/motor."""
    doc = b.load_document(ORK)
    if ballast_g is not None:
        # ajusta a massa dos discos de lastro proporcionalmente ao alvo
        discos = [c for c in b.iter_components(doc)
                  if str(c.getName()) == "Componente de massa"]
        atual = sum(float(c.getMass()) for c in discos) * 1000
        if atual > 0:
            fator = ballast_g / atual
            for c in discos:
                c.setComponentMass(float(c.getMass()) * fator)
    sim = b.get_simulation(doc)
    if mods.get("motor"):
        b.set_motor(doc, sim, "Garrafa 2L - cilindro", f"file:{mods['motor']}")
    ov = {"random_seed": seed, "time_step": TS}
    if wind is not None:
        ov["wind_speed_average"] = wind
    if wind_dir is not None:
        ov["wind_direction_deg"] = wind_dir
    if angle is not None:
        ov["launch_rod_angle_deg"] = angle
    b.apply_sim_overrides(sim, ov)
    b.run_simulation(sim)
    return extract_metrics(sim, doc)


def bloco(titulo):
    return f"\n{'='*66}\n{titulo}\n{'='*66}"


def main():
    linhas = ["PLAYBOOK DE LANÇAMENTO — bit04 (3 aletas, sem cant)",
              "gerado automaticamente | alcance no passo fino 0.005",
              "lastro alvo: 416 g de Durepoxi | motor base: VinagreReal-1_8L"]

    # ---------- 1. sensibilidade ao lastro ----------
    linhas.append(bloco("1. SENSIBILIDADE AO LASTRO (quão preciso pesar o Durepoxi)"))
    linhas.append(f"{'lastro':>8} {'alcance(20 ventos)':>20} {'estab.pós-queima':>18}")
    base_motor = f"{MOTORES}\\VinagreReal-1_8L.eng"
    for g in (386, 406, 416, 426, 446):
        ds, est = [], None
        for s in range(101, 116):
            m = simula({"motor": base_motor}, s, ballast_g=float(g))
            if m.horizontal_distance:
                ds.append(m.horizontal_distance)
                est = m.stability_max
        a = np.array(ds)
        flag = "" if (est or 0) >= 1.0 else "  <-- INSTAVEL (<1,0)"
        marca = "  <== ALVO" if g == 416 else ""
        linhas.append(f"{g:>6}g {a.mean():>17.1f}m {est or 0:>16.2f}cal{flag}{marca}")
    linhas.append("\nLeitura: se a linha do seu peso real ainda estiver >=1,0 cal e o")
    linhas.append("alcance mudar pouco, você tem folga. Pese o mais perto de 416 g que der.")

    # ---------- 2. melhor config por vento ----------
    linhas.append(bloco("2. MELHOR CONFIG POR VENTO (qual vinagre + ângulo usar no dia)"))
    linhas.append(f"{'vento':>6} {'melhor vinagre':>16} {'ângulo':>8} {'alcance':>9}")
    motores = {"1.0L": "VinagreReal-1_0L", "1.2L": "VinagreReal-1_2L",
               "1.4L": "VinagreReal-1_4L", "1.55L": "VinagreReal-1_55L",
               "1.8L": "VinagreReal-1_8L"}
    for vento in (0, 2, 4, 6):
        melhor = (-1, None, None)
        for nome, mot in motores.items():
            for ang in (45, 50, 52, 55):
                ds = []
                for s in (101, 105, 110):
                    m = simula({"motor": f"{MOTORES}\\{mot}.eng"}, s,
                               wind=float(vento), angle=float(ang))
                    if m.horizontal_distance and (m.stability_max or 0) >= 1.0:
                        ds.append(m.horizontal_distance)
                if ds and np.mean(ds) > melhor[0]:
                    melhor = (float(np.mean(ds)), nome, ang)
        if melhor[1]:
            linhas.append(f"{vento:>4}m/s {melhor[1]:>16} {melhor[2]:>6}° {melhor[0]:>7.0f}m")

    # ---------- 3. Monte Carlo realista ----------
    linhas.append(bloco("3. ALCANCE ESPERADO NO DIA (Monte Carlo: vento + erros de montagem)"))
    rng = np.random.default_rng(2026)
    amostras = []
    for _ in range(120):
        vento = float(abs(rng.normal(2.0, 1.5)))           # vento típico
        wdir = float(rng.uniform(0, 360))                  # direção qualquer
        ang = float(rng.normal(52, 2))                     # erro de mira ~2°
        lastro = float(rng.normal(416, 12))                # erro de pesagem ~12 g
        m = simula({"motor": base_motor}, int(rng.integers(1, 9999)),
                   wind=vento, wind_dir=wdir, angle=ang, ballast_g=lastro)
        if m.horizontal_distance and (m.stability_max or 0) >= 1.0:
            amostras.append(m.horizontal_distance)
    a = np.array(amostras)
    linhas.append(f"amostras válidas: {len(a)}/120")
    if len(a):
        linhas.append(f"  alcance esperado: {a.mean():.0f} m")
        linhas.append(f"  faixa provável (80%): {np.percentile(a,10):.0f} a {np.percentile(a,90):.0f} m")
        linhas.append(f"  pior caso observado: {a.min():.0f} m | melhor: {a.max():.0f} m")
    linhas.append("\nEste é o número honesto para apostar: não os 380 m de laboratório")
    linhas.append("(vento fixo ideal), e sim a faixa acima, que já inclui vento real e")
    linhas.append("os errinhos normais de construção.")

    txt = "\n".join(linhas)
    (SAIDA / "PLAYBOOK_lancamento.txt").write_text(txt, encoding="utf-8")
    print(txt)
    print(f"\n>>> salvo em {SAIDA / 'PLAYBOOK_lancamento.txt'}")


if __name__ == "__main__":
    main()
