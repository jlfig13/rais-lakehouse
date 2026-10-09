---
aula: 15
titulo: "Tuning: threads, memória, partições e Spark UI"
origem: ['Guia Parte 14']
depende_de: [14]
checks: ['a15_memoria_cabe_no_container', 'a15_threads_explicitas', 'a15_benchmark_registrado', 'a15_adr_tuning']
---

# Aula 15 — Tuning: threads, memória, partições e Spark UI

<!-- Página GERADA por scripts/gerar_curso.py. Edite aulas.yml e curso/conteudo/. -->

<div class="rl-aula" data-aula="15" data-onde="container" data-lab=""></div>

| | |
| --- | --- |
| Origem no guia | Guia Parte [14](../guia/parte-14.md) |
| Depende de | [Aula 14](aula-14.md) |
| Entregas | `scripts/bench.sh`, `docs/benchmark.csv`, `ADR de configuração padrão em docs/decisoes.md`, `.env ajustado` |
| Onde os checks rodam | Container spark |

O mesmo pipeline pode levar minutos ou horas, ou morrer por falta de memória, dependendo de quatro ou cinco configurações. Esta aula ensina a escolhê-las por medição, e não por palpite, e a registrar a escolha.

**Convenção:** <span class="rl-complemento">Complemento didático</span> marca o que não está no guia original.

## 1. Objetivos e pré-requisitos

1. Explicar como threads, memória e partições interagem em modo local.
2. Encaixar a configuração do Spark nos limites do container e do host.
3. Calcular um número inicial de partições de shuffle.
4. Diagnosticar pela Spark UI: spill, excesso ou falta de partições, skew.
5. Fazer um benchmark e registrar a configuração padrão.

**Pré-requisitos:** Aula 14 (pipeline rodando; bronze de pelo menos um ano), Aula 08 (shuffle e `explain`).

## 2. Contextualização

