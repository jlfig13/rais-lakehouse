# Aula 03 — Docker Compose: serviços, rede, volumes e configuração

Oct 9, 2026 · @João Lucas Ribeiro Figueiredo

Ao final desta aula, um único comando (`make up`) sobe os três serviços do RAIS Lakehouse — `minio`, `minio-init` e `spark` — com rede, volumes, limites de recursos e configuração vinda do `.env`.

```yaml
# Metadados (front matter de curso/docs/aulas/aula-03.md)
aula: 3
titulo: "Docker Compose: serviços, rede, volumes e configuração"
origem: ["Guia Parte 2.3", "Guia Parte 2.4", "Guia Parte 4.6", "Guia Parte 4.7", "Guia Parte 4.8", "Guia Parte 4.9"]
depende_de: [2]
entrega: ["docker-compose.yml", ".env.example", "Makefile", "docker/minio/init-minio.sh", "docker/minio/policy-rais.json"]
checks:
  - id: a03_compose_valido
  - id: a03_servicos_no_ar
  - id: a03_minio_init_ok
  - id: a03_portas_so_locais
```

**Convenção:** **\[Complemento didático\]** marca o que não está no guia original; o resto vem do RAIS Lakehouse Guide, com a parte indicada.

## 1. Objetivos e pré-requisitos

### Objetivos de aprendizagem

1. Ler e escrever um `docker-compose.yml`: serviços, imagens e builds, portas, variáveis, volumes e dependências.
2. Explicar como os containers se encontram pela rede do Compose e por que `localhost` não funciona entre eles.
3. Usar interpolação de variáveis (`${VAR}`, `${VAR:-padrão}`, `${VAR:?erro}`) e separar configuração de código com `.env` e `.env.example`.
4. Diferenciar volume nomeado de bind mount e escolher o certo para cada tipo de dado.
5. Controlar a ordem de inicialização com `depends_on` e um *init container*.
6. Limitar CPU e memória de um container e relacionar esses limites com o Spark.
7. Criar atalhos com Makefile.

### Pré-requisitos

| Item | Por quê |
| --- | --- |
| Aula 02 concluída | O serviço `spark` usa o Dockerfile e a tag `rais-spark:local` |
| Plugin Compose do Docker | `docker compose version` deve responder |
| `make` instalado | No Ubuntu/WSL, vem no pacote `make` (ou `build-essential`) |
| Imagem do MinIO escolhida | O guia deixa imagem e tag em aberto por causa da mudança de distribuição em 2025 (passo 2 do tutorial) |

**Sobre a ordem das aulas.** O `minio-init` usa dois arquivos (`init-minio.sh` e `policy-rais.json`) que a Aula 04 explica em detalhe. Aqui você os cria exatamente como no guia, para o Compose subir completo; o conteúdo deles é tema da próxima aula.

### Duração sugerida

Cerca de 3 horas. **\[Complemento didático\]**

## 2. Contextualização: por que orquestrar vários containers

O RAIS Lakehouse não é um container, são três que precisam subir numa ordem, conversar entre si e guardar dados fora deles. Fazer isso com `docker run` à mão é possível, mas frágil; o Compose descreve tudo num arquivo versionado. **\[Complemento didático\]** — contexto adicionado.

### Sem Compose

Para subir o ambiente só com `docker run`, você precisaria lembrar e digitar, a cada vez:

- criar uma rede e conectar os três containers a ela;
- criar os volumes;
- passar cerca de dez variáveis de ambiente, com as senhas certas;
- publicar quatro portas;
- esperar o MinIO responder antes de rodar o `minio-init`, e esperar o `minio-init` terminar antes de subir o `spark`.

Um esquecimento — uma variável errada, uma porta exposta para a rede toda — passa despercebido.

### Com Compose

Tudo isso fica no `docker-compose.yml`, que vai para o Git. O ambiente sobe com `docker compose up -d` e é igual para qualquer pessoa: o ADR-002 da Aula 01 ("reprodutível: qualquer pessoa sobe o projeto com um comando").

### Quando usar e quando não

| Situação | Compose serve? |
| --- | --- |
| Vários serviços numa máquina (desenvolvimento, estudo, servidor pequeno) | Sim — é o caso do curso |
| Um único container simples | Opcional; `docker run` basta |
| Vários servidores, alta disponibilidade, escala automática | Não é o foco do Compose; usa-se um orquestrador de cluster (ex.: Kubernetes) |

## 3. Fundamentação teórica

### 3.1 YAML em cinco regras

O `docker-compose.yml` é escrito em YAML. O guia (Parte 2.3) destaca a regra principal: **indentação com espaços, nunca tab**, indicando hierarquia. **\[Complemento didático\]** As outras quatro:

