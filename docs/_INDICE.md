# OBAFOG — índice da pasta

Cada foguete **físico** é `bitNN` (bit01 = primeiro que o Murilo construiu).
Dentro de cada pasta, o arquivo `bitNN_MODELO_FINAL.ork` é **o projeto vigente**
daquele foguete; os demais arquivos são histórico, estudos e simulações.

Motor: vinagre 4% + bicarbonato em excesso, modelado pela física do CO₂ (lei de
Henry) e calibrado em dois dados reais do Murilo — **170 psi com 1,55 L** e o
**voo real de 275 m** (fator k = 2,17). Cada pasta traz seus `.eng` em `motores/`.

> ⚠ **O voo de 275 m foi do bit02, não do bit03** (corrigido em 20/08/2026 pelo
> próprio Murilo). O bit03 voou ~100 m. Isso importa porque o fator k = 2,17
> saiu de ajustar um voo de 275 m à geometria do bit03 — que não é a geometria
> que voou. **Não existe `.ork` do bit02**: a pasta só tem os STL das ogivas.
> Enquanto não houver modelo do bit02, o k = 2,17 fica sob suspeita e o único
> voo bom do projeto continua sem âncora geométrica.

## Os foguetes

| Pasta | O que é | Projeto vigente | Alcance previsto |
|---|---|---|---|
| `bit01 ogivas/` | 1º foguete | ogivas STL | — |
| `bit02 ogivas/` | 2º foguete | ogivas STL (**sem `.ork`**) | **275 m medido** |
| `bit03 2L real/` | 3º foguete | `foguete_novo.ork` | ~100 m real |
| **`bit04 2L script/`** | **4º — otimizado, garrafa 2L** | **`bit04_MODELO_FINAL.ork`** | **369 m** (motor 1,55 L/170 psi) · 388 m (1,8 L) |
| **`bit05 2L humano/`** | **5º — projeto por pesquisa humana, garrafa 2L** | **`bit05_MODELO_FINAL.ork`** | **276 m** (motor 1,55 L/170 psi) |
| **`bit06 1,8L script/`** | **6º — garrafa retornável REDUZIDA (~1,8 L, Ø9,585 cm)** | `bit06_MODELO_FINAL.ork` | **363 m** (1,35 L/170 psi) · 377 m (1,5 L) |
| **`bit07 robusto 2L/`** | **7º — projetado por NOTA multicritério (alcance + robustez a pressão + leveza + margem), garrafa 2L** | `bit07_MODELO_FINAL.ork` | **284 m** a 140 psi · 308 m a 170 psi (0,9 L, 1,34 kg, estab. mín. 1,25 cal) |
| **`bit08 45 graus/`** | **8º — aletas a 45°, 6 aletas** | `bit08_MODELO_FINAL.ork` | ver o `.ork` |
| **`bit09 otimizada/`** | **9º — otimizada, 3 aletas** | `bit09_MODELO_FINAL.ork` | ver o `.ork` |

> **Lançamentos reais de 04/08/2026 — bit04 e bit05 falharam.** A bancada só deu
> 140–150 psi (projeto: 170) e os dois saíram rasos, batendo numa cerca à frente.
> O diagnóstico está em `bit07 robusto 2L/LEIA-ME.md`: a pressão custa só ~11% de
> alcance; o que os dois tinham em comum era **estabilidade mínima de voo de
> 0,24–0,46 calibre** (o mínimo nunca foi restringido nas otimizações antigas —
> só o valor pós-queima). O bit07 nasce com essa restrição corrigida.

Todos os projetos vigentes usam os **materiais reais de construção**:
**ogiva impressa em PLA** (1250 kg/m³) e **aletas de poliestireno 1,0 mm**
(1050 kg/m³), com lastro de **Durepoxi** (1,7 g/cm³) na ponta da ogiva.

## Conteúdo de apoio dentro das pastas

- `bit04/foguete_real/` — estudo digital completo da garrafa 2L: modelo fiel da
  garrafa, calibração dos motores, modelo humano vs otimizado, testes com lastro
  metálico, bancos e planilhas. É a base física de tudo.
- `bitNN/motores/` — família `.eng` daquele foguete
- `bitNN/simulacoes/` ou `otimizacao/` — bancos SQLite e gráficos
- `bitNN/versoes_teste/` — os melhores designs alternativos
- `bit04/backups/` — cópias antigas do .ork

## Outras pastas

| Pasta | O que é |
|---|---|
| `base de lançamento/` | CAD da base (F3D/STEP/STL) |
| `geral/` | Regulamento 20ª OBAFOG 2026, edital, gabaritos, planejamento e o **protocolo do dia de campo** |
| `playlist/` | Vídeos de referência (recorde MOBFOG nível 4 = 488,5 m, Red Bears) |
| `_TODOS_OS_TESTES.xlsx` | Resumo de TODOS os experimentos e simulações |

## Documentos do dia de campo

| Arquivo em `geral/` | O que é |
|---|---|
| `Protocolo_de_Testes_OBAFOG.pdf` | Roteiro do dia: ordem dos testes, ruptura hidrostática, vedação, gatilho, curva pressão × tempo, 5 fichas de registro, kit e segurança |
| `PROTOCOLO-DE-TESTES-LEIA-ANTES.md` | **Leia antes do PDF.** Uma seção dele (o teste do barbante, §2.2) ficou desatualizada e contradiz o diagnóstico do bit07 |
| `Ficha_de_Campo_OBAFOG.pdf` | Ficha de campo |
| `Planejamento_Foguete_OBAFOG_Modelo4.pdf` | Planejamento do foguete + base (v3, a vigente) |
| `EDITAL-TURMA-04.pdf` | Edital da turma |

O protocolo traz três regras que não são negociáveis: **ruptura sempre com água,
nunca com ar**; **teto de pressão = o menor valor de ruptura medido**, não a
média; e **peça esbranquiçada não voa** (cristalização térmica do PET).

## Para abrir os .ork com o motor visível

O motor vem de arquivo `.eng` externo. No OpenRocket:
**Editar → Preferências → Diretórios de curvas de empuxo do usuário** e adicione
a pasta `motores/` do foguete em questão.
