"""Checks da Aula 12: contrato da silver."""
from delta.tables import DeltaTable
from pyspark.sql import functions as F

from config.settings import BRONZE, SILVER
from src.delta_io import ler

TIPOS = {
    "ano": "int", "cod_municipio": "string", "cnae_classe": "string", "cbo": "string",
    "sexo": "int", "escolaridade": "int", "idade": "int", "mes_desligamento": "int",
    "tempo_emprego_meses": "decimal(10,1)", "vinculo_ativo": "boolean",
    "remun_dezembro_nom": "decimal(18,2)", "remun_dezembro_sm": "decimal(18,2)",
    "cod_uf": "string", "cnae_divisao": "string", "desligado_no_ano": "boolean",
}


def silver_ano(spark, ano):
    return ler(spark, SILVER).filter(F.col("ano") == ano)


def test_a12_silver_delta(spark):
    assert DeltaTable.isDeltaTable(spark, SILVER), "Silver não existe. Rode o passo 2."


def test_a12_contagem_igual_bronze(spark, ano):
    bronze = ler(spark, BRONZE).filter(F.col("ano") == ano).count()
    silver = silver_ano(spark, ano).count()
    assert silver == bronze, (
        f"silver={silver:,} bronze={bronze:,}. Diagnóstico: algum filter() na silver está "
        "removendo linhas; valores inválidos devem virar NULL."
    )


def test_a12_tipos_do_contrato(spark):
    reais = dict(ler(spark, SILVER).dtypes)
    erradas = {c: (reais.get(c), t) for c, t in TIPOS.items() if reais.get(c) != t}
    assert not erradas, f"Coluna: (obtido, esperado) -> {erradas}"


def test_a12_uf_valida(spark, ano):
    s = silver_ano(spark, ano)
    pct = s.select(F.avg(F.col("cod_uf").isNull().cast("int"))).first()[0]
    assert pct <= 0.01, f"{pct:.1%} de UF nula. Veja o arquivo NI e a regra do município."


def test_a12_idade_plausivel(spark, ano):
    fora = silver_ano(spark, ano).filter(~F.col("idade").between(14, 100)).limit(1).count()
    assert fora == 0, "Há idades fora de 14..100 que deviam ter virado NULL."
