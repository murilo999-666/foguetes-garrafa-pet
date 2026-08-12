# bit07 — o foguete projetado para AGUENTAR a bancada real

**Projeto vigente: `bit07_MODELO_FINAL.ork`** (gerado por
`openrocket-optimizer/scripts/bit07_robusto.py`)
**Ranking completo: `RELATORIO_bit07.md` e `ranking_bit07.csv`**

---

## 1. O que aconteceu no campo (04/08/2026)

bit04 e bit05 foram lançados. Nos dois casos a bancada só chegou a **140–150 psi**
(o projeto assumia 170). Os dois **não subiram**: saíram rasos e pegaram numa
cerca logo à frente.

## 2. O que a simulação diz sobre isso

`scripts/diagnostico_pressao_bit0405.py` refez os dois voos com motores gerados
para cada pressão (mesma química, rendimento de CO₂ reduzido):

**bit04** (1,8 L de vinagre, 416 g de lastro, 52°)

| psi | saída do trilho | apogeu | alcance | estab. mín | estab. máx |
|---|---|---|---|---|---|
| 130 | 26,0 m/s | 75 m | 299 m | **0,46 cal** | 0,99 cal |
| 140 | 26,8 m/s | 81 m | 314 m | **0,46 cal** | 0,99 cal |
| 170 | 29,8 m/s | 94 m | 352 m | **0,46 cal** | 1,00 cal |

**bit05** (1,55 L, 115 g de lastro, 46°)

| psi | saída do trilho | apogeu | alcance | estab. mín | estab. máx |
|---|---|---|---|---|---|
| 130 | 32,4 m/s | 102 m | 252 m | **0,24 cal** | 1,01 cal |
| 140 | 33,8 m/s | 106 m | 258 m | **0,24 cal** | 1,01 cal |
| 170 | 36,8 m/s | 118 m | 276 m | **0,24 cal** | 1,01 cal |

### Conclusão honesta

**A pressão sozinha NÃO explica a falha.** De 170 para 140 psi o foguete perde
~11% de alcance (bit04: 352→314 m; bit05: 276→258 m) e continua saindo do
tubo-guia a 27–34 m/s. Pela física do voo, os dois deveriam ter voado ~300 m e
~250 m. Não voaram — logo a causa está **fora do modelo aerodinâmico**: soltura
da base, vedação/rosca, desalinhamento de aleta, tubo-guia. A falta de pressão
foi o gatilho, não a explicação inteira.

**O que os dois tinham em comum e ninguém tinha olhado: margem zero.**
- estabilidade **mínima** durante o voo: 0,46 cal (bit04) e 0,24 cal (bit05) —
  a regra prática do foguetemodelismo pede **≥ 1,0 calibre em todo o voo**;
- bit04 com estabilidade pós-queima **exatamente 1,00 cal** (o otimizador parou
  colado no limite que eu tinha imposto);
- bit04 pesando 2,46 kg na decolagem, com 416 g de Durepoxi na ponta.

Enquanto a garrafa está cheia de líquido o CG fica atrás; nessa janela os dois
foguetes eram **quase instáveis**. Qualquer perturbação na saída (tip-off,
rajada, um grau de aleta torta) vira um ângulo grande — e o foguete sai
apontando para a cerca. As restrições antigas da otimização exigiam estabilidade
só **depois** da queima; a mínima nunca foi restringida. Esse foi o erro de
projeto, e é o que o bit07 corrige.

## 3. O modelo novo: nota de 0 a 100

O bit07 não é otimizado para uma pressão. Cada candidato é simulado em
**8 pressões (130, 140, 150, 160, 170, 180, 190, 200 psi) × 3 ventos**, e recebe uma nota:

| critério | peso | 0 ponto em | nota cheia em | por que |
|---|---|---|---|---|
| **Alcance robusto** (média das 8 pressões) | **40** | 150 m | 400 m | é o que a OBAFOG pontua |
| **Consistência** (pior pressão ÷ média) | **25** | 0,70 | 0,95 | um projeto de 380 m que só anda a 180 psi vale menos que um de 330 m que anda igual em qualquer dia |
| **Leveza** (massa seca: estrutura + lastro) | **20** | 700 g | 250 g | peso é o que transforma falta de empuxo em voo rasante |
| **Estabilidade mínima do voo** | **10** | 1,0 cal | 2,0 cal | o erro do bit04/bit05 |
| **Saída do tubo-guia** | **5** | 15 m/s | 25 m/s | sair rápido = tolerar tip-off e vento |

**Restrições duras** (reprovam o design, em TODAS as pressões):
estabilidade sempre entre **1,0 e 3,5 cal** · saída do trilho **≥ 15 m/s** ·
apogeu **≥ 40 m** · raiz da aleta ≥ 50% da corda total (não descola).

### A primeira rodada errou — e o erro vale registro

A busca v1 usava "alcance − peso" como atalho na etapa 1 e só aplicava a nota
completa nos finalistas. Resultado: **40 finalistas idênticos, todos colados em
1,00 cal**, e 24 deles reprovados a 180 psi por caírem para 0,97–0,99 cal. O
otimizador reproduziu exatamente o vício do bit04. Está arquivada em
`versoes_teste/` (`bit07_v1_alcance_na_borda.ork`, nota 41,5 e **inviável** pela
régua corrigida).

