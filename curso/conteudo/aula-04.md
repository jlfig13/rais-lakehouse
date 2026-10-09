# Aula 04 — MinIO e S3: buckets, S3A e menor privilégio

Oct 9, 2026

Ao final desta aula você entende como o lake é guardado no MinIO, o que o `minio-init` faz linha a linha e prova que o usuário da aplicação só consegue mexer no bucket `rais`.

```yaml
aula: 4
titulo: "MinIO e S3: buckets, S3A e menor privilégio"
origem: ["Guia Parte 4.1", "Guia Parte 4.5", "Guia Apêndice B"]
depende_de: [3]
entrega: ["docker/minio/init-minio.sh", "docker/minio/policy-rais.json"]
checks: [a04_bucket_existe, a04_app_grava_no_rais, a04_app_nao_cria_bucket, a04_app_nao_e_admin]
```

**Convenção:** **\[Complemento didático\]** marca o que não está no guia original.

## 1. Objetivos e pré-requisitos

1. Explicar object storage: bucket, objeto, chave e prefixo.
2. Explicar a API S3, o conector S3A e o *path-style*.
3. Ler a política `policy-rais.json` e o script `init-minio.sh` linha a linha.
4. Aplicar o princípio do menor privilégio e prová-lo com testes.
5. Usar o cliente `mc` para inspecionar o lake.

**Pré-requisitos:** Aula 03 concluída, ambiente no ar (`make ps` com `minio-init` em `exited (0)`).

## 2. Contextualização

Um lake precisa de um lugar barato, durável e acessível por rede para guardar arquivos. Disco local não escala nem é compartilhável; HDFS exige um cluster Hadoop. O padrão de mercado é **object storage com API S3**, e o MinIO oferece essa API on-premises (ADR-003 da Aula 01). Como o código do curso só fala S3, ele roda sem mudança em qualquer storage compatível.

| Opção | Quando faz sentido | Limitação |
| --- | --- | --- |
| Disco local / NFS | Estudo inicial, uma máquina | Sem API S3; difícil compartilhar |
| HDFS | Cluster Hadoop existente | Pesado para uso individual |
| MinIO (escolha do guia) | On-premises, API S3, aprender o padrão de nuvem | Distribuição community mudou em 2025 |
| Outros S3 compatíveis | Alternativa ao MinIO | O `init-minio.sh` usa `mc` e precisaria ser adaptado |

## 3. Fundamentação teórica

### 3.1 Object storage (guia, Parte 4.1)

- Guarda **objetos** (arquivo + metadados) dentro de **buckets**, acessados por API HTTP (o padrão S3).
- **Não existem diretórios de verdade.** `bronze/rais_vinculos/ano=2022/arq.parquet` é só o nome (a **chave**) do objeto; as "pastas" são uma convenção visual.
- **\[Complemento didático\]** O trecho comum no início de várias chaves (`bronze/rais_vinculos/`) é chamado de **prefixo**. Listar "uma pasta" é, na verdade, listar objetos com um prefixo.

| Sistema de arquivos | Object storage |
| --- | --- |
| Pastas reais, renomear é barato | Prefixos; "renomear" é copiar e apagar cada objeto |
| Editar parte de um arquivo | Objeto é escrito inteiro |
| Acesso por caminho local | Acesso por HTTP com credenciais |

**Consequência prática.** **\[Complemento didático\]** Como renomear é caro e não atômico em S3, o Delta não depende de renomear arquivos para garantir transações: ele usa o log `_delta_log/` (Aula 10).

### 3.2 S3A e path-style (guia, Parte 4.1)

- O Spark acessa S3 pelo conector **S3A** (biblioteca `hadoop-aws`, já na imagem desde a Aula 02), com caminhos `s3a://bucket/caminho`.
- O MinIO exige **path-style** (`http://minio:9000/rais/...`) em vez de *virtual-host style* (`http://rais.minio:9000/...`). Sem isso, o Spark tenta resolver o host `rais.minio` e falha com `UnknownHostException` (Apêndice B do guia). A configuração é `fs.s3a.path.style.access=true`, feita no `get_spark` (Aula 06).

### 3.3 Menor privilégio (guia, Parte 4.1)

O usuário *root* do MinIO serve só para administrar. A aplicação usa um usuário próprio, com acesso **apenas** ao bucket `rais`. **Por que:** se a credencial da aplicação vazar (num notebook compartilhado, num log), o estrago fica restrito a um bucket e não dá controle do servidor.

