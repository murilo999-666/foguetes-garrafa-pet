# ⚠️ Achado: 56% da grade de motores do bit07 é fisicamente impossível

Descoberto em **2026-08-17, madrugada**, ao verificar os arquivos `.eng` que o
chkdsk recuperou (`D:\7-Recuperados-revisar\found.001\`).

---

## O que está errado

A grade de motores do bit07 cruzava **carga de vinagre × pressão** livremente:
7 cargas × 8 pressões = 56 motores. Mas quem limita o CO₂ é o **ácido acético do
vinagre** (o bicarbonato entra em excesso). Cada carga tem um **teto físico** de
pressão, e pedir mais que isso não é "difícil" — é impossível.

Os próprios arquivos denunciam. O cabeçalho de `Bit07-L0_90-P170.eng` diz:

```
; bit07 garrafa 2L | 0.90 L vinagre 4% | rendimento de CO2 eta=1.69
```

**η = 1,69** significa "preciso de 169% do CO₂ que este vinagre pode fornecer".

## O tamanho do problema

| Carga | Teto físico | O que a grade oferecia | Motores impossíveis |
|---|---|---|---|
| **0,90 L** | **100 psi** | 130 a 200 psi | **8 de 8 — todos** |
| **1,10 L** | **122 psi** | 130 a 200 psi | **8 de 8 — todos** |
| 1,30 L | 143 psi | 130 a 200 psi | 6 de 8 |
| 1,45 L | 159 psi | 130 a 200 psi | 4 de 8 |
| 1,55 L | 170 psi | 130 a 200 psi | 1 de 6 |
| 1,70 L | 186 psi | 130 a 200 psi | 2 de 8 |
| 1,80 L | 196 psi | 130 a 200 psi | 1 de 8 |

**30 dos 54 motores íntegros (56%) exigem mais CO₂ do que a carga fornece.**

## Por que isso importa muito

A carga **recomendada pelo playbook do bit07 era 0,90 L** — e essa é justamente a
que **não alcança nenhuma** das pressões da tabela. O teto dela é 100 psi.

Ou seja, esta linha do `PLAYBOOK_lancamento.txt`:

```
carga    130psi 140psi 150psi 160psi 170psi 180psi 190psi 200psi  estab.mín
0,90 L      272    283    291    301    308    317    322    329   1,24 cal <== USE
```

**é inteiramente ficção.** Nenhuma daquelas oito colunas pode acontecer com 0,9 L.

Isso também explica, em parte, a frustração de campo: o projeto prometia 284 m a
"140 psi" com 0,9 L, mas 0,9 L nunca chegaria a 140 psi — o manômetro ia parar
perto de 100.

## O que NÃO está afetado

- **O manual novo do bit07 MODELO FINAL**
  (`impressão/MODELO_FINAL/MANUAL_bit07_FINAL_LANCAMENTO.pdf`) está **correto**.
  Ele foi refeito com os motores `VinagreReal`, que são calculados no teto físico
  de cada carga (1,0 L → 111 psi, 1,55 L → 170 psi, etc.), e a tabela dele traz a
  pressão nominal verdadeira de cada carga.

- **O bit06 (o que voa hoje)** está correto por construção: a campanha dele varre
  o **rendimento da reação (η de 0,70 a 1,00)** em vez de psi absoluto, então toda
  combinação simulada é possível por definição. Foi exatamente para evitar este
  erro que o eixo foi trocado.

## O que fazer com o bit07

1. **Não use a tabela do `PLAYBOOK_lancamento.txt`.** Use o manual novo.
2. Se for regerar a grade de motores, use o método do bit06:
   `scripts/motor_bit06_rendimento.py` parametriza por rendimento e nunca gera
   combinação impossível. O equivalente para a garrafa 2 L é trivial (só trocar
   `V_BOTTLE` para 2,10e-3 e o diâmetro para 104 mm).
3. Os 2 arquivos corrompidos (`Bit07-L1_55-P180.eng` e `-P190.eng`, ambos vazios)
   não fazem falta: eram impossíveis ou desnecessários de qualquer forma.

## Estado dos arquivos recuperados

`D:\7-Recuperados-revisar\found.001\` — 57 arquivos:
- 54 `.eng` íntegros (cabeçalho RASP válido, curva de empuxo completa)
- 2 `.eng` vazios (`Bit07-L1_55-P180`, `Bit07-L1_55-P190`)
- 1 `manifesto.json`

Não devolvi ao `bit07 robusto 2L/motores/` porque, sabendo disso, **mais da metade
deles não deveria ser usada**. Se quiser a grade de volta, o certo é regerá-la
pelo rendimento.