| Regra | Exemplo | Erro comum |
| --- | --- | --- |
| `chave: valor` cria um mapa | `image: nginx:1.27` | Esquecer o espaço depois dos dois-pontos |
| `- item` cria uma lista | `- "127.0.0.1:8080:80"` | Misturar lista e mapa no mesmo nível |
| Indentação define o pai | `ports` dentro de um serviço | Um espaço a mais ou a menos muda o significado |
| `#` inicia comentário | `# só acessível na sua máquina` | — |
| Aspas protegem valores ambíguos | `"127.0.0.1:8080:80"`, `restart: "no"` | Sem aspas, `no` vira o booleano falso |

### 3.2 A anatomia de um Compose (guia, Parte 2.3)

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

### 3.3 Rede e DNS: por que `localhost` não funciona entre containers

O Compose cria uma rede própria em que cada serviço é encontrado **pelo nome** (guia, Parte 2.3). Dentro do container `spark`, o MinIO está em `http://minio:9000`, e não em `localhost` — "um erro clássico", nas palavras do guia.

**\[Complemento didático\]** Por quê: cada container tem sua própria interface de rede. `localhost` dentro do `spark` é o próprio `spark`, onde nada escuta na porta 9000. O Compose registra cada serviço num DNS interno, então o nome `minio` resolve para o endereço do container do MinIO.

| De onde | Para onde | Endereço |
| --- | --- | --- |
| Container `spark` | MinIO | `http://minio:9000` |
| Container `minio-init` | MinIO | `http://minio:9000` |
| Seu navegador (host) | JupyterLab | `http://localhost:8888` (porta publicada) |
| Seu navegador (host) | Console do MinIO | `http://localhost:9001` |

### 3.4 Portas: `EXPOSE` × `ports`

- `EXPOSE` no Dockerfile só documenta (Aula 02).
- `ports` no Compose **publica**: liga uma porta do host a uma porta do container, no formato `IP_do_host:porta_host:porta_container`.
- Sem o IP (`"8888:8888"`), a porta fica acessível de **qualquer** interface do host, inclusive da rede. Com `127.0.0.1`, só da sua máquina. O guia usa sempre `127.0.0.1` (Parte 4.7).
- Containers na mesma rede não precisam de `ports` para conversar: o `spark` fala com o `minio` direto pela rede interna.

### 3.5 Volume nomeado × bind mount

| Critério | Volume nomeado | Bind mount |
| --- | --- | --- |
| Sintaxe | `minio-data:/data` | `./:/app` |
| Quem gerencia o local | O Docker | Você (um caminho do host) |
| Uso no curso | Dados do MinIO (`minio-data`), temporários do Spark (`spark-tmp`) | Código (`./:/app`), staging (`./staging:/staging`) |
| Ver e editar pelo host | Indireto | Direto |
| Apagado por `docker compose down -v` | **Sim** | Não (só a ligação) |

**Regra:** o que você edita vai em bind mount; o que só o serviço usa vai em volume (guia, Parte 2.1). O guia observa que, para guardar o MinIO num disco específico do servidor, basta trocar o volume por um bind mount (ex.: `/mnt/dados/minio:/data`).

### 3.6 Configuração: `.env`, interpolação e `environment`

O Compose lê automaticamente o arquivo `.env` da mesma pasta (guia, Parte 2.3):

| Sintaxe | Comportamento |
| --- | --- |
| `${VAR}` | Usa o valor de `VAR` |
| `${VAR:-padrao}` | Usa `padrao` se `VAR` não existir |
| `${VAR:?mensagem}` | **Interrompe** com erro se `VAR` não existir — ótimo para senhas obrigatórias |

**Atenção a dois mecanismos diferentes** **\[Complemento didático\]**:

1. **Interpolação:** o Compose substitui `${...}` no próprio YAML usando o `.env`. Isso configura o Compose.
2. **`environment`:** define as variáveis que o processo **dentro** do container enxerga.

Uma variável no `.env` só chega ao container se for listada em `environment` (ou se você usar `env_file`). O guia escolhe `environment` explícito para que cada container receba só o que precisa — o `spark` nunca recebe a senha de administrador do MinIO (Parte 4.7, menor privilégio).

### 3.7 Ordem de inicialização: `depends_on` e init container

- `depends_on: [minio]` só garante que o container do MinIO **foi iniciado** antes, não que já aceita conexões. Por isso o `init-minio.sh` tem um laço que espera o MinIO responder (Aula 04).
- `condition: service_completed_successfully` espera o outro serviço **terminar com código 0**. É assim que o `spark` só sobe depois que o `minio-init` criou bucket e usuário.
- **Init container** é um serviço que roda uma tarefa de preparação e termina (`restart: "no"`). O guia usa esse padrão no `minio-init` (Parte 4.7).

### 3.8 Limites de recursos

`cpus` e `mem_limit` limitam o container (os cgroups da Aula 02). As configurações do Spark precisam caber **dentro** desses limites (guia, Parte 4.7; detalhado na Aula 15). Se a JVM passar do `mem_limit`, o Docker encerra o container (código 137). No Docker Desktop, o limite do próprio Docker Desktop precisa ser maior que `CONTAINER_MEM`.

### 3.9 Política de reinício

