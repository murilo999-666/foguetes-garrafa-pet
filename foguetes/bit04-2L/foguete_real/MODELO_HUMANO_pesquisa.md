# Modelo por conhecimento humano — base de pesquisa e decisões de projeto

Foguete de garrafa PET 2L, motor vinagre+bicarbonato calibrado (1,55 L / 170 psi).
Projetado 100% por princípios de foguetismo, física e experiência humana — SEM
otimizador. Objetivo: comparar com o campeão dos 100 mil testes no mesmo banco.

## Fontes consultadas

1. **OBAFOG/MOBFOG nível 4** (docs.oba.org.br/obafog-nivel-4; Clube Centauri;
   relatos IFC/IFMG): propelente vinagre 4% + bicarbonato; lançamento oblíquo
   para máximo alcance horizontal; recomenda-se **ogiva** e **junção de garrafas**
   para expandir o tanque; pressão fixa em valor seguro.
2. **Apogee Rockets / Peak of Flight #442** (Tim Van Milligan, "best fin shape"):
   **3 aletas reduzem o arrasto de interferência em 25%** vs. 4; aleta **elíptica**
   tem o menor arrasto induzido; trapezoidal é o melhor custo/benefício construtivo.
3. **Nakka Rocketry** (nakka-rocketry.net/fins): CP ≥ 1 calibre atrás do CG;
   aletas maiores empurram o CP para trás (mais estável).
4. **CFD subsônico de cones** (WRA2 Water Rocket Forum; Crowell 1996; IRJET):
   **abaixo de Mach 0,8 o arrasto de pressão do nariz é ~zero para todos os
   formatos** — domina o atrito (área molhada). Nariz **arredondado/elíptico**
   tem o menor arrasto subsônico; pontudo só ganha em transônico/supersônico.
   (Nosso foguete faz ~70 m/s = **Mach 0,20** → regime subsônico puro.)
5. **Abdul Hamid et al. 2022, Int. Trans. J. Eng. (sugar rocket, OpenRocket+ANSYS,
   9 combinações)**: estabilidade 1,31–1,64 cal em todos; **aletas swept = mais
   estáveis** (CG e CP mais afastados); nariz elíptico = mais estável; diferença
   de desempenho entre formatos é **pequena** (apogeu 139–155 m); triangular voa
   mais alto por ter menor área/arrasto, mas é o menos estável.
6. **Regra de calibres** (Handbook of Model Rocketry, Stine; múltiplos fóruns):
   margem estática ótima **1,0–2,0 cal**; alvo prático **1,5–2,0**; acima de 2
   causa "weathercocking" (cata-vento) excessivo contra o vento.
7. **Ângulo de lançamento** (Quora/AirCommand; NASA GRC; estudos de water rocket):
   sem ar seria 45°; **com arrasto o ótimo sobe levemente para ~46–47°**.
8. **Coeficiente balístico / alcance** (Wikipedia; BYU flight eqs; NASA Dymos):
   após a queima (<0,2 s) o voo é balístico; massa maior = menor desaceleração,
   mas massa maior também reduz a velocidade inicial → há um **ótimo de massa**.
   Filosofia humana clássica: manter LEVE, só o lastro necessário p/ estabilidade.

## Decisões de projeto (com justificativa)

| Parâmetro | Escolha | Por quê (fonte) |
|---|---|---|
| Ângulo | **46°** | ótimo teórico c/ arrasto, não 45° (7) |
| Nariz (ogiva) | **ELIPSOIDE**, ~18 cm | menor arrasto subsônico + CG mais à frente = menos lastro (4,5) |
| Nº de aletas | **3** | −25% arrasto de interferência (2) |
| Formato aleta | **swept (trapézio enflechado)** | mais estável, menor form drag (2,5) |
| Material aleta | poliestireno **1,0 mm** | rígido, à prova d'água, construível (não o fio-de-navalha de 0,6 mm) |
| Estabilidade | **1,5–1,7 cal** (pós-queima) | consenso 1,5–2,0; faixa da própria equipe (6) |
| Lastro | **mínimo p/ 1,5–1,7 cal** | filosofia "leve" de máxima velocidade (8) — contraste direto com o otimizador |
| Motor | **1,55 L / 170 psi** | pressão validada pelo Murilo (voo real de 275 m) |

## Diferença esperada vs. otimizador

O otimizador dos 100 mil testes escolheu: nariz parabólico-0,88, ~400 g de
Durepoxi (PESADO, para maximizar coeficiente balístico com este motor potente),
aletas de papel-cartão de 0,6 mm, 52°. O modelo humano segue a heurística
clássica oposta: **leve, só o lastro necessário**, 46°, aletas robustas. A
comparação mostra se a intuição humana ou a busca exaustiva rende mais alcance.
