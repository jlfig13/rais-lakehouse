<!-- Página GERADA de docs/guia/rais-lakehouse-guia.md -->

# Parte [10](parte-10.md) — Silver

## 10.1 Conceito { #parte-10-1 }

A silver é onde o dado fica **confiável**:
1. Seleciona só as colunas úteis.
2. Converte os tipos: decimal com vírgula vira `decimal`, códigos pequenos viram `int`.
3. Valida formatos: município com 6 dígitos, CNAE com 5, idade plausível.
4. Transforma valores inválidos ou "ignorados" em `NULL`.
5. Deriva campos: UF a partir do município, divisão CNAE a partir da classe.
6. **Mantém uma linha por vínculo**: a silver **não filtra linhas**, só limpa valores. Por isso a contagem da silver deve bater com a da bronze.

**Códigos com zero à esquerda** (CBO, CNAE, município) ficam como **string**. Converter `"012345"` para número vira `12345` e destrói a informação. Já códigos pequenos de categoria (sexo, escolaridade) viram `int`, o que unifica `"01"` e `"1"`.

## 10.2 `src/silver.py` { #parte-10-2 }

```python
"""Silver: tipagem, validação e padronização da RAIS."""
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

from config.settings import BRONZE, SILVER
from src.delta_io import gravar_ano, ler
from src.utils import col_or_null, get_spark, to_decimal, to_int

# Sem estas colunas não faz sentido continuar
OBRIGATORIAS = ["municipio", "vinculo_ativo_31_12", "vl_remun_dezembro_nom"]


def construir_silver(ano: int, spark: SparkSession | None = None) -> None:
    spark = spark or get_spark("rais-silver")
    b = ler(spark, BRONZE).filter(F.col("ano") == ano)

    faltando = [c for c in OBRIGATORIAS if c not in b.columns]
    if faltando:
        raise ValueError(f"Ano {ano}: colunas obrigatórias ausentes: {faltando}")

    # 1) Seleção + tipagem
    s = b.select(
        F.col("ano"),
        col_or_null(b, "municipio").alias("cod_municipio"),
        col_or_null(b, "cnae_2_0_classe").alias("cnae_classe"),
        col_or_null(b, "cbo_ocupacao_2002").alias("cbo"),
        col_or_null(b, "natureza_juridica").alias("natureza_juridica"),
        to_int(b, "sexo_trabalhador").alias("sexo"),
        to_int(b, "escolaridade_apos_2005").alias("escolaridade"),
        to_int(b, "raca_cor").alias("raca_cor"),
        to_int(b, "idade").alias("idade"),
        to_int(b, "tamanho_estabelecimento").alias("tamanho_estab"),
        to_int(b, "mes_desligamento").alias("mes_desligamento"),
        to_int(b, "motivo_desligamento").alias("motivo_desligamento"),
        to_decimal(b, "tempo_emprego", 10, 1).alias("tempo_emprego_meses"),
        (F.trim(F.col("vinculo_ativo_31_12")) == "1").alias("vinculo_ativo"),
        to_decimal(b, "vl_remun_dezembro_nom").alias("remun_dezembro_nom"),
        to_decimal(b, "vl_remun_media_nom").alias("remun_media_nom"),
        to_decimal(b, "vl_remun_dezembro_sm").alias("remun_dezembro_sm"),
        to_decimal(b, "vl_remun_media_sm").alias("remun_media_sm"),
    )

    # 2) Validação: valor fora do padrão vira NULL
    s = (
        s
        .withColumn("cod_municipio",
                    F.when(F.col("cod_municipio").rlike(r"^\d{6}$"), F.col("cod_municipio")))
        .withColumn("cnae_classe",
                    F.when(F.col("cnae_classe").rlike(r"^\d{5}$"), F.col("cnae_classe")))
        .withColumn("idade", F.when(F.col("idade").between(14, 100), F.col("idade")))
        # 0 = não desligado -> NULL (CONFIRME no dicionário)
        .withColumn("mes_desligamento",
                    F.when(F.col("mes_desligamento").between(1, 12), F.col("mes_desligamento")))
    )

    # 3) Campos derivados (substring de NULL é NULL)
    s = (
        s
        .withColumn("cod_uf", F.substring("cod_municipio", 1, 2))
        .withColumn("cnae_divisao", F.substring("cnae_classe", 1, 2))
        .withColumn("desligado_no_ano", F.col("mes_desligamento").isNotNull())
    )

    gravar_ano(spark, s, SILVER, ano)
    print(f"[silver] {ano} gravado em {SILVER}")


if __name__ == "__main__":
    import sys

    construir_silver(int(sys.argv[1]))
```
```bash
docker compose exec spark python -m src.silver 2022
```

## Exercícios (notebook `03_silver.ipynb`)
1. `printSchema()`: os tipos estão como planejado?
2. Conte os `NULL` por coluna:
   ```python
   s.select([F.sum(F.col(c).isNull().cast("int")).alias(c) for c in s.columns]).show(vertical=True)
   ```
3. Distribuição de `idade` e `remun_dezembro_sm` (`s.describe(...)`). Há valores absurdos?
4. Qual a % de vínculos com `vinculo_ativo = true`?
5. `remun_dezembro_nom = 0` significa o quê no dicionário? Decida se vira `NULL` e registre em `docs/dicionario.md`.

### Checkpoint
- Os tipos estão corretos (`decimal`, `int`, `boolean`, `string`).
- **Contagem da silver = contagem da bronze** do mesmo ano.
- Commit: `feat: camada silver`.

---