| Valor | Comportamento | No curso |
| --- | --- | --- |
| `"no"` | Nunca reinicia | `minio-init` (roda uma vez) |
| `unless-stopped` | Reinicia se cair ou se o Docker reiniciar, exceto se você o parou | `minio` |
| Ausente | Igual a `"no"` | `spark` |

## 4. Arquitetura: topologia do Compose e ordem de inicialização

Os três serviços vivem numa rede privada criada pelo Compose. Do lado de fora, só o seu computador alcança quatro portas; dentro, os serviços se acham pelo nome.

&#91;embedded content: RAIS Lakehouse · 3 serviços, 2 volumes, 2 bind mounts\]

O `spark` fala com o `minio` pela rede interna (S3A) e só sobe depois que o `minio-init` termina; os dados do lake ficam no volume `minio-data`, e o código entra no `spark` por bind mount.

### Ordem de inicialização

1. `minio` inicia (nenhuma dependência).
2. `minio-init` inicia logo depois (`depends_on: [minio]`) e espera o MinIO responder.
3. `minio-init` cria bucket, política e usuário e termina com código 0.
4. `spark` é construído (se necessário) e inicia (`service_completed_successfully`).
5. O JupyterLab fica disponível em `127.0.0.1:8888`.

Se o passo 3 falhar, o passo 4 não acontece — e o erro aparece em `make ps`, não horas depois no meio de um pipeline.

## 5. Tutorial: subir o ambiente com um comando

Sete passos: escolher a imagem do MinIO, criar os arquivos do `minio-init`, configurar o `.env`, escrever o `docker-compose.yml`, escrever o Makefile, validar e subir. Trabalhe na raiz `~/rais-lakehouse` criada na Aula 02.

### Passo 1 — Escolher a imagem do MinIO

O guia deixa imagem e tag em aberto porque o projeto MinIO mudou a forma de distribuir a edição *community* em 2025. Antes de continuar:

1. Consulte o repositório oficial do MinIO e veja como a edição community é distribuída hoje (imagem pronta, imagem de terceiros ou build a partir do código).
2. Escolha uma **tag fixa** (nunca `latest`) para o servidor e outra para o cliente `mc`.
3. Anote as duas; elas vão para `MINIO_IMAGE` e `MC_IMAGE` no passo 3.

Como o código do curso usa só a API S3, outro armazenamento S3 compatível também serve; o guia cita essa alternativa na Parte 4. **\[Complemento didático\]** Nesse caso o `init-minio.sh`, que usa o `mc`, precisaria ser adaptado.

### Passo 2 — Arquivos do `minio-init` (explicados na Aula 04)

```bash
mkdir -p docker/minio staging
```

`docker/minio/policy-rais.json` (guia, Parte 4.5):

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

`docker/minio/init-minio.sh` (guia, Parte 4.5):

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

O guia avisa que a sintaxe de `mc admin policy` mudou entre versões do `mc`; se o `minio-init` falhar, confira com `mc admin policy --help` (Aula 04).

### Passo 3 — `.env.example` e `.env` (guia, Parte 4.6)

Crie `.env.example` — ele vai para o Git e documenta o que é necessário, com valores fictícios:

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

# ---------- Spark (ver Aula 15) ----------
SPARK_THREADS=4
SPARK_MEM=8g
SPARK_SHUFFLE=32

# ---------- Jupyter ----------
JUPYTER_TOKEN=troque-este-token
```

Depois copie e edite com os valores reais:

```bash
cp .env.example .env
id -u          # coloque este número em HOST_UID no .env
```

| Variável | O que pôr | Por quê |
| --- | --- | --- |
| `MINIO_IMAGE`, `MC_IMAGE` | As tags escolhidas no passo 1 | O Compose falha sem elas (`:?`) |
| `MINIO_ROOT_PASSWORD`, `APP_SECRET_KEY`, `JUPYTER_TOKEN` | Senhas longas e diferentes entre si | Evitar credenciais fracas ou reaproveitadas |
| `HOST_UID` | Saída de `id -u` | Permissões do bind mount (Aula 02) |
| `CONTAINER_CPUS`, `CONTAINER_MEM` | Abaixo do que sua máquina tem | Ver a tabela de pontos de partida da Aula 15; para 16 GB de RAM, o guia sugere `11g` e `6` |
| `SPARK_MEM` | Cerca de 65–75% de `CONTAINER_MEM` | A JVM precisa caber no container (Aula 15) |

**\[Complemento didático\]** Gere senhas aleatórias, por exemplo com `openssl rand -base64 24`. O `.env` não pode ir para o Git: o `.gitignore` da Aula 05 o exclui; até lá, não rode `git add .`.

### Passo 4 — `docker-compose.yml` (guia, Parte 4.7)

Salve na raiz do projeto:

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
      - "127.0.0.1:8888:8888"             # JupyterLab
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

### Passo 5 — Makefile (guia, Parte 4.8)

> A indentação dos comandos **tem que ser TAB**, não espaços (guia). Se o seu editor converte tab em espaços, desative isso para Makefiles.

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

**Alvos da plataforma** **\[Complemento didático\]** — acrescente ao fim do Makefile. Eles usam os checks em `labcheck/` (plano técnico, seção 7):

```makefile
AULA ?= 01
ANO  ?= 2022

