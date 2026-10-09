---
aula: 6
titulo: "Ambiente no ar: SparkSession, Delta, S3A e teste de fumaça"
origem: ['Guia Parte 4.2', 'Guia Parte 4.9', 'Guia Parte 4.10', 'Guia Parte 7.3 (get_spark)']
depende_de: [3, 4, 5]
checks: ['a06_versao_spark', 'a06_config_s3a', 'a06_smoke_1000', 'a06_smoke_e_delta']
---

# Aula 06 — Ambiente no ar: SparkSession, Delta, S3A e teste de fumaça

<!-- Página GERADA por scripts/gerar_curso.py. Edite curso/aulas.yml. -->

**Conteúdo completo da aula (13 seções):** [abrir o documento da Aula 06](https://claude.ai/code/artifact/71275b02-cd69-41ca-bf72-89b88b7012b5)

| | |
| --- | --- |
| Origem no guia | Guia Parte 4.2, Guia Parte 4.9, Guia Parte 4.10, Guia Parte 7.3 (get_spark) |
| Depende de | [Aula 03](aula-03.md), [Aula 04](aula-04.md), [Aula 05](aula-05.md) |
| Entregas | `src/utils.py (get_spark)`, `scripts/smoke_test.py`, `labcheck/conftest.py`, `scripts/gerar_progresso.py` |
| Onde os checks rodam | Container spark |

## Validação

```bash
make check AULA=06 ANO=2022
```

Arquivo: `labcheck/test_aula06.py`. Cada execução grava o resultado em `progress/historico.jsonl`; depois rode `make progresso` para atualizar a página [Progresso](../progresso.md).

| Check | O que verifica |
| --- | --- |
| `a06_versao_spark` | versao spark |
| `a06_config_s3a` | config s3a |
| `a06_smoke_1000` | smoke 1000 |
| `a06_smoke_e_delta` | smoke e delta |
