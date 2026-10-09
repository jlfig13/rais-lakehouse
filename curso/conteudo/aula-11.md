# Aula 11 — Ingestão e camada bronze

Oct 9, 2026

Ao final desta aula o primeiro ano da RAIS está no lake: extraído da landing, lido com o separador e o encoding certos e gravado como tabela Delta na bronze, fiel à origem e reprocessável sem duplicar.

```yaml
aula: 11
titulo: "Ingestão e camada bronze"
origem: ["Guia Parte 8", "Guia Parte 9"]
depende_de: [9, 10]
entrega: ["src/ingest.py", "src/bronze.py", "notebooks/02_bronze.ipynb"]
checks: [a11_bronze_delta, a11_ano_carregado, a11_tudo_string, a11_arquivo_origem, a11_idempotente]
```


## 1. Objetivos e pré-requisitos

1. Separar aquisição (download), extração e carga, e tornar cada uma idempotente.
2. Ler o texto da RAIS com o separador, o encoding e as opções corretas.
3. Aplicar as regras da bronze: tudo string, nomes normalizados, partição por ano, rastreabilidade.
4. Usar `mergeSchema` para absorver mudanças de schema entre anos.
5. Validar contagem, tipos e idempotência.

**Pré-requisitos:** Aula 09 (`.7z` em `staging/landing/2022/`), Aula 10 (`utils`, `delta_io`).

## 2. Contextualização

A bronze é a **cópia fiel e eficiente** da origem (guia, Parte 9.1). Ela não interpreta nada; existe para que nunca mais seja preciso reler o `.txt` lento e pesado. Se um dia a regra da silver mudar, refaz-se a silver a partir da bronze, sem tocar na landing. Isso divide o custo: a parte mais cara (ler texto latin-1 com dezenas de milhões de linhas) acontece uma vez por ano de dado.

## 3. Fundamentação teórica

### 3.1 Ingestão (guia, Parte 8.1)

Ingerir é trazer o dado da fonte **sem alterá-lo**. Separe **baixar** de **extrair**: se um passo falhar, você refaz só ele. Torne cada passo **idempotente**: se o arquivo já existe, ele é pulado.

**Download atômico.** O download grava primeiro em `.part` e só renomeia no fim: um download interrompido nunca é confundido com um arquivo completo (guia, Parte 8.2).

### 3.2 As cinco regras da bronze (guia, Parte 9.1)

| Regra | Por quê |
| --- | --- |
| Tudo `string` | Mudanças de formato entre anos não quebram a carga; tipar é tarefa da silver |
| Nomes normalizados | Parquet e Delta não lidam bem com espaços e acentos em nomes de coluna |
| Particionada por `ano` com `replaceWhere` | Reprocessar 2022 não toca em 2021 |
| `mergeSchema=True` | Coluna nova num ano novo é **adicionada**; anos antigos ficam com NULL. Sem a opção, o Delta **recusa** a gravação |
| Rastreabilidade | Cada linha guarda o arquivo de origem |

### 3.3 Opções de leitura do CSV

| Opção | Valor | Efeito |
| --- | --- | --- |
| `header` | `True` | Primeira linha é cabeçalho |
| `sep` | `;` | Separador da RAIS |
| `encoding` | `ISO-8859-1` | latin-1; sem isso, acentos viram `�` |
| `inferSchema` | `False` | Tudo string, de propósito — e evita uma passada extra pelos dados para inferir tipos |
| caminho `raw/<ano>/*.txt` | glob | Lê todas as regiões do ano numa só leitura |

### 3.4 Coluna oculta `_metadata`

Fontes de arquivo no Spark expõem uma coluna oculta `_metadata` com informações do arquivo lido; `_metadata.file_name` é o nome. O guia a captura **antes** de renomear as colunas, para garantir que ela ainda seja resolvível.

## 4. Arquitetura e fluxo

```
 staging/landing/2022/*.7z ── extrair(2022) ──▶ staging/raw/2022/*.txt
                                                     │ spark.read.csv(sep=';', latin-1, sem inferência)
                                                     ▼
                         + arquivo_origem (_metadata.file_name)
                         + normalize_columns
                         + ano = 2022
                                                     │ gravar_ano(merge_schema=True)
                                                     ▼
                         s3a://rais/bronze/rais_vinculos/ano=2022/  (Delta)
                                                     │
                         --limpar-raw  ──▶  apaga staging/raw/2022 (landing permanece)
```

## 5. Tutorial

### Passo 1 — `src/ingest.py` (guia, Parte 8.2)

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

