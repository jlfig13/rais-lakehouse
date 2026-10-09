# Apêndices A–G — RAIS Lakehouse

Oct 9, 2026

Material de consulta do curso: armadilhas, solução de problemas, glossário, comandos, checklists, versões e próximos passos. Os apêndices A a C e G vêm dos apêndices do guia, ampliados com o conteúdo das aulas; D, E e F consolidam o que está espalhado pelas 16 aulas.

## Apêndice A — Armadilhas da RAIS (guia, Apêndice A)

| # | Armadilha | Consequência | Como o projeto trata | Aula |
| --- | --- | --- | --- | --- |
| 1 | O schema muda entre anos | Carga quebra ou coluna some | Bronze toda string com `mergeSchema`; `col_or_null`; `OBRIGATORIAS` | 10, 11, 12 |
| 2 | eSocial a partir do ano-base 2019 | Cobertura muda entre anos; séries podem saltar | Ler as notas técnicas de cada ano | 09 |
| 3 | Versão parcial × final | Total de um ano abaixo do real | Usar a final e registrar (data, hash) | 09 |
| 4 | Arquivo "NI" (não identificados) | UF nula na gold | Incluir para total nacional; decidir e documentar | 09, 13 |
| 5 | "Ignorado" varia por coluna (`-1`, `0`, `{ñ class}`) | Lixo tratado como valor | Decisão coluna a coluna no dicionário; `try_cast` | 09, 12 |
| 6 | Zeros à esquerda (CBO, CNAE, município) | Joins falham, códigos corrompidos | Sempre string | 09, 12 |
| 7 | Nominal × salário mínimo | Crescimento salarial ilusório | Séries históricas com `*_sm` | 09, 13 |
| 8 | Vínculo ≠ pessoa | Conclusões sobre "trabalhadores" erradas | Grão no contrato; rótulos "vínculos" | 01, 09, 13 |
| 9 | Disco | `.txt` enche o disco | `--limpar-raw` após a bronze | 11, 14 |
| 10 | Encoding | `Munic�pio` | `ISO-8859-1` na leitura | 11 |

## Apêndice B — Solução de problemas

Organizado pela ordem em que o erro costuma aparecer. As linhas sem marcação vêm do Apêndice B do guia.

### B.1 Docker e build

| Sintoma | Causa provável | Solução | Aula |
| --- | --- | --- | --- |
| `Cannot connect to the Docker daemon` | Docker Desktop fechado / serviço parado | Abrir / iniciar | 02 |
| `Unable to locate package openjdk-17-jre-headless` | Imagem base sem `-bookworm` | Voltar a `python:3.11-slim-bookworm` | 02 |
| `ClassNotFoundException: S3AFileSystem` | JAR não baixou no build | `docker compose build --no-cache spark` | 02, 06 |
| `Permission denied` em `/app` ou `/staging` | UID diferente entre host e container | Ajustar `HOST_UID` (`id -u`) e reconstruir | 02, 03 |

### B.2 Compose e serviços

| Sintoma | Causa provável | Solução | Aula |
| --- | --- | --- | --- |
| `required variable ... is missing a value` | `.env` ausente ou incompleto | Copiar de `.env.example` | 03 |
| `minio-init` termina com erro | Credenciais ou sintaxe do `mc` | `docker compose logs minio-init`; ajustar à versão do `mc` | 03, 04 |
| `spark` não sobe | `minio-init` falhou (dependência) | Resolver o `minio-init` primeiro | 03 |
| `port is already allocated` | Outro processo na porta | Parar o processo ou mudar a porta do host | 03 |
| `make: *** missing separator` | Espaços no lugar de TAB no Makefile | Usar TAB | 03 |
| Container morre com código 137 | `mem_limit` estourado | Reduzir `SPARK_MEM` ou aumentar `CONTAINER_MEM` | 03, 15 |

### B.3 MinIO e S3A

