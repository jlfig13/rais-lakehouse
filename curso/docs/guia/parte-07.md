<!-- Página GERADA de docs/guia/rais-lakehouse-guia.md -->

# Parte [7](parte-07.md) — Código base: configuração e utilitários

## 7.1 Conceito: configuração por ambiente { #parte-7-1 }

Os princípios da metodologia **12-Factor App** orientam esta parte: a configuração vem de **variáveis de ambiente**, e não fica fixa no código. O mesmo código roda no seu notebook, no container e num servidor, mudando só o ambiente.

## 7.2 `config/settings.py` { #parte-7-2 }

```python
"""Configurações do projeto, lidas de variáveis de ambiente (com padrões seguros)."""
import os
from pathlib import Path

# --- Staging local (arquivos temporários) ---
STAGING = Path(os.getenv("RAIS_STAGING", "/staging"))
LANDING = STAGING / "landing"
RAW = STAGING / "raw"

# --- Lake (Delta no MinIO). Para testar sem MinIO: RAIS_LAKE=file:///tmp/lake ---
LAKE = os.getenv("RAIS_LAKE", "s3a://rais")
BRONZE = f"{LAKE}/bronze/rais_vinculos"
SILVER = f"{LAKE}/silver/rais_vinculos"
GOLD = f"{LAKE}/gold"

# --- Anos (ajuste ao último ano-base publicado) ---
ANOS = list(range(2019, 2025))
```

## 7.3 `src/utils.py` { #parte-7-3 }

```python
"""SparkSession e funções auxiliares reutilizáveis."""
import os
import re
import unicodedata

from pyspark.sql import Column, DataFrame, SparkSession
from pyspark.sql import functions as F


def get_spark(app_name: str = "rais") -> SparkSession:
    """Cria a SparkSession local com Delta e S3A (MinIO).

    Todos os recursos são ajustáveis por variável de ambiente (ver Parte 14).
    Obs.: memória e nº de threads só valem se a sessão ainda não existe.
    """
    threads = int(os.getenv("SPARK_THREADS", "4"))

    return (
        SparkSession.builder
        .master(f"local[{threads}]")
        .appName(app_name)
        # --- Delta Lake (JARs já estão na imagem) ---
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog",
                "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        # --- Recursos ---
        .config("spark.driver.memory", os.getenv("SPARK_MEM", "4g"))
        .config("spark.sql.shuffle.partitions", os.getenv("SPARK_SHUFFLE", "32"))
        .config("spark.sql.files.maxPartitionBytes", "128m")
        .config("spark.sql.adaptive.enabled", "true")
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true")
        .config("spark.local.dir", os.getenv("SPARK_TMP", "/tmp/spark"))
        .config("spark.sql.session.timeZone", "America/Sao_Paulo")
        # --- S3A -> MinIO ---
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
        .config("spark.hadoop.fs.s3a.endpoint", os.getenv("MINIO_ENDPOINT", "http://minio:9000"))
        .config("spark.hadoop.fs.s3a.access.key", os.getenv("S3_ACCESS_KEY", ""))
        .config("spark.hadoop.fs.s3a.secret.key", os.getenv("S3_SECRET_KEY", ""))
        .config("spark.hadoop.fs.s3a.path.style.access", "true")
        .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false")
        .getOrCreate()
    )


def normalize_col(name: str) -> str:
    """'Vl Remun Média (SM)' -> 'vl_remun_media_sm'."""
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-z0-9]+", "_", s.lower().strip())
    return s.strip("_")


def normalize_columns(df: DataFrame) -> DataFrame:
    """Normaliza todos os nomes de coluna; falha se dois nomes colidirem."""
    novos = [normalize_col(c) for c in df.columns]
    repetidos = {c for c in novos if novos.count(c) > 1}
    if repetidos:
        raise ValueError(f"Colunas duplicadas após normalizar: {repetidos}")
    return df.toDF(*novos)


def col_or_null(df: DataFrame, name: str) -> Column:
    """Coluna como string; NULL se não existir (o schema da RAIS muda entre anos)."""
    if name not in df.columns:
        return F.lit(None).cast("string")
    return F.trim(F.col(name))


def to_int(df: DataFrame, name: str) -> Column:
    """Texto -> int. Valor inválido ou coluna ausente vira NULL (sem quebrar o job)."""
    if name not in df.columns:
        return F.lit(None).cast("int")
    return F.expr(f"try_cast(trim(`{name}`) AS int)")


def to_decimal(df: DataFrame, name: str, precision: int = 18, scale: int = 2) -> Column:
    """'1.234,56' ou '1234,56' -> decimal. Inválido ou ausente vira NULL."""
    if name not in df.columns:
        return F.lit(None).cast(f"decimal({precision},{scale})")
    sem_milhar = f"regexp_replace(trim(`{name}`), '\\\\.', '')"
    com_ponto = f"regexp_replace({sem_milhar}, ',', '.')"
    return F.expr(f"try_cast({com_ponto} AS decimal({precision},{scale}))")
```