Correção: a etapa 1 passou a otimizar **a própria nota**, e a restrição subiu
para **1,08 cal** — a estabilidade cai ~0,02 cal de 140 para 180 psi, então
quem marca 1,00 no pior caso reprova no melhor. Foi preciso criar a métrica
`dry_mass` (massa seca lida do mínimo da série de massa) para que "leveza"
pudesse valer ponto sem depender de qual motor o design escolheu.

Foi verificado antes de fixar (800 simulações de sondagem) que o limite de
1,0 cal é **atingível**: dá para chegar a 2,76 cal nesta garrafa, e mais da
metade dos designs viáveis já passa de 1,0 cal. Não é uma restrição impossível
— é uma que o bit04 e o bit05 simplesmente não tinham.

## 3b. Resultado

40 finalistas re-simulados nas **8 pressões (130→200 psi)**: **todos aprovados**
(na v1 eram 16 de 40), com estabilidade mínima **1,56–1,95 cal** e notas entre **69,8 e 71,3** —
empate técnico (nenhum design quebra a 190/200 psi: a estabilidade mínima é a do
lançamento, com a garrafa cheia, e não piora com pressão alta). Por isso o `RELATORIO_bit07.md` entrega a **fronteira**, não um
vencedor só: A (maior nota), B (maior alcance), C (mais leve) e
**D (materiais reais)**.

A busca livre escolhe **papelão** para ogiva e aletas, porque leveza vale 20
pontos — no modelo funciona, a 45 m/s de saída não. O `bit07_MODELO_FINAL.ork` é
a opção D com as espessuras arredondadas para o que você constrói (PLA 1,2 mm,
poliestireno 1,0 mm): custa 3 m de alcance e 36 g, mantém 1,24 cal.

Se preferir margem a metros, `bit07_E_margem_extra.ork`: **1,51 cal** por
−16 m e +37 g (ogiva ogival de 29,4 cm, 4 aletas, lastro 14,3 cm).

| | bit04 (real) | bit05 (real) | **bit07** |
|---|---|---|---|
| massa na decolagem | 2,46 kg | 1,95 kg | **1,34 kg** |
| lastro | 416 g | 115 g | **180 g** |
| vinagre | 1,8 L | 1,55 L | **0,9 L** |
| estabilidade mínima | 0,46 cal | 0,24 cal | **1,25 cal** |
| alcance a 140 psi | 314 m | 258 m | **284 m** |
| alcance a 170 psi | 352 m | 276 m | **308 m** |
| alcance a 200 psi | — | — | **329 m** |

O bit07 abre mão de ~30 m simulados para sair do tubo com o dobro da margem e
1,1 kg a menos. Achado que vale sozinho: **0,9 L de vinagre rende o mesmo que
1,55 L** (284 vs 283 m a 140 psi) e devolve 0,23 cal de margem — carga grande
só adiciona peso.

Instruções de construção, tolerância do lastro, ângulo e checklist:
`PLAYBOOK_lancamento.txt`.
Peças prontas para imprimir/cortar (ogiva STL, molde 1:1 da aleta em PDF,
gabarito de alinhamento em DXF): `impressão/` — veja `impressão/LEIA-ME.md`.

## 4. Liberdade de projeto (a mesma de sempre)

Livre: ogiva (6–30 cm, formato, parede 0,6–3 mm, PLA/poliestireno/papelão),
lastro de Durepoxi no bico (0–26 cm de preenchimento, massa derivada do volume
real), aletas (3–6 unidades, planform livre, material, cant ±2°, posição),
carga de vinagre (0,9–1,8 L) e ângulo de lançamento (30–60°).

Fixo: o corpo é a **garrafa PET 2L retornável real** (`garrafa2L_base.ork`), sem
metal no lastro (regulamento).

## 5. Motores

`motores/` traz a grade **carga de vinagre × pressão realmente atingida**
(7 cargas × 8 pressões, 130→200 psi), gerada por
`scripts/motor_bit07_pressao.py`. A pressão entra como *rendimento de CO₂*
η = P_alvo / P_nominal — cobre bicarbonato fraco, vinagre abaixo de 4%, reação
incompleta e vazamento, que é o que aconteceu de verdade.
`manifesto.json` tem impulso, pico e massa de propelente de cada um.

## 6. Antes do próximo lançamento

1. **Meça a pressão e anote** — o motor certo é o da coluna da pressão que você
   realmente atingiu, não a de projeto.
2. Se der 140 psi de novo, investigue a **causa** (bicarbonato em excesso de
   verdade? vinagre 4%? vedação da rosca? tempo entre fechar e lançar?) — o
   bit07 aguenta 140 psi, mas 170 continua valendo ~10% a mais de alcance.
3. Confira o alinhamento das aletas com o gabarito e a firmeza da base: a
   simulação diz que os dois voos deveriam ter dado certo, então o que falhou
   está na montagem/lançamento.
