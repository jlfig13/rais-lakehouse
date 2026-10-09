---
aula: 12
titulo: "Camada silver: tipagem, validação e campos derivados"
origem: ['Guia Parte 10']
depende_de: [11]
checks: ['a12_silver_delta', 'a12_contagem_igual_bronze', 'a12_tipos_do_contrato', 'a12_uf_valida', 'a12_idade_plausivel']
---

# Aula 12 — Camada silver: tipagem, validação e campos derivados

<!-- Página GERADA por scripts/gerar_curso.py. Edite curso/aulas.yml. -->

**Conteúdo completo da aula (13 seções):** [abrir o documento da Aula 12](https://claude.ai/code/artifact/fd16d518-50fe-44bc-adfc-dc512f42f943)

| | |
| --- | --- |
| Origem no guia | Guia Parte 10 |
| Depende de | [Aula 11](aula-11.md) |
| Entregas | `src/silver.py`, `notebooks/03_silver.ipynb`, `docs/dicionario.md (decisões)` |
| Onde os checks rodam | Container spark |

## Validação

```bash
make check AULA=12 ANO=2022
```

Arquivo: `labcheck/test_aula12.py`. Cada execução grava o resultado em `progress/historico.jsonl`; depois rode `make progresso` para atualizar a página [Progresso](../progresso.md).

| Check | O que verifica |
| --- | --- |
| `a12_silver_delta` | silver delta |
| `a12_contagem_igual_bronze` | contagem igual bronze |
| `a12_tipos_do_contrato` | tipos do contrato |
| `a12_uf_valida` | uf valida |
| `a12_idade_plausivel` | idade plausivel |
