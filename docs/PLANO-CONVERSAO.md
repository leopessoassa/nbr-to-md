# Plano de conversão de NBRs (PDF → Markdown)

Este documento é o plano de implementação do conversor. Foi escrito para que um agente de IA (ou pessoa) consiga implementar cada etapa em sequência, sem precisar tomar decisões de arquitetura. Cada etapa tem entradas, saídas, regras e critérios de aceite.

Ambiente: Python 3.12 via mise. **Todo comando Python deve ser executado como `mise exec -- python ...`**.

---

## 1. Diagnóstico dos PDFs atuais

Levantamento feito com PyMuPDF sobre os 5 arquivos em `nbr/`.

| Arquivo | Páginas | Edição | Gerador | Observações |
|---|---|---|---|---|
| `nbr/5410/NBR5410.pdf` | 217 | 2004, versão corrigida 2008 | Bullzip PDF Printer | glifos sem mapeamento Unicode na fonte `ArialMT-Identity-H` |
| `nbr/5419/NBR5419-1 ...pdf` | 87 | 2026 | ABNT | fórmulas montadas com glifos de uso privado |
| `nbr/5419/NBR5419-2 ...pdf` | 270 | 2026 | ABNT | muitas tabelas, fluxograma raster |
| `nbr/5419/NBR5419-3 ...pdf` | 99 | 2026 | ABNT | — |
| `nbr/5419/NBR5419-4 ...pdf` | 107 | 2026 | ABNT | fórmulas com raiz e colchetes grandes |

Constatações que definem o desenho do conversor:

1. **Todos têm camada de texto.** Não é preciso OCR para o texto corrido. A extração é feita com PyMuPDF, de forma determinística.
2. **Sem marcadores (bookmarks).** `doc.get_toc()` retorna vazio. A hierarquia de seções precisa ser inferida pela numeração (`5.1.5.4.2`, `A.3`) e pela fonte em negrito.
3. **Marca d'água de licença em todas as páginas:** texto rotacionado em Helvetica, `Exemplar para uso exclusivo - <EMPRESA> - <CNPJ> (Pedido ... Impresso: ...)`. Contém dados do licenciado e **deve ser removido sempre**.
4. **Imagem de fundo em todas as páginas:** imagem do tamanho da página (logotipo ABNT esmaecido). Deve ser ignorada.
5. **Cabeçalho e rodapé repetidos:** `ABNT NBR 5410:2004`, `© ABNT 2004 – Todos os direitos reservados` e o número da página (arábico ou romano).
6. **Glifos sem mapeamento Unicode na NBR 5410.** A fonte embutida `IZWWBL+ArialMT-Identity-H` (o span informa só `ArialMT`) não tem tabela `ToUnicode` para alguns glifos. Na configuração padrão (`TEXT_CID_FOR_UNKNOWN_UNICODE` ligada), o PyMuPDF devolve `chr(id_do_glifo)` para esses glifos. Por isso aparecem letras aleatórias que, na verdade, são números de glifo. O pdfplumber/pdfminer mostra os mesmos glifos como `(cid:N)`, com o mesmo número, o que confirma o diagnóstico de forma independente. Mapeamento confirmado renderizando as páginas 17 e 48:

   | Glifo | PyMuPDF devolve | pdfplumber devolve | Caractere real |
   |---|---|---|---|
   | 326 | `ņ` (U+0146 = 326) | `(cid:326)` | `—` (travessão) |
   | 650 | `ʊ` (U+028A = 650) | `(cid:650)` | `•` (marcador de lista) |
   | 507 | `ǻ` (U+01FB = 507) | `(cid:507)` | `Δ` (ex.: I<sub>Δn</sub>) |
   | 148 | `\x94` (148) | `(cid:148)` | `≤` (ex.: R<sub>A</sub> · I<sub>Δn</sub> ≤ U<sub>L</sub>) |

   **O problema é maior do que parece.** Uma varredura completa com `get_texttrace()` encontrou na 5410 **575 ocorrências de 31 glifos distintos** sem Unicode: 4 da `ArialMT` (os da tabela acima e mais 153 e 159) e 27 da `SymbolMT`. Os da `SymbolMT` são os mais perigosos: como os números dos glifos são baixos, o PyMuPDF os devolve como **letras ASCII comuns**, e o texto parece normal mas está errado. Exemplos confirmados renderizando:

   | Fonte, glifo | PyMuPDF devolve | Caractere real | Onde |
   |---|---|---|---|
   | SymbolMT 100 | `d` | `≤` | p. 29, "≤ 2 000 m" (54 ocorrências) |
   | SymbolMT 80 | `P` | `μ` | p. 35, "10 μs" |
   | SymbolMT 32 | espaço | `√` | p. 119, "F = 1/√n" |

   As quatro NBR 5419 têm **zero** glifos sem Unicode.

   Consequência: o mapa de correção deve usar como chave **(fonte, número do glifo)**, e não o caractere errado. Assim ele não colide com um `ņ` ou um `d` legítimos e vale para qualquer NBR futura com o mesmo defeito. Os 24 glifos restantes da 5410 serão identificados no marco M1 (Etapa 12, passo 5).
7. **Espaços especiais nas NBR 5419:** `\u200a`, `\u2002`, `\u2003` e `\t` entre número da seção e texto.
8. **Subscritos e sobrescritos perdem-se no texto plano:** `RX = NX × PX × LX` é na verdade R<sub>X</sub> = N<sub>X</sub> × P<sub>X</sub> × L<sub>X</sub>; `mg/m2` é `mg/m²`; `1 mm1)` é `1 mm` + nota de rodapé `1)`. Eles são detectáveis: o span tem fonte menor (ex.: 9,1 contra 11,0) e baseline deslocada (+2 pt para subscrito, negativa para sobrescrito).
9. **Fórmulas montadas com glifos da área de uso privado** (U+F8EB a U+F8FE são pedaços de parênteses/colchetes grandes da fonte Symbol) e, em alguns casos, com pequenas imagens. Precisam de reconstrução para LaTeX.
10. **Tabelas com bordas.** `page.find_tables()` do PyMuPDF detecta corretamente (testado na Tabela 5/6 da 5410 e na tabela de símbolos da 5419-2). Tabelas continuam entre páginas com `Tabela 5 (continuação)` / `(conclusão)`. Há linhas de agrupamento (célula mesclada em toda a largura).
11. **Figuras de três tipos:**
    - vetoriais com texto real por cima (ex.: Figura 1 da 5419-1);
    - raster com texto dentro da imagem (ex.: fluxograma da Figura 1 da 5419-2);
    - esquemas elétricos raster (ex.: esquema TN-C-S na 5410).
    Nenhum dos três vira texto sozinho. Exigem imagem recortada + descrição textual revisada.
12. **Formato de numeração difere entre edições:** na 5410 o número da seção fica numa linha e o texto na linha seguinte; na 5419 fica na mesma linha separado por tab.
13. **Definições (Seção 3)** seguem o padrão `3.1.19 termo (termo em inglês)` + definição na linha seguinte.

