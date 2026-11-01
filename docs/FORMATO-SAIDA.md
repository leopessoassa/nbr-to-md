# Formato de saída (Markdown das normas)

Especificação do Markdown gerado em `normas/<id>/`. Qualquer renderizador ou validador deve seguir este documento. Status: **rascunho, aguardando revisão do dono do repositório** (Etapa 1 do plano).

## 1. Front matter

Bloco YAML no início de `normas/<id>/<id>.md`:

```yaml
---
norma: ABNT NBR 5410
id: nbr-5410
norma_completa: ABNT NBR 5410:2004
titulo: Instalações elétricas de baixa tensão
titulo_en: Electrical installations of buildings — Low voltage
edicao: Segunda edição
data_publicacao: 2004-09-30
valida_a_partir_de: 2005-03-31
versao_corrigida: 2008-03-17
ics: ["91.140.50"]
palavras_chave: ["Instalação elétrica em edificação"]
paginas_pdf: 217
fonte_pdf_sha256: "<hash>"
conversor_versao: "0.1.0"
data_conversao: 2026-10-31
marcacoes:
  "[imagem] ... [/imagem]": "descrição de figura escrita por IA, não revisada; não é texto normativo"
  "[imagem revisada] ... [/imagem]": "descrição de figura revisada por pessoa; não é texto normativo"
  "[formula] ... [/formula]": "fórmula transcrita por IA a partir de imagem, não revisada"
  "[formula revisada] ... [/formula]": "fórmula transcrita e revisada por pessoa"
---
```

Os campos de data e de edição vêm da capa do PDF. Campos não encontrados ficam ausentes, e a validação registra o motivo em `revisao.md`.

## 2. Cabeçalhos

- `#`: título da norma, uma vez só.
- `##`: seções de 1º nível e anexos.
  - `## 5 Proteção para garantir segurança`
  - `## Anexo A (normativo) Faixas de tensão`
- `###` a `######`: níveis seguintes, conforme o número de partes. `5.1` é `###`, `5.1.5` é `####`, e assim por diante.
- Profundidade acima de 6: sem cabeçalho. Usa-se parágrafo numerado com o número em negrito.
- O número fica no texto do cabeçalho: `### 5.1 Proteção contra choques elétricos`.

## 3. Parágrafo numerado sem título

```markdown
**5.1.5.4.2** Se, em espaços nos quais for prevista normalmente ...
```

O número acompanha todo parágrafo numerado, para que a IA possa citar a cláusula.

## 4. Notas e exemplos

```markdown
> **NOTA** Os afastamentos delimitadores ...

> **NOTA 2** ...

> **EXEMPLO** ...
```

## 5. Listas

- Itens `a)`, `b)` viram `- a) texto`.
- Marcadores `—` e `•` viram `- texto`.
- Listas aninhadas seguem a indentação (x0 do bloco).

## 6. Definições (Seção 3)

```markdown
#### 3.1.19 componente natural do SPDA

*Em inglês: natural component of LPS*

elemento metálico não instalado especificamente para proteção ...
```

## 7. Marcação inline

- Subscrito: `R<sub>X</sub>`, `I<sub>Δn</sub>`.
- Sobrescrito em unidade: caractere Unicode quando existir (`m²`, `m³`, `10⁻³`). Caso contrário, `<sup>`.
- Marcador de nota de rodapé `1)`: nota Markdown `[^t5-1]`, com prefixo da tabela ou da página.
- Negrito e itálico só quando o PDF tem e o texto não é cabeçalho. Termos estrangeiros em itálico usam `*...*`.

## 8. Fórmulas em destaque

```markdown
$$
R_X = N_X \times P_X \times L_X \tag{3}
$$

onde

- $N_X$ é o número de eventos perigosos por ano (ver Anexo A);
```

Fórmulas convertidas automaticamente do texto não recebem marcador. Fórmulas transcritas a partir de imagem seguem a seção 10.

## 9. Tabelas

- Simples (sem células mescladas): tabela GFM com `|`.
- Complexa (mesclagem ou cabeçalho em vários níveis): `<table>` HTML com `rowspan` e `colspan`.
- Linha de agrupamento (célula em toda a largura): linha GFM com o texto em negrito na primeira coluna e as demais vazias.
- Legenda acima da tabela: `**Tabela 6 — Presença de substâncias corrosivas ou poluentes**`.
- Notas da tabela logo abaixo, como `> **NOTA**`.
- Quebras de linha dentro da célula viram espaço, exceto itens de lista, que viram `<br>`.
- Tabela que continua em outra página é emitida uma única vez, inteira.

## 10. Figuras e marcação de descrição

