# RAIS Lakehouse

Lakehouse **open source e on-premises** com os microdados de vínculos da RAIS (2019 em diante),
construído com **PySpark 3.5**, **Delta Lake 3.2** e **MinIO**, orquestrado por **Docker Compose**.
O repositório é também uma **plataforma de aprendizagem**: 16 aulas, laboratórios e checks
automáticos que validam o seu ambiente de verdade.

## Arquitetura

```
FTP do MTE ──► staging/landing (.7z) ──► staging/raw (.txt)      disco local (temporário)
                                              │
                                              ▼
                     s3a://rais/bronze ──► silver ──► gold          MinIO + Delta Lake
                     (tudo string)      (tipada)   (5 tabelas)
```

| Camada | Conteúdo | Regra principal |
| --- | --- | --- |
| landing / raw | `.7z` baixados e `.txt` extraídos | temporário, pode ser apagado |
| bronze | cópia fiel, todas as colunas `string` + `ano` + `arquivo_origem` | reprocessar um ano troca só aquele ano (`replaceWhere`) |
| silver | tipada e validada, um vínculo por linha | inválido vira `NULL`; nenhuma linha é descartada |
| gold | `gold_emprego_uf_ano`, `gold_gap_sexo_uf_ano`, `gold_top_cnae_uf_ano`, `gold_escolaridade_ano`, `gold_desligamento_uf_ano` | recalculada inteira; unidade é "vínculos" |

Serviços (`docker-compose.yml`): `minio` (armazenamento), `minio-init` (cria bucket, política
e usuário da aplicação e termina), `spark` (PySpark + JupyterLab) e `curso` (site das aulas).
Todas as portas ficam presas em `127.0.0.1`.

```
config/         caminhos e anos (settings.py)
src/            pipeline: ingest, bronze, silver, gold, checks, run_pipeline
tests/          testes de unidade + integração sobre amostra sintética (rodam no CI)
labs/           exercícios das Aulas 07 e 08 + gerador da amostra sintética
labcheck/       checks das aulas (labcheck/host/ = Aulas 02–05, rodam no host)
curso/          site do curso (Zensical): aulas.yml + páginas geradas
docs/           decisões (ADRs), dicionário de dados, benchmark
progress/       histórico local dos checks (não versionado)
```

## Como rodar

### 1. Pré-requisitos

