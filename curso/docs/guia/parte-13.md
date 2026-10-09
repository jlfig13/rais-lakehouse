<!-- Página GERADA de docs/guia/rais-lakehouse-guia.md -->

# Parte [13](parte-13.md) — Delta Lake na prática

## 13.1 Conceito: o que é uma tabela Delta { #parte-13-1 }

```
silver/rais_vinculos/
├── _delta_log/
│   ├── 00000000000000000000.json   ← versão 0: "adicionou os arquivos A, B, C"
│   ├── 00000000000000000001.json   ← versão 1: "removeu B, adicionou D"
│   └── ...
├── ano=2022/
│   ├── part-0000-A.parquet
│   └── ...
```

- **Delta = arquivos Parquet + log de transações** (`_delta_log/`).
- Cada gravação vira um **commit** no log, que lista quais arquivos entram e quais saem. Ler a tabela é ler o log e depois os arquivos que ele aponta.
- **ACID:** a gravação ou acontece por inteiro ou não acontece. Se o job cair no meio, os leitores continuam vendo a versão anterior, sem dado pela metade.
- **Arquivos não são apagados na hora:** ficam "órfãos" até o `VACUUM`. É isso que permite o *time travel*.

## 13.2 Operações (notebook `05_delta.ipynb`) { #parte-13-2 }

```python
from delta.tables import DeltaTable

from config.settings import SILVER
from src.utils import get_spark

spark = get_spark("delta-ops")
dt = DeltaTable.forPath(spark, SILVER)
```

**Histórico (auditoria)**
```python
dt.history().select("version", "timestamp", "operation", "operationParameters").show(truncate=False)
```

**Time travel**
```python
v0 = spark.read.format("delta").option("versionAsOf", 0).load(SILVER)
ontem = spark.read.format("delta").option("timestampAsOf", "2026-10-08").load(SILVER)
```
Serve para reproduzir um relatório antigo, comparar antes e depois de uma correção e investigar o que mudou.

**Restaurar versão**
```python
dt.restoreToVersion(0)
```

**Compactar arquivos pequenos**
```python
dt.optimize().executeCompaction()
dt.optimize().where("ano = 2022").executeCompaction()   # só uma partição
```

**Limpar arquivos órfãos**
```python
dt.vacuum(168)   # remove arquivos sem referência há mais de 168 h (7 dias)
```
> ⚠️ Depois do `VACUUM`, as versões que dependiam dos arquivos removidos **não funcionam mais** no time travel. Não reduza o prazo abaixo de 168 h sem entender o impacto.

**Schema enforcement × evolution**
```python
from pyspark.sql import functions as F

extra = spark.read.format("delta").load(SILVER).limit(10).withColumn("coluna_nova", F.lit("x"))

# 1) Sem mergeSchema -> o Delta RECUSA (enforcement)
extra.write.format("delta").mode("append").save(SILVER)

# 2) Com mergeSchema -> o Delta EVOLUI o schema
extra.write.format("delta").mode("append").option("mergeSchema", "true").save(SILVER)
```
> Faça esse exercício numa **cópia** da tabela (ex.: `f"{LAKE}/_lab/silver"`), não na silver real.

## Exercícios
1. Reprocesse a silver de 2022 e confira em `history()` que surgiu uma versão nova **sem duplicar linhas**.
2. Compare a contagem entre a versão 0 e a atual.
3. Rode `OPTIMIZE` e compare o número de arquivos antes e depois (console do MinIO).
4. Rode o exercício de enforcement e evolution numa cópia e explique a diferença.

### Checkpoint
Você sabe explicar o que há no `_delta_log`, por que o *time travel* funciona e por que o `VACUUM` o limita.

---