### 3.4 A política `policy-rais.json`

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

| Campo | Significado |
| --- | --- |
| `Version` | Versão da linguagem de políticas (formato da AWS que o MinIO adota); não é uma data sua |
| `Effect: Allow` | A regra concede permissão |
| `Action: s3:*` | Todas as ações S3 |
| `arn:aws:s3:::rais` | O bucket em si (listar, por exemplo) |
| `arn:aws:s3:::rais/*` | Todos os objetos dentro dele (ler, gravar, apagar) |

O que não está listado é negado: outros buckets e operações administrativas. O guia observa que, se o nome do bucket mudar no `.env`, o JSON precisa mudar também.

**\[Complemento didático\]** `s3:*` inclui apagar o próprio bucket `rais`. Para uma política mais estreita, liste só as ações necessárias (desafio 1).

## 4. Arquitetura e fluxo

```
  minio-init (root)                         spark (usuário rais-app)
  │ 1. mc alias set local ... ROOT          │
  │ 2. mc mb rais                           │  s3a://rais/bronze/...  → permitido
  │ 3. mc admin policy create rais-rw       │  s3a://outro/...        → negado (403)
  │ 4. mc admin user add rais-app           │  mc admin ...           → negado
  │ 5. mc admin policy attach rais-rw       │
  ▼                                          ▼
  ┌────────────────────────────────────────┐
  │ MinIO  — bucket rais                                     │
  │   bronze/  silver/  gold/  _smoke/  _lab/               │
  └────────────────────────────────────────┘
```

O root só aparece no `minio-init`; tudo que o curso processa usa o `rais-app`.

## 5. Tutorial: ler e operar o MinIO

### Passo 1 — Ler o script `init-minio.sh` (criado na Aula 03)

| Linha | O que faz | Por quê |
| --- | --- | --- |
| `set -eu` | Para no primeiro erro (`-e`) e em variável não definida (`-u`) | Falhar cedo e com clareza |
| `until mc alias set local ...; do sleep 2; done` | Tenta se conectar a cada 2 s até o MinIO responder | `depends_on` só garante que o MinIO iniciou, não que aceita conexões (Aula 03) |
| `mc mb --ignore-existing local/${RAIS_BUCKET}` | Cria o bucket; não falha se já existir | Idempotência |
| `mc admin policy create ... 2>/dev/null \|\| true` | Cria a política; ignora erro se já existir | Idempotência |
| `mc admin user add local "$APP_ACCESS_KEY" "$APP_SECRET_KEY"` | Cria (ou atualiza) o usuário da aplicação | Credencial separada da de root |
| `mc admin policy attach ... --user ...` | Liga a política ao usuário | Sem isso, o usuário não acessa nada |

O guia avisa: a sintaxe de `mc admin policy` mudou entre versões do `mc`; se der erro, rode `mc admin policy --help` dentro do container e ajuste.

**\[Complemento didático\]** O `|| true` torna o script idempotente, mas também esconde erros reais nessas duas linhas (ex.: sintaxe errada). Por isso o laboratório verifica o resultado final em vez de confiar no código de saída do script.

### Passo 2 — Abrir um terminal com o `mc`

```bash
# Container temporário do serviço minio-init, com shell em vez do script
docker compose run --rm --entrypoint /bin/sh minio-init
```

Dentro dele, configure dois apelidos — um como administrador, outro como aplicação:

```sh
mc alias set adm http://minio:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD"
mc alias set app http://minio:9000 "$APP_ACCESS_KEY" "$APP_SECRET_KEY"
```

- As variáveis já existem nesse container (bloco `environment` do `minio-init`).
- `alias` é um nome local para "servidor + credencial".

### Passo 3 — Explorar

```sh
mc ls adm                      # buckets visíveis para o root
mc ls app/rais                 # conteúdo do bucket como aplicação (vazio por enquanto)
mc admin user list adm         # usuários: deve aparecer rais-app
mc admin policy list adm       # políticas: deve aparecer rais-rw
```

### Passo 4 — Provar o menor privilégio

```sh
echo ok | mc pipe app/rais/_lab/teste.txt   # grava um objeto: deve funcionar
mc cat app/rais/_lab/teste.txt              # lê: imprime ok
mc rm app/rais/_lab/teste.txt               # apaga
mc mb app/outro-bucket                      # cria bucket: deve FALHAR (acesso negado)
mc admin user list app                      # operação de admin: deve FALHAR
```

