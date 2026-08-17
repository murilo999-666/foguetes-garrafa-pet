# bit07_B — coifa PLA + aletas polietileno (arquivos de impressão)

Gerado a partir de `bit07_B_maior_alcance.ork`. Troquei **a coifa para PLA (impressão 3D)**
e **as aletas para polietileno de 1,0 mm**, gerei os arquivos de fabricação e comparei
as simulações antes/depois.

## Arquivos nesta pasta

| Arquivo | O que é | Como usar |
|---|---|---|
| `bit07_B_coifa_PLA.stl` | Coifa inteira (292 mm), parede 1,2 mm | Fatiar e imprimir em PLA (precisa Z ≥ 300 mm) |
| `bit07_B_coifa_PLA_parte1_base.stl` | **Metade de baixo** + colar de encaixe | Imprimir base na mesa (166 mm de altura) |
| `bit07_B_coifa_PLA_parte2_ponta.stl` | **Metade de cima** (ponta) | Imprimir rim na mesa (146 mm de altura) |
| `bit07_B_aleta_molde.pdf` | Molde 1:1 da aleta (A4) | **Imprimir a 100%**, colar na chapa e recortar |
| `bit07_B_aleta_molde.svg` | Mesmo molde em vetor | Abrir no navegador/Inkscape p/ imprimir ou cortar |
| `bit07_B_aleta_molde.dxf` | Contorno de 1 aleta | Corte a laser / plotter de recorte (Silhouette/Cricut) |
| `bit07_B_aletas_4x.dxf` | 4 aletas aninhadas | Corte a laser da chapa inteira de uma vez |
| `comparacao.csv` / `.json` | Simulações antes × depois | Planilha / dados brutos |
| `../../bit07_B_PLA_polietileno.ork` | O foguete já com os materiais novos | Abrir no OpenRocket |

## Coifa (STL) — impressão 3D

- **Forma**: série parabólica (K = 0,7056), fiel ao `.ork`.
- **Dimensões**: altura **292 mm**, Ø base **104 mm**, parede **1,2 mm**, ponta maciça nos primeiros ~4 mm.
- **Orientação**: já sai com a **base na mesa (Z=0) e a ponta pra cima** — é só carregar no slicer.
- **Malha**: sólida e estanque (*watertight/manifold* verificado — 216 mil triângulos).
- **Material**: PLA (densidade 1250 kg/m³ na simulação).

### Versão inteira × versão em 2 partes
- `bit07_B_coifa_PLA.stl` = peça única de **292 mm** (só cabe em Z ≥ 300 mm).
- **Recomendado**: as duas metades `parte1_base` (166 mm) + `parte2_ponta` (146 mm),
  que cabem em qualquer mesa FDM comum.

### Como montar as 2 partes (junta de encaixe)
- A **parte1 (base)** tem um **colar interno** que sobe 20 mm; a **parte2 (ponta)**
  encaixa por cima e desliza sobre esse colar.
- **Folga de 0,35 mm** em toda a volta → entra justinho sem forçar. Se sua impressora
  tende a "engordar" as peças, líme/lixe leve o colar; se ficar frouxo, é só a cola preencher.
- A metade de cima **apoia** no ombro da metade de baixo (batente natural) — não tem como
  afundar demais. Passe cola (cianoacrilato ou epóxi) no colar antes de encaixar.
- Ambas as metades saem **estanques (watertight/manifold)** e já orientadas pra impressão
  (base/rim na mesa, ponta pra cima) — é só carregar no slicer.

### Sugestão de fatiamento
- Parede: 3 perímetros (≈1,2 mm, casa com a espessura do modelo).
- Preenchimento: 5–10 % (ou modo vaso, se sua peça não precisar do rebordo).
- Suportes: não precisa (a ponta é maciça e a base é aberta).
- Camada: 0,2–0,28 mm. Sem balanço crítico.

## Aletas (molde) — recorte de polietileno 1,0 mm

