# Aula 07 — PySpark I: DataFrames, transformações, agregações e SQL

Oct 9, 2026

Ao final desta aula você escreve as transformações básicas do PySpark — selecionar, filtrar, criar colunas, converter tipos, agregar e usar SQL — sobre dados pequenos em memória, antes de tocar na RAIS.

```yaml
aula: 7
titulo: "PySpark I: DataFrames, transformações, agregações e SQL"
origem: ["Guia Parte 5.1", "Guia Parte 5.2", "Guia Parte 5.3", "Guia Parte 5.4", "Guia Parte 5.9"]
depende_de: [6]
entrega: ["labs/__init__.py", "labs/aula07.py", "notebooks/01_fundamentos.ipynb"]
checks: [a07_media_por_sexo, a07_admissoes_por_ano, a07_faixa_salarial, a07_sql_igual_dataframe]
```


## 1. Objetivos e pré-requisitos

1. Criar e inspecionar DataFrames (`show`, `printSchema`, `count`, `columns`).
2. Usar `select`, `filter`, `withColumn`, `when/otherwise`, `cast`, `withColumnRenamed`, `drop`, `orderBy`.
3. Agregar com `groupBy().agg()` e nomear resultados com `alias`.
4. Escrever a mesma consulta em DataFrame e em SQL.
5. Transformar exercícios em funções testáveis em `labs/aula07.py`.

**Pré-requisitos:** Aula 06 (`get_spark` funcionando), Python básico, SQL básico.

## 2. Contextualização

A RAIS tem dezenas de milhões de linhas por ano (Aula 09); aprender PySpark direto nela torna cada erro lento e caro. O guia começa com seis linhas em memória (Parte 5) justamente para isso: os mesmos comandos funcionam com 6 ou 60 milhões de linhas, e erros aparecem em segundos.

**por que Spark e não pandas?**

| Critério | pandas | PySpark |
| --- | --- | --- |
| Onde os dados ficam | Todos na memória de um processo | Divididos em partições, processadas em paralelo |
| Volume confortável | Cabe na RAM | Maior que a RAM (com spill em disco) |
| Execução | Imediata (cada linha roda na hora) | Preguiçosa: monta um plano e otimiza (Aula 08) |
| Mutabilidade | DataFrame mutável | DataFrame imutável |
| Uso no curso | Gráficos sobre a gold (Aula 13) | Todo o processamento |

## 3. Fundamentação teórica

### 3.1 SparkSession (guia, Parte 5.1)

O PySpark é a API Python do Apache Spark, que roda na JVM. A `SparkSession` é o ponto de entrada; só existe uma por processo. No curso, ela vem do `get_spark()` (Aula 06); nos exemplos do guia, de `SparkSession.builder.master("local[2]")...` — as duas formas funcionam para os dados pequenos desta aula.

**Convenção de imports (guia):** `from pyspark.sql import functions as F`. Evite `from pyspark.sql.functions import *`, que sobrescreve funções nativas como `sum`, `max` e `round`.

### 3.2 DataFrame (guia, Parte 5.2)

Uma tabela **distribuída** (dividida em partições) e **imutável** (cada operação gera um DataFrame novo). Por isso se escreve `df = df.withColumn(...)`: sem a reatribuição, a coluna nova se perde.

**Schema** é a lista de colunas com seus tipos. Tipos comuns: `string`, `int`, `bigint` (o `long` do Python), `double`, `decimal(p,s)`, `boolean`, `date`. Na RAIS, o tipo de cada coluna é uma decisão de projeto (Aula 12).

### 3.3 Expressões de coluna

`F.col("salario")` representa uma coluna; operações sobre ela (`* 13`, `> 3500`, `.cast("string")`) geram novas expressões, que só são calculadas quando uma ação roda. Em condições combinadas use `&` (E), `|` (OU), `~` (NÃO) e **parênteses em cada comparação** (guia, Parte 5.3); `and`/`or` do Python não funcionam com colunas.

### 3.4 NULL em comparações

Em Spark (como em SQL), qualquer comparação com `NULL` resulta em `NULL`, e `filter` descarta linhas cujo resultado não é verdadeiro. `F.col("x") != "a"` **não** devolve as linhas com `x` nulo. Use `isNull()`/`isNotNull()` explicitamente. Isso importa na silver, onde valores inválidos viram `NULL` (Aula 12).

### 3.5 Agregações (guia, Parte 5.4)

