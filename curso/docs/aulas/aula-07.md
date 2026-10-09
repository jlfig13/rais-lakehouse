---
aula: 7
titulo: "PySpark I: DataFrames, transformações, agregações e SQL"
origem: ['Guia Parte 5.1', 'Guia Parte 5.2', 'Guia Parte 5.3', 'Guia Parte 5.4', 'Guia Parte 5.9']
depende_de: [6]
checks: ['a07_media_por_sexo', 'a07_admissoes_por_ano', 'a07_faixa_salarial', 'a07_sql_igual_dataframe']
---

# Aula 07 — PySpark I: DataFrames, transformações, agregações e SQL

<!-- Página GERADA por scripts/gerar_curso.py. Edite curso/aulas.yml. -->

**Conteúdo completo da aula (13 seções):** [abrir o documento da Aula 07](https://claude.ai/code/artifact/1b3a5a26-3bd2-4117-9d33-559b3b8b9532)

| | |
| --- | --- |
| Origem no guia | Guia Parte 5.1, Guia Parte 5.2, Guia Parte 5.3, Guia Parte 5.4, Guia Parte 5.9 |
| Depende de | [Aula 06](aula-06.md) |
| Entregas | `labs/__init__.py`, `labs/aula07.py`, `notebooks/01_fundamentos.ipynb` |
| Onde os checks rodam | Container spark |

## Validação

```bash
make check AULA=07 ANO=2022
```

Arquivo: `labcheck/test_aula07.py`. Cada execução grava o resultado em `progress/historico.jsonl`; depois rode `make progresso` para atualizar a página [Progresso](../progresso.md).

| Check | O que verifica |
| --- | --- |
| `a07_media_por_sexo` | media por sexo |
| `a07_admissoes_por_ano` | admissoes por ano |
| `a07_faixa_salarial` | faixa salarial |
| `a07_sql_igual_dataframe` | sql igual dataframe |
