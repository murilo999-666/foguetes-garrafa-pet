# bit06 v2 — coifa de garrafa PET + nota aerodinâmica

Gerado em 2026-08-16 22:27 | garrafa reduzida ~1,8 L (Ø9,585 cm) | **coifa de garrafa PET moldada a quente, ogival, 17–18 cm**

**8.100 simulações** (10m36s) — 50 finalistas pontuados em 4 rendimentos × 3 ventos.

## A nota, critério por critério

| critério | peso | 0 ponto em | nota cheia em | por que está aqui |
|---|---|---|---|---|
| Alcance robusto | 28 | 100 m | 280 m | é o que a OBAFOG pontua |
| Consistência | 12 | 0.70 | 0.95 | a bancada varia de um dia p/ outro |
| Leveza | 20 | 1000 g | 300 g | peso vira voo rasante quando falta empuxo |
| Estabilidade mínima | 10 | 1.0 cal | 2.0 cal | o que faltou no bit04/05 |
| Saída do trilho | 2 | 25 m/s | 40 m/s | tolera tip-off e vento |
| **Arrasto (Cd médio)** | 12 | 0.55 | 0.33 | foguete limpo continua limpo fora do script |
| **Amortecimento em arfagem** | 6 | 0.0002 | 0.0028 | faz a oscilação morrer, não só voltar |
| **Ângulo de ataque** | 4 | 6.5° | 3.5° | voar de través = cata-vento |
| **Rigidez aeroelástica** | 6 | 30 | 300 | aleta fina demais balança; o OpenRocket não vê |

Restrições duras (reprovam): estabilidade sempre entre 1.0 e 3.5 cal, saída do trilho ≥ 15.0 m/s, apogeu ≥ 30 m — em TODOS os rendimentos.

> As âncoras vêm de 140 amostras viáveis do próprio espaço de busca. As do
> bit06 v1 não serviriam: alcance com nota cheia em 340 m (ninguém passa de
> 255 com a coifa curta) e trilho com nota cheia em 25 m/s (o p05 já é 27,8).

## Ranking

| # | nota | alcance | pior η | massa | estab | Cd | AoA | amort. | rigidez |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **74.7** | 283 m | 259 m | 366 g | 1.36 | 0.351 | 4.5° | 0.0003 | 12 |
| 2 | **74.6** | 283 m | 259 m | 355 g | 1.31 | 0.348 | 4.6° | 0.0002 | 11 |
| 3 | **74.3** | 284 m | 259 m | 371 g | 1.37 | 0.350 | 4.6° | 0.0003 | 14 |
| 4 | **74.3** | 277 m | 254 m | 333 g | 1.29 | 0.353 | 4.6° | 0.0002 | 15 |
| 5 | **74.3** | 282 m | 260 m | 317 g | 1.10 | 0.334 | 4.8° | 0.0002 | 25 |
| 6 | **74.3** | 280 m | 258 m | 311 g | 1.08 | 0.336 | 4.7° | 0.0002 | 24 |
| 7 | **74.1** | 284 m | 260 m | 361 g | 1.32 | 0.347 | 4.9° | 0.0002 | 11 |
| 8 | **74.1** | 284 m | 260 m | 371 g | 1.38 | 0.350 | 4.9° | 0.0003 | 15 |
| 9 | **74.1** | 283 m | 259 m | 353 g | 1.27 | 0.347 | 4.5° | 0.0002 | 15 |
| 10 | **74.1** | 283 m | 259 m | 358 g | 1.33 | 0.349 | 4.9° | 0.0002 | 15 |
| 11 | **74.0** | 284 m | 260 m | 363 g | 1.31 | 0.348 | 4.8° | 0.0003 | 21 |
| 12 | **74.0** | 282 m | 258 m | 356 g | 1.32 | 0.349 | 4.9° | 0.0003 | 12 |
| 13 | **73.9** | 285 m | 260 m | 371 g | 1.34 | 0.349 | 4.8° | 0.0002 | 15 |
| 14 | **73.9** | 282 m | 258 m | 350 g | 1.26 | 0.349 | 4.7° | 0.0002 | 22 |
| 15 | **73.9** | 282 m | 259 m | 354 g | 1.29 | 0.348 | 5.0° | 0.0003 | 21 |

## Campeão — parâmetros de construção

| parâmetro | valor |
|---|---|
| nose_length | 17.742 |
| nose_shape | OGIVE |
| nose_shape_param | 0.925 |
| nose_thickness | 0.641 |
| nose_material | pet_garrafa |
| ballast_fill | 8.694 |
| fin_count | 3 |
| fin_root | 7.557 |
| fin_tip | 3.420 |
| fin_sweep | 11.623 |
| fin_height | 14.794 |
| fin_thickness | 0.835 |
| fin_material | polietileno |
| fin_cant | 0.000 |
| fin_position | -0.023 |
| motor | 1.35 L de vinagre (teto 171 psi) |
| launch_angle | 53.089 |

### Nota do campeão

| critério | pontos | de |
|---|---|---|
| alcance | 28.0 | 28 |
| consistencia | 10.4 | 12 |
| leveza | 18.1 | 20 |
| estabilidade | 3.6 | 10 |
| saida_trilho | 0.9 | 2 |
| arrasto | 10.8 | 12 |
| amortecimento | 0.1 | 6 |
| angulo_ataque | 2.7 | 4 |
| rigidez_aleta | 0.0 | 6 |
| **TOTAL** | **74.7** | **100** |

### Composição do arrasto do campeão

| parcela | Cd | o que é |
|---|---|---|
| atrito (pele) | 0.1319 | superfície molhada pelo ar |
| pressão (forma) | 0.2046 | nariz e ombro empurrando ar |
| base (esteira) | 0.0147 | vácuo atrás da traseira |
| **total** | **0.3512** | razão de finura 5.36 |

### Alcance por rendimento

| η | pressão | alcance |
|---|---|---|
| 0.70 | 120 psi | 259 m |
| 0.80 | 137 psi | 278 m |
| 0.90 | 154 psi | 291 m |
| 1.00 | 171 psi | 304 m |
