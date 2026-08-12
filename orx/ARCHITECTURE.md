# Arquitetura — Plataforma de Otimização Automática para OpenRocket

## Decisão central: como controlar o OpenRocket

Foi verificado (inspecionando o jar instalado em `C:\Program Files\OpenRocket`):

- Instalação local: **OpenRocket 24.12** (`jar/OpenRocket-24.12.jar`) com **JDK 17 embutido** (`jre/`).
- Na 24.12 os pacotes Java são `info.openrocket.core.*` / `info.openrocket.swing.*`
  (o antigo `net.sf.openrocket` não existe mais — por isso o `orhelper` do PyPI,
  preso ao OpenRocket 15.03/Java 8, foi **descartado**).
- Classes-chave confirmadas no jar: `GeneralRocketLoader`, `GeneralRocketSaver`,
  `Simulation`, `FlightDataType`, `BarrowmanCalculator`, `MassCalculator`,
  `GuiModule`, `PluginModule`, `Application`.

**Escolha: JPype 1.x carregando o jar oficial com o JDK 17 embutido do próprio
OpenRocket.** Isso é a "API oficial Java" (prioridade 1 do requisito): chamamos
os mesmos objetos que a GUI usa, sem parsear XML na unha. A edição direta do
`.ork` fica como backend alternativo possível (a interface de backend é
abstrata), mas não é necessária.

Consequência importante: **JPype só permite 1 JVM por processo e ela não pode
ser reiniciada**. Logo, paralelismo = `multiprocessing`, com um worker = um
processo = uma JVM própria, recebendo tarefas por fila.

## Camadas

```
optimize.py / CLI
      │
  mcp/tools.py          ← fachada de ferramentas p/ Claude Code (simulate, change_fin, …)
      │
  optimizer/            ← algoritmos (ask/tell) + modo adaptativo
      │
  objectives/           ← função objetivo + restrições (declarativas, YAML)
      │
  simulation/           ← runner (1 sim), batch (N sims, paralelo), extração de métricas
      │
  rocket/               ← modelo de parâmetros: aplicar {param: valor} num .ork carregado
      │
  bridge/               ← JVM (JPype) + wrappers finos sobre info.openrocket.core
      │
  results/ (SQLite)  analysis/  plots/  config/  utils/
```

### `bridge/` — ponte Java
- `jvm.py`: localiza jar + jvm.dll (auto-descoberta + override no YAML), inicia a
  JVM headless (`-Djava.awt.headless=true`), injeta Guice
  (`GuiModule` + `PluginModule`, `Application.setInjector`, `startLoader()`).
- `orjava.py`: helpers — carregar/salvar documento, listar componentes,
  rodar `Simulation.simulate()`, ler `FlightDataBranch` como numpy,
  calcular CP/CG/estabilidade via `BarrowmanCalculator`/`MassCalculator`.

### `rocket/` — modelo de parâmetros
- Cada parâmetro modificável é um `ParameterSpec` declarativo:
  `nome`, `component` (busca por nome/tipo na árvore), `attribute`
  (mapeado para getter/setter Java), `bounds`, `unit`, `type`
  (contínuo/inteiro/categórico — ex.: formato do cone).
- `apply_design(doc, {param: valor})` altera o documento carregado sempre por
  setters oficiais → o projeto permanece válido; `enableEvents`/listeners do OR
  cuidam da consistência.
- Cobre: cone (comprimento/formato/espessura), tubo, transição, aletas
  (todas as dimensões, forma, posição, espessura), massas/lastro (valor e
  posição), paraquedas (diâmetro/Cd/evento), motor (troca por designação),
  materiais, sobremassa (override), posição de qualquer componente.

