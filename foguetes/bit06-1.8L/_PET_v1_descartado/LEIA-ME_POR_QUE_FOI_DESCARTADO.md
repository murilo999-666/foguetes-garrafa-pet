# ⚠️ bit06 PET — versão 1, DESCARTADA (não construir)

Primeira rodada da campanha com a coifa de garrafa PET moldada.
Gerada em **2026-08-16 ~21:15**, descartada em **~21:50** e substituída pela v2.

Os arquivos ficam aqui por histórico. **Não use para construir.**

---

## Os três erros

### 1. Aletas demais — 4 em vez de 3
A busca escolheu **4 aletas**. O Murilo prefere **3**: menos peças para alinhar,
e alinhamento de aleta é o defeito nº 1 da lista (é o principal suspeito de
bit04 e bit05 não terem subido). Uma aleta a menos é uma chance a menos de errar
o ângulo na colagem.

Na v2 o número de aletas saiu do espaço de busca: **fixo em 3**.

### 2. A leveza tinha sido rebaixada de 20 para 10 pontos — erro meu
A régua original do bit06 dava **20 pontos** para massa seca, o 3º critério mais
pesado. Ao abrir espaço para os termos aerodinâmicos (arrasto, amortecimento,
ângulo de ataque, rigidez) eu cortei a leveza para **10** — e não avisei.

O efeito apareceu direto no resultado: o modelo v1 ficou com **394 g de massa
seca e 242 g de lastro**, contra 339 g / 146 g do bit06 anterior. Ou seja, o
projeto engordou justamente porque o critério que segurava o peso tinha perdido
metade da força.

Na v2 a leveza volta a **20 pontos**, o 2º maior peso, atrás só do alcance:

| critério | v1 (errada) | v2 |
|---|---|---|
| Alcance | 30 | 28 |
| **Leveza** | **10** | **20** |
| Consistência | 15 | 12 |
| Arrasto | 12 | 12 |
| Estabilidade mínima | 10 | 10 |
| Amortecimento | 8 | 6 |
| Rigidez da aleta | 5 | 6 |
| Ângulo de ataque | 5 | 4 |
| Saída do trilho | 5 | 2 |

### 3. Aletas inclinadas (cant) que não dá para construir
O campeão v1 usava **cant de −1,99°**, quase o limite do espaço de busca. O
Murilo não consegue reproduzir essa inclinação colando à mão.

Isso é pior do que parece: um cant que existe no modelo e não existe na peça faz
a simulação contar com um giro estabilizante que o foguete real **não vai ter**.
O papel fica melhor que o campo — exatamente o tipo de otimismo que já custou
dois lançamentos.

Na v2 o cant é **fixo em 0°**.

---

## O que NÃO estava errado

Vale registrar, porque é a preocupação natural: **este modelo era estável em toda
a faixa de pressão.** Medido nos quatro rendimentos de reação:

| η | pressão | estabilidade mínima | estabilidade máxima | alcance |
|---|---|---|---|---|
| 0,70 | 120 psi | **1,51 cal** | 2,16 | 253 m |
| 0,80 | 137 psi | **1,51 cal** | 2,17 | 273 m |
| 0,90 | 154 psi | **1,51 cal** | 2,17 | 289 m |
| 1,00 | 171 psi | **1,51 cal** | 2,17 | 303 m |

A estabilidade **não varia com a pressão** (1,51 cal nas quatro) — faz sentido:
o pior momento é sempre o lançamento, com a garrafa cheia, e isso não depende de
quanto CO₂ a reação rendeu. Nenhuma pressão reprovava.

Então o descarte é por **construtibilidade e por peso**, não por instabilidade.

---

## Conteúdo desta pasta

| Arquivo | O que é |
|---|---|
| `bit06_PET_B_CONSTRUTIVEL.ork` | o que seria entregue (4 aletas, cant −2°, 394 g) |
| `bit06_PET_A_CAMPEAO.ork` | campeão da busca livre (aletas de papel-cartão 0,84 mm) |
| `bit06_PET_C_RIGIDA.ork` / `_D_MARGEM.ork` | variantes de rigidez e de margem |
| `FOLHA_bit06_PET.pdf` | folha de construção da v1 |
| `RELATORIO_bit06_PET_AERO.md` | relatório completo da campanha v1 (40.720 simulações) |
| `ranking_bit06_pet_aero.csv` | os 60 finalistas com todas as métricas |
| `impressao_PET/` | molde das aletas da v1 (4 unidades) |

A campanha v1 em si foi válida — 40.720 simulações, sem falhas. O que estava
errado eram as **regras** que ela recebeu.
