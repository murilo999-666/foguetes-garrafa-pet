"""Gabarito "COPO" de colagem de aletas — veste ao longo da garrafa PET.

Como prende
-----------
O copo NAO encosta na rosca: ele comeca logo acima do anel de suporte e para
sozinho pela CUNHA DO OMBRO. O perfil interno e' uma copia do ombro real da
garrafa com 0,5 mm de folga, entao ele so entra ate a posicao certa — subir
mais que ~0,3 mm ja trava (conferido no fim do arquivo).

Isso deixa a rosca inteira livre: a tampa rosqueia normalmente, pegando 100 %
do fio. E o furo minimo (D35) passa folgado pelo anel de suporte (D33) na hora
de vestir e de tirar.

As 3 fendas a 120 graus sao abertas EM CIMA. A aleta entra pela fenda e encosta
na garrafa; a fenda garante o angulo de 120 graus e o plano da aleta passando
pelo eixo. Depois da cola secar, o copo sai PARA BAIXO (pelo bocal) e as aletas
saem pelas fendas.

O STL ja sai NA POSICAO DE IMPRESSAO: boca grande na mesa (maior area de
contato) e nenhuma face em 90 graus — a parede mais deitada da 57 graus da
vertical, que com 3 mm de espessura imprime sem suporte.

Medidas em mm. Internamente z = 0 e' o bocal, crescendo para dentro da garrafa;
a rotacao para impressao e' aplicada so na hora de gravar.
"""

import math
import struct
import sys

# ----------------------------------------------------------------------
# PARAMETROS
# ----------------------------------------------------------------------
# numero de aletas: pode passar na linha de comando -> "python gerar_copo.py 4"
N_ALETAS     = int(sys.argv[1]) if len(sys.argv) > 1 else 3
ESP_ALETA    = 1.0    # espessura da aleta (poliestireno 1,0 mm)
FOLGA_ALETA  = 0.6    # folga da fenda (entra sem forcar, sobra p/ cola)

ALTURA       = 100.0  # altura total da peca ("uns 10 cm")
ESP_PAREDE   = 3.0    # espessura da parede

D_ANEL       = 33.0   # anel de suporte da garrafa (ork: r=0.0165)
FOLGA_ANEL   = 1.0    # folga p/ passar pelo anel ao vestir/tirar
D_CORPO      = 104.0  # cilindro da garrafa        (ork: r=0.052)
FOLGA_OMBRO  = 0.5    # folga radial no ombro e no cilindro

Z_INICIO     = 14.5   # onde o copo comeca (topo do anel) -> rosca toda livre
Z_FENDA      = 24.0   # onde as fendas comecam (raiz da aleta so comeca em 25,4)
D_BASE       = 48.0   # diametro externo do anel macico da base (rigidez)

SAIDA = rf"D:\OBAFOG\geral\gabarito3d\gabarito_copo_{N_ALETAS}aletas.stl"

# Perfil REAL do ombro, amostrado do .ork (z do bocal, raio) -----------
OMBRO = [
    (18.50, 12.45), (20.46, 15.84), (22.43, 18.88), (24.39, 21.64),
    (26.36, 24.17), (28.32, 26.50), (30.29, 28.66), (32.25, 30.67),
    (34.21, 32.54), (36.18, 34.28), (38.14, 35.92), (40.11, 37.45),
    (42.07, 38.88), (44.04, 40.22), (46.00, 41.48), (47.96, 42.66),
    (49.93, 43.76), (51.89, 44.78), (53.86, 45.74), (55.82, 46.64),
    (57.79, 47.47), (59.75, 48.23), (61.71, 48.94), (63.68, 49.59),
    (65.64, 50.18), (67.61, 50.71), (69.57, 51.20), (71.54, 51.62),
    (73.50, 52.00),
]

# ----------------------------------------------------------------------
h_fenda    = (ESP_ALETA + FOLGA_ALETA) / 2.0
r_min_bore = D_ANEL / 2 + FOLGA_ANEL       # nunca menor: precisa passar o anel
r_cil      = D_CORPO / 2 + FOLGA_OMBRO
r_base     = D_BASE / 2
Z_TOPO     = Z_INICIO + ALTURA


def r_garrafa(z):
    if z <= OMBRO[0][0]:
        return OMBRO[0][1]
    if z >= OMBRO[-1][0]:
        return OMBRO[-1][1]
    for (z0, r0), (z1, r1) in zip(OMBRO, OMBRO[1:]):
        if z0 <= z <= z1:
            return r0 + (z - z0) / (z1 - z0) * (r1 - r0)
    return OMBRO[-1][1]


def raio_interno(z):
    return max(r_min_bore, min(r_cil, r_garrafa(z) + FOLGA_OMBRO))


def raio_externo(z):
    return max(raio_interno(z) + ESP_PAREDE, r_base if z <= Z_FENDA else 0.0)


tris = []


def tri(a, b, c):
    tris.append((a, b, c))


def quad(a, b, c, d):
    tri(a, b, c)
    tri(a, c, d)


