"""Gera as páginas do site do curso (curso/docs/) a partir de curso/aulas.yml e de labcheck/.

[Complemento da plataforma] Fonte única: os metadados ficam no YAML e a lista de checks é
lida dos próprios arquivos de teste (com `ast`, sem importar nada). Assim o site nunca
descreve um check que não existe. O texto de cada aula vem de curso/conteudo/aula-NN.md
(export em Markdown do documento da aula); sem ele, a página aponta para o documento.

Uso: python -m scripts.gerar_curso
"""
import ast
import re
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
META = RAIZ / "curso" / "aulas.yml"
DOCS = RAIZ / "curso" / "docs"
CONTEUDO = RAIZ / "curso" / "conteudo"
ONDE = {"host": "Host (WSL/Linux)", "container": "Container spark"}


def arquivo_de_checks(aula: int) -> Path | None:
    for pasta in ("labcheck/host", "labcheck"):
        p = RAIZ / pasta / f"test_aula{aula:02d}.py"
        if p.exists():
            return p
    return None


def checks(arquivo: Path) -> list[tuple[str, str]]:
    """[(id, descrição)] a partir das funções test_* e de suas docstrings."""
    arvore = ast.parse(arquivo.read_text(encoding="utf-8"))
    saida = []
    for no in arvore.body:
        if isinstance(no, ast.FunctionDef) and no.name.startswith("test_"):
            doc = (ast.get_docstring(no) or "").splitlines()
            ident = no.name.removeprefix("test_")
            # Sem docstring: a07_media_por_sexo -> "media por sexo"
            legivel = ident.split("_", 1)[1].replace("_", " ")
            saida.append((ident, doc[0] if doc else legivel))
    return saida


def comando(aula: int, onde: str, arquivo: Path) -> str:
    if onde == "host":
        if arquivo.parent.name == "host":
            return f"make check-host AULA={aula:02d}"
        rel = arquivo.relative_to(RAIZ)
        return f".venv-host/bin/pytest -v {rel}   # ou: make check AULA={aula:02d}"
    return f"make check AULA={aula:02d} ANO=2022"


def limpar_conteudo(md: str, url_doc: str) -> str:
    """Adapta o export do documento à página: tira o repetido e o que não renderiza."""
    linhas = md.splitlines()
    # Título (a página gera o seu) e a linha de data/autor do documento
    while linhas and (not linhas[0].strip() or linhas[0].startswith("# ")
                      or re.match(r"^[A-Z][a-z]{2} \d{1,2}, \d{4}", linhas[0])):
        linhas.pop(0)
    texto = "\n".join(linhas)
    # Bloco de metadados (já está na tabela do topo da página)
    texto = re.sub(r"```yaml\n(?:#[^\n]*\n)?aula: .*?```\n+", "", texto, count=1, flags=re.S)
    # Diagramas interativos do documento não vêm no export
    texto = re.sub(
        r"&#91;embedded content: (.+?)\\\]",
        lambda m: f'!!! note "Diagrama interativo"\n    "{m.group(1)}" está no '
                  f"[documento original]({url_doc}).",
        texto,
    )
    # Checklists escritos numa linha só ("**Checklist manual:** \[ \] a · \[ \] b") viram listas
    def lista(m: re.Match) -> str:
        itens = [i.strip() for i in re.split(r"\s*·\s*", m.group(2))]
        itens = [re.sub(r"^\\\[ \\\]\s*", "", i) for i in itens if i]
        return f"{m.group(1)}\n\n" + "\n".join(f"- [ ] {i}" for i in itens)

    texto = re.sub(r"^(\*\*[^*\n]+:?\*\*:?)\s*(\\\[ \\\].*)$", lista, texto, flags=re.M)
    return texto.strip() + "\n"


def qtd_criterios(n: int) -> int:
    """Itens de checklist da aula: são os critérios que a página deixa marcar."""
    fonte = CONTEUDO / f"aula-{n:02d}.md"
    if not fonte.exists():
        return 0
    return len(re.findall(r"^\s*- \[ \] ", limpar_conteudo(fonte.read_text(encoding="utf-8"), ""),
                          flags=re.M))


def arquivo_lab(a: dict) -> str:
    """Primeiro arquivo de entrega que existe e abre bem no JupyterLab (para o botão da página)."""
    for e in a["entrega"]:
        caminho = e.split(" ")[0]
        if (caminho.endswith((".py", ".ipynb")) and not Path(caminho).name.startswith("__")
                and (RAIZ / caminho).exists()):
            return caminho
    return ""


