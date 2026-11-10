---
norma: ABNT NBR 5410:2004
id: nbr-5419-1
secao: anexo-e
titulo: Anexo E (informativo) Correntes de surto devido às descargas atmosféricas
  em diferentes pontos da instalação
---

[Arquivo único](../nbr-5419-1.md)

## Anexo E (informativo) Correntes de surto devido às descargas atmosféricas em diferentes pontos da instalação

### E.1 Geral

**E.1.1** Para dimensionar adequadamente condutores, *DPS* e outros componentes, é fundamental avaliar a ameaça de surtos no ponto específico de instalação. Essa avaliação deve considerar as correntes provenientes de descargas atmosféricas e os efeitos de indução nos laços da instalação. A ameaça identificada deve ser inferior aos níveis de suportabilidade dos componentes utilizados, conforme estabelecido por ensaios apropriados, quando necessário.

**E.1.2** O surto causado por descargas atmosféricas pode ser estimado utilizando valores simplificados, com base nas considerações a seguir.

### E.2 Correntes de surto devidas às descargas atmosféricas na estrutura (fonte de dano S1)

#### E.2.1 Correntes de surto que fluem por partes condutivas externas e linhas conectadas à estrutura

**E.2.1.1** Na proteção contra descargas atmosféricas diretas na estrutura, é fundamental considerar a distribuição da corrente entre as partes condutivas externas, as linhas conectadas à estrutura e o subsistema de aterramento.

**E.2.1.2** Quando a corrente de descarga atmosférica é conduzida à terra, ela se divide entre o subsistema de aterramento, as partes condutivas externas e as linhas elétricas, seja diretamente ou por meio de *DPS* a elas conectados.

(E.1)

*I*<sub>F</sub> = *k*<sub>e</sub> *× I / n*

onde

*k*<sub>e</sub> é o fator de divisão da corrente;

*n* é o número total de partes condutivas externas e linhas elétricas aéreas e enterradas conectadas à estrutura;

*I* é a corrente da descarga atmosférica relevante para o nível de proteção contra descargas atmosféricas (*NP*) considerado;

*I*<sub>F</sub> é a parcela da corrente da descarga atmosférica que flui por cada parte condutiva e linhas externas.

**E.2.1.3** O fator de divisão da corrente depende de:

- a impedância convencional de aterramento de partes condutivas e linhas enterradas e aéreas conectadas;

- a impedância convencional de aterramento do subsistema de aterramento da estrutura.

**E.2.1.4** Para estruturas com subsistema de aterramento conforme a ABNT NBR 5419-3, o valor do fator de divisão de corrente pode ser assumido como *k*<sub>e</sub> = 0,5.

> **NOTA** Uma avaliação mais precisa do *k*<sub>e</sub> é possível considerando as características das linhas conectadas e da impedância de aterramento convencional real da estrutura e das partes conectadas.

#### E.2.2 Fatores que influenciam na divisão da corrente de descargas atmosféricas e sua carga em linhas elétricas de energia

**E.2.2.1** Cada um dos *n*’ condutores da linha leva para fora da estrutura uma parte igual *I*’<sub>F</sub> da corrente de descarga atmosférica.

**E.2.2.2** O valor de *I*’<sub>F</sub> depende de:

- o tipo de linha: aérea ou enterrada;

- a característica da linha: blindada ou não blindada;

- o nível de isolação da linha;

- o número de condutores da linha;

- a impedância convencional de aterramento dos postes para linhas aéreas;

- a resistividade do solo para linhas enterradas.

**E.2.2.3** Os maiores valores de *I*’<sub>F</sub> são obtidos no caso de uma linha aérea não blindada de dois condutores com baixos valores de nível de isolação e de impedância de aterramento dos postes.

**E.2.2.4** Para cálculos detalhados, vários fatores podem influenciar a amplitude e a forma destes surtos:

- o comprimento do cabo pode influenciar a divisão de corrente e as características de forma de onda devido à relação L/R;

- diferentes impedâncias de condutores de neutro e de fase podem influenciar a divisão de corrente e sua carga entre condutores de linha (ver Nota 1);

- diferentes impedâncias do transformador podem influenciar a divisão de corrente e sua carga (este efeito é desprezável, se o transformador estiver protegido por *DPS* que curto-circuita sua impedância);

