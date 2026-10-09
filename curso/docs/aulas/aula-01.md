---
aula: 1
titulo: "Arquitetura Lakehouse e o projeto RAIS Lakehouse"
origem: ['Guia Parte 1']
depende_de: []
checks: ['a01_adrs_registrados']
---

# Aula 01 — Arquitetura Lakehouse e o projeto RAIS Lakehouse

<!-- Página GERADA por scripts/gerar_curso.py. Edite curso/aulas.yml. -->

**Conteúdo completo da aula (13 seções):** [abrir o documento da Aula 01](https://claude.ai/code/artifact/2a86be26-af3d-40e8-9385-2e68ce777f1e)

| | |
| --- | --- |
| Origem no guia | Guia Parte 1 |
| Depende de | — |
| Entregas | `docs/decisoes.md` |
| Onde os checks rodam | Host (WSL/Linux) |

## Validação

```bash
.venv-host/bin/pytest -v labcheck/test_aula01.py   # ou: make check AULA=01
```

Arquivo: `labcheck/test_aula01.py`. Cada execução grava o resultado em `progress/historico.jsonl`; depois rode `make progresso` para atualizar a página [Progresso](../progresso.md).

| Check | O que verifica |
| --- | --- |
| `a01_adrs_registrados` | adrs registrados |
