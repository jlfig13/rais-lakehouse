# Aula 10 — Delta Lake e código base: transações, utilitários e dimensões

Oct 9, 2026

Esta aula entrega as três peças de código que bronze, silver e gold reutilizam — utilitários de conversão, a camada de leitura e escrita Delta e as dimensões — e explica como o Delta garante que reprocessar um ano não corrompe nem duplica dados.

```yaml
aula: 10
titulo: "Delta Lake e código base: transações, utilitários e dimensões"
origem: ["Guia Parte 7.3", "Guia Parte 7.4", "Guia Parte 7.5", "Guia Parte 13.1", "Guia Parte 15.3"]
depende_de: [6, 8]
entrega: ["src/utils.py (completo)", "src/delta_io.py", "src/dims.py", "tests/conftest.py", "tests/test_utils.py"]
checks: [a10_testes_utils, a10_gravar_ano_idempotente, a10_replacewhere_protege, a10_dims_tipos]
```


## 1. Objetivos e pré-requisitos

1. Explicar o que é uma tabela Delta e o papel do `_delta_log/`.
2. Explicar ACID, `replaceWhere`, *schema enforcement* e *schema evolution*.
3. Escrever os utilitários de normalização e conversão tolerante (`try_cast`).
4. Centralizar leitura e escrita Delta em `src/delta_io.py`.
5. Criar dimensões com schema explícito.

**Pré-requisitos:** Aula 06 (`get_spark`), Aula 08 (partições), Aula 09 (formato da RAIS).

## 2. Contextualização

Gravar Parquet num diretório funciona até o primeiro problema: um job que cai no meio deixa arquivos pela metade visíveis; um reprocessamento com `append` duplica um ano; um arquivo com colunas erradas entra sem aviso. O Delta resolve os três (ADR-004). E dado público sujo exige conversões que não derrubem 50 milhões de linhas por causa de uma (guia, Parte 7.3).

## 3. Fundamentação teórica

### 3.1 O que é uma tabela Delta (guia, Parte 13.1)

```
silver/rais_vinculos/
├── _delta_log/
│   ├── 00000000000000000000.json   ← versão 0: "adicionou os arquivos A, B, C"
│   ├── 00000000000000000001.json   ← versão 1: "removeu B, adicionou D"
│   └── ..
├── ano=2022/
│   ├── part-0000-A.parquet
│   └── ..
```

- **Delta = arquivos Parquet + log de transações** (`_delta_log/`).
- Cada gravação vira um **commit** no log, listando quais arquivos entram e quais saem. Ler a tabela é ler o log e depois os arquivos que ele aponta.
- **ACID:** a gravação acontece por inteiro ou não acontece. Se o job cair no meio, os leitores continuam vendo a versão anterior.
- **Arquivos não são apagados na hora:** ficam "órfãos" até o `VACUUM`. É isso que permite o *time travel* (Aula 14).

Por isso arquivos Parquet "soltos" na pasta não fazem parte da tabela se o log não os listar — e por isso nunca se deve apagar ou copiar arquivos de uma tabela Delta à mão.

### 3.2 `replaceWhere`: sobrescrever só um ano, atomicamente

Com `mode("overwrite").option("replaceWhere", "ano = 2022")`, o Delta troca só os dados que satisfazem a condição, num único commit. Se o DataFrame tiver alguma linha que **não** satisfaz `ano = X`, o Delta recusa a gravação — proteção contra gravar dado no lugar errado (guia, Parte 7.4). É a base da idempotência por ano (Aula 01).

### 3.3 Schema enforcement × evolution

| Opção | Comportamento | Uso no curso |
| --- | --- | --- |
| (padrão) enforcement | Recusa gravação com coluna nova ou tipo incompatível | Silver |
| `mergeSchema=true` | Acrescenta colunas novas à tabela; anos antigos ficam com NULL nelas | Bronze (o schema da RAIS muda entre anos) |
| `overwriteSchema=true` | Substitui o schema inteiro num overwrite | Gold (recriada por completo) |

### 3.4 Conversão tolerante: `try_cast`

`try_cast` devolve `NULL` em vez de erro quando a conversão falha. Em dado público "sujo", evita que uma linha estragada derrube milhões de linhas boas; a Aula 16 mede quantos `NULL` surgiram (guia, Parte 7.3). O preço: erros viram NULL em silêncio. Por isso todo `try_cast` precisa de uma checagem de quantidade de NULL depois.

### 3.5 `decimal` para dinheiro

`double` tem erro de arredondamento binário (`0.1 + 0.2 != 0.3`); `decimal` é exato (guia, Parte 7.3). Somar milhões de remunerações em `double` acumula erro.

### 3.6 DRY: um módulo para o formato de tabela

Se um dia o projeto migrar para Iceberg, muda **um arquivo** (`delta_io.py`) — princípio *Don't Repeat Yourself* (guia, Parte 7.4).

## 4. Arquitetura e fluxo

