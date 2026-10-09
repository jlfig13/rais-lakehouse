<!-- Página GERADA de docs/guia/rais-lakehouse-guia.md -->

# Parte [2](parte-02.md) — Conceitos de Docker e Docker Compose

## 2.1 Os blocos fundamentais { #parte-2-1 }

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

## 2.2 Sintaxe do Dockerfile { #parte-2-2 }

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

## 2.3 Sintaxe do Docker Compose (YAML) { #parte-2-3 }

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

## 2.4 Comandos essenciais { #parte-2-4 }

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
