# Manual de montagem e lançamento — bit07_B (maior alcance)

Foguete de garrafa PET 2 L, coifa PLA impressa + aletas de polietileno 1 mm.
Baseado em `bit07_B_PLA_polietileno.ork`. Todos os números de voo vêm de simulação
no OpenRocket com **os materiais reais desta versão** (motor VinagreReal calibrado
no voo de 275 m, k=1,70).

> Variante "maior alcance": é **pesada de propósito** (286 g de lastro) e voa mais
> longe justamente por isso — alto coeficiente balístico. Se você quer mais margem
> de estabilidade e menos peso, o `bit07_MODELO_FINAL.ork` (0,9 L, 180 g) é o irmão
> leve; este aqui é o que vai mais longe.

---

## 1. Especificação

| Item | Valor |
|---|---|
| Corpo | garrafa PET 2 L **retornável** (a de sempre) |
| Coifa | parabólica, parâmetro 0,71 — **comprimento 29,2 cm**, Ø base 10,4 cm, PLA parede 1,2 mm |
| Aletas | **4 unidades**, polietileno **1,0 mm** (bordo de ataque 20,1 cm · fuga 19,7 cm · raiz 8,5 cm · ponta 1,1 cm) |
| Lastro | **286 g** de Durepoxi no bico da coifa (faixa segura 250–330 g) |
| Comprimento total | ~63,8 cm |
| Massa seca | ~499 g (estrutura ~213 g + lastro 286 g) |
| CG / CP | 36,0 cm / 47,9 cm a partir da ponta |
| Estabilidade (projeto) | **1,47 cal** a 1,55 L (nunca abaixo de 1,0 em nenhuma carga) |

---

## 2. Lista de materiais

- 1 garrafa PET 2 L retornável em bom estado (sem vincos, rosca intacta)
- Coifa impressa: `bit07_B_coifa_PLA_parte1_base.stl` + `..._parte2_ponta.stl` (PLA)
- 1 chapa de **polietileno 1,0 mm** (dá pras 4 aletas, ~15 × 19 cm por aleta)
- Molde das aletas: `bit07_B_aleta_molde.pdf` (imprimir a 100 %)
- **Durepoxi** (massa epóxi) para o lastro — separe ~300 g
- Cola: cianoacrilato (super cola) ou epóxi; e cola de contato/PU para colar PE
- Vinagre 4 %, bicarbonato de sódio, balança de cozinha, manômetro na base

---

## 3. Montagem

### 3.1 Coifa (2 peças + encaixe)
1. Imprima as duas metades em PLA (parede 1,2 mm ≈ 3 perímetros, 5–10 % de preenchimento).
2. A **parte de baixo** tem um colar interno; a **ponta** encaixa por cima e desliza
   sobre o colar até bater no ombro. Folga de 0,35 mm — entra justo.
3. Teste o encaixe a seco. Passe epóxi/cianoacrilato no colar e una as metades,
   apertando até o batente. Limpe o excesso. Deixe curar.
   *(detalhes no `LEIA-ME.md` desta pasta.)*

### 3.2 Lastro (Durepoxi no bico)
1. Com a coifa **já colada**, preencha o **bico** (a ponta interna) com Durepoxi.
2. **Pese enquanto enche**: alvo **286 g** de massa epóxi. Vai concentrada na ponta —
   é o que joga o CG pra frente e dá estabilidade.
3. Tolerância: qualquer coisa entre **250 e 330 g** voa bem (ver tabela do item 4).
   Se passar um pouco, tudo bem — nesta versão peso extra ajuda o alcance.
4. Deixe curar de cabeça pra baixo pra massa assentar no bico.

### 3.3 Aletas (recorte do polietileno)
1. Imprima `bit07_B_aleta_molde.pdf` **a 100 % / tamanho real** (confira a barra de 100 mm com a régua).
2. Cole/fixe o molde na chapa de PE e recorte **4 aletas** idênticas com estilete.
   A linha verde tracejada é a **raiz** (aresta que cola no corpo).
3. Cole as 4 aletas **igualmente espaçadas (90°)** ao redor da base da garrafa,
   raiz alinhada com o eixo do foguete. **Alinhamento de aleta é o item nº 1** —
   desalinhamento foi o suspeito de bit04/bit05 não subirem. Use um gabarito/esquadro.
4. PE é difícil de colar: **lixe a área de cola** da aleta e do corpo e use cola de
   contato ou PU (epóxi comum descola do PE liso). Reforce a raiz com uma tira.

---

## 4. Lastro: quanto pesar (a 1,55 L / ~170 psi)

| Lastro | Massa seca | Estabilidade | Alcance | Apogeu |
|---:|---:|---:|---:|---:|
| 150 g | 363 g | 1,22 cal | 291 m | 75 m |
| 200 g | 413 g | 1,32 cal | 302 m | 74 m |
| 250 g | 463 g | 1,41 cal | 310 m | 73 m |
| **286 g** | **499 g** | **1,47 cal** | **313 m** | 72 m |
| 330 g | 543 g | 1,54 cal | 314 m | 70 m |
| 380 g | 593 g | 1,63 cal | 315 m | 68 m |

**Leitura:** aqui, mais lastro = mais estabilidade **e** um tico mais de alcance (satura
perto de 330 g). Não precisa ser perfeito: **250–330 g** é a faixa boa. Alvo 286 g.

