"""Dimensões pequenas que traduzem códigos em rótulos. CONFIRME os códigos no dicionário.

Origem: Guia Parte 7.5 / Aula 10.
"""
from pyspark.sql import DataFrame, SparkSession

UFS = [
    ("11", "RO"), ("12", "AC"), ("13", "AM"), ("14", "RR"), ("15", "PA"), ("16", "AP"),
    ("17", "TO"), ("21", "MA"), ("22", "PI"), ("23", "CE"), ("24", "RN"), ("25", "PB"),
    ("26", "PE"), ("27", "AL"), ("28", "SE"), ("29", "BA"), ("31", "MG"), ("32", "ES"),
    ("33", "RJ"), ("35", "SP"), ("41", "PR"), ("42", "SC"), ("43", "RS"), ("50", "MS"),
    ("51", "MT"), ("52", "GO"), ("53", "DF"),
]

SEXO = [(1, "Masculino"), (2, "Feminino")]

ESCOLARIDADE = [
    (1, "Analfabeto"), (2, "Até 5ª incompleto"), (3, "5ª completo fundamental"),
    (4, "6ª a 9ª fundamental"), (5, "Fundamental completo"), (6, "Médio incompleto"),
    (7, "Médio completo"), (8, "Superior incompleto"), (9, "Superior completo"),
    (10, "Mestrado"), (11, "Doutorado"),
]


def dim_uf(spark: SparkSession) -> DataFrame:
    return spark.createDataFrame(UFS, "cod_uf string, uf string")


def dim_sexo(spark: SparkSession) -> DataFrame:
    return spark.createDataFrame(SEXO, "sexo int, sexo_desc string")


def dim_escolaridade(spark: SparkSession) -> DataFrame:
    return spark.createDataFrame(ESCOLARIDADE, "escolaridade int, escolaridade_desc string")
