# Decisões de arquitetura — RAIS Lakehouse

Origem: Guia Parte 1.3 / Aula 01. Formato ADR: uma decisão nunca é apagada; se mudar,
o ADR antigo passa a "substituída por ADR-XXX".

## ADR-001 — Spark em modo `local` num container

- **Status:** aceita
- **Data:** 2026-10-09
- **Contexto:** projeto educacional, uma única máquina, só software open source on-premises.
- **Decisão:** rodar o Spark com `master = local[N]` dentro do container `spark`.
- **Alternativas consideradas:** cluster Spark standalone — mais peças para operar sem ganho
  numa máquina só.
- **Consequências:** o código é o mesmo que rodaria num cluster (só mudam `master` e recursos);
  o limite de escala é a máquina (Aula 15).

## ADR-002 — Docker Compose

- **Status:** aceita
- **Data:** 2026-10-09
- **Contexto:** qualquer pessoa precisa subir o mesmo ambiente com um comando.
- **Decisão:** orquestrar MinIO, init e Spark com Docker Compose.
- **Alternativas consideradas:** instalar tudo no host — não reprodutível.
- **Consequências:** exige Docker (no Windows, via WSL2); versões fixadas em `.env` e Dockerfile.

## ADR-003 — MinIO (API S3) como armazenamento do lake

- **Status:** aceita
- **Data:** 2026-10-09
- **Contexto:** armazenamento de objetos open source e on-premises.
- **Decisão:** MinIO, acessado pelo Spark via S3A.
- **Alternativas consideradas:** HDFS (pesado para uma máquina); disco local (não ensina S3).
- **Consequências:** o código só fala S3 e migra para qualquer storage compatível.

## ADR-004 — Delta Lake como formato de tabela

- **Status:** aceita
- **Data:** 2026-10-09
- **Contexto:** precisamos de ACID, versões e controle de schema sobre Parquet
  no MinIO, usando só PySpark e software open source.
- **Decisão:** usar Delta Lake (delta-spark) em bronze, silver e gold.
- **Alternativas consideradas:** Apache Iceberg — mesmos recursos centrais, mas
  exige configurar um catálogo desde o início; vantagem em multi-engine que
  ainda não precisamos.
- **Consequências:** setup simples (JARs + 2 configs); leitura por outras engines
  depende do suporte delas ao Delta; migrar para Iceberg exigirá trocar a camada
  de I/O (centralizada em src/delta_io.py).

## ADR-005 — Staging (landing/raw) em disco local

- **Status:** aceita
- **Data:** 2026-10-09
- **Contexto:** `.7z` e `.txt` baixados são temporários.
- **Decisão:** manter landing e raw em disco local montado em `/staging`.
- **Alternativas consideradas:** guardar no MinIO — versionamento e custo sem necessidade.
- **Consequências:** o staging não é o dado oficial; pode ser apagado (`--limpar-raw`).

## ADR-006 — JARs embutidos na imagem

- **Status:** aceita
- **Data:** 2026-10-09
- **Contexto:** baixar dependências do Maven em toda execução é lento e frágil.
- **Decisão:** copiar os JARs de Delta e S3A para a imagem no build.
- **Alternativas consideradas:** `spark.jars.packages` em tempo de execução.
- **Consequências:** funciona sem internet após o build e é reprodutível; atualizar versões
  exige rebuild.

<!-- Aula 15: registre aqui o ADR-007 com a configuração de threads, memória e
     partições escolhida, e o link para docs/benchmark.csv. -->

## ADR-008 — Vários layouts de arquivo da RAIS no mesmo pipeline

- **Status:** aceita
- **Data:** 2026-10-13
- **Contexto:** nos arquivos reais do Nordeste, 2021 e 2022 vêm em `.txt` separado por `;`,
  com vírgula decimal e zero para remuneração ausente; 2023 vem em `.COMT` separado por `,`,
  com campos entre aspas, outros nomes de coluna, ponto decimal e campo vazio para remuneração
  ausente. O pipeline original não encontrava o arquivo de 2023 e, se encontrasse, leria os
  salários cem vezes maiores.
- **Decisão:** a bronze lê todos os arquivos da pasta do ano, detecta o separador pelo
  cabeçalho e renomeia as colunas para os nomes canônicos (`DE_PARA` em `src/bronze.py`);
  `to_decimal` decide o formato pela presença de vírgula; a silver trata remuneração vazia
  como 0 (`remuneracao` em `src/silver.py`).
- **Alternativas consideradas:** um pipeline por layout (duplica código); manter os nomes de
  cada ano na bronze e unificar só na silver (a bronze ficaria com colunas diferentes por ano,
  e o `mergeSchema` encheria a tabela de colunas quase vazias).
- **Consequências:** um ano com layout novo exige só acrescentar entradas ao `DE_PARA`; a
  bronze deixa de ser cópia literal dos nomes de origem (os valores continuam fiéis). Validado
  com 20 mil vínculos reais de 2021 e 2023: `remun_dezembro_nom / remun_dezembro_sm` deu 1.104
  e 1.324, os salários mínimos de cada ano. Um valor `1.234` sem vírgula seria lido como
  1,234; a RAIS não usa separador de milhar sem decimais, mas confira ao adotar um ano novo.

## Contratos de camada

### bronze — rais_vinculos
- Grão: uma linha por linha do arquivo de origem
- Tipos: todas as colunas string, exceto `ano` (int)
- Colunas: nomes normalizados (minúsculas, sem acento, `_`)
- Partição: `ano`
- Rastreabilidade: coluna `arquivo_origem`
- Garantia: reprocessar um ano substitui só aquele ano

### silver — rais_vinculos
- Grão: um vínculo por linha (NÃO é uma pessoa)
- Contagem: igual à bronze do mesmo ano
- Tipos: decimal para valores, int para códigos pequenos,
  string para códigos com zero à esquerda (CBO, CNAE, município)
- Inválido vira NULL; nenhuma linha é descartada

### gold — gold_*
- Grão: definido pela pergunta de cada tabela (ex.: ano × UF)
- Unidade: "vínculos", nunca "trabalhadores"
- Séries históricas usam colunas *_sm (salário mínimo)
- Recalculada inteira a cada execução
