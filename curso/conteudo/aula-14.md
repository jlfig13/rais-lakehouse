# Aula 14 — Pipeline completo, idempotência e operações Delta

Oct 9, 2026

Até aqui cada camada foi rodada à mão. Esta aula junta tudo num pipeline de um comando, que processa 2019 até o último ano disponível, e ensina a operar as tabelas Delta: histórico, *time travel*, restauração, compactação e limpeza.

```yaml
aula: 14
titulo: "Pipeline completo, idempotência e operações Delta"
origem: ["Guia Parte 12", "Guia Parte 13.2", "Guia Parte 15.4 (checks.py)"]
depende_de: [13]
entrega: ["src/run_pipeline.py", "src/checks.py", "notebooks/05_delta.ipynb"]
checks: [a14_varios_anos_na_gold, a14_checar_silver, a14_historico, a14_time_travel, a14_optimize]
```


## 1. Objetivos e pré-requisitos

1. Orquestrar extração, bronze, silver (por ano) e gold numa única execução.
2. Garantir idempotência e reutilizar uma SparkSession.
3. Integrar checagens de qualidade que interrompem o pipeline.
4. Usar `history`, `versionAsOf`/`timestampAsOf`, `restoreToVersion`, `OPTIMIZE` e `VACUUM`.
5. Distinguir *schema enforcement* de *evolution* na prática.

**Pré-requisitos:** Aulas 11–13 com um ano; `.7z` dos outros anos em `staging/landing/<ano>/`; espaço em disco.

## 2. Contextualização

Um pipeline é executar os mesmos passos para cada ano, de forma **idempotente**: rodar duas vezes produz o mesmo resultado (guia, Parte 12.1). Pipelines falham — falta disco, um arquivo vem corrompido, a máquina reinicia. Se reexecutar for seguro, a recuperação é só "rodar de novo"; se não for, cada falha vira uma investigação manual. As operações Delta são a rede de segurança quando algo dá errado mesmo assim.

## 3. Fundamentação teórica

### 3.1 Três fontes de idempotência (guia, Parte 12.1)

| Etapa | Mecanismo |
| --- | --- |
| Download | Arquivos já baixados são pulados |
| Bronze e silver | `replaceWhere` por ano |
| Gold | Recriada inteira |

### 3.2 Uma SparkSession para tudo

Criar a sessão custa segundos e inicia uma JVM. O pipeline cria **uma** e a passa para todas as etapas (por isso as funções aceitam `spark=None`).

### 3.3 Checagens que param o pipeline

`checar_silver` roda logo após cada silver e usa `assert`: se a contagem ou os NULL fugirem do esperado, o pipeline para **antes** de gerar uma gold errada. "Falham alto para não esconder problema" (guia, Parte 15.4).

### 3.4 Operações Delta (guia, Parte 13.2)

| Operação | Para quê | Cuidado |
| --- | --- | --- |
| `history()` | Auditoria: versão, data, operação, parâmetros | — |
| `versionAsOf` / `timestampAsOf` | Ler versão antiga: reproduzir relatório, comparar antes/depois | Só funciona se os arquivos ainda existem |
| `restoreToVersion(n)` | Voltar a tabela a uma versão | Cria uma versão nova; não apaga o histórico |
| `optimize().executeCompaction()` | Juntar arquivos pequenos | Use depois de muitas gravações |
| `vacuum(168)` | Remover arquivos sem referência há mais de 168 h | **Depois dele, versões antigas param de funcionar no time travel** |

Ordem que faz sentido em manutenção: `OPTIMIZE` (gera arquivos novos e marca os antigos como removidos) e, dias depois, `VACUUM` (apaga de fato os antigos) — mantendo uma janela para *time travel*.

## 4. Arquitetura e fluxo

```
make pipeline ANOS="2019 2020 ... 2024"
 └─ run_pipeline.py
     ├─ get_spark()  (uma vez)
     ├─ para cada ano:
     │    extrair ─▶ bronze ─▶ [--limpar-raw] ─▶ silver ─▶ checar_silver (para se falhar)
     ├─ gold (uma vez, sobre todos os anos)
     └─ spark.stop()
```

## 5. Tutorial

### Passo 1 — `src/checks.py` (guia, Parte 15.4)

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

- `F.avg(isNull().cast("int"))` é a proporção de NULL: média de zeros e uns.
- Os limites (5%, 1%) são palpites iniciais do guia; calibre-os com o seu dado e registre a decisão.
- O guia apresenta este arquivo na Parte 15; ele vem nesta aula porque o pipeline o importa.

