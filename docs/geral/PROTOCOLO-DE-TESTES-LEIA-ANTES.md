# Protocolo de Testes — leia isto antes de levar a campo

O `Protocolo_de_Testes_OBAFOG.pdf` (7 páginas) é o roteiro do dia de campo:
ordem dos testes, ruptura hidrostática, vedação, gatilho, curva pressão × tempo,
lançamentos de baixa pressão, cinco fichas de registro, kit e regras de
segurança. **Quase tudo nele continua valendo e vale seguir à risca.**

Uma seção não vale mais.

## A correção: §2.2, teste do barbante

O protocolo é de **16 de julho de 2026**. Nele, sobre girar o foguete
carregado no barbante:

> "Carregado ele vai cambalhotar — isso é esperado (−0,37 cal), não é defeito.
> Quem resolve isso é o tubo de lançamento."

**Isso ficou para trás.** Em 04/08 o bit04 e o bit05 falharam nos dois
lançamentos reais, e o diagnóstico que saiu daí (`foguetes/bit07-2L/LEIA-ME.md`,
seção 2) é o oposto:

- os dois tinham estabilidade **mínima de voo** de 0,46 e 0,24 calibre;
- a regra do foguetemodelismo pede **≥ 1,0 calibre em todo o voo**, não só
  depois da queima;
- as otimizações antigas restringiam só a estabilidade pós-queima. A mínima
  nunca foi restringida, e foi por aí que os dois passaram;
- o bit07 nasce com a restrição corrigida e chega a **1,25 cal de mínima**,
  abrindo mão de uns 30 m simulados para isso.

Ou seja: margem negativa com a garrafa cheia **é defeito de projeto**, não
característica esperada. O tubo de lançamento ajuda, mas não é o conserto.

**O que fazer com o teste do barbante, então:** continue fazendo. Ele é útil
e barato. Só mude a leitura — se o foguete cambalhotar carregado, isso é
motivo para voltar ao projeto, não para anotar "esperado" e seguir.

## O que continua valendo, sem ressalva

- Ruptura **sempre com água, nunca com ar**. Não é preferência, é a diferença
  entre uma garrafa que rasga e derrama e uma que vira estilhaço.
- Teto de pressão = **o menor valor de ruptura medido**, não a média.
- Peça esbranquiçada não voa (cristalização térmica do PET = material frágil).
- Vedação de verdade se testa **com ar e água com sabão**, não com água. O que
  sai da reação é CO₂; água esconde microfresta que deixa gás passar.
- Rompa o grupo de **controle** (garrafas originais) antes das reduzidas. Sem
  ele o número da reduzida não significa nada.
- Numere as garrafas. Filme em câmera lenta: o lançamento dura ~0,2 s.

## Ficou pendente de conferir

O protocolo cita **CP em 42,6 cm** e margem carregada de **−0,37 cal**, mas não
diz de qual foguete. Pelas datas é anterior ao bit06 e ao bit07. Antes de usar
esses números como referência de bancada, confirme contra o `.ork` vigente do
foguete que você for levar.
