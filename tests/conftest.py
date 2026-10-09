"""SparkSession compartilhada pelos testes de unidade (Guia Parte 15.3).

Não usa get_spark: testes de unidade não precisam de MinIO nem Delta e rodam no CI.
"""
import pytest
from pyspark.sql import SparkSession


@pytest.fixture(scope="session")
def spark():
    s = (SparkSession.builder.master("local[1]").appName("tests")
         .config("spark.sql.shuffle.partitions", "1")
         .config("spark.ui.enabled", "false")
         .getOrCreate())
    yield s
    s.stop()
