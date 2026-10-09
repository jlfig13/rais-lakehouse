"""Checagens de qualidade sobre os dados reais. Falham alto para não esconder problema.

Origem: Guia Parte 15.4 / Aula 14.
"""
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from config.settings import BRONZE, SILVER
from src.delta_io import ler

# Limites iniciais: calibre depois de conhecer os dados
MAX_NULL_REMUN = 0.05
MAX_NULL_UF = 0.01


def validar_silver(s: DataFrame, b: DataFrame, ano: int) -> int:
    """Regras de qualidade sobre DataFrames já filtrados no ano. Devolve o total de linhas."""
    total_s, total_b = s.count(), b.count()
    assert total_s > 0, f"{ano}: silver vazia"
    assert total_s == total_b, f"{ano}: silver ({total_s}) != bronze ({total_b})"

    pct = s.select(
        F.avg(F.col("remun_dezembro_nom").isNull().cast("int")).alias("remun"),
        F.avg(F.col("cod_uf").isNull().cast("int")).alias("uf"),
    ).first()

    assert pct["remun"] <= MAX_NULL_REMUN, f"{ano}: {pct['remun']:.1%} de remuneração nula"
    assert pct["uf"] <= MAX_NULL_UF, f"{ano}: {pct['uf']:.1%} de UF nula"
    return total_s


def checar_silver(spark: SparkSession, ano: int) -> None:
    s = ler(spark, SILVER).filter(F.col("ano") == ano)
    b = ler(spark, BRONZE).filter(F.col("ano") == ano)
    total = validar_silver(s, b, ano)
    print(f"[checks] {ano}: {total:,} vínculos OK")
