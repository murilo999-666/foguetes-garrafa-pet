# OBAFOG — foguetes de garrafa PET

Repositório **privado** da equipe: projetos, simulações, arquivos de fabricação e
a plataforma de otimização usada para projetar os foguetes.

Motor: **vinagre 4 % + bicarbonato em excesso**, modelado pela física do CO₂ (lei de
Henry + blowdown bifásico) e calibrado em dois dados reais medidos pelo Murilo —
**170 psi com 1,55 L** (bancada) e o **voo real de 275 m** (fator de escoamento k = 2,17).
Atenção: esse voo de 275 m foi do **bit02**, não do bit03, e não existe `.ork` do
bit02 — ver o aviso em `docs/_INDICE.md`.

---

## Como o repositório está organizado

```
foguetes/          um diretório por foguete FÍSICO (bit01 … bit08)
laboratorios/      estudos digitais que não viraram foguete
base-de-lancamento/ CAD da base (F3D / STEP / STL)
docs/              regulamento, índices, planilhas, referências
orx/               a plataforma de otimização (código-fonte)
```

Dentro de cada foguete, o arquivo `bitNN_MODELO_FINAL.ork` (ou equivalente marcado
no LEIA-ME da pasta) é **o projeto vigente**; o resto é histórico e estudo.

---

## Os foguetes

| Pasta | O que é | Projeto vigente | Situação |
|---|---|---|---|
| `foguetes/bit01` | 1º foguete | ogivas em STL | histórico |
| `foguetes/bit02` | 2º foguete | ogivas em STL | histórico |
| `foguetes/bit02` | 2º — garrafa 2 L | só STL de ogiva | **voou 275 m reais** (o único voo bom, sem modelo) |
| `foguetes/bit03` | 3º — garrafa 2 L | `foguete_novo.ork` | voou ~100 m |
| `foguetes/bit04-2L` | 4º — otimizado, 2 L | `bit04_MODELO_FINAL.ork` | ❌ **falhou no lançamento** |
| `foguetes/bit05-2L` | 5º — projeto humano, 2 L | `bit05_MODELO_FINAL.ork` | ❌ **falhou no lançamento** |
| `foguetes/bit06-1.8L` | 6º — garrafa **reduzida** ~1,8 L | `bit06_B_CONSTRUTIVEL.ork` | ✅ **reprojetado** (2026-08-11) |
| `foguetes/bit07-2L` | 7º — projeto por **nota multicritério**, 2 L | `bit07_MODELO_FINAL.ork` | ✅ pronto para construir |
| `foguetes/bit08` | reservado | — | — |

---

## A lição que organiza tudo

> **04/08/2026 — bit04 e bit05 foram lançados e não subiram.** Saíram rasos e
> bateram numa cerca à frente.

A bancada só entregou 140–150 psi, contra os 170 psi de projeto. Mas o diagnóstico
mostrou que **a pressão explica só ~11 % do alcance** — a física dizia que os dois
deveriam ter voado. O que eles tinham em comum era outra coisa:

| Projeto | Estabilidade **mínima durante o voo** |
|---|---|
| bit04 | **0,46 cal** |
| bit05 | **0,24 cal** |
| bit06 antigo | **0,51 cal** |

As otimizações antigas só restringiam a estabilidade **estática** e a **pós-queima**,
nunca a **mínima em voo**. E em foguete de garrafa o CG fica atrás enquanto ainda há
líquido — a estabilidade despenca justo no meio da subida, onde ninguém olhava.

Do bit07 em diante todo projeto carrega **`stability_min ≥ 1,0 cal` como restrição
dura**, verificada em todos os cenários de pressão/rendimento.

### A segunda lição: pressão nominal ≠ pressão real

O bicarbonato entra em excesso, então quem limita o CO₂ é o **ácido do vinagre**.
Cada carga tem um **teto físico** de pressão, que só é atingido se a reação render
tudo e nada vazar. Os projetos antigos foram dimensionados exatamente nesse teto
(η = 1,00) — por isso prometiam pressões que a bancada nunca entregou (η real ≈ 0,85).

O bit06 já é otimizado varrendo o **rendimento da reação (η = 0,70 … 1,00)**, o que
garante que toda combinação simulada é fisicamente possível.

---

## Projetos vigentes em detalhe

### bit07 (garrafa 2 L) — `foguetes/bit07-2L`
Ogiva parabólica **24,8 cm em PLA 1,2 mm** (impressa em 2 peças com encaixe),
**3 aletas de polietileno 1,0 mm**, lastro **180 g** de Durepoxi.
Carga recomendada **1,0 L de vinagre a 55°** → **256 m**, estabilidade 1,20 cal.

