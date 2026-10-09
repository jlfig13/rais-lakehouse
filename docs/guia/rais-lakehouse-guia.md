# RAIS Lakehouse — PySpark + Delta Lake + MinIO com Docker Compose

Guia educacional e roteiro de um projeto de GitHub. Você vai construir, do zero, um *lakehouse* on-premises e 100% open source que processa os microdados da **RAIS** (2019 até o último ano-base publicado) nas camadas **bronze → silver → gold**.

**O que você vai aprender**
- **Docker e Docker Compose:** imagem, container, volume, rede, variáveis de ambiente.
- **PySpark:** DataFrame, transformações, agregações, joins, window functions, *lazy evaluation*, partições.
- **Delta Lake:** transações ACID, versionamento, *time travel*, schema enforcement, `OPTIMIZE` e `VACUUM`.
- **MinIO:** object storage compatível com S3, buckets, credenciais e políticas de acesso.
- **Engenharia de dados:** arquitetura medallion, idempotência, qualidade de dados e tuning do Spark.
- **Projeto profissional:** estrutura de repositório, testes, lint, CI no GitHub Actions, commits e README.

**Como usar este guia**
- Cada parte segue a mesma sequência: **Conceito** (o que e por quê), **Sintaxe/Prática** (o que fazer) e **Checkpoint** (como saber que deu certo).
- Siga na ordem e faça um commit ao fim de cada parte (a Parte 3 explica como).
- Comece com **1 ano e 1 região** (ex.: 2022 + Nordeste) e só escale na Parte 12.

> ⚠️ **Pontos que você precisa confirmar por conta própria**, porque mudam com o tempo e eu não consigo verificá-los no seu ambiente:
> 1. **Nomes de colunas e códigos da RAIS** de cada ano. Confira no dicionário oficial (Parte 6). O código foi escrito para falhar com mensagem clara se faltar algo.
> 2. **Imagem Docker do MinIO.** O projeto mudou a forma de distribuição da edição *community* em 2025. Confira no repositório oficial qual imagem e tag usar (Parte 4).
> 3. **Compatibilidade de versões** entre PySpark, Delta e hadoop-aws (Parte 4).
> 4. **URL de download** dos microdados (Parte 8).

---

## Sumário

- Parte 1 — Arquitetura e decisões
- Parte 2 — Conceitos de Docker e Docker Compose
- Parte 3 — Estrutura do repositório e Git
- Parte 4 — Infraestrutura: Dockerfile, Compose e MinIO
- Parte 5 — Fundamentos de PySpark
- Parte 6 — Conhecendo a RAIS
- Parte 7 — Código base: configuração e utilitários
- Parte 8 — Ingestão
- Parte 9 — Bronze
- Parte 10 — Silver
- Parte 11 — Gold
- Parte 12 — Pipeline completo (2019 → hoje)
- Parte 13 — Delta Lake na prática
- Parte 14 — Tuning: threads, memória e partições
- Parte 15 — Qualidade, testes e CI
- Parte 16 — Boas práticas de GitHub
- Apêndices: armadilhas, solução de problemas, glossário, próximos passos

---

# Parte 1 — Arquitetura e decisões

## 1.1 Visão geral

```
                    ┌──────────────────────── docker compose ────────────────────────┐
                    │                                                                 │
  gov.br (.7z) ───▶ │  container "spark"                     container "minio"        │
                    │  ┌───────────────────────────┐        ┌───────────────────────┐ │
                    │  │ Python + Java + PySpark   │  S3A   │ bucket "rais"          │ │
                    │  │ + Delta + JupyterLab      │ ─────▶ │  bronze/ (Delta)       │ │
                    │  │                           │        │  silver/ (Delta)       │ │
                    │  │ /staging (disco local):   │        │  gold/   (Delta)       │ │
                    │  │   landing/ (.7z)          │        └───────────────────────┘ │
                    │  │   raw/ (.txt temporário)  │                                   │
                    │  └───────────────────────────┘        container "minio-init"    │
                    │                                       (cria bucket e usuário)   │
                    └─────────────────────────────────────────────────────────────────┘
```

## 1.2 Camadas (arquitetura medallion)

| Camada | Onde fica | Formato | Objetivo | Regra de ouro |
|---|---|---|---|---|
| **landing** | disco local (`/staging/landing`) | `.7z` original | Guardar o arquivo como veio | Nunca editar; é a fonte da verdade |
| **raw** | disco local (`/staging/raw`) | `.txt` extraído | Arquivo intermediário | Temporário; apague após a bronze |
| **bronze** | MinIO | Delta | Cópia fiel e eficiente da origem | Tudo `string`, nomes normalizados, sem regra de negócio |
| **silver** | MinIO | Delta | Dado limpo e tipado | Uma linha = um vínculo, tipos corretos |
| **gold** | MinIO | Delta | Respostas prontas para análise | Cada tabela responde uma pergunta |

## 1.3 Decisões de arquitetura

Registre decisões assim (formato **ADR**, *Architecture Decision Record*) em `docs/decisoes.md`. É uma prática muito valorizada em projetos de portfólio.

| # | Decisão | Escolha | Alternativa considerada | Motivo |
|---|---|---|---|---|
| 1 | Execução | Spark em modo `local` num container | Cluster Spark standalone | Uma máquina basta para aprender; o código é o mesmo num cluster |
| 2 | Orquestração de infraestrutura | Docker Compose | Instalar tudo no host | Reprodutível: qualquer pessoa sobe o projeto com um comando |
| 3 | Armazenamento | MinIO (API S3) | HDFS, disco local | API S3 é padrão de mercado; o código migra para qualquer S3 |
| 4 | Formato de tabela | **Delta Lake** | Apache Iceberg | Setup mais simples no PySpark (sem catálogo); mesmos conceitos |
| 5 | Staging | Disco local | MinIO | `.7z`/`.txt` são temporários; não precisam de versionamento |
| 6 | JARs | Embutidos na imagem | Baixar do Maven em tempo de execução | Funciona sem internet e é reprodutível |

**Delta × Iceberg, em resumo:** os dois oferecem ACID, *time travel*, `MERGE` e evolução de schema. O Delta exige só JARs e duas configurações no Spark. O Iceberg exige configurar um **catálogo** (REST, JDBC, Hive ou Hadoop) desde o início e brilha quando vários engines (Trino, Flink, Spark) leem as mesmas tabelas. Aprendendo Delta, migrar depois é tranquilo.

---

# Parte 2 — Conceitos de Docker e Docker Compose

## 2.1 Os blocos fundamentais

| Conceito | O que é | Analogia |
|---|---|---|
| **Imagem** | Pacote imutável com sistema, bibliotecas e código | A "receita" pronta / um molde |
| **Dockerfile** | Arquivo de texto com as instruções para construir a imagem | A receita escrita |
| **Container** | Uma instância em execução de uma imagem | O bolo feito a partir da receita |
| **Volume** | Armazenamento que sobrevive ao container | Um HD externo plugado no container |
| **Bind mount** | Pasta do seu computador montada dentro do container | Uma pasta compartilhada |
| **Rede** | Rede virtual entre containers | Uma LAN privada |
| **Docker Compose** | Arquivo YAML que descreve vários containers juntos | A "planta" do ambiente inteiro |

**Containers são descartáveis.** Tudo que é escrito dentro do container e não está num volume ou bind mount **some** quando ele é removido. Por isso:
- dados do MinIO → **volume**;
- seu código → **bind mount** (você edita no host e o container vê na hora);
- arquivos temporários do Spark → **volume**.

## 2.2 Sintaxe do Dockerfile

