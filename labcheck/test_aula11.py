"""Checks da Aula 11: bronze do ano carregada, fiel e idempotente."""
import pytest
from delta.tables import DeltaTable
from pyspark.sql import functions as F

from config.settings import BRONZE
from src.delta_io import ler


def test_a11_bronze_delta(spark):
    assert DeltaTable.isDeltaTable(spark, BRONZE), f"{BRONZE} não é Delta. Rode o passo 2."


def test_a11_ano_carregado(spark, ano):
    assert ler(spark, BRONZE).filter(F.col("ano") == ano).limit(1).count() == 1, f"Ano {ano} vazio na bronze."


def test_a11_tudo_string(spark):
    nao_string = [c for c, t in ler(spark, BRONZE).dtypes if c != "ano" and t != "string"]
    assert not nao_string, f"Colunas tipadas na bronze: {nao_string}. A bronze é toda string."


def test_a11_arquivo_origem(spark, ano):
    b = ler(spark, BRONZE).filter(F.col("ano") == ano)
    assert b.filter(F.col("arquivo_origem").isNull()).limit(1).count() == 0, "Linhas sem arquivo_origem."


def test_a11_idempotente(spark, ano):
    """Em todas as versões da tabela que contêm o ano, a contagem dele é a mesma."""
    versoes = [r["version"] for r in DeltaTable.forPath(spark, BRONZE).history().select("version").collect()]
    contagens = set()
    for v in versoes:
        n = (spark.read.format("delta").option("versionAsOf", v).load(BRONZE)
             .filter(F.col("ano") == ano).count())
        if n:
            contagens.add((v, n))
    if len(contagens) < 2:
        pytest.skip(f"Reprocesse {ano} uma vez (python -m src.bronze {ano}) para validar a idempotência.")
    assert len({n for _, n in contagens}) == 1, f"Contagem do ano mudou entre versões: {sorted(contagens)}"