.PHONY: check check-host progresso

check:           ## valida uma aula no container. Ex.: make check AULA=11 ANO=2022
	$(COMPOSE) exec spark pytest -v labcheck/test_aula$(AULA).py --ano $(ANO)

check-host:      ## valida aulas de infraestrutura (02-03). Ex.: make check-host AULA=03
	.venv-host/bin/pytest -v labcheck/host/test_aula$(AULA).py

progresso:       ## gera curso/docs/progresso.md a partir do histórico
	$(COMPOSE) exec spark python -m scripts.gerar_progresso
```

Para o `help` listar alvos com hífen (`check-host`), troque `'^[a-z]+:.*##'` por `'^[a-z-]+:.*##'` na regra `help`.

**Alvos que ainda não funcionam:** `smoke` (Aula 06), `pipeline` (Aula 14), `check` e `progresso` (esqueleto da plataforma: `--ano` é uma opção definida no `labcheck/conftest.py`). Eles ficam prontos aqui para não reabrir o Makefile a cada aula.

### Passo 6 — Validar antes de subir

```bash
docker compose config
```

- Mostra o YAML final com as variáveis resolvidas (guia, Parte 2.4). **Atenção:** ele imprime também as senhas do `.env`; não cole essa saída em lugar público.
- Se faltar uma variável marcada com `:?`, o comando para com a mensagem que você escreveu (ex.: `defina MINIO_IMAGE no .env`).
- Para só validar, sem imprimir: `docker compose config -q` (silencioso; o código de saída diz se está válido).

### Passo 7 — Subir

```bash
make up            # ou: docker compose up -d --build
make ps            # minio "running", minio-init "exited (0)", spark "running"
docker compose logs minio-init      # deve terminar com "[init] MinIO pronto."
```

Acesse (guia, Parte 4.9):

- **JupyterLab:** http://localhost:8888, com o `JUPYTER_TOKEN`.
- **Console do MinIO:** http://localhost:9001, com o usuário root, se disponível na sua versão.

**Resultados esperados:** os três serviços aparecem em `make ps` com os estados acima; o JupyterLab abre no navegador; o console do MinIO mostra o bucket `rais`, vazio. Estes são os estados que a configuração deve produzir — confira os da sua execução.

## 6. Como cada bloco funciona

### `name: rais-lakehouse`

Define o nome do projeto. Ele vira prefixo de tudo que o Compose cria: containers (ex.: `rais-lakehouse-spark-1`, nome usado no `docker stats` da Aula 15), volumes (`rais-lakehouse_minio-data`) e a rede (`rais-lakehouse_default`). **\[Complemento didático\]** Sem `name`, o prefixo seria o nome da pasta — e renomear a pasta "perderia" os volumes antigos.

### Serviço `minio`

| Chave | O que faz | Por quê (guia, Parte 4.7) |
| --- | --- | --- |
| `image: ${MINIO_IMAGE:?...}` | Imagem do servidor | Obrigatória; tag fixa definida por você |
| `command: server /data --console-address ":9001"` | Inicia o servidor guardando dados em `/data` e o console na 9001 | `/data` é onde o volume é montado |
| `environment` | Usuário e senha de administrador | Só o MinIO e o `minio-init` recebem esses valores |
| `ports` | 9000 (API S3) e 9001 (console), só em `127.0.0.1` | Acesso do seu navegador sem expor à rede |
| `volumes: minio-data:/data` | Persiste o lake | "O lake inteiro mora aqui" |
| `restart: unless-stopped` | Volta sozinho se cair | Armazenamento deve estar sempre de pé |

### Serviço `minio-init`

| Chave | O que faz |
| --- | --- |
| `image: ${MC_IMAGE:?...}` | Imagem do cliente `mc` |
| `depends_on: [minio]` | Só garante que o MinIO foi iniciado antes; o script espera ele responder |
| `entrypoint` | Substitui o comando padrão da imagem pelo script |
| `environment` | Credenciais de root (para administrar), da aplicação (para criar o usuário) e nome do bucket |
| `volumes ... :ro` | Monta o script e a política **somente leitura** (`:ro`), sem copiá-los para uma imagem |
| `restart: "no"` | Roda uma vez e termina — o padrão *init container* |

### Serviço `spark`

| Chave | O que faz | Observação |
| --- | --- | --- |
| `build` + `args.HOST_UID` | Faz o mesmo build da Aula 02, lendo o UID do `.env` | `context: .` é a raiz; `dockerfile` aponta o caminho |
| `image: rais-spark:local` | Dá ao resultado do build o nome da Aula 02 | Com `build` e `image` juntos, o Compose constrói e etiqueta |
| `depends_on ... service_completed_successfully` | Sobe só depois que o `minio-init` terminou com código 0 | Se o init falha, o `spark` não sobe — falha visível, não silenciosa |
| `MINIO_ENDPOINT: http://minio:9000` | Endereço do MinIO pela rede interna | **Nome do serviço, não `localhost`** |
| `S3_ACCESS_KEY`, `S3_SECRET_KEY` | Credenciais do usuário da aplicação | Nunca as de root |
| `RAIS_LAKE`, `RAIS_STAGING`, `SPARK_*` | Configuração lida por `config/settings.py` e `get_spark` | Aulas 05, 06 e 15 |
| `ports` 8888 e `4040-4041` | Jupyter e Spark UI | Faixa 4040–4041: se o Jupyter já tem uma sessão na 4040, um segundo processo (como o pipeline) usa a 4041 |
| `./:/app` | Bind mount do código | Edita no VS Code, o container vê na hora |
| `${HOST_STAGING_DIR:-./staging}:/staging` | Bind mount da landing e da raw | Pode apontar para um disco maior |
| `spark-tmp:/tmp/spark` | Volume para *spill* e shuffle | Aula 15 |
| `cpus`, `mem_limit` | Limites do container | `SPARK_MEM` precisa caber em `CONTAINER_MEM` |
| `command: > jupyter lab ...` | Substitui o `CMD ["bash"]` da imagem pelo JupyterLab | `>` em YAML junta as linhas numa só |

