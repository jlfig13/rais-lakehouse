<!-- Página GERADA de docs/guia/rais-lakehouse-guia.md -->

# Parte [9](parte-09.md) — Bronze

## 9.1 Conceito { #parte-9-1 }

A bronze é a **cópia fiel e eficiente** da origem:
- **Tudo como `string`**: mudanças de formato entre anos não quebram a carga, e tipar é tarefa da silver.
- **Nomes normalizados**: Parquet e Delta não lidam bem com espaços e acentos em nomes de coluna.
- **Particionada por `ano`** e gravada com `replaceWhere`: reprocessar 2022 não toca em 2021.
- **`mergeSchema=True`**: se um ano novo trouxer uma coluna nova, o Delta a **adiciona** à tabela, e os anos antigos ficam com `NULL` nela. Sem essa opção, o Delta **recusa** a gravação (*schema enforcement*).
- **Rastreabilidade**: guardamos o arquivo de origem de cada linha.

## 9.2 `src/bronze.py` { #parte-9-2 }

```python
"""Bronze: CSV/TXT da RAIS -> Delta, fiel à origem."""
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

from config.settings import BRONZE, RAW
from src.delta_io import gravar_ano
from src.utils import get_spark, normalize_columns


def construir_bronze(ano: int, spark: SparkSession | None = None) -> None:
    spark = spark or get_spark("rais-bronze")

    df = (
        spark.read
        .option("header", True)
        .option("sep", ";")
        .option("encoding", "ISO-8859-1")
        .option("inferSchema", False)          # tudo string, de propósito
        .csv(str(RAW / str(ano) / "*.txt"))
    )

    # Rastreabilidade: nome do arquivo de origem (antes de renomear as colunas)
    df = df.withColumn("arquivo_origem", F.col("_metadata.file_name"))
    df = normalize_columns(df).withColumn("ano", F.lit(ano).cast("int"))

    gravar_ano(spark, df, BRONZE, ano, merge_schema=True)
    print(f"[bronze] {ano} gravado em {BRONZE}")


if __name__ == "__main__":
    import sys

    construir_bronze(int(sys.argv[1]))
```
```bash
docker compose exec spark python -m src.bronze 2022
```

## 9.3 Explorando (notebook `02_bronze.ipynb`) { #parte-9-3 }

```python
from config.settings import BRONZE
from src.delta_io import ler
from src.utils import get_spark

spark = get_spark()
b = ler(spark, BRONZE)

b.printSchema()                                    # tudo string
print(f"{b.count():,} vínculos")
b.select("municipio", "sexo_trabalhador", "vl_remun_media_nom").show(10)
```

## Exercícios
1. Quantos vínculos e quantas colunas há?
2. Liste os valores distintos de `sexo_trabalhador` e `vinculo_ativo_31_12`.
3. Confira se as colunas da Parte [6](parte-06.md) existem: `set(esperadas) - set(b.columns)`.
4. Compare o tamanho do `.txt` com o da bronze (console do MinIO). Qual é a taxa de compressão?
5. Rode a bronze de 2022 **duas vezes** e confirme que a contagem **não dobrou** (idempotência).

### Checkpoint
A pasta `bronze/rais_vinculos/ano=2022/` existe no MinIO, com `_delta_log/`. Depois disso, você pode apagar `staging/raw/2022/`, porque o `.7z` em `landing` continua como fonte. Commit: `feat: camada bronze`.

---
