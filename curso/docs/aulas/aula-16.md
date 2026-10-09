---
aula: 16
titulo: "Qualidade, testes, CI e boas práticas de GitHub"
origem: ['Guia Parte 15', 'Guia Parte 16']
depende_de: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
checks: ['a16_testes_passam', 'a16_lint_passa', 'a16_workflow_ci', 'a16_readme_completo', 'a16_licenca']
---

# Aula 16 — Qualidade, testes, CI e boas práticas de GitHub

<!-- Página GERADA por scripts/gerar_curso.py. Edite aulas.yml e curso/conteudo/. -->

<div class="rl-aula" data-aula="16" data-onde="container" data-lab=""></div>

| | |
| --- | --- |
| Origem no guia | Guia Parte [15](../guia/parte-15.md), Guia Parte [16](../guia/parte-16.md) |
| Depende de | [Aula 01](aula-01.md), [Aula 02](aula-02.md), [Aula 03](aula-03.md), [Aula 04](aula-04.md), [Aula 05](aula-05.md), [Aula 06](aula-06.md), [Aula 07](aula-07.md), [Aula 08](aula-08.md), [Aula 09](aula-09.md), [Aula 10](aula-10.md), [Aula 11](aula-11.md), [Aula 12](aula-12.md), [Aula 13](aula-13.md), [Aula 14](aula-14.md), [Aula 15](aula-15.md) |
| Entregas | `pyproject.toml`, `.github/workflows/ci.yml`, `README.md`, `LICENSE`, `tag v1.0.0` |
| Onde os checks rodam | Container spark |

A última aula transforma o lakehouse num projeto profissional: testes que rodam a cada push, análise estática, histórico de commits legível e um README que mostra decisões, resultados e limitações.

## 1. Objetivos e pré-requisitos

1. Distinguir teste de unidade, teste de fumaça, checagem de dados e os checks da plataforma.
2. Configurar pytest e ruff no `pyproject.toml`.
3. Montar um CI no GitHub Actions que roda sem MinIO.
4. Usar Conventional Commits, branches e Pull Requests.
5. Escrever um README de portfólio e publicar uma versão.

**Pré-requisitos:** todas as aulas anteriores; conta no GitHub.

## 2. Contextualização

Código de dados quebra de forma silenciosa: um ajuste numa regra da silver passa sem erro e muda um número da gold. Testes automatizados avisam antes de alguém ver um gráfico estranho. E, num projeto de portfólio, o repositório é avaliado pelo que mostra sem que você esteja presente: CI verde, commits claros e um README que explica as escolhas dizem mais que o código em si.

## 3. Fundamentação teórica

### 3.1 Tipos de verificação (guia, Parte [15.1](../guia/parte-15.md#parte-15-1))

| Tipo | O que verifica | Quando roda | Precisa de MinIO? | No projeto |
| --- | --- | --- | --- | --- |
| Teste de unidade | Uma função isolada, com dados minúsculos | A cada commit (CI) | Não | `tests/` |
| Teste de fumaça | A infraestrutura funciona de ponta a ponta | Ao subir o ambiente | Sim | `scripts/smoke_test.py` |
| Checagem de dados | O dado real faz sentido | A cada execução do pipeline | Sim | `src/checks.py` |
| Checks da plataforma | O aluno concluiu cada aula | Sob demanda (`make check`) | Depende da aula | `labcheck/` |

### 3.2 Análise estática com ruff

Análise estática lê o código sem executá-lo e aponta problemas. As regras escolhidas pelo guia:

| Grupo | Detecta |
| --- | --- |
| `E` | Erros de estilo (pycodestyle) |
| `F` | Erros reais: import não usado, nome indefinido (pyflakes) |
| `I` | Ordem de imports |
| `B` | Bugs comuns (flake8-bugbear), ex.: argumento padrão mutável |
| `UP` | Sintaxe moderna para a versão do Python |

### 3.3 CI sem MinIO