**Detalhe do `command`.** `--ip=0.0.0.0` faz o Jupyter escutar em todas as interfaces **dentro** do container; isso é necessário para a porta publicada funcionar. Quem restringe o acesso à sua máquina é o `127.0.0.1` em `ports`, não o Jupyter. `--ServerApp.token` exige o token no primeiro acesso.

### Bloco `volumes:` final

Declara os volumes nomeados. O Compose os cria na primeira subida e os mantém em `down`. Só `down -v` os apaga (guia, Parte 2.4: "⚠️ remove também os VOLUMES (apaga o lake!)").

### Makefile

| Elemento | Significado |
| --- | --- |
| `COMPOSE := docker compose` | Variável atribuída uma vez |
| `ANOS ?= 2022` | Valor padrão que pode ser trocado na chamada: `make pipeline ANOS="2021 2022"` |
| `.PHONY` | Diz ao `make` que esses alvos não são arquivos; sem isso, um arquivo chamado `test` faria `make test` não rodar |
| `## texto` | Comentário que o alvo `help` extrai para listar os comandos |
| `$$1`, `$$2` | `$$` escapa o `$` para o `awk` receber `$1` |
| `@` no início do comando | Não ecoa o comando antes de executá-lo |

### Comandos do dia a dia (guia, Parte 2.4)

```bash
docker compose up -d --build      # constrói (se preciso) e sobe tudo em segundo plano
docker compose ps                 # lista os containers e o estado de cada um
docker compose logs -f spark      # acompanha o log de um serviço
docker compose exec spark bash    # abre um terminal dentro do container
docker compose stop               # para os containers (mantém tudo)
docker compose down               # remove containers e rede (volumes ficam)
docker compose down -v            # ⚠️ remove também os VOLUMES (apaga o lake!)
docker compose config             # mostra o YAML final, com variáveis resolvidas
```

**\[Complemento didático\]** `exec` roda um comando num container **já em execução**; `docker compose run` cria um container **novo** para o comando. No curso, use `exec`.

## 7. Exemplos práticos

Cinco experimentos com o ambiente no ar, cada um provando um conceito da seção 3. **\[Complemento didático\]** — experimentos adicionados; só usam o que o guia configura.

### Exemplo 1 — DNS do Compose e o erro do `localhost`

```bash
# Dentro do spark: o nome "minio" resolve para um IP da rede do Compose
docker compose exec spark getent hosts minio

# Pelo nome do serviço: funciona
docker compose exec spark python -c "import urllib.request as u; print(u.urlopen('http://minio:9000/minio/health/live').status)"

# Por localhost: falha
docker compose exec spark python -c "import urllib.request as u; print(u.urlopen('http://localhost:9000/minio/health/live').status)"
```

- **Esperado:** o primeiro imprime um IP e o nome `minio`; o segundo imprime `200` (o MinIO responde no endpoint de saúde); o terceiro termina com erro de conexão recusada — dentro do `spark`, nada escuta na 9000.
- Este é o erro clássico do guia, reproduzido de propósito.

### Exemplo 2 — Cada container vê só as variáveis dele

```bash
docker compose exec spark env | grep -E 'MINIO|S3_|RAIS|SPARK' | sed 's/=.*/=***/'
docker compose exec spark printenv MINIO_ROOT_PASSWORD; echo "código de saída: $?"
```

- O `sed` troca os valores por `***` para você não exibir senhas na tela.
- **Esperado:** aparecem `MINIO_ENDPOINT`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `RAIS_*` e `SPARK_*`; `MINIO_ROOT_PASSWORD` não existe no `spark` (código de saída diferente de 0). É o menor privilégio do guia funcionando.

