---
aula: 16
titulo: "Qualidade, testes, CI e boas práticas de GitHub"
origem: ['Guia Parte 15', 'Guia Parte 16']
depende_de: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
checks: ['a16_testes_passam', 'a16_lint_passa', 'a16_workflow_ci', 'a16_readme_completo', 'a16_licenca']
---

# Aula 16 — Qualidade, testes, CI e boas práticas de GitHub

<!-- Página GERADA por scripts/gerar_curso.py. Edite curso/aulas.yml. -->

**Conteúdo completo da aula (13 seções):** [abrir o documento da Aula 16](https://claude.ai/code/artifact/02c8a8bb-a86e-4813-bbdb-a84118cf25a6)

| | |
| --- | --- |
| Origem no guia | Guia Parte 15, Guia Parte 16 |
| Depende de | [Aula 01](aula-01.md), [Aula 02](aula-02.md), [Aula 03](aula-03.md), [Aula 04](aula-04.md), [Aula 05](aula-05.md), [Aula 06](aula-06.md), [Aula 07](aula-07.md), [Aula 08](aula-08.md), [Aula 09](aula-09.md), [Aula 10](aula-10.md), [Aula 11](aula-11.md), [Aula 12](aula-12.md), [Aula 13](aula-13.md), [Aula 14](aula-14.md), [Aula 15](aula-15.md) |
| Entregas | `pyproject.toml`, `.github/workflows/ci.yml`, `README.md`, `LICENSE`, `tag v1.0.0` |
| Onde os checks rodam | Container spark |

## Validação

```bash
make check AULA=16 ANO=2022
```

Arquivo: `labcheck/test_aula16.py`. Cada execução grava o resultado em `progress/historico.jsonl`; depois rode `make progresso` para atualizar a página [Progresso](../progresso.md).

| Check | O que verifica |
| --- | --- |
| `a16_testes_passam` | testes passam |
| `a16_lint_passa` | lint passa |
| `a16_workflow_ci` | workflow ci |
| `a16_readme_completo` | readme completo |
| `a16_licenca` | licenca |
