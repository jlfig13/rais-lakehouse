---
aula: 17
titulo: "Catálogo de dados, metadados e consumo por IA"
origem: ['Complemento da plataforma']
depende_de: [10, 13, 14]
checks: ['a17_catalogo_valido', 'a17_catalogo_confere_com_lake', 'a17_comentarios_aplicados', 'a17_contexto_ia']
---

# Aula 17 — Catálogo de dados, metadados e consumo por IA

<!-- Página GERADA por scripts/gerar_curso.py. Edite aulas.yml e curso/conteudo/. -->

<div class="rl-aula" data-aula="17" data-onde="container" data-lab="src/catalogo.py"></div>

| | |
| --- | --- |
| Origem no guia | Complemento da plataforma |
| Depende de | [Aula 10](aula-10.md), [Aula 13](aula-13.md), [Aula 14](aula-14.md) |
| Entregas | `catalogo/rais.yml`, `src/catalogo.py`, `catalogo/rais.json` |
| Onde os checks rodam | Container spark |

Ao final desta aula cada tabela do lake tem descrição, grão, dono e descrição de coluna com unidade, gravados na própria tabela Delta e num arquivo JSON pronto para servir de contexto a uma IA. Você também entende o que é o Unity Catalog e quando um catálogo completo como ele passa a valer a pena.

## 1. Objetivos e pré-requisitos

1. Explicar o que é um catálogo de dados e o que ele resolve (descoberta, significado, governança).
2. Conhecer o Unity Catalog OSS e alternativas (Hive Metastore, Apache Polaris, DataHub, OpenMetadata).
3. Descrever tabelas e colunas num arquivo versionado e validá-lo com Pydantic.
4. Gravar as descrições como `COMMENT` nas tabelas Delta e conferir o catálogo contra o schema real.
5. Exportar o catálogo como contexto para IA e saber usá-lo com segurança.

**Pré-requisitos:** Aula 13 (gold), Aula 14 (pipeline) e Aula 10 (Pydantic, seção 3.7).

## 2. Contextualização

Depois de 16 aulas o lake tem dezenas de colunas em nove tabelas. Quem chega ao projeto pergunta: "`remun_media_dez_sm` é média de quê? A `qtd_vinculos` conta pessoas? Qual tabela uso para comparar anos?". Hoje a resposta está espalhada pelas aulas e pelo `docs/dicionario.md`. Um **catálogo de dados** junta essas respostas num lugar consultável por pessoas, por ferramentas de BI e por modelos de IA, e mantém o significado colado ao dado.

## 3. Fundamentação teórica

### 3.1 O que um catálogo faz

| Função | Pergunta que responde | Exemplo no projeto |
| --- | --- | --- |
| Inventário | Que tabelas existem e onde estão? | `gold.gold_emprego_uf_ano` em `s3a://rais/gold/...` |
| Significado | O que cada coluna quer dizer, em que unidade? | `qtd_vinculos`: vínculos ativos em 31/12 |
| Grão e regras | O que uma linha representa? Que cuidados tomar? | "ano × UF"; "vínculo não é pessoa" |
| Responsabilidade | Quem cuida, com que frequência atualiza? | dono, atualização |
| Governança | Quem pode ler e escrever o quê? | (Unity Catalog: permissões por tabela) |
| Linhagem | De onde a tabela vem? | gold ← silver ← bronze |

### 3.2 Unity Catalog

