<!-- Página GERADA de docs/guia/rais-lakehouse-guia.md -->

# Parte [5](parte-05.md) — Fundamentos de PySpark

Abra o JupyterLab (http://localhost:8888) e crie `notebooks/01_fundamentos.ipynb`. Esta parte usa dados pequenos em memória, sem RAIS.

## 5.1 SparkSession — a porta de entrada { #parte-5-1 }

```python
from pyspark.sql import SparkSession, functions as F, Window

spark = SparkSession.builder.master("local[2]").appName("estudo").getOrCreate()
```
**Conceito:** o PySpark é a API Python do Apache Spark, que roda na JVM (por isso a imagem tem Java). A `SparkSession` é o ponto de entrada, e só existe uma por processo. Enquanto ela existir, o painel de execução fica em http://localhost:4040.

**Convenção de imports:** `from pyspark.sql import functions as F` é o padrão da comunidade. Evite `from pyspark.sql.functions import *`, que sobrescreve funções nativas do Python como `sum`, `max` e `round`.

## 5.2 DataFrame { #parte-5-2 }

Um DataFrame é uma tabela **distribuída** (dividida em partições) e **imutável** (cada operação gera um DataFrame novo).

```python
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
df.printSchema()   # mostra o schema (nomes e tipos)
df.count()         # conta as linhas
df.columns         # lista as colunas
```

## 5.3 Transformações básicas { #parte-5-3 }

```python
# Selecionar colunas
df.select("nome", "salario")
df.select(F.col("nome"), (F.col("salario") * 2).alias("dobro"))

# Filtrar linhas (filter e where são sinônimos)
df.filter(F.col("salario") > 3500)
df.filter((F.col("uf") == "PE") & (F.col("salario") > 3000))   # & = E, | = OU, ~ = NÃO

# Criar ou alterar coluna
df = df.withColumn("salario_anual", F.col("salario") * 13)

# Condicional (equivale ao CASE WHEN do SQL)
df = df.withColumn(
    "faixa",
    F.when(F.col("salario") < 3000, "baixa")
     .when(F.col("salario") < 4500, "media")
     .otherwise("alta"),
)

# Converter tipos
df = df.withColumn("admissao", F.to_date("admissao"))
df = df.withColumn("id", F.col("id").cast("string"))

# Renomear e remover
df = df.withColumnRenamed("nome", "nome_completo").drop("salario_anual")

# Ordenar
df.orderBy(F.col("salario").desc())
```
> Em condições combinadas, **use parênteses** em cada comparação: `(a > 1) & (b < 2)`. Sem eles, a precedência dos operadores do Python gera erro.

## 5.4 Agregações { #parte-5-4 }

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
**Boa prática:** sempre dê nome às colunas agregadas com `.alias()`. Sem isso, o nome vira algo como `avg(salario)`, que é ruim de usar depois.

## 5.5 Joins { #parte-5-5 }

```python
ufs = spark.createDataFrame(
    [("PE", "Pernambuco"), ("SP", "São Paulo"), ("BA", "Bahia")], ["uf", "nome_uf"]
)

df.join(ufs, on="uf", how="left")                    # left, inner, right, full, left_anti...
df.join(F.broadcast(ufs), on="uf", how="left")       # tabela pequena -> broadcast
```
**Conceito:** um join normal faz *shuffle* (redistribui as duas tabelas pela chave). Com `broadcast`, o Spark copia a tabela pequena inteira para todas as tarefas e evita o shuffle. Use em **dimensões** (tabelas de códigos e rótulos).

## 5.6 Window functions { #parte-5-6 }

```python
w = Window.partitionBy("uf").orderBy(F.col("salario").desc())

df.withColumn("rank_na_uf", F.row_number().over(w)).show()
df.withColumn("media_da_uf", F.avg("salario").over(Window.partitionBy("uf"))).show()
```
Diferente do `groupBy`, uma window **não reduz** as linhas: ela calcula um valor por linha olhando para um grupo.

## 5.7 Lazy evaluation — o conceito mais importante { #parte-5-7 }

- **Transformações** (`select`, `filter`, `withColumn`, `groupBy`, `join`) **não executam nada**. Elas só montam um plano.
- **Ações** (`show`, `count`, `collect`, `toPandas`, `write`) **disparam a execução**.

```python
plano = df.filter(F.col("uf") == "PE").select("nome_completo")   # nada rodou ainda
plano.explain()                                                  # mostra o plano
plano.show()                                                     # agora executou
```
**Por que importa:** o otimizador (Catalyst) enxerga o plano inteiro antes de executar. Por exemplo, ele aplica o filtro antes de ler colunas desnecessárias (*predicate pushdown*). Por isso, **evite `collect()` e `toPandas()` em dados grandes**: eles trazem tudo para a memória do driver.

## 5.8 Partições e escrita { #parte-5-8 }

```python
df.rdd.getNumPartitions()   # quantas partições o DataFrame tem
df.repartition(4)           # redistribui (com shuffle)
df.coalesce(1)              # junta partições (sem shuffle completo)

df.write.mode("overwrite").partitionBy("uf").parquet("/tmp/estudo_parquet")
spark.read.parquet("/tmp/estudo_parquet").filter("uf = 'PE'").show()
```
`partitionBy("uf")` cria pastas `uf=PE/`, `uf=SP/` e assim por diante. Uma consulta com filtro por `uf` lê **só a pasta necessária** (*partition pruning*).

**Modos de escrita**
| Modo | Comportamento |
|---|---|
| `error` (padrão) | Falha se o destino existir |
| `overwrite` | Substitui |
| `append` | Adiciona |
| `ignore` | Não faz nada se existir |

## 5.9 SQL também funciona { #parte-5-9 }

```python
df.createOrReplaceTempView("pessoas")
spark.sql("SELECT uf, AVG(salario) AS media FROM pessoas GROUP BY uf").show()
```
A API de DataFrame e o SQL geram o **mesmo plano**. Use o que deixar o código mais legível.

## Exercícios

1. Qual a média salarial por sexo?
2. Quem tem o maior salário em cada UF? (dica: window + `row_number`)
3. Crie `ano_admissao` e conte as admissões por ano.
4. Grave o resultado do exercício 1 em Parquet e leia de volta.
5. Rode `.explain()` num `filter + groupBy` e encontre o `Exchange` (é o shuffle).

<details>
<summary>Gabarito (tente antes de abrir)</summary>

```python
# 1
df.groupBy("sexo").agg(F.round(F.avg("salario"), 2).alias("media")).show()

# 2
w = Window.partitionBy("uf").orderBy(F.col("salario").desc())
df.withColumn("r", F.row_number().over(w)).filter("r = 1").drop("r").show()

# 3
(df.withColumn("ano_admissao", F.year("admissao"))
   .groupBy("ano_admissao").count().orderBy("ano_admissao").show())

# 4
r = df.groupBy("sexo").agg(F.avg("salario").alias("media"))
r.write.mode("overwrite").parquet("/tmp/media_sexo")
spark.read.parquet("/tmp/media_sexo").show()

# 5
df.filter(F.col("salario") > 3000).groupBy("uf").count().explain()
```
</details>

### Checkpoint
Você consegue explicar com suas palavras: (a) a diferença entre transformação e ação; (b) o que é shuffle e por que ele é caro; (c) por que Parquet particionado é mais rápido que CSV.

---