`groupBy(colunas).agg(funções)` agrupa e resume. Sempre dê nome com `.alias()`; sem isso o nome vira algo como `avg(salario)`, ruim de usar depois. `F.percentile_approx(col, 0.5)` dá a mediana aproximada — aproximada porque a exata exigiria ordenar todos os dados, o que é caro em volume grande.

### 3.6 SQL (guia, Parte 5.9)

`createOrReplaceTempView("nome")` registra o DataFrame como tabela temporária da sessão; `spark.sql(...)` consulta. A API de DataFrame e o SQL geram **o mesmo plano**: use o que deixar o código mais legível.

## 4. Arquitetura e fluxo

```
 dados Python (lista de tuplas)
        │  spark.createDataFrame(dados, colunas)
        ▼
 DataFrame (imutável, em partições)
        │  select / filter / withColumn / groupBy ...   ← transformações: só montam o plano
        ▼
 DataFrame derivado
        │  show / count / collect / write             ← ações: executam
        ▼
 resultado na tela, no driver ou no lake
```

A diferença entre transformação e ação é o tema central da Aula 08.

## 5. Tutorial

Abra o JupyterLab (`localhost:8888`) e crie `notebooks/01_fundamentos.ipynb`.

### Passo 1 — Sessão e dados (guia, Partes 5.1–5.2)

```python
from pyspark.sql import functions as F

from src.utils import get_spark

spark = get_spark("estudo")

dados = [
    (1, "Ana",    "F", "PE", 3200.50, "2021-03-01"),
    (2, "Bruno",  "M", "PE", 4100.00, "2020-07-15"),
    (3, "Carla",  "F", "SP", 5800.00, "2019-01-10"),
    (4, "Diego",  "M", "SP", 2900.00, "2022-11-05"),
    (5, "Elisa",  "F", "BA", 3500.00, "2021-09-20"),
    (6, "Felipe", "M", "BA", 3900.00, "2018-02-14"),
]
df = spark.createDataFrame(dados, ["id", "nome", "sexo", "uf", "salario", "admissao"])

df.show()          # mostra as primeiras linhas
df.printSchema()   # nomes e tipos
df.count()         # número de linhas (ação)
df.columns         # lista de colunas (não executa nada)
```

**Esperado em `printSchema`:** `id: long`, `salario: double` e as demais `string` — o Spark infere tipos dos valores Python, e `admissao` ainda é texto.

### Passo 2 — Transformações básicas (guia, Parte 5.3)

```python
df.select("nome", "salario")
df.select(F.col("nome"), (F.col("salario") * 2).alias("dobro"))

df.filter(F.col("salario") > 3500)
df.filter((F.col("uf") == "PE") & (F.col("salario") > 3000))

df = df.withColumn("salario_anual", F.col("salario") * 13)

df = df.withColumn(
    "faixa",
    F.when(F.col("salario") < 3000, "baixa")
     .when(F.col("salario") < 4500, "media")
     .otherwise("alta"),
)

df = df.withColumn("admissao", F.to_date("admissao"))     # texto -> date
df = df.withColumn("id", F.col("id").cast("string"))

df = df.withColumnRenamed("nome", "nome_completo").drop("salario_anual")
df.orderBy(F.col("salario").desc())
```

- `when` é avaliado em ordem: a primeira condição verdadeira vence; `otherwise` cobre o resto. Sem `otherwise`, o resto vira `NULL`.
- `F.to_date("admissao")` sem formato espera `aaaa-mm-dd`; um texto fora do padrão vira `NULL`.

### Passo 3 — Agregações (guia, Parte 5.4)

```python
(df.groupBy("uf")
   .agg(
       F.count("*").alias("qtd"),
       F.round(F.avg("salario"), 2).alias("salario_medio"),
       F.sum("salario").alias("massa_salarial"),
       F.percentile_approx("salario", 0.5).alias("mediana"),
   )
   .orderBy("uf")
   .show())
```

### Passo 4 — SQL (guia, Parte 5.9)

```python
df.createOrReplaceTempView("pessoas")
spark.sql("SELECT uf, AVG(salario) AS media FROM pessoas GROUP BY uf").show()
```

### Passo 5 — Exercícios como funções testáveis

Crie `labs/__init__.py` vazio e `labs/aula07.py` com as assinaturas abaixo; implemente o corpo de cada função.