### Exemplo 3 — Volumes sobrevivem ao `down`

```bash
make down          # remove containers e rede
docker volume ls   # rais-lakehouse_minio-data e rais-lakehouse_spark-tmp continuam
make up            # sobe de novo
```

- **Esperado:** depois do `make up`, o console do MinIO mostra o bucket `rais` como antes.
- **Não rode `docker compose down -v`** fora de um teste consciente: ele apaga o lake.

### Exemplo 4 — O `minio-init` é idempotente

```bash
docker compose run --rm minio-init
```

- `run --rm` cria um container novo do serviço, executa o script e o remove.
- **Esperado:** o log termina em `[init] MinIO pronto.` e o código de saída é 0, mesmo com bucket, política e usuário já existentes. É o que permite subir o ambiente quantas vezes quiser.

### Exemplo 5 — Os limites de recursos estão valendo

```bash
docker stats --no-stream
```

- **Esperado:** na linha `rais-lakehouse-spark-1`, a coluna `MEM USAGE / LIMIT` mostra como limite o valor de `CONTAINER_MEM`. Os containers sem `mem_limit` mostram como limite a memória total disponível ao Docker.

## 8. Armadilhas, diagnóstico e soluções

| Sintoma | Causa provável | Como confirmar | Solução |
| --- | --- | --- | --- |
| `required variable MINIO_IMAGE is missing a value: defina MINIO_IMAGE no .env` | `.env` ausente, fora da raiz ou sem a variável | `ls -a` na raiz; `docker compose config` | Criar o `.env` a partir do `.env.example` (passo 3) |
| Erro de YAML (`mapping values are not allowed`, `did not find expected key`) | Indentação errada ou tab no YAML | A mensagem indica linha e coluna | Usar só espaços; conferir alinhamento |
| `minio-init` termina com erro | Credenciais ou sintaxe do `mc` (guia, Apêndice B) | `docker compose logs minio-init` | Ajustar o script à versão do `mc` (Aula 04) |
| `spark` não sobe e `make ps` mostra `minio-init` com código ≠ 0 | O `spark` depende do init (guia, Apêndice B) | `make ps` | Resolver o `minio-init` primeiro |
| `minio-init` fica preso em "aguardando o MinIO" | MinIO não subiu (imagem errada, senha curta) | `docker compose logs minio` | Corrigir a causa no log do MinIO |
| `Connection refused` ao acessar o MinIO de dentro do `spark` | Uso de `localhost` (guia, Apêndice B) | Exemplo 1 | Usar `http://minio:9000` |
| `Bind for 127.0.0.1:8888 failed: port is already allocated` | **\[Complemento didático\]** Outro programa usa a porta | `docker ps` ou outro Jupyter aberto | Parar o outro processo ou mudar a porta do host (`127.0.0.1:8889:8888`) |
| `Permission denied` em `/app` ou `/staging` | UID diferente entre host e container (guia, Apêndice B) | `id` no container × `id -u` no host | Ajustar `HOST_UID` e `make up` (reconstrói) |
| Container `spark` reinicia ou sai com código 137 | `mem_limit` estourado (guia, Apêndice B) | `docker compose ps -a`; `docker stats` | Reduzir `SPARK_MEM` ou aumentar `CONTAINER_MEM` |
| `make: *** missing separator` | Espaços no lugar de TAB no Makefile (guia, Apêndice B) | Editor mostrando espaços | Usar TAB |
| Lake sumiu depois de reiniciar | Alguém rodou `down -v` | `docker volume ls` sem `minio-data` | Recarregar a partir da landing (ela é a fonte da verdade, Aula 01) |
| Mudança no `.env` não fez efeito | Containers criados com os valores antigos | `docker compose config` mostra o novo valor | `make up` recria os containers afetados |

### Roteiro de diagnóstico

**\[Complemento didático\]**

1. `docker compose config -q` — o arquivo é válido e todas as variáveis existem?
2. `make ps` — quem está `running`, quem saiu e com que código?
3. `docker compose logs <serviço>` — leia o fim do log de quem falhou primeiro, na ordem minio → minio-init → spark.
4. `docker compose exec spark bash` — teste de dentro (DNS, variáveis, permissões).

## 9. Boas práticas para produção

1. **Configuração no `.env`, modelo no `.env.example`.** O `.env` real nunca vai para o Git (guia, Partes 3.3 e 4.6).
2. **`${VAR:?mensagem}` para tudo que é obrigatório,** em especial senhas e imagens: o erro aparece na subida, com uma mensagem útil.
3. **`environment` explícito por serviço** em vez de `env_file` compartilhado: cada container recebe só o que precisa (Parte 4.7).
4. **Portas publicadas em `127.0.0.1`** (Parte 4.7). Exponha na rede só com TLS e autenticação forte.
5. **Volumes nomeados para dados de serviço; bind mount para o que você edita.**
6. **Init containers idempotentes** para preparar dependências, com `service_completed_successfully`.
7. **Limites de CPU e memória definidos,** coerentes com a configuração do Spark (Aula 15).
8. **`docker compose config` antes de subir** mudanças grandes.
9. **Makefile como documentação executável:** os comandos importantes ficam com nome e descrição em `make help`.
10. **\[Complemento didático\]** Em servidor compartilhado, guarde senhas num gerenciador de segredos em vez de arquivo `.env` em disco; para estudo, o `.env` com permissão restrita (`chmod 600 .env`) basta.