| Sintoma | Causa provável | Solução | Aula |
| --- | --- | --- | --- |
| `Connection refused` ao acessar o MinIO | `localhost` dentro do container | `http://minio:9000` | 03, 04 |
| `403` / `InvalidAccessKeyId` | Usuário da aplicação não criado ou sem política | Log do `minio-init`; conferir `APP_ACCESS_KEY` | 04 |
| `UnknownHostException: rais.minio` | Faltou path-style | `fs.s3a.path.style.access=true` | 04, 06 |
| Acesso negado só em alguns caminhos | Bucket diferente no `.env` e no JSON | Alinhar `RAIS_BUCKET` e `policy-rais.json` | 04 |

### B.4 Spark, Delta e pipeline

| Sintoma | Causa provável | Solução | Aula |
| --- | --- | --- | --- |
| `OutOfMemoryError` | Heap da JVM pequeno | Menos threads ou mais `SPARK_MEM` | 15 |
| Spark UI não abre | Sem sessão ativa ou porta errada | A UI só existe com sessão; tentar 4041 | 06, 15 |
| Mudou `SPARK_MEM` e nada mudou | Sessão já existia | Reiniciar kernel/processo | 06 |
| `ValueError: Colunas duplicadas após normalizar` | Cabeçalhos que colidem | Tratar antes de normalizar | 10, 11 |
| Erro de schema ao gravar | Enforcement do Delta | Corrigir dado ou `mergeSchema` só na bronze | 10 |
| Erro de `replaceWhere` | Linhas fora do ano | Filtrar o DataFrame pelo ano | 10 |
| Contagem silver ≠ bronze | `filter` na silver | Anular em vez de filtrar | 12 |
| UF nula na gold | Arquivo NI ou município inválido | `left_anti` com `dim_uf`; decidir e documentar | 08, 13 |
| Time travel falha para versão antiga | `VACUUM` já removeu os arquivos | Esperado; reter mais tempo | 14 |

### B.5 Git e CI

| Sintoma | Causa provável | Solução | Aula |
| --- | --- | --- | --- |
| `.env` no `git status` | `.gitignore` ausente/errado | `git check-ignore -v .env` | 05 |
| `.env` commitado | — | Remover do índice **e trocar as senhas** | 05, 16 |
| CI sem Java | Falta `setup-java` | Ver `ci.yml` | 16 |
| CI com `ModuleNotFoundError: src` | Falta `pythonpath` | `pyproject.toml` | 16 |

## Apêndice C — Glossário

Termos do Apêndice C do guia, mais os introduzidos nas aulas.