def pagina_aula(a: dict, base: str) -> str:
    n = a["aula"]
    arq = arquivo_de_checks(n)
    lista = checks(arq) if arq else []
    url_doc = f"{base}/{a['doc']}"
    fonte = CONTEUDO / f"aula-{n:02d}.md"
    dep = ", ".join(f"[Aula {d:02d}](aula-{d:02d}.md)" for d in a["depende_de"]) or "—"
    linhas = [
        "---",
        f"aula: {n}",
        f'titulo: "{a["titulo"]}"',
        f"origem: {a['origem']}",
        f"depende_de: {a['depende_de']}",
        f"checks: {[c for c, _ in lista]}",
        "---",
        "",
        f"# Aula {n:02d} — {a['titulo']}",
        "",
        "<!-- Página GERADA por scripts/gerar_curso.py. Edite aulas.yml e curso/conteudo/. -->",
        "",
        f'<div class="rl-aula" data-aula="{n}" data-onde="{a["onde"]}" '
        f'data-lab="{arquivo_lab(a)}"></div>',
        "",
        "| | |",
        "| --- | --- |",
        f"| Origem no guia | {', '.join(a['origem'])} |",
        f"| Depende de | {dep} |",
        f"| Entregas | {', '.join(f'`{e}`' for e in a['entrega'])} |",
        f"| Onde os checks rodam | {ONDE[a['onde']]} |",
        f"| Documento original | [abrir]({url_doc}) |",
        "",
    ]
    if fonte.exists():
        linhas += [limpar_conteudo(fonte.read_text(encoding="utf-8"), url_doc), ""]
    else:
        linhas += [
            '!!! warning "Conteúdo ainda não importado"',
            f"    O texto desta aula ainda não está em `curso/conteudo/aula-{n:02d}.md`. "
            f"Leia no [documento da Aula {n:02d}]({url_doc}).",
            "",
        ]
    linhas += ["## Checks automáticos", ""]
    if arq:
        linhas += [
            "```bash",
            comando(n, a["onde"], arq),
            "```",
            "",
            f"Arquivo: `{arq.relative_to(RAIZ)}`. Cada execução grava o resultado em "
            "`progress/historico.jsonl`; depois rode `make progresso` para atualizar a página "
            "[Progresso](../progresso.md).",
            "",
            "| Check | O que verifica |",
            "| --- | --- |",
        ]
        linhas += [f"| `{c}` | {d} |" for c, d in lista]
    else:
        linhas.append("Esta aula não tem checks automáticos.")
    return "\n".join(linhas) + "\n"


def pagina_indice(meta: dict, base: str) -> str:
    linhas = [
        "# RAIS Lakehouse — Plataforma de aprendizagem",
        "",
        "Curso prático de PySpark, Delta Lake e MinIO construindo um lakehouse com os "
        "microdados da RAIS (bronze → silver → gold), tudo open source e local.",
        "",
        "## Como estudar",
        "",
        "1. Abra a aula na trilha abaixo e estude o conteúdo na própria página.",
        "2. Faça o tutorial e o laboratório no [Ambiente](ambiente.md) (JupyterLab e MinIO "
        "integrados), no terminal ou no VS Code.",
        "3. Marque os critérios de conclusão na página da aula: eles ficam gravados em "
        "`progress/estudo.json`.",
        "4. Rode os checks da aula. Só avance quando passarem; o resultado aparece na trilha.",
        "",
        "> Os checks verificam o **seu** ambiente. Este site não executa código e não "
        "mostra resultados que você não produziu.",
        "",
        "## Trilha",
        "",
        '<div id="rl-resumo"></div>',
        "",
        "| Aula | Título | Depende de | Checks | Progresso |",
        "| --- | --- | --- | --- | --- |",
    ]
    for a in meta["aulas"]:
        n = a["aula"]
        arq = arquivo_de_checks(n)
        dep = ", ".join(f"{d:02d}" for d in a["depende_de"]) or "—"
        linhas.append(f"| {n:02d} | [{a['titulo']}](aulas/aula-{n:02d}.md) | {dep} | "
                      f"{len(checks(arq)) if arq else 0} | "
                      f'<span class="rl-trilha" data-aula="{n}" '
                      f'data-criterios="{qtd_criterios(n)}">—</span> |')
    linhas += [
        "",
        f"Apêndices A–G: [página de apêndices](apendices.md). "
        f"Diagnóstico e plano técnico da plataforma: [documento]({base}/{meta['plano_doc']}).",
    ]
    return "\n".join(linhas) + "\n"


def pagina_apendices(meta: dict, base: str) -> str:
    url_doc = f"{base}/{meta['apendices_doc']}"
    fonte = CONTEUDO / "apendices.md"
    if fonte.exists():
        return "# Apêndices\n\n" + limpar_conteudo(fonte.read_text(encoding="utf-8"), url_doc)
    linhas = ["# Apêndices", "", f"Todos os apêndices estão num único documento: "
              f"[abrir os apêndices]({url_doc}).", ""]
    linhas += [f"- Apêndice {t}" for t in meta["apendices"]]
    return "\n".join(linhas) + "\n"


def pagina_ambiente() -> str:
    return "\n".join([
        "# Ambiente",
        "",
        "<!-- Página GERADA por scripts/gerar_curso.py. -->",
        "",
        "JupyterLab, console do MinIO e Spark UI num só lugar. As ferramentas abrem aqui "
        "dentro; se preferir, use **abrir em nova aba**.",
        "",
        '<div id="rl-ambiente"></div>',
        "",
        '??? info "Primeiro acesso"',
        "    - **JupyterLab:** na primeira vez, cole o token (`JUPYTER_TOKEN` do `.env`).",
        "    - **MinIO:** entre com `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` do `.env`.",
        "    - **Spark UI:** só existe enquanto há uma sessão Spark aberta (Aula 06).",
        "",
    ]) + "\n"


def main() -> None:
    meta = yaml.safe_load(META.read_text(encoding="utf-8"))
    base = meta["docs_base"]
    (DOCS / "aulas").mkdir(parents=True, exist_ok=True)
    for a in meta["aulas"]:
        destino = DOCS / "aulas" / f"aula-{a['aula']:02d}.md"
        destino.write_text(pagina_aula(a, base), encoding="utf-8")
    (DOCS / "index.md").write_text(pagina_indice(meta, base), encoding="utf-8")
    (DOCS / "apendices.md").write_text(pagina_apendices(meta, base), encoding="utf-8")
    (DOCS / "ambiente.md").write_text(pagina_ambiente(), encoding="utf-8")
    print(f"[curso] {len(meta['aulas'])} aulas geradas em {DOCS}")


if __name__ == "__main__":
    main()