- São **4 aletas idênticas**. Geometria (do `.ork`): bordo de ataque **201 mm**,
  ponta **11 mm**, bordo de fuga **197 mm**, raiz **84,7 mm**; peça cabe em **150 × 183 mm** (A4).
- **Imprima o PDF a 100% / "tamanho real"** (desligue "ajustar à página"). Confira na
  régua a **barra de 100 mm** impressa no rodapé antes de cortar.
- A **linha verde tracejada** é a **raiz** (aresta que cola no corpo do foguete).
- Fluxo manual: imprime → cola/fita o papel na chapa → recorta com estilete → repete 4×
  (ou imprime 4 cópias). Para laser/plotter, use os `.dxf`.

## Comparação de voo — materiais originais × novos

Rodei **as 8 simulações embutidas no arquivo** (cargas de vinagre de 0,6 a 1,8 L),
frescas, com os materiais antigos (papel-cartão) e depois com os novos (PLA + polietileno).
Tudo o mais idêntico (motor, ângulo 57,9°, vento 2 m/s).

- **Massa seca**: 423 g → **499 g** (+76 g). Peso de decolagem 2,33 → 2,41 kg.
- **Estabilidade mínima**: praticamente igual, levemente melhor (CG foi um tico à frente).
- **Velocidade de saída do trilho**: cai ~1–3 m/s (segue bem acima do mínimo seguro).

| Sim (carga vinagre) | Alcance ANTES (m) | Alcance DEPOIS (m) | delta (m) | Apogeu a/d (m) | v.saída a/d (m/s) | Estab.mín a/d (cal) |
|---|---|---|---|---|---|---|
| #2 (1,8 L) | 326.2 | 325.5 | -0.7 | 78.8 / 75.2 | 34.4 / 33.0 | 1.35 / 1.38 |
| #3 (1,7 L) | 323.7 | 322.9 | -0.8 | 78.1 / 74.7 | 34.0 / 35.2 | 1.37 / 1.43 |
| #4 (1,55 L) | 314.9 | 312.3 | -2.6 | 75.8 / 71.8 | 36.9 / 35.1 | 1.44 / 1.47 |
| #5 (1,4 L) | 303.9 | 299.3 | -4.6 | 72.5 / 68.2 | 37.9 / 36.1 | 1.50 / 1.53 |
| #6 (1,2 L) | 285.6 | 278.8 | -6.8 | 66.8 / 62.2 | 38.9 / 36.7 | 1.59 / 1.62 |
| #7 (1,0 L) | 256.2 | 246.7 | -9.5 | 58.1 / 53.2 | 39.6 / 37.1 | 1.72 / 1.74 |
| #8 (0,8 L) | 215.9 | 203.1 | -12.8 | 46.8 / 41.8 | 40.7 / 37.6 | 1.92 / 1.92 |
| #9 (0,6 L) | 161.9 | 146.6 | -15.3 | 32.7 / 28.3 | 37.7 / 36.4 | 2.13 / 2.16 |

**Leitura**: com carga alta (o cenário de maior alcance, 1,55–1,8 L) a troca custa
**menos de 3 m** — praticamente de graça, e você ganha uma coifa e aletas de verdade,
mais robustas e reproduzíveis. O peso extra pesa mais nas cargas pequenas (voos curtos),
onde o alcance é menor de qualquer jeito. A estabilidade não piora em nenhum caso.

### Premissas (ajuste se quiser)
- PLA = **1250 kg/m³**, parede **1,2 mm**.
- Polietileno = **950 kg/m³** (HDPE em chapa), espessura **1,0 mm**.
- Se sua chapa for LDPE (~920) ou o PLA for impresso com pouco preenchimento, a massa real
  fica **menor** que a simulada — ou seja, o alcance real tende a ser **igual ou melhor** que
  a coluna "DEPOIS". Me diga a densidade/preenchimento reais e eu refino.