### Passo 2 — `src/run_pipeline.py` (guia, Parte 12.2)

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

| Argumento | Efeito | Exemplo |
| --- | --- | --- |
| `--anos` | Lista de anos; padrão `ANOS` do `settings.py` | `--anos 2021 2022` |
| `--etapas` | Quais etapas rodar; `choices` rejeita nomes errados | `--etapas silver gold` |
| `--limpar-raw` | Apaga `raw/<ano>` após a bronze | — |

`nargs="*"` aceita zero ou mais valores; `action="store_true"` faz do argumento uma chave liga/desliga. `args.limpar_raw` usa `_` porque o `argparse` converte hífens.

### Passo 3 — Executar (guia, Parte 12.3)

```bash
# Um ano, de ponta a ponta
make pipeline ANOS=2022

# Vários anos
make pipeline ANOS="2019 2020 2021 2022 2023 2024"

# Só refazer silver e gold (bronze já pronta)
make pipeline ANOS=2022 ETAPAS="silver gold"
```

Antes de rodar todos os anos, coloque os `.7z` de cada ano na landing e confira o espaço em disco (guia). Se algum ano destoar muito dos outros na contagem, veja o Apêndice A (eSocial e versão parcial).

### Passo 4 — Operações Delta (guia, Parte 13.2), notebook `05_delta.ipynb`

```python
from delta.tables import DeltaTable

from config.settings import SILVER
from src.utils import get_spark

spark = get_spark("delta-ops")
dt = DeltaTable.forPath(spark, SILVER)

# Histórico (auditoria)
dt.history().select("version", "timestamp", "operation", "operationParameters").show(truncate=False)

# Time travel
v0 = spark.read.format("delta").option("versionAsOf", 0).load(SILVER)
ontem = spark.read.format("delta").option("timestampAsOf", "2026-10-08").load(SILVER)

# Restaurar uma versão (cuidado: só quando quiser de fato voltar)
# dt.restoreToVersion(0)

# Compactar arquivos pequenos
dt.optimize().executeCompaction()
dt.optimize().where("ano = 2022").executeCompaction()   # só uma partição

# Limpar arquivos órfãos
dt.vacuum(168)   # remove arquivos sem referência há mais de 168 h (7 dias)
```

Troque a data do `timestampAsOf` por uma em que a tabela já existia; uma data anterior à criação gera erro. O `restoreToVersion` está comentado de propósito.

### Passo 5 — Schema enforcement × evolution numa cópia (guia, Parte 13.2)

```python
from pyspark.sql import functions as F
from config.settings import LAKE

copia = f"{LAKE}/_lab/silver"
spark.read.format("delta").load(SILVER).limit(1000).write.format("delta").mode("overwrite").save(copia)

extra = spark.read.format("delta").load(copia).limit(10).withColumn("coluna_nova", F.lit("x"))

# 1) Sem mergeSchema -> o Delta RECUSA (enforcement)
extra.write.format("delta").mode("append").save(copia)

# 2) Com mergeSchema -> o Delta EVOLUI o schema
extra.write.format("delta").mode("append").option("mergeSchema", "true").save(copia)
```

O guia insiste: faça isso numa **cópia**, nunca na silver real.

## 6. Funcionamento e resultados esperados

| Verificação | Esperado |
| --- | --- |
| Fim do pipeline | `[fim] Ns` sem `AssertionError` |
| Total por ano na gold | Um valor por ano, na casa das dezenas de milhões com todas as regiões (guia, Parte 12) |
| Reprocessar um ano | Nova versão no histórico, mesma contagem |
| `OPTIMIZE` | Operação `OPTIMIZE` no histórico; menos arquivos |
| Passo 5, comando 1 | Erro de schema |
| Passo 5, comando 2 | Gravação aceita; `coluna_nova` aparece com NULL nas linhas antigas |

```python
# Checkpoint do guia (Parte 12.3)
from pyspark.sql import functions as F
from config.settings import GOLD
from src.delta_io import ler

g = ler(spark, f"{GOLD}/gold_emprego_uf_ano")
g.groupBy("ano").agg(F.sum("qtd_vinculos").alias("vinculos")).orderBy("ano").show()
```

## 7. Exemplos práticos