---

## 5. Motor: vinagre + bicarbonato × pressão × alcance

Cada carga de vinagre 4 %, reagida com bicarbonato **em excesso**, dá uma pressão
nominal e um alcance. Bicarbonato "de uso" = ~130 g por litro de vinagre (o que você
já faz: ~200 g a 1,55 L). O mínimo estequiométrico é ~56 g/L — o excesso garante
reação completa.

| Vinagre | Bicarbonato (uso) | Pressão nominal | Alcance | Apogeu | Estab. mín | Saída trilho |
|---:|---:|---:|---:|---:|---:|---:|
| 0,60 L | ~80 g | 67 psi | 147 m | 28 m | 2,16 cal | 36 m/s |
| 0,80 L | ~105 g | 89 psi | 203 m | 42 m | 1,92 cal | 38 m/s |
| 1,00 L | ~130 g | 111 psi | 247 m | 53 m | 1,74 cal | 37 m/s |
| 1,20 L | ~155 g | 133 psi | 279 m | 62 m | 1,62 cal | 37 m/s |
| 1,40 L | ~180 g | 154 psi | 299 m | 68 m | 1,53 cal | 36 m/s |
| **1,55 L** | **~200 g** | **170 psi** | **312 m** | 72 m | 1,47 cal | 35 m/s |
| 1,70 L | ~220 g | 186 psi | 323 m | 75 m | 1,43 cal | 35 m/s |
| 1,80 L | ~235 g | 196 psi | 326 m | 75 m | 1,38 cal | 33 m/s |

### Como escolher a carga
- **Recomendado: 1,55 L → ~170 psi → ~312 m.** É o ponto onde a química foi calibrada
  no seu voo real, e a garrafa 2 L retornável aguenta bem.
- **Máximo alcance: 1,7–1,8 L → 186–196 psi → 323–326 m.** Só **se** a garrafa e a base
  aguentarem essa pressão com segurança (ver item 8). Ganha ~14 m sobre 1,55 L.
- Abaixo de 1,2 L o alcance cai rápido — não vale, a menos que você queira um voo curto.

### ⚠️ Pressão é NOMINAL (reação completa + boa vedação)
A coluna "pressão nominal" supõe que **todo** o CO₂ ficou no sistema. Se a bancada
entregar menos (bicarbonato velho, vinagre fraco, vazamento na rosca/bocal, reação
incompleta ao fechar), a pressão **e** o impulso caem juntos — foi exatamente o que
derrubou bit04 e bit05 (só deram 140–150 psi). **Meça a pressão no manômetro e anote.**
Se mediu menos que a nominal da sua carga, espere menos alcance que a tabela.

---

## 6. Ângulo de lançamento

Alvo **55°** (medido da vertical). Entre 50° e 60° o alcance muda pouco (~4 m); o topo
é plano. Não perca tempo afinando o ângulo — gaste conferindo a firmeza da base e o
alinhamento do tubo-guia.

---

## 7. Procedimento de lançamento (checklist)

**Preparação (mesa)**
- [ ] Garrafa sem vincos/trincas; rosca e vedação boas
- [ ] Lastro pesado e curado (alvo 286 g, faixa 250–330 g)
- [ ] 4 aletas alinhadas (90°), cola curada, raiz reforçada
- [ ] Coifa colada, encaixe firme
- [ ] Vinagre medido (ex.: 1,55 L) e bicarbonato pesado (~200 g)

**Na base**
- [ ] Base firme e nivelada; tubo-guia sem folga e **sem tocar as aletas**
- [ ] Ângulo ~55°
- [ ] Manômetro conectado e funcionando
- [ ] Bicarbonato dentro, fechar rápido, travar na base
- [ ] **Pressão medida e anotada** (compare com a nominal da carga)
- [ ] Área livre: ninguém e nada (cerca!) no primeiro terço da trajetória
- [ ] Contagem → soltar

**Depois**
- [ ] Anotar pressão real, alcance, apogeu, o que deu certo/errado
- [ ] Conferir aletas e coifa (dano no pouso?)

---

## 8. Segurança de pressão

Garrafa PET 2 L retornável aguenta bem a faixa de trabalho do projeto, mas **pressão
alta é energia armazenada**. Regras:
- Até ~170 psi: faixa validada no seu histórico (1,55 L). OK com garrafa boa.
- **180–200 psi (cargas 1,7–1,8 L): só com garrafa que você já testou** e pressurizando
  com todos atrás de anteparo/à distância. Se a garrafa tiver qualquer marca, descarte.
- Nunca fique sobre/à frente do foguete pressurizado. Pressurize e afaste-se; solte à distância.
- Descarte garrafas após alguns voos em alta pressão (fadiga do PET).

---

## 9. Números esperados no dia (carga 1,55 L, ~170 psi, vento 2 m/s, 55°)

| | |
|---|---|
| Saída do tubo-guia | ~35 m/s |
| Apogeu | ~72 m |
| **Alcance** | **~312 m** (299 m a 154 psi · 326 m a 196 psi) |
| Estabilidade | 1,47 cal no lançamento |
| Massa seca | ~499 g |

*Alcance real tende a bater ou superar a tabela se a chapa de PE for mais leve (LDPE)
ou o PLA for impresso com pouco preenchimento — a massa cai e o alcance sobe um pouco.*