Saia com `exit`; o container é removido (`--rm`).

## 6. Funcionamento e resultados esperados

| Passo | Resultado esperado | Se não acontecer |
| --- | --- | --- |
| `mc ls adm` | Lista o bucket `rais` | O `minio-init` falhou: `docker compose logs minio-init` |
| `mc admin user list adm` | `rais-app` com a política `rais-rw` | Linha `policy attach` falhou em silêncio (`\|\| true`) |
| `mc pipe` / `cat` / `rm` como `app` | Grava, lê e apaga | Política não anexada ou nome do bucket diferente no JSON |
| `mc mb app/outro-bucket` | Erro de acesso negado | Usuário com política ampla demais (ex.: `readwrite`) |
| `mc admin ... app` | Erro de acesso negado | Usuário com privilégio de admin — corrigir já |

Os valores acima são o que a configuração deve produzir; vale o que sua execução mostrar.

## 7. Exemplos práticos

**Exemplo 1 — Prefixos não são pastas.** **\[Complemento didático\]**

```sh
echo a | mc pipe app/rais/_lab/x/y/z.txt
mc ls app/rais/_lab/            # mostra x/ como se fosse pasta
mc rm app/rais/_lab/x/y/z.txt
mc ls app/rais/_lab/            # x/ some: não existia pasta, só a chave
```

**Exemplo 2 — Tamanho do lake.** Depois das Aulas 11–13, `mc du app/rais/bronze` e `mc du app/rais/silver` mostram quanto cada camada ocupa — útil no exercício de compressão da Aula 11.

**Exemplo 3 — Ver uma tabela Delta por dentro.** Depois da Aula 06: `mc ls --recursive app/rais/_smoke/teste` lista os `.parquet` e a pasta `_delta_log/` com um `.json` por versão.

## 8. Armadilhas, diagnóstico e soluções

| Sintoma | Causa provável | Solução |
| --- | --- | --- |
| `minio-init` termina com erro | Credenciais ou sintaxe do `mc` (guia, Apêndice B) | `docker compose logs minio-init`; ajustar ao `mc admin policy --help` |
| `403` / `InvalidAccessKeyId` no Spark | Usuário da aplicação não criado ou sem política (guia, Apêndice B) | Conferir o log do `minio-init` e o `APP_ACCESS_KEY` |
| `UnknownHostException: rais.minio` | Faltou path-style (guia, Apêndice B) | `fs.s3a.path.style.access=true` (Aula 06) |
| `Connection refused` | `localhost` em vez de `minio` (guia, Apêndice B) | `http://minio:9000` |
| Acesso negado só em alguns caminhos | Bucket renomeado no `.env` e não no JSON | Alinhar `RAIS_BUCKET` e `policy-rais.json` |
| MinIO não sobe | **\[Complemento didático\]** Senha de root curta demais ou imagem inválida | `docker compose logs minio` |
| Trocar `APP_SECRET_KEY` não tem efeito no Spark | Container `spark` criado com o valor antigo | `make up` para recriar |

## 9. Boas práticas

1. Root só para administrar; aplicação com usuário e política próprios (Parte 4.1).
2. Política restrita ao bucket do projeto; em produção, também às ações necessárias. **\[Complemento didático\]**
3. Scripts de preparação idempotentes (Parte 4.5), validados pelo estado final.
4. Organizar o bucket por prefixos de camada (`bronze/`, `silver/`, `gold/`) e separar áreas de teste (`_smoke/`, `_lab/`).
5. Backup do volume do MinIO e da landing (a landing é a fonte da verdade, Aula 01).
6. **\[Complemento didático\]** Em produção, HTTPS no MinIO (`fs.s3a.connection.ssl.enabled=true`); o curso usa HTTP porque tudo fica na rede interna e em `127.0.0.1`.

## 10. Riscos

| Tipo | Risco | Mitigação |
| --- | --- | --- |
| Segurança | Credencial de root vazar | Root só no `minio`/`minio-init`; nunca no `spark` |
| Segurança | Credencial da aplicação vazar | Política restrita ao bucket; trocar a senha e `make up` |
| Segurança | Tráfego sem TLS | Aceitável só em rede interna e porta local |
| Integridade | `s3:*` permite apagar o bucket | Política mais estreita (desafio 1); backup |
| Integridade | Escrita parcial visível em Parquet puro | Delta Lake (Aula 10) |
| Custo | Lake crescendo sem controle | `mc du`; `VACUUM` (Aula 14) |