def revolucao(zs, n=128):
    """Anel macico de revolucao (a base que segura os dedos)."""
    for z0, z1 in zip(zs, zs[1:]):
        i0, o0 = raio_interno(z0), raio_externo(z0)
        i1, o1 = raio_interno(z1), raio_externo(z1)
        for k in range(n):
            a0 = 2 * math.pi * k / n
            a1 = 2 * math.pi * (k + 1) / n
            c0, s0 = math.cos(a0), math.sin(a0)
            c1, s1 = math.cos(a1), math.sin(a1)
            quad((o0 * c0, o0 * s0, z0), (o0 * c1, o0 * s1, z0),
                 (o1 * c1, o1 * s1, z1), (o1 * c0, o1 * s0, z1))
            quad((i0 * c0, i0 * s0, z0), (i1 * c0, i1 * s0, z1),
                 (i1 * c1, i1 * s1, z1), (i0 * c1, i0 * s1, z0))
    for z, sinal in ((zs[0], -1), (zs[-1], +1)):
        ri, ro = raio_interno(z), raio_externo(z)
        for k in range(n):
            a0 = 2 * math.pi * k / n
            a1 = 2 * math.pi * (k + 1) / n
            c0, s0 = math.cos(a0), math.sin(a0)
            c1, s1 = math.cos(a1), math.sin(a1)
            if sinal < 0:
                quad((ri * c0, ri * s0, z), (ri * c1, ri * s1, z),
                     (ro * c1, ro * s1, z), (ro * c0, ro * s0, z))
            else:
                quad((ri * c0, ri * s0, z), (ro * c0, ro * s0, z),
                     (ro * c1, ro * s1, z), (ri * c1, ri * s1, z))


def dedo(theta_a, theta_b, zs, m=20):
    """Um dedo do copo. As faces da fenda sao PLANOS afastados h_fenda do plano
    radial — e' isso que da fenda de largura constante, e nao setor angular."""
    era = (math.cos(theta_a), math.sin(theta_a), 0.0)
    eta = (-math.sin(theta_a), math.cos(theta_a), 0.0)
    erb = (math.cos(theta_b), math.sin(theta_b), 0.0)
    etb = (-math.sin(theta_b), math.cos(theta_b), 0.0)

    def face_a(r, z):
        u = math.sqrt(max(r * r - h_fenda * h_fenda, 0.0))
        return (u * era[0] + h_fenda * eta[0], u * era[1] + h_fenda * eta[1], z)

    def face_b(r, z):
        u = math.sqrt(max(r * r - h_fenda * h_fenda, 0.0))
        return (u * erb[0] - h_fenda * etb[0], u * erb[1] - h_fenda * etb[1], z)

    def arco(r, z, j):
        a0 = theta_a + math.asin(min(1.0, h_fenda / r))
        a1 = theta_b - math.asin(min(1.0, h_fenda / r))
        a = a0 + (a1 - a0) * j / m
        return (r * math.cos(a), r * math.sin(a), z)

    for z0, z1 in zip(zs, zs[1:]):
        i0, o0 = raio_interno(z0), raio_externo(z0)
        i1, o1 = raio_interno(z1), raio_externo(z1)
        for j in range(m):
            quad(arco(o0, z0, j), arco(o0, z0, j + 1),
                 arco(o1, z1, j + 1), arco(o1, z1, j))
            quad(arco(i0, z0, j), arco(i1, z1, j),
                 arco(i1, z1, j + 1), arco(i0, z0, j + 1))
        quad(face_a(i0, z0), face_a(o0, z0), face_a(o1, z1), face_a(i1, z1))
        quad(face_b(i0, z0), face_b(i1, z1), face_b(o1, z1), face_b(o0, z0))

    for z, sinal in ((zs[0], -1), (zs[-1], +1)):
        ri, ro = raio_interno(z), raio_externo(z)
        for j in range(m):
            if sinal < 0:
                quad(arco(ri, z, j), arco(ri, z, j + 1),
                     arco(ro, z, j + 1), arco(ro, z, j))
            else:
                quad(arco(ri, z, j), arco(ro, z, j),
                     arco(ro, z, j + 1), arco(ri, z, j + 1))


def estacoes(z0, z1, passo=1.0):
    zs, z = [z0], z0
    while z < z1 - 1e-9:
        z = min(z + passo, z1)
        zs.append(z)
    return zs


# ----------------------------------------------------------------------
# montagem
# ----------------------------------------------------------------------
revolucao(estacoes(Z_INICIO, Z_FENDA))          # anel macico da base
passo = 2 * math.pi / N_ALETAS
for k in range(N_ALETAS):
    dedo(k * passo, (k + 1) * passo, estacoes(Z_FENDA, Z_TOPO))

# ----------------------------------------------------------------------
# rotacao 180 graus em X -> boca grande na mesa (rotacao propria: nao inverte
# as normais, ao contrario de espelhar em z)
# ----------------------------------------------------------------------
def p_impressao(p):
    return (p[0], -p[1], Z_TOPO - p[2])


tris = [(p_impressao(a), p_impressao(b), p_impressao(c)) for a, b, c in tris]

with open(SAIDA, "wb") as f:
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

print(f"OK  {SAIDA}")
print(f"    triangulos ........ {len(tris)}")
print(f"    peca .............. z={Z_INICIO} ate {Z_TOPO} mm do bocal ({ALTURA:.0f} mm)")
print(f"    rosca livre ....... 0 a 12 mm -> a tampa pega 100% do fio")
print(f"    furo minimo ....... D{2*r_min_bore:.1f} mm (passa pelo anel D{D_ANEL})")
print(f"    D externo base .... D{2*r_base:.1f} mm   topo D{2*raio_externo(Z_TOPO):.1f} mm")
print(f"    fendas ............ {N_ALETAS} de {2*h_fenda:.1f} mm a {360/N_ALETAS:.0f} graus, "
      f"de z={Z_FENDA} ao topo")