```markdown
![Figura 7 — Zona de alcance normal](assets/figura-07.png)

**Figura 7 — Zona de alcance normal**

[imagem]
Desenho em corte mostrando uma superfície S onde as pessoas circulam ...

Rótulos presentes na figura: "S", "2,50 m", "0,75 m", "1,25 m".
[/imagem]
```

Regras:

- A descrição fica **sempre** entre `[imagem]` e `[/imagem]`. Cada marcador ocupa a sua própria linha. O conteúdo pode ter parágrafos, listas e um bloco ` ```mermaid ` (fluxogramas).
- Enquanto a descrição não foi revisada (`revisado_por: ia` em `revisoes.yaml`), a abertura é exatamente `[imagem]`. Depois da revisão humana (`revisado_por: humano`), a abertura passa a ser `[imagem revisada]`. O fechamento é sempre `[/imagem]`. Assim, buscar `[imagem]` lista só as descrições pendentes.
- Fórmulas transcritas pelo Kiro a partir de imagem usam `[formula]` e `[formula revisada]` ... `[/formula]`, envolvendo o bloco `$$ ... $$`. Fórmulas convertidas automaticamente do texto não recebem marcador.
- Figura ainda sem descrição: `[imagem]` com a linha `PENDENTE: descrição não escrita.` e os rótulos extraídos.
- Texto entre marcadores **não é texto da norma**. A validação de cobertura ignora esse trecho.

## 11. Marcadores de página

`<!-- p. 53 -->` antes do primeiro bloco de cada página.

## 12. Proibido no Markdown final

- Marca d'água, CNPJ e número de pedido.
- Cabeçalho ou rodapé repetido.
- Sumário com linhas pontilhadas.
- Caracteres da área de uso privado U+F000 a U+F8FF.
- Os caracteres quebrados `ņ`, `ʊ`, `ǻ`, `\x94`, `□` e `\uFFFD`.
- Os marcadores de diagnóstico `⟦glifo:` e `(cid:`.

## 13. Arquivos derivados

- `secoes/<arquivo>.md`: um arquivo por seção de nível 1. Repete um front matter curto (`norma`, `id`, `secao`, `titulo`), tem link para o arquivo único e ajusta os caminhos de imagem para `../assets/`.
- `chunks.jsonl`: um objeto JSON por linha, com um registro por cláusula, definição, tabela ou figura. Exemplo:

```json
{"id":"nbr-5410#5.1.5.4.2","norma":"ABNT NBR 5410:2004","secao":"5.1.5.4.2","caminho":["5 Proteção para garantir segurança","5.1 Proteção contra choques elétricos"],"tipo":"requisito","paginas":[53],"texto":"Se, em espaços nos quais ...","referencias":["5.1.5.4.1","Tabela 18","Figura 7"]}
```

  Registros de figura trazem `imagem` e `descricao_revisada`. Registros de fórmula trazem `formula_revisada`. Limite de 1 500 tokens por registro, estimado como caracteres divididos por 4.

- `termos.json`: lista `{numero, termo, termo_en, definicao}` extraída da Seção 3.
- `manifest.json`: id, metadados, sha256 do PDF, versão do conversor, data, contagens de seções, tabelas, figuras, fórmulas e pendências.
- `revisao.md`: alertas e pendências da validação.

## 14. Notas de rodapé pendentes

Quando o marcador `[^pN-n]` aparece no texto mas a definição da nota não foi localizada no PDF, o bloco de pendência fica assim:

```markdown
[rodape]
PENDENTE: definição da nota [^p30-1] não localizada no PDF.
[/rodape]
```

- O marcador `[rodape]` / `[/rodape]` segue a mesma regra de `[imagem]` e `[formula]`: cada marcador ocupa a sua linha, e a validação exige que estejam balanceados.
- A tag é gerada pelo pipeline, não escrita à mão. Revisão manual: procurar `[rodape]` no repositório.
- Definições localizadas saem como bloco `rodape` (texto `N) …`) e são emitidas como nota de rodapé Markdown `[^pN-n]: …`.

## 15. Símbolos em frase (pendentes)

Uma imagem pequena dentro de uma frase, como o símbolo de isolação dupla, não é fórmula nem figura. Ela vira um bloco próprio, na altura da imagem:

```markdown
![Símbolo](assets/simbolo-p051-01.png)
[simbolo]
PENDENTE: símbolo não transcrito.
[/simbolo]
```

- A tag `[simbolo]` / `[/simbolo]` segue a mesma regra de `[imagem]`, `[formula]` e `[rodape]`. O marcador de abertura fica sozinho na sua linha.
- A tag é gerada pelo pipeline. Revisão manual: procurar `[simbolo]` no repositório.
- A transcrição do símbolo (texto equivalente) é feita na revisão, como nas figuras.
