"""Bronze: CSV/TXT da RAIS -> Delta, fiel à origem.

Origem: Guia Parte 9.2 / Aula 11.
[Complemento] Leitura e preparação separadas em funções sem E/S de tabela
(`ler_texto`, `preparar_bronze`) para poderem ser testadas sem MinIO/Delta.
"""
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from config.settings import BRONZE, RAW
from src.delta_io import gravar_ano
from src.utils import get_spark, normalize_columns


def ler_texto(spark: SparkSession, caminho: str) -> DataFrame:
    """Lê os .txt da RAIS: separador ';', latin-1, tudo string."""
    return (
        spark.read
        .option("header", True)
        .option("sep", ";")
        .option("encoding", "ISO-8859-1")
        .option("inferSchema", False)          # tudo string, de propósito
        .csv(caminho)
    )


def preparar_bronze(df: DataFrame, ano: int) -> DataFrame:
    """Rastreabilidade + nomes normalizados + coluna ano. `df` deve vir direto de ler_texto."""
    # Nome do arquivo de origem (antes de renomear as colunas)
    df = df.withColumn("arquivo_origem", F.col("_metadata.file_name"))
    return normalize_columns(df).withColumn("ano", F.lit(ano).cast("int"))


def construir_bronze(ano: int, spark: SparkSession | None = None) -> None:
    spark = spark or get_spark("rais-bronze")
    df = preparar_bronze(ler_texto(spark, str(RAW / str(ano) / "*.txt")), ano)
    gravar_ano(spark, df, BRONZE, ano, merge_schema=True)
    print(f"[bronze] {ano} gravado em {BRONZE}")


if __name__ == "__main__":
    import sys

    construir_bronze(int(sys.argv[1]))