Manuais prontos em `impressão/MODELO_FINAL/`:
`MANUAL_bit07_FINAL_MONTAGEM.pdf` e `MANUAL_bit07_FINAL_LANCAMENTO.pdf`,
mais os STLs da coifa e os moldes 1:1 das aletas.

⚠️ Com 1,7 L e 1,8 L a estabilidade cai para 0,97 e 0,95 cal — **reprova**.

### bit06 (garrafa reduzida ~1,8 L) — `foguetes/bit06-1.8L`
Reprojetado do zero com **99.920 simulações** (nota multicritério 0–100).
Ogiva parabólica **27,5 cm em PLA 1,2 mm** (2 peças), **3 aletas de polietileno
1,0 mm**, lastro **146 g**. Carga **1,50 L a 54°** → **281 m** no cenário realista
(η = 0,80), estabilidade 1,31 cal.

O projeto anterior está em `_MODELO_ANTIGO_falhou/` com um README explicando a
aposentadoria: voava mais longe no papel (329 m) com **0,51 cal** de estabilidade.

---

## `orx` — a plataforma de otimização

`orx/` é o pacote Python que projeta os foguetes: dirige o **OpenRocket 24.12**
headless via JPype, aplica designs paramétricos no `.ork`, simula em lote e otimiza.

```
orx/src/orx/         bridge (JVM/OpenRocket), rocket, simulation, optimizer, results
orx/config/*.yaml    espaço de busca, objetivo e restrições de cada campanha
orx/scripts/         campanhas, geradores de motor, exportadores de fabricação
```

Pontos que valem saber antes de mexer:

- **1 JVM por processo** (limitação do JPype) → paralelismo é `multiprocessing` com
  spawn. Scripts **precisam** de guard `if __name__ == "__main__":`, senão o pool trava.
- A JVM sobe enxuta (`-Xms32m`, SerialGC) porque a máquina de origem está **sem
  arquivo de paginação**; com o padrão do G1 seis workers estouravam o limite de
  commit do Windows e a busca morria no meio.
- Campanhas longas rodam **um bloco por processo** (`bit06_orquestrador.py`), o que
  devolve toda a memória ao SO entre blocos e sobrevive à falha de um bloco isolado.
- Massa de recheio que segue perfil cônico (o lastro de Durepoxi no bico) precisa ser
  discretizada em vários discos — modelar como um cilindro único erra o CG em ~1,5 cm.

### Reproduzir uma campanha (exemplo: bit06)

```powershell
cd orx
python -m venv .venv; .venv\Scripts\pip install -e .
.venv\Scripts\python scripts\motor_bit06_rendimento.py   # família de motores
.venv\Scripts\python scripts\bit06_orquestrador.py       # ~100 mil simulações
.venv\Scripts\python scripts\bit06_variantes.py          # variantes A/B/C + confronto
.venv\Scripts\python scripts\exportar_fabricacao.py <arquivo.ork> --saida <pasta> --nome bit06
```

`exportar_fabricacao.py` lê a geometria **do próprio `.ork`** e gera o STL da coifa
(inteira e cortada em 2 peças com encaixe) e os moldes 1:1 das aletas em SVG/PDF/DXF.
As malhas saem verificadas como estanques (*watertight/manifold*).

---

## Abrir os `.ork` com o motor visível

Os motores vêm de arquivos `.eng` externos. No OpenRocket:
**Editar → Preferências → Diretórios de curvas de empuxo do usuário** e adicione a
pasta `motores/` do foguete em questão.

---

## O que NÃO está versionado (e por quê)

O material original em `D:\OBAFOG` soma **8,0 GB em 73.519 arquivos**. Ficou de fora
o que o Git não comporta ou o que é regenerável:

| Conteúdo | Tamanho | Motivo |
|---|---|---|
| `playlist/` (25 vídeos) | 5,6 GB | conteúdo de terceiros (YouTube); índice preservado em `docs/playlist-referencias.md` |
| Bancos `.sqlite` de simulação | ~1,7 GB | regeneráveis; o maior tem 780 MB (acima do limite de 100 MB/arquivo do GitHub) |
| `_motores_gerados/` | 72.783 arquivos | `.eng` gerados por varredura paramétrica |
| Instalador do OpenRocket | 124 MB | software baixável |
| CSVs brutos de otimização | 80 + 45 MB | dumps regeneráveis; os rankings curados estão versionados |
| Logs de execução e `hs_err_pid*` | ~25 MB | saída de console |

Tudo isso continua no computador do Murilo, em `D:\OBAFOG`.
