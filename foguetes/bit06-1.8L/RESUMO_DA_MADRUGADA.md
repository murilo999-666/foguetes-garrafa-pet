# O que rodou enquanto você dormia — 17/08, madrugada

## TL;DR: o foguete que você montou está certo. Não mude nada.

A campanha completa de **99.920 simulações** terminou às 03:17. Comparei o que
você construiu com o melhor que ela achou, na mesma régua:

| versão | nota | alcance | massa seca | **estabilidade** |
|---|---:|---:|---:|---:|
| **o que você construiu** | 73,6 | 278 m | 365 g | **1,36 cal** |
| campanha 99k — construtível | 73,8 | 283 m | 349 g | 1,22 cal |
| campanha 99k — campeão livre | 74,9 | 282 m | 323 g | 1,21 cal |

**Com 12 vezes mais busca, o ganho foi +0,2 ponto e +5 metros — pagando 0,14 cal
de margem de estabilidade.** Isso não é um upgrade, é uma troca ruim para quem já
teve dois foguetes que não subiram.

A busca convergiu: o seu projeto está no platô. Pode voar tranquilo.

---

## Um achado importante sobre o bit07 (leia antes de usá-lo)

Ao verificar os motores que o chkdsk recuperou, descobri que **56% da grade de
motores do bit07 é fisicamente impossível**.

O grid cruzava carga × pressão livremente, mas quem limita o CO₂ é o ácido do
vinagre. Os próprios arquivos denunciam — `Bit07-L0_90-P170.eng` diz
`rendimento de CO2 eta=1.69`, ou seja "preciso de 169% do CO₂ que este vinagre
tem".

O pior: a carga **recomendada** pelo playbook do bit07 era **0,90 L**, cujo teto
físico é **100 psi**. A tabela dele promete de 130 a 200 psi para essa carga.
**Nenhuma daquelas colunas pode acontecer.**

- ❌ Não use a tabela do `PLAYBOOK_lancamento.txt`
- ✅ O manual novo (`impressão/MODELO_FINAL/MANUAL_bit07_FINAL_LANCAMENTO.pdf`)
  está correto — foi refeito com pressões reais
- ✅ O bit06 de hoje está imune: a campanha dele varre **rendimento**, não psi

Detalhes em `foguetes/bit07 robusto 2L/ACHADO_grid_de_motores_impossivel.md`.

---

## Novidade para levar hoje: `FICHA_DE_CAMPO.pdf`

Todo o modelo do projeto está ancorado em dois números reais medidos por você
(170 psi na bancada, 275 m do bit03) — mas não existia onde anotar os próximos.

Fiz uma ficha de uma página para preencher **no local**: pressão medida (o campo
mais importante), carga, ângulo, alcance, e espaço para escrever o que os números
não pegam. Traz também a tabela do que esperar para cada leitura do manômetro.

**Imprima junto com o resto.** É esse papel que calibra o próximo foguete.

---

## Verificações que fiz

- **Molde × projeto**: o molde que você vai cortar bate exatamente com o `.ork`
  que vai voar — 3 aletas, polietileno 1,0 mm, cant zero, 150,0 × 185,1 mm nos
  dois. Conferido peça por peça.
- **Motores recuperados**: 54 dos 57 arquivos estão íntegros, 2 vazios. Deixei em
  `D:\7-Recuperados-revisar\` — não devolvi ao bit07 porque, sabendo do problema
  acima, mais da metade não deveria ser usada.
- **Pipeline pós-mudança de pastas**: testado de ponta a ponta antes de rodar a
  campanha.

---

## O que está pronto para imprimir

| Arquivo | Para quê |
|---|---|
| `impressao_PET/bit06pet_aleta_molde.pdf` | recortar as 3 aletas (100%, confira a régua) |
| `FOLHA_bit06_PET.pdf` | montagem + lançamento |
| `FICHA_DE_CAMPO.pdf` | **preencher no local** |

O que você já tinha continua intacto em `_ENTREGUE_16ago_2245/` — a campanha nova
não tocou nessa pasta.

---

## Números do dia

**1,35 L de vinagre + ~176 g de bicarbonato, a 53°, lastro 209 g.**
Aletas: bordo de ataque a **150 mm do bocal**.
Espere **~272 m** se o manômetro der ~137 psi.

Boa sorte. 🚀
