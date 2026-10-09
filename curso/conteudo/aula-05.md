# Aula 05 — Repositório, Git e configuração por ambiente

Oct 9, 2026

Ao final desta aula o RAIS Lakehouse é um repositório Git organizado, sem dados nem segredos versionados, com a configuração lida de variáveis de ambiente em `config/settings.py`.

```yaml
aula: 5
titulo: "Repositório, Git e configuração por ambiente"
origem: ["Guia Parte 3", "Guia Parte 7.1", "Guia Parte 7.2"]
depende_de: [1, 3]
entrega: [".gitignore", "config/settings.py", "estrutura de pastas", "primeiro commit"]
checks: [a05_repositorio_git, a05_env_ignorado, a05_env_nao_versionado, a05_estrutura, a05_settings_padrao]
```


## 1. Objetivos e pré-requisitos

1. Montar a estrutura de pastas do projeto e justificar cada pasta.
2. Escrever `.gitignore` e `.dockerignore` que protegem dados e segredos.
3. Explicar a configuração por ambiente (12-Factor) e escrever `config/settings.py`.
4. Fazer o primeiro commit com mensagem no padrão Conventional Commits.

**Pré-requisitos:** Aulas 01 a 03 (arquivos `docs/decisoes.md`, Dockerfile, compose, `.env`). Git instalado (`git --version`) e configurado com `git config --global user.name` e `user.email`.

**Nota de ordem.** O guia monta a estrutura antes da infraestrutura (Parte 3). O curso inverteu a ordem para você ver o Docker funcionando antes; esta aula organiza o que já existe e completa o que falta.

## 2. Contextualização

Um projeto de dados acumula três coisas que não podem ser tratadas igual: **código** (versão controlada, revisada), **configuração** (muda por máquina, inclui senhas) e **dados** (grandes, reconstruíveis). Misturar os três gera os problemas clássicos: senha no GitHub, repositório de vários GB, código que só roda na máquina de quem escreveu. Esta aula separa os três.

| Tipo | Onde vive | Vai para o Git? |
| --- | --- | --- |
| Código e documentação | `src/`, `config/`, `docker/`, `docs/`, `tests/` | Sim |
| Modelo de configuração | `.env.example` | Sim |
| Configuração real e segredos | `.env` | **Nunca** |
| Dados | `staging/`, volume do MinIO | **Nunca** |
| Progresso pessoal da plataforma | `progress/` | Não |

## 3. Fundamentação teórica

### 3.1 Por que esta estrutura (guia, Parte 3.1)

- `src/` guarda o código de produção, importável e testável. `notebooks/` é só para explorar.
- `config/` separa **configuração** de **lógica**: trocar de ambiente não exige mudar código.
- `docker/` concentra a infraestrutura; `docs/` concentra as decisões e o conhecimento do domínio.

Notebook não é código de produção porque mistura execução e estado (células rodadas fora de ordem), é difícil de testar e gera diffs ilegíveis no Git. Explore no notebook; quando algo funciona, mova para `src/` como função.

### 3.2 Configuração por ambiente (guia, Parte 7.1)

Os princípios da metodologia **12-Factor App** orientam o projeto: a configuração vem de **variáveis de ambiente**, não fica fixa no código. O mesmo código roda no seu notebook, no container e num servidor, mudando só o ambiente.

A cadeia completa no curso:

```
.env  ──(interpolação)──▶  docker-compose.yml  ──(environment)──▶  processo no container
                                                                   │
                                                     os.getenv("RAIS_LAKE", padrão)
                                                                   ▼
                                                         config/settings.py
```

### 3.3 Regras de ouro do repositório (guia, Parte 3.3)

1. **Nunca** versione dados nem segredos (`.env`, senhas, chaves).
2. Versione um `.env.example` com valores fictícios para documentar o que é necessário.
3. Faça um commit pequeno por passo concluído.

### 3.4 `.gitignore` × `.dockerignore`

