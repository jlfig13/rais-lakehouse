<!-- Página GERADA de docs/guia/rais-lakehouse-guia.md -->

# Parte [11](parte-11.md) — Gold

## 11.1 Conceito { #parte-11-1 }

A gold nasce de **perguntas de negócio**. Cada tabela responde uma pergunta específica e é pequena o bastante para ir direto a um gráfico, um BI ou um relatório.

**Regras de ouro**
- **R$ nominal não é comparável entre anos** (inflação e reajuste do mínimo). Para série histórica, use as colunas em **salários mínimos** (`*_sm`).
- A unidade é **vínculo**, não pessoa. Escreva "vínculos" nos rótulos, nunca "trabalhadores".
- Indicadores de estoque (quantos empregos existem) usam **vínculos ativos em 31/12**.

| Tabela | Pergunta |
|---|---|
| `gold_emprego_uf_ano` | Quantos vínculos ativos e qual a remuneração por UF e ano? |
| `gold_gap_sexo_uf_ano` | Quanto a remuneração média das mulheres representa da dos homens? |
| `gold_top_cnae_uf_ano` | Quais as 10 divisões de atividade com maior massa salarial por UF? |
| `gold_escolaridade_ano` | Como a remuneração varia com a escolaridade? |
| `gold_desligamento_uf_ano` | Qual a proporção de vínculos desligados no ano? |

## 11.2 `src/gold.py` { #parte-11-2 }

```python
"""Gold: tabelas analíticas prontas para consumo."""
from pyspark.sql import DataFrame, SparkSession, Window
from pyspark.sql import functions as F

from config.settings import GOLD, SILVER
from src.delta_io import gravar_tabela, ler
from src.dims import dim_escolaridade, dim_sexo, dim_uf
from src.utils import get_spark


def emprego_uf(ativos: DataFrame, uf: DataFrame) -> DataFrame:
    return (
        ativos.groupBy("ano", "cod_uf")
        .agg(
            F.count("*").alias("qtd_vinculos"),
            F.sum("remun_dezembro_nom").alias("massa_salarial_dez_nom"),
            F.round(F.avg("remun_dezembro_nom"), 2).alias("remun_media_dez_nom"),
            F.round(F.avg("remun_dezembro_sm"), 2).alias("remun_media_dez_sm"),
            F.percentile_approx("remun_dezembro_sm", 0.5).alias("remun_mediana_dez_sm"),
        )
        .join(uf, "cod_uf", "left")
    )


def gap_sexo(ativos: DataFrame, uf: DataFrame) -> DataFrame:
    return (
        ativos.groupBy("ano", "cod_uf")
        .agg(
            F.avg(F.when(F.col("sexo") == 2, F.col("remun_dezembro_sm"))).alias("rem_mulher_sm"),
            F.avg(F.when(F.col("sexo") == 1, F.col("remun_dezembro_sm"))).alias("rem_homem_sm"),
        )
        .withColumn("razao_mulher_homem",
                    F.round(F.col("rem_mulher_sm") / F.col("rem_homem_sm"), 3))
        .join(uf, "cod_uf", "left")
    )


def top_cnae(ativos: DataFrame, uf: DataFrame, n: int = 10) -> DataFrame:
    por_cnae = (
        ativos.filter(F.col("cnae_divisao").isNotNull())
        .groupBy("ano", "cod_uf", "cnae_divisao")
        .agg(
            F.count("*").alias("qtd_vinculos"),
            F.sum("remun_dezembro_nom").alias("massa_salarial_dez_nom"),
        )
    )
    w = Window.partitionBy("ano", "cod_uf").orderBy(F.col("massa_salarial_dez_nom").desc())
    return (
        por_cnae.withColumn("posicao", F.row_number().over(w))
        .filter(F.col("posicao") <= n)
        .join(uf, "cod_uf", "left")
    )


def escolaridade(ativos: DataFrame, esc: DataFrame) -> DataFrame:
    return (
        ativos.groupBy("ano", "escolaridade")
        .agg(
            F.count("*").alias("qtd_vinculos"),
            F.round(F.avg("remun_dezembro_sm"), 2).alias("remun_media_dez_sm"),
        )
        .join(esc, "escolaridade", "left")
    )


def desligamento(silver: DataFrame, uf: DataFrame) -> DataFrame:
    return (
        silver.groupBy("ano", "cod_uf")
        .agg(
            F.count("*").alias("qtd_vinculos_no_ano"),
            F.sum(F.col("desligado_no_ano").cast("int")).alias("qtd_desligados"),
        )
        .withColumn("taxa_desligamento",
                    F.round(F.col("qtd_desligados") / F.col("qtd_vinculos_no_ano"), 4))
        .join(uf, "cod_uf", "left")
    )


def construir_gold(spark: SparkSession | None = None) -> None:
    spark = spark or get_spark("rais-gold")

    silver = ler(spark, SILVER)
    ativos = silver.filter(F.col("vinculo_ativo"))
    uf = F.broadcast(dim_uf(spark))
    esc = F.broadcast(dim_escolaridade(spark))

    tabelas = {
        "gold_emprego_uf_ano": emprego_uf(ativos, uf),
        "gold_gap_sexo_uf_ano": gap_sexo(ativos, uf),
        "gold_top_cnae_uf_ano": top_cnae(ativos, uf),
        "gold_escolaridade_ano": escolaridade(ativos, esc),
        "gold_desligamento_uf_ano": desligamento(silver, uf),
    }
    for nome, df in tabelas.items():
        gravar_tabela(df.coalesce(4), f"{GOLD}/{nome}")   # poucos arquivos: tabela pequena
        print(f"[gold] {nome}")

    _ = dim_sexo  # disponível para enriquecer novas tabelas (exercício)


if __name__ == "__main__":
    construir_gold()
```

**Boa prática aplicada:** cada tabela é uma **função pura** (recebe DataFrames e devolve DataFrame). Isso torna o código **testável**: você chama `gap_sexo(df_de_teste, dim)` num teste, sem MinIO (Parte [15](parte-15.md)).

## 11.3 Consultando (notebook `04_gold.ipynb`) { #parte-11-3 }

```python
from pyspark.sql import functions as F

from config.settings import GOLD
from src.delta_io import ler
from src.utils import get_spark

spark = get_spark()
g = ler(spark, f"{GOLD}/gold_emprego_uf_ano")
g.orderBy(F.col("qtd_vinculos").desc()).show(10)

# Gold é pequena: pode ir para o pandas e virar gráfico
pdf = g.filter("uf = 'PE'").orderBy("ano").toPandas()
pdf.plot(x="ano", y="remun_media_dez_sm", marker="o")
```
> Use `toPandas()` **só** em tabelas gold. Em silver ou bronze, a memória estoura.

## Exercícios
1. Quais as 5 UFs com mais vínculos ativos?
2. Onde a `razao_mulher_homem` é menor?
3. Crie `gold_porte_ano` (remuneração por `tamanho_estab`).
4. Crie `gold_faixa_etaria_ano` (faixas `<25`, `25–39`, `40–59`, `60+` com `F.when`).
5. Exporte uma tabela gold para CSV e abra no Excel ou Power BI:
   ```python
   g.coalesce(1).write.mode("overwrite").option("header", True).csv("/staging/export/emprego")
   ```

### Checkpoint
- A soma de `qtd_vinculos` em `gold_emprego_uf_ano` bate com `silver.filter("vinculo_ativo").count()`.
- Nenhuma linha tem `uf` nula. Se houver, existe código de município fora da dimensão, e vale investigar.
- Commit: `feat: camada gold`.

---