| Instrução | Para que serve | Exemplo |
|---|---|---|
| `FROM` | Imagem base | `FROM python:3.11-slim-bookworm` |
| `ARG` | Variável **só durante o build** | `ARG DELTA_VERSION=3.2.0` |
| `ENV` | Variável disponível **no container** | `ENV PYTHONPATH=/app` |
| `RUN` | Executa um comando no build (gera uma camada) | `RUN pip install -r requirements.txt` |
| `COPY` | Copia arquivos do host para a imagem | `COPY requirements.txt /tmp/` |
| `WORKDIR` | Diretório de trabalho padrão | `WORKDIR /app` |
| `USER` | Usuário que executa os comandos seguintes | `USER app` |
| `EXPOSE` | Documenta a porta usada (não publica) | `EXPOSE 8888` |
| `CMD` | Comando padrão ao iniciar o container | `CMD ["jupyter", "lab"]` |

**Cache de camadas.** Cada `RUN`/`COPY` é uma camada em cache. Se uma camada muda, todas as seguintes são refeitas. Então coloque **o que muda pouco primeiro** (sistema, Java, JARs) e **o que muda muito por último** (código). Copie `requirements.txt` e instale as dependências **antes** de copiar o código.

## 2.3 Sintaxe do Docker Compose (YAML)

YAML usa **indentação com espaços** (nunca tab) para indicar hierarquia.

```yaml
name: meu-projeto              # nome do projeto (prefixo dos containers/volumes)

services:                      # cada serviço vira um container
  meu-servico:
    image: nginx:1.27          # usa uma imagem pronta...
    build: .                   # ...ou constrói a partir de um Dockerfile
    ports:
      - "127.0.0.1:8080:80"    # host:container (só acessível na sua máquina)
    environment:
      CHAVE: ${VARIAVEL}       # valor vem do arquivo .env
    volumes:
      - dados:/data            # volume nomeado
      - ./codigo:/app          # bind mount
    depends_on:
      outro-servico:
        condition: service_completed_successfully

volumes:
  dados:                       # declara o volume nomeado
```

**Interpolação de variáveis.** O Compose lê automaticamente o arquivo `.env` na mesma pasta:
- `${VAR}` usa o valor de `VAR`;
- `${VAR:-padrao}` usa `padrao` se `VAR` não existir;
- `${VAR:?mensagem}` **interrompe** com erro se `VAR` não existir (ótimo para senhas obrigatórias).

**Rede.** O Compose cria uma rede própria em que cada serviço é encontrado **pelo nome**. Dentro do container `spark`, o MinIO está em `http://minio:9000`, e não em `localhost`. Esse é um erro clássico.

## 2.4 Comandos essenciais

```bash
docker compose up -d --build      # constrói (se preciso) e sobe tudo em segundo plano
docker compose ps                 # lista os containers e o estado de cada um
docker compose logs -f spark      # acompanha o log de um serviço
docker compose exec spark bash    # abre um terminal dentro do container
docker compose stop               # para os containers (mantém tudo)
docker compose down               # remove containers e rede (volumes ficam)
docker compose down -v            # ⚠️ remove também os VOLUMES (apaga o lake!)
docker compose config             # mostra o YAML final, com variáveis resolvidas (ótimo para depurar)
```

---

# Parte 3 — Estrutura do repositório e Git

## 3.1 Estrutura final

```
rais-lakehouse/
├── .github/
│   └── workflows/
│       └── ci.yml                # CI: lint + testes a cada push/PR
├── config/
│   ├── __init__.py
│   └── settings.py               # caminhos e parâmetros (lidos de variáveis de ambiente)
├── docker/
│   ├── minio/
│   │   ├── init-minio.sh         # cria bucket, usuário e política
│   │   └── policy-rais.json      # permissão restrita ao bucket
│   └── spark/
│       └── Dockerfile            # imagem Python + Java + PySpark + Delta
├── docs/
│   ├── decisoes.md               # ADRs (Parte 1.3)
│   └── dicionario.md             # colunas da RAIS que você usa
├── notebooks/                    # exploração (não é código de produção)
├── scripts/
│   ├── __init__.py
│   ├── smoke_test.py             # teste de ponta a ponta da infraestrutura
│   └── bench.sh                  # benchmark de tuning
├── src/
│   ├── __init__.py
│   ├── utils.py                  # SparkSession e funções auxiliares
│   ├── delta_io.py               # leitura/escrita Delta
│   ├── dims.py                   # tabelas de domínio
│   ├── ingest.py                 # download e extração
│   ├── bronze.py
│   ├── silver.py
│   ├── gold.py
│   ├── checks.py                 # validações de qualidade
│   └── run_pipeline.py           # orquestra as etapas
├── staging/                      # landing/raw (NÃO versionado)
├── tests/
│   ├── conftest.py
│   └── test_utils.py
├── .dockerignore
├── .env.example                  # modelo de configuração (versionado)
├── .gitignore
├── docker-compose.yml
├── LICENSE
├── Makefile                      # atalhos de comandos
├── pyproject.toml                # configuração de ruff e pytest
├── README.md
├── requirements.txt              # dependências de execução
└── requirements-dev.txt          # dependências de desenvolvimento
```

**Por que essa separação?**
- `src/` guarda o código de produção, que é importável e testável. `notebooks/` é só para explorar.
- `config/` separa **configuração** de **lógica**: trocar ambiente não exige mudar código.
- `docker/` concentra a infraestrutura, e `docs/` concentra as decisões e o conhecimento do domínio.

## 3.2 Criar o repositório

```bash
mkdir rais-lakehouse && cd rais-lakehouse
git init -b main

mkdir -p .github/workflows config docker/minio docker/spark docs notebooks scripts src staging tests
touch config/__init__.py scripts/__init__.py src/__init__.py staging/.gitkeep
```

**`.gitignore`**
```gitignore
# Segredos
.env

# Dados (nunca versionar)
staging/*
!staging/.gitkeep
*.7z
*.parquet

# Python
__pycache__/
*.pyc
.venv/
.pytest_cache/
.ruff_cache/

# Jupyter
.ipynb_checkpoints/

# Spark
spark-warehouse/
metastore_db/
derby.log
```

**`.dockerignore`** (o que **não** vai para o contexto de build da imagem, o que deixa o build mais rápido e seguro)
```gitignore
.git
.env
staging
.venv
**/__pycache__
.ipynb_checkpoints
```

## 3.3 Regras de ouro do repositório

1. **Nunca** versione dados nem segredos (`.env`, senhas, chaves).
2. Versione um `.env.example` com valores fictícios, para documentar o que é necessário.
3. Faça um commit pequeno por passo concluído (veja a Parte 16).

### Checkpoint
```bash
git status        # deve mostrar só arquivos de estrutura, nada de dados
git add . && git commit -m "chore: estrutura inicial do projeto"
```

---

# Parte 4 — Infraestrutura: Dockerfile, Compose e MinIO

## 4.1 Conceitos de MinIO e S3

- **Object storage** guarda **objetos** (arquivos + metadados) dentro de **buckets**, acessados por API HTTP (o padrão S3).
- Não existem diretórios de verdade: `bronze/rais_vinculos/ano=2022/arq.parquet` é só o **nome (chave)** do objeto. As "pastas" são uma convenção visual.
- O Spark acessa S3 pelo conector **S3A** (biblioteca `hadoop-aws`), com caminhos `s3a://bucket/caminho`.
- O MinIO exige **path-style** (`http://minio:9000/rais/...`) em vez de *virtual-host style* (`http://rais.minio:9000/...`).
- **Princípio do menor privilégio:** o usuário *root* do MinIO serve só para administrar. A aplicação usa um usuário próprio, com acesso **apenas** ao bucket `rais`.

## 4.2 Versões