## 10. Riscos: segurança, desempenho, custos e integridade

| Tipo | Risco | Mitigação |
| --- | --- | --- |
| Segurança | MinIO ou Jupyter acessíveis pela rede | Portas em `127.0.0.1` |
| Segurança | Senha de root do MinIO dentro do `spark` | `environment` explícito, só com o usuário da aplicação |
| Segurança | `.env` commitado | `.gitignore` (Aula 05); se acontecer, troque as senhas (guia, Parte 16.4) |
| Segurança | `docker compose config` imprime segredos | Não compartilhar a saída; usar `-q` para validar |
| Segurança | Credenciais fracas ou padrão | `.env.example` com placeholders, nunca senhas reais; gerar senhas aleatórias |
| Desempenho | Spark sem memória dentro do container | `SPARK_MEM` ≈ 65–75% de `CONTAINER_MEM` (Aula 15) |
| Desempenho | Spill em `/tmp` pequeno | Volume `spark-tmp` dedicado |
| Custo | Volume `minio-data` crescendo sem controle | Monitorar `docker system df`; `VACUUM` do Delta (Aula 14) |
| Integridade | `down -v` apaga o lake | Nunca no dia a dia; a landing permite reconstruir |
| Integridade | `spark` subindo antes de bucket e usuário existirem | `depends_on` com `service_completed_successfully` |

## 11. Laboratório e validação na plataforma

A aula está concluída quando os quatro checks passam com o ambiente no ar e o checklist manual está marcado. Como na Aula 02, os checks rodam no host, porque consultam o próprio Docker Compose.

### O que esta aula acrescenta ao projeto

| Arquivo | Papel no projeto final |
| --- | --- |
| `docker-compose.yml` | Define todo o ambiente; as aulas seguintes só o usam |
| `.env.example` | Documenta a configuração necessária; vai para o Git |
| `.env` | Configuração real; **não** vai para o Git |
| `Makefile` | Interface de comandos do curso, incluindo os alvos da plataforma |
| `docker/minio/*` | Preparação do MinIO, detalhada na Aula 04 |

### Checks automáticos

**\[Complemento didático\]** — código da plataforma. Arquivo `labcheck/host/test_aula03.py`, executado na raiz do projeto:

```python
"""Checks da Aula 03. Rodam no host, na raiz do projeto, com o ambiente no ar."""
import json
import subprocess


def compose(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", "compose", *args], capture_output=True, text=True, timeout=120)


def servicos() -> dict:
    """Estado de cada serviço, incluindo os que já terminaram (-a)."""
    r = compose("ps", "-a", "--format", "json")
    assert r.returncode == 0, f"docker compose ps falhou: {r.stderr.strip()}"
    texto = r.stdout.strip()
    # Versões recentes imprimem um JSON por linha; algumas antigas, uma lista. Aceita os dois.
    if texto.startswith("["):
        itens = json.loads(texto)
    else:
        itens = [json.loads(linha) for linha in texto.splitlines() if linha.strip()]
    return {item["Service"]: item for item in itens}


def test_a03_compose_valido():
    r = compose("config", "-q")
    assert r.returncode == 0, f"Compose inválido ou variável faltando: {r.stderr.strip()}"


def test_a03_servicos_no_ar():
    s = servicos()
    for nome in ("minio", "spark"):
        estado = s.get(nome, {}).get("State")
        assert estado == "running", f"{nome} está '{estado}'. Veja: docker compose logs {nome}"


def test_a03_minio_init_ok():
    init = servicos().get("minio-init")
    assert init is not None, "minio-init nunca rodou. Rode: make up"
    assert init["State"] == "exited" and init["ExitCode"] == 0, (
        f"minio-init: estado {init['State']}, código {init['ExitCode']}. "
        "Veja: docker compose logs minio-init (Aula 04)"
    )


def test_a03_portas_so_locais():
    r = compose("config", "--format", "json")  # saída fica só na memória do teste
    assert r.returncode == 0, r.stderr.strip()
    expostas = [
        f"{nome}:{porta.get('published')}"
        for nome, svc in json.loads(r.stdout)["services"].items()
        for porta in svc.get("ports", [])
        if porta.get("host_ip") != "127.0.0.1"
    ]
    assert not expostas, f"Portas expostas fora de 127.0.0.1: {expostas}"
```

- **Entradas:** o `docker-compose.yml`, o `.env` e o estado atual dos containers.
- **Saídas:** passou ou falhou, com o comando de diagnóstico na mensagem.
- **Sobre `config --format json`:** a saída contém as senhas resolvidas do `.env`; o teste só a lê em memória e nunca a imprime.
- **Limite:** os nomes de campo (`Service`, `State`, `ExitCode`, `host_ip`) são os do Compose v2 atual. Se a sua versão usar outros, o teste falha com `KeyError` — confira a saída de `docker compose ps -a --format json` e ajuste.

