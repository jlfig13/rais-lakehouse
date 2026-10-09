"""Checks da Aula 06: Spark, Delta e MinIO integrados."""
from config.settings import LAKE

SMOKE = f"{LAKE}/_smoke/teste"


def test_a06_versao_spark(spark):
    assert spark.version == "3.5.3", f"Spark {spark.version}; o curso usa 3.5.3 (Aula 02)."


def test_a06_config_s3a(spark):
    assert spark.conf.get("spark.hadoop.fs.s3a.path.style.access") == "true", "Path-style desligado."
    assert "minio" in spark.conf.get("spark.hadoop.fs.s3a.endpoint"), "Endpoint não aponta para o serviço minio."


def test_a06_smoke_1000(spark):
    total = spark.read.format("delta").load(SMOKE).count()
    assert total == 1000, f"{total} linhas em {SMOKE}. Rode: make smoke"


def test_a06_smoke_e_delta(spark):
    from delta.tables import DeltaTable

    assert DeltaTable.isDeltaTable(spark, SMOKE), f"{SMOKE} não é uma tabela Delta."
