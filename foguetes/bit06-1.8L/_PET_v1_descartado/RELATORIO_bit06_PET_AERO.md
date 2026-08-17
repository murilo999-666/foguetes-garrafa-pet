# bit06 v2 — coifa de garrafa PET + nota aerodinâmica

Gerado em 2026-08-16 21:15 | garrafa reduzida ~1,8 L (Ø9,585 cm) | **coifa de garrafa PET moldada a quente, ogival, 17–18 cm**

**40.720 simulações** (9m12s) — 60 finalistas pontuados em 4 rendimentos × 3 ventos.

## A nota, critério por critério

| critério | peso | 0 ponto em | nota cheia em | por que está aqui |
|---|---|---|---|---|
| Alcance robusto | 30 | 100 m | 280 m | é o que a OBAFOG pontua |
| Consistência | 15 | 0.70 | 0.95 | a bancada varia de um dia p/ outro |
| Leveza | 10 | 1000 g | 300 g | peso vira voo rasante quando falta empuxo |
| Estabilidade mínima | 10 | 1.0 cal | 2.0 cal | o que faltou no bit04/05 |
| Saída do trilho | 5 | 25 m/s | 40 m/s | tolera tip-off e vento |
| **Arrasto (Cd médio)** | 12 | 0.55 | 0.33 | foguete limpo continua limpo fora do script |
| **Amortecimento em arfagem** | 8 | 0.0002 | 0.0028 | faz a oscilação morrer, não só voltar |
| **Ângulo de ataque** | 5 | 6.5° | 3.5° | voar de través = cata-vento |
| **Rigidez aeroelástica** | 5 | 30 | 300 | aleta fina demais balança; o OpenRocket não vê |

Restrições duras (reprovam): estabilidade sempre entre 1.0 e 3.5 cal, saída do trilho ≥ 15.0 m/s, apogeu ≥ 30 m — em TODOS os rendimentos.

> As âncoras vêm de 140 amostras viáveis do próprio espaço de busca. As do
> bit06 v1 não serviriam: alcance com nota cheia em 340 m (ninguém passa de
> 255 com a coifa curta) e trilho com nota cheia em 25 m/s (o p05 já é 27,8).

## Ranking

| # | nota | alcance | pior η | massa | estab | Cd | AoA | amort. | rigidez |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **73.8** | 282 m | 256 m | 381 g | 1.52 | 0.353 | 4.4° | 0.0005 | 17 |
| 2 | **72.7** | 283 m | 260 m | 335 g | 1.23 | 0.340 | 4.4° | 0.0004 | 26 |
| 3 | **72.6** | 284 m | 261 m | 338 g | 1.21 | 0.338 | 4.3° | 0.0003 | 27 |
| 4 | **72.6** | 283 m | 258 m | 375 g | 1.39 | 0.352 | 4.5° | 0.0004 | 19 |
| 5 | **72.5** | 284 m | 260 m | 359 g | 1.36 | 0.348 | 4.5° | 0.0002 | 18 |
| 6 | **72.4** | 288 m | 261 m | 383 g | 1.30 | 0.338 | 4.0° | 0.0003 | 23 |
| 7 | **72.4** | 284 m | 261 m | 330 g | 1.19 | 0.335 | 4.4° | 0.0003 | 24 |
| 8 | **72.4** | 286 m | 261 m | 342 g | 1.19 | 0.336 | 4.0° | 0.0003 | 28 |
| 9 | **72.4** | 283 m | 259 m | 365 g | 1.39 | 0.349 | 5.0° | 0.0005 | 17 |
| 10 | **72.4** | 286 m | 261 m | 382 g | 1.39 | 0.348 | 4.7° | 0.0004 | 17 |
| 11 | **72.3** | 284 m | 259 m | 369 g | 1.40 | 0.351 | 4.8° | 0.0004 | 15 |
| 12 | **72.3** | 285 m | 259 m | 375 g | 1.37 | 0.350 | 4.6° | 0.0004 | 18 |
| 13 | **72.3** | 293 m | 263 m | 445 g | 1.55 | 0.342 | 4.8° | 0.0005 | 17 |
| 14 | **72.2** | 286 m | 260 m | 366 g | 1.27 | 0.340 | 4.0° | 0.0002 | 20 |
| 15 | **72.2** | 283 m | 257 m | 382 g | 1.42 | 0.355 | 4.7° | 0.0004 | 19 |

## Campeão — parâmetros de construção

| parâmetro | valor |
|---|---|
| nose_length | 17.004 |
| nose_shape | OGIVE |
| nose_shape_param | 0.788 |
| nose_thickness | 0.503 |
| nose_material | pet_garrafa |
| ballast_fill | 9.520 |
| fin_count | 4 |
| fin_root | 7.596 |
| fin_tip | 0.000 |
| fin_sweep | 14.000 |
| fin_height | 10.818 |
| fin_thickness | 0.845 |
| fin_material | papel_cartao |
| fin_cant | -1.993 |
| fin_position | 0.000 |
| motor | 1.35 L de vinagre (teto 171 psi) |
| launch_angle | 57.797 |

### Nota do campeão

| critério | pontos | de |
|---|---|---|
| alcance | 30.0 | 30 |
| consistencia | 12.6 | 15 |
| leveza | 8.8 | 10 |
| estabilidade | 5.2 | 10 |
| saida_trilho | 2.2 | 5 |
| arrasto | 10.7 | 12 |
| amortecimento | 0.8 | 8 |
| angulo_ataque | 3.4 | 5 |
| rigidez_aleta | 0.0 | 5 |
| **TOTAL** | **73.8** | **100** |

### Composição do arrasto do campeão

| parcela | Cd | o que é |
|---|---|---|
| atrito (pele) | 0.1353 | superfície molhada pelo ar |
| pressão (forma) | 0.2033 | nariz e ombro empurrando ar |
| base (esteira) | 0.0148 | vácuo atrás da traseira |
| **total** | **0.3534** | razão de finura 5.59 |

### Alcance por rendimento

| η | pressão | alcance |
|---|---|---|
| 0.70 | 120 psi | 256 m |
| 0.80 | 137 psi | 276 m |
| 0.90 | 154 psi | 291 m |
| 1.00 | 171 psi | 304 m |
