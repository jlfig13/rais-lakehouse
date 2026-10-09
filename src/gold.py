"""Gold: tabelas analíticas prontas para consumo.

Origem: Guia Parte 11.2 / Aula 13. Cada tabela é uma função pura (testável sem lake).
"""
from pyspark.sql import DataFrame, SparkSession, Window
from pyspark.sql import functions as F

from config.settings import GOLD, SILVER
from src.delta_io import gravar_tabela, ler
from src.dims import dim_escolaridade, dim_uf
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


def tabelas_gold(silver: DataFrame, spark: SparkSession) -> dict[str, DataFrame]:
    """As cinco tabelas gold a partir da silver (sem gravar nada)."""
    ativos = silver.filter(F.col("vinculo_ativo"))
    uf = F.broadcast(dim_uf(spark))
    esc = F.broadcast(dim_escolaridade(spark))
    return {
        "gold_emprego_uf_ano": emprego_uf(ativos, uf),
        "gold_gap_sexo_uf_ano": gap_sexo(ativos, uf),
        "gold_top_cnae_uf_ano": top_cnae(ativos, uf),
        "gold_escolaridade_ano": escolaridade(ativos, esc),
        "gold_desligamento_uf_ano": desligamento(silver, uf),
    }


def construir_gold(spark: SparkSession | None = None) -> None:
    spark = spark or get_spark("rais-gold")
    for nome, df in tabelas_gold(ler(spark, SILVER), spark).items():
        gravar_tabela(df.coalesce(4), f"{GOLD}/{nome}")   # poucos arquivos: tabela pequena
        print(f"[gold] {nome}")


if __name__ == "__main__":
    construir_gold()
