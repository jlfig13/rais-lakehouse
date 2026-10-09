<!-- Página GERADA de docs/guia/rais-lakehouse-guia.md -->

# Parte [12](parte-12.md) — Pipeline completo (2019 → hoje)

## 12.1 Conceito { #parte-12-1 }

Um pipeline executa os mesmos passos para cada ano, de forma **idempotente**: rodar duas vezes produz o mesmo resultado. Isso vem de três escolhas: arquivos já baixados são pulados, a bronze e a silver usam `replaceWhere` por ano, e a gold é recriada inteira.

**Uma `SparkSession` para tudo:** criar a sessão custa segundos e inicia uma JVM. O pipeline cria **uma** sessão e a passa para todas as etapas.

## 12.2 `src/run_pipeline.py` { #parte-12-2 }

```python
"""Orquestra o pipeline: extração -> bronze -> silver (por ano) -> gold."""
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
```

## 12.3 Execução { #parte-12-3 }

```bash
# Um ano, de ponta a ponta
make pipeline ANOS=2022

# Vários anos
make pipeline ANOS="2019 2020 2021 2022 2023 2024"

# Só refazer silver e gold (bronze já pronta)
make pipeline ANOS=2022 ETAPAS="silver gold"
```
> Antes de rodar todos os anos, coloque os `.7z` de cada ano em `staging/landing/<ano>/` e confira o espaço em disco.

### Checkpoint
```python
from pyspark.sql import functions as F
g = ler(spark, f"{GOLD}/gold_emprego_uf_ano")
g.groupBy("ano").agg(F.sum("qtd_vinculos").alias("vinculos")).orderBy("ano").show()
```
Deve aparecer um total por ano, na casa das dezenas de milhões quando todas as regiões estão carregadas. Se algum ano destoar muito dos outros, veja o [Apêndice A](apendice-a.md) (eSocial e versão parcial). Commit: `feat: pipeline completo`.

---
