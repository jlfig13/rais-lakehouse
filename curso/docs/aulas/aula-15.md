---
aula: 15
titulo: "Tuning: threads, memória, partições e Spark UI"
origem: ['Guia Parte 14']
depende_de: [14]
checks: ['a15_memoria_cabe_no_container', 'a15_threads_explicitas', 'a15_benchmark_registrado', 'a15_adr_tuning']
---

# Aula 15 — Tuning: threads, memória, partições e Spark UI

<!-- Página GERADA por scripts/gerar_curso.py. Edite curso/aulas.yml. -->

**Conteúdo completo da aula (13 seções):** [abrir o documento da Aula 15](https://claude.ai/code/artifact/b0aac994-bba9-4da2-8169-69b801a42a73)

| | |
| --- | --- |
| Origem no guia | Guia Parte 14 |
| Depende de | [Aula 14](aula-14.md) |
| Entregas | `scripts/bench.sh`, `docs/benchmark.csv`, `ADR de configuração padrão em docs/decisoes.md`, `.env ajustado` |
| Onde os checks rodam | Container spark |

## Validação

```bash
make check AULA=15 ANO=2022
```

Arquivo: `labcheck/test_aula15.py`. Cada execução grava o resultado em `progress/historico.jsonl`; depois rode `make progresso` para atualizar a página [Progresso](../progresso.md).

| Check | O que verifica |
| --- | --- |
| `a15_memoria_cabe_no_container` | memoria cabe no container |
| `a15_threads_explicitas` | threads explicitas |
| `a15_benchmark_registrado` | benchmark registrado |
| `a15_adr_tuning` | adr tuning |
