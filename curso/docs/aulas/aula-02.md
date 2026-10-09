---
aula: 2
titulo: "Docker: imagens, containers e o Dockerfile do Spark"
origem: ['Guia Parte 2.1', 'Guia Parte 2.2', 'Guia Parte 4.2', 'Guia Parte 4.3', 'Guia Parte 4.4']
depende_de: [1]
checks: ['a02_imagem_existe', 'a02_java_17', 'a02_pyspark_delta', 'a02_jars_s3a_delta', 'a02_usuario_nao_root']
---

# Aula 02 — Docker: imagens, containers e o Dockerfile do Spark

<!-- Página GERADA por scripts/gerar_curso.py. Edite aulas.yml e curso/conteudo/. -->

<div class="rl-aula" data-aula="2" data-onde="host" data-lab=""></div>

| | |
| --- | --- |
| Origem no guia | Guia Parte [2.1](../guia/parte-02.md#parte-2-1), Guia Parte [2.2](../guia/parte-02.md#parte-2-2), Guia Parte [4.2](../guia/parte-04.md#parte-4-2), Guia Parte [4.3](../guia/parte-04.md#parte-4-3), Guia Parte [4.4](../guia/parte-04.md#parte-4-4) |
| Depende de | [Aula 01](aula-01.md) |
| Entregas | `docker/spark/Dockerfile`, `requirements.txt`, `requirements-dev.txt`, `.dockerignore` |
| Onde os checks rodam | Host (WSL/Linux) |
| Documento original | [abrir](https://claude.ai/code/artifact/3a17b7ff-ce58-4699-b232-429afbe389e2) |

Ao final desta aula a imagem `rais-spark:local` existe na sua máquina, com Python 3.11, Java 17, PySpark 3.5.3, Delta 3.2.0 e os JARs do S3A, rodando como usuário não-root. Ela é a base de todo o resto do curso.

**Convenção:** <span class="rl-complemento">Complemento didático</span> marca explicações que não estão no guia original. O resto vem do RAIS Lakehouse Guide, com a parte indicada.

## 1. Objetivos e pré-requisitos

### Objetivos de aprendizagem

1. Explicar a diferença entre imagem, container, volume e bind mount.
2. Explicar como as camadas e o cache de build funcionam, e ordenar um Dockerfile para aproveitá-los.
3. Ler e escrever as instruções `FROM`, `ARG`, `ENV`, `RUN`, `COPY`, `WORKDIR`, `USER`, `EXPOSE` e `CMD`.
4. Construir a imagem `rais-spark:local` e verificar o que há dentro dela.
5. Justificar cada escolha do Dockerfile do guia: versões fixas, JARs embutidos, usuário não-root.

### Pré-requisitos

| Item | Por quê | Onde |
| --- | --- | --- |
| Aula 01 | Entender o papel do container `spark` na arquitetura | Aula 01, seção 4 |
| Terminal Linux básico | Todos os comandos rodam no terminal | — |
| Windows: WSL2 com Ubuntu | O guia recomenda WSL2 para rodar Spark no Windows | Tutorial, passo 1 |
| \~10 GB livres em disco | Imagem base, Java, bibliotecas Python e JARs | — |
| Internet durante o build | O build baixa pacotes do Debian, do PyPI e do Maven | — |

### Duração sugerida

Cerca de 3 horas: 1 h de teoria, 1 h de tutorial (o primeiro build demora), 1 h de exemplos e exercícios. <span class="rl-complemento">Complemento didático</span>

## 2. Contextualização: por que containers

O Spark precisa de Java numa versão compatível, de uma versão específica do Python, de bibliotecas Python e de JARs com versões casadas entre si. Instalar tudo isso à mão em cada máquina é lento e frágil; um container empacota o ambiente inteiro e o reproduz igual em qualquer lugar. <span class="rl-complemento">Complemento didático</span> — contexto adicionado.

### O problema "funciona na minha máquina"

Imagine três pessoas rodando o projeto:

- Uma tem Java 11, a outra Java 21, a terceira não tem Java.
- Uma instalou `pyspark` 4.x, que ativa o modo ANSI por padrão e transforma conversões inválidas em erro (o guia escolhe 3.5 justamente por isso, Parte [4.2](../guia/parte-04.md#parte-4-2)).
- Uma baixou `hadoop-aws` 3.3.6, diferente do Hadoop 3.3.4 embutido no PySpark 3.5; versões desencontradas costumam falhar com erros de classe ausente.

O mesmo código dá três resultados diferentes. O Docker resolve isso: o ambiente é descrito num arquivo (o **Dockerfile**), construído uma vez numa **imagem**, e executado como **container** idêntico em qualquer máquina com Docker.

### Quando usar e quando não usar

| Situação | Containers ajudam? | Por quê |
| --- | --- | --- |
| Projeto com várias dependências de sistema (Java, JARs) | Sim | Encapsula o que é difícil de instalar |
| Vários serviços que conversam (Spark + MinIO) | Sim | Cada serviço no seu container, ligados por rede (Aula 03) |
| Script Python puro, sem dependências nativas | Talvez | Um `venv` pode bastar |
| Interface gráfica de desktop | Pouco | Containers são pensados para processos sem tela |
| Máquina sem virtualização disponível | Não funciona | Docker Desktop no Windows exige WSL2 ou Hyper-V |

### Alternativas

- **Instalação direta no sistema:** simples para uma pessoa, impossível de reproduzir com precisão. O ADR-002 da Aula 01 descarta essa opção.
- **Ambientes virtuais (`venv`, `conda`):** isolam bibliotecas Python, mas não o Java nem os JARs.
- **Máquinas virtuais:** isolam tudo, mas são mais pesadas (seção 3.6).

## 3. Fundamentação teórica

### 3.1 Os blocos fundamentais (guia, Parte [2.1](../guia/parte-02.md#parte-2-1))

| Conceito | O que é | Analogia do guia |
| --- | --- | --- |
| **Imagem** | Pacote imutável com sistema, bibliotecas e código | A "receita" pronta / um molde |
| **Dockerfile** | Arquivo de texto com as instruções para construir a imagem | A receita escrita |
| **Container** | Uma instância em execução de uma imagem | O bolo feito a partir da receita |
| **Volume** | Armazenamento que sobrevive ao container | Um HD externo plugado no container |
| **Bind mount** | Pasta do seu computador montada dentro do container | Uma pasta compartilhada |
| **Rede** | Rede virtual entre containers | Uma LAN privada |
| **Docker Compose** | Arquivo YAML que descreve vários containers juntos | A planta do ambiente inteiro (Aula 03) |

### 3.2 Containers são descartáveis

Tudo que é escrito dentro do container e não está num volume ou bind mount **some** quando o container é removido. Por isso o guia define (Parte [2.1](../guia/parte-02.md#parte-2-1)):

- dados do MinIO → **volume** (`minio-data`);
- seu código → **bind mount** (`./:/app`), para editar no host e o container ver na hora;
- arquivos temporários do Spark → **volume** (`spark-tmp`).

Nesta aula você só constrói a imagem; volumes e bind mounts entram em uso na Aula 03.

### 3.3 O que é, por dentro, um container

<span class="rl-complemento">Complemento didático</span> No Linux, um container é um processo comum isolado por recursos do kernel: **namespaces** (o processo vê só os seus próprios processos, rede e sistema de arquivos) e **cgroups** (limites de CPU e memória — os mesmos que o Compose usa em `cpus` e `mem_limit` na Aula 03). Não há um sistema operacional inteiro rodando: o container compartilha o kernel do host.

No Windows e no macOS não existe kernel Linux nativo, então o Docker Desktop roda uma máquina virtual Linux leve (no Windows, via WSL2) e os containers rodam dentro dela.

### 3.4 Camadas e cache de build

Uma imagem é uma pilha de **camadas** somente leitura. Cada instrução `RUN` ou `COPY` gera uma camada com os arquivos que ela criou ou alterou (guia, Parte [2.2](../guia/parte-02.md#parte-2-2)). <span class="rl-complemento">Complemento didático</span> Instruções como `ENV`, `WORKDIR`, `USER`, `EXPOSE` e `CMD` só alteram metadados da imagem, sem arquivos novos.

Quando um container roda, o Docker põe uma camada **gravável** fina por cima da pilha. É nela que vão as escritas do processo — e é ela que some quando o container é removido (seção 3.2).

**Cache.** Ao reconstruir, o Docker reaproveita cada camada cuja instrução e entradas não mudaram. A regra do guia:

> Se uma camada muda, todas as seguintes são refeitas. Coloque o que muda pouco primeiro (sistema, Java, JARs) e o que muda muito por último (código). Copie `requirements.txt` e instale as dependências **antes** de copiar o código.

**Consequência de ordenar errado.** Se o Dockerfile copiasse o projeto inteiro antes do `pip install`, qualquer alteração num arquivo `.py` invalidaria a camada de instalação, e cada build reinstalaria PySpark e Jupyter do zero.

### 3.5 Tags, registry e versões fixas

<span class="rl-complemento">Complemento didático</span> Uma imagem é identificada por `repositório:tag`, por exemplo `python:3.11-slim-bookworm`. Imagens públicas vêm de um **registry** (o padrão é o Docker Hub). Uma tag é um rótulo móvel: o mantenedor pode apontá-la para uma imagem nova. Por isso o guia proíbe `latest` (Parte [4.2](../guia/parte-04.md#parte-4-2)): ele muda sem aviso, e o build de hoje deixaria de ser igual ao de amanhã.

A imagem que você constrói recebe a tag `rais-spark:local`. `local` indica que ela não vem de nenhum registry: existe só na sua máquina.

### 3.6 Container × máquina virtual

<span class="rl-complemento">Complemento didático</span>

| Critério | Container | Máquina virtual |
| --- | --- | --- |
| O que isola | Processos, rede e arquivos, compartilhando o kernel | Um sistema operacional inteiro, com kernel próprio |
| Inicialização | Segundos | Dezenas de segundos a minutos |
| Consumo de memória | O do processo | O do sistema convidado inteiro + o processo |
| Isolamento de segurança | Bom, mas o kernel é compartilhado | Mais forte |
| Uso no curso | Spark, MinIO, site | Só a VM interna do Docker Desktop no Windows/macOS |

### 3.7 As versões da imagem do curso (guia, Parte [4.2](../guia/parte-04.md#parte-4-2))

| Componente | Versão | Observação do guia |
| --- | --- | --- |
| Python | 3.11 | — |
| Java | 17 | Requisito do Spark 3.5 |
| PySpark | 3.5.3 | Sem ANSI por padrão (o 4.x ativa) |
| delta-spark | 3.2.0 | Compatível com Spark 3.5 (confirme a matriz na documentação do Delta) |
| hadoop-aws | 3.3.4 | Mesma versão do Hadoop embutido no PySpark 3.5 |
| aws-java-sdk-bundle | 1.12.262 | Dependência do hadoop-aws 3.3.4 |

Essas quatro peças (PySpark, Delta, hadoop-aws e SDK) precisam ser compatíveis entre si. Trocar uma delas isoladamente é a causa mais comum de "o Spark não sobe" (Apêndice B).

## 4. Arquitetura: as camadas da imagem rais-spark

A imagem do curso é uma pilha de seis camadas, ordenada do que quase nunca muda (o sistema) ao que muda mais (o usuário e as pastas, que dependem do seu UID). Cada container criado a partir dela compartilha essas camadas e ganha só uma camada gravável própria.

!!! note "Diagrama interativo"
    "Imagem rais-spark · 6 camadas e 2 containers" está no [documento original](https://claude.ai/code/artifact/3a17b7ff-ce58-4699-b232-429afbe389e2).

Uma mudança em `requirements-dev.txt` invalida a camada do `COPY` e todas acima dela; o Java e a imagem base continuam vindo do cache.

### Fluxo do build ao container

1. **Contexto:** `docker build` envia a pasta do projeto, filtrada pelo `.dockerignore`.
2. **Camadas:** cada `RUN` e `COPY` do Dockerfile vira uma camada; as que não mudaram vêm do cache.
3. **Imagem:** a pilha recebe o nome `rais-spark:local`.
4. **Container:** `docker run` (ou o Compose, Aula 03) cria um container com uma camada gravável sobre a imagem.
5. **Persistência:** o que precisa sobreviver ao container vai para volume ou bind mount (Aula 03); o resto some com `docker rm`.

## 5. Tutorial: construir a imagem rais-spark

São sete passos: instalar o Docker, criar a pasta, escrever três arquivos de apoio, escrever o Dockerfile, construir e conferir. O único comando demorado é o build do passo 6.

### Passo 1 — Instalar e testar o Docker

<span class="rl-complemento">Complemento didático</span> O guia pressupõe Docker instalado. Siga a documentação oficial do Docker para o seu sistema; os comandos de instalação mudam com o tempo e não são reproduzidos aqui.

| Sistema | O que instalar | Observação |
| --- | --- | --- |
| Windows | WSL2 com Ubuntu + Docker Desktop com integração WSL ativada | Rode todos os comandos do curso dentro do Ubuntu (WSL), com o projeto em `~/`, não em `/mnt/c` |
| Linux | Docker Engine + plugin Compose | Para rodar sem `sudo`, a documentação ensina a adicionar seu usuário ao grupo `docker` (veja Riscos, seção 10) |
| macOS | Docker Desktop | — |

Teste:

```bash
docker version              # mostra a versão do cliente e do servidor (daemon)
docker run --rm hello-world # baixa uma imagem mínima, executa e remove o container
```

- **Resultado esperado:** `docker version` mostra as seções `Client` e `Server`; o `hello-world` imprime uma mensagem de boas-vindas.
- **Se aparecer só `Client` e um erro de conexão:** o daemon não está rodando. No Windows, abra o Docker Desktop; no Linux, inicie o serviço do Docker.
- `--rm` remove o container ao terminar, para não acumular containers parados.

### Passo 2 — Criar a pasta do projeto

A estrutura completa do repositório é montada na Aula 05. Por enquanto, só o necessário para o build:

```bash
mkdir -p ~/rais-lakehouse/docker/spark   # -p cria as pastas intermediárias e não falha se já existirem
cd ~/rais-lakehouse
```

### Passo 3 — Dependências Python (guia, Parte [4.3](../guia/parte-04.md#parte-4-3))

`requirements.txt` — o que o projeto precisa para **executar**:

```text
pyspark==3.5.3
delta-spark==3.2.0
py7zr==0.22.0
```

`requirements-dev.txt` — o que é usado só para **desenvolver**:

```text
jupyterlab==4.2.5
pytest==8.3.3
ruff==0.6.9
pandas==2.2.3
matplotlib==3.9.2
```

- `==` fixa a versão exata. Sem isso, cada build poderia instalar uma versão diferente.
- `delta-spark` aqui é o pacote Python (para `from delta.tables import DeltaTable`); os JARs do Delta, usados pela JVM, entram no passo 5.
- O guia avisa: se alguma versão não instalar, use a mais recente da mesma linha (ex.: `4.2.x`).

### Passo 4 — `.dockerignore` (guia, Parte [3.2](../guia/parte-03.md#parte-3-2))

```gitignore
.git
.env
staging
.venv
**/__pycache__
.ipynb_checkpoints
```

**O que faz.** O comando de build envia a pasta do projeto (o **contexto de build**) ao Docker. O `.dockerignore` exclui o que não deve ir: o histórico Git (pesado), o `.env` (segredos) e `staging` (os `.7z` da RAIS, vários GB). Sem ele, o build ficaria lento e um segredo poderia acabar dentro de uma camada da imagem.

### Passo 5 — O Dockerfile (guia, Parte [4.4](../guia/parte-04.md#parte-4-4))

Salve em `docker/spark/Dockerfile`, exatamente como no guia:

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

A seção 6 explica cada bloco linha a linha.

### Passo 6 — Construir a imagem

```bash
docker build \
  -f docker/spark/Dockerfile \
  -t rais-spark:local \
  --build-arg HOST_UID="$(id -u)" \
  .
```

| Parte | Significado |
| --- | --- |
| `docker build` | Constrói uma imagem a partir de um Dockerfile |
| `-f docker/spark/Dockerfile` | Caminho do Dockerfile (ele não está na raiz) |
| `-t rais-spark:local` | Nome e tag da imagem; é o mesmo nome que o Compose usará na Aula 03 |
| `--build-arg HOST_UID="$(id -u)"` | Passa o seu UID para o `ARG HOST_UID`; `id -u` imprime o UID do usuário atual |
| `.` (ponto final) | O contexto de build: a pasta atual, filtrada pelo `.dockerignore` |

<span class="rl-complemento">Complemento didático</span> Na Aula 03 o Compose faz este mesmo build (`docker compose up --build`), lendo `HOST_UID` do `.env`. Construir à mão aqui serve para ver cada etapa isolada.

- **Duração:** o primeiro build baixa a imagem base, o Java, as bibliotecas Python e quatro JARs; leva vários minutos, dependendo da sua conexão.
- **Resultado esperado:** o build termina sem erro, e `docker image ls rais-spark` lista a imagem com a tag `local`.

### Passo 7 — Conferir o conteúdo da imagem

```bash
# Java instalado? (java -version escreve na saída de erro; o 2>&1 junta as duas saídas)
docker run --rm rais-spark:local java -version 2>&1

# PySpark e Delta importáveis, nas versões fixadas?
docker run --rm rais-spark:local python -c "import pyspark, delta; print(pyspark.__version__)"

# Quem é o usuário e qual o UID?
docker run --rm rais-spark:local id
```

| Comando | Resultado esperado |
| --- | --- |
| `java -version` | Uma linha com `17` (OpenJDK 17) |
| `python -c ...` | `3.5.3` |
| `id` | `uid=` igual ao seu `id -u` e nome `app`, nunca `uid=0(root)` |

O resultado exato da sua máquina é o que vale; os valores acima são o que o Dockerfile deve produzir, não uma saída já executada.

## 6. Como cada bloco do Dockerfile funciona

Cada bloco resolve um problema específico; entender o problema é o que permite adaptar o arquivo sem quebrá-lo.

### Referência de instruções (guia, Parte [2.2](../guia/parte-02.md#parte-2-2))

| Instrução | Para que serve | Exemplo |
| --- | --- | --- |
| `FROM` | Imagem base | `FROM python:3.11-slim-bookworm` |
| `ARG` | Variável **só durante o build** | `ARG DELTA_VERSION=3.2.0` |
| `ENV` | Variável disponível **no container** | `ENV PYTHONPATH=/app` |
| `RUN` | Executa um comando no build (gera uma camada) | `RUN pip install -r requirements.txt` |
| `COPY` | Copia arquivos do contexto para a imagem | `COPY requirements.txt /tmp/` |
| `WORKDIR` | Diretório de trabalho padrão | `WORKDIR /app` |
| `USER` | Usuário que executa os comandos seguintes | `USER app` |
| `EXPOSE` | Documenta a porta usada (não publica) | `EXPOSE 8888` |
| `CMD` | Comando padrão ao iniciar o container | `CMD ["bash"]` |

### Bloco 1 — `FROM python:3.11-slim-bookworm`

- **O que faz:** começa de uma imagem oficial do Python 3.11 sobre Debian 12 (bookworm), na variante `slim` (sem pacotes extras).
- **Por que bookworm explícito:** o guia escolhe a base porque o repositório do Debian 12 tem o pacote `openjdk-17-jre-headless`. <span class="rl-complemento">Complemento didático</span> Uma tag sem a versão do Debian (ex.: `python:3.11-slim`) pode passar a apontar para uma versão mais nova do Debian, cujo repositório pode não ter mais o Java 17 — e o `apt-get install` do bloco 3 quebraria.

### Bloco 2 — `ARG` com versões

- **O que faz:** declara variáveis com valor padrão, usadas nos blocos seguintes como `${DELTA_VERSION}`.
- **Por que:** a versão aparece num lugar só. Para testar outra versão sem editar o arquivo: `--build-arg DELTA_VERSION=...`.
- **Cuidado:** um `ARG` não existe quando o container roda. Se o programa precisar do valor em execução, use `ENV`.

### Bloco 3 — Pacotes do sistema

```dockerfile
RUN apt-get update \
 && apt-get install -y --no-install-recommends openjdk-17-jre-headless curl procps \
 && rm -rf /var/lib/apt/lists/*
```

- **`openjdk-17-jre-headless`:** o Java 17 sem componentes gráficos — o Spark é um programa da JVM.
- **`curl`:** usado no bloco 5 para baixar os JARs.
- **`procps`:** <span class="rl-complemento">Complemento didático</span> fornece comandos como `ps` e `top`, úteis para inspecionar processos dentro do container.
- **`--no-install-recommends` e `rm -rf /var/lib/apt/lists/*`:** deixam a imagem menor (guia, Parte [4.4](../guia/parte-04.md#parte-4-4)).
- **Por que tudo num único `RUN` com `&&`:** <span class="rl-complemento">Complemento didático</span> se o `update` ficasse num `RUN` separado, a camada dele poderia ser reaproveitada do cache numa build futura com uma lista de pacotes desatualizada. Juntos, eles sempre rodam em conjunto. E a limpeza só reduz a imagem se acontecer na mesma camada que criou os arquivos.

### Bloco 4 — Dependências Python antes do código

```dockerfile
COPY requirements.txt requirements-dev.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.txt -r /tmp/requirements-dev.txt
```

- Copia **só** os dois arquivos de dependências. Enquanto eles não mudarem, a camada do `pip install` vem do cache, mesmo que você altere todo o código do projeto.
- `--no-cache-dir` evita guardar o cache do pip dentro da imagem.
- O código do projeto não é copiado: ele entra por bind mount na Aula 03. O guia observa que, para produção, você adicionaria `COPY . /app`.

### Bloco 5 — JARs dentro da pasta do PySpark

- **Primeira linha:** pergunta ao próprio Python onde o PySpark está instalado e monta o caminho da pasta `jars` dele. Assim o Dockerfile não depende de um caminho fixo.
- **Por que nessa pasta:** o Spark carrega automaticamente todos os JARs dali. Com isso, a configuração da Aula 06 não precisa baixar pacotes do Maven quando a sessão inicia — o ADR-006 da Aula 01 (funciona sem internet, reprodutível).
- **Os quatro JARs:** `hadoop-aws` e `aws-java-sdk-bundle` permitem ao Spark falar S3 (MinIO, Aula 04); `delta-spark` e `delta-storage` implementam o Delta Lake (Aula 10).
- **`curl -fsSL`:** `-f` faz o comando falhar se o servidor responder com erro, em vez de gravar a página de erro como se fosse o JAR (guia, Parte [4.4](../guia/parte-04.md#parte-4-4)). `-sS` silencia o progresso mas mostra erros; `-L` segue redirecionamentos.

### Bloco 6 — Usuário não-root

```dockerfile
RUN useradd -m -u "${HOST_UID}" app \
 && mkdir -p /app /staging /tmp/spark \
 && chown -R app:app /app /staging /tmp/spark
```

- **Por que não-root:** se um processo dentro do container for comprometido, ele não tem privilégios de administrador no container.
- **Por que o mesmo UID do host:** arquivos criados pelo container num bind mount ficam com o UID de quem os criou. Com o UID igual ao seu, você consegue editar e apagar esses arquivos no host sem `sudo`. Com UIDs diferentes, aparece `Permission denied` ([Apêndice B](../guia/apendice-b.md) do guia).
- **Por que criar e dar dono a `/tmp/spark`:** <span class="rl-complemento">Complemento didático</span> na Aula 03 essa pasta vira um volume nomeado. Na primeira vez, o Docker copia o dono da pasta existente na imagem para o volume; sem esse `chown`, o volume nasceria pertencendo a root e o Spark não conseguiria gravar nele.

### Bloco 7 — Ambiente e comando padrão

- **`ENV PYTHONPATH=/app`:** permite `from src.utils import ...` e `from config.settings import ...` de qualquer pasta.
- **`ENV PYTHONUNBUFFERED=1`:** os `print` aparecem nos logs na hora, sem ficar presos num buffer.
- **`WORKDIR /app` e `USER app`:** daqui em diante os comandos rodam em `/app`, como `app`.
- **`EXPOSE 8888 4040`:** documenta as portas do Jupyter e da Spark UI. Não publica nada: quem publica é o Compose (Aula 03).
- **`CMD ["bash"]`:** o comando padrão é um terminal. O Compose o substitui pelo JupyterLab (Aula 03). <span class="rl-complemento">Complemento didático</span> A forma em lista (`["bash"]`) executa o programa diretamente, sem passar por um shell intermediário.

## 7. Exemplos práticos

Quatro experimentos curtos mostram, na sua máquina, os conceitos da seção 3: camadas, cache, UID e os JARs funcionando. <span class="rl-complemento">Complemento didático</span> — os experimentos são adicionados; os comandos usam só a imagem do guia.

### Exemplo 1 — Ver as camadas da imagem

```bash
docker history rais-spark:local
```

- **O que mostra:** uma linha por instrução, da mais recente (topo) à imagem base (fim), com o tamanho que cada uma acrescentou.
- **O que observar:** as linhas de `RUN apt-get`, `RUN pip install` e a dos JARs concentram o tamanho. As de `ENV`, `WORKDIR`, `USER`, `EXPOSE` e `CMD` aparecem com tamanho 0 — só metadados.

### Exemplo 2 — Medir o efeito do cache

```bash
# a) Rebuild sem mudar nada: tudo deve vir do cache e terminar em segundos
docker build -f docker/spark/Dockerfile -t rais-spark:local --build-arg HOST_UID="$(id -u)" .

# b) Altere requirements-dev.txt (ex.: acrescente uma linha em branco no fim) e rebuild
docker build -f docker/spark/Dockerfile -t rais-spark:local --build-arg HOST_UID="$(id -u)" .
```

- **Em (a):** a saída do build marca as etapas como `CACHED`.
- **Em (b):** o bloco 3 (apt) continua em cache, mas o `COPY` dos requirements mudou — então ele, o `pip install` e **tudo depois dele** (JARs, usuário) são refeitos. É a regra "se uma camada muda, todas as seguintes são refeitas" na prática.
- Desfaça a alteração do arquivo ao terminar.

### Exemplo 3 — Por que o UID importa

```bash
# Monta a pasta atual em /app e cria um arquivo de dentro do container
docker run --rm -v "$PWD":/app rais-spark:local touch /app/criado_no_container.txt

# No host: de quem é o arquivo?
ls -ln criado_no_container.txt
rm criado_no_container.txt
```

- `-v "$PWD":/app` é um bind mount: a pasta atual do host aparece como `/app` no container.
- **Resultado esperado:** o terceiro campo do `ls -ln` (UID do dono) é igual ao seu `id -u`, e o `rm` funciona sem `sudo`.
- **Para ver o problema:** reconstrua com `--build-arg HOST_UID=1234` e repita; o arquivo nasce com UID 1234 e você pode precisar de `sudo` para apagá-lo. Reconstrua com o seu UID depois.

### Exemplo 4 — Primeira sessão Spark com Delta (sem MinIO)

Este exemplo prova que Java, PySpark e os JARs do Delta funcionam juntos, gravando uma tabela Delta no disco interno do container.

```bash
docker run --rm -i rais-spark:local python - <<'EOF'
from pyspark.sql import SparkSession

spark = (
    SparkSession.builder
    .master("local[1]")                     # 1 thread basta para o teste
    .appName("teste-imagem")
    # As duas configurações que ativam o Delta (as mesmas de get_spark, Aula 06)
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
    .config("spark.sql.catalog.spark_catalog",
            "org.apache.spark.sql.delta.catalog.DeltaCatalog")
    .getOrCreate()
)

caminho = "/tmp/spark/delta_teste"          # pasta criada e com dono app no Dockerfile
spark.range(3).write.format("delta").mode("overwrite").save(caminho)
print("linhas:", spark.read.format("delta").load(caminho).count())
spark.stop()
EOF
```

- **`-i`:** mantém a entrada padrão aberta, para o Python ler o script do *heredoc* (`<<'EOF' ... EOF`). As aspas em `'EOF'` impedem o shell de interpretar `$` dentro do script.
- **`python -`:** o hífen manda o Python ler o programa da entrada padrão.
- **Resultado esperado:** muitas linhas de log do Spark (normal) e, perto do fim, `linhas: 3`.
- **Se der `ClassNotFoundException` com `delta` no nome:** os JARs do Delta não estão na pasta do PySpark; veja a seção 8.
- **Note:** como `--rm` remove o container, a tabela gravada some junto. É a seção 3.2 na prática: escrita fora de volume é descartável.

## 8. Armadilhas, diagnóstico e soluções

Quase todo erro desta aula aparece no build ou no primeiro `docker run`, e a mensagem costuma apontar a linha do Dockerfile que falhou.

| Sintoma | Causa provável | Como confirmar | Solução |
| --- | --- | --- | --- |
| `Cannot connect to the Docker daemon` | Docker Desktop fechado ou serviço parado | `docker version` mostra só `Client` | Abrir o Docker Desktop / iniciar o serviço |
| `permission denied ... docker.sock` (Linux) | Usuário sem permissão no Docker | O mesmo comando funciona com `sudo` | Seguir o pós-instalação da documentação oficial (ver Riscos) |
| `E: Unable to locate package openjdk-17-jre-headless` | Imagem base trocada por outra versão do Debian | `FROM` não termina em `-bookworm` | Voltar para `python:3.11-slim-bookworm` |
| `ERROR: Could not find a version that satisfies the requirement ...` | Versão fixada inexistente ou indisponível | Mensagem cita o pacote | Usar a mais recente da mesma linha, como o guia orienta |
| `curl: (22) The requested URL returned error: 404` | Versão em `ARG` sem JAR correspondente no Maven | Abrir a URL da mensagem no navegador | Corrigir a versão no `ARG` |
| `COPY failed: ... requirements-dev.txt: not found` | Arquivo ausente ou fora do contexto | `ls` na pasta onde rodou o build | Criar o arquivo; rodar o build a partir da raiz do projeto |
| `useradd: UID 1000 is not unique` | <span class="rl-complemento">Complemento didático</span> já existe um usuário com esse UID na imagem base | Erro no bloco 6 | Usar outro `HOST_UID` ou checar a imagem base |
| Build lento e envio de vários GB ("transferring context") | `.dockerignore` ausente ou incompleto | Tamanho do contexto no início do build | Criar o `.dockerignore` do passo 4 |
| `ClassNotFoundException` com `S3AFileSystem` ou `delta` | JAR não baixou ou foi para a pasta errada | Exemplo 4 falha; listar a pasta `jars` | `docker build --no-cache ...` e conferir o bloco 5 |
| `Permission denied` ao gravar em `/app` ou `/tmp/spark` | UID diferente entre host e container | `id` no container × `id -u` no host | Rebuild com `--build-arg HOST_UID="$(id -u)"` |
| Mudança no Dockerfile "não fez efeito" | Container antigo ainda rodando ou imagem não reconstruída | `docker image ls` mostra data antiga | Rebuild e recriar o container |

### Diagnóstico de um build que falha

<span class="rl-complemento">Complemento didático</span>

1. Leia de baixo para cima: a última etapa listada antes do erro é a instrução que falhou.
2. Para ver toda a saída de um `RUN`, rode o build com `--progress=plain`.
3. Para investigar o estado logo antes da falha, comente a instrução que falhou e as seguintes, construa, e abra um terminal: `docker run --rm -it rais-spark:local bash`.
4. Se suspeitar de cache corrompido ou desatualizado, `--no-cache` força refazer tudo.

## 9. Boas práticas para produção

1. **Versões fixas em tudo:** imagem base com versão do sistema, pacotes Python com `==`, JARs por `ARG` (guia, Parte [4.2](../guia/parte-04.md#parte-4-2)).
2. **Ordene por frequência de mudança:** sistema → dependências → código (guia, Parte [2.2](../guia/parte-02.md#parte-2-2)).
3. **Instale e limpe na mesma camada** (`apt-get update && install && rm -rf ...`).
4. **Usuário não-root** com UID controlado (guia, Parte [4.4](../guia/parte-04.md#parte-4-4)).
5. **`.dockerignore` sempre,** e nunca segredos dentro da imagem: tudo que entra numa camada continua na imagem, mesmo se apagado numa camada posterior. <span class="rl-complemento">Complemento didático</span>
6. **Dependências embutidas, não baixadas em execução** (ADR-006).
7. **Separe execução de desenvolvimento.** <span class="rl-complemento">Complemento didático</span> O guia instala `jupyterlab`, `pytest` e `ruff` na mesma imagem, o que é prático para estudo. Em produção, a imagem que roda o pipeline levaria só o `requirements.txt` (técnica comum: *multi-stage build* ou duas imagens).
8. **Em produção, copie o código para a imagem** (`COPY . /app`) em vez de usar bind mount, para que a imagem seja um artefato completo e imutável (guia, Parte [4.4](../guia/parte-04.md#parte-4-4)).

## 10. Riscos: segurança, desempenho, custos e integridade

| Tipo | Risco | Mitigação |
| --- | --- | --- |
| Segurança | Processo do container rodando como root | `USER app` (bloco 6) |
| Segurança | Segredo copiado para a imagem | `.dockerignore` com `.env`; nunca `COPY . .` sem ele |
| Segurança | Grupo `docker` no Linux equivale a acesso de administrador à máquina | <span class="rl-complemento">Complemento didático</span> Adicione só o seu usuário, em máquina pessoal; em servidor compartilhado, avalie o modo *rootless* do Docker |
| Segurança | Imagem base com vulnerabilidades conhecidas | <span class="rl-complemento">Complemento didático</span> Reconstrua periodicamente para pegar atualizações de segurança da base, mantendo a mesma tag de versão |
| Desempenho | Build lento a cada alteração | Ordem das camadas e `.dockerignore` |
| Desempenho | Projeto em `/mnt/c` no Windows | Manter o projeto no sistema de arquivos do WSL |
| Custo | Imagens e camadas antigas ocupando disco | <span class="rl-complemento">Complemento didático</span> `docker image prune` remove imagens sem tag; confira antes o que será removido |
| Integridade | Versões incompatíveis entre PySpark, Delta e hadoop-aws | Versões fixas e conferidas pela tabela da Parte [4.2](../guia/parte-04.md#parte-4-2) |
| Integridade | JAR corrompido gravado como se fosse válido | `curl -f` falha o build em erro HTTP |
| Integridade | Ambiente diferente entre pessoas | Uma única imagem para todos |

## 11. Laboratório e validação na plataforma

A aula está concluída quando os cinco checks automáticos passam na sua máquina e o checklist manual está marcado. Os checks rodam no host, e não no container, porque precisam do CLI do Docker (plano técnico, seção 7).

### O que esta aula acrescenta ao projeto

| Arquivo | Papel no projeto final |
| --- | --- |
| `docker/spark/Dockerfile` | Base de execução de todo o pipeline, do JupyterLab e dos checks das Aulas 04 em diante |
| `requirements.txt` / `requirements-dev.txt` | Dependências fixadas, reutilizadas no CI (Aula 16) |
| `.dockerignore` | Protege segredos e dados de entrarem na imagem |

### Checks automáticos

<span class="rl-complemento">Complemento didático</span> — código novo da plataforma, que verifica exatamente os resultados esperados do tutorial. Arquivo `labcheck/host/test_aula02.py`:

```python
"""Checks da Aula 02. Rodam no host (WSL/Linux), pois usam o CLI do Docker."""
import os
import subprocess

IMAGEM = "rais-spark:local"

JARS_ESPERADOS = {
    "hadoop-aws-3.3.4.jar",
    "aws-java-sdk-bundle-1.12.262.jar",
    "delta-spark_2.12-3.2.0.jar",
    "delta-storage-3.2.0.jar",
}

LISTAR_JARS = (
    "import glob, os, pyspark; "
    "d = os.path.join(os.path.dirname(pyspark.__file__), 'jars'); "
    "print('\\n'.join(os.path.basename(p) for p in glob.glob(d + '/*.jar')))"
)


def rodar(*args: str) -> subprocess.CompletedProcess:
    """Executa um comando do Docker sem lançar exceção; o teste decide o que é falha."""
    return subprocess.run(["docker", *args], capture_output=True, text=True, timeout=300)


def na_imagem(*cmd: str) -> subprocess.CompletedProcess:
    return rodar("run", "--rm", IMAGEM, *cmd)


def test_a02_imagem_existe():
    r = rodar("image", "inspect", IMAGEM)
    assert r.returncode == 0, f"Imagem {IMAGEM} não existe. Faça o passo 6 da Aula 02."


def test_a02_java_17():
    r = na_imagem("java", "-version")
    saida = r.stdout + r.stderr  # java -version escreve na saída de erro
    assert r.returncode == 0 and '"17' in saida, (
        f"Java 17 não encontrado: {saida.strip()[:200]}. Confira o bloco 3 e o FROM -bookworm."
    )


def test_a02_pyspark_delta():
    r = na_imagem("python", "-c", "import pyspark, delta; print(pyspark.__version__)")
    assert r.returncode == 0, f"Import falhou: {r.stderr.strip()[-300:]}"
    assert r.stdout.strip() == "3.5.3", f"PySpark {r.stdout.strip()} != 3.5.3. Confira requirements.txt."


def test_a02_jars_s3a_delta():
    r = na_imagem("python", "-c", LISTAR_JARS)
    faltando = JARS_ESPERADOS - set(r.stdout.split())
    assert not faltando, f"JARs ausentes: {sorted(faltando)}. Rebuild com --no-cache e confira o bloco 5."


def test_a02_usuario_nao_root():
    r = na_imagem("id", "-u")
    uid = r.stdout.strip()
    assert uid != "0", "O container roda como root. Confira USER app no bloco 7."
    assert uid == str(os.getuid()), (
        f"UID do container ({uid}) != seu UID ({os.getuid()}). "
        'Rebuild com --build-arg HOST_UID="$(id -u)".'
    )
```

- **Entradas:** nenhuma; tudo é lido da imagem.
- **Saídas:** pytest mostra cada check como passou ou falhou; a mensagem de falha diz o que fazer.
- **Dependências no host:** Python 3 e pytest. No Ubuntu (WSL), instale num ambiente virtual: `python3 -m venv .venv-host && .venv-host/bin/pip install pytest`.
- **`os.getuid()`** só existe em Linux e macOS — por isso o check roda no WSL, não no PowerShell.
- **Registro do progresso:** o `conftest.py` de `labcheck/host/`, criado no esqueleto da plataforma, grava cada resultado em `progress/historico.jsonl`.

### Como rodar

```bash
# Enquanto o Makefile da plataforma não existe (Aula 03):
.venv-host/bin/pytest -v labcheck/host/test_aula02.py

# Depois do esqueleto da plataforma:
make check-host AULA=02
```

### Checklist manual

- [ ] Sei explicar a diferença entre imagem, container, volume e bind mount.
- [ ] Sei dizer por que o `pip install` vem antes da cópia do código.
- [ ] Vi no Exemplo 2 quais etapas foram refeitas ao mudar `requirements-dev.txt`, e por quê.
- [ ] O Exemplo 4 imprimiu `linhas: 3`.
- [ ] Sei explicar por que o UID do container deve ser igual ao meu.

## 12. Exercícios, revisão e desafios

### Exercícios práticos

1. Rode `docker history rais-spark:local` e identifique as três camadas mais pesadas. A qual bloco do Dockerfile cada uma corresponde?
2. Mova o `COPY requirements...` e o `RUN pip install` para **depois** do bloco 5, reconstrua e repita o Exemplo 2. O que mudou no tempo do rebuild? Depois, desfaça a mudança.
3. Construa a imagem com `--build-arg DELTA_VERSION=9.9.9`. Leia o erro, identifique o comando que falhou e explique por que `curl -f` foi importante. Reconstrua com o valor correto.
4. Abra um terminal no container (`docker run --rm -it rais-spark:local bash`) e responda: em qual pasta você está? Quem é você? O que `ls "$(python -c 'import os,pyspark;print(os.path.dirname(pyspark.__file__))')/jars" | grep delta` mostra?

### Perguntas de revisão

1. Qual a diferença entre `ARG` e `ENV`? Dê um exemplo do Dockerfile do curso para cada um.
2. Por que `EXPOSE 8888` não basta para abrir o JupyterLab no navegador?
3. O que acontece com um arquivo gravado em `/tmp/spark` num container iniciado com `docker run --rm` sem volume?
4. Por que a imagem base usa `-bookworm` explicitamente?
5. Por que os JARs vão para a pasta `jars` do PySpark e não são baixados quando a sessão Spark inicia?
6. Um colega diz que "apagar o `.env` numa camada posterior resolve" depois de ele ter sido copiado para a imagem. Ele está certo?

**Respostas sugeridas** (tente antes de ler):

1. `ARG` existe só no build (`ARG DELTA_VERSION`); `ENV` existe no container em execução (`ENV PYTHONPATH=/app`).
2. `EXPOSE` só documenta; a porta precisa ser publicada (`-p` no `docker run` ou `ports` no Compose, Aula 03).
3. Some quando o container é removido; só volumes e bind mounts persistem.
4. Para garantir um Debian que tem `openjdk-17-jre-headless` e evitar que a tag passe a apontar para outra versão do sistema.
5. Para funcionar sem internet e ser reprodutível (ADR-006).
6. Não. A camada anterior continua na imagem com o arquivo dentro; o certo é nunca copiá-lo (`.dockerignore`).

### Desafios

1. **Imagem de execução enxuta.** Escreva um Dockerfile alternativo que instale só `requirements.txt` (sem Jupyter, pytest, ruff, pandas, matplotlib). Compare o tamanho com `docker image ls`. Não substitua o do curso: guarde como `docker/spark/Dockerfile.runtime`.
2. **Rootless.** Pesquise na documentação oficial o modo *rootless* do Docker e escreva um parágrafo sobre quando ele valeria a pena para este projeto.
3. **ADR.** Registre em `docs/decisoes.md` a decisão "imagem única para desenvolvimento e execução", com a alternativa do desafio 1 e as consequências.

## 13. Referências cruzadas

| Tema | Onde | Fonte no guia |
| --- | --- | --- |
| Papel do container `spark` na arquitetura; ADR-002 e ADR-006 | Aula 01 | Parte [1](../guia/parte-01.md) |
| Compose, volumes, bind mount, `ports`, `cpus`, `mem_limit`, `HOST_UID` no `.env` | Aula 03 | Partes [2.3](../guia/parte-02.md#parte-2-3)–[2.4](../guia/parte-02.md#parte-2-4), [4.6](../guia/parte-04.md#parte-4-6)–[4.7](../guia/parte-04.md#parte-4-7) |
| Uso dos JARs S3A com o MinIO | Aula 04 | Parte [4.1](../guia/parte-04.md#parte-4-1) |
| `.gitignore`, estrutura completa do repositório | Aula 05 | Parte [3](../guia/parte-03.md) |
| `get_spark` com as configurações do Delta e do S3A; teste de fumaça | Aula 06 | Partes [4.10](../guia/parte-04.md#parte-4-10), [7.3](../guia/parte-07.md#parte-7-3) |
| `_delta_log` e o que os JARs do Delta implementam | Aula 10 | Parte [13.1](../guia/parte-13.md#parte-13-1) |
| Limites de memória e CPU do container | Aula 15 | Parte [14.1](../guia/parte-14.md#parte-14-1) |
| `requirements*.txt` no CI | Aula 16 | Parte [15.5](../guia/parte-15.md#parte-15-5) |
| Erros de build e permissão | Apêndice B | Apêndice B |
| Comandos `docker` | Apêndice D | Parte [2.4](../guia/parte-02.md#parte-2-4) |
| Termos: imagem, camada, bind mount, volume | Apêndice C | Apêndice C |
| Plano técnico da plataforma (checks no host) | [Diagnóstico e plano técnico](https://claude.ai/code/artifact/68629f60-3f2f-40f2-a390-85d81360ea9e), seção 7 | — |


## Checks automáticos

```bash
make check-host AULA=02
```

Arquivo: `labcheck/host/test_aula02.py`. Cada execução grava o resultado em `progress/historico.jsonl`; depois rode `make progresso` para atualizar a página [Progresso](../progresso.md).

| Check | O que verifica |
| --- | --- |
| `a02_imagem_existe` | imagem existe |
| `a02_java_17` | java 17 |
| `a02_pyspark_delta` | pyspark delta |
| `a02_jars_s3a_delta` | jars s3a delta |
| `a02_usuario_nao_root` | usuario nao root |
