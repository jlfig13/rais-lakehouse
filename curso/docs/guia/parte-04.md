<!-- Página GERADA de docs/guia/rais-lakehouse-guia.md -->

# Parte [4](parte-04.md) — Infraestrutura: Dockerfile, Compose e MinIO

## 4.1 Conceitos de MinIO e S3 { #parte-4-1 }

- **Object storage** guarda **objetos** (arquivos + metadados) dentro de **buckets**, acessados por API HTTP (o padrão S3).
- Não existem diretórios de verdade: `bronze/rais_vinculos/ano=2022/arq.parquet` é só o **nome (chave)** do objeto. As "pastas" são uma convenção visual.
- O Spark acessa S3 pelo conector **S3A** (biblioteca `hadoop-aws`), com caminhos `s3a://bucket/caminho`.
- O MinIO exige **path-style** (`http://minio:9000/rais/...`) em vez de *virtual-host style* (`http://rais.minio:9000/...`).
- **Princípio do menor privilégio:** o usuário *root* do MinIO serve só para administrar. A aplicação usa um usuário próprio, com acesso **apenas** ao bucket `rais`.

## 4.2 Versões { #parte-4-2 }

| Componente | Versão | Observação |
|---|---|---|
| Python | 3.11 | |
| Java | 17 | requisito do Spark 3.5 |
| PySpark | 3.5.3 | sem ANSI por padrão (o 4.x ativa) |
| delta-spark | 3.2.0 | compatível com Spark 3.5 (confirme a matriz na documentação do Delta) |
| hadoop-aws | 3.3.4 | mesma versão do Hadoop embutido no PySpark 3.5 |
| aws-java-sdk-bundle | 1.12.262 | dependência do hadoop-aws 3.3.4 |

> **Por que fixar versões?** Com versões fixas, o build de hoje e o de daqui a um ano produzem a mesma imagem. Nunca use `latest` em projeto sério: ele muda sem aviso.

## 4.3 Dependências Python { #parte-4-3 }

**`requirements.txt`** (execução)
```text
pyspark==3.5.3
delta-spark==3.2.0
py7zr==0.22.0
```

**`requirements-dev.txt`** (desenvolvimento)
```text
jupyterlab==4.2.5
pytest==8.3.3
ruff==0.6.9
pandas==2.2.3
matplotlib==3.9.2
```
> As versões acima são uma base. Se alguma não instalar, use a mais recente da mesma linha (ex.: `4.2.x`).

## 4.4 Dockerfile do Spark { #parte-4-4 }