---

## 2. Decisões de projeto

### 2.1 Abordagem: regras sobre PyMuPDF, não modelo de ML

| Opção | Prós | Contras |
|---|---|---|
| **PyMuPDF + regras (escolhida)** | determinístico, auditável, rápido, já instalado, controle total sobre marca d'água e caracteres | exige escrever as regras de layout |
| `pymupdf4llm` | pronto, 1 linha | não remove marca d'água/rodapé, não corrige caracteres, não junta tabelas entre páginas |
| Docling / Marker (ML) | bom em layout genérico | pesado (GPU/torch), resultado varia entre versões, difícil garantir "zero perda" |

Os PDFs são digitais, com texto e bordas de tabela. Regras resolvem com precisão e permitem validar cobertura de texto palavra por palavra.

**MarkItDown (Microsoft) avaliado e descartado como conversor.** Testado na versão 0.1.9 sobre as NBRs: não gerou nenhum cabeçalho, manteve cabeçalho e rodapé (216 ocorrências na 5410), picotou as tabelas, transformou a equação (3) da 5419-2 em tabela falsa, separou subscritos das letras e emitiu `(cid:N)` no lugar dos glifos sem mapeamento. Aproveitamos duas ideias dele: o pdfplumber como **segundo extrator independente** para validar a cobertura (Etapa 11) e o código `(cid:N)` do pdfminer para **confirmar o mapa de glifos** (Etapas 4 e 11). Os dois usam o pdfplumber, que já está instalado, sem instalar o MarkItDown.

### 2.2 Princípio "nada se perde"

