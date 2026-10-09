<!-- Página GERADA de docs/guia/rais-lakehouse-guia.md -->

# Parte [3](parte-03.md) — Estrutura do repositório e Git

## 3.1 Estrutura final { #parte-3-1 }

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

## 3.2 Criar o repositório { #parte-3-2 }

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

## 3.3 Regras de ouro do repositório { #parte-3-3 }

1. **Nunca** versione dados nem segredos (`.env`, senhas, chaves).
2. Versione um `.env.example` com valores fictícios, para documentar o que é necessário.
3. Faça um commit pequeno por passo concluído (veja a Parte [16](parte-16.md)).

### Checkpoint
```bash
git status        # deve mostrar só arquivos de estrutura, nada de dados
git add . && git commit -m "chore: estrutura inicial do projeto"
```

---