**`docker/spark/Dockerfile`**
```dockerfile
# 1) Base: Python sobre Debian 12 (bookworm), que tem o OpenJDK 17 no repositório
FROM python:3.11-slim-bookworm

# 2) Versões como ARG: muda num lugar só
ARG HADOOP_AWS_VERSION=3.3.4
ARG AWS_SDK_VERSION=1.12.262
ARG DELTA_VERSION=3.2.0
ARG SCALA_VERSION=2.12
ARG HOST_UID=1000

# 3) Pacotes do sistema (muda pouco -> fica no topo para aproveitar o cache)
RUN apt-get update \
 && apt-get install -y --no-install-recommends openjdk-17-jre-headless curl procps \
 && rm -rf /var/lib/apt/lists/*

# 4) Dependências Python (antes do código, para aproveitar o cache)
COPY requirements.txt requirements-dev.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.txt -r /tmp/requirements-dev.txt

# 5) JARs do Delta e do S3A dentro da pasta de JARs do PySpark
#    (assim o Spark os carrega sozinho, sem internet em tempo de execução)
RUN SPARK_JARS="$(python -c 'import os, pyspark; print(os.path.join(os.path.dirname(pyspark.__file__), "jars"))')" \
 && MAVEN=https://repo1.maven.org/maven2 \
 && curl -fsSL -o "$SPARK_JARS/hadoop-aws-${HADOOP_AWS_VERSION}.jar" \
      "$MAVEN/org/apache/hadoop/hadoop-aws/${HADOOP_AWS_VERSION}/hadoop-aws-${HADOOP_AWS_VERSION}.jar" \
 && curl -fsSL -o "$SPARK_JARS/aws-java-sdk-bundle-${AWS_SDK_VERSION}.jar" \
      "$MAVEN/com/amazonaws/aws-java-sdk-bundle/${AWS_SDK_VERSION}/aws-java-sdk-bundle-${AWS_SDK_VERSION}.jar" \
 && curl -fsSL -o "$SPARK_JARS/delta-spark_${SCALA_VERSION}-${DELTA_VERSION}.jar" \
      "$MAVEN/io/delta/delta-spark_${SCALA_VERSION}/${DELTA_VERSION}/delta-spark_${SCALA_VERSION}-${DELTA_VERSION}.jar" \
 && curl -fsSL -o "$SPARK_JARS/delta-storage-${DELTA_VERSION}.jar" \
      "$MAVEN/io/delta/delta-storage/${DELTA_VERSION}/delta-storage-${DELTA_VERSION}.jar"

# 6) Usuário sem privilégios de root (segurança).
#    O UID igual ao do seu usuário no host evita problemas de permissão no bind mount.
RUN useradd -m -u "${HOST_UID}" app \
 && mkdir -p /app /staging /tmp/spark \
 && chown -R app:app /app /staging /tmp/spark

ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1

WORKDIR /app
USER app

EXPOSE 8888 4040
CMD ["bash"]
```

**O que observar**
- `--no-install-recommends` e `rm -rf /var/lib/apt/lists/*` deixam a imagem menor.
- `curl -fsSL` faz o build **falhar** se o download der erro (`-f`), em vez de gravar um arquivo corrompido.
- O código **não** é copiado para a imagem, porque entra via bind mount. Para produção, você adicionaria `COPY . /app`.
- Descubra seu UID com `id -u` no Linux/WSL. No Mac, normalmente o padrão 1000 funciona.

## 4.5 Inicialização do MinIO { #parte-4-5 }

**`docker/minio/policy-rais.json`** (permissão só no bucket `rais`)
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:*"],
      "Resource": ["arn:aws:s3:::rais", "arn:aws:s3:::rais/*"]
    }
  ]
}
```
> Se mudar o nome do bucket no `.env`, mude aqui também.

**`docker/minio/init-minio.sh`**
```sh
#!/bin/sh
# Prepara o MinIO: bucket, política e usuário da aplicação.
# É idempotente: pode rodar várias vezes sem quebrar nada.
set -eu

echo "[init] aguardando o MinIO responder..."
until mc alias set local "http://minio:9000" "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" >/dev/null 2>&1; do
  sleep 2
done

echo "[init] criando bucket ${RAIS_BUCKET}"
mc mb --ignore-existing "local/${RAIS_BUCKET}"

echo "[init] criando política e usuário da aplicação"
mc admin policy create local rais-rw /init/policy-rais.json 2>/dev/null || true
mc admin user add local "$APP_ACCESS_KEY" "$APP_SECRET_KEY"
mc admin policy attach local rais-rw --user "$APP_ACCESS_KEY" 2>/dev/null || true

echo "[init] MinIO pronto."
```
> A sintaxe de `mc admin policy` mudou entre versões do `mc`. Se der erro, rode `mc admin policy --help` dentro do container e ajuste.

## 4.6 Variáveis de ambiente { #parte-4-6 }

**`.env.example`** (versionado, com valores fictícios)
```bash
# ---------- Imagens (CONFIRME imagem e tag atuais no repositório oficial do MinIO) ----------
MINIO_IMAGE=<imagem-do-minio>:<tag-fixa>
MC_IMAGE=<imagem-do-mc>:<tag-fixa>

# ---------- MinIO: administrador (só para administrar) ----------
MINIO_ROOT_USER=troque-admin
MINIO_ROOT_PASSWORD=troque-por-senha-com-16+-caracteres

