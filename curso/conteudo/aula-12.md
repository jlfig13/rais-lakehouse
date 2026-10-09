# Aula 12 — Camada silver: tipagem, validação e campos derivados

Oct 9, 2026

A silver transforma a bronze (texto fiel à origem) em dado confiável: tipos corretos, valores inválidos como NULL, campos derivados — e exatamente uma linha por vínculo, sem perder nenhuma.

```yaml
aula: 12
titulo: "Camada silver: tipagem, validação e campos derivados"
origem: ["Guia Parte 10"]
depende_de: [11]
entrega: ["src/silver.py", "notebooks/03_silver.ipynb", "docs/dicionario.md (decisões)"]
checks: [a12_silver_delta, a12_contagem_igual_bronze, a12_tipos_do_contrato, a12_uf_valida, a12_idade_plausivel]
```


## 1. Objetivos e pré-requisitos

1. Aplicar as seis responsabilidades da silver.
2. Decidir o tipo de cada coluna (string, int, decimal, boolean) e justificar.
3. Validar formatos com expressões regulares e faixas plausíveis.
4. Derivar UF, divisão CNAE e flag de desligamento.
5. Provar que nenhuma linha foi perdida.

**Pré-requisitos:** Aula 10 (utilitários), Aula 11 (bronze do ano), Aula 09 (dicionário).

## 2. Contextualização

A gold faz contas: somas, médias, proporções. Contas sobre texto não funcionam, e contas sobre valores lixo (`{ñ class}`, idade 999) dão resultados errados sem aviso. A silver é o lugar único onde essas decisões são tomadas e documentadas, para que toda tabela gold herde as mesmas regras.

## 3. Fundamentação teórica (guia, Parte 10.1)

### 3.1 As seis responsabilidades

1. Selecionar só as colunas úteis.
2. Converter tipos: decimal com vírgula vira `decimal`, códigos pequenos viram `int`.
3. Validar formatos: município com 6 dígitos, CNAE com 5, idade plausível.
4. Transformar valores inválidos ou "ignorados" em `NULL`.
5. Derivar campos: UF a partir do município, divisão CNAE a partir da classe.
6. **Manter uma linha por vínculo**: a silver não filtra linhas, só limpa valores. Por isso a contagem da silver deve bater com a da bronze.

### 3.2 Decisão de tipos

| Tipo de dado | Tipo na silver | Exemplos | Por quê |
| --- | --- | --- | --- |
| Código com zero à esquerda | `string` | CBO, CNAE, município | `"012345"` como número vira `12345` e destrói a informação |
| Código pequeno de categoria | `int` | sexo, escolaridade, raça/cor | Unifica `"01"` e `"1"`; casa com as dimensões `int` |
| Valor monetário | `decimal(18,2)` | remunerações | Exato (Aula 10) |
| Medida com decimal | `decimal(10,1)` | tempo de emprego | Vírgula decimal na origem |
| Sim/não | `boolean` | vínculo ativo, desligado no ano | Filtros diretos (`filter("vinculo_ativo")`) |

### 3.3 Por que não deduplicar

Como o dado público é anonimizado, **não há chave única** para deduplicar. Dois vínculos com todos os campos iguais podem ser reais (duas pessoas com o mesmo perfil no mesmo estabelecimento). Deduplicar "por todas as colunas" apagaria vínculos legítimos.

### 3.4 Validar e anular em vez de filtrar

`F.when(condição_válida, valor)` sem `otherwise` devolve NULL quando a condição é falsa: o valor inválido some, a linha fica. Filtrar a linha inteira por causa de uma idade inválida jogaria fora uma remuneração válida.

## 4. Arquitetura e fluxo

```
 bronze (ano = X, tudo string)
   │ 1. checa colunas obrigatórias  ── falta?  → ValueError (para o pipeline)
   │ 2. select + tipagem (col_or_null, to_int, to_decimal)
   │ 3. validação (regex, faixas)  → inválido vira NULL
   │ 4. derivados (cod_uf, cnae_divisao, desligado_no_ano)
   ▼
 silver (ano = X)  ── gravar_ano (sem mergeSchema: contrato fixo)
   │
   └─ checagem: contagem silver == contagem bronze
```

## 5. Tutorial