| Termo | Definição | Aula |
| --- | --- | --- |
| ACID | Atomicidade, consistência, isolamento e durabilidade: a transação acontece inteira ou não acontece | 01, 10 |
| ADR | Architecture Decision Record: registro curto de uma decisão, com contexto, alternativas e consequências | 01 |
| AQE | Adaptive Query Execution: o Spark reotimiza o plano durante a execução | 15 |
| Ação | Operação que dispara a execução (`show`, `count`, `write`) | 07, 08 |
| Bind mount | Pasta do host montada no container | 02, 03 |
| Broadcast join | Join em que a tabela pequena é copiada para todas as tarefas, sem shuffle | 08 |
| Bucket | Contêiner de objetos num object storage | 04 |
| cgroups | Recurso do kernel Linux que limita CPU e memória de um processo | 02, 15 |
| Chave / prefixo | Nome completo de um objeto S3 / início comum entre chaves (as "pastas") | 04 |
| Contrato de camada | O que o consumidor de uma camada pode assumir: grão, tipos, garantias | 01 |
| Data skew | Dados concentrados em poucas chaves, gerando tarefas desbalanceadas | 15 |
| Fixture | Recurso preparado pelo pytest e injetado nos testes (ex.: `spark`, `tmp_path`) | 10, 16 |
| Função pura | Recebe e devolve DataFrames sem ler nem gravar nada; testável sem lake | 13 |
| Grão | O que uma linha representa (na RAIS, um vínculo) | 01, 09 |
| Idempotência | Executar várias vezes produz o mesmo resultado | 01, 14 |
| Imagem / container | Pacote imutável / instância em execução de uma imagem | 02 |
| Init container | Serviço que prepara algo e termina (`minio-init`) | 03 |
| Lazy evaluation | Transformações só executam quando há uma ação | 08 |
| Medallion | Organização em bronze, silver e gold | 01 |
| `mergeSchema` / `overwriteSchema` | Acrescentar colunas novas / substituir o schema inteiro na escrita Delta | 10 |
| `OPTIMIZE` / `VACUUM` | Compactar arquivos pequenos / remover arquivos sem referência | 14 |
| Partition pruning | Ler só as partições exigidas pelo filtro | 08 |
| Path-style | Endereço S3 no formato `host/bucket/chave`, exigido pelo MinIO | 04 |
| `replaceWhere` | Sobrescrita atômica só dos dados que satisfazem uma condição | 10 |
| S3A | Conector Hadoop/Spark para storage compatível com S3 | 04 |
| Schema enforcement / evolution | Recusar ou aceitar mudanças de schema na escrita | 10, 14 |
| Shuffle | Redistribuição de dados entre partições; a operação mais cara do Spark | 08 |
| SM | Salário mínimo; unidade de remuneração comparável entre anos | 09 |
| Spill | Dados despejados em disco quando não cabem na memória | 15 |
| Time travel | Ler uma versão antiga de uma tabela Delta | 14 |
| `try_cast` | Conversão que devolve NULL em vez de erro | 10 |
| Vínculo | Relação de emprego registrada; a unidade de uma linha na RAIS | 09 |
| Window function | Cálculo por linha olhando um grupo, sem reduzir linhas | 08 |

## Apêndice D — Referência de comandos

### D.1 Docker e Compose (guia, Parte 2.4)

```bash
docker compose up -d --build      # constrói (se preciso) e sobe tudo em segundo plano
docker compose ps -a              # estado dos containers, inclusive os que terminaram
docker compose logs -f spark      # acompanha o log de um serviço
docker compose exec spark bash    # terminal dentro do container
docker compose run --rm minio-init  # reexecuta o init num container novo
docker compose stop               # para (mantém tudo)
docker compose down               # remove containers e rede (volumes ficam)
docker compose down -v            # ⚠️ remove também os VOLUMES (apaga o lake!)
docker compose config -q          # valida o YAML e as variáveis sem imprimir segredos
docker stats --no-stream          # CPU e memória por container
docker history rais-spark:local   # camadas da imagem
```

### D.2 Makefile do projeto (Aula 03)

| Alvo | Faz |
| --- | --- |
| `make up` / `down` / `ps` / `logs` / `shell` | Ciclo de vida do ambiente |
| `make smoke` | Teste de fumaça (Aula 06) |
| `make pipeline ANOS="2021 2022" ETAPAS="silver gold"` | Pipeline (Aula 14) |
| `make test` / `lint` / `fmt` | Testes, análise e formatação (Aula 16) |
| `make check AULA=NN ANO=2022` | Checks de uma aula no container |
| `make check-host AULA=NN` | Checks das aulas de infraestrutura no host |
| `make progresso` | Gera a página de progresso |

### D.3 Cliente `mc` (Aula 04)

```sh
mc alias set app http://minio:9000 "$APP_ACCESS_KEY" "$APP_SECRET_KEY"
mc ls app/rais                       # lista
mc ls --recursive app/rais/_smoke    # lista tudo abaixo do prefixo
mc du app/rais/silver                # tamanho de uma camada
mc admin policy --help               # sintaxe da sua versão
```

### D.4 Spark e Delta (Aulas 06–14)

```python
from delta.tables import DeltaTable

spark.read.format("delta").load(caminho)                                   # ler
spark.read.format("delta").option("versionAsOf", 0).load(caminho)          # time travel
dt = DeltaTable.forPath(spark, caminho)
dt.history().select("version", "operation").show()                       # histórico
dt.optimize().executeCompaction()                                         # compactar
dt.vacuum(168)                                                            # limpar (≥ 168 h)
df.explain()                                                              # plano
spark.conf.get("spark.sql.shuffle.partitions")                            # configuração efetiva
```

