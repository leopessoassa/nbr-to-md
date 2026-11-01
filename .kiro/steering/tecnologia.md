# Tecnologia

## Ambiente

- Windows com shell bash. Python 3.12, gerenciado pelo mise (`mise.toml`).
- **Todo comando Python começa com `mise exec -- python`.** Exemplos:
  - `mise exec -- python -m pip install -e ".[dev]"`
  - `mise exec -- python -m nbr2md converter nbr-5410`
  - `mise exec -- python -m pytest -q`
- Para ver acentos no terminal: `export PYTHONIOENCODING=utf-8` no mesmo comando.
- Não rodar processos que não terminam sozinhos (watch, servidores).

## Dependências

- Extração: PyMuPDF (`pymupdf>=1.28`) é a fonte principal de texto, imagens e desenhos.
- pdfplumber (`pdfplumber>=0.11`) é usado só como segundo extrator independente, na validação e no diagnóstico de glifos (`inspecionar --glifos`).
- Configuração: PyYAML.
- Testes: pytest (extra `dev`).
- Não usar MarkItDown, Docling, Marker nem bibliotecas de ML.

## Regras de código

- O pipeline é determinístico. Nada de chamadas de API de modelo dentro do conversor.
- A flag `TEXT_CID_FOR_UNKNOWN_UNICODE` do PyMuPDF fica sempre desligada.
- Limites de validação não são afrouxados para fazer um teste passar.
- Saída em UTF-8 e NFC.

## Testes

- `mise exec -- python -m pytest -q` deve passar por inteiro antes de qualquer entrega.
- Fixtures de regressão por norma ficam em `tests/fixtures/<id>/`.
