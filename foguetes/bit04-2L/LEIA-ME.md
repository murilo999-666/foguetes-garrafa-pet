# foguete_real — modelo digital de referência (garrafa 2L)

Esta pasta NÃO é um foguete físico (não tem número `bitNN`). É o **estudo
digital de referência** da garrafa PET 2L retornável, de onde saíram os motores
físicos calibrados usados em todos os modelos.

## Conteúdo

- `garrafa2L_base.ork` — modelo fiel da garrafa 2L (Ø104 mm, ~105 g, base
  petaloide, ombro, anel de suporte, rosca e lábio do bocal PCO-1810)
- `motores/VinagreReal-*.eng` — família de motores físicos (vinagre 4% +
  bicarbonato), calibrados em 2 dados reais do Murilo:
  - **170 psi com 1,55 L** (química do CO₂ / lei de Henry)
  - **voo real de 275 m** a 45° (fator de escoamento k = 2,17)
  - `motores/fator_calibracao.txt` documenta o k e a banda de incerteza
- `foguete_MODELO_HUMANO.ork` — projeto por pesquisa/física (275 m)
- `foguete_real_otimizado.ork` — campeão da busca (motor 1,8 L / 196 psi, 391 m)
- `foguete_real_otimizado_SEGURO_1_55L.ork` — campeão com pressão validada
  (1,55 L / 170 psi, 371 m)
- `MODELO_HUMANO_pesquisa.md` — as fontes de pesquisa e decisões de projeto
- `otimizacao/` — banco SQLite e gráficos; `versoes_teste/` — top designs

## Relação com o bit05

O bit05 usa a MESMA química/calibração, mas com a garrafa reduzida (~1,8 L),
gerando sua própria família `VinagreBit05-*.eng`. Este estudo 2L continua como
referência e ponto de comparação.