- a relação entre as impedâncias convencionais de aterramento do transformador e os itens do lado da carga pode influenciar a divisão de corrente e sua carga (quanto menor a impedância do transformador, maior é a corrente de surto que flui para o sistema de baixa tensão);

- instalações consumidoras em paralelo provocam uma redução da impedância do sistema de baixa tensão; isso pode aumentar a corrente de descargas atmosféricas parcial que flui para este sistema.

> **NOTA 1** No caso de esquema TN, se o condutor de neutro (N) tiver vários pontos aterrados, a menor impedância de N em comparação com os condutores de fase L1, L2 e L3 pode resultar em muito mais corrente fluindo pelo condutor de N. O valor da corrente que flui por cada condutor depende do valor da impedância de cada condutor.

> **NOTA 2** Ver ABNT NBR 5419-4:2026, Anexo D, para obter mais informações.

**E.2.2.5** Os valores aproximados da corrente *I*’<sub>F</sub> que flui por condutores da linha ligada à estrutura podem ser avaliados como indicado em E.2.3.

#### E.2.3 Correntes de surto fluindo por condutores da linha conectada à estrutura

**E.2.3.1** Se as linhas de entrada (por exemplo, linhas elétricas de energia e de sinal) estiverem sem blindagem ou não forem roteadas em condutos metálicos, presume-se que cada um dos *n*’ condutores da linha carrega uma porção igual *I*’<sub>F</sub> da corrente de descargas atmosféricas

(E.2)

*I’*<sub>F</sub> = *k’*<sub>e</sub> *× I*

onde

*I*’<sub>F</sub> é a parcela da corrente de descargas atmosféricas que flui por cada condutor da linha;

(E.3)

*k’*<sub>e</sub> = *k*<sub>e</sub> / *n*’

onde

*n’* é o número total de condutores

**E.2.3.2** Para as linhas blindadas com ligação equipotencial na entrada, os valores do fator de divisão de corrente *k*’<sub>e</sub> para cada um dos *n’* condutores de uma linha blindada são determinados por:

(E.4)

*k’*<sub>e</sub> = *k*<sub>e</sub> × *R*<sub>S</sub> / (*n*’ × *R*<sub>S</sub>+ *R*<sub>C</sub>)

onde

*R*<sub>S</sub> é a resistência ôhmica por unidade de comprimento da blindagem;

*R*<sub>C</sub> é a resistência ôhmica por unidade de comprimento do condutor interno.

> **NOTA 1** A Equação (E.4) pode subestimar o papel da blindagem no desvio da corrente de descargas atmosféricas devido à indutância mútua entre o núcleo e a blindagem.

> **NOTA 2** O uso das Equações (E.3) e (E.4) pode superestimar a corrente que flui pelos condutores das linhas de sinal.

#### E.2.4 Correntes de surto fluindo por partes condutivas e cabos internos à estrutura conectada ao *SPDA*

**E.2.4.1** Se as linhas internas (linhas elétricas de energia e de sinal) tiverem uma ligação equipotencial ao *SPDA* no nível da cobertura (ou seja, a distância de segurança não é obtida) e na barra de ligação equipotencial no nível do solo, cada um dos *n’* condutores da linha transporta uma parte igual *I’*<sub>F</sub> da corrente das descargas atmosféricas

(E.5)

*I’*<sub>F</sub> = *k’*<sub>c</sub> × I

onde

(E.6)

*k’*<sub>c</sub> = *k*<sub>c</sub> / 2*n’*

*k*<sub>c</sub> é o coeficiente de acordo com a ABNT NBR 5419-3;

*n’* é o número total de condutores.

**E.2.4.2** Para linhas blindadas, os valores do fator de divisão de corrente *k’*<sub>c</sub> para cada um dos condutores *n’* de uma linha blindada são determinados por:

(E.7)

*k’*<sub>c</sub> = *K*<sub>c</sub> × *R*<sub>S</sub> / 2 (*n’* × *R*<sub>S</sub>+ *R*<sub>C</sub>)

onde

*R*<sub>S</sub> é a resistência ôhmica por unidade de comprimento da blindagem;

*R*<sub>C</sub> é a resistência ôhmica por unidade de comprimento do condutor interno.

