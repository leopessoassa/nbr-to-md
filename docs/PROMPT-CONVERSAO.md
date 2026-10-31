# Prompt para iniciar a conversão de uma NBR

## Como usar

1. Abra um chat novo no Kiro (modo Vibe, Autopilot).
2. Copie o bloco do prompt, abaixo.
3. Troque as duas linhas marcadas com `<<< TROCAR` pelo arquivo e pelo id da tabela a seguir.
4. Converta **um arquivo por chat**. Comece pela 5419-1, que é a mais curta e tem o layout mais limpo. Ela serve para construir o conversor. A 5410 fica por último, porque tem 31 glifos quebrados.

| Ordem | Arquivo | Id |
|---|---|---|
| 1 | `nbr/5419/NBR5419-1 - Princípios gerais.pdf` | `nbr-5419-1` |
| 2 | `nbr/5419/NBR5419-2 - Gerenciamento de risco.pdf` | `nbr-5419-2` |
| 3 | `nbr/5419/NBR5419-3 - Danos físicos a estruturas e perigos à vida.pdf` | `nbr-5419-3` |
| 4 | `nbr/5419/NBR5419-4 - Sistemas elétricos e eletrônicos internos.pdf` | `nbr-5419-4` |
| 5 | `nbr/5410/NBR5410.pdf` | `nbr-5410` |

No primeiro chat, o conversor ainda não existe, e a IA vai implementá-lo (Modo A). Nos chats seguintes, ela usa o conversor existente e só ajusta a configuração ou o código quando for necessário (Modo B).

## Prompt

````text
Você vai converter UMA norma técnica (NBR) de PDF para Markdown neste repositório.

ARQUIVO A CONVERTER: nbr/5419/NBR5419-1 - Princípios gerais.pdf     <<< TROCAR
ID DA NORMA:         nbr-5419-1                                      <<< TROCAR

## 1. Leia antes de qualquer ação

1. Leia o arquivo `docs/PLANO-CONVERSAO.md` inteiro. Ele é a especificação. Siga as regras, os nomes de arquivo, os formatos e os critérios de aceite exatamente como estão escritos.
2. Na Seção 1 do plano, releia o que foi diagnosticado para o ARQUIVO A CONVERTER.
3. Se existirem, leia `docs/FORMATO-SAIDA.md` e os arquivos em `.kiro/steering/`.
4. Verifique se `src/nbr2md/` existe:
   - Não existe: siga o MODO A.
   - Existe: siga o MODO B.

## 2. Escopo (obrigatório)

- Converta SOMENTE o ARQUIVO A CONVERTER. Não abra, não converta e não gere saída para nenhum outro PDF de `nbr/`.
- Grave somente em: `src/`, `tests/`, `config/defaults.yaml`, `config/<ID DA NORMA>/`, `build/<ID DA NORMA>/`, `normas/<ID DA NORMA>/`, `normas/llms.txt`, `docs/FORMATO-SAIDA.md`, `.kiro/steering/`, `pyproject.toml`, `mise.toml`, `.gitignore` e `README.md`.
- Não altere `config/<outro id>/` nem `normas/<outro id>/`. Se uma mudança no código alterar a saída de outra norma já convertida, os testes de regressão dela precisam continuar passando. Se não passarem, pare e me explique.
- Não faça commit nem push. Eu faço.
- Antes de apagar qualquer coisa fora de `build/<ID DA NORMA>/` e `normas/<ID DA NORMA>/`, me pergunte.

## 3. Ambiente

- Windows com shell bash. O Python 3.12 é gerenciado pelo mise.
- TODO comando Python deve começar com `mise exec -- python`. Exemplos:
  - `mise exec -- python -m pip install -e ".[dev]"`
  - `mise exec -- python -m nbr2md converter <ID DA NORMA>`
  - `mise exec -- python -m pytest -q`
- Para ver acentos no terminal, use `export PYTHONIOENCODING=utf-8` no mesmo comando.
- Não rode processos que não terminam sozinhos (watch, servidores).
- Bibliotecas já instaladas: pymupdf 1.28, pdfplumber 0.11, pypdf. Não instale MarkItDown, Docling, Marker nem bibliotecas de ML.

## 4. MODO A: o conversor ainda não existe

Implemente o plano em marcos, trabalhando com o ARQUIVO A CONVERTER. Ao final de cada marco, PARE e me mostre o relatório da Seção 7 deste prompt. Só siga para o próximo marco quando eu responder.

