---
aula: 9
titulo: "O domínio RAIS: microdados, dicionário e armadilhas"
origem: ['Guia Parte 6', 'Guia Apêndice A']
depende_de: [5]
checks: ['a09_7z_na_landing', 'a09_7z_contem_txt', 'a09_dicionario_preenchido']
---

# Aula 09 — O domínio RAIS: microdados, dicionário e armadilhas

<!-- Página GERADA por scripts/gerar_curso.py. Edite aulas.yml e curso/conteudo/. -->

<div class="rl-aula" data-aula="9" data-onde="container" data-lab=""></div>

| | |
| --- | --- |
| Origem no guia | Guia Parte [6](../guia/parte-06.md), Guia [Apêndice A](../guia/apendice-a.md) |
| Depende de | [Aula 05](aula-05.md) |
| Entregas | `staging/landing/<ano>/*.7z`, `docs/dicionario.md` |
| Onde os checks rodam | Container spark |

Antes de processar a RAIS, é preciso entender o que cada linha representa, como os arquivos são publicados e onde estão as armadilhas. Ao final desta aula você terá o primeiro `.7z` na landing e o `docs/dicionario.md` preenchido.

## 1. Objetivos e pré-requisitos

1. Explicar o que é a RAIS e qual o grão dos microdados de vínculos.
2. Descrever o formato dos arquivos (compactação, separador, encoding, decimal, códigos de "ignorado").
3. Ler o dicionário oficial e documentar as colunas usadas pelo projeto.
4. Reconhecer as armadilhas que afetam análises históricas.
5. Colocar o primeiro arquivo real na landing.

**Pré-requisitos:** Aula 05 (estrutura e `docs/`); espaço em disco para os `.7z` (vários GB quando extraídos).

## 2. Contextualização

Engenharia de dados sem conhecimento do domínio produz tabelas tecnicamente corretas e analiticamente erradas. Na RAIS, o erro mais grave — chamar vínculos de "trabalhadores" — não é de código: é de entendimento. Esta aula vem antes da bronze porque todas as decisões da silver e da gold dependem dela.

## 3. Fundamentação teórica (guia, Parte [6.1](../guia/parte-06.md#parte-6-1))

### 3.1 O que é a RAIS

A **RAIS** (Relação Anual de Informações Sociais) é o registro anual dos vínculos formais de trabalho, mantido pelo Ministério do Trabalho e Emprego (MTE).

### 3.2 Grão: vínculo, não pessoa

- Os microdados públicos são **anonimizados**: não há CPF nem identificador do trabalhador.
- **Cada linha é um vínculo, não uma pessoa**, e não é possível deduplicar pessoas.
- Uma pessoa com dois empregos formais aparece duas vezes.

Consequência para o projeto: a silver não deduplica (não existe chave para isso), e a gold escreve "vínculos", nunca "trabalhadores" (contrato de camada, Aula 01).

### 3.3 Bases disponíveis

| Base | Grão | Uso no curso |
| --- | --- | --- |
| Vínculos | Um vínculo por linha | Base principal |
| Estabelecimentos | Um estabelecimento por linha | Evolução (Apêndice G) |

### 3.4 Formato dos arquivos de vínculos

| Característica | Valor | Onde o projeto trata |
| --- | --- | --- |
| Compactação | `.7z` | Ingestão (`py7zr`, Aula 11) |
| Divisão | Por região, ex.: `RAIS_VINC_PUB_NORDESTE.7z`, `..._SP.7z`, `..._NI.7z` (NI = não identificado) | Bronze lê todos os `.txt` do ano |
| Separador | `;` | Bronze |
| Encoding | `latin-1` (ISO-8859-1) | Bronze |
| Decimal | Vírgula (`1234,56`) | Silver (`to_decimal`) |
| Cabeçalho | Com acentos e espaços (`Vl Remun Média Nom`) | Bronze (`normalize_columns`) |
| "Ignorado" | Códigos que variam por coluna (`-1`, `0`, `{ñ class}`) | Silver (vira NULL) |

