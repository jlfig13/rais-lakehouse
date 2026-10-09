<!-- Página GERADA de docs/guia/rais-lakehouse-guia.md -->

# Parte [6](parte-06.md) — Conhecendo a RAIS

## 6.1 Conceito { #parte-6-1 }

A **RAIS** (Relação Anual de Informações Sociais) é o registro anual dos vínculos formais de trabalho, mantido pelo Ministério do Trabalho e Emprego.

- Os microdados públicos são **anonimizados**: não há CPF nem identificador do trabalhador. **Cada linha é um vínculo, não uma pessoa**, e não é possível deduplicar pessoas.
- Há duas bases: **vínculos** (usaremos) e **estabelecimentos** (fica como evolução).
- A partir do ano-base 2019, parte das empresas passou a declarar pelo **eSocial**, e a cobertura foi migrando por grupos de empresas ao longo dos anos. Leia as notas técnicas de cada ano antes de comparar séries.

**Formato dos arquivos de vínculos**
- Compactados em `.7z`, **divididos por região** (nomes parecidos com `RAIS_VINC_PUB_NORDESTE.7z`, `..._SP.7z`, `..._NI.7z`; "NI" = não identificado). Confira os nomes reais de cada ano.
- Separador `;`, encoding `latin-1` (ISO-8859-1) e decimal com **vírgula** (`1234,56`).
- Cabeçalho com acentos e espaços (ex.: `Vl Remun Média Nom`).
- Valores "ignorado" representados por códigos que variam por coluna (`-1`, `0`, `{ñ class}`...).

## 6.2 Prática { #parte-6-2 }

1. Na página de estatísticas do trabalho do MTE (`gov.br/trabalho-e-emprego`, seção RAIS/microdados), baixe:
   - o **dicionário/layout** de vínculos do ano escolhido;
   - **um** arquivo regional de **um** ano (sugestão: 2022 + Nordeste).
2. Coloque o `.7z` em `staging/landing/2022/`.
3. Documente em `docs/dicionario.md` as colunas usadas. Os nomes abaixo estão na forma **normalizada** pelo nosso código (minúsculas, sem acento, `_` no lugar de espaços e símbolos):

| Coluna normalizada | Significado | Tipo na silver | Observação |
|---|---|---|---|
| `municipio` | Código IBGE (6 dígitos) do município | string | 2 primeiros dígitos = UF |
| `cnae_2_0_classe` | Atividade econômica (5 dígitos) | string | 2 primeiros = divisão |
| `cbo_ocupacao_2002` | Ocupação | string | **zeros à esquerda importam** |
| `vinculo_ativo_31_12` | Ativo em 31/12 | boolean | geralmente `1`/`0` |
| `sexo_trabalhador` | Sexo | int | confira os códigos |
| `escolaridade_apos_2005` | Grau de instrução | int | códigos 1–11 |
| `raca_cor` | Raça/cor | int | confira os códigos |
| `idade` | Idade | int | |
| `tempo_emprego` | Tempo de emprego (meses) | decimal | vírgula decimal |
| `mes_desligamento` | Mês do desligamento | int | `0` = não desligado (confirme) |
| `motivo_desligamento` | Motivo | int | |
| `tamanho_estabelecimento` | Faixa de tamanho | int | |
| `natureza_juridica` | Natureza jurídica | string | |
| `vl_remun_dezembro_nom` | Remuneração de dezembro (R$ nominal) | decimal | |
| `vl_remun_media_nom` | Remuneração média do ano (R$ nominal) | decimal | |
| `vl_remun_dezembro_sm` | Remuneração de dezembro em salários mínimos | decimal | **comparável entre anos** |
| `vl_remun_media_sm` | Remuneração média em salários mínimos | decimal | **comparável entre anos** |

### Checkpoint
Você tem o `.7z` em `staging/landing/2022/`, o dicionário em mãos e o `docs/dicionario.md` preenchido.

---