Em modo `local`, **tudo roda numa única JVM** dentro do container `spark`. Cada thread executa uma tarefa por vez, e todas **dividem a mesma memória** (guia, Parte [14.1](../guia/parte-14.md#parte-14-1)):

> **Mais threads = mais paralelismo, mas menos memória por tarefa.**

<span class="rl-complemento">Complemento didático</span> Por isso "usar todos os núcleos" (`local[*]`) nem sempre é mais rápido: com pouca memória por tarefa, o Spark despeja dados em disco (*spill*) e fica mais lento — ou o container morre.

## 3. Fundamentação teórica (guia, Parte [14](../guia/parte-14.md))

### 3.1 Duas camadas de limite

```
┌───────────────────── Host (sua máquina) ─────────────────────┐
│  ┌───────────── Container spark (cpus, mem_limit) ─────────┐ │
│  │  ┌────────── JVM do Spark (SPARK_MEM) ─────────────┐   │ │
│  │  │  thread 1 │ thread 2 │ ... │ thread N (SPARK_THREADS) │   │ │
│  │  └───────────────────────────────────────────┘   │ │
│  │  + Python, Jupyter, overhead da JVM                          │ │
│  └──────────────────────────────────────────────────────────┘ │
│  + sistema operacional, MinIO, outros programas                  │
└─────────────────────────────────────────────────────────────┘
```

**Regras de encaixe:**

- `SPARK_THREADS ≤ CONTAINER_CPUS`
- `SPARK_MEM ≈ 65–75% de CONTAINER_MEM` (o resto vai para overhead da JVM, Python e Jupyter)
- `CONTAINER_MEM + memória do MinIO + sistema < RAM do host`
- Se a JVM passar do `mem_limit`, o Docker **mata o container** (*OOMKilled*, código 137).

### 3.2 Os botões

| Botão | Onde | Como pensar |
| --- | --- | --- |
| Threads | `SPARK_THREADS` → `local[N]` | Núcleos do container. Mire em 2–4 GB de `SPARK_MEM` por thread |
| Memória | `SPARK_MEM` → `spark.driver.memory` | 65–75% de `CONTAINER_MEM` |
| Partições de shuffle | `SPARK_SHUFFLE` → `spark.sql.shuffle.partitions` | 100–200 MB por partição e ≥ 2–4× o nº de threads |
| Partições de leitura | `spark.sql.files.maxPartitionBytes` | Padrão 128 MB; aumentar gera menos tarefas, maiores |
| Disco de spill | `spark.local.dir` → volume `spark-tmp` | Precisa de espaço |
| AQE | `spark.sql.adaptive.*` | Junta partições pequenas sozinho (só reduz, não aumenta) |

### 3.3 Pontos de partida (guia, Parte [14.3](../guia/parte-14.md#parte-14-3))

| RAM do host / núcleos | `CONTAINER_MEM` | `CONTAINER_CPUS` | `SPARK_MEM` | `SPARK_THREADS` | `SPARK_SHUFFLE` |
| --- | --- | --- | --- | --- | --- |
| 8 GB / 4 | 5g | 3 | 3g | 2 | 16 |
| 16 GB / 8 | 11g | 6 | 8g | 4 | 32 |
| 32 GB / 8–12 | 24g | 8 | 18g | 6 | 48 |
| 64 GB / 16 | 48g | 14 | 36g | 12 | 96 |

São **pontos de partida**, não verdades.

### 3.4 Calcular o número de partições (guia, Parte [14.4](../guia/parte-14.md#parte-14-4))

1. Descubra o volume do shuffle: rode uma vez e veja *Stages → Shuffle Write* na Spark UI.
2. `partições ≈ volume_do_shuffle / 128 MB`.
3. Arredonde para um **múltiplo do número de threads**, para que todas fiquem ocupadas até a última "onda" de tarefas.

Exemplo: shuffle de 6 GB e 4 threads → 6144 / 128 = 48 partições (múltiplo de 4).

### 3.5 Skew, spill e cache

- **Spill:** dados despejados em disco quando não cabem na memória.
- **Data skew:** dados concentrados em poucas chaves, gerando tarefas desbalanceadas — uma tarefa muito mais lenta que as outras.
- **Cache:** <span class="rl-complemento">Complemento didático</span> `df.cache()` guarda um DataFrame reutilizado várias vezes (como `ativos` na gold) para não recalculá-lo a cada ação (Aula 08, lazy evaluation). Consome memória; libere com `unpersist()`. O guia não o usa; experimente no desafio 2.

## 4. Arquitetura e fluxo do ajuste

```
 configuração inicial (tabela 3.3)
   │
   ▼
 rodar a silver de 1 ano ──▶ anotar tempo
   │
   ▼
 Spark UI (localhost:4040 ou 4041) → aba Stages
   │   spill? muitas tarefas minúsculas? poucas enormes? uma lenta?
   ▼
 mudar UMA variável ──▶ rodar de novo ──▶ comparar
   │
   ▼
 benchmark → docs/benchmark.csv → ADR → .env
```

## 5. Tutorial

### Passo 1 — Encaixar a configuração

Veja a RAM e os núcleos do host (`free -g` e `nproc` no Linux/WSL; no Windows, o limite do WSL em `.wslconfig`). Escolha a linha da tabela 3.3 e ajuste o `.env`. Como `SPARK_*` só vale ao criar a sessão, e `CONTAINER_*` só ao recriar o container:

```bash
make up            # recria o container com os novos limites
```

### Passo 2 — Observar uma execução

```bash
make pipeline ANOS=2022 ETAPAS=silver &   # roda em segundo plano
docker stats rais-lakehouse-spark-1        # memória e CPU em tempo real (Ctrl+C para sair)
```

Abra a Spark UI (`localhost:4040`; se o Jupyter já tem uma sessão, `4041`) e vá em **Stages**.

### Passo 3 — Ler os sinais (guia, Parte [14.5](../guia/parte-14.md#parte-14-5))

| O que você vê | Diagnóstico | O que fazer |
| --- | --- | --- |
| *Spill (disk)* alto | Falta memória por tarefa | Menos threads ou mais `SPARK_MEM` |
| Milhares de tarefas de poucos KB | Partições demais | Reduzir `SPARK_SHUFFLE` |
| Poucas tarefas grandes e lentas | Partições de menos | Aumentar `SPARK_SHUFFLE` |
| Uma tarefa muito mais lenta que as outras | *Data skew* | Rever a chave do `groupBy`/`join`; `repartition` por outra coluna |
| `OutOfMemoryError` no log | Heap da JVM insuficiente | Menos threads, mais `SPARK_MEM`, menos dados por vez |
| Container reinicia / código 137 | `mem_limit` estourado | Reduzir `SPARK_MEM` ou aumentar `CONTAINER_MEM` |
| CPU baixa o tempo todo | Gargalo de E/S (MinIO/disco) | Mais partições de leitura; verificar o disco do MinIO |

### Passo 4 — Benchmark (guia, Parte [14.6](../guia/parte-14.md#parte-14-6))

`scripts/bench.sh` (rode **dentro** do container: `make shell`):

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

- Cada combinação roda um processo Python novo, então `SPARK_THREADS` e `SPARK_SHUFFLE` passados na linha de comando valem (a sessão é criada do zero).
- `set -euo pipefail` faz o script parar no primeiro erro.
- <span class="rl-complemento">Complemento didático</span> Se seu `CONTAINER_CPUS` for menor que 6, troque `2 4 6` por valores que caibam. A silver roda com `checar_silver` junto, como no pipeline.

### Passo 5 — Registrar a decisão

Responda em `docs/decisoes.md` (guia): (a) o ganho com mais threads é linear? (b) em que ponto aparece spill? (c) qual configuração vira o padrão no `.env` e por quê? Escreva como ADR, com `SPARK_THREADS`, `SPARK_MEM` e `SPARK_SHUFFLE` escolhidos.

## 6. Funcionamento e resultados esperados

| Item | Esperado |
| --- | --- |
| `docs/benchmark.csv` | Cabeçalho + 9 linhas |
| Tendência típica | Ganho que diminui com mais threads; um ponto a partir do qual mais threads não ajudam ou pioram (confirme no seu resultado — não há número certo a priori) |
| ADR | Configuração escolhida e evidência do benchmark |

## 7. Exemplos práticos

**Exemplo 1 — Controle no código (guia, Parte [14.7](../guia/parte-14.md#parte-14-7)).**

```python
df.rdd.getNumPartitions()                       # quantas partições agora
df.repartition(48, "cod_uf")                    # redistribui por chave (com shuffle)
df.coalesce(4)                                  # reduz partições sem shuffle completo
spark.conf.set("spark.sql.shuffle.partitions", "64")   # muda em execução
```

Configurações de **SQL** mudam em execução; as de **memória** e `master` só ao criar a sessão.

**Exemplo 2 — Skew na RAIS.** <span class="rl-complemento">Complemento didático</span> SP concentra muito mais vínculos que outras UFs; um `repartition("cod_uf")` deixaria uma tarefa enorme. Na Spark UI, isso aparece como uma tarefa muito mais lenta no estágio. O `groupBy` com agregação parcial (Aula 08) atenua o problema.

**Exemplo 3 — Quando virar cluster (guia, Parte [14.7](../guia/parte-14.md#parte-14-7)).** Num Spark standalone on-premises, os equivalentes são `spark.executor.instances`, `spark.executor.cores`, `spark.executor.memory` e `spark.cores.max`. A lógica não muda: núcleos por executor × memória por núcleo.

## 8. Armadilhas, diagnóstico e soluções

| Sintoma | Causa | Solução |
| --- | --- | --- |
| Mudei `SPARK_MEM` e nada mudou | Sessão já existia (Jupyter) | Reiniciar o kernel |
| Mudei `CONTAINER_MEM` e nada mudou | Container não recriado | `make up` |
| Código 137 | `SPARK_MEM` não cabe no container | Regra dos 65–75% |
| Docker Desktop trava a máquina | Limite do Docker Desktop/WSL maior que a RAM livre | Ajustar `.wslconfig` / Docker Desktop |
| Benchmark sem diferença entre combinações | Gargalo de E/S, não de CPU | Olhar CPU no `docker stats`; disco do MinIO |
| Disco cheio durante o job | Spill no volume `spark-tmp` | Mais memória por tarefa ou mais disco |

## 9. Boas práticas

1. Começar conservador e medir (guia).
2. Mudar **uma variável por vez** (guia).
3. Threads explícitas; nunca `local[*]` sem pensar (guia).
4. Partições múltiplas do número de threads (guia).
5. Registrar a configuração escolhida como ADR, com a evidência.
6. <span class="rl-complemento">Complemento didático</span> Refazer o benchmark quando o volume mudar muito (ex.: passar de 1 para 6 anos na gold).

## 10. Riscos

| Tipo | Risco | Mitigação |
| --- | --- | --- |
| Desempenho | Configuração ótima para 1 ano ruim para 6 | Refazer o benchmark |
| Integridade operacional | Container morto no meio do pipeline | Idempotência permite rodar de novo (Aula 14) |
| Custo | Spill enchendo o disco | Volume com espaço; mais memória por tarefa |
| Estabilidade do host | Limites acima da RAM real | Regras de encaixe |

## 11. Laboratório e validação na plataforma

**Contribuição ao projeto:** configuração padrão medida e documentada no `.env` e nos ADRs.

<span class="rl-complemento">Complemento didático</span> `labcheck/test_aula15.py`. O primeiro check lê o limite de memória do container no cgroup (v2 ou v1) e o compara com `spark.driver.memory`:

```python
"""Checks da Aula 15: configuração que cabe no container e decisão registrada."""
import os
from pathlib import Path

import pytest

UNIDADES = {"k": 1024, "m": 1024**2, "g": 1024**3, "t": 1024**4}


def em_bytes(valor: str) -> int:
    valor = valor.strip().lower()
    if valor[-1] in UNIDADES:
        return int(float(valor[:-1]) * UNIDADES[valor[-1]])
    return int(valor)


def limite_container() -> int | None:
    for arquivo in ("/sys/fs/cgroup/memory.max", "/sys/fs/cgroup/memory/memory.limit_in_bytes"):
        p = Path(arquivo)
        if p.exists():
            texto = p.read_text().strip()
            return None if texto == "max" else int(texto)
    return None


def test_a15_memoria_cabe_no_container(spark):
    limite = limite_container()
    if limite is None:
        pytest.skip("Container sem limite de memória visível.")
    driver = em_bytes(spark.conf.get("spark.driver.memory"))
    assert driver <= 0.8 * limite, (
        f"SPARK_MEM ({driver / 1024**3:.1f} GB) acima de 80% do container ({limite / 1024**3:.1f} GB)."
    )


def test_a15_threads_explicitas(spark):
    assert spark.conf.get("spark.master") != "local[*]", "Use SPARK_THREADS explícito."


def test_a15_benchmark_registrado():
    p = Path("docs/benchmark.csv")
    assert p.exists(), "Rode o passo 4."
    linhas = [linha for linha in p.read_text().splitlines() if linha.strip()]
    assert linhas[0] == "threads,shuffle,segundos" and len(linhas) >= 4, f"CSV incompleto: {linhas[:3]}"


def test_a15_adr_tuning():
    texto = Path("docs/decisoes.md").read_text(encoding="utf-8")
    assert "SPARK_THREADS" in texto and "SPARK_SHUFFLE" in texto, "Registre a configuração escolhida como ADR."
```

- O limite de 80% é uma margem de segurança acima dos 65–75% recomendados pelo guia.
- `memory.max` contém `max` quando não há limite; o check é pulado.
- Rode com `make check AULA=15`.

**Checklist manual:**

- [ ] vi spill (ou a ausência dele) na Spark UI
- [ ] mudei uma variável por vez
- [ ] o `.env` reflete a configuração do ADR.

## 12. Exercícios, revisão e desafios

**Exercícios**

1. (Guia) Rode a gold com `shuffle.partitions = 8` e depois com `400`. Compare o tempo e a aba Stages. O que mudou?
2. Calcule o número de partições pelo método da seção 3.4 a partir do *Shuffle Write* real da sua silver.

**Revisão**

1. Por que mais threads podem deixar o job mais lento?
2. Qual a diferença entre `OutOfMemoryError` e código 137?
3. Por que o número de partições deve ser múltiplo do de threads?
4. O que o AQE faz e o que ele não faz?

**Respostas sugeridas:** (1) menos memória por tarefa, mais spill; (2) o primeiro é a JVM sem heap; o segundo é o Docker matando o container por passar do `mem_limit`; (3) para todas as threads trabalharem até a última onda; (4) junta partições pequenas; não aumenta partições.

**Desafios**

1. Estenda o `bench.sh` para variar também `SPARK_MEM` e plote o resultado com pandas.
2. Aplique `ativos.cache()` na gold e meça o tempo antes e depois. Registre se vale a pena.

## 13. Referências cruzadas

| Tema | Onde |
| --- | --- |
| cgroups, `cpus`, `mem_limit` | Aulas 02 e 03 |
| `get_spark` e variáveis `SPARK_*` | Aula 06 |
| Shuffle, `explain`, partições | Aula 08 |
| Pipeline e idempotência | Aula 14 |
| ADRs | Aula 01 |
| Tabela de configurações | Apêndice F |


## Checks automáticos

```bash
make check AULA=15 ANO=2022
```

Arquivo: `labcheck/test_aula15.py`. Cada execução grava o resultado em `progress/historico.jsonl`; depois rode `make progresso` para atualizar a página [Progresso](../progresso.md).

| Check | O que verifica |
| --- | --- |
| `a15_memoria_cabe_no_container` | memoria cabe no container |
| `a15_threads_explicitas` | threads explicitas |
| `a15_benchmark_registrado` | benchmark registrado |
| `a15_adr_tuning` | adr tuning |