**Exemplo 1 — Recuperar de um erro.** Você mudou a regra de idade na silver, rodou 2022 e percebeu que zerou a coluna. Opções: corrigir e rodar de novo (idempotente) ou `restoreToVersion` para a versão anterior enquanto investiga. Antes do `VACUUM`, as duas funcionam.

**Exemplo 2 — Comparar antes e depois de uma correção.**

```python
antes = spark.read.format("delta").option("versionAsOf", 3).load(SILVER).filter("ano = 2022")
depois = spark.read.format("delta").load(SILVER).filter("ano = 2022")
print(antes.filter("idade IS NULL").count(), depois.filter("idade IS NULL").count())
```

(Troque `3` por uma versão real do seu histórico.)

**Exemplo 3 — Só a gold.** Mudou a definição de uma tabela gold? `make pipeline ETAPAS=gold` recria só a gold, em minutos.

**Exemplo 4 — Manifesto da execução: contagens de cada camada a cada rodada.** As checagens param o pipeline quando algo está errado *agora*; o manifesto guarda o histórico para você comparar *entre execuções*. Uma linha JSON por execução e ano, num arquivo que só cresce:

```python
import json
from datetime import datetime, timezone

from pyspark.sql import functions as F

from config.settings import BRONZE, GOLD, SILVER
from src.delta_io import ler


def manifesto(spark, ano: int) -> dict:
    bronze = ler(spark, BRONZE).filter(F.col("ano") == ano).count()
    silver = ler(spark, SILVER).filter(F.col("ano") == ano).count()
    gold = (ler(spark, f"{GOLD}/gold_emprego_uf_ano").filter(F.col("ano") == ano)
            .agg(F.sum("qtd_vinculos")).first()[0])
    return {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "ano": ano,
            "spark": spark.version, "bronze": bronze, "silver": silver,
            "gold_vinculos_ativos": int(gold or 0)}


registro = manifesto(spark, 2022)
assert registro["bronze"] == registro["silver"], registro
with open("/staging/manifesto.jsonl", "a", encoding="utf-8") as f:
    f.write(json.dumps(registro, ensure_ascii=False) + "\n")
```

Saída real sobre a amostra: `{"ano": 2022, "spark": "3.5.3", "bronze": 500, "silver": 500, "gold_vinculos_ativos": 389}`. Com o histórico, perguntas como "o total de 2022 mudou depois que reprocessamos?" (idempotência) ou "o ano novo tem um volume plausível perto dos anteriores?" passam a ter resposta em segundos.

**Checklist de idempotência e consistência do pipeline.**

| Pergunta | Como verificar | Esperado |
| --- | --- | --- |
| Reprocessar um ano duplica dados? | Rode `--anos 2022` duas vezes e compare o manifesto | Mesmas contagens |
| Reprocessar 2022 mexe em 2021? | Contagem de 2021 antes e depois | Igual |
| A gold reflete todos os anos? | `groupBy("ano")` na gold × anos da silver | Mesmos anos |
| Uma execução que falhou no meio deixou lixo? | `DESCRIBE HISTORY` (Passo 4): a escrita interrompida não aparece | Só versões completas |
| O volume do ano é plausível? | Compare com o ano anterior no manifesto | Variação explicável (ver Apêndice A: eSocial, versão parcial) |

## 8. Armadilhas, diagnóstico e soluções

| Sintoma | Causa | Solução |
| --- | --- | --- |
| `AssertionError: silver (...) != bronze (...)` | Filtro na silver | Aula 12 |
| `AssertionError: ...% de UF nula` | Arquivo NI ou regra de município | Investigar; calibrar o limite e documentar |
| `FileNotFoundError: Nenhum .7z` | Ano sem arquivo na landing | Baixar ou tirar o ano de `--anos` |
| Pipeline lento ou morre com 137 | Recursos | Aula 15; rodar um ano por vez |
| `timestampAsOf` com erro | Data antes da criação da tabela ou depois do último commit | Usar data dentro do histórico |
| Time travel falha para versão antiga | `VACUUM` já removeu os arquivos | Esperado; retenha mais tempo se precisar |
| `make pipeline` com `ETAPAS` errado | Nome fora de `choices` | Usar `extrair bronze silver gold` |

## 9. Boas práticas

