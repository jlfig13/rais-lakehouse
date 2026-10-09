---
aula: 5
titulo: "Repositório, Git e configuração por ambiente"
origem: ['Guia Parte 3', 'Guia Parte 7.1', 'Guia Parte 7.2']
depende_de: [1, 3]
checks: ['a05_repositorio_git', 'a05_env_ignorado', 'a05_env_nao_versionado', 'a05_estrutura', 'a05_settings_padrao']
---

# Aula 05 — Repositório, Git e configuração por ambiente

<!-- Página GERADA por scripts/gerar_curso.py. Edite curso/aulas.yml. -->

**Conteúdo completo da aula (13 seções):** [abrir o documento da Aula 05](https://claude.ai/code/artifact/deb2b052-a840-40d4-b0da-d8e8478ca6de)

| | |
| --- | --- |
| Origem no guia | Guia Parte 3, Guia Parte 7.1, Guia Parte 7.2 |
| Depende de | [Aula 01](aula-01.md), [Aula 03](aula-03.md) |
| Entregas | `.gitignore`, `config/settings.py`, `estrutura de pastas`, `primeiro commit` |
| Onde os checks rodam | Host (WSL/Linux) |

## Validação

```bash
make check-host AULA=05
```

Arquivo: `labcheck/host/test_aula05.py`. Cada execução grava o resultado em `progress/historico.jsonl`; depois rode `make progresso` para atualizar a página [Progresso](../progresso.md).

| Check | O que verifica |
| --- | --- |
| `a05_repositorio_git` | repositorio git |
| `a05_env_ignorado` | env ignorado |
| `a05_env_nao_versionado` | env nao versionado |
| `a05_estrutura` | estrutura |
| `a05_settings_padrao` | settings padrao |
