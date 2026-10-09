"""Checks da Aula 13: gold completa e coerente com a silver."""
import subprocess

from delta.tables import DeltaTable
from pyspark.sql import functions as F

from config.settings import GOLD, SILVER
from src.delta_io import ler

TABELAS = ["gold_emprego_uf_ano", "gold_gap_sexo_uf_ano", "gold_top_cnae_uf_ano",
           "gold_escolaridade_ano", "gold_desligamento_uf_ano"]


def test_a13_cinco_tabelas(spark):
    faltando = [t for t in TABELAS if not DeltaTable.isDeltaTable(spark, f"{GOLD}/{t}")]
    assert not faltando, f"Tabelas ausentes: {faltando}. Rode: python -m src.gold"


def test_a13_total_bate_silver(spark, ano):
    gold = (ler(spark, f"{GOLD}/gold_emprego_uf_ano").filter(F.col("ano") == ano)
            .agg(F.sum("qtd_vinculos")).first()[0])
    silver = ler(spark, SILVER).filter((F.col("ano") == ano) & F.col("vinculo_ativo")).count()
    assert gold == silver, f"gold={gold:,} silver ativos={silver:,}"


def test_a13_uf_preenchida(spark, ano):
    g = ler(spark, f"{GOLD}/gold_emprego_uf_ano").filter(F.col("ano") == ano)
    nulas = g.filter(F.col("uf").isNull()).select("cod_uf").collect()
    assert not nulas, f"UF nula para cod_uf {[r[0] for r in nulas]}. Investigue com left_anti."


def test_a13_top10(spark):
    maximo = ler(spark, f"{GOLD}/gold_top_cnae_uf_ano").agg(F.max("posicao")).first()[0]
    assert maximo <= 10, f"posicao máxima {maximo}"


def test_a13_teste_gap_sexo():
    r = subprocess.run(["pytest", "-q", "tests/test_utils.py::test_gap_sexo"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout[-500:]
