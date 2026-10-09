---
aula: 14
titulo: "Pipeline completo, idempotência e operações Delta"
origem: ['Guia Parte 12', 'Guia Parte 13.2', 'Guia Parte 15.4 (checks.py)']
depende_de: [13]
checks: ['a14_varios_anos_na_gold', 'a14_checar_silver', 'a14_historico', 'a14_time_travel', 'a14_optimize']
---

# Aula 14 — Pipeline completo, idempotência e operações Delta

<!-- Página GERADA por scripts/gerar_curso.py. Edite curso/aulas.yml. -->

**Conteúdo completo da aula (13 seções):** [abrir o documento da Aula 14](https://claude.ai/code/artifact/1b766905-154a-48d2-9291-f43d5dfa6ee4)

| | |
| --- | --- |
| Origem no guia | Guia Parte 12, Guia Parte 13.2, Guia Parte 15.4 (checks.py) |
| Depende de | [Aula 13](aula-13.md) |
| Entregas | `src/run_pipeline.py`, `src/checks.py`, `notebooks/05_delta.ipynb` |
| Onde os checks rodam | Container spark |

## Validação

```bash
make check AULA=14 ANO=2022
```

Arquivo: `labcheck/test_aula14.py`. Cada execução grava o resultado em `progress/historico.jsonl`; depois rode `make progresso` para atualizar a página [Progresso](../progresso.md).

| Check | O que verifica |
| --- | --- |
| `a14_varios_anos_na_gold` | varios anos na gold |
| `a14_checar_silver` | checar silver |
| `a14_historico` | historico |
| `a14_time_travel` | time travel |
| `a14_optimize` | optimize |