> **NOTA 1** A Equação (E.7) pode subestimar o papel da blindagem no desvio da corrente de descarga atmosférica, devido à indutância mútua entre o núcleo e a blindagem.

> **NOTA 2** Em certas situações, tanto a Equação (E.5) quanto a Equação (E.6) podem subestimar a corrente parcial de descarga atmosférica que passa pelos *DPS* no nível da cobertura.

> **NOTA 3** Usando as Equações (E.6) e (E.7), pode-se superestimar a corrente que flui pelos condutores das linhas de sinal.

#### E.2.5 Correntes de surto fluindo por cabos conectados a diferentes pontos do subsistema de aterramento

**E.2.5.1** Se uma linha é ligada em dois pontos diferentes de um subsistema de aterramento projetado conforme a ABNT NBR 5419-3, cada um dos *n’* condutores da linha carrega uma parte igual *I’*<sub>F</sub> da corrente de descarga atmosférica:

- no caso de uma linha não blindada:

(E.8)

*I’*<sub>F</sub> = *0,1* × *I* × *n’ / (2 n’* − *1)*

- no caso de uma linha blindada:

(E.9)

*I’*<sub>F</sub> = *0,1* × *I × R*<sub>S</sub>*/ (n’ × R*<sub>S</sub>*+ R*<sub>C</sub>*)*

onde

*n’* é o número total de condutores;

*R*<sub>S</sub> é a resistência ôhmica por unidade de comprimento da blindagem;

*R*<sub>C</sub> é a resistência ôhmica por unidade de comprimento do condutor interno.

> **NOTA 1** A Equação (E.9) pode subestimar o papel da blindagem no desvio da corrente de descarga atmosférica, devido à indutância mútua entre o núcleo e a blindagem.

> **NOTA 2** Uma avaliação mais precisa da *I’*<sub>F</sub> é possível considerando as características das linhas ligadas e do arranjo de aterramento.

**E.2.5.2** No caso de um eletrodo de aterramento pelas fundações de acordo com a ABNT NBR 5419-3 em que haja muitos módulos (na ordem de 1 m × 1 m), assume-se que a corrente que flui por estas linhas é desprezável, exceto para interligações realizadas em grandes distâncias.

### E.3 Correntes de surto devido a descargas atmosféricas nas linhas (fonte de dano S3)

**E.3.1** Para proteger linhas conectadas contra descargas atmosféricas diretas, é importante considerar a divisão da corrente de descarga em ambos os sentidos da linha e a possibilidade de falha de isolação.

**E.3.2** Cada um dos *n’* condutores da linha conduz uma parte igual a *I*’<sub>F</sub> da corrente de descarga atmosférica.

**E.3.3** O valor de *I*’<sub>F</sub> depende de:

- o tipo de linha: aérea ou enterrada;

- a característica da linha: blindada ou não blindada;

- o nível de isolação da linha;

- o número de condutores da linha;

- a impedância de aterramento associada aos postes para linhas aéreas;

- a resistividade do solo para linhas enterradas.

**E.3.4** Os maiores valores da corrente *I*’<sub>F</sub> são observados quando ocorre o impacto da descarga atmosférica em um poste próximo ao consumidor e quando a linha aérea não é blindada, possuindo dois condutores com altos níveis de isolação e alto nível de impedância de aterramento nos postes.

**E.3.5** No entanto, a carga da corrente que flui pelo *DPS* na entrada da linha na estrutura não muda com o ponto onde a corrente da descarga atmosférica atinge a linha.

**E.3.6** Os valores máximos aproximados de corrente *I*’<sub>F</sub> são apresentados na Tabela E.1 para linha de baixa tensão e na Tabela E.2 para sistemas de sinal, de acordo com o nível de proteção contra descargas atmosféricas (*NP*).

A seleção de um *DPS* deve considerar diversos fatores inter-relacionados, além dos valores de pico das correntes de surto. Na ausência de avaliações precisas desses fatores, os valores de corrente relatados nas Tabelas E.1 e E.2 podem ser utilizados como valores convencionais para a seleção do conjunto de DPS com uma determinada probabilidade (*P*<sub>DPS</sub>).

> **NOTA** Nas linhas de energia em AT e MT, a proteção a ser utilizada está relacionada com os para-raios de linha.

### E.4 Correntes de surto devido a descargas atmosféricas próximo das linhas (fonte de dano S4)

