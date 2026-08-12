# ⚠️ MODELO ANTIGO — APOSENTADO (não usar para construir)

Esta pasta guarda o **projeto bit06 anterior** e todo o material que o gerou.
Ele foi aposentado em **2026-08-11** e substituído pelo reprojeto que está na
pasta de cima (`bit06_MODELO_FINAL.ork` + `RELATORIO_bit06.md`).

Está tudo aqui por histórico e rastreabilidade — **não use estes arquivos como
referência de construção.**

---

## Por que foi aposentado

### 1. Foi otimizado por alcance puro
O bit06 antigo buscava **só distância**. O resultado foi um foguete de 376 m
"no papel" com **estabilidade ~1,03 cal** — ou seja, parado em cima do limite
mínimo aceitável, sem margem nenhuma.

Essa é **exatamente a assinatura de bit04 e bit05**, que foram lançados de
verdade em 2026-08-04, saíram rasos e bateram numa cerca:

| Projeto | Massa | Lastro | Estabilidade mínima em voo | O que aconteceu |
|---|---|---|---|---|
| bit04 | 2,46 kg | 416 g | **0,46 cal** | não subiu, bateu na cerca |
| bit05 | 1,95 kg | 115 g | **0,24 cal** | não subiu, bateu na cerca |
| bit06 antigo | — | — | **~1,03 cal** (estático) | nunca teve `stability_min` verificada |

O erro de método era o mesmo nos três: as restrições antigas só exigiam
estabilidade **estática** e **pós-queima**, nunca a **mínima durante o voo**.
Em foguete de garrafa o CG fica atrás enquanto ainda há líquido, então a
estabilidade *cai* no meio da subida — justo onde ninguém estava olhando.

### 2. Assumia reação química perfeita
As pressões do projeto antigo eram:

- `bit06_MODELO_FINAL.ork` → 1,35 L de vinagre a **"170 psi"**
- `foguete_bit06_OTIMIZADO.ork` → 1,5 L a **"189 psi"**

Recalculando a química da garrafa reduzida (1,82 L internos), essas são
**exatamente as pressões NOMINAIS** dessas cargas — o teto físico, atingido
apenas se **todo** o CO₂ do ácido acético ficar no sistema e nada vazar.

A bancada real do Murilo entregou **η ≈ 0,82–0,88** (esperava 170 psi nos
lançamentos do bit04/05 e o manômetro deu 140–150 psi). Ou seja: o projeto
antigo foi dimensionado para o melhor caso possível e nunca testado no caso real.

---

## O que o reprojeto mudou

| | Antigo | Novo |
|---|---|---|
| Critério | alcance puro | **nota 0–100** (alcance 40 · consistência 25 · leveza 20 · estabilidade 10 · saída de trilho 5) |
| Estabilidade | ~1,03 cal, não restringida em voo | **restrição dura**: nunca < 1,0 cal em nenhum cenário |
| Pressão | 1 ponto, nominal (η=1,00) | **4 rendimentos** (η = 0,70 · 0,80 · 0,90 · 1,00) × 3 ventos |
| Física do motor | carga → psi nominal | grade **carga × rendimento**, nenhuma combinação impossível |
| Busca | otimização por alcance | **~100 mil simulações** em 8 blocos independentes |

O eixo de robustez agora é o **rendimento da reação (η)**, não psi absoluto.
Motivo: o bicarbonato entra em excesso, então quem limita o CO₂ é o **ácido do
vinagre** — cada carga tem um teto de pressão. Varrer η garante que toda
combinação simulada é fisicamente possível, e η<1 é exatamente o modo de falha
que derrubou bit04/bit05.

---

## Conteúdo desta pasta

| Arquivo | O que é |
|---|---|
| `bit06_MODELO_FINAL.ork` | campeão antigo (1,35 L / 170 psi nominal, 363 m) |
| `foguete_bit06_OTIMIZADO.ork` | variante mais agressiva (1,5 L / 189 psi, 376 m) |
| `foguete_bit06_OTIMIZADO_SEGURO_170psi.ork` | a mesma, limitada a 170 psi |
| `foguete_bit06_MODELO_HUMANO.ork` | projeto "só por pesquisa/física", sem otimizador (279 m) |
| `LEIA-ME.md` | o README antigo, com as tabelas originais |
| `bit06_otimizacao_completa.csv` / `.xlsx` | banco bruto da otimização antiga |
| `motores/` | família `VinagreBit06-*.eng` antiga (por carga, sem eixo de rendimento) |
| `simulacoes/` | banco SQLite e gráficos da rodada antiga |
| `versoes_teste/` | variantes "robusto01..15" daquela busca |

**Observação:** estes `.ork` não abrem mais com as simulações prontas — eles
referenciam os motores antigos por designação e o OpenRocket não os resolve
sozinho. A geometria continua legível normalmente.

---

## O que NÃO está aqui (e por quê)

`garrafa_bit06_base.ork` ficou **na pasta de cima**, de propósito.

Ele não é "o modelo que falhou" — é o **modelo fiel da garrafa física vazia**
(PET retornável reduzida: Ø9,585 cm, 33 cm, ~104 g). A garrafa não tem culpa
nenhuma no que deu errado; ela é insumo dos projetos novos e continua sendo a
base do reprojeto.
