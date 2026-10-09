---
aula: 2
titulo: "Docker: imagens, containers e o Dockerfile do Spark"
origem: ['Guia Parte 2.1', 'Guia Parte 2.2', 'Guia Parte 4.2', 'Guia Parte 4.3', 'Guia Parte 4.4']
depende_de: [1]
checks: ['a02_imagem_existe', 'a02_java_17', 'a02_pyspark_delta', 'a02_jars_s3a_delta', 'a02_usuario_nao_root']
---

# Aula 02 — Docker: imagens, containers e o Dockerfile do Spark

<!-- Página GERADA por scripts/gerar_curso.py. Edite curso/aulas.yml. -->

**Conteúdo completo da aula (13 seções):** [abrir o documento da Aula 02](https://claude.ai/code/artifact/3a17b7ff-ce58-4699-b232-429afbe389e2)

| | |
| --- | --- |
| Origem no guia | Guia Parte 2.1, Guia Parte 2.2, Guia Parte 4.2, Guia Parte 4.3, Guia Parte 4.4 |
| Depende de | [Aula 01](aula-01.md) |
| Entregas | `docker/spark/Dockerfile`, `requirements.txt`, `requirements-dev.txt`, `.dockerignore` |
| Onde os checks rodam | Host (WSL/Linux) |

## Validação

```bash
make check-host AULA=02
```

Arquivo: `labcheck/host/test_aula02.py`. Cada execução grava o resultado em `progress/historico.jsonl`; depois rode `make progresso` para atualizar a página [Progresso](../progresso.md).

| Check | O que verifica |
| --- | --- |
| `a02_imagem_existe` | imagem existe |
| `a02_java_17` | java 17 |
| `a02_pyspark_delta` | pyspark delta |
| `a02_jars_s3a_delta` | jars s3a delta |
| `a02_usuario_nao_root` | usuario nao root |