- **Para começar,** o guia recomenda baixar o `.7z` manualmente (Aula 09) e usar só o `extrair`. O `baixar` depende de um endereço de FTP que deve ser confirmado no site do MTE.
- `ftp.login()` sem argumentos faz login anônimo.
- O container precisa de acesso à internet para `baixar`; em ambiente sem saída, só o caminho manual funciona.

```bash
docker compose exec spark python -m src.ingest 2022
docker compose exec spark bash -c "ls -lh /staging/raw/2022/ && head -c 500 /staging/raw/2022/*.txt"
```

O `head` deve mostrar o cabeçalho separado por `;`. Acentos estranhos aqui são esperados: o encoding é tratado na leitura (guia, Parte 8).

### Passo 2 — `src/bronze.py` (guia, Parte 9.2)

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

- `spark: SparkSession | None = None`: a função aceita uma sessão existente (o pipeline passa a mesma para todas as etapas, Aula 14) ou cria uma.
- O `ano` é acrescentado após a normalização e é a única coluna `int` da bronze.

```bash
docker compose exec spark python -m src.bronze 2022
```

### Passo 3 — Explorar (guia, Parte 9.3), notebook `02_bronze.ipynb`

```python
from config.settings import BRONZE
from src.delta_io import ler
from src.utils import get_spark

spark = get_spark()
b = ler(spark, BRONZE)

b.printSchema()                                    # tudo string (exceto ano)
print(f"{b.count():,} vínculos")
b.select("municipio", "sexo_trabalhador", "vl_remun_media_nom").show(10)
```

### Passo 4 — Limpar a raw

Depois de validar a bronze, apague `staging/raw/2022/`: o `.7z` na landing continua como fonte (guia, Parte 9). O pipeline da Aula 14 faz isso com `--limpar-raw`.

## 6. Funcionamento e resultados esperados

| Etapa | Esperado |
| --- | --- |
| Extração | Um ou mais `.txt` em `/staging/raw/2022/` |
| Leitura | Colunas com nomes legíveis e acentos corretos após normalização |
| Gravação | `bronze/rais_vinculos/ano=2022/` com Parquet e `_delta_log/` no MinIO |
| Schema | Todas `string`, exceto `ano: integer` |
| Tamanho | Bronze bem menor que o `.txt` (compressão colunar) — meça no exercício 4 |
| Reprocessar | Contagem do ano igual antes e depois |

## 7. Exemplos práticos

**Exemplo 1 — Encoding errado, de propósito.** Leia o mesmo `.txt` com `encoding` `UTF-8` e compare o nome da coluna de município: aparece `Munic�pio` (guia, Apêndice A, item 10).

**Exemplo 2 — Linhas por região.** `b.groupBy("arquivo_origem").count().show(truncate=False)` mostra quantos vínculos vieram de cada `.txt` — útil para notar uma região faltando.

**Exemplo 3 — Colunas esperadas.** `set(colunas_esperadas) - set(b.columns)` com as colunas da Aula 09 revela diferenças de nome naquele ano antes de chegar à silver.

## 8. Armadilhas, diagnóstico e soluções

| Sintoma | Causa | Solução |
| --- | --- | --- |
| `FileNotFoundError: Nenhum .7z` | Arquivo fora de `landing/<ano>/` | Conferir caminho (Aula 09) |
| `Path does not exist: .../raw/2022/*.txt` | Extração não feita ou extensão diferente | Rodar `extrair`; conferir a extensão real dos arquivos |
| Acentos como `�` | Encoding errado | `ISO-8859-1` |
| Uma coluna só com tudo dentro | Separador errado | `sep=";"` |
| `ValueError: Colunas duplicadas após normalizar` | Cabeçalhos que colidem | Tratar antes de normalizar (Aula 10) |
| Erro de schema ao gravar ano novo | Faltou `merge_schema=True` | Usar como no guia |
| Contagem dobrou | Gravação fora de `gravar_ano` (`append`) | Restaurar versão (Aula 14) e usar `gravar_ano` |
| Disco cheio | `raw` não apagada | Apagar após validar |
| `OutOfMemoryError` na leitura | Recursos pequenos | Aula 15; processar uma região por vez |

## 9. Boas práticas

1. Download manual primeiro; automação depois de confirmar a URL (guia).
2. Etapas separadas e idempotentes (guia).
3. Bronze sem regra de negócio (guia).
4. Validar a bronze antes de apagar a raw.
5. Registrar a contagem de linhas por arquivo de origem a cada carga, para comparar entre anos.

## 10. Riscos

