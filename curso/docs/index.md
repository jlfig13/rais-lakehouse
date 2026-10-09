# RAIS Lakehouse — Plataforma de aprendizagem

Curso prático de PySpark, Delta Lake e MinIO construindo um lakehouse com os microdados da RAIS (bronze → silver → gold), tudo open source e local.

## Como estudar

1. Abra a aula na trilha abaixo e leia o documento completo (link no topo da página).
2. Faça o tutorial e o laboratório no seu ambiente (terminal, VS Code ou JupyterLab).
3. Rode os checks da aula. Só avance quando passarem.
4. Rode `make progresso` e veja a página [Progresso](progresso.md).

> Os checks verificam o **seu** ambiente. Este site não executa código e não mostra resultados que você não produziu.

## Trilha

| Aula | Título | Depende de | Checks |
| --- | --- | --- | --- |
| 01 | [Arquitetura Lakehouse e o projeto RAIS Lakehouse](aulas/aula-01.md) | — | 1 |
| 02 | [Docker: imagens, containers e o Dockerfile do Spark](aulas/aula-02.md) | 01 | 5 |
| 03 | [Docker Compose: serviços, rede, volumes e configuração](aulas/aula-03.md) | 02 | 4 |
| 04 | [MinIO e S3: buckets, S3A e menor privilégio](aulas/aula-04.md) | 03 | 4 |
| 05 | [Repositório, Git e configuração por ambiente](aulas/aula-05.md) | 01, 03 | 5 |
| 06 | [Ambiente no ar: SparkSession, Delta, S3A e teste de fumaça](aulas/aula-06.md) | 03, 04, 05 | 4 |
| 07 | [PySpark I: DataFrames, transformações, agregações e SQL](aulas/aula-07.md) | 06 | 4 |
| 08 | [PySpark II: joins, window functions, lazy evaluation e partições](aulas/aula-08.md) | 07 | 4 |
| 09 | [O domínio RAIS: microdados, dicionário e armadilhas](aulas/aula-09.md) | 05 | 3 |
| 10 | [Delta Lake e código base: transações, utilitários e dimensões](aulas/aula-10.md) | 06, 08 | 4 |
| 11 | [Ingestão e camada bronze](aulas/aula-11.md) | 09, 10 | 5 |
| 12 | [Camada silver: tipagem, validação e campos derivados](aulas/aula-12.md) | 11 | 5 |
| 13 | [Camada gold: perguntas de negócio e funções puras](aulas/aula-13.md) | 12 | 5 |
| 14 | [Pipeline completo, idempotência e operações Delta](aulas/aula-14.md) | 13 | 5 |
| 15 | [Tuning: threads, memória, partições e Spark UI](aulas/aula-15.md) | 14 | 4 |
| 16 | [Qualidade, testes, CI e boas práticas de GitHub](aulas/aula-16.md) | 01, 02, 03, 04, 05, 06, 07, 08, 09, 10, 11, 12, 13, 14, 15 | 5 |

Apêndices A–G: [página de apêndices](apendices.md). Diagnóstico e plano técnico da plataforma: [documento](https://claude.ai/code/artifact/68629f60-3f2f-40f2-a390-85d81360ea9e).