O **Unity Catalog** é o catálogo da Databricks, aberto em 2024 como projeto open source ([repositório](https://github.com/unitycatalog/unitycatalog), [site](https://www.unitycatalog.io/)). Ele organiza os dados num espaço de nomes de três níveis, `catálogo.schema.tabela` (por exemplo, `rais.gold.gold_emprego_uf_ano`), e guarda, além das tabelas, volumes (arquivos), funções e modelos de ML. Roda como um servidor com API REST; o Spark se conecta por um conector próprio e passa a enxergar as tabelas pelo nome, sem caminho.

| Ponto | Detalhe |
| --- | --- |
| O que traz | Nomes lógicos em vez de caminhos, permissões (`GRANT`), descrições, auditoria e um único ponto de acesso para vários motores |
| Como roda localmente | Um container a mais no Compose com o servidor do Unity Catalog; confira no repositório oficial a imagem e a versão atuais, como fizemos com o MinIO |
| Integração com este projeto | O conector Spark do Unity Catalog exige versões casadas de Spark e Delta. Confira a matriz de compatibilidade da versão escolhida contra as nossas (Spark 3.5.3, Delta 3.2.0); se ela pedir outra versão do Delta, a troca é uma decisão de arquitetura que mexe na imagem (Aula 02) e merece um ADR |
| Quando vale | Várias equipes, vários motores (Spark, Trino, DuckDB) lendo as mesmas tabelas, necessidade de controle de acesso por tabela ou coluna |
| Quando não vale | Um projeto de uma pessoa ou uma equipe pequena com um motor só: o custo de operar mais um serviço supera o ganho |

**Alternativas.** O *Hive Metastore* é o catálogo histórico do ecossistema Hadoop/Spark (só nomes e schemas, sem governança rica). O *Apache Polaris* é um catálogo REST para tabelas Iceberg. *DataHub* e *OpenMetadata* são catálogos de **descoberta**: não servem as tabelas aos motores, mas indexam metadados de várias fontes, mostram linhagem e permitem busca.

### 3.3 O catálogo deste projeto: leve e versionado

Para o tamanho do RAIS Lakehouse, um catálogo em arquivo resolve o essencial (inventário, significado, grão, regras) sem operar um servidor:

1. **`catalogo/rais.yml`** — fonte única, versionada no Git e revisada em pull request como qualquer código.
2. **`src/catalogo.py`** — valida o YAML com Pydantic, confere contra o schema real das tabelas e grava as descrições **dentro** das tabelas Delta (`COMMENT` em colunas e `TBLPROPERTIES` na tabela). Assim o significado viaja com o dado: qualquer `DESCRIBE TABLE` mostra as descrições.
3. **`catalogo/rais.json`** — exportação com tipos reais e regras de negócio, para ferramentas e para IA.

Se o projeto crescer, o mesmo YAML vira a carga inicial de um Unity Catalog: as descrições já existem, só mudam de lugar.

## 4. Arquitetura e fluxo

```
 catalogo/rais.yml ──(Pydantic)──▶ objetos Catalogo/Tabela/Coluna
        │                                   │
        │                     conferir ◀── schema real das tabelas Delta (s3a://rais/...)
        │                                   │ problemas? → para com a lista
        ▼                                   ▼
  revisão em PR              aplicar: ALTER TABLE ... SET TBLPROPERTIES / ALTER COLUMN ... COMMENT
                                            │
                                            ▼
                             catalogo/rais.json (tipos + descrições + regras) → IA, BI, site
```

A gold é recriada inteira a cada execução e perde os comentários; por isso o pipeline ganhou a etapa `catalogo`, que roda depois da gold.

## 5. Tutorial

### Passo 1 — Ler o catálogo

Abra `catalogo/rais.yml`. Cada tabela tem `nome` (`camada.tabela`), `caminho` no lake, `descricao`, `grao`, `atualizacao`, uma `pergunta` (na gold) e a lista de `colunas`. A bronze tem `completa: false` porque suas dezenas de colunas variam por ano; silver e gold exigem descrição de todas as colunas. O topo do arquivo traz as `regras` de negócio que valem para todo o lake.

### Passo 2 — Validar e conferir

```bash
docker compose exec spark python -m src.catalogo
```

O módulo valida o YAML (um campo faltando ou uma descrição curta demais param com o caminho exato do erro) e compara cada tabela com o schema real. Experimente apagar a descrição de `qtd_vinculos` da `gold_emprego_uf_ano` e rodar de novo: a saída aponta `coluna sem descrição: qtd_vinculos`.

### Passo 3 — Gravar no lake e exportar

```bash
docker compose exec spark python -m src.catalogo --aplicar
# ou, no fim do pipeline:
make pipeline ANOS="2022" ETAPAS="silver gold catalogo"
```

Confira a descrição gravada na tabela:

```python
from config.settings import GOLD

spark.sql(f"DESCRIBE TABLE delta.`{GOLD}/gold_emprego_uf_ano`").show(truncate=False)
spark.sql(f"SHOW TBLPROPERTIES delta.`{GOLD}/gold_emprego_uf_ano`").show(truncate=False)
```

Resultado real sobre o lake do projeto: a coluna `qtd_vinculos` aparece com o comentário "Vínculos ativos em 31/12. Unidade: vínculos." e a tabela com as propriedades `rais.grao = ano × UF`, `rais.dono` e `rais.atualizacao`.

### Passo 4 — Usar o catálogo como contexto para IA

`catalogo/rais.json` tem, para cada tabela, caminho, grão, pergunta, colunas com tipo real e unidade, e as regras de negócio. Para um assistente que gera SQL, o contexto é montado assim:

```python
import json

catalogo = json.load(open("catalogo/rais.json", encoding="utf-8"))
gold = [t for t in catalogo["tabelas"] if t["nome"].startswith("gold.")]
contexto = "\n".join(
    [f"Regras: {' '.join(catalogo['regras_de_negocio'])}"]
    + [f"Tabela {t['nome']} (grão: {t['grao']}): {t['descricao']} Colunas: "
       + "; ".join(f"{c['nome']} ({c['tipo']}, {c['unidade'] or 'sem unidade'}): {c['descricao']}"
                   for c in t["colunas"])
       for t in gold]
)
print(contexto[:600])
```

Esse texto vai no início da conversa com o modelo, antes da pergunta. Com ele, a IA sabe que deve usar `*_sm` para comparar anos e escrever "vínculos", porque as regras estão no contexto e não dependem de quem pergunta.

## 6. Funcionamento e resultados esperados

| Passo | Esperado |
| --- | --- |
| `python -m src.catalogo` | `[catalogo] ok: 7 tabelas conferidas com o lake` |
| `--aplicar` | Comentários nas colunas e `catalogo/rais.json` gerado |
| `DESCRIBE TABLE` | Coluna `comment` preenchida |
| Coluna nova na gold sem descrição | A conferência falha e aponta a coluna |

## 7. Exemplos práticos

**Exemplo 1 — Catálogo como teste.** `labcheck/test_aula17.py` roda a conferência: se alguém criar uma coluna na gold e esquecer de descrevê-la, o check falha. Documentação passa a ser verificada como código.

**Exemplo 2 — Busca por significado.** Com as descrições no JSON, achar "onde está a remuneração em salários mínimos" é um filtro simples:

```python
[(t["nome"], c["nome"]) for t in catalogo["tabelas"] for c in t["colunas"]
 if c["unidade"] == "salários mínimos"]
```

**Exemplo 3 — Do YAML ao Unity Catalog.** Se um dia o projeto adotar o Unity Catalog, as mesmas descrições viram comandos `COMMENT ON TABLE rais.gold.gold_emprego_uf_ano IS '...'`: o trabalho de documentar já está feito e versionado.

## 8. Armadilhas, diagnóstico e soluções

| Sintoma | Causa | Solução |
| --- | --- | --- |
| Comentários sumiram da gold | A gold é recriada com `overwriteSchema` | Rode a etapa `catalogo` depois da gold |
| `tabela não encontrada` | Pipeline ainda não criou a tabela | Rode o pipeline antes |
| `coluna descrita não existe` | Coluna renomeada na transformação | Atualize o YAML no mesmo PR da mudança |
| `ValidationError` ao carregar | Campo faltando ou descrição curta | A mensagem aponta `tabelas.N.colunas.M.descricao` |
| IA responde "trabalhadores" | Regras fora do contexto | Envie `regras_de_negocio` junto com as tabelas |

## 9. Boas práticas

1. O catálogo muda no mesmo pull request que muda a tabela.
2. Descreva a unidade e o grão sempre; são as duas informações que mais evitam erro de análise.
3. Uma pergunta de negócio por tabela gold, escrita no catálogo.
4. Para IA, entregue só a gold e o catálogo; nunca microdados.
5. Prefira descrições que alguém de fora do time entenda, sem siglas internas.

## 10. Riscos

| Tipo | Risco | Mitigação |
| --- | --- | --- |
| Integridade | Catálogo desatualizado induz a erro | Conferência automática (Passo 2 e check) |
| Segurança | IA com acesso a dados sensíveis | Só gold agregada, modo leitura, consultas registradas |
| Operação | Servidor de catálogo vira ponto de falha | Catálogo em arquivo até haver necessidade real de governança |

## 11. Laboratório e validação na plataforma

Checks em `labcheck/test_aula17.py` (container):

```bash
make check AULA=17
```

**Checklist manual**

- [ ] Sei explicar a diferença entre um catálogo que serve tabelas (Unity Catalog) e um de descoberta (DataHub, OpenMetadata).
- [ ] Rodei `python -m src.catalogo --aplicar` e vi os comentários no `DESCRIBE TABLE`.
- [ ] Montei o contexto para IA a partir de `catalogo/rais.json`.
- [ ] Sei por que os comentários da gold precisam ser regravados a cada execução.

## 12. Exercícios, revisão e desafios

**Exercícios**

1. Descreva no catálogo a tabela `gold_faixa_etaria_ano` (exercício 4 da Aula 13) e rode a conferência.
2. Acrescente à gold a coluna `regiao` (Aula 13, seção 3.6) e veja a conferência apontar a coluna sem descrição. Descreva-a.

**Revisão**

1. Por que gravar as descrições na própria tabela Delta, e não só no YAML?
2. Quando o Unity Catalog passa a valer o custo de operar mais um serviço?
3. O que precisa ir no contexto de uma IA para ela não confundir vínculo com pessoa?

**Respostas sugeridas:** (1) porque o significado viaja com o dado: qualquer motor que leia a tabela vê as descrições; (2) com várias equipes, vários motores e necessidade de permissões por tabela; (3) as regras de negócio do catálogo, junto com grão e unidade de cada coluna.

**Desafio:** suba o Unity Catalog OSS num container do Compose, registre a `gold_emprego_uf_ano` como tabela externa apontando para o caminho no MinIO e leve as descrições do YAML para lá. Registre num ADR as versões usadas e o que precisou mudar na imagem.

## 13. Referências cruzadas

| Tema | Onde |
| --- | --- |
| Pydantic | Aula 10, seção 3.7 |
| Enriquecimento e preparação para IA | Aula 13, seções 3.6 e 3.7 |
| Pipeline e etapas | Aula 14 |
| Matriz de validações | Aula 16, seção 3.6 |
| Unity Catalog | [Repositório oficial](https://github.com/unitycatalog/unitycatalog) |


## Checks automáticos

```bash
make check AULA=17 ANO=2022
```

Arquivo: `labcheck/test_aula17.py`. Cada execução grava o resultado em `progress/historico.jsonl`; depois rode `make progresso` para atualizar a página [Progresso](../progresso.md).

| Check | O que verifica |
| --- | --- |
| `a17_catalogo_valido` | catalogo/rais.yml passa na validação do Pydantic. |
| `a17_catalogo_confere_com_lake` | Toda tabela existe e toda coluna de silver/gold está descrita. |
| `a17_comentarios_aplicados` | As descrições estão gravadas na gold (rode: python -m src.catalogo --aplicar). |
| `a17_contexto_ia` | catalogo/rais.json existe, com regras de negócio e tipos das colunas. |