### Passo 1 — `src/silver.py` (guia, Parte 10.2)

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

**Leitura guiada.**

| Trecho | O que faz | Consequência |
| --- | --- | --- |
| `OBRIGATORIAS` | Falha cedo se faltar coluna essencial | Erro claro no pipeline, em vez de uma silver sem remuneração |
| `col_or_null` | Coluna ausente vira NULL | Anos com schema diferente não quebram |
| `(F.trim(...) == "1")` | Texto → boolean | `"0"` → false; vazio ou outro valor → false; NULL → NULL |
| `rlike(r"^\d{6}$")` | Exatamente 6 dígitos | `^` e `$` ancoram início e fim; sem eles, `"1234567"` passaria |
| `between(14, 100)` | Faixa inclusiva | Idades fora viram NULL |
| `mes_desligamento` 1–12 | 0 (não desligado) vira NULL | `desligado_no_ano` = mês não nulo |
| `F.substring(col, 1, 2)` | Dois primeiros caracteres (índice começa em 1) | `cod_uf` NULL quando o município é inválido |
| `gravar_ano` sem `merge_schema` | Enforcement | Mudar o contrato exige decisão explícita |

### Passo 2 — Rodar

```bash
docker compose exec spark python -m src.silver 2022
```

### Passo 3 — Explorar (guia, Parte 10), notebook `03_silver.ipynb`

```python
from pyspark.sql import functions as F
from config.settings import SILVER
from src.delta_io import ler
from src.utils import get_spark

spark = get_spark()
s = ler(spark, SILVER).filter("ano = 2022")
s.printSchema()

# NULL por coluna
s.select([F.sum(F.col(c).isNull().cast("int")).alias(c) for c in s.columns]).show(vertical=True)

s.describe("idade", "remun_dezembro_sm").show()
```

### Passo 4 — Registrar decisões em `docs/dicionario.md`

Para cada coluna em que você decidiu algo (ex.: o significado de `remun_dezembro_nom = 0`), escreva a decisão e o motivo (guia, Parte 10, exercício 5).

## 6. Funcionamento e resultados esperados

| Verificação | Esperado |
| --- | --- |
| `printSchema` | Tipos da tabela 3.2 |
| Contagem | **Igual à bronze** do mesmo ano |
| Conversões | Nenhum erro; valores ruins viraram NULL |
| `cod_uf` NULL | Próximo de zero (o arquivo NI pode gerar alguns) |
| `idade` | Entre 14 e 100 ou NULL |

As faixas de NULL aceitáveis são calibradas com o seu dado; os limites iniciais do guia estão na Aula 16.

## 7. Exemplos práticos

**Exemplo 1 — Antes e depois.**

| Bronze (string) | Silver | Por quê |
| --- | --- | --- |
| `municipio = "261160"` | `cod_municipio = "261160"`, `cod_uf = "26"` | 6 dígitos, válido |
| `municipio = "9999"` | `cod_municipio = NULL`, `cod_uf = NULL` | Formato inválido |
| `idade = "150"` | `idade = NULL` | Fora da faixa |
| `vl_remun_dezembro_nom = "2350,75"` | `2350.75` | Vírgula convertida |
| `vl_remun_dezembro_nom = "{ñ class}"` | `NULL` | `try_cast` falhou |
| `sexo_trabalhador = "02"` | `sexo = 2` | `to_int` unifica |

**Exemplo 2 — Onde os NULL surgiram.** Compare `s.filter(F.col("cod_uf").isNull())` com a bronze, juntando pela `arquivo_origem`, para ver se os NULL vêm do arquivo NI.

**Exemplo 3 — Validações recomendadas da silver: perfil de nulos e domínios.** A silver transforma valores inválidos em NULL; o risco é uma regra errada zerar uma coluna inteira sem ninguém notar. Duas checagens pegam isso: o perfil de nulos por coluna (compare com a carga anterior) e a conferência de domínio contra as dimensões.

