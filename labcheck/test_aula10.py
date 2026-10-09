"""Checks da Aula 10."""
import subprocess

import pytest
from delta.tables import DeltaTable
from pyspark.errors import AnalysisException
from pyspark.sql import functions as F

from config.settings import LAKE
from src.delta_io import gravar_ano, ler
from src.dims import dim_escolaridade, dim_sexo, dim_uf

LAB = f"{LAKE}/_lab/aula10"


def test_a10_testes_utils():
    r = subprocess.run(["pytest", "-q", "tests/test_utils.py"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout[-500:]


def test_a10_gravar_ano_idempotente(spark):
    df = spark.range(100).withColumn("ano", F.lit(2022))
    gravar_ano(spark, df, LAB, 2022)
    gravar_ano(spark, df, LAB, 2022)
    assert ler(spark, LAB).filter("ano = 2022").count() == 100
    assert DeltaTable.forPath(spark, LAB).history().count() >= 2


def test_a10_replacewhere_protege(spark):
    errado = spark.range(5).withColumn("ano", F.lit(2023))
    gravar_ano(spark, spark.range(1).withColumn("ano", F.lit(2022)), LAB, 2022)  # garante tabela
    # Delta recusa dados de 2023 numa escrita com replaceWhere "ano = 2022".
    with pytest.raises(AnalysisException):
        gravar_ano(spark, errado, LAB, 2022)


def test_a10_dims_tipos(spark):
    assert dict(dim_uf(spark).dtypes) == {"cod_uf": "string", "uf": "string"}
    assert dict(dim_sexo(spark).dtypes)["sexo"] == "int"
    assert dim_escolaridade(spark).count() == 11