O guia avisa: confira os nomes reais dos arquivos de cada ano.

### 3.5 eSocial, versão parcial e final

- A partir do ano-base 2019, parte das empresas passou a declarar pelo **eSocial**, e a cobertura foi migrando por grupos de empresas ao longo dos anos. Leia as notas técnicas de cada ano antes de comparar séries (guia, Parte [6.1](../guia/parte-06.md#parte-6-1) e Apêndice A).
- Alguns anos tiveram divulgação **parcial** antes da **final**. Use a final e registre a escolha (Apêndice A).

### 3.6 Nominal × salário mínimo

R$ nominal não é comparável entre anos (inflação e reajuste do mínimo). Para séries históricas, use as colunas em **salários mínimos** (`*_sm`) (guia, Parte [11.1](../guia/parte-11.md#parte-11-1) e Apêndice A).

### 3.7 Qual é o último ano disponível?

O guia usa `ANOS = 2019–2024`. O site do MTE tem material de apresentação identificado como "RAIS ano-base 2025"; confirme se os **microdados** desse ano já estão publicados e, se estiverem, ajuste `ANOS` em `config/settings.py` (Aula 05).

## 4. Arquitetura e fluxo

```
 gov.br/trabalho-e-emprego (RAIS / microdados)
   ├─ dicionário/layout do ano ──▶ docs/dicionario.md (você documenta)
   └─ RAIS_VINC_PUB_<REGIAO>.7z ──▶ staging/landing/<ano>/   (fonte da verdade, nunca editar)
                                         │  Aula 11: extrair
                                         ▼
                                   staging/raw/<ano>/*.txt  (temporário)
```

## 5. Tutorial (guia, Parte [6.2](../guia/parte-06.md#parte-6-2))

### Passo 1 — Baixar o dicionário e um arquivo

1. Na página de estatísticas do trabalho do MTE (`gov.br/trabalho-e-emprego`, seção RAIS/microdados), baixe o **dicionário/layout** de vínculos do ano escolhido.
2. Baixe **um** arquivo regional de **um** ano. Sugestão do guia: **2022 + Nordeste** (menor que SP).
3. Coloque o `.7z` em `staging/landing/2022/` (no host, a pasta `staging/` do projeto; no container, `/staging/landing/2022/`).

```bash
mkdir -p staging/landing/2022
ls -lh staging/landing/2022/
sha256sum staging/landing/2022/*.7z > staging/landing/2022/SHA256SUMS
```

O `sha256sum` registra uma "impressão digital" do arquivo. Se um dia o arquivo for baixado de novo, comparar os hashes diz se o MTE publicou uma versão diferente (ex.: parcial → final).

### Passo 2 — Documentar as colunas em `docs/dicionario.md`

Os nomes estão na forma **normalizada** pelo código do projeto (minúsculas, sem acento, `_` no lugar de espaços e símbolos). Confira cada uma no dicionário oficial do seu ano:

| Coluna normalizada | Significado | Tipo na silver | Observação |
| --- | --- | --- | --- |
| `municipio` | Código IBGE (6 dígitos) do município | string | 2 primeiros dígitos = UF |
| `cnae_2_0_classe` | Atividade econômica (5 dígitos) | string | 2 primeiros = divisão |
| `cbo_ocupacao_2002` | Ocupação | string | **zeros à esquerda importam** |
| `vinculo_ativo_31_12` | Ativo em 31/12 | boolean | geralmente `1`/`0` |
| `sexo_trabalhador` | Sexo | int | confira os códigos |
| `escolaridade_apos_2005` | Grau de instrução | int | códigos 1–11 |
| `raca_cor` | Raça/cor | int | confira os códigos |
| `idade` | Idade | int |  |
| `tempo_emprego` | Tempo de emprego (meses) | decimal | vírgula decimal |
| `mes_desligamento` | Mês do desligamento | int | `0` = não desligado (confirme) |
| `motivo_desligamento` | Motivo | int |  |
| `tamanho_estabelecimento` | Faixa de tamanho | int |  |
| `natureza_juridica` | Natureza jurídica | string |  |
| `vl_remun_dezembro_nom` | Remuneração de dezembro (R$ nominal) | decimal |  |
| `vl_remun_media_nom` | Remuneração média do ano (R$ nominal) | decimal |  |
| `vl_remun_dezembro_sm` | Remuneração de dezembro em salários mínimos | decimal | **comparável entre anos** |
| `vl_remun_media_sm` | Remuneração média em salários mínimos | decimal | **comparável entre anos** |

Acrescente ao arquivo, por coluna: o nome original no cabeçalho do seu ano, os códigos de "ignorado" e a decisão tomada. Exemplo:

```markdown
## vl_remun_dezembro_nom
- Nome original (2022): Vl Remun Dezembro Nom
- Ignorado: (preencher conforme o dicionário)
- Decisão: valor inválido vira NULL na silver; 0 = (decidir no exercício 5 da Aula 12)
```

## 6. Funcionamento e resultados esperados

| Passo | Esperado |
| --- | --- |
| Download | Um `.7z` de alguns centenas de MB a poucos GB (varia por região e ano; confira) |
| Landing | Arquivo em `staging/landing/2022/`, fora do Git (Aula 05) |
| Dicionário | Todas as colunas da tabela presentes, com nome original e códigos de ignorado |

## 7. Exemplos práticos

**Exemplo 1 — Por que CBO é texto.** Um código como `"012345"` convertido para número vira `12345`; ao juntar com uma tabela de ocupações, o join falha silenciosamente. Por isso códigos com zero à esquerda ficam `string` da bronze à gold (guia, Parte [10.1](../guia/parte-10.md#parte-10-1)).

**Exemplo 2 — UF a partir do município.** `261160` → UF `26` (PE). A silver deriva `cod_uf` assim, e a gold junta com `dim_uf` (Aulas 10 e 12).

**Exemplo 3 — Estoque × fluxo.** Indicadores de **estoque** (quantos empregos existem) usam vínculos ativos em 31/12; a taxa de desligamento usa todos os vínculos do ano (gold, Aula 13).

## 8. Armadilhas (guia, [Apêndice A](../guia/apendice-a.md))

1. **O schema muda entre anos.** Por isso bronze toda string com `mergeSchema`, `col_or_null` e colunas obrigatórias.
2. **eSocial a partir do ano-base 2019** pode afetar comparações históricas.
3. **Versão parcial × final.** Use a final e registre.
4. **Arquivo NI:** inclua para o total nacional; não tem UF válida.
5. **"Ignorado" varia por coluna.** Decida coluna a coluna e documente.
6. **Zeros à esquerda:** CBO, CNAE e município são string.
7. **Nominal × salário mínimo:** série histórica usa `*_sm`.
8. **Vínculo ≠ pessoa.**
9. **Disco:** apague `raw` após a bronze (`--limpar-raw`).
10. **Encoding:** `Munic�pio` indica encoding errado.

| Sintoma no pipeline | Armadilha provável |
| --- | --- |
| Total de um ano muito abaixo dos vizinhos | Versão parcial, região faltando ou mudança de cobertura |
| UF nula na gold | Arquivo NI ou município inválido |
| Coluna obrigatória ausente | Nome diferente naquele ano |
| Crescimento salarial "alto demais" | Série em R$ nominal |

## 9. Boas práticas

1. Começar com 1 ano e 1 região (guia).
2. Documentar cada decisão sobre o dado em `docs/dicionario.md`.
3. Guardar o `.7z` original intocado; ele é a fonte da verdade.
4. Registrar data do download e hash do arquivo.

## 10. Riscos

| Tipo | Risco | Mitigação |
| --- | --- | --- |
| Integridade analítica | Conclusões sobre pessoas a partir de vínculos | Grão no contrato; rótulos "vínculos" |
| Integridade | Misturar versão parcial e final | Hash e data no dicionário |
| Custo | Disco cheio com `.txt` | Apagar `raw` após a bronze |
| Privacidade | Microdados são anonimizados, mas cruzamentos muito finos podem ser sensíveis | Publicar só agregados (gold) |

## 11. Laboratório e validação na plataforma

**Contribuição ao projeto:** a landing é a entrada do pipeline; o dicionário orienta a silver.

`labcheck/test_aula09.py` (container):

```python
"""Checks da Aula 09: arquivo real na landing e dicionário documentado."""
from pathlib import Path

import py7zr

from config.settings import LANDING

OBRIGATORIAS = ["municipio", "vinculo_ativo_31_12", "vl_remun_dezembro_nom", "vl_remun_dezembro_sm"]


def arquivos(ano):
    return sorted((LANDING / str(ano)).glob("*.7z"))


def test_a09_7z_na_landing(ano):
    assert arquivos(ano), f"Nenhum .7z em {LANDING / str(ano)}. Faça o passo 1."


def test_a09_7z_contem_txt(ano):
    for arq in arquivos(ano):
        with py7zr.SevenZipFile(arq, "r") as z:
            nomes = z.getnames()
        assert any(n.lower().endswith(".txt") for n in nomes), f"{arq.name} não contém .txt: {nomes[:5]}"


def test_a09_dicionario_preenchido():
    caminho = Path("docs/dicionario.md")
    assert caminho.exists(), "docs/dicionario.md não existe (passo 2)."
    texto = caminho.read_text(encoding="utf-8")
    faltando = [c for c in OBRIGATORIAS if c not in texto]
    assert not faltando, f"Colunas não documentadas: {faltando}"
```

- `getnames()` lista o conteúdo do `.7z` sem extrair — barato.
- Rode com `make check AULA=09 ANO=2022`.

**Checklist manual:**

- [ ] li as notas técnicas do ano escolhido
- [ ] sei explicar por que vínculo ≠ pessoa
- [ ] registrei versão (parcial/final), data e hash do arquivo.

## 12. Exercícios, revisão e desafios

**Exercícios**

1. No dicionário oficial, encontre os códigos de `sexo_trabalhador` e `escolaridade_apos_2005` e confira com as dimensões que serão criadas na Aula 10.
2. Liste os arquivos disponíveis para 2022 e anote o tamanho de cada região.

**Revisão**

1. Por que não dá para deduplicar pessoas?
2. Qual coluna usar para comparar remuneração entre 2019 e 2024?
3. O que é o arquivo NI e quando incluí-lo?
4. Por que a cobertura pode variar a partir de 2019?

**Respostas sugeridas:** (1) dados anonimizados, sem identificador; (2) as colunas `*_sm`; (3) vínculos sem identificação de localidade, necessário para o total nacional; (4) a migração da declaração para o eSocial por grupos de empresas.

**Desafio:** escreva em `docs/decisoes.md` um ADR "Quais anos e versões entram no projeto", citando as notas técnicas que você leu.

## 13. Referências cruzadas

| Tema | Onde |
| --- | --- |
| Contrato de grão "vínculo" | Aula 01 |
| `ANOS` em `settings.py` | Aula 05 |
| `normalize_columns`, `to_decimal`, dimensões | Aula 10 |
| Extração e bronze | Aula 11 |
| Tipagem e validação | Aula 12 |
| Indicadores e rótulos | Aula 13 |
| Lista completa de armadilhas | Apêndice A |


## Checks automáticos

```bash
make check AULA=09 ANO=2022
```

Arquivo: `labcheck/test_aula09.py`. Cada execução grava o resultado em `progress/historico.jsonl`; depois rode `make progresso` para atualizar a página [Progresso](../progresso.md).

| Check | O que verifica |
| --- | --- |
| `a09_7z_na_landing` | 7z na landing |
| `a09_7z_contem_txt` | 7z contem txt |
| `a09_dicionario_preenchido` | dicionario preenchido |