```python
from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from config.settings import SILVER
from src.delta_io import ler
from src.dims import dim_sexo


def perfil_nulos(df: DataFrame) -> DataFrame:
    """Uma linha por coluna com o % de NULL. Guarde o resultado de cada carga para comparar."""
    total = df.count()
    linha = df.select([F.sum(F.col(c).isNull().cast("int")).alias(c) for c in df.columns]).first()
    dados = [(c, round(100 * (linha[c] or 0) / total, 2)) for c in df.columns]
    return spark.createDataFrame(dados, "coluna string, pct_nulo double").orderBy(F.desc("pct_nulo"))


s = ler(spark, SILVER).filter(F.col("ano") == 2022)
perfil_nulos(s).show(30, truncate=False)

# Domínio: código de sexo preenchido que não existe na dimensão
fora = s.join(dim_sexo(spark), "sexo", "left_anti").filter(F.col("sexo").isNotNull()).count()
assert fora == 0, f"{fora} vínculos com código de sexo fora da dimensão: confira o dicionário"
```

Testado sobre a amostra: perfil com as 21 colunas da silver e nenhum código de sexo fora da dimensão.

**Como ler o perfil.** Um valor alto não é erro por si só: `mes_desligamento` é NULL para todo vínculo não desligado, e isso é esperado. O que importa é a **variação** entre cargas e colunas que deveriam estar quase cheias (`cod_municipio`, `remun_dezembro_nom`). Se `remun_dezembro_nom` passa de 2% para 100% de NULL num ano novo, a conversão decimal quebrou (no layout de 2023, o decimal é ponto, ver Aula 09).

| Validação da silver | Regra | Onde |
| --- | --- | --- |
| Contagem silver = bronze | Nenhuma linha perdida ou inventada | `checar_silver`, check `a12_contagem_igual_bronze` |
| Tipos do contrato | `decimal(18,2)` para dinheiro, `string` para códigos | check `a12_tipos_do_contrato` |
| Perfil de nulos | Variação pequena entre cargas | Exemplo 3 |
| Domínios | Códigos dentro das dimensões | Exemplo 3 (`left_anti`) |
| Faixas plausíveis | Idade 14–100; mês 1–12 | check `a12_idade_plausivel` |
| UF derivada | Menos de 1% de UF nula | check `a12_uf_valida` |

## 8. Armadilhas, diagnóstico e soluções

| Sintoma | Causa | Solução |
| --- | --- | --- |
| `ValueError: colunas obrigatórias ausentes` | Nome diferente naquele ano | Conferir na bronze e mapear o nome |
| Contagem silver < bronze | Algum `filter` na silver | Remover; anular valores em vez de filtrar |
| Coluna inteira NULL | Nome de origem errado em `col_or_null`/`to_int` | `set(esperadas) - set(b.columns)` (Aula 11) |
| Remunerações com valores absurdos | Escape do ponto em `to_decimal` | Teste de unidade da Aula 10 |
| `cnae_classe` quase toda NULL | Formato com pontuação (ex.: `47.11-3`) naquele ano | Ajustar a regra e documentar no dicionário |
| Erro de schema ao gravar | Contrato mudou | Decidir conscientemente; recriar a silver se necessário |
| `vinculo_ativo` todo false | Código diferente de `"1"` naquele ano | Conferir valores distintos na bronze |

## 9. Boas práticas

1. A silver não filtra linhas (guia).
2. Não inventar deduplicação (guia).
3. Toda regra de validação vem do dicionário e fica documentada.
4. Medir NULL por coluna a cada carga (Aula 16).
5. Contrato fixo protegido por schema enforcement.

## 10. Riscos

| Tipo | Risco | Mitigação |
| --- | --- | --- |
| Integridade | Linhas perdidas | Checagem de contagem |
| Integridade | Regra errada zera uma coluna | NULL por coluna; limites na Aula 16 |
| Integridade analítica | Código de "ignorado" tratado como valor real | Decisões no dicionário |
| Desempenho | Muitas colunas desnecessárias | Selecionar só o que a gold usa |

## 11. Laboratório e validação na plataforma

**Contribuição ao projeto:** a silver alimenta todas as tabelas gold.

`labcheck/test_aula12.py` (somente leitura):