## 11. Laboratório e validação na plataforma

**Contribuição ao projeto:** o bucket `rais` com usuário e política corretos é o destino de bronze, silver e gold.

**\[Complemento didático\]** Checks em `labcheck/host/test_aula04.py`. Rodam no host porque usam `docker compose run`; o teste roda o `mc` como **aplicação**, nunca como root.

```python
"""Checks da Aula 04: o usuário da aplicação acessa só o bucket rais."""
import subprocess

PREFIXO = 'mc alias set app http://minio:9000 "$APP_ACCESS_KEY" "$APP_SECRET_KEY" >/dev/null && '


def como_app(comando: str) -> subprocess.CompletedProcess:
    """Roda um comando mc num container temporário, autenticado como rais-app."""
    return subprocess.run(
        ["docker", "compose", "run", "--rm", "--entrypoint", "/bin/sh",
         "minio-init", "-c", PREFIXO + comando],
        capture_output=True, text=True, timeout=180,
    )


def test_a04_bucket_existe():
    r = como_app("mc ls app/rais")
    assert r.returncode == 0, f"rais-app não lista o bucket: {r.stderr.strip()[-300:]}"


def test_a04_app_grava_no_rais():
    r = como_app("echo ok | mc pipe app/rais/_lab/aula04.txt && mc cat app/rais/_lab/aula04.txt "
                 "&& mc rm app/rais/_lab/aula04.txt")
    assert r.returncode == 0 and "ok" in r.stdout, f"Gravação falhou: {r.stderr.strip()[-300:]}"


def test_a04_app_nao_cria_bucket():
    r = como_app("mc mb app/proibido-aula04")
    assert r.returncode != 0, (
        "rais-app conseguiu criar um bucket: a política está ampla demais. "
        "Apague o bucket proibido-aula04 como root e revise policy-rais.json."
    )


def test_a04_app_nao_e_admin():
    r = como_app("mc admin user list app")
    assert r.returncode != 0, "rais-app executa comandos de administração. Revise a política."
```

```bash
make check-host AULA=04
```

**Checklist manual**

- [ ] Sei explicar por que "pastas" em S3 são prefixos.
- [ ] Sei explicar path-style e o erro que aparece sem ele.
- [ ] Li cada linha do `init-minio.sh` e sei o motivo dela.
- [ ] Os dois comandos do passo 4 que deviam falhar falharam.

## 12. Exercícios, revisão e desafios

**Exercícios**

1. Rode `docker compose run --rm minio-init` duas vezes e confirme que termina com código 0 nas duas. Que linhas garantem isso?
2. Grave três objetos em `app/rais/_lab/a/`, `_lab/b/` e `_lab/a/c/` e liste `_lab/` com e sem `--recursive`. Explique a diferença. Apague-os.

**Revisão**

1. Por que a credencial do Spark não é a de root?
2. O que significa `arn:aws:s3:::rais/*`?
3. Por que o Delta não depende de renomear arquivos?
4. Qual erro aparece sem path-style e por quê?

**Respostas sugeridas:** (1) menor privilégio: um vazamento fica restrito ao bucket; (2) todos os objetos dentro do bucket `rais`; (3) em S3 renomear é copiar e apagar, caro e não atômico — o Delta usa o `_delta_log`; (4) `UnknownHostException: rais.minio`, porque o cliente tenta o estilo `bucket.host`.

**Desafios**

1. Escreva uma política que permita só listar, ler, gravar e apagar **objetos** em `rais` (sem apagar o bucket). Teste com o passo 4 antes de adotá-la e registre como ADR.
2. Crie um segundo usuário somente leitura (`rais-leitor`) para um futuro BI e prove que ele não grava.

## 13. Referências cruzadas

| Tema | Onde |
| --- | --- |
| ADR-003 (MinIO) | Aula 01 |
| JARs `hadoop-aws` e SDK na imagem | Aula 02 |
| Serviço `minio-init`, `depends_on`, `.env` | Aula 03 |
| `get_spark` com S3A e path-style; teste de fumaça em `_smoke/` | Aula 06 |
| `_delta_log` e por que o Delta evita renomear | Aula 10 |
| `VACUUM` e tamanho do lake | Aula 14 |
| Erros 403, path-style, `Connection refused` | Apêndice B |
| Comandos `mc` | Apêndice D |