**Conceitos aplicados**
- **`try_cast`:** devolve `NULL` em vez de erro quando a conversão falha. Em dado público "sujo", isso evita que uma linha estragada derrube 50 milhões de linhas boas. A Parte [15](parte-15.md) mede quantos `NULL` surgiram.
- **Crases** (`` `nome` ``) protegem nomes de coluna dentro de expressões SQL.
- **Type hints** (`-> Column`) e **docstrings** documentam o contrato de cada função.
- **Por que `decimal` e não `double` para dinheiro?** `double` tem erro de arredondamento binário (`0.1 + 0.2 != 0.3`), e `decimal` é exato.

## 7.4 `src/delta_io.py` — leitura e escrita Delta { #parte-7-4 }

```python
"""Leitura e escrita Delta centralizadas (um só lugar para mudar o formato)."""
from delta.tables import DeltaTable
from pyspark.sql import DataFrame, SparkSession


def ler(spark: SparkSession, caminho: str) -> DataFrame:
    return spark.read.format("delta").load(caminho)


def gravar_ano(
    spark: SparkSession, df: DataFrame, caminho: str, ano: int, merge_schema: bool = False
) -> None:
    """Substitui ATOMICAMENTE apenas a partição do ano informado.

    - Tabela nova: grava normalmente, particionada por ano.
    - Tabela existente: usa replaceWhere -> troca só `ano = X`, sem tocar nos outros anos.
    """
    escrita = df.write.format("delta").mode("overwrite").partitionBy("ano")
    if merge_schema:
        escrita = escrita.option("mergeSchema", "true")

    if DeltaTable.isDeltaTable(spark, caminho):
        escrita = escrita.option("replaceWhere", f"ano = {ano}")
    escrita.save(caminho)


def gravar_tabela(df: DataFrame, caminho: str) -> None:
    """Recria a tabela inteira (uso na gold, que é recalculada por completo)."""
    (df.write.format("delta")
       .mode("overwrite")
       .option("overwriteSchema", "true")
       .partitionBy("ano")
       .save(caminho))
```

**Por que centralizar?** Se um dia você migrar para Iceberg, muda **um arquivo**. Isso é o princípio **DRY** (*Don't Repeat Yourself*).

**Segurança do `replaceWhere`:** se o DataFrame tiver alguma linha que **não** satisfaz `ano = X`, o Delta recusa a gravação. É uma proteção contra gravar dado no lugar errado.

## 7.5 `src/dims.py` — tabelas de domínio { #parte-7-5 }

```python
"""Dimensões pequenas que traduzem códigos em rótulos. CONFIRME os códigos no dicionário."""
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
```
> O schema em texto (`"cod_uf string, uf string"`) evita que o Spark "adivinhe" os tipos.

### Checkpoint
```python
from src.utils import normalize_col
normalize_col("Vl Remun Média (SM)")   # 'vl_remun_media_sm'
normalize_col("Vínculo Ativo 31/12")   # 'vinculo_ativo_31_12'
```
Rode também `make smoke` (Parte [4.10](parte-04.md#parte-4-10)). Depois, commit: `feat: configuração e utilitários`.

---