```python
"""Checks da Aula 12: contrato da silver."""
from delta.tables import DeltaTable
from pyspark.sql import functions as F

from config.settings import BRONZE, SILVER
from src.delta_io import ler

TIPOS = {
    "ano": "int", "cod_municipio": "string", "cnae_classe": "string", "cbo": "string",
    "sexo": "int", "escolaridade": "int", "idade": "int", "mes_desligamento": "int",
    "tempo_emprego_meses": "decimal(10,1)", "vinculo_ativo": "boolean",
    "remun_dezembro_nom": "decimal(18,2)", "remun_dezembro_sm": "decimal(18,2)",
    "cod_uf": "string", "cnae_divisao": "string", "desligado_no_ano": "boolean",
}


def silver_ano(spark, ano):
    return ler(spark, SILVER).filter(F.col("ano") == ano)


def test_a12_silver_delta(spark):
    assert DeltaTable.isDeltaTable(spark, SILVER), "Silver não existe. Rode o passo 2."


def test_a12_contagem_igual_bronze(spark, ano):
    bronze = ler(spark, BRONZE).filter(F.col("ano") == ano).count()
    silver = silver_ano(spark, ano).count()
    assert silver == bronze, (
        f"silver={silver:,} bronze={bronze:,}. Diagnóstico: algum filter() na silver está "
        "removendo linhas; valores inválidos devem virar NULL."
    )


def test_a12_tipos_do_contrato(spark):
    reais = dict(ler(spark, SILVER).dtypes)
    erradas = {c: (reais.get(c), t) for c, t in TIPOS.items() if reais.get(c) != t}
    assert not erradas, f"Coluna: (obtido, esperado) -> {erradas}"


def test_a12_uf_valida(spark, ano):
    s = silver_ano(spark, ano)
    pct = s.select(F.avg(F.col("cod_uf").isNull().cast("int"))).first()[0]
    assert pct <= 0.01, f"{pct:.1%} de UF nula. Veja o arquivo NI e a regra do município."


def test_a12_idade_plausivel(spark, ano):
    fora = silver_ano(spark, ano).filter(~F.col("idade").between(14, 100)).limit(1).count()
    assert fora == 0, "Há idades fora de 14..100 que deviam ter virado NULL."
```

- O limite de 1% de UF nula é o do guia (Parte 15.4) e deve ser calibrado com o seu dado.
- `~F.col("idade").between(...)` com idade NULL dá NULL e a linha não entra no filtro — o check conta só idades não nulas fora da faixa (Aula 07, seção 3.4).
- Rode com `make check AULA=12 ANO=2022`.

**Checklist manual:** \[ \] rodei a contagem de NULL por coluna · \[ \] registrei pelo menos uma decisão no dicionário · \[ \] sei explicar por que não deduplicamos.

## 12. Exercícios, revisão e desafios

**Exercícios (guia, Parte 10)**

1. `printSchema()`: os tipos estão como planejado?
2. Conte os NULL por coluna.
3. Distribuição de `idade` e `remun_dezembro_sm`. Há valores absurdos?
4. Qual a % de vínculos com `vinculo_ativo = true`?
5. `remun_dezembro_nom = 0` significa o quê no dicionário? Decida se vira NULL e registre.

**Revisão**

1. Por que CBO é string e sexo é int?
2. Por que `when` sem `otherwise` e não `filter`?
3. Por que a silver não usa `mergeSchema`?
4. O que garante a regra "contagem silver = bronze"?

**Respostas sugeridas:** (1) CBO tem zero à esquerda; sexo é categoria pequena que casa com a dimensão; (2) para anular o valor sem perder a linha; (3) o contrato da silver é fixo e deve ser protegido; (4) que a silver não perde nem inventa vínculos.

**Desafios**

1. Acrescente `faixa_etaria` como campo derivado na silver ou mantenha-o só na gold. Defenda a escolha num ADR.
2. Escreva uma função `perfil_nulos(df)` que devolva um DataFrame (coluna, pct\_nulo) e use-a na Aula 16.

## 13. Referências cruzadas

| Tema | Onde |
| --- | --- |
| NULL em comparações | Aula 07 |
| Dicionário e códigos de ignorado | Aula 09 |
| `to_int`, `to_decimal`, `gravar_ano`, dimensões `int` | Aula 10 |
| Bronze de origem | Aula 11 |
| Consumo pela gold | Aula 13 |
| `checar_silver` no pipeline | Aula 14 |
| Limites de NULL e testes | Aula 16 |