| Arquivo | Quem lê | Protege contra |
| --- | --- | --- |
| `.gitignore` | Git | Dados e segredos irem para o repositório |
| `.dockerignore` | `docker build` | Dados e segredos irem para o contexto de build e para camadas da imagem (Aula 02) |

Um não substitui o outro.

## 4. Arquitetura: a estrutura final (guia, Parte 3.1)

```
rais-lakehouse/
├── .github/workflows/ci.yml      # CI (Aula 16)
├── config/__init__.py, settings.py
├── docker/minio/ (init-minio.sh, policy-rais.json)   docker/spark/Dockerfile
├── docs/decisoes.md, dicionario.md
├── notebooks/                    # exploração
├── scripts/__init__.py, smoke_test.py, bench.sh
├── src/__init__.py, utils.py, delta_io.py, dims.py, ingest.py,
│       bronze.py, silver.py, gold.py, checks.py, run_pipeline.py
├── staging/                      # landing/raw (NÃO versionado)
├── tests/conftest.py, test_utils.py
├── .dockerignore  .env.example  .gitignore  docker-compose.yml
├── LICENSE  Makefile  pyproject.toml  README.md
└── requirements.txt  requirements-dev.txt
```

**pastas da plataforma** (plano técnico, seção 6): `curso/` (site), `labs/` (exercícios verificáveis), `labcheck/` (checks; `labcheck/host/` para os do host) e `progress/` (não versionado).

## 5. Tutorial

### Passo 1 — Iniciar o repositório e criar as pastas (guia, Parte 3.2)

```bash
cd ~/rais-lakehouse
git init -b main        # -b main: nome do branch inicial

mkdir -p .github/workflows config docker/minio docker/spark docs notebooks scripts src staging tests
touch config/__init__.py scripts/__init__.py src/__init__.py staging/.gitkeep

# Pastas da plataforma
mkdir -p labs labcheck/host progress curso/docs
```

- `__init__.py` vazio marca a pasta como pacote Python, permitindo `from config.settings import ...`.
- `staging/.gitkeep`: o Git não versiona pastas vazias; o arquivo vazio mantém a pasta no repositório (o conteúdo dela fica ignorado).
- Se `docs/decisoes.md` (Aula 01) estiver em outro lugar, mova-o para `docs/`.

### Passo 2 — `.gitignore` (guia, Parte 3.2)

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

Acrescente as entradas da plataforma:

```gitignore
# Plataforma
progress/
.venv-host/
```

| Padrão | Significado |
| --- | --- |
| `staging/*` + `!staging/.gitkeep` | Ignora tudo dentro de `staging`, exceto o `.gitkeep` (`!` reinclui) |
| `*.7z`, `*.parquet` | Segurança extra: nenhum arquivo desses tipos entra, esteja onde estiver |
| `spark-warehouse/`, `metastore_db/`, `derby.log` | Arquivos que o Spark cria localmente em alguns usos |

O `.dockerignore` já foi criado na Aula 02.

### Passo 3 — `config/settings.py` (guia, Parte 7.2)

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

| Nome | Tipo | Origem | Usado em |
| --- | --- | --- | --- |
| `STAGING`, `LANDING`, `RAW` | `Path` (caminho local) | `RAIS_STAGING` (o compose define `/staging`) | Aulas 09 e 11 |
| `LAKE` | `str` (URI) | `RAIS_LAKE` (o compose define `s3a://rais`) | Todas as camadas |
| `BRONZE`, `SILVER`, `GOLD` | `str` | Derivados de `LAKE` | Aulas 11 a 14 |
| `ANOS` | `list[int]` | Fixo no código | Aula 14 |

**Por que `Path` para staging e `str` para o lake:** o staging é disco local, manipulado com `pathlib`; o lake é uma URI (`s3a://`) que só o Spark entende. `range(2019, 2025)` gera 2019 a 2024 (o fim não entra); atualize quando o MTE publicar um ano novo.

### Passo 4 — `docs/` e `.env.example`

