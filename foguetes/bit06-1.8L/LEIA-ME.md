# bit06 — garrafa PET retornável REDUZIDA (~1,8 L, Ø9,585 cm)

**Projeto vigente: `bit06_B_CONSTRUTIVEL.ork`** — coifa PLA impressa + aletas de
polietileno 1,0 mm. Reprojetado em **2026-08-11** com o método do bit07
(nota multicritério + restrições duras), a partir de **99.920 simulações**.

O projeto anterior está em `_MODELO_ANTIGO_falhou/` — leia o README de lá para
entender por que foi aposentado.

---

## O que construir

| | |
|---|---|
| Corpo | garrafa PET retornável reduzida ~1,8 L |
| Coifa | parabólica (par. 0,61), **27,5 cm**, PLA 1,2 mm, impressa em **2 peças** |
| Aletas | **3**, polietileno **1,0 mm** (184 / 40 / 193 / 71,5 mm) |
| Lastro | **146 g** de Durepoxi (bico preenchido 12 cm) — faixa 90–222 g |
| Massa seca | 339 g · comprimento 63,3 cm |
| Motor | **1,50 L de vinagre + ~195 g de bicarbonato** |
| Ângulo | 54° |
| Estabilidade mínima | **1,31 cal** (nunca abaixo de 1,0 em nenhum cenário) |

**Alcance esperado**, conforme o rendimento da reação (leia o manômetro):

| η | pressão | alcance |
|---|---|---|
| 0,70 (dia ruim) | 132 psi | 265 m |
| **0,80** (o que a bancada deu no bit04/05) | **151 psi** | **281 m** |
| 0,90 (bom dia) | 170 psi | 295 m |
| 1,00 (reação perfeita) | 189 psi | 307 m |

---

## Arquivos

| Arquivo | O que é |
|---|---|
| **`bit06_B_CONSTRUTIVEL.ork`** | **o projeto para construir** (PLA + polietileno) |
| `bit06_A_CAMPEAO.ork` | campeão da busca (poliestireno 0,8 mm) — referência de teto |
| `bit06_C_MARGEM_EXTRA.ork` | mais estável (1,59 cal), porém 176 g mais pesado |
| `bit06_MODELO_FINAL.ork` | cópia do campeão salva pela campanha |
| `MANUAL_bit06_MONTAGEM.pdf` | passo a passo de construção + tabela do lastro |
| `MANUAL_bit06_LANCAMENTO.pdf` | motor, cargas, checklist, segurança |
| `RELATORIO_bit06.md` | como a nota é montada + ranking dos 60 finalistas |
| `ranking_bit06.csv` | os 60 finalistas com todos os números |
| `impressao/` | STL da coifa (inteira e em 2 peças) + moldes das aletas |
| `motores/` | 28 motores `Bit06-L<carga>-E<rendimento>.eng` + manifesto |
| `garrafa_bit06_base.ork` | modelo fiel da garrafa vazia (base para novos projetos) |
| `acompanhar.ps1` | painel de acompanhamento da campanha |
| `simulacoes/` | banco SQLite, ranking, variantes, tabelas de lastro e carga |
| `_MODELO_ANTIGO_falhou/` | o projeto anterior e por que foi aposentado |

---

## As três versões

| Versão | Nota | Alcance médio | Massa seca | Estab. | Para que serve |
|---|---|---|---|---|---|
| A — campeão | 74,6 | 289 m | 331 g | 1,31 cal | teto teórico (poliestireno 0,8 mm) |
| **B — construtível** | **73,8** | **287 m** | **339 g** | **1,31 cal** | **é este que você constrói** |
| C — margem extra | 67,1 | 298 m | 515 g | 1,59 cal | mais estável, bem mais pesado |

A versão B troca poliestireno 0,8 mm por PLA impresso + polietileno 1,0 mm (o que
você tem) e arredonda tudo para régua. Custa **0,8 ponto e 2 m** — de graça.

---

## Como a nota funciona (0–100)

| critério | peso | 0 ponto | nota cheia |
|---|---|---|---|
| Alcance robusto (média dos rendimentos) | 40 | 120 m | 340 m |
| Consistência (pior η / média) | 25 | 0,70 | 0,95 |
| Leveza (massa seca) | 20 | 600 g | 200 g |
| Estabilidade mínima em voo | 10 | 1,0 cal | 2,0 cal |
| Saída do tubo-guia | 5 | 15 m/s | 25 m/s |

**Restrições duras** (reprovam): estabilidade sempre entre 1,0 e 3,5 cal, saída do
trilho ≥ 15 m/s, apogeu ≥ 30 m — em **todos** os rendimentos.

---

## Por que o eixo é rendimento, não psi

O bicarbonato entra em excesso, então quem limita o CO₂ é o **ácido do vinagre**.
Cada carga tem um **teto físico** de pressão (1,50 L → 189 psi). Varrer o
**rendimento da reação (η)** garante que toda combinação simulada é possível — e
η<1 é exatamente o modo de falha real (bicarbonato velho, vinagre fraco,
vazamento, reação incompleta) que derrubou bit04 e bit05.

> O bit06 antigo foi projetado em η=1,00, o teto físico. Por isso prometia
> pressões que a bancada nunca entregou.

---

## Confronto com o modelo antigo (mesma régua)

| | Antigo | **Novo (B)** |
|---|---|---|
| Alcance médio | 329 m | 287 m |
| Massa seca | 471 g | 339 g |
| **Estabilidade mínima** | **0,51 cal ❌** | **1,31 cal ✅** |
| Nota | 68,4 | **73,8** |

O antigo voa mais longe **no papel** — e está na mesma faixa de estabilidade do
bit04 (0,46 cal) e do bit05 (0,24 cal), os dois que saíram rasos e bateram na
cerca. Ele **reprova** na restrição dura de 1,0 cal.

---

## Reproduzir

```powershell
cd C:\Users\muril\openrocket-optimizer
.venv\Scripts\python scripts\motor_bit06_rendimento.py     # 28 motores
.venv\Scripts\python scripts\bit06_orquestrador.py         # ~100k simulações
.venv\Scripts\python scripts\bit06_variantes.py            # A / B / C + antigo
.venv\Scripts\python scripts\bit06_lastro.py               # tabela do lastro
.venv\Scripts\python scripts\bit06_cargas.py               # tabela de cargas
.venv\Scripts\python scripts\exportar_fabricacao.py "D:\OBAFOG\bit06 1,8L\bit06_B_CONSTRUTIVEL.ork" --saida "D:\OBAFOG\bit06 1,8L\impressao" --nome bit06
```
