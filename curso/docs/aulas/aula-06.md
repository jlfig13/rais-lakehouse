---
aula: 6
titulo: "Ambiente no ar: SparkSession, Delta, S3A e teste de fumaça"
origem: ['Guia Parte 4.2', 'Guia Parte 4.9', 'Guia Parte 4.10', 'Guia Parte 7.3 (get_spark)']
depende_de: [3, 4, 5]
checks: ['a06_versao_spark', 'a06_config_s3a', 'a06_smoke_1000', 'a06_smoke_e_delta']
---

# Aula 06 — Ambiente no ar: SparkSession, Delta, S3A e teste de fumaça

<!-- Página GERADA por scripts/gerar_curso.py. Edite aulas.yml e curso/conteudo/. -->

<div class="rl-aula" data-aula="6" data-onde="container" data-lab="src/utils.py"></div>

| | |
| --- | --- |
| Origem no guia | Guia Parte [4.2](../guia/parte-04.md#parte-4-2), Guia Parte [4.9](../guia/parte-04.md#parte-4-9), Guia Parte [4.10](../guia/parte-04.md#parte-4-10), Guia Parte [7.3](../guia/parte-07.md#parte-7-3) (get_spark) |
| Depende de | [Aula 03](aula-03.md), [Aula 04](aula-04.md), [Aula 05](aula-05.md) |
| Entregas | `src/utils.py (get_spark)`, `scripts/smoke_test.py`, `labcheck/conftest.py`, `scripts/gerar_progresso.py` |
| Onde os checks rodam | Container spark |

Ao final desta aula a função `get_spark` cria uma sessão Spark já ligada ao Delta e ao MinIO, e o teste de fumaça grava e lê 1000 linhas no lake. A partir daqui, todo código do curso começa com `get_spark()`. A aula também instala o mecanismo de progresso da plataforma.

## 1. Objetivos e pré-requisitos

1. Explicar o que é a `SparkSession` e o que cada configuração do `get_spark` faz.
2. Ativar o Delta com as duas configurações de extensão e catálogo.
3. Configurar o S3A para o MinIO (endpoint, credenciais, path-style, SSL).
4. Rodar e interpretar o teste de fumaça de ponta a ponta.
5. Usar o `make check` e a página de progresso da plataforma.

**Pré-requisitos:** Aulas 03 a 05; ambiente no ar (`make up`).

## 2. Contextualização

Até aqui cada peça foi testada isolada: a imagem (Aula 02), os serviços (Aula 03), o MinIO (Aula 04). Falta o elo: o Spark, dentro do container, gravando tabelas Delta no MinIO com as credenciais da aplicação. Um **teste de fumaça** (*smoke test*) é o teste mínimo de ponta a ponta: não verifica regras de negócio, só se a infraestrutura "liga sem soltar fumaça". Ele vem antes de qualquer pipeline porque um erro de infraestrutura no meio de um processamento de horas é muito mais caro de diagnosticar.

## 3. Fundamentação teórica

### 3.1 SparkSession

A `SparkSession` é o ponto de entrada do Spark; só existe uma por processo (guia, Parte [5.1](../guia/parte-05.md#parte-5-1)). `getOrCreate()` devolve a existente se já houver uma. **Consequência:** configurações de **memória e `master`** só valem quando a sessão é criada — num notebook, mudá-las exige reiniciar o kernel (guia, Parte [7.3](../guia/parte-07.md#parte-7-3)). Configurações de SQL podem mudar depois com `spark.conf.set` (Aula 15).

### 3.2 Modo local

`master("local[N]")` roda o Spark inteiro numa JVM, com N threads (ADR-001). O código é o mesmo que rodaria num cluster; só muda o `master` e os recursos (Aula 15).

### 3.3 Como o Delta se liga ao Spark

Os JARs do Delta já estão no classpath (Aula 02). Duas configurações os ativam:

| Configuração | Valor | Efeito |
| --- | --- | --- |
| `spark.sql.extensions` | `io.delta.sql.DeltaSparkSessionExtension` | Acrescenta ao Spark os comandos e regras do Delta |
| `spark.sql.catalog.spark_catalog` | `org.apache.spark.sql.delta.catalog.DeltaCatalog` | Faz o catálogo padrão entender tabelas Delta |

Sem elas, `format("delta")` falha ou operações como `DeltaTable.forPath` não funcionam.

### 3.4 Como o S3A encontra o MinIO

| Configuração | Valor no curso | Por quê |
| --- | --- | --- |
| `fs.s3a.impl` | `S3AFileSystem` | Liga o esquema `s3a://` ao conector |
| `fs.s3a.endpoint` | `http://minio:9000` | Nome do serviço na rede do Compose (Aula 03) |
| `fs.s3a.access.key` / `secret.key` | `S3_ACCESS_KEY` / `S3_SECRET_KEY` | Usuário da aplicação, nunca root (Aula 04) |
| `fs.s3a.path.style.access` | `true` | Obrigatório para MinIO (Aula 04) |
| `fs.s3a.connection.ssl.enabled` | `false` | HTTP na rede interna; `true` se usar HTTPS |

O prefixo `spark.hadoop.` passa a configuração do Spark para a camada Hadoop, onde o S3A vive.

### 3.5 Versões (guia, Parte [4.2](../guia/parte-04.md#parte-4-2))

Python 3.11 · Java 17 · PySpark 3.5.3 · delta-spark 3.2.0 · hadoop-aws 3.3.4 · aws-java-sdk-bundle 1.12.262. O teste de fumaça é a prova de que essa combinação funciona na sua máquina.

## 4. Arquitetura e fluxo do teste de fumaça

```
make smoke
  └─ docker compose exec spark python -m scripts.smoke_test
       └─ get_spark()  ── lê SPARK_*, MINIO_ENDPOINT, S3_* do ambiente
            │
            ├─ spark.range(1000) ──▶ write.format("delta") ──S3A──▶ s3a://rais/_smoke/teste/
            │                                                      ├─ part-*.parquet
            │                                                      └─ _delta_log/00000000000000000000.json
            └─ read.format("delta").count() ◀──S3A── (lê o log, depois os Parquet)
                  └─ assert total == 1000 → "[ok] ..."
```

## 5. Tutorial

### Passo 1 — `src/utils.py` com `get_spark` (guia, Parte [7.3](../guia/parte-07.md#parte-7-3))

Nesta aula o arquivo contém só o `get_spark` e os imports; as funções auxiliares entram na Aula 10.

```python
"""SparkSession e funções auxiliares reutilizáveis."""
import os

from pyspark.sql import SparkSession


def get_spark(app_name: str = "rais") -> SparkSession:
    """Cria a SparkSession local com Delta e S3A (MinIO).

    Todos os recursos são ajustáveis por variável de ambiente (ver Aula 15).
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
```

| Configuração de recurso | O que faz | Aula de aprofundamento |
| --- | --- | --- |
| `spark.driver.memory` | Memória da JVM (em modo local, é toda a memória do Spark) | 15 |
| `spark.sql.shuffle.partitions` | Nº de partições após um shuffle | 08, 15 |
| `spark.sql.files.maxPartitionBytes` | Tamanho máximo de cada partição de leitura | 15 |
| `spark.sql.adaptive.*` | AQE: reotimiza o plano durante a execução e junta partições pequenas | 15 |
| `spark.local.dir` | Onde vai o *spill*; aponta para o volume `spark-tmp` | 03, 15 |
| `spark.sql.session.timeZone` | Fuso usado em datas e horas | — |

### Passo 2 — `scripts/smoke_test.py` (guia, Parte [4.10](../guia/parte-04.md#parte-4-10))

```python
"""Valida a infraestrutura: Spark sobe, Delta funciona e o MinIO aceita escrita/leitura."""
from config.settings import LAKE
from src.utils import get_spark


def main() -> None:
    spark = get_spark("smoke-test")
    caminho = f"{LAKE}/_smoke/teste"

    spark.range(1000).write.format("delta").mode("overwrite").save(caminho)
    total = spark.read.format("delta").load(caminho).count()

    assert total == 1000, f"esperado 1000, obtido {total}"
    print(f"[ok] Spark {spark.version} + Delta + MinIO funcionando ({total} linhas)")
    spark.stop()


if __name__ == "__main__":
    main()
```

- `spark.range(1000)` cria um DataFrame com uma coluna `id` de 0 a 999 — dado sintético mínimo.
- `mode("overwrite")` torna o teste repetível: cada execução cria uma nova versão Delta em vez de duplicar.
- `python -m scripts.smoke_test` (forma usada no Makefile) roda o arquivo como módulo, a partir de `/app`, por isso os imports `config` e `src` funcionam.

### Passo 3 — Rodar

```bash
make smoke
```

**Resultado esperado:** muitas linhas de log do Spark (normais) e, no fim, `[ok] Spark 3.5.3 + Delta + MinIO funcionando (1000 linhas)`. Em seguida, no console do MinIO (ou com `mc ls --recursive app/rais/_smoke/teste`, Aula 04), aparecem arquivos `.parquet` e a pasta `_delta_log/`.

### Passo 4 — Ver a Spark UI

Num notebook do JupyterLab (`localhost:8888`), rode `from src.utils import get_spark; spark = get_spark()` e abra `http://localhost:4040`. A UI só existe enquanto a sessão existir; um segundo processo simultâneo usa a 4041 (guia, [Apêndice B](../guia/apendice-b.md)).

### Passo 5 — Instalar o mecanismo de progresso da plataforma

`labcheck/conftest.py` serve aos checks do container e do host:

```python
"""Configuração comum dos checks: opção --ano, fixture spark e registro do progresso."""
import json
import re
from datetime import datetime
from pathlib import Path

import pytest

HISTORICO = Path("progress/historico.jsonl")


def pytest_addoption(parser):
    parser.addoption("--ano", type=int, default=2022, help="ano-base usado pelos checks")


@pytest.fixture(scope="session")
def ano(request):
    return request.config.getoption("--ano")


@pytest.fixture(scope="session")
def spark():
    from src.utils import get_spark  # importa só se um check precisar (o host não tem PySpark)

    sessao = get_spark("labcheck")
    yield sessao
    sessao.stop()


def pytest_runtest_logreport(report):
    """Grava uma linha por check em progress/historico.jsonl."""
    if report.when != "call" and not (report.when == "setup" and report.skipped):
        return
    m = re.search(r"test_aula(\d+)\.py::test_(\w+)", report.nodeid)
    if not m:
        return
    status = "passou" if report.passed else "pulou" if report.skipped else "falhou"
    linha = {
        "ts": datetime.now().astimezone().isoformat(timespec="seconds"),
        "aula": int(m.group(1)),
        "check": m.group(2),
        "status": status,
        "detalhe": str(report.longrepr)[-300:] if report.failed else "",
        "origem": "execucao_real",
    }
    HISTORICO.parent.mkdir(exist_ok=True)
    with HISTORICO.open("a", encoding="utf-8") as f:
        f.write(json.dumps(linha, ensure_ascii=False) + "\n")
```

- `pytest_addoption` e `pytest_runtest_logreport` são *hooks* do pytest: funções com nomes padronizados que o pytest chama sozinho.
- O nome do arquivo de teste (`test_aula06.py`) e da função (`test_a06_...`) definem `aula` e `check` no histórico — por isso a convenção de nomes é obrigatória.
- `report.longrepr` é o texto do erro; guardamos só o fim (300 caracteres) para o histórico não crescer demais.

`scripts/gerar_progresso.py`:

```python
"""Gera curso/docs/progresso.md a partir de progress/historico.jsonl."""
import json
from collections import defaultdict
from pathlib import Path

HISTORICO = Path("progress/historico.jsonl")
SAIDA = Path("curso/docs/progresso.md")


def main() -> None:
    ultimo = {}
    if HISTORICO.exists():
        for linha in HISTORICO.read_text(encoding="utf-8").splitlines():
            r = json.loads(linha)
            ultimo[(r["aula"], r["check"])] = r  # a execução mais recente vence

    por_aula = defaultdict(list)
    for (aula, _), r in ultimo.items():
        por_aula[aula].append(r)

    linhas = ["# Progresso", "", "Gerado por `make progresso` a partir de execuções reais.", "",
              "| Aula | Checks passando | Última execução |", "| --- | --- | --- |"]
    for aula in range(1, 17):
        rs = por_aula.get(aula, [])
        ok = sum(r["status"] == "passou" for r in rs)
        quando = max((r["ts"] for r in rs), default="—")
        linhas.append(f"| {aula:02d} | {ok}/{len(rs)} | {quando} |")

    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    print(f"[progresso] {SAIDA}")


if __name__ == "__main__":
    main()
```

**Limite conhecido:** o total mostrado é o de checks **já executados**, não o declarado no front matter da aula. Ler o front matter para mostrar "0/5" de aulas ainda não validadas fica como evolução da plataforma.

## 6. Funcionamento e resultados esperados

| Etapa | O que acontece | Esperado |
| --- | --- | --- |
| `get_spark()` | Cria a JVM com Delta e S3A | Sem erro; `spark.version` = `3.5.3` |
| `write.format("delta")` | Grava Parquet e o primeiro JSON do log no MinIO | Sem `403` nem `ClassNotFoundException` |
| `read...count()` | Lê o log e conta | `1000` |
| `make check AULA=06` | Roda os checks e grava o histórico | 4 checks passando |
| `make progresso` | Gera `curso/docs/progresso.md` | Linha da Aula 06 com 4/4 |

## 7. Exemplos práticos

**Exemplo 1 — Conferir a configuração efetiva.** Num notebook:

```python
from src.utils import get_spark
spark = get_spark()
for chave in ["spark.master", "spark.driver.memory", "spark.sql.shuffle.partitions",
              "spark.hadoop.fs.s3a.endpoint", "spark.hadoop.fs.s3a.path.style.access"]:
    print(chave, "=", spark.conf.get(chave))
```

Não imprima `access.key` nem `secret.key`: o notebook pode ser compartilhado.

**Exemplo 2 — Lake sem MinIO.** O `settings.py` aceita `RAIS_LAKE=file:///tmp/lake` (Aula 05). Rode `docker compose exec -e RAIS_LAKE=file:///tmp/lake spark python -m scripts.smoke_test`: o mesmo teste grava em disco local do container. Útil para isolar se um erro é do Spark/Delta ou do MinIO.

**Exemplo 3 — Ver as versões da tabela de fumaça.** Rode `make smoke` duas vezes e depois, num notebook:

```python
from delta.tables import DeltaTable
from config.settings import LAKE

DeltaTable.forPath(spark, f"{LAKE}/_smoke/teste").history().select("version", "operation").show()
```

Aparecem duas linhas `WRITE`, versões 0 e 1. Prévia da Aula 14.

## 8. Armadilhas, diagnóstico e soluções

| Sintoma | Causa provável | Solução |
| --- | --- | --- |
| `ClassNotFoundException: S3AFileSystem` | JAR não baixou no build (guia, [Apêndice B](../guia/apendice-b.md)) | `docker compose build --no-cache spark` |
| `ClassNotFoundException` com `delta` | JARs do Delta ausentes | Idem; check `a02_jars_s3a_delta` |
| `403` / `InvalidAccessKeyId` | Usuário da aplicação ausente ou sem política | Aula 04, checks `a04_*` |
| `UnknownHostException: rais.minio` | Path-style desligado | `fs.s3a.path.style.access=true` |
| `Connection refused` | Endpoint com `localhost` | `MINIO_ENDPOINT=http://minio:9000` |
| Mudou `SPARK_MEM` e nada mudou | Sessão já existia (guia, Parte [7.3](../guia/parte-07.md#parte-7-3)) | Reiniciar o kernel / processo |
| Spark UI não abre | Sem sessão ativa ou porta 4041 (guia, [Apêndice B](../guia/apendice-b.md)) | Criar sessão; tentar 4041 |
| `ModuleNotFoundError: scripts` | Falta `scripts/__init__.py` | Aula 05, passo 1 |
| Container cai com código 137 | `SPARK_MEM` maior que cabe no container | Aula 15 |

## 9. Boas práticas

1. Uma função única (`get_spark`) cria a sessão em todo o projeto: muda-se a configuração num lugar só.
2. Recursos por variável de ambiente, com padrões conservadores.
3. Teste de fumaça após qualquer mudança de imagem, versão ou credencial.
4. Áreas de teste separadas no lake (`_smoke/`, `_lab/`).
5. Nunca imprimir chaves de configuração de credenciais em notebooks ou logs.

## 10. Riscos

| Tipo | Risco | Mitigação |
| --- | --- | --- |
| Segurança | Credenciais expostas por `spark.conf.get` num notebook | Não imprimir chaves `*.key` |
| Desempenho | `local[*]` sufocando a máquina | Threads explícitas por `SPARK_THREADS` |
| Integridade | Versões incompatíveis passando despercebidas | Teste de fumaça e check de versão |
| Custo | Versões da tabela de fumaça acumulando | Desprezível; `VACUUM` na Aula 14 se quiser |

## 11. Laboratório e validação na plataforma

**Contribuição ao projeto:** `get_spark` é usado por todas as camadas e checks; o mecanismo de progresso passa a valer para todas as aulas.

`labcheck/test_aula06.py` (roda no container):

```python
"""Checks da Aula 06: Spark, Delta e MinIO integrados."""
from config.settings import LAKE

SMOKE = f"{LAKE}/_smoke/teste"


def test_a06_versao_spark(spark):
    assert spark.version == "3.5.3", f"Spark {spark.version}; o curso usa 3.5.3 (Aula 02)."


def test_a06_config_s3a(spark):
    assert spark.conf.get("spark.hadoop.fs.s3a.path.style.access") == "true", "Path-style desligado."
    assert "minio" in spark.conf.get("spark.hadoop.fs.s3a.endpoint"), "Endpoint não aponta para o serviço minio."


def test_a06_smoke_1000(spark):
    total = spark.read.format("delta").load(SMOKE).count()
    assert total == 1000, f"{total} linhas em {SMOKE}. Rode: make smoke"


def test_a06_smoke_e_delta(spark):
    from delta.tables import DeltaTable

    assert DeltaTable.isDeltaTable(spark, SMOKE), f"{SMOKE} não é uma tabela Delta."
```

```bash
make smoke
make check AULA=06
make progresso
```

**Checklist manual**

- [ ] Sei dizer o que cada uma das duas configurações do Delta faz.
- [ ] Sei explicar por que mudar `SPARK_MEM` exige reiniciar a sessão.
- [ ] Abri a Spark UI e vi o job do `count()`.
- [ ] A página `curso/docs/progresso.md` foi gerada.

## 12. Exercícios, revisão e desafios

**Exercícios**

1. Rode o Exemplo 2 (lake local) e o `make smoke` normal. Compare onde os arquivos foram parar.
2. Comente temporariamente a linha de path-style, rode `make smoke`, leia o erro e restaure.

**Revisão**

1. Para que servem `spark.sql.extensions` e `spark.sql.catalog.spark_catalog`?
2. Por que `fs.s3a.endpoint` usa `minio` e não `localhost`?
3. Por que o teste usa `mode("overwrite")`?
4. Como o histórico sabe a qual aula pertence cada check?

**Respostas sugeridas:** (1) ativar os comandos do Delta e o catálogo que entende tabelas Delta; (2) DNS do Compose (Aula 03); (3) para ser repetível sem duplicar; (4) pelo nome do arquivo `test_aulaNN.py` e da função `test_...`.

**Desafio:** faça o `gerar_progresso.py` ler o front matter de `curso/docs/aulas/aula-NN.md` e mostrar o total **declarado** de checks por aula.

## 13. Referências cruzadas

| Tema | Onde |
| --- | --- |
| JARs, versões e imagem | Aula 02 |
| Variáveis `SPARK_*`, `MINIO_ENDPOINT`, `S3_*`; alvos `smoke`, `check`, `progresso` | Aula 03 |
| Usuário da aplicação e path-style | Aula 04 |
| `config/settings.py` | Aula 05 |
| SparkSession e lazy evaluation em profundidade | Aulas 07 e 08 |
| Restante do `src/utils.py` e `_delta_log` | Aula 10 |
| `DESCRIBE HISTORY`, `VACUUM` | Aula 14 |
| Ajuste de threads, memória e partições | Aula 15 |


## Checks automáticos

```bash
make check AULA=06 ANO=2022
```

Arquivo: `labcheck/test_aula06.py`. Cada execução grava o resultado em `progress/historico.jsonl`; depois rode `make progresso` para atualizar a página [Progresso](../progresso.md).

| Check | O que verifica |
| --- | --- |
| `a06_versao_spark` | versao spark |
| `a06_config_s3a` | config s3a |
| `a06_smoke_1000` | smoke 1000 |
| `a06_smoke_e_delta` | smoke e delta |