### D.5 Git (Aulas 05 e 16)

```bash
git status && git check-ignore -v .env
git switch -c feat/minha-funcionalidade
git commit -m "feat(gold): nova tabela"
git push -u origin feat/minha-funcionalidade
git tag v1.0.0 && git push --tags
```

## Apêndice E — Checklists operacionais

### E.1 Checklist final do guia

- [ ] Repositório criado, `.gitignore` e `.env.example` versionados, `.env` fora do Git
- [ ] `make up` sobe minio, minio-init (exit 0) e spark
- [ ] `make smoke` passa
- [ ] Fundamentos de PySpark concluídos
- [ ] Dicionário baixado e `docs/dicionario.md` preenchido
- [ ] Bronze, silver e gold gravadas em Delta no MinIO
- [ ] Contagem silver = bronze e checagens passando
- [ ] Reprocessar um ano não duplica dados
- [ ] Time travel, `OPTIMIZE` e schema enforcement testados
- [ ] Benchmark feito e configuração padrão registrada em `docs/decisoes.md`
- [ ] Testes, lint e CI verdes
- [ ] README com arquitetura, decisões, resultados e limitações

### E.2 Validação por aula na plataforma

| Aulas | Comando | Onde roda |
| --- | --- | --- |
| 01 | `make check AULA=01` | Container |
| 02, 03, 04, 05 | `make check-host AULA=NN` | Host (WSL/Linux) |
| 06–16 | `make check AULA=NN ANO=2022` | Container |
| Todas | `make progresso` | Container |

### E.3 Antes de rodar o pipeline

- [ ] `make ps`: minio e spark `running`, minio-init `exited (0)`
- [ ] `.7z` de cada ano em `staging/landing/<ano>/`, versão final, hash registrado
- [ ] Espaço em disco para o maior ano extraído + o volume do MinIO
- [ ] `ANOS` em `config/settings.py` coerente com os arquivos
- [ ] Configuração de recursos do ADR de tuning no `.env`

### E.4 Depois de rodar

- [ ] Nenhum `AssertionError` de `checar_silver`
- [ ] Totais por ano na gold coerentes entre si (saltos explicados por notas técnicas)
- [ ] `staging/raw/` vazia
- [ ] `make check` das Aulas 11–14 passando

### E.5 Manutenção periódica

- [ ] `OPTIMIZE` nas tabelas silver após várias cargas
- [ ] `VACUUM(168)` depois, respeitando a janela de time travel
- [ ] Backup da landing e do volume do MinIO
- [ ] Reconstruir a imagem para atualizações de segurança da base, mantendo as versões fixas
- [ ] Atualizar uma dependência por vez, com o CI verde

## Apêndice F — Versões e configurações

### F.1 Versões (guia, Parte 4.2)

| Componente | Versão | Observação |
| --- | --- | --- |
| Python | 3.11 | Imagem `python:3.11-slim-bookworm` |
| Java | 17 | `openjdk-17-jre-headless` |
| PySpark | 3.5.3 | Sem ANSI por padrão |
| delta-spark | 3.2.0 | Confirme a matriz de compatibilidade |
| hadoop-aws | 3.3.4 | Igual ao Hadoop do PySpark 3.5 |
| aws-java-sdk-bundle | 1.12.262 | Dependência do hadoop-aws 3.3.4 |
| py7zr | 0.22.0 |  |
| jupyterlab / pytest / ruff / pandas / matplotlib | 4.2.5 / 8.3.3 / 0.6.9 / 2.2.3 / 3.9.2 | Se não instalar, use a mais recente da mesma linha |
| MinIO e `mc` | A definir | Tag fixa no `.env`; confirme a distribuição atual |

### F.2 Variáveis de ambiente

