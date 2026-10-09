"""Checks da Aula 08."""
from pyspark.sql import functions as F

from labs import aula07, aula08


def ufs(spark):
    return spark.createDataFrame([("PE", "Pernambuco"), ("SP", "São Paulo"), ("BA", "Bahia")], ["uf", "nome_uf"])


def test_a08_maior_salario_por_uf(spark):
    r = {row["uf"]: row["nome"] for row in aula08.maior_salario_por_uf(aula07.exemplo(spark)).collect()}
    assert r == {"PE": "Bruno", "SP": "Carla", "BA": "Felipe"}, f"Obtido: {r}"


def test_a08_join_broadcast(spark):
    df = aula08.com_nome_uf(aula07.exemplo(spark), ufs(spark))
    assert df.count() == 6 and df.filter(F.col("nome_uf").isNull()).count() == 0
    assert "BroadcastExchange" in aula08.plano(df), "O join não usou broadcast."


def test_a08_detecta_shuffle(spark):
    df = aula07.exemplo(spark)
    assert aula08.tem_shuffle(df.groupBy("uf").count())
    assert not aula08.tem_shuffle(df.filter(F.col("uf") == "PE"))
    assert not aula08.tem_shuffle(aula08.com_nome_uf(df, ufs(spark)))


def test_a08_particionado_pruning(spark, tmp_path):
    destino = str(tmp_path / "parquet")
    aula07.exemplo(spark).write.mode("overwrite").partitionBy("uf").parquet(destino)
    lido = spark.read.parquet(destino).filter("uf = 'PE'")
    assert lido.count() == 2
    assert "PartitionFilters" in aula08.plano(lido), "Leitura sem partition pruning."