**E.4.1** Os surtos de descargas atmosféricas próximos às linhas possuem uma quantidade de energia significativamente menor em comparação com as descargas atmosféricas diretas nas linhas (fonte de dano S3).

**E.4.2** Assume-se que cada um dos *n’* condutores da linha carrega a mesma parcela de *I*’<sub>F</sub> da corrente da descarga atmosférica.

**E.4.3** O valor de *I*’<sub>F</sub> depende de:

- o tipo de linha: aérea ou enterrada;

- a característica da linha: blindada ou não blindada;

- o nível de isolação da linha;

- a altura dos condutores para linhas aéreas;

- a resistividade do solo para linhas enterradas.

**E.4.4** Os maiores valores de corrente *I*’<sub>F</sub> são obtidos quando ocorre o impacto direto no solo de alta resistividade próximo à linha e quando a linha é aérea não blindada e apresenta altos níveis de isolação.

**E.4.5** Para as linhas blindadas, assume-se que os valores de corrente apresentados nas Tabelas E.1 e E.2 podem ser reduzidos por um fator de 0,5.

**E.4.6** Os valores máximos aproximados de corrente *I*’<sub>F</sub> são apresentados na Tabela E.1 para linhas de baixa tensão e na Tabela E.2 para sistemas de sinal, de acordo com o nível de proteção contra descargas atmosféricas (*NP*).

**E.4.7** A seleção de um *DPS* deve considerar diversos fatores inter-relacionados, além dos valores de pico das correntes de surto. Na ausência de avaliações precisas desses fatores, os valores de corrente relatados nas Tabelas E.1 e E.2 podem ser utilizados como valores convencionais para a seleção de um *DPS* com uma determinada probabilidade *P*<sub>SPD</sub>.

### E.5 Correntes de surto devido a efeitos de indução (fontes de dano S1 ou S2)

#### E.5.1 Geral

**E.5.1.1** Surtos são causados pelos efeitos de indução de campos magnéticos gerados por descargas atmosféricas próximas (fonte S2) ou correntes de descargas atmosféricas que fluem no *SPDA* externo ou na blindagem espacial da *ZPR* 1 (fonte S1).

**E.5.1.2** Os efeitos de indução de campos magnéticos também podem ser gerados quando correntes de descargas atmosféricas fluem em estruturas que possuem uma estrutura metálica contínua ou são feitas de concreto armado e atuam como elemento natural do *SPDA*.

**E.5.1.3** A corrente induzida *I*’<sub>F</sub> é influenciada, em termos de amplitude e forma de onda, pela indutância e resistência do circuito em laço.

**E.5.1.4** Esses surtos devem ser considerados próximo ou no equipamento, no interior da *ZPR* 1 e na fronteira da *ZPR* 1 com a *ZPR* 2.

#### E.5.2 Correntes de surto no interior de uma *ZPR* 1 sem blindagem

**E.5.2.1** No interior de uma *ZPR* 1 não blindada, como aquela protegida apenas por um *SPDA* externo de acordo com a ABNT NBR 5419-3 e com largura de malha superior a 5 m, podem ocorrer surtos relativamente altos devido aos efeitos de indução do campo magnético não atenuado.

**E.5.2.2** Para a fonte de danos S1, os maiores valores de *I*’<sub>F</sub> são obtidos quando em um *SPDA* há longos trechos paralelos entre os condutores de descida e laços formados pelo sistema interno e uma curta distância entre eles com altos coeficientes de divisão de corrente *k*<sub>c</sub> entre os condutores do *SPDA*.

**E.5.2.3** Para a fonte S2, os maiores valores de *I*’<sub>F</sub> estão presentes quando houver grandes laços formados pelos condutores do sistema interno.

**E.5.2.4** Os valores máximos aproximados de corrente *I*’<sub>F</sub> são apresentados na Tabela E.1 para linhas de baixa tensão e na Tabela E.2 para linhas de sinal, de acordo com o nível de proteção contra descargas atmosféricas (*NP*).

A seleção de um *DPS* deve considerar diversos fatores inter-relacionados, além dos valores de pico das correntes de surto. Na ausência de avaliações precisas desses fatores, os valores de corrente relatados nas Tabelas E.1 e E.2 podem ser utilizados como valores convencionais para a seleção de um *DPS* com uma determinada probabilidade *P*<sub>SPD.</sub>