### Como rodar

```bash
make up
make check-host AULA=03
```

### Checklist manual

- [ ] O Exemplo 1 mostrou que `minio` funciona e `localhost` não, de dentro do `spark`.
- [ ] O Exemplo 2 mostrou que o `spark` não recebe a senha de root.
- [ ] O Exemplo 3 mostrou que o bucket sobrevive a `make down` + `make up`.
- [ ] Sei explicar a diferença entre interpolação no YAML e `environment`.
- [ ] Sei explicar o que `service_completed_successfully` garante e o que `depends_on` simples não garante.

## 12. Exercícios, revisão e desafios

### Exercícios práticos

1. Remova temporariamente `JUPYTER_TOKEN` do `.env` e rode `docker compose config -q`. Qual mensagem aparece e de onde ela vem? Restaure a variável.
2. Troque a porta do Jupyter no host para 8889 (`"127.0.0.1:8889:8888"`), rode `make up` e acesse. O que mudou dentro do container? E fora? Volte para 8888.
3. Sem alterar nada, compare `CONTAINER_MEM` e `SPARK_MEM` do seu `.env` com o Exemplo 5. Depois responda: o que aconteceria com `CONTAINER_MEM=2g` e `SPARK_MEM=8g` quando o Spark processasse dados de verdade? (Dica: seção 3.8 e código 137.)
4. Rode `make help` e confirme que todos os alvos aparecem com descrição, incluindo `check-host`.

### Perguntas de revisão

1. Por que o `spark` usa `http://minio:9000` e o seu navegador usa `http://localhost:9001`?
2. Qual a diferença entre `make down` e `docker compose down -v`?
3. O que acontece se o `minio-init` falhar? Por que esse comportamento é desejável?
4. Uma variável está no `.env` mas o processo no container não a enxerga. Qual a causa provável?
5. Por que o Jupyter usa `--ip=0.0.0.0` se o objetivo é acesso só local?
6. Por que o `restart` do `minio-init` é `"no"`, com aspas?

**Respostas sugeridas** (tente antes de ler):

1. Entre containers vale o DNS interno do Compose; do host, vale a porta publicada em `127.0.0.1`.
2. `down` remove containers e rede e mantém os volumes; `down -v` apaga também os volumes, ou seja, o lake.
3. O `spark` não sobe (`service_completed_successfully`); o erro aparece na subida em vez de surgir depois como falha de acesso ao MinIO.
4. Ela não está listada em `environment` do serviço; o `.env` só alimenta a interpolação do YAML.
5. Para escutar na interface de rede do container, por onde chega a porta publicada; a restrição ao host é feita pelo `127.0.0.1` em `ports`.
6. Sem aspas, o YAML interpreta `no` como booleano falso, e a chave espera um texto.

### Desafios

1. **Disco dedicado.** Troque o volume `minio-data` por um bind mount para uma pasta fora do projeto, como o guia sugere. Que cuidado com permissões você precisou tomar? Registre como ADR.
2. **Healthcheck.** Pesquise na documentação do Compose a chave `healthcheck` e a condição `service_healthy`. Escreva como ela poderia substituir o laço de espera do `init-minio.sh`, e qual dependência da imagem do MinIO isso criaria.
3. **Perfil do curso.** Quando chegar o esqueleto da plataforma, um serviço `curso` será acrescentado (plano técnico, seção 5). Esboce o bloco YAML dele usando a mesma imagem do `spark` e a porta `127.0.0.1:8000`.

## 13. Referências cruzadas

| Tema | Onde | Fonte no guia |
| --- | --- | --- |
| ADR-002 (Docker Compose) e papel de cada container | Aula 01 | Parte 1 |
| Imagem `rais-spark:local`, `HOST_UID`, camadas | Aula 02 | Partes 2.2, 4.4 |
| `init-minio.sh`, política `rais-rw`, menor privilégio no MinIO | Aula 04 | Parte 4.5 |
| `.gitignore` do `.env`; `config/settings.py` lendo as variáveis | Aula 05 | Partes 3.2, 7.2 |
| `get_spark` usando `MINIO_ENDPOINT`, `S3_*`, `SPARK_*`; `make smoke` | Aula 06 | Partes 4.10, 7.3 |
| `make pipeline` | Aula 14 | Parte 12 |
| `CONTAINER_MEM`, `SPARK_MEM`, `docker stats`, Spark UI 4040/4041 | Aula 15 | Parte 14 |
| Erros de subida, permissão e memória | Apêndice B | Apêndice B |
| Comandos `docker compose` e `make` | Apêndice D | Partes 2.4, 4.8 |
| Serviço `curso` e alvos `check`, `check-host`, `progresso` | Diagnóstico e plano técnico, seções 5 e 7 | — |