- Marco 0 (Etapa 0 do plano, mais os steerings `produto.md` e `tecnologia.md` da Seção 6 do plano): estrutura do projeto, `pyproject.toml`, CLI com `--help` funcionando, `.gitignore`.
- Marco M1 (Etapas 1 a 4): `docs/FORMATO-SAIDA.md`, configuração, extração e limpeza. Mostre a contagem de linhas removidas por tipo (marca d'água, cabeçalho, rodapé) e o conteúdo de `build/<ID>/glifos-desconhecidos.json`.
- Marco M2 (Etapas 5 e 6): marcação inline, blocos e classificação.
- Marco M3 (Etapa 7): tabelas.
- Marco M4 (Etapa 8, mais o comando `recortes`): figuras e fórmulas, ainda sem descrições.
- Marco M5 (Etapas 10 e 11): árvore, os três formatos de saída e a validação passando sem bloqueantes.
- Marco M6 (Etapa 9): descrição das figuras e das fórmulas que vieram de imagem (regras na Seção 6 deste prompt).
- Marco M7: os steerings restantes da Seção 6 do plano (`formato-saida.md`, `nova-norma.md`, `descrever-figuras.md`) e a seção "Como converter uma norma" no `README.md`.

A cada etapa, crie os testes do critério de aceite daquela etapa e rode-os. Os critérios citam várias normas. Implemente só os que se aplicam ao ARQUIVO A CONVERTER e liste os demais como "a verificar quando a norma X for convertida".

## 5. MODO B: o conversor já existe

1. Rode `mise exec -- python -m pytest -q`. Se algo falhar ANTES de você mudar qualquer coisa, pare e me avise.
2. Siga a Etapa 12 do plano para o ARQUIVO A CONVERTER, passo a passo:
   - crie `config/<ID>/norma.yaml`;
   - rode `converter` e `validar`;
   - leia `normas/<ID>/revisao.md` e `build/<ID>/glifos-desconhecidos.json`.
3. Resolva os problemas nesta ordem de preferência:
   - ajuste em `config/<ID>/norma.yaml`;
   - ajuste em `config/defaults.yaml`, só se a regra servir para qualquer NBR;
   - mudança no código, com teste novo, mantendo os testes das outras normas passando.
4. Glifos desconhecidos: renderize cada um (`inspecionar <pdf> --pagina N --glifos --png`), abra o PNG, identifique o caractere, confira o `(cid:N)` do pdfplumber e só então adicione em `mapa_glifos`. Nunca adivinhe um glifo sem ver a imagem.
5. PARE e me mostre o relatório da Seção 7 quando a validação passar sem bloqueantes, antes de descrever as figuras.
6. Com o meu OK, faça a descrição das figuras (Seção 6 deste prompt) e o relatório final.

## 6. Descrição de figuras e fórmulas (Etapa 9 do plano)

- Rode `mise exec -- python -m nbr2md recortes <ID>` e trabalhe a partir de `build/<ID>/recortes/pendencias.yaml`.
- Abra cada PNG com a ferramenta de leitura de imagem. Use a legenda e os rótulos extraídos como apoio.
- Trabalhe em lotes de até 10 figuras. Depois de cada lote, grave em `config/<ID>/revisoes.yaml` e reconverta.
- Para cada item, grave `revisado_por: ia` e o `hash_recorte` de `pendencias.yaml`. NUNCA grave `revisado_por: humano`; só eu faço isso.
- Descreva o que a figura mostra, de forma objetiva. Não acrescente requisitos nem interpretações normativas.
  - Fluxograma: Mermaid `flowchart`, com o texto dos nós idêntico ao da figura.
  - Esquema elétrico: condutores, ligações, aterramentos e massas, da esquerda para a direita.
  - Gráfico: eixos, unidades, curvas e pontos legíveis.
  - Fórmula: LaTeX exato, conferindo cada índice e expoente contra a imagem.
- No Markdown final, cada descrição fica entre `[imagem]` e `[/imagem]` e cada fórmula transcrita fica entre `[formula]` e `[/formula]`, com cada marcador sozinho na sua linha. Isso é feito pelo renderizador; não escreva os marcadores à mão no Markdown gerado.
- Se uma figura estiver ilegível, grave `PENDENTE:` com o motivo, em vez de inventar.

## 7. Relatório ao fim de cada marco ou parada

Mostre, nesta ordem:
1. O que foi feito, com a lista de arquivos criados ou alterados.
2. Resultado dos testes (`pytest -q`): quantos passaram e quantos falharam.
3. Números da validação, quando ela já existir: cobertura PyMuPDF (%), cobertura cruzada pdfplumber (%), páginas abaixo de 98%, seções, tabelas, figuras e fórmulas encontradas, glifos desconhecidos, pendências.
4. Três trechos curtos do Markdown gerado, de tipos diferentes (por exemplo: título com parágrafo numerado, tabela e nota), copiados do arquivo, com a página do PDF de origem. Antes de mostrar, compare cada trecho com o PDF renderizado da página (`page.get_pixmap`).
5. Problemas encontrados e decisões tomadas que não estavam no plano.
6. O que falta e qual é o próximo passo.

## 8. Regras que não podem ser quebradas

- O texto da norma nunca é parafraseado, resumido ou "corrigido" por estilo. Correção de texto só via `correcoes_texto` em `revisoes.yaml`, e só para defeito de extração comprovado pela imagem da página.
- Não baixe limites de validação, não desligue verificações e não remova texto para fazer a validação passar. Se um limite parecer errado, pare e me explique com números.
- A flag `TEXT_CID_FOR_UNKNOWN_UNICODE` do PyMuPDF fica sempre desligada (ver Etapa 3 do plano).
- Marca d'água, CNPJ e número de pedido nunca aparecem em `normas/`.
- Se o plano estiver ambíguo ou contradizer o que você observa no PDF, pare e me pergunte. Não escolha sozinho.

## 9. Definição de pronto

A conversão do ARQUIVO A CONVERTER está pronta quando:
- `mise exec -- python -m nbr2md validar <ID>` termina com código 0;
- existem `normas/<ID>/<ID>.md`, `normas/<ID>/secoes/`, `normas/<ID>/chunks.jsonl`, `normas/<ID>/termos.json`, `normas/<ID>/manifest.json`, `normas/<ID>/revisao.md` e `normas/<ID>/assets/`;
- `normas/llms.txt` lista a norma;
- toda figura com legenda tem um bloco `[imagem]` (descrição ou `PENDENTE:`);
- `tests/fixtures/<ID>/` tem 10 trechos verificados contra a imagem da página, e `pytest -q` passa por inteiro.

Comece pela Seção 1.
````