| Componente | Versão | Observação |
|---|---|---|
| Python | 3.11 | |
| Java | 17 | requisito do Spark 3.5 |
| PySpark | 3.5.3 | sem ANSI por padrão (o 4.x ativa) |
| delta-spark | 3.2.0 | compatível com Spark 3.5 (confirme a matriz na documentação do Delta) |
| hadoop-aws | 3.3.4 | mesma versão do Hadoop embutido no PySpark 3.5 |
| aws-java-sdk-bundle | 1.12.262 | dependência do hadoop-aws 3.3.4 |

> **Por que fixar versões?** Com versões fixas, o build de hoje e o de daqui a um ano produzem a mesma imagem. Nunca use `latest` em projeto sério: ele muda sem aviso.

## 4.3 Dependências Python

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

## 4.4 Dockerfile do Spark

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

## 4.5 Inicialização do MinIO

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

## 4.6 Variáveis de ambiente

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

## 4.7 docker-compose.yml

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
- **`cpus` e `mem_limit`:** limitam o container. As configurações do Spark precisam caber **dentro** desses limites (Parte 14).
- **Volume nomeado `minio-data`:** para guardar em uma pasta específica do servidor (ex.: um disco dedicado), troque por bind mount: `- /mnt/dados/minio:/data`.
- No **Docker Desktop** (Windows/Mac), o limite de memória do Docker Desktop precisa ser maior que `CONTAINER_MEM`.

## 4.8 Makefile (atalhos)

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

## 4.9 Subindo tudo

```bash
mkdir -p staging
make up            # ou: docker compose up -d --build
make ps            # minio "running", minio-init "exited (0)", spark "running"
docker compose logs minio-init      # deve terminar com "[init] MinIO pronto."
```
Acesse:
- **JupyterLab:** http://localhost:8888 (use o `JUPYTER_TOKEN`)
- **Console MinIO:** http://localhost:9001 (usuário root), se disponível na sua versão

## 4.10 Teste de fumaça

O teste usa a função `get_spark` da Parte 7. Crie primeiro `config/settings.py` e `src/utils.py` (Parte 7) e depois volte aqui.

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

# Parte 5 — Fundamentos de PySpark