```
                 src/utils.py                    src/delta_io.py              src/dims.py
 bronze.py ──▶  normalize_columns            ──▶ gravar_ano(merge_schema=True)
 silver.py ──▶  col_or_null, to_int,         ──▶ ler / gravar_ano
                 to_decimal
 gold.py   ──▶                              ──▶ ler / gravar_tabela         ◀── dim_uf, dim_escolaridade
```

## 5. Tutorial

### Passo 1 — Completar `src/utils.py` (guia, Parte 7.3)

Mantenha o `get_spark` da Aula 06 e acrescente os imports e funções abaixo:

```python
import re
import unicodedata

from pyspark.sql import Column, DataFrame
from pyspark.sql import functions as F


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

| Função | Entrada | Saída | Erro possível |
| --- | --- | --- | --- |
| `normalize_col` | nome de coluna | nome normalizado | — |
| `normalize_columns` | DataFrame | DataFrame com nomes normalizados | `ValueError` se dois nomes colidirem |
| `col_or_null` | DataFrame, nome | `Column` string (com `trim`) ou NULL | — |
| `to_int` | DataFrame, nome | `Column` int ou NULL | — (inválido vira NULL) |
| `to_decimal` | DataFrame, nome, precisão, escala | `Column` decimal ou NULL | — |

**Detalhes que importam:**

- `NFKD` + `encode("ascii", "ignore")` separa o acento da letra e descarta o acento.
- As **crases** (`` `nome` ``) protegem nomes de coluna dentro de expressões SQL.
- **O escape do ponto em `to_decimal`:** no código Python há quatro barras (`'\\\\.'`); o Python entrega duas ao SQL, que entrega `\.` à expressão regular — um ponto literal. Com menos barras, o ponto viraria "qualquer caractere" e apagaria todos os dígitos.
- `to_decimal` remove o ponto de milhar e troca a vírgula por ponto, nessa ordem.

### Passo 2 — `src/delta_io.py` (guia, Parte 7.4)

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

**Por que o `if isDeltaTable`:** na primeira gravação não há tabela, então o overwrite simples a cria; nas seguintes, `replaceWhere` garante que só o ano informado muda.

### Passo 3 — `src/dims.py` (guia, Parte 7.5)

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

O schema em texto (`"cod_uf string, uf string"`) evita que o Spark "adivinhe" os tipos. `cod_uf` é string (vem do texto do município); `sexo` e `escolaridade` são int (a silver converte esses códigos com `to_int`, Aula 12).

### Passo 4 — Testes de unidade (guia, Parte 15.3)

`tests/conftest.py`:

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

`tests/test_utils.py` (a parte dos utilitários; o teste da gold entra na Aula 13):

```python
from decimal import Decimal

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
```

```bash
make test
```

Esta SparkSession de teste **não** usa `get_spark`: testes de unidade não precisam de MinIO nem Delta, e assim rodam no CI do GitHub (Aula 16).

## 6. Funcionamento e resultados esperados

| Item | Esperado |
| --- | --- |
| `make test` | 3 testes passando |
| `gravar_ano` duas vezes no mesmo ano | Contagem igual; duas versões no histórico |
| `gravar_ano(ano=2022)` com linhas de 2023 | Erro do Delta, nada gravado |
| Dimensões | `printSchema` com `cod_uf: string`, `sexo: integer` |

## 7. Exemplos práticos

**Exemplo 1 — Idempotência na prática.** Num notebook:

```python
from pyspark.sql import functions as F
from config.settings import LAKE
from src.delta_io import gravar_ano, ler
from src.utils import get_spark

spark = get_spark()
lab = f"{LAKE}/_lab/aula10"
df = spark.range(100).withColumn("ano", F.lit(2022))

