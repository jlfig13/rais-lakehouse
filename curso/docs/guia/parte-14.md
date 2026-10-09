<!-- Página GERADA de docs/guia/rais-lakehouse-guia.md -->

# Parte [14](parte-14.md) — Tuning: threads, memória e partições

## 14.1 Conceito { #parte-14-1 }

Em modo `local`, **tudo roda numa única JVM** dentro do container `spark`. Cada **thread** executa uma **tarefa** (*task*) por vez, e todas **dividem a mesma memória**.

> **Mais threads = mais paralelismo, mas menos memória por tarefa.**

Existem **duas camadas de limite**, e uma precisa caber na outra:

```
┌───────────────────── Host (sua máquina) ─────────────────────┐
│  ┌───────────── Container spark (cpus, mem_limit) ─────────┐ │
│  │  ┌────────── JVM do Spark (SPARK_MEM) ────────────────┐ │ │
│  │  │  thread 1 │ thread 2 │ ... │ thread N (SPARK_THREADS) │ │ │
│  │  └──────────────────────────────────────────────────────┘ │ │
│  │  + Python, Jupyter, overhead da JVM                      │ │
│  └──────────────────────────────────────────────────────────┘ │
│  + sistema operacional, MinIO, outros programas               │
└───────────────────────────────────────────────────────────────┘
```

**Regras de encaixe**
- `SPARK_THREADS ≤ CONTAINER_CPUS`
- `SPARK_MEM ≈ 65–75% de CONTAINER_MEM` (o resto vai para overhead da JVM, Python e Jupyter)
- `CONTAINER_MEM + memória do MinIO + sistema < RAM do host`
- Se a JVM passar do `mem_limit`, o Docker **mata o container** (erro *OOMKilled*, código 137).

## 14.2 Os botões { #parte-14-2 }

| Botão | Onde | Como pensar |
|---|---|---|
| Threads | `SPARK_THREADS` → `local[N]` | Núcleos do container. Mire em 2–4 GB de `SPARK_MEM` por thread |
| Memória | `SPARK_MEM` → `spark.driver.memory` | 65–75% de `CONTAINER_MEM` |
| Partições de shuffle | `SPARK_SHUFFLE` → `spark.sql.shuffle.partitions` | 100–200 MB por partição e ≥ 2–4× o nº de threads |
| Partições de leitura | `spark.sql.files.maxPartitionBytes` | Padrão 128 MB; aumentar gera menos tarefas, maiores |
| Disco de spill | `spark.local.dir` → volume `spark-tmp` | Precisa de espaço: é para lá que vai o que não cabe na memória |
| AQE | `spark.sql.adaptive.*` | Ligado: o Spark junta partições pequenas sozinho (só reduz, não aumenta) |

## 14.3 Pontos de partida { #parte-14-3 }

| RAM do host / núcleos | `CONTAINER_MEM` | `CONTAINER_CPUS` | `SPARK_MEM` | `SPARK_THREADS` | `SPARK_SHUFFLE` |
|---|---|---|---|---|---|
| 8 GB / 4 | 5g | 3 | 3g | 2 | 16 |
| 16 GB / 8 | 11g | 6 | 8g | 4 | 32 |
| 32 GB / 8–12 | 24g | 8 | 18g | 6 | 48 |
| 64 GB / 16 | 48g | 14 | 36g | 12 | 96 |

São **pontos de partida**, não verdades. Ajuste medindo (14.5).

## 14.4 Como calcular o número de partições { #parte-14-4 }

1. Descubra o volume do shuffle: rode uma vez e veja *Stages → Shuffle Write* na Spark UI.
2. `partições ≈ volume_do_shuffle / 128 MB`
3. Arredonde para um **múltiplo do número de threads**, para que todas fiquem ocupadas até a última "onda" de tarefas.

Exemplo: shuffle de 6 GB e 4 threads → 6144 / 128 = 48 partições (48 é múltiplo de 4).

## 14.5 Método de ajuste { #parte-14-5 }

1. Rode a silver de um ano com a configuração inicial e anote o tempo.
2. Abra a **Spark UI** (http://localhost:4040; num segundo processo simultâneo, 4041), aba **Stages**.
3. Leia os sinais:

| O que você vê | Diagnóstico | O que fazer |
|---|---|---|
| *Spill (disk)* alto | Falta memória por tarefa | Menos threads ou mais `SPARK_MEM` |
| Milhares de tarefas de poucos KB | Partições demais | Reduzir `SPARK_SHUFFLE` |
| Poucas tarefas grandes e lentas | Partições de menos | Aumentar `SPARK_SHUFFLE` |
| Uma tarefa muito mais lenta que as outras | *Data skew* (desbalanceamento) | Rever a chave do `groupBy`/`join`; `repartition` por outra coluna |
| `OutOfMemoryError` no log | Heap da JVM insuficiente | Menos threads, mais `SPARK_MEM`, menos dados por vez |
| Container reinicia / código 137 | `mem_limit` estourado | Reduzir `SPARK_MEM` ou aumentar `CONTAINER_MEM` |
| CPU baixa o tempo todo | Gargalo de E/S (MinIO/disco) | Mais partições de leitura; verificar o disco do MinIO |

4. Mude **uma variável por vez**, rode de novo e compare.

**Monitorar o container em tempo real:**
```bash
docker stats rais-lakehouse-spark-1
```

## 14.6 Benchmark { #parte-14-6 }

**`scripts/bench.sh`** (rode **dentro** do container: `make shell`)
```bash
#!/usr/bin/env bash
# Mede o tempo da silver variando threads e partições de shuffle.
set -euo pipefail
ANO="${1:-2022}"

printf "threads,shuffle,segundos\n"
for t in 2 4 6; do
  for p in 16 32 64; do
    inicio=$(date +%s)
    SPARK_THREADS=$t SPARK_SHUFFLE=$p \
      python -m src.run_pipeline --anos "$ANO" --etapas silver > /dev/null 2>&1
    printf "%s,%s,%s\n" "$t" "$p" "$(( $(date +%s) - inicio ))"
  done
done
```
```bash
bash scripts/bench.sh 2022 | tee docs/benchmark.csv
```
Responda em `docs/decisoes.md`: (a) o ganho com mais threads é linear? (b) em que ponto aparece *spill*? (c) qual configuração vira o padrão no `.env` e por quê?

## 14.7 Controle dentro do código { #parte-14-7 }

```python
df.rdd.getNumPartitions()                       # quantas partições agora
df.repartition(48, "cod_uf")                    # redistribui por chave (com shuffle)
df.coalesce(4)                                  # reduz partições sem shuffle completo
spark.conf.set("spark.sql.shuffle.partitions", "64")   # muda em execução
```
As configurações de **SQL** mudam em execução. As de **memória** e de `master` só valem ao criar a sessão (em notebook, reinicie o kernel).

**Quando virar cluster:** num Spark standalone on-premises, os equivalentes são `spark.executor.instances`, `spark.executor.cores`, `spark.executor.memory` e `spark.cores.max`. A lógica não muda: núcleos por executor × memória por núcleo.

---