| Tipo | Risco | Mitigação |
| --- | --- | --- |
| Integridade | Download incompleto tratado como completo | `.part` + rename |
| Integridade | Duplicação por reprocessamento | `replaceWhere` via `gravar_ano` |
| Integridade | Perder a origem | Landing intocada; `arquivo_origem` |
| Custo | `.txt` ocupando dezenas de GB | `--limpar-raw` |
| Segurança | FTP sem criptografia | Dado público; conferir hash (Aula 09) |

## 11. Laboratório e validação na plataforma

**Contribuição ao projeto:** a bronze é a fonte da silver e o ponto de reprocessamento sem reler texto.

`labcheck/test_aula11.py` (somente leitura):

```python
"""Checks da Aula 11: bronze do ano carregada, fiel e idempotente."""
import pytest
from delta.tables import DeltaTable
from pyspark.sql import functions as F

from config.settings import BRONZE
from src.delta_io import ler


def test_a11_bronze_delta(spark):
    assert DeltaTable.isDeltaTable(spark, BRONZE), f"{BRONZE} não é Delta. Rode o passo 2."


def test_a11_ano_carregado(spark, ano):
    assert ler(spark, BRONZE).filter(F.col("ano") == ano).limit(1).count() == 1, f"Ano {ano} vazio na bronze."


def test_a11_tudo_string(spark):
    nao_string = [c for c, t in ler(spark, BRONZE).dtypes if c != "ano" and t != "string"]
    assert not nao_string, f"Colunas tipadas na bronze: {nao_string}. A bronze é toda string."


def test_a11_arquivo_origem(spark, ano):
    b = ler(spark, BRONZE).filter(F.col("ano") == ano)
    assert b.filter(F.col("arquivo_origem").isNull()).limit(1).count() == 0, "Linhas sem arquivo_origem."


def test_a11_idempotente(spark, ano):
    """Em todas as versões da tabela que contêm o ano, a contagem dele é a mesma."""
    versoes = [r["version"] for r in DeltaTable.forPath(spark, BRONZE).history().select("version").collect()]
    contagens = set()
    for v in versoes:
        n = (spark.read.format("delta").option("versionAsOf", v).load(BRONZE)
             .filter(F.col("ano") == ano).count())
        if n:
            contagens.add((v, n))
    if len(contagens) < 2:
        pytest.skip(f"Reprocesse {ano} uma vez (python -m src.bronze {ano}) para validar a idempotência.")
    assert len({n for _, n in contagens}) == 1, f"Contagem do ano mudou entre versões: {sorted(contagens)}"
```

- O último check usa *time travel* (Aula 14) para comparar versões **sem** reprocessar nada.
- Rode com `make check AULA=11 ANO=2022`.

**Checklist manual:** \[ \] vi o acento correto no `printSchema` · \[ \] reprocessei o ano uma vez · \[ \] apaguei a raw depois de validar.

## 12. Exercícios, revisão e desafios

**Exercícios (guia, Parte 9)**

1. Quantos vínculos e quantas colunas há?
2. Liste os valores distintos de `sexo_trabalhador` e `vinculo_ativo_31_12`.
3. Confira se as colunas da Aula 09 existem: `set(esperadas) - set(b.columns)`.
4. Compare o tamanho do `.txt` com o da bronze (`du -sh` na raw; `mc du` no lake, Aula 04). Qual é a taxa de compressão?
5. Rode a bronze de 2022 duas vezes e confirme que a contagem não dobrou.

**Revisão**

1. Por que separar `baixar` e `extrair`?
2. Por que `inferSchema=False`?
3. O que acontece ao gravar um ano com coluna nova sem `mergeSchema`?
4. Por que capturar `_metadata.file_name` antes de `normalize_columns`?

**Respostas sugeridas:** (1) refazer só o passo que falhou; (2) tudo string e uma passada a menos nos dados; (3) o Delta recusa (enforcement); (4) para ainda conseguir resolver a coluna oculta antes de renomear o DataFrame.

**Desafio:** faça o `extrair` pular arquivos já extraídos (idempotência também nesta etapa) e registre o tempo de cada etapa.

## 13. Referências cruzadas

| Tema | Onde |
| --- | --- |
| Landing, hash, nomes dos arquivos | Aula 09 |
| `normalize_columns`, `gravar_ano`, `mergeSchema` | Aula 10 |
| Tipagem a partir da bronze | Aula 12 |
| `--limpar-raw`, pipeline e time travel | Aula 14 |
| Memória e partições de leitura | Aula 15 |
| Armadilhas de encoding e disco | Apêndice A |