gravar_ano(spark, df, lab, 2022)
gravar_ano(spark, df, lab, 2022)            # de novo
print(ler(spark, lab).count())              # 100, não 200
```

**Exemplo 2 — A proteção do `replaceWhere`.** Tente `gravar_ano(spark, df.withColumn("ano", F.lit(2023)), lab, 2022)`: o Delta recusa, porque há linhas fora de `ano = 2022`. Leia a mensagem de erro.

**Exemplo 3 — Ver o log.** Com o `mc` (Aula 04): `mc ls app/rais/_lab/aula10/_delta_log/` mostra um `.json` por versão; `mc cat` de um deles mostra as ações `add` e `remove`.

## 8. Armadilhas, diagnóstico e soluções

| Sintoma | Causa | Solução |
| --- | --- | --- |
| `ValueError: Colunas duplicadas após normalizar` | Dois cabeçalhos que viram o mesmo nome | Renomear um deles antes de normalizar e documentar |
| `to_decimal` devolve valores errados (dígitos sumindo) | Escape do ponto errado | Conferir as quatro barras |
| Erro de schema ao gravar | Enforcement do Delta | Corrigir o DataFrame, ou `mergeSchema` só onde a evolução é desejada |
| Erro de `replaceWhere` | Linhas fora do ano | Filtrar o DataFrame pelo ano antes de gravar |
| Ano duplicado | Uso de `append` | Sempre `gravar_ano` |
| Arquivos apagados à mão quebraram a tabela | Log aponta para arquivos inexistentes | Nunca mexer em arquivos Delta fora do Spark; restaurar versão (Aula 14) |

## 9. Boas práticas

1. Toda E/S de tabela passa por `delta_io.py` (guia).
2. `try_cast` sempre seguido de checagem de NULL (Aula 16).
3. `decimal` para valores monetários (guia).
4. Schema explícito em dimensões (guia).
5. `mergeSchema` só na bronze; silver protegida por enforcement.
6. Type hints e docstrings documentam o contrato de cada função (guia, Parte 7.3).

## 10. Riscos

| Tipo | Risco | Mitigação |
| --- | --- | --- |
| Integridade | Dados parciais visíveis | Commits atômicos do Delta |
| Integridade | Reprocessamento duplica | `replaceWhere` |
| Integridade | Erros convertidos em NULL silenciosamente | Checagem de NULL (Aula 16) |
| Integridade | Gravar ano no lugar errado | Recusa do `replaceWhere` |
| Custo | Versões antigas ocupando espaço | `VACUUM` (Aula 14) |

## 11. Laboratório e validação na plataforma

**Contribuição ao projeto:** os três módulos são importados por todas as camadas.

`labcheck/test_aula10.py`. Ele grava apenas na área de teste `_lab/aula10`, nunca nas camadas do projeto.

```python
"""Checks da Aula 10."""
import subprocess

import pytest
from delta.tables import DeltaTable
from pyspark.sql import functions as F

from config.settings import LAKE
from src.delta_io import gravar_ano, ler
from src.dims import dim_escolaridade, dim_sexo, dim_uf

LAB = f"{LAKE}/_lab/aula10"


def test_a10_testes_utils():
    r = subprocess.run(["pytest", "-q", "tests/test_utils.py"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout[-500:]


def test_a10_gravar_ano_idempotente(spark):
    df = spark.range(100).withColumn("ano", F.lit(2022))
    gravar_ano(spark, df, LAB, 2022)
    gravar_ano(spark, df, LAB, 2022)
    assert ler(spark, LAB).filter("ano = 2022").count() == 100
    assert DeltaTable.forPath(spark, LAB).history().count() >= 2


def test_a10_replacewhere_protege(spark):
    errado = spark.range(5).withColumn("ano", F.lit(2023))
    gravar_ano(spark, spark.range(1).withColumn("ano", F.lit(2022)), LAB, 2022)  # garante tabela
    with pytest.raises(Exception):
        gravar_ano(spark, errado, LAB, 2022)


def test_a10_dims_tipos(spark):
    assert dict(dim_uf(spark).dtypes) == {"cod_uf": "string", "uf": "string"}
    assert dict(dim_sexo(spark).dtypes)["sexo"] == "int"
    assert dim_escolaridade(spark).count() == 11
```

- `pytest.raises(Exception)` passa se o bloco lançar erro — aqui, o erro **é** o comportamento correto.
- Rode com `make check AULA=10`.

**Checklist manual:** \[ \] abri um JSON do `_delta_log` e identifiquei `add`/`remove` · \[ \] sei explicar as quatro barras do `to_decimal` · \[ \] sei quando usar `mergeSchema` e quando não.

## 12. Exercícios, revisão e desafios

**Exercícios**

1. Acrescente a `test_utils.py` um caso para `normalize_columns` que deve lançar `ValueError` (dica: colunas `"A b"` e `"a_b"`).
2. Grave no `_lab` um DataFrame com uma coluna extra usando `gravar_ano` sem e com `merge_schema=True`. Explique a diferença.

**Revisão**

1. O que acontece com os leitores se um job Delta cair no meio da escrita?
2. Por que a bronze usa `mergeSchema` e a silver não?
3. Qual o risco do `try_cast` e como compensá-lo?
4. Por que não apagar arquivos de uma tabela Delta à mão?

**Respostas sugeridas:** (1) continuam vendo a versão anterior; (2) a bronze precisa aceitar colunas novas de anos novos; a silver tem contrato fixo; (3) erros viram NULL em silêncio — medir NULL depois; (4) o log continuaria apontando para eles e a tabela quebraria.

**Desafio:** escreva `gravar_ano` para Iceberg em pseudocódigo e liste o que mais mudaria no projeto (configuração do catálogo, `get_spark`).

## 13. Referências cruzadas

| Tema | Onde |
| --- | --- |
| ADR-004 (Delta) | Aula 01 |
| Partições e pruning | Aula 08 |
| Formato da RAIS e códigos de ignorado | Aula 09 |
| Uso na bronze, silver e gold | Aulas 11, 12 e 13 |
| Histórico, time travel, OPTIMIZE, VACUUM | Aula 14 |
| Checagem de NULL e CI | Aula 16 |
