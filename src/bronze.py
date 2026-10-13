"""Bronze: CSV/TXT da RAIS -> Delta, fiel à origem.

Origem: Guia Parte 9.2 / Aula 11.
[Complemento] Leitura e preparação separadas em funções sem E/S de tabela
(`ler_texto`, `preparar_bronze`) para poderem ser testadas sem MinIO/Delta.

O layout dos arquivos muda entre anos (Aula 09, armadilha 11). Conferido nos arquivos reais:
até 2022, `.txt` separado por ';'; em 2023, `.COMT` separado por ',' com campos entre aspas e
outros nomes de coluna. Por isso a bronze lê todos os arquivos da pasta do ano, detecta o
separador pelo cabeçalho de cada um e renomeia as colunas para os nomes canônicos (DE_PARA).
"""
from pathlib import Path

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from config.settings import BRONZE, RAW
from src.delta_io import gravar_ano
from src.utils import get_spark, normalize_columns

# Nomes do layout de 2023 (já normalizados) -> nomes canônicos usados pelo projeto
DE_PARA = {
    "municipio_codigo": "municipio",
    "cnae_2_0_classe_codigo": "cnae_2_0_classe",
    "cbo_2002_ocupacao_codigo": "cbo_ocupacao_2002",
    "ind_vinculo_ativo_31_12_codigo": "vinculo_ativo_31_12",
    "sexo_codigo": "sexo_trabalhador",
    "escolaridade_apos_2005_codigo": "escolaridade_apos_2005",
    "raca_cor_codigo": "raca_cor",
    "mes_desligamento_codigo": "mes_desligamento",
    "motivo_desligamento_codigo": "motivo_desligamento",
    "tamanho_estabelecimento_codigo": "tamanho_estabelecimento",
    "natureza_juridica_codigo": "natureza_juridica",
    "vl_rem_dezembro_nom": "vl_remun_dezembro_nom",
    "vl_rem_media_nom": "vl_remun_media_nom",
    "vl_rem_dezembro_sm": "vl_remun_dezembro_sm",
    "vl_rem_media_sm": "vl_remun_media_sm",
}


def ler_texto(spark: SparkSession, caminho: str | list[str], sep: str = ";") -> DataFrame:
    """Lê arquivos da RAIS: latin-1, tudo string. Campos entre aspas são aceitos."""
    return (
        spark.read
        .option("header", True)
        .option("sep", sep)
        .option("encoding", "ISO-8859-1")
        .option("inferSchema", False)          # tudo string, de propósito
        .csv(caminho)
    )


def canonizar(df: DataFrame) -> DataFrame:
    """Renomeia colunas de layouts novos para os nomes canônicos (sem sobrescrever existentes)."""
    for antigo, canonico in DE_PARA.items():
        if antigo in df.columns and canonico not in df.columns:
            df = df.withColumnRenamed(antigo, canonico)
    return df


def preparar_bronze(df: DataFrame, ano: int) -> DataFrame:
    """Rastreabilidade + nomes normalizados e canônicos + coluna ano.

    `df` deve vir direto de ler_texto (a coluna oculta _metadata só existe na leitura).
    """
    if "arquivo_origem" not in df.columns:
        df = df.withColumn("arquivo_origem", F.col("_metadata.file_name"))
    return canonizar(normalize_columns(df)).withColumn("ano", F.lit(ano).cast("int"))


def separador(arquivo: Path) -> str:
    """';' ou ',' conforme o que mais aparece no cabeçalho do arquivo."""
    with open(arquivo, encoding="latin-1") as f:
        cabecalho = f.readline()
    return ";" if cabecalho.count(";") >= cabecalho.count(",") else ","


def ler_ano(spark: SparkSession, pasta: Path, ano: int) -> DataFrame:
    """Todos os arquivos da pasta (qualquer extensão), agrupados por separador e unidos."""
    grupos: dict[str, list[str]] = {}
    for arq in sorted(p for p in pasta.iterdir() if p.is_file() and not p.name.startswith(".")):
        grupos.setdefault(separador(arq), []).append(str(arq))
    if not grupos:
        raise FileNotFoundError(f"Nenhum arquivo em {pasta}")
    partes = [preparar_bronze(ler_texto(spark, arqs, sep), ano) for sep, arqs in grupos.items()]
    df = partes[0]
    for parte in partes[1:]:
        df = df.unionByName(parte, allowMissingColumns=True)
    return df


def construir_bronze(ano: int, spark: SparkSession | None = None) -> None:
    spark = spark or get_spark("rais-bronze")
    df = ler_ano(spark, RAW / str(ano), ano)
    gravar_ano(spark, df, BRONZE, ano, merge_schema=True)
    print(f"[bronze] {ano} gravado em {BRONZE}")


if __name__ == "__main__":
    import sys

    construir_bronze(int(sys.argv[1]))
