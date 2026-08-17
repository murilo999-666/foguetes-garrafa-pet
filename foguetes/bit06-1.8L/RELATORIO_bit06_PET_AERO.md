# bit06 v2 — coifa de garrafa PET + nota aerodinâmica

Gerado em 2026-08-17 03:17 | garrafa reduzida ~1,8 L (Ø9,585 cm) | **coifa de garrafa PET moldada a quente, ogival, 17–18 cm**

**99.920 simulações** (6m48s) — 60 finalistas pontuados em 4 rendimentos × 3 ventos.

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
| 1 | **75.4** | 282 m | 259 m | 323 g | 1.21 | 0.338 | 4.3° | 0.0002 | 17 |
| 2 | **75.4** | 285 m | 262 m | 321 g | 1.13 | 0.330 | 4.0° | 0.0002 | 22 |
| 3 | **75.3** | 286 m | 260 m | 357 g | 1.29 | 0.337 | 3.9° | 0.0002 | 15 |
| 4 | **75.3** | 283 m | 259 m | 339 g | 1.25 | 0.337 | 4.2° | 0.0002 | 15 |
| 5 | **75.3** | 285 m | 261 m | 338 g | 1.23 | 0.335 | 4.2° | 0.0002 | 15 |
| 6 | **75.3** | 284 m | 260 m | 339 g | 1.25 | 0.336 | 4.2° | 0.0002 | 16 |
| 7 | **75.3** | 284 m | 261 m | 325 g | 1.21 | 0.334 | 4.6° | 0.0002 | 15 |
| 8 | **75.2** | 284 m | 261 m | 329 g | 1.19 | 0.334 | 4.2° | 0.0002 | 20 |
| 9 | **75.2** | 284 m | 261 m | 327 g | 1.19 | 0.335 | 4.3° | 0.0002 | 20 |
| 10 | **75.2** | 284 m | 259 m | 349 g | 1.27 | 0.336 | 4.0° | 0.0002 | 15 |
| 11 | **75.2** | 285 m | 262 m | 326 g | 1.17 | 0.333 | 4.3° | 0.0002 | 20 |
| 12 | **75.2** | 286 m | 263 m | 334 g | 1.23 | 0.335 | 4.6° | 0.0002 | 15 |
| 13 | **75.2** | 285 m | 261 m | 330 g | 1.18 | 0.333 | 4.2° | 0.0002 | 21 |
| 14 | **75.1** | 287 m | 262 m | 356 g | 1.28 | 0.338 | 4.1° | 0.0002 | 16 |
| 15 | **75.1** | 286 m | 262 m | 338 g | 1.22 | 0.335 | 4.2° | 0.0002 | 15 |

## Campeão — parâmetros de construção

| parâmetro | valor |
|---|---|
| nose_length | 17.118 |
| nose_shape | OGIVE |
| nose_shape_param | 0.878 |
| nose_thickness | 0.467 |
| nose_material | pet_garrafa |
| ballast_fill | 8.277 |
| fin_count | 3 |
| fin_root | 7.505 |
| fin_tip | 3.097 |
| fin_sweep | 11.903 |
| fin_height | 12.940 |
| fin_thickness | 0.819 |
| fin_material | papel_cartao |
| fin_cant | 0.000 |
| fin_position | -0.129 |
| motor | 1.35 L de vinagre (teto 171 psi) |
| launch_angle | 56.436 |

### Nota do campeão

| critério | pontos | de |
|---|---|---|
| alcance | 28.0 | 28 |
| consistencia | 10.5 | 12 |
| leveza | 19.3 | 20 |
| estabilidade | 2.1 | 10 |
| saida_trilho | 1.0 | 2 |
| arrasto | 11.6 | 12 |
| amortecimento | 0.0 | 6 |
| angulo_ataque | 2.9 | 4 |
| rigidez_aleta | 0.0 | 6 |
| **TOTAL** | **75.4** | **100** |

### Composição do arrasto do campeão

| parcela | Cd | o que é |
|---|---|---|
| atrito (pele) | 0.1248 | superfície molhada pelo ar |
| pressão (forma) | 0.1982 | nariz e ombro empurrando ar |
| base (esteira) | 0.0148 | vácuo atrás da traseira |
| **total** | **0.3378** | razão de finura 5.29 |

### Alcance por rendimento

| η | pressão | alcance |
|---|---|---|
| 0.70 | 120 psi | 259 m |
| 0.80 | 137 psi | 276 m |
| 0.90 | 154 psi | 290 m |
| 1.00 | 171 psi | 302 m |