- **Windows:** WSL2 com Ubuntu + Docker Desktop com integração WSL ativada. Clone e rode tudo
  **dentro do WSL** (ex.: `~/projetos`), não em `C:\` — o acesso a `/mnt/c` é lento e quebra
  permissões. No VS Code, use a extensão *WSL* ("Reopen in WSL").
- **Linux/macOS:** Docker Engine + plugin Compose, `make` e `git`.
- Recursos sugeridos: 8 GB de RAM livres para o container e ~30 GB de disco por ano processado.

### 2. Configurar

```bash
git clone <url-do-seu-repositorio> rais-lakehouse && cd rais-lakehouse
cp .env.example .env
```

Edite o `.env`: defina **imagem e tag fixas** do MinIO e do `mc` (confira no repositório
oficial do MinIO), troque todas as senhas e o token do Jupyter, e ajuste `HOST_UID` com o
resultado de `id -u`. O `.env` nunca vai para o Git.

### 3. Subir e testar

```bash
make up          # constrói a imagem e sobe minio, minio-init e spark
make smoke       # Spark + Delta + MinIO: grava e lê 1000 linhas
make test        # testes de unidade
```

- JupyterLab: http://localhost:8888 (token do `.env`)
- Console do MinIO: http://localhost:9001
- Spark UI (com um job rodando): http://localhost:4040

### 4. Rodar o pipeline

```bash
make pipeline ANOS="2022"                        # extrair → bronze → silver → gold
make pipeline ANOS="2021 2022" ETAPAS="silver gold"
```

O download (`src/ingest.py`) usa o FTP público do MTE. Se o seu ambiente não alcança o FTP,
baixe o `.7z` manualmente para `staging/landing/<ano>/` e rode a partir de `extrair`.

### 5. Estudar com a plataforma

```bash
make curso                       # site das aulas em http://localhost:8000
make check-host AULA=02          # Aulas 01–05 (host; exige .venv-host com pytest)
make check AULA=11 ANO=2022      # Aulas 06–16 (container spark)
make progresso                   # atualiza curso/docs/progresso.md a partir do histórico
```

Para os checks do host: `python3 -m venv .venv-host && .venv-host/bin/pip install pytest`.
Cada check grava uma linha em `progress/historico.jsonl` com `"origem": "execucao_real"`;
a página de progresso só mostra o que foi executado na sua máquina.

**Sem a RAIS real:** `python -m labs.amostra.gerar_amostra --saida staging/raw/2022` gera uma
amostra **sintética** no formato dos microdados (latin-1, `;`, vírgula decimal). Os números
calculados sobre ela não são resultados da RAIS.

## Decisões técnicas

Registradas como ADRs em [`docs/decisoes.md`](docs/decisoes.md): Spark `local` num container,
Docker Compose, MinIO via S3A, Delta Lake (e não Iceberg), staging em disco local e JARs
embutidos na imagem. Os contratos de camada estão no mesmo arquivo. Outras escolhas:

- **Idempotência:** bronze e silver gravam com `replaceWhere` por `ano`; a gold é recriada.
- **Schema:** `mergeSchema` só na bronze; a silver tem tipos fixos (schema enforcement).
- **Dinheiro em `decimal(18,2)`**, nunca `double`; códigos com zero à esquerda ficam `string`.
- **Funções puras** (`preparar_bronze`, `transformar_silver`, `tabelas_gold`, `validar_silver`)
  separadas da escrita, para testar a lógica sem MinIO nem Delta.
- **Menor privilégio:** o Spark usa o usuário `rais-app`, restrito ao bucket `rais`.

## Limitações

- **Versões:** PySpark 3.5.3, delta-spark 3.2.0, hadoop-aws 3.3.4 e aws-java-sdk-bundle
  1.12.262 são fixadas juntas; trocar uma exige conferir a compatibilidade das outras.
- **Escala:** uma máquina. Anos inteiros da RAIS têm dezenas de milhões de linhas; ajuste
  threads, memória e partições (Aula 15) antes de processar vários anos.
- **Layout da RAIS muda entre anos.** Os nomes de coluna usados em `src/silver.py` devem ser
  conferidos no dicionário oficial de cada ano (`docs/dicionario.md`).
- **Grão é o vínculo, não a pessoa.** Uma pessoa com dois empregos aparece duas vezes.
- **Site do curso:** Zensical é um projeto novo (0.0.x); a versão está fixada.
- **Conteúdo completo das aulas** está nos documentos linkados em cada página do site; o
  repositório guarda metadados, laboratórios e checks.

### Relatório de validação desta versão

| Item | Status | Como |
| --- | --- | --- |
| Lint (`ruff check .`) | ✅ validado | executado |
| Testes de unidade e integração bronze→silver→gold sobre amostra sintética | ✅ validado | `pytest -q` (sem Delta/MinIO) |
| Checks das Aulas 07 e 08 | ✅ validado | com soluções temporárias, `LABCHECK_SEM_LAKE=1` |
| Checks das Aulas 01 e 09 (dicionário) | ✅ validado | executado |
| Registro de progresso e `gerar_progresso.py` | ✅ validado | executado |
| `docker compose config` | ✅ validado | com um `.env` de teste |
| Build do site (`zensical build`) | ✅ validado | executado |
| Build da imagem, MinIO, Delta/S3A, `make smoke`, pipeline com RAIS real | ⚠️ **não validado** | o ambiente de geração não tinha acesso ao Docker Hub nem ao Maven Central |
| Checks das Aulas 02–06 e 10–16 | ⚠️ **não validado** | dependem do ambiente acima |

Rode `make up && make smoke && make test` na sua máquina para fechar esses itens.

## Licença

[MIT](LICENSE)