#### E.5.3 Correntes de surto no interior de *ZPR* com blindagem espacial

**E.5.3.1** No interior de uma *ZPR* com blindagem espacial cuja largura de malha seja inferior a 5 m, a geração de surtos devido aos efeitos de indução de campos magnéticos é significativamente reduzida. Nessas situações, os picos são significativamente menores do que os indicados em E.5.2.

**E.5.3.2** No interior da *ZPR* 1 os efeitos de indução são menores devido ao efeito de amortecimento da blindagem espacial.

**E.5.3.3** No interior da *ZPR* 2 os surtos são ainda mais reduzidos devido ao efeito cascata das blindagens espaciais de *ZPR* 1 e *ZPR* 2.

### E.6 Correntes típicas de surto

**E.6.1** Os efeitos das sobretensões de todas as fontes de dano (S1, S2, S3 e S4) podem ser determinados usando os parâmetros típicos apresentados nas Tabelas E.1 e E.2.

> **NOTA** É possível realizar o cálculo específico da divisão de corrente. No entanto, pode-se consultar a Tabela E.1 e a Tabela E.2 quando nenhum cálculo específico for realizado.

**Tabela E.1 – Correntes típicas de surto devido a descargas atmosféricas em linhas de energia**

**em baixa tensão**

<table><tr><th rowspan="3">***NP***</th><th colspan="5">**Linhas de energia em baixa tensão**</th></tr><tr><td colspan="2">**Descargas atmosféricas** **diretas e próximas à linha**</td><td>**Descarga** **atmosférica** **próximo da** **estrutura** <sup>a</sup></td><td>**Descarga** **atmosférica na** **estrutura** <sup>b, f</sup></td><td>**Descarga** **atmosférica** **na estrutura**</td></tr><tr><td>**Fonte de** **danos** **S3**<sup>c</sup> kA 10/350 μs</td><td>**Fonte de dano** **S4**<sup>d</sup> kA 8/20 μs</td><td>**Fonte de dano** **S2** kA 8/20 μs</td><td>**Fonte de** **dano S1** **(acoplamento** **indutivo)** kA 8/20 μs</td><td>**Fonte de** **dano S1**<sup>e</sup> **(acoplamento** **resistivo)** kA 10/350 μs</td></tr><tr><td>III e IV</td><td>5</td><td>2,5<sup>g</sup></td><td>0,1<sup>f</sup></td><td>5</td><td>12,5</td></tr><tr><td>II</td><td>7,5</td><td>3,75<sup>g</sup></td><td>0,15 <sup>f</sup></td><td>7,5</td><td>18,75</td></tr><tr><td>I</td><td>10</td><td>5g</td><td>0,2 <sup>f</sup></td><td>10</td><td>25</td></tr></table>

> **NOTA** Todos os valores referem-se a cada condutor da linha. <sup>a</sup> Para outras características de laço e estrutura (área de laço da ordem de 50 m², largura igual a 0,5 m), os valores devem ser multiplicados pelos fatores k<sub>S1</sub>, k<sub>S2</sub> e k<sub>S3</sub> *(*ver ABNT NBR 5419-2:2026, B.4*).* <sup>b</sup> Para outras características de laço e estrutura (área de laço da ordem de 50 m², largura igual a 0,5 m), os valores devem ser multiplicados pelos fatores *k*<sub>S1</sub>, *k*<sub>S2</sub> e *k*<sub>S3</sub> (ver ABNT NBR 5419-2:2026, B.4)*.* <sup>c</sup> Os valores apresentados são relevantes para as primeiras descargas (de uma descarga atmosférica) positivas e negativas em caso de impacto direto na linha aérea trifásica com condutores de neutro, considerando uma impedância de aterramento dos postes da linha de *Z*<sub>p</sub> = 50 Ω. Para linhas com apenas dois condutores, os valores podem ser dobrados. Já para linhas enterradas em solos com baixa resistividade (ρ < 250 Ωm), os valores podem ser reduzidos pela metade. <sup>d</sup> Os valores apresentados são relevantes para as primeiras descargas (de uma descarga atmosférica) positivas e negativas em linhas aéreas localizadas em solos de alta resistividade (ρ ≥ 3 000 Ωm). No caso de linhas enterradas ou linhas aéreas em solos de baixa resistividade, os valores podem ser significativamente reduzidos. <sup>e</sup> Os valores atuais são relevantes para as primeiras descargas (de uma descarga atmosférica) positivas e negativas e são aplicáveis quando *n* = 1, considerando uma linha de serviço com condutores trifásicos mais condutor de neutro (*n’* = 4) e um fator de divisão *k*<sub>e</sub> = 0,5. Informações mais detalhadas podem ser encontradas em E.2. <sup>f</sup> Geralmente, os *DPS* projetados para S1 (acoplamento indutivo) cobrem a necessidade de eventos S2 e S4. <sup>g</sup> Os valores reportados nessa coluna estão estabelecidos na IEC 60364-5-53 e são associados a probabilidades significativamente mais baixas do que os valores de outras colunas. Esses valores só podem ser utilizados quando não é realizada uma análise de risco específica. Para probabilidades associadas, ver ABNT NBR 5419-2.