- `docs/decisoes.md`: os ADRs da Aula 01.
- `docs/dicionario.md`: criado na Aula 09.
- Confirme que `.env.example` (Aula 03) tem só valores fictícios.

### Passo 5 — Conferir e fazer o primeiro commit

```bash
git status                    # NADA de .env, staging/* ou .7z na lista
git check-ignore -v .env      # mostra a regra do .gitignore que ignora o .env
git add .
git commit -m "chore: estrutura inicial do projeto"
```

- `git check-ignore -v` imprime o arquivo e a linha da regra; se não imprimir nada, o arquivo **não** está ignorado.
- `chore:` é o tipo para manutenção no padrão Conventional Commits (detalhado na Aula 16).

## 6. Funcionamento e resultados esperados

| Passo | Resultado esperado | Sinal de problema |
| --- | --- | --- |
| 1 | Pastas criadas, `git status` funciona | `fatal: not a git repository` |
| 2 | `.env` e `staging/*` somem do `git status` | `.env` listado como arquivo novo |
| 3 | `python -c "from config.settings import LAKE; print(LAKE)"` imprime `s3a://rais` | `ModuleNotFoundError: config` (rodou fora da raiz ou sem `__init__.py`) |
| 5 | `git log --oneline` mostra um commit | Commit contém `.env` (ver Riscos) |

## 7. Exemplos práticos

**Exemplo 1 — A mesma configuração, dois ambientes.**

```bash
# No host (sem as variáveis do compose): valores padrão
python3 -c "from config.settings import LAKE, STAGING; print(LAKE, STAGING)"

# No container (com as variáveis do compose)
docker compose exec spark python -c "from config.settings import LAKE, STAGING; print(LAKE, STAGING)"

# Sobrescrevendo só para um comando: lake em disco local, sem MinIO
RAIS_LAKE=file:///tmp/lake python3 -c "from config.settings import BRONZE; print(BRONZE)"
```

O código não mudou; só o ambiente. É o 12-Factor na prática.

**Exemplo 2 — O `.gitignore` funcionando.** Crie `staging/landing/teste.7z` com `touch` e rode `git status`: o arquivo não aparece. Apague-o.

## 8. Armadilhas, diagnóstico e soluções

| Sintoma | Causa | Solução |
| --- | --- | --- |
| `.env` aparece no `git status` | `.gitignore` ausente, com nome errado ou fora da raiz | Corrigir o `.gitignore`; `git check-ignore -v .env` |
| `.env` já foi commitado | Commit feito antes do `.gitignore` | `git rm --cached .env` + commit, **e troque todas as senhas**: o histórico guarda o conteúdo (guia, Parte 16.4) |
| `ModuleNotFoundError: No module named 'config'` | Executado fora da raiz ou sem `__init__.py` | Rodar da raiz; no container, `PYTHONPATH=/app` (Aula 02) resolve |
| Pasta `staging` sumiu do repositório clonado | Faltou `!staging/.gitkeep` | Ver passo 2 |
| Repositório enorme | Dados commitados | Remover do índice; dados grandes no histórico exigem reescrever o histórico |

## 9. Boas práticas

1. Estrutura previsível: produção em `src/`, exploração em `notebooks/`, decisões em `docs/` (Parte 3.1).
2. Configuração só por variável de ambiente, com padrões seguros (Parte 7.1).
3. `.env.example` sempre atualizado quando surgir variável nova.
4. Commits pequenos, um por passo concluído (Parte 3.3).
5. Revise `git status` antes de todo `git add .`; prefira `git add <arquivo>` quando estiver em dúvida.

## 10. Riscos

| Tipo | Risco | Mitigação |
| --- | --- | --- |
| Segurança | Segredo no histórico do Git | `.gitignore` desde o primeiro commit; se vazar, trocar senhas |
| Segurança | Segredo na imagem Docker | `.dockerignore` (Aula 02) |
| Integridade | Código dependente de caminho fixo da sua máquina | Caminhos só em `settings.py`, vindos do ambiente |
| Custo | Repositório pesado com dados | `staging/*`, `*.7z`, `*.parquet` ignorados |