1. Uma sessão por execução (guia).
2. Checagens que interrompem o pipeline (guia).
3. Rodar um ano completo antes de todos (guia).
4. `OPTIMIZE` periódico; `VACUUM` com retenção ≥ 168 h (guia).
5. Experimentos de schema só em cópias (guia).
6. Guardar o log de cada execução (ex.: `make pipeline ... | tee logs/pipeline_<data>.log`, com `logs/` no `.gitignore`).

## 10. Riscos

| Tipo | Risco | Mitigação |
| --- | --- | --- |
| Integridade | Gold gerada sobre silver errada | `checar_silver` antes da gold |
| Integridade | `VACUUM` com retenção curta apaga a possibilidade de voltar | Nunca abaixo de 168 h sem motivo |
| Integridade | `restoreToVersion` acidental | Usar só de propósito; é reversível por outro restore |
| Custo | Versões acumulando GB | `VACUUM` periódico |
| Desempenho | Todos os anos de uma vez sem recursos | Aula 15 |

## 11. Laboratório e validação na plataforma

**Contribuição ao projeto:** o lakehouse passa a ser atualizado por um comando, com qualidade verificada e operação documentada.

`labcheck/test_aula14.py` (somente leitura):

```python
"""Checks da Aula 14: pipeline com vários anos e operação Delta."""
from delta.tables import DeltaTable

from config.settings import GOLD, SILVER
from src.checks import checar_silver
from src.delta_io import ler


def test_a14_varios_anos_na_gold(spark):
    anos = [r[0] for r in ler(spark, f"{GOLD}/gold_emprego_uf_ano").select("ano").distinct().collect()]
    assert len(anos) >= 2, f"Gold só tem {sorted(anos)}. Rode o pipeline com pelo menos 2 anos."


def test_a14_checar_silver(spark, ano):
    checar_silver(spark, ano)  # lança AssertionError com o motivo se algo estiver fora


def test_a14_historico(spark):
    assert DeltaTable.forPath(spark, SILVER).history().count() >= 2, "Silver com uma única versão."


def test_a14_time_travel(spark):
    assert spark.read.format("delta").option("versionAsOf", 0).load(SILVER).limit(1).count() == 1


def test_a14_optimize(spark):
    ops = {r[0] for r in DeltaTable.forPath(spark, SILVER).history().select("operation").collect()}
    assert "OPTIMIZE" in ops, "Rode dt.optimize().executeCompaction() na silver (passo 4)."
```

- `a14_time_travel` falha se um `VACUUM` já tiver removido os arquivos da versão 0 — nesse caso, é a demonstração prática do aviso do guia; anote e siga.
- Rode com `make check AULA=14 ANO=2022`.

**Checklist manual:** \[ \] rodei o pipeline com pelo menos 2 anos · \[ \] vi `history()` e li uma versão antiga · \[ \] fiz o passo 5 numa cópia · \[ \] sei explicar por que `VACUUM` limita o time travel.

## 12. Exercícios, revisão e desafios

**Exercícios (guia, Parte 13)**

1. Reprocesse a silver de 2022 e confira em `history()` que surgiu uma versão nova sem duplicar linhas.
2. Compare a contagem entre a versão 0 e a atual.
3. Rode `OPTIMIZE` e compare o número de arquivos antes e depois (console do MinIO ou `mc ls --recursive`).
4. Rode o exercício de enforcement e evolution numa cópia e explique a diferença.

**Revisão**

1. Quais são as três fontes de idempotência do pipeline?
2. Por que `checar_silver` roda antes da gold?
3. O que `restoreToVersion` faz com o histórico?
4. Por que não `vacuum(0)`?

**Respostas sugeridas:** (1) pular downloads existentes, `replaceWhere` por ano, gold recriada; (2) para não publicar gold sobre silver errada; (3) cria uma versão nova igual à antiga, mantendo o histórico; (4) apagaria imediatamente todos os arquivos antigos, eliminando o time travel e arriscando leitores em andamento.

**Desafio:** registre o tempo de cada etapa por ano (bronze, silver, checks) num CSV em `docs/` e identifique a etapa mais cara — entrada para a Aula 15.

## 13. Referências cruzadas

| Tema | Onde |
| --- | --- |
| Idempotência (conceito) | Aula 01 |
| `ANOS`, `RAW` | Aula 05 |
| `_delta_log`, `replaceWhere`, `mergeSchema` | Aula 10 |
| Etapas individuais | Aulas 11–13 |
| Recursos e tempo de execução | Aula 15 |
| Testes e CI | Aula 16 |
| Comandos Delta | Apêndice D |
