"""Teste de integração bronze -> silver -> gold sobre a AMOSTRA SINTÉTICA.

[Complemento da plataforma] Roda sem MinIO e sem Delta: usa as funções puras
(`ler_texto`, `preparar_bronze`, `transformar_silver`, `tabelas_gold`, `validar_silver`).
Valida os CONTRATOS das camadas (Aula 01), não números da RAIS real.
"""
import pytest
from pyspark.sql import functions as F

from labs.amostra.gerar_amostra import escrever_txt
from src.bronze import ler_texto, preparar_bronze
from src.checks import validar_silver
from src.gold import tabelas_gold
from src.silver import transformar_silver

ANO = 2022
LINHAS = 500


@pytest.fixture(scope="module")
def camadas(spark, tmp_path_factory):
    raw = tmp_path_factory.mktemp("raw")
    escrever_txt(raw, LINHAS)
    bronze = preparar_bronze(ler_texto(spark, str(raw / "*.txt")), ANO).cache()
    silver = transformar_silver(bronze, ANO).cache()
    return bronze, silver, tabelas_gold(silver, spark)


def test_bronze_tudo_string(camadas):
    bronze, _, _ = camadas
    assert bronze.count() == LINHAS
    assert all(t == "string" for c, t in bronze.dtypes if c != "ano")
    assert "municipio" in bronze.columns and "vl_remun_dezembro_sm" in bronze.columns


def test_bronze_encoding_latin1(camadas):
    bronze, _, _ = camadas
    # Se o encoding estivesse errado, "Município" viraria algo como "munic_pio"
    assert "municipio" in bronze.columns
    assert bronze.filter(F.col("arquivo_origem").isNull()).count() == 0


def test_silver_mesma_contagem_e_validacoes(camadas):
    bronze, silver, _ = camadas
    assert silver.count() == bronze.count()
    assert silver.filter(~F.col("idade").between(14, 100)).count() == 0
    assert silver.filter(F.col("cod_municipio").isNull()).count() > 0      # '9999' anulado
    assert silver.filter(F.col("remun_dezembro_nom").isNull()).count() > 0  # '{ñ class}' anulado
    assert dict(silver.dtypes)["remun_dezembro_nom"] == "decimal(18,2)"


def test_checagem_de_qualidade_passa(camadas):
    bronze, silver, _ = camadas
    # A amostra tem ~0,5% de município inválido; o limite do guia é 1%.
    assert validar_silver(silver, bronze, ANO) == LINHAS


def test_gold_total_bate_com_silver(camadas):
    _, silver, gold = camadas
    total = gold["gold_emprego_uf_ano"].agg(F.sum("qtd_vinculos")).first()[0]
    assert total == silver.filter("vinculo_ativo").count()
    assert gold["gold_top_cnae_uf_ano"].agg(F.max("posicao")).first()[0] <= 10
    desl = gold["gold_desligamento_uf_ano"].agg(F.sum("qtd_vinculos_no_ano")).first()[0]
    assert desl == silver.count()
