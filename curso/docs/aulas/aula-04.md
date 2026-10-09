---
aula: 4
titulo: "MinIO e S3: buckets, S3A e menor privilégio"
origem: ['Guia Parte 4.1', 'Guia Parte 4.5', 'Guia Apêndice B']
depende_de: [3]
checks: ['a04_bucket_existe', 'a04_app_grava_no_rais', 'a04_app_nao_cria_bucket', 'a04_app_nao_e_admin']
---

# Aula 04 — MinIO e S3: buckets, S3A e menor privilégio

<!-- Página GERADA por scripts/gerar_curso.py. Edite curso/aulas.yml. -->

**Conteúdo completo da aula (13 seções):** [abrir o documento da Aula 04](https://claude.ai/code/artifact/b2146c2c-98fe-429c-8a64-45ef03038b2d)

| | |
| --- | --- |
| Origem no guia | Guia Parte 4.1, Guia Parte 4.5, Guia Apêndice B |
| Depende de | [Aula 03](aula-03.md) |
| Entregas | `docker/minio/init-minio.sh`, `docker/minio/policy-rais.json` |
| Onde os checks rodam | Host (WSL/Linux) |

## Validação

```bash
make check-host AULA=04
```

Arquivo: `labcheck/host/test_aula04.py`. Cada execução grava o resultado em `progress/historico.jsonl`; depois rode `make progresso` para atualizar a página [Progresso](../progresso.md).

| Check | O que verifica |
| --- | --- |
| `a04_bucket_existe` | bucket existe |
| `a04_app_grava_no_rais` | app grava no rais |
| `a04_app_nao_cria_bucket` | app nao cria bucket |
| `a04_app_nao_e_admin` | app nao e admin |