```python
"""Exercícios da Aula 07 (PySpark I). Cada função recebe e devolve DataFrame."""
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

DADOS = [
    (1, "Ana", "F", "PE", 3200.50, "2021-03-01"),
    (2, "Bruno", "M", "PE", 4100.00, "2020-07-15"),
    (3, "Carla", "F", "SP", 5800.00, "2019-01-10"),
    (4, "Diego", "M", "SP", 2900.00, "2022-11-05"),
    (5, "Elisa", "F", "BA", 3500.00, "2021-09-20"),
    (6, "Felipe", "M", "BA", 3900.00, "2018-02-14"),
]


def exemplo(spark: SparkSession) -> DataFrame:
    return spark.createDataFrame(DADOS, ["id", "nome", "sexo", "uf", "salario", "admissao"])


def media_por_sexo(df: DataFrame) -> DataFrame:
    """Colunas: sexo, media (média salarial arredondada a 2 casas)."""
    ..


def admissoes_por_ano(df: DataFrame) -> DataFrame:
    """Colunas: ano_admissao, qtd — ordenado por ano."""
    ..


def faixa_salarial(df: DataFrame) -> DataFrame:
    """Acrescenta a coluna faixa: baixa (< 3000), media (< 4500), alta (resto)."""
    ..
```

Respostas na seção 12.

## 6. Funcionamento e resultados esperados

| Operação | Resultado esperado com os dados do guia |
| --- | --- |
| `df.count()` | 6 |
| `filter(salario > 3500)` | Bruno, Carla e Felipe (Elisa ganha exatamente 3500 e fica de fora) |
| `faixa` | baixa: Diego; alta: Carla; media: os outros quatro |
| média por sexo | F ≈ 4166,83; M ≈ 3633,33 |
| admissões por ano | 2021 → 2; 2018, 2019, 2020, 2022 → 1 cada |

Valores calculados a partir dos dados do guia; confirme na sua execução.

## 7. Exemplos práticos

**Exemplo 1 — Da RAIS ao exercício.** O exercício "média salarial por sexo" é a semente da tabela `gold_gap_sexo_uf_ano` (Aula 13), que usa `F.avg(F.when(F.col("sexo") == 2, F.col("remun_dezembro_sm")))` — um `when` dentro de um `avg` para calcular a média só de um grupo.

**Exemplo 2 — Faixas.** A faixa salarial é o mesmo padrão de `gold_faixa_etaria_ano` (exercício da Aula 13).

**Exemplo 3 — SQL e DataFrame lado a lado.**

```python
a = df.groupBy("uf").agg(F.avg("salario").alias("media"))
b = spark.sql("SELECT uf, AVG(salario) AS media FROM pessoas GROUP BY uf")
print(sorted(a.collect()) == sorted(b.collect()))   # True: mesmo resultado
```

`collect()` traz tudo para o driver — aceitável aqui, com 3 linhas; proibido em tabelas grandes (Aula 08).

## 8. Armadilhas, diagnóstico e soluções

| Sintoma | Causa | Solução |
| --- | --- | --- |
| `TypeError: Column is not iterable` ou `sum` estranho | `from pyspark.sql.functions import *` sobrescreveu funções nativas | `from pyspark.sql import functions as F` |
| `ValueError: Cannot convert column into bool` | `and`/`or` ou falta de parênteses na condição | `(a > 1) & (b < 2)` |
| Coluna nova sumiu | Faltou reatribuir (`df = df.withColumn(...)`) | DataFrames são imutáveis |
| `AnalysisException: ... cannot be resolved` | Nome de coluna errado ou já renomeada | Conferir `df.columns` |
| Agregado com nome `avg(salario)` | Faltou `alias` | Sempre `.alias()` |
| Linhas com NULL sumiram do filtro | Comparação com NULL | `isNull()` explícito |
| Data virou NULL | Texto fora do formato esperado por `to_date` | Passar o formato: `F.to_date("col", "dd/MM/yyyy")` |

## 9. Boas práticas

1. `functions as F` sempre (guia).
2. Nomear toda agregação com `alias` (guia).
3. Escolher entre DataFrame e SQL pela legibilidade; o plano é o mesmo (guia).
4. Funções que recebem e devolvem DataFrame ("funções puras") em vez de código solto: são testáveis, e é o padrão da gold (Aula 13).
5. Testar com dados pequenos antes de rodar no volume real.

## 10. Riscos

