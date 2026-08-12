# bit06 — reprojeto por NOTA multicritério (0–100)

Gerado em 2026-08-11 07:46 | garrafa PET retornável REDUZIDA ~1,8 L (Ø9,585 cm)

**99.920 simulações** (6m58s) — 60 finalistas re-simulados em 4 rendimentos de reação × 3 ventos.

## Por que o modelo antigo foi aposentado

O `bit06` anterior (em `_MODELO_ANTIGO_falhou/`) foi otimizado por **alcance puro**: 376 m no papel, estabilidade ~1,03 cal. É a mesma assinatura de bit04 e bit05, que foram lançados de verdade, saíram rasos e bateram numa cerca.

Além disso, as pressões que ele assumia (1,35 L → "170 psi"; 1,5 L → "189 psi") são exatamente as pressões **nominais** dessas cargas — ou seja, o projeto contava com **rendimento perfeito da reação**. A bancada real do Murilo entregou η ≈ 0,82–0,88.

## O eixo de robustez: rendimento, não psi

O bicarbonato entra em excesso, então quem limita o CO₂ é o **ácido do vinagre**. Cada carga tem um teto físico de pressão. Por isso a robustez aqui é varrida em **rendimento de reação (η)** — toda combinação é fisicamente possível, e η<1 é exatamente o que derrubou bit04/bit05.

| η | significado | 1,20 L | 1,35 L | 1,50 L |
|---|---|---|---|---|
| 0.70 | dia ruim | 107 psi | 120 psi | 132 psi |
| 0.80 | o que a bancada deu no bit04/05 | 122 psi | 137 psi | 151 psi |
| 0.90 | bom dia | 137 psi | 154 psi | 170 psi |
| 1.00 | reação perfeita (teto físico) | 152 psi | 171 psi | 189 psi |

## Como a nota é montada

| critério | peso | 0 ponto em | nota cheia em |
|---|---|---|---|
| Alcance robusto (média dos rendimentos) | 40 | 120 m | 340 m |
| Consistência (pior η / média) | 25 | 0.70 | 0.95 |
| Leveza (massa seca) | 20 | 600 g | 200 g |
| Estabilidade mínima do voo | 10 | 1.0 cal | 2.0 cal |
| Saída do tubo-guia | 5 | 15 m/s | 25 m/s |

Restrições duras (reprovam o design): estabilidade sempre entre 1.0 e 3.5 cal, saída do trilho ≥ 15.0 m/s, apogeu ≥ 30 m — em TODOS os rendimentos.

## Ranking

| # | nota | alcance médio | pior η | massa seca | estab mín | trilho | η=0.70 | η=0.80 | η=0.90 | η=1.00 |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **74.6** | 289 m | 266 m | 331 g | 1.31 cal | 30.5 m/s | 266 | 282 | 297 | 309 |
| 2 | **74.5** | 291 m | 269 m | 298 g | 1.08 cal | 31.3 m/s | 269 | 284 | 298 | 310 |
| 3 | **74.5** | 287 m | 265 m | 333 g | 1.36 cal | 30.5 m/s | 265 | 281 | 295 | 307 |
| 4 | **74.5** | 293 m | 271 m | 310 g | 1.11 cal | 31.0 m/s | 271 | 287 | 301 | 313 |
| 5 | **74.5** | 292 m | 270 m | 310 g | 1.13 cal | 31.0 m/s | 270 | 286 | 301 | 312 |
| 6 | **74.4** | 292 m | 270 m | 303 g | 1.08 cal | 31.2 m/s | 270 | 286 | 300 | 312 |
| 7 | **74.4** | 294 m | 272 m | 325 g | 1.16 cal | 30.6 m/s | 272 | 288 | 302 | 314 |
| 8 | **74.4** | 293 m | 271 m | 319 g | 1.14 cal | 30.8 m/s | 271 | 287 | 301 | 313 |
| 9 | **74.3** | 299 m | 276 m | 327 g | 1.09 cal | 30.6 m/s | 276 | 293 | 308 | 320 |
| 10 | **74.3** | 297 m | 274 m | 325 g | 1.11 cal | 30.7 m/s | 274 | 291 | 306 | 317 |
| 11 | **74.3** | 299 m | 276 m | 338 g | 1.15 cal | 30.4 m/s | 276 | 292 | 308 | 320 |
| 12 | **74.3** | 299 m | 276 m | 342 g | 1.17 cal | 30.7 m/s | 276 | 292 | 307 | 320 |
| 13 | **74.3** | 297 m | 274 m | 321 g | 1.10 cal | 30.8 m/s | 274 | 290 | 305 | 317 |
| 14 | **74.3** | 294 m | 272 m | 322 g | 1.13 cal | 30.7 m/s | 272 | 288 | 303 | 314 |
| 15 | **74.3** | 293 m | 270 m | 352 g | 1.33 cal | 30.5 m/s | 270 | 286 | 302 | 314 |

## Campeão — parâmetros de construção

| parâmetro | valor |
|---|---|
| nose_length | 27.700 |
| nose_shape | PARABOLIC |
| nose_shape_param | 0.606 |
| nose_thickness | 1.558 |
| nose_material | poliestireno |
| ballast_fill | 11.878 |
| fin_count | 3 |
| fin_root | 6.560 |
| fin_tip | 0.000 |
| fin_sweep | 12.582 |
| fin_height | 13.690 |
| fin_thickness | 0.800 |
| fin_material | poliestireno |
| fin_cant | -0.095 |
| fin_position | -0.380 |
| motor | 1.50 L de vinagre (teto 189 psi) |
| launch_angle | 54.302 |

### Nota do campeão, critério por critério

| critério | pontos | de |
|---|---|---|
| alcance | 30.7 | 40 |
| consistencia | 22.3 | 25 |
| leveza | 13.5 | 20 |
| estabilidade | 3.1 | 10 |
| saida_trilho | 5.0 | 5 |
| **TOTAL** | **74.6** | **100** |

### Alcance esperado por rendimento

| η | pressão | alcance |
|---|---|---|
| 0.70 | 132 psi | 266 m |
| 0.80 | 151 psi | 282 m |
| 0.90 | 170 psi | 297 m |
| 1.00 | 189 psi | 309 m |
