---
aula: 8
titulo: "PySpark II: joins, window functions, lazy evaluation e partições"
origem: ['Guia Parte 5.5', 'Guia Parte 5.6', 'Guia Parte 5.7', 'Guia Parte 5.8']
depende_de: [7]
checks: ['a08_maior_salario_por_uf', 'a08_join_broadcast', 'a08_detecta_shuffle', 'a08_particionado_pruning']
---

# Aula 08 — PySpark II: joins, window functions, lazy evaluation e partições

<!-- Página GERADA por scripts/gerar_curso.py. Edite curso/aulas.yml. -->

**Conteúdo completo da aula (13 seções):** [abrir o documento da Aula 08](https://claude.ai/code/artifact/a6511bda-2b14-4319-a278-e288ee8b9b5f)

| | |
| --- | --- |
| Origem no guia | Guia Parte 5.5, Guia Parte 5.6, Guia Parte 5.7, Guia Parte 5.8 |
| Depende de | [Aula 07](aula-07.md) |
| Entregas | `labs/aula08.py` |
| Onde os checks rodam | Container spark |

## Validação

```bash
make check AULA=08 ANO=2022
```

Arquivo: `labcheck/test_aula08.py`. Cada execução grava o resultado em `progress/historico.jsonl`; depois rode `make progresso` para atualizar a página [Progresso](../progresso.md).

| Check | O que verifica |
| --- | --- |
| `a08_maior_salario_por_uf` | maior salario por uf |
| `a08_join_broadcast` | join broadcast |
| `a08_detecta_shuffle` | detecta shuffle |
| `a08_particionado_pruning` | particionado pruning |
