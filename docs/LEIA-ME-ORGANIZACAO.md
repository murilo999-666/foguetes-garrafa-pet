# Disco D: — mapa da organização

Reorganizado em **2026-08-16**. Antes havia **47 itens soltos na raiz**; agora são
**7 grupos**. Nada foi apagado — tudo foi apenas movido.

## Os grupos

| Pasta | O que vai aqui |
|---|---|
| **`1-Competicoes/`** | projetos de competição científica: OBAFOG (foguetes), OBR, FIciências, FEBRACE |
| **`2-Robotica/`** | Arduino, seguidores de linha, sketches e bibliotecas |
| **`3-Escola/`** | trabalhos escolares |
| **`4-Pessoal/`** | arquivos pessoais, escritas, exportações |
| **`5-Programas/`** | `instaladores/` (.exe, .msi) e `ferramentas/` (portáteis) |
| **`6-Backups-outros-PCs/`** | backups de outras máquinas (~60 GB) |
| **`7-Recuperados-revisar/`** | o que o chkdsk recuperou — **precisa da sua conferência** |

Na raiz ficam só coisas do sistema: `$RECYCLE.BIN`, `System Volume Information`, `bootTel.dat`.

## 1-Competicoes/OBAFOG/ — reorganizado por dentro

```
OBAFOG/
├── foguetes/            bit01 … bit08  (um por foguete físico)
├── laboratorios/        estudos digitais que não viraram foguete
├── docs/                geral/, índice, lista de compras, planilhas, dashboard
├── base de lançamento/  CAD da base
├── motores-referencia/  veio da raiz do D: ("motores vinagre openrocket")
└── playlist/            vídeos de referência (5,6 GB)
```

### ATENÇÃO — os caminhos do orx foram atualizados junto

O otimizador tinha **152 referências fixas** a `D:\OBAFOG` em **47 arquivos**
(14 configs + 33 scripts). Todas foram reescritas, e o pipeline foi **testado de
ponta a ponta** (busca → pontuação → salvamento do `.ork`) antes de rodar qualquer
campanha.

Também foi corrigido um problema que só aparece quando a pasta muda de lugar: o
banco SQLite guarda o caminho do motor `.eng` como **texto** dentro do design.
Designs antigos apontavam para o caminho velho e quebravam ao salvar o `.ork`.
Agora o caminho é normalizado na leitura do banco (`normaliza_motor` em
`scripts/bit06_pet_aero.py`).

**Se mover o OBAFOG de novo, refaça a substituição de caminhos** — senão quebra.

## 7-Recuperados-revisar/ — olhe com calma

| Item | O que é |
|---|---|
| **`found.001/`** | **57 arquivos `.eng` — a grade de motores do bit07** (`Bit07-L0_90-P130.eng`…). São os motores por pressão que tinham sumido; o chkdsk recuperou. |
| `found.000/` | 1 arquivo `.chk` — provavelmente lixo |
| `found.002/` | vazia |
| `OBAFOG$pasta/` | sobra de pasta antiga; só tem `impressão/` dentro |
| `Microsoft.Services.Store.winmd` | arquivo solto de instalador |

Deixei aqui em vez de apagar ou devolver ao OBAFOG: os motores do `found.001`
parecem os que faltavam, mas quem confirma se estão íntegros é você.

## Onde foi parar cada coisa

| Antes (raiz do D:) | Agora |
|---|---|
| `OBAFOG/` | `1-Competicoes/OBAFOG/` |
| `OBR/`, `OBR-*.zip` | `1-Competicoes/` |
| `FIciencias - Agrinho/` | `1-Competicoes/` (com os 2 PDFs de regulamento dentro) |
| `PROJETO_EVTOL_FEBRACE/`, `Anexo-I-*.docx` | `1-Competicoes/` |
| `projetos_arduino/`, `controle_ps2_rf/` | `2-Robotica/` |
| `seguidor_linha_competicao/`, `segue-linha_seed/`, `Q1084-Sketch/` | `2-Robotica/` |
| `Adafruit_*.zip`, `PushButton-master.zip` | `2-Robotica/` |
| `Trabalho Geografia`, `Trabalho Historia` | `3-Escola/` |
| `Murilo/`, `escritas minhas/`, `telegram_export/`, `*.mcpack` | `4-Pessoal/` |
| instaladores diversos (.exe/.msi) | `5-Programas/instaladores/` |
| `autoclicker meu/`, `RetroArch-Win64/`, `claude-counter-main*`, `tinytask.*`, `NVIDIA/` | `5-Programas/ferramentas/` |
| `comp_joseivo1/`, `comp_joseivo2/` | `6-Backups-outros-PCs/` |
| `found.00*/`, `OBAFOG$pasta/` | `7-Recuperados-revisar/` |
| `motores vinagre openrocket/` | `1-Competicoes/OBAFOG/motores-referencia/` |
