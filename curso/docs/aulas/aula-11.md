---
aula: 11
titulo: "Ingestão e camada bronze"
origem: ['Guia Parte 8', 'Guia Parte 9']
depende_de: [9, 10]
checks: ['a11_bronze_delta', 'a11_ano_carregado', 'a11_tudo_string', 'a11_arquivo_origem', 'a11_idempotente']
---

# Aula 11 — Ingestão e camada bronze

<!-- Página GERADA por scripts/gerar_curso.py. Edite curso/aulas.yml. -->

**Conteúdo completo da aula (13 seções):** [abrir o documento da Aula 11](https://claude.ai/code/artifact/b043954e-5c45-4bae-b96a-05f16753aa75)

| | |
| --- | --- |
| Origem no guia | Guia Parte 8, Guia Parte 9 |
| Depende de | [Aula 09](aula-09.md), [Aula 10](aula-10.md) |
| Entregas | `src/ingest.py`, `src/bronze.py`, `notebooks/02_bronze.ipynb` |
| Onde os checks rodam | Container spark |

## Validação

```bash
make check AULA=11 ANO=2022
```

Arquivo: `labcheck/test_aula11.py`. Cada execução grava o resultado em `progress/historico.jsonl`; depois rode `make progresso` para atualizar a página [Progresso](../progresso.md).

| Check | O que verifica |
| --- | --- |
| `a11_bronze_delta` | bronze delta |
| `a11_ano_carregado` | ano carregado |
| `a11_tudo_string` | tudo string |
| `a11_arquivo_origem` | arquivo origem |
| `a11_idempotente` | Em todas as versões da tabela que contêm o ano, a contagem dele é a mesma. |
