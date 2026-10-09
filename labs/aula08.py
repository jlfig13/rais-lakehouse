"""Exercícios da Aula 08 (PySpark II).

Implemente as funções marcadas com NotImplementedError e valide com:
    make check AULA=08
"""
import contextlib
import io

from pyspark.sql import DataFrame, Window  # noqa: F401  (Window: exercício 2)
from pyspark.sql import functions as F  # noqa: F401


def plano(df: DataFrame) -> str:
    """Texto do explain() (o PySpark imprime o plano; capturamos a saída)."""
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        df.explain()
    return buffer.getvalue()


def tem_shuffle(df: DataFrame) -> bool:
    """True se o plano tem Exchange que NÃO seja BroadcastExchange."""
    raise NotImplementedError("Aula 08 — exercício 1: tem_shuffle")


def maior_salario_por_uf(df: DataFrame) -> DataFrame:
    """Uma linha por UF com a pessoa de maior salário (window + row_number)."""
    raise NotImplementedError("Aula 08 — exercício 2: maior_salario_por_uf")


def com_nome_uf(df: DataFrame, ufs: DataFrame) -> DataFrame:
    """Left join com a dimensão de UFs, usando broadcast."""
    raise NotImplementedError("Aula 08 — exercício 3: com_nome_uf")
