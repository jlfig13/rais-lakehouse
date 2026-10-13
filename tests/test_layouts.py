"""Layouts da RAIS: até 2022 (';', vírgula) e 2023 (',', aspas, ponto decimal, outros nomes).

Os cabeçalhos abaixo reproduzem, encurtados, os dos arquivos reais do Nordeste (Aula 09).
"""
from decimal import Decimal

from src.bronze import ler_ano
from src.utils import to_decimal

ANTIGO = (
    "Município;CBO Ocupação 2002;Vínculo Ativo 31/12;Sexo Trabalhador;Vl Remun Dezembro Nom\n"
    "261160;411005;1;2;2350,75\n"
)
NOVO_2023 = (
    '"Município - Código","CBO 2002 Ocupação - Código","Ind Vínculo Ativo 31/12 - Código",'
    '"Sexo - Código","Vl Rem Dezembro Nom"\n'
    '230440," 411005",1,2,7771.49\n'
)


def test_to_decimal_ponto_decimal(spark):
    df = spark.createDataFrame([("7771.49",), (" 5.88",), ("11.0",)], ["v"])
    out = [r[0] for r in df.select(to_decimal(df, "v")).collect()]
    assert out == [Decimal("7771.49"), Decimal("5.88"), Decimal("11.00")]


def test_ler_ano_com_dois_layouts(spark, tmp_path):
    (tmp_path / "RAIS_VINC_PUB_NORDESTE.txt").write_text(ANTIGO, encoding="latin-1")
    (tmp_path / "RAIS_VINC_PUB_NORDESTE.COMT").write_text(NOVO_2023, encoding="latin-1")

    df = ler_ano(spark, tmp_path, 2023)

    for coluna in ["municipio", "cbo_ocupacao_2002", "vinculo_ativo_31_12", "sexo_trabalhador",
                   "vl_remun_dezembro_nom", "arquivo_origem", "ano"]:
        assert coluna in df.columns, (coluna, df.columns)
    linhas = {r["arquivo_origem"]: r for r in df.collect()}
    assert set(linhas) == {"RAIS_VINC_PUB_NORDESTE.txt", "RAIS_VINC_PUB_NORDESTE.COMT"}
    novo = linhas["RAIS_VINC_PUB_NORDESTE.COMT"]
    assert novo["municipio"] == "230440" and novo["cbo_ocupacao_2002"].strip() == "411005"
    valores = df.select(to_decimal(df, "vl_remun_dezembro_nom").alias("v")).collect()
    assert sorted(r["v"] for r in valores) == [Decimal("2350.75"), Decimal("7771.49")]


def test_remuneracao_vazia_vira_zero_e_invalida_vira_nulo(spark):
    from src.silver import remuneracao

    df = spark.createDataFrame([("0000000000,00",), (None,), ("",), ("{ñ class}",), ("7771.49",)],
                               "vl_remun_dezembro_nom string")
    out = [r[0] for r in df.select(remuneracao(df, "vl_remun_dezembro_nom")).collect()]
    assert out == [Decimal("0.00"), Decimal("0.00"), Decimal("0.00"), None, Decimal("7771.49")]
