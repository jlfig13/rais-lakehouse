---
aula: 1
titulo: "Arquitetura Lakehouse e o projeto RAIS Lakehouse"
origem: ['Guia Parte 1']
depende_de: []
checks: ['a01_adrs_registrados']
---

# Aula 01 — Arquitetura Lakehouse e o projeto RAIS Lakehouse

<!-- Página GERADA por scripts/gerar_curso.py. Edite aulas.yml e curso/conteudo/. -->

<div class="rl-aula" data-aula="1" data-onde="host" data-lab=""></div>

| | |
| --- | --- |
| Origem no guia | Guia Parte [1](../guia/parte-01.md) |
| Depende de | — |
| Entregas | `docs/decisoes.md` |
| Onde os checks rodam | Host (WSL/Linux) |
| Documento original | [abrir](https://claude.ai/code/artifact/2a86be26-af3d-40e8-9385-2e68ce777f1e) |

## 1. Objetivos e pré-requisitos

Ao final desta aula você saberá explicar o que é um lakehouse, por que o projeto usa bronze, silver e gold, e terá registrado as seis decisões de arquitetura do RAIS Lakehouse em `docs/decisoes.md`.

**Convenção usada em todo o curso.** Trechos marcados com <span class="rl-complemento">Complemento didático</span> são explicações adicionadas para ensinar e não estavam no guia original. Todo o resto vem do RAIS Lakehouse Guide (Parte [1](../guia/parte-01.md), Arquitetura e decisões).

### Objetivos de aprendizagem

1. Diferenciar data warehouse, data lake e lakehouse, e dizer qual problema cada um resolve.
2. Explicar o que é um formato de tabela (Delta Lake, Apache Iceberg) e por que Parquet sozinho não basta.
3. Descrever a arquitetura medallion e a regra de ouro de cada camada: landing, raw, bronze, silver e gold.
4. Identificar os componentes do RAIS Lakehouse (Spark, MinIO, Delta, Docker Compose, staging local) e o papel de cada um.
5. Escrever um ADR (Architecture Decision Record) e um contrato de camada.

### Pré-requisitos

| Item | Nível esperado | Onde aprender, se faltar |
| --- | --- | --- |
| Python | Ler funções, listas e dicionários | Qualquer curso introdutório |
| SQL | `SELECT`, `WHERE`, `GROUP BY`, `JOIN` | Aula 07 revisa o equivalente em PySpark |
| Terminal | Navegar em pastas, criar arquivos | Aula 02 usa o terminal intensamente |
| Git | Opcional nesta aula | Aula 05 |
| Docker, Spark, Delta | Nenhum | Aulas 02 a 06 e 10 |

Esta aula é conceitual. Ela não exige nada instalado: o único artefato produzido é um arquivo Markdown.

### Duração sugerida

Cerca de 2 horas: 60 minutos de leitura, 30 de tutorial e 30 de exercícios. <span class="rl-complemento">Complemento didático</span>

## 2. Contextualização: por que o lakehouse existe

O lakehouse existe para juntar o armazenamento barato e aberto do data lake com as garantias de um data warehouse: transações, schema controlado e versões. <span class="rl-complemento">Complemento didático</span> — esta seção inteira é contexto histórico adicionado; o guia original parte direto para a arquitetura.

### O problema concreto deste curso

Os microdados da RAIS chegam como arquivos `.7z` com texto separado por `;`, encoding `latin-1`, decimal com vírgula e dezenas de milhões de linhas por ano (Parte [6](../guia/parte-06.md) do guia). Você precisa transformar isso em respostas como "qual a remuneração média por UF de 2019 a 2024". Três abordagens são possíveis.

### Abordagem 1 — Data warehouse

Um banco analítico (ex.: PostgreSQL usado como DW, ou um DW comercial) com tabelas tipadas e SQL.

- **Resolve:** consultas rápidas, transações, controle de acesso, schema rígido.
- **Custa:** o dado precisa ser carregado e tipado antes de entrar; armazenamento e processamento ficam acoplados; formatos proprietários dificultam levar o dado para outra ferramenta.
- **Quando usar:** dados bem estruturados, volume moderado, muitos usuários de SQL e BI.

### Abordagem 2 — Data lake

Arquivos guardados num storage barato (disco, HDFS, object storage S3), lidos por engines como o Spark.

- **Resolve:** guarda qualquer formato, escala barato, separa armazenamento de processamento.
- **Custa:** não há transações. Se um job falha no meio da escrita, sobram arquivos pela metade. Ninguém impede que um arquivo com colunas erradas entre na pasta. Não há histórico de versões.
- **Consequência típica:** o "data swamp" — um lago cheio de arquivos que ninguém confia em usar.

### Abordagem 3 — Lakehouse (a escolha do curso)

Arquivos abertos (Parquet) no storage barato, mais uma **camada de metadados transacional** (o formato de tabela: Delta Lake, Apache Iceberg ou Apache Hudi) que adiciona ACID, schema enforcement, versões e time travel.

| Critério | Data warehouse | Data lake | Lakehouse |
| --- | --- | --- | --- |
| Armazenamento | Interno ao banco | Arquivos em storage barato | Arquivos em storage barato |
| Formato | Proprietário ou interno | Aberto (CSV, Parquet) | Aberto (Parquet + log de transações) |
| Transações ACID | Sim | Não | Sim |
| Controle de schema | Rígido | Nenhum | Enforcement com evolução opcional |
| Versões / time travel | Depende do produto | Não | Sim |
| Escala de volume | Limitada pelo banco | Alta | Alta |
| Complexidade de operação | Média | Baixa no início, alta depois | Média |

### Quando o lakehouse NÃO é a melhor escolha

- Poucos GB de dados bem estruturados e uma equipe só de SQL: um PostgreSQL bem modelado é mais simples.
- Necessidade de consultas de baixíssima latência para aplicações (sistemas transacionais): use um banco OLTP.
- Ninguém para operar a infraestrutura: um serviço gerenciado pode custar menos que o tempo da equipe.

No RAIS Lakehouse, o lakehouse se justifica por três motivos do guia: volume de dezenas de milhões de linhas por ano, schema que muda entre anos e a exigência de usar apenas software open source on-premises.

## 3. Fundamentação teórica

Um lakehouse tem quatro peças independentes: storage, formato de arquivo, formato de tabela e engine de processamento. Entender cada uma separadamente é o que permite trocar uma sem reescrever as outras.

### 3.1 As quatro peças

| Peça | O que faz | No RAIS Lakehouse | Alternativas |
| --- | --- | --- | --- |
| Storage | Guarda bytes de forma durável | MinIO (API S3) | Disco local, HDFS, outros S3 compatíveis |
| Formato de arquivo | Organiza os dados dentro de cada arquivo | Parquet | ORC, Avro, CSV |
| Formato de tabela | Diz quais arquivos formam a tabela em cada versão | Delta Lake | Apache Iceberg, Apache Hudi |
| Engine | Lê, transforma e grava | Apache Spark (PySpark) em modo local | Trino, Flink, DuckDB |

<span class="rl-complemento">Complemento didático</span> A separação entre storage e engine é o que permite, por exemplo, processar com Spark hoje e consultar a mesma tabela com Trino amanhã (o guia cita Trino como próximo passo no Apêndice D).

### 3.2 Parquet: formato de arquivo colunar

**O que é.** Um formato que grava os dados coluna por coluna, com compressão e estatísticas (mínimo e máximo) por bloco. <span class="rl-complemento">Complemento didático</span>

**Por que importa.** Uma consulta que usa 3 de 50 colunas lê só essas 3 do disco. Filtros podem pular blocos inteiros cujo mínimo e máximo não atendem à condição. O guia (Partes [5.8](../guia/parte-05.md#parte-5-8) e [9](../guia/parte-09.md)) mostra essa vantagem ao comparar o tamanho do `.txt` com o da bronze.

**O limite.** Parquet descreve um arquivo, não uma tabela. Uma pasta com 200 arquivos Parquet não sabe quais deles são válidos, quais estão pela metade ou qual era o conteúdo de ontem.

### 3.3 Formato de tabela: o que o Delta Lake acrescenta

O Delta grava, ao lado dos Parquet, uma pasta `_delta_log/` com um arquivo JSON por versão. Cada versão registra quais arquivos entraram e quais saíram (Parte [13.1](../guia/parte-13.md#parte-13-1) do guia). Ler a tabela é: ler o log, descobrir a lista de arquivos válidos e só então ler esses Parquet. Disso derivam as garantias:

| Garantia | Significado | Sem formato de tabela |
| --- | --- | --- |
| Atomicidade | A escrita aparece inteira ou não aparece | Job que cai no meio deixa arquivos parciais visíveis |
| Isolamento | Leitores veem sempre uma versão completa | Leitor pode pegar metade de uma escrita |
| Schema enforcement | Escrita com schema incompatível é recusada | Arquivo com colunas erradas entra silenciosamente |
| Time travel | Ler versões anteriores | Impossível depois de sobrescrever |
| Overwrite por partição atômico | `replaceWhere` troca só um ano | Overwrite dinâmico pode deixar estado intermediário |

O detalhe operacional de cada garantia é tema da Aula 10 (fundamentos Delta) e da Aula 14 (operações Delta).

### 3.4 Delta Lake × Apache Iceberg

O guia escolhe Delta (ADR nº 4). A comparação abaixo resume a justificativa do guia:

| Critério | Delta Lake | Apache Iceberg |
| --- | --- | --- |
| Recursos centrais (ACID, time travel, MERGE, evolução de schema) | Sim | Sim |
| Setup no PySpark | JARs + duas configurações | Exige configurar um catálogo (REST, JDBC, Hive ou Hadoop) desde o início |
| Ponto forte | Integração direta com Spark | Várias engines lendo as mesmas tabelas |
| Curva de aprendizado no curso | Menor | Maior |

**Consequência de escolher errado.** Escolher Iceberg sem precisar de multi-engine adiciona um componente (o catálogo) para operar e depurar logo na primeira aula prática. Escolher Delta e depois precisar de várias engines exige migração — o guia lembra que os conceitos são os mesmos, então a migração é de configuração e não de modelo mental.

### 3.5 Arquitetura medallion

**O que é.** Uma convenção de organizar o lake em camadas de qualidade crescente. O guia usa cinco níveis: dois de staging (landing, raw) e três no lake (bronze, silver, gold).

**Por que existe.** Separar responsabilidades: cada camada tem uma única regra de ouro, então um erro é localizado e corrigido numa camada sem contaminar as outras. E as camadas posteriores podem ser sempre reconstruídas a partir das anteriores.

| Camada | Onde fica | Formato | Objetivo | Regra de ouro |
| --- | --- | --- | --- | --- |
| landing | disco local `/staging/landing` | `.7z` original | Guardar o arquivo como veio | Nunca editar; é a fonte da verdade |
| raw | disco local `/staging/raw` | `.txt` extraído | Arquivo intermediário | Temporário; apagar após a bronze |
| bronze | MinIO | Delta | Cópia fiel e eficiente da origem | Tudo `string`, nomes normalizados, sem regra de negócio |
| silver | MinIO | Delta | Dado limpo e tipado | Uma linha = um vínculo, tipos corretos |
| gold | MinIO | Delta | Respostas prontas para análise | Cada tabela responde uma pergunta |

**Alternativas.** <span class="rl-complemento">Complemento didático</span> Há quem use só duas camadas (raw e curated) ou modelagem dimensional direta (staging → fato/dimensão). Medallion não é obrigatório; é uma convenção que funciona bem quando a origem é suja e muda com o tempo, exatamente o caso da RAIS.

### 3.6 Idempotência

**O que é.** Executar o mesmo passo duas vezes produz o mesmo resultado que executar uma vez. **Por que importa:** pipelines falham e são reexecutados; sem idempotência, cada reexecução duplica dados. No guia ela vem de três escolhas: pular arquivos já baixados, gravar bronze e silver com `replaceWhere` por ano e recriar a gold inteira (Parte [12.1](../guia/parte-12.md#parte-12-1)). É um conceito que atravessa todo o curso.

## 4. Arquitetura do RAIS Lakehouse

Três containers orquestrados pelo Docker Compose formam o projeto: `spark` processa, `minio` armazena e `minio-init` prepara o armazenamento e termina. A landing e a raw ficam em disco local; bronze, silver e gold ficam no MinIO como tabelas Delta.

!!! note "Diagrama interativo"
    "RAIS Lakehouse · 3 containers, 5 camadas" está no [documento original](https://claude.ai/code/artifact/2a86be26-af3d-40e8-9385-2e68ce777f1e).

O `.7z` entra na landing e é extraído para a raw; o Spark lê esse texto e grava cada camada no bucket `rais`. Só a gold, em destaque, é consumida por análises e BI.

### Componentes

| Componente | Papel | Por que está aqui | Aula |
| --- | --- | --- | --- |
| Container `spark` | Python 3.11, Java 17, PySpark 3.5.3, delta-spark 3.2.0 e JupyterLab | Uma imagem reprodutível com tudo que o processamento precisa | 02, 06 |
| Spark em modo `local` | Executa as transformações usando os núcleos do container | Uma máquina basta; o código é o mesmo num cluster (ADR-001) | 06, 15 |
| `/staging` (bind mount) | Guarda landing e raw no disco do host | Arquivos temporários não precisam de versionamento (ADR-005) | 03, 11 |
| Container `minio` | Object storage com API S3, porta 9000 (API) e 9001 (console) | Padrão S3, migra para qualquer storage compatível (ADR-003) | 04 |
| Container `minio-init` | Cria o bucket `rais`, a política `rais-rw` e o usuário da aplicação | Separa administração de uso; idempotente | 04 |
| Conector S3A (`hadoop-aws`) | Permite ao Spark ler e gravar em `s3a://rais/...` | É como o Spark fala S3 | 04, 06 |
| Delta Lake | Log de transações sobre os Parquet de cada camada | ACID, versões, schema enforcement (ADR-004) | 10, 14 |
| Volume `minio-data` | Onde os dados do lake moram de fato | Sobrevive à remoção dos containers | 03 |

### Fluxo de dados, passo a passo

1. **Aquisição:** o `.7z` de cada região e ano é baixado para `/staging/landing/<ano>/` (manual ou por `src/ingest.py`).
2. **Extração:** `extrair(ano)` descompacta para `/staging/raw/<ano>/`.
3. **Bronze:** o Spark lê o texto (`;`, `latin-1`), normaliza nomes e grava Delta em `s3a://rais/bronze/rais_vinculos`, partição `ano`.
4. **Limpeza da raw:** com `--limpar-raw`, a pasta `raw/<ano>` é apagada; a landing permanece.
5. **Silver:** lê a bronze do ano, tipa, valida e grava em `s3a://rais/silver/rais_vinculos`.
6. **Checagem:** `checar_silver` confirma contagem silver = bronze e limites de NULL.
7. **Gold:** lê a silver inteira e recria as cinco tabelas em `s3a://rais/gold/<tabela>`.

Os passos 2 a 6 repetem por ano; o passo 7 roda uma vez no fim (Parte [12](../guia/parte-12.md) do guia, detalhada na Aula 14).

## 5. Tutorial: decisões de arquitetura e contratos de camada

O entregável desta aula é o arquivo `docs/decisoes.md`, com as seis decisões do guia em formato ADR e um contrato por camada. Ele vai para o repositório na Aula 05; por enquanto, escreva-o num editor de texto qualquer.

### Passo 1 — Entender o formato ADR

Um **ADR** (Architecture Decision Record) é um registro curto de uma decisão técnica: contexto, decisão, alternativas e consequências. O guia recomenda registrá-los em `docs/decisoes.md` (Parte [1.3](../guia/parte-01.md#parte-1-3)).

**Por que existe.** Seis meses depois, ninguém lembra por que o projeto usa Delta e não Iceberg. Sem o registro, a decisão é rediscutida do zero ou, pior, revertida sem entender o motivo. <span class="rl-complemento">Complemento didático</span> Em entrevistas e portfólio, ADRs mostram que você sabe justificar escolhas, não só executá-las.

### Passo 2 — Criar o modelo

<span class="rl-complemento">Complemento didático</span> O guia usa uma tabela resumida. O modelo abaixo expande cada linha em campos, o que é útil para decisões que você vai revisitar.

```markdown
# Decisões de arquitetura — RAIS Lakehouse

## ADR-NNN — <título curto da decisão>

- **Status:** aceita | substituída por ADR-XXX | em discussão
- **Data:** AAAA-MM-DD
- **Contexto:** que problema ou restrição forçou a decisão
- **Decisão:** o que foi escolhido, em uma frase
- **Alternativas consideradas:** o que foi descartado e por quê
- **Consequências:** o que fica mais fácil, o que fica mais difícil, o que precisa ser revisto
```

**Campos explicados.**

- **Status:** uma decisão nunca é apagada. Se mudar, o ADR antigo vira "substituída por ADR-XXX", preservando o histórico.
- **Contexto:** a restrição real (ex.: "só open source on-premises"). É o campo mais importante, porque é ele que diz quando a decisão deixa de valer.
- **Consequências:** inclua as negativas. Uma decisão sem custo listado provavelmente não foi analisada.

### Passo 3 — Preencher os seis ADRs do guia

As seis decisões abaixo vêm da Parte [1.3](../guia/parte-01.md#parte-1-3) do guia. Exemplo completo do ADR-004:

```markdown
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
```

Preencha os outros cinco no mesmo formato:

| ADR | Decisão | Alternativa | Motivo (do guia) |
| --- | --- | --- | --- |
| 001 | Spark em modo `local` num container | Cluster Spark standalone | Uma máquina basta para aprender; o código é o mesmo num cluster |
| 002 | Docker Compose | Instalar tudo no host | Reprodutível: qualquer pessoa sobe o projeto com um comando |
| 003 | MinIO (API S3) | HDFS, disco local | API S3 é padrão de mercado; o código migra para qualquer S3 |
| 004 | Delta Lake | Apache Iceberg | Setup mais simples no PySpark; mesmos conceitos |
| 005 | Staging em disco local | MinIO | `.7z`/`.txt` são temporários; não precisam de versionamento |
| 006 | JARs embutidos na imagem | Baixar do Maven em execução | Funciona sem internet e é reprodutível |

### Passo 4 — Escrever os contratos de camada

<span class="rl-complemento">Complemento didático</span> Um **contrato de camada** diz o que quem consome a camada pode assumir. O guia define as regras de ouro; o contrato as transforma em promessas verificáveis. Adicione ao mesmo arquivo:

```markdown
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
```

Cada item do contrato vira uma verificação automática nas Aulas 12 e 16 (ex.: "contagem silver = bronze" é exatamente o que `checar_silver` testa).

### Passo 5 — Desenhar o diagrama

Reproduza o diagrama da seção 4 desta aula no seu README (ASCII, Mermaid ou imagem). O guia traz uma versão em ASCII na Parte [1.1](../guia/parte-01.md#parte-1-1) que pode ser copiada como ponto de partida.

## 6. Como cada etapa funciona e o que esperar

O tutorial produz um documento, não código. O teste de que ele está bom é: alguém que não participou da decisão consegue entender por que o projeto é assim lendo só o `docs/decisoes.md`.

| Passo | O que acontece | Resultado esperado | Sinal de que algo está errado |
| --- | --- | --- | --- |
| 1. Entender ADR | Você separa decisão de implementação | Consegue dizer o contexto de cada escolha | Você descreve "o que" mas não "por que" |
| 2. Modelo | Um formato único para todas as decisões | Arquivo com o cabeçalho e o modelo | Cada ADR com campos diferentes |
| 3. Seis ADRs | Cada decisão tem contexto, alternativa e custo | Seis entradas, cada uma com pelo menos uma consequência negativa | Consequências só positivas |
| 4. Contratos | Regras de ouro viram promessas verificáveis | Três contratos (bronze, silver, gold) com grão definido | Grão ausente ou vago ("dados limpos") |
| 5. Diagrama | A arquitetura cabe numa imagem | Diagrama no README | Componentes no diagrama que não estão nos ADRs |

**Por que o grão é o item mais importante do contrato.** <span class="rl-complemento">Complemento didático</span> O grão diz o que uma linha representa. Na RAIS, confundir "um vínculo" com "uma pessoa" é o erro analítico mais grave possível: uma pessoa com dois empregos aparece duas vezes, e os microdados públicos são anonimizados, então não há como deduplicar pessoas (Parte [6.1](../guia/parte-06.md#parte-6-1) do guia). Declarar o grão no contrato impede que alguém some vínculos e chame o resultado de "número de trabalhadores".

## 7. Exemplo prático: um vínculo atravessando as camadas

Acompanhar uma única linha de ponta a ponta mostra o papel de cada camada melhor que qualquer definição. <span class="rl-complemento">Complemento didático</span> Os valores abaixo são fictícios, montados para ilustrar; os nomes de colunas e as transformações são os do guia (Partes [6](../guia/parte-06.md), [9](../guia/parte-09.md), [10](../guia/parte-10.md) e [11](../guia/parte-11.md)).

### Na landing

O arquivo `RAIS_VINC_PUB_NORDESTE.7z` (nome ilustrativo; confira os nomes reais de cada ano) fica em `/staging/landing/2022/`, intocado. Se tudo depois der errado, é daqui que se recomeça.

### Na raw

Depois de extraído, uma linha do `.txt` se parece com isto (cabeçalho e linha, encurtados):

```text
Município;CNAE 2.0 Classe;CBO Ocupação 2002;Vínculo Ativo 31/12;Sexo Trabalhador;Idade;Vl Remun Dezembro Nom;Vl Remun Dezembro (SM)
261160;47113;411005;1;2;34;2350,75;1,94
```

Repare: separador `;`, vírgula decimal e cabeçalho com acentos, espaços e parênteses.

### Na bronze

A mesma linha, com nomes normalizados e **tudo como string** (mais `ano` e `arquivo_origem`):

| coluna | valor | tipo |
| --- | --- | --- |
| `municipio` | `"261160"` | string |
| `cnae_2_0_classe` | `"47113"` | string |
| `vinculo_ativo_31_12` | `"1"` | string |
| `sexo_trabalhador` | `"2"` | string |
| `vl_remun_dezembro_nom` | `"2350,75"` | string |
| `vl_remun_dezembro_sm` | `"1,94"` | string |
| `ano` | `2022` | int |

**Por que não tipar já aqui?** Se em algum ano uma coluna trouxer um valor inesperado (ex.: `{ñ class}`), tipar na bronze derrubaria a carga inteira. Guardar como string garante que a bronze é sempre uma cópia fiel; a decisão sobre o valor inválido fica para a silver.

### Na silver

| coluna | valor | tipo | transformação |
| --- | --- | --- | --- |
| `cod_municipio` | `"261160"` | string | validado com 6 dígitos |
| `cod_uf` | `"26"` | string | 2 primeiros dígitos do município |
| `cnae_classe` | `"47113"` | string | validado com 5 dígitos |
| `cnae_divisao` | `"47"` | string | 2 primeiros dígitos da classe |
| `sexo` | `2` | int | `try_cast` |
| `vinculo_ativo` | `true` | boolean | `== "1"` |
| `remun_dezembro_nom` | `2350.75` | decimal(18,2) | vírgula → ponto, `try_cast` |
| `remun_dezembro_sm` | `1.94` | decimal(18,2) | idem |

Uma linha continua sendo uma linha: a silver limpa valores, mas não descarta registros.

### Na gold

A linha deixa de existir individualmente. Ela é somada com todos os vínculos ativos de PE em 2022 e contribui para uma linha de `gold_emprego_uf_ano`:

| ano | cod\_uf | uf | qtd\_vinculos | remun\_media\_dez\_sm |
| --- | --- | --- | --- | --- |
| 2022 | 26 | PE | (soma dos vínculos ativos) | (média em salários mínimos) |

Ela também entra em `gold_gap_sexo_uf_ano` (como `sexo = 2`, feminino, a confirmar no dicionário) e em `gold_top_cnae_uf_ano` (divisão 47).

### O que o exemplo ensina

1. Cada camada só faz o seu trabalho: a bronze não interpreta, a silver não agrega, a gold não limpa.
2. Uma coluna nominal (R$) e outra em salário mínimo (SM) convivem; só a SM é comparável entre anos (Apêndice A, item 7 do guia).
3. Código com zero à esquerda fica string desde a bronze até a gold.

## 8. Armadilhas, diagnóstico e soluções

Os erros desta aula são de desenho, não de código. Eles custam pouco agora e muito depois, porque se espalham por todas as camadas.

| Armadilha | Sintoma que aparece mais tarde | Causa | Solução |
| --- | --- | --- | --- |
| Regra de negócio na bronze | Reprocessar a bronze muda números da gold sem que a origem mude | Filtros ou conversões feitos cedo demais | Bronze só normaliza nomes; toda interpretação vai para a silver |
| Tipar na bronze | Carga de um ano inteiro falha por um valor inválido | Cast estrito em dado público sujo | Bronze toda string; silver com `try_cast` (Aula 10) |
| Silver que filtra linhas | Contagem silver ≠ bronze; totais da gold não batem com a fonte | Descartar inválidos em vez de anulá-los | Inválido vira NULL; a checagem de contagem pega o desvio (Aula 16) |
| Gold genérica ("tabela de tudo") | Tabela gold gigante, lenta e que ninguém sabe usar | Gold desenhada a partir dos dados, não das perguntas | Uma tabela por pergunta, como as cinco da Aula 13 |
| Confundir vínculo com pessoa | Relatório diz "X trabalhadores" | Grão não declarado | Contrato de camada com grão explícito |
| Comparar R$ nominal entre anos | Crescimento salarial inflado pela inflação e pelo reajuste do mínimo | Uso de `*_nom` em série histórica | Usar `*_sm` em comparações entre anos |
| Sem idempotência | Dados duplicados após reexecutar um ano | `append` em vez de substituir a partição | `replaceWhere` por ano (Aulas 10 e 14) |
| Lake sem formato de tabela | Arquivos parciais após falha; schema quebrado silenciosamente | Parquet puro | Delta Lake (ADR-004) |
| Decisões não registradas | Equipe rediscute ou reverte escolhas | Ausência de ADRs | `docs/decisoes.md` mantido a cada mudança |

### Como diagnosticar um problema de arquitetura

<span class="rl-complemento">Complemento didático</span> Quando um número da gold parece errado, percorra as camadas de trás para frente:

1. **Gold:** a agregação usa o filtro certo (ex.: só vínculos ativos)? A coluna certa (`_sm` ou `_nom`)?
2. **Silver:** a contagem bate com a bronze? Quantos NULL surgiram na coluna usada?
3. **Bronze:** a contagem bate com o número de linhas do arquivo? Todas as regiões do ano foram carregadas?
4. **Landing:** o arquivo é a versão final ou parcial daquele ano? (Apêndice A, item 3 do guia.)

A camada em que o número "desvia" pela primeira vez é onde está o erro. Essa busca só é possível porque cada camada tem uma responsabilidade única.

## 9. Boas práticas para produção

1. **A landing é a única fonte imutável.** Bronze, silver e gold são reconstruíveis; faça backup da landing e do código, não necessariamente das camadas derivadas (guia, Parte [1.2](../guia/parte-01.md#parte-1-2): a landing é a fonte da verdade).
2. **Uma regra de ouro por camada,** escrita no contrato. Se uma transformação não cabe na regra da camada, ela está no lugar errado.
3. **Configuração fora do código.** Caminhos, credenciais e recursos vêm de variáveis de ambiente (metodologia 12-Factor, Parte [7.1](../guia/parte-07.md#parte-7-1) do guia; detalhado na Aula 05).
4. **Versões fixas.** Nunca `latest` em imagens ou dependências: o build de hoje precisa ser igual ao de daqui a um ano (Parte [4.2](../guia/parte-04.md#parte-4-2); Aulas 02 e 06).
5. **Centralize o formato de tabela.** Toda leitura e escrita Delta passa por um único módulo (`src/delta_io.py`, Aula 10). Trocar Delta por Iceberg vira mudança de um arquivo.
6. **Toda decisão nova vira ADR,** inclusive as que revertem uma anterior.
7. **Grão explícito em toda tabela.** <span class="rl-complemento">Complemento didático</span> Escreva o grão no contrato e no nome ou descrição da tabela (ex.: `gold_emprego_uf_ano` já diz ano × UF).
8. **Comece pequeno.** O guia recomenda 1 ano e 1 região (ex.: 2022 + Nordeste) antes de escalar para 2019–último ano publicado.

## 10. Riscos: segurança, desempenho, custos e integridade

| Tipo | Risco | Como a arquitetura do curso mitiga | Onde é tratado |
| --- | --- | --- | --- |
| Segurança | Credenciais no repositório | `.env` fora do Git; `.env.example` com valores fictícios | Aulas 03 e 05 |
| Segurança | Serviços expostos na rede | Portas publicadas só em `127.0.0.1` | Aula 03 |
| Segurança | Aplicação com poder de administrador | Usuário do MinIO só com acesso ao bucket `rais` | Aula 04 |
| Desempenho | Ler CSV repetidamente | Bronze em Parquet colunar via Delta | Aula 11 |
| Desempenho | Muitos arquivos pequenos | `OPTIMIZE` e `coalesce` na gold | Aulas 13 e 14 |
| Desempenho | Memória insuficiente na máquina | Limites de container e tuning do Spark | Aula 15 |
| Custo | Disco cheio com `.txt` extraído | `raw` é temporária (`--limpar-raw`) | Aulas 11 e 14 |
| Custo | Versões antigas acumulando arquivos | `VACUUM` com retenção de 168 h | Aula 14 |
| Integridade | Escrita interrompida deixa dado parcial | Transações ACID do Delta | Aula 10 |
| Integridade | Reexecução duplica dados | `replaceWhere` por ano; gold recriada | Aulas 10 e 14 |
| Integridade | Schema muda entre anos | Bronze string + `mergeSchema` | Aula 11 |
| Integridade | Conclusões erradas sobre pessoas | Grão "vínculo" no contrato | Aulas 09 e 13 |

**Sobre os dados em si.** <span class="rl-complemento">Complemento didático</span> Os microdados da RAIS são públicos e anonimizados, então o risco de vazamento de dados pessoais é baixo. Isso não dispensa os cuidados acima: o mesmo projeto, reaproveitado com dados internos de uma empresa, herdaria qualquer descuido de segurança.

**Custo no on-premises.** <span class="rl-complemento">Complemento didático</span> Sem nuvem, o custo é disco, memória e tempo de máquina. O principal consumidor de disco é o `.txt` extraído; o Parquet comprimido da bronze ocupa uma fração dele (você mede isso no exercício 4 da Aula 11).

## 11. Validação e critérios de conclusão

A aula está concluída quando todos os itens abaixo estão marcados.

- [ ] Consigo explicar, sem consultar, a diferença entre data warehouse, data lake e lakehouse, com uma vantagem e uma desvantagem de cada.
- [ ] Consigo explicar por que Parquet sozinho não oferece transações e o que o `_delta_log/` acrescenta.
- [ ] Sei a regra de ouro de cada uma das cinco camadas (landing, raw, bronze, silver, gold).
- [ ] `docs/decisoes.md` tem os seis ADRs, cada um com contexto, alternativa e pelo menos uma consequência negativa.
- [ ] Os três contratos de camada declaram grão, tipos e garantias.
- [ ] Sei explicar por que a contagem da silver deve ser igual à da bronze.
- [ ] Sei explicar por que séries históricas usam colunas em salário mínimo.

**Autoteste rápido.** <span class="rl-complemento">Complemento didático</span> Leia o seu `docs/decisoes.md` como se fosse outra pessoa. Para cada ADR, pergunte: "em que situação esta decisão deixaria de valer?". Se a resposta não estiver no campo Contexto, reescreva-o.

### Validação na plataforma

<span class="rl-complemento">Complemento didático</span> Check automático desta aula, em `labcheck/test_aula01.py`. Ele só lê o repositório; roda dentro do container ou no host.

```python
"""Check da Aula 01: decisões de arquitetura registradas."""
from pathlib import Path

DECISOES = Path("docs/decisoes.md")


def test_a01_adrs_registrados():
    assert DECISOES.exists(), "docs/decisoes.md não existe. Faça o tutorial da Aula 01."
    texto = DECISOES.read_text(encoding="utf-8")
    qtd = texto.count("## ADR-")
    assert qtd >= 6, f"{qtd} ADRs encontrados; a Aula 01 pede os 6 do guia."
    assert "## Contratos de camada" in texto, "Faltam os contratos de camada (passo 4)."
```

- **Como rodar:** `make check AULA=01` (depois do esqueleto da plataforma).
- **Limite:** o check confere que os ADRs e os contratos existem, não a qualidade do texto; essa parte fica no checklist acima.
- **Contribuição ao projeto:** `docs/decisoes.md` é a referência das decisões; as Aulas 02 (desafio 3) e 15 acrescentam ADRs a ele.

## 12. Exercícios, revisão e desafios

### Exercícios práticos

1. Escreva um sétimo ADR para uma decisão que o guia toma implicitamente: "a gold é recalculada inteira a cada execução, em vez de incremental". Liste uma vantagem e uma desvantagem.
2. Para cada linha da tabela de armadilhas (seção 8), aponte em qual contrato de camada (seção 5, passo 4) existe uma cláusula que a previne. Se alguma armadilha não tiver cláusula, escreva-a.
3. Refaça o exemplo da seção 7 para um vínculo com `idade = 150` e `cnae = "4711"` (4 dígitos). O que acontece com cada valor na silver? (Dica: Parte [10.2](../guia/parte-10.md#parte-10-2) do guia.)

### Perguntas de revisão

1. Por que a bronze guarda tudo como string, se a silver vai converter os tipos de qualquer jeito?
2. Qual camada você recalcula se descobrir um erro na regra de validação de idade? E se descobrir que um ano foi baixado na versão parcial?
3. O que significa "o Delta recusa a gravação" no contexto de schema enforcement, e por que isso é bom?
4. Por que a raw não fica no MinIO?
5. Em que situação você trocaria Delta por Iceberg?
6. Uma pessoa com dois empregos formais em 2022 aparece quantas vezes na silver? E na contagem `qtd_vinculos` da gold?

**Respostas sugeridas** (tente responder antes de ler):

1. Porque o schema muda entre anos e há valores inválidos; tipar cedo derruba a carga e mistura interpretação com cópia.
2. Erro de validação: silver e gold (a bronze está correta). Versão parcial: refazer desde a landing, com o arquivo final.
3. A escrita com schema incompatível é rejeitada; isso impede corrupção silenciosa da tabela.
4. Porque é temporária e reconstruível a partir da landing; não precisa de versionamento (ADR-005).
5. Quando várias engines diferentes precisarem ler e escrever as mesmas tabelas.
6. Duas vezes, se os dois vínculos estiverem ativos em 31/12; e conta como 2 vínculos na gold.

Se errou alguma, releia a seção correspondente desta aula antes de seguir.

### Desafios

1. **Arquitetura alternativa.** Desenhe como seria o mesmo projeto com Iceberg e catálogo REST. Que novo serviço aparece no Docker Compose? Que ADRs mudariam?
2. **Medallion ou não.** Escreva um parágrafo defendendo uma arquitetura com só duas camadas (raw e curated) para a RAIS, e outro refutando. Qual argumento é mais forte?
3. **Contrato verificável.** Para cada cláusula do contrato da silver, escreva em português como você testaria automaticamente se ela está sendo cumprida. Guarde a lista: ela vira código na Aula 16.

## 13. Referências cruzadas

| Tema desta aula | Aprofundado em | Fonte no guia |
| --- | --- | --- |
| Docker, containers e imagem | Aula 02 | Parte [2](../guia/parte-02.md), [4.4](../guia/parte-04.md#parte-4-4) |
| Docker Compose e a infraestrutura de três serviços | Aula 03 | Parte [2.3](../guia/parte-02.md#parte-2-3), [4.6](../guia/parte-04.md#parte-4-6)–[4.8](../guia/parte-04.md#parte-4-8) |
| MinIO, S3A e menor privilégio | Aula 04 | Parte [4.1](../guia/parte-04.md#parte-4-1), [4.5](../guia/parte-04.md#parte-4-5) |
| `docs/decisoes.md` no repositório e configuração 12-Factor | Aula 05 | Parte [3](../guia/parte-03.md), [7.1](../guia/parte-07.md#parte-7-1)–[7.2](../guia/parte-07.md#parte-7-2) |
| Parquet, partições e lazy evaluation | Aulas 07 e 08 | Parte [5](../guia/parte-05.md) |
| Grão "vínculo" e colunas da RAIS | Aula 09 | Parte [6](../guia/parte-06.md) |
| Formato de tabela e `_delta_log` | Aula 10 | Parte [7.4](../guia/parte-07.md#parte-7-4), [13.1](../guia/parte-13.md#parte-13-1) |
| Bronze | Aula 11 | Parte [9](../guia/parte-09.md) |
| Silver | Aula 12 | Parte [10](../guia/parte-10.md) |
| Gold e perguntas de negócio | Aula 13 | Parte [11](../guia/parte-11.md) |
| Idempotência e operações Delta | Aula 14 | Parte [12](../guia/parte-12.md), [13.2](../guia/parte-13.md#parte-13-2) |
| Desempenho | Aula 15 | Parte [14](../guia/parte-14.md) |
| Contratos como testes | Aula 16 | Parte [15](../guia/parte-15.md) |
| Termos (ACID, idempotência, medallion, grão) | Apêndice C — Glossário | Apêndice C |
| Armadilhas da RAIS | Apêndice A | Apêndice A |


## Checks automáticos

```bash
.venv-host/bin/pytest -v labcheck/test_aula01.py   # ou: make check AULA=01
```

Arquivo: `labcheck/test_aula01.py`. Cada execução grava o resultado em `progress/historico.jsonl`; depois rode `make progresso` para atualizar a página [Progresso](../progresso.md).

| Check | O que verifica |
| --- | --- |
| `a01_adrs_registrados` | adrs registrados |
