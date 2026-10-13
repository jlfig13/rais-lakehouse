"""Silver: tipagem, validação e padronização da RAIS.

Origem: Guia Parte 10.2 / Aula 12.
[Complemento] A transformação foi extraída para `transformar_silver` (função pura),
para ser testada sem MinIO/Delta. O comportamento é o do guia.
"""
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from config.settings import BRONZE, SILVER
from src.delta_io import gravar_ano, ler
from src.utils import col_or_null, get_spark, to_decimal, to_int

# Sem estas colunas não faz sentido continuar
OBRIGATORIAS = ["municipio", "vinculo_ativo_31_12", "vl_remun_dezembro_nom"]


def remuneracao(b: DataFrame, nome: str):
    """Remuneração em decimal; campo vazio = sem remuneração no período (0).

    Conferido nos arquivos reais: até 2022 a RAIS grava 0 ("0000000000,00") para quem não
    recebeu no período; em 2023 passou a deixar o campo vazio. Tratar os dois como 0 mantém as
    médias da gold comparáveis entre anos. Texto inválido continua virando NULL.
    """
    if nome not in b.columns:
        return to_decimal(b, nome)  # coluna ausente: NULL
    vazio = F.col(nome).isNull() | (F.trim(F.col(nome)) == "")
    return F.when(vazio, F.lit(0).cast("decimal(18,2)")).otherwise(to_decimal(b, nome))


def transformar_silver(b: DataFrame, ano: int) -> DataFrame:
    """Recebe a bronze de UM ano e devolve a silver desse ano (mesmo número de linhas)."""
    faltando = [c for c in OBRIGATORIAS if c not in b.columns]
    if faltando:
        raise ValueError(f"Ano {ano}: colunas obrigatórias ausentes: {faltando}")

    # 1) Seleção + tipagem
    s = b.select(
        F.col("ano"),
        col_or_null(b, "municipio").alias("cod_municipio"),
        col_or_null(b, "cnae_2_0_classe").alias("cnae_classe"),
        col_or_null(b, "cbo_ocupacao_2002").alias("cbo"),
        col_or_null(b, "natureza_juridica").alias("natureza_juridica"),
        to_int(b, "sexo_trabalhador").alias("sexo"),
        to_int(b, "escolaridade_apos_2005").alias("escolaridade"),
        to_int(b, "raca_cor").alias("raca_cor"),
        to_int(b, "idade").alias("idade"),
        to_int(b, "tamanho_estabelecimento").alias("tamanho_estab"),
        to_int(b, "mes_desligamento").alias("mes_desligamento"),
        to_int(b, "motivo_desligamento").alias("motivo_desligamento"),
        to_decimal(b, "tempo_emprego", 10, 1).alias("tempo_emprego_meses"),
        (F.trim(F.col("vinculo_ativo_31_12")) == "1").alias("vinculo_ativo"),
        remuneracao(b, "vl_remun_dezembro_nom").alias("remun_dezembro_nom"),
        remuneracao(b, "vl_remun_media_nom").alias("remun_media_nom"),
        remuneracao(b, "vl_remun_dezembro_sm").alias("remun_dezembro_sm"),
        remuneracao(b, "vl_remun_media_sm").alias("remun_media_sm"),
    )

    # 2) Validação: valor fora do padrão vira NULL
    s = (
        s
        .withColumn("cod_municipio",
                    F.when(F.col("cod_municipio").rlike(r"^\d{6}$"), F.col("cod_municipio")))
        .withColumn("cnae_classe",
                    F.when(F.col("cnae_classe").rlike(r"^\d{5}$"), F.col("cnae_classe")))
        .withColumn("idade", F.when(F.col("idade").between(14, 100), F.col("idade")))
        # 0 = não desligado -> NULL (CONFIRME no dicionário)
        .withColumn("mes_desligamento",
                    F.when(F.col("mes_desligamento").between(1, 12), F.col("mes_desligamento")))
    )

    # 3) Campos derivados (substring de NULL é NULL)
    return (
        s
        .withColumn("cod_uf", F.substring("cod_municipio", 1, 2))
        .withColumn("cnae_divisao", F.substring("cnae_classe", 1, 2))
        .withColumn("desligado_no_ano", F.col("mes_desligamento").isNotNull())
    )


def construir_silver(ano: int, spark: SparkSession | None = None) -> None:
    spark = spark or get_spark("rais-silver")
    b = ler(spark, BRONZE).filter(F.col("ano") == ano)
    gravar_ano(spark, transformar_silver(b, ano), SILVER, ano)
    print(f"[silver] {ano} gravado em {SILVER}")


if __name__ == "__main__":
    import sys

    construir_silver(int(sys.argv[1]))
