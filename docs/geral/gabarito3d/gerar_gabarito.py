"""Gera o STL do gabarito de colagem de aletas que veste no BOCAL da garrafa PET.

Conceito: uma "coroa" que desce sobre a rosca da garrafa e para no anel de
suporte (o colarinho). Como esse gargalo e' padronizado (PCO) em praticamente
toda garrafa de refrigerante, o mesmo gabarito serve 1,5 L / 2 L de qualquer
marca, descartavel ou retornavel.

Dela saem N canaletas a 120 graus (duas paredes paralelas com folga da espessura
da aleta). A aleta entra na canaleta, que garante de uma vez:
  - o angulo de 120 graus entre as aletas
  - o plano da aleta passando pelo eixo (nao sai torta / nao "cai" de lado)
  - as tres aletas iguais entre si

Tudo em milimetros. Mexa nos parametros abaixo e rode de novo para regerar.
"""

import math
import struct

# ----------------------------------------------------------------------
# PARAMETROS  (medidas tiradas do proprio bit07_MODELO_FINAL.ork)
# ----------------------------------------------------------------------
N_ALETAS      = 3       # numero de aletas (3 = padrao do projeto)
ESP_ALETA     = 1.0     # espessura da aleta em mm (poliestireno 1,0)
FOLGA_ALETA   = 0.6     # folga na canaleta p/ entrar sem forcar (+cola/tinta)

D_ROSCA       = 27.4    # diametro da rosca do bocal   (ork: r=0.0137)
D_ANEL        = 33.0    # diametro do anel de suporte  (ork: r=0.0165)
D_CORPO       = 104.0   # diametro do corpo da garrafa (ork: r=0.052)
ALT_ROSCA     = 12.0    # altura da rosca              (ork: 0.012)

FOLGA_BOCAL   = 0.7     # folga radial do furo sobre a rosca (encaixe deslizante)
FOLGA_CORPO   = 2.0     # afastamento das paredes altas em relacao ao corpo

ESP_PAREDE    = 2.5     # espessura de cada parede da canaleta
CUBO_OD       = 42.0    # diametro externo do cubo central
R_EXTERNO     = 90.0    # ate onde a canaleta vai (raio)
Z_WEB         = 18.0    # altura da parte baixa: termina onde o ombro comeca,
                        # entao ela so convive com rosca/anel/pescoco (fino)
Z_TOPO        = 70.0    # altura total das paredes altas

SAIDA_STL     = r"D:\OBAFOG\geral\gabarito3d\gabarito_aletas_bocal.stl"

# ----------------------------------------------------------------------
# derivados
# ----------------------------------------------------------------------
r_furo   = D_ROSCA / 2 + FOLGA_BOCAL          # raio do furo central
r_cubo   = CUBO_OD / 2
r_parede = D_CORPO / 2 + FOLGA_CORPO          # onde a parede alta comeca
meia_fenda = (ESP_ALETA + FOLGA_ALETA) / 2    # meia largura do vao da aleta
r_web    = 18.0                               # as paredes entram no cubo aqui

tris: list[tuple] = []


def _quad(a, b, c, d):
    tris.append((a, b, c))
    tris.append((a, c, d))


def cuboid(theta, r0, r1, z0, z1, s0, s1):
    """Caixa no referencial cilindrico: radial r, axial z, tangencial s."""
    er = (math.cos(theta), math.sin(theta), 0.0)
    et = (-math.sin(theta), math.cos(theta), 0.0)

    def P(r, z, s):
        return (r * er[0] + s * et[0], r * er[1] + s * et[1], z)

    p000, p100 = P(r0, z0, s0), P(r1, z0, s0)
    p110, p010 = P(r1, z1, s0), P(r0, z1, s0)
    p001, p101 = P(r0, z0, s1), P(r1, z0, s1)
    p111, p011 = P(r1, z1, s1), P(r0, z1, s1)
    _quad(p100, p110, p010, p000)   # face s0
    _quad(p011, p111, p101, p001)   # face s1
    _quad(p001, p101, p100, p000)   # z0
    _quad(p110, p111, p011, p010)   # z1
    _quad(p010, p011, p001, p000)   # r0
    _quad(p101, p111, p110, p100)   # r1


def anel(r_in, r_out, z0, z1, n=96):
    """Tubo anelar fechado (o cubo central que veste na rosca)."""
    for i in range(n):
        a0 = 2 * math.pi * i / n
        a1 = 2 * math.pi * (i + 1) / n
        ci, si = math.cos(a0), math.sin(a0)
        cj, sj = math.cos(a1), math.sin(a1)
        i0 = (r_in * ci, r_in * si, z0)
        i1 = (r_in * cj, r_in * sj, z0)
        i2 = (r_in * cj, r_in * sj, z1)
        i3 = (r_in * ci, r_in * si, z1)
        o0 = (r_out * ci, r_out * si, z0)
        o1 = (r_out * cj, r_out * sj, z0)
        o2 = (r_out * cj, r_out * sj, z1)
        o3 = (r_out * ci, r_out * si, z1)
        _quad(i0, i3, i2, i1)   # parede interna (normal p/ dentro)
        _quad(o0, o1, o2, o3)   # parede externa
        _quad(i0, i1, o1, o0)   # tampa de baixo
        _quad(i3, o3, o2, i2)   # tampa de cima


# ----------------------------------------------------------------------
# montagem
# ----------------------------------------------------------------------
# 1) cubo central: desce sobre a rosca e encosta no anel de suporte
anel(r_furo, r_cubo, 0.0, ALT_ROSCA)

# 2) por aleta: duas paredes paralelas formando a canaleta
for k in range(N_ALETAS):
    th = 2 * math.pi * k / N_ALETAS
    for lado in (+1, -1):
        s0 = lado * meia_fenda
        s1 = lado * (meia_fenda + ESP_PAREDE)
        sa, sb = min(s0, s1), max(s0, s1)
        # parte baixa: encosta na mesa (sem balanco na impressao) e reforca
        cuboid(th, r_web, R_EXTERNO, 0.0, Z_WEB, sa, sb)
        # parte alta: so a partir do raio que ja passou do corpo da garrafa
        cuboid(th, r_parede, R_EXTERNO, Z_WEB, Z_TOPO, sa, sb)

# ----------------------------------------------------------------------
# grava STL binario
# ----------------------------------------------------------------------
with open(SAIDA_STL, "wb") as f:
    f.write(b"\0" * 80)
    f.write(struct.pack("<I", len(tris)))
    for a, b, c in tris:
        ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
        vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
        nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
        ln = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
        f.write(struct.pack("<3f", nx / ln, ny / ln, nz / ln))
        for p in (a, b, c):
            f.write(struct.pack("<3f", *p))
        f.write(struct.pack("<H", 0))

print(f"OK  {SAIDA_STL}")
print(f"    triangulos ......... {len(tris)}")
print(f"    furo central ....... D{2*r_furo:.1f} mm  (rosca D{D_ROSCA} + {FOLGA_BOCAL} folga)")
print(f"    vao da aleta ....... {2*meia_fenda:.1f} mm  (aleta {ESP_ALETA} + {FOLGA_ALETA} folga)")
print(f"    diametro total ..... {2*R_EXTERNO:.0f} mm")
print(f"    altura total ....... {Z_TOPO:.0f} mm")
print(f"    aletas ............. {N_ALETAS} a {360/N_ALETAS:.0f} graus")
