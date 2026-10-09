"""Checks da Aula 07: exercícios de labs/aula07.py."""

from labs import aula07


def test_a07_media_por_sexo(spark):
    r = {row["sexo"]: float(row["media"]) for row in aula07.media_por_sexo(aula07.exemplo(spark)).collect()}
    assert r == {"F": 4166.83, "M": 3633.33}, f"Obtido: {r}"


def test_a07_admissoes_por_ano(spark):
    r = [(row["ano_admissao"], row["qtd"]) for row in aula07.admissoes_por_ano(aula07.exemplo(spark)).collect()]
    assert r == [(2018, 1), (2019, 1), (2020, 1), (2021, 2), (2022, 1)], f"Obtido: {r}"


def test_a07_faixa_salarial(spark):
    r = {row["nome"]: row["faixa"] for row in aula07.faixa_salarial(aula07.exemplo(spark)).collect()}
    assert r["Diego"] == "baixa" and r["Carla"] == "alta" and r["Ana"] == "media", f"Obtido: {r}"


def test_a07_sql_igual_dataframe(spark):
    df = aula07.exemplo(spark)
    df.createOrReplaceTempView("pessoas_a07")
    via_sql = spark.sql("SELECT sexo, ROUND(AVG(salario), 2) AS media FROM pessoas_a07 GROUP BY sexo")
    via_df = aula07.media_por_sexo(df)
    assert sorted(via_sql.collect()) == sorted(via_df.select("sexo", "media").collect())
