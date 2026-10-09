---
aula: 13
titulo: "Camada gold: perguntas de negócio e funções puras"
origem: ['Guia Parte 11', 'Guia Parte 15.3 (test_gap_sexo)']
depende_de: [12]
checks: ['a13_cinco_tabelas', 'a13_total_bate_silver', 'a13_uf_preenchida', 'a13_top10', 'a13_teste_gap_sexo']
---

# Aula 13 — Camada gold: perguntas de negócio e funções puras

<!-- Página GERADA por scripts/gerar_curso.py. Edite curso/aulas.yml. -->

**Conteúdo completo da aula (13 seções):** [abrir o documento da Aula 13](https://claude.ai/code/artifact/9899f93a-7b7c-4cbf-9663-51283e5d2b65)

| | |
| --- | --- |
| Origem no guia | Guia Parte 11, Guia Parte 15.3 (test_gap_sexo) |
| Depende de | [Aula 12](aula-12.md) |
| Entregas | `src/gold.py`, `tests/test_utils.py (test_gap_sexo)`, `notebooks/04_gold.ipynb` |
| Onde os checks rodam | Container spark |

## Validação

```bash
make check AULA=13 ANO=2022
```

Arquivo: `labcheck/test_aula13.py`. Cada execução grava o resultado em `progress/historico.jsonl`; depois rode `make progresso` para atualizar a página [Progresso](../progresso.md).

| Check | O que verifica |
| --- | --- |
| `a13_cinco_tabelas` | cinco tabelas |
| `a13_total_bate_silver` | total bate silver |
| `a13_uf_preenchida` | uf preenchida |
| `a13_top10` | top10 |
| `a13_teste_gap_sexo` | teste gap sexo |
