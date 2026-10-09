---
aula: 3
titulo: "Docker Compose: serviços, rede, volumes e configuração"
origem: ['Guia Parte 2.3', 'Guia Parte 2.4', 'Guia Parte 4.6', 'Guia Parte 4.7', 'Guia Parte 4.8', 'Guia Parte 4.9']
depende_de: [2]
checks: ['a03_compose_valido', 'a03_servicos_no_ar', 'a03_minio_init_ok', 'a03_portas_so_locais']
---

# Aula 03 — Docker Compose: serviços, rede, volumes e configuração

<!-- Página GERADA por scripts/gerar_curso.py. Edite curso/aulas.yml. -->

**Conteúdo completo da aula (13 seções):** [abrir o documento da Aula 03](https://claude.ai/code/artifact/793081c7-12c1-461c-9264-a1ba634a16b5)

| | |
| --- | --- |
| Origem no guia | Guia Parte 2.3, Guia Parte 2.4, Guia Parte 4.6, Guia Parte 4.7, Guia Parte 4.8, Guia Parte 4.9 |
| Depende de | [Aula 02](aula-02.md) |
| Entregas | `docker-compose.yml`, `.env.example`, `Makefile`, `docker/minio/init-minio.sh`, `docker/minio/policy-rais.json` |
| Onde os checks rodam | Host (WSL/Linux) |

## Validação

```bash
make check-host AULA=03
```

Arquivo: `labcheck/host/test_aula03.py`. Cada execução grava o resultado em `progress/historico.jsonl`; depois rode `make progresso` para atualizar a página [Progresso](../progresso.md).

| Check | O que verifica |
| --- | --- |
| `a03_compose_valido` | compose valido |
| `a03_servicos_no_ar` | servicos no ar |
| `a03_minio_init_ok` | minio init ok |
| `a03_portas_so_locais` | portas so locais |