Abra o JupyterLab (http://localhost:8888) e crie `notebooks/01_fundamentos.ipynb`. Esta parte usa dados pequenos em memória, sem RAIS.

## 5.1 SparkSession — a porta de entrada

```python
from pyspark.sql import SparkSession, functions as F, Window

spark = SparkSession.builder.master("local[2]").appName("estudo").getOrCreate()
```
**Conceito:** o PySpark é a API Python do Apache Spark, que roda na JVM (por isso a imagem tem Java). A `SparkSession` é o ponto de entrada, e só existe uma por processo. Enquanto ela existir, o painel de execução fica em http://localhost:4040.

**Convenção de imports:** `from pyspark.sql import functions as F` é o padrão da comunidade. Evite `from pyspark.sql.functions import *`, que sobrescreve funções nativas do Python como `sum`, `max` e `round`.

## 5.2 DataFrame

Um DataFrame é uma tabela **distribuída** (dividida em partições) e **imutável** (cada operação gera um DataFrame novo).

```python
dados = [
    (1, "Ana",    "F", "PE", 3200.50, "2021-03-01"),
    (2, "Bruno",  "M", "PE", 4100.00, "2020-07-15"),
    (3, "Carla",  "F", "SP", 5800.00, "2019-01-10"),
    (4, "Diego",  "M", "SP", 2900.00, "2022-11-05"),
    (5, "Elisa",  "F", "BA", 3500.00, "2021-09-20"),
    (6, "Felipe", "M", "BA", 3900.00, "2018-02-14"),
]
df = spark.createDataFrame(dados, ["id", "nome", "sexo", "uf", "salario", "admissao"])

df.show()          # mostra as primeiras linhas
df.printSchema()   # mostra o schema (nomes e tipos)
df.count()         # conta as linhas
df.columns         # lista as colunas
```

## 5.3 Transformações básicas

```python
# Selecionar colunas
df.select("nome", "salario")
df.select(F.col("nome"), (F.col("salario") * 2).alias("dobro"))

# Filtrar linhas (filter e where são sinônimos)
df.filter(F.col("salario") > 3500)
df.filter((F.col("uf") == "PE") & (F.col("salario") > 3000))   # & = E, | = OU, ~ = NÃO

# Criar ou alterar coluna
df = df.withColumn("salario_anual", F.col("salario") * 13)

# Condicional (equivale ao CASE WHEN do SQL)
df = df.withColumn(
    "faixa",
    F.when(F.col("salario") < 3000, "baixa")
     .when(F.col("salario") < 4500, "media")
     .otherwise("alta"),
)

# Converter tipos
df = df.withColumn("admissao", F.to_date("admissao"))
df = df.withColumn("id", F.col("id").cast("string"))

# Renomear e remover
df = df.withColumnRenamed("nome", "nome_completo").drop("salario_anual")

# Ordenar
df.orderBy(F.col("salario").desc())
```
> Em condições combinadas, **use parênteses** em cada comparação: `(a > 1) & (b < 2)`. Sem eles, a precedência dos operadores do Python gera erro.

## 5.4 Agregações

```python
(df.groupBy("uf")
   .agg(
       F.count("*").alias("qtd"),
       F.round(F.avg("salario"), 2).alias("salario_medio"),
       F.sum("salario").alias("massa_salarial"),
       F.percentile_approx("salario", 0.5).alias("mediana"),
   )
   .orderBy("uf")
   .show())
```
**Boa prática:** sempre dê nome às colunas agregadas com `.alias()`. Sem isso, o nome vira algo como `avg(salario)`, que é ruim de usar depois.

## 5.5 Joins

```python
ufs = spark.createDataFrame(
    [("PE", "Pernambuco"), ("SP", "São Paulo"), ("BA", "Bahia")], ["uf", "nome_uf"]
)

df.join(ufs, on="uf", how="left")                    # left, inner, right, full, left_anti...
df.join(F.broadcast(ufs), on="uf", how="left")       # tabela pequena -> broadcast
```
**Conceito:** um join normal faz *shuffle* (redistribui as duas tabelas pela chave). Com `broadcast`, o Spark copia a tabela pequena inteira para todas as tarefas e evita o shuffle. Use em **dimensões** (tabelas de códigos e rótulos).

## 5.6 Window functions

```python
w = Window.partitionBy("uf").orderBy(F.col("salario").desc())

df.withColumn("rank_na_uf", F.row_number().over(w)).show()
df.withColumn("media_da_uf", F.avg("salario").over(Window.partitionBy("uf"))).show()
```
Diferente do `groupBy`, uma window **não reduz** as linhas: ela calcula um valor por linha olhando para um grupo.

## 5.7 Lazy evaluation — o conceito mais importante

- **Transformações** (`select`, `filter`, `withColumn`, `groupBy`, `join`) **não executam nada**. Elas só montam um plano.
- **Ações** (`show`, `count`, `collect`, `toPandas`, `write`) **disparam a execução**.

```python
plano = df.filter(F.col("uf") == "PE").select("nome_completo")   # nada rodou ainda
plano.explain()                                                  # mostra o plano
plano.show()                                                     # agora executou
```
**Por que importa:** o otimizador (Catalyst) enxerga o plano inteiro antes de executar. Por exemplo, ele aplica o filtro antes de ler colunas desnecessárias (*predicate pushdown*). Por isso, **evite `collect()` e `toPandas()` em dados grandes**: eles trazem tudo para a memória do driver.

## 5.8 Partições e escrita

```python
df.rdd.getNumPartitions()   # quantas partições o DataFrame tem
df.repartition(4)           # redistribui (com shuffle)
df.coalesce(1)              # junta partições (sem shuffle completo)

df.write.mode("overwrite").partitionBy("uf").parquet("/tmp/estudo_parquet")
spark.read.parquet("/tmp/estudo_parquet").filter("uf = 'PE'").show()
```
`partitionBy("uf")` cria pastas `uf=PE/`, `uf=SP/` e assim por diante. Uma consulta com filtro por `uf` lê **só a pasta necessária** (*partition pruning*).

**Modos de escrita**
| Modo | Comportamento |
|---|---|
| `error` (padrão) | Falha se o destino existir |
| `overwrite` | Substitui |
| `append` | Adiciona |
| `ignore` | Não faz nada se existir |

## 5.9 SQL também funciona

```python
df.createOrReplaceTempView("pessoas")
spark.sql("SELECT uf, AVG(salario) AS media FROM pessoas GROUP BY uf").show()
```
A API de DataFrame e o SQL geram o **mesmo plano**. Use o que deixar o código mais legível.

## Exercícios

1. Qual a média salarial por sexo?
2. Quem tem o maior salário em cada UF? (dica: window + `row_number`)
3. Crie `ano_admissao` e conte as admissões por ano.
4. Grave o resultado do exercício 1 em Parquet e leia de volta.
5. Rode `.explain()` num `filter + groupBy` e encontre o `Exchange` (é o shuffle).

<details>
<summary>Gabarito (tente antes de abrir)</summary>

```python
# 1
df.groupBy("sexo").agg(F.round(F.avg("salario"), 2).alias("media")).show()

# 2
w = Window.partitionBy("uf").orderBy(F.col("salario").desc())
df.withColumn("r", F.row_number().over(w)).filter("r = 1").drop("r").show()

# 3
(df.withColumn("ano_admissao", F.year("admissao"))
   .groupBy("ano_admissao").count().orderBy("ano_admissao").show())

# 4
r = df.groupBy("sexo").agg(F.avg("salario").alias("media"))
r.write.mode("overwrite").parquet("/tmp/media_sexo")
spark.read.parquet("/tmp/media_sexo").show()

# 5
df.filter(F.col("salario") > 3000).groupBy("uf").count().explain()
```
</details>

### Checkpoint
Você consegue explicar com suas palavras: (a) a diferença entre transformação e ação; (b) o que é shuffle e por que ele é caro; (c) por que Parquet particionado é mais rápido que CSV.

---

# Parte 6 — Conhecendo a RAIS

## 6.1 Conceito

A **RAIS** (Relação Anual de Informações Sociais) é o registro anual dos vínculos formais de trabalho, mantido pelo Ministério do Trabalho e Emprego.

- Os microdados públicos são **anonimizados**: não há CPF nem identificador do trabalhador. **Cada linha é um vínculo, não uma pessoa**, e não é possível deduplicar pessoas.
- Há duas bases: **vínculos** (usaremos) e **estabelecimentos** (fica como evolução).
- A partir do ano-base 2019, parte das empresas passou a declarar pelo **eSocial**, e a cobertura foi migrando por grupos de empresas ao longo dos anos. Leia as notas técnicas de cada ano antes de comparar séries.

**Formato dos arquivos de vínculos**
- Compactados em `.7z`, **divididos por região** (nomes parecidos com `RAIS_VINC_PUB_NORDESTE.7z`, `..._SP.7z`, `..._NI.7z`; "NI" = não identificado). Confira os nomes reais de cada ano.
- Separador `;`, encoding `latin-1` (ISO-8859-1) e decimal com **vírgula** (`1234,56`).
- Cabeçalho com acentos e espaços (ex.: `Vl Remun Média Nom`).
- Valores "ignorado" representados por códigos que variam por coluna (`-1`, `0`, `{ñ class}`...).

## 6.2 Prática

1. Na página de estatísticas do trabalho do MTE (`gov.br/trabalho-e-emprego`, seção RAIS/microdados), baixe:
   - o **dicionário/layout** de vínculos do ano escolhido;
   - **um** arquivo regional de **um** ano (sugestão: 2022 + Nordeste).
2. Coloque o `.7z` em `staging/landing/2022/`.
3. Documente em `docs/dicionario.md` as colunas usadas. Os nomes abaixo estão na forma **normalizada** pelo nosso código (minúsculas, sem acento, `_` no lugar de espaços e símbolos):

| Coluna normalizada | Significado | Tipo na silver | Observação |
|---|---|---|---|
| `municipio` | Código IBGE (6 dígitos) do município | string | 2 primeiros dígitos = UF |
| `cnae_2_0_classe` | Atividade econômica (5 dígitos) | string | 2 primeiros = divisão |
| `cbo_ocupacao_2002` | Ocupação | string | **zeros à esquerda importam** |
| `vinculo_ativo_31_12` | Ativo em 31/12 | boolean | geralmente `1`/`0` |
| `sexo_trabalhador` | Sexo | int | confira os códigos |
| `escolaridade_apos_2005` | Grau de instrução | int | códigos 1–11 |
| `raca_cor` | Raça/cor | int | confira os códigos |
| `idade` | Idade | int | |
| `tempo_emprego` | Tempo de emprego (meses) | decimal | vírgula decimal |
| `mes_desligamento` | Mês do desligamento | int | `0` = não desligado (confirme) |
| `motivo_desligamento` | Motivo | int | |
| `tamanho_estabelecimento` | Faixa de tamanho | int | |
| `natureza_juridica` | Natureza jurídica | string | |
| `vl_remun_dezembro_nom` | Remuneração de dezembro (R$ nominal) | decimal | |
| `vl_remun_media_nom` | Remuneração média do ano (R$ nominal) | decimal | |
| `vl_remun_dezembro_sm` | Remuneração de dezembro em salários mínimos | decimal | **comparável entre anos** |
| `vl_remun_media_sm` | Remuneração média em salários mínimos | decimal | **comparável entre anos** |

### Checkpoint
Você tem o `.7z` em `staging/landing/2022/`, o dicionário em mãos e o `docs/dicionario.md` preenchido.

---

# Parte 7 — Código base: configuração e utilitários

## 7.1 Conceito: configuração por ambiente

Os princípios da metodologia **12-Factor App** orientam esta parte: a configuração vem de **variáveis de ambiente**, e não fica fixa no código. O mesmo código roda no seu notebook, no container e num servidor, mudando só o ambiente.

## 7.2 `config/settings.py`

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

## 7.3 `src/utils.py`

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
- **`try_cast`:** devolve `NULL` em vez de erro quando a conversão falha. Em dado público "sujo", isso evita que uma linha estragada derrube 50 milhões de linhas boas. A Parte 15 mede quantos `NULL` surgiram.
- **Crases** (`` `nome` ``) protegem nomes de coluna dentro de expressões SQL.
- **Type hints** (`-> Column`) e **docstrings** documentam o contrato de cada função.
- **Por que `decimal` e não `double` para dinheiro?** `double` tem erro de arredondamento binário (`0.1 + 0.2 != 0.3`), e `decimal` é exato.

## 7.4 `src/delta_io.py` — leitura e escrita Delta

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

## 7.5 `src/dims.py` — tabelas de domínio

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
Rode também `make smoke` (Parte 4.10). Depois, commit: `feat: configuração e utilitários`.

---

# Parte 8 — Ingestão (landing → raw)

## 8.1 Conceito

Ingerir é trazer o dado da fonte **sem alterá-lo**. Separe **baixar** de **extrair**: se um passo falhar, você refaz só ele. E torne cada passo **idempotente**: se o arquivo já existe, ele é pulado.

## 8.2 `src/ingest.py`

```python
"""Download e extração dos microdados da RAIS."""
import ftplib
from pathlib import Path

import py7zr

from config.settings import LANDING, RAW

# CONFIRME o endereço atual na página de microdados do MTE: ele já mudou no passado.
FTP_HOST = "ftp.mtps.gov.br"
FTP_PATH = "/pdet/microdados/RAIS/{ano}/"


def baixar(ano: int, filtro: str = "VINC") -> list[Path]:
    """Baixa os .7z de vínculos de um ano para landing/<ano>/ (pula os já baixados)."""
    destino = LANDING / str(ano)
    destino.mkdir(parents=True, exist_ok=True)
    baixados: list[Path] = []

    with ftplib.FTP(FTP_HOST, timeout=120) as ftp:
        ftp.login()
        ftp.cwd(FTP_PATH.format(ano=ano))
        for nome in ftp.nlst():
            if filtro not in nome.upper() or not nome.lower().endswith(".7z"):
                continue
            arquivo = destino / nome
            if arquivo.exists():
                print(f"[skip] {nome}")
            else:
                print(f"[baixando] {nome}")
                parcial = arquivo.with_suffix(".part")
                with open(parcial, "wb") as f:
                    ftp.retrbinary(f"RETR {nome}", f.write)
                parcial.rename(arquivo)          # só "existe" quando terminou
            baixados.append(arquivo)
    return baixados


def extrair(ano: int) -> Path:
    """Extrai todos os .7z de landing/<ano>/ para raw/<ano>/."""
    origem, destino = LANDING / str(ano), RAW / str(ano)
    destino.mkdir(parents=True, exist_ok=True)

    arquivos = sorted(origem.glob("*.7z"))
    if not arquivos:
        raise FileNotFoundError(f"Nenhum .7z em {origem}")

    for arq in arquivos:
        print(f"[extraindo] {arq.name}")
        with py7zr.SevenZipFile(arq, "r") as z:
            z.extractall(path=destino)
    return destino


if __name__ == "__main__":
    import sys

    extrair(int(sys.argv[1]))
```

**Detalhe de boa prática:** o download grava primeiro em `.part` e só renomeia no fim. Assim, um download interrompido nunca é confundido com um arquivo completo.

**Para começar:** baixe o `.7z` manualmente pelo navegador para `staging/landing/2022/` e use só o `extrair`.

```bash
docker compose exec spark python -m src.ingest 2022
```

### Checkpoint
```bash
docker compose exec spark bash -c "ls -lh /staging/raw/2022/ && head -c 500 /staging/raw/2022/*.txt"
```
Deve aparecer o cabeçalho separado por `;`. Acentos estranhos são esperados, porque o encoding é tratado na bronze.

---

# Parte 9 — Bronze

## 9.1 Conceito

A bronze é a **cópia fiel e eficiente** da origem:
- **Tudo como `string`**: mudanças de formato entre anos não quebram a carga, e tipar é tarefa da silver.
- **Nomes normalizados**: Parquet e Delta não lidam bem com espaços e acentos em nomes de coluna.
- **Particionada por `ano`** e gravada com `replaceWhere`: reprocessar 2022 não toca em 2021.
- **`mergeSchema=True`**: se um ano novo trouxer uma coluna nova, o Delta a **adiciona** à tabela, e os anos antigos ficam com `NULL` nela. Sem essa opção, o Delta **recusa** a gravação (*schema enforcement*).
- **Rastreabilidade**: guardamos o arquivo de origem de cada linha.

## 9.2 `src/bronze.py`

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

## 9.3 Explorando (notebook `02_bronze.ipynb`)

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
3. Confira se as colunas da Parte 6 existem: `set(esperadas) - set(b.columns)`.
4. Compare o tamanho do `.txt` com o da bronze (console do MinIO). Qual é a taxa de compressão?
5. Rode a bronze de 2022 **duas vezes** e confirme que a contagem **não dobrou** (idempotência).

### Checkpoint
A pasta `bronze/rais_vinculos/ano=2022/` existe no MinIO, com `_delta_log/`. Depois disso, você pode apagar `staging/raw/2022/`, porque o `.7z` em `landing` continua como fonte. Commit: `feat: camada bronze`.

---

# Parte 10 — Silver

## 10.1 Conceito

A silver é onde o dado fica **confiável**:
1. Seleciona só as colunas úteis.
2. Converte os tipos: decimal com vírgula vira `decimal`, códigos pequenos viram `int`.
3. Valida formatos: município com 6 dígitos, CNAE com 5, idade plausível.
4. Transforma valores inválidos ou "ignorados" em `NULL`.
5. Deriva campos: UF a partir do município, divisão CNAE a partir da classe.
6. **Mantém uma linha por vínculo**: a silver **não filtra linhas**, só limpa valores. Por isso a contagem da silver deve bater com a da bronze.

**Códigos com zero à esquerda** (CBO, CNAE, município) ficam como **string**. Converter `"012345"` para número vira `12345` e destrói a informação. Já códigos pequenos de categoria (sexo, escolaridade) viram `int`, o que unifica `"01"` e `"1"`.

## 10.2 `src/silver.py`

```python
"""Silver: tipagem, validação e padronização da RAIS."""
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

from config.settings import BRONZE, SILVER
from src.delta_io import gravar_ano, ler
from src.utils import col_or_null, get_spark, to_decimal, to_int

# Sem estas colunas não faz sentido continuar
OBRIGATORIAS = ["municipio", "vinculo_ativo_31_12", "vl_remun_dezembro_nom"]


def construir_silver(ano: int, spark: SparkSession | None = None) -> None:
    spark = spark or get_spark("rais-silver")
    b = ler(spark, BRONZE).filter(F.col("ano") == ano)

    faltando = [c for c in OBRIGATORIAS if c not in b.columns]
    if faltando:
        raise ValueError(f"Ano {ano}: colunas obrigatórias ausentes: {faltando}")

    # 1) Seleção + tipagem
    s = b.select(
        F.col("ano"),
        col_or_null(b, "municipio").alias("cod_municipio"),
        col_or_null(b, "cnae_2_0_classe").alias("cnae_classe"),
        col_or_null(b, "cbo_ocupacao_2002").alias("cbo"),
        col_or_null(b, "natureza_juridica").alias("natureza_juridica"),
        to_int(b, "sexo_trabalhador").alias("sexo"),
        to_int(b, "escolaridade_apos_2005").alias("escolaridade"),
        to_int(b, "raca_cor").alias("raca_cor"),
        to_int(b, "idade").alias("idade"),
        to_int(b, "tamanho_estabelecimento").alias("tamanho_estab"),
        to_int(b, "mes_desligamento").alias("mes_desligamento"),
        to_int(b, "motivo_desligamento").alias("motivo_desligamento"),
        to_decimal(b, "tempo_emprego", 10, 1).alias("tempo_emprego_meses"),
        (F.trim(F.col("vinculo_ativo_31_12")) == "1").alias("vinculo_ativo"),
        to_decimal(b, "vl_remun_dezembro_nom").alias("remun_dezembro_nom"),
        to_decimal(b, "vl_remun_media_nom").alias("remun_media_nom"),
        to_decimal(b, "vl_remun_dezembro_sm").alias("remun_dezembro_sm"),
        to_decimal(b, "vl_remun_media_sm").alias("remun_media_sm"),
    )

    # 2) Validação: valor fora do padrão vira NULL
    s = (
        s
        .withColumn("cod_municipio",
                    F.when(F.col("cod_municipio").rlike(r"^\d{6}$"), F.col("cod_municipio")))
        .withColumn("cnae_classe",
                    F.when(F.col("cnae_classe").rlike(r"^\d{5}$"), F.col("cnae_classe")))
        .withColumn("idade", F.when(F.col("idade").between(14, 100), F.col("idade")))
        # 0 = não desligado -> NULL (CONFIRME no dicionário)
        .withColumn("mes_desligamento",
                    F.when(F.col("mes_desligamento").between(1, 12), F.col("mes_desligamento")))
    )

    # 3) Campos derivados (substring de NULL é NULL)
    s = (
        s
        .withColumn("cod_uf", F.substring("cod_municipio", 1, 2))
        .withColumn("cnae_divisao", F.substring("cnae_classe", 1, 2))
        .withColumn("desligado_no_ano", F.col("mes_desligamento").isNotNull())
    )

    gravar_ano(spark, s, SILVER, ano)
    print(f"[silver] {ano} gravado em {SILVER}")


if __name__ == "__main__":
    import sys

    construir_silver(int(sys.argv[1]))
```
```bash
docker compose exec spark python -m src.silver 2022
```

## Exercícios (notebook `03_silver.ipynb`)
1. `printSchema()`: os tipos estão como planejado?
2. Conte os `NULL` por coluna:
   ```python
   s.select([F.sum(F.col(c).isNull().cast("int")).alias(c) for c in s.columns]).show(vertical=True)
   ```
3. Distribuição de `idade` e `remun_dezembro_sm` (`s.describe(...)`). Há valores absurdos?
4. Qual a % de vínculos com `vinculo_ativo = true`?
5. `remun_dezembro_nom = 0` significa o quê no dicionário? Decida se vira `NULL` e registre em `docs/dicionario.md`.

### Checkpoint
- Os tipos estão corretos (`decimal`, `int`, `boolean`, `string`).
- **Contagem da silver = contagem da bronze** do mesmo ano.
- Commit: `feat: camada silver`.

---

# Parte 11 — Gold

## 11.1 Conceito

A gold nasce de **perguntas de negócio**. Cada tabela responde uma pergunta específica e é pequena o bastante para ir direto a um gráfico, um BI ou um relatório.

**Regras de ouro**
- **R$ nominal não é comparável entre anos** (inflação e reajuste do mínimo). Para série histórica, use as colunas em **salários mínimos** (`*_sm`).
- A unidade é **vínculo**, não pessoa. Escreva "vínculos" nos rótulos, nunca "trabalhadores".
- Indicadores de estoque (quantos empregos existem) usam **vínculos ativos em 31/12**.

| Tabela | Pergunta |
|---|---|
| `gold_emprego_uf_ano` | Quantos vínculos ativos e qual a remuneração por UF e ano? |
| `gold_gap_sexo_uf_ano` | Quanto a remuneração média das mulheres representa da dos homens? |
| `gold_top_cnae_uf_ano` | Quais as 10 divisões de atividade com maior massa salarial por UF? |
| `gold_escolaridade_ano` | Como a remuneração varia com a escolaridade? |
| `gold_desligamento_uf_ano` | Qual a proporção de vínculos desligados no ano? |

## 11.2 `src/gold.py`

```python
"""Gold: tabelas analíticas prontas para consumo."""
from pyspark.sql import DataFrame, SparkSession, Window
from pyspark.sql import functions as F

from config.settings import GOLD, SILVER
from src.delta_io import gravar_tabela, ler
from src.dims import dim_escolaridade, dim_sexo, dim_uf
from src.utils import get_spark


def emprego_uf(ativos: DataFrame, uf: DataFrame) -> DataFrame:
    return (
        ativos.groupBy("ano", "cod_uf")
        .agg(
            F.count("*").alias("qtd_vinculos"),
            F.sum("remun_dezembro_nom").alias("massa_salarial_dez_nom"),
            F.round(F.avg("remun_dezembro_nom"), 2).alias("remun_media_dez_nom"),
            F.round(F.avg("remun_dezembro_sm"), 2).alias("remun_media_dez_sm"),
            F.percentile_approx("remun_dezembro_sm", 0.5).alias("remun_mediana_dez_sm"),
        )
        .join(uf, "cod_uf", "left")
    )


def gap_sexo(ativos: DataFrame, uf: DataFrame) -> DataFrame:
    return (
        ativos.groupBy("ano", "cod_uf")
        .agg(
            F.avg(F.when(F.col("sexo") == 2, F.col("remun_dezembro_sm"))).alias("rem_mulher_sm"),
            F.avg(F.when(F.col("sexo") == 1, F.col("remun_dezembro_sm"))).alias("rem_homem_sm"),
        )
        .withColumn("razao_mulher_homem",
                    F.round(F.col("rem_mulher_sm") / F.col("rem_homem_sm"), 3))
        .join(uf, "cod_uf", "left")
    )


def top_cnae(ativos: DataFrame, uf: DataFrame, n: int = 10) -> DataFrame:
    por_cnae = (
        ativos.filter(F.col("cnae_divisao").isNotNull())
        .groupBy("ano", "cod_uf", "cnae_divisao")
        .agg(
            F.count("*").alias("qtd_vinculos"),
            F.sum("remun_dezembro_nom").alias("massa_salarial_dez_nom"),
        )
    )
    w = Window.partitionBy("ano", "cod_uf").orderBy(F.col("massa_salarial_dez_nom").desc())
    return (
        por_cnae.withColumn("posicao", F.row_number().over(w))
        .filter(F.col("posicao") <= n)
        .join(uf, "cod_uf", "left")
    )


def escolaridade(ativos: DataFrame, esc: DataFrame) -> DataFrame:
    return (
        ativos.groupBy("ano", "escolaridade")
        .agg(
            F.count("*").alias("qtd_vinculos"),
            F.round(F.avg("remun_dezembro_sm"), 2).alias("remun_media_dez_sm"),
        )
        .join(esc, "escolaridade", "left")
    )


def desligamento(silver: DataFrame, uf: DataFrame) -> DataFrame:
    return (
        silver.groupBy("ano", "cod_uf")
        .agg(
            F.count("*").alias("qtd_vinculos_no_ano"),
            F.sum(F.col("desligado_no_ano").cast("int")).alias("qtd_desligados"),
        )
        .withColumn("taxa_desligamento",
                    F.round(F.col("qtd_desligados") / F.col("qtd_vinculos_no_ano"), 4))
        .join(uf, "cod_uf", "left")
    )


def construir_gold(spark: SparkSession | None = None) -> None:
    spark = spark or get_spark("rais-gold")

    silver = ler(spark, SILVER)
    ativos = silver.filter(F.col("vinculo_ativo"))
    uf = F.broadcast(dim_uf(spark))
    esc = F.broadcast(dim_escolaridade(spark))

    tabelas = {
        "gold_emprego_uf_ano": emprego_uf(ativos, uf),
        "gold_gap_sexo_uf_ano": gap_sexo(ativos, uf),
        "gold_top_cnae_uf_ano": top_cnae(ativos, uf),
        "gold_escolaridade_ano": escolaridade(ativos, esc),
        "gold_desligamento_uf_ano": desligamento(silver, uf),
    }
    for nome, df in tabelas.items():
        gravar_tabela(df.coalesce(4), f"{GOLD}/{nome}")   # poucos arquivos: tabela pequena
        print(f"[gold] {nome}")

    _ = dim_sexo  # disponível para enriquecer novas tabelas (exercício)


if __name__ == "__main__":
    construir_gold()
```

**Boa prática aplicada:** cada tabela é uma **função pura** (recebe DataFrames e devolve DataFrame). Isso torna o código **testável**: você chama `gap_sexo(df_de_teste, dim)` num teste, sem MinIO (Parte 15).

## 11.3 Consultando (notebook `04_gold.ipynb`)

```python
from pyspark.sql import functions as F

from config.settings import GOLD
from src.delta_io import ler
from src.utils import get_spark

spark = get_spark()
g = ler(spark, f"{GOLD}/gold_emprego_uf_ano")
g.orderBy(F.col("qtd_vinculos").desc()).show(10)

# Gold é pequena: pode ir para o pandas e virar gráfico
pdf = g.filter("uf = 'PE'").orderBy("ano").toPandas()
pdf.plot(x="ano", y="remun_media_dez_sm", marker="o")
```
> Use `toPandas()` **só** em tabelas gold. Em silver ou bronze, a memória estoura.

## Exercícios
1. Quais as 5 UFs com mais vínculos ativos?
2. Onde a `razao_mulher_homem` é menor?
3. Crie `gold_porte_ano` (remuneração por `tamanho_estab`).
4. Crie `gold_faixa_etaria_ano` (faixas `<25`, `25–39`, `40–59`, `60+` com `F.when`).
5. Exporte uma tabela gold para CSV e abra no Excel ou Power BI:
   ```python
   g.coalesce(1).write.mode("overwrite").option("header", True).csv("/staging/export/emprego")
   ```

### Checkpoint
- A soma de `qtd_vinculos` em `gold_emprego_uf_ano` bate com `silver.filter("vinculo_ativo").count()`.
- Nenhuma linha tem `uf` nula. Se houver, existe código de município fora da dimensão, e vale investigar.
- Commit: `feat: camada gold`.

---

# Parte 12 — Pipeline completo (2019 → hoje)

## 12.1 Conceito

Um pipeline executa os mesmos passos para cada ano, de forma **idempotente**: rodar duas vezes produz o mesmo resultado. Isso vem de três escolhas: arquivos já baixados são pulados, a bronze e a silver usam `replaceWhere` por ano, e a gold é recriada inteira.

**Uma `SparkSession` para tudo:** criar a sessão custa segundos e inicia uma JVM. O pipeline cria **uma** sessão e a passa para todas as etapas.

## 12.2 `src/run_pipeline.py`

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

## 12.3 Execução

```bash
# Um ano, de ponta a ponta
make pipeline ANOS=2022

# Vários anos
make pipeline ANOS="2019 2020 2021 2022 2023 2024"

# Só refazer silver e gold (bronze já pronta)
make pipeline ANOS=2022 ETAPAS="silver gold"
```
> Antes de rodar todos os anos, coloque os `.7z` de cada ano em `staging/landing/<ano>/` e confira o espaço em disco.

### Checkpoint
```python
from pyspark.sql import functions as F
g = ler(spark, f"{GOLD}/gold_emprego_uf_ano")
g.groupBy("ano").agg(F.sum("qtd_vinculos").alias("vinculos")).orderBy("ano").show()
```
Deve aparecer um total por ano, na casa das dezenas de milhões quando todas as regiões estão carregadas. Se algum ano destoar muito dos outros, veja o Apêndice A (eSocial e versão parcial). Commit: `feat: pipeline completo`.

---

# Parte 13 — Delta Lake na prática

## 13.1 Conceito: o que é uma tabela Delta

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

## 13.2 Operações (notebook `05_delta.ipynb`)

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

# Parte 14 — Tuning: threads, memória e partições

## 14.1 Conceito

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

## 14.2 Os botões

| Botão | Onde | Como pensar |
|---|---|---|
| Threads | `SPARK_THREADS` → `local[N]` | Núcleos do container. Mire em 2–4 GB de `SPARK_MEM` por thread |
| Memória | `SPARK_MEM` → `spark.driver.memory` | 65–75% de `CONTAINER_MEM` |
| Partições de shuffle | `SPARK_SHUFFLE` → `spark.sql.shuffle.partitions` | 100–200 MB por partição e ≥ 2–4× o nº de threads |
| Partições de leitura | `spark.sql.files.maxPartitionBytes` | Padrão 128 MB; aumentar gera menos tarefas, maiores |
| Disco de spill | `spark.local.dir` → volume `spark-tmp` | Precisa de espaço: é para lá que vai o que não cabe na memória |
| AQE | `spark.sql.adaptive.*` | Ligado: o Spark junta partições pequenas sozinho (só reduz, não aumenta) |

## 14.3 Pontos de partida

| RAM do host / núcleos | `CONTAINER_MEM` | `CONTAINER_CPUS` | `SPARK_MEM` | `SPARK_THREADS` | `SPARK_SHUFFLE` |
|---|---|---|---|---|---|
| 8 GB / 4 | 5g | 3 | 3g | 2 | 16 |
| 16 GB / 8 | 11g | 6 | 8g | 4 | 32 |
| 32 GB / 8–12 | 24g | 8 | 18g | 6 | 48 |
| 64 GB / 16 | 48g | 14 | 36g | 12 | 96 |

São **pontos de partida**, não verdades. Ajuste medindo (14.5).

## 14.4 Como calcular o número de partições

1. Descubra o volume do shuffle: rode uma vez e veja *Stages → Shuffle Write* na Spark UI.
2. `partições ≈ volume_do_shuffle / 128 MB`
3. Arredonde para um **múltiplo do número de threads**, para que todas fiquem ocupadas até a última "onda" de tarefas.

Exemplo: shuffle de 6 GB e 4 threads → 6144 / 128 = 48 partições (48 é múltiplo de 4).

## 14.5 Método de ajuste

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

## 14.6 Benchmark

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

## 14.7 Controle dentro do código

```python
df.rdd.getNumPartitions()                       # quantas partições agora
df.repartition(48, "cod_uf")                    # redistribui por chave (com shuffle)
df.coalesce(4)                                  # reduz partições sem shuffle completo
spark.conf.set("spark.sql.shuffle.partitions", "64")   # muda em execução
```
As configurações de **SQL** mudam em execução. As de **memória** e de `master` só valem ao criar a sessão (em notebook, reinicie o kernel).

**Quando virar cluster:** num Spark standalone on-premises, os equivalentes são `spark.executor.instances`, `spark.executor.cores`, `spark.executor.memory` e `spark.cores.max`. A lógica não muda: núcleos por executor × memória por núcleo.

---

# Parte 15 — Qualidade, testes e CI

## 15.1 Conceito

| Tipo | O que verifica | Quando roda | Precisa de MinIO? |
|---|---|---|---|
| **Teste de unidade** | Uma função isolada, com dados minúsculos | A cada commit (CI) | Não |
| **Teste de fumaça** | A infraestrutura funciona de ponta a ponta | Ao subir o ambiente | Sim |
| **Checagem de dados** | O dado real faz sentido | A cada execução do pipeline | Sim |

## 15.2 Configuração: `pyproject.toml`

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

## 15.3 Testes de unidade

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

## 15.4 Checagens de dados

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

## 15.5 CI no GitHub Actions

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

# Parte 16 — Boas práticas de GitHub

## 16.1 Commits (Conventional Commits)

Formato: `tipo(escopo opcional): descrição no imperativo`

| Tipo | Uso | Exemplo |
|---|---|---|
| `feat` | Nova funcionalidade | `feat(gold): tabela de gap salarial por sexo` |
| `fix` | Correção | `fix(silver): tratar CNAE com menos de 5 dígitos` |
| `docs` | Documentação | `docs: explicar tuning no README` |
| `refactor` | Mudança interna sem alterar comportamento | `refactor: centralizar escrita Delta` |
| `test` | Testes | `test: cobrir to_decimal` |
| `chore` | Manutenção | `chore: atualizar delta-spark` |
| `perf` | Performance | `perf: broadcast nas dimensões` |

**Commits pequenos e frequentes.** Um commit deve fazer **uma** coisa. Isso facilita revisar, entender o histórico e desfazer.

## 16.2 Branches e Pull Requests

```bash
git switch -c feat/gold-faixa-etaria       # uma branch por funcionalidade
# ...trabalho e commits...
git push -u origin feat/gold-faixa-etaria  # depois abra um PR no GitHub
```
- A `main` está sempre funcionando.
- Mesmo sozinho, use PRs: o CI roda antes do merge e o PR documenta o porquê da mudança.
- Prefixos: `feat/`, `fix/`, `docs/`, `refactor/`.

## 16.3 README.md (a vitrine do projeto)

Estrutura recomendada:
```markdown
# RAIS Lakehouse

Lakehouse open source on-premises para os microdados da RAIS (2019–2024),
com PySpark, Delta Lake e MinIO orquestrados por Docker Compose.

## Arquitetura
(diagrama + tabela das camadas)

## Stack
PySpark 3.5 · Delta Lake 3.2 · MinIO · Docker Compose · pytest · GitHub Actions

## Como rodar
1. `cp .env.example .env` e preencha
2. `make up`
3. Baixe os .7z para `staging/landing/<ano>/`
4. `make pipeline ANOS=2022`

## Tabelas gold
(o que cada uma responde)

## Decisões técnicas
Ver `docs/decisoes.md`

## Principais aprendizados / resultados
(2 ou 3 achados dos dados + 1 gráfico)

## Limitações
(eSocial, vínculos ≠ pessoas, versão parcial...)

## Fonte dos dados
RAIS/MTE — microdados públicos.
```
**Para portfólio**, as seções que mais pesam são **Decisões técnicas**, **Resultados** (um gráfico vale muito) e **Limitações**. Elas mostram maturidade.

## 16.4 Outros cuidados

- **LICENSE:** escolha uma (MIT é a mais simples) para deixar claro como outros podem usar o código.
- **Tags de versão:** marque marcos com `git tag v0.1.0 && git push --tags` (ex.: v0.1 = bronze/silver, v0.2 = gold).
- **Segredos:** se um `.env` for commitado por engano, **troque as senhas**. Apagar o commit não basta, porque o histórico guarda o conteúdo.
- **Dependências:** atualize de propósito, uma de cada vez, com o CI verde.
- **Issues:** use as *issues* do GitHub como backlog (ex.: "Adicionar RAIS Estabelecimentos").

---

# Apêndice A — Armadilhas conhecidas

1. **O schema muda entre anos.** Por isso a bronze é toda string com `mergeSchema`, e há `col_or_null` e `OBRIGATORIAS`.
2. **eSocial a partir do ano-base 2019.** A forma de declaração mudou gradualmente por grupos de empresas, o que pode afetar comparações históricas. Leia as notas técnicas de cada ano.
3. **Versão parcial × final.** Alguns anos tiveram divulgação parcial antes da final. Use a final e registre a escolha.
4. **Arquivo "NI".** São os não identificados. Inclua-o para ter o total nacional; ele não tem UF válida.
5. **"Ignorado" varia por coluna** (`-1`, `0`, `{ñ class}`). Decida coluna a coluna e documente.
6. **Zeros à esquerda.** CBO, CNAE e município são **string**.
7. **Nominal × salário mínimo.** Para série histórica, use `*_sm`.
8. **Vínculo ≠ pessoa.** Uma pessoa pode ter vários vínculos.
9. **Disco.** Apague `raw` após a bronze (`--limpar-raw`) e monitore o volume do MinIO.
10. **Encoding.** Se `Município` aparecer como `Munic�pio`, o encoding está errado.

# Apêndice B — Solução de problemas

| Sintoma | Causa provável | Solução |
|---|---|---|
| `minio-init` termina com erro | Credenciais ou sintaxe do `mc` | `docker compose logs minio-init`; ajuste o script à versão do `mc` |
| `spark` não sobe | `minio-init` falhou (dependência) | Resolva o `minio-init` primeiro |
| `Connection refused` ao acessar o MinIO | Usou `localhost` dentro do container | Use `http://minio:9000` |
| `ClassNotFoundException: S3AFileSystem` | JAR não baixou no build | Refaça com `docker compose build --no-cache spark` |
| `403` / `InvalidAccessKeyId` | Usuário da aplicação não criado ou sem política | Veja o log do `minio-init`; confira `APP_ACCESS_KEY` |
| `UnknownHostException: rais.minio` | Faltou path-style | `fs.s3a.path.style.access=true` |
| `Permission denied` em `/app` ou `/staging` | UID diferente entre host e container | Ajuste `HOST_UID` (`id -u`) e reconstrua |
| Container morre com código 137 | `mem_limit` estourado | Reduza `SPARK_MEM` ou aumente `CONTAINER_MEM` |
| `OutOfMemoryError` | Heap da JVM pequeno | Menos threads ou mais `SPARK_MEM` |
| Spark UI não abre | Sem sessão ativa ou porta errada | A UI só existe enquanto há sessão; tente 4041 |
| `make` reclama de "missing separator" | Espaços no lugar de TAB no Makefile | Use TAB |

# Apêndice C — Glossário

- **ACID:** atomicidade, consistência, isolamento e durabilidade. Garante que uma transação acontece inteira ou não acontece.
- **AQE:** *Adaptive Query Execution*. O Spark reotimiza o plano durante a execução.
- **Bind mount:** pasta do host montada no container.
- **Broadcast join:** join em que a tabela pequena é copiada para todas as tarefas, sem shuffle.
- **Data skew:** dados concentrados em poucas chaves, gerando tarefas desbalanceadas.
- **Idempotência:** executar várias vezes produz o mesmo resultado.
- **Lazy evaluation:** transformações só executam quando há uma ação.
- **Medallion:** organização em bronze, silver e gold.
- **Partition pruning:** ler só as partições exigidas pelo filtro.
- **S3A:** conector Hadoop/Spark para storage compatível com S3.
- **Schema enforcement / evolution:** recusar ou aceitar mudanças de schema na escrita.
- **Shuffle:** redistribuição de dados entre partições; é a operação mais cara do Spark.
- **Spill:** dados despejados em disco quando não cabem na memória.
- **Time travel:** ler uma versão antiga de uma tabela Delta.
- **Vínculo:** relação de emprego registrada; é a unidade de uma linha na RAIS.

# Apêndice D — Próximos passos

1. **RAIS Estabelecimentos:** some a segunda base e pratique joins grandes e skew.
2. **`MERGE` no Delta:** pratique *upserts* com uma tabela de correções.
3. **Iceberg:** recrie a gold em Iceberg com catálogo REST e compare a experiência.
4. **Consulta SQL:** suba o **Trino** no Compose para consultar o lake por SQL.
5. **Orquestração:** agende o pipeline com **Airflow** ou **Dagster** no mesmo Compose.
6. **Visualização:** suba **Metabase** ou **Superset** no Compose e conecte à gold.
7. **Cluster:** transforme o serviço `spark` em master + workers (Spark standalone) e observe o que muda no tuning.

---

## Checklist final

- [ ] Repositório criado, `.gitignore` e `.env.example` versionados, `.env` fora do Git
- [ ] `make up` sobe minio, minio-init (exit 0) e spark
- [ ] `make smoke` passa
- [ ] Parte 5 concluída (exercícios de fundamentos)
- [ ] Dicionário baixado e `docs/dicionario.md` preenchido
- [ ] Bronze, silver e gold gravadas em Delta no MinIO
- [ ] Contagem silver = bronze e checagens passando
- [ ] Reprocessar um ano não duplica dados
- [ ] Time travel, `OPTIMIZE` e schema enforcement testados
- [ ] Benchmark feito e configuração padrão registrada em `docs/decisoes.md`
- [ ] Testes, lint e CI verdes
- [ ] README com arquitetura, decisões, resultados e limitações