**Tabela E.2 – Correntes típicas de surto devido a descargas atmosféricas em linhas de sinal**

<table><tr><th rowspan="3">***NP***</th><th colspan="5">**Linhas de sinal**<sup>a</sup></th></tr><tr><td colspan="2">**Descargas atmosféricas** **diretas e próximas à linha**</td><td>**Descarga** **atmosférica** **próximo da** **estrutura** <sup>b</sup></td><td>**Descarga** **atmosférica** **na estrutura** <sup>c</sup></td><td>**Descarga** **atmosférica** **na estrutura**</td></tr><tr><td>**Fonte de** **dano S3**<sup>d</sup> kA 10/350 μs</td><td>**Fonte de** **dano S4**<sup>e</sup> kA 8/20 μs</td><td>**Fonte de dano** **S2** kA 8/20 μs</td><td>**Fonte de** **dano S1** **(acoplamento** **indutivo)** kA 8/20 μs</td><td>**Fonte de** **dano S1**<sup>d</sup> **(acoplamento** **resistivo)** kA 10/350 μs</td></tr><tr><td>III e IV</td><td>1</td><td>0,3</td><td>0,1</td><td>5</td><td>1,25</td></tr><tr><td>II</td><td>1,5</td><td>0,45</td><td>0,15</td><td>7,5</td><td>1,875</td></tr><tr><td>I</td><td>2</td><td>0,6</td><td>0,2</td><td>10</td><td>2,5</td></tr></table>

> **NOTA** Todos os valores referem-se a cada condutor da linha. <sup>a</sup> Ver Recomendação K.67 da UIT-T [20] para obter mais informações. <sup>b</sup> Para outras características de laço e estrutura (área de laço da ordem de 50 m², largura igual a 0,5 m), os valores devem ser multiplicados pelos fatores *k*<sub>S1</sub>, *k*<sub>S2</sub> e *k*<sub>S3</sub> (ver ABNT NBR 5419-2:2026, B.4)*.* <sup>c</sup> Para outras características de laço e estrutura, os valores devem ser multiplicados pelos fatores k<sub>S1</sub>, k<sub>S2</sub> e k<sub>S3</sub> (ver ABNT NBR 5419-2:2026, B.4)*.* <sup>d</sup> Os valores são aplicáveis às primeiras descargas (de uma descarga atmosférica) positivas e negativas, tanto para linhas aéreas não blindadas com múltiplos pares, quanto para uma ou duas linhas não blindadas em uma linha metálica convencional. No caso de linhas enterradas em solos com baixa resistividade (ρ < 250 Ωm), os valores podem ser reduzidos pela metade. <sup>e</sup> Os valores são relevantes para as primeiras descargas (de uma descarga atmosférica) de descargas atmosféricas negativas e para linhas aéreas e não blindadas. No caso de linhas enterradas em solos com baixa resistividade (ρ < 250 Ωm), os valores podem ser reduzidos pela metade

**E.6.2** Para as linhas blindadas, assume-se que os valores de corrente apresentados nas Tabelas E.1 e E.2 podem ser reduzidos por um fator de 0,5.

> **NOTA** Assume-se que a resistência da blindagem é aproximadamente igual à resistência de todos os condutores de linha em paralelo.