| Variável | Lida por | Função |
| --- | --- | --- |
| `MINIO_IMAGE`, `MC_IMAGE` | Compose | Imagens do MinIO e do `mc` |
| `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD` | `minio`, `minio-init` | Administrador |
| `APP_ACCESS_KEY`, `APP_SECRET_KEY` | `minio-init`; chegam ao `spark` como `S3_*` | Usuário da aplicação |
| `RAIS_BUCKET` | Compose | Nome do bucket (deve casar com `policy-rais.json`) |
| `HOST_STAGING_DIR`, `HOST_UID` | Compose / build | Pasta de staging e UID do usuário `app` |
| `CONTAINER_CPUS`, `CONTAINER_MEM` | Compose | Limites do container `spark` |
| `SPARK_THREADS`, `SPARK_MEM`, `SPARK_SHUFFLE` | `get_spark` | Recursos do Spark |
| `JUPYTER_TOKEN` | Compose | Acesso ao JupyterLab |
| `MINIO_ENDPOINT`, `RAIS_LAKE`, `RAIS_STAGING`, `SPARK_TMP` | `settings.py`, `get_spark` | Definidas no compose, não no `.env` |

### F.3 Configurações do `get_spark` (guia, Parte 7.3)

| Configuração | Valor | Muda em execução? |
| --- | --- | --- |
| `master` | `local[SPARK_THREADS]` | Não |
| `spark.driver.memory` | `SPARK_MEM` (padrão 4g) | Não |
| `spark.sql.shuffle.partitions` | `SPARK_SHUFFLE` (padrão 32) | Sim |
| `spark.sql.files.maxPartitionBytes` | 128m | Sim |
| `spark.sql.adaptive.enabled` / `coalescePartitions.enabled` | true | Sim |
| `spark.local.dir` | `SPARK_TMP` | Não |
| `spark.sql.session.timeZone` | America/Sao\_Paulo | Sim |
| `spark.sql.extensions` / `spark.sql.catalog.spark_catalog` | Delta | Não |
| `spark.hadoop.fs.s3a.*` | endpoint, chaves, path-style, SSL | Não (na prática, defina na criação) |

### F.4 Pontos de partida de recursos (guia, Parte 14.3)

| RAM do host / núcleos | `CONTAINER_MEM` | `CONTAINER_CPUS` | `SPARK_MEM` | `SPARK_THREADS` | `SPARK_SHUFFLE` |
| --- | --- | --- | --- | --- | --- |
| 8 GB / 4 | 5g | 3 | 3g | 2 | 16 |
| 16 GB / 8 | 11g | 6 | 8g | 4 | 32 |
| 32 GB / 8–12 | 24g | 8 | 18g | 6 | 48 |
| 64 GB / 16 | 48g | 14 | 36g | 12 | 96 |

## Apêndice G — Próximos passos

### G.1 Do guia (Apêndice D)

1. **RAIS Estabelecimentos:** some a segunda base e pratique joins grandes e skew.
2. **`MERGE` no Delta:** pratique *upserts* com uma tabela de correções.
3. **Iceberg:** recrie a gold em Iceberg com catálogo REST e compare a experiência.
4. **Consulta SQL:** suba o Trino no Compose para consultar o lake por SQL.
5. **Orquestração:** agende o pipeline com Airflow ou Dagster no mesmo Compose.
6. **Visualização:** suba Metabase ou Superset no Compose e conecte à gold.
7. **Cluster:** transforme o serviço `spark` em master + workers (Spark standalone) e observe o que muda no tuning.

### G.2 Da plataforma de estudo

1. Fazer a página de progresso mostrar o total **declarado** de checks por aula, lendo o front matter (desafio da Aula 06).
2. Criar a amostra sintética no formato da RAIS para testes de integração no CI (plano técnico, seção 2).
3. Acrescentar ao CI o build do site do curso, depois de confirmar o comando do Zensical.
4. Exportar cada documento de aula para `curso/docs/aulas/aula-NN.md`, mantendo o bloco de metadados como front matter.
