"""Orquestra o pipeline: extração -> bronze -> silver (por ano) -> gold.

Origem: Guia Parte 12.2 / Aula 14.
"""
import argparse
import shutil
import time

from config.settings import ANOS, RAW
from src.bronze import construir_bronze
from src.checks import checar_silver
from src.gold import construir_gold
from src.ingest import extrair
from src.silver import construir_silver
from src.utils import get_spark

ETAPAS = ["extrair", "bronze", "silver", "gold"]


def main() -> None:
    p = argparse.ArgumentParser(description="Pipeline RAIS")
    p.add_argument("--anos", nargs="*", type=int, default=ANOS)
    p.add_argument("--etapas", nargs="*", default=ETAPAS, choices=ETAPAS)
    p.add_argument("--limpar-raw", action="store_true",
                   help="apaga staging/raw/<ano> depois da bronze")
    args = p.parse_args()

    spark = get_spark("rais-pipeline")
    inicio = time.time()

    for ano in args.anos:
        print(f"\n===== {ano} =====")
        if "extrair" in args.etapas:
            extrair(ano)
        if "bronze" in args.etapas:
            construir_bronze(ano, spark)
            if args.limpar_raw:
                shutil.rmtree(RAW / str(ano), ignore_errors=True)
        if "silver" in args.etapas:
            construir_silver(ano, spark)
            checar_silver(spark, ano)

    if "gold" in args.etapas:
        construir_gold(spark)

    print(f"\n[fim] {time.time() - inicio:,.0f}s")
    spark.stop()


if __name__ == "__main__":
    main()