### `simulation/`
- `runner.py`: executa 1 simulação com opções (vento, ângulo do trilho, etc. do
  YAML) e devolve `FlightMetrics` (dataclass): apogeu, vel. máx, acel. máx,
  tempo de voo, tempo/velocidade na ejeção, **distância horizontal do ponto de
  lançamento ao pouso** (posição E/N no pouso), CP, CG, calibre de estabilidade
  (mín. durante o voo e estático), massa, comprimento, eventos.
- `batch.py`: fila de designs → pool de processos-worker (cada um com sua JVM),
  resultados escritos no SQLite conforme chegam; tolerante a falha de sim
  individual.

### `objectives/` e restrições
- Objetivo = nome de métrica ou expressão sobre métricas (ex.:
  `horizontal_distance`, `apogee - 0.1*max_velocity`), com `maximize|minimize`.
- Restrição = `métrica + min/max` (ex.: `stability_min: {min: 1.0, max: 3.0}`).
  Violou → avaliação marcada `infeasible` no banco e descartada pelo otimizador
  (penalidade configurável para algoritmos que precisam de valor).
- Trocar objetivo = editar YAML; multiobjetivo suportado guardando todas as
  métricas de cada avaliação (Pareto em `analysis/`).

### `optimizer/`
- Interface `Optimizer` estilo **ask/tell**: `ask(n) -> [designs]`,
  `tell(design, metrics, score, feasible)`. Registry por nome no YAML.
- Implementações: grid, random, hill climbing, simulated annealing, genético,
  Optuna (TPE e CMA-ES via sampler), e adaptador genérico p/ Nevergrad
  (opcional, se instalado).
- **Modo adaptativo** (`adaptive.py`): meta-estratégia que lê o histórico do
  SQLite e alterna exploração↔refinamento (perfis `wide|balanced|local`),
  estreita bounds em regiões promissoras, desprioriza categorias ruins e
  parâmetros de baixa influência (correlação/variância), evita duplicatas
  (hash de design com tolerância).

### `results/` — SQLite
- Tabelas: `runs` (sessão de otimização: config, objetivo, algoritmo),
  `evaluations` (1 linha por simulação: JSON dos parâmetros + todas as
  métricas + score + feasible + timestamps), índice por run/score.
- Export: CSV/JSON por avaliação e do agregado; timeseries opcional por sim.

### `analysis/` e `plots/`
- `compare.py`: comparações automáticas em linguagem natural ("aletas
  trapezoidais aumentaram X% a distância", "lastro ideal entre A e B g") via
  agrupamento por categoria e faixas de melhor desempenho.
- `sensitivity.py`: influência de cada parâmetro (correlação + fANOVA do Optuna
  quando disponível).
- `plots/`: convergência, histogramas, dispersão/heatmap por par de parâmetros,
  Pareto front, 3D, comparação entre algoritmos. Tudo salvo em `results/plots/`.

### Interface
- CLI: `python optimize.py run|simulate|best|compare|plot|export ...`
  (argparse; tudo dirigido pelo YAML + overrides de linha de comando).
- `mcp/tools.py`: funções de alto nível para o Claude Code
  (`simulate`, `change_fin`, `change_nose`, `change_ballast`, `change_motor`,
  `run_batch`, `compare`, `export_results`, `best_design`, `search`,
  `optimize`) — mesmas rotinas da CLI, importáveis; preparado para virar
  servidor MCP real depois.

## Etapas de desenvolvimento (com verificação a cada uma)

1. **M1** — Bridge JPype (smoke test com exemplo oficial). ✅ gate: apogeu real impresso.
2. **M2** — `rocket/`: ler/alterar/salvar parâmetros; gate: alterar aleta e ver CP mudar.
3. **M3** — `simulation/runner`: métricas completas incl. distância horizontal.
4. **M4** — `results/` SQLite + `batch` paralelo; gate: N sims paralelas gravadas.
5. **M5** — `objectives/` + otimizadores + adaptativo; gate: otimização curta converge.
6. **M6** — `analysis/` + `plots/`.
7. **M7** — CLI, fachada de ferramentas, testes, README.
