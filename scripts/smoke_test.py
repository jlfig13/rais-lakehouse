"""Valida a infraestrutura: Spark sobe, Delta funciona e o MinIO aceita escrita/leitura.

Origem: Guia Parte 4.10 / Aula 06.
"""
from config.settings import LAKE
from src.utils import get_spark


def main() -> None:
    spark = get_spark("smoke-test")
    caminho = f"{LAKE}/_smoke/teste"

    spark.range(1000).write.format("delta").mode("overwrite").save(caminho)
    total = spark.read.format("delta").load(caminho).count()

    assert total == 1000, f"esperado 1000, obtido {total}"
    print(f"[ok] Spark {spark.version} + Delta + MinIO funcionando ({total} linhas)")
    spark.stop()


if __name__ == "__main__":
    main()
