---
aula: 8
titulo: "PySpark II: joins, window functions, lazy evaluation e partições"
origem: ['Guia Parte 5.5', 'Guia Parte 5.6', 'Guia Parte 5.7', 'Guia Parte 5.8']
depende_de: [7]
checks: ['a08_maior_salario_por_uf', 'a08_join_broadcast', 'a08_detecta_shuffle', 'a08_particionado_pruning']
---

# Aula 08 — PySpark II: joins, window functions, lazy evaluation e partições

<!-- Página GERADA por scripts/gerar_curso.py. Edite aulas.yml e curso/conteudo/. -->

<div class="rl-aula" data-aula="8" data-onde="container" data-lab="labs/aula08.py"></div>

| | |
| --- | --- |
| Origem no guia | Guia Parte [5.5](../guia/parte-05.md#parte-5-5), Guia Parte [5.6](../guia/parte-05.md#parte-5-6), Guia Parte [5.7](../guia/parte-05.md#parte-5-7), Guia Parte [5.8](../guia/parte-05.md#parte-5-8) |
| Depende de | [Aula 07](aula-07.md) |
| Entregas | `labs/aula08.py` |
| Onde os checks rodam | Container spark |

Esta aula cobre o que separa "saber a sintaxe" de "saber usar o Spark": como ele decide executar (lazy evaluation e plano), o que custa caro (shuffle) e como os dados ficam no disco (partições e Parquet).

**Convenção:** <span class="rl-complemento">Complemento didático</span> marca o que não está no guia original.

## 1. Objetivos e pré-requisitos

1. Fazer joins e decidir quando usar `broadcast`.
2. Usar window functions para rankings e médias por grupo sem perder linhas.
3. Explicar lazy evaluation, distinguir transformação de ação e ler um `explain()`.
4. Identificar um shuffle no plano.
5. Controlar partições (`repartition`, `coalesce`) e gravar Parquet particionado com *partition pruning*.

**Pré-requisitos:** Aula 07 (DataFrame `df` de exemplo e `labs/aula07.py`).

## 2. Contextualização

Na RAIS, a silver de um ano tem dezenas de milhões de linhas, e a gold faz `groupBy` e `join` sobre ela. A diferença entre um job de minutos e um de horas quase sempre está em: quantos shuffles ele faz, se a dimensão foi "broadcastada" e quantas partições existem. Esta aula dá as ferramentas para enxergar isso antes de rodar no volume real. <span class="rl-complemento">Complemento didático</span>

## 3. Fundamentação teórica

### 3.1 Joins (guia, Parte [5.5](../guia/parte-05.md#parte-5-5))

| Tipo | Mantém |
| --- | --- |
| `inner` | Só as chaves presentes nos dois lados |
| `left` | Todas as linhas da esquerda; colunas da direita viram NULL quando não há par |
| `right`, `full` | Espelho do left; ambos os lados |
| `left_anti` | Linhas da esquerda **sem** par na direita (ótimo para achar códigos fora da dimensão) |

**Custo.** Um join normal faz *shuffle*: redistribui as duas tabelas pela chave, para que linhas com a mesma chave fiquem na mesma tarefa. Com `F.broadcast(tabela_pequena)`, o Spark copia a tabela pequena inteira para todas as tarefas e evita o shuffle. Use em **dimensões** (códigos e rótulos) — como `dim_uf` na gold (Aula 13).

<span class="rl-complemento">Complemento didático</span> O Spark também faz broadcast automático quando estima que uma tabela é pequena (limite configurável). O `F.broadcast` explícito torna a intenção clara e não depende da estimativa.

**Risco:** broadcast de uma tabela que não é pequena estoura a memória.

### 3.2 Window functions (guia, Parte [5.6](../guia/parte-05.md#parte-5-6))

Diferente do `groupBy`, uma window **não reduz** as linhas: calcula um valor por linha olhando um grupo.

| Parte | Papel |
| --- | --- |
| `Window.partitionBy("uf")` | Define o grupo (não confundir com partições físicas) |
| `.orderBy(F.col("salario").desc())` | Ordem dentro do grupo (necessária para rankings) |
| `F.row_number().over(w)` | 1, 2, 3... por grupo, sem empates |
| `F.avg(...).over(Window.partitionBy("uf"))` | Média do grupo repetida em cada linha |

<span class="rl-complemento">Complemento didático</span> `row_number` desempata arbitrariamente; `rank` dá a mesma posição a empates e pula a seguinte; `dense_rank` não pula. Na gold, `top_cnae` usa `row_number` para garantir no máximo 10 linhas por UF.

### 3.3 Lazy evaluation — o conceito mais importante (guia, Parte [5.7](../guia/parte-05.md#parte-5-7))

- **Transformações** (`select`, `filter`, `withColumn`, `groupBy`, `join`) **não executam nada**; só montam um plano.
- **Ações** (`show`, `count`, `collect`, `toPandas`, `write`) **disparam a execução**.

O otimizador (Catalyst) enxerga o plano inteiro antes de executar — por exemplo, aplica o filtro antes de ler colunas desnecessárias (*predicate pushdown*). Por isso, evite `collect()` e `toPandas()` em dados grandes: eles trazem tudo para a memória do driver.

<span class="rl-complemento">Complemento didático</span> Consequência prática: um erro numa transformação (ex.: divisão que gera problema em certos dados) só aparece quando a ação roda, às vezes linhas depois no notebook. E cada ação reexecuta o plano desde o início, a menos que haja cache (Aula 15).

### 3.4 Shuffle e o `explain()`

**Shuffle** é a redistribuição de dados entre partições; é a operação mais cara do Spark (guia, [Apêndice C](../guia/apendice-c.md)). Ocorre em `groupBy`, `join` (sem broadcast), `orderBy`, `repartition`. No `explain()`, aparece como nó `Exchange`.

| No plano | Significado |
| --- | --- |
| `Exchange hashpartitioning(...)` | Shuffle por chave (groupBy, join) |
| `Exchange rangepartitioning(...)` | Shuffle para ordenar (orderBy) |
| `BroadcastExchange` | Cópia da tabela pequena — **não** é shuffle |
| `AdaptiveSparkPlan` | AQE ligado (Aula 15); o plano final pode mudar em execução |

### 3.5 Partições e escrita (guia, Parte [5.8](../guia/parte-05.md#parte-5-8))

| Operação | Efeito | Custo |
| --- | --- | --- |
| `df.rdd.getNumPartitions()` | Quantas partições o DataFrame tem | — |
| `repartition(n)` / `repartition(n, "col")` | Redistribui | Shuffle |
| `coalesce(n)` | Junta partições | Sem shuffle completo |
| `write.partitionBy("uf")` | Cria pastas `uf=PE/`, `uf=SP/` no disco | — |

`partitionBy` habilita **partition pruning**: uma consulta com filtro por `uf` lê só a pasta necessária. No curso, bronze, silver e gold são particionadas por `ano`.

**Partição de memória × partição de disco.** <span class="rl-complemento">Complemento didático</span> `repartition` muda como o DataFrame está dividido para processamento; `partitionBy` na escrita muda como os arquivos são organizados em pastas. São conceitos diferentes com o mesmo nome.

**Modos de escrita (guia, Parte [5.8](../guia/parte-05.md#parte-5-8)):** `error` (padrão, falha se existir), `overwrite`, `append`, `ignore`.

## 4. Arquitetura e fluxo

```
 df.filter(...).groupBy("uf").agg(...).show()
 │
 ├─ 1. plano lógico (o que você pediu)
 ├─ 2. Catalyst otimiza (pushdown, poda de colunas)
 ├─ 3. plano físico:  Scan → Filter → HashAggregate(parcial)
 │                       → Exchange hashpartitioning(uf)   ← shuffle
 │                       → HashAggregate(final)
 └─ 4. show() executa: tarefas por partição, em paralelo nas threads
```

<span class="rl-complemento">Complemento didático</span> O `HashAggregate` aparece duas vezes porque o Spark agrega parcialmente em cada partição antes do shuffle, para mandar menos dados pela rede.

## 5. Tutorial

Continue no notebook da Aula 07 (o DataFrame `df` original, com `nome` — recrie com `aula07.exemplo(spark)` se tiver renomeado).

### Passo 1 — Joins (guia, Parte [5.5](../guia/parte-05.md#parte-5-5))

```python
from pyspark.sql import Window, functions as F
from labs import aula07

df = aula07.exemplo(spark)
ufs = spark.createDataFrame(
    [("PE", "Pernambuco"), ("SP", "São Paulo"), ("BA", "Bahia")], ["uf", "nome_uf"]
)

df.join(ufs, on="uf", how="left").show()
df.join(F.broadcast(ufs), on="uf", how="left").explain()   # procure BroadcastExchange
```

### Passo 2 — Window functions (guia, Parte [5.6](../guia/parte-05.md#parte-5-6))

```python
w = Window.partitionBy("uf").orderBy(F.col("salario").desc())

df.withColumn("rank_na_uf", F.row_number().over(w)).show()
df.withColumn("media_da_uf", F.avg("salario").over(Window.partitionBy("uf"))).show()
```

### Passo 3 — Lazy evaluation (guia, Parte [5.7](../guia/parte-05.md#parte-5-7))

```python
plano = df.filter(F.col("uf") == "PE").select("nome")   # nada rodou ainda
plano.explain()                                         # mostra o plano
plano.show()                                            # agora executou
```

Compare com um plano que tem shuffle: `df.groupBy("uf").count().explain()`.

### Passo 4 — Partições e escrita (guia, Parte [5.8](../guia/parte-05.md#parte-5-8))

```python
df.rdd.getNumPartitions()
df.repartition(4).rdd.getNumPartitions()   # 4
df.coalesce(1).rdd.getNumPartitions()      # 1

df.write.mode("overwrite").partitionBy("uf").parquet("/tmp/estudo_parquet")
spark.read.parquet("/tmp/estudo_parquet").filter("uf = 'PE'").show()
```

No terminal do container (`make shell`): `ls /tmp/estudo_parquet` mostra `uf=BA`, `uf=PE`, `uf=SP`. Rode `.explain()` na leitura filtrada e procure `PartitionFilters` — é o pruning acontecendo.

### Passo 5 — `labs/aula08.py`

<span class="rl-complemento">Complemento didático</span> Assinaturas para implementar (respostas na seção 12):

```python
"""Exercícios da Aula 08 (PySpark II)."""
import contextlib
import io

from pyspark.sql import DataFrame, Window
from pyspark.sql import functions as F


def plano(df: DataFrame) -> str:
    """Texto do explain() (o PySpark imprime o plano; capturamos a saída)."""
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        df.explain()
    return buffer.getvalue()


def tem_shuffle(df: DataFrame) -> bool:
    """True se o plano tem Exchange que NÃO seja BroadcastExchange."""
    ...


def maior_salario_por_uf(df: DataFrame) -> DataFrame:
    """Uma linha por UF com a pessoa de maior salário (window + row_number)."""
    ...


def com_nome_uf(df: DataFrame, ufs: DataFrame) -> DataFrame:
    """Left join com a dimensão de UFs, usando broadcast."""
    ...
```

## 6. Funcionamento e resultados esperados

| Operação | Esperado |
| --- | --- |
| Maior salário por UF | PE → Bruno; SP → Carla; BA → Felipe |
| `explain` do filter + select | Sem `Exchange` |
| `explain` do groupBy | `Exchange hashpartitioning` |
| `explain` do join com broadcast | `BroadcastExchange` e `BroadcastHashJoin`, sem `Exchange hashpartitioning` |
| Leitura filtrada por `uf` | `PartitionFilters` no plano; 2 linhas para PE |

## 7. Exemplos práticos

**Exemplo 1 — Códigos órfãos com `left_anti`.** <span class="rl-complemento">Complemento didático</span> Na RAIS, para achar municípios cuja UF não está em `dim_uf` (o problema de "UF nula" da Aula 13): `silver.select("cod_uf").distinct().join(dim_uf(spark), "cod_uf", "left_anti").show()`.

**Exemplo 2 — Top N por grupo.** `gold_top_cnae_uf_ano` (Aula 13) é exatamente o padrão do passo 2: window por `ano, cod_uf` ordenada por massa salarial, `row_number`, filtro `<= 10`.

**Exemplo 3 — Pruning por ano.** Bronze, silver e gold são particionadas por `ano`; `filter(F.col("ano") == 2022)` lê só aquele ano — é o que torna barato reprocessar um ano (Aula 11).

## 8. Armadilhas, diagnóstico e soluções

| Sintoma | Causa | Solução |
| --- | --- | --- |
| `OutOfMemoryError` no driver | `collect()`/`toPandas()` em dado grande | Só em resultados pequenos |
| Join multiplicou linhas | Chave repetida na dimensão | Garantir chave única na dimensão (`distinct`/conferir) |
| Colunas da direita todas NULL | Tipos diferentes na chave (`"26"` × `26`) ou espaços | Mesmo tipo e `trim` nas chaves |
| `AnalysisException: ambiguous reference` | Mesma coluna nos dois lados do join | `on="coluna"` (string) em vez de expressão, ou renomear |
| Erro aparece "depois" da linha culpada | Lazy evaluation | Rodar uma ação pequena (`limit(5).show()`) após cada passo ao depurar |
| Muitos arquivos minúsculos na escrita | Muitas partições × muitas pastas | `coalesce` antes de gravar tabelas pequenas |
| Ranking com empates inesperados | Uso de `rank` em vez de `row_number` | Escolher conscientemente |

## 9. Boas práticas

1. `broadcast` em dimensões pequenas (guia).
2. Ler `explain()` antes de rodar algo caro no volume real.
3. Particionar por coluna de filtro frequente e baixa cardinalidade (`ano`, não `cod_municipio`). <span class="rl-complemento">Complemento didático</span>
4. `coalesce` para reduzir arquivos de saída; `repartition` só quando precisar redistribuir por chave.
5. Evitar `collect()` fora de resultados pequenos (guia).

## 10. Riscos

| Tipo | Risco | Mitigação |
| --- | --- | --- |
| Desempenho | Shuffles desnecessários | `explain`; broadcast; menos `orderBy` intermediários |
| Desempenho | Particionar por coluna de alta cardinalidade gera milhares de pastas | Particionar por `ano` |
| Integridade | Join que duplica ou perde linhas | Conferir contagens antes/depois; `left_anti` |
| Integridade | Empates mal tratados em rankings | `row_number` com critério de desempate explícito |

## 11. Laboratório e validação na plataforma

**Contribuição ao projeto:** broadcast, window e partitionBy são usados na gold e em todas as camadas; ler planos é a base do tuning (Aula 15).

<span class="rl-complemento">Complemento didático</span> `labcheck/test_aula08.py`:

```python
"""Checks da Aula 08."""
from pyspark.sql import functions as F

from labs import aula07, aula08


def ufs(spark):
    return spark.createDataFrame([("PE", "Pernambuco"), ("SP", "São Paulo"), ("BA", "Bahia")], ["uf", "nome_uf"])


def test_a08_maior_salario_por_uf(spark):
    r = {row["uf"]: row["nome"] for row in aula08.maior_salario_por_uf(aula07.exemplo(spark)).collect()}
    assert r == {"PE": "Bruno", "SP": "Carla", "BA": "Felipe"}, f"Obtido: {r}"


def test_a08_join_broadcast(spark):
    df = aula08.com_nome_uf(aula07.exemplo(spark), ufs(spark))
    assert df.count() == 6 and df.filter(F.col("nome_uf").isNull()).count() == 0
    assert "BroadcastExchange" in aula08.plano(df), "O join não usou broadcast."


def test_a08_detecta_shuffle(spark):
    df = aula07.exemplo(spark)
    assert aula08.tem_shuffle(df.groupBy("uf").count())
    assert not aula08.tem_shuffle(df.filter(F.col("uf") == "PE"))
    assert not aula08.tem_shuffle(aula08.com_nome_uf(df, ufs(spark)))


def test_a08_particionado_pruning(spark, tmp_path):
    destino = str(tmp_path / "parquet")
    aula07.exemplo(spark).write.mode("overwrite").partitionBy("uf").parquet(destino)
    lido = spark.read.parquet(destino).filter("uf = 'PE'")
    assert lido.count() == 2
    assert "PartitionFilters" in aula08.plano(lido), "Leitura sem partition pruning."
```

- `tmp_path` é uma fixture do pytest: uma pasta temporária única por teste.
- Rode com `make check AULA=08`.

**Checklist manual:**

- [ ] li um plano com `Exchange` e outro com `BroadcastExchange`
- [ ] vi as pastas `uf=...` no disco
- [ ] sei explicar por que `HashAggregate` aparece duas vezes.

## 12. Exercícios, revisão e desafios

**Respostas dos exercícios do guia (Parte [5](../guia/parte-05.md), exercícios 2, 4 e 5)** — tente antes de ler:

```python
def tem_shuffle(df):
    return any("Exchange" in linha and "BroadcastExchange" not in linha
               for linha in plano(df).splitlines())


def maior_salario_por_uf(df):
    w = Window.partitionBy("uf").orderBy(F.col("salario").desc())
    return df.withColumn("r", F.row_number().over(w)).filter("r = 1").drop("r")


def com_nome_uf(df, ufs):
    return df.join(F.broadcast(ufs), on="uf", how="left")
```

**Revisão**

1. Qual a diferença entre `groupBy` e window?
2. `BroadcastExchange` é shuffle?
3. Por que um erro numa transformação só aparece mais tarde?
4. Qual a diferença entre `repartition(4)` e `write.partitionBy("uf")`?

**Respostas sugeridas:** (1) groupBy reduz a uma linha por grupo; window mantém todas as linhas; (2) não: copia a tabela pequena, sem redistribuir a grande; (3) lazy evaluation: só a ação executa; (4) o primeiro divide o DataFrame em memória; o segundo organiza arquivos em pastas.

**Desafios**

1. Compare o plano do desafio 1 da Aula 07 (top por UF com groupBy + join) com a versão window. Quantos `Exchange` cada um tem?
2. Grave o mesmo DataFrame particionado por `id` (6 pastas) e por `uf` (3 pastas). Extrapole: o que aconteceria particionando a RAIS por município?

## 13. Referências cruzadas

| Tema | Onde |
| --- | --- |
| Fundamentos de DataFrame | Aula 07 |
| `dim_uf` e broadcast na gold | Aulas 10 e 13 |
| Partições por `ano` e `replaceWhere` | Aulas 10 e 11 |
| AQE, `shuffle.partitions`, Spark UI, skew, cache | Aula 15 |
| Termos: shuffle, broadcast, pruning, lazy evaluation | Apêndice C |


## Checks automáticos

```bash
make check AULA=08 ANO=2022
```

Arquivo: `labcheck/test_aula08.py`. Cada execução grava o resultado em `progress/historico.jsonl`; depois rode `make progresso` para atualizar a página [Progresso](../progresso.md).

| Check | O que verifica |
| --- | --- |
| `a08_maior_salario_por_uf` | maior salario por uf |
| `a08_join_broadcast` | join broadcast |
| `a08_detecta_shuffle` | detecta shuffle |
| `a08_particionado_pruning` | particionado pruning |
