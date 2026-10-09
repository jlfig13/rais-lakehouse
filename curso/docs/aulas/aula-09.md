---
aula: 9
titulo: "O domínio RAIS: microdados, dicionário e armadilhas"
origem: ['Guia Parte 6', 'Guia Apêndice A']
depende_de: [5]
checks: ['a09_7z_na_landing', 'a09_7z_contem_txt', 'a09_dicionario_preenchido']
---

# Aula 09 — O domínio RAIS: microdados, dicionário e armadilhas

<!-- Página GERADA por scripts/gerar_curso.py. Edite curso/aulas.yml. -->

**Conteúdo completo da aula (13 seções):** [abrir o documento da Aula 09](https://claude.ai/code/artifact/41224932-e2c0-431d-8172-c8afac692149)

| | |
| --- | --- |
| Origem no guia | Guia Parte 6, Guia Apêndice A |
| Depende de | [Aula 05](aula-05.md) |
| Entregas | `staging/landing/<ano>/*.7z`, `docs/dicionario.md` |
| Onde os checks rodam | Container spark |

## Validação

```bash
make check AULA=09 ANO=2022
```

Arquivo: `labcheck/test_aula09.py`. Cada execução grava o resultado em `progress/historico.jsonl`; depois rode `make progresso` para atualizar a página [Progresso](../progresso.md).

| Check | O que verifica |
| --- | --- |
| `a09_7z_na_landing` | 7z na landing |
| `a09_7z_contem_txt` | 7z contem txt |
| `a09_dicionario_preenchido` | dicionario preenchido |
