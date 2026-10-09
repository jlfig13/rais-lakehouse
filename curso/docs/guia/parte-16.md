<!-- Página GERADA de docs/guia/rais-lakehouse-guia.md -->

# Parte [16](parte-16.md) — Boas práticas de GitHub

## 16.1 Commits (Conventional Commits) { #parte-16-1 }

Formato: `tipo(escopo opcional): descrição no imperativo`

| Tipo | Uso | Exemplo |
|---|---|---|
| `feat` | Nova funcionalidade | `feat(gold): tabela de gap salarial por sexo` |
| `fix` | Correção | `fix(silver): tratar CNAE com menos de 5 dígitos` |
| `docs` | Documentação | `docs: explicar tuning no README` |
| `refactor` | Mudança interna sem alterar comportamento | `refactor: centralizar escrita Delta` |
| `test` | Testes | `test: cobrir to_decimal` |
| `chore` | Manutenção | `chore: atualizar delta-spark` |
| `perf` | Performance | `perf: broadcast nas dimensões` |

**Commits pequenos e frequentes.** Um commit deve fazer **uma** coisa. Isso facilita revisar, entender o histórico e desfazer.

## 16.2 Branches e Pull Requests { #parte-16-2 }

```bash
git switch -c feat/gold-faixa-etaria       # uma branch por funcionalidade
# ...trabalho e commits...
git push -u origin feat/gold-faixa-etaria  # depois abra um PR no GitHub
```
- A `main` está sempre funcionando.
- Mesmo sozinho, use PRs: o CI roda antes do merge e o PR documenta o porquê da mudança.
- Prefixos: `feat/`, `fix/`, `docs/`, `refactor/`.

## 16.3 README.md (a vitrine do projeto) { #parte-16-3 }

Estrutura recomendada:
```markdown
# RAIS Lakehouse

Lakehouse open source on-premises para os microdados da RAIS (2019–2024),
com PySpark, Delta Lake e MinIO orquestrados por Docker Compose.

## Arquitetura
(diagrama + tabela das camadas)

## Stack
PySpark 3.5 · Delta Lake 3.2 · MinIO · Docker Compose · pytest · GitHub Actions

## Como rodar
1. `cp .env.example .env` e preencha
2. `make up`
3. Baixe os .7z para `staging/landing/<ano>/`
4. `make pipeline ANOS=2022`

## Tabelas gold
(o que cada uma responde)

## Decisões técnicas
Ver `docs/decisoes.md`

## Principais aprendizados / resultados
(2 ou 3 achados dos dados + 1 gráfico)

## Limitações
(eSocial, vínculos ≠ pessoas, versão parcial...)

## Fonte dos dados
RAIS/MTE — microdados públicos.
```
**Para portfólio**, as seções que mais pesam são **Decisões técnicas**, **Resultados** (um gráfico vale muito) e **Limitações**. Elas mostram maturidade.

## 16.4 Outros cuidados { #parte-16-4 }

- **LICENSE:** escolha uma (MIT é a mais simples) para deixar claro como outros podem usar o código.
- **Tags de versão:** marque marcos com `git tag v0.1.0 && git push --tags` (ex.: v0.1 = bronze/silver, v0.2 = gold).
- **Segredos:** se um `.env` for commitado por engano, **troque as senhas**. Apagar o commit não basta, porque o histórico guarda o conteúdo.
- **Dependências:** atualize de propósito, uma de cada vez, com o CI verde.
- **Issues:** use as *issues* do GitHub como backlog (ex.: "Adicionar RAIS Estabelecimentos").

---