| Tipo | Risco | Mitigação |
| --- | --- | --- |
| Desempenho | `collect()`/`toPandas()` em dado grande estoura o driver | Usar só em resultados pequenos (gold) |
| Integridade | Filtros perdendo NULLs silenciosamente | Tratar NULL de forma explícita |
| Integridade | `double` para dinheiro acumula erro de arredondamento | `decimal` na silver (Aula 10) |

## 11. Laboratório e validação na plataforma

**Contribuição ao projeto:** as operações desta aula são as mesmas da silver e da gold; o padrão de funções testáveis é o da Aula 13.

`labcheck/test_aula07.py` (container):

```python
"""Checks da Aula 07: exercícios de labs/aula07.py."""
from pyspark.sql import functions as F

from labs import aula07


def test_a07_media_por_sexo(spark):
    r = {row["sexo"]: float(row["media"]) for row in aula07.media_por_sexo(aula07.exemplo(spark)).collect()}
    assert r == {"F": 4166.83, "M": 3633.33}, f"Obtido: {r}"


def test_a07_admissoes_por_ano(spark):
    r = [(row["ano_admissao"], row["qtd"]) for row in aula07.admissoes_por_ano(aula07.exemplo(spark)).collect()]
    assert r == [(2018, 1), (2019, 1), (2020, 1), (2021, 2), (2022, 1)], f"Obtido: {r}"


def test_a07_faixa_salarial(spark):
    r = {row["nome"]: row["faixa"] for row in aula07.faixa_salarial(aula07.exemplo(spark)).collect()}
    assert r["Diego"] == "baixa" and r["Carla"] == "alta" and r["Ana"] == "media", f"Obtido: {r}"


def test_a07_sql_igual_dataframe(spark):
    df = aula07.exemplo(spark)
    df.createOrReplaceTempView("pessoas_a07")
    via_sql = spark.sql("SELECT sexo, ROUND(AVG(salario), 2) AS media FROM pessoas_a07 GROUP BY sexo")
    via_df = aula07.media_por_sexo(df)
    assert sorted(via_sql.collect()) == sorted(via_df.select("sexo", "media").collect())
```

```bash
make check AULA=07
```

**Checklist manual:** \[ \] executei os passos 1–4 no notebook · \[ \] sei explicar por que `df.withColumn` precisa de reatribuição · \[ \] sei por que Elisa não aparece em `salario > 3500`.

## 12. Exercícios, revisão e desafios

**Exercícios (guia, Parte 5, exercícios 1 e 3)** — implemente em `labs/aula07.py`.

**Respostas** (tente antes de ler):

```python
def media_por_sexo(df):
    return df.groupBy("sexo").agg(F.round(F.avg("salario"), 2).alias("media"))


def admissoes_por_ano(df):
    return (df.withColumn("ano_admissao", F.year(F.to_date("admissao")))
              .groupBy("ano_admissao").agg(F.count("*").alias("qtd"))
              .orderBy("ano_admissao"))


def faixa_salarial(df):
    return df.withColumn(
        "faixa",
        F.when(F.col("salario") < 3000, "baixa").when(F.col("salario") < 4500, "media").otherwise("alta"),
    )
```

**Revisão**

1. Por que `from pyspark.sql.functions import *` é desaconselhado?
2. O que acontece com uma linha cujo `salario` é NULL em `filter(F.col("salario") > 3500)`?
3. Por que `percentile_approx` e não mediana exata?
4. DataFrame ou SQL: qual é mais rápido?

**Respostas sugeridas:** (1) sobrescreve `sum`, `max`, `round` do Python; (2) a comparação dá NULL e a linha é descartada; (3) a exata exige ordenar tudo, cara em volume grande; (4) nenhum: geram o mesmo plano.

**Desafios**

1. Escreva `top_salario_por_uf` usando só `groupBy` e `join` (sem window). Na Aula 08 você refaz com window e compara.
2. Recrie os dados com schema explícito em texto (`"id int, nome string, ..."`), com `salario` como `decimal(10,2)`, e compare o `printSchema`.

## 13. Referências cruzadas

| Tema | Onde |
| --- | --- |
| `get_spark` | Aula 06 |
| Joins, windows, lazy evaluation, partições, Parquet | Aula 08 |
| `try_cast`, `decimal` e conversões da RAIS | Aulas 10 e 12 |
| Funções puras na gold | Aula 13 |
| Termos: DataFrame, schema, ação, transformação | Apêndice C |
