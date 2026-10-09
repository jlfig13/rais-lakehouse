# RAIS Lakehouse — Plataforma de aprendizagem

Curso prático de PySpark, Delta Lake e MinIO construindo um lakehouse com os microdados da RAIS (bronze → silver → gold), tudo open source e local.

## Como estudar

1. Abra a aula na trilha abaixo e estude o conteúdo na própria página.
2. Faça o tutorial e o laboratório no [Ambiente](ambiente.md) (JupyterLab e MinIO integrados), no terminal ou no VS Code.
3. Marque os critérios de conclusão na página da aula: eles ficam gravados em `progress/estudo.json`.
4. Rode os checks da aula. Só avance quando passarem; o resultado aparece na trilha.

> Os checks verificam o **seu** ambiente. Este site não executa código e não mostra resultados que você não produziu.

## Trilha

<div id="rl-resumo"></div>

| Aula | Título | Depende de | Checks | Progresso |
| --- | --- | --- | --- | --- |
| 01 | [Arquitetura Lakehouse e o projeto RAIS Lakehouse](aulas/aula-01.md) | — | 1 | <span class="rl-trilha" data-aula="1" data-criterios="7">—</span> |
| 02 | [Docker: imagens, containers e o Dockerfile do Spark](aulas/aula-02.md) | 01 | 5 | <span class="rl-trilha" data-aula="2" data-criterios="5">—</span> |
| 03 | [Docker Compose: serviços, rede, volumes e configuração](aulas/aula-03.md) | 02 | 4 | <span class="rl-trilha" data-aula="3" data-criterios="5">—</span> |
| 04 | [MinIO e S3: buckets, S3A e menor privilégio](aulas/aula-04.md) | 03 | 4 | <span class="rl-trilha" data-aula="4" data-criterios="4">—</span> |
| 05 | [Repositório, Git e configuração por ambiente](aulas/aula-05.md) | 01, 03 | 5 | <span class="rl-trilha" data-aula="5" data-criterios="3">—</span> |
| 06 | [Ambiente no ar: SparkSession, Delta, S3A e teste de fumaça](aulas/aula-06.md) | 03, 04, 05 | 4 | <span class="rl-trilha" data-aula="6" data-criterios="4">—</span> |
| 07 | [PySpark I: DataFrames, transformações, agregações e SQL](aulas/aula-07.md) | 06 | 4 | <span class="rl-trilha" data-aula="7" data-criterios="3">—</span> |
| 08 | [PySpark II: joins, window functions, lazy evaluation e partições](aulas/aula-08.md) | 07 | 4 | <span class="rl-trilha" data-aula="8" data-criterios="3">—</span> |
| 09 | [O domínio RAIS: microdados, dicionário e armadilhas](aulas/aula-09.md) | 05 | 3 | <span class="rl-trilha" data-aula="9" data-criterios="3">—</span> |
| 10 | [Delta Lake e código base: transações, utilitários e dimensões](aulas/aula-10.md) | 06, 08 | 4 | <span class="rl-trilha" data-aula="10" data-criterios="3">—</span> |
| 11 | [Ingestão e camada bronze](aulas/aula-11.md) | 09, 10 | 5 | <span class="rl-trilha" data-aula="11" data-criterios="3">—</span> |
| 12 | [Camada silver: tipagem, validação e campos derivados](aulas/aula-12.md) | 11 | 5 | <span class="rl-trilha" data-aula="12" data-criterios="3">—</span> |
| 13 | [Camada gold: perguntas de negócio e funções puras](aulas/aula-13.md) | 12 | 5 | <span class="rl-trilha" data-aula="13" data-criterios="3">—</span> |
| 14 | [Pipeline completo, idempotência e operações Delta](aulas/aula-14.md) | 13 | 5 | <span class="rl-trilha" data-aula="14" data-criterios="4">—</span> |
| 15 | [Tuning: threads, memória, partições e Spark UI](aulas/aula-15.md) | 14 | 4 | <span class="rl-trilha" data-aula="15" data-criterios="3">—</span> |
| 16 | [Qualidade, testes, CI e boas práticas de GitHub](aulas/aula-16.md) | 01, 02, 03, 04, 05, 06, 07, 08, 09, 10, 11, 12, 13, 14, 15 | 5 | <span class="rl-trilha" data-aula="16" data-criterios="4">—</span> |

Apêndices A–G: [página de apêndices](apendices.md). Diagnóstico e plano técnico da plataforma: [documento](https://claude.ai/code/artifact/68629f60-3f2f-40f2-a390-85d81360ea9e).