# ---------- MinIO: usuário da aplicação (o Spark usa este) ----------
APP_ACCESS_KEY=rais-app
APP_SECRET_KEY=troque-por-outra-senha-forte
RAIS_BUCKET=rais

# ---------- Pastas no host ----------
HOST_STAGING_DIR=./staging
HOST_UID=1000

# ---------- Recursos do container ----------
CONTAINER_CPUS=6
CONTAINER_MEM=12g

# ---------- Spark (ver Parte 14) ----------
SPARK_THREADS=4
SPARK_MEM=8g
SPARK_SHUFFLE=32

# ---------- Jupyter ----------
JUPYTER_TOKEN=troque-este-token
```
```bash
cp .env.example .env     # e edite o .env com seus valores reais
```

## 4.7 docker-compose.yml { #parte-4-7 }

```yaml
name: rais-lakehouse

services:

  # ---------------------------------------------------------------- armazenamento
  minio:
    image: ${MINIO_IMAGE:?defina MINIO_IMAGE no .env}
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER:?defina MINIO_ROOT_USER}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD:?defina MINIO_ROOT_PASSWORD}
    ports:
      - "127.0.0.1:9000:9000"     # API S3
      - "127.0.0.1:9001:9001"     # console web
    volumes:
      - minio-data:/data
    restart: unless-stopped

  # ---------------------------------------------------------------- setup (roda e termina)
  minio-init:
    image: ${MC_IMAGE:?defina MC_IMAGE no .env}
    depends_on:
      - minio
    entrypoint: ["/bin/sh", "/init/init-minio.sh"]
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD}
      APP_ACCESS_KEY: ${APP_ACCESS_KEY:?defina APP_ACCESS_KEY}
      APP_SECRET_KEY: ${APP_SECRET_KEY:?defina APP_SECRET_KEY}
      RAIS_BUCKET: ${RAIS_BUCKET:-rais}
    volumes:
      - ./docker/minio/init-minio.sh:/init/init-minio.sh:ro
      - ./docker/minio/policy-rais.json:/init/policy-rais.json:ro
    restart: "no"

  # ---------------------------------------------------------------- processamento
  spark:
    build:
      context: .
      dockerfile: docker/spark/Dockerfile
      args:
        HOST_UID: ${HOST_UID:-1000}
    image: rais-spark:local
    depends_on:
      minio-init:
        condition: service_completed_successfully
    environment:
      # O container recebe SÓ o que precisa (nada de senha de root)
      MINIO_ENDPOINT: http://minio:9000          # nome do serviço, não localhost!
      S3_ACCESS_KEY: ${APP_ACCESS_KEY}
      S3_SECRET_KEY: ${APP_SECRET_KEY}
      RAIS_LAKE: s3a://${RAIS_BUCKET:-rais}
      RAIS_STAGING: /staging
      SPARK_THREADS: ${SPARK_THREADS:-4}
      SPARK_MEM: ${SPARK_MEM:-8g}
      SPARK_SHUFFLE: ${SPARK_SHUFFLE:-32}
      SPARK_TMP: /tmp/spark
    ports:
      - "127.0.0.1:8888:8888"     # JupyterLab
      - "127.0.0.1:4040-4041:4040-4041"   # Spark UI (4040) e a de um 2º processo simultâneo (4041)
    volumes:
      - ./:/app                                   # seu código (bind mount)
      - ${HOST_STAGING_DIR:-./staging}:/staging   # landing/raw
      - spark-tmp:/tmp/spark                      # spill/shuffle do Spark
    cpus: ${CONTAINER_CPUS:-4}
    mem_limit: ${CONTAINER_MEM:-8g}
    command: >
      jupyter lab --ip=0.0.0.0 --port=8888 --no-browser
      --ServerApp.token=${JUPYTER_TOKEN:?defina JUPYTER_TOKEN}

volumes:
  minio-data:     # o lake inteiro mora aqui
  spark-tmp:
```

**Decisões explicadas**
- **Faixa de portas `4040-4041`:** se o Jupyter já tem uma sessão aberta (porta 4040), um segundo processo, como o pipeline, usa a 4041. Para conferir o mapeamento final, use `docker compose config`.
- **Portas em `127.0.0.1`:** os serviços ficam acessíveis só na sua máquina, não na rede. Expor o MinIO ou o Jupyter na rede sem TLS e autenticação forte é um risco.
- **`minio-init` separado:** é um *init container*. Ele roda, configura e termina, e o `spark` só sobe depois que ele termina com sucesso (`service_completed_successfully`).
- **`environment` explícito** no lugar de `env_file: .env`: cada container recebe só as variáveis de que precisa (menor privilégio).
- **`cpus` e `mem_limit`:** limitam o container. As configurações do Spark precisam caber **dentro** desses limites (Parte [14](parte-14.md)).
- **Volume nomeado `minio-data`:** para guardar em uma pasta específica do servidor (ex.: um disco dedicado), troque por bind mount: `- /mnt/dados/minio:/data`.
- No **Docker Desktop** (Windows/Mac), o limite de memória do Docker Desktop precisa ser maior que `CONTAINER_MEM`.

## 4.8 Makefile (atalhos) { #parte-4-8 }

> No Makefile, a indentação dos comandos **tem que ser TAB**, não espaços.

```makefile
COMPOSE := docker compose
ANOS    ?= 2022
ETAPAS  ?= extrair bronze silver gold

.PHONY: help up down logs ps shell smoke pipeline test lint fmt

help:            ## lista os comandos
	@grep -E '^[a-z]+:.*##' Makefile | awk -F':.*## ' '{printf "  %-10s %s\n", $$1, $$2}'

up:              ## constrói e sobe a infraestrutura
	$(COMPOSE) up -d --build

down:            ## para e remove containers (mantém os dados)
	$(COMPOSE) down

logs:            ## acompanha os logs
	$(COMPOSE) logs -f

ps:              ## estado dos containers
	$(COMPOSE) ps -a

shell:           ## terminal dentro do container spark
	$(COMPOSE) exec spark bash

smoke:           ## teste de fumaça (Spark + Delta + MinIO)
	$(COMPOSE) exec spark python -m scripts.smoke_test

pipeline:        ## roda o pipeline. Ex.: make pipeline ANOS="2021 2022"
	$(COMPOSE) exec spark python -m src.run_pipeline --anos $(ANOS) --etapas $(ETAPAS) --limpar-raw

test:            ## testes
	$(COMPOSE) exec spark pytest -q

lint:            ## análise estática
	$(COMPOSE) exec spark ruff check .

fmt:             ## formata o código
	$(COMPOSE) exec spark ruff format .
```

## 4.9 Subindo tudo { #parte-4-9 }

```bash
mkdir -p staging
make up            # ou: docker compose up -d --build
make ps            # minio "running", minio-init "exited (0)", spark "running"
docker compose logs minio-init      # deve terminar com "[init] MinIO pronto."
```
Acesse:
- **JupyterLab:** http://localhost:8888 (use o `JUPYTER_TOKEN`)
- **Console MinIO:** http://localhost:9001 (usuário root), se disponível na sua versão

## 4.10 Teste de fumaça { #parte-4-10 }

O teste usa a função `get_spark` da Parte [7](parte-07.md). Crie primeiro `config/settings.py` e `src/utils.py` (Parte [7](parte-07.md)) e depois volte aqui.

**`scripts/smoke_test.py`**
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
```bash
make smoke
```

### Checkpoint
- Aparece `[ok] Spark 3.5.x + Delta + MinIO funcionando (1000 linhas)`.
- No console do MinIO, o bucket `rais` tem `_smoke/teste/` com arquivos `.parquet` e a pasta `_delta_log/`.
- Commit: `git commit -m "feat(infra): docker compose com spark, delta e minio"`.

---
