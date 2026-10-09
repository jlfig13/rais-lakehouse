"""SparkSession e funções auxiliares reutilizáveis.

Origem: Guia Parte 7.3 / Aulas 06 e 10.
"""
import os
import re
import unicodedata

from pyspark.sql import Column, DataFrame, SparkSession
from pyspark.sql import functions as F


def get_spark(app_name: str = "rais") -> SparkSession:
    """Cria a SparkSession local com Delta e S3A (MinIO).

    Todos os recursos são ajustáveis por variável de ambiente (ver Aula 15).
    Obs.: memória e nº de threads só valem se a sessão ainda não existe.
    """
    threads = int(os.getenv("SPARK_THREADS", "4"))

    return (
        SparkSession.builder
        .master(f"local[{threads}]")
        .appName(app_name)
        # --- Delta Lake (JARs já estão na imagem) ---
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog",
                "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        # --- Recursos ---
        .config("spark.driver.memory", os.getenv("SPARK_MEM", "4g"))
        .config("spark.sql.shuffle.partitions", os.getenv("SPARK_SHUFFLE", "32"))
        .config("spark.sql.files.maxPartitionBytes", "128m")
        .config("spark.sql.adaptive.enabled", "true")
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true")
        .config("spark.local.dir", os.getenv("SPARK_TMP", "/tmp/spark"))
        .config("spark.sql.session.timeZone", "America/Sao_Paulo")
        # --- S3A -> MinIO ---
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
        .config("spark.hadoop.fs.s3a.endpoint", os.getenv("MINIO_ENDPOINT", "http://minio:9000"))
        .config("spark.hadoop.fs.s3a.access.key", os.getenv("S3_ACCESS_KEY", ""))
        .config("spark.hadoop.fs.s3a.secret.key", os.getenv("S3_SECRET_KEY", ""))
        .config("spark.hadoop.fs.s3a.path.style.access", "true")
        .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false")
        .getOrCreate()
    )


def normalize_col(name: str) -> str:
    """'Vl Remun Média (SM)' -> 'vl_remun_media_sm'."""
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-z0-9]+", "_", s.lower().strip())
    return s.strip("_")


def normalize_columns(df: DataFrame) -> DataFrame:
    """Normaliza todos os nomes de coluna; falha se dois nomes colidirem."""
    novos = [normalize_col(c) for c in df.columns]
    repetidos = {c for c in novos if novos.count(c) > 1}
    if repetidos:
        raise ValueError(f"Colunas duplicadas após normalizar: {repetidos}")
    return df.toDF(*novos)


def col_or_null(df: DataFrame, name: str) -> Column:
    """Coluna como string; NULL se não existir (o schema da RAIS muda entre anos)."""
    if name not in df.columns:
        return F.lit(None).cast("string")
    return F.trim(F.col(name))


def to_int(df: DataFrame, name: str) -> Column:
    """Texto -> int. Valor inválido ou coluna ausente vira NULL (sem quebrar o job)."""
    if name not in df.columns:
        return F.lit(None).cast("int")
    return F.expr(f"try_cast(trim(`{name}`) AS int)")


def to_decimal(df: DataFrame, name: str, precision: int = 18, scale: int = 2) -> Column:
    """'1.234,56' ou '1234,56' -> decimal. Inválido ou ausente vira NULL."""
    if name not in df.columns:
        return F.lit(None).cast(f"decimal({precision},{scale})")
    sem_milhar = f"regexp_replace(trim(`{name}`), '\\\\.', '')"
    com_ponto = f"regexp_replace({sem_milhar}, ',', '.')"
    return F.expr(f"try_cast({com_ponto} AS decimal({precision},{scale}))")
