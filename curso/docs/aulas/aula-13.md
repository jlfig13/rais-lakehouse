---
aula: 13
titulo: "Camada gold: perguntas de negócio e funções puras"
origem: ['Guia Parte 11', 'Guia Parte 15.3 (test_gap_sexo)']
depende_de: [12]
checks: ['a13_cinco_tabelas', 'a13_total_bate_silver', 'a13_uf_preenchida', 'a13_top10', 'a13_teste_gap_sexo']
---

# Aula 13 — Camada gold: perguntas de negócio e funções puras

<!-- Página GERADA por scripts/gerar_curso.py. Edite aulas.yml e curso/conteudo/. -->

<div class="rl-aula" data-aula="13" data-onde="container" data-lab="src/gold.py"></div>

| | |
| --- | --- |
| Origem no guia | Guia Parte [11](../guia/parte-11.md), Guia Parte [15.3](../guia/parte-15.md#parte-15-3) (test_gap_sexo) |
| Depende de | [Aula 12](aula-12.md) |
| Entregas | `src/gold.py`, `tests/test_utils.py (test_gap_sexo)`, `notebooks/04_gold.ipynb` |
| Onde os checks rodam | Container spark |

A gold é o que alguém de fora do time de dados consome. Ao final desta aula existem cinco tabelas, cada uma respondendo uma pergunta, calculadas por funções testáveis e prontas para gráfico, BI ou relatório.

## 1. Objetivos e pré-requisitos

1. Desenhar tabelas a partir de perguntas, com grão explícito.
2. Escolher métricas corretas: estoque × fluxo, nominal × salário mínimo, média × mediana.
3. Escrever cada tabela como função pura e testá-la sem MinIO.
4. Usar broadcast nas dimensões e window para rankings.
5. Consumir a gold em pandas e exportar CSV.

**Pré-requisitos:** Aula 12 (silver), Aula 08 (window e broadcast), Aula 10 (dimensões).

## 2. Contextualização

A gold nasce de **perguntas de negócio** (guia, Parte [11.1](../guia/parte-11.md#parte-11-1)). Cada tabela responde uma pergunta específica e é pequena o bastante para ir direto a um gráfico. Uma "gold de tudo" (a silver agregada por todas as dimensões) parece flexível, mas joga de volta para o consumidor as decisões difíceis — qual coluna de remuneração, só ativos ou não — e cada consumidor decide diferente.

## 3. Fundamentação teórica (guia, Parte [11.1](../guia/parte-11.md#parte-11-1))

### 3.1 Regras de ouro

- **R$ nominal não é comparável entre anos.** Para série histórica, use as colunas em salários mínimos (`*_sm`).
- A unidade é **vínculo**, não pessoa: escreva "vínculos" nos rótulos, nunca "trabalhadores".
- Indicadores de **estoque** (quantos empregos existem) usam **vínculos ativos em 31/12**.

### 3.2 As cinco tabelas

| Tabela | Pergunta | Grão | Base |
| --- | --- | --- | --- |
| `gold_emprego_uf_ano` | Quantos vínculos ativos e qual a remuneração por UF e ano? | ano × UF | Ativos |
| `gold_gap_sexo_uf_ano` | Quanto a remuneração média das mulheres representa da dos homens? | ano × UF | Ativos |
| `gold_top_cnae_uf_ano` | Quais as 10 divisões de atividade com maior massa salarial por UF? | ano × UF × divisão (≤ 10) | Ativos |
| `gold_escolaridade_ano` | Como a remuneração varia com a escolaridade? | ano × escolaridade | Ativos |
| `gold_desligamento_uf_ano` | Qual a proporção de vínculos desligados no ano? | ano × UF | **Todos** os vínculos do ano (fluxo) |

### 3.3 Média, mediana e massa

Remuneração tem distribuição assimétrica: poucos salários muito altos puxam a média para cima. Por isso `gold_emprego_uf_ano` traz média e mediana (`percentile_approx`). **Massa salarial** é a soma das remunerações — mede o tamanho econômico, não o salário típico.

### 3.4 Funções puras

Cada tabela é uma **função pura**: recebe DataFrames e devolve DataFrame, sem ler nem gravar nada. Isso torna o código testável: você chama `gap_sexo(df_de_teste, dim)` num teste, sem MinIO (guia, Parte [11.2](../guia/parte-11.md#parte-11-2)).

### 3.5 Recalcular inteira

A gold é recriada por completo a cada execução (`gravar_tabela` com `overwriteSchema`). Como as tabelas são pequenas, isso é barato e elimina toda uma classe de erro de atualização incremental (exercício 1 da Aula 01).

## 4. Arquitetura e fluxo

```
 silver (todos os anos)
   ├─ filter(vinculo_ativo) = ativos ─┬─ emprego_uf(ativos, dim_uf)        → gold_emprego_uf_ano
   │                                  ├─ gap_sexo(ativos, dim_uf)          → gold_gap_sexo_uf_ano
   │                                  ├─ top_cnae(ativos, dim_uf, n=10)    → gold_top_cnae_uf_ano
   │                                  └─ escolaridade(ativos, dim_escol.)  → gold_escolaridade_ano
   └─ (todos) ──────────────────────────── desligamento(silver, dim_uf)     → gold_desligamento_uf_ano
                         dimensões sempre com F.broadcast; cada tabela: coalesce(4) + gravar_tabela
```

## 5. Tutorial

### Passo 1 — `src/gold.py` (guia, Parte [11.2](../guia/parte-11.md#parte-11-2))

```python
"""Gold: tabelas analíticas prontas para consumo."""
from pyspark.sql import DataFrame, SparkSession, Window
from pyspark.sql import functions as F

from config.settings import GOLD, SILVER
from src.delta_io import gravar_tabela, ler
from src.dims import dim_escolaridade, dim_sexo, dim_uf
from src.utils import get_spark


def emprego_uf(ativos: DataFrame, uf: DataFrame) -> DataFrame:
    return (
        ativos.groupBy("ano", "cod_uf")
        .agg(
            F.count("*").alias("qtd_vinculos"),
            F.sum("remun_dezembro_nom").alias("massa_salarial_dez_nom"),
            F.round(F.avg("remun_dezembro_nom"), 2).alias("remun_media_dez_nom"),
            F.round(F.avg("remun_dezembro_sm"), 2).alias("remun_media_dez_sm"),
            F.percentile_approx("remun_dezembro_sm", 0.5).alias("remun_mediana_dez_sm"),
        )
        .join(uf, "cod_uf", "left")
    )


def gap_sexo(ativos: DataFrame, uf: DataFrame) -> DataFrame:
    return (
        ativos.groupBy("ano", "cod_uf")
        .agg(
            F.avg(F.when(F.col("sexo") == 2, F.col("remun_dezembro_sm"))).alias("rem_mulher_sm"),
            F.avg(F.when(F.col("sexo") == 1, F.col("remun_dezembro_sm"))).alias("rem_homem_sm"),
        )
        .withColumn("razao_mulher_homem",
                    F.round(F.col("rem_mulher_sm") / F.col("rem_homem_sm"), 3))
        .join(uf, "cod_uf", "left")
    )


def top_cnae(ativos: DataFrame, uf: DataFrame, n: int = 10) -> DataFrame:
    por_cnae = (
        ativos.filter(F.col("cnae_divisao").isNotNull())
        .groupBy("ano", "cod_uf", "cnae_divisao")
        .agg(
            F.count("*").alias("qtd_vinculos"),
            F.sum("remun_dezembro_nom").alias("massa_salarial_dez_nom"),
        )
    )
    w = Window.partitionBy("ano", "cod_uf").orderBy(F.col("massa_salarial_dez_nom").desc())
    return (
        por_cnae.withColumn("posicao", F.row_number().over(w))
        .filter(F.col("posicao") <= n)
        .join(uf, "cod_uf", "left")
    )


def escolaridade(ativos: DataFrame, esc: DataFrame) -> DataFrame:
    return (
        ativos.groupBy("ano", "escolaridade")
        .agg(
            F.count("*").alias("qtd_vinculos"),
            F.round(F.avg("remun_dezembro_sm"), 2).alias("remun_media_dez_sm"),
        )
        .join(esc, "escolaridade", "left")
    )


def desligamento(silver: DataFrame, uf: DataFrame) -> DataFrame:
    return (
        silver.groupBy("ano", "cod_uf")
        .agg(
            F.count("*").alias("qtd_vinculos_no_ano"),
            F.sum(F.col("desligado_no_ano").cast("int")).alias("qtd_desligados"),
        )
        .withColumn("taxa_desligamento",
                    F.round(F.col("qtd_desligados") / F.col("qtd_vinculos_no_ano"), 4))
        .join(uf, "cod_uf", "left")
    )


def construir_gold(spark: SparkSession | None = None) -> None:
    spark = spark or get_spark("rais-gold")

    silver = ler(spark, SILVER)
    ativos = silver.filter(F.col("vinculo_ativo"))
    uf = F.broadcast(dim_uf(spark))
    esc = F.broadcast(dim_escolaridade(spark))

    tabelas = {
        "gold_emprego_uf_ano": emprego_uf(ativos, uf),
        "gold_gap_sexo_uf_ano": gap_sexo(ativos, uf),
        "gold_top_cnae_uf_ano": top_cnae(ativos, uf),
        "gold_escolaridade_ano": escolaridade(ativos, esc),
        "gold_desligamento_uf_ano": desligamento(silver, uf),
    }
    for nome, df in tabelas.items():
        gravar_tabela(df.coalesce(4), f"{GOLD}/{nome}")   # poucos arquivos: tabela pequena
        print(f"[gold] {nome}")

    _ = dim_sexo  # disponível para enriquecer novas tabelas (exercício)


if __name__ == "__main__":
    construir_gold()
```

**Leitura guiada.**

| Trecho | Explicação |
| --- | --- |
| `F.avg(F.when(sexo == 2, valor))` | `when` sem `otherwise` gera NULL para os outros sexos; `avg` ignora NULL — resultado: média só das mulheres |
| `razao_mulher_homem` | 0,75 significa que a média feminina é 75% da masculina |
| `F.sum(desligado_no_ano.cast("int"))` | `true` vira 1, `false` vira 0: soma = quantidade |
| `cnae_divisao.isNotNull()` | CNAE inválido (NULL na silver) não entra no ranking |
| `.join(uf, "cod_uf", "left")` | Mantém linhas sem UF conhecida (com `uf` NULL) para que o problema apareça no check |
| `coalesce(4)` | Poucos arquivos por tabela pequena (Aula 08) |
| `_ = dim_sexo` | O guia deixa a dimensão pronta para exercícios |

### Passo 2 — Teste de unidade da gold (guia, Parte [15.3](../guia/parte-15.md#parte-15-3))

Acrescente a `tests/test_utils.py`:

```python
from src.dims import dim_uf
from src.gold import gap_sexo


def test_gap_sexo(spark):
    ativos = spark.createDataFrame(
        [(2022, "26", 1, Decimal("2.00")), (2022, "26", 2, Decimal("1.50"))],
        "ano int, cod_uf string, sexo int, remun_dezembro_sm decimal(18,2)",
    )
    linha = gap_sexo(ativos, dim_uf(spark)).first()
    assert linha["uf"] == "PE"
    assert float(linha["razao_mulher_homem"]) == 0.75
```

Este teste roda sem MinIO e sem RAIS — é o ganho das funções puras.

### Passo 3 — Rodar e consultar (guia, Parte [11.3](../guia/parte-11.md#parte-11-3))

```bash
docker compose exec spark python -m src.gold
```

Notebook `04_gold.ipynb`:

```python
from pyspark.sql import functions as F
from config.settings import GOLD
from src.delta_io import ler
from src.utils import get_spark

spark = get_spark()
g = ler(spark, f"{GOLD}/gold_emprego_uf_ano")
g.orderBy(F.col("qtd_vinculos").desc()).show(10)

# Gold é pequena: pode ir para o pandas e virar gráfico
pdf = g.filter("uf = 'PE'").orderBy("ano").toPandas()
pdf.plot(x="ano", y="remun_media_dez_sm", marker="o")
```

Use `toPandas()` **só** em tabelas gold; em silver ou bronze a memória estoura. Com um só ano carregado, o gráfico tem um ponto; ele ganha sentido na Aula 14.

## 6. Funcionamento e resultados esperados

| Verificação | Esperado |
| --- | --- |
| Tabelas | 5 pastas em `s3a://rais/gold/` |
| Soma de `qtd_vinculos` em `gold_emprego_uf_ano` | = `silver.filter("vinculo_ativo").count()` |
| `uf` nula | Nenhuma (se houver, há código de município fora da dimensão) |
| `posicao` em top CNAE | 1 a 10 |
| `razao_mulher_homem` | Entre 0 e algo próximo de 1 na maioria das UFs (confira no seu dado) |

## 7. Exemplos práticos

**Exemplo 1 — Uma pergunta nova vira uma função nova.** "Remuneração por porte" → `def porte(ativos): return ativos.groupBy("ano", "tamanho_estab").agg(...)` + uma entrada no dicionário `tabelas` + um teste.

**Exemplo 2 — Exportar para Excel ou Power BI (guia, exercício 5).**

```python
g.coalesce(1).write.mode("overwrite").option("header", True).csv("/staging/export/emprego")
```

O CSV fica em `staging/export/emprego/` no host (bind mount) — um arquivo `part-*.csv`.

**Exemplo 3 — Investigar UF nula.** `left_anti` da silver com `dim_uf` (Aula 08, Exemplo 1).

## 8. Armadilhas, diagnóstico e soluções

| Sintoma | Causa | Solução |
| --- | --- | --- |
| Soma da gold ≠ silver ativos | Filtro extra ou join que duplicou | Conferir `dim_uf` com chave única; contagens por etapa |
| `uf` nula | Código fora da dimensão (ex.: NI) | `left_anti`; decidir e documentar |
| Razão mulher/homem NULL | Nenhum vínculo de um dos sexos ou códigos de sexo diferentes | Conferir códigos no dicionário (Aula 09) |
| Crescimento salarial irreal | Série em R$ nominal | `*_sm` |
| `toPandas` lento ou OOM | Rodado na silver | Só na gold |
| Escolaridade com rótulo NULL | Código fora de 1–11 | Conferir dicionário |

## 9. Boas práticas

1. Uma tabela por pergunta, com grão no nome (guia).
2. Rótulos dizem "vínculos" (guia).
3. Funções puras com testes (guia).
4. Broadcast nas dimensões (guia).
5. `toPandas` só na gold (guia).
6. Documentar cada tabela gold no README: pergunta, grão, colunas, base (ativos ou todos).

## 10. Riscos

| Tipo | Risco | Mitigação |
| --- | --- | --- |
| Integridade analítica | Leitura de vínculos como pessoas | Rótulos e README |
| Integridade analítica | Média distorcida por extremos | Mediana junto |
| Integridade | Join com dimensão duplicada infla totais | Check de soma |
| Privacidade | Recortes muito finos expondo poucos vínculos | Evitar publicar células com contagem muito pequena |

## 11. Laboratório e validação na plataforma

**Contribuição ao projeto:** as cinco tabelas são o produto final do lakehouse.

`labcheck/test_aula13.py`:

```python
"""Checks da Aula 13: gold completa e coerente com a silver."""
import subprocess

from delta.tables import DeltaTable
from pyspark.sql import functions as F

from config.settings import GOLD, SILVER
from src.delta_io import ler

TABELAS = ["gold_emprego_uf_ano", "gold_gap_sexo_uf_ano", "gold_top_cnae_uf_ano",
           "gold_escolaridade_ano", "gold_desligamento_uf_ano"]


def test_a13_cinco_tabelas(spark):
    faltando = [t for t in TABELAS if not DeltaTable.isDeltaTable(spark, f"{GOLD}/{t}")]
    assert not faltando, f"Tabelas ausentes: {faltando}. Rode: python -m src.gold"


def test_a13_total_bate_silver(spark, ano):
    gold = (ler(spark, f"{GOLD}/gold_emprego_uf_ano").filter(F.col("ano") == ano)
            .agg(F.sum("qtd_vinculos")).first()[0])
    silver = ler(spark, SILVER).filter((F.col("ano") == ano) & F.col("vinculo_ativo")).count()
    assert gold == silver, f"gold={gold:,} silver ativos={silver:,}"


def test_a13_uf_preenchida(spark, ano):
    g = ler(spark, f"{GOLD}/gold_emprego_uf_ano").filter(F.col("ano") == ano)
    nulas = g.filter(F.col("uf").isNull()).select("cod_uf").collect()
    assert not nulas, f"UF nula para cod_uf {[r[0] for r in nulas]}. Investigue com left_anti."


def test_a13_top10(spark):
    maximo = ler(spark, f"{GOLD}/gold_top_cnae_uf_ano").agg(F.max("posicao")).first()[0]
    assert maximo <= 10, f"posicao máxima {maximo}"


def test_a13_teste_gap_sexo():
    r = subprocess.run(["pytest", "-q", "tests/test_utils.py::test_gap_sexo"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout[-500:]
```

- O check de UF nula é rigoroso de propósito: se o arquivo NI for carregado, ele falha e obriga você a decidir e documentar (excluir, ou mapear para "NI").
- Rode com `make check AULA=13 ANO=2022`.

**Checklist manual:**

- [ ] gerei um gráfico a partir da gold
- [ ] exportei um CSV e abri no Excel ou Power BI
- [ ] sei explicar por que desligamento usa todos os vínculos.

## 12. Exercícios, revisão e desafios

**Exercícios (guia, Parte [11](../guia/parte-11.md))**

1. Quais as 5 UFs com mais vínculos ativos?
2. Onde a `razao_mulher_homem` é menor?
3. Crie `gold_porte_ano` (remuneração por `tamanho_estab`).
4. Crie `gold_faixa_etaria_ano` (faixas `<25`, `25–39`, `40–59`, `60+` com `F.when`).
5. Exporte uma tabela gold para CSV e abra no Excel ou Power BI.

**Revisão**

1. Por que a taxa de desligamento não usa só os ativos?
2. Como `avg(when(...))` calcula a média só de um grupo?
3. Por que `left` e não `inner` no join com `dim_uf`?
4. Por que as funções não gravam nada?

**Respostas sugeridas:** (1) desligado em 31/12 não está ativo; usar só ativos esconderia os desligamentos; (2) os outros grupos viram NULL e `avg` ignora NULL; (3) para não perder linhas e tornar visível o código sem UF; (4) para serem testáveis sem lake.

**Desafios**

1. Escreva o teste de unidade de `gold_faixa_etaria_ano` antes de implementá-la.
2. Acrescente `remun_mediana_dez_sm` a `gold_gap_sexo_uf_ano` e compare com a razão das médias.

## 13. Referências cruzadas

| Tema | Onde |
| --- | --- |
| Grão e rótulos | Aulas 01 e 09 |
| Agregações, `when` | Aula 07 |
| Window, broadcast, `left_anti` | Aula 08 |
| Dimensões e `gravar_tabela` | Aula 10 |
| Silver de origem | Aula 12 |
| Gold com vários anos | Aula 14 |
| Testes e CI | Aula 16 |


## Checks automáticos

```bash
make check AULA=13 ANO=2022
```

Arquivo: `labcheck/test_aula13.py`. Cada execução grava o resultado em `progress/historico.jsonl`; depois rode `make progresso` para atualizar a página [Progresso](../progresso.md).

| Check | O que verifica |
| --- | --- |
| `a13_cinco_tabelas` | cinco tabelas |
| `a13_total_bate_silver` | total bate silver |
| `a13_uf_preenchida` | uf preenchida |
| `a13_top10` | top10 |
| `a13_teste_gap_sexo` | teste gap sexo |
