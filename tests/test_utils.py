"""Testes de unidade (Guia Parte 15.3 / Aulas 10, 13 e 16)."""
from decimal import Decimal

import pytest

from src.dims import dim_uf
from src.gold import gap_sexo
from src.utils import normalize_col, normalize_columns, to_decimal, to_int


def test_normalize_col():
    assert normalize_col("Vl Remun Média (SM)") == "vl_remun_media_sm"
    assert normalize_col("Vínculo Ativo 31/12") == "vinculo_ativo_31_12"


def test_normalize_columns_colisao(spark):
    df = spark.createDataFrame([("1", "2")], ["A b", "a_b"])
    with pytest.raises(ValueError):
        normalize_columns(df)


def test_to_decimal(spark):
    df = spark.createDataFrame([("1234,56",), ("1.234,56",), ("{ñ class}",), (None,)], ["v"])
    out = [r[0] for r in df.select(to_decimal(df, "v")).collect()]
    assert out == [Decimal("1234.56"), Decimal("1234.56"), None, None]


def test_to_int_coluna_ausente(spark):
    df = spark.createDataFrame([("1",)], ["x"])
    assert df.select(to_int(df, "nao_existe")).first()[0] is None


def test_gap_sexo(spark):
    ativos = spark.createDataFrame(
        [(2022, "26", 1, Decimal("2.00")), (2022, "26", 2, Decimal("1.50"))],
        "ano int, cod_uf string, sexo int, remun_dezembro_sm decimal(18,2)",
    )
    linha = gap_sexo(ativos, dim_uf(spark)).first()
    assert linha["uf"] == "PE"
    assert float(linha["razao_mulher_homem"]) == 0.75
