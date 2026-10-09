"""Checks da Aula 14: pipeline com vários anos e operação Delta."""
from delta.tables import DeltaTable

from config.settings import GOLD, SILVER
from src.checks import checar_silver
from src.delta_io import ler


def test_a14_varios_anos_na_gold(spark):
    anos = [r[0] for r in ler(spark, f"{GOLD}/gold_emprego_uf_ano").select("ano").distinct().collect()]
    assert len(anos) >= 2, f"Gold só tem {sorted(anos)}. Rode o pipeline com pelo menos 2 anos."


def test_a14_checar_silver(spark, ano):
    checar_silver(spark, ano)  # lança AssertionError com o motivo se algo estiver fora


def test_a14_historico(spark):
    assert DeltaTable.forPath(spark, SILVER).history().count() >= 2, "Silver com uma única versão."


def test_a14_time_travel(spark):
    assert spark.read.format("delta").option("versionAsOf", 0).load(SILVER).limit(1).count() == 1


def test_a14_optimize(spark):
    ops = {r[0] for r in DeltaTable.forPath(spark, SILVER).history().select("operation").collect()}
    assert "OPTIMIZE" in ops, "Rode dt.optimize().executeCompaction() na silver (passo 4)."
