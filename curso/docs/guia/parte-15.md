<!-- Página GERADA de docs/guia/rais-lakehouse-guia.md -->

# Parte [15](parte-15.md) — Qualidade, testes e CI

## 15.1 Conceito { #parte-15-1 }

| Tipo | O que verifica | Quando roda | Precisa de MinIO? |
|---|---|---|---|
| **Teste de unidade** | Uma função isolada, com dados minúsculos | A cada commit (CI) | Não |
| **Teste de fumaça** | A infraestrutura funciona de ponta a ponta | Ao subir o ambiente | Sim |
| **Checagem de dados** | O dado real faz sentido | A cada execução do pipeline | Sim |

## 15.2 Configuração: `pyproject.toml` { #parte-15-2 }

```toml
[project]
name = "rais-lakehouse"
version = "0.1.0"
description = "Lakehouse open source da RAIS com PySpark, Delta Lake e MinIO"
requires-python = ">=3.11"

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP"]   # erros, imports, bugs comuns, sintaxe moderna

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

## 15.3 Testes de unidade { #parte-15-3 }

**`tests/conftest.py`** (uma SparkSession compartilhada por todos os testes)
```python
import pytest
from pyspark.sql import SparkSession


@pytest.fixture(scope="session")
def spark():
    s = (SparkSession.builder.master("local[1]").appName("tests")
         .config("spark.sql.shuffle.partitions", "1")
         .getOrCreate())
    yield s
    s.stop()
```

**`tests/test_utils.py`**
```python
from decimal import Decimal

from src.dims import dim_uf
from src.gold import gap_sexo
from src.utils import normalize_col, to_decimal, to_int


def test_normalize_col():
    assert normalize_col("Vl Remun Média (SM)") == "vl_remun_media_sm"
    assert normalize_col("Vínculo Ativo 31/12") == "vinculo_ativo_31_12"


def test_to_decimal(spark):
    df = spark.createDataFrame([("1234,56",), ("1.234,56",), ("{ñ class}",), (None,)], ["v"])
    out = [r[0] for r in df.select(to_decimal(df, "v")).collect()]
    assert out == [Decimal("1234.56"), Decimal("1234.56"), None, None]


def test_to_int_coluna_ausente(spark):
    df = spark.createDataFrame([("1",)], ["x"])
    assert df.select(to_int(df, "nao_existe")).first()[0] is None


def test_gap_sexo(spark):
    ativos = spark.createDataFrame(
        [(2022, "26", 1, Decimal("2.00")), (2022, "26", 2, Decimal("1.50"))],
        "ano int, cod_uf string, sexo int, remun_dezembro_sm decimal(18,2)",
    )
    linha = gap_sexo(ativos, dim_uf(spark)).first()
    assert linha["uf"] == "PE"
    assert float(linha["razao_mulher_homem"]) == 0.75
```
```bash
make test
```

## 15.4 Checagens de dados { #parte-15-4 }

**`src/checks.py`**
```python
"""Checagens de qualidade sobre os dados reais. Falham alto para não esconder problema."""
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

from config.settings import BRONZE, SILVER
from src.delta_io import ler

# Limites iniciais: calibre depois de conhecer os dados
MAX_NULL_REMUN = 0.05
MAX_NULL_UF = 0.01


def checar_silver(spark: SparkSession, ano: int) -> None:
    s = ler(spark, SILVER).filter(F.col("ano") == ano)
    b = ler(spark, BRONZE).filter(F.col("ano") == ano)

    total_s, total_b = s.count(), b.count()
    assert total_s > 0, f"{ano}: silver vazia"
    assert total_s == total_b, f"{ano}: silver ({total_s}) != bronze ({total_b})"

    pct = s.select(
        F.avg(F.col("remun_dezembro_nom").isNull().cast("int")).alias("remun"),
        F.avg(F.col("cod_uf").isNull().cast("int")).alias("uf"),
    ).first()

    assert pct["remun"] <= MAX_NULL_REMUN, f"{ano}: {pct['remun']:.1%} de remuneração nula"
    assert pct["uf"] <= MAX_NULL_UF, f"{ano}: {pct['uf']:.1%} de UF nula"
    print(f"[checks] {ano}: {total_s:,} vínculos OK")
```

## 15.5 CI no GitHub Actions { #parte-15-5 }

**`.github/workflows/ci.yml`**
```yaml
name: ci

on:
  push:
    branches: [main]
  pull_request:

jobs:
  testes:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip

      - uses: actions/setup-java@v4
        with:
          distribution: temurin
          java-version: "17"

      - name: Instalar dependências
        run: pip install -r requirements.txt -r requirements-dev.txt

      - name: Lint
        run: ruff check .

      - name: Testes
        run: pytest -q
```
**Por que funciona sem MinIO:** os testes de unidade usam DataFrames em memória e não importam nada que precise de S3. Por isso as funções de transformação foram escritas como **funções puras**.

### Checkpoint
`make test` e `make lint` passam. No GitHub, a aba **Actions** fica verde após o push. Commit: `test: testes de unidade e CI`.

---
