# Dicionário de dados — RAIS Vínculos

Origem: Guia Parte 6 / Aula 09 (preenchimento) e Aula 12 (decisões da silver).

> **Este arquivo é um modelo.** Os nomes abaixo são os nomes *normalizados* que o código
> usa (`src/silver.py`). Confira cada um no dicionário oficial publicado com os microdados
> do ano que você baixou e preencha as colunas "Nome original" e "Descrição oficial".
> O check `a09_dicionario_preenchido` só verifica se as colunas obrigatórias estão listadas;
> a conferência com o documento oficial é sua.

| Nome normalizado | Nome original (arquivo do ano) | Descrição oficial | Tipo na silver | Decisão de limpeza |
| --- | --- | --- | --- | --- |
| municipio | _preencher_ | _preencher_ | string (`cod_municipio`) | 6 dígitos; senão NULL |
| vinculo_ativo_31_12 | _preencher_ | _preencher_ | boolean (`vinculo_ativo`) | "1" → true |
| vl_remun_dezembro_nom | _preencher_ | _preencher_ | decimal(18,2) | vírgula decimal; inválido → NULL |
| vl_remun_dezembro_sm | _preencher_ | _preencher_ | decimal(18,2) | vírgula decimal; inválido → NULL |

## Armadilhas registradas

- _Anote aqui o que encontrar (encoding, códigos de "ignorado", mudanças de layout entre anos)._
