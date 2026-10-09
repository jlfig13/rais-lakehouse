"""Leitura e escrita Delta centralizadas (um só lugar para mudar o formato).

Origem: Guia Parte 7.4 / Aula 10.
"""
from pyspark.sql import DataFrame, SparkSession


def ler(spark: SparkSession, caminho: str) -> DataFrame:
    return spark.read.format("delta").load(caminho)


def gravar_ano(
    spark: SparkSession, df: DataFrame, caminho: str, ano: int, merge_schema: bool = False
) -> None:
    """Substitui ATOMICAMENTE apenas a partição do ano informado.

    - Tabela nova: grava normalmente, particionada por ano.
    - Tabela existente: usa replaceWhere -> troca só `ano = X`, sem tocar nos outros anos.
    """
    # Importado aqui: os testes de unidade não dependem do Delta.
    from delta.tables import DeltaTable

    escrita = df.write.format("delta").mode("overwrite").partitionBy("ano")
    if merge_schema:
        escrita = escrita.option("mergeSchema", "true")

    if DeltaTable.isDeltaTable(spark, caminho):
        escrita = escrita.option("replaceWhere", f"ano = {ano}")
    escrita.save(caminho)


def gravar_tabela(df: DataFrame, caminho: str) -> None:
    """Recria a tabela inteira (uso na gold, que é recalculada por completo)."""
    (df.write.format("delta")
       .mode("overwrite")
       .option("overwriteSchema", "true")
       .partitionBy("ano")
       .save(caminho))
