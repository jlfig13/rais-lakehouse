---
aula: 10
titulo: "Delta Lake e código base: transações, utilitários e dimensões"
origem: ['Guia Parte 7.3', 'Guia Parte 7.4', 'Guia Parte 7.5', 'Guia Parte 13.1', 'Guia Parte 15.3']
depende_de: [6, 8]
checks: ['a10_testes_utils', 'a10_gravar_ano_idempotente', 'a10_replacewhere_protege', 'a10_dims_tipos']
---

# Aula 10 — Delta Lake e código base: transações, utilitários e dimensões

<!-- Página GERADA por scripts/gerar_curso.py. Edite curso/aulas.yml. -->

**Conteúdo completo da aula (13 seções):** [abrir o documento da Aula 10](https://claude.ai/code/artifact/c3c12a5b-9b8a-45a2-b3c1-63a91cbc0002)

| | |
| --- | --- |
| Origem no guia | Guia Parte 7.3, Guia Parte 7.4, Guia Parte 7.5, Guia Parte 13.1, Guia Parte 15.3 |
| Depende de | [Aula 06](aula-06.md), [Aula 08](aula-08.md) |
| Entregas | `src/utils.py (completo)`, `src/delta_io.py`, `src/dims.py`, `tests/conftest.py`, `tests/test_utils.py` |
| Onde os checks rodam | Container spark |

## Validação

```bash
make check AULA=10 ANO=2022
```

Arquivo: `labcheck/test_aula10.py`. Cada execução grava o resultado em `progress/historico.jsonl`; depois rode `make progresso` para atualizar a página [Progresso](../progresso.md).

| Check | O que verifica |
| --- | --- |
| `a10_testes_utils` | testes utils |
| `a10_gravar_ano_idempotente` | gravar ano idempotente |
| `a10_replacewhere_protege` | replacewhere protege |
| `a10_dims_tipos` | dims tipos |
