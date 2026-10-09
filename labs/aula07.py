"""Exercícios da Aula 07 (PySpark I). Cada função recebe e devolve DataFrame.

Implemente as funções marcadas com NotImplementedError e valide com:
    make check AULA=07
"""
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F  # noqa: F401  (você vai usar nas soluções)

DADOS = [
    (1, "Ana", "F", "PE", 3200.50, "2021-03-01"),
    (2, "Bruno", "M", "PE", 4100.00, "2020-07-15"),
    (3, "Carla", "F", "SP", 5800.00, "2019-01-10"),
    (4, "Diego", "M", "SP", 2900.00, "2022-11-05"),
    (5, "Elisa", "F", "BA", 3500.00, "2021-09-20"),
    (6, "Felipe", "M", "BA", 3900.00, "2018-02-14"),
]


def exemplo(spark: SparkSession) -> DataFrame:
    return spark.createDataFrame(DADOS, ["id", "nome", "sexo", "uf", "salario", "admissao"])


def media_por_sexo(df: DataFrame) -> DataFrame:
    """Colunas: sexo, media (média salarial arredondada a 2 casas)."""
    raise NotImplementedError("Aula 07 — exercício 1: media_por_sexo")


def admissoes_por_ano(df: DataFrame) -> DataFrame:
    """Colunas: ano_admissao, qtd — ordenado por ano."""
    raise NotImplementedError("Aula 07 — exercício 2: admissoes_por_ano")


def faixa_salarial(df: DataFrame) -> DataFrame:
    """Acrescenta a coluna faixa: baixa (< 3000), media (< 4500), alta (resto)."""
    raise NotImplementedError("Aula 07 — exercício 3: faixa_salarial")