## 11. Laboratório e validação na plataforma

**Contribuição ao projeto:** o repositório passa a ser a fonte única do projeto; `settings.py` é importado por todas as camadas.

`labcheck/host/test_aula05.py` (roda no host, na raiz):

```python
"""Checks da Aula 05: repositório organizado e sem segredos versionados."""
import os
import subprocess
import sys
from pathlib import Path

PASTAS = ["config", "docker/spark", "docker/minio", "docs", "notebooks", "scripts", "src", "staging", "tests"]


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], capture_output=True, text=True)


def test_a05_repositorio_git():
    assert git("rev-parse", "--is-inside-work-tree").returncode == 0, "Rode git init -b main (passo 1)."


def test_a05_env_ignorado():
    assert git("check-ignore", "-q", ".env").returncode == 0, ".env não está no .gitignore (passo 2)."


def test_a05_env_nao_versionado():
    r = git("ls-files", "--error-unmatch", ".env")
    assert r.returncode != 0, ".env está versionado! git rm --cached .env e TROQUE as senhas."


def test_a05_estrutura():
    faltando = [p for p in PASTAS if not Path(p).is_dir()]
    assert not faltando, f"Pastas ausentes: {faltando}"


def test_a05_settings_padrao():
    env = {k: v for k, v in os.environ.items() if not k.startswith("RAIS_")}
    r = subprocess.run([sys.executable, "-c", "from config.settings import LAKE; print(LAKE)"],
                       capture_output=True, text=True, env=env)
    assert r.stdout.strip() == "s3a://rais", f"Padrão inesperado: {r.stdout or r.stderr}"
```

- O último check remove as variáveis `RAIS_*` para conferir o **padrão** do `settings.py`.
- Rode com `make check-host AULA=05`.

**Checklist manual**

- [ ] `git log --oneline` mostra o primeiro commit, sem `.env` nem dados.
- [ ] Sei explicar a cadeia `.env` → compose → `os.getenv`.
- [ ] Rodei o Exemplo 1 e vi valores diferentes no host e no container.

## 12. Exercícios, revisão e desafios

**Exercícios**

1. Acrescente ao `settings.py` uma constante `EXPORT = STAGING / "export"` (usada na Aula 13) e faça um commit `feat: pasta de exportação`.
2. Simule o vazamento: crie um repositório de teste em `/tmp`, commite um `.env` falso e veja com `git log -p` que ele continua no histórico depois de `git rm`.

**Revisão**

1. Por que `staging/*` e não `staging/`?
2. Qual a diferença entre `.gitignore` e `.dockerignore`?
3. Por que `LAKE` é `str` e `LANDING` é `Path`?
4. O que fazer se o `.env` foi para o GitHub?

**Respostas sugeridas:** (1) para poder reincluir o `.gitkeep` com `!`; com `staging/` a pasta inteira é ignorada e a exceção não funciona; (2) um protege o repositório, o outro o contexto de build e a imagem; (3) o lake é uma URI do Spark, o staging é disco local; (4) remover do índice e trocar todas as senhas — apagar o commit não basta.

**Desafio:** escreva um *pre-commit hook* (`.git/hooks/pre-commit`) que impeça commits contendo `.env` ou arquivos `.7z`.

## 13. Referências cruzadas

| Tema | Onde |
| --- | --- |
| ADRs em `docs/decisoes.md` | Aula 01 |
| `.dockerignore`, `PYTHONPATH=/app` | Aula 02 |
| `.env`, `.env.example`, `environment` | Aula 03 |
| `get_spark` lendo o ambiente | Aula 06 |
| `docs/dicionario.md` | Aula 09 |
| Conventional Commits, branches, README, LICENSE | Aula 16 |
| Plano técnico: pastas da plataforma | Diagnóstico e plano técnico, seção 6 |