- O texto normativo **nunca é parafraseado**. Toda palavra do PDF (exceto marca d'água, cabeçalho, rodapé e sumário) precisa aparecer no Markdown. Isso é verificado automaticamente (Etapa 11).
- O que não vira texto (figuras, fórmulas complexas) vira **imagem recortada + equivalente textual**. O equivalente textual feito por IA fica marcado como tal.
- Toda decisão incerta gera um item no relatório de revisão (`revisao.md`) em vez de ser descartada em silêncio.
- Cada bloco guarda a página de origem, para rastreabilidade.

### 2.3 Otimização para IA

- Hierarquia explícita com cabeçalhos Markdown que refletem a numeração da norma.
- O número da seção acompanha **todo** parágrafo numerado, para a IA poder citar "conforme 5.1.5.4.2".
- Front matter YAML com metadados (norma, edição, validade).
- Saída em três formas: arquivo único, arquivos por seção principal e `chunks.jsonl` para RAG (um registro por cláusula, com caminho hierárquico).
- Sem ruído: sem cabeçalhos/rodapés, sem linhas pontilhadas do sumário, sem quebras de linha no meio de frases.
- Marcadores de página como comentário HTML (`<!-- p. 53 -->`): invisíveis na renderização, úteis para auditoria, baratos em tokens.

### 2.4 Pipeline determinístico + revisões versionadas

A parte que precisa de "olho" (descrever figura, transcrever fórmula em LaTeX) não é feita dentro do pipeline por chamada de API. Ela fica num arquivo YAML de revisões por norma (`config/<id>/revisoes.yaml`), escrito manualmente pelo Kiro numa sessão de chat (lendo os PNGs gerados) e revisado por você. No Markdown, todo conteúdo escrito pelo Kiro fica entre marcadores `[imagem]` ... `[/imagem]` (ou `[formula]` ... `[/formula]`) até ser revisado. O pipeline aplica essas revisões de forma determinística. Assim, rodar a conversão duas vezes produz exatamente o mesmo resultado e não exige chave de API.

---

## 3. Estrutura do repositório

```
nbr-to-md/
├── mise.toml
├── pyproject.toml
├── README.md
├── docs/
│   ├── PLANO-CONVERSAO.md          (este arquivo)
│   └── FORMATO-SAIDA.md            (especificação do Markdown gerado, Etapa 1)
├── .kiro/
│   ├── steering/
│   │   ├── produto.md
│   │   ├── tecnologia.md
│   │   ├── formato-saida.md
│   │   └── nova-norma.md
│   └── specs/nbr2md/               (requirements.md, design.md, tasks.md)
├── nbr/                            (PDFs de origem, entrada)
│   ├── 5410/NBR5410.pdf
│   └── 5419/...
├── config/
│   ├── defaults.yaml               (regras genéricas para todas as NBRs)
│   └── nbr-5410/
│       ├── norma.yaml              (ajustes específicos da norma)
│       └── revisoes.yaml           (figuras, fórmulas, correções manuais)
├── src/nbr2md/
│   ├── __init__.py
│   ├── __main__.py                 (permite `python -m nbr2md`)
│   ├── cli.py
│   ├── config.py
│   ├── modelo.py                   (dataclasses da representação intermediária)
│   ├── extrair.py
│   ├── limpar.py
│   ├── inline.py
│   ├── blocos.py
│   ├── classificar.py
│   ├── tabelas.py
│   ├── figuras.py
│   ├── formulas.py
│   ├── estrutura.py
│   ├── revisoes.py
│   ├── renderizar.py
│   ├── chunks.py
│   └── validar.py
├── tests/
│   ├── conftest.py
│   ├── fixtures/                   (trechos esperados, verificados à mão)
│   └── test_*.py
├── build/                          (intermediários, no .gitignore)
│   └── nbr-5410/
│       ├── 01-spans/pagina-0001.json
│       ├── 02-limpo/...
│       ├── 03-blocos.json
│       ├── 04-arvore.json
│       └── recortes/               (PNGs para revisão por IA)
└── normas/                         (saída final, versionada)
    ├── llms.txt                    (índice de todas as normas convertidas)
    └── nbr-5410/
        ├── nbr-5410.md        (arquivo único completo)
        ├── secoes/
        │   ├── 00-preliminares.md
        │   ├── 01-escopo.md
        │   └── anexo-a.md
        ├── assets/
        │   ├── figura-07.png
        │   └── equacao-03.png
        ├── chunks.jsonl
        ├── termos.json
        ├── manifest.json
        └── revisao.md              (pendências e alertas)
```

### Identificador da norma (`id`)

Formato: `nbr-<numero>[-<parte>]`, tudo minúsculo, **sem o ano**.
Exemplos: `nbr-5410`, `nbr-5419-1`, `nbr-5419-2`.

O `id` não muda entre edições porque uma nova edição **substitui** a anterior (ver Etapa 12a). A edição vigente fica registrada no front matter, no `manifest.json` e no campo `norma` dos chunks (`ABNT NBR 5410:2004`). As edições antigas continuam acessíveis só pelo histórico do Git.

---

## 4. Representação intermediária (`modelo.py`)

Todas as etapas trocam dados por estas estruturas (dataclasses serializáveis em JSON). Isso permite testar cada etapa isoladamente e inspecionar `build/`.

```python
@dataclass
class Span:
    texto: str
    fonte: str          # ex.: "ArialMT", "Arial-BoldMT"
    tamanho: float
    negrito: bool       # "Bold" no nome da fonte OU flags & 16
    italico: bool       # "Italic"/"Oblique" no nome OU flags & 2
    bbox: tuple[float, float, float, float]
    origem_y: float     # baseline (span["origin"][1])
    direcao: tuple[float, float]  # line["dir"]; (1,0) = horizontal

@dataclass
class Linha:
    spans: list[Span]
    bbox: tuple
    pagina: int

@dataclass
class Bloco:
    id: str             # ex.: "p053-b007"
    tipo: str           # ver Etapa 6
    pagina: int
    paginas: list[int]  # quando atravessa páginas
    bbox: tuple
    texto_md: str       # já com <sub>/<sup>/negrito aplicados
    numero: str | None  # "5.1.5.4.2", "A.3", "3.1.19"
    extra: dict         # tabela: linhas/células; figura: caminho do PNG etc.

@dataclass
class No:               # nó da árvore de seções
    numero: str | None
    titulo: str
    nivel: int
    blocos: list[Bloco]
    filhos: list["No"]
```

---

## 5. Etapas de implementação

Cada etapa abaixo é uma tarefa independente. Implementar na ordem. Ao fim de cada uma, rodar os testes da etapa.

### Etapa 0. Preparação do projeto

1. Criar `pyproject.toml` com pacote `nbr2md` em `src/`, dependências `pymupdf>=1.28`, `pyyaml`, `pdfplumber>=0.11` (segundo extrator, usado na validação e no diagnóstico de glifos) e, em `dev`, `pytest`.
2. Instalar em modo editável: `mise exec -- python -m pip install -e ".[dev]"`.
3. Adicionar tarefas ao `mise.toml` para facilitar:
   ```toml
   [tasks.converter]
   run = "python -m nbr2md converter"
   [tasks.testar]
   run = "python -m pytest -q"
   ```
4. Criar `.gitignore` com `build/`, `__pycache__/`, `*.egg-info/`. O repositório é privado, então `nbr/` (PDFs) e `normas/` (saída) **são versionados**.
5. CLI (`cli.py`, com `argparse`):
   - `converter <id|caminho.pdf> [--ate-etapa N] [--paginas 1-20]`
   - `inspecionar <pdf> --pagina N [--glifos] [--png]` (mostra spans com fonte, tamanho e bbox; com `--glifos`, lista os glifos sem Unicode do PyMuPDF lado a lado com os `(cid:N)` do pdfplumber; com `--png`, salva o recorte de cada glifo em `build/`)
   - `recortes <id>` (gera PNGs de figuras/fórmulas para revisão)
   - `validar <id>`
   - `todas` (converte todas as normas com `config/*/norma.yaml`)

**Aceite:** `mise exec -- python -m nbr2md --help` funciona.

### Etapa 1. Especificação do formato de saída

Antes de codificar o renderizador, escrever `docs/FORMATO-SAIDA.md` e copiar o essencial para `.kiro/steering/formato-saida.md`. Conteúdo obrigatório (regras abaixo):

**Front matter**
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
---
```

**Cabeçalhos**
- `#` = título da norma (uma vez).
- `##` = seções de 1º nível e anexos: `## 5 Proteção para garantir segurança`, `## Anexo A (normativo) Faixas de tensão`.
- `###` a `######` = níveis seguintes conforme a quantidade de pontos (`5.1` → `###`, `5.1.5` → `####` ...).
- Profundidade acima de 6: não usar cabeçalho; usar parágrafo com número em negrito.
- O número fica no texto do cabeçalho: `### 5.1 Proteção contra choques elétricos`.

**Parágrafo numerado sem título** (requisito):
```
**5.1.5.4.2** Se, em espaços nos quais for prevista normalmente ...
```

**Notas e exemplos**
```
> **NOTA** Os afastamentos delimitadores ...

> **NOTA 2** ...

> **EXEMPLO** ...
```

**Listas**: `a)`, `b)` viram `a)` em lista Markdown (`- a) texto`); `—` e `•` viram `- texto`. Listas aninhadas por indentação (x0 do bloco).

**Definições**
```
#### 3.1.19 componente natural do SPDA

*Em inglês: natural component of LPS*

elemento metálico não instalado especificamente para proteção ...
```

**Inline**
- Subscrito: `R<sub>X</sub>`, `I<sub>Δn</sub>`.
- Sobrescrito em unidade: caractere Unicode quando existir (`m²`, `m³`, `10⁻³`); senão `<sup>`.
- Marcador de nota de rodapé `1)`: nota de rodapé Markdown `[^t5-1]` (prefixo da tabela ou página).
- Negrito/itálico só quando o PDF tem e não é cabeçalho. Termos estrangeiros em itálico mantêm `*...*`.

**Fórmulas em destaque**
```
$$
R_X = N_X \times P_X \times L_X \tag{3}
$$

onde

- $N_X$ é o número de eventos perigosos por ano (ver Anexo A);
```

**Tabelas**
- Simples (sem células mescladas): tabela GFM com `|`.
- Complexas (mesclagem, cabeçalho em vários níveis): `<table>` HTML com `rowspan`/`colspan`.
- Linha de agrupamento (célula em toda a largura): na GFM, linha com o texto em negrito na 1ª coluna e demais vazias.
- Legenda acima: `**Tabela 6 — Presença de substâncias corrosivas ou poluentes**`.
- Notas da tabela logo abaixo, como `> **NOTA**`.
- Quebras de linha dentro da célula viram espaço, exceto itens de lista, que viram `<br>`.
- Tabela que continua em várias páginas é emitida uma única vez, inteira.

**Figuras**
```
![Figura 7 — Zona de alcance normal](assets/figura-07.png)

**Figura 7 — Zona de alcance normal**

[imagem]
Desenho em corte mostrando uma superfície S onde as pessoas circulam ...

Rótulos presentes na figura: "S", "2,50 m", "0,75 m", "1,25 m".
[/imagem]
```

Regras da marcação de descrição de figura:
- A descrição fica **sempre** entre `[imagem]` e `[/imagem]`, cada marcador sozinho na sua linha, com o conteúdo nas linhas entre eles. O conteúdo pode ter parágrafos, listas e um bloco ```` ```mermaid ```` (fluxogramas).
- Enquanto a descrição não foi revisada por você (`revisado_por: ia` em `revisoes.yaml`), o marcador de abertura é exatamente `[imagem]`. Depois da revisão (`revisado_por: humano`), passa a ser `[imagem revisada]`; o fechamento continua `[/imagem]`. Assim, buscar `[imagem]` no repositório lista só as descrições pendentes.
- Fórmulas que o Kiro transcreveu a partir de imagem ou de glifos quebrados seguem a mesma regra com `[formula]` / `[formula revisada]` ... `[/formula]`, envolvendo o bloco `$$ ... $$`. Fórmulas convertidas automaticamente do texto (sem interpretação visual) não recebem marcador.
- Figura ainda sem descrição: `[imagem]` com o texto `PENDENTE: descrição não escrita.` e os rótulos extraídos.
- Texto entre os marcadores **não é texto da norma**. O front matter declara isso para a IA leitora (campo `marcacoes`, abaixo) e a validação de cobertura (Etapa 11) ignora esse trecho.

Front matter recebe também:
```yaml
marcacoes:
  "[imagem] ... [/imagem]": "descrição de figura escrita por IA, não revisada; não é texto normativo"
  "[imagem revisada] ... [/imagem]": "descrição de figura revisada por pessoa; não é texto normativo"
  "[formula] ... [/formula]": "fórmula transcrita por IA a partir de imagem, não revisada"
  "[formula revisada] ... [/formula]": "fórmula transcrita e revisada por pessoa"
```

**Marcadores de página**: `<!-- p. 53 -->` antes do primeiro bloco de cada página.

**Proibido no Markdown final**: marca d'água, CNPJ, número de pedido, cabeçalho/rodapé repetido, sumário com pontilhado, caracteres U+F000–U+F8FF, `ņ`, `ʊ`, `ǻ`, `\x94`, `□`, `\uFFFD`, `⟦glifo:`, `(cid:`.

**Aceite:** documento revisado pelo dono do repositório.

### Etapa 2. Configuração (`config.py`)

`config/defaults.yaml` contém as regras genéricas; `config/<id>/norma.yaml` sobrescreve só o necessário (merge profundo, listas são concatenadas).

`defaults.yaml` (ponto de partida):
```yaml
remover:
  marca_dagua:
    - regex: "^Exemplar para uso exclusivo"
    - texto_rotacionado: true        # linha com dir != (1,0) é descartada
  cabecalho_rodape:
    faixa_superior: 0.08             # fração da altura da página
    faixa_inferior: 0.08
    repeticao_minima: 0.4            # aparece em >=40% das páginas (dígitos normalizados)
    regex:
      - "^ABNT NBR [\\d\\-]+:\\d{4}$"
      - "^© ABNT \\d{4}.{1,3}Todos os direitos reservados$"
      - "^[ivxlcdm]+$"
      - "^\\d{1,3}$"
  imagem_fundo_area_minima: 0.85     # imagem que cobre >=85% da página é ignorada
normalizar_espacos: ["\u200a", "\u2002", "\u2003", "\u2009", "\u00a0", "\t"]
mapa_glifos: {}                      # (fonte, id do glifo) -> caractere; ver norma.yaml
mapa_caracteres: {}                  # substituições de caractere por caractere (casos sem glifo)
inline:
  razao_tamanho_sub_sup: 0.88        # span com tamanho < 0.88 × tamanho da linha
  deslocamento_baseline_min: 0.8     # pt
estrutura:
  regex_secao: "^(?P<num>(?:[A-Z]|\\d{1,2})(?:\\.\\d{1,2})*)\\s+(?P<resto>.*)$"
  regex_anexo: "^Anexo (?P<letra>[A-Z])\\s*(?:\\((?P<tipo>normativo|informativo)\\))?\\s*(?P<titulo>.*)$"
  regex_tabela: "^Tabela (?P<num>[A-Z]?\\.?\\d+)\\s*(?:\\((?P<cont>continuação|conclusão)\\))?\\s*[—–-]?\\s*(?P<titulo>.*)$"
  regex_figura: "^Figura (?P<num>[A-Z]?\\.?\\d+)\\s*[—–-]\\s*(?P<titulo>.*)$"
  regex_nota: "^NOTA(?:\\s+(?P<n>\\d+))?\\b"
  regex_exemplo: "^EXEMPLO(?:\\s+(?P<n>\\d+))?\\b"
  regex_item_letra: "^(?P<l>[a-z])\\)\\s*"
  marcadores_lista: ["—", "–", "•", "-"]
  secoes_preliminares: ["Prefácio", "Introdução", "Sumário"]
  descartar: ["Sumário"]
```

`config/nbr-5410/norma.yaml`:
```yaml
id: nbr-5410
fonte: nbr/5410/NBR5410.pdf
mapa_glifos:
  ArialMT:              # nome da fonte como aparece no span (sem prefixo de subconjunto)
    326: "—"            # confirmado p. 17 (pdfplumber: (cid:326))
    650: "•"            # confirmado p. 17 (pdfplumber: (cid:650))
    507: "Δ"            # confirmado p. 48 (pdfplumber: (cid:507))
    148: "≤"            # confirmado p. 48 (pdfplumber: (cid:148))
    # 153, 159: identificar no M1
  SymbolMT:
    100: "≤"            # confirmado p. 29
    80: "μ"             # confirmado p. 35
    32: "√"             # confirmado p. 119
    # outros 24 glifos: identificar no M1 via build/nbr-5410/glifos-desconhecidos.json
paginas:
  capa: [1]
  sumario: [3, 8]       # confirmar com `inspecionar`
```

Para as 5419 o `norma.yaml` só precisa de `id` e `fonte` no início; ajustes surgem durante a validação.

**Aceite:** teste que carrega defaults + norma e verifica merge.

### Etapa 3. Extração (`extrair.py`)

Para cada página: `page.get_text("dict", flags=pymupdf.TEXTFLAGS_DICT & ~pymupdf.TEXT_PRESERVE_IMAGES)` e converte cada span em `Span`. Salva `build/<id>/01-spans/pagina-NNNN.json`.

Também extrai por página:
- `page.get_image_info(xrefs=True)` → lista de imagens com bbox;
- `page.get_drawings()` → só a contagem e bbox agregada por região (para achar figuras vetoriais);
- `page.find_tables()` → bbox e células (guardar em JSON, usado na Etapa 7).

**Glifos sem mapeamento Unicode.** Método testado na 5410 (575 de 575 ocorrências casadas):
1. Extrair o texto com `get_text("rawdict", flags=TEXTFLAGS_DICT & ~TEXT_PRESERVE_IMAGES & ~TEXT_CID_FOR_UNKNOWN_UNICODE)`. Sem a flag `TEXT_CID_FOR_UNKNOWN_UNICODE`, todo glifo sem mapeamento vem como `U+FFFD`, e não como uma letra falsa. **Essa flag nunca pode ficar ligada em nenhum ponto do pipeline.**
2. Montar um índice da página com `page.get_texttrace()`: para cada caractere com `unicode == 0xFFFD`, a chave é `(round(origem_x, 1), round(origem_y, 1))` e o valor é `(fonte do span, id do glifo)`.
3. Para cada `U+FFFD` do passo 1, buscar no índice a chave da origem do caractere (`char["origin"]`) e guardar no `Span` o campo `glifos_sem_unicode: list[{indice, glifo, fonte}]`.
4. `U+FFFD` sem par no índice é erro registrado em `limpeza.json`, e não pode ser ignorado.

Não usar a estratégia de extrair duas vezes com e sem a flag e casar os caracteres por posição na lista: foi testada e divergiu em 10 páginas da 5410.

Gravar também `build/<id>/glifos-desconhecidos.json`: contagem por `(fonte, glifo)` com até 3 exemplos de contexto (página e 40 caracteres ao redor). Esse arquivo é o que se consulta para preencher `mapa_glifos` numa NBR nova.

Calcular e guardar `sha256` do PDF.

**Aceite:** extrair a 5410 inteira em menos de 1 min; JSON da p. 31 contém spans `Tabela 6`.

### Etapa 4. Limpeza (`limpar.py`)

Ordem obrigatória:

1. **Marca d'água:** descartar linhas com `direcao != (1.0, 0.0)` e linhas que casam com `remover.marca_dagua.regex`. Registrar a quantidade removida por página (deve ser ≥ 1 em todas).
2. **Imagem de fundo:** descartar imagens com área ≥ 85% da página.
3. **Cabeçalho/rodapé:** primeiro pela regex; depois pela heurística de repetição: normalizar o texto da linha (dígitos → `#`) e, se estiver nas faixas superior/inferior e se repetir em ≥ 40% das páginas, descartar.
4. **Glifos sem mapeamento e mapa de caracteres:**
   - Para cada `U+FFFD` com glifo registrado (Etapa 3), procurar `mapa_glifos[fonte][glifo]`, com o nome da fonte sem o prefixo de subconjunto (`IZWWBL+ArialMT` → `ArialMT`). Se achar, substituir.
   - Se não achar, **não descartar**: trocar por `⟦glifo:<fonte>:<n>⟧`, registrar em `limpeza.json` e deixar a validação bloquear. Assim nenhum glifo desconhecido some em silêncio.
   - **Confirmação cruzada com pdfplumber**, só para diagnóstico: o comando `inspecionar <pdf> --glifos` abre a mesma página com pdfplumber e lista os caracteres `(cid:N)` com fonte e posição. Para cada glifo do `mapa_glifos`, o `N` do pdfplumber deve coincidir com o id do glifo do PyMuPDF na mesma posição (tolerância de 1 pt). Divergência indica que o mapa está apontando para o glifo errado.
   - Depois aplicar `mapa_caracteres` (substituição simples de caractere, para defeitos que não são de glifo).
5. **Espaços:** substituir espaços especiais por espaço normal; colapsar espaços múltiplos; manter o tab como separador lógico apenas para detectar "número + texto" (guardar a informação antes de normalizar).
6. **Glifos de uso privado (U+F000–U+F8FF):** não remover. Marcar a linha com `extra["pua"] = True`. Essas linhas indicam fórmula (Etapa 8).
7. **Unicode NFC** em todo texto.

Salvar `build/<id>/02-limpo/` e um `limpeza.json` com contagens.

**Aceite (testes):**
- Nenhuma linha restante contém `Exemplar para uso exclusivo` nem o CNPJ, em nenhuma das 5 normas.
- Nenhuma linha restante é `ABNT NBR 5410:2004` isolada.
- A 5410 não tem mais `ņ`, `ʊ`, `ǻ`, `\x94`, `U+FFFD` nem `⟦glifo:`; a p. 17 tem `•` nos itens de "serviços de segurança", a p. 48 tem `Δ` e `≤`, a p. 29 tem `≤ 2 000 m` (e não `d 2 000 m`), a p. 35 tem `10 μs` e a p. 119 tem `√`.
- `glifos-desconhecidos.json` da 5410 lista 31 pares (fonte, glifo) e 575 ocorrências; o das quatro 5419 está vazio.
- `inspecionar nbr/5410/NBR5410.pdf --pagina 48 --glifos` mostra `(cid:507)` e `(cid:148)` do pdfplumber nas mesmas posições dos glifos 507 e 148 do PyMuPDF.
- Um `ņ` legítimo (teste sintético com texto mapeado) **não** é alterado.

### Etapa 5. Marcação inline (`inline.py`)

Para cada linha:

1. Tamanho de referência = mediana do tamanho dos spans da linha, ponderada pelo número de caracteres.
2. Span é **subscrito** se `tamanho < 0.88 × ref` e `origem_y − baseline_ref ≥ 0.8`; **sobrescrito** se `tamanho < 0.88 × ref` e `baseline_ref − origem_y ≥ 0.8`.
3. Sobrescrito no formato `\d+\)` logo após palavra/número = marcador de nota de rodapé. Guardar para ligar à nota da tabela/página.
4. Sobrescrito `2`, `3`, `-1`... após unidade (`m`, `mm`, `cm`, `km`, `s`, `m/s`) → Unicode (`²`, `³`, `⁻¹`).
5. Demais → `<sub>…</sub>` / `<sup>…</sup>`.
6. Negrito/itálico: juntar spans vizinhos com o mesmo estilo antes de emitir `**`/`*`; não emitir estilo para espaços.
7. Corrigir espaço espúrio antes do span seguinte (`P` + `X` + ` é` → `P<sub>X</sub> é`).

**Aceite:** a linha da p. 42 da 5419-2 vira `R<sub>X</sub> = N<sub>X</sub> × P<sub>X</sub> × L<sub>X</sub>`; `mg/m2` da 5410 p. 31 vira `mg/m²`; `1 mm1)` vira `1 mm[^…]`.

### Etapa 6. Blocos e classificação (`blocos.py`, `classificar.py`)

**Agrupar linhas em blocos** (por página, ordem de leitura de cima para baixo; as NBRs são de 1 coluna):
- Nova linha começa novo bloco se: o espaço vertical até a anterior > 0,6 × altura da linha; ou muda o x0 de forma relevante (> 8 pt) sem ser continuação de item de lista; ou a linha casa com alguma regex de início (seção, nota, tabela, figura, item).
- Linhas dentro de bbox de tabela (Etapa 7) ou de figura (Etapa 8) são retiradas daqui.
- Juntar linhas com espaço. **Não remover hífen de fim de linha** (português tem `pode-se`, `utiliza-se`); só juntar sem espaço quando a linha termina em hífen **e** a próxima começa com minúscula **e** a palavra sem hífen aparecer em outro lugar do documento.

**Caso 5410:** número da seção sozinho numa linha (`5.1.5.4.2`) e texto na linha seguinte → juntar como um só bloco numerado.

**Tipos de bloco** (testar nesta ordem):

| tipo | regra |
|---|---|
| `anexo` | regex_anexo, negrito |
| `titulo_secao` | regex_secao + negrito + resto curto (< 120 caracteres) sem ponto final |
| `paragrafo_numerado` | regex_secao com texto corrido (não negrito ou longo) |
| `definicao` | numeração `3.x.y` dentro da Seção 3 "Termos e definições" |
| `legenda_tabela` | regex_tabela |
| `legenda_figura` | regex_figura |
| `nota` | regex_nota |
| `exemplo` | regex_exemplo |
| `item_lista` | regex_item_letra ou marcador de lista no início |
| `legenda_itens` | bloco "Legenda" e itens `a`, `b`, `1`, `2` abaixo de figura/tabela |
| `rodape` | nota de rodapé de página (fonte menor, parte inferior, começa com `\d\)` ou `[a-z]`) |
| `paragrafo` | o resto |

**Juntar entre páginas:** se o último bloco da página N é `paragrafo`/`paragrafo_numerado`/`item_lista` e não termina em `.`, `:` ou `;`, e o primeiro bloco da página N+1 é `paragrafo` que começa com minúscula, juntar e preencher `paginas = [N, N+1]`.

**Preliminares:** capa → só front matter (extrair título, título em inglês, datas, ICS, ISBN, palavras-chave por regex); `Sumário` → descartar, mas guardar a lista de entradas (número + título + página) para validação; `Prefácio` e `Introdução` → seções sem número.

**Aceite:** testes de fixture com 3 trechos por norma (um título, um parágrafo numerado, uma nota, um item de lista) comparados ao esperado.

### Etapa 7. Tabelas (`tabelas.py`)

1. Usar o resultado de `page.find_tables()` (estratégia padrão por linhas). Se uma região tiver legenda `Tabela N` acima mas nenhuma tabela detectada, tentar `find_tables(strategy="text")` e marcar `extra["confianca"]="baixa"` + item em `revisao.md`.
2. Associar cada tabela à legenda mais próxima acima (até 40 pt). Tabela sem legenda: verificar se é continuação (ver 3); senão marcar para revisão.
3. **Continuação:** legenda `Tabela N (continuação)`/`(conclusão)` ou tabela no topo da página seguinte com o mesmo número de colunas e cabeçalho igual → concatenar linhas e descartar o cabeçalho repetido.
4. Conteúdo das células: reextrair o texto de cada célula a partir dos spans limpos (Etapas 4 e 5) dentro do bbox da célula, para manter `<sub>`, `²` e o mapa de caracteres. Não usar o texto cru do `find_tables`.
5. **Detecção de mesclagem:** célula `None` no resultado do PyMuPDF indica mesclagem. Linha com todas as células iguais (como a linha "Número médio anual de eventos perigosos..." da 5419-2) = linha de agrupamento.
6. Decidir formato: sem mesclagem → GFM; com mesclagem fora do padrão "linha de agrupamento" → HTML.
7. Notas e notas de rodapé dentro da última linha (ex.: `NOTA Nas condições AE2...` dentro da Tabela 5) → retirar da tabela e emitir como `> **NOTA**` logo após.
8. Escapar `|` dentro de células GFM.

**Aceite:** Tabela 5 da 5410 sai uma vez só, com todas as linhas de AE1 a AE6; tabela de símbolos da 5419-2 tem as linhas de agrupamento em negrito; contagem de células não vazias igual à soma das partes.

### Etapa 8. Figuras e fórmulas (`figuras.py`, `formulas.py`)

**Figuras**
1. Para cada `legenda_figura`, a região da figura é: abaixo do último bloco de texto que não pertence à figura até o topo da legenda, na largura da página útil. Refinar pela união dos bboxes de imagens (exceto fundo) e desenhos vetoriais nessa faixa.
2. Linhas de texto dentro da região = rótulos da figura (não entram no texto corrido). Guardar em `extra["rotulos"]`.
3. Recortar com `page.get_pixmap(clip=regiao, dpi=200)` e salvar `normas/<id>/assets/figura-<num>.png` (número com dois dígitos; anexos: `figura-a-05.png`). Se a imagem raster original for maior que o recorte, salvar a original também.
4. Bloco "Legenda" com itens abaixo da figura → lista Markdown, mantida no texto.

**Fórmulas**
1. Detectar fórmula em destaque: linha centralizada (ou com tab) terminando em `(\d+)` alinhado à direita; ou linha marcada com `pua=True`; ou imagem pequena (altura < 60 pt) fora de figura.
2. Se não houver PUA nem imagem: converter o texto inline já marcado para LaTeX simples (`R<sub>X</sub>` → `R_X`, `×` → `\times`, `≤` → `\le`, `Δ` → `\Delta`, `√` → `\sqrt{}` quando claro). Emitir `$$ ... \tag{n} $$`.
3. Se houver PUA ou imagem: recortar como `assets/equacao-<n>.png`, emitir a imagem e, dentro de `[formula]` ... `[/formula]`, o LaTeX das revisões (Etapa 9). Sem transcrição ainda: dentro dos marcadores, `PENDENTE: fórmula não transcrita.` seguido do texto bruto num bloco de código, e um item em `revisao.md`.
4. Bloco "onde" seguinte vira lista de definições de variáveis.

**Comando `recortes <id>`:** gera os PNGs de todas as figuras e fórmulas pendentes em `build/<id>/recortes/` e um `pendencias.yaml` com o esqueleto a ser preenchido (id, página, legenda, rótulos extraídos).

**Aceite:** 5419-1 Figura 1 gera PNG legível e rótulos `ABNT NBR 5419-2`, `PDA`, `SPDA`, `MPS`; equação (3) da 5419-2 sai em LaTeX sem revisão manual.

### Etapa 9. Revisões (`revisoes.py`) e descrição das figuras pelo Kiro

As descrições de figuras e as fórmulas que vêm de imagem são escritas **manualmente pelo Kiro**, numa sessão de chat, sem API de visão no pipeline. O pipeline só lê o resultado em `config/<id>/revisoes.yaml`.

Formato de `config/<id>/revisoes.yaml`:
```yaml
figuras:
  "1":
    arquivo: assets/figura-01.png
    hash_recorte: "sha256 do PNG usado ao descrever"
    descricao: |
      Fluxograma de decisão. Começa em "Identificar a estrutura a ser protegida" ...
    mermaid: |
      flowchart TD
        A[Identificar a estrutura a ser protegida] --> B[Identificar os tipos de perdas relevantes]
        ...
    revisado_por: "ia"              # "ia" (Kiro escreveu) | "humano" (você conferiu)
equacoes:
  "3":
    hash_recorte: "..."
    latex: 'R_X = N_X \times P_X \times L_X'
    revisado_por: "ia"
correcoes_texto:
  - pagina: 48
    de: "RA . IΔn ≤ UL"
    para: "R<sub>A</sub> · I<sub>Δn</sub> ≤ U<sub>L</sub>"
```

Regras para quem preenche (vão também para o steering `nova-norma.md`):
- Descrever o que a figura mostra de forma objetiva, sem acrescentar requisitos ou interpretações normativas.
- Fluxograma → Mermaid `flowchart`, texto dos nós idêntico ao da figura.
- Esquema elétrico (TN, TT, IT etc.) → descrição dos condutores, ligações, pontos de aterramento e massas, na ordem esquerda→direita.
- Gráfico → eixos, unidades, curvas e pontos notáveis legíveis.
- Fórmula → LaTeX exato, conferindo cada índice.
- Todo item escrito pelo Kiro entra com `revisado_por: ia`. Só você troca para `humano`.
- O renderizador escolhe o marcador pelo campo: `ia` → `[imagem]` / `[formula]`; `humano` → `[imagem revisada]` / `[formula revisada]` (formato na Etapa 1).
- Se o `hash_recorte` não bater com o PNG atual (a figura mudou, por exemplo numa nova edição), o item volta a ser tratado como `ia` e aparece em `revisao.md` como "recorte alterado desde a descrição".

**Fluxo de descrição com o Kiro** (passo a passo para a sessão de chat):
1. Rodar `mise exec -- python -m nbr2md recortes <id>`. Gera `build/<id>/recortes/*.png` e `build/<id>/recortes/pendencias.yaml` (número, página, legenda, rótulos extraídos, hash).
2. Pedir ao Kiro: "descreva as figuras pendentes de `<id>`". O Kiro lê cada PNG com a ferramenta de leitura de imagem, usa a legenda e os rótulos como apoio e grava a entrada em `revisoes.yaml` com `revisado_por: ia`. Lotes de até 10 figuras por sessão, para manter a atenção em cada uma.
3. Reconverter. As descrições aparecem no Markdown entre `[imagem]` e `[/imagem]`.
4. Você revisa (buscando `[imagem]` ou lendo a seção "Pendentes de revisão humana" de `revisao.md`), corrige o texto em `revisoes.yaml` se precisar e troca para `revisado_por: humano`. Na próxima conversão o marcador vira `[imagem revisada]`.

O pipeline aplica `correcoes_texto` após a Etapa 6 (substituição exata dentro da página indicada; falha se o texto `de` não for encontrado, para não aplicar correção obsoleta).

### Etapa 10. Árvore de seções e renderização (`estrutura.py`, `renderizar.py`, `chunks.py`)

**Árvore**
- Pilha por nível: o nível de `5.1.5.4` é 4 (número de partes). Anexo `A` é nível 1; `A.3` nível 2.
- Blocos não numerados entram no nó corrente.
- `Tabela`, `Figura`, `NOTA` pertencem à seção onde aparecem.

**Renderização** (`nbr-<id>.md`): seguir exatamente `FORMATO-SAIDA.md`. Linha em branco entre blocos. Quebra de linha só entre blocos (não quebrar parágrafo em 80 colunas).

**Arquivos por seção** (`secoes/`): um arquivo por nó de nível 1 (inclui anexos e preliminares). Cada arquivo repete um front matter curto (`norma`, `id`, `secao`, `titulo`) e um link para o arquivo único. Caminhos de imagem ajustados (`../assets/...`).

**Referências cruzadas** (opcional, fase 2): transformar `ver 5.1.6.2`, `tabela 18`, `Figura 7`, `Anexo B` em links para âncoras. Só quando o alvo existir na árvore.

**`chunks.jsonl`** (um objeto JSON por linha, um por parágrafo numerado / definição / tabela / figura; parágrafos sem número entram no chunk da seção pai):
```json
{"id":"nbr-5410#5.1.5.4.2","norma":"ABNT NBR 5410:2004","secao":"5.1.5.4.2",
 "caminho":["5 Proteção para garantir segurança","5.1 Proteção contra choques elétricos","5.1.5 ...","5.1.5.4 ..."],
 "tipo":"requisito","paginas":[53],"texto":"Se, em espaços nos quais ...",
 "referencias":["5.1.5.4.1","Tabela 18","Figura 7"]}
```
Chunks do tipo `figura` têm `texto` com a legenda + a descrição **com os marcadores `[imagem]`/`[imagem revisada]` preservados**, mais os campos `"imagem":"assets/figura-07.png"` e `"descricao_revisada": false|true`. O mesmo vale para fórmulas transcritas (`"formula_revisada"`).
Limite de 1 500 tokens por chunk (estimar como caracteres/4); tabela maior é dividida por grupos de linhas, repetindo o cabeçalho.

**`termos.json`**: lista `{numero, termo, termo_en, definicao}` extraída da Seção 3.

**`manifest.json`**: id, metadados, sha256 do PDF, versão do conversor, data, contagens (seções, tabelas, figuras, equações, pendências).

**`normas/llms.txt`**: índice gerado com uma linha por norma: título, id, link para o arquivo único e para `secoes/`.

### Etapa 11. Validação (`validar.py`), o controle de "nada se perde"

Gera `normas/<id>/revisao.md` e retorna código ≠ 0 se algum critério bloqueante falhar.

| Verificação | Como | Bloqueante |
|---|---|---|
| Cobertura de texto | multiconjunto de palavras do texto limpo (Etapa 4, sem sumário/capa) vs palavras do Markdown sem marcação; mostrar palavras faltantes com página | sim, se < 99,5% |
| Cobertura cruzada (pdfplumber) | ver "Validação com segundo extrator", abaixo | sim, se < 99,0% |
| Glifos | nenhum `⟦glifo:` no Markdown; todo `(cid:N)` do pdfplumber corresponde a uma entrada de `mapa_glifos` | sim |
| Texto extra | palavras no Markdown que não estão no PDF, ignorando o conteúdo entre `[imagem…]`/`[/imagem]` e `[formula…]`/`[/formula]` | sim, se > 0,2% |
| Marcadores balanceados | todo `[imagem]`/`[imagem revisada]` tem `[/imagem]` (idem `[formula]`), sem aninhamento; toda figura com legenda tem exatamente um bloco de descrição | sim |
| Caracteres proibidos | lista da Etapa 1 | sim |
| Marca d'água/CNPJ | regex | sim |
| Sumário vs árvore | toda entrada do sumário existe como seção com mesmo número e título | sim |
| Sequência de numeração | sem saltos (`5.1.3` seguido de `5.1.5` sem `5.1.4` gera alerta) | não |
| Tabelas e figuras | `Tabela 1..N` e `Figura 1..N` (e por anexo) sem lacunas; toda menção "tabela X" no texto tem alvo | sim para lacunas |
| Notas de rodapé | todo marcador `[^x]` tem definição e vice-versa | sim |
| Pendências | seção "Pendentes de revisão humana" em `revisao.md`: cada `[imagem]`/`[formula]` não revisado, com número, página e caminho do PNG; e cada `PENDENTE` | não (lista) |
| Markdown válido | `npx markdownlint-cli2` (Node 22 já está no mise) com regras ajustadas para HTML inline | não |

**Validação com segundo extrator (pdfplumber).** A cobertura da primeira linha da tabela usa o próprio texto do PyMuPDF como referência. Se o PyMuPDF não enxergar um trecho, o erro não aparece. Por isso há uma conferência com um extrator independente:
1. Para cada página fora da capa e do sumário, `pdfplumber.open(pdf).pages[i]` e `page.filter(lambda o: o.get("object_type") != "char" or o.get("upright", True))`, para descartar texto girado (marca d'água), como faz o MarkItDown. Depois `extract_words(keep_blank_chars=False, x_tolerance=1.5, extra_attrs=["fontname"])` (o `fontname` é necessário no passo 3).
2. Descartar palavras nas faixas de cabeçalho e rodapé (mesmas frações de `defaults.yaml`) e as que casam com as regex de remoção.
3. Trocar cada `(cid:N)` pelo caractere de `mapa_glifos` da fonte daquele caractere. `(cid:N)` sem mapeamento é erro bloqueante (linha "Glifos").
4. Normalizar dos dois lados (NFC, minúsculas, sem pontuação nas pontas, `²`→`2`, `<sub>`/`<sup>` removidos) e comparar os multiconjuntos de palavras **por página**, usando os marcadores `<!-- p. N -->` do Markdown para separar as páginas.
5. Relatar em `revisao.md` as páginas com cobertura < 98%, com as palavras faltantes. Palavras de rótulos de figura (dentro das regiões de figura da Etapa 8) contam como cobertas se estiverem na lista "Rótulos presentes na figura".

Diferenças de hifenização e de palavras coladas (`mg/m2e`, comum no pdfminer) são toleradas por uma segunda tentativa de casamento que junta pares de palavras adjacentes antes de declarar a palavra como faltante.

**Teste de regressão:** `tests/fixtures/<id>/` com 10 trechos verificados à mão por norma (incluindo uma tabela e uma fórmula). Qualquer mudança que altere esses trechos quebra o teste.

### Etapa 12. Processo para cada nova NBR

1. Copiar o PDF para `nbr/<numero>/`.
2. Criar `config/<id>/norma.yaml` com `id` e `fonte`.
3. `mise exec -- python -m nbr2md converter <id>`.
4. `mise exec -- python -m nbr2md validar <id>` e ler `revisao.md`.
5. Para glifos desconhecidos: abrir `build/<id>/glifos-desconhecidos.json`, renderizar o trecho (`inspecionar <pdf> --pagina N --glifos --png`), identificar o caractere visualmente, adicionar em `mapa_glifos` e conferir que o `(cid:N)` do pdfplumber bate. Outros defeitos de caractere vão para `mapa_caracteres`.
6. `recortes <id>` → o Kiro descreve as figuras em `revisoes.yaml` (fluxo da Etapa 9) → você revisa e troca `revisado_por` para `humano`.
7. Reconverter, validar até não haver bloqueantes.
8. Adicionar fixtures de regressão e fazer commit de `nbr/<numero>/`, `config/<id>/` e `normas/<id>/`.

Se uma nova norma exigir mudança no código (não só configuração), a mudança precisa manter os testes das normas anteriores passando.

### Etapa 12a. Nova edição de uma norma já convertida (substituição)

A edição nova substitui a antiga. O `id` e as pastas não mudam; o histórico fica só no Git.

1. Substituir o PDF em `nbr/<numero>/` (apagar o antigo, copiar o novo).
2. Atualizar `fonte` em `config/<id>/norma.yaml` se o nome do arquivo mudou. Rever `mapa_glifos`, `mapa_caracteres` e `paginas` (capa, sumário), que podem ter mudado.
3. Não apagar `revisoes.yaml`. Rodar `converter` e `validar`:
   - `correcoes_texto` cujo texto `de` não existe mais falham e precisam ser removidas ou refeitas;
   - figuras e fórmulas cujo `hash_recorte` mudou voltam para `[imagem]`/`[formula]` (pendentes) e aparecem em `revisao.md`;
   - figuras com o mesmo hash mantêm a descrição e o status de revisão.
4. O conversor apaga e regenera `normas/<id>/` por completo (inclusive `assets/` e `secoes/`), para não sobrar arquivo da edição antiga. Antes de apagar, confere que o caminho está dentro de `normas/`.
5. Atualizar as fixtures de regressão da norma com trechos da nova edição.
6. Commit único com mensagem `ABNT NBR <numero>: substitui edição <ano antigo> por <ano novo>`.

---

## 6. Arquivos Kiro a criar

**`.kiro/steering/produto.md`** (sempre incluído): objetivo do projeto, princípio "nada se perde", proibição de parafrasear texto normativo, público (IAs e RAG).

**`.kiro/steering/tecnologia.md`** (sempre incluído): Python 3.12 via mise; rodar tudo com `mise exec -- python ...`; PyMuPDF como única dependência de extração; nada de chamadas de API dentro do pipeline; testes com `mise exec -- python -m pytest -q`.

**`.kiro/steering/formato-saida.md`** (`inclusion: fileMatch`, `fileMatchPattern: 'normas/**/*.md'` e também referenciado em `renderizar.py`): resumo da Etapa 1, com `#[[file:docs/FORMATO-SAIDA.md]]`.

**`.kiro/steering/nova-norma.md`** (`inclusion: manual`): o passo a passo das Etapas 12 e 12a.

**`.kiro/steering/descrever-figuras.md`** (`inclusion: manual`): as regras de descrição e o fluxo da Etapa 9, incluindo: gravar sempre com `revisado_por: ia`, nunca marcar como `humano`, preencher `hash_recorte` com o hash de `pendencias.yaml`, e o formato dos marcadores `[imagem]`/`[formula]`.

**Spec `.kiro/specs/nbr2md/`**: `requirements.md` derivado das Seções 2 e 5 (critérios de aceite de cada etapa viram requisitos), `design.md` derivado das Seções 3 e 4, `tasks.md` com uma tarefa por etapa (0 a 12a), na ordem deste plano.

**Hook sugerido:** `PostFileSave` em `src/nbr2md/**/*.py` rodando `mise exec -- python -m pytest -q`.

---

## 7. Ordem sugerida e marcos

| Marco | Etapas | Resultado verificável |
|---|---|---|
| M1 | 0–4 | texto limpo das 5 normas sem marca d'água, cabeçalho ou caractere quebrado |
| M2 | 5–6 | NBR 5419-1 (a menor) em Markdown com hierarquia correta, ainda sem tabelas/figuras |
| M3 | 7 | tabelas da 5419-2 e da 5410 corretas, inclusive as que atravessam páginas |
| M4 | 8–9 | figuras recortadas e fórmulas em LaTeX, revisões preenchidas para a 5419-1 |
| M5 | 10–11 | as 5 normas passam na validação; `chunks.jsonl`, `termos.json`, `llms.txt` gerados |
| M6 | 12 | steerings e spec criados; processo documentado no README |

Começar pela 5419-1 (87 páginas, edição 2026, layout mais limpo) e usar a 5410 como teste de robustez (layout de 2004, caracteres trocados, número da seção em linha separada).

---

## 8. Decisões do dono do repositório

1. **Repositório privado.** PDFs (`nbr/`) e saída (`normas/`) são versionados. A marca d'água continua sendo removida porque é ruído para a IA (e expõe dados do comprador).
2. **Figuras descritas manualmente pelo Kiro**, sem API de visão no pipeline (Etapa 9). Descrições ficam entre `[imagem]` e `[/imagem]` para revisão manual posterior; após a revisão, a abertura vira `[imagem revisada]`. Fórmulas transcritas a partir de imagem usam `[formula]` ... `[/formula]` com a mesma lógica.
3. **Três formatos de saída:** arquivo único, arquivos por seção e `chunks.jsonl` (Etapa 10).
4. **Nova edição substitui a anterior.** O `id` não tem ano; processo na Etapa 12a.
