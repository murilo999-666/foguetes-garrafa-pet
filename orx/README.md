# OpenRocket Optimizer (orx)

Plataforma de otimização automática para OpenRocket: uma IA (ou você) modifica
parâmetros do foguete, executa centenas/milhares de simulações e analisa os
resultados para otimizar o projeto — com algoritmos de grade, aleatório,
hill climbing, simulated annealing, genético, Optuna (TPE/CMA-ES), Nevergrad
e um **modo adaptativo** que estreita o espaço de busca conforme aprende.

Controle do OpenRocket: **API Java oficial** (jar 24.12 + JDK 17 embutido da
própria instalação, via JPype) rodando headless — sem edição frágil de XML.
Toda a superfície de API usada foi verificada por reflexão contra o jar
instalado (`scripts/dump_api.py`).

## Requisitos

- Windows com **OpenRocket 24.12** instalado em `C:\Program Files\OpenRocket`
  (outros caminhos: configure `paths.openrocket_dir` no YAML)
- Python 3.11+

## Instalação

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e .[dev]
```

## Uso rápido (CLI)

```powershell
$py = ".venv\Scripts\python"

& $py optimize.py info                     # componentes do foguete + parâmetros
& $py optimize.py params                   # baseline (valores atuais do .ork)
& $py optimize.py simulate                 # simula o baseline
& $py optimize.py simulate --design '{\"fin_root_chord\": 9, \"nose_shape\": \"OGIVE\"}'
& $py optimize.py optimize                 # roda a otimização do YAML
& $py optimize.py optimize --algorithm optuna --evaluations 500
& $py optimize.py best                     # melhor design da última run
& $py optimize.py compare                  # resumo automático (faixas ideais, categorias, influência)
& $py optimize.py compare --runs 3,4,5     # compara algoritmos entre runs
& $py optimize.py plot                     # convergência, histogramas, heatmap, Pareto, 3D
& $py optimize.py export --format csv
& $py optimize.py save-best --out results\melhor.ork
& $py optimize.py motors C6                # busca no banco de motores (1096 conjuntos)
```

Tudo é dirigido por `config/default.yaml`: arquivo `.ork` base, parâmetros
otimizáveis (com faixas/unidades), objetivo, restrições, algoritmo, paralelismo.

## Uso pelo Claude Code (ou Python)

```python
from orx.mcp.tools import Session

s = Session("config/default.yaml")
s.components()                       # árvore do foguete
s.simulate()                         # baseline
s.change_fin(root_chord=9, height=5) # acumula no design de trabalho
s.change_nose(shape="OGIVE")
s.change_ballast(12)
s.simulate()                         # simula o design acumulado
s.run_batch([{...}, {...}])          # lote de designs
s.optimize(algorithm="adaptive", max_evaluations=300)
s.best_design()                      # melhor design viável
s.compare()                          # análise textual automática
s.plot(); s.export_results()
s.save_design("melhor.ork")
```

## Conceitos

- **Parâmetro** (`parameters` no YAML): `component` (nome no .ork) + `attribute`
  (vira setter Java: `root_chord` → `setRootChord`; especiais: `shape`,
  `position`, `cd`, `deploy_delay/altitude/event`, `override_mass`, `motor`,
  `ejection_delay`) + `unit` (mm/cm/m/g/kg/deg) + faixa (`low/high/step`) ou
  `choices` (categórico).
- **Objetivo**: nome de métrica ou expressão (`apogee - 2*ground_hit_velocity`),
  `maximize`/`minimize`. Métricas disponíveis: apogeu, vel./acel. máximas, Mach,
  tempos (apogeu/voo/ejeção), velocidades (ejeção/pouso/saída do trilho),
  **distância horizontal até o pouso**, estabilidade (estática/mín/máx em
  calibres), CP, CG, massa, comprimento.
- **Restrições**: `metric` + `min`/`max`. Violou → design descartado
  (feasible=0 no banco, penalidade para o otimizador).
- **Runs**: cada otimização vira uma run no SQLite (`results/orx.sqlite`),
  com todas as avaliações (parâmetros JSON + métricas JSON + score).

## Modo adaptativo

`algorithm: adaptive` com `profile: wide | balanced | local`:
1. exploração ampla (random);
2. análise do histórico → **estreita bounds** à região do top-25%, descarta
   categorias fracas, reporta parâmetros de baixa influência;
3. modelagem com Optuna TPE no espaço estreitado;
4. refinamento local (hill climbing) em volta do melhor.

Designs duplicados (tolerância 0,5% da faixa) não são re-simulados.

## Paralelismo

`batch.workers: N` roda N processos, cada um com sua própria JVM (limitação do
JPype: 1 JVM/processo). Válido para algoritmos com suporte a lote (grid,
random, genetic, optuna, nevergrad, adaptive).

## Estrutura

```
src/orx/
  bridge/      JVM headless + wrappers verificados da API Java (24.12)
  config/      YAML -> dataclasses validadas
  rocket/      aplicação de designs via setters oficiais
  simulation/  runner (1 sim) e métricas de voo
  objectives/  objetivo (expressões) e restrições
  optimizer/   espaço de busca, algoritmos ask/tell, engine, adaptativo
  results/     SQLite + export CSV/JSON
  analysis/    comparações automáticas em linguagem natural + sensibilidade
  plots/       convergência, histogramas, efeitos, heatmap, Pareto, 3D
  mcp/         fachada de ferramentas p/ Claude Code
  cli.py       CLI (optimize.py)
tests/         14 unitários + 4 integração (pytest -m integration)
```

Novo algoritmo de otimização = uma subclasse de `Optimizer` com
`@register("nome")` em `src/orx/optimizer/` — nada mais muda.

## Testes

```powershell
.venv\Scripts\python -m pytest -q                     # unitários (sem JVM)
.venv\Scripts\python -m pytest -q -m integration      # com OpenRocket real
```