Os testes de unidade usam DataFrames em memória e não precisam de S3. Por isso as transformações foram escritas como **funções puras** (guia, Parte [15.5](../guia/parte-15.md#parte-15-5); Aula 13). O CI só precisa de Python, Java e as dependências.

### 3.4 Conventional Commits (guia, Parte [16.1](../guia/parte-16.md#parte-16-1))

Formato: `tipo(escopo opcional): descrição no imperativo`.

| Tipo | Uso | Exemplo |
| --- | --- | --- |
| `feat` | Nova funcionalidade | `feat(gold): tabela de gap salarial por sexo` |
| `fix` | Correção | `fix(silver): tratar CNAE com menos de 5 dígitos` |
| `docs` | Documentação | `docs: explicar tuning no README` |
| `refactor` | Mudança interna sem alterar comportamento | `refactor: centralizar escrita Delta` |
| `test` | Testes | `test: cobrir to_decimal` |
| `chore` | Manutenção | `chore: atualizar delta-spark` |
| `perf` | Performance | `perf: broadcast nas dimensões` |

Commits pequenos e frequentes: um commit faz **uma** coisa.

### 3.5 Branches e Pull Requests (guia, Parte [16.2](../guia/parte-16.md#parte-16-2))

- A `main` está sempre funcionando.
- Uma branch por funcionalidade (`feat/`, `fix/`, `docs/`, `refactor/`).
- Mesmo sozinho, use PRs: o CI roda antes do merge e o PR documenta o porquê da mudança.

## 4. Arquitetura e fluxo

```
 branch feat/... ── commits ── git push ──▶ GitHub
                                          │
                                          ▼
                               Actions (ci.yml)
                               ├─ setup Python 3.11 + Java 17
                               ├─ pip install requirements*
                               ├─ ruff check .
                               └─ pytest  (tests/, sem MinIO)
                                          │ verde
                                          ▼
                               Pull Request ── merge ──▶ main ── tag v1.0.0
```

## 5. Tutorial

### Passo 1 — `pyproject.toml` (guia, Parte [15.2](../guia/parte-15.md#parte-15-2))

```toml
[project]
name = "rais-lakehouse"
version = "0.1.0"
description = "Lakehouse open source da RAIS com PySpark, Delta Lake e MinIO"
requires-python = ">=3.11"

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP"]   # erros, imports, bugs comuns, sintaxe moderna

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

- `testpaths = ["tests"]`: `pytest` sem argumentos roda só `tests/` — **não** os checks da plataforma, que precisam do ambiente.
- `pythonpath = ["."]`: permite `from src...` nos testes sem instalar o pacote.

### Passo 2 — Testes de unidade

`tests/conftest.py` e `tests/test_utils.py` já existem (Aulas 10 e 13). Confira:

```bash
make test     # pytest -q dentro do container
make lint     # ruff check .
make fmt      # ruff format . (formata)
```

Corrija o que o ruff apontar; `ruff check --fix .` resolve parte automaticamente.

### Passo 3 — CI (guia, Parte [15.5](../guia/parte-15.md#parte-15-5))

`.github/workflows/ci.yml`:

```yaml
name: ci

on:
  push:
    branches: [main]
  pull_request:

jobs:
  testes:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip

      - uses: actions/setup-java@v4
        with:
          distribution: temurin
          java-version: "17"

      - name: Instalar dependências
        run: pip install -r requirements.txt -r requirements-dev.txt

      - name: Lint
        run: ruff check .

      - name: Testes
        run: pytest -q
```

| Trecho | Significado |
| --- | --- |
| `on: push (main)` e `pull_request` | Roda em todo push na main e em todo PR |
| `runs-on: ubuntu-latest` | Máquina virtual Linux do GitHub |
| `actions/checkout@v4` | Baixa o repositório |
| `setup-python` com `cache: pip` | Python 3.11, com cache das dependências entre execuções |
| `setup-java` (temurin 17) | Java para o PySpark |
| `ruff check .` e `pytest -q` | Falha o CI se lint ou testes falharem |

**passo da plataforma.** Depois que o site do curso existir (`curso/mkdocs.yml`), acrescente um passo que faça o build do site para pegar links quebrados. O comando exato do Zensical deve ser confirmado na documentação dele (plano técnico, seção 4).

### Passo 4 — Publicar no GitHub

```bash
git status                         # nada de .env, staging/*, progress/
git add . && git commit -m "test: testes de unidade e CI"
git remote add origin <url-do-seu-repositório>
git push -u origin main
```

Abra a aba **Actions** do repositório: o workflow deve ficar verde.

### Passo 5 — Fluxo com branch e PR (guia, Parte [16.2](../guia/parte-16.md#parte-16-2))

```bash
git switch -c feat/gold-faixa-etaria       # uma branch por funcionalidade
# ...trabalho e commits..
git push -u origin feat/gold-faixa-etaria  # depois abra um PR no GitHub
```

### Passo 6 — README (guia, Parte [16.3](../guia/parte-16.md#parte-16-3))

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

Para portfólio, as seções que mais pesam são **Decisões técnicas**, **Resultados** (um gráfico vale muito) e **Limitações** (guia). Ajuste o intervalo de anos ao que você realmente processou.

### Passo 7 — Licença e versão (guia, Parte [16.4](../guia/parte-16.md#parte-16-4))

- **LICENSE:** escolha uma (MIT é a mais simples) para deixar claro como outros podem usar o código. O GitHub oferece modelos ao criar o arquivo pela interface.
- **Tags:** marque marcos.

```bash
git tag v1.0.0 && git push --tags
```

O guia sugere marcos como v0.1 = bronze/silver e v0.2 = gold; a v1.0.0 marca o curso concluído.

## 6. Funcionamento e resultados esperados

| Item | Esperado |
| --- | --- |
| `make test` | Todos os testes de `tests/` passando |
| `make lint` | Nenhum erro |
| Aba Actions | Workflow verde no último push |
| README | Seções do passo 6 preenchidas com o seu projeto |
| `git log --oneline` | Mensagens no padrão Conventional Commits |

## 7. Exemplos práticos

**Exemplo 1 — Um teste que pega uma regressão.** Mude temporariamente o `rlike` do município na silver para `^\d{5}$`, extraia a validação para uma função pura e escreva um teste com `"261160"`: o teste falha e mostra o erro antes de qualquer pipeline rodar.

**Exemplo 2 — Histórico legível.**

```text
feat(gold): tabela de faixa etária
test(gold): cobrir faixas de idade
fix(silver): aceitar município com 6 dígitos apenas
docs: limitações do eSocial no README
```

**Exemplo 3 — Issues como backlog (guia, Parte [16.4](../guia/parte-16.md#parte-16-4)).** Abra issues como "Adicionar RAIS Estabelecimentos" ou "Migrar gold para Iceberg" (Apêndice G).

## 8. Armadilhas, diagnóstico e soluções

| Sintoma | Causa | Solução |
| --- | --- | --- |
| CI falha com `JAVA_HOME is not set` ou erro de gateway do Java | Falta o `setup-java` | Passo 3 |
| CI falha em `ModuleNotFoundError: src` | Falta `pythonpath` no `pyproject.toml` | Passo 1 |
| CI tenta acessar MinIO | Teste de unidade importando código que lê o lake na importação | Manter funções puras; leitura só dentro de funções |
| `pytest` local roda os checks da plataforma | Rodado com caminho `labcheck/` | `make test` (usa `testpaths`) |
| `.env` commitado | Faltou `.gitignore` | Remover e **trocar as senhas**: apagar o commit não basta (guia, Parte [16.4](../guia/parte-16.md#parte-16-4)) |
| PR com dezenas de mudanças misturadas | Commits grandes | Uma branch e um tema por PR |

## 9. Boas práticas (guia, Parte [16](../guia/parte-16.md))

1. Commits pequenos e frequentes, no padrão Conventional Commits.
2. `main` sempre funcionando; PRs mesmo trabalhando sozinho.
3. Testes de unidade para toda função de transformação nova.
4. Atualizar dependências de propósito, uma de cada vez, com o CI verde.
5. README com decisões, resultados e limitações.
6. Issues do GitHub como backlog.

## 10. Riscos

| Tipo | Risco | Mitigação |
| --- | --- | --- |
| Segurança | Segredo no histórico público | `.gitignore`; se vazar, trocar senhas |
| Segurança | Dados no repositório público | `staging/*`, `*.7z`, `*.parquet` ignorados (Aula 05) |
| Integridade | Regressão silenciosa | Testes de unidade e CI |
| Integridade | Checagem de dados desligada "para passar" | Calibrar limites com evidência e registrar |
| Reputação | README promete o que o projeto não faz | Seção de limitações honesta |

## 11. Laboratório e validação na plataforma

**Contribuição ao projeto:** o projeto final fica testado, documentado e publicado.

`labcheck/test_aula16.py`:

```python
"""Checks da Aula 16: qualidade e publicação."""
import subprocess
from pathlib import Path

SECOES_README = ["## Arquitetura", "## Como rodar", "## Decisões técnicas", "## Limitações"]


def rodar(*cmd: str) -> subprocess.CompletedProcess:
    return subprocess.run(list(cmd), capture_output=True, text=True)


def test_a16_testes_passam():
    r = rodar("pytest", "-q", "tests")
    assert r.returncode == 0, r.stdout[-800:]


def test_a16_lint_passa():
    r = rodar("ruff", "check", ".")
    assert r.returncode == 0, r.stdout[-800:]


def test_a16_workflow_ci():
    ci = Path(".github/workflows/ci.yml")
    assert ci.exists(), "Crie .github/workflows/ci.yml (passo 3)."
    texto = ci.read_text()
    assert "pytest" in texto and "ruff" in texto and "setup-java" in texto


def test_a16_readme_completo():
    texto = Path("README.md").read_text(encoding="utf-8")
    faltando = [s for s in SECOES_README if s not in texto]
    assert not faltando, f"Seções ausentes no README: {faltando}"


def test_a16_licenca():
    assert Path("LICENSE").exists(), "Acrescente um arquivo LICENSE (passo 7)."
```

- O CI verde no GitHub não é verificável daqui sem credenciais; ele fica no checklist manual.
- Rode com `make check AULA=16`, depois `make progresso` para ver o curso inteiro.

**Checklist manual:**

- [ ] Actions verde no último push
- [ ] abri ao menos um PR
- [ ] README tem um gráfico gerado a partir da gold
- [ ] tag `v1.0.0` publicada.

## 12. Exercícios, revisão e desafios

**Exercícios**

1. Escreva testes de unidade para `emprego_uf` e `desligamento` (Aula 13) com DataFrames de 3 a 5 linhas.
2. Quebre um teste de propósito numa branch, abra um PR e veja o CI bloquear.
3. Reescreva três mensagens de commit antigas suas no padrão Conventional Commits (só como exercício; não reescreva histórico publicado).

**Revisão**

1. Por que o CI funciona sem MinIO?
2. Qual a diferença entre `tests/` e `labcheck/`?
3. Por que apagar o commit com `.env` não basta?
4. Quais seções do README mais pesam num portfólio?

**Respostas sugeridas:** (1) testes de unidade usam DataFrames em memória e funções puras; (2) `tests/` testa o código e roda no CI; `labcheck/` verifica o estado do seu ambiente; (3) o histórico e cópias já feitas guardam o conteúdo — troque as senhas; (4) decisões técnicas, resultados e limitações.

**Desafios**

1. Acrescente ao CI um job que roda o teste de fumaça com `RAIS_LAKE=file:///tmp/lake` (sem MinIO). Que configurações do `get_spark` atrapalham e como contorná-las?
2. Use a amostra sintética da plataforma (plano técnico, seção 2) para um teste de integração bronze → silver → gold no CI.

## 13. Referências cruzadas

| Tema | Onde |
| --- | --- |
| ADRs | Aula 01 |
| `requirements*.txt` | Aula 02 |
| `.gitignore` e primeiro commit | Aula 05 |
| `tests/conftest.py`, `test_utils.py` | Aulas 10 e 13 |
| `checks.py` | Aula 14 |
| Checklists e comandos | Apêndices D e E |
| Próximos passos | Apêndice G |


## Checks automáticos

```bash
make check AULA=16 ANO=2022
```

Arquivo: `labcheck/test_aula16.py`. Cada execução grava o resultado em `progress/historico.jsonl`; depois rode `make progresso` para atualizar a página [Progresso](../progresso.md).

| Check | O que verifica |
| --- | --- |
| `a16_testes_passam` | testes passam |
| `a16_lint_passa` | lint passa |
| `a16_workflow_ci` | workflow ci |
| `a16_readme_completo` | readme completo |
| `a16_licenca` | licenca |
